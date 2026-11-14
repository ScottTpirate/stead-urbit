#!/usr/bin/env python3
"""Owner-local live pilot checks. Run behind the host traffic fence."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import stat
import struct
from urllib.parse import urlsplit

import core_conn
import project_migration
from digests import read_source, sha
from execution_policy import GuardError, directory_fd
from portable_code import private_directory, publish_directory
from portable_recovery import UUID, match, private_file, same_entry, same_path


ROOT = Path(__file__).resolve().parents[2]
SHIP = re.compile(r'~[a-z]+(?:-{1,2}[a-z]+)*\Z')
DESK = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')
TOKEN = re.compile(r'[0-9a-f]{64}\Z')
MAX_REVISION = 2**64 - 1
JOURNAL_PAGE_BYTES = 32_768


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = dict(pairs)
    require(len(result) == len(pairs), 'Duplicate JSON property')
    return result


def revision(value):
    require(isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,19}', value)
            and int(value) <= MAX_REVISION, 'Use the reviewed positive configuration revision')
    return value


def token(value):
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def approved_runtime(digest):
    lock = json.loads((ROOT / 'specs/urbit/toolchain.lock.json').read_bytes(), object_pairs_hook=unique)
    require(digest == lock['runtime']['binary_sha256'],
            'Approved live runtime must also match the exact candidate toolchain pin')
    return digest


def private_pier(pier):
    pier = pier.absolute()
    uid = os.geteuid()
    require(uid > 0, 'Use the dedicated non-root Vere service account')
    require(pier.resolve(strict=True) == pier, 'Use the actual pier path without aliases')
    for directory in (pier, pier / '.urb'):
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == uid and not info.st_mode & 0o077,
                'Pier and .urb must be owned by the service account and private')
    return pier


def pem(path, *, private):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1
                and (not private or stat.S_IMODE(info.st_mode) == 0o600),
                'Use a regular, operator-owned PEM file with private key mode 0600')
        raw = source.read(16385)
    lines = raw.splitlines()
    require(len(raw) <= 16384 and 0 < len(lines) <= (64 if private else 128)
            and all(0 < len(line) <= 256 and all(32 <= byte <= 126 for byte in line) for line in lines),
            'PEM exceeds native input bounds')
    return '[' + ' '.join(core_conn.atom(line) for line in lines) + ' ~]'


class OwnerProcess:
    def __init__(self, pid, binary, pier, digest, *, desk, role):
        require(DESK.fullmatch(desk) and role in ('home', 'identity'), 'Use the installed pilot desk and role')
        self.desk = desk
        self.role = role
        self.proc = Path(f'/proc/{pid}')
        self.pid = pid
        self.binary = binary.absolute()
        self.pier = private_pier(pier)
        self.uid = os.geteuid()
        require(pid > 1, 'Use the current supervised Vere PID')
        self.socket = self.pier / '.urb' / 'conn.sock'
        require(token(digest) and sha(self.binary) == digest, 'Vere executable differs from the pinned digest')
        with (self.proc / 'exe').open('rb') as source:
            require(hashlib.file_digest(source, 'sha256').hexdigest() == digest,
                    'Running Vere executable differs from the pinned digest')
        self.started = self.start_time()
        self.check()

    def start_time(self):
        fields = (self.proc / 'stat').read_text().rsplit(')', 1)[1].split()
        require(fields[0] not in ('Z', 'X'), 'Vere has exited')
        return fields[19]

    def check(self):
        require(self.proc.stat().st_uid == self.uid and self.start_time() == self.started
                and (self.proc / 'exe').resolve(strict=True) == self.binary.resolve(strict=True),
                'Vere ownership or process identity changed')
        argv = (self.proc / 'cmdline').read_bytes().split(b'\0')[:-1]
        require(bool(argv) and argv[-1] == os.fsencode(self.pier), 'Vere was started with a different pier path')
        info = self.socket.lstat()
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == self.uid, 'Khan socket ownership changed')

    def peer(self, channel):
        pid, uid, _ = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require((pid, uid) == (self.pid, self.uid), 'Khan socket did not connect to the reviewed Vere process')
        self.check()

    def tls(self, host, port, digest):
        self.check()
        require(token(digest) and 0 < port <= 65535, 'Use the reviewed TLS certificate digest and listener port')
        owned = set()
        for descriptor in (self.proc / 'fd').iterdir():
            try:
                link = descriptor.readlink().as_posix()
            except FileNotFoundError:
                continue
            match = re.fullmatch(r'socket:\[(\d+)\]', link)
            if match:
                owned.add(match[1])
        listeners = set()
        for name in ('tcp', 'tcp6'):
            for line in (Path('/proc/self/net') / name).read_text().splitlines()[1:]:
                fields = line.split()
                if fields[3] == '0A' and int(fields[1].rsplit(':', 1)[1], 16) == port:
                    listeners.add(fields[9])
        require(bool(listeners) and listeners <= owned, 'The reviewed Vere process must own the TLS listener exclusively')
        with socket.create_connection(('127.0.0.1', port), timeout=5) as connection:
            with ssl.create_default_context().wrap_socket(connection, server_hostname=host) as tls:
                require(hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest() == digest,
                        'Native TLS served a different certificate')
        self.check()

    def call(self, ship, mode, route, value):
        require(len(ship) <= 64 and SHIP.fullmatch(ship), 'Use the expected canonical ship name')
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode() if value is not None else b''
        path = '~'
        if mode == 'project-journal-page':
            require(self.role == 'home' and re.fullmatch(r'0|[1-9][0-9]{0,7}', route)
                    and int(route) < project_migration.MAX_JOURNAL and 0 < len(raw) <= 2048,
                    'Use the exact retired project scope and a bounded byte offset')
            path = f'[%project-journal {core_conn.atom(raw)} {core_conn.atom(route.encode())} ~]'
            raw = b''
        elif route:
            segment = {'bootstrap': 'bootstrap', 'operator-status': 'operator',
                       'project-retirement-status': 'project-retirement'}[mode]
            path = f'[%{segment} {core_conn.atom(route.encode())} ~]'
        if mode == 'handoff-status':
            path = '[%home-handoff %status ~]'
        if mode == 'pack-relay-status':
            require(self.role == 'home' and not route and value is None, 'Pack relay status belongs to Home')
            path = '[%pack-relay %status ~]'
        if mode == 'pack-relay-policy':
            require(self.role == 'home' and not route and 0 < len(raw) <= 2048, 'Use a bounded Home pack relay policy')
        require(len(raw) <= 65536, 'Home configuration exceeds the native limit')
        noun = (f'[32 %fyrd [%{self.desk} %stead-pilot-owner %noun '
                f'[%noun [{ship} %stead-{self.role} %{mode} {path} {core_conn.atom(raw)}]]]]')
        return self.exchange(noun)

    def install_certificate(self, ship, key, chain):
        require(len(ship) <= 64 and SHIP.fullmatch(ship), 'Use the expected canonical ship name')
        key_noun = pem(key, private=True)
        chain_noun = pem(chain, private=False)
        noun = (f'[32 %fyrd [%{self.desk} %stead-pilot-cert %noun '
                f'[%noun [{ship} {key_noun} {chain_noun}]]]]')
        require(self.exchange(noun) == {'requested': 'yes'}, 'Native Eyre certificate request failed')

    def exchange(self, noun):
        self.check()
        try:
            response = core_conn.exchange(self.binary, self.socket, noun, check_peer=self.peer)
        except Exception:
            # Framing traces can include private configuration and certificate keys.
            raise ValueError('Owner-local Gall exchange failed') from None
        self.check()
        value = (response['outcome'] or {}).get('json')
        require(isinstance(value, dict) and value.get('protocol') != 'stead.test-terminal/1',
                'Native app did not acknowledge the owner-local operation')
        return value


def status(owner, ship, expected):
    nonce = secrets.token_hex(32)
    value = owner.call(ship, 'operator-status', nonce, None)
    require(value.keys() == {'protocol', 'home', 'nonce', 'origin', 'custody', 'runtime', 'config_revision',
                             'runtime_matches', 'projection_ready', 'available', 'incarnation'}
            and value['protocol'] == 'stead.operator-status/1' and value['home'] == ship and value['nonce'] == nonce
            and value['runtime'] == 'live-synthetic' and value['custody'] == 'operator-pilot'
            and value['runtime_matches'] == 'yes' and value['config_revision'] == expected
            and value['projection_ready'] in ('yes', 'no') and value['available'] in ('yes', 'no')
            and ((value['available'] == 'yes' and token(value['incarnation']))
                 or (value['available'] == 'no' and value['incarnation'] == '')),
            'Native status differs from the reviewed live Home identity, profile, revision or incarnation')
    return value


def bootstrap(owner, ship, expected, *, origin, port, certificate, previous=None):
    before = status(owner, ship, expected)
    require(before['projection_ready'] == 'yes' and before['available'] == 'no' and before['origin'] == origin,
            'Expected the configured live Home with ready projection and closed startup state')
    host = urlsplit(origin).hostname
    require(host is not None, 'Expected the reviewed Home HTTPS origin')
    owner.tls(host, port, certificate)
    nonce = secrets.token_hex(32)
    value = owner.call(ship, 'bootstrap', nonce,
                       {'protocol': 'stead.bootstrap/2', 'nonce': nonce, 'expected_revision': expected})
    require(value.keys() == {'protocol', 'status', 'home', 'nonce', 'incarnation', 'runtime', 'config_revision'}
            and value['protocol'] == 'stead.bootstrap/2' and value['status'] == 'ready'
            and value['home'] == ship and value['nonce'] == nonce and value['runtime'] == 'live-synthetic'
            and value['config_revision'] == expected and token(value['incarnation'])
            and value['incarnation'] != previous, 'Native bootstrap acknowledgement did not match this start')
    after = status(owner, ship, expected)
    require(after['available'] == after['projection_ready'] == 'yes' and after['origin'] == origin
            and after['incarnation'] == value['incarnation'], 'Native Home readiness changed after bootstrap')
    owner.tls(host, port, certificate)
    return {'home': ship, 'runtime': 'live-synthetic', 'pid': owner.pid,
            'config_revision': expected, 'incarnation': after['incarnation']}


def bootstrap_identity(owner, ship, *, origin, port, certificate, previous=None):
    host = urlsplit(origin).hostname
    require(host is not None, 'Expected the reviewed Identity HTTPS origin')
    owner.tls(host, port, certificate)
    nonce = secrets.token_hex(32)
    value = owner.call(ship, 'bootstrap', nonce, {'protocol': 'stead.bootstrap/1', 'nonce': nonce})
    require(value.keys() == {'protocol', 'status', 'home', 'nonce', 'incarnation'}
            and value['protocol'] == 'stead.bootstrap/1' and value['status'] == 'ready'
            and value['home'] == ship and value['nonce'] == nonce and token(value['incarnation'])
            and value['incarnation'] != previous, 'Native Identity acknowledgement did not match this start')
    owner.tls(host, port, certificate)
    return {'identity': ship, 'pid': owner.pid, 'incarnation': value['incarnation']}


def handoff_status(owner, ship):
    value = owner.call(ship, 'handoff-status', '', None)
    require(value.keys() == {'protocol', 'home', 'phase', 'generation'}
            and value['protocol'] == 'stead.home-handoff/1' and value['home'] == ship
            and value['phase'] in ('open', 'sealed'), 'Unexpected native handoff status')
    revision(value['generation'])
    return value


def relay_status(owner, ship):
    value = owner.call(ship, 'pack-relay-status', '', None)
    require(set(value) == {'protocol', 'status', 'generation', 'incarnation'}
            and value['protocol'] == 'stead.git-pack-relay-status/1'
            and value['status'] in ('open', 'closed')
            and re.fullmatch(r'0|[1-9][0-9]{0,19}', value['generation'])
            and int(value['generation']) <= MAX_REVISION
            and (token(value['incarnation']) or value['incarnation'] == '' and value['status'] == 'closed'),
            'Native pack relay status differs from the expected profile')
    return value


def relay_policy(owner, ship, policy):
    require(isinstance(policy, dict) and policy.get('protocol') == 'stead.git-pack-relay-policy/1',
            'Use a reviewed pack relay policy')
    operation = policy.get('operation')
    require(operation in ('open', 'close'), 'Use an explicit pack relay operation')
    before = relay_status(owner, ship)
    require(policy.get('expected_generation') == before['generation'] and token(before['incarnation']),
            'Pack relay generation or Home incarnation changed')
    if operation == 'open':
        require(before['status'] == 'closed' and policy.get('incarnation') == before['incarnation'],
                'Pack relay open requires the current closed Home incarnation')
        expected = revision(policy.get('worker_generation'))
    else:
        expected = revision(str(int(before['generation']) + 1))
    require(owner.call(ship, 'pack-relay-policy', '', policy) == {}, 'Pack relay policy acknowledgement differs')
    after = relay_status(owner, ship)
    require(after['generation'] == expected and after['incarnation'] == before['incarnation']
            and after['status'] == ('open' if operation == 'open' else 'closed'),
            'Pack relay policy readback differs')
    return after


def change_handoff(owner, ship, operation, generation, proof):
    require(operation in ('seal', 'activate') and token(proof), 'Use the exact handoff challenge or ticket')
    generation = revision(generation)
    sealing = operation == 'seal'
    before = handoff_status(owner, ship)
    require(before['generation'] == generation and before['phase'] == ('open' if sealing else 'sealed'),
            'Home handoff phase or generation changed')
    following = int(generation) + int(sealing)
    require(following <= MAX_REVISION, 'Home handoff generation exhausted')
    try:
        require(owner.call(ship, 'handoff', '', {'operation': operation, 'generation': generation, 'proof': proof}) == {},
                'Unexpected native handoff acknowledgment')
        after = handoff_status(owner, ship)
        require(after['generation'] == str(following) and after['phase'] == ('sealed' if sealing else 'open'),
                'Unexpected native handoff result')
    except (OSError, ValueError):
        raise ValueError('Handoff result unconfirmed. Read handoff-status before proceeding.') from None
    return after


def read_handoff_ticket(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size in (64, 65),
                'Use a private owner-owned ticket file with mode 0600')
        value = source.read(66).removesuffix(b'\n')
    require(re.fullmatch(rb'[0-9a-f]{64}', value) is not None, 'Invalid private ticket bytes')
    return value.decode('ascii')


def retirement_status(owner, ship, project):
    require(match(UUID, project), 'Use a canonical project ID')
    value = owner.call(ship, 'project-retirement-status', project, None)
    fields = {'protocol', 'home', 'project_id', 'authority_epoch', 'journal_head', 'writer_state'}
    require(value.get('protocol') == 'stead.project-retirement-status/1' and value.get('home') == ship
            and value.get('project_id') == project and token(value.get('journal_head')),
            'Unexpected native retirement status')
    revision(value.get('authority_epoch'))
    if value.get('writer_state') == 'retired':
        fields |= {'migration_id', 'destination_home', 'retired_at_ms'}
        require(match(UUID, value.get('migration_id')) and match(SHIP, value.get('destination_home'))
                and value['destination_home'] != ship, 'Unexpected native retirement destination')
        revision(value.get('retired_at_ms'))
    else:
        require(value.get('writer_state') == 'active', 'Unexpected native writer state')
    require(value.keys() == fields, 'Unexpected native retirement fields')
    return value


def retired_scope(ship, intent):
    require(intent.keys() == {'protocol', 'project_id', 'migration_id', 'authority_epoch',
                              'destination_home', 'expected_journal_head'}
            and intent['protocol'] == 'stead.project-retire/1' and match(UUID, intent['migration_id'])
            and match(SHIP, intent['destination_home']) and intent['destination_home'] != ship
            and token(intent['expected_journal_head']), 'Use the exact reviewed project retirement intent')
    return {'writer_state': 'retired', 'authority_epoch': revision(intent['authority_epoch']),
            'journal_head': intent['expected_journal_head'], 'migration_id': intent['migration_id'],
            'destination_home': intent['destination_home']}


def retire_project(owner, ship, intent):
    expected = retired_scope(ship, intent)
    project = intent['project_id']
    before = retirement_status(owner, ship, project)
    require(all(before[key] == expected[key] for key in ('authority_epoch', 'journal_head')),
            'Project authority or journal head changed')
    if before['writer_state'] == 'retired':
        require(all(before[key] == value for key, value in expected.items()), 'Project already retired to a different intent')
        return before
    try:
        require(owner.call(ship, 'project-retire', '', intent) == {}, 'Unexpected retirement acknowledgment')
        after = retirement_status(owner, ship, project)
        require(all(after.get(key) == value for key, value in expected.items()), 'Unexpected native retirement result')
    except (OSError, ValueError):
        raise ValueError('Retirement result unconfirmed. Read project-retirement-status before proceeding.') from None
    return after


def capture_journal_pages(owner, ship, intent, before, stream):
    scope = {key: before[key] for key in ('home', 'project_id', 'migration_id', 'authority_epoch',
                                          'destination_home', 'journal_head')}
    fields = scope.keys() | {'protocol', 'journal_count', 'offset', 'done', 'data_base64'}
    digest = hashlib.sha256()
    offset = 0
    count = None
    while offset < project_migration.MAX_JOURNAL:
        value = owner.call(ship, 'project-journal-page', str(offset), intent)
        require(value.keys() == fields and value['protocol'] == 'stead.project-journal-page/1'
                and all(value[key] == expected for key, expected in scope.items())
                and value['offset'] == str(offset) and value['done'] in ('yes', 'no'),
                'Unexpected frozen project journal page')
        page_count = revision(value['journal_count'])
        require(int(page_count) <= project_migration.MAX_ROWS and count in (None, page_count),
                'Unexpected frozen project journal record count')
        count = page_count
        encoded = value['data_base64']
        require(isinstance(encoded, str) and len(encoded) <= ((JOURNAL_PAGE_BYTES + 2) // 3) * 4,
                'Frozen project journal page exceeds byte bound')
        chunk = base64.b64decode(encoded, validate=True)
        require(0 < len(chunk) <= JOURNAL_PAGE_BYTES and offset + len(chunk) <= project_migration.MAX_JOURNAL
                and base64.b64encode(chunk).decode('ascii') == encoded
                and (value['done'] == 'yes' or len(chunk) == JOURNAL_PAGE_BYTES),
                'Invalid frozen project journal page bytes')
        stream.write(chunk)
        digest.update(chunk)
        offset += len(chunk)
        if value['done'] == 'yes':
            return {'journal_head': before['journal_head'], 'journal_count': count, 'journal_sha256': digest.hexdigest()}
    raise ValueError('Frozen project journal exceeds byte bound')


def export_project_journal(owner, ship, intent, destination):
    expected = retired_scope(ship, intent)
    project = intent['project_id']
    before = retirement_status(owner, ship, project)
    require(all(before.get(key) == value for key, value in expected.items()),
            'Project must be retired under this exact migration intent')
    with directory_fd(destination.parent) as parent:
        opened_parent = private_directory(parent)
        private_parent = Path(f'/proc/self/fd/{parent}')
        require(not os.path.lexists(private_parent / destination.name), 'Journal output already exists')
        name = '.stead-project-journal-' + secrets.token_hex(16)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        opened = os.fstat(fd)
        try:
            with os.fdopen(fd, 'wb') as stream:
                os.fchmod(stream.fileno(), 0o600)
                evidence = capture_journal_pages(owner, ship, intent, before, stream)
                stream.flush()
                os.fsync(stream.fileno())
            last_time = project_migration.verify_journal(private_parent / name, before, evidence)
            require(last_time <= int(before['retired_at_ms']) and retirement_status(owner, ship, project) == before,
                    'Frozen project retirement observation changed')
            require(same_entry(parent, name, opened) and same_path(destination.parent, opened_parent),
                    'Journal output directory or temporary file changed')
            publish_directory(parent, name, destination.name)
            os.fsync(parent)
        finally:
            if same_entry(parent, name, opened):
                os.unlink(name, dir_fd=parent)
    return {'home': ship, 'project_id': project, 'migration_id': before['migration_id'], **evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--pier', type=Path, required=True)
    parser.add_argument('--ship', required=True)
    parser.add_argument('--desk', required=True)
    parser.add_argument('--role', choices=('home', 'identity'), required=True)
    parser.add_argument('--approved-runtime-sha256', required=True)
    commands = parser.add_subparsers(dest='operation', required=True)
    configure = commands.add_parser('configure')
    configure.add_argument('config', type=Path)
    cert = commands.add_parser('cert')
    cert.add_argument('--key', type=Path, required=True)
    cert.add_argument('--chain', type=Path, required=True)
    commands.add_parser('handoff-status')
    seal = commands.add_parser('handoff-seal')
    seal.add_argument('--generation', required=True)
    seal.add_argument('--challenge', required=True)
    activate = commands.add_parser('handoff-activate')
    activate.add_argument('--generation', required=True)
    activate.add_argument('--ticket-file', type=Path, required=True)
    retirement = commands.add_parser('project-retirement-status')
    retirement.add_argument('--project', required=True)
    retire = commands.add_parser('project-retire')
    retire.add_argument('--intent-file', type=Path, required=True)
    journal = commands.add_parser('project-journal-export')
    journal.add_argument('--intent-file', type=Path, required=True)
    journal.add_argument('--output', type=Path, required=True)
    pack = commands.add_parser('pack-stage')
    pack.add_argument('--attestation-file', type=Path, required=True)
    commands.add_parser('pack-relay-status')
    relay = commands.add_parser('pack-relay-policy')
    relay.add_argument('--policy-file', type=Path, required=True)
    for name in ('status', 'bootstrap'):
        command = commands.add_parser(name)
        command.add_argument('--revision', help='Reviewed Home configuration revision')
        if name == 'bootstrap':
            command.add_argument('--origin', required=True)
            command.add_argument('--listener-port', type=int, required=True)
            command.add_argument('--certificate-sha256', required=True)
            command.add_argument('--previous-incarnation')
    args = parser.parse_args()
    try:
        owner = OwnerProcess(args.pid, args.binary, args.pier, approved_runtime(args.approved_runtime_sha256),
                             desk=args.desk, role=args.role)
        if args.operation == 'configure':
            config = json.loads(read_source(args.config, 65536), object_pairs_hook=unique)
            require(isinstance(config, dict), 'Use a reviewed configuration object')
            if args.role == 'home':
                require(config.get('protocol') == 'stead.team-config/1' and config.get('home') == args.ship
                        and config.get('custody') == 'operator-pilot' and config.get('runtime') == 'live-synthetic',
                        'Use a reviewed configuration for this live Home')
            else:
                require(config.get('protocol') == 'stead.identity-config/1',
                        'Use a reviewed configuration for this Identity')
            require(owner.call(args.ship, 'configure', '', config) == {}, 'Unexpected native configuration result')
            value = {'ship': args.ship, 'status': 'configured'}
        elif args.operation == 'cert':
            owner.install_certificate(args.ship, args.key, args.chain)
            value = {'ship': args.ship, 'status': 'certificate-requested'}
        elif args.operation == 'status':
            require(args.role == 'home', 'Only the Home role exposes owner-local status')
            value = status(owner, args.ship, revision(args.revision))
        elif args.operation in ('pack-relay-status', 'pack-relay-policy'):
            require(args.role == 'home', 'Only the Home role supports pack relay control')
            value = (relay_status(owner, args.ship) if args.operation == 'pack-relay-status' else
                     relay_policy(owner, args.ship, json.loads(private_file(args.policy_file, 2_048), object_pairs_hook=unique)))
        elif args.operation.startswith('handoff-'):
            require(args.role == 'home', 'Only the Home role supports handoff')
            if args.operation == 'handoff-status':
                value = handoff_status(owner, args.ship)
            else:
                operation = args.operation.removeprefix('handoff-')
                proof = args.challenge if operation == 'seal' else read_handoff_ticket(args.ticket_file)
                value = change_handoff(owner, args.ship, operation, args.generation, proof)
        elif args.operation in ('project-retirement-status', 'project-retire', 'project-journal-export', 'pack-stage'):
            require(args.role == 'home', 'Only the Home role supports this operation')
            if args.operation == 'project-retirement-status':
                value = retirement_status(owner, args.ship, args.project)
            elif args.operation in ('project-retire', 'project-journal-export'):
                intent = json.loads(private_file(args.intent_file, 2_048), object_pairs_hook=unique)
                require(isinstance(intent, dict), 'Use a reviewed retirement intent object')
                value = (retire_project(owner, args.ship, intent) if args.operation == 'project-retire'
                         else export_project_journal(owner, args.ship, intent, args.output))
            else:
                attestation = json.loads(private_file(args.attestation_file, 65_536), object_pairs_hook=unique)
                require(isinstance(attestation, dict) and attestation.get('protocol') == 'stead.code-pack-attestation/1',
                        'Use a verified pack attestation')
                require(owner.call(args.ship, 'pack-stage', '', attestation) == {}, 'Unexpected pack staging acknowledgment')
                value = {'home': args.ship, 'status': 'staged'}
        else:
            require(args.previous_incarnation is None or token(args.previous_incarnation), 'Invalid prior incarnation')
            options = {'origin': args.origin, 'port': args.listener_port, 'certificate': args.certificate_sha256,
                       'previous': args.previous_incarnation}
            if args.role == 'home':
                value = bootstrap(owner, args.ship, revision(args.revision), **options)
            else:
                require(args.revision is None, 'Identity bootstrap does not take a Home revision')
                value = bootstrap_identity(owner, args.ship, **options)
        print(json.dumps(value, sort_keys=True, separators=(',', ':')))
    except (OSError, ValueError, GuardError) as error:
        parser.exit(1, f'Live pilot owner check failed: {error}\n')


if __name__ == '__main__':
    main()

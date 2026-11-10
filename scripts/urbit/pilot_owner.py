#!/usr/bin/env python3
"""Owner-local live pilot checks. Run behind the host traffic fence."""
from __future__ import annotations

import argparse
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
from digests import read_source, sha


ROOT = Path(__file__).resolve().parents[2]
SHIP = re.compile(r'~[a-z]+(?:-{1,2}[a-z]+)*\Z')
DESK = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')
TOKEN = re.compile(r'[0-9a-f]{64}\Z')
MAX_REVISION = 2**64 - 1


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
        path = '[%bootstrap ' if mode == 'bootstrap' else '[%operator '
        path = path + core_conn.atom(route.encode()) + ' ~]' if route else '~'
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode() if value is not None else b''
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
        else:
            require(args.previous_incarnation is None or token(args.previous_incarnation), 'Invalid prior incarnation')
            options = {'origin': args.origin, 'port': args.listener_port, 'certificate': args.certificate_sha256,
                       'previous': args.previous_incarnation}
            if args.role == 'home':
                value = bootstrap(owner, args.ship, revision(args.revision), **options)
            else:
                require(args.revision is None, 'Identity bootstrap does not take a Home revision')
                value = bootstrap_identity(owner, args.ship, **options)
        print(json.dumps(value, sort_keys=True))
    except (OSError, ValueError) as error:
        parser.exit(1, f'Live pilot owner check failed: {error}\n')


if __name__ == '__main__':
    main()

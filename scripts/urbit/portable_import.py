"""Loss-aware create-only import through a disposable Home's member authority."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import http.client
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import sys

import portable_recovery as portable

MAX_STEPS = 256
MAX_PLAN = 256 * 1024
MAX_PROGRESS = 128 * 1024
MAX_BATCH = 16
MAX_SESSIONS = 16
TARGET_FIELDS = ('home', 'identity_ship', 'principal_id', 'binding_id', 'binding_revision',
                 'organization_id', 'team_id')
STEP_PHASES = {'ready', 'awaiting-receipt', 'complete'}
ATTEMPTS = {'pending', 'rejected', 'unconfirmed'}
RECEIPT_FIELDS = {
    'protocol', 'status', 'request_id', 'canonical_sha256', 'project_id', 'resource_id',
    'resource_kind', 'container_id', 'resource_revision', 'authority_epoch', 'operation',
    'principal_id', 'binding_id', 'binding_revision', 'identity_ship', 'authentication',
    'authentication_strength', 'session_audit_id', 'runtime', 'accepted_at_ms', 'git_commit_oid',
}
IMPORT_LOSSES = [
    'Fresh project, resource and request IDs, revisions, receipts and Git commits.',
    'Original page header IDs are rewritten. Markdown body bytes and embedded links are preserved.',
    'Private collections belong to the importing member. Shared collections are shared only with target project grants.',
    'No source identities, grants, ownership, history or historical attribution are restored.',
]


class LoopbackHTTPS(http.client.HTTPSConnection):
    """The fixed local route uses numeric TCP and the configured TLS hostname."""
    def __init__(self, host, port, context, timeout):
        super().__init__(host, port, context=context, timeout=timeout)
        self.tls_context = context

    def connect(self):
        raw = socket.create_connection(('127.0.0.1', self.port), self.timeout)
        try:
            self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class LocalHome(portable.HTTPSQueries):
    def __init__(self, credentials, *, ca_file=None):
        super().__init__(credentials, ca_file=ca_file)
        portable.require(self.parts.hostname == 'home.localhost', 'disposable-home-required')
        self.read = portable.Reads(self)

    def _connection(self, timeout):
        return LoopbackHTTPS(self.parts.hostname, self.parts.port, self.context, timeout)

    def member(self):
        _, member = self.read.one('identity')
        portable.identity(member, self.credentials['principal_id'])
        _, capabilities = self.read.one('capabilities')
        portable.require(capabilities.get('runtime') == 'isolated-fake'
                         and capabilities.get('commands') == 'stead.command/3', 'disposable-home-required')
        return member

    def send(self, command):
        return portable.decoded(self._post('/stead/api/command', command))


def target_member(member):
    portable.identity(member, member.get('principal_id'))
    portable.require(member['can_create'] == 'yes', 'project-creator-required')
    return {name: member[name] for name in TARGET_FIELDS}


def child_id(seed, *parts):
    # A reviewed plan has one random v7 namespace. Rebuilding its commands
    # after an interruption produces the same IDs without another random draw.
    raw = bytearray(hashlib.sha256(b'stead.import-id/1\0' + portable.encoded([seed, *parts])).digest()[:16])
    raw[:6] = bytes.fromhex(seed[:8] + seed[9:13])
    raw[6] = (raw[6] & 15) | 112
    raw[8] = (raw[8] & 63) | 128
    value = raw.hex()
    return f'{value[:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:]}'


def command_digest(command):
    return portable.sha(b'stead.command/3\0' + portable.encoded(command)[:-1])


def import_title(value):
    portable.text(value, 800)
    portable.require(1 <= len(value) <= 200 and all(ord(char) >= 32 for char in value), 'import-title')


def plan_commands(files, artifact_digest, origin, target, seed, title, key):
    portable.require(portable.origin(origin).hostname == 'home.localhost', 'disposable-home-required')
    portable.require(portable.match(portable.TOKEN, artifact_digest), 'import-archive-digest')
    portable.require(portable.match(portable.UUID, seed), 'import-seed')
    portable.shape(target, set(TARGET_FIELDS))
    portable.identity(target | {'display_name': '', 'can_create': 'yes',
                                'session_audit_id': '0' * 64}, target['principal_id'])
    import_title(title)
    portable.require(isinstance(key, str) and re.fullmatch(r'[A-Z][A-Z0-9]{1,9}', key), 'import-project-key')
    data = portable.decoded(files['records.json'], portable.MAX_CAPTURE)
    source = data['project']['project_id']
    project = child_id(seed, 'project')
    commands = []
    steps = []

    def add(operation, original, target_id, payload):
        command = {'protocol': 'stead.command/3', 'request_id': child_id(seed, 'request', operation, *original),
                   'project_id': project, 'resource_id': target_id, 'expected_revision': '0',
                   'authority_epoch': '1', 'operation': operation, 'payload': payload}
        portable.require(len(portable.encoded(command)) <= 65536, 'import-command-size')
        commands.append(command)
        steps.append({'operation': operation, 'source_scope': list(original), 'resource_id': target_id,
                      'request_id': command['request_id'], 'canonical_sha256': command_digest(command)})

    portable.require(1 + sum(len(data[name]) for name in ('work', 'containers', 'documents', 'relations'))
                     <= MAX_STEPS, 'import-step-limit')
    add('project.create', (source,), project, {'organization_id': target['organization_id'],
        'owning_team_id': target['team_id'], 'title': title, 'project_key': key, 'preset': 'general'})
    for row in sorted(data['work'], key=lambda item: item['resource_id']):
        original = row['resource_id']
        import_title(row['title'])
        portable.require('\r' not in row['description'], 'import-work-description')
        add('work.create', (original,), child_id(seed, 'work', original),
            {name: row[name] for name in ('title', 'description', 'type', 'status', 'priority')})
    for row in sorted(data['containers'], key=lambda item: item['resource_id']):
        original = row['resource_id']
        import_title(row['title'])
        add('container.create', (original,), child_id(seed, 'container', original),
            {name: row[name] for name in ('title', 'visibility')})
    for row in sorted(data['documents'], key=lambda item: (item['container_id'], item['resource_id'])):
        container, original = row['container_id'], row['resource_id']
        resource = child_id(seed, 'document', container, original)
        markdown = files[row['markdown_file']].decode('utf-8').replace(f'\nid: {original}\n', f'\nid: {resource}\n', 1)
        add('document.save', (container, original), resource,
            {'container_id': child_id(seed, 'container', container), 'markdown': markdown})
    for row in sorted(data['relations'], key=lambda item: item['resource_id']):
        payload = {'type': row['type']}
        for side in ('source', 'target'):
            kind, container, resource = (row[f'{side}_{name}'] for name in ('kind', 'container_id', 'id'))
            payload.update({f'{side}_project_id': project, f'{side}_kind': kind,
                f'{side}_container_id': child_id(seed, 'container', container) if container else '',
                f'{side}_id': child_id(seed, kind, container, resource) if container else child_id(seed, kind, resource)})
        original = row['resource_id']
        add('relation.create', (original,), child_id(seed, 'relation', original), payload)
    all_ids = [command[name] for command in commands for name in ('request_id', 'resource_id')]
    portable.require(len(set(all_ids)) == len(all_ids), 'import-id-collision')
    plan = {'protocol': 'stead.portable-import-plan/1', 'artifact_sha256': artifact_digest,
            'origin': origin, 'target': target, 'seed': seed, 'title': title, 'project_key': key,
            'project_id': project, 'steps': steps,
            'losses': {'source_omissions': portable.LOSSES['omitted'], 'import_changes': IMPORT_LOSSES}}
    return plan, commands


def published_plan(plan, output):
    raw = portable.encoded(plan)
    portable.require(len(raw) <= MAX_PLAN, 'import-plan-size')
    output = Path(output)
    parent = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(parent)
        portable.require(info.st_uid == os.getuid() and not info.st_mode & 0o077, 'import-plan-private-directory')
        fd = os.open(output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            os.fsync(parent)
            portable.require(portable.same_entry(parent, output.name, os.fstat(stream.fileno()))
                             and portable.same_path(output.parent, info), 'import-plan-moved')
    finally:
        os.close(parent)
    return portable.sha(raw)


def load_plan(archive, path, digest):
    portable.require(portable.match(portable.TOKEN, digest), 'import-plan-digest')
    raw = portable.private_file(path, MAX_PLAN)
    portable.require(portable.sha(raw) == digest, 'import-plan-digest')
    plan = portable.decoded(raw, MAX_PLAN)
    portable.shape(plan, {'protocol', 'artifact_sha256', 'origin', 'target', 'seed',
                          'title', 'project_key', 'project_id', 'steps', 'losses'})
    portable.require(portable.match(portable.TOKEN, plan['artifact_sha256']), 'import-archive-digest')
    files, _ = portable.verify(archive, expected_sha256=plan['artifact_sha256'])
    expected, commands = plan_commands(files, plan['artifact_sha256'], plan['origin'], plan['target'],
                                       plan['seed'], plan['title'], plan['project_key'])
    portable.require(raw == portable.encoded(expected), 'import-plan-reconstruction')
    return plan, commands


def checked_receipt(value, command, target, sessions):
    portable.shape(value, RECEIPT_FIELDS)
    operation = command['operation']
    kind = operation.split('.')[0]
    container = command['resource_id'] if kind == 'container' else command['payload'].get('container_id', '')
    expected = {'protocol': 'stead.receipt/3', 'status': 'accepted', 'request_id': command['request_id'],
                'canonical_sha256': command_digest(command), 'project_id': command['project_id'],
                'resource_id': command['resource_id'], 'operation': operation, 'resource_kind': kind,
                'container_id': container, 'resource_revision': '1', 'authority_epoch': '1',
                'principal_id': target['principal_id'], 'binding_id': target['binding_id'],
                'binding_revision': target['binding_revision'], 'identity_ship': target['identity_ship'],
                'authentication': 'native-approved-browser/1', 'authentication_strength': 'native-approved-browser',
                'runtime': 'isolated-fake'}
    portable.require(all(value[key] == item for key, item in expected.items())
                     and portable.match(portable.TOKEN, value['session_audit_id'])
                     and portable.sha(value['session_audit_id'].encode()) in sessions, 'import-receipt-correlation')
    portable.number(value['accepted_at_ms'])
    oid = value['git_commit_oid']
    portable.require(portable.match(portable.OID, oid) if kind == 'document' else oid == '', 'import-receipt-git')
    return {'request_id': command['request_id'], 'canonical_sha256': expected['canonical_sha256'],
            'receipt_sha256': portable.sha(portable.encoded(value)), 'git_commit_oid': oid}


def check_progress(value, digest, commands):
    portable.shape(value, {'protocol', 'plan_sha256', 'phase', 'accepted', 'pending'})
    portable.require(value['protocol'] == 'stead.portable-import-progress/1' and value['plan_sha256'] == digest
                     and value['phase'] in STEP_PHASES and isinstance(value['accepted'], list)
                     and len(value['accepted']) <= len(commands), 'import-progress-scope')
    for item, command in zip(value['accepted'], commands):
        portable.shape(item, {'request_id', 'canonical_sha256', 'receipt_sha256', 'git_commit_oid'})
        portable.require(item['request_id'] == command['request_id']
                         and item['canonical_sha256'] == command_digest(command)
                         and portable.match(portable.TOKEN, item['receipt_sha256'])
                         and (portable.match(portable.OID, item['git_commit_oid']) if command['operation'] == 'document.save'
                              else item['git_commit_oid'] == ''), 'import-progress-prefix')
    pending = value['pending']
    if value['phase'] == 'complete':
        portable.require(len(value['accepted']) == len(commands) and pending is None, 'import-progress-completion')
    elif value['phase'] == 'ready':
        portable.require(len(value['accepted']) < len(commands) and pending is None, 'import-progress-ready')
    else:
        portable.require(len(value['accepted']) < len(commands), 'import-progress-pending')
        portable.shape(pending, {'request_id', 'sessions', 'last_attempt'})
        sessions = pending['sessions']
        portable.require(pending['request_id'] == commands[len(value['accepted'])]['request_id']
                         and pending['last_attempt'] in ATTEMPTS and isinstance(sessions, list)
                         and 1 <= len(sessions) <= MAX_SESSIONS
                         and all(portable.match(portable.TOKEN, item) for item in sessions)
                         and len(set(sessions)) == len(sessions), 'import-progress-pending')


class Progress:
    """Keep the original pending command through process death and lost replies."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.opened = None

    def __enter__(self):
        self.fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self.info = os.fstat(self.fd)
            portable.require(self.info.st_uid == os.getuid() and not self.info.st_mode & 0o077,
                             'import-progress-private-directory')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.fd)
            raise
        return self

    def __exit__(self, *_):
        os.close(self.fd)

    def bound(self):
        portable.require(portable.same_path(self.directory, self.info), 'import-progress-moved')
        if self.opened is None:
            try:
                os.stat('progress.json', dir_fd=self.fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            raise portable.RecoveryError('import-progress-replaced')
        else:
            portable.require(portable.same_entry(self.fd, 'progress.json', self.opened), 'import-progress-replaced')

    def load(self, digest, commands):
        try:
            fd = os.open('progress.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        except FileNotFoundError:
            value = {'protocol': 'stead.portable-import-progress/1', 'plan_sha256': digest,
                     'phase': 'ready', 'accepted': [], 'pending': None}
        else:
            with os.fdopen(fd, 'rb') as stream:
                self.opened = os.fstat(stream.fileno())
                portable.require(stat.S_ISREG(self.opened.st_mode) and self.opened.st_nlink == 1
                                 and self.opened.st_uid == os.getuid() and not self.opened.st_mode & 0o077
                                 and 0 < self.opened.st_size <= MAX_PROGRESS, 'import-progress-file')
                value = portable.decoded(stream.read(MAX_PROGRESS + 1), MAX_PROGRESS)
        self.bound()
        check_progress(value, digest, commands)
        return value

    def save(self, value):
        raw = portable.encoded(value)
        portable.require(len(raw) <= MAX_PROGRESS, 'import-progress-size')
        self.bound()
        name = '.stead-import-' + secrets.token_hex(16)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        with os.fdopen(fd, 'wb') as stream:
            opened = os.fstat(stream.fileno())
            try:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                self.bound()
                portable.require(portable.same_entry(self.fd, name, opened), 'import-progress-replaced')
                os.replace(name, 'progress.json', src_dir_fd=self.fd, dst_dir_fd=self.fd)
                self.opened = opened
                os.fsync(self.fd)
                self.bound()
            finally:
                if portable.same_entry(self.fd, name, opened):
                    os.unlink(name, dir_fd=self.fd)


def check_project(home, plan):
    stamp, row = home.read.one('project', plan['project_id'])
    portable.require(stamp[0] == '1' and all(row.get(key) == value for key, value in {
        'kind': 'project', 'project_id': plan['project_id'], 'resource_id': plan['project_id'], 'role': 'maintainer',
        'policy_revision': '1', 'authority_epoch': '1', 'preset': 'general',
        'project_key': plan['project_key'], 'title': plan['title'],
    }.items()), 'import-target-changed')


def check_target(home, plan):
    portable.require(home.credentials['origin'] == plan['origin'], 'import-target-origin')
    who = home.member()
    portable.require(target_member(who) == plan['target'], 'import-target-member')
    return portable.sha(who['session_audit_id'].encode())


def apply_import(home, plan, digest, commands, progress, limit):
    portable.require(type(limit) is int and 1 <= limit <= MAX_BATCH, 'import-batch-limit')
    state = progress.load(digest, commands)
    session = check_target(home, plan)
    for _ in range(limit):
        if state['phase'] == 'complete':
            break
        index = len(state['accepted'])
        if index:
            check_project(home, plan)
        command = commands[index]
        pending = state['pending']
        sessions = [] if pending is None else list(pending['sessions'])
        if session not in sessions:
            portable.require(len(sessions) < MAX_SESSIONS, 'import-session-limit')
            sessions.append(session)
        pending = {'request_id': command['request_id'], 'sessions': sessions, 'last_attempt': 'pending'}
        state.update(phase='awaiting-receipt', pending=pending)
        progress.save(state)  # No transmission until the original intent is durable.
        try:
            result = home.send(command)
            if (isinstance(result, dict) and result.get('protocol') == 'stead.result/3'
                    and result.get('status') == 'rejected' and result.get('request_id') == command['request_id']
                    and result.get('canonical_sha256') == command_digest(command)
                    and isinstance(result.get('error'), str) and re.fullmatch(r'[a-z_]{1,64}', result['error'])):
                pending['last_attempt'] = 'rejected'
                progress.save(state)
                break
            receipt = checked_receipt(result, command, plan['target'], sessions)
        except portable.RecoveryError:
            pending['last_attempt'] = 'unconfirmed'
            progress.save(state)
            break
        state['accepted'].append(receipt)
        state.update(phase='complete' if len(state['accepted']) == len(commands) else 'ready', pending=None)
        progress.save(state)
    return {'phase': state['phase'], 'project_id': plan['project_id'], 'accepted': len(state['accepted']),
            'total': len(commands), 'last_attempt': state['pending']['last_attempt'] if state['pending'] else None}


def verify_import(home, plan, digest, commands, progress):
    state = progress.load(digest, commands)
    portable.require(state['phase'] == 'complete', 'import-not-complete')
    check_target(home, plan)
    check_project(home, plan)
    data, _ = portable.capture(home, plan['project_id'], plan['target']['principal_id'], plan['origin'])
    maps = {}
    for operation, name in (('work.create', 'work'), ('container.create', 'containers'),
                            ('document.save', 'documents'), ('relation.create', 'relations')):
        maps[operation] = {row['resource_id']: row for row in data[name]}
        portable.require(len(maps[operation]) == len(data[name]), 'import-unexpected-records')
    for command in commands[1:]:
        rows = maps[command['operation']]
        row = rows.pop(command['resource_id'], {})
        portable.require(row.get('resource_revision') == '1'
                         and all(row.get(key) == value for key, value in command['payload'].items()),
                         'import-readback-mismatch')
    portable.require(not any(maps.values()), 'import-unexpected-records')
    check_project(home, plan)
    return {'phase': 'verified', 'project_id': plan['project_id'], 'accepted': len(state['accepted']),
            'work': len(data['work']), 'collections': len(data['containers']),
            'documents': len(data['documents']), 'relations': len(data['relations'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest='operation', required=True)
    prepare = operations.add_parser('plan', help='Read target identity and generate a create-only plan')
    apply = operations.add_parser('apply', help='Explicitly apply or retry one bounded batch')
    verify = operations.add_parser('verify', help='Check authorized native readback against a completed plan')
    for sub in (prepare, apply, verify):
        sub.add_argument('--archive', required=True)
        sub.add_argument('--session-file', required=True)
        sub.add_argument('--ca-file')
    prepare.add_argument('--archive-sha256', required=True)
    prepare.add_argument('--target-home', required=True)
    prepare.add_argument('--project-key', required=True)
    prepare.add_argument('--title', required=True)
    prepare.add_argument('--output', required=True)
    for sub in (apply, verify):
        sub.add_argument('--plan', required=True)
        sub.add_argument('--plan-sha256', required=True)
        sub.add_argument('--confirm-project', required=True)
        sub.add_argument('--progress', required=True, help='Dedicated existing directory with mode 0700')
    apply.add_argument('--limit', type=int, default=MAX_BATCH)
    args = parser.parse_args(argv)
    try:
        credentials = portable.session_file(args.session_file)
        home = LocalHome(credentials, ca_file=args.ca_file)
        if args.operation == 'plan':
            files, facts = portable.verify(args.archive, expected_sha256=args.archive_sha256)
            target = target_member(home.member())
            portable.require(target['home'] == args.target_home, 'import-target-home')
            plan, commands = plan_commands(files, facts['sha256'], credentials['origin'], target,
                                          portable.new_id(), args.title, args.project_key)
            _, visible = home.read.walk('projects', '', bound=16)
            portable.require(not any(row.get('project_key') == args.project_key for row in visible), 'import-target-key-in-use')
            digest = published_plan(plan, args.output)
            result = {'phase': 'planned', 'project_id': plan['project_id'], 'plan_sha256': digest, 'commands': len(commands)}
        else:
            plan, commands = load_plan(args.archive, args.plan, args.plan_sha256)
            portable.require(plan['project_id'] == args.confirm_project, 'import-project-confirmation')
            with Progress(args.progress) as progress:
                if args.operation == 'apply':
                    result = apply_import(home, plan, args.plan_sha256, commands, progress, args.limit)
                else:
                    result = verify_import(home, plan, args.plan_sha256, commands, progress)
        sys.stdout.buffer.write(portable.encoded(result))
        return 2 if result['phase'] == 'awaiting-receipt' else 0
    except (portable.RecoveryError, OSError, KeyError, TypeError, ValueError, OverflowError):
        # Retain durable progress and never print credential-bearing failures.
        print('Portable import stopped. Preserve the private plan and progress before retrying.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

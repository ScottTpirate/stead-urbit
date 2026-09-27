"""Deterministic capacity recipes and a transport-injected native qualification lane.

Recipes describe expected transitions; they never fabricate home state/counters.
No callback means not_run. Host recipe tests are not native qualification.
The caller owns isolated fixture lifecycle, guarded execution and real transport.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import time


CODE = Path(__file__).resolve().parent
ROOT = CODE.parent.parent
SPECS = Path('/specs') if CODE == Path('/code') else ROOT / 'specs/urbit'
NATIVE = Path('/native/core/desk') if CODE == Path('/code') else ROOT / 'native/core/desk'
FIXTURE_SHA256 = 'e693116efbc00b1131714f9eb7077ec678669d4fdb27ddfdce284461e0dffe74'
PREDECESSOR_COMMIT = '77428f6c35eb0fe7b7e497b64c5a1eab92e943cd'
PREDECESSOR_FILES = {
    'stead-core-v1.hoon': '879615a5547d06a09d382c2bac4c5cb20cdf03236ddfdab79c9f1da15bd33cb5',
    'stead-codec-v1.hoon': 'ce4c7a69b03ee1761590c37e71ff49b9f63a1a2edd2aaa6dfbf75bc3c960584a'}
FREEZES = {'contract-freeze.json': '61d9a18f16b8b01629bd35177d5b801cc05cd8ddaf7f68c3cc1678faf642cf90',
           'v2/contract-freeze.json': 'a2336e5060c71c7c16849b3151cc024a598d6cdf867561452eff1338e3232670'}
V1_CORPUS_SHA256 = '88d554aebc48e071f63db981263cacdfb144c16aa870046248134ba667362e4c'
PROJECT = '019939ba-4000-7000-8000-000000000001'
CONTAINERS = {'bus': '019939ba-4000-7000-8000-000000000004',
              'zod': '019939ba-4000-7000-8000-000000000007'}
PRINCIPALS = {ship: f'019939ba-4000-7000-8000-{number:012x}'
              for ship, number in (('zod', 0x101), ('bus', 0x102), ('nec', 0x103), ('bud', 0x104))}
BINDINGS = {ship: f'019939ba-4000-7000-8000-{number:012x}'
            for ship, number in (('zod', 0x201), ('bus', 0x202), ('nec', 0x203), ('bud', 0x204))}
COUNTS = ('projects', 'work_items', 'documents', 'grants', 'objects', 'object_bytes', 'journal_events', 'receipts')
PRESERVED_HASHES = ('journal_sha256', 'receipts_sha256', 'objects_sha256',
                    'bindings_sha256', 'containers_sha256', 'reachable_sha256')
HEX256 = re.compile(r'[0-9a-f]{64}')
LIMITS = {'projects': 16, 'work_items': 128, 'grants': 128, 'documents': 32,
          'history': 128, 'object_bytes': 8388608, 'ordinary': 4096, 'security_per_project': 128}
RECEIPT_FIELDS = frozenset(('protocol', 'status', 'request_id', 'canonical_sha256', 'project_id',
    'resource_id', 'resource_kind', 'container_id', 'resource_revision', 'authority_epoch',
    'principal_id', 'binding_id', 'authentication', 'authentication_strength', 'accepted_at_ms', 'git_commit_oid'))
RESOURCE_KINDS = {'project.create': 'project', 'work.create': 'work', 'work.update': 'work',
                 'document.save': 'document', 'policy.grant': 'policy', 'policy.revoke': 'policy'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def decoded(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON response key: ' + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('Non-JSON response constant: ' + value)

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)


def uuid(kind, number):
    base = {'request': 0x100000000000, 'project': 0x200000000000,
            'grant': 0x300000000000, 'work': 0x400000000000, 'document': 0x500000000000}[kind]
    if type(number) is not int or not 0 <= number < 0x100000000000:
        raise ValueError('Synthetic identifier range')
    return f'019939ba-4000-7000-8000-{base + number:012x}'


@dataclass(frozen=True)
class Entry:
    sender: str
    command: dict

    @property
    def raw(self):
        raw = encoded(self.command)
        if not 0 < len(raw) <= 65536:
            raise ValueError('Command byte bound')
        return raw

    @property
    def digest(self):
        return sha(self.command['protocol'].encode() + b'\0' + self.raw)


class Commands:
    def __init__(self, version, bank):
        if version not in (1, 2) or not 0 <= bank < 100:
            raise ValueError('Unsupported recipe version/bank')
        self.version, self.next_id = version, bank * 100000

    def make(self, operation, project, resource, revision, payload, sender='zod'):
        self.next_id += 1
        return Entry(sender, {'protocol': f'stead.command/{self.version}',
            'request_id': uuid('request', self.next_id), 'project_id': project, 'resource_id': resource,
            'expected_revision': str(revision), 'authority_epoch': '1', 'operation': operation, 'payload': payload})

    def project(self, project, title='Synthetic capacity project'):
        return self.make('project.create', project, project, 0, {
            'organization_id': '019939ba-4000-7000-8000-000000000005',
            'owning_team_id': '019939ba-4000-7000-8000-000000000006',
            'title': title, 'project_key': 'CAP', 'preset': 'general'})

    def grant(self, project, grant, revision, ship='bus', role='contributor'):
        return self.make('policy.grant', project, project, revision, {
            'grant_id': grant, 'principal_id': PRINCIPALS[ship], 'role': role, 'expires_at_ms': '4102444800000'})

    def work(self, project, work, revision=0, sender='zod'):
        return self.make('work.create' if revision == 0 else 'work.update', project, work, revision,
            {'title': 'Synthetic work', 'description': f'Accepted revision {revision + 1}.',
             'type': 'task', 'status': 'todo', 'priority': 'medium'}, sender)

    def document(self, document, revision=0, sender='zod', byte_length=None):
        markdown = f'---\nid: {document}\ntype: page\nstate: draft\n---\nSynthetic revision {revision + 1}.\n'
        if byte_length is not None:
            padding = byte_length - len(markdown.encode())
            if not 0 <= padding or byte_length > 32768:
                raise ValueError('Synthetic Markdown byte bound')
            markdown += 'x' * padding
        return self.make('document.save', PROJECT, document, revision,
            {'container_id': CONTAINERS[sender], 'markdown': markdown}, sender)

    def revoke(self, project, grant, revision):
        return self.make('policy.revoke', project, project, revision, {'grant_id': grant})


def batch_value(entries):
    if not entries or len(entries) > 32 or len({entry.sender for entry in entries}) != 1:
        raise ValueError('Batch count/sender bound')
    raw = encoded({str(index): entry.raw.decode('utf-8') for index, entry in enumerate(entries)})
    if len(raw) > 65536:
        raise ValueError('Batch UTF-8 byte bound')
    return raw


def batches(entries):
    group = []
    for entry in entries:
        try:
            batch_value(group + [entry])
        except ValueError:
            if not group:
                raise
            yield group
            group = []
            batch_value([entry])
        group.append(entry)
    if group:
        yield group


def recipe_digest(entries):
    return sha(b'stead.qualification.recipe/1\0' + encoded([
        {'sender': entry.sender, 'raw_utf8': entry.raw.decode()} for entry in entries]))


def exhaustion_recipe():
    old, new = Commands(1, 1), Commands(2, 2)
    projects = (PROJECT, uuid('project', 2))
    setup, grants, creators, works = [], {}, {}, {}
    for project_number, project in enumerate(projects):
        creator = old.project(project)
        setup.append(creator)
        creators[project] = creator
        explicit = []
        for index in range(127):
            gid = uuid('grant', project_number * 1000 + index)
            setup.append(old.grant(project, gid, index + 1))
            explicit.append(gid)
        # Revoke the creator last, while every earlier check still has an
        # explicit tested content grant. Organization scope does not grant it.
        grants[project] = explicit + [creator.command['request_id']]
    for index, project in enumerate(projects):
        works[project] = uuid('work', index)
        setup.append(old.work(project, works[project]))
    document = old.document(uuid('document', 0))
    setup.append(document)
    fill = [old.work(PROJECT, works[PROJECT], revision)
            for revision in range(1, 4096 - len(setup) + 1)]
    ordinary = setup + fill
    assert len(ordinary) == 4096
    failed_old_revokes = [old.revoke(project, grants[project][0], 128) for project in projects]
    revokes = {project: [new.revoke(project, gid, 128 + index) for index, gid in enumerate(grants[project])]
               for project in projects}
    overflow = new.work(PROJECT, works[PROJECT], len(fill) + 1)
    closed_probes = {project: new.work(project, works[project], len(fill) + 1 if project == PROJECT else 1,
                                      sender='bus') for project in projects}
    unaccepted_legacy = old.work(PROJECT, works[PROJECT], len(fill) + 1)
    return {'name': 'v1-exhaustion-migration-security-reserve', 'projects': projects,
            'setup': setup, 'fill': fill, 'ordinary': ordinary, 'grants': grants,
            'creators': creators, 'works': works, 'document': document,
            'old_revokes': failed_old_revokes, 'revokes': revokes, 'overflow': overflow,
            'closed_probes': closed_probes, 'unaccepted_legacy': unaccepted_legacy}


def predecessor_privacy_recipe():
    factory = Commands(1, 3)
    other = uuid('project', 3000)
    hidden, visible = uuid('work', 3000), uuid('work', 3001)
    private_document = uuid('document', 3000)
    setup = [factory.project(PROJECT), factory.grant(PROJECT, uuid('grant', 3000), 1),
             factory.project(other), factory.work(other, hidden), factory.work(PROJECT, visible, sender='bus')]
    before = factory.work(PROJECT, visible, 1, sender='bus')
    private = factory.document(private_document)
    after = factory.work(PROJECT, visible, 2, sender='bus')
    same_container_denial = factory.document(private_document, sender='bus')
    other_project_collision = factory.document(hidden, sender='bus')
    fresh = factory.document(uuid('document', 3001), sender='bus')
    return {'name': 'v1-private-identity-and-sequence-reproduction', 'setup': setup,
        'visible_before': before, 'private_save': private, 'visible_after': after,
        'same_project_denial': same_container_denial, 'cross_project_denial': other_project_collision,
        'fresh_control': fresh, 'private_reads': [
            {'kind': 'document', 'project': PROJECT, 'resource': private_document},
            {'kind': 'project', 'project': other, 'resource': other},
            {'kind': 'work', 'project': other, 'resource': hidden}]}


def resource_recipes():
    """Every starting state is built with real version-2 commands after empty migration."""
    results = []
    for bank, name in enumerate(('projects', 'work_items', 'grants', 'documents', 'history'), start=10):
        factory = Commands(2, bank)
        setup = [] if name == 'projects' else [factory.project(PROJECT)]
        accepted = []
        if name == 'projects':
            accepted = [factory.project(uuid('project', 100 + index)) for index in range(16)]
            rejected = factory.project(uuid('project', 116))
        elif name == 'work_items':
            accepted = [factory.work(PROJECT, uuid('work', 100 + index)) for index in range(128)]
            rejected = factory.work(PROJECT, uuid('work', 228))
        elif name == 'grants':
            accepted = [factory.grant(PROJECT, uuid('grant', 10000 + index), index + 1) for index in range(127)]
            rejected = factory.grant(PROJECT, uuid('grant', 10127), 128)
        elif name == 'documents':
            accepted = [factory.document(uuid('document', 100 + index)) for index in range(32)]
            rejected = factory.document(uuid('document', 132))
        else:
            accepted = [factory.document(uuid('document', 500), index) for index in range(128)]
            rejected = factory.document(uuid('document', 500), 128)
        results.append({'name': name, 'setup': setup, 'accepted': accepted, 'rejected': rejected})
    factory = Commands(2, 20)
    setup = [factory.project(PROJECT), factory.grant(PROJECT, uuid('grant', 20000), 1)]
    # At most127 saves/container: history128 cannot cause this lane's refusal.
    # Distinct maximum-size Markdown creates exact, unshared blob bytes.
    candidates = [factory.document(uuid('document', 1000 + index % 2), index // 2,
                    sender=('zod', 'bus')[index % 2], byte_length=32768) for index in range(254)]
    results.append({'name': 'object_bytes', 'setup': setup, 'candidates': candidates})
    return results


def recipe_inventory():
    """Planned immutable bytes/counts, never observations of an accepted home."""
    recipe = exhaustion_recipe()
    result = {recipe['name']: {'status': 'unexecuted',
        'ordinary_sha256': recipe_digest(recipe['ordinary']), 'ordinary_commands': len(recipe['ordinary']),
        'old_refusals_sha256': recipe_digest(recipe['old_revokes']),
        'revocations_sha256': {project: recipe_digest(entries) for project, entries in recipe['revokes'].items()},
        'ordinary_overflow_sha256': recipe_digest([recipe['overflow']]),
        'unaccepted_legacy_sha256': recipe_digest([recipe['unaccepted_legacy']]),
        'closed_project_mutations_sha256': recipe_digest(list(recipe['closed_probes'].values())),
        'unauthorized_boundary_probe': 'Exact overflow command via bud transport before authorized refusal',
        'missing_binding_probe': 'Exact overflow command via bus after owner binding-drop, then restore exact binding state',
        'malformed_predecessor_keys': ['', 'policy', 'grant', 'reachable', 'initialized']}}
    privacy = predecessor_privacy_recipe()
    entries = privacy['setup'] + [privacy[key] for key in ('visible_before', 'private_save', 'visible_after',
        'same_project_denial', 'cross_project_denial', 'fresh_control')]
    result[privacy['name']] = {'status': 'unexecuted', 'sha256': recipe_digest(entries),
        'commands': len(entries), 'private_read_requests': privacy['private_reads']}
    for recipe in resource_recipes():
        entries = recipe['setup'] + recipe.get('accepted', recipe.get('candidates', []))
        if 'rejected' in recipe:
            entries += [recipe['rejected']]
        result[recipe['name']] = {'status': 'unexecuted', 'sha256': recipe_digest(entries),
                                  'commands': len(entries),
                                  'unauthorized_boundary_probe': 'Exact failing command via bud transport before authorized refusal'}
    return result


def source_binding(fixture_raw):
    if sha(fixture_raw) != FIXTURE_SHA256:
        raise ValueError('Exact frozen fixture bytes required')
    result = {'fixture_sha256': sha(fixture_raw), 'driver_sha256': sha(Path(__file__).read_bytes()),
              'predecessor_commit': PREDECESSOR_COMMIT,
              'predecessor_import_adjustment': 'stead-core imports stead-codec-v1; all other predecessor bytes unchanged',
              'freeze_verification_scope': 'Both exact manifests and their runtime-mounted code/spec inputs; full docs/tests additionally verified on host'}
    for name, expected in PREDECESSOR_FILES.items():
        value = sha((NATIVE / 'lib' / name).read_bytes())
        if value != expected:
            raise ValueError('Provenance-bound predecessor source changed: ' + name)
        result[name] = value
    for name, expected in FREEZES.items():
        raw = (SPECS / name).read_bytes()
        if sha(raw) != expected:
            raise ValueError('Frozen manifest bytes changed: ' + name)
        result[name] = expected
        # /code and /specs are the read-only runtime mounts. The complete
        # manifests (including docs/tests) are additionally verified on host.
        for file, digest in json.loads(raw)['files'].items():
            path = None
            if file.startswith('specs/urbit/'):
                path = SPECS / file.removeprefix('specs/urbit/')
            elif file.startswith('scripts/urbit/'):
                path = CODE / file.removeprefix('scripts/urbit/')
            if path is not None:
                if sha(path.read_bytes()) != digest:
                    raise ValueError('Frozen executable/input bytes changed: ' + file)
                result[file] = digest
    result['v1_corpus_sha256'] = sha((SPECS / 'fixtures/native-cases.json').read_bytes())
    if result['v1_corpus_sha256'] != V1_CORPUS_SHA256:
        raise ValueError('Preserved v1 corpus bytes changed')
    for name in ('app/stead-home.hoon', 'lib/stead-core.hoon', 'lib/stead-codec.hoon',
                 'lib/stead-git.hoon', 'ted/stead-client.hoon'):
        result[name] = sha((NATIVE / name).read_bytes())
    return result


def uint(value):
    if not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]*', value):
        raise ValueError('Expected canonical decimal snapshot counter')
    return int(value)


class Driver:
    def __init__(self, call, classification, provenance, fixture_raw):
        self.call, self.classification, self.fixture_raw = call, classification, fixture_raw
        self.report = {'protocol': 'stead.qualification/1', 'status': 'not_run',
            'classification': classification, 'native_qualified': False, 'provenance': provenance,
            'checks': [], 'calls': [], 'batches': [], 'recipes': recipe_inventory(), 'pending': [],
            'limits': LIMITS, 'unimplemented': [
                'Policy uint64 overflow cannot be reached by a bounded legitimate-transition fixture.',
                'This lane does not qualify abrupt-crash recovery, browser/live identity, transport observer races, or external effects.']}

    def check(self, name, condition, **details):
        self.report['checks'].append({'name': name, 'passed': bool(condition), **details})
        if not condition:
            raise AssertionError(name)

    def invoke(self, ship, mode, route='/', raw=b'', **kwargs):
        result = self.call(ship, mode, route, raw, **kwargs)
        if not isinstance(result, dict) or not {'raw', 'json'} <= result.keys():
            raise AssertionError('Missing terminal transport evidence')
        # The injected transport owns original terminal frames/transcripts. Do
        # not duplicate large Markdown journal snapshots into this report.
        native = result.get('native', {})
        self.report['calls'].append({'ship': ship, 'mode': mode, 'route': route,
            'request_sha256': sha(raw), 'control': None if 'control' not in kwargs else {
                'operation': kwargs['control'][0], 'sender': kwargs['control'][1],
                'key': kwargs['control'][2], 'value_sha256': sha(kwargs['control'][3].encode())},
            'response_utf8_sha256': sha(result['raw'].encode()) if isinstance(result['raw'], str) else None,
            'response_bytes': len(result['raw'].encode()) if isinstance(result['raw'], str) else None,
            'response_frame_sha256': native.get('response_frame_sha256') if isinstance(native, dict) else None,
            'response_protocol': result['json'].get('protocol') if isinstance(result['json'], dict) else None})
        if self.classification == 'local-real-native-fake-ships':
            self.check('real-native-terminal-frame', isinstance(native, dict)
                and isinstance(native.get('response_frame_sha256'), str)
                and bool(HEX256.fullmatch(native['response_frame_sha256'])))
        if result['json'] is not None:
            self.check('bounded-consistent-response-json', isinstance(result['raw'], str)
                and 0 < len(result['raw'].encode()) <= 262144 and decoded(result['raw']) == result['json'])
        return result

    def control(self, operation, sender='zod', key='', value='', *, negative=False):
        # Only the private fixture's bounded full-state loads get this budget.
        # It permits measuring validation; exceeding it is still a failure.
        wait = {'timeout': 620} if operation in ('migrate-legacy', 'load-bad-legacy') else {}
        result = self.invoke('zod', 'control', control=(operation, sender, key, value), **wait)
        if negative:
            native = result.get('native', {})
            stderr = native.get('stderr') if isinstance(native, dict) else None
            lines = [line.strip() for line in stderr.splitlines() if line.strip()] if isinstance(stderr, str) else []
            self.check('native-control-specific-nack:' + operation,
                result['raw'] is None and result['json'] is None
                and isinstance(native, dict) and native.get('stdout') == '[32 %avow 1]'
                and 'stead-unsupported-state' in lines and 'poke-fail' in lines
                and lines[-1:] == ['eval: bail: %thread-fail'] and 'timeout' not in lines)
        else:
            self.check('native-control-terminal-ack:' + operation, result['json'] == {})
        return result

    def snapshot(self, predecessor=False):
        path = '/v1/predecessor-snapshot' if predecessor else '/v1/fixture-snapshot'
        value = self.invoke('zod', 'read', path)['json']
        self.check('owner-snapshot-present', isinstance(value, dict) and value.get('protocol') == 'stead.fixture-snapshot/1')
        for key in COUNTS:
            uint(value[key])
        uint(value['ordinary_count'])
        self.check('snapshot-security-and-revision-maps', isinstance(value.get('security_counts'), dict)
            and isinstance(value.get('revisions'), dict))
        for group in ('security_counts', 'revisions'):
            for counter in value[group].values():
                uint(counter)
        for key in ('state_jam_sha256', *PRESERVED_HASHES):
            self.check('snapshot-hash:' + key, isinstance(value.get(key), str) and bool(HEX256.fullmatch(value[key])))
        return value

    def unchanged(self, before, after, name):
        keys = ('state_jam_sha256', *COUNTS, *PRESERVED_HASHES, 'revisions', 'ordinary_count', 'security_counts')
        self.check(name, all(before[key] == after[key] for key in keys))

    def receipt(self, result, entry, *, predecessor=False):
        command = entry.command
        self.check('accepted-exact-command', isinstance(result, dict) and result.get('status') == 'accepted'
            and result.get('protocol') == ('stead.receipt/1' if predecessor else 'stead.receipt/2')
            and result.get('request_id') == command['request_id']
            and result.get('canonical_sha256') == entry.digest
            and result.get('project_id') == command['project_id']
            and result.get('resource_id') == command['resource_id']
            and result.get('principal_id') == PRINCIPALS[entry.sender]
            and result.get('binding_id') == BINDINGS[entry.sender]
            and result.get('authority_epoch') == command['authority_epoch']
            and result.get('authentication') == 'fake-native/1'
            and result.get('authentication_strength') == 'synthetic-native-sender'
            and result.get('resource_revision') == str(int(command['expected_revision']) + 1))
        uint(result['accepted_at_ms'])
        if result['protocol'] == 'stead.receipt/2':
            self.check('receipt-has-only-authorized-resource-scope', set(result) == RECEIPT_FIELDS
                and result['resource_kind'] == RESOURCE_KINDS[command['operation']]
                and result['container_id'] == command['payload'].get('container_id', ''))
        return result

    def apply_batch(self, entries, *, predecessor=False, accepted=True, expected_error='capacity_exceeded'):
        before = self.snapshot(predecessor)
        payload = batch_value(entries)
        operation = 'legacy-batch' if predecessor else 'native-batch'
        self.control(operation, entries[0].sender, 'all' if accepted else '', payload.decode())
        path = '/v1/predecessor-response' if predecessor else '/v1/batch-response'
        outer = self.invoke('zod', 'read', path)['json']
        self.check('batch-response-present', isinstance(outer, dict)
            and outer.get('protocol') == 'stead.fixture-predecessor/1'
            and isinstance(outer.get('response'), str))
        response = decoded(outer['response'])
        after = self.snapshot(predecessor)
        self.report['batches'].append({'operation': operation, 'sender': entries[0].sender,
            'commands': len(entries), 'payload_bytes': len(payload), 'payload_sha256': sha(payload),
            'recipe_sha256': recipe_digest(entries), 'first_request_id': entries[0].command['request_id'],
            'last_request_id': entries[-1].command['request_id'], 'response': response,
            'before_state_sha256': before['state_jam_sha256'], 'after_state_sha256': after['state_jam_sha256'],
            'before_counts': {key: before[key] for key in COUNTS}, 'after_counts': {key: after[key] for key in COUNTS}})
        if accepted:
            self.receipt(response, entries[-1], predecessor=predecessor)
            self.check('all-batch-commands-created-one-journal-and-receipt',
                uint(after['journal_events']) - uint(before['journal_events']) == len(entries)
                and uint(after['receipts']) - uint(before['receipts']) == len(entries))
        else:
            self.check('exact-native-refusal:' + expected_error, response == {
                'protocol': 'stead.result/1' if predecessor else 'stead.result/2',
                'status': 'rejected', 'error': expected_error})
            self.unchanged(before, after, 'refusal-preserves-all-authoritative-state')
        return response, after

    def accept_all(self, entries, predecessor=False):
        last = None
        for batch in batches(entries):
            last = self.apply_batch(batch, predecessor=predecessor)
        return last

    def command(self, entry):
        cmd = entry.command
        route = f"/v2/result/~{entry.sender}/{BINDINGS[entry.sender]}/{cmd['project_id']}/{cmd['request_id']}/{entry.digest}"
        return self.invoke(entry.sender, 'command', route, entry.raw)

    def direct(self, entry):
        return self.command(entry)['json']

    def recover(self, entry, sender=None):
        cmd = entry.command
        container = cmd['payload'].get('container_id', cmd['project_id'])
        route = f"/v2/receipt/{cmd['project_id']}/{container}/{cmd['resource_id']}/{cmd['operation']}/{cmd['request_id']}"
        return self.invoke(sender or entry.sender, 'read', route)

    def denied_without_change(self, entry, sender='bud', name='unauthorized-before-capacity'):
        before = self.snapshot()
        probe = Entry(sender, entry.command)
        self.check(name, self.direct(probe) == {
            'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'})
        self.unchanged(before, self.snapshot(), name + ':state-unchanged')

    def missing_binding_at_capacity(self, entry):
        before = self.snapshot()
        self.control('binding-drop', sender='bus')
        try:
            missing = self.snapshot()
            self.check('fixture-removed-current-contributor-binding',
                       missing['bindings_sha256'] != before['bindings_sha256'])
            probe = Entry('bus', entry.command)
            # No authenticated result subscription exists after this binding
            # is removed. Its exact watch NACK cannot stand in for a mutation.
            result = self.command(probe)
            native = result.get('native', {})
            stderr = native.get('stderr') if isinstance(native, dict) else None
            lines = [line.strip() for line in stderr.splitlines() if line.strip()] if isinstance(stderr, str) else []
            self.check('missing-binding-result-watch-specifically-denied',
                result['raw'] is None and result['json'] is None
                and isinstance(native, dict) and native.get('stdout') == '[32 %avow 1]'
                and all(hint in lines for hint in ('stead-watch-denied', 'watch-ack', 'watch-ack-fail'))
                and lines[-1:] == ['eval: bail: %thread-fail'] and 'timeout' not in lines)
            self.unchanged(missing, self.snapshot(), 'missing-binding-watch-preserves-state')
            # Deliver a real Gall poke without first registering a result watch.
            # This ACK is transport completion only, never business acceptance.
            ack = self.invoke('bus', 'poke', raw=probe.raw)
            self.check('missing-binding-poke-transport-ack-only', ack['json'] == {})
            self.unchanged(missing, self.snapshot(), 'missing-binding-real-poke-preserves-state')
            # The existing owner-only fixture also exposes the actual native
            # final transition result for this exact sender and command.
            denial, after = self.apply_batch([probe], accepted=False, expected_error='denied_or_not_found')
            self.check('missing-current-binding-before-ordinary-capacity', denial == {
                'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'})
            self.unchanged(missing, after, 'missing-binding-final-transition-preserves-state')
        finally:
            # Best effort only: a failed transport remains a failed run. No
            # counters/receipts are fabricated to restore a passing result.
            self.control('binding-restore', sender='bus')
            self.unchanged(before, self.snapshot(), 'exact-binding-restored-after-denied-capacity-probe')

    def reset_current(self):
        self.control('legacy-init', value=self.fixture_raw.decode())
        self.control('migrate-legacy')
        current = self.snapshot()
        self.check('empty-supported-predecessor-migrated', all(uint(current[key]) == 0
            for key in ('projects', 'work_items', 'documents', 'grants', 'objects', 'object_bytes', 'journal_events', 'receipts')))

    def predecessor_privacy(self):
        recipe = predecessor_privacy_recipe()
        self.control('legacy-init', value=self.fixture_raw.decode())
        self.accept_all(recipe['setup'], predecessor=True)
        before, _ = self.apply_batch([recipe['visible_before']], predecessor=True)
        private, _ = self.apply_batch([recipe['private_save']], predecessor=True)
        after, last = self.apply_batch([recipe['visible_after']], predecessor=True)
        self.check('old-member-receipt-exposes-private-intervening-sequence',
            uint(after['journal_sequence']) - uint(before['journal_sequence']) == 2
            and uint(private['journal_sequence']) == uint(before['journal_sequence']) + 1
            and before['journal_digest'] != after['journal_digest'])
        self.report['recipes'][recipe['name']]['observed_receipts'] = {
            'member_before': before, 'private_save': private, 'member_after': after}
        for query in recipe['private_reads']:
            self.control('legacy-read', sender='bus', key=query['kind'],
                         value=encoded({key: query[key] for key in ('project', 'resource')}).decode())
            outer = self.invoke('zod', 'read', '/v1/predecessor-response')['json']
            self.check('predecessor-private-read-envelope', isinstance(outer, dict)
                and outer.get('protocol') == 'stead.fixture-predecessor/1' and isinstance(outer.get('response'), str))
            self.check('predecessor-private-read-denied', decoded(outer['response']) == {
                'protocol': 'stead.result/1', 'status': 'rejected', 'error': 'denied_or_not_found'})
        self.unchanged(last, self.snapshot(True), 'old-private-reads-change-no-authoritative-state')
        self.apply_batch([recipe['same_project_denial']], predecessor=True, accepted=False,
                         expected_error='denied_or_not_found')
        self.apply_batch([recipe['cross_project_denial']], predecessor=True, accepted=False,
                         expected_error='invalid_command')
        self.apply_batch([recipe['fresh_control']], predecessor=True)
        self.report['recipes'][recipe['name']]['status'] = 'executed'

    def exhaustion(self):
        recipe = exhaustion_recipe()
        self.control('legacy-init', value=self.fixture_raw.decode())
        old_doc, _ = self.accept_all(recipe['setup'], predecessor=True)
        _, near = self.accept_all(recipe['fill'][:-1], predecessor=True)
        self.check('legitimate-predecessor-near-ordinary-limit', uint(near['journal_events']) == 4095)
        _, full = self.apply_batch(recipe['fill'][-1:], predecessor=True)
        self.check('actual-old-transition-filled4096', uint(full['journal_events']) == 4096
            and uint(full['receipts']) == 4096 and uint(full['projects']) == 2
            and uint(full['grants']) == 256 and uint(full['work_items']) == 2 and uint(full['documents']) == 1)
        for entry in recipe['old_revokes']:
            self.apply_batch([entry], predecessor=True, accepted=False)
        self.check('old-revocation-failure-reproduced-in-both-projects', len(recipe['old_revokes']) == 2)
        current_before = self.snapshot()
        for key in ('', 'policy', 'grant', 'reachable', 'initialized'):
            self.control('load-bad-legacy', key=key, negative=True)
            self.unchanged(current_before, self.snapshot(), 'malformed-predecessor-rejection-is-atomic:' + (key or 'receipts'))
            self.unchanged(full, self.snapshot(True), 'malformed-load-does-not-change-predecessor:' + (key or 'receipts'))
        self.control('migrate-legacy')
        migrated = self.snapshot()
        self.check('migration-preserves-exact-history-content-and-bindings',
            all(full[key] == migrated[key] for key in (*COUNTS, *PRESERVED_HASHES)))
        self.check('migration-does-not-create-security-events', uint(migrated['ordinary_count']) == 4096
            and all(uint(migrated['security_counts'][project]) == 0 for project in recipe['projects']))
        doc = recipe['document']
        view = self.invoke('zod', 'read', f"/v2/document/{PROJECT}/{CONTAINERS['zod']}/{doc.command['resource_id']}")['json']
        self.check('migrated-document-bytes-and-native-git-commit', view.get('status') == 'read'
            and view['payload']['markdown'] == doc.command['payload']['markdown']
            and view['payload']['git_commit_oid'] == old_doc['git_commit_oid'])
        replay = self.receipt(self.direct(doc), doc)
        self.check('v1-replay-projects-original-acceptance', replay['protocol'] == 'stead.receipt/2'
            and all(replay[key] == old_doc[key] for key in ('accepted_at_ms', 'canonical_sha256', 'git_commit_oid')))
        recovered = self.recover(doc)
        self.receipt(recovered['json'], doc)
        self.check('migrated-v1-recovery-matches-current-public-retry',
            recovered['json'] == replay and recovered['raw'].encode() == encoded(replay))
        self.report['recipes'][recipe['name']]['migrated_receipt_projections'] = {
            'predecessor': old_doc, 'retry': replay, 'recovery': recovered['json']}
        self.check('never-accepted-legacy-command-rejected', self.direct(recipe['unaccepted_legacy']) == {
            'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'unsupported_version'})
        self.unchanged(migrated, self.snapshot(), 'migration-read-replay-recovery-and-legacy-denial-create-no-events')
        self.denied_without_change(recipe['overflow'])
        self.missing_binding_at_capacity(recipe['overflow'])
        before = self.snapshot()
        self.check('ordinary-exhaustion-does-not-consume-security-reserve', self.direct(recipe['overflow']) == {
            'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'capacity_exceeded'})
        self.unchanged(before, self.snapshot(), 'ordinary-overflow-is-atomic')
        for project_index, project in enumerate(recipe['projects']):
            revokes = recipe['revokes'][project]
            _, partial = self.apply_batch(revokes[:1])
            original = self.direct(revokes[0])
            self.receipt(original, revokes[0])
            self.unchanged(partial, self.snapshot(), 'revoke-retry-consumes-no-reserve')
            self.accept_all(revokes[1:])
            closed = self.snapshot()
            self.check('all128-retained-grants-revoked:' + project,
                uint(closed['security_counts'][project]) == 128 and uint(closed['ordinary_count']) == 4096
                and uint(closed['journal_events']) == 4096 + 128 * (project_index + 1))
            for sender in ('zod', 'bus'):
                self.check('closed-project-read-denied:' + sender,
                    self.invoke(sender, 'read', '/v2/project/' + project)['json'] == {
                        'protocol':'stead.result/2', 'status':'rejected', 'error':'denied_or_not_found'})
            self.check('closed-project-retry-denied', self.direct(recipe['creators'][project]) == {
                'protocol':'stead.result/2', 'status':'rejected', 'error':'denied_or_not_found'})
            for sender in ('zod', 'bus'):
                self.check('closed-project-receipt-recovery-denied:' + sender,
                    self.recover(recipe['creators'][project], sender)['json'] == {
                        'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'})
            self.denied_without_change(recipe['closed_probes'][project], 'bus', 'revoked-member-mutation-at-ordinary-capacity')
            if project_index == 0:
                other = recipe['projects'][1]
                self.check('other-project-reserve-and-content-remain-independent',
                    uint(closed['security_counts'][other]) == 0
                    and self.invoke('bus', 'read', '/v2/work/' + other + '/' + recipe['works'][other])['json'].get('status') == 'read')
            self.unchanged(closed, self.snapshot(), 'closed-project-denials-do-not-change-state')
        self.report['recipes'][recipe['name']]['status'] = 'executed'

    def resource_boundaries(self):
        for recipe in resource_recipes():
            name = recipe['name']
            self.reset_current()
            self.accept_all(recipe['setup'])
            if name == 'object_bytes':
                refusal = False
                for index, entry in enumerate(recipe['candidates']):
                    before = self.snapshot()
                    if uint(before['object_bytes']) + 32768 > 8388608:
                        self.denied_without_change(entry)
                    result = self.direct(entry)
                    after = self.snapshot()
                    if result == {'protocol':'stead.result/2','status':'rejected','error':'capacity_exceeded'}:
                        self.unchanged(before, after, 'object-budget-refusal-is-atomic')
                        self.check('object-budget-before-history-or-other-limits', index < 254
                            and uint(before['journal_events']) < 4096 and uint(before['documents']) == 2
                            and int(entry.command['expected_revision']) < 128
                            and uint(before['object_bytes']) <= 8388608
                            and uint(before['object_bytes']) + 32768 > 8388608)
                        refusal = True
                        break
                    self.receipt(result, entry)
                    self.check('document-object-admission-count', uint(after['journal_events']) == uint(before['journal_events']) + 1
                        and uint(after['receipts']) == uint(before['receipts']) + 1
                        and uint(after['objects']) == uint(before['objects']) + 3
                        and uint(after['object_bytes']) > uint(before['object_bytes']))
                self.check('object-budget-boundary-reached-with-legitimate-saves', refusal)
            else:
                _, boundary = self.accept_all(recipe['accepted'])
                count_key = 'journal_events' if name == 'history' else name
                wanted = 129 if name == 'history' else LIMITS[name]
                self.check('actual-resource-capacity-reached:' + name, uint(boundary[count_key]) == wanted)
                self.denied_without_change(recipe['rejected'])
                self.apply_batch([recipe['rejected']], accepted=False)
            self.report['recipes'][name]['status'] = 'executed'


def run(call=None, *, classification='unexecuted', provenance=None, fixture_raw=None):
    driver = Driver(call, classification, provenance, fixture_raw)
    report = driver.report
    started = time.monotonic()
    try:
        fixture_raw = (SPECS / 'native-fixture.json').read_bytes() if fixture_raw is None else fixture_raw
        driver.fixture_raw = fixture_raw
        report['source_before'] = source_binding(fixture_raw)
        if call is None or not isinstance(provenance, dict) or not provenance:
            report['pending'].append('Real transport callback and explicit native source provenance are required.')
            return report
        driver.predecessor_privacy()
        driver.exhaustion()
        driver.resource_boundaries()
        driver.check('all-eight-planned-recipes-executed', len(report['recipes']) == 8
            and all(recipe['status'] == 'executed' for recipe in report['recipes'].values())
            and bool(report['calls']) and bool(report['checks'])
            and all(check['passed'] for check in report['checks']))
        report['status'] = 'passed' if classification == 'local-real-native-fake-ships' else 'host-only'
        report['native_qualified'] = report['status'] == 'passed'
    except Exception as error:
        report.update(status='failed', native_qualified=False, error=type(error).__name__ + ': ' + str(error))
    finally:
        try:
            if 'source_before' in report:
                report['source_after'] = source_binding(fixture_raw)
            if 'source_before' in report and report['source_before'] != report['source_after']:
                report.update(status='failed', native_qualified=False, error='Qualification source changed during execution')
        except Exception as error:
            report.update(status='failed', native_qualified=False, error=type(error).__name__ + ': ' + str(error))
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    return report

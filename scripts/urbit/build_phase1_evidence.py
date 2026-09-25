"""Read-only derivation of Phase 1 claims from retained native execution.

This program never runs Vere, starts ships, sleeps, or edits a raw report.  It
replays the reviewed assertion drivers through callbacks that can only return
an exact retained command's response.  A producer's ``passed`` label is never
a business predicate.  Qualification additionally requires current committed
inputs, completed guards, the two actual execution lanes, and separately
supplied independent source/N/A/host dispositions.

``build`` returns documents without writing.  The CLI writes a *new* directory
only.  An incomplete derivation is useful diagnostic output, never acceptance.
"""
from __future__ import annotations

import argparse
import copy
from collections import defaultdict
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import threading

import core_cases_v2 as QA
import core_conn
import delivery_cases as DC
import delivery_suite as DS
import digests
import execution_policy
import gall_schedule_proof
import native_transcript
import qualification_cases as QC
import qualification_gate as G

PROTOCOL = 'stead.phase1-evidence-derivation/1'
MOUNTS = ('scripts/urbit', 'native', 'specs/urbit',
          'tests/urbit/native_gall_schedule', 'tests/urbit/skill_evaluation')
CORE_DEPS = ('core_test.py', 'core_conn.py', 'core_cases_v2.py', 'core_export.py',
             'delivery_cases.py', 'delivery_suite.py', 'qualification_cases.py',
             'qualification_gate.py', 'native_transcript.py')
SCHEDULE_DEPS = ('gall_schedule.py', 'gall_schedule_proof.py', 'delivery_cases.py',
                 'core_conn.py', 'digests.py')
MODULES = (QA, core_conn, DC, DS, digests, execution_policy, gall_schedule_proof, native_transcript, QC, G)
LOADED_FILES = {Path(module.__file__).name: digests.sha(module.__file__) for module in MODULES}
LOADED_FILES[Path(__file__).name] = digests.sha(__file__)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode()


def decode(raw):
    return json.loads(raw, object_pairs_hook=G.unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-JSON constant: ' + value)))


def reference(path, raw, pointer=''):
    return {'path': str(path), 'sha256': sha(raw), 'pointer': pointer}


def command_source(mode, route='/', raw=b'', control=None):
    """Pure spelling of the frozen core_conn request; no encoder invocation."""
    require(isinstance(raw, bytes) and len(raw) <= 70000 and not raw.endswith(b'\0'), 'Invalid request bytes')
    require(isinstance(route, str) and re.fullmatch(r'/[a-zA-Z0-9~/._-]*', route) and len(route) <= 1024,
            'Invalid literal request route')
    payload = core_conn.atom(raw)
    if mode == 'control':
        require(isinstance(control, (list, tuple)) and len(control) == 4, 'Missing exact control tuple')
        operation, ship, key, value = control
        payload = f'(jam [%{operation} ~{ship} {core_conn.atom(key.encode())} {core_conn.atom(value.encode())}])'
    parts = [core_conn.atom(part.encode()) for part in route.split('/') if part]
    path = '[' + ' '.join(parts) + ' ~]' if parts else '~'
    return f'[32 %fyrd [%base %stead-client %noun [%noun [~zod %{mode} {path} {payload}]]]]'


def expected_inputs(root):
    """Independently observe repository/toolchain bytes; never read report claims."""
    root = Path(root).resolve(strict=True)
    code, specs = root / 'scripts/urbit', root / 'specs/urbit'
    errors = []
    for name, digest in LOADED_FILES.items():
        require(digests.sha(code / name) == digest, 'Loaded derivation helper changed: ' + name)
    git = lambda *args: subprocess.check_output(['git', *args], cwd=root, timeout=20)
    commit = git('rev-parse', 'HEAD').decode().strip()
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'Invalid observed source commit')
    files = {}
    for prefix in MOUNTS:
        observed = digests.source_inventory(root / prefix, ignore_python_cache=prefix == 'scripts/urbit')
        files.update({prefix + '/' + name: value for name, value in observed.items()})
    committed = {}
    for item in git('ls-tree', '-r', '-z', commit, '--', *MOUNTS).split(b'\0'):
        if not item:
            continue
        metadata, path = item.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        name = path.decode()
        require(kind == 'blob' and mode in ('100644', '100755'), 'Redirected committed source')
        raw = digests.read_source(root / name)
        committed[name] = sha(raw)
        if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != oid:
            errors.append('Observed bytes differ from committed blob: ' + name)
    if files != committed:
        errors.append('Actual mounted source inventory differs from committed tree')
    if git('status', '--porcelain', '--untracked-files=all', '--', *MOUNTS).strip():
        errors.append('Qualification input paths are dirty')
    require(git('rev-parse', 'HEAD').decode().strip() == commit, 'Source commit changed during capture')
    lock_path = specs / 'toolchain.lock.json'
    lock = decode(lock_path.read_bytes())
    kernel = root / '.runtime' / lock['kernel']['directory']
    require(digests.tree_sha(kernel, source_links=True) == lock['kernel']['source_tree_sha256'],
            'Pinned kernel source differs from lock')
    require(digests.sha(root / '.runtime' / lock['runtime']['binary']) == lock['runtime']['binary_sha256'],
            'Pinned Vere bytes differ from lock')
    native = digests.source_inventory(root / 'native/core/desk', ignore_python_cache=False)
    overlay = digests.source_inventory(root / 'tests/urbit/native_gall_schedule/desk', ignore_python_cache=False)
    require(not (set(native) & set(overlay)), 'Schedule installation collision')
    tree = G.tree_digest(native)
    common = {'native': tree, 'harness': digests.source_sha(code), 'toolchain': digests.sha(lock_path)}
    core = {**common, 'runner': {name: digests.sha(code / name) for name in CORE_DEPS}}
    for key, name in {'fixture': 'native-fixture.json', 'cases': 'fixtures/native-cases-v2.json',
                     'previous_cases': 'fixtures/native-cases.json', 'vectors': 'fixtures/commands.json',
                     'freeze': 'v2/contract-freeze.json', 'v2_vectors': 'v2/commands.json',
                     'previous_freeze': 'contract-freeze.json', 'qualification_manifest': 'v2/qualification-gate.json'}.items():
        core[key] = digests.sha(specs / name)
    schedule = {**common, 'runner': {name: digests.sha(code / name) for name in SCHEDULE_DEPS},
                'overlay': G.tree_digest(overlay),
                'fixtures': digests.sha(root / 'tests/urbit/native_gall_schedule/inputs.json'),
                'corpus': core['cases'], 'freeze': core['freeze'],
                'gall': digests.sha(kernel / 'pkg/arvo/sys/vane/gall.hoon')}
    base = {'source_commit': commit, 'native_tree_sha256': tree, 'runtime_lock_sha256': core['toolchain'],
            'corpus_sha256': core['cases'], 'contract_freeze_sha256': core['freeze'],
            'runner_sha256': core['runner']['core_test.py'], 'observer_sha256': native['app/stead-observer.hoon']}
    lanes = {}
    for name, value, installed in (('core', core, native), ('gall_schedule', schedule, native | overlay)):
        lanes[name] = {**base, 'runner_sha256': value['runner']['core_test.py' if name == 'core' else 'gall_schedule.py'],
                       'loaded_closure_sha256': value['harness'], 'installed_clay_tree_sha256': G.tree_digest(installed)}
    return {**base, 'guard_sha256': digests.sha(code / 'execution_policy.py'), 'source_files': files,
            'native_source_files': native, 'schedule_source_files': overlay, 'execution_lanes': lanes,
            'execution_inputs': {'core': core, 'gall_schedule': schedule},
            'independent_reviewers': ['/root/independent_review'], 'implementation_owner': '/root',
            'observed_source': {'committed_bytes_verified': not errors, 'errors': errors,
                                'derivation_files': LOADED_FILES}}


class Retained:
    """Bounded, immutable command/transport resolver and exact-byte binding."""
    def __init__(self, report, ref, read):
        G.validate_transport(report, ref, read)
        self.report, self.ref, self.read = report, ref, read
        self.lines, self.commands, self.by_line = {}, {}, {}
        artifact = report['transport_artifact']
        compressed = read(str(Path(ref['path']).parent / artifact['file']))
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            for number in range(1, artifact['records'] + 1):
                raw = stream.readline(24 * 1024 * 1024 + 1)
                require(raw.endswith(b'\n') and len(raw) <= 24 * 1024 * 1024, 'Transport line bound')
                self.lines[number] = (raw, decode(raw))
        for index, command in enumerate(report['commands']):
            if 'transcript' not in command:
                continue
            raw = self.record(command['transcript'])
            require(command['transcript']['line'] not in self.by_line, 'Duplicate native command transcript identity')
            self.commands[index] = raw
            self.by_line[command['transcript']['line']] = index
            if raw.get('status') != 'failed':
                require(core_conn.parse_response(raw['stdout']) == raw['outcome'], 'Decoded outcome differs from native terminal')
                require(command.get('request_sha256') == sha(raw['request'].encode()), 'Native request digest mismatch')

    def record(self, ref):
        require(ref.get('artifact') == self.report['transport_artifact']['file'], 'Foreign transcript artifact')
        raw, value = self.lines[ref['line']]
        require(ref.get('record_sha256') == sha(raw) and ref.get('record_bytes') == len(raw), 'Transcript record differs')
        return value

    def native_ref(self, index):
        return {**self.ref, 'pointer': '/commands/' + str(index)}

    def response(self, index):
        raw = self.commands[index]
        require(raw.get('status') != 'failed', 'Retained native transport failed')
        return {**copy.deepcopy(raw['outcome'] or {'raw': None, 'json': None}),
                'native': copy.deepcopy(self.report['commands'][index])}

    def bind_response(self, response):
        require(isinstance(response, dict) and isinstance(response.get('native'), dict), 'Missing native response reference')
        index = self.by_line[response['native']['transcript']['line']]
        expected = self.response(index)
        # A paired delivery trace may be added by the read-only adapter.
        stripped = copy.deepcopy(response)
        stripped['native'].pop('delivery', None)
        require(stripped == expected, 'Supplied response differs from exact native command outcome')
        return index

    def trace(self, trace, result):
        refs = [self.bind_response(trace['response'])]
        for sentinel in trace['sentinels']:
            refs.extend(self.bind_response(sentinel[name]) for name in ('before', 'after'))
        for log in trace['runtime_log_evidence']:
            value = self.record(log['transcript'])
            raw = bytes.fromhex(value['hex'])
            require(value.get('kind') == 'runtime-log-delta' and all(value[key] == log[key]
                    for key in ('ship', 'path', 'start', 'end')), 'Wrong runtime log interval')
            require(len(raw) == log['end'] - log['start'] and sha(raw) == log['sha256'], 'Edited runtime log bytes')
            require(not native_transcript.RuntimeLogs.ERROR.search(raw), 'Runtime diagnostic cannot prove clean zero delivery')
        DC.verify_one_shot(trace, result['raw'], ship=trace['request']['ship'], route=trace['request']['route'])
        require(refs[1] < refs[0] < refs[2], 'Foreign observer does not bracket request observation')
        return refs


class Replay:
    """Only exact prior native exchanges can satisfy a request; never execute it."""
    def __init__(self, retained, start=0, stop=None):
        self.retained, self.start, self.stop = retained, start, stop or len(retained.report['commands'])
        self.used, self.cursors, self.lock = set(), defaultdict(lambda: start), threading.RLock()

    def call(self, ship, mode, route='/', raw=b'', **kwargs):
        source = command_source(mode, route, raw, kwargs.get('control'))
        with self.lock:
            key = (ship, mode)
            for index, record in self.retained.commands.items():
                if index < self.cursors[key] or index >= self.stop or index in self.used:
                    continue
                if (record.get('ship'), record.get('mode'), record.get('route'), record.get('input_sha256')) != (
                        ship, mode, route, sha(raw)):
                    continue
                actual = record.get('request', record.get('transport', {}).get('request'))
                if actual != source:
                    continue
                self.used.add(index)
                self.cursors[key] = index + 1
                if record.get('status') == 'failed':
                    failure = record.get('error', '')
                    require(isinstance(record.get('transport'), dict), 'Failed exchange lacks actual trace')
                    if failure.startswith('TimeoutError:'):
                        raise TimeoutError(failure.split(':', 1)[1].strip())
                    raise ValueError('Unsupported recorded transport failure: ' + failure)
                return self.retained.response(index)
        raise ValueError('Missing exact retained exchange: ' + str((ship, mode, route, sha(raw))))

    def snapshot(self):
        value = self.call('zod', 'read', '/v1/fixture-snapshot')['json']
        require(isinstance(value, dict) and value.get('protocol') == 'stead.fixture-snapshot/1', 'Missing authority snapshot')
        return value

    def now(self):
        return int(self.snapshot()['now_ms'])

    def wait(self, deadline, evidence):
        require(isinstance(evidence, dict) and evidence.get('deadline_ms') == deadline
                and type(evidence.get('elapsed_seconds')) in (int, float)
                and 0 <= evidence['elapsed_seconds'] <= 180, 'Missing exact retained expiry observation')
        for _ in range(3700):
            now = self.now()
            if now >= deadline:
                require(evidence.get('now_ms') == now, 'Wait observation differs from authority clock')
                return copy.deepcopy(evidence)
        raise ValueError('Recorded authority clock did not cross deadline')

    def facts(self):
        return [self.retained.native_ref(index) for index in sorted(self.used)]


def lifecycle(report, evidence):
    old, new = evidence['old_pid'], evidence['replacement_pid']
    require(type(old) is int and type(new) is int and old > 0 and new > 0 and old != new
            and evidence.get('old_exit') == 0, 'Invalid retained restart identity')
    rows = report.get('lifecycle', [])
    launches = [(i, row['result']['pid']) for i, row in enumerate(rows)
                if row.get('command') == 'launch zod' and isinstance(row.get('result'), dict) and 'pid' in row['result']]
    old_indices = [i for i, pid in launches if pid == old]
    new_indices = [i for i, pid in launches if pid == new]
    require(len(old_indices) == len(new_indices) == 1 and old_indices[0] < new_indices[0], 'Restart lacks actual process launches')
    stops = [row for row in rows[old_indices[0] + 1:new_indices[0]] if row.get('command') == 'shutdown zod']
    require(len(stops) == 1 and stops[0]['result'] == {'exit_code': 0, 'forced': False}, 'Missing graceful native shutdown')


def concurrent_records(retained, requests, results):
    """Verify the exact two observed call intervals, never infer overlap from CAS."""
    release = retained.report.get('concurrent_release')
    rows = retained.report.get('concurrent_submissions')
    require(isinstance(release, dict) and set(release) == {
        'protocol', 'clock', 'participants', 'barrier_timeout_seconds', 'released_ns'}
        and release['protocol'] == 'stead.concurrent-native-calls/1'
        and release['clock'] == 'time.monotonic_ns'
        and type(release['participants']) is int and release['participants'] == 2
        and type(release['barrier_timeout_seconds']) is int and release['barrier_timeout_seconds'] == 10,
        'Missing exact two-worker barrier release')
    require(isinstance(rows, list) and len(rows) == len(requests) == len(results) == 2
            and [request[0] for request in requests] == ['bus', 'zod'],
            'Wrong concurrent writer inventory')

    def clock(value):
        require(type(value) is int and 0 < value < 2**63, 'Invalid finite monotonic call time')
        return value

    released = clock(release['released_ns'])
    indices, intervals, starts, finishes = [], [], [], []
    fields = {'sender', 'command', 'route', 'input_sha256', 'ready_ns',
              'started_ns', 'finished_ns', 'response', 'interval'}
    for row, (ship, command), result in zip(rows, requests, results, strict=True):
        require(isinstance(row, dict) and set(row) == fields
                and row['sender'] == ship and row['command'] == command
                and row['route'] == DS.command_route(ship, command)
                and row['input_sha256'] == sha(QA.canonical(command)),
                'Concurrent submission differs from exact requested command')
        ready, started, finished = (clock(row[key]) for key in ('ready_ns', 'started_ns', 'finished_ns'))
        require(ready <= released <= started < finished
                and released - ready <= 10_000_000_000
                and finished - released <= 180_000_000_000,
                'Reversed, unbounded or uncoordinated native call interval')
        require(row['response'] == result, 'Concurrent response differs from replayed actual outcome')
        index = retained.bind_response(result)
        require(isinstance(row['interval'], dict) and set(row['interval']) == {'transcript'},
                'Missing actual retained call interval')
        interval_ref = row['interval']['transcript']
        require(isinstance(interval_ref, dict) and type(interval_ref.get('line')) is int
                and interval_ref['line'] > result['native']['transcript']['line'],
                'Call interval must follow its completed response')
        interval = retained.record(interval_ref)
        require(interval == {'kind': 'concurrent-call-interval', 'release': release,
            **{key: row[key] for key in ('sender', 'route', 'input_sha256',
                                        'ready_ns', 'started_ns', 'finished_ns')},
            'response_transcript': result['native']['transcript']},
            'Claimed overlap differs from actual retained timing record')
        actual = retained.commands[index]
        require((actual['ship'], actual['mode'], actual['route'], actual['request']) == (
            ship, 'command', row['route'], command_source('command', row['route'], QA.canonical(command))),
            'Concurrent interval is tied to the wrong native exchange')
        indices.append(index)
        intervals.append(interval_ref['line'])
        starts.append(started)
        finishes.append(finished)
    require(len(set(indices)) == 2, 'One native exchange cannot represent two concurrent calls')
    require(len(set(intervals)) == 2, 'Distinct observed call interval records are required')
    require(max(starts) < min(finishes), 'Native command call intervals do not overlap')
    return indices


def export_records(value, ship, project, container, snapshot, cwd):
    """Reconstruct the recorded stock-Git journey from already bound native reads.

    No Git program is called. Captured metadata must agree with the bytes; a
    contradictory maximum, object, command, ref or file is rejected unchanged.
    """
    responses = value['native']
    require(isinstance(responses, list) and 2 <= len(responses) <= 513, 'Export native response inventory')
    maximum = max(len(response['raw'].encode()) for response in responses)
    require(type(value.get('max_response_bytes')) is int and value['max_response_bytes'] == maximum
            and 0 < maximum <= 262144, 'Claimed export response bound differs from actual native bytes')
    for response in responses:
        envelope, native = response['json'], response['native']
        require(native['ship'] == ship and native['mode'] == 'read'
                and envelope.get('protocol') == 'stead.result/2' and envelope.get('status') == 'read'
                and envelope.get('project_id') == project and envelope.get('resource_id') == container,
                'Native export envelope/actor differs')
    require(responses[0]['native']['route'] == f'/v2/git/{project}/{container}', 'Export manifest path differs')
    manifest = responses[0]['json']['payload']
    head = snapshot or manifest['snapshot_commit_oid']
    require(isinstance(head, str) and re.fullmatch(r'[0-9a-f]{40}', head)
            and value['snapshot_commit_oid'] == head, 'Export head differs from native manifest/selected snapshot')

    def tree_entries(body):
        entries = []
        while body:
            header, body = body.split(b'\0', 1)
            mode, name = header.split(b' ', 1)
            require(mode == b'100644' and QA.FILE.fullmatch(name.decode('ascii')) and len(body) >= 20,
                    'Native export tree entry differs from supported Git subset')
            entries.append((name.decode('ascii'), body[:20].hex()))
            body = body[20:]
            require(len(entries) <= 32, 'Native export tree entry bound')
        require([name for name, _ in entries] == sorted({name for name, _ in entries}), 'Native tree ordering/uniqueness')
        return entries

    pending, objects, bodies, materialization = [(head, 'commit')], {}, {}, []
    position, head_tree = 1, None
    while pending:
        oid, kind = pending.pop()
        if oid in objects:
            require(objects[oid]['kind'] == kind, 'Contradictory native graph object type')
            continue
        require(position < len(responses), 'Missing reachable native object response')
        response = responses[position]
        position += 1
        payload = response['json']['payload']
        require(response['native']['route'] == f'/v2/git-object/{project}/{container}/{head}/{oid}'
                and payload.get('oid') == oid and payload.get('snapshot_commit_oid') == head
                and payload.get('kind') == kind, 'Native object read graph/order/scope mismatch')
        body = bytes.fromhex(payload['hex'])
        require(len(body) == int(payload['byte_length']) and len(body) <= 65536
                and hashlib.sha1(f'{kind} {len(body)}\0'.encode() + body).hexdigest() == oid,
                'Native object bytes differ from original Git identity')
        objects[oid] = {'kind': kind, 'byte_length': len(body), 'hex': body.hex()}
        bodies[oid] = body
        materialization.append((oid, kind))
        if kind == 'commit':
            headers = body.split(b'\n\n', 1)[0].decode('ascii').splitlines()
            trees = [line[5:] for line in headers if line.startswith('tree ')]
            parents = [line[7:] for line in headers if line.startswith('parent ')]
            require(len(trees) == 1 and len(parents) <= 1, 'Native commit tree/parent shape')
            if oid == head:
                head_tree = trees[0]
            pending.extend((parent, 'commit') for parent in parents)
            pending.append((trees[0], 'tree'))
        elif kind == 'tree':
            pending.extend((child, 'blob') for _, child in tree_entries(body))
        else:
            require(kind == 'blob', 'Unsupported native object kind')
    require(position == len(responses) and value['objects'] == objects, 'Native export object inventory differs')
    if snapshot is None:
        require(manifest['objects'] == {oid: obj['kind'] for oid, obj in objects.items()},
                'Current authorized manifest differs from reachable object inventory')
    entries = tree_entries(bodies[head_tree])
    files = {name: {'oid': oid, 'hex': bodies[oid].hex()} for name, oid in entries}
    require(value['files'] == files, 'Captured exported files differ from native tree/blob bytes')
    require(isinstance(cwd, str) and re.fullmatch(r'/state/logs/core-export-[0-9]{8}T[0-9]{6}Z-[1-9][0-9]*', cwd),
            'Export repository must be the exact run/ordinal directory')
    commands = value['git_commands']
    require(isinstance(commands, list) and len(commands) == 5 + len(materialization) + len(entries),
            'Missing or extra stock Git command record')
    index = 0

    def git(arguments, output='', *, init=False):
        nonlocal index
        record = commands[index]
        index += 1
        require(isinstance(record, dict) and set(record) == {'argv', 'returncode', 'stdout', 'stderr'}
                and record['argv'] == ['git', '-C', cwd, *arguments]
                and type(record['returncode']) is int and record['returncode'] == 0
                and record['stdout'] == output and isinstance(record['stderr'], str)
                and (len(record['stderr']) <= 4096 if init else record['stderr'] == ''),
                'Stock Git command, cwd, exit or native-derived output differs: ' + arguments[0])
        return record

    git(['init', '--bare', '--template='], f'Initialized empty Git repository in {cwd}/\n', init=True)
    for oid, kind in materialization:
        git(['hash-object', '-w', '-t', kind, '--stdin'], oid + '\n')
    git(['symbolic-ref', 'HEAD', 'refs/heads/main'])
    git(['update-ref', 'refs/heads/main', head])
    fsck = git(['fsck', '--full', '--strict'])
    require(value['fsck'] == fsck, 'Captured fsck is detached from materialization/ref context')
    git(['ls-tree', '-rz', head], ''.join(f'100644 blob {oid}\t{name}\0' for name, oid in entries))
    for _, oid in entries:
        git(['cat-file', 'blob', oid], bodies[oid].decode('utf-8', errors='replace'))
    result = copy.deepcopy(value)
    result.update(max_response_bytes=maximum, objects=objects, files=files, snapshot_commit_oid=head)
    return result


def replay_qa(retained, corpus):
    replay = Replay(retained)
    raw = retained.report['qa']
    by_name = {case['name']: case for case in raw['cases']}
    occurrences = defaultdict(int)
    derivations = {}
    runner = None
    export_count = 0

    def capture(key):
        return copy.deepcopy(raw['captures'][runner.current['name']][key])

    def observed(case, ship, route, result):
        index = occurrences[case]
        occurrences[case] += 1
        trace = by_name[case]['delivery_observations'][index]
        require(trace['request']['ship'] == (ship or result['native']['ship'])
                and trace['request']['route'] == (route or result['native']['route']), 'Observed request scope mismatch')
        references = retained.trace(trace, result) + [retained.bind_response(result)]
        replay.used.update(references)
        derivations['one-shot/' + case + ':' + str(index + 1)] = {
            'status': 'passed', 'checks': [{'name': 'exact-one-shot-and-active-foreign-sentinel', 'passed': True}],
            'facts': [retained.native_ref(i) for i in sorted(set(references))],
            'trace': {**retained.ref, 'pointer': '/qa/cases/' + str(next(i for i, row in enumerate(raw['cases'])
                if row['name'] == case)) + '/delivery_observations/' + str(index)}}
        return copy.deepcopy(trace)

    def export(ship, project, container, snapshot=None):
        nonlocal export_count
        export_count += 1
        value = capture('export')
        responses = value['native']
        require(isinstance(responses, list) and bool(responses), 'Missing export native responses')
        for response in responses:
            native = response['native']
            require(native['ship'] == ship and native['mode'] == 'read', 'Wrong export actor')
            wanted = replay.call(ship, 'read', native['route'])
            require(response == wanted, 'Export response differs from requested native read')
        match = re.fullmatch(r'core-([0-9]{8}T[0-9]{6}Z)-transport\.jsonl\.gz', retained.report['transport_artifact']['file'])
        require(match is not None, 'Missing original export run identity')
        cwd = f'/state/logs/core-export-{match[1]}-{export_count}'
        return export_records(value, ship, project, container, snapshot, cwd)

    def matrix(case, captures):
        ids = corpus['fixture_ids']
        project, bus_container, zod_container = ids['project'], ids['bus_container'], ids['zod_container']
        bus = captures[case['action']['base_manifest_from']]['export']
        bus_head = bus['snapshot_commit_oid']
        bus_blob = next(oid for oid, obj in bus['objects'].items() if obj['kind'] == 'blob')
        zod = replay.call('zod', 'read', f'/v2/git/{project}/{zod_container}')['json']['payload']
        zod_head = zod['snapshot_commit_oid']
        zod_blob = next(oid for oid, kind in zod['objects'].items() if kind == 'blob')
        variants = ((bus_container, bus_head, bus_blob), (zod_container, zod_head, zod_blob),
                    (bus_container, zod_head, zod_blob), (zod_container, bus_head, bus_blob),
                    (bus_container, '0' * 40, bus_blob), (bus_container, bus_head, '0' * 40))
        return {'variants': [{'name': name, 'response': replay.call('bus', 'read', f'/v2/git-object/{project}/{cid}/{head}/{oid}')}
                             for name, (cid, head, oid) in zip(case['action']['variants'], variants, strict=True)]}

    def restart():
        value = capture('restart')
        lifecycle(retained.report, value)
        return value

    class RecordedQA(QA.Runner):
        def execute(self, case):
            before = set(replay.used)
            try:
                super().execute(case)
            finally:
                derivations[case['name']] = {'facts': [retained.native_ref(i) for i in sorted(replay.used - before)],
                                             'checks': self.current['checks']}

    runner = RecordedQA(corpus, replay.call, replay.snapshot, restart, export, matrix,
                        trusted_now_ms=replay.now,
                        wait_until=lambda deadline: replay.wait(deadline, capture('expiry_observation')),
                        include_second_project=True, include_scoped_privacy=True,
                        delivery_evidence=observed, defer_phase1_reviews=True,
                        classification='retained-native-predicate-replay')
    result = runner.run()
    allowed = {(case, name) for case, name in G.DEFERRED.values()}
    for case in result['cases']:
        group = derivations.setdefault(case['name'], {'checks': [], 'facts': []})
        group['status'] = ('passed' if bool(case['checks']) and case['status'] in ('passed', 'incomplete')
                           and all(check['status'] == 'passed' or check['status'] == 'skipped'
                           and (case['name'], check['name']) in allowed for check in case['checks']) else 'failed')
        if case.get('error'):
            group['error'] = case['error']
    return result, derivations, replay


def replay_capacity(retained, start, fixture):
    replay = Replay(retained, start)
    driver = QC.Driver(replay.call, 'local-real-native-fake-ships', {'retained': retained.ref}, fixture)
    groups = {}
    for name, method in (('predecessor-privacy', driver.predecessor_privacy),
                         ('exhaustion', driver.exhaustion), ('resource-boundaries', driver.resource_boundaries)):
        begin, used = len(driver.report['checks']), set(replay.used)
        try:
            method()
            groups[name] = {'status': 'passed'}
        except (ValueError, AssertionError, KeyError, IndexError, TypeError) as error:
            groups[name] = {'status': 'failed', 'error': str(error)}
        groups[name].update(checks=driver.report['checks'][begin:],
                            facts=[retained.native_ref(i) for i in sorted(replay.used - used)])
        if groups[name]['status'] != 'passed':
            break
    return groups, replay


class CoreStages:
    """Recompute core-only predicates from the same frozen vectors/commands."""
    def __init__(self, retained, corpus, specs, start):
        self.retained, self.corpus, self.specs = retained, corpus, specs
        self.replay, self.groups, self.current = Replay(retained, start), {}, None

    def check(self, name, condition):
        self.current['checks'].append({'name': name, 'passed': bool(condition)})
        require(condition, name)

    def stage(self, name, method):
        self.current = {'status': 'failed', 'checks': []}
        self.groups[name] = self.current
        before = set(self.replay.used)
        try:
            method()
            require(bool(self.current['checks']), 'No derived stage predicates')
            self.current['status'] = 'passed'
        except (ValueError, AssertionError, KeyError, IndexError, TypeError) as error:
            self.current['error'] = str(error)
        self.current['facts'] = [self.retained.native_ref(i) for i in sorted(self.replay.used - before)]
        return self.current['status'] == 'passed'

    def same(self, before):
        after = self.replay.snapshot()
        self.check('exact-business-snapshot-unchanged', before['state_jam_sha256'] == after['state_jam_sha256'])
        return after

    def control(self, value, succeeds=True, sender='zod'):
        result = self.replay.call(sender, 'control', control=value)
        self.check('owner-control:' + value[0], result['json'] == {} if succeeds else
                   result['json'] is None and 'poke-fail' in result['native']['stderr'])
        return result

    def codec(self):
        cases = []
        for version, file in ((1, 'fixtures/commands.json'), (2, 'v2/commands.json')):
            vectors = decode((self.specs / file).read_bytes())
            self.check('six-frozen-vectors:' + str(version), len(vectors) == 6)
            cases += [(f'frozen-v{version}-vector-{i}', QA.canonical(v['request']), 'accept', v)
                      for i, v in enumerate(vectors)]
        for case in self.corpus['codec_lane']['new_vectors']:
            if 'raw_utf8' in case:
                raw = case['raw_utf8'].encode()
            elif 'raw_hex' in case:
                raw = bytes.fromhex(case['raw_hex'])
            elif 'raw_recipe' in case:
                recipe = case['raw_recipe']
                raw = (recipe['prefix'] + recipe['append_utf8'] * recipe['repeat']).encode()
            else:
                recipe = case['command_recipe']
                value = copy.deepcopy(self.corpus['commands'][recipe['base_command_ref']])
                for path, replacement in recipe.get('replace', {}).items():
                    value[path[1:]] = replacement
                for path, specification in recipe['repeat_string'].items():
                    _, parent, field = path.split('/')
                    value[parent][field] = specification['value'] * specification['repeat']
                raw = QA.canonical(value)
            cases.append((case['name'], raw, case['expected']['codec'], None))
        baseline = self.replay.snapshot()
        for name, raw, expected, vector in cases:
            value = self.replay.call('bus', 'codec', raw=raw)['json']
            if expected == 'accept':
                parsed = decode(raw)
                canonical = QA.canonical(parsed)
                digest = sha(parsed['protocol'].encode() + b'\0' + canonical)
                self.check('codec:' + name, value == {'status': 'accepted', 'canonical': canonical.decode(), 'sha256': digest})
                if vector is not None:
                    self.check('frozen-digest:' + name, digest == vector['sha256'])
            else:
                self.check('codec:' + name, value == {'status': 'rejected', 'error': 'invalid_command'})
                poke = self.replay.call('bus', 'poke', raw=raw)
                self.check('native-home-rejection:' + name, poke['json'] is None and 'stead-invalid-command' in poke['native']['stderr'])
            self.same(baseline)

    def contexts(self):
        normal = {'classification': 'public-synthetic', 'custody': 'local-disposable',
                  'runtime': 'isolated-fake', 'authentication': 'fake-native/1'}
        baseline = self.replay.snapshot()
        cmd = self.corpus['commands'][self.corpus['trusted_context_lane']['probe_commands'][0]]
        raw, route = QA.canonical(cmd), DS.command_route('bus', cmd)
        pairs = {'expired-binding': (('expiry', '0'), ('expiry', '4102444800000')),
                 'revoked-binding': (('active', 'no'), ('active', 'yes')),
                 'missing-binding': (('binding-drop', ''), ('binding-restore', '')),
                 'unsupported-agent-delegation': (('kind', 'agent'), ('kind', 'person')),
                 'contradictory-context': (('kind', 'service'), ('kind', 'person'))}
        for case in self.corpus['trusted_context_lane']['cases']:
            name, info = case['name'], case['owner_local_fixture_change']
            if info['target'] == 'profile':
                field = info['field']
                operation = 'missing' if info['change'] == 'missing' else 'profile'
                change, restore = (operation, 'bus', field, 'unsupported'), ('profile', 'bus', field, normal[field])
            elif name == 'unsupported-authentication-mechanism':
                change, restore = ('profile', 'bus', 'authentication', 'oidc'), ('profile', 'bus', 'authentication', 'fake-native/1')
            else:
                a, b = pairs[name]
                change, restore = (a[0], 'bus', '', a[1]), (b[0], 'bus', '', b[1])
            self.control(change)
            invalid = self.replay.snapshot()
            result = self.replay.call('bus', 'command', route, raw)
            self.check('native-watch-context-denied:' + name, result['json'] is None
                       and 'stead-watch-denied' in result['native']['stderr'] and 'watch-ack-fail' in result['native']['stderr'])
            self.check('native-poke-context-denied:' + name, self.replay.call('bus', 'poke', raw=raw)['json'] == {})
            for path in self.corpus['trusted_context_lane']['probe_reads']:
                self.check('native-read-context-denied:' + name, self.replay.call('bus', 'read', path)['json'] == QA.DENIAL)
            self.same(invalid)
            self.control(restore)
            self.same(baseline)

    def roundtrip(self):
        before = self.replay.snapshot()
        for operation in ('load-future', 'load-counter'):
            result = self.control((operation, 'bus', '', ''), succeeds=False)
            self.check('specific-unsupported-version:' + operation, 'stead-unsupported-state' in result['native']['stderr'])
            self.same(before)
        self.control(('roundtrip', 'bus', '', ''))
        self.same(before)
        self.control(('binding-drop', 'bus', '', ''), succeeds=False, sender='bud')
        self.same(before)

    def concurrency(self):
        ids, before = self.corpus['fixture_ids'], self.replay.snapshot()
        before_index = max(self.replay.used)
        template = self.corpus['commands']['journal_first_project_followup']
        requests, results = [], []
        for index, ship in enumerate(('bus', 'zod')):
            cmd = copy.deepcopy(template)
            cmd.update(request_id=f'019939ba-4000-7000-8000-00000000800{index}', expected_revision='4')
            cmd['payload']['title'] = 'Concurrent synthetic writer ' + ship
            requests.append((ship, cmd))
            results.append(self.replay.call(ship, 'command', DS.command_route(ship, cmd), QA.canonical(cmd)))
        indices = concurrent_records(self.retained, requests, results)
        self.check('actual-two-call-overlap-after-baseline', before_index < min(indices))
        accepted = [i for i, result in enumerate(results) if result['json'] and result['json'].get('status') == 'accepted']
        rejected = [result for result in results if result['json'] == {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'revision_conflict'}]
        self.check('two-principal-one-winner', len(accepted) == len(rejected) == 1)
        winner = accepted[0]
        self.check('trusted-winner-receipt', results[winner]['json']['principal_id'] == self.corpus['principals'][requests[winner][0]]
                   and results[winner]['json']['resource_revision'] == '5')
        view = self.replay.call('nec', 'read', f"/v2/work/{ids['project']}/{ids['work_a']}")
        self.check('reader-sees-winner', view['json']['payload'] == requests[winner][1]['payload'] and view['json']['resource_revision'] == '5')
        after = self.replay.snapshot()
        self.check('concurrent-results-precede-final-snapshot', max(indices) < max(self.replay.used))
        self.check('one-durable-acceptance', int(after['journal_events']) == int(before['journal_events']) + 1
                   and int(after['receipts']) == int(before['receipts']) + 1 and after['objects'] == before['objects'])
        path = f"/v2/document/{ids['project']}/{ids['bus_container']}/{ids['document_a']}"
        owner, outsider = (self.replay.call(ship, 'read', path) for ship in ('bus', 'bud'))
        self.check('same-path-concurrent-private-read-separation', owner['json']['payload']['markdown'] ==
                   self.corpus['commands']['document_a_2']['payload']['markdown'] and outsider['json'] == QA.DENIAL)
        denied = self.replay.call('bud', 'command', DS.command_route('bus', requests[0][1]), QA.canonical(requests[0][1]))
        self.check('another-sender-cannot-reserve-result', denied['json'] is None and 'stead-watch-denied' in denied['native']['stderr'])
        self.same(after)


def replay_delivery(retained, corpus, start):
    replay = Replay(retained, start)
    raw = retained.report['delivery']
    cases = {case['name']: case for case in raw['cases']}
    watches = defaultdict(list)
    for ref in raw['calls']:
        record = retained.record(ref)
        response = record['result']
        index = retained.bind_response(response)
        require(index >= start, 'Delivery call precedes delivery stage')
        if response['native']['mode'] == 'observe':
            wire = bytes.fromhex(record['kwargs']['raw'])
            request = decode(wire)
            require(retained.commands[index]['request'] == command_source('observe', '/', wire), 'Edited observer control')
            if request['action'] == 'watch':
                watches[response['native']['ship']].append(request['id'])
    require(all(len(ids) <= 80 and len(ids) == len(set(ids)) for ids in watches.values()), 'Duplicate/excessive observer probes')

    class Pool:
        def allocate(self, ship):
            with replay.lock:
                require(bool(watches[ship]), 'Missing retained allocated probe')
                return watches[ship].pop(0)

    suite = None
    seen, groups = set(), {}

    def runtime_errors(cursor=None):
        if cursor is None:
            return {'cursor': 'retained-start'}
        details = next(row['detail'] for row in cases[suite.current['name']]['assertions']
                       if row['name'] == 'known-valid-mark-positive-control')
        request = details['request']
        source = next(result for result in (retained.response(i) for i in replay.used)
                      if result['native']['ship'] == request['ship'] and result['native']['route'] == request['route']
                      and result['native']['mode'] == 'read')
        replay.used.update(retained.trace(details, source))
        return {'errors': [], 'segments': copy.deepcopy(details['runtime_log_evidence'])}

    def wait(deadline):
        evidence = next(row['detail'] for row in cases[suite.current['name']]['assertions']
                        if row['name'] == 'actual-real-expiry-observed')
        return replay.wait(deadline, evidence)

    def unavailable(attempt):
        evidence = copy.deepcopy(cases['home-unavailable']['unavailability'])
        lifecycle(retained.report, evidence)
        actual = attempt(replay.call)
        require(actual == evidence['attempt'], 'Unavailable outcome differs from retained transport exception')
        return evidence

    class RecordedSuite(DS.Suite):
        def check(self, name, condition, detail=None):
            nonlocal seen
            group = groups.setdefault(self.current['name'], {'checks': [], 'facts': []})
            group['facts'].extend(retained.native_ref(i) for i in sorted(replay.used - seen))
            seen = set(replay.used)
            group['checks'].append({'name': name, 'passed': bool(condition)})
            super().check(name, condition, detail)

    suite = RecordedSuite(corpus, replay.call, snapshot=replay.snapshot,
        pending_snapshot=lambda: replay.call('zod', 'read', '/v1/pending-snapshot'),
        control=lambda *value: replay.call('zod', 'control', control=value),
        trusted_now_ms=replay.now, wait_until=wait, unavailable_home=unavailable,
        pause=lambda seconds: None, runtime_errors=runtime_errors,
        provenance={'retained': retained.ref}, classification='real-native-fake-ships', probe_pool=Pool())
    result = suite.run()
    for case in result['cases']:
        group = groups.setdefault(case['name'], {'checks': [], 'facts': []})
        group['status'] = 'passed' if case['status'] in ('passed', 'incomplete') and bool(group['checks']) else 'failed'
        if case.get('error'):
            group['error'] = case['error']
        if case.get('missing'):
            group['missing'] = case['missing']
    return groups, replay


def compile_facts(report, ref):
    wanted = [(ship, '+stead-build-probe', '%stead-builds-pass') for ship in ('zod', 'bus', 'nec', 'bud')]
    wanted += [('zod', '+stead-codec-probe', '%stead-codec-six-vectors-pass'),
               ('zod', '+stead-core-probe', '%stead-core-basic-and-counter-edge-pass'),
               ('zod', '+stead-reducers-probe', '%stead-native-reducers-pass')]
    facts, checks = [], []
    for ship, source, expected in wanted:
        matches = [(i, row) for i, row in enumerate(report['commands'])
                   if row.get('ship') == ship and row.get('dojo') == source]
        require(len(matches) == 1 and matches[0][1].get('result', '').strip() == expected,
                'Missing exact native compile/probe result: ' + ship + ':' + source)
        facts.append({**ref, 'pointer': '/commands/' + str(matches[0][0])})
        checks.append({'name': ship + ':' + source, 'passed': True})
    for ship, source in [('zod', '|start %stead-home')] + [(ship, '|start %stead-observer') for ship in DC.FAKES]:
        matches = [(i, row) for i, row in enumerate(report['commands'])
                   if row.get('ship') == ship and row.get('dojo') == source and isinstance(row.get('result'), str)]
        require(len(matches) == 1, 'Missing native app start')
        facts.append({**ref, 'pointer': '/commands/' + str(matches[0][0])})
    return {'status': 'passed', 'checks': checks, 'facts': facts,
            'scope': 'Actual compile/probe results; counter-edge probe uses explicitly synthetic state.'}


def evaluator_facts(report, ref):
    """Only retained actual evaluator bytes can establish these controls."""
    indices = G.validate_evaluator_controls(report)
    facts = [{**ref, 'pointer': '/commands/' + str(index)} for index in indices]
    return {'status': 'passed', 'facts': facts,
            'checks': [{'name': name, 'passed': True} for name in (
                'actual-invalid-input-parse-failure', 'actual-complete-frame-above-64KiB', 'actual-exact-decoded-result')]}


def requirement_groups(corpus):
    """The exact 66-row reviewed mapping; indices are resolved to frozen names."""
    cases = list(corpus['ordered_cases'])
    for lane in ('real_expiry_continuation', 'source_review_continuation', 'separate_project_journal_lane', 'scoped_privacy_lane'):
        cases += corpus[lane]['cases']
    require(len(cases) == 148 and len({row['name'] for row in cases}) == 148, 'Wrong frozen QA case inventory')
    q = lambda *indices: ['qa/' + cases[i]['name'] for i in indices]
    privacy = ['capacity/predecessor-privacy']
    exhaustion = ['capacity/exhaustion']
    resources = ['capacity/resource-boundaries']
    held = ['delivery/known-mark-and-held-outsider']
    leave = ['delivery/leave-and-fresh-retry']
    expiry = ['delivery/lazy-expiry-and-same-path-retirement']
    missing = ['delivery/missing-channel-and-wrong-digest']
    result = {
        'scoped-private-metadata': privacy + q(*range(129, 148), 11, 51, 92, 93, 94),
        'v2-native-compile': ['core/compile'] + q(0),
        'v2-ordered-journey': q(*range(148)),
        'v2-codec-and-home-rejection': ['core/codec'],
        'v2-context-controls': ['core/contexts'],
        'v2-concurrent-cas': ['core/concurrency'],
        'legacy-private-project-probe-reproduced': privacy,
        'legacy-private-container-probe-reproduced': privacy,
        'v2-cross-project-local-id': q(5, 13, 126, 127, 128, *range(142, 148)),
        'v2-cross-container-local-id': q(63, 64, 65, 132, *range(137, 142)),
        'v2-public-receipt-normal': q(11, 51, 139, 144),
        'v2-public-receipt-retry': q(75, 96, 130, 134, 108, 112, 120),
        'v2-public-receipt-recovery': q(19, 33, 68, 105, 113, 114, 121, 123, 135) + missing,
        'v2-public-export-projection': q(92, 93, 94, 98, 131, 136),
        'legacy-revocation-exhaustion-reproduced': exhaustion,
        'v2-security-revoke-reserve': exhaustion,
        'v2-cross-project-security-admin': exhaustion,
        'v2-security-reserve-exhaustion': exhaustion,
        'v2-security-counter-u64-edge': ['core/compile'],
        'boundary-projects': resources,
        'boundary-grants': resources + exhaustion + q(29, 35, 44),
        'boundary-work': resources + q(126, 127, 128, 142, 144, 145) + ['core/concurrency'],
        'boundary-documents-tree': resources,
        'boundary-container-history': resources,
        'boundary-object-bytes': resources,
        'boundary-ordinary-journal-receipts': exhaustion,
        'boundary-pending': ['delivery/pending-quotas'],
        'delivery-positive-known-mark-control': held,
        'delivery-ended-duct-no-late-fact': leave + expiry,
        'delivery-expired-same-path-reregistration': expiry,
        'delivery-late-old-leave': ['schedule/late-old-leave'],
        'delivery-expiration-lazy': expiry,
        'delivery-leave-cancels': leave,
        'delivery-same-path-private-readers': held,
        'delivery-wrong-sender-digest': ['delivery/wrong-sender-and-binding'] + missing,
        'delivery-missing-channel': missing,
        'delivery-home-unavailable': ['delivery/home-unavailable'],
        'delivery-late-response': leave + expiry,
        'migration-current-roundtrip': ['core/roundtrip'],
        'migration-actual-v1-vase': exhaustion,
        'migration-legacy-receipt-projection': exhaustion,
        'migration-invalid-predecessors': ['core/roundtrip'] + exhaustion,
        'warm-home-restart': q(95, 96, 97, 98),
        'evaluator-error-boundaries': ['core/evaluator']}
    return result


def build(root, *, core_path, schedule_path, core_guard_path, schedule_guard_path,
          dispositions_path=None, output_prefix):
    """Return four documents, reading only. Missing facts remain nonpassing."""
    root = Path(root).resolve(strict=True)
    reader = G.artifact_reader(root)
    retained_bytes = {}

    def read(path):
        raw = reader(str(path))
        previous = retained_bytes.setdefault(str(path), raw)
        require(previous == raw, 'Retained artifact changed during derivation')
        return raw

    def load(path):
        raw = read(path)
        return decode(raw), reference(path, raw)

    manifest, manifest_ref = load('specs/urbit/v2/qualification-gate.json')
    corpus = decode(read('specs/urbit/fixtures/native-cases-v2.json'))
    core, core_ref = load(core_path)
    schedule, schedule_ref = load(schedule_path)
    core_guard, core_guard_ref = load(core_guard_path)
    schedule_guard, schedule_guard_ref = load(schedule_guard_path)
    expected = expected_inputs(root)
    groups, errors = {}, []
    native = Retained(core, core_ref, read)

    def derive(name, function):
        try:
            groups[name] = function()
        except (ValueError, AssertionError, KeyError, IndexError, TypeError) as error:
            groups[name] = {'status': 'failed', 'checks': [], 'facts': [], 'error': str(error)}

    derive('core/compile', lambda: compile_facts(core, core_ref))
    derive('core/evaluator', lambda: evaluator_facts(core, core_ref))
    qa_result, qa_groups, qa_replay = replay_qa(native, corpus)
    for name, value in qa_groups.items():
        groups['qa/' + name] = value
    stages = CoreStages(native, corpus, root / 'specs/urbit', max(qa_replay.used, default=-1) + 1)
    for name in ('codec', 'contexts', 'roundtrip', 'concurrency'):
        if not stages.stage(name, getattr(stages, name)):
            break
    groups.update({'core/' + key: value for key, value in stages.groups.items()})
    if stages.groups.get('concurrency', {}).get('status') == 'passed':
        try:
            delivery, replay = replay_delivery(native, corpus, max(stages.replay.used) + 1)
            groups.update({'delivery/' + key: value for key, value in delivery.items()})
            if all(value['status'] == 'passed' for value in delivery.values()) and len(delivery) == 8:
                capacity, _ = replay_capacity(native, max(replay.used) + 1, read('specs/urbit/native-fixture.json'))
                groups.update({'capacity/' + key: value for key, value in capacity.items()})
        except (ValueError, AssertionError, KeyError, IndexError, TypeError) as error:
            errors.append('Later native lane derivation: ' + str(error))

    def scheduled():
        G.validate_schedule(schedule)
        validation = gall_schedule_proof.validate(schedule['positive'])
        facts = [{**schedule_ref, 'pointer': '/commands/' + str(i)} for i, row in enumerate(schedule['commands'])
                 if row.get('dojo') in ('+stead-gall-schedule', '+stead-gall-schedule-negative')]
        require(len(facts) == 2, 'Missing exact scheduled Gall positive/negative commands')
        return {'status': 'passed', 'checks': validation['assertions'], 'facts': facts,
                'scope': schedule['scope'], 'positive': {**schedule_ref, 'pointer': '/positive'}}

    derive('schedule/late-old-leave', scheduled)
    mapping = requirement_groups(corpus)
    for row in manifest['required']:
        if row['id'].startswith('delivery:'):
            _, name, occurrence = row['id'].split(':')
            mapping[row['id']] = ['qa/one-shot/' + name + ':' + occurrence]
    required_native = {row['id'] for row in manifest['required'] if row['kind'] == 'native'}
    require(set(mapping) == required_native and len(mapping) == 66 and len(manifest['required']) == 73,
            'Unmapped or changed qualification requirement inventory')
    guards, guard_errors = {}, {}
    for lane, report, guard in (('core', core, core_guard), ('gall_schedule', schedule, schedule_guard)):
        try:
            G.validate_lane(lane, report, guard, expected)
            require(guard['guard_sha256'] == expected['guard_sha256'], 'Guard source mismatch')
            guards[lane] = 'completed'
        except (ValueError, AssertionError, KeyError, IndexError, TypeError) as error:
            guards[lane], guard_errors[lane] = 'failed', str(error)
    proofs, items = {}, []
    prefix = Path(output_prefix)
    require(not prefix.is_absolute() and '..' not in prefix.parts and prefix.parts, 'Output prefix must be repository-relative')
    proof_path = (prefix / 'proofs.json').as_posix()
    for requirement in manifest['required']:
        identifier = requirement['id']
        if requirement['kind'] != 'native':
            continue
        selected = mapping[identifier]
        available = [groups.get(name, {}) for name in selected]
        ok = bool(available) and all(group.get('status') == 'passed' and group.get('checks') and group.get('facts') for group in available)
        lane = 'gall_schedule' if identifier == 'delivery-late-old-leave' else 'core'
        status = 'passed' if ok else 'incomplete'
        facts = []
        for group in available:
            for fact in group.get('facts', []):
                record = G.pointer(schedule if lane == 'gall_schedule' else core, fact['pointer'])
                # An expected unavailable exchange supports its detailed
                # derivation, but is never disguised as a successful command.
                if record.get('status') not in ('fail', 'failed') and fact not in facts:
                    facts.append(fact)
        # Full fact sets occur once in derivations; two anchors provide the
        # gate's native admission references without duplicating megabytes.
        anchors = facts if identifier == 'evaluator-error-boundaries' else facts[:1] + facts[-1:] if len(facts) > 1 else facts
        proof = {'id': identifier, 'kind': 'native', 'status': status, 'scope': requirement['scope'],
                 'classification': ('real-native-evaluator' if identifier == 'evaluator-error-boundaries' else
                    'native-scheduled-gall' if lane == 'gall_schedule' else 'real-native-fake-ships'),
                 'execution_lane': lane, 'bindings': expected['execution_lanes'][lane],
                 'guard_status': guards[lane], 'native': anchors,
                 'assertions': [{'name': name, 'status': status,
                     'predicate': 'Every selected bounded predicate was recomputed from exact retained command bytes.',
                     'derivations': ['/derivations/' + key.replace('~', '~0').replace('/', '~1') for key in selected]}
                     for name in requirement['assertions']]}
        if not ok:
            proof['missing_or_failed_derivations'] = [name for name, group in zip(selected, available)
                if group.get('status') != 'passed' or not group.get('checks') or not group.get('facts')]
        proofs[identifier] = proof
    external, continuity = [], None
    if dispositions_path is not None:
        disposition_document, _ = load(dispositions_path)
        continuity = disposition_document.get('historical_guard_continuity')
        external = disposition_document['items']
        allowed = {row['id'] for row in manifest['required'] if row['kind'] != 'native'}
        require(isinstance(external, list) and len({row['id'] for row in external}) == len(external)
                and all(row.get('id') in allowed for row in external), 'Only original seven external typed dispositions are accepted')
        for item in external:
            proof = G.retained(item['artifact'], read)
            for name in proof.get('reviewed_source_files', {}):
                raw = read(name)
                expected['source_files'][name] = sha(raw)
                committed = subprocess.check_output(['git', 'show', expected['source_commit'] + ':' + name],
                                                    cwd=root, timeout=20)
                require(committed == raw, 'Independently reviewed source differs from observed commit: ' + name)
    document = {'protocol': PROTOCOL, 'classification': 'host-derivation-from-retained-native-bytes',
                'native_execution_performed': False, 'independent_acceptance_performed': False,
                'proofs': proofs, 'derivations': groups, 'derivation_errors': errors,
                'guard_errors': guard_errors, 'raw_qa_status': core.get('qa', {}).get('status'),
                'replayed_qa_counts': qa_result.get('case_counts'),
                'source_observation': expected['observed_source'],
                'historical_reports_unchanged': True}
    proof_raw = encoded(document)
    require(len(proof_raw) <= 32 * 1024 * 1024, 'Derived proof artifact exceeds admission bound')
    for identifier, proof in proofs.items():
        items.append({key: proof[key] for key in ('id', 'kind', 'status', 'bindings', 'execution_lane')}
                     | {'artifact': reference(proof_path, proof_raw, '/proofs/' + identifier.replace('~', '~0').replace('/', '~1'))})
    items.extend(copy.deepcopy(external))
    index = {'manifest': manifest_ref, 'executions': {'core': core_ref, 'gall_schedule': schedule_ref},
             'guards': {'core': core_guard_ref, 'gall_schedule': schedule_guard_ref}, 'items': items}
    if continuity is not None:
        # This is a retained independent review reference, not an exemption
        # manufactured by this builder. The gate owns its exact two-ID scope.
        index['historical_guard_continuity'] = copy.deepcopy(continuity)
    qualification = G.reconcile(manifest, index, expected,
        read_artifact=lambda path: proof_raw if path == proof_path else read(path))
    if expected['observed_source']['errors']:
        qualification['status'] = 'failed'
        qualification.setdefault('errors', []).extend(expected['observed_source']['errors'])
    for path, raw in retained_bytes.items():
        require(reader(path) == raw, 'Input artifact changed during read-only build')
    require({name: digests.sha(root / 'scripts/urbit' / name) for name in LOADED_FILES} == LOADED_FILES,
            'Derivation source changed during read-only build')
    for prefix in MOUNTS:
        actual = digests.source_inventory(root / prefix, ignore_python_cache=prefix == 'scripts/urbit')
        wanted = {name[len(prefix) + 1:]: digest for name, digest in expected['source_files'].items()
                  if name.startswith(prefix + '/')}
        require(actual == wanted, 'Observed source inventory changed during derivation: ' + prefix)
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, timeout=20).decode().strip()
            == expected['source_commit'], 'Commit changed during derivation')
    return {'proofs': document, 'evidence_index': index, 'expected_bindings': expected,
            'qualification_report': qualification}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    for name in ('core', 'schedule', 'core-guard', 'schedule-guard', 'output-dir'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--dispositions')
    args = parser.parse_args(argv)
    root = args.root.resolve(strict=True)
    relative = Path(args.output_dir)
    require(not relative.is_absolute() and relative.parts and '..' not in relative.parts,
            'Output directory must be repository-relative')
    with execution_policy.directory_fd(root / relative.parent) as parent:
        identity = os.fstat(parent)
        try:
            os.stat(relative.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('Output directory already exists; raw artifacts are never overwritten')
        result = build(root, core_path=args.core, schedule_path=args.schedule,
                       core_guard_path=args.core_guard, schedule_guard_path=args.schedule_guard,
                       dispositions_path=args.dispositions, output_prefix=args.output_dir)
        # Detect a replaced parent name, while retaining the original handle
        # for every mutation. A later rename cannot redirect an open dir_fd.
        with execution_policy.directory_fd(root / relative.parent) as current:
            observed = os.fstat(current)
            require((observed.st_dev, observed.st_ino) == (identity.st_dev, identity.st_ino),
                    'Output parent changed during derivation')
        os.mkdir(relative.name, mode=0o700, dir_fd=parent)
        directory = os.open(relative.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=parent)
        try:
            names = {'proofs': 'proofs.json', 'evidence_index': 'index.json', 'expected_bindings': 'bindings.json',
                     'qualification_report': 'qualification.json'}
            for key, name in names.items():
                descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                     0o600, dir_fd=directory)
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(encoded(result[key]))
        finally:
            os.close(directory)
    print(json.dumps({'classification': PROTOCOL, 'native_execution_performed': False,
                      'status': result['qualification_report']['status'], 'output': args.output_dir}))
    return 0 if result['qualification_report']['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

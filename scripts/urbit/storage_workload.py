"""Fixed T06 workload on the real configured disposable Home transport.

No CLI, boot, actor substitution or live-pier selection. team_check owns the
authenticated four-ship setup and final cleanup. Host tests inject transport
only to verify this controller; their timings are not native measurements.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time

PROFILE = 'stead.storage-initial/1'
WORKLOAD = {'projects': 2, 'work_per_project': 32, 'docs_per_project': 8,
            'comments_per_work': 4, 'document_edits_after_create': 4}
MAX_SECONDS = 1800
MAX_CALLS = 768
MAX_TRANSPORT_BYTES = 2 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')
RECEIPT_FIELDS = {'protocol', 'status', 'request_id', 'canonical_sha256', 'project_id',
    'resource_id', 'resource_kind', 'container_id', 'resource_revision', 'authority_epoch',
    'operation', 'principal_id', 'binding_id', 'binding_revision', 'identity_ship',
    'authentication', 'authentication_strength', 'session_audit_id', 'runtime',
    'accepted_at_ms', 'git_commit_oid'}


def require(ok):
    if not ok:
        raise ValueError('Fixed storage workload refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def uid(number):
    require(type(number) is int and 0 <= number < 2 ** 48)
    return '019939ba-4000-7000-8000-' + f'{number:012x}'


def uint(value):
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]{0,19}', value) is not None)
    number = int(value)
    require(number < 2 ** 64)
    return number


def distribution(values):
    """Nearest-rank percentiles over actual retained integer nanoseconds."""
    require(type(values) is list and 0 < len(values) <= MAX_CALLS
            and all(type(v) is int and v >= 0 for v in values))
    ordered = sorted(values)
    return {'samples': len(values), 'minimum_ns': ordered[0], 'maximum_ns': ordered[-1],
            'p50_ns': ordered[math.ceil(len(values) * .50) - 1],
            'p95_ns': ordered[math.ceil(len(values) * .95) - 1]}


def transport_record(result, ship, mode, raw, route):
    """Retain one original frame and original JSON, without duplicate renderings."""
    require(ship == 'bus' and mode in ('command', 'query') and type(raw) is bytes
            and 0 < len(raw) <= 65536 and type(route) is str and len(route) <= 1024)
    frame = result['response_frame_hex']
    require(type(frame) is str and re.fullmatch(r'(?:[0-9a-f]{2}){5,1000005}', frame) is not None)
    require(sha(bytes.fromhex(frame)) == result['response_frame_sha256'])
    text = result['outcome']['raw']
    require(type(text) is str and 0 < len(text.encode()) <= 262144
            and json.loads(text) == result['outcome']['json'])
    return {'ship': ship, 'mode': mode, 'input_sha256': sha(raw), 'input_hex': raw.hex(),
            'route': route, 'response_frame_sha256': result['response_frame_sha256'],
            'response_frame_hex': frame, 'outcome_raw': text}


def receipt(value, command, actor):
    require(type(value) is dict and set(value) == RECEIPT_FIELDS)
    expected = {'protocol': 'stead.receipt/3', 'status': 'accepted',
        'request_id': command['request_id'], 'canonical_sha256': sha(b'stead.command/3\0' + canonical(command)),
        'project_id': command['project_id'], 'resource_id': command['resource_id'],
        'resource_kind': command['operation'].split('.')[0],
        'container_id': command['resource_id'] if command['operation'] == 'container.create'
                        else command['payload'].get('container_id', ''),
        'resource_revision': str(uint(command['expected_revision']) + 1), 'authority_epoch': '1',
        'operation': command['operation'], 'principal_id': actor['principal_id'],
        'binding_id': actor['binding_id'], 'binding_revision': actor['binding_revision'],
        'identity_ship': '~bus', 'authentication': 'native-sender/1',
        'authentication_strength': 'native-sender', 'session_audit_id': '', 'runtime': 'isolated-fake'}
    require(all(value[key] == item for key, item in expected.items()) and uint(value['accepted_at_ms']) > 0)
    require(type(value['git_commit_oid']) is str
            and (re.fullmatch('[0-9a-f]{40}', value['git_commit_oid']) is not None
                 if command['operation'] == 'document.save' else value['git_commit_oid'] == ''))


def rows(value, query):
    require(type(value) is dict and set(value) == {'protocol', 'status', 'authority_epoch',
        'generation', 'cursor', 'rows', 'request_id', 'kind', 'project_id', 'container_id', 'resource_id'})
    require(value['protocol'] == 'stead.query-result/3' and value['status'] == 'read'
        and all(value[k] == query[k] for k in ('request_id', 'kind', 'project_id', 'container_id', 'resource_id'))
        and value['authority_epoch'] == ('1' if query['project_id'] else '0')
        and type(value['generation']) is str and HEX.fullmatch(value['generation']) is not None
        and type(value['cursor']) is str and (value['cursor'] == '' or HEX.fullmatch(value['cursor']) is not None)
        and type(value['rows']) is dict and len(value['rows']) <= 20
        and set(value['rows']) == {str(i) for i in range(len(value['rows']))})
    return list(value['rows'].values())


def host_sample(host):
    """Non-atomic live metadata sample of the owned Home process and its .urb."""
    host['execution_check']()
    process = host['TEAM'].children['zod']
    require(process.poll() is None and type(process.pid) is int and process.pid > 1)
    proc = Path('/proc') / str(process.pid)
    before = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()[19]
    status = (proc / 'status').read_text()
    memory = {}
    for key in ('VmRSS', 'VmHWM'):
        match = re.search(r'^' + key + r':\s+([0-9]+) kB$', status, re.M)
        require(match is not None)
        memory[key + '_bytes'] = int(match[1]) * 1024
    root = host['LIVE'] / 'zod' / '.urb'
    require(root.is_dir() and not root.is_symlink())
    count = logical = allocated = special = 0
    inodes = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        host['execution_check']()
        for name in [*dirs, *files]:
            item = Path(directory) / name
            info = item.lstat()
            require(not stat.S_ISLNK(info.st_mode))
            count += 1
            require(count <= 32768)
            if stat.S_ISREG(info.st_mode):
                identity = (info.st_dev, info.st_ino)
                if identity not in inodes:
                    inodes.add(identity)
                    logical += info.st_size
                    allocated += info.st_blocks * 512
            elif not stat.S_ISDIR(info.st_mode):
                special += 1
    require(process.poll() is None and before == (proc / 'stat').read_text().rsplit(') ', 1)[1].split()[19])
    return {'pid': process.pid, 'process_start_ticks': before, **memory,
            'urb_logical_bytes': logical, 'urb_allocated_bytes': allocated,
            'urb_entries': count, 'urb_special_entries': special, 'atomic': False}


def native_observation(output):
    """Parse only the fixed read-only suspended Home generator's small atom."""
    require(type(output) is str and len(output) <= 16384
            and re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', output.strip()) is not None)
    number = int(output.strip().replace('.', ''), 16)
    raw = number.to_bytes((number.bit_length() + 7) // 8, 'little')
    value = json.loads(raw)
    fields = {'protocol', 'saved_version', 'vase_bytes', 'payload_bytes', 'journal_bytes',
        'receipt_bytes', 'object_bytes', 'objects', 'projects', 'work_items', 'documents',
        'comments', 'journal_events', 'receipts', 'saved_vase_sha256'}
    require(type(value) is dict and set(value) == fields and canonical(value) == raw
            and value['protocol'] == 'stead.storage-observation/1' and value['saved_version'] == '3'
            and type(value['saved_vase_sha256']) is str and HEX.fullmatch(value['saved_vase_sha256']) is not None)
    for key in fields - {'protocol', 'saved_vase_sha256'}:
        uint(value[key])
    require(all(value[k] == str(v) for k, v in {'projects': 2, 'work_items': 64,
        'documents': 16, 'comments': 256, 'journal_events': 404, 'receipts': 404}.items()))
    require(all(uint(value[k]) > 0 for k in ('vase_bytes', 'payload_bytes', 'journal_bytes',
                                           'receipt_bytes', 'object_bytes', 'objects')))
    return value


def run(*, call, config, guard, sample, checkpoint, clock=time.monotonic_ns):
    """Use the caller's current native bus transport; never synthesize receipts."""
    require(config['home'] == '~zod' and config['custody'] == 'local-disposable'
            and config['runtime'] == 'isolated-fake' and set(config['bindings']) == {'~bus', '~nec'})
    actor = config['bindings']['~bus']
    require(actor['active'] == 'yes' and config['project_creators'] == {actor['principal_id']: 'yes'})
    report = {'protocol': 'stead.storage-workload/1', 'profile': PROFILE, 'status': 'fail',
        'scope': 'Configured disposable command/query3 round trips; no browser or live pilot',
        'workload': dict(WORKLOAD), 'qualifies_phase': False, 'samples': [], 'resources': [],
        'accepted_writes': 0, 'verified_readbacks': 0, 'pages': [], 'latency': None,
        'error_class': None}
    sequence = 1000000
    start = clock()
    def current():
        guard()
        require(0 <= clock() - start < MAX_SECONDS * 1000000000)
    def request():
        nonlocal sequence
        sequence += 1
        return uid(sequence)
    def invoke(mode, value):
        current()
        require(len(report['samples']) < MAX_CALLS)
        began = clock()
        observed = call('bus', mode, value)
        ended = clock()
        require(type(began) is int and type(ended) is int and ended >= began)
        report['samples'].append({'kind': mode, 'operation': value.get('operation', value.get('kind')),
            'duration_ns': ended - began, 'request_sha256': sha(canonical(value)),
            'response_sha256': sha(canonical(observed))})
        current()
        return observed
    def query(kind, project='', resource='', container='', cursor=''):
        return {'protocol': 'stead.query/3', 'request_id': request(), 'kind': kind,
            'project_id': project, 'resource_id': resource, 'container_id': container,
            'search': '', 'cursor': cursor}
    def read(kind, project='', resource='', container='', cursor=''):
        q = query(kind, project, resource, container, cursor)
        value = invoke('query', q)
        return rows(value, q), value
    def write(operation, project, resource, revision, payload):
        value = {'protocol': 'stead.command/3', 'request_id': request(), 'operation': operation,
            'project_id': project, 'resource_id': resource, 'authority_epoch': '1',
            'expected_revision': str(revision), 'payload': payload}
        observed = invoke('command', value)
        receipt(observed, value, actor)
        report['accepted_writes'] += 1
    def snapshot(stage):
        current(); report['resources'].append({'stage': stage, 'observed': sample()})
        checkpoint(report)
    try:
        initial, response = read('projects')
        require(initial == [] and response['cursor'] == '')
        snapshot('empty-configured-home')
        projects = [uid(100000 + i) for i in range(2)]
        for index, project in enumerate(projects):
            write('project.create', project, project, 0, {'organization_id': config['organization_id'],
                'owning_team_id': config['team_id'], 'title': 'T06 synthetic ' + str(index),
                'project_key': 'STORE' + ('A' if index == 0 else 'B'), 'preset': 'general'})
            for i in range(32):
                work = uid(200000 + index * 32 + i)
                payload = {'title': 'T06 Work ' + str(i), 'description': 'Synthetic storage baseline. λ\n',
                           'type': 'task', 'status': 'todo', 'priority': 'medium'}
                write('work.create', project, work, 0, payload)
                actual, response = read('work', project, work)
                require(len(actual) == 1 and response['cursor'] == ''
                    and actual[0]['resource_id'] == work and actual[0]['resource_revision'] == '1'
                    and all(actual[0][key] == value for key, value in payload.items()))
                report['verified_readbacks'] += 1
        snapshot('64-work-created')
        for index, project in enumerate(projects):
            for i in range(32):
                work = uid(200000 + index * 32 + i)
                bodies = ['T06 comment ' + str(j) + ' for ' + work + '. λ\n' for j in range(4)]
                for j, body in enumerate(bodies):
                    write('work.comment', project, work, j + 1, {'body': body})
                actual, response = read('comments', project, work)
                require(response['cursor'] == '' and len(actual) == 4)
                for j, row in enumerate(actual):
                    require(row['body'] == bodies[j] and row['comment_revision'] == str(j + 2)
                        and row['principal_id'] == actor['principal_id'] and row['identity_ship'] == '~bus'
                        and uint(row['accepted_at_ms']) > 0)
                report['verified_readbacks'] += 1
        snapshot('256-comments-retained')
        for index, project in enumerate(projects):
            container = uid(300000 + index)
            write('container.create', project, container, 0, {'title': 'T06 shared Docs', 'visibility': 'shared'})
            for i in range(8):
                document = uid(400000 + index * 8 + i)
                for revision in range(5):
                    markdown = ('---\nid: ' + document + '\ntype: page\nstate: published\n---\n'
                        + '# T06 synthetic document ' + str(i) + '\n\nRevision ' + str(revision + 1)
                        + '. λ\n' + ('Bounded public fixture text.\n' * 32))
                    write('document.save', project, document, revision, {'container_id': container, 'markdown': markdown})
                    actual, response = read('document', project, document, container)
                    require(len(actual) == 1 and response['cursor'] == '' and actual[0]['resource_id'] == document
                        and actual[0]['resource_revision'] == str(revision + 1) and actual[0]['markdown'] == markdown)
                    report['verified_readbacks'] += 1
        snapshot('16-docs-four-edits-each')
        # List reads exercise the actual 20-row cursor boundary, after all writes.
        for index, project in enumerate(projects):
            first, a = read('work', project)
            require(len(first) == 20 and a['cursor'] != '')
            second, b = read('work', project, cursor=a['cursor'])
            require(len(second) == 12 and b['cursor'] == '' and a['generation'] == b['generation'])
            ids = [row['resource_id'] for row in first + second]
            require(len(set(ids)) == 32 and set(ids) == {uid(200000 + index * 32 + i) for i in range(32)})
            report['pages'].append({'project_id': project, 'rows': [20, 12], 'generation': a['generation']})
        require(report['accepted_writes'] == 404 and report['verified_readbacks'] == 208)
        report['latency'] = {kind: distribution([r['duration_ns'] for r in report['samples'] if r['kind'] == kind])
                             for kind in ('command', 'query')}
        report['latency']['document.save'] = distribution([r['duration_ns'] for r in report['samples']
                                                         if r['operation'] == 'document.save'])
        report['status'] = 'pass'
    except BaseException as error:
        report['error_class'] = type(error).__name__
        raise
    finally:
        report['elapsed_ns'] = clock() - start
        checkpoint(report)
    return report

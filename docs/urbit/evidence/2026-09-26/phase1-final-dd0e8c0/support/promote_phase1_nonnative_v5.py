#!/usr/bin/env python3
"""Unexecuted v5 nonnative promotion; prepared by /root, pending independent review. Run only after integrator source review.

Creates a NEW portable directory from the exact current142-test host capture,
its independent retained-byte audit and current independently reviewed capacity-diagnostic source.
No tests, ships, participants or native commands execute. The frozen73-row
readiness must still FAIL with all66 native obligations missing. The focused
native diagnostic is not a prerequisite or a supplied native proof here.
All v1/v2/v3/v4 evidence, earlier failures and historical guard bindings remain
unchanged. The selected142 tests overlap the full472 host tests.
"""
import argparse
import collections
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

ROOT = Path('/home/skilgore/stead-urbit')
HEAD = '3f0f3778997798f2ed208e206b46882a87340eb1'
IMPLEMENTATION_HEAD = 'a1d35b27d8ee482b1854c7352ebc6eecf96a2b08'
WORK = '.runtime/phase01-20260926'
OLD = 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v4'
DEST = 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v5'
REVIEW = 'docs/urbit/reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md'
FRESH = HOST_AUDIT = None  # Exact newly executed capture/audit supplied by the integrator.
REFRESH_REVIEW = '.runtime/phase01-20260926/nonnative-v5-refresh-plan.json'
LIFECYCLE_REVIEW = '.runtime/phase01-20260926/capacity-fix/source-review.json'
PINS = {'.runtime/phase01-20260926/nonnative-v5-refresh-plan.json': '0a17e1e86de473591e5844541ea7876f2582bd66492daff4a137656330017ad8', '.runtime/phase01-20260926/capacity-fix/source-review.json': '751de4e1e472e7869588e1b116f502250921019f7e1a30369621dbf7e8ca5d90', '.runtime/phase01-20260926/host-a1d35b2/result.json': '3e8187edaee1d11cae5abce4587bb71beece7c3993879aa05a2e9e21d5f2779b', '.runtime/phase01-20260926/host-a1d35b2/host.log': 'dbcfbb940261da5e3d9a7f82fbce2ec6d92e3198f2f7175a7cef58b5f7f582f3', 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v4/source-dispositions.json': 'f46141acdc9a6ef56f461d3424b4b695aaaea1a515a96bb913e0f95930f08b2d', 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v4/dispositions.json': '2ef0e381b9b0918a6e2ba9f46fb74887af6246fccba1f4e1a3e2cdb11c519c52', 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v4/historical-guard-continuity.json': 'c1a9e9ce34fc0f5b668f33dfd37a0de4e6269363e8951601f71c7d90f6a24b9f', 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v4/retention-index.json': 'a7a4855532e729003161890a262d91c92052dc7ee8229411b7dfc2772513facc', 'docs/urbit/reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md': 'ae0edda0a91d5b89b1cd070c8685de8d73dbc190093563c8cd2d4dba1d51b717', 'specs/urbit/v2/qualification-gate.json': 'f374349cc3ccd64993e3dade9a44e306854479c228b7f93d6559647006aee94c', 'scripts/urbit/build_phase1_evidence.py': 'c886c18fb25c0e381f346a6b7ec0387a784410acacfcac9ea72b6a5881708f7f', 'scripts/urbit/qualification_gate.py': 'ce0d8d0d87e9556940143943d7107099bfeb5c36eec6744342e555bfd292a6ab', '.runtime/phase01-20260926/promote_phase1_nonnative_v4.py': '8ec61b5d51220a0032e42fa47a77a7644e9cbc5562260918f1654b306a4e104c'}
MODULE_COUNTS = {'test_execution_policy': 6, 'test_runtime_guard_adversarial': 26,
    'test_harness_safety': 43, 'test_dev_flow': 32, 'test_delivery_cases': 10,
    'test_delivery_evidence_regressions': 11, 'test_delivery_suite': 14}
OUTPUTS = {'capture-script.py', 'launch.json', 'host-current.stdout.log',
    'host-current.stderr.log', 'before.json', 'test-events.jsonl',
    'selected-tests.json', 'worker.json'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, timeout=20)


def verify_repository():
    require(git('remote', 'get-url', 'origin').decode().strip() ==
            'https://github.com/ScottTpirate/stead-urbit.git', 'Wrong derivative fetch remote')
    require(git('remote', 'get-url', '--push', 'origin').decode().strip() ==
            'https://github.com/ScottTpirate/stead-urbit.git', 'Wrong derivative push remote')
    require(git('remote', 'get-url', '--push', 'upstream').decode().strip() ==
            'DISABLED_UPSTREAM_PUSH', 'Upstream push protection changed')
    require(git('rev-parse', 'HEAD').decode().strip() == HEAD, 'Frozen source commit changed')


def parts(name):
    require(isinstance(name, str) and name and '\x00' not in name, 'Invalid artifact path')
    value = PurePosixPath(name)
    require(not value.is_absolute() and value.as_posix() == name and
            all(x not in ('.', '..', '') for x in value.parts), 'Noncanonical artifact path')
    return value.parts


def directory(root_fd, path):
    fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
    try:
        for name in parts(path):
            nxt = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def prepare(root_fd):
    outputs, copied, observed = {}, [], {}

    def read(name):
        if name in outputs:
            return outputs[name]
        names = parts(name)
        fd = directory(root_fd, '/'.join(names[:-1])) if len(names) > 1 else os.dup(root_fd)
        try:
            source = os.open(names[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(source, 'rb') as stream:
                info = os.fstat(stream.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 4 * 1024 * 1024,
                        'Unbounded or special evidence input: ' + name)
                raw = stream.read(4 * 1024 * 1024 + 1)
                require(len(raw) == info.st_size, 'Evidence input changed while reading: ' + name)
        finally:
            os.close(fd)
        if name in PINS:
            require(sha(raw) == PINS[name], 'Pinned evidence changed: ' + name)
        if name in observed:
            require(sha(raw) == observed[name], 'Evidence changed during preparation: ' + name)
        observed[name] = sha(raw)
        return raw

    def ref(name, pointer=''):
        return {'path': name, 'sha256': sha(read(name)), 'pointer': pointer}

    def document(name, value):
        require(name not in outputs, 'Duplicate planned output')
        outputs[name] = encoded(value)
        return ref(name)

    def exact_copy(source, suffix):
        target = DEST + '/' + suffix
        require(target not in outputs, 'Duplicate copy target')
        outputs[target] = read(source)
        copied.append({'source': ref(source), 'retained': ref(target), 'bytes': len(outputs[target])})
        return target

    for name in PINS:
        read(name)
    tree = {}
    for row in git('ls-tree', '-r', '-z', HEAD).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            tree[name.decode()] = metadata.decode().split()

    def committed(name, digest):
        raw = read(name)
        metadata = tree.get(name, [])
        require(len(metadata) == 3 and metadata[0] in ('100644', '100755') and
                metadata[1] == 'blob' and sha(raw) == digest and
                hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == metadata[2],
                'Source differs from frozen committed bytes: ' + name)

    def capture(source, suffix, passing):
        raw = read(source + '/host-current.json')
        report = json.loads(raw)
        require(set(report['outputs']) == OUTPUTS, 'Unexpected host output inventory')
        for name, expected in report['outputs'].items():
            body = read(source + '/' + name)
            require(expected == {'path': name, 'bytes': len(body), 'sha256': sha(body)},
                    'Host output binding mismatch: ' + name)
            exact_copy(source + '/' + name, suffix + '/' + name)
        exact_copy(source + '/host-current.json', suffix + '/host-current.json')
        selected = json.loads(read(source + '/selected-tests.json'))
        ids = selected['test_ids']
        require(not selected['loader_errors'] and len(ids) == len(set(ids)) == 142 and
                collections.Counter(x.split('.')[0] for x in ids) == MODULE_COUNTS,
                'Wrong selected test identity inventory')
        require(report['test_loader']['modules'] == list(MODULE_COUNTS), 'Wrong selected modules')
        prior_ids = json.loads(read(OLD + '/host-current/selected-tests.json'))['test_ids']
        require(len(prior_ids) == len(set(prior_ids)) == 142 and prior_ids == ids,
                'Selected modules must retain the exact unchanged 142-test identity inventory')
        events = [json.loads(x) for x in read(source + '/test-events.jsonl').splitlines()]
        require(collections.Counter(x['event'] for x in events) == {'start': 142, 'finish': 142, 'subtest': 174},
                'Unexpected event inventory')
        starts = [x for x in events if x['event'] == 'start']
        ends = [{k: v for k, v in x.items() if k != 'event'} for x in events if x['event'] == 'finish']
        require([x['id'] for x in starts] == ids and [x['id'] for x in ends] == ids and ends == report['observed_tests'] and
                all(type(x['started_ns']) is int and type(x['finished_ns']) is int and
                    0 < x['started_ns'] < x['finished_ns'] for x in ends) and
                all(x['status'] == 'passed' for x in events if x['event'] == 'subtest'), 'Incomplete actual test events')
        require(all(report[key] == ids for key in ('expected_test_ids', 'started_test_ids', 'observed_test_ids')),
                'Test summary differs from recorded identities')
        failed = [x['id'] for x in ends if x['status'] != 'passed']
        wanted = [] if passing else ['test_harness_safety.DigestSafety.test_fresh_cache_prefix_executes_source_instead_of_old_host_bytecode']
        require(failed == wanted and report['status'] == ('passed' if passing else 'failed') and
                report['exit_code'] == (0 if passing else 1) and report['all_tests_passed'] is passing,
                'Host observed outcome mismatch')
        require(report['test_inventory_complete'] is True and report['tests_observed'] == 142 and
                report['native_execution'] is False and report['classification'] == 'host-mocked-execution' and
                report['executor'] == '/root' and report['reviewer'] == '/root', 'Wrong execution classification')
        require(all(report[key] == HEAD for key in ('base_head_before', 'base_head_after')) and
                all(report[key] is True for key in ('source_files_unchanged', 'committed_bytes_verified_before', 'committed_bytes_verified_after')) and
                report['source_uncommitted'] is False and not report['source_status_before'] and not report['source_status_after'],
                'Uncommitted or stale host source')
        files = report['source_files_before']
        worker = json.loads(read(source + '/worker.json'))
        expected_inventory = {name for name in tree if name == 'Makefile' or name.startswith(
            ('scripts/urbit/', 'native/', 'specs/urbit/', 'tests/urbit/'))}
        require(set(files) == expected_inventory and len(files) == 156 and files == report['source_files_after'] == worker['source_files_before'] ==
                worker['source_files_after'] and worker['observed_tests'] == ends, 'Worker source/result mismatch')
        before_record = json.loads(read(source + '/before.json'))
        require(before_record['source_files_before'] == files and before_record['base_head_before'] == HEAD
                and before_record['committed_bytes_verified_before'] is True, 'Initial checkpoint source mismatch')
        require(report['test_pycache_prefix'] is None and report['test_dont_write_bytecode'] is True
                and report['loader_pycache_prefix'].endswith('/unused-python-cache'), 'Cache-control environment mismatch')
        for name, digest in files.items():
            committed(name, digest)
        before, after = report['resources_before'], report['resources_after']
        require(before == after and before['cpu_max'] == '5000 10000' and before['affinity'] == [19]
                and len(before['pids']) == 1 and before['control_group'].endswith('/' + before['scope']),
                'Resource readback mismatch')
        done = report['scope_completion']
        require(not report['cancellation'] and done['ActiveState'] == 'inactive' and
                done['LoadState'] == 'not-found' and done['ControlGroup'] == '' and done['Result'] == 'success'
                and done['exit_code'] == 0 and done['stderr'] == '', 'Unverified host cleanup')
        launch = json.loads(read(source + '/launch.json'))
        require(launch['command'] == report['command'] and launch['unit'] == before['scope'] and
                launch['environment_overrides'] == report['environment_overrides'], 'Launch/report mismatch')
        stderr = read(source + '/host-current.stderr.log').decode()
        require(re.search(r'Ran 142 tests in [0-9.]+s\n\n' + ('OK' if passing else r'FAILED \(failures=1\)'), stderr),
                'Actual unittest log differs from recorded result')
        return report

    # The complete previous portable bundle remains immutable and referenced.
    previous_index = json.loads(read(OLD + '/retention-index.json'))
    previous_records = previous_index['generated_artifacts'] + [row['retained'] for row in previous_index['copies']]
    for item in previous_records:
        require(sha(read(item['path'])) == item['sha256'], 'Prior retained artifact changed')
    fresh = capture(FRESH, 'host-current', True)
    reviewed_path = exact_copy(REFRESH_REVIEW, 'source-refresh-review.json')
    audited_path = exact_copy(HOST_AUDIT, 'host-retained-audit.json')
    lifecycle_path = exact_copy(LIFECYCLE_REVIEW, 'capacity-source-review.json')
    refresh = json.loads(read(reviewed_path))
    audit = json.loads(read(audited_path))
    lifecycle_review = json.loads(read(lifecycle_path))
    require(refresh['protocol'] == 'stead.independent-nonnative-v5-refresh-plan/1'
            and refresh['status'] == 'source-review-complete-current-host-recapture-and-promotion-pending'
            and refresh['reviewer'] == '/root/independent_review' and refresh['observed_head'] == HEAD
            and refresh['implementation_source_commit'] == IMPLEMENTATION_HEAD
            and refresh['tests_executed'] is False and refresh['native_execution_performed'] is False
            and refresh['phase_qualification'] is False and not refresh['blocking_source_findings'],
            'Missing bounded independent source refresh review')
    require(audit['protocol'] == 'stead.nonnative-v5-retained-host-audit/1'
            and audit['status'] == 'reviewed-passed' and audit['reviewer'] == '/root/independent_review'
            and audit['source_commit'] == HEAD and audit['capture'] == ref(FRESH + '/host-current.json')
            and audit['source_review'] == ref(REFRESH_REVIEW)
            and audit['host_test_execution'] is False and audit['native_execution'] is False
            and audit['qualification_acceptance'] is False
            and audit['all_output_hashes_verified'] is True
            and audit['all156_source_files_match_current_committed_git_blobs'] is True
            and audit['unique_selected_started_finished_passed_ids'] == 142
            and audit['passed_subtests'] == 174 and audit['module_counts'] == MODULE_COUNTS,
            'Missing current independent exact host audit')
    require(refresh['prior_independent_delta_review']['sha256'] == ref(LIFECYCLE_REVIEW)['sha256']
            and lifecycle_review['reviewer'] == '/root/gall_schedule_review'
            and lifecycle_review['base_commit'] == refresh['base_v4_commit']
            and lifecycle_review['status'] == 'source-review-approved-for-focused-guarded-native-diagnostic'
            and lifecycle_review['blocking_findings'] == []
            and lifecycle_review['native_execution_performed'] is False
            and lifecycle_review['host_tests_launched_by_reviewer'] is False
            and lifecycle_review['qualifies_phase'] is False,
            'Independent capacity source review differs from exact current patch')
    reviewed = lifecycle_review['reviewed_source_files_sha256']
    require(sha(git('diff', refresh['base_v4_commit'], HEAD, '--', *sorted(reviewed)))
            == lifecycle_review['reviewed_patch_sha256'], 'Independent exact reviewed patch changed')
    for name, digest in reviewed.items():
        committed(name, digest)
    for label in ('metadata', 'log'):
        item = audit['full_host_check'][label]
        require(item['pointer'] == '' and item['sha256'] == sha(read(item['path'])), 'Full host record changed')
        exact_copy(item['path'], 'full-host/' + ('result.json' if label == 'metadata' else 'host.log'))
    full = json.loads(read(audit['full_host_check']['metadata']['path']))
    require(full['source_commit'] == IMPLEMENTATION_HEAD and full['exit'] == 0
            and full['committed_tested_inputs_unchanged'] is True
            and full['log_sha256'] == audit['full_host_check']['log']['sha256'], 'Full host binding mismatch')
    require(re.search(rb'Ran 472 tests in [0-9.]+s\n\nOK', read(audit['full_host_check']['log']['path'])),
            'Full host log inventory missing')
    require(not git('diff', IMPLEMENTATION_HEAD, HEAD, '--', 'Makefile', 'scripts/urbit', 'native', 'specs/urbit', 'tests/urbit'),
            'Full host execution source differs from current tested inputs')
    old_proofs = json.loads(read(OLD + '/source-dispositions.json'))
    guard_proof = copy.deepcopy(old_proofs['proofs']['guard-independent-source-review'])
    require(guard_proof['reviewer'] == '/root/independent_review', 'Original composite reviewer changed')
    current = refresh['guard_reviewed_source_files']
    changes = refresh['guard_changed_source_files']
    require(set(current) == set(guard_proof['reviewed_source_files']) and len(current) == 7
            and set(changes) == {'Makefile', 'scripts/urbit/harness.py', 'scripts/urbit/supervisor.py'}
            and {name for name in current if current[name] != guard_proof['reviewed_source_files'][name]} == set(changes),
            'Refresh must change exactly the three independently reviewed composite files')
    for name, digest in current.items():
        committed(name, digest)
        previous = sha(git('show', refresh['base_v4_commit'] + ':' + name))
        require(previous == guard_proof['reviewed_source_files'][name], 'Previous reviewed source differs')
        if name in changes:
            require(changes[name] == {'old': previous, 'new': digest}, 'Reviewed guard delta differs')
    guard_proof['reviewed_source_files'] = current
    guard_proof['findings_pre_v5_retain_their_original_review_bindings'] = True
    for finding in refresh['guard_delta_findings']:
        guard_proof['findings'].append({**finding, 'independent_reviewer': '/root/independent_review',
                                       'review': ref(reviewed_path, '/guard_delta_findings')})
    guard_proof['scope'] = ('Composite independent source review of exact common guard and four-fake lifecycle. '
        'Original common and prior changed-source findings retain their attributed source versions. '
        'The v5 fixed guarded diagnostic delta is reviewed by independent_review; its native lifetime '
        'and derivation delta is separately source-reviewed by gall_schedule_review. No native qualification.')
    guard_proof['independence']['v5_delta_author'] = '/root'
    guard_proof['independence']['v5_delta_independent_reviewer'] = '/root/independent_review'
    guard_proof['independence']['v5_capacity_source_review'] = ref(lifecycle_path)
    confirmed_path = DEST + '/guard-source-proof-confirmation.json'
    document(confirmed_path, {'protocol': 'stead.guard-source-composite-refresh/5',
        'source_commit': HEAD, 'recorded_by': '/root',
        'original_common_guard_reviewer': '/root/independent_review',
        'current_delta_reviewer': '/root/independent_review',
        'previous_composite_proof': ref(OLD + '/source-dispositions.json', '/proofs/guard-independent-source-review'),
        'previous_composite_confirmation': guard_proof['independence']['final_composite_confirmation'],
        'independently_confirmed_files': current, 'current_delta_review': ref(reviewed_path),
        'independent_lifecycle_source_review': ref(lifecycle_path),
        'scope': 'Three changed composite-source files plus unchanged prior common review, with original attribution. No new approval of historical native executions or focused native predicate.',
        'host_test_execution': False, 'native_execution': False, 'qualification_acceptance': False})
    host_confirmation_ref = document(DEST + '/host-audit-confirmation.json', {
        'protocol': 'stead.retained-host-audit/5', 'auditor': '/root/independent_review',
        'source_audit': ref(audited_path), 'host_capture': ref(DEST + '/host-current/host-current.json'),
        'original_capture': ref(FRESH + '/host-current.json'),
        'host_test_execution': False, 'native_execution': False,
        'scope': 'Portable exact capture reference for the actual independent retained-byte audit; no rerun or native qualification claim.'})

    # Fresh nonexistent import cache: -B alone would still admit existing pyc.
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(ROOT / '.runtime' / ('promotion-import-cache-' + os.urandom(16).hex()))
    require(not os.path.lexists(sys.pycache_prefix), 'Import cache unexpectedly exists')
    sys.path.insert(0, str(ROOT / 'scripts/urbit'))
    import build_phase1_evidence as B
    import qualification_gate as G
    expected = B.expected_inputs(ROOT)
    require(expected['source_commit'] == HEAD and expected['observed_source']['committed_bytes_verified'] is True and
            not expected['observed_source']['errors'], 'Current mounted inputs cannot be bound')
    base = {key: expected[key] for key in G.BASE_BINDINGS}
    proofs = copy.deepcopy(old_proofs)
    proofs['proofs']['guard-independent-source-review'] = guard_proof
    guard_proof['independence']['final_composite_confirmation'] = ref(confirmed_path)
    guard_proof['underlying_artifacts'] = [ref(OLD + '/source-dispositions.json', '/proofs/guard-independent-source-review'), ref(reviewed_path), ref(lifecycle_path), ref(confirmed_path)]
    passed_ids = {row['id']: i for i, row in enumerate(fresh['observed_tests'])}
    for identifier, proof in proofs['proofs'].items():
        for name, digest in proof.get('reviewed_source_files', {}).items():
            committed(name, digest)
            expected['source_files'][name] = digest  # same committed extra-source check as B.build()
        proof['bindings'] = {'guard_sha256': expected['guard_sha256']} if identifier == 'guard-negative-host-tests' else copy.deepcopy(base)
        proof['supersedes'] = ref(OLD + '/source-dispositions.json', '/proofs/' + identifier)
        if proof['kind'] == 'host_mocked':
            proof['tests_observed'] = 142
            proof['executor'] = '/root'
            proof['current_retained_evidence_audit'] = host_confirmation_ref
            proof['underlying_artifacts'] = [ref(DEST + '/host-current/' + name) for name in
                ('host-current.json', 'host-current.stderr.log', 'selected-tests.json', 'test-events.jsonl')]
            for assertion in proof['assertions']:
                require(assertion['observed_test_ids'] and set(assertion['observed_test_ids']) <= passed_ids.keys(),
                        'Independent assertion mapping lacks current passed tests')
                assertion['observed_test_records'] = [ref(DEST + '/host-current/host-current.json', '/observed_tests/' + str(passed_ids[name]))
                    for name in assertion['observed_test_ids']]
    proofs['proofs']['guard-negative-host-tests']['evidence_limit'] = (
        '142 actual root-executed host tests; thermal/systemd test responses are mocked. '
        'Python child, file, flock, cache and Unix socket operations are real host controls. The total '
        'includes authored offline-home lifecycle controls and overlaps the full472 host tests. It is not '
        'native execution or additive to previous runs. Original assertion mapping and the current '
        'independent retained-evidence audit retain their separate attribution.')
    proofs['status'] = 'bound-to-observed-committed-source'
    proofs['binding_observed_source_commit'] = HEAD
    proofs['promotion'] = {'prepared_by': '/root', 'original_review': ref(OLD + '/source-dispositions.json'),
        'scope': 'Mechanical exact-byte retention and current binding using the retained current source delta/host audit; original common reviewer attribution preserved.',
        'host_test_execution': False, 'native_execution': False, 'independent_review_performed': False,
        'host_audit_confirmation': host_confirmation_ref, 'composite_confirmation': ref(confirmed_path)}
    document(DEST + '/source-dispositions.json', proofs)
    index = copy.deepcopy(json.loads(read(OLD + '/dispositions.json')))
    for item in index['items']:
        if item['id'] in proofs['proofs']:
            item['artifact'] = ref(DEST + '/source-dispositions.json', '/proofs/' + item['id'])
            item['bindings'] = proofs['proofs'][item['id']]['bindings']
    continuity = copy.deepcopy(json.loads(read(OLD + '/historical-guard-continuity.json')))
    continuity['current_source_review'] = ref(DEST + '/source-dispositions.json', '/proofs/guard-independent-source-review')
    continuity['current_host_tests'] = ref(DEST + '/source-dispositions.json', '/proofs/guard-negative-host-tests')
    continuity['final_source_binding_pending'] = False
    continuity['binding_observed_source_commit'] = HEAD
    continuity['previous_review'] = ref(OLD + '/historical-guard-continuity.json')
    index['historical_guard_continuity'] = document(DEST + '/historical-guard-continuity.json', continuity)
    index['status'] = 'bound-nonnative-dispositions-only'
    index['scope'] = 'Exactly seven typed nonnative dispositions. Native qualification and final independent acceptance remain required.'
    document(DEST + '/dispositions.json', index)
    manifest = json.loads(read('specs/urbit/v2/qualification-gate.json'))
    bridge = G.validate_historical_guard_continuity(index, expected, read)
    readiness = G.evaluate(manifest, index, expected, read_artifact=read, _historical_guard_bindings=bridge)
    supplied = {item['id'] for item in index['items']}
    require(len(supplied) == 7 and not readiness['errors'] and readiness['status'] == 'failed' and
            readiness['native_required'] == 66 and readiness['native_passed'] == 0 and
            all(row['status'] == (G.DISPOSITION[row['kind']] if row['id'] in supplied else 'missing')
                for row in readiness['items']), 'Seven typed records are not admissible: ' + json.dumps(readiness))
    document(DEST + '/nonnative-readiness.json', readiness)
    document(DEST + '/source-bindings.json', expected)
    document(DEST + '/retention-index.json', {'protocol': 'stead.nonnative-evidence-retention/1',
        'source_commit': HEAD, 'prepared_by': '/root', 'copies': copied,
        'existing_reviews_unchanged': True, 'historical_reports_unchanged': True,
        'host_test_execution': False, 'native_execution': False, 'independent_acceptance_performed': False,
        'scope': 'New current142 capture/source-review/audit copies and seven typed bindings only; all v1/v2/v3/v4 captures, failed runs and historical guard artifacts remain unchanged. Native focused/fullcore/Gall qualification is separate.',
        'previous_retention_index': ref(OLD + '/retention-index.json'),
        'generated_artifacts': [ref(name) for name in sorted(outputs) if name not in {x['retained']['path'] for x in copied}]})
    # Recheck every observed source/evidence input before the first output write.
    for name in tuple(observed):
        read(name)
    verify_repository()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--promote', action='store_true', required=True,
                        help='explicitly create the new evidence directory after integrator review')
    parser.add_argument('--capture', required=True)
    parser.add_argument('--capture-sha256', required=True)
    parser.add_argument('--audit', required=True)
    parser.add_argument('--audit-sha256', required=True)
    args = parser.parse_args()
    global FRESH, HOST_AUDIT
    FRESH, HOST_AUDIT = args.capture, args.audit
    parts(FRESH)
    parts(HOST_AUDIT)
    require(FRESH.startswith(WORK + '/host-recapture-') and HOST_AUDIT == WORK + '/nonnative-v5-host-audit.json', 'Unexpected current execution/audit paths')
    require(all(re.fullmatch(r'[0-9a-f]{64}', value) for value in (args.capture_sha256, args.audit_sha256)), 'Exact capture/audit hashes required')
    PINS[FRESH + '/host-current.json'] = args.capture_sha256
    PINS[HOST_AUDIT] = args.audit_sha256
    verify_repository()
    root_fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    parent_fd = output_fd = None
    try:
        parent_fd = directory(root_fd, str(PurePosixPath(DEST).parent))
        name = PurePosixPath(DEST).name
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('Destination already exists; nothing will be overwritten')
        planned = prepare(root_fd)  # parent fd stays anchored throughout all reads
        os.mkdir(name, mode=0o755, dir_fd=parent_fd)
        output_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        for path, raw in sorted(planned.items()):
            relative = str(PurePosixPath(path).relative_to(DEST))
            components = parts(relative)
            fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output_fd)
            try:
                for component in components[:-1]:
                    try:
                        os.mkdir(component, mode=0o755, dir_fd=fd)
                    except FileExistsError:
                        pass
                    nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = nxt
                out = os.open(components[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd)
                with os.fdopen(out, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.fsync(fd)
            finally:
                os.close(fd)
        os.fsync(output_fd)
        os.fsync(parent_fd)
        print(json.dumps({'status': 'copied-and-bound-nonnative-only', 'directory': DEST,
            'files': len(planned), 'native_executed': False, 'qualification': 'not-complete',
            'dispositions_sha256': sha(planned[DEST + '/dispositions.json'])}, sort_keys=True))
    finally:
        for fd in (output_fd, parent_fd, root_fd):
            if fd is not None:
                os.close(fd)


if __name__ == '__main__':
    main()

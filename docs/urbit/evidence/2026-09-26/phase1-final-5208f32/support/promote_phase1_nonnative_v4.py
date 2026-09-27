#!/usr/bin/env python3
"""Unexecuted v4 nonnative promotion. Run only after integrator source review.

Creates a NEW portable directory from the exact current142-test host capture,
its independent retained-byte audit and current guarded-diagnostic source review.
No tests, ships, participants or native commands execute. The frozen73-row
readiness must still FAIL with all66 native obligations missing. The focused
native diagnostic is not a prerequisite or a supplied native proof here.
All v1/v2/v3 evidence, earlier failures and historical guard bindings remain
unchanged. The selected142 tests overlap the full470 host tests.
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
HEAD = '5208f3273426e8fe76dc8622ffe93ace93982e17'
WORK = '.runtime/phase01-20260926'
OLD = 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v3'
DEST = 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v4'
REVIEW = 'docs/urbit/reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md'
FRESH = '.runtime/phase01-20260926/host-recapture-20260926t204028z-b96bdc45'
REFRESH_REVIEW = '.runtime/phase01-20260926/nonnative-v4-source-review.json'
HOST_AUDIT = '.runtime/phase01-20260926/nonnative-v4-host-audit.json'
LIFECYCLE_REVIEW = '.runtime/phase01-20260926/delivery-lifecycle-fix-review.json'
PINS = {'.runtime/phase01-20260926/host-recapture-20260926t204028z-b96bdc45/host-current.json': '7a42fd5e031820b0c7a933147887d7dac71b2d3226f412b23f329e5167b53d8e',
 '.runtime/phase01-20260926/nonnative-v4-source-review.json': '9df4ca622f2b1f381b9533bd3a708c3dc062177fc030d8ab70dabc34d8ffb566',
 '.runtime/phase01-20260926/nonnative-v4-host-audit.json': 'c6621ddc37e6898fccfaca00e034e4487ead2880930c2b7e6710b8d83a09c920',
 '.runtime/phase01-20260926/delivery-lifecycle-fix-review.json': '0c3fd4c76fd96b4351be98b67334c2a8682c931020fef76b575f8688dab0a795',
 '.runtime/phase01-20260926/host-5208f32/result.json': '3e83f810a8fadfa8cf9ee7695061761d7be5ba09df88473887b99e205c82de79',
 '.runtime/phase01-20260926/host-5208f32/host.log': '8802873e4b153b33bd06ada7bc9b2c454da2fd0b2c0f630bb230e7ac8c4a802f',
 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v3/source-dispositions.json': '8e4e8dfce6dd58eb1a90bff1a44690796320c7a425854fedbd8300faa1f14703',
 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v3/dispositions.json': 'a4503dd9a76cb723aa5eb81168655a04e3da3665c37448fe7b924c614ef5dff6',
 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v3/historical-guard-continuity.json': 'dbb4535f8040fcfaa9e17730ee496252e8a15285b4d0ef9b582acc14192ff348',
 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v3/retention-index.json': '7984c453bbdaa60182f4e2d03b4fb2a356fa3657e6581ac05d7d7248e5625c8d',
 'docs/urbit/reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md': 'ae0edda0a91d5b89b1cd070c8685de8d73dbc190093563c8cd2d4dba1d51b717',
 'specs/urbit/v2/qualification-gate.json': 'f374349cc3ccd64993e3dade9a44e306854479c228b7f93d6559647006aee94c',
 'scripts/urbit/build_phase1_evidence.py': 'c886c18fb25c0e381f346a6b7ec0387a784410acacfcac9ea72b6a5881708f7f',
 'scripts/urbit/qualification_gate.py': 'ce0d8d0d87e9556940143943d7107099bfeb5c36eec6744342e555bfd292a6ab',
 '.runtime/phase01-20260926/promote_phase1_nonnative_v3.py': '8cf2c4ca55bae7ce499bdfaecf1aa6bc92b857c14bcc34be4c52b57ae823d7fb'}
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
        removed = {'test_delivery_suite.DeliveryScheduleHostTests.test_unavailable_home_does_not_green_adapter_programming_errors'}
        added = {'test_delivery_suite.DeliveryScheduleHostTests.' + name for name in (
            'test_only_specific_drained_native_timeout_is_expected_unavailability',
            'test_unavailable_home_rejects_transport_and_programming_failures',
            'test_unavailable_home_rejects_business_output_ack_and_unrelated_bails',
            'test_home_lifecycle_leaves_home_offline_after_transport_failure',
            'test_home_lifecycle_drains_before_restart_and_rejects_dead_sender')}
        require(len(prior_ids) == len(set(prior_ids)) == 138 and
                set(prior_ids) - set(ids) == removed and set(ids) - set(prior_ids) == added,
                '142 inventory must be prior138 minus one old predicate plus five exact new regressions')
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
    lifecycle_path = exact_copy(LIFECYCLE_REVIEW, 'delivery-lifecycle-source-review.json')
    refresh = json.loads(read(reviewed_path))
    audit = json.loads(read(audited_path))
    lifecycle_review = json.loads(read(lifecycle_path))
    require(refresh['protocol'] == 'stead.nonnative-v4-source-review/1'
            and refresh['status'] == 'source-review-complete-execution-refresh-pending'
            and refresh['reviewer'] == '/root/independent_review' and refresh['source_commit'] == HEAD
            and refresh['source_review_performed'] is True and refresh['host_test_execution'] is False
            and refresh['native_execution'] is False and refresh['qualification_acceptance'] is False,
            'Missing bounded independent source refresh review')
    require(audit['protocol'] == 'stead.nonnative-v4-retained-host-audit/1'
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
    require(refresh['independent_lifecycle_source_review'] == ref(LIFECYCLE_REVIEW)
            and lifecycle_review['reviewer'] == '/root/core_acceptance_review'
            and lifecycle_review['head_observed_at_review'] == HEAD
            and lifecycle_review['status'] == 'source-review-approved-for-focused-guarded-native-diagnostic'
            and lifecycle_review['blocking_findings'] == []
            and lifecycle_review['native_execution_performed'] is False
            and lifecycle_review['host_tests_launched_by_reviewer'] is False
            and lifecycle_review['qualifies_phase'] is False
            and lifecycle_review['reviewed_source_files_sha256'] == refresh['reviewed_changed_files'],
            'Independent lifecycle source review differs from exact current patch')
    for label in ('metadata', 'log'):
        item = audit['full_host_check'][label]
        require(item['pointer'] == '' and item['sha256'] == sha(read(item['path'])), 'Full host record changed')
        exact_copy(item['path'], 'full-host/' + ('result.json' if label == 'metadata' else 'host.log'))
    full = json.loads(read(audit['full_host_check']['metadata']['path']))
    require(full['source_commit'] == HEAD and full['exit'] == 0
            and full['committed_tested_inputs_unchanged'] is True
            and full['log_sha256'] == audit['full_host_check']['log']['sha256'], 'Full host binding mismatch')
    require(re.search(rb'Ran 470 tests in [0-9.]+s\n\nOK', read(audit['full_host_check']['log']['path'])),
            'Full host log inventory missing')
    old_proofs = json.loads(read(OLD + '/source-dispositions.json'))
    guard_proof = copy.deepcopy(old_proofs['proofs']['guard-independent-source-review'])
    require(guard_proof['reviewer'] == '/root/independent_review'
            and refresh['previous_source_files'] == guard_proof['reviewed_source_files'],
            'Original composite reviewer or source inventory changed')
    current = refresh['reviewed_source_files']
    require(set(current) == set(guard_proof['reviewed_source_files']) and len(current) == 7
            and {name for name in current if current[name] != guard_proof['reviewed_source_files'][name]}
                == {'Makefile', 'scripts/urbit/harness.py', 'scripts/urbit/supervisor.py'},
            'Refresh must change exactly the three reviewed composite files')
    require(refresh['previous_source_commit'] == '55475f0565ceb38db9eb5bc057962967398aa5da'
            and sha(git('diff', refresh['previous_source_commit'], HEAD, '--', *sorted(refresh['reviewed_changed_files'])))
                == refresh['reviewed_patch_sha256'], 'Reviewed complete source patch differs')
    for name, digest in refresh['all_reviewed_files'].items():
        committed(name, digest)
        require(sha(git('show', refresh['previous_source_commit'] + ':' + name))
                == refresh['previous_reviewed_files'][name], 'Previous reviewed source differs')
    guard_proof['reviewed_source_files'] = current
    guard_proof['findings_pre_v4_retain_their_original_review_bindings'] = True
    for finding in refresh['guard_delta_findings']:
        guard_proof['findings'].append({**finding, 'independent_reviewer': '/root/independent_review',
                                       'review': ref(reviewed_path, '/guard_delta_findings')})
    guard_proof['scope'] = ('Composite independent source review of exact common guard and four-fake lifecycle. '
        'Original common and prior changed-source findings retain their attributed source versions. '
        'The v4 fixed guarded diagnostic delta is reviewed by independent_review; its native lifetime '
        'and derivation delta is separately source-reviewed by core_acceptance_review. No native qualification.')
    guard_proof['independence']['v4_delta_author'] = '/root'
    guard_proof['independence']['v4_delta_independent_reviewer'] = '/root/independent_review'
    guard_proof['independence']['v4_lifecycle_source_review'] = ref(lifecycle_path)
    confirmed_path = DEST + '/guard-source-proof-confirmation.json'
    document(confirmed_path, {'protocol': 'stead.guard-source-composite-refresh/4',
        'source_commit': HEAD, 'recorded_by': '/root/independent_review',
        'original_common_guard_reviewer': '/root/independent_review',
        'current_delta_reviewer': '/root/independent_review',
        'previous_composite_proof': ref(OLD + '/source-dispositions.json', '/proofs/guard-independent-source-review'),
        'previous_composite_confirmation': guard_proof['independence']['final_composite_confirmation'],
        'independently_confirmed_files': current, 'current_delta_review': ref(reviewed_path),
        'independent_lifecycle_source_review': ref(lifecycle_path),
        'scope': 'Three changed composite-source files plus unchanged prior common review, with original attribution. No new approval of historical native executions or focused native predicate.',
        'host_test_execution': False, 'native_execution': False, 'qualification_acceptance': False})
    host_confirmation_ref = document(DEST + '/host-audit-confirmation.json', {
        'protocol': 'stead.retained-host-audit/4', 'auditor': '/root/independent_review',
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
        'includes authored offline-home lifecycle controls and overlaps the full470 host tests. It is not '
        'native execution or additive to previous runs. Original assertion mapping and the current '
        'independent retained-evidence audit retain their separate attribution.')
    proofs['status'] = 'bound-to-observed-committed-source'
    proofs['binding_observed_source_commit'] = HEAD
    proofs['promotion'] = {'prepared_by': '/root/independent_review', 'original_review': ref(OLD + '/source-dispositions.json'),
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
        'source_commit': HEAD, 'prepared_by': '/root/independent_review', 'copies': copied,
        'existing_reviews_unchanged': True, 'historical_reports_unchanged': True,
        'host_test_execution': False, 'native_execution': False, 'independent_acceptance_performed': False,
        'scope': 'New current142 capture/source-review/audit copies and seven typed bindings only; all v1/v2/v3 captures, failed runs and historical guard artifacts remain unchanged. Native focused/fullcore/Gall qualification is separate.',
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
    parser.parse_args()
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

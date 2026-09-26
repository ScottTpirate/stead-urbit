#!/usr/bin/env python3
"""Unexecuted promotion preparation. Run only after integrator review.

Copies exact retained host/confirmation bytes into a NEW evidence directory,
then binds the seven existing independent dispositions to the observed commit.
It runs no tests, ships, participant tools or native commands. The whole frozen
73-row check must still show 66 missing native obligations here. This v2 copy
uses only the pinned current 137-test capture and reviewed single harness delta.
It preserves the previous promotion script and complete portable bundle. Original
reviews, failed captures and historical 93/81 C/platform records are untouched.
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
HEAD = '0d877cff4319de8d437f0da58d4518535f758c36'
WORK = '.runtime/phase01-20260926'
OLD = 'docs/urbit/evidence/2026-09-26/phase1-nonnative'
DEST = 'docs/urbit/evidence/2026-09-26/phase1-nonnative-v2'
REVIEW = 'docs/urbit/reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md'
FRESH = '.runtime/phase01-20260926/host-recapture-20260926t181203z-2193e0df'
REFRESH_REVIEW = '.runtime/phase01-20260926/nonnative-v2-refresh-review.json'
EDITOR_HANDOFF = '.runtime/workflow-v2-proposal/SOURCE_REVIEW_HANDOFF.json'
PINS = {'.runtime/phase01-20260926/host-recapture-20260926t181203z-2193e0df/host-current.json': '57d402c3bb5b481d892bd1a336abd186bd3490c80cc27f0dce37c25f9937161c', '.runtime/phase01-20260926/nonnative-v2-refresh-review.json': '3d4c33fd59737a3d12b1838ca62c3843ab52c09d60f4294de6d51ef0932260cc', '.runtime/workflow-v2-proposal/SOURCE_REVIEW_HANDOFF.json': '5e69f7067c4953300b2ee6f9ee25826fff2f3b3eed4849127225fc6672ed2b7c', 'docs/urbit/evidence/2026-09-26/phase1-nonnative/source-dispositions.json': '87a2c38cb7288119c6b542d225e2e1cc25bb35798bb8592666f30c8aabbcdf2f', 'docs/urbit/evidence/2026-09-26/phase1-nonnative/dispositions.json': 'f0873e943303326ef350559c8554e832fd6bec7a4e444c790f4c4f19b6ff9251', 'docs/urbit/evidence/2026-09-26/phase1-nonnative/historical-guard-continuity.json': 'aa20f96d3a7c1aa6d313dd97397a51dfef99fcd26a1af4a6dd23fb21e96541c0', 'docs/urbit/evidence/2026-09-26/phase1-nonnative/retention-index.json': '770c81d9ee8a8213f810af9c9d3f5fe8ea6e5be9ad1d7449bb7aed4ceddb1382', 'docs/urbit/reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md': 'ae0edda0a91d5b89b1cd070c8685de8d73dbc190093563c8cd2d4dba1d51b717', 'specs/urbit/v2/qualification-gate.json': 'f374349cc3ccd64993e3dade9a44e306854479c228b7f93d6559647006aee94c', 'scripts/urbit/build_phase1_evidence.py': '1eb8f8dad1199ce9f3cf6667ef3f26e20774ab3eb50d54590e5b0b30e4b8fb63', 'scripts/urbit/qualification_gate.py': 'ce0d8d0d87e9556940143943d7107099bfeb5c36eec6744342e555bfd292a6ab', '.runtime/phase01-20260926/promote_phase1_nonnative.py': 'fe5d786d07f7e50ec8f381b29ba8533c7d942382eda28bd84508387bf749496a'}
MODULE_COUNTS = {'test_execution_policy': 6, 'test_runtime_guard_adversarial': 26,
    'test_harness_safety': 43, 'test_dev_flow': 31, 'test_delivery_cases': 10,
    'test_delivery_evidence_regressions': 11, 'test_delivery_suite': 10}
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
                require(stat.S_ISREG(info.st_mode) and info.st_size <= 4 * 1024 * 1024,
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
        require(not selected['loader_errors'] and len(ids) == len(set(ids)) == 137 and
                collections.Counter(x.split('.')[0] for x in ids) == MODULE_COUNTS,
                'Wrong selected test identity inventory')
        require(report['test_loader']['modules'] == list(MODULE_COUNTS), 'Wrong selected modules')
        events = [json.loads(x) for x in read(source + '/test-events.jsonl').splitlines()]
        require(collections.Counter(x['event'] for x in events) == {'start': 137, 'finish': 137, 'subtest': 162},
                'Unexpected event inventory')
        starts = [x for x in events if x['event'] == 'start']
        ends = [{k: v for k, v in x.items() if k != 'event'} for x in events if x['event'] == 'finish']
        require([x['id'] for x in starts] == ids and ends == report['observed_tests'] and
                all(x['started_ns'] < x['finished_ns'] for x in ends) and
                all(x['status'] == 'passed' for x in events if x['event'] == 'subtest'), 'Incomplete actual test events')
        require(all(report[key] == ids for key in ('expected_test_ids', 'started_test_ids', 'observed_test_ids')),
                'Test summary differs from recorded identities')
        failed = [x['id'] for x in ends if x['status'] != 'passed']
        wanted = [] if passing else ['test_harness_safety.DigestSafety.test_fresh_cache_prefix_executes_source_instead_of_old_host_bytecode']
        require(failed == wanted and report['status'] == ('passed' if passing else 'failed') and
                report['exit_code'] == (0 if passing else 1) and report['all_tests_passed'] is passing,
                'Host observed outcome mismatch')
        require(report['test_inventory_complete'] is True and report['tests_observed'] == 137 and
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
        require(re.search(r'Ran 137 tests in [0-9.]+s\n\n' + ('OK' if passing else r'FAILED \(failures=1\)'), stderr),
                'Actual unittest log differs from recorded result')
        return report

    # The complete previous portable bundle remains immutable and referenced.
    previous_index = json.loads(read(OLD + '/retention-index.json'))
    previous_records = previous_index['generated_artifacts'] + [row['retained'] for row in previous_index['copies']]
    for item in previous_records:
        require(sha(read(item['path'])) == item['sha256'], 'Prior retained artifact changed')
    fresh = capture(FRESH, 'host-current', True)
    reviewed_path = exact_copy(REFRESH_REVIEW, 'refresh-review.json')
    handoff_path = exact_copy(EDITOR_HANDOFF, 'editor-source-review-handoff.json')
    refresh, handoff = json.loads(read(reviewed_path)), json.loads(read(handoff_path))
    require(refresh['reviewer'] == '/root/gall_schedule_review' and refresh['source_commit'] == HEAD
            and refresh['source_review_performed'] is True and refresh['host_test_execution'] is False
            and refresh['native_execution'] is False and refresh['qualification_acceptance'] is False,
            'Missing bounded independent refresh review')
    require(refresh['host_capture_audit']['capture'] == ref(FRESH + '/host-current.json')
            and refresh['editor_source_handoff'] == ref(EDITOR_HANDOFF), 'Wrong reviewed capture/handoff')
    old_proofs = json.loads(read(OLD + '/source-dispositions.json'))
    guard_proof = copy.deepcopy(old_proofs['proofs']['guard-independent-source-review'])
    require(guard_proof['reviewer'] == '/root/independent_review'
            and refresh['previous_source_files'] == guard_proof['reviewed_source_files'],
            'Original composite reviewer or source inventory changed')
    current = refresh['reviewed_source_files']
    require(set(current) == set(guard_proof['reviewed_source_files']) and len(current) == 7
            and {name for name in current if current[name] != guard_proof['reviewed_source_files'][name]}
                == {'scripts/urbit/harness.py'}, 'Refresh must change exactly one reviewed source')
    before = git('show', refresh['previous_source_commit'] + ':scripts/urbit/harness.py')
    oldline = b"    workflow = ROOT / '.runtime/workflow-evaluation'\n"
    newline = b"    workflow = ROOT / '.runtime/workflow-evaluation-v2'\n"
    require(sha(before) == guard_proof['reviewed_source_files']['scripts/urbit/harness.py']
            and before.count(oldline) == 1 and before.replace(oldline, newline, 1) == read('scripts/urbit/harness.py'),
            'Harness refresh exceeds the independently reviewed single replacement')
    require(handoff['independent_reviewer'] == '/root/editor_tool_review'
            and handoff['recorded_by'] == '/root/independent_review'
            and handoff['harness_sha256'] == current['scripts/urbit/harness.py']
            and handoff['adapter_sha256'] == sha(read('scripts/urbit/skill_evaluation_support.py')),
            'Editor confirmation does not bind current harness/adapter')
    for name, digest in current.items():
        committed(name, digest)
    guard_proof['reviewed_source_files'] = current
    guard_proof['findings'].append({'source': 'scripts/urbit/harness.py',
        'claim': 'The sole v2 guard-source delta selects .runtime/workflow-evaluation-v2 with unchanged ownership/private/no-symlink checks and read-only /workflow mount.',
        'independent_reviewer': '/root/gall_schedule_review', 'review': ref(reviewed_path, '/harness_delta')})
    guard_proof['scope'] = ('Composite independent source review of exact common guard and four-fake lifecycle. '
        'Original common and prior changed-source reviews retain their attribution; the single v2 workflow-root '
        'delta is independently reviewed by gall_schedule_review and editor_tool_review. No native qualification.')
    guard_proof['independence']['v2_delta_independent_reviewer'] = '/root/gall_schedule_review'
    guard_proof['independence']['v2_editor_confirmation'] = ref(handoff_path)
    confirmed_path = DEST + '/guard-source-proof-confirmation.json'
    document(confirmed_path, {'protocol': 'stead.guard-source-composite-refresh/2',
        'source_commit': HEAD, 'recorded_by': '/root/gall_schedule_review',
        'original_common_guard_reviewer': '/root/independent_review',
        'current_delta_reviewer': '/root/gall_schedule_review',
        'previous_composite_proof': ref(OLD + '/source-dispositions.json', '/proofs/guard-independent-source-review'),
        'previous_composite_confirmation': guard_proof['independence']['final_composite_confirmation'],
        'independently_confirmed_files': current, 'current_delta_review': ref(reviewed_path),
        'editor_source_review_handoff': ref(handoff_path),
        'scope': 'Exact single changed-source delta plus unchanged prior common review; no impersonation of the original reviewer or new approval of historical executions.',
        'host_test_execution': False, 'native_execution': False, 'qualification_acceptance': False})
    host_confirmation_ref = document(DEST + '/host-audit-confirmation.json', {
        'protocol': 'stead.retained-host-audit/2', 'auditor': '/root/gall_schedule_review',
        'source_audit': ref(reviewed_path, '/host_capture_audit'),
        'host_capture': ref(DEST + '/host-current/host-current.json'),
        'original_capture': ref(FRESH + '/host-current.json'),
        'host_test_execution': False, 'native_execution': False,
        'scope': 'Portable exact capture reference for the attributed independent retained-byte audit; no rerun or qualification claim.'})

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
    guard_proof['underlying_artifacts'] = [ref(OLD + '/source-dispositions.json', '/proofs/guard-independent-source-review'), ref(reviewed_path), ref(handoff_path), ref(confirmed_path)]
    passed_ids = {row['id']: i for i, row in enumerate(fresh['observed_tests'])}
    for identifier, proof in proofs['proofs'].items():
        for name, digest in proof.get('reviewed_source_files', {}).items():
            committed(name, digest)
            expected['source_files'][name] = digest  # same committed extra-source check as B.build()
        proof['bindings'] = {'guard_sha256': expected['guard_sha256']} if identifier == 'guard-negative-host-tests' else copy.deepcopy(base)
        proof['supersedes'] = ref(OLD + '/source-dispositions.json', '/proofs/' + identifier)
        if proof['kind'] == 'host_mocked':
            proof['tests_observed'] = 137
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
        '137 actual root-executed host tests; thermal/systemd test responses are mocked. '
        'Python child, file, flock and cache operations are real host controls. The total '
        'includes delivery tests and is not additive to previous runs. Original assertion '
        'mapping and independent retained-evidence audit are separately attributed.')
    proofs['status'] = 'bound-to-observed-committed-source'
    proofs['binding_observed_source_commit'] = HEAD
    proofs['promotion'] = {'prepared_by': '/root/gall_schedule_review', 'original_review': ref(OLD + '/source-dispositions.json'),
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
        'source_commit': HEAD, 'prepared_by': '/root/gall_schedule_review', 'copies': copied,
        'existing_reviews_unchanged': True, 'historical_reports_unchanged': True,
        'host_test_execution': False, 'native_execution': False, 'independent_acceptance_performed': False,
        'scope': 'New current capture/review copies and typed bindings only; all prior captures, failed cache control and historical guard artifacts remain unchanged.',
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

#!/usr/bin/env python3
"""Unexecuted promotion preparation. Run only after integrator review.

Copies exact retained host/confirmation bytes into a NEW evidence directory,
then binds the seven existing independent dispositions to the observed commit.
It runs no tests, ships, participant tools or native commands. The whole frozen
73-row check must still show 66 missing native obligations here. Original
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
HEAD = '8334a75cad4c2b063147e7e3352cdf76da0d5893'
WORK = '.runtime/phase01-20260926'
OLD = 'docs/urbit/evidence/2026-09-25/phase1-nonnative'
DEST = 'docs/urbit/evidence/2026-09-26/phase1-nonnative'
REVIEW = 'docs/urbit/reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md'
FRESH = WORK + '/host-recapture-20260926t170802z-2065cd1f'
FAILED = WORK + '/host-recapture-20260926t165951z-c080d84a'
CACHE = 'unused-python-cache/tmp/stead-source-cache-nzzv_yr_/reviewer_fixture.cpython-314.pyc'
PINS = {
    FRESH + '/host-current.json': 'a6c3ce3878da93544609f71dfe847a6751395cd938c40b9a26993d35008e40c8',
    FAILED + '/host-current.json': '7e64d81ca2f7bdfd555282499d24be457ff68c0ea37e5fee7a3ed88869d7947a',
    FAILED + '/' + CACHE: '6f52c60b0af4ac463862ca3f7b62862a5f143f1957fc7074ed7b101017144ab6',
    WORK + '/guard-source-proof-proposed.json': 'dcd7b1634d0817f875448cc84e4414c3c3ebdc04dc2ef646f3c067689250e3f9',
    WORK + '/guard-source-proof-confirmation.json': '523292f26db197a0b48e6fa4f316308f95b51ec6f646cd4269325156fea2fefe',
    OLD + '/source-dispositions-pending.json': 'dd18bf2e8258c6a5f66a5e12f0279d70472cd33e670122a469ceeb7208772fe9',
    OLD + '/dispositions-pending.json': '31c91e8873d2bcb2e038f08e3057ac940edb5878558f8fede0e395123840c6e3',
    OLD + '/historical-guard-continuity-pending.json': 'b66548aaec507b4f9b03b41075033d664c4486e4ebf67cf2b8231af5c4786f88',
    REVIEW: 'ae0edda0a91d5b89b1cd070c8685de8d73dbc190093563c8cd2d4dba1d51b717',
    'specs/urbit/v2/qualification-gate.json': 'f374349cc3ccd64993e3dade9a44e306854479c228b7f93d6559647006aee94c',
    'scripts/urbit/build_phase1_evidence.py': '1eb8f8dad1199ce9f3cf6667ef3f26e20774ab3eb50d54590e5b0b30e4b8fb63',
    'scripts/urbit/qualification_gate.py': 'ce0d8d0d87e9556940143943d7107099bfeb5c36eec6744342e555bfd292a6ab',
}
MODULE_COUNTS = {'test_execution_policy': 6, 'test_runtime_guard_adversarial': 26,
    'test_harness_safety': 43, 'test_dev_flow': 31, 'test_delivery_cases': 10,
    'test_delivery_evidence_regressions': 11, 'test_delivery_suite': 10}
OUTPUTS = {'capture-script.py', 'launch.json', 'host-current.stdout.log',
    'host-current.stderr.log', 'before.json', 'test-events.jsonl',
    'selected-tests.json', 'worker.json'}
HOST_CONFIRMATION = (
    'Host artifact audit complete, no new execution: host-current '
    'a6c3ce3878da93544609f71dfe847a6751395cd938c40b9a26993d35008e40c8 '
    'has all8 output hashes valid,137 unique expected/started/finished/passed IDs '
    'and162 passed subtests; seven modules6/26/43/31/10/11/10. All155 captured '
    'source SHA256s match current worktree and actual8334a75 Git blob IDs. '
    'CPU5000/10000 +affinity19 before/after, same sole PID, exit0, unloaded clean '
    'scope; actual unittest2.910s, worker3.631861s, outer4.340288s. All old15 '
    'guard assertion test IDs and2 delivery IDs occur in current passes. '
    'Receipt/no-effect/delivery source hashes unchanged; composite proposed7 '
    'hashes current and editor-confirmed. Historical guard old7166/currentda16 '
    'exact627B nine-line permitted delta verified, old two historical proof '
    'hashes/bindings unchanged. Promotion needs source proof composite '
    'substitution,137 root-executed host refs/counts, final common bindings, then '
    'bottom-up continuity/index refs. Preserve old127 and failed137 artifacts, '
    'no new heat/platform claim. I am returning now to release slot.')


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
        require(len(files) == 155 and files == report['source_files_after'] == worker['source_files_before'] ==
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

    fresh = capture(FRESH, 'host-current', True)
    capture(FAILED, 'host-failed-cache-control', False)
    exact_copy(FAILED + '/' + CACHE, 'host-failed-cache-control/' + CACHE + '.bin')
    proposed_path = exact_copy(WORK + '/guard-source-proof-proposed.json', 'guard-source-proof-proposed.json')
    confirmed_path = exact_copy(WORK + '/guard-source-proof-confirmation.json', 'guard-source-proof-confirmation.json')
    proposal, confirmation = json.loads(read(proposed_path)), json.loads(read(confirmed_path))
    require(confirmation['proposal'] == {k: v for k, v in ref(WORK + '/guard-source-proof-proposed.json').items() if k != 'pointer'} and
            confirmation['confirmation_from'] == '/root/editor_tool_review' and confirmation['recorded_by'] == '/root/independent_review',
            'Missing exact independent composite confirmation')
    guard_proof = copy.deepcopy(proposal['proposed_proof'])
    require(guard_proof['reviewer'] == '/root/independent_review' and guard_proof['reviewed_source_files'] ==
            confirmation['independently_confirmed_files'], 'Composite source inventory mismatch')
    for prior in confirmation['independently_confirmed_prior_records']:
        require(sha(read(prior['path'])) == prior['sha256'], 'Original independent review changed')
    host_confirmation_ref = document(DEST + '/host-audit-confirmation.json', {
        'protocol': 'stead.retained-collaboration-confirmation/1', 'confirmation_from': '/root/independent_review',
        'recorded_by': '/root/gall_schedule_review', 'confirmation_delivery': 'Actual collaboration message received; recorder did not impersonate reviewer or execute tests.',
        'confirmation_verbatim': HOST_CONFIRMATION, 'host_capture': ref(DEST + '/host-current/host-current.json'),
        'native_execution': False, 'host_test_execution': False,
        'scope': 'Retained-byte audit and attribution only; not independent native or phase acceptance.'})

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
    old_proofs = json.loads(read(OLD + '/source-dispositions-pending.json'))
    proofs = copy.deepcopy(old_proofs)
    proofs['proofs']['guard-independent-source-review'] = guard_proof
    guard_proof['independence']['final_composite_confirmation'] = ref(confirmed_path)
    guard_proof['underlying_artifacts'] = [ref(proposed_path), ref(confirmed_path)]
    passed_ids = {row['id']: i for i, row in enumerate(fresh['observed_tests'])}
    for identifier, proof in proofs['proofs'].items():
        for name, digest in proof.get('reviewed_source_files', {}).items():
            committed(name, digest)
            expected['source_files'][name] = digest  # same committed extra-source check as B.build()
        proof['bindings'] = {'guard_sha256': expected['guard_sha256']} if identifier == 'guard-negative-host-tests' else copy.deepcopy(base)
        proof['supersedes'] = ref(OLD + '/source-dispositions-pending.json', '/proofs/' + identifier)
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
    proofs['promotion'] = {'prepared_by': '/root/gall_schedule_review', 'original_review': ref(OLD + '/source-dispositions-pending.json'),
        'scope': 'Mechanical exact-byte retention and verified common binding; original reviewer attribution preserved.',
        'host_test_execution': False, 'native_execution': False, 'independent_review_performed': False,
        'host_audit_confirmation': host_confirmation_ref, 'composite_confirmation': ref(confirmed_path)}
    document(DEST + '/source-dispositions.json', proofs)
    index = copy.deepcopy(json.loads(read(OLD + '/dispositions-pending.json')))
    for item in index['items']:
        if item['id'] in proofs['proofs']:
            item['artifact'] = ref(DEST + '/source-dispositions.json', '/proofs/' + item['id'])
            item['bindings'] = proofs['proofs'][item['id']]['bindings']
    continuity = copy.deepcopy(json.loads(read(OLD + '/historical-guard-continuity-pending.json')))
    continuity['current_source_review'] = ref(DEST + '/source-dispositions.json', '/proofs/guard-independent-source-review')
    continuity['current_host_tests'] = ref(DEST + '/source-dispositions.json', '/proofs/guard-negative-host-tests')
    continuity['final_source_binding_pending'] = False
    continuity['binding_observed_source_commit'] = HEAD
    continuity['previous_review'] = ref(OLD + '/historical-guard-continuity-pending.json')
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
        'scope': 'New exact copies and mechanical typed bindings; retained failed cache control remains failed.',
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

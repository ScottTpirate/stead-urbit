"""Fail-closed current-phase evidence reconciliation; never starts a runtime.

Historical skipped/failed reports are read-only input. Passing a host validator
does not create native evidence. Each claim points to exact artifact bytes and a
typed result within them; source and N/A dispositions stay separately labeled.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import gzip
import io
import json
from pathlib import Path
import re

HEX = re.compile(r'[0-9a-f]{64}')
BASE_BINDINGS = ('source_commit', 'native_tree_sha256', 'runtime_lock_sha256',
                 'corpus_sha256', 'contract_freeze_sha256', 'runner_sha256')
NATIVE_BINDINGS = BASE_BINDINGS + ('installed_clay_tree_sha256', 'loaded_closure_sha256', 'observer_sha256')
DISPOSITION = {'native': 'passed', 'source_review': 'reviewed', 'not_applicable': 'not_applicable',
               'host_mocked': 'passed', 'real_host': 'passed', 'real_platform_mocked_sensors': 'passed'}
DEFERRED = {
    'scoped-private-metadata': ('project-views-never-include-other-owner-private-metadata',
                              'projection-timing-and-all-metadata-nondisclosure'),
    'no-effect-subsystem': ('restart-preserves-content-policy-objects-and-journal',
                            'no-external-effects-replayed'),
    'receipt-lookup-order': ('downgraded-reader-cannot-recover-write-receipt', 'source-ordering-property')}
DELIVERY = ('known-mark-and-held-outsider', 'wrong-sender-and-binding',
            'missing-channel-and-wrong-digest', 'leave-and-fresh-retry',
            'lazy-expiry-and-same-path-retirement', 'pending-quotas',
            'home-unavailable', 'ended-leave-attempt')
RECIPES = {'v1-private-identity-and-sequence-reproduction', 'v1-exhaustion-migration-security-reserve',
           'projects', 'work_items', 'grants', 'documents', 'history', 'object_bytes'}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def passed_checks(rows, key='passed'):
    return isinstance(rows, list) and bool(rows) and all(isinstance(row, dict)
        and isinstance(row.get('name'), str) and bool(row['name'])
        and (row.get(key) is True if key == 'passed' else row.get(key) == 'passed') for row in rows)


def deferred_execution(report):
    """Admit only fully executed stages and the three frozen typed deferrals.

    This is a runtime completion boundary, never an acceptance disposition.
    It neither changes raw checks nor approves the later independent proofs.
    """
    require(not report.get('error') and passed_checks(report.get('checks')), 'Failed or empty native stage checks')
    required_checks = {'loaded-supervisor-source-matches', 'loaded-core-runner-source-matches',
        'native-evaluator-failure-and-large-frame-controls', 'all-qa-native-cases-executed-without-failure',
        'native-on-save-on-load-roundtrip', 'two-principal-concurrent-cas-one-winner',
        'delivery-has-no-observed-failure', 'native-capacity-and-predecessor-qualification'}
    require(required_checks <= {r['name'] for r in report['checks']}, 'Missing executed native stage')
    qa = report['qa']
    specs = Path('/specs') if Path(__file__).parent == Path('/code') else Path(__file__).resolve().parents[2] / 'specs/urbit'
    corpus = json.loads((specs / 'fixtures/native-cases-v2.json').read_bytes())
    cases = list(corpus['ordered_cases'])
    for key in ('real_expiry_continuation', 'source_review_continuation', 'separate_project_journal_lane', 'scoped_privacy_lane'):
        cases += corpus[key]['cases']
    require(qa.get('status') == 'incomplete' and qa.get('classification') == 'local-real-native-fake-ships',
            'Wrong native QA completion classification')
    require([r['name'] for r in qa['cases']] == [r['name'] for r in cases], 'Missing or reordered native cases')
    expected = {(case, name, 'Required typed current evidence missing: ' + identifier)
                for identifier, (case, name) in DEFERRED.items()}
    skips = [r for r in qa['checks'] if r.get('status') != 'passed']
    require(len(skips) == 3 and all(r.get('status') == 'skipped' for r in skips)
            and {(r.get('case'), r.get('name'), r.get('reason')) for r in skips} == expected,
            'Unexpected missing or rewritten QA disposition')
    require(qa['checks'] == [check for case in qa['cases'] for check in case['checks']],
            'QA aggregate differs from retained case checks')
    for case in qa['cases']:
        wanted = 'incomplete' if case['name'] in {value[0] for value in DEFERRED.values()} else 'passed'
        require(case.get('status') == wanted and bool(case['checks']), 'Unexecuted or failed QA case')
    require(qa.get('case_counts') == {'passed': 145, 'incomplete': 3}, 'Native case counts differ')
    delivery = report['delivery']
    require(delivery.get('classification') == 'real-native-fake-ships'
            and delivery.get('status') == 'incomplete' and bool(delivery.get('calls')),
            'Delivery runtime did not reach its single known deferred schedule')
    require([r['name'] for r in delivery['cases']] == list(DELIVERY), 'Missing native delivery case')
    for row in delivery['cases']:
        require(passed_checks(row.get('assertions'), 'status'), 'Failed or empty delivery assertions')
        if row['name'] == 'ended-leave-attempt':
            require(row.get('status') == 'incomplete' and row.get('missing') == [
                'Actual delayed old native leave injection at home remains unavailable; pinned Gall source review is a distinct proof.'],
                'Unrecognized old-leave deferral')
        else:
            require(row.get('status') == 'passed' and not row.get('missing'), 'Additional incomplete delivery case')
    capacity = report['qualification']
    require(capacity.get('status') == 'passed' and capacity.get('native_qualified') is True
            and set(capacity['recipes']) == RECIPES and all(r.get('status') == 'executed' for r in capacity['recipes'].values())
            and passed_checks(capacity.get('checks')) and bool(capacity.get('calls')) and bool(capacity.get('batches')),
            'Capacity or predecessor native execution incomplete')
    controls = report['evaluator_controls']
    require(controls.get('status') == 'passed' and controls.get('invalid_input', {}).get('encoder_rejected') is True
            and controls.get('large_frame_bytes', 0) > 65536, 'Missing actual evaluator failure/frame controls')
    require(len(report.get('concurrent_submissions', [])) == 2 and bool(report.get('commands'))
            and report.get('supported_predecessor_versions') == [1], 'Missing concurrency, commands or predecessor lane')
    return list(DEFERRED)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate evidence JSON key')
        result[key] = value
    return result


def pointer(value, path):
    if path == '':
        return value
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('JSON pointer must be explicit')
    for encoded in path[1:].split('/'):
        token = encoded.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('Noncanonical array pointer')
            value = value[int(token)]
        else:
            value = value[token]
    return value


def artifact_reader(root):
    root = Path(root).resolve(strict=True)

    def read(path):
        if not isinstance(path, str) or Path(path).is_absolute():
            raise ValueError('Evidence artifact must be repository-relative')
        candidate = (root / path).resolve(strict=True)
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError('Evidence artifact escapes repository or is not a file')
        if candidate.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('Evidence artifact exceeds bounded input size')
        return candidate.read_bytes()
    return read


def evaluate(manifest, evidence, expected_bindings, *, read_artifact=None):
    """Return failed for missing/stale/mock-as-native/zero-assertion evidence.

    evidence is a list (or {'items': list}) with id/kind/status/bindings/artifact.
    artifact is {path,sha256,pointer}; its pointed result repeats kind/status and
    has explicit assertions [{name,status}], plus nonempty native records for a
    native claim. read_artifact(path)->bytes must read actual retained evidence.
    Source/N-A results also name their independent reviewer and exact scope.
    """
    required = manifest.get('required', [])
    items = evidence.get('items', []) if isinstance(evidence, dict) else evidence
    report = {'protocol': 'stead.qualification-gate/2', 'status': 'failed',
              'test_owner': '/root/qa_review', 'items': [],
              'historical_skips': manifest.get('historical_skips', []),
              'historical_reports_unchanged': True,
              'scope': manifest.get('scope'), 'errors': []}
    if not isinstance(required, list) or not required or not isinstance(items, list):
        report['errors'].append('Nonempty required manifest and explicit evidence list required')
        return report
    names = [item.get('id') for item in required if isinstance(item, dict)]
    supplied_names = [item.get('id') for item in items if isinstance(item, dict)]
    if len(names) != len(required) or len(set(names)) != len(names) or any(not isinstance(n, str) or not n for n in names):
        report['errors'].append('Duplicate, empty or malformed required identity')
        return report
    if len(supplied_names) != len(items) or len(set(supplied_names)) != len(supplied_names):
        report['errors'].append('Duplicate or malformed supplied evidence identity')
        return report
    extra = set(supplied_names) - set(names)
    if extra:
        report['errors'].append('Unknown evidence identities: ' + ', '.join(sorted(extra)))
    supplied = {item['id']: item for item in items}
    for requirement in required:
        identifier, kind = requirement['id'], requirement.get('kind')
        row = {'id': identifier, 'kind': kind, 'status': 'missing', 'scope': requirement.get('scope')}
        report['items'].append(row)
        item = supplied.get(identifier)
        if item is None:
            row['reason'] = 'Required current-phase evidence was not executed or supplied'
            continue
        try:
            expected_status = DISPOSITION[kind]
            if item.get('kind') != kind or item.get('status') != expected_status:
                raise ValueError('Evidence kind/status cannot qualify this requirement')
            bindings = item.get('bindings', {})
            expected_source = (expected_bindings.get('execution_lanes', {}).get(item.get('execution_lane'), {})
                               if kind == 'native' and 'execution_lanes' in expected_bindings else expected_bindings)
            keys = NATIVE_BINDINGS if kind == 'native' else requirement.get('binding_keys', BASE_BINDINGS)
            if not keys or not isinstance(bindings, dict):
                raise ValueError('Exact evidence source bindings required')
            for key in keys:
                expected = expected_source.get(key)
                pattern = r'[0-9a-f]{40}' if key == 'source_commit' else r'[0-9a-f]{64}'
                if not isinstance(expected, str) or not re.fullmatch(pattern, expected) or bindings.get(key) != expected:
                    raise ValueError('Missing/stale expected binding: ' + key)
            artifact = item.get('artifact', {})
            if read_artifact is None or not isinstance(artifact.get('sha256'), str) or not HEX.fullmatch(artifact['sha256']):
                raise ValueError('Actual retained artifact reader and digest required')
            raw = read_artifact(artifact['path'])
            if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
                raise ValueError('Artifact bytes do not match evidence digest')
            proof = pointer(json.loads(raw, object_pairs_hook=unique), artifact['pointer'])
            if not isinstance(proof, dict) or proof.get('kind') != kind or proof.get('status') != expected_status:
                raise ValueError('Artifact result does not support typed disposition')
            assertions = proof.get('assertions')
            if not isinstance(assertions, list) or not assertions:
                raise ValueError('Zero-assertion artifact cannot pass')
            assertion_names = [a.get('name') for a in assertions if isinstance(a, dict)]
            if len(assertion_names) != len(assertions) or len(set(assertion_names)) != len(assertion_names):
                raise ValueError('Malformed/duplicate artifact assertion')
            if any(a.get('status') != expected_status for a in assertions):
                raise ValueError('Failed/skipped/missing assertion preserved as nonpassing')
            wanted = requirement.get('assertions', [])
            if not wanted or not set(wanted).issubset(assertion_names):
                raise ValueError('Required named assertion missing')
            if proof.get('bindings') != bindings:
                raise ValueError('Artifact source bindings differ from index')
            if kind == 'native':
                wanted_class = ('real-native-evaluator' if identifier == 'evaluator-error-boundaries'
                                else 'native-scheduled-gall' if identifier == 'delivery-late-old-leave'
                                and item.get('execution_lane') == 'gall_schedule' else 'real-native-fake-ships')
                if proof.get('classification') != wanted_class or not proof.get('native'):
                    raise ValueError('Actual native commands/signs missing or mocked')
                if proof.get('guard_status') != 'completed':
                    raise ValueError('Guard refused/tripped/incomplete native execution')
            elif kind in ('source_review', 'not_applicable'):
                reviewers = expected_bindings.get('independent_reviewers', ['/root/qa_review', '/root/hoon_review'])
                if (proof.get('reviewer') not in reviewers or proof.get('reviewer') == expected_bindings.get('implementation_owner', '/root')
                        or proof.get('reviewer') not in ('/root/qa_review', '/root/hoon_review', '/root/independent_review')
                        or not proof.get('scope')):
                    raise ValueError('Bounded independent source disposition required')
                files = proof.get('reviewed_source_files')
                current_files = expected_bindings.get('source_files', {})
                if not isinstance(files, dict) or not files or any(
                        not isinstance(value, str) or not HEX.fullmatch(value) or current_files.get(path) != value
                        for path, value in files.items()):
                    raise ValueError('Reviewed source bytes do not match current exact source files')
                if kind == 'not_applicable' and (identifier != 'no-effect-subsystem' or not proof.get('reason')):
                    raise ValueError('N/A limited to explicitly absent external-effect subsystem')
            row.update(status=expected_status, verified_by=report['protocol'],
                       artifact=artifact, bindings=bindings, assertion_count=len(assertions))
        except (KeyError, ValueError, TypeError, IndexError, OSError) as error:
            row.update(status='failed', reason=f'{type(error).__name__}: {error}')
    report['counts'] = dict(Counter(row['status'] for row in report['items']))
    report['native_required'] = sum(row['kind'] == 'native' for row in report['items'])
    report['native_passed'] = sum(row['kind'] == 'native' and row['status'] == 'passed' for row in report['items'])
    if not report['errors'] and all(row['status'] == DISPOSITION.get(row['kind']) for row in report['items']):
        report['status'] = 'passed'
    return report


def tree_digest(files):
    require(isinstance(files, dict) and bool(files) and all(isinstance(name, str)
        and not Path(name).is_absolute() and '..' not in Path(name).parts
        and isinstance(value, str) and HEX.fullmatch(value) for name, value in files.items()),
        'Exact nonempty source file map required')
    return hashlib.sha256(''.join(value + '  ' + name + '\n'
                          for name, value in sorted(files.items(), key=lambda row: Path(row[0]).parts)).encode()).hexdigest()


def retained(reference, read):
    require(callable(read) and isinstance(reference, dict), 'Retained artifact reader and reference required')
    raw = read(reference['path'])
    require(isinstance(raw, bytes) and len(raw) <= 32 * 1024 * 1024
            and hashlib.sha256(raw).hexdigest() == reference['sha256'], 'Retained artifact digest/bound mismatch')
    return pointer(json.loads(raw, object_pairs_hook=unique), reference['pointer'])


def validate_lane(lane, raw, guard, expected):
    require(raw.get('source_commit_after') == raw.get('source_commit') and bool(raw.get('source_commit')),
            'Committed source missing or changed during execution')
    require(raw.get('inputs_before') == raw.get('inputs_after') and bool(raw.get('inputs_before')),
            'Execution source changed or is missing')
    source = raw['inputs_before']
    require(source == expected['execution_inputs'][lane], 'Exact recorded execution inputs differ from reviewed inputs')
    files = dict(expected['native_source_files'])
    tree_digest(files)
    ships = ('zod', 'bus', 'nec', 'bud') if lane == 'core' else ('zod',)
    if lane == 'gall_schedule':
        overlay = expected['schedule_source_files']
        require(not (set(files) & set(overlay)) and source['overlay'] == tree_digest(overlay), 'Schedule overlay collision or drift')
        files.update(overlay)
    require(raw.get('installed_files') == files
        and raw.get('installed_by_ship') == {s: files for s in ships}
        and raw.get('clay_verified_by_ship') == {s: files for s in ships}, 'Incomplete actual installed/Clay file comparisons')
    observed = {'source_commit': raw['source_commit'], 'native_tree_sha256': source['native'],
        'runtime_lock_sha256': source['toolchain'], 'corpus_sha256': source['cases' if lane == 'core' else 'corpus'],
        'contract_freeze_sha256': source['freeze'], 'runner_sha256': source['runner'][lane + '.py' if lane == 'gall_schedule' else 'core_test.py'],
        'loaded_closure_sha256': source['harness'], 'installed_clay_tree_sha256': tree_digest(files),
        'observer_sha256': files['app/stead-observer.hoon']}
    require(observed == expected['execution_lanes'][lane], 'Expected lane bindings differ from actual execution')
    for key in ('source_commit', 'native_tree_sha256', 'runtime_lock_sha256', 'corpus_sha256', 'contract_freeze_sha256', 'observer_sha256'):
        require(observed[key] == expected[key], 'Lane differs from common source binding: ' + key)
    require(source['native'] == tree_digest(expected['native_source_files']), 'Native source tree does not match file manifest')
    lease = raw['execution_guard']
    require(guard.get('status') == 'completed' and guard.get('exit_code') == 0 and guard.get('launched') is True
            and not guard.get('reason') and bool(guard.get('run_id'))
            and guard['run_id'] == lease['run_id'] and guard['guard_sha256'] == lease['guard_sha256']
            and guard['policy'] == lease['policy']
            and hashlib.sha256(json.dumps(guard['policy'], sort_keys=True).encode()).hexdigest() == lease['policy_sha256'],
            'Native guard not completed or bound to this execution')
    require(passed_checks(raw.get('checks')) and bool(raw.get('commands')), 'Missing/failed native commands or checks')


def validate_transport(report, execution, read):
    artifact = report['transport_artifact']
    require(artifact.get('encoding') == 'gzip-jsonl' and Path(artifact['file']).name == artifact['file'],
            'Invalid transport artifact')
    compressed = read(str(Path(execution['path']).parent / artifact['file']))
    require(isinstance(compressed, bytes) and len(compressed) <= 32 * 1024 * 1024
            and hashlib.sha256(compressed).hexdigest() == artifact['sha256'], 'Transport compressed digest/bound mismatch')
    wanted = {}
    stack = [report]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            ref = item.get('transcript')
            if isinstance(ref, dict):
                require(ref.get('artifact') == artifact['file'] and type(ref.get('line')) is int and ref['line'] > 0,
                        'Invalid retained transport reference')
                wanted.setdefault(ref['line'], []).append((ref, item))
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    require(bool(wanted), 'No retained transport references')
    digest, total, count = hashlib.sha256(), 0, 0
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        while line := stream.readline(24 * 1024 * 1024 + 1):
            count += 1
            total += len(line)
            require(len(line) <= 24 * 1024 * 1024 and total <= 512 * 1024 * 1024 and line.endswith(b'\n'),
                    'Transport expanded bounds exceeded')
            digest.update(line)
            value = json.loads(line, object_pairs_hook=unique)
            for ref, item in wanted.pop(count, []):
                require(ref.get('record_sha256') == hashlib.sha256(line).hexdigest()
                        and ref.get('record_bytes') == len(line), 'Transport record digest/bound mismatch')
                for key in ('ship', 'mode', 'route', 'input_sha256', 'input_bytes', 'response_frame_sha256', 'stdout', 'stderr'):
                    if key in item and key in value:
                        abbreviated = (key == 'stdout' and item[key] == '<see exact transcript>'
                                       and isinstance(value[key], str) and len(value[key]) > 1024)
                        require(abbreviated or item[key] == value[key], 'Transport summary differs from exact record')
    require(not wanted and count > 0 and count == artifact['records'] and total == artifact['uncompressed_bytes']
            and digest.hexdigest() == artifact['uncompressed_sha256'], 'Transport inventory/digest mismatch')


def validate_evaluator_controls(report):
    """Bind three retained pure-evaluator exchanges; never infer ship delivery."""
    controls = report['evaluator_controls']
    require(isinstance(controls, dict) and controls.get('status') == 'passed'
            and controls.get('classification') == 'real-native-evaluator',
            'Wrong evaluator control classification')
    commands = controls.get('commands')
    require(isinstance(commands, list) and len(commands) == 3, 'Exactly three evaluator control exchanges required')
    require(isinstance(report.get('commands'), list), 'Missing retained evaluator command list')
    indices = [index for index, row in enumerate(report['commands'])
               if isinstance(row, dict) and row.get('mode') == 'evaluator']
    require(len(indices) == 3 and [report['commands'][index] for index in indices] == commands,
            'Evaluator controls differ from retained command inventory')
    specs = Path('/specs') if Path(__file__).parent == Path('/code') else Path(__file__).resolve().parents[2] / 'specs/urbit'
    binary = '/runtime/' + json.loads((specs / 'toolchain.lock.json').read_bytes(), object_pairs_hook=unique)['runtime']['binary']
    observed = []
    fields = {'mode', 'argv', 'input_hex', 'stdout_hex', 'stderr_hex', 'exit_code'}
    for command, flag in zip(commands, ('-jn', '-jn', '-ckn'), strict=True):
        require(isinstance(command, dict) and set(command) == fields and command['mode'] == 'evaluator'
                and command['argv'] == [binary, 'eval', '--loom', '29', flag]
                and type(command['exit_code']) is int and command['exit_code'] == 0,
                'Wrong evaluator argv, mode, result or record shape')
        values = []
        for key in ('input_hex', 'stdout_hex', 'stderr_hex'):
            value = command[key]
            require(isinstance(value, str) and len(value) <= 2_000_000
                    and re.fullmatch(r'(?:[0-9a-f]{2})*', value) is not None,
                    'Malformed or oversized evaluator bytes')
            values.append(bytes.fromhex(value))
        observed.append(values)

    def complete_frame(value):
        return (len(value) >= 5 and value[0] == 0
                and 0 < int.from_bytes(value[1:5], 'little') <= 1_000_000
                and len(value) == 5 + int.from_bytes(value[1:5], 'little'))

    bad_input, bad_output, bad_error = observed[0]
    require(bad_input == b'[' and not complete_frame(bad_output) and bool(bad_error.strip()),
            'Missing actual invalid-input evaluator rejection')
    require(controls.get('invalid_input') == {'exit': 0, 'encoder_rejected': True,
            'stdout_hex': bad_output.hex(), 'stderr': bad_error.decode(errors='replace')},
            'Invalid-input summary differs from retained evaluator bytes')
    expected = {'protocol': 'stead.framing-control/1', 'synthetic_text': 'x' * 34000}
    raw = json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()
    noun = b"[32 %avow 0 %noun %stead-core-result '" + raw.hex().encode() + b"']"
    encode_input, frame, encode_error = observed[1]
    decode_input, text, decode_error = observed[2]
    require(encode_input == noun and complete_frame(frame) and len(frame) > 65536 and decode_input == frame,
            'Large evaluator frame is missing, truncated, small or disconnected')
    match = re.fullmatch(rb"\s*\[32\s+%avow\s+0\s+%noun\s+%stead-core-result\s+'([0-9a-f]+)'\]\s*", text)
    require(match is not None, 'Missing exact decoded evaluator result')
    decoded = bytes.fromhex(match[1].decode())
    require(decoded == raw and json.loads(decoded, object_pairs_hook=unique) == expected,
            'Evaluator roundtrip changed exact result bytes')
    require(type(controls.get('large_frame_bytes')) is int and controls['large_frame_bytes'] == len(frame)
            and controls.get('large_frame_hex') == frame.hex()
            and controls.get('large_frame_sha256') == hashlib.sha256(frame).hexdigest()
            and controls.get('result_sha256') == hashlib.sha256(decoded).hexdigest()
            and controls.get('decoded_stdout') == text.decode('utf-8')
            and controls.get('encode_stderr') == encode_error.decode(errors='replace')
            and controls.get('decode_stderr') == decode_error.decode(errors='replace'),
            'Evaluator summaries differ from actual command bytes')
    return indices


def validate_schedule(report):
    import gall_schedule_proof
    import gall_schedule
    require(report.get('status') == 'pass' and report.get('stage') == 'completed'
            and report.get('classification') == 'native-scheduled-gall'
            and report.get('requirement') == 'delivery-late-old-leave', 'Wrong scheduled Gall completion/scope')
    actual = gall_schedule_proof.validate(report['positive'])
    require(actual == report.get('positive_validation'), 'Scheduled Gall validation differs from actual noun proof')
    positives = [c for c in report['commands'] if c.get('dojo') == '+stead-gall-schedule']
    require(len(positives) == 1, 'Missing unique actual scheduled Gall command')
    match = re.fullmatch(r"\s*\[%stead-core-result\s+'([0-9a-f]+)'\]\s*", positives[0]['result'])
    require(match is not None and json.loads(bytes.fromhex(match[1]), object_pairs_hook=unique) == report['positive'],
            'Scheduled Gall payload differs from native response')
    control = report['negative_control']
    require(control.get('status') == 'passed' and control.get('expected_pending') == 2 and control.get('actual_pending') == 1,
            'Missing scheduled Gall runtime-negative control')
    command = report['commands'][control['command_index']]
    log = command['log'].encode()
    require(command.get('dojo') == '+stead-gall-schedule-negative'
        and command.get('log_bytes') == len(log) and command.get('log_sha256') == hashlib.sha256(log).hexdigest()
        and gall_schedule.intended_negative(command['result'], command['log']), 'Wrong scheduled Gall runtime negative')


def reconcile(manifest, bundle, expected_bindings, *, read_artifact=None):
    """Validate retained execution before evaluating independently derived claims.

    This host reader never reruns Hoon, rewrites historical skips, or invents
    business predicates. Each typed proof still requires independent review of
    its assertion derivation and exact raw native references.
    """
    failed = {'protocol': 'stead.qualification-reconciliation/1', 'status': 'failed', 'items': [],
              'errors': [], 'historical_reports_unchanged': True, 'classification': 'retained-evidence-validation'}
    try:
        specs = Path(__file__).resolve().parents[2] / 'specs/urbit/v2/qualification-gate.json'
        require(manifest == json.loads(specs.read_bytes(), object_pairs_hook=unique),
                'Current phase requires the exact authoritative 73-item manifest')
        require(bundle['manifest'].get('pointer') == '' and retained(bundle['manifest'], read_artifact) == manifest,
                'Missing exact retained manifest bytes')
        require(set(bundle['executions']) == {'core', 'gall_schedule'} and set(bundle['guards']) == {'core', 'gall_schedule'},
                'Exactly the two native execution lanes and completed guards required')
        reports = {}
        for lane, reference in bundle['executions'].items():
            require(reference.get('pointer') == '', 'Execution reference must retain whole report')
            reports[lane] = retained(reference, read_artifact)
            guard = retained(bundle['guards'][lane], read_artifact)
            require(guard.get('guard_sha256') == expected_bindings.get('guard_sha256'),
                    'Expected guard source differs from actual native execution')
            validate_lane(lane, reports[lane], guard, expected_bindings)
        core = reports['core']
        require(core['inputs_before'].get('qualification_manifest') == bundle['manifest']['sha256']
                and core.get('independent_closeout', {}).get('manifest_sha256') == bundle['manifest']['sha256'],
                'Native execution used a different qualification manifest')
        evaluator_indices = validate_evaluator_controls(core)
        require(core.get('status') == 'execution_complete'
                and core.get('execution_status') == 'completed-awaiting-independent-qualification'
                and core.get('classification') == 'local-real-native-fake-ships'
                and core.get('deferred_qa_requirements') == deferred_execution(core), 'Native core execution incomplete')
        validate_transport(core, bundle['executions']['core'], read_artifact)
        validate_schedule(reports['gall_schedule'])
        requirements = {r['id']: r for r in manifest['required']}
        for item in bundle['items']:
            proof = retained(item['artifact'], read_artifact)
            require(proof.get('scope') == requirements[item['id']]['scope'], 'Typed proof scope differs from requirement')
            if item.get('kind') != 'native':
                continue
            lane = 'gall_schedule' if item['id'] == 'delivery-late-old-leave' else 'core'
            require(item.get('execution_lane') == lane and proof.get('execution_lane') == lane
                    and isinstance(proof.get('native'), list) and bool(proof['native'])
                    and all(isinstance(reference, dict) for reference in proof['native']),
                    'Native proof has wrong lane or no references')
            if item['id'] == 'evaluator-error-boundaries':
                require([reference.get('pointer') for reference in proof['native']]
                        == ['/commands/' + str(index) for index in evaluator_indices],
                        'Evaluator proof must reference all three exact control exchanges')
            for reference in proof['native']:
                execution = bundle['executions'][lane]
                require(reference.get('path') == execution['path'] and reference.get('sha256') == execution['sha256'],
                        'Native proof refers outside its admitted execution')
                require(isinstance(reference.get('pointer'), str)
                        and re.fullmatch(r'/commands/(0|[1-9][0-9]*)', reference['pointer']),
                        'Native evidence must reference an actual command, not metadata')
                record = retained(reference, read_artifact)
                require(isinstance(record, dict) and bool(record)
                        and record.get('status') not in ('failed', 'fail', 'not_run', 'skipped')
                        and record.get('passed') is not False, 'Native reference is missing, failed, or not a record')
                if record.get('mode') == 'evaluator':
                    require(item['id'] == 'evaluator-error-boundaries',
                            'Pure evaluator records cannot support ship or Dojo requirements')
                else:
                    require(record.get('ship') in ('zod', 'bus', 'nec', 'bud') and (
                        isinstance(record.get('dojo'), str) and isinstance(record.get('result'), str)
                        or isinstance(record.get('mode'), str) and isinstance(record.get('stdout'), str)
                        and isinstance(record.get('stderr'), str) and isinstance(record.get('transcript'), dict)),
                        'Native command is missing its actual response/transport')
        result = evaluate(manifest, bundle, expected_bindings, read_artifact=read_artifact)
        result.update(protocol=failed['protocol'], classification=failed['classification'],
                      execution_artifacts=bundle['executions'], guard_artifacts=bundle['guards'],
                      test_owner='/root/independent_review')
        return result
    except (KeyError, ValueError, TypeError, IndexError, OSError, EOFError) as error:
        failed['errors'].append(type(error).__name__ + ': ' + str(error))
        return failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_bytes(), object_pairs_hook=unique)
    bundle = read(args.evidence)
    result = reconcile(read(args.manifest), bundle, read(args.bindings), read_artifact=artifact_reader(args.root))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{result['status'].upper()} current gate: {result.get('native_passed', 0)}/{result.get('native_required', 0)} native requirements supported")
    raise SystemExit(0 if result['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()

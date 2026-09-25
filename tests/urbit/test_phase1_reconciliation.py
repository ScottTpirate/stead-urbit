"""Authored HOST fixtures for Phase 1 reconciliation, never native evidence.

These reports deliberately imitate native report structure. No ship, Hoon
compiler, guard, network, subprocess or external service runs in this module.
Passing these tests proves rejection/format behavior, not a Phase 1 result.

Integrator-owned API under test:
    qualification_gate.reconcile(manifest, evidence_bundle, expected_bindings,
                                 *, read_artifact=None) -> gate-shaped result
The existing evaluate API remains available for its narrower format tests.
"""
from __future__ import annotations

from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
sys.path.insert(0, str(ROOT / 'tests/urbit'))
import qualification_gate as G
import gall_schedule_proof
from test_gall_schedule_proof import specimen as authored_schedule_payload


DEFERRED = {
    'scoped-private-metadata': ('project-views-never-include-other-owner-private-metadata',
                                'projection-timing-and-all-metadata-nondisclosure'),
    'no-effect-subsystem': ('restart-preserves-content-policy-objects-and-journal',
                            'no-external-effects-replayed'),
    'receipt-lookup-order': ('downgraded-reader-cannot-recover-write-receipt',
                            'source-ordering-property'),
}
DELIVERY_NAMES = (
    'known-mark-and-held-outsider', 'wrong-sender-and-binding',
    'missing-channel-and-wrong-digest', 'leave-and-fresh-retry',
    'lazy-expiry-and-same-path-retirement', 'pending-quotas',
    'home-unavailable', 'ended-leave-attempt',
)
RECIPES = (
    'v1-private-identity-and-sequence-reproduction',
    'v1-exhaustion-migration-security-reserve', 'projects', 'work_items',
    'grants', 'documents', 'history', 'object_bytes',
)
SHIPS = ('zod', 'bus', 'nec', 'bud')


def raw(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':')) + '\n').encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def named_digest(value):
    return digest(('AUTHORED HOST FIXTURE: ' + value).encode())


def file_tree(entries):
    """The digests.tree_sha byte convention, independently specified here."""
    return digest(''.join(value + '  ' + name + '\n'
                          for name, value in sorted(entries.items())).encode())


def assertion(name, status='passed'):
    return {'name': name, 'status': status}


def authored_evaluator_controls():
    """Consistent invented exchange bytes, NOT a real jam frame or native run."""
    expected = {'protocol': 'stead.framing-control/1', 'synthetic_text': 'x' * 34000}
    encoded = json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()
    noun = b"[32 %avow 0 %noun %stead-core-result '" + encoded.hex().encode() + b"']"
    frame = b'\0' + (68000).to_bytes(4, 'little') + b'x' * 68000
    error = b'AUTHORED HOST PARSE REJECTION'
    binary = '/runtime/' + json.loads((ROOT / 'specs/urbit/toolchain.lock.json').read_bytes())['runtime']['binary']
    commands = [{'mode': 'evaluator', 'argv': [binary, 'eval', '--loom', '29', flag],
                 'input_hex': source.hex(), 'stdout_hex': stdout.hex(), 'stderr_hex': stderr.hex(), 'exit_code': 0}
                for flag, source, stdout, stderr in (
                    ('-jn', b'[', b'', error), ('-jn', noun, frame, b''), ('-ckn', frame, noun, b''))]
    return {'status': 'passed', 'classification': 'real-native-evaluator', 'commands': commands,
            'invalid_input': {'exit': 0, 'encoder_rejected': True, 'stdout_hex': '', 'stderr': error.decode()},
            'large_frame_bytes': len(frame), 'large_frame_hex': frame.hex(), 'large_frame_sha256': digest(frame),
            'result_sha256': digest(encoded), 'decoded_stdout': noun.decode(), 'encode_stderr': '', 'decode_stderr': ''}


def diagnostic(result):
    """Keep a negative test failure readable rather than dumping all 73 proofs."""
    return {'status': result.get('status'), 'errors': result.get('errors'),
            'counts': result.get('counts'),
            'nonpassing': [{key: row.get(key) for key in ('id', 'status', 'reason')}
                          for row in result.get('items', [])
                          if row.get('status') in ('failed', 'missing')][:5]}


class AuthoredFixture:
    """All observations below are invented data for this host unit test."""

    def __init__(self):
        self.manifest_raw = (ROOT / 'specs/urbit/v2/qualification-gate.json').read_bytes()
        self.manifest = json.loads(self.manifest_raw)
        self.source_commit = 'a' * 40
        self.native_files = {
            'app/stead-home.hoon': named_digest('home'),
            'app/stead-observer.hoon': named_digest('observer'),
            'lib/stead-core.hoon': named_digest('core'),
        }
        self.overlay_files = {
            'gen/stead-gall-schedule.hoon': named_digest('positive generator'),
            'gen/stead-gall-schedule-negative.hoon': named_digest('negative generator'),
            'lib/stead-gall-schedule.hoon': named_digest('actual Gall schedule library'),
        }
        self.guard_policy = {'start_c': 75, 'stop_c': 90, 'sample_seconds': 1,
            'stale_seconds': 3, 'cooperative_seconds': 10, 'terminate_seconds': 10,
            'kill_seconds': 5, 'cpu_period_us': 10000, 'cpu_quota_us': 5000}
        common = {'source_commit': self.source_commit,
            'native_tree_sha256': file_tree(self.native_files),
            'runtime_lock_sha256': named_digest('runtime lock'),
            'corpus_sha256': named_digest('corpus'),
            'contract_freeze_sha256': named_digest('v2 freeze'),
            'observer_sha256': self.native_files['app/stead-observer.hoon']}
        self.expected = dict(common, runner_sha256=named_digest('reconciler'),
            source_files={'native/core/desk/' + key: value for key, value in self.native_files.items()},
            native_source_files=copy.deepcopy(self.native_files),
            schedule_source_files=copy.deepcopy(self.overlay_files),
            independent_reviewers=['/root/independent_review'],
            implementation_owner='/root', execution_lanes={})
        self.reports, self.guards = {}, {}
        for lane, runner in (('core', 'core_test.py'), ('gall_schedule', 'gall_schedule.py')):
            installed = dict(self.native_files)
            if lane == 'gall_schedule':
                installed.update(self.overlay_files)
            bindings = dict(common, runner_sha256=named_digest(runner),
                loaded_closure_sha256=named_digest(lane + ' loaded harness'),
                installed_clay_tree_sha256=file_tree(installed))
            self.expected['execution_lanes'][lane] = bindings
            inputs = {'native': common['native_tree_sha256'],
                'toolchain': common['runtime_lock_sha256'],
                'cases': common['corpus_sha256'], 'corpus': common['corpus_sha256'],
                'freeze': common['contract_freeze_sha256'],
                'previous_freeze': named_digest('v1 freeze'),
                'fixture': named_digest('native fixture'),
                'qualification_manifest': digest(self.manifest_raw),
                'harness': bindings['loaded_closure_sha256'],
                'runner': {runner: bindings['runner_sha256'],
                           'core_conn.py': named_digest('core connection')},
                'overlay': file_tree(self.overlay_files), 'gall': named_digest('pinned Gall')}
            run_id = ('b' if lane == 'core' else 'c') * 32
            lease = {'run_id': run_id, 'generation': 10,
                'guard_sha256': named_digest('execution policy source'),
                'policy_sha256': digest(json.dumps(self.guard_policy, sort_keys=True).encode()),
                'policy': copy.deepcopy(self.guard_policy)}
            self.guards[lane] = {'format': 1, 'run_id': run_id, 'label': lane,
                'status': 'completed', 'exit_code': 0, 'launched': True, 'reason': None,
                'guard_sha256': lease['guard_sha256'], 'policy': copy.deepcopy(self.guard_policy),
                'events': [{'event': 'final', 'status': 'completed', 'reason': None}], 'cleanup': []}
            ships = SHIPS if lane == 'core' else ('zod',)
            self.reports[lane] = {'source_commit': self.source_commit,
                'source_commit_after': self.source_commit,
                'inputs_before': inputs, 'inputs_after': copy.deepcopy(inputs),
                'installed_files': installed,
                'installed_by_ship': {ship: copy.deepcopy(installed) for ship in ships},
                'clay_verified_by_ship': {ship: copy.deepcopy(installed) for ship in ships},
                'execution_guard': lease, 'checks': [], 'commands': [],
                'fixture_classification': 'AUTHORED HOST FIXTURE; NOT NATIVE EVIDENCE'}
        self.expected['guard_sha256'] = self.guards['core']['guard_sha256']
        self.expected['execution_inputs'] = {lane: copy.deepcopy(report['inputs_before'])
                                              for lane, report in self.reports.items()}
        self._core()
        self._schedule()
        self.proofs = {}
        for requirement in self.manifest['required']:
            identifier, kind = requirement['id'], requirement['kind']
            status = G.DISPOSITION[kind]
            lane = 'gall_schedule' if identifier == 'delivery-late-old-leave' else 'core'
            bindings = (self.expected['execution_lanes'][lane] if kind == 'native'
                        else {key: self.expected[key]
                              for key in requirement.get('binding_keys', G.BASE_BINDINGS)})
            proof = {'id': identifier, 'kind': kind, 'status': status,
                'scope': requirement['scope'], 'bindings': copy.deepcopy(bindings),
                'assertions': [assertion(name, status) for name in requirement['assertions']]}
            if kind == 'native':
                proof.update(execution_lane=lane,
                    classification='native-scheduled-gall' if lane == 'gall_schedule' else 'real-native-fake-ships',
                    guard_status='completed',
                    native=[{'$execution': lane, 'pointer': '/commands/0'}])
                if identifier == 'evaluator-error-boundaries':
                    proof['classification'] = 'real-native-evaluator'
                    proof['native'] = [{'$execution': 'core', 'pointer': '/commands/' + str(index)}
                                       for index in (1, 2, 3)]
            elif kind in ('source_review', 'not_applicable'):
                proof.update(reviewer='/root/independent_review', author='/root',
                    reviewed_source_files=copy.deepcopy(self.expected['source_files']))
                if kind == 'not_applicable':
                    proof['reason'] = 'No external-effect subsystem in this bounded source profile.'
            self.proofs[identifier] = proof
        self.extra_items = []
        self.omit_items = set()

    def _core(self):
        core = self.reports['core']
        corpus = json.loads((ROOT / 'specs/urbit/fixtures/native-cases-v2.json').read_bytes())
        cases = list(corpus['ordered_cases'])
        for key in ('real_expiry_continuation', 'source_review_continuation',
                    'separate_project_journal_lane', 'scoped_privacy_lane'):
            cases.extend(corpus[key]['cases'])
        rows = []
        for case in cases:
            row = {'name': case['name'], 'status': 'passed', 'checks': [
                dict(assertion('native-result-present'), case=case['name'])]}
            for identifier, (name, check) in DEFERRED.items():
                if name == case['name']:
                    row['status'] = 'incomplete'
                    row['checks'].append({'case': name, 'name': check, 'status': 'skipped',
                        'reason': 'Required typed current evidence missing: ' + identifier})
            rows.append(row)
        core.update(status='execution_complete',
            execution_status='completed-awaiting-independent-qualification',
            classification='local-real-native-fake-ships', error=None,
            deferred_qa_requirements=list(DEFERRED),
            independent_closeout={'status': 'pending',
                'manifest_sha256': core['inputs_before']['qualification_manifest']},
            qa={'status': 'incomplete', 'classification': 'local-real-native-fake-ships',
                'case_counts': dict(Counter(row['status'] for row in rows)), 'cases': rows,
                'checks': [copy.deepcopy(check) for row in rows for check in row['checks']]},
            qa_coverage_status='incomplete',
            delivery={'status': 'incomplete', 'classification': 'real-native-fake-ships',
                'native_qualified': False, 'functional_scope_passed': False,
                'calls': [{'native': {'fixture': 'AUTHORED HOST ONLY'}}],
                'cases': [{'name': name, 'status': 'passed',
                    'assertions': [assertion('nonempty-case-evidence')]}
                    for name in DELIVERY_NAMES]},
            qualification={'status': 'passed', 'classification': 'local-real-native-fake-ships',
                'native_qualified': True, 'recipes': {name: {'status': 'executed'} for name in RECIPES},
                'checks': [{'name': 'all-eight-planned-recipes-executed', 'passed': True}],
                'calls': [{'fixture': 'AUTHORED HOST ONLY'}], 'batches': [{'count': 1}]},
            evaluator_controls={'status': 'passed', 'classification': 'real-native-evaluator',
                'invalid_input': {'encoder_rejected': True, 'exit': 0,
                    'stdout_hex': '00', 'stderr': 'eval: bail: %exit'},
                'large_frame_bytes': 68159, 'large_frame_sha256': named_digest('large frame'),
                'result_sha256': named_digest('large result')},
            concurrent_submissions=[{'sender': 'bus', 'fixture': 'AUTHORED HOST ONLY'},
                                    {'sender': 'zod', 'fixture': 'AUTHORED HOST ONLY'}],
            supported_predecessor_versions=[1])
        core['delivery']['cases'][-1].update(status='incomplete', missing=[
            'Actual delayed old native leave injection at home remains unavailable; pinned Gall source review is a distinct proof.'])
        core['checks'] = [{'name': name, 'passed': True} for name in (
            'loaded-supervisor-source-matches', 'loaded-core-runner-source-matches',
            'native-evaluator-failure-and-large-frame-controls',
            'all-qa-native-cases-executed-without-failure', 'native-on-save-on-load-roundtrip',
            'two-principal-concurrent-cas-one-winner', 'delivery-has-no-observed-failure',
            'native-capacity-and-predecessor-qualification')]
        self.transport_record = {'ship': 'zod', 'mode': 'read', 'route': '/v1/fixture-snapshot',
            'input_sha256': digest(b''), 'input_bytes': 0,
            'request': 'AUTHORED HOST TRANSPORT FIXTURE', 'stdout': '[32 %avow 0 %noun %stead-core-result \'7b7d\']',
            'stderr': '', 'response_frame_sha256': named_digest('invented response frame'),
            'outcome': {'raw': '{}', 'json': {}}}
        line = raw(self.transport_record)
        self.transport = gzip.compress(line, mtime=0)
        core['transport_artifact'] = {'file': 'transport.jsonl.gz', 'encoding': 'gzip-jsonl',
            'records': 1, 'sha256': digest(self.transport), 'uncompressed_bytes': len(line),
            'uncompressed_sha256': digest(line), 'scope': 'AUTHORED HOST ONLY'}
        core['commands'] = [{key: self.transport_record[key] for key in (
            'ship', 'mode', 'route', 'input_sha256', 'input_bytes',
            'response_frame_sha256', 'stdout', 'stderr')} | {
            'request_sha256': digest(self.transport_record['request'].encode()),
            'transcript': {'artifact': 'transport.jsonl.gz', 'line': 1,
                'record_bytes': len(line), 'record_sha256': digest(line)}}]
        core['evaluator_controls'] = authored_evaluator_controls()
        core['commands'].extend(copy.deepcopy(core['evaluator_controls']['commands']))

    def _schedule(self):
        report = self.reports['gall_schedule']
        payload = authored_schedule_payload()
        positive_text = "[%stead-core-result '" + raw(payload).hex() + "']"
        diagnostic = '[%stead-scheduled-gall-pending-control 2 1]\n'
        report.update(status='pass', stage='completed', classification='native-scheduled-gall',
            requirement='delivery-late-old-leave',
            scope='Actual pinned Gall and app gates; simulated dispatch queue and fixed clock; no Ames or UDP.',
            positive=payload, positive_validation=gall_schedule_proof.validate(payload),
            commands=[{'ship': 'zod', 'dojo': '+stead-gall-schedule', 'result': positive_text,
                       'log_offset': 0, 'log_bytes': 0, 'log_sha256': digest(b''), 'log': ''},
                      {'ship': 'zod', 'dojo': '+stead-gall-schedule-negative', 'result': '~',
                       'log_offset': 0, 'log_bytes': len(diagnostic.encode()),
                       'log_sha256': digest(diagnostic.encode()), 'log': diagnostic}],
            checks=[{'name': 'positive-native-result-shape', 'passed': True},
                    {'name': 'wrong-pending-count-is-specific-runtime-failure', 'passed': True}],
            negative_control={'status': 'passed', 'expected_pending': 2,
                              'actual_pending': 1, 'command_index': 1})

    def materialize(self):
        artifacts = {'core.json': raw(self.reports['core']),
            'gall_schedule.json': raw(self.reports['gall_schedule']),
            'manifest.json': self.manifest_raw,
            'guard-core.json': raw(self.guards['core']),
            'guard-gall_schedule.json': raw(self.guards['gall_schedule']),
            'transport.jsonl.gz': self.transport}

        def reference(path, pointer=''):
            return {'path': path, 'sha256': digest(artifacts[path]), 'pointer': pointer}

        def expand(value):
            if isinstance(value, dict) and '$execution' in value:
                return reference(value['$execution'] + '.json', value['pointer'])
            if isinstance(value, dict):
                return {key: expand(item) for key, item in value.items()}
            if isinstance(value, list):
                return [expand(item) for item in value]
            return value

        proofs = expand(copy.deepcopy(self.proofs))
        artifacts['proofs.json'] = raw({'proofs': proofs})
        items = [{'id': identifier, 'kind': proof['kind'], 'status': proof['status'],
            'bindings': copy.deepcopy(proof['bindings']),
            **({'execution_lane': proof['execution_lane']} if 'execution_lane' in proof else {}),
            'artifact': reference('proofs.json', '/proofs/' + identifier)}
            for identifier, proof in proofs.items() if identifier not in self.omit_items]
        bundle = {'items': items + copy.deepcopy(self.extra_items),
            'manifest': reference('manifest.json'),
            'executions': {lane: reference(lane + '.json') for lane in self.reports},
            'guards': {lane: reference('guard-' + lane + '.json') for lane in self.guards}}
        return bundle, artifacts


class Phase1ReconciliationHostTests(unittest.TestCase):
    def historical_fixture(self, *, current_extra=b''):
        """Authored review wrapper around unchanged real historical records."""
        fixture = AuthoredFixture()
        actual = (ROOT / 'scripts/urbit/execution_policy.py').read_bytes()
        old = actual.replace(G.GUARD_LAUNCH_ADDITION, b'', 1)
        self.assertEqual(digest(old), '7166d197a6e3879f21c22637f2bd3074ff90975c33a2149f6e07763e2eeaa04e')
        current = actual + current_extra
        guard_sha = digest(current)
        fixture.expected['guard_sha256'] = guard_sha
        fixture.expected['source_files']['scripts/urbit/execution_policy.py'] = guard_sha
        for lane in fixture.guards:
            fixture.guards[lane]['guard_sha256'] = guard_sha
            fixture.reports[lane]['execution_guard']['guard_sha256'] = guard_sha
        fixture.proofs['guard-independent-source-review']['reviewed_source_files']['scripts/urbit/execution_policy.py'] = guard_sha
        host_log = b'AUTHORED host output fixture; this is not a retained execution result\n'
        fixture.proofs['guard-negative-host-tests'].update(bindings={'guard_sha256': guard_sha},
            underlying_artifacts=[{'path': 'authored-host.log', 'sha256': digest(host_log)}])
        historical = {}
        names = {'guard-real-hot-preflight-refusal': ('guard-real-preflight-93c.json', 'guard-real-start-81c.json'),
                 'guard-real-platform-mocked-sensors': ('guard-platform-mocked-sensors.json', 'guard-platform-mocked-sensors.log')}
        original_bytes = {}
        for identifier, files in names.items():
            refs = []
            for name in files:
                path = 'docs/urbit/evidence/2026-09-13/qualification/' + name
                original_bytes[path] = (ROOT / path).read_bytes()
                refs.append({'path': path, 'sha256': digest(original_bytes[path])})
            historical[identifier] = refs
            fixture.proofs[identifier].update(bindings={'guard_sha256': digest(old)}, underlying_artifacts=copy.deepcopy(refs))

        def attach(bundle, artifacts):
            artifacts.update(original_bytes)
            artifacts.update({'old-guard.py': old, 'current-guard.py': current, 'authored-host.log': host_log})
            items = {item['id']: item for item in bundle['items']}
            review = {'protocol': 'stead.historical-guard-continuity/1', 'status': 'reviewed',
                'reviewer': '/root/independent_review',
                'fixture_classification': 'AUTHORED HOST WRAPPER; NOT AN ACTUAL REVIEW',
                'change_id': 'add-prelaunch-resample-cancel-check-and-lease-publication',
                'historical_guard_sha256': digest(old), 'current_guard_sha256': guard_sha,
                'previous_source': {'path': 'old-guard.py', 'sha256': digest(old)},
                'current_source': {'path': 'current-guard.py', 'sha256': guard_sha},
                'historical_artifacts': copy.deepcopy(historical),
                'current_source_review': copy.deepcopy(items['guard-independent-source-review']['artifact']),
                'current_host_tests': copy.deepcopy(items['guard-negative-host-tests']['artifact'])}
            artifacts['continuity.json'] = raw(review)
            bundle['historical_guard_continuity'] = {'path': 'continuity.json', 'sha256': digest(artifacts['continuity.json']), 'pointer': ''}
        return fixture, attach

    def call(self, fixture, *, damage=None, reader=True):
        bundle, artifacts = fixture.materialize()
        if damage is not None:
            damage(bundle, artifacts)
        before = copy.deepcopy((fixture.manifest, bundle, fixture.expected, artifacts))
        self.assertTrue(callable(getattr(G, 'reconcile', None)),
                        'Integrator must implement qualification_gate.reconcile; these are acceptance tests.')
        result = G.reconcile(fixture.manifest, bundle, fixture.expected,
                             read_artifact=artifacts.__getitem__ if reader else None)
        self.assertEqual((fixture.manifest, bundle, fixture.expected, artifacts), before,
                         'Reconciliation must not rewrite source artifacts, raw skips or evidence inputs')
        return result

    def rejects(self, fixture, **kwargs):
        result = self.call(fixture, **kwargs)
        self.assertEqual(result['status'], 'failed', diagnostic(result))
        return result

    def test_fixture_inventory_and_native_payload_are_explicitly_host_only(self):
        fixture = AuthoredFixture()
        self.assertEqual(len(fixture.proofs), 73)
        self.assertEqual(sum(p['kind'] == 'native' for p in fixture.proofs.values()), 66)
        self.assertEqual(fixture.reports['core']['qa']['case_counts'], {'passed': 145, 'incomplete': 3})
        self.assertFalse(fixture.reports['gall_schedule']['positive_validation']['native_execution_verified'])

    def test_complete_authored_format_resolves_all73_without_mutating_raw_skips(self):
        fixture = AuthoredFixture()
        result = self.call(fixture)
        self.assertEqual(result['status'], 'passed', diagnostic(result))
        self.assertEqual((result['native_required'], result['native_passed']), (66, 66))
        self.assertEqual(len(result['items']), 73)
        rows = {row['id']: row for row in result['items']}
        self.assertEqual(rows['no-effect-subsystem']['status'], 'not_applicable')
        self.assertEqual(rows['receipt-lookup-order']['status'], 'reviewed')
        self.assertEqual(fixture.reports['core']['qa']['status'], 'incomplete')
        self.assertEqual(fixture.reports['core']['delivery']['cases'][-1]['status'], 'incomplete')
        self.assertTrue(result['historical_reports_unchanged'])

    def test_different_runner_and_installed_overlay_bindings_are_preserved_per_lane(self):
        fixture = AuthoredFixture()
        lanes = fixture.expected['execution_lanes']
        for key in ('runner_sha256', 'loaded_closure_sha256', 'installed_clay_tree_sha256'):
            self.assertNotEqual(lanes['core'][key], lanes['gall_schedule'][key])
        self.assertEqual(self.call(fixture)['status'], 'passed')

    def test_missing_duplicate_unknown_or_optionalized_required_item_fails(self):
        for mode in ('missing', 'duplicate', 'unknown', 'optional'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                if mode in ('missing', 'optional'):
                    fixture.omit_items.add('receipt-lookup-order')
                    if mode == 'optional':
                        next(r for r in fixture.manifest['required'] if r['id'] == 'receipt-lookup-order')['optional'] = True
                    self.rejects(fixture)
                else:
                    def damage(bundle, artifacts):
                        extra = copy.deepcopy(bundle['items'][0])
                        if mode == 'unknown':
                            extra['id'] = 'unmanifested-claim'
                        bundle['items'].append(extra)
                    self.rejects(fixture, damage=damage)
        for mode in ('missing-manifest', 'manifest-digest', 'raw-manifest-hash',
                     'different-manifest-scope', 'reduced-manifest'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                if mode == 'raw-manifest-hash':
                    for report in fixture.reports.values():
                        for inputs in ('inputs_before', 'inputs_after'):
                            report[inputs]['qualification_manifest'] = '0' * 64
                elif mode in ('different-manifest-scope', 'reduced-manifest'):
                    if mode == 'different-manifest-scope':
                        fixture.manifest['scope'] = 'Unapproved substitute acceptance scope'
                    else:
                        removed = fixture.manifest['required'].pop()
                        del fixture.proofs[removed['id']]
                    # All supplied claims and declared raw hashes agree with
                    # the altered manifest; the frozen definition must still win.
                    fixture.manifest_raw = raw(fixture.manifest)
                    for report in fixture.reports.values():
                        for inputs in ('inputs_before', 'inputs_after'):
                            report[inputs]['qualification_manifest'] = digest(fixture.manifest_raw)
                    fixture.expected['execution_inputs'] = {
                        lane: copy.deepcopy(report['inputs_before'])
                        for lane, report in fixture.reports.items()}
                def damage(bundle, artifacts):
                    if mode == 'missing-manifest':
                        del bundle['manifest']
                    elif mode == 'manifest-digest':
                        bundle['manifest']['sha256'] = '0' * 64
                self.rejects(fixture, damage=damage)

    def test_each_binding_must_match_actual_lane_inputs_not_repeated_claim_metadata(self):
        for lane in ('core', 'gall_schedule'):
            for key in G.NATIVE_BINDINGS:
                with self.subTest(lane=lane, key=key):
                    fixture = AuthoredFixture()
                    fake = '0' * (40 if key == 'source_commit' else 64)
                    # An internally consistent index/proof/expected forgery must
                    # still disagree with the retained raw report and fail.
                    fixture.expected['execution_lanes'][lane][key] = fake
                    for proof in fixture.proofs.values():
                        if proof.get('execution_lane') == lane:
                            proof['bindings'][key] = fake
                    self.rejects(fixture)

    def test_source_drift_missing_source_manifest_and_incomplete_clay_comparison_fail(self):
        for mode in ('after-drift', 'missing-installed', 'empty-installed', 'missing-ship',
                     'missing-file', 'clay-mismatch', 'overlay-collision'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                core = fixture.reports['core']
                if mode == 'after-drift':
                    core['inputs_after']['runner']['core_test.py'] = '0' * 64
                elif mode == 'missing-installed':
                    del core['installed_files']
                elif mode == 'empty-installed':
                    core['installed_files'] = {}
                elif mode == 'missing-ship':
                    del core['installed_by_ship']['nec']
                elif mode == 'missing-file':
                    del core['clay_verified_by_ship']['bus']['app/stead-observer.hoon']
                elif mode == 'clay-mismatch':
                    core['clay_verified_by_ship']['bus']['app/stead-observer.hoon'] = '0' * 64
                else:
                    fixture.expected['schedule_source_files']['app/stead-home.hoon'] = named_digest('replacement')
                self.rejects(fixture)
        for lane in ('core', 'gall_schedule'):
            for mode in ('missing-final-commit', 'changed-final-commit'):
                with self.subTest(lane=lane, mode=mode):
                    fixture = AuthoredFixture()
                    if mode == 'missing-final-commit':
                        del fixture.reports[lane]['source_commit_after']
                    else:
                        fixture.reports[lane]['source_commit_after'] = '0' * 40
                    self.rejects(fixture)
        for lane, path in (('gall_schedule', ('gall',)),
                           ('core', ('runner', 'core_conn.py')),
                           ('gall_schedule', ('runner', 'core_conn.py')),
                           ('core', ('fixture',)), ('core', ('previous_freeze',))):
            with self.subTest(lane=lane, source_path=path):
                fixture = AuthoredFixture()
                # Before and after agree, and the nine summary bindings do
                # not change; the full expected input closure must detect it.
                for key in ('inputs_before', 'inputs_after'):
                    parent = fixture.reports[lane][key]
                    for part in path[:-1]:
                        parent = parent[part]
                    parent[path[-1]] = named_digest('different recorded input')
                self.rejects(fixture)

    def test_exact_deferred_ids_and_actual_skipped_checks_are_both_required(self):
        for mode in ('missing-id', 'unknown-id', 'duplicate-id', 'extra-skip', 'rewritten-pass', 'wrong-reason'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                core = fixture.reports['core']
                if mode == 'missing-id':
                    core['deferred_qa_requirements'].pop()
                elif mode == 'unknown-id':
                    core['deferred_qa_requirements'][0] = 'native-roundtrip-failure'
                elif mode == 'duplicate-id':
                    core['deferred_qa_requirements'].append('scoped-private-metadata')
                elif mode == 'extra-skip':
                    core['qa']['checks'].append(assertion('unreviewed-native-failure', 'skipped'))
                elif mode == 'rewritten-pass':
                    for row in core['qa']['checks']:
                        if row['status'] == 'skipped':
                            row['status'] = 'passed'
                else:
                    next(row for row in core['qa']['checks'] if row['status'] == 'skipped')['reason'] = 'No runtime available'
                self.rejects(fixture)

    def test_failed_or_incomplete_runtime_cannot_become_awaiting_review(self):
        for mode in ('top-fail', 'false-pass', 'missing-completion', 'wrong-case-count',
                     'roundtrip', 'missing-stage', 'failed-qa', 'empty-qa',
                     'not-run-delivery', 'extra-delivery-missing', 'qualification-failed',
                     'missing-recipe', 'missing-evaluator', 'empty-commands'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                core = fixture.reports['core']
                if mode == 'top-fail':
                    core['status'] = 'fail'
                elif mode == 'false-pass':
                    core['status'] = 'pass'
                elif mode == 'missing-completion':
                    del core['execution_status']
                elif mode == 'wrong-case-count':
                    core['qa']['case_counts'] = {'passed': 148}
                elif mode == 'roundtrip':
                    core['checks'].append({'name': 'owner-control:roundtrip', 'passed': False})
                    core['error'] = 'AssertionError: owner-control:roundtrip'
                elif mode == 'missing-stage':
                    del core['concurrent_submissions']
                elif mode == 'failed-qa':
                    core['qa']['cases'][0]['status'] = 'failed'
                elif mode == 'empty-qa':
                    core['qa']['cases'] = []
                elif mode == 'not-run-delivery':
                    core['delivery']['cases'][0]['status'] = 'not_run'
                elif mode == 'extra-delivery-missing':
                    core['delivery']['cases'][0].update(status='incomplete', missing=['Lost actual observer'])
                elif mode == 'qualification-failed':
                    core['qualification']['checks'][0]['passed'] = False
                elif mode == 'missing-recipe':
                    del core['qualification']['recipes']['history']
                elif mode == 'missing-evaluator':
                    del core['evaluator_controls']['invalid_input']
                else:
                    core['commands'] = []
                self.rejects(fixture)

    def test_empty_runtime_checks_calls_batches_and_observer_assertions_fail(self):
        for path in (('checks',), ('qa', 'checks'), ('delivery', 'calls'),
                     ('qualification', 'checks'), ('qualification', 'calls'),
                     ('qualification', 'batches'), ('delivery', 'cases', 0, 'assertions')):
            with self.subTest(path=path):
                fixture = AuthoredFixture()
                parent = fixture.reports['core']
                for part in path[:-1]:
                    parent = parent[part]
                parent[path[-1]] = []
                self.rejects(fixture)

    def test_arbitrary_truthy_native_or_wrong_report_pointer_is_not_execution_evidence(self):
        for native in ([{'AUTHORED MOCK': 'a label is not a retained native command'}], [],
                       [{'$execution': 'core', 'pointer': '/missing'}],
                       [{'$execution': 'core', 'pointer': '/qa/status'}],
                       [{'$execution': 'core', 'pointer': '/inputs_before'}],
                       [{'$execution': 'core', 'pointer': '/execution_guard'}],
                       [{'$execution': 'core', 'pointer': '/qualification/recipes/history'}],
                       [{'$execution': 'gall_schedule', 'pointer': '/commands/0'}]):
            with self.subTest(native=native):
                fixture = AuthoredFixture()
                fixture.proofs['v2-native-compile']['native'] = native
                self.rejects(fixture)

    def test_evaluator_raw_bytes_inventory_and_summaries_are_required(self):
        for mode in ('empty-bytes', 'missing-record', 'extra-record', 'wrong-argv', 'wrong-runtime',
                     'bool-exit', 'nonzero-exit', 'odd-hex', 'nonhex', 'oversized',
                     'wrong-input', 'silent-rejection', 'valid-frame-rejection', 'short-frame',
                     'bad-frame-length', 'disconnected-decode', 'changed-result',
                     'wrong-frame-hash', 'wrong-result-hash', 'wrong-raw-summary', 'wrong-diagnostic'):
            with self.subTest(mode=mode):
                controls = authored_evaluator_controls()
                commands = controls['commands']
                if mode == 'empty-bytes':
                    for row in commands:
                        row.update(input_hex='', stdout_hex='', stderr_hex='')
                elif mode == 'missing-record': commands.pop()
                elif mode == 'extra-record': commands.append(copy.deepcopy(commands[0]))
                elif mode == 'wrong-argv': commands[2]['argv'][4] = '-jn'
                elif mode == 'wrong-runtime': commands[0]['argv'][0] = '/runtime/../other'
                elif mode == 'bool-exit': commands[0]['exit_code'] = False
                elif mode == 'nonzero-exit': commands[0]['exit_code'] = -11
                elif mode == 'odd-hex': commands[0]['stdout_hex'] = '0'
                elif mode == 'nonhex': commands[0]['stdout_hex'] = 'gg'
                elif mode == 'oversized': commands[0]['stdout_hex'] = '00' * 1_000_001
                elif mode == 'wrong-input': commands[0]['input_hex'] = b']'.hex()
                elif mode == 'silent-rejection': commands[0]['stderr_hex'] = ''
                elif mode == 'valid-frame-rejection': commands[0]['stdout_hex'] = b'\0\1\0\0\0x'.hex()
                elif mode == 'short-frame': commands[1]['stdout_hex'] = b'\0\1\0\0\0x'.hex()
                elif mode == 'bad-frame-length': commands[1]['stdout_hex'] = controls['large_frame_hex'][:-2]
                elif mode == 'disconnected-decode': commands[2]['input_hex'] = '00'
                elif mode == 'changed-result': commands[2]['stdout_hex'] = b"[32 %avow 0 %noun %stead-core-result '7b7d']".hex()
                elif mode == 'wrong-frame-hash': controls['large_frame_sha256'] = '0' * 64
                elif mode == 'wrong-result-hash': controls['result_sha256'] = '0' * 64
                elif mode == 'wrong-raw-summary': controls['large_frame_hex'] = '00'
                elif mode == 'wrong-diagnostic': controls['encode_stderr'] = 'unobserved diagnostic'
                report = {'evaluator_controls': controls, 'commands': copy.deepcopy(commands)}
                with self.assertRaises(ValueError):
                    G.validate_evaluator_controls(report)
        controls = authored_evaluator_controls()
        with self.assertRaises(ValueError):
            G.validate_evaluator_controls({'evaluator_controls': controls,
                'commands': [dict(row, input_hex='00') for row in controls['commands']]})

    def test_evaluator_references_require_all_three_and_cannot_prove_ship_actions(self):
        fixture = AuthoredFixture()
        fixture.proofs['evaluator-error-boundaries']['classification'] = 'real-native-fake-ships'
        self.rejects(fixture)
        for pointers in ([1], [1, 1, 3], [3, 2, 1], [0, 2, 3]):
            with self.subTest(pointers=pointers):
                fixture = AuthoredFixture()
                fixture.proofs['evaluator-error-boundaries']['native'] = [
                    {'$execution': 'core', 'pointer': '/commands/' + str(index)} for index in pointers]
                self.rejects(fixture)
        for camouflage in (False, True):
            with self.subTest(camouflage=camouflage):
                fixture = AuthoredFixture()
                fixture.proofs['v2-native-compile']['native'] = [{'$execution': 'core', 'pointer': '/commands/1'}]
                if camouflage:
                    for rows in (fixture.reports['core']['commands'][1:],
                                 fixture.reports['core']['evaluator_controls']['commands']):
                        rows[0].update(ship='zod', dojo='AUTHORED non-Dojo evaluator', result='')
                self.rejects(fixture)

    def test_historical_guard_records_keep_original_binding_with_exact_current_review(self):
        fixture, attach = self.historical_fixture()
        result = self.call(fixture, damage=attach)
        self.assertEqual(result['status'], 'passed', diagnostic(result))
        rows = {row['id']: row for row in result['items']}
        self.assertEqual(rows['guard-real-hot-preflight-refusal']['bindings']['guard_sha256'],
                         '7166d197a6e3879f21c22637f2bd3074ff90975c33a2149f6e07763e2eeaa04e')
        self.assertEqual(rows['guard-negative-host-tests']['bindings']['guard_sha256'], fixture.expected['guard_sha256'])
        self.rejects(fixture)

    def test_historical_guard_bridge_rejects_other_changes_and_missing_current_evidence(self):
        fixture, attach = self.historical_fixture(current_extra=b'\n# an additional unreviewed source change\n')
        self.rejects(fixture, damage=attach)
        for mode in ('owner-review', 'unknown-change', 'extra-requirement', 'wrong-current-review',
                     'changed-original-bytes', 'changed-original-ref', 'missing-host-output'):
            with self.subTest(mode=mode):
                fixture, attach = self.historical_fixture()
                def damage(bundle, artifacts):
                    attach(bundle, artifacts)
                    review = json.loads(artifacts['continuity.json'])
                    if mode == 'owner-review': review['reviewer'] = '/root'
                    elif mode == 'unknown-change': review['change_id'] = 'accept-any-later-guard'
                    elif mode == 'extra-requirement': review['historical_artifacts']['v2-native-compile'] = []
                    elif mode == 'wrong-current-review': review['current_source_review'] = review['current_host_tests']
                    elif mode == 'changed-original-bytes':
                        path = review['historical_artifacts']['guard-real-hot-preflight-refusal'][0]['path']
                        artifacts[path] += b' changed'
                    elif mode == 'changed-original-ref':
                        review['historical_artifacts']['guard-real-hot-preflight-refusal'][0]['sha256'] = '0' * 64
                    elif mode == 'missing-host-output': artifacts.pop('authored-host.log')
                    artifacts['continuity.json'] = raw(review)
                    bundle['historical_guard_continuity']['sha256'] = digest(artifacts['continuity.json'])
                self.rejects(fixture, damage=damage)

    def test_missing_reader_wrong_hash_missing_artifact_and_changed_transcript_fail(self):
        self.rejects(AuthoredFixture(), reader=False)
        for mode in ('index-hash', 'raw-hash', 'missing-artifact', 'transcript-bytes', 'record-hash'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                if mode == 'record-hash':
                    fixture.reports['core']['commands'][0]['transcript']['record_sha256'] = '0' * 64
                def damage(bundle, artifacts):
                    if mode == 'index-hash':
                        bundle['items'][0]['artifact']['sha256'] = '0' * 64
                    elif mode == 'raw-hash':
                        bundle['executions']['core']['sha256'] = '0' * 64
                    elif mode == 'missing-artifact':
                        del artifacts['core.json']
                    elif mode == 'transcript-bytes':
                        artifacts['transport.jsonl.gz'] += b'changed'
                self.rejects(fixture, damage=damage)

    def test_native_assertions_must_be_nonempty_complete_successful_and_unique(self):
        for mode in ('empty', 'missing-name', 'failed', 'skipped', 'duplicate'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                proof = fixture.proofs['v2-context-controls']
                if mode == 'empty':
                    proof['assertions'] = []
                elif mode == 'missing-name':
                    proof['assertions'][0]['name'] = 'different-control'
                elif mode in ('failed', 'skipped'):
                    proof['assertions'][0]['status'] = mode
                else:
                    proof['assertions'] *= 2
                self.rejects(fixture)

    def test_guard_must_be_retained_completed_and_bound_to_exact_execution(self):
        for lane in ('core', 'gall_schedule'):
            for field, value in (('status', 'failed'), ('status', 'running'), ('exit_code', 1),
                                 ('launched', False), ('run_id', 'f' * 32),
                                 ('guard_sha256', '0' * 64), ('reason', 'thermal stop')):
                with self.subTest(lane=lane, field=field, value=value):
                    fixture = AuthoredFixture()
                    fixture.guards[lane][field] = value
                    self.rejects(fixture)
        def missing(bundle, artifacts):
            del bundle['guards']['gall_schedule']
        self.rejects(AuthoredFixture(), damage=missing)
        fixture = AuthoredFixture()
        fixture.expected['guard_sha256'] = named_digest('different unexecuted guard')
        for proof in fixture.proofs.values():
            if 'guard_sha256' in proof['bindings']:
                proof['bindings']['guard_sha256'] = fixture.expected['guard_sha256']
        self.rejects(fixture)

    def test_independent_source_and_na_dispositions_cannot_be_self_approved_or_retyped(self):
        for identifier in ('no-effect-subsystem', 'receipt-lookup-order'):
            for mode in ('self', 'unknown-reviewer', 'missing-reviewer', 'stale-source',
                         'empty-source', 'passed-status', 'empty-scope'):
                with self.subTest(identifier=identifier, mode=mode):
                    fixture = AuthoredFixture()
                    proof = fixture.proofs[identifier]
                    if mode == 'self':
                        proof['reviewer'] = '/root'
                        fixture.expected['independent_reviewers'].append('/root')
                    elif mode == 'unknown-reviewer':
                        proof['reviewer'] = '/root/unassigned_agent'
                    elif mode == 'missing-reviewer':
                        del proof['reviewer']
                    elif mode == 'stale-source':
                        proof['reviewed_source_files']['native/core/desk/app/stead-home.hoon'] = '0' * 64
                    elif mode == 'empty-source':
                        proof['reviewed_source_files'] = {}
                    elif mode == 'passed-status':
                        proof['status'] = 'passed'
                    else:
                        proof['scope'] = ''
                    self.rejects(fixture)
        fixture = AuthoredFixture()
        del fixture.proofs['no-effect-subsystem']['reason']
        self.rejects(fixture)

    def test_scoped_native_privacy_cannot_be_resolved_by_source_review_or_na(self):
        for kind in ('source_review', 'not_applicable'):
            with self.subTest(kind=kind):
                fixture = AuthoredFixture()
                fixture.proofs['scoped-private-metadata'].update(kind=kind, status=G.DISPOSITION[kind])
                self.rejects(fixture)

    def test_scheduled_gall_classification_is_allowed_only_for_late_old_leave(self):
        fixture = AuthoredFixture()
        fixture.proofs['delivery-leave-cancels'].update(
            classification='native-scheduled-gall', execution_lane='gall_schedule',
            bindings=copy.deepcopy(fixture.expected['execution_lanes']['gall_schedule']),
            native=[{'$execution': 'gall_schedule', 'pointer': '/commands/0'}])
        self.rejects(fixture)
        fixture = AuthoredFixture()
        fixture.reports['gall_schedule']['requirement'] = 'delivery-leave-cancels'
        self.rejects(fixture)

    def test_schedule_requires_actual_positive_payload_and_specific_runtime_negative(self):
        for mode in ('missing-positive', 'invalid-positive', 'missing-negative', 'compile-error',
                     'wrong-count', 'wrong-command', 'failed-check', 'forged-positive-label'):
            with self.subTest(mode=mode):
                fixture = AuthoredFixture()
                report = fixture.reports['gall_schedule']
                if mode == 'missing-positive':
                    del report['positive']
                elif mode == 'invalid-positive':
                    report['positive']['requirement'] = 'wrong-scope'
                elif mode == 'missing-negative':
                    del report['negative_control']
                elif mode == 'compile-error':
                    report['commands'][1].update(log='mint-nice\n', log_bytes=10,
                                                 log_sha256=digest(b'mint-nice\n'))
                elif mode == 'wrong-count':
                    diagnostic = '[%stead-scheduled-gall-pending-control 3 1]\n'
                    report['commands'][1].update(log=diagnostic, log_bytes=len(diagnostic),
                                                 log_sha256=digest(diagnostic.encode()))
                elif mode == 'wrong-command':
                    report['commands'][1]['dojo'] = '+unrelated-negative'
                elif mode == 'failed-check':
                    report['checks'][0]['passed'] = False
                else:
                    report['positive_validation'] = {'status': 'passed', 'assertions': []}
                self.rejects(fixture)


if __name__ == '__main__':
    unittest.main(verbosity=2)

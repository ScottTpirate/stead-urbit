"""Synthetic failed-worker disclosure/admission controls; no native claim."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/ci'), str(ROOT / 'scripts/urbit')]
import worker_failure as failure
import worker_result
import worker
import owned_child


class FailureProjectionTests(unittest.TestCase):
    def test_source_spans_require_admitted_source_and_exact_byte_bounds(self):
        source = 'native/core/desk/lib/stead-fixture.hoon'
        sources = {source: b'first\nsecond\n'}
        raw = (self.secret + '\n/lib/stead-fixture/hoon:<[1 2].[2 6]>\n'
               '/lib/unknown/hoon:<[1 1].[2 1]>\n'
               '/lib/stead-fixture/hoon:<[0 1].[1 1]>\n'
               '/lib/stead-fixture/hoon:<[1 1].[9 1]>\n'
               '/lib/stead-fixture/hoon:<[1 7].[2 1]>\n'
               '/lib/stead-fixture/hoon:<[2 6].[2 1]>\n'
               'private/lib/stead-fixture/hoon:<[1 1].[1 2]>\n'
               '/lib/stead-fixture/hoon:<[1 2].[2 6]>').encode()
        self.value['native']['native_unit_transcripts'] = [{'log_hex': raw.hex()}]
        observed = failure.project(self.frame(), self.inputs, run_id=self.run, sources=sources)
        self.assertEqual(observed['native']['last_unit']['source_spans'], {'locations': [{
            'path': source, 'start_line': 1, 'start_column': 2, 'end_line': 2, 'end_column': 6}], 'truncated': False})
        self.assertNotIn(self.secret, json.dumps(observed))
        self.assertEqual(failure.source_spans(raw, None), {'locations': [], 'truncated': False})
        for malformed in ([], {'x': b''} | {str(i): b'' for i in range(513)}, {source: 'private'}):
            with self.subTest(source_type=type(malformed).__name__), self.assertRaises(ValueError):
                failure.source_spans(raw, malformed)

    def test_source_spans_are_unique_and_capped_at_sixteen(self):
        path = 'native/core/desk/tests/stead-fixture.hoon'
        raw = '\n'.join(f'/tests/stead-fixture/hoon:<[{n} 1].[{n} 2]>' for n in range(1, 19)).encode()
        result = failure.source_spans(raw, {path: b'x\n' * 18})
        self.assertEqual(len(result['locations']), 16)
        self.assertEqual(result['locations'][-1]['start_line'], 16)
        self.assertTrue(result['truncated'])

    def test_last_unit_reports_only_registered_names_and_closed_verdicts(self):
        inventory = json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_bytes())
        suite = next(row for row in inventory['suites'] if row['path'] == '/tests/stead-workspace-views')
        arm = suite['arms'][0]
        raw = ('private ' + self.secret + '\nnest-fail\n'
               + 'FAILED ' + suite['path'] + '/' + arm + '\n'
               + 'CRASHED ' + suite['path'] + '/' + self.secret + '\n'
               + 'OK /tests/stead-unknown/' + arm + '\n').encode()
        self.value['native']['native_unit_transcripts'] = [{
            'path': suite['path'], 'log_hex': raw.hex(), 'terminal': '[32 %avow 0 %noun 1]'}]
        observed = failure.project(self.frame(), self.inputs, run_id=self.run, inventory=inventory)
        row = observed['native']['last_unit']
        self.assertEqual(row['path'], suite['path'])
        self.assertEqual(row['registered_arm_observations'], [{'arm': arm, 'outcome': 'FAILED'}])
        self.assertTrue(row['markers']['nest-fail'])
        self.assertEqual(row['log_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse(observed['qualifies_phase'])
        self.assertNotIn(self.secret, json.dumps(observed))
        self.assertNotIn(raw.hex(), json.dumps(observed))
        self.value['native']['native_unit_transcripts'][0]['path'] = self.secret
        self.value['native']['native_unit_transcripts'][0]['terminal'] = self.secret
        unknown = failure.project(self.frame(), self.inputs, run_id=self.run, inventory=inventory)['native']['last_unit']
        self.assertEqual(unknown['path'], 'unrecognized')
        self.assertEqual(unknown['terminal'], 'unrecognized')
        self.assertEqual(unknown['registered_arm_observations'], [])

    def test_last_unit_requires_bounded_hex_and_registered_inventory(self):
        for value in (None, {}, [{}] * 101, [None], [{'log_hex': 'z0'}], [{'log_hex': '00' * 262145}]):
            self.value['native']['native_unit_transcripts'] = value
            with self.subTest(value=str(value)[:60]), self.assertRaises(ValueError):
                self.project()
        self.value['native']['native_unit_transcripts'] = [{'path': '/tests/stead-workspace-views',
            'log_hex': ('exit\nFAILED /tests/stead-workspace-views/' + self.secret).encode().hex()}]
        observed = self.project()['native']['last_unit']
        self.assertEqual(observed['path'], 'unrecognized')
        self.assertEqual(observed['registered_arm_observations'], [])
        self.assertTrue(observed['markers']['exit'])

    def test_last_unit_rejects_duplicate_and_contradictory_registered_verdicts(self):
        inventory = json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_bytes())
        suite = inventory['suites'][0]
        name = suite['path'] + '/' + suite['arms'][0]
        for outcomes in (('OK', 'OK'), ('OK', 'FAILED')):
            raw = '\n'.join(outcome + ' ' + name for outcome in outcomes).encode()
            self.value['native']['native_unit_transcripts'] = [{'path': suite['path'], 'log_hex': raw.hex()}]
            with self.subTest(outcomes=outcomes), self.assertRaises(ValueError):
                failure.project(self.frame(), self.inputs, run_id=self.run, inventory=inventory)

    def test_first_ingress_retirement_uses_only_closed_codes(self):
        self.value['native']['admission_failure'] = {'ingress_retirement': {
            'cause': 'guard-refusal', 'error': 'control-input', 'extra': self.secret}}
        observed = self.project()['native']['admission']['ingress_retirement']
        self.assertEqual(observed, {'cause': 'guard-refusal', 'error': 'control-input'})
        self.assertNotIn(self.secret, json.dumps(self.project()))
        self.value['native']['admission_failure']['ingress_retirement'] = {'cause': self.secret, 'error': self.secret}
        self.assertEqual(self.project()['native']['admission']['ingress_retirement'],
                         {'cause': 'unrecognized', 'error': 'unrecognized'})
        for bad in (None, [], self.secret):
            self.value['native']['admission_failure']['ingress_retirement'] = bad
            with self.subTest(value=bad), self.assertRaises(ValueError):
                self.project()

    def test_bootstrap_failures_use_fixed_codes_without_response_content(self):
        examples = [(ship + '-' + assertion, ship + '-' + reason)
                    for ship in failure.SHIPS
                    for assertion, reason in (('owner-bootstrap-acknowledged', 'initial-bootstrap'),
                                              ('restart-fresh-bootstrap', 'restart-bootstrap'))]
        examples += [('Native bootstrap readiness not acknowledged', 'bootstrap-readiness'),
                     ('Native bootstrap acknowledgement differs', 'bootstrap-ack'),
                     ('Native bootstrap owner changed', 'bootstrap-owner-changed'),
                     ('Native bootstrap readiness budget exhausted', 'bootstrap-budget'),
                     ('Native bootstrap acknowledgement arrived after deadline', 'bootstrap-late')]
        for message, reason in examples:
            with self.subTest(message=message):
                self.value['native']['error'] = 'AssertionError: ' + message
                self.assertEqual(self.project()['native']['error']['reason'], reason)
                self.value['native']['error'] += self.secret
                projected = self.project()
                self.assertEqual(projected['native']['error']['reason'], 'unrecognized')
                self.assertNotIn(self.secret, json.dumps(projected))

    def test_native_control_reason_is_closed_and_discards_appended_content(self):
        for message, reason in (('Specific compiler failure absent','control-compiler-diagnostic'),
                ('Native timer ignored client timeout','control-timeout-absent'),
                ('Missing arm fixture failed before discovery','control-missing-arm-fixture')):
            self.assertEqual(failure.error_kind('ValueError: '+message),{'class':'ValueError','reason':reason})
            self.assertEqual(failure.error_kind('ValueError: '+message+' private content'),
                {'class':'ValueError','reason':'unrecognized'})

    def setUp(self):
        self.run = 'a' * 32
        self.inputs = {'expected_native_inputs': {'native': 'b' * 64}}
        self.secret = 'PRIVATE_SESSION_AND_DOJO_VALUE_123'
        self.value = {'format': 'stead.local-ci-worker/1', 'status': 'fail', 'run_id': self.run,
                      'inputs_sha256': hashlib.sha256(worker_result.canonical(self.inputs)).hexdigest(),
                      'cleanup': True, 'error': 'TimeoutError: zod did not become ready within 1200s',
                      'diagnostic': {'stage': 'fresh-ready', 'ship': 'zod', 'pre_cleanup': {
                          'zod': {'started': True, 'exit_code': None, 'ports_present': True,
                                  'conn_present': True, 'kernel_ready_observed': False}}},
                      'native': {'error': 'ValueError: ' + self.secret,
                          'checks': [{'name': self.secret, 'passed': True}, {'name': self.secret, 'passed': False}],
                          'commands': [{'dojo': self.secret, 'result': self.secret}],
                          'inputs_before': self.inputs['expected_native_inputs'],
                          'inputs_after': self.inputs['expected_native_inputs'],
                          'native_failure': {'stage': 'response-header', 'error': self.secret,
                                             'request': self.secret, 'response_frame_hex': self.secret}},
                      'failure_logs': {'zod': {'bytes_total': 100, 'tail_hex': (self.secret + '\nhttp: live').encode().hex(),
                                               'truncated': False}}}

    def frame(self, value=None):
        return (self.secret + '\n' + worker_result.PREFIX + json.dumps(self.value if value is None else value) + '\n').encode()

    def project(self, value=None):
        return failure.project(self.frame(value), self.inputs, run_id=self.run)

    def test_closed_projection_retains_location_but_no_private_text(self):
        result = self.project()
        encoded = json.dumps(result)
        for secret in (self.secret, self.secret.encode().hex(), self.value['error']):
            self.assertNotIn(secret, encoded)
        self.assertEqual(result['stage'], 'fresh-ready')
        self.assertEqual(result['ship'], 'zod')
        self.assertEqual(result['error'], {'class': 'TimeoutError', 'reason': 'ready-timeout'})
        self.assertEqual(result['native']['error']['reason'], 'unrecognized')
        self.assertEqual(result['native']['checks_passed'], 1)
        self.assertEqual(result['native']['checks_failed'], 1)
        self.assertEqual(result['native']['frame_stage'], 'response-header')
        self.assertTrue(result['native']['inputs_match'])
        self.assertTrue(result['log_observations']['zod']['markers']['http_live'])
        self.assertFalse(result['qualifies_phase'])
        self.assertNotIn('status', result)

    def test_wrong_run_input_format_or_pass_are_not_diagnostic_admission(self):
        for change in ({'status': 'pass'}, {'run_id': 'c' * 32}, {'inputs_sha256': 'd' * 64},
                       {'format': 'stead-other/1'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.project(self.value | change)

    def test_admission_location_is_closed_and_preserves_original_and_rollback_codes(self):
        value = copy.deepcopy(self.value)
        value['native']['checks'] += [{'name': 'nec-owner-bootstrap-acknowledged', 'passed': True},
                                     {'name': 'nec-owned-peer-admission', 'passed': False}]
        value['native']['admission_failure'] = {
            'ship': 'nec', 'mode': 'initial', 'step': 'tls-verify',
            'error': 'ValueError: TLS listener is not exclusively owned by the current native child',
            'rollback_errors': ['OSError: ' + self.secret], 'nonce': self.secret}
        result = self.project(value)
        admission = result['native']['admission']
        self.assertEqual(admission['last_completed_check'], 'nec-owner-bootstrap-acknowledged')
        self.assertEqual(admission['error']['reason'], 'tls-listener-ownership')
        self.assertEqual(admission['rollback_errors'], [{'class': 'OSError', 'reason': 'unrecognized'}])
        self.assertNotIn(self.secret, json.dumps(result))
        for key in ('ship', 'mode', 'step', 'error'):
            value['native']['admission_failure'][key] = self.secret
        value['native']['checks'][-2]['name'] += self.secret
        result = self.project(value)
        self.assertNotIn(self.secret, json.dumps(result))
        self.assertEqual(result['native']['admission']['last_completed_check'], 'unrecognized')
        self.assertEqual(result['native']['admission']['step'], 'unrecognized')

    def test_admission_projection_rejects_unbounded_or_malformed_shapes(self):
        for admission in ([], {'rollback_errors': {}}, {'rollback_errors': ['private'] * 3}):
            value = copy.deepcopy(self.value)
            value['native']['admission_failure'] = admission
            with self.subTest(admission=admission), self.assertRaises(ValueError):
                self.project(value)

    def test_filesystem_diagnostics_are_exact_closed_categories(self):
        for message, reason in [('Unexpected seed refusal', 'seed-refusal'),
                                ('Unexpected cache write refusal', 'cache-errno'),
                                ('Cache mount is writable', 'cache-mount')]:
            with self.subTest(message=message):
                self.assertEqual(failure.error_kind('ValueError: ' + message),
                                 {'class': 'ValueError', 'reason': reason})
                self.assertEqual(failure.error_kind('ValueError: ' + message + self.secret)['reason'],
                                 'unrecognized')

    def test_capabilities_assertions_are_closed_codes_without_native_values(self):
        for name, reason in [('native-public-capabilities-current-member', 'capabilities-member'),
                             ('native-capabilities-unbound-sender-denied', 'capabilities-denial')]:
            value = copy.deepcopy(self.value)
            value['native']['error'] = 'AssertionError: ' + name
            self.assertEqual(self.project(value)['native']['error'],
                             {'class': 'AssertionError', 'reason': reason})
            value['native']['error'] += self.secret
            result = self.project(value)
            self.assertEqual(result['native']['error']['reason'], 'unrecognized')
            self.assertNotIn(self.secret, json.dumps(result))

    def test_empty_duplicate_truncated_nonfinal_invalid_utf8_and_oversized_frames_refused(self):
        raw = self.frame()
        duplicate = raw.replace(b'"status": "fail"', b'"status": "fail", "status": "fail"')
        for altered in (b'', raw + raw, raw[:-2], raw + b'after\n', b'\xff' + raw, duplicate,
                        b'x' * (32 * 1024**2 + 1)):
            with self.subTest(length=len(altered)), self.assertRaises((ValueError, UnicodeError)):
                failure.project(altered, self.inputs, run_id=self.run)

    def test_migration_diagnostics_are_bounded_closed_and_separate_from_logs(self):
        value = copy.deepcopy(self.value)
        output = self.secret + '\n%stead-ci-migration-grants\nnest-fail'
        value['migration'] = {'output': output, 'source_sha256': self.secret}
        value['failure_logs']['zod']['tail_hex'] = b'find-fork\n%stead-ci-migration-roundtrip'.hex()
        result = self.project(value)
        self.assertNotIn(self.secret, json.dumps(result))
        observed = result['migration']
        self.assertTrue(observed['present'])
        self.assertEqual(observed['output_bytes'], len(output.encode()))
        self.assertEqual(observed['output_sha256'], hashlib.sha256(output.encode()).hexdigest())
        self.assertTrue(observed['markers']['stead-ci-migration-grants'])
        self.assertTrue(observed['markers']['nest-fail'])
        self.assertFalse(observed['markers']['stead-ci-migration-roundtrip'])
        self.assertFalse(observed['markers']['find-fork'])
        value['migration']['output'] = 'not-nest-fail-private'
        self.assertFalse(self.project(value)['migration']['markers']['nest-fail'])
        value['migration']['output'] = '%generator-build-fail'
        self.assertTrue(self.project(value)['migration']['markers']['generator-build-fail'])
        self.assertFalse(self.project(value)['migration']['markers']['build-fail'])
        value['migration']['output'] = 'private-generator-build-fail-private'
        self.assertFalse(self.project(value)['migration']['markers']['generator-build-fail'])
        self.assertFalse(self.project()['migration']['present'])

    def test_migration_output_shapes_and_byte_bounds_fail_closed(self):
        for migration in ([], {'output': []}, {'output': 1}, {'output': 'x' * 1_000_001},
                          {'output': '\u96ea' * 333334}):
            with self.subTest(shape=type(migration).__name__), self.assertRaises(ValueError):
                self.project(self.value | {'migration': migration})

    def test_free_text_or_bad_numeric_fields_cannot_escape_projection(self):
        value = copy.deepcopy(self.value)
        value['diagnostic'].update(stage=self.secret, ship=self.secret)
        value['diagnostic']['pre_cleanup']['zod'].update(exit_code=True, started=self.secret)
        value['native']['native_failure']['stage'] = self.secret
        value['native']['inputs_after'] = {}
        value['failure_logs']['zod'].update(bytes_total=True)
        value['cleanup_error'] = self.secret + ': ' + self.secret
        result = self.project(value)
        self.assertNotIn(self.secret, json.dumps(result))
        self.assertEqual(result['stage'], 'unrecognized')
        self.assertIsNone(result['pre_cleanup']['zod']['exit_code'])
        self.assertFalse(result['pre_cleanup']['zod']['started'])
        self.assertIsNone(result['log_observations']['zod']['bytes_total'])
        self.assertFalse(result['native']['inputs_match'])

    def test_malformed_or_unbounded_private_shapes_refused(self):
        for change in ({'diagnostic': []}, {'native': []}, {'native': {'checks': [None] * 2001}},
                       {'failure_logs': {'zod': {'tail_hex': '00' * 262145}}},
                       {'failure_logs': {'zod': {'tail_hex': 'xx'}}}):
            with self.subTest(keys=list(change)), self.assertRaises(ValueError):
                self.project(self.value | change)

    def test_diagnostic_snapshot_failure_cannot_prevent_cleanup(self):
        with patch.object(failure, 'snapshot', side_effect=OSError(self.secret)):
            self.assertEqual(failure.capture_snapshot(object()), {})

    def test_failed_frame_is_not_successful_verification(self):
        with self.assertRaises(ValueError):
            worker_result.verify(self.frame(), self.inputs, run_id=self.run, inventory={})

    def test_boot_error_survives_cleanup_error_and_launcher_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'logs').mkdir()
            child = Mock(pid=123)
            launcher = Mock()
            launcher.spawn.return_value = child
            host = SimpleNamespace(LIVE=root / 'live', STATE=root, SHIPS=('zod',),
                LOCK={'runtime': {'binary': 'unused'}, 'boot_artifact': {'archive': 'unused'}},
                LOGS={}, PROCESSES={}, EVIDENCE=[], gate=Mock(), execution_check=Mock(), record=Mock(),
                wait_ready=Mock(side_effect=TimeoutError('zod did not become ready within 1200s')),
                all_stop=Mock(side_effect=OSError(self.secret)))
            progress = {}
            try:
                with patch.object(owned_child, 'ChildLauncher', return_value=launcher), \
                     patch.object(worker, 'capture_snapshot', return_value={'observed': True}):
                    with self.assertRaisesRegex(TimeoutError, 'did not become ready'):
                        worker.fresh_seeds(host, progress)
                launcher.close.assert_called_once()
                self.assertEqual(progress['stage'], 'fresh-ready')
                self.assertEqual(progress['pre_cleanup'], {'observed': True})
                self.assertTrue(progress['initiating_error'].startswith('TimeoutError:'))
                self.assertEqual(len(progress['seed_cleanup_errors']), 1)
            finally:
                for log in host.LOGS.values():
                    log.close()


if __name__ == '__main__':
    unittest.main()

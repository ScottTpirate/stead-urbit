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

"""Host-only CI boundary controls; these never claim native execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/ci'), str(ROOT / 'scripts/urbit')]
import local
import core_conn
import native_units
import worker_result as result
from gall_schedule_proof import _jam, _atom


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.controller = {name: b'controller' for name in (
            'native/core/desk/app/stead-home.hoon', 'native/core/desk/lib/stead-core.hoon',
            'native/core/desk/lib/stead-git.hoon', 'native/core/desk/lib/stead-core-v1.hoon',
            'native/core/desk/lib/stead-codec-v1.hoon', 'native/core/desk/tests/stead-session.hoon',
            'native/core/desk/ted/stead-team-client.hoon', 'scripts/ci/migration.hoon',
            'scripts/ci/controls/missing.hoon', 'scripts/ci/controls/compiler.hoon',
            'scripts/ci/controls/delay.hoon')}
        self.candidate = {name: raw for name, raw in self.controller.items() if name.startswith('native/')}

    def test_product_changes_are_selected_and_test_bytes_frozen(self):
        self.candidate['native/core/desk/app/stead-home.hoon'] = b'candidate'
        composed, selected = local.compose(self.controller, self.candidate)
        self.assertEqual(composed['native/core/desk/app/stead-home.hoon'], b'candidate')
        self.assertEqual(composed['native/core/desk/gen/stead-ci-migration-probe.hoon'], b'controller')
        self.assertNotIn('native/core/desk/tests/stead-session.hoon', selected)

    def test_candidate_cannot_replace_test_client_or_predecessor_closure(self):
        for name in ('tests/stead-session.hoon', 'ted/stead-team-client.hoon',
                     'lib/stead-git.hoon', 'lib/stead-core-v1.hoon', 'lib/stead-codec-v1.hoon'):
            with self.subTest(name=name):
                altered = self.candidate | {'native/core/desk/' + name: b'poison'}
                with self.assertRaisesRegex(ValueError, 'collision'):
                    local.compose(self.controller, altered)

    def test_deleted_predecessor_dependency_is_not_silently_restored(self):
        for library in ('stead-git.hoon', 'stead-core-v1.hoon', 'stead-codec-v1.hoon'):
            altered = {name: raw for name, raw in self.candidate.items() if not name.endswith('/' + library)}
            with self.subTest(library=library), self.assertRaises(ValueError):
                local.compose(self.controller, altered)

    def test_missing_product_unknown_input_and_control_collision_fail(self):
        for altered in (self.candidate | {'native/core/desk/lib/new.hoon': b'unknown'},
                        self.candidate | {'native/core/desk/gen/stead-ci-migration-probe.hoon': b'poison'},
                        {name: raw for name, raw in self.candidate.items() if not name.endswith('stead-home.hoon')}):
            with self.assertRaises(ValueError):
                local.compose(self.controller, altered)


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_text())
        self.run = 'a' * 32
        h = 'b' * 64
        self.inputs = {'controller_files': {'scripts/ci/migration.hoon': {'sha256': h},
            'specs/urbit/toolchain.lock.json': {'sha256': h}}, 'composed_files': {},
            'runtime_binary_sha256': h, 'expected_native_inputs': {'toolchain': h}}
        mounts = {prefix: {name[len(prefix) + 1:]: item['sha256'] for name, item in self.inputs['controller_files'].items()
                          if name.startswith(prefix + '/')} for prefix in ('scripts/urbit', 'scripts/ci', 'specs/urbit', 'web/dev')}
        mounts['native'] = {}
        digest = hashlib.sha256(result.canonical(mounts)).hexdigest()
        names = ['configured-startup-controller-present', 'explicit-creator-project-accepted',
                 'duplicate-native-command-idempotent', 'ungranted-member-no-project',
                 'native-reader-write-denied', 'native-maintainer-write-accepted',
                 'native-stale-revision-rejected', 'restart-preserves-exact-command-receipt',
                 'restart-preserves-authorized-work', 'restart-invalidates-native-update-cursor-and-watch']
        units, transcripts, commands = [], [], []
        for entry in [*self.inventory['suites'], self.inventory['negative_control']]:
            negative = 'marker' in entry
            raw = 'built   ' + entry['path'] + '/hoon\n'
            if negative:
                raw += entry['marker'] + '\n'
            raw += ''.join(('FAILED' if negative else 'OK') + ' ' + entry['path'] + '/' + arm + '\n' for arm in entry['arms'])
            terminal = '[32 %avow 0 %noun ' + ('1' if negative else '0') + ']'
            units.append(native_units.verify_output(raw + '\n' + terminal, path=entry['path'], expected=entry['arms'],
                succeeds=not negative, failure_marker=entry.get('marker')))
            transcripts.append({'path': entry['path'], 'log_hex': raw.encode().hex(), 'log_bytes': len(raw.encode()), 'terminal': terminal})
            jam = _jam((32, (_atom('avow'), (0, (_atom('noun'), 1 if negative else 0)))))
            frame = b'\0' + len(jam).to_bytes(4, 'little') + jam
            commands.append({'ship': 'zod', 'native_test': {'resolved_path': '/~zod/base/~2026.9.27' + entry['path'],
                'stdout': terminal, 'timeout_seconds': entry.get('timeout_seconds', 60),
                'response_frame_hex': frame.hex(), 'response_frame_sha256': hashlib.sha256(frame).hexdigest()}})
        self.value = {'format': 'stead.local-ci-worker/1', 'status': 'pass', 'run_id': self.run,
            'inputs_sha256': hashlib.sha256(result.canonical(self.inputs)).hexdigest(), 'cleanup': True,
            'admission': {'status': 'admitted', 'run_id': self.run}, 'mounts_before': digest, 'mounts_after': digest,
            'isolation': {'private_network': True, 'host_credentials_absent': True, 'fresh_state': True, 'external_route_absent': True},
            'fresh_seeds': {'format': 1, 'toolchain_sha256': h, 'ships': {name: h for name in ('zod', 'bus', 'nec', 'bud')}},
            'migration': {'source_sha256': h, 'output': '%stead-ci-supported-migration-pass'},
            'native': {'status': 'pass', 'stage': 'completed', 'classification': 'local-real-configured-gall-development',
                'inputs_before': self.inputs['expected_native_inputs'], 'inputs_after': self.inputs['expected_native_inputs'],
                'execution_guard': {'run_id': self.run}, 'installed': {name: {} for name in ('zod', 'bus', 'nec', 'bud')},
                'checks': [{'name': name, 'passed': True} for name in names],
                'restarts': {name: {'passed': True} for name in ('zod', 'bus', 'nec', 'bud')},
                'native_units': units, 'native_unit_transcripts': transcripts, 'commands': commands}}
        # Synthetic records below are solely verifier controls. They are never
        # used by the actual worker or published as native observations.
        self.value['filesystem_controls'] = {'classification': 'real-disposable-filesystem-controls',
            'seed_before': h, 'seed_poisoned': 'c' * 64, 'seed_after': h,
            'seed_refusal': 'Seed integrity failure: zod', 'runtime_expected': h, 'runtime_after': h,
            'owned_truncated_sha256': 'd' * 64, 'cache_mount_read_only': True,
            'cache_write_errno': 30, 'cache_pin_refused': True}
        missing = copy.deepcopy(commands[0]['native_test'])
        missing['resolved_path'] = '/~zod/base/~2026.9.27/controls/stead-ci-missing'
        def unit_request(path):
            resolved = '/~zod/base/~2026.9.27' + path
            parts = resolved.split('/')[1:]
            atoms = ' '.join(core_conn.atom(part.encode()) for part in parts)
            beam = 0
            for part in reversed(parts):
                beam = (_atom(part), beam)
            jam = _jam((32, (_atom('fyrd'), (_atom('base'), (_atom('test'), (_atom('noun'), (_atom('path'), beam)))))))
            return {'resolved_path': resolved, 'timeout_seconds': 60,
                'request': f'[32 %fyrd [%base %test %noun [%path [{atoms} ~]]]]',
                'encoded_frame_hex': (b'\0' + len(jam).to_bytes(4, 'little') + jam).hex()}
        missing.update(unit_request('/controls/stead-ci-missing'))
        compiler_jam = _jam((32, (_atom('avow'), 1)))
        compiler_frame = b'\0' + len(compiler_jam).to_bytes(4, 'little') + compiler_jam
        timer_jam = _jam((32, (_atom('avow'), (0, (_atom('noun'), (_atom('stead-core-result'), _atom('7b7d')))))))
        timer_frame = b'\0' + len(timer_jam).to_bytes(4, 'little') + timer_jam
        request = '[32 %fyrd [%base %stead-ci-delay %noun [%noun ~]]]'
        request_jam = _jam((32, (_atom('fyrd'), (_atom('base'), (_atom('stead-ci-delay'), (_atom('noun'), (_atom('noun'), 0)))))))
        request_frame = (b'\0' + len(request_jam).to_bytes(4, 'little') + request_jam).hex()
        timer = {'request': request, 'outcome': {'raw': '{}', 'json': {}}, 'request_frame_hex': request_frame,
            'response_frame_hex': timer_frame.hex(), 'response_frame_sha256': hashlib.sha256(timer_frame).hexdigest()}
        original = bytes.fromhex(commands[0]['native_test']['response_frame_hex'])
        wrong_jam = _jam((32, (_atom('avow'), (0, (_atom('noun'), 1)))))
        wrong = b'\0' + len(wrong_jam).to_bytes(4, 'little') + wrong_jam
        self.value['negative_controls'] = {
            'classification': 'real-native-controls-and-labeled-frame-fault-injection',
            'missing_arm': {'path': '/controls/stead-ci-missing', 'native_test': missing,
                'refusal': 'Native discovered/executed arm mismatch',
                'log_hex': b'built   /controls/stead-ci-missing/hoon\nOK /controls/stead-ci-missing/test-ci-renamed\n'.hex()},
            'compiler_failure': {'path': '/controls/stead-ci-compiler',
                'log_hex': b'find-fork stead-ci-deliberately-undefined\n'.hex(), 'error': 'Unexpected terminal',
                'native_failure': unit_request('/controls/stead-ci-compiler') | {'stage': 'parse-terminal', 'received_frame_hex': compiler_frame.hex()}},
            'timer_positive': timer, 'timer_recovered': copy.deepcopy(timer),
            'timer_timeout': {'deadline_seconds': .05, 'elapsed_seconds': .1, 'native_failure': {
                'stage': 'response-header', 'received_frame_hex': '', 'request': request,
                'error': 'TimeoutError: timed out', 'encoded_frame_hex': request_frame}},
            'frame_fault_injection': {'original_sha256': hashlib.sha256(original).hexdigest(),
                'controls': {name: {'injected_hex': raw.hex(), 'refusal': 'Native frame/verdict mismatch'}
                    for name, raw in {'truncated': original[:-1], 'corrupt_verdict': wrong}.items()}}}

    def verify(self, value):
        return result.verify(result.PREFIX.encode() + result.canonical(value) + b'\n', self.inputs,
            run_id=self.run, inventory=self.inventory)

    def test_complete_mock_record_only_tests_parser(self):
        self.assertEqual(self.verify(self.value), self.value)

    def test_cache_permission_refusal_requires_readonly_mount(self):
        self.value['filesystem_controls']['cache_write_errno'] = 13
        self.assertEqual(self.verify(self.value), self.value)
        for key, replacement in [('cache_mount_read_only', False), ('cache_mount_read_only', 1),
                                 ('cache_write_errno', True), ('cache_write_errno', 1)]:
            altered = copy.deepcopy(self.value)
            altered['filesystem_controls'][key] = replacement
            with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                self.verify(altered)
        del self.value['filesystem_controls']['cache_mount_read_only']
        with self.assertRaises(ValueError):
            self.verify(self.value)

    def test_empty_failed_missing_or_other_source_records_are_refused(self):
        changes = [('status', 'fail'), ('run_id', 'c' * 32), ('cleanup', False),
                   ('inputs_sha256', 'd' * 64), ('mounts_before', 'e' * 64)]
        for field, replacement in changes:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(self.value | {field: replacement})
        for field, replacement in [('checks', []), ('native_units', []), ('installed', {}), ('native_unit_transcripts', []),
                                   ('commands', []), ('restarts', {}), ('inputs_before', {}), ('execution_guard', {})]:
            altered = copy.deepcopy(self.value); altered['native'][field] = replacement
            with self.subTest(field=field), self.assertRaises((ValueError, KeyError)):
                self.verify(altered)

    def test_claimed_unit_pass_cannot_replace_transcript_or_runner(self):
        for target, key, replacement in [('native_unit_transcripts', 'terminal', '[32 %avow 0 %noun 1]'),
                                         ('native_unit_transcripts', 'log_hex', ''),
                                         ('commands', 'ship', 'bus')]:
            altered = copy.deepcopy(self.value); altered['native'][target][0][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(altered)

    def test_framing_and_decoded_terminal_must_match(self):
        for frame in (b'\0', b'\0\1\0\0\0', b'\0\1\0\0\0\0',
                      b'\0' + (len(jam := _jam((32, (_atom('avow'), (0, (_atom('noun'), 1))))))).to_bytes(4, 'little') + jam):
            altered = copy.deepcopy(self.value)
            observed = altered['native']['commands'][0]['native_test']
            observed.update(response_frame_hex=frame.hex(), response_frame_sha256=hashlib.sha256(frame).hexdigest())
            with self.assertRaises(ValueError):
                self.verify(altered)

    def test_truncation_multiple_frames_and_duplicate_keys_fail(self):
        valid = result.PREFIX.encode() + result.canonical(self.value) + b'\n'
        for raw in (b'', valid[:-3], valid + valid, valid + b'extra\n',
                    valid.replace(b'"cleanup":true', b'"cleanup":true,"cleanup":false')):
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                result.verify(raw, self.inputs, run_id=self.run, inventory=self.inventory)

    def test_missing_rejection_control_or_fabricated_restoration_is_refused(self):
        for field in ('filesystem_controls', 'negative_controls'):
            altered = copy.deepcopy(self.value)
            del altered[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(altered)

    def test_native_negative_requests_cannot_be_invented_or_rebound(self):
        for field, key, replacement in (
            ('timer_positive', 'request_frame_hex', '00'),
            ('timer_recovered', 'request_frame_hex', '00'),
            ('timer_positive', 'request', '[32 %fyrd ~]')):
            altered = copy.deepcopy(self.value)
            altered['negative_controls'][field][key] = replacement
            with self.subTest(field=field, key=key), self.assertRaises(ValueError):
                self.verify(altered)
        for field, key, replacement in (
            ('compiler_failure', 'resolved_path', '/~zod/base/~2026.9.27/controls/stead-other'),
            ('compiler_failure', 'encoded_frame_hex', '00'),
            ('compiler_failure', 'timeout_seconds', 99),
            ('timer_timeout', 'encoded_frame_hex', '00')):
            altered = copy.deepcopy(self.value)
            altered['negative_controls'][field]['native_failure'][key] = replacement
            with self.subTest(field=field, key=key), self.assertRaises(ValueError):
                self.verify(altered)
        for field, key, replacement in (
            ('filesystem_controls', 'seed_after', 'e' * 64),
            ('filesystem_controls', 'cache_write_errno', 1),
            ('negative_controls', 'missing_arm', {}),
            ('negative_controls', 'timer_timeout', {}),
            ('negative_controls', 'compiler_failure', {})):
            altered = copy.deepcopy(self.value)
            altered[field][key] = replacement
            with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
                self.verify(altered)


if __name__ == '__main__':
    unittest.main()

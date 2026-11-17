"""Six authored inert boundaries; no historical timeout bytes are reconstructed.

Socket/process/Dojo operations are doubles. The final case runs the actual
fixed coordinator with those doubles; it proves orchestration, not Hoon cost.
"""
import copy
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/urbit'), str(ROOT / 'scripts/ci')]
import core_conn
import native_units as units
import team_check as coordinator
import worker_failure


class RestoreTimeoutDiagnosticsTests(unittest.TestCase):
    def inventory(self):
        return json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_bytes())

    def progress(self, received=b''):
        entry = units.restore_entries(self.inventory())[1]
        return {'path': entry['path'],
                'transport': units.interruption_transport('response-header', 60001, received, 60),
                'log': units.partial_log(entry, b'')}

    def test_structural_frame_progress_keeps_exact_bytes_without_verdict(self):
        header = b'\0\x03\0\0\0'
        examples = [(b'', 'empty', None), (b'\0\x03', 'partial-header', None),
                    (b'\x01\x03\0\0\0', 'invalid-header', None),
                    (b'\0\0\0\0\0', 'invalid-header', None),
                    (header, 'partial-body', 3), (header + b'x', 'partial-body', 3),
                    (header + b'xyz', 'complete', 3), (header + b'xyza', 'overlong', 3)]
        for raw, state, declared in examples:
            with self.subTest(state=state, size=len(raw)):
                value = self.progress(raw)
                self.assertEqual(value['transport']['frame_state'], state)
                self.assertEqual(value['transport']['declared_body_bytes'], declared)
                self.assertEqual(value['transport']['received_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertIs(value['transport']['terminal_accepted'], False)
                self.assertEqual(units.validate_interrupted_unit(value, self.inventory()), value)

    def test_closed_types_bounds_and_scope_cannot_expand_deadline(self):
        value = self.progress()
        for key, wrong in [('elapsed_ms', True), ('elapsed_ms', 180001), ('elapsed_ms', -1),
                           ('timeout_seconds', 60.0), ('timeout_seconds', 61),
                           ('received_bytes', False), ('stage', 'private exception text'),
                           ('terminal_accepted', 0), ('frame_state', []),
                           ('declared_body_bytes', 0), ('received_sha256', 'secret')]:
            changed = copy.deepcopy(value)
            changed['transport'][key] = wrong
            with self.subTest(key=key, wrong=wrong), self.assertRaises(ValueError):
                units.validate_interrupted_unit(changed, self.inventory())
        for changed in (value | {'path': '/tests/private'}, value | {'raw': 'secret'},
                        value | {'log': value['log'] | {'build_observed': 1}}):
            with self.assertRaises(ValueError):
                units.validate_interrupted_unit(changed, self.inventory())
        for kwargs in [('response-body', 180001, b'', 60), ('decode', 1, b'', 61),
                       ('decode', True, b'', 60), ('decode', 1, b'x' * 1000006, 60)]:
            with self.assertRaises(ValueError):
                units.interruption_transport(*kwargs)
        for key, wrong in [('positive_suites', True), ('positive_arms', 329),
                           ('timeout_seconds', 180), ('qualification', 0)]:
            with self.assertRaises(ValueError):
                units.validate_restore_scope(units.restore_scope() | {key: wrong})

    def test_partial_logs_export_only_registered_complete_observations(self):
        entry = units.restore_entries(self.inventory())[1]
        arm = entry['arms'][0]
        raw = ('built   ' + entry['path'] + '/hoon\nOK      ' + entry['path'] + '/' + arm + '\n').encode()
        value = units.partial_log(entry, raw + b'private exception payload\n')
        self.assertTrue(value['build_observed'])
        self.assertEqual(value['registered_arm_observations'], [{'arm': arm, 'outcome': 'OK'}])
        self.assertNotIn('private exception', json.dumps(value))
        self.assertEqual(value['log_sha256'], hashlib.sha256(raw + b'private exception payload\n').hexdigest())
        self.assertEqual(units.partial_log(entry, raw.rstrip(b'\n'))['registered_arm_observations'], [])
        for malformed in (raw + raw, raw + b'OK /tests/other/test-foreign\n', raw + b'\xff'):
            result = units.partial_log(entry, malformed)
            self.assertEqual(result['projection_status'], 'malformed')
            self.assertEqual(result['registered_arm_observations'], [])
            self.assertFalse(result['build_observed'])

    def test_actual_transport_timeout_retains_progress_and_original_exception(self):
        error = TimeoutError('synthetic private socket text')
        class Channel:
            def __init__(self):
                self.calls, self.closed, self.timeouts = 0, False, []
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.closed = True
            def settimeout(self, value):
                self.timeouts.append(value)
            def connect(self, value):
                pass
            def sendall(self, value):
                pass
            def recv(self, size):
                self.calls += 1
                if self.calls == 1:
                    return b'\0\x03'
                raise error
        channel = Channel()
        stderr = (b'loom: mapped 512MB\nlite: arvo formula 4ce68411\n'
                  b'lite: core 641296f\nlite: final state 641296f\neval (jam, newt):\n')
        with patch.object(socket, 'socket', return_value=channel), \
             patch.object(core_conn, 'evaluate', return_value=(b'\0\x01\0\0\0x', stderr)) as evaluate, \
             patch('time.monotonic', return_value=10.0):
            with self.assertRaises(TimeoutError) as caught:
                units.run('never-executed', '/inert/socket', '/~zod/base/~2026.1.1' + units.RESTORE_PATH, 60)
        self.assertIs(caught.exception, error)
        self.assertEqual(channel.calls, 2)
        self.assertTrue(channel.closed)
        self.assertEqual(evaluate.call_count, 1)
        self.assertTrue(all(value == 60 for value in channel.timeouts))
        self.assertEqual(error.native_interruption['frame_state'], 'partial-header')
        self.assertEqual(error.native_interruption['received_bytes'], 2)
        self.assertEqual(error.native_interruption['stage'], 'response-header')
        self.assertNotIn('synthetic private socket text', json.dumps(error.native_interruption))

    def test_fixed_selection_and_public_projection_refuse_crossed_claims(self):
        inventory = self.inventory()
        entries = units.restore_entries(inventory)
        self.assertEqual([row['path'] for row in entries], [units.NEGATIVE_PATH, units.RESTORE_PATH])
        self.assertEqual(len(inventory['suites']), 48)
        self.assertEqual(sum(len(row['arms']) for row in inventory['suites']), 329)
        self.assertEqual(len(entries[1]['arms']), 8)
        self.assertEqual([row.get('timeout_seconds', 60) for row in entries], [60, 60])
        fixture = ROOT / 'native/core/desk/tests/stead-product-restore.hoon'
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(),
                         'e8e0a1709e5fce6f51d6216e2781242d30f84428b8e2dcca9bb1eb47e0899469')
        error = TimeoutError('secret')
        error.native_interruption = self.progress()['transport']
        report = {'diagnostic_scope': units.restore_scope(), 'native_units': [{'path': units.NEGATIVE_PATH}],
                  'native_unit_transcripts': [{'path': units.NEGATIVE_PATH}], 'checks': []}
        coordinator.diagnostic_error(report, error, 'suite', units.RESTORE_PATH)
        coordinator.diagnostic_unit_progress(report, entries[1], error, b'', inventory)
        closed = worker_failure.diagnostic_limits(report, inventory)
        self.assertEqual(closed['unit_progress']['path'], units.RESTORE_PATH)
        for field, extra in [('native_units', {'path': units.RESTORE_PATH}),
                             ('native_unit_transcripts', {'path': units.RESTORE_PATH}),
                             ('checks', {'name': 'native-unit-arms:' + units.RESTORE_PATH, 'passed': True})]:
            changed = copy.deepcopy(report)
            changed[field].append(extra)
            with self.assertRaises(ValueError):
                worker_failure.diagnostic_limits(changed, inventory)
        changed = copy.deepcopy(report)
        changed['native_unit_transcripts'] = []
        with self.assertRaises(ValueError):
            worker_failure.diagnostic_limits(changed, inventory)
        original = copy.deepcopy(report)
        with patch.object(units, 'partial_log', side_effect=ValueError('private failure')):
            coordinator.diagnostic_unit_progress(report, entries[1], error, b'', inventory)
        self.assertEqual(report, original)

    def test_actual_fixed_coordinator_timeout_keeps_negative_only_and_cleans_up(self):
        real_path = Path
        real_probe = coordinator.completed_build_probe
        inventory = self.inventory()
        entries = units.restore_entries(inventory)
        class KernelPath:
            def __truediv__(self, name):
                return self
            def resolve(self, strict=False):
                return self
            def is_relative_to(self, root):
                return root == '/kernel'
        for malformed_projection in (False, True):
            events, writes = [], []
            with self.subTest(malformed_projection=malformed_projection), tempfile.TemporaryDirectory() as directory:
                folder = real_path(directory)
                (folder / 'zod.log').write_bytes(b'')
                def paths(value):
                    return {'/state/logs': folder, '/state/logs/zod.log': folder / 'zod.log',
                        '/specs/phase2-pure-units.json': ROOT / 'specs/urbit/phase2-pure-units.json',
                        '/kernel/pkg/arvo': KernelPath()}.get(str(value), real_path(value))
                def dojo(ship, source, **kwargs):
                    self.assertEqual(ship, 'zod')
                    events.append(('dojo', source))
                    if source == '+stead-build-probe':
                        return '%stead-builds-pass'
                    if source.startswith('`path`%'):
                        return '/~zod/base/~2026.1.1' + source[len('`path`%'):]
                    self.assertTrue(source.startswith('=/  raw=@t'))
                    return '%.y'
                error = TimeoutError('synthetic secret original timeout')
                def native_run(binary, socket_path, path, timeout):
                    events.append(('suite', path, timeout))
                    if path.endswith(units.RESTORE_PATH):
                        error.native_interruption = {'unknown': 'secret'} if malformed_projection else self.progress()['transport']
                        raise error
                    return {'stdout': '[32 %avow 0 %noun 1]'}
                def verify(completed, *, path, **kwargs):
                    self.assertEqual(path, units.NEGATIVE_PATH)
                    return {'path': path, 'synthetic': True}
                host = {'TEAM': object(), 'execution_check': lambda **kwargs: {},
                    'LOADED_SOURCE_DIGEST': 'a' * 64,
                    'team_lifecycle': SimpleNamespace(LOADED_INGRESS_DIGEST='a' * 64),
                    'all_stop': lambda: events.append(('stop',)),
                    'copy_seed_to_live': lambda: events.append(('seed',)),
                    'SHIPS': ('zod', 'bus', 'nec', 'bud'),
                    'launch': lambda ship, fresh=False: events.append(('launch', ship)),
                    'wait_ready': lambda ship: None, 'dojo': dojo, 'record': lambda *args: None,
                    'LIVE': folder, 'LOCK': {'runtime': {'binary': 'never-executed'}}}
                with patch.object(coordinator, 'Path', side_effect=paths), \
                     patch.object(coordinator, 'sha', return_value='a' * 64), \
                     patch.object(coordinator, 'tree_sha', return_value='a' * 64), \
                     patch.object(coordinator, 'source_sha', return_value='a' * 64), \
                     patch.object(coordinator, 'closure', return_value={'source': 'a' * 64}), \
                     patch.object(coordinator, 'LOADED_CLOSURE', {'source': 'a' * 64}), \
                     patch.object(coordinator.native_install, 'install', return_value=249), \
                     patch.object(units, 'run', side_effect=native_run), \
                     patch.object(units, 'verify_output', side_effect=verify), \
                     patch.object(coordinator, 'completed_build_probe', side_effect=lambda h, r, c: real_probe(h, r, c, folder)), \
                     patch.object(coordinator.execution_policy, 'write_json', side_effect=lambda p, r: writes.append(copy.deepcopy(r))), \
                     patch.object(coordinator.traceback, 'print_exc'):
                    # The existing worker, not team_check, owns final stop.
                    # Model that caller finally with an inert cleanup callback;
                    # this case does not claim a real worker/process teardown.
                    try:
                        result = coordinator.run(host)
                    finally:
                        host['all_stop']()
                self.assertEqual([e for e in events if e[0] == 'launch'], [('launch', 'zod')])
                self.assertEqual([e for e in events if e[0] == 'suite'],
                    [('suite', '/~zod/base/~2026.1.1' + row['path'], 60) for row in entries])
                self.assertEqual(result['status'], 'fail')
                self.assertIs(result['qualifies_phase'], False)
                self.assertTrue(result['error'].startswith('TimeoutError:'))
                final = writes[-1]
                self.assertEqual(final['diagnostic_interruption']['path'], units.RESTORE_PATH)
                self.assertEqual([row['path'] for row in final['native_unit_transcripts']], [units.NEGATIVE_PATH])
                self.assertEqual([row['path'] for row in final['native_units']], [units.NEGATIVE_PATH])
                self.assertNotIn('product_observation', final)
                self.assertNotIn('captures', final)
                self.assertEqual(events[-1], ('stop',))
                self.assertEqual(final['inputs_before'], final['inputs_after'])
                self.assertEqual('diagnostic_unit_interruption' in final, not malformed_projection)
                self.assertNotIn('synthetic secret', json.dumps(final))


if __name__ == '__main__':
    unittest.main()

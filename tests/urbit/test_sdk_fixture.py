"""Host fixture/dispatch/cleanup controls with mocked native operations."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/sdk_native'), str(ROOT / 'scripts/urbit')]
SPEC = importlib.util.spec_from_file_location('sdk_fixture_controller', ROOT / 'scripts/sdk_native/controller.py')
CONTROLLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROLLER)


class SDKFixtureTests(unittest.TestCase):
    def peers(self):
        return [SimpleNamespace(ship=ship, binary='/pinned-vere', pier=Path('/state') / ship, commands=[])
                for ship in ('zod', 'nec')]

    def query(self):
        return {'protocol': 'stead.query/3', 'request_id': CONTROLLER.uid(40001), 'kind': 'work',
                'project_id': CONTROLLER.uid(2), 'container_id': '', 'resource_id': '', 'search': '', 'cursor': ''}

    def test_fixture_has_two_distinct_individuals_and_no_home_binding(self):
        config = CONTROLLER.fixture_config(1000)
        self.assertEqual(set(config['bindings']), {'~bus', '~nec'})
        self.assertNotIn(config['home'], config['bindings'])
        self.assertEqual(config['bindings']['~bus']['principal_id'], CONTROLLER.uid(102))
        self.assertEqual(config['bindings']['~nec']['principal_id'], CONTROLLER.uid(104))
        self.assertEqual(config['bindings']['~nec']['binding_id'], CONTROLLER.uid(204))
        self.assertEqual(set(config['project_creators']), {p['principal_id'] for p in config['bindings'].values()})
        self.assertTrue(all(int(p['expires_at_ms']) > 1000 for p in config['bindings'].values()))
        for invalid in (0, -1, True, 2**64 - 7200000):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                CONTROLLER.fixture_config(invalid)

    def test_business_call_uses_real_member_socket_and_member_bound_route(self):
        home, member = self.peers()
        denied = {'protocol': 'stead.result/3', 'status': 'rejected', 'error': 'denied_or_not_found'}
        with patch.object(CONTROLLER.team_conn, 'run', return_value={'outcome': {'json': denied}}) as run:
            self.assertEqual(CONTROLLER.fixture_call(home, member, 'query', self.query()), denied)
        args = run.call_args.args
        self.assertEqual(args[1], Path('/state/nec/.urb/conn.sock'))
        self.assertTrue(args[3].startswith('/v3/result/~nec/' + CONTROLLER.uid(204) + '/1/'))
        self.assertEqual(json.loads(args[4]), self.query())
        self.assertEqual(home.commands, [])
        self.assertEqual(len(member.commands), 1)

    def test_missing_or_home_member_and_supplied_business_route_are_refused(self):
        home, member = self.peers()
        with patch.object(CONTROLLER.team_conn, 'run') as run:
            for wrong in (None, home, SimpleNamespace(ship='bus')):
                with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                    CONTROLLER.fixture_call(home, wrong, 'query', self.query())
            with self.assertRaises(ValueError):
                CONTROLLER.fixture_call(home, member, 'query', self.query(), '/v3/result/~zod/')
            run.assert_not_called()

    def test_configuration_stays_owner_local(self):
        home, member = self.peers()
        with patch.object(CONTROLLER.team_conn, 'run', return_value={'outcome': {'json': {}}}) as run:
            CONTROLLER.fixture_call(home, member, 'configure', CONTROLLER.fixture_config(1000), '/')
        self.assertEqual(run.call_args.args[1], Path('/state/zod/.urb/conn.sock'))
        self.assertEqual(member.commands, [])

    def test_bootstrap_keeps_explicit_refusal_and_requires_fresh_correlated_ack(self):
        home, member = self.peers()
        attempts = []
        refusal = {'protocol': 'stead.test-terminal/1', 'status': 'failed', 'kind': 'poke-fail'}
        def reply(_home, _member, _mode, value, route, **kwargs):
            self.assertEqual(route, '/bootstrap/' + value['nonce'])
            self.assertLessEqual(kwargs['timeout'], 75)
            if not attempts:
                return refusal
            return {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~zod',
                    'nonce': value['nonce'], 'incarnation': 'c' * 64}
        guard = Mock()
        with patch.object(CONTROLLER, 'fixture_call', side_effect=reply), patch.object(CONTROLLER.time, 'sleep'), \
                patch.object(CONTROLLER.secrets, 'token_hex', side_effect=['a' * 64, 'b' * 64]):
            ack = CONTROLLER.bootstrap_home(home, member, guard, attempts)
        self.assertEqual(ack['nonce'], 'b' * 64)
        self.assertEqual([a['status'] for a in attempts], ['failed', 'ready'])
        self.assertEqual(guard.call_count, 2)

    def test_bootstrap_refusals_are_bounded_and_cannot_qualify(self):
        home, member = self.peers()
        attempts = []
        refusal = {'protocol': 'stead.test-terminal/1', 'status': 'failed', 'kind': 'poke-fail'}
        with patch.object(CONTROLLER, 'fixture_call', return_value=refusal) as call, \
                patch.object(CONTROLLER.time, 'sleep'), self.assertRaises(TimeoutError):
            CONTROLLER.bootstrap_home(home, member, lambda: None, attempts)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(len(attempts), 3)

    def test_bootstrap_timeout_and_wrong_ack_are_not_retried(self):
        home, member = self.peers()
        wrong = {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~zod',
                 'nonce': 'wrong', 'incarnation': 'c' * 64}
        for kwargs, error in [({'return_value': wrong}, ValueError), ({'side_effect': TimeoutError}, TimeoutError)]:
            with self.subTest(error=error), patch.object(CONTROLLER, 'fixture_call', **kwargs) as call:
                with self.assertRaises(error):
                    CONTROLLER.bootstrap_home(home, member, lambda: None, [])
                self.assertEqual(call.call_count, 1)

    def test_bootstrap_late_correct_ack_cannot_admit_consumer(self):
        home, member = self.peers()
        attempts = []
        def reply(_home, _member, _mode, value, _route, **_kwargs):
            return {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~zod',
                    'nonce': value['nonce'], 'incarnation': 'c' * 64}
        with patch.object(CONTROLLER, 'fixture_call', side_effect=reply) as call, \
                patch.object(CONTROLLER.time, 'monotonic', side_effect=[0, 0, 181]), self.assertRaises(TimeoutError):
            CONTROLLER.bootstrap_home(home, member, lambda: None, attempts)
        call.assert_called_once()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]['status'], 'ready')

    def test_failed_control_cleanup_does_not_skip_home_or_transcripts(self):
        home, member = self.peers()
        member.stop = Mock(side_effect=OSError('synthetic failed stop'))
        home.stop = Mock(return_value={'clean': True, 'reaped': True})
        cleanup = {}
        with tempfile.TemporaryDirectory(prefix='sdk-cleanup-', dir=ROOT / '.runtime') as temporary:
            directory = Path(temporary)
            results = [CONTROLLER.close_native(role, child, cleanup, directory)
                       for role, child in [('control_member', member), ('home', home)]]
            self.assertEqual(results, [False, True])
            self.assertIn('control_member_error', cleanup)
            self.assertTrue(cleanup['home']['reaped'])
            self.assertEqual({p.name for p in directory.iterdir()}, {'control_member-transcript.json', 'home-transcript.json'})
        member.stop.assert_called_once()
        home.stop.assert_called_once()

    def test_transcript_failure_still_stops_native_and_fails_cleanup(self):
        home, _ = self.peers()
        home.stop = Mock(return_value={'clean': True, 'reaped': True})
        cleanup = {}
        with tempfile.TemporaryDirectory(prefix='sdk-cleanup-', dir=ROOT / '.runtime') as temporary:
            self.assertFalse(CONTROLLER.close_native('home', home, cleanup, Path(temporary) / 'absent'))
        home.stop.assert_called_once()
        self.assertIn('home_transcript_error', cleanup)

    def test_native_fixed_identity_ports_remain_closed(self):
        for ship, port in [('nec', 31337), ('zod', 31338), ('bud', 31339), ('bus', 18081)]:
            with self.subTest(ship=ship, port=port), self.assertRaises(ValueError):
                CONTROLLER.Native(ship, port, lambda: None)


if __name__ == '__main__':
    unittest.main()

"""Synthetic configured-startup readiness controls; no native qualification."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import team_check


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.process = Mock()
        self.process.poll.return_value = None
        self.entry = {'process': self.process, 'nonce': 'a' * 64,
                      'suspended': True, 'acknowledged': False}
        self.team = SimpleNamespace(boots={'zod': self.entry},
                                    children={'zod': self.process}, admit=Mock())
        self.guard = Mock()
        self.call = Mock()
        for target, replacement in (('monotonic', lambda: self.now), ('sleep', self.sleep)):
            change = patch.object(team_check.time, target, replacement)
            change.start()
            self.addCleanup(change.stop)

    def sleep(self, seconds):
        self.now += seconds

    def ready(self, ship='zod'):
        return {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~' + ship,
                'nonce': 'a' * 64, 'incarnation': 'b' * 64}

    def refused(self):
        return {'protocol': 'stead.test-terminal/1', 'status': 'failed', 'kind': 'poke-fail',
                'trace': 'native readiness refusal', 'trace_jam_hex': 'abcd'}

    def run_bootstrap(self, ship='zod'):
        return team_check.bootstrap_ready(self.team, ship, self.call, self.guard)

    def test_initial_and_reloaded_apps_require_exact_owner_ack(self):
        for ship in ('zod', 'bus', 'nec', 'bud'):
            with self.subTest(ship=ship):
                self.team.boots = {ship: self.entry}
                self.team.children = {ship: self.process}
                self.call.reset_mock(side_effect=True)
                self.call.side_effect = [self.refused(), self.ready(ship)]
                self.assertEqual(self.run_bootstrap(ship), self.ready(ship))
                self.assertEqual(self.call.call_count, 2)
                self.assertEqual(self.call.call_args_list[0], self.call.call_args_list[1])
                arguments = self.call.call_args.kwargs
                self.assertEqual(arguments['timeout'], 75)
                self.assertEqual(arguments['target'], ship)
                self.assertEqual(arguments['route'], '/bootstrap/' + self.entry['nonce'])
                self.assertEqual(arguments['app'], 'stead-home' if ship == 'zod' else 'stead-identity')
                self.team.admit.assert_not_called()
                self.assertFalse(self.entry['acknowledged'])

    def test_three_explicit_refusals_remain_a_failure(self):
        self.call.return_value = self.refused()
        with self.assertRaisesRegex(TimeoutError, 'not acknowledged'):
            self.run_bootstrap()
        self.assertEqual(self.call.call_count, 3)
        self.team.admit.assert_not_called()

    def test_wrong_missing_extra_and_malformed_ack_never_retry(self):
        good = self.ready()
        cases = [good | {key: 'wrong'} for key in good]
        cases += [{k: v for k, v in good.items() if k != key} for key in good]
        cases += [good | {'extra': 'value'}, good | {'incarnation': 'A' * 64},
                  good | {'incarnation': None}, None, []]
        for value in cases:
            with self.subTest(value=value):
                self.call.reset_mock()
                self.call.return_value = value
                with self.assertRaisesRegex(ValueError, 'acknowledgement differs'):
                    self.run_bootstrap()
                self.assertEqual(self.call.call_count, 1)

    def test_only_complete_poke_refusals_can_retry(self):
        bad = [self.refused() | {key: value} for key, value in (
            ('kind', 'watch-ack-fail'), ('status', 'ready'), ('protocol', 'other'),
            ('trace', None), ('trace_jam_hex', ''), ('trace_jam_hex', 'abc'),
            ('trace_jam_hex', 'ABCD'))]
        bad += [self.refused() | {'extra': 'value'},
                {k: v for k, v in self.refused().items() if k != 'trace'}]
        for value in bad:
            with self.subTest(value=value):
                self.call.reset_mock()
                self.call.return_value = value
                with self.assertRaisesRegex(ValueError, 'acknowledgement differs'):
                    self.run_bootstrap()
                self.assertEqual(self.call.call_count, 1)

    def test_transport_and_evaluator_errors_never_retry(self):
        for error in (TimeoutError, OSError, RuntimeError, ValueError):
            with self.subTest(error=error):
                self.call.reset_mock()
                self.call.side_effect = error('exchange failed')
                with self.assertRaisesRegex(error, 'exchange failed'):
                    self.run_bootstrap()
                self.assertEqual(self.call.call_count, 1)

    def test_no_exchange_starts_without_full_existing_budget(self):
        self.guard.side_effect = lambda: self.sleep(46)
        with self.assertRaisesRegex(TimeoutError, 'budget exhausted'):
            self.run_bootstrap()
        self.call.assert_not_called()

    def test_slow_refusal_does_not_shorten_next_transport_timeout(self):
        def slow(*args, **kwargs):
            self.sleep(46)
            return self.refused()
        self.call.side_effect = slow
        with self.assertRaisesRegex(TimeoutError, 'budget exhausted'):
            self.run_bootstrap()
        self.assertEqual(self.call.call_count, 1)
        self.assertEqual(self.call.call_args.kwargs['timeout'], 75)

    def test_late_ack_is_not_admission(self):
        def late(*args, **kwargs):
            self.sleep(180)
            return self.ready()
        self.call.side_effect = late
        with self.assertRaisesRegex(TimeoutError, 'after deadline'):
            self.run_bootstrap()
        self.assertEqual(self.call.call_count, 1)
        self.team.admit.assert_not_called()

    def test_guard_failure_before_or_after_exchange_is_final(self):
        for outcomes, count in (([RuntimeError('guard lost')], 0),
                                ([None, RuntimeError('guard lost')], 1)):
            with self.subTest(count=count):
                self.call.reset_mock()
                self.call.return_value = self.ready()
                self.guard.side_effect = outcomes
                with self.assertRaisesRegex(RuntimeError, 'guard lost'):
                    self.run_bootstrap()
                self.assertEqual(self.call.call_count, count)

    def test_dead_child_is_not_used(self):
        self.process.poll.return_value = 0
        with self.assertRaisesRegex(ValueError, 'owner changed'):
            self.run_bootstrap()
        self.call.assert_not_called()

    def test_changed_live_owner_or_nonce_never_admits(self):
        original = copy.copy(self.entry)
        changes = (
            lambda: self.team.boots.update(zod=copy.copy(self.entry)),
            lambda: self.team.children.update(zod=Mock()),
            lambda: self.entry.update(process=Mock()),
            lambda: self.entry.update(nonce='c' * 64),
            lambda: self.entry.update(acknowledged=True),
            lambda: self.entry.update(suspended=False),
            lambda: setattr(self.process.poll, 'return_value', 1),
        )
        for change in changes:
            with self.subTest(change=change):
                self.entry.clear()
                self.entry.update(original)
                self.team.boots = {'zod': self.entry}
                self.team.children = {'zod': self.process}
                self.process.poll.return_value = None
                self.call.reset_mock()
                def changed(*args, **kwargs):
                    change()
                    return self.ready()
                self.call.side_effect = changed
                with self.assertRaisesRegex(ValueError, 'owner changed'):
                    self.run_bootstrap()
                self.assertEqual(self.call.call_count, 1)
                self.team.admit.assert_not_called()


if __name__ == '__main__':
    unittest.main()

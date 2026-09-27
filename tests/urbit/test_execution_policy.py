"""Light controlled-child guard tests, never native execution qualification.

Thermal readings and systemd scope construction/signaling are explicitly mocked.
Python children, inherited flock descriptors, temporary logs and shutdown effects
are real. Independent adversarial review lives in test_runtime_guard_adversarial.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import execution_policy as guard


def reading(temperature=45):
    now = time.monotonic()
    return guard.Sample(now, now, {'thermal_zone0:x86_pkg_temp': temperature}, ('thermal_zone0:x86_pkg_temp',))


class ControlledChildExecution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-execution-policy-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ready = self.root / 'child-ready'
        self.processes, self.signals = [], []
        self.policy = guard.Policy(sample_seconds=.01, cooperative_seconds=0,
                                   terminate_seconds=.15, kill_seconds=.15)
        self.original_popen = subprocess.Popen
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(guard, 'scope_command',
            side_effect=lambda command, *_args: command))
        def launch(*args, **kwargs):
            process = self.original_popen(*args, **kwargs)
            self.processes.append(process)
            return process
        self.stack.enter_context(patch.object(guard.subprocess, 'Popen', side_effect=launch))
        def owned_signal(unit, signum):
            self.assertRegex(unit, r'^stead-native-[0-9a-f]{32}\.scope$')
            self.signals.append(signum)
            process = self.processes[-1]
            if process.poll() is None:
                process.send_signal(signum)
            return {'signal': signal.Signals(signum).name, 'returncode': 0}
        self.stack.enter_context(patch.object(guard, 'signal_owned_scope', side_effect=owned_signal))
        self.addCleanup(self.cleanup_children)

    def cleanup_children(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)

    def factory(self, program):
        def command(control, run_id):
            # This is explicitly a mocked resource proof; real scoped read-back
            # is tested separately and never inferred from this child fixture.
            guard.write_json(control / 'scope.json', {'unit': 'stead-native-' + run_id + '.scope'})
            return [sys.executable, '-c', program, str(self.ready)]
        return command

    def run_child(self, program, sampler=reading, **kwargs):
        with (self.root / 'console.log').open('wb') as output:
            return guard.run_guarded(self.factory(program), root=self.root,
                label='controlled-child', policy=self.policy, timeout=3,
                console=output, sampler=sampler, **kwargs)

    def test_clean_light_child_completion_is_not_labeled_native_pass(self):
        report = self.run_child('print("synthetic child completed", flush=True)')
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['exit_code'], 0)
        self.assertIn('synthetic child completed', (self.root / 'console.log').read_text())
        self.assertEqual(guard.read_json(Path(report['run_directory']) / 'report.json'), json.loads(json.dumps(report)))
        self.assertEqual(self.signals, [])

    def test_hot_preflight_never_launches_a_child(self):
        report = self.run_child('raise SystemExit("must not execute")', sampler=lambda: reading(76))
        self.assertFalse(report['launched'])
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(self.processes, [])
        self.assertEqual(report['events'][0]['sample']['readings_c']['thermal_zone0:x86_pkg_temp'], 76)

    def test_existing_stop_never_launches_a_child(self):
        report = self.run_child('raise SystemExit("must not execute")', stop_requested=lambda: True)
        self.assertEqual(report['status'], 'failed')
        self.assertFalse(report['launched'])
        self.assertEqual(self.processes, [])

    def test_trip_with_child_exit_zero_stays_failed_and_preserves_crossing(self):
        program = ('import signal,sys,time; from pathlib import Path; '
                   'signal.signal(signal.SIGTERM, lambda *_: sys.exit(0)); '
                   'Path(sys.argv[1]).write_text("ready"); time.sleep(60)')
        report = self.run_child(program, sampler=lambda: reading(90 if self.ready.exists() else 45))
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['exit_code'], 0)
        self.assertIn('Thermal ceiling', report['reason'])
        self.assertIn(signal.SIGTERM, self.signals)
        values = [event['sample']['readings_c']['thermal_zone0:x86_pkg_temp']
                  for event in report['events'] if 'sample' in event]
        self.assertIn(90, values)
        self.assertEqual(guard.read_json(Path(report['run_directory']) / 'control/lease.json')['state'], 'stopped')

    def test_uncooperative_owned_child_is_killed_within_bounded_cleanup(self):
        program = ('import signal,sys,time; from pathlib import Path; '
                   'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
                   'Path(sys.argv[1]).write_text("ready"); time.sleep(60)')
        before = time.monotonic()
        report = self.run_child(program, sampler=lambda: reading(90 if self.ready.exists() else 45))
        self.assertLess(time.monotonic() - before, 2)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['exit_code'], -signal.SIGKILL)
        self.assertEqual(self.signals, [signal.SIGTERM, signal.SIGKILL])
        with guard.HeavyRunLock(self.root / '.runtime/native-execution.lock'):
            self.assertIsNotNone(self.processes[0].poll())

    def test_child_keeps_exclusive_lock_after_parent_descriptor_closes(self):
        lock = self.root / 'owned.lock'
        with guard.HeavyRunLock(lock) as owner:
            process = self.original_popen([sys.executable, '-c',
                'import sys,time; from pathlib import Path; Path(sys.argv[1]).write_text("ready"); time.sleep(60)',
                str(self.ready)], pass_fds=(owner.descriptor,))
            self.processes.append(process)
            deadline = time.monotonic() + 1
            while not self.ready.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(self.ready.exists())
        with self.assertRaises(BlockingIOError):
            with guard.HeavyRunLock(lock):
                self.fail('Inherited child lost the shared execution lock')
        process.terminate()
        process.wait(timeout=1)
        with guard.HeavyRunLock(lock):
            pass


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Two inert deadline/custody cases: no evaluator or child process runs."""
import contextlib
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('deadline_worker', ROOT / 'scripts/ci/pure_eval/worker.py')
W = importlib.util.module_from_spec(spec)
spec.loader.exec_module(W)


class PureEvalDeadlineTests(unittest.TestCase):
    @contextlib.contextmanager
    def inert_child(self, times, lease):
        process = types.SimpleNamespace(pid=12345, poll=Mock(return_value=None))
        stop, close = Mock(), Mock()
        owned = types.SimpleNamespace(command=Mock(return_value=['inert-never-executed']))
        source = b'never evaluated\n'
        job = dict(label='catalog-debug', kind='suite', source=source,
                   source_sha256=hashlib.sha256(source).hexdigest(), timeout_seconds=85,
                   arms=('test-inert',))
        real_temp = tempfile.TemporaryFile
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(W.tempfile, 'TemporaryFile',
                side_effect=lambda **_: real_temp(dir=directory)))
            stack.enter_context(patch.object(W, 'Path', return_value=types.SimpleNamespace(iterdir=lambda: iter([1]))))
            stack.enter_context(patch.object(W, 'process_ids', return_value={1, 555}))
            spawn = stack.enter_context(patch.object(W.subprocess, 'Popen', return_value=process))
            stack.enter_context(patch.object(W.os, 'pidfd_open', return_value=777))
            stack.enter_context(patch.object(W.os, 'close', close))
            stack.enter_context(patch.object(W, 'stop', stop))
            stack.enter_context(patch.object(W.time, 'monotonic', side_effect=times))
            sleep = stack.enter_context(patch.object(W.time, 'sleep', side_effect=AssertionError('No sleep after refusal')))
            yield job, owned, lease, process, spawn, stop, close, sleep, directory

    def test_exact_suite_or_total_deadline_classifies_timeout_and_closes_owned_child(self):
        for total, times in ((1000, [10, 95]), (12, [10, 12]), (1000, [10, float('nan')])):
            with self.subTest(total=total, times=times), self.inert_child(times, Mock()) as x:
                job, owned, lease, process, spawn, stop, close, sleep, directory = x
                with self.assertRaisesRegex(TimeoutError, '^Fixed evaluator job deadline$'):
                    W.evaluate(job, owned, lease, {1, 555}, total)
                spawn.assert_called_once()
                stop.assert_called_once_with(process, 777)
                close.assert_called_once_with(777)
                sleep.assert_not_called()
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_current_lease_refusal_keeps_original_exception_and_same_cleanup(self):
        error = ValueError('inert revoked lease')
        lease = types.SimpleNamespace(check=Mock(side_effect=[None, error]))
        with self.inert_child([10], lease) as x:
            job, owned, lease, process, spawn, stop, close, sleep, directory = x
            with self.assertRaises(ValueError) as caught:
                W.evaluate(job, owned, lease, {1, 555}, 1000)
            self.assertIs(caught.exception, error)
            spawn.assert_called_once()
            stop.assert_called_once_with(process, 777)
            close.assert_called_once_with(777)
            sleep.assert_not_called()
            self.assertEqual(lease.check.call_count, 2)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()

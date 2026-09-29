"""Real small host process/EOF controls; no Hoon or hosted claim."""
import copy
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import stat
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import hosted

# Both processes retain stdout. The descendant has its own session and does
# not cooperate with its parent's ordinary exit or with wrapper termination.
HOLDER = '''import os, sys, time
pid = os.fork()
if pid == 0:
    os.setsid()
    print('DETACHED_STDOUT_READY', flush=True)
    time.sleep(60)
    os._exit(0)
assert sys.stdin.buffer.read(1) == b'x'
'''


class HostedLifetimeControls(unittest.TestCase):
    def command(self):
        pins = json.loads((ROOT / 'specs/urbit/toolchain.lock.json').read_text())
        with patch.object(hosted, 'local', SimpleNamespace(TEMP_BYTES=1024**2, STATE_BYTES=1024**2), create=True):
            full = hosted.sandbox_command(Path('/unused'), {'pins': pins, 'run_id': 'a' * 32})
        # Exercise the production namespace/lifetime options with only public
        # system binaries mounted. No pins, project state or network is needed.
        command = full[:full.index('--ro-bind')] + ['--ro-bind', '/usr', '/usr']
        for name in ('bin', 'sbin', 'lib', 'lib64'):
            path = Path('/') / name
            command += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
        return command + ['--proc', '/proc', '--dev', '/dev', '--clearenv', '--',
            '/usr/bin/python3', '-I', '-B', '-c', HOLDER]

    @staticmethod
    def descendants(pid):
        children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
        result = []
        for child in children:
            child = int(child)
            result.append(child)
            result.extend(HostedLifetimeControls.descendants(child))
        return result

    def exercise(self, signum):
        process = subprocess.Popen(self.command(), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        descriptors = []
        try:
            self.assertTrue(select.select([process.stdout], [], [], 5)[0], 'No ready frame')
            self.assertEqual(process.stdout.readline(), b'DETACHED_STDOUT_READY\n')
            descendants = self.descendants(process.pid)
            self.assertGreaterEqual(len(descendants), 3)
            detached = [pid for pid in descendants if os.getsid(pid) == pid
                and Path(f'/proc/{pid}/comm').read_text().strip() == 'python3']
            self.assertEqual(len(detached), 1, 'Detached stdout holder not independently observed')
            # Retained pidfds observe actual process death without PID reuse.
            descriptors = [os.pidfd_open(pid) for pid in descendants]
            self.assertFalse(select.select(descriptors, [], [], 0)[0])
            if signum is None:
                process.stdin.write(b'x')
                process.stdin.flush()
            else:
                process.send_signal(signum)
            process.stdin.close()
            process.stdin = None
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(stdout, b'')
            self.assertEqual(stderr, b'')
            self.assertEqual(process.returncode, 0 if signum is None else -signum)
            for descriptor in descriptors:
                self.assertTrue(select.select([descriptor], [], [], 2)[0], 'Owned descendant survived wrapper')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for descriptor in descriptors:
                if not select.select([descriptor], [], [], 0)[0]:
                    signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                os.close(descriptor)
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe is not None:
                    pipe.close()

    def test_wrapper_sigterm_closes_stdout_and_kills_detached_descendant(self):
        self.exercise(signal.SIGTERM)

    def test_wrapper_sigkill_closes_stdout_and_kills_detached_descendant(self):
        self.exercise(signal.SIGKILL)

    def test_ordinary_command_exit_closes_stdout_and_kills_detached_descendant(self):
        self.exercise(None)

    def test_expected_refusal_cannot_hide_incomplete_cleanup(self):
        good = {'error': 'ValueError: Hosted caller ended', 'cleanup_errors': [],
            'collector': {'error': None, 'overflow': False, 'eof': True, 'completed': True},
            'child_terminated': True, 'exit_code': -15}
        hosted.require_collected_child(good)
        for key, value in [('eof', False), ('completed', False), ('error', 'OSError'), ('overflow', True)]:
            bad = copy.deepcopy(good)
            bad['collector'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Incomplete'):
                hosted.require_collected_child(bad)
        for delta in ({'collector': {}}, {'cleanup_errors': ['timeout']},
                      {'child_terminated': False}, {'exit_code': None}, {'exit_code': True}):
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, 'Incomplete'):
                hosted.require_collected_child({**good, **delta})

    def test_guardian_preserves_primary_error_when_stop_collector_start_and_close_fail(self):
        # Mock root admission only; the child is real. This is fault-injection
        # evidence for reporting/reaping, not hosted service qualification.
        reports, children = {}, []
        real_popen = subprocess.Popen
        class FailingClose:
            def __init__(self, pipe):
                self.pipe = pipe
            @property
            def closed(self):
                return self.pipe.closed
            def close(self):
                self.pipe.close()
                raise OSError('control close failure')
        def spawn(*args, **kwargs):
            process = real_popen(['/usr/bin/python3', '-I', '-B', '-c', 'import time; time.sleep(30)'],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.stdout = FailingClose(process.stdout)
            children.append(process)
            return process
        def write(path, value, **kwargs):
            if path.name == 'STOP':
                raise OSError('control stop failure')
            reports[path.name] = value
        context = {'run_id': 'a' * 32, 'gid': os.getgid(), 'guard_sha256': 'b' * 64}
        evidence = {'run_id': context['run_id'], 'unit': 'test', 'cgroup': 'test', 'limits': {}, 'cpus': [0]}
        with ExitStack() as stack:
            for name, value in [('POLICY', {'thermal': 'test-only', 'profile': 'test-only'}),
                    ('execution_policy', SimpleNamespace(read_json=lambda *a, **k: context)),
                    ('observe', lambda *a: evidence), ('regular_root', lambda *a: None), ('write', write)]:
                stack.enter_context(patch.object(hosted, name, value, create=True))
            stack.enter_context(patch.object(hosted.os, 'getuid', return_value=0))
            stack.enter_context(patch.object(hosted.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFIFO)))
            stack.enter_context(patch.object(hosted.signal, 'signal'))
            stack.enter_context(patch.object(hosted.select, 'select', return_value=([], [], [])))
            stack.enter_context(patch.object(hosted.subprocess, 'Popen', side_effect=spawn))
            stack.enter_context(patch.object(hosted.threading.Thread, 'start', side_effect=RuntimeError('control collector start')))
            self.assertEqual(hosted.guardian(Path('/unused')), 1)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assertTrue(children[0].stdout.closed)
        result = reports['guard.json']
        self.assertEqual(result['error'], 'RuntimeError: control collector start')
        self.assertEqual(result['status'], 'fail')
        self.assertTrue(result['child_terminated'])
        self.assertIn('Stop receipt: OSError', result['cleanup_errors'])
        self.assertIn('Unstarted collector pipe close: OSError', result['cleanup_errors'])
        self.assertIn('Output collector did not finish with EOF', result['cleanup_errors'])
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            hosted.require_collected_child(result)

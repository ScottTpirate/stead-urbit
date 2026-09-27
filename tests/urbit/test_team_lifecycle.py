"""Host manager failure controls. Native replies and packet policy are mocked.

The post-spawn controls use a real harmless sleep child and supervisor cleanup;
native saved-state semantics still require the separate configured Urbit lane.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import digests
import team_lifecycle


class TeamLifecycleTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'scripts/urbit/supervisor.py'
        spec = importlib.util.spec_from_file_location('manager_test_supervisor', path)
        self.supervisor = importlib.util.module_from_spec(spec)
        read = Path.read_text
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == Path('/toolchain.json') else read(p, *a, **kw)), \
                patch.object(digests, 'source_sha', return_value='host-test'):
            spec.loader.exec_module(self.supervisor)
        self.supervisor.record = Mock()
        self.manager = team_lifecycle.TeamLifecycle.__new__(team_lifecycle.TeamLifecycle)
        self.manager.guard = Mock()
        self.manager.children, self.manager.boots, self.manager.restart_expected = {}, {}, {}
        self.manager.record = Mock()
        self.manager.certificates = Path('/mocked-disposable-certificates')
        self.tls_verification = patch.object(team_lifecycle.native_tls, 'verify', return_value={'classification': 'mocked-tls'})
        self.tls_verification.start()
        self.addCleanup(self.tls_verification.stop)
        self.manager.ingress = {name: Mock() for name in team_lifecycle.APPS}
        self.manager.peers = SimpleNamespace(lock=threading.RLock(), closed=threading.Event(), block=Mock(), release=Mock())
        def block(ship):
            if self.manager.peers.closed.is_set():
                raise ValueError('Native peer barrier closed')
        self.manager.peers.block.side_effect = block
        def injection(ship):
            return os.memfd_create('host-test-startup-placeholder'), {'classification': 'mocked-jam'}
        self.manager.injection = Mock(side_effect=injection)
        self.manager.launcher = SimpleNamespace(spawn=Mock(side_effect=self.spawn))
        self.supervisor.TEAM = self.manager
        self.processes = []
        self.addCleanup(self.reap)

    def spawn(self, arguments, **options):
        # No candidate/native code. Production argv is deliberately not run.
        process = subprocess.Popen(['/usr/bin/sleep', '30'], **options)
        self.processes.append(process)
        return process

    def reap(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)

    def launch(self, *, register=None):
        return self.manager.launch('zod', ['/not-executed/vere', '/fake/pier'],
            lifetime_fd=0, log=subprocess.DEVNULL, fresh=True,
            register=register or (lambda child: self.supervisor.PROCESSES.__setitem__('zod', child)))

    def test_post_spawn_failures_remain_owned_and_are_reaped(self):
        for stage in ('bind_child', 'record'):
            with self.subTest(stage=stage):
                self.manager.ingress['zod'].bind_child.side_effect = ValueError('bind failed') if stage == 'bind_child' else None
                self.manager.record.side_effect = ValueError('record failed') if stage == 'record' else None
                with self.assertRaises(ValueError):
                    self.launch()
                child = self.supervisor.PROCESSES['zod']
                self.assertIs(child, self.processes[-1])
                with self.assertRaises(RuntimeError):  # sleep's TERM is deliberately unclean.
                    self.supervisor.all_stop()
                self.assertIsNotNone(child.poll())

    def test_closed_fence_after_jam_prevents_spawn(self):
        original = self.manager.injection.side_effect
        def close_during_jam(ship):
            result = original(ship)
            self.manager.peers.closed.set()
            return result
        self.manager.injection.side_effect = close_during_jam
        with self.assertRaisesRegex(ValueError, 'barrier closed'):
            self.launch()
        self.manager.launcher.spawn.assert_not_called()

    def test_guard_stop_during_jam_prevents_spawn(self):
        original = self.manager.injection.side_effect
        def stop_during_jam(ship):
            result = original(ship)
            self.manager.guard.side_effect = InterruptedError('stopped')
            return result
        self.manager.injection.side_effect = stop_during_jam
        with self.assertRaises(InterruptedError):
            self.launch()
        self.manager.launcher.spawn.assert_not_called()

    def test_stop_during_registration_cannot_leave_child_unowned(self):
        def register(child):
            self.supervisor.PROCESSES['zod'] = child
            self.manager.guard.side_effect = InterruptedError('stopped')
        with self.assertRaises(InterruptedError):
            self.launch(register=register)
        self.assertIs(self.supervisor.PROCESSES['zod'], self.processes[-1])
        with self.assertRaises(RuntimeError):
            self.supervisor.all_stop()
        self.assertIsNotNone(self.processes[-1].poll())

    def test_first_awake_checkpoint_is_final(self):
        child = Mock(); child.poll.return_value = None
        self.supervisor.PROCESSES['zod'] = child
        checkpoint = Mock(side_effect=[ValueError('app awake'), None])
        self.manager.suspension_checkpoint = checkpoint
        with patch.object(self.supervisor, 'execution_check'), patch.object(self.supervisor, 'dojo', return_value='%408'):
            with self.assertRaisesRegex(ValueError, 'app awake'):
                self.supervisor.wait_ready('zod', timeout=1)
        checkpoint.assert_called_once()
        self.manager.peers.release.assert_not_called()

    def test_failure_signals_before_any_blocked_ingress_cleanup(self):
        child = Mock(); child.poll.return_value = None
        self.supervisor.PROCESSES['zod'] = child
        self.manager.disarm_browser = Mock(side_effect=AssertionError('Must not acquire ingress lock here'))
        self.supervisor.peer_fence_failed(ValueError('packet policy unknown'))
        child.terminate.assert_called_once()
        self.assertTrue(self.supervisor.STOP_REQUESTED.is_set())
        self.assertTrue(self.supervisor.FORCED_STOP.is_set())
        self.manager.disarm_browser.assert_not_called()

    def test_restart_missing_app_or_changed_saved_state_is_rejected(self):
        child = Mock(); child.poll.return_value = None
        self.manager.children['zod'] = child
        self.manager.restart_expected['zod'] = 'a' * 64
        for present, digest in ((False, 'a' * 64), (True, 'b' * 64)):
            self.manager.boots['zod'] = {'process': child, 'fresh': False, 'suspended': False}
            with patch.object(self.manager, 'exists_on_base', return_value=present), \
                    patch.object(self.manager, 'saved_fingerprint', return_value=digest):
                with self.assertRaisesRegex(ValueError, 'expected saved state'):
                    self.manager.suspension_checkpoint('zod', Mock(return_value='%.n'))
            self.assertFalse(self.manager.boots['zod']['suspended'])

    def test_saved_state_rejects_wrong_desk_or_failed_native_version_assertion(self):
        with self.assertRaisesRegex(ValueError, 'verified desk'):
            self.manager.saved_fingerprint('zod', Mock(return_value='%other'))
        with self.assertRaisesRegex(ValueError, 'not a hash'):
            self.manager.saved_fingerprint('zod', Mock(side_effect=['%base', 'native assertion failure']))

    def test_rejected_bootstrap_does_not_release_peers(self):
        child = Mock(); child.poll.return_value = None
        self.manager.children['zod'] = child
        self.manager.boots['zod'] = {'process': child, 'suspended': True, 'acknowledged': False, 'nonce': 'new'}
        self.manager.ingress['zod'].arm.side_effect = ValueError('Stale bootstrap completion')
        with patch.object(self.manager, 'exists_on_base', return_value=True):
            with self.assertRaisesRegex(ValueError, 'Stale bootstrap'):
                self.manager.admit('zod', {'nonce': 'old'}, Mock())
        self.manager.peers.release.assert_not_called()
        self.manager.ingress['zod'].disarm.assert_called_with(child)
        self.manager.peers.block.assert_called_with('zod')

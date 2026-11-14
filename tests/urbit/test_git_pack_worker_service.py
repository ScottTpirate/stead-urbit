"""Exercise the reviewed worker profile and real isolated stock Git path."""
import os
from contextlib import nullcontext
from pathlib import Path
from queue import Queue
import shutil
import signal
import socket
import subprocess
import sys
import time
from threading import Thread
import unittest
from unittest.mock import Mock, patch

import test_git_pack_proof as fixtures
from git_pack_receive_adapter import Admission
import git_pack_worker_service as service
from portable_recovery import RecoveryError, decoded, encoded, sha


class WorkerServiceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GitPackProofTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.profile = self.root / 'profile.json'
        self.key = self.root / 'private.pem'
        result = subprocess.run(['/usr/bin/openssl', 'genpkey', '-algorithm', 'Ed25519', '-out', self.key],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.key.chmod(0o600)
        for name in ('spool', 'socket'):
            item = self.root / name
            item.mkdir(mode=0o710 if name == 'socket' else 0o700)
            item.chmod(0o710 if name == 'socket' else 0o700)
        self.git = Path(self.fixture.git).resolve()
        self.values = {
            'protocol': service.PROFILE, 'worker_uid': os.getuid(), 'relay_uid': os.getuid() + 1,
            'socket_gid': os.getgid(), 'socket': str(self.root / 'socket' / 'worker.sock'),
            'spool': str(self.root / 'spool'), 'store': str(self.fixture.storage), 'git': str(self.git),
            'git_sha256': sha(self.git.read_bytes()), 'key': str(self.key), 'key_generation': 5,
        }
        if os.getuid() == 0 or os.getgid() == 0:
            self.skipTest('unprivileged dedicated worker fixture')
        self.write_profile()

    def write_profile(self, **overrides):
        self.profile.write_bytes(encoded(self.values | overrides))
        self.profile.chmod(0o600)

    def real_sandbox(self):
        if not shutil.which(service.BWRAP):
            self.skipTest('fixed Bubblewrap executable unavailable')
        try:
            service.sandbox_ready()
        except RecoveryError as error:
            self.skipTest(f'real namespace fixture unavailable: {error}')

    def test_private_profile_rejects_changed_permissions_symlinks_fields_and_paths(self):
        profile = service.load(self.profile)
        self.assertEqual(profile.key, self.key)
        self.assertEqual(profile.git, self.git)
        self.profile.chmod(0o640)
        with self.assertRaisesRegex(RecoveryError, 'worker-service-private-file'):
            service.load(self.profile)
        self.profile.chmod(0o600)
        alias = self.root / 'alias'
        alias.symlink_to(self.profile)
        with self.assertRaises(OSError):
            service.load(alias)
        for field, value in (('relay_uid', os.getuid()), ('key_generation', True),
                             ('key', str(self.fixture.storage / 'outside.pem')), ('key', '/usr/example.pem'),
                             ('git', './git'), ('provides_shell', True)):
            with self.subTest(field=field, value=value), self.assertRaises(RecoveryError):
                self.write_profile(**{field: value})
                service.load(self.profile)

    def test_refuses_failure_without_opening_socket_or_disclosing_paths(self):
        with patch.object(service, 'sandbox_ready', side_effect=RecoveryError('worker-service-isolation-unavailable')), \
                patch.object(service, 'WorkerSocket') as listener, patch.object(service.sys, 'stderr') as stderr:
            self.assertEqual(service.main(['--profile', str(self.profile)]), 1)
            self.assertNotIn(str(self.root), ''.join(call.args[0] for call in stderr.write.call_args_list))
        listener.assert_not_called()
        self.assertFalse(Path(self.values['socket']).exists())
        self.assertEqual(list(Path(self.values['spool']).iterdir()), [])

    def test_engine_digest_and_signing_key_are_checked_before_socket_open(self):
        self.real_sandbox()
        self.write_profile(git_sha256='c' * 64)
        with self.assertRaisesRegex(RecoveryError, 'worker-service-engine-digest'):
            service.serve(service.load(self.profile))
        self.write_profile()
        self.key.write_bytes(b'invalid signing key')
        with self.assertRaisesRegex(RecoveryError, 'worker-signing-key-type'):
            service.serve(service.load(self.profile))
        self.assertFalse(Path(self.values['socket']).exists())
        self.assertEqual(list(Path(self.values['spool']).iterdir()), [])

    def test_sandboxed_stock_git_preserves_exact_push_proof(self):
        self.real_sandbox()
        wall = time.time_ns() // 1_000_000
        claim = self.fixture.claim | {'admitted_at_ms': str(wall - 1000), 'expires_at_ms': str(wall + 30_000)}
        raw = encoded(claim)
        expected = self.fixture.export(claim, now_ms=lambda: wall)
        profile = service.load(self.profile)
        with service.worker(profile) as worker:
            proof = worker(Admission(raw, sha(raw)), self.fixture.wire, time.monotonic() + 20)
            self.assertEqual(proof, expected)
            self.assertEqual(decoded(proof)['wire_sha256'], claim['wire_sha256'])
        self.assertEqual(list(profile.spool.iterdir()), [])

    def test_engine_receives_only_bare_repo_and_cannot_see_key_store_or_network(self):
        self.real_sandbox()
        profile = service.load(self.profile)
        # A trusted diagnostic replaces Git in this fixture so the exact
        # production wrapper has to enforce isolation against its own engine.
        probe = self.root / 'isolation-probe'
        probe.write_text('#!/usr/bin/python3 -I\n'
                         'from pathlib import Path\nimport os, socket, sys\n'
                         f'assert not any(Path(item).exists() for item in {list(map(str, (profile.key, profile.store, profile.socket, self.root, profile.spool)))!r})\n'
                         'assert [name for _, name in socket.if_nameindex()] == ["lo"]\n'
                         'assert not Path("/etc").exists()\n'
                         'assert len(list(Path("/proc").glob("[0-9]*"))) <= 3\n'
                         'for fd in Path("/proc/self/fd").iterdir():\n'
                         '    try: target = os.readlink(fd)\n'
                         '    except FileNotFoundError: continue\n'
                         f'    assert not target.startswith({str(self.root)!r}), target\n'
                         'assert os.statvfs("/").f_flag & os.ST_RDONLY\n'
                         'assert sys.argv[1:3] == ["--git-dir", "/repo"]\n'
                         'assert (Path("/repo") / "known").read_bytes() == b"fixture"\n'
                         '(Path("/repo") / "result").write_bytes(b"private")\n', encoding='ascii')
        probe.chmod(0o700)
        repository = self.root / 'temporary-repo'
        repository.mkdir(mode=0o700)
        (repository / 'known').write_bytes(b'fixture')
        self.write_profile(git=str(probe), git_sha256=sha(probe.read_bytes()))
        with service.worker(service.load(self.profile)) as worker, service.directory_fd(repository) as fd:
            environment = dict.fromkeys(service.GIT_ENV, '')
            result = subprocess.run([worker.git, '--git-dir', f'/proc/self/fd/{fd}', 'probe'],
                                    env=environment, pass_fds=(fd,), capture_output=True, timeout=6)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((repository / 'result').read_bytes(), b'private')

    def test_sigterm_ends_idle_foreground_service_and_releases_exact_socket(self):
        self.real_sandbox()
        profile = service.load(self.profile)
        launcher = Path(service.__file__).resolve()
        with subprocess.Popen([sys.executable, '-B', launcher, '--profile', self.profile],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as daemon:
            try:
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline and not profile.socket.is_socket() and daemon.poll() is None:
                    time.sleep(0.02)
                self.assertTrue(profile.socket.is_socket())
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as unauthorized:
                    unauthorized.settimeout(2)
                    unauthorized.connect(str(profile.socket))
                    self.assertEqual(unauthorized.recv(1), b'')
                daemon.send_signal(signal.SIGTERM)
                self.assertEqual(daemon.wait(timeout=2), 0)
            finally:
                if daemon.poll() is None:
                    daemon.kill()
        self.assertFalse(profile.socket.exists())
        self.assertEqual(list(profile.spool.iterdir()), [])

    def test_sigterm_in_flight_allows_current_request_to_finish_once(self):
        profile = service.load(self.profile)
        served = []
        original = signal.getsignal(signal.SIGTERM)

        def request(*args, **kwargs):
            served.append('started')
            signal.raise_signal(signal.SIGTERM)
            served.append('finished')

        endpoint = Mock(serve_one=Mock(side_effect=request))
        with patch.object(service, 'worker', return_value=nullcontext(Mock())), \
                patch.object(service, 'WorkerSocket', return_value=nullcontext(endpoint)):
            service.serve(profile)
        endpoint.serve_one.assert_called_once()
        self.assertEqual(served, ['started', 'finished'])
        self.assertEqual(signal.getsignal(signal.SIGTERM), original)

    def test_stopping_during_accept_refuses_the_new_connection(self):
        profile = service.load(self.profile)
        worker = Mock()
        outcome = Queue()
        entered = Queue()
        later = iter((False, True))

        def stopping():
            stopped = next(later)
            if not stopped:
                entered.put(True)
            return stopped

        with service.WorkerSocket(profile.socket, profile.spool, profile.relay_uid, profile.worker_uid, worker,
                                  profile.key_generation, profile.key, group_gid=profile.socket_gid) as endpoint, \
                socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as new_connection:
            runner = Thread(target=lambda: outcome.put(endpoint.serve_one(time.monotonic() + 4, stopping=stopping)),
                            daemon=True)
            runner.start()
            entered.get(timeout=2)
            new_connection.settimeout(2)
            new_connection.connect(str(profile.socket))
            self.assertEqual(new_connection.recv(1), b'')
            self.assertFalse(outcome.get(timeout=2))
            runner.join(2)
        worker.assert_not_called()


if __name__ == '__main__':
    unittest.main()

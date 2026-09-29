"""Real host sockets/child lifetimes; dummy byte backend, not TLS/Eyre evidence."""
from pathlib import Path
import importlib.util
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('stead_tls_ingress', ROOT / 'web/dev/ingress.py')
ingress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingress)


class IngressTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / '.runtime/ingress-host-tests'
        directory.mkdir(parents=True, exist_ok=True)
        # Exercise a real sun_path overflow even from a short checkout path.
        self.temp = tempfile.TemporaryDirectory(prefix='nested-' + 'x' * 80, dir=directory)
        self.addCleanup(self.temp.cleanup)
        self.calls = []
        self.back = socket.socket()
        self.back.bind(('127.0.0.1', 0)); self.back.listen(8)
        self.back.settimeout(.1)
        self.stop = threading.Event()
        self.guard_failed = False
        self.peers = set()
        self.worker = threading.Thread(target=self.echo, daemon=True); self.worker.start()
        self.fence = None
        self.children = []
        self.addCleanup(self.cleanup)
        self.fence = ingress.TLSIngress(self.temp.name, 'zod', self.guard, connect=self.connect)
        self.first = self.child()
        self.nonce = self.fence.bind_child(self.first)

    def guard(self):
        if self.guard_failed:
            raise RuntimeError('Guard expired')

    def connect(self, target, *, timeout):
        self.calls.append(target)
        self.assertEqual(target, ('127.0.0.1', 18443))
        return socket.create_connection(self.back.getsockname(), timeout=timeout)

    def child(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.children.append(process)
        return process

    def echo(self):
        while not self.stop.is_set():
            try:
                peer, _ = self.back.accept(); self.peers.add(peer); peer.settimeout(.1)
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                while not self.stop.is_set():
                    try:
                        data = peer.recv(16384)
                        if not data: break
                        peer.sendall(data)
                    except socket.timeout:
                        continue
            except OSError:
                pass
            finally:
                peer.close(); self.peers.discard(peer)

    def cleanup(self):
        if self.fence is not None:
            self.fence.close()
        self.stop.set(); self.back.close()
        for peer in tuple(self.peers): peer.close()
        self.worker.join(timeout=2)
        for process in self.children:
            if process.poll() is None: process.terminate()
            process.wait(timeout=2)
        self.assertFalse(self.worker.is_alive())

    def peer(self):
        client = socket.socket(socket.AF_UNIX); client.settimeout(2)
        self.addCleanup(client.close)
        directory = os.open(self.fence.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            client.connect(f'/proc/self/fd/{directory}/{self.fence.path.name}')
        finally:
            os.close(directory)
        return client

    def ack(self, nonce=None, **extra):
        return dict(protocol='stead.bootstrap/1', status='ready', home='~zod', nonce=nonce or self.nonce, incarnation='a' * 64, **extra)

    def closed(self, peer):
        try: self.assertEqual(peer.recv(1), b'')
        except (ConnectionResetError, BrokenPipeError): pass

    def test_no_backend_bytes_before_bootstrap_then_exact_raw_relay(self):
        self.assertGreater(len(os.fsencode(self.fence.path)), 107)
        peer = self.peer(); peer.sendall(b'pre-bootstrap'); self.closed(peer)
        self.assertEqual(self.calls, [])
        self.fence.arm(self.first, self.nonce, self.ack())
        peer = self.peer(); data = b'\x16\x03\x01synthetic-opaque-bytes'; peer.sendall(data)
        self.assertEqual(peer.recv(100), data)
        self.assertEqual(self.calls, [('127.0.0.1', 18443)])

    def test_existing_socket_is_preserved_when_second_bind_is_refused(self):
        inode = self.fence.path.stat().st_ino
        with self.assertRaises(OSError):
            ingress.TLSIngress(self.temp.name, 'zod', self.guard, connect=self.connect)
        self.assertEqual(self.fence.path.stat().st_ino, inode)
        self.fence.arm(self.first, self.nonce, self.ack())
        peer = self.peer(); peer.sendall(b'original')
        self.assertEqual(peer.recv(20), b'original')

    def test_shared_or_redirected_directory_cannot_admit_a_listener(self):
        path = Path(self.temp.name) / 'other'
        path.mkdir(mode=0o750)
        path.chmod(0o750)
        with self.assertRaisesRegex(ValueError, 'mode 0700'):
            ingress.TLSIngress(path, 'bus', self.guard)
        path.rmdir()
        path.symlink_to(self.temp.name, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Private existing'):
            ingress.TLSIngress(path, 'bus', self.guard)
        path.unlink()

    def test_stale_ack_cannot_reopen_a_new_child_or_reuse_an_accepted_nonce(self):
        self.fence.arm(self.first, self.nonce, self.ack())
        peer = self.peer(); peer.sendall(b'first'); self.assertEqual(peer.recv(10), b'first')
        second = self.child()
        with self.assertRaisesRegex(ValueError, 'Previous child'): self.fence.bind_child(second)
        self.first.terminate(); self.first.wait(timeout=2)
        second_nonce = self.fence.bind_child(second)
        self.closed(peer)
        with self.assertRaises(ValueError): self.fence.arm(self.first, self.nonce, self.ack())
        self.closed(self.peer())
        self.fence.arm(second, second_nonce, self.ack(second_nonce))
        with self.assertRaises(ValueError): self.fence.arm(second, second_nonce, self.ack(second_nonce))
        self.assertFalse(self.fence.armed)

    def test_child_exit_and_guard_failure_close_existing_streams(self):
        self.fence.arm(self.first, self.nonce, self.ack())
        peer = self.peer(); peer.sendall(b'live'); self.assertEqual(peer.recv(10), b'live')
        self.first.terminate(); self.first.wait(timeout=2); self.closed(peer)
        second = self.child(); nonce = self.fence.bind_child(second)
        self.fence.arm(second, nonce, self.ack(nonce)); peer = self.peer()
        peer.sendall(b'live'); self.assertEqual(peer.recv(10), b'live')
        self.guard_failed = True; self.closed(peer)
        with self.assertRaises(RuntimeError): self.fence.arm(second, nonce, self.ack(nonce))
        self.assertFalse(self.fence.armed)

    def test_disarm_retires_even_an_unconsumed_bootstrap_ack(self):
        captured = self.ack()
        self.fence.disarm(self.first)
        with self.assertRaises(ValueError): self.fence.arm(self.first, self.nonce, captured)
        self.closed(self.peer()); self.assertEqual(self.calls, [])
        fresh = self.fence.bind_child(self.first)
        self.assertNotEqual(fresh, self.nonce)
        self.fence.arm(self.first, fresh, self.ack(fresh))
        peer = self.peer(); peer.sendall(b'fresh'); self.assertEqual(peer.recv(10), b'fresh')

    def test_first_monitor_refusal_survives_recovery_rollback_and_snapshot_mutation(self):
        raised = threading.Event()
        def once():
            if threading.current_thread() is self.fence.monitor and not raised.is_set():
                raised.set()
                raise ValueError('Control input must be bounded and singly linked')
        with patch.object(self.fence, 'guard', side_effect=once):
            deadline = time.monotonic() + 2
            while not self.fence.retirement() and time.monotonic() < deadline:
                time.sleep(.01)
            expected = {'cause': 'guard-refusal', 'error': 'control-input'}
            self.assertEqual(self.fence.retirement(), expected)
            with self.assertRaisesRegex(ValueError, 'Stale bootstrap'):
                self.fence.arm(self.first, self.nonce, self.ack())
            self.fence.disarm(self.first)
            observed = self.fence.retirement(); observed['cause'] = 'changed'
            self.assertEqual(self.fence.retirement(), expected)
        self.assertFalse(self.fence.armed)
        self.closed(self.peer()); self.assertEqual(self.calls, [])
        fresh = self.fence.bind_child(self.first)
        self.assertNotEqual(fresh, self.nonce)
        self.assertEqual(self.fence.retirement(), {})

    def test_retirement_never_retains_unknown_exception_text(self):
        with patch.object(self.fence, 'guard', side_effect=ValueError('PRIVATE_GUARD_DETAIL')):
            with self.assertRaises(ValueError):
                self.fence.arm(self.first, self.nonce, self.ack())
        self.assertEqual(self.fence.retirement(), {'cause': 'guard-refusal', 'error': 'unrecognized'})
        self.fence.close()
        self.assertEqual(self.fence.retirement(), {'cause': 'guard-refusal', 'error': 'unrecognized'})

    def test_relay_thread_start_failure_releases_all_owned_sockets(self):
        self.fence.arm(self.first, self.nonce, self.ack())
        with patch.object(ingress.threading.Thread, 'start', side_effect=RuntimeError('injected thread failure')):
            peer = self.peer(); self.closed(peer)
        with self.fence.lock:
            self.assertEqual(self.fence.connections, set())
            self.assertEqual(self.fence.threads, set())

    def test_ack_shape_and_target_ship_are_fixed(self):
        with self.assertRaises(ValueError): self.fence.arm(self.first, self.nonce, self.ack(extra='x'))
        with self.assertRaises(ValueError): ingress.TLSIngress(self.temp.name, 'any-port', self.guard)
        peer = self.peer(); self.closed(peer); self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()

"""Real local sockets with synthetic byte backends; no native/TLS acceptance."""
from contextlib import ExitStack
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/dev'))
from loopback_bridge import LoopbackBridge, PORTS


class LoopbackBridgeTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix='stead-host-relay-'))
        self.directory = Path(directory); self.directory.chmod(0o700)
        self.closed = threading.Event()
        self.servers, self.backends, self.threads = [], [], []
        self.stack.callback(self.cleanup_backends)
        for ship in PORTS:
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(self.directory / (ship + '.tls.sock')))
            (self.directory / (ship + '.tls.sock')).chmod(0o600)
            server.listen(64); server.settimeout(.1); self.servers.append(server)
            thread = threading.Thread(target=self.accept, args=(server,), daemon=True)
            self.threads.append(thread); thread.start()
        self.bridge = self.stack.enter_context(LoopbackBridge(self.directory, lambda: None))

    def cleanup_backends(self):
        self.closed.set()
        for stream in [*self.servers, *self.backends]:
            try:
                stream.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            stream.close()
        for thread in self.threads:
            thread.join(timeout=2)

    def accept(self, server):
        while not self.closed.is_set():
            try:
                peer, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.backends.append(peer)
            thread = threading.Thread(target=self.echo, args=(peer,), daemon=True)
            self.threads.append(thread); thread.start()

    def echo(self, peer):
        try:
            while not self.closed.is_set():
                data = peer.recv(16384)
                if not data:
                    peer.shutdown(socket.SHUT_WR)
                    return
                peer.sendall(data)
        except OSError:
            pass
        finally:
            peer.close()

    @staticmethod
    def wait(predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            if time.monotonic() > deadline:
                raise AssertionError('Host relay condition timed out')
            time.sleep(.01)

    def connect(self, ship='zod'):
        return self.stack.enter_context(socket.create_connection(('127.0.0.1', PORTS[ship]), timeout=2))

    def test_exact_binary_bytes_and_headers_and_half_close(self):
        payload = bytes(range(256)) * 1024 + b'Forwarded: proto=https\r\nX-Forwarded-For: synthetic\r\n'
        for ship in PORTS:
            client = self.connect(ship)
            sender = threading.Thread(target=lambda: (client.sendall(payload), client.shutdown(socket.SHUT_WR)))
            sender.start()
            received = bytearray()
            while block := client.recv(16384):
                received.extend(block)
            sender.join(timeout=2)
            self.assertFalse(sender.is_alive())
            self.assertEqual(bytes(received), payload)

    def test_failed_worker_start_leaves_no_worker_or_stream(self):
        original = threading.Thread.start
        def start(thread):
            if thread._target == self.bridge.relay:
                raise RuntimeError('authored thread-start failure')
            return original(thread)
        with patch.object(threading.Thread, 'start', start):
            for _ in range(4):
                client = self.connect()
                self.assertEqual(client.recv(1), b'')
        # Frontend EOF can precede removal of the backend in the same locked
        # failure handler. Observe the completed cleanup transaction.
        with self.bridge.lock:
            self.assertEqual(self.bridge.workers, set())
            self.assertEqual(self.bridge.streams, set())

    def test_connection_bound_and_health_failure_close_streams(self):
        clients = [self.connect() for _ in range(32)]
        self.wait(lambda: len(self.bridge.streams) == 64)
        extra = self.connect()
        self.assertEqual(extra.recv(1), b'')
        def failed():
            raise ValueError('authored guard stop')
        self.bridge.healthy = failed
        self.assertTrue(self.bridge.closed.wait(2))
        self.wait(lambda: not self.bridge.workers)
        self.assertTrue(all(client.recv(1) == b'' for client in clients))

    def test_changed_socket_mode_is_refused_before_connect(self):
        (self.directory / 'zod.tls.sock').chmod(0o666)
        client = self.connect()
        self.assertEqual(client.recv(1), b'')
        self.assertEqual(self.bridge.streams, set())

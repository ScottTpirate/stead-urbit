"""Actual local socket/UDP controls. These do not execute or qualify Urbit."""
import importlib.util
import json
from pathlib import Path
import socket
import struct
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('sdk_bridge', ROOT / 'scripts/sdk_native/bridge.py')
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class SDKBridgeTests(unittest.TestCase):
    def setUp(self):
        self.parent, self.peer = socket.socketpair()
        self.bridge = BRIDGE.Bridge(self.parent, 31519, 31337)
        self.native = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.native.bind(('127.0.0.1', 31337))
        self.native.settimeout(.2)
        self.peer.settimeout(.3)

    def tearDown(self):
        self.bridge.close()
        self.peer.close()
        self.native.close()

    def wait_failed(self):
        deadline = time.monotonic() + 2
        while self.bridge.error is None and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertIsNotNone(self.bridge.error)
        self.assertFalse(self.bridge.opened.is_set())

    def frame(self, kind, payload):
        self.peer.sendall(kind + struct.pack('!I', len(payload)) + payload)

    def test_bidirectional_fixed_udp_preserves_packet_and_source(self):
        self.bridge.admit()
        self.native.sendto(b'outgoing\0bytes', ('127.0.0.1', 31519))
        header = BRIDGE.exact(self.peer, 5)
        self.assertEqual(header[:1], b'D')
        self.assertEqual(BRIDGE.exact(self.peer, struct.unpack('!I', header[1:])[0]), b'outgoing\0bytes')
        self.frame(b'D', b'incoming\0bytes')
        raw, address = self.native.recvfrom(65536)
        self.assertEqual((raw, address), (b'incoming\0bytes', ('127.0.0.1', 31519)))

    def test_pre_admission_datagrams_are_discarded_not_delayed(self):
        self.native.sendto(b'closed-outbound', ('127.0.0.1', 31519))
        self.frame(b'D', b'closed-inbound')
        deadline = time.monotonic() + 2
        while self.bridge.dropped != 2 and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(self.bridge.dropped, 2)
        self.bridge.admit()
        with self.assertRaises(TimeoutError):
            self.native.recvfrom(100)
        with self.assertRaises(TimeoutError):
            self.peer.recv(1)

    def test_wrong_local_udp_sender_closes_forwarding(self):
        self.bridge.admit()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as stranger:
            stranger.sendto(b'wrong-source', ('127.0.0.1', 31519))
        self.wait_failed()

    def test_oversized_datagram_is_not_truncated_into_valid_packet(self):
        self.bridge.admit()
        # IPv4 maximum itself cannot be exceeded through sendto; the stream
        # boundary must reject a too-large frame before allocating its body.
        self.peer.sendall(b'D' + struct.pack('!I', 65508))
        self.wait_failed()

    def test_unknown_frame_cannot_select_an_address_or_protocol(self):
        self.peer.sendall(b'T' + struct.pack('!I', 4) + b'HTTP')
        self.wait_failed()

    def test_eof_during_frame_closes_transport(self):
        self.peer.sendall(b'D\0')
        self.peer.shutdown(socket.SHUT_WR)
        self.wait_failed()

    def test_command_queue_is_bounded(self):
        self.frame(b'J', b'{"id":1}')
        self.frame(b'J', b'{"id":2}')
        self.wait_failed()

    def test_json_request_and_response_keep_correlation(self):
        self.frame(b'J', b'{"id":1,"operation":"stop","value":{}}')
        self.assertEqual(self.bridge.get(1), {'id': 1, 'operation': 'stop', 'value': {}})
        self.bridge.message({'id': 1, 'result': {'reaped': True}})
        header = BRIDGE.exact(self.peer, 5)
        self.assertEqual(header[:1], b'J')
        self.assertEqual(json.loads(BRIDGE.exact(self.peer, struct.unpack('!I', header[1:])[0])), {'id': 1, 'result': {'reaped': True}})

    def test_alias_port_is_exclusive(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as duplicate:
            with self.assertRaises(OSError):
                duplicate.bind(('127.0.0.1', 31519))

    def test_fixed_ports_only(self):
        with self.assertRaises(ValueError):
            BRIDGE.Bridge(self.peer, 31337, 80)

    def test_one_absolute_deadline_for_trickled_frame(self):
        self.peer.sendall(b'D' + struct.pack('!I', 8))
        started = time.monotonic()
        for _ in range(4):
            time.sleep(.6)
            if self.bridge.error is not None:
                break
            self.peer.sendall(b'x')
        self.wait_failed()
        self.assertIsInstance(self.bridge.error, TimeoutError)
        self.assertLess(time.monotonic() - started, 3)

    def test_disarm_clears_queued_forwarding_across_a_paused_receiver(self):
        self.bridge.admit()
        with self.bridge.forward_lock:
            self.native.sendto(b'queued', ('127.0.0.1', 31519))
            done = threading.Event()
            def close_admission():
                self.bridge.disarm()
                done.set()
            controller = threading.Thread(target=close_admission)
            controller.start()
            deadline = time.monotonic() + 1
            while self.bridge.opened.is_set() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertFalse(self.bridge.opened.is_set())
        controller.join(1)
        self.assertTrue(done.is_set())
        with self.assertRaises(TimeoutError):
            self.peer.recv(1)


if __name__ == '__main__':
    unittest.main()

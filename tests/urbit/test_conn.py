"""Host parser regressions from actual native failure; not new native execution."""
import json
from pathlib import Path
import socket
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import conn


class ConnRegressions(unittest.TestCase):
    def test_actual_khan_rejection_has_unprefixed_hint(self):
        report = json.loads((ROOT / 'docs/urbit/evidence/2026-09-12/native-smoke-rejection-parser-failure.json').read_text())
        response = report['commands'][-1]['result']
        conn.assert_result(response, False, '%stead-smoke-denied')
        for bad in ('%stead-smoke-stale', 'thread-fail', None):
            with self.assertRaises(AssertionError):
                conn.assert_result(response, False, bad)
        with self.assertRaises(AssertionError):
            conn.assert_result(response, True)

    def test_network_or_generic_failure_cannot_pass_negative(self):
        for stdout, stderr in (('[32 %avow 0 %noun %stead-smoke-ack]', 'stead-smoke-denied\npoke-fail'),
                               ('[32 %avow 1]', 'poke-fail'),
                               ('[32 %avow 1]', 'unrelated stead-smoke-denied prefix\npoke-fail')):
            with self.assertRaises(AssertionError):
                conn.assert_result({'stdout': stdout, 'stderr': stderr}, False, '%stead-smoke-denied')

    def test_newt_bounds_and_tag(self):
        for header in (b'error', b'\0\0\0\0\0', b'\1\1\0\0\0', b'\0' + (conn.LIMIT + 1).to_bytes(4, 'little'), b''):
            with self.assertRaises(ValueError):
                conn.framed_length(header)

    def test_deadline_and_eof_fail_without_terminal_result(self):
        left, right = socket.socketpair()
        with left, right:
            with self.assertRaises(TimeoutError):
                conn.read_exact(left, 5, time.monotonic() - 1)
            right.shutdown(socket.SHUT_WR)
            with self.assertRaises(ValueError):
                conn.read_exact(left, 5, time.monotonic() + 1)

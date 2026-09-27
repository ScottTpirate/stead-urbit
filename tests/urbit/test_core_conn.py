"""Host framing regressions; these do not substitute for native execution."""
import json
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import core_conn


class CoreConnectionTests(unittest.TestCase):
    def wrap(self, raw):
        return "[32 %avow 0 %noun %stead-core-result '" + raw.hex() + "']"

    def test_exact_json_bytes_survive_hoon_renderer_heuristics(self):
        raw = json.dumps({'markdown': 'quote " \\ newline\n café 🛰', 'empty': ''}, ensure_ascii=False).encode()
        result = core_conn.parse_response(self.wrap(raw))
        self.assertEqual(result['raw'].encode(), raw)
        self.assertEqual(result['json'], json.loads(raw))

    def test_nack_or_bare_ack_cannot_become_acceptance(self):
        self.assertIsNone(core_conn.parse_response('[32 %avow 1]'))
        for value in ('>=', '[32 %avow 0]', '[32 %avow 0 %noun %stead-core-result 0x7b7d]',
                      self.wrap(b'{}') + self.wrap(b'{}')):
            with self.assertRaises(ValueError):
                core_conn.parse_response(value)

    def test_malformed_result_never_becomes_business_json(self):
        for raw in (b'{"status":"accepted","status":"rejected"}', b'[]', b'\xff', b'{}\0', b'{} {}',
                    b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}'):
            with self.assertRaises((ValueError, UnicodeError)):
                core_conn.parse_response(self.wrap(raw))

    def test_cord_and_path_limits_fail_before_executing_runtime(self):
        with patch.object(core_conn.subprocess, 'run') as process:
            for kwargs in ({'raw': b'{}\0'}, {'raw': b'x' * 70001},
                           {'route': "/v1/' injected"}, {'route': '/' + 'x' * 1024}):
                with self.assertRaises(ValueError):
                    core_conn.run('/unused', '/unused', 'poke', **kwargs)
            process.assert_not_called()

    def test_control_bounds_fail_before_runtime(self):
        with patch.object(core_conn, 'evaluate') as evaluate:
            for key, value in (('x' * 1025, ''), ('', 'x' * 65537), ('', 'bad\0value')):
                with self.assertRaises(ValueError):
                    core_conn.run('/unused', '/unused', 'control',
                                  control=('legacy-read', 'bus', key, value))
            evaluate.assert_not_called()

    def test_evaluator_zero_exit_and_truncation_controls(self):
        # Mocked evaluator outputs test failure propagation, not native success.
        frame = b'\0' + (70000).to_bytes(4, 'little') + b'x' * 70000
        with patch.object(core_conn, 'evaluate', return_value=(frame, b'')):
            with self.assertRaisesRegex(AssertionError, 'Invalid evaluator input'):
                core_conn.evaluator_controls('/unused')
        with patch.object(core_conn, 'evaluate', side_effect=[(b'', b'parse failed'), (frame[:-1], b'')]):
            with self.assertRaisesRegex(AssertionError, 'truncated'):
                core_conn.evaluator_controls('/unused')

    def test_evaluator_missing_or_partial_terminal_result_fails(self):
        frame = b'\0' + (70000).to_bytes(4, 'little') + b'x' * 70000
        for terminal in (b'[32 %avow 1]', b"[32 %avow 0 %noun %stead-core-result '7b7d']"):
            with self.subTest(terminal=terminal), patch.object(core_conn, 'evaluate',
                    side_effect=[(b'', b'parse failed'), (frame, b''), (terminal, b'')]):
                with self.assertRaisesRegex(AssertionError, 'exact bytes'):
                    core_conn.evaluator_controls('/unused')

    def test_evaluator_requires_actual_frame_larger_than_pipe_boundary(self):
        for size in (32, 65536):
            frame = b'\0' + (size - 5).to_bytes(4, 'little') + b'x' * (size - 5)
            with self.subTest(size=size), patch.object(core_conn, 'evaluate',
                    side_effect=[(b'', b'parse failed'), (frame, b'')]):
                with self.assertRaisesRegex(AssertionError, 'not above64KiB'):
                    core_conn.evaluator_controls('/unused')

    def test_evaluator_large_frame_requires_exact_roundtrip(self):
        expected = {'protocol': 'stead.framing-control/1', 'synthetic_text': 'x' * 34000}
        raw = json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()
        frame = b'\0' + (68000).to_bytes(4, 'little') + b'x' * 68000
        with patch.object(core_conn, 'evaluate', side_effect=[(b'', b'parse failed'),
                (frame, b''), (self.wrap(raw).encode(), b'')]):
            result = core_conn.evaluator_controls('/unused')
        self.assertEqual(result['status'], 'passed')
        self.assertGreater(result['large_frame_bytes'], 65536)
        self.assertEqual(result['large_frame_hex'], frame.hex())
        self.assertEqual(result['decoded_stdout'], self.wrap(raw))
        self.assertEqual([r['argv'] for r in result['commands']], [
            ['/unused', 'eval', '--loom', '29', flag] for flag in ('-jn', '-jn', '-ckn')])
        self.assertEqual(bytes.fromhex(result['commands'][0]['input_hex']), b'[')
        self.assertEqual(bytes.fromhex(result['commands'][1]['stdout_hex']), frame)
        self.assertEqual(bytes.fromhex(result['commands'][2]['input_hex']), frame)
        self.assertEqual(bytes.fromhex(result['commands'][2]['stdout_hex']), self.wrap(raw).encode())

    def test_evaluator_crash_is_not_an_expected_parse_rejection(self):
        with patch.object(core_conn, 'evaluate', side_effect=subprocess.CalledProcessError(-11, ['Vere', 'eval'])):
            with self.assertRaises(subprocess.CalledProcessError):
                core_conn.evaluator_controls('/unused')

    def test_evaluator_silent_missing_output_cannot_pass(self):
        with patch.object(core_conn, 'evaluate', return_value=(b'', b'')):
            with self.assertRaisesRegex(AssertionError, 'parse failure evidence'):
                core_conn.evaluator_controls('/unused')

    def test_partial_frame_and_timeout_preserve_failed_exchange(self):
        request = b'\0\1\0\0\0x'
        header = b'\0\x0a\0\0\0'
        for ending in (b'', TimeoutError('bounded synthetic timeout')):
            channel = MagicMock()
            channel.__enter__.return_value = channel
            channel.recv.side_effect = [header, b'xy', ending]
            with self.subTest(ending=ending), patch.object(core_conn, 'evaluate', return_value=(request, b'')), \
                    patch.object(core_conn.socket, 'socket', return_value=channel):
                with self.assertRaises((ValueError, TimeoutError)) as failed:
                    core_conn.run('/unused', '/unused', 'read')
                trace = failed.exception.native_failure
                self.assertEqual(trace['stage'], 'response-body')
                self.assertEqual(trace['received_frame_hex'], (header + b'xy').hex())
                self.assertEqual(trace['encoded_frame_hex'], request.hex())

    def test_encoder_process_failure_retains_diagnostics(self):
        error = subprocess.CalledProcessError(-11, ['Vere', 'eval'], output=b'partial', stderr=b'crash diagnostic')
        with patch.object(core_conn, 'evaluate', side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError) as failed:
                core_conn.run('/unused', '/unused', 'read')
            self.assertEqual(failed.exception.native_failure['evaluator_exit'], -11)
            self.assertEqual(failed.exception.native_failure['evaluator_output_hex'], b'partial'.hex())
            self.assertEqual(failed.exception.native_failure['evaluator_stderr'], 'crash diagnostic')

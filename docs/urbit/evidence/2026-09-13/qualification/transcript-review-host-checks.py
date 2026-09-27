"""Retained replay of independent host checks originally executed inline.

Only temporary files, mocked evaluator/socket/process outputs, and the Python
standard library are used. This script never launches Vere or a fake ship.
The rotation check was originally a separate inline probe; here it is a fifth
test beside the four original wrapper checks.
"""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import core_conn
import native_transcript


class IndependentWrapperReview(unittest.TestCase):
    def implementation(self, *, code=0, out=b'framed output', err=b'diagnostic', timeout=False):
        def run(args, *, stdout, stderr, **kwargs):
            stdout.write(out)
            stderr.write(err)
            if timeout:
                raise subprocess.TimeoutExpired(args, 30)
            return SimpleNamespace(returncode=code, args=args)
        return run

    def test_real_tempfiles_preserve_both_streams(self):
        with patch.object(core_conn.subprocess, 'run', side_effect=self.implementation()):
            self.assertEqual(core_conn.evaluate('/unused', '-jn', b'input'),
                             (b'framed output', b'diagnostic'))

    def test_nonzero_and_timeout_preserve_bounded_both_streams(self):
        for options, exception in (({'code': -11}, subprocess.CalledProcessError),
                                   ({'timeout': True}, subprocess.TimeoutExpired)):
            with self.subTest(options=options), patch.object(
                    core_conn.subprocess, 'run', side_effect=self.implementation(**options)):
                with self.assertRaises(exception) as result:
                    core_conn.evaluate('/unused', '-jn', b'input')
                self.assertEqual(result.exception.output, b'framed output')
                self.assertEqual(result.exception.stderr, b'diagnostic')

    def test_oversized_stdout_and_stderr_keep_prefix_and_fail(self):
        for values in ({'out': b'x' * 1000002}, {'err': b'y' * 1000002}):
            with self.subTest(stream=next(iter(values))), patch.object(
                    core_conn.subprocess, 'run', side_effect=self.implementation(**values)):
                with self.assertRaises(ValueError) as result:
                    core_conn.evaluate('/unused', '-jn', b'input')
                evidence = result.exception.eval_failure
                self.assertFalse(evidence['complete'])
                self.assertLessEqual(len(evidence['stdout_prefix_hex']), 2000002)
                self.assertLessEqual(len(evidence['stderr_prefix_hex']), 2000002)

    def test_max_wire_and_bad_terminal_failure_is_retained_exactly(self):
        request = b'\0\x01\0\0\0x'
        body = b'x' * 1000000
        header = b'\0' + len(body).to_bytes(4, 'little')
        channel = MagicMock()
        channel.__enter__.return_value = channel
        channel.recv.side_effect = [header, body]
        with patch.object(core_conn, 'evaluate', side_effect=[
                (request, b''), (b'invalid' + b'x' * 999993, b'')]), \
                patch.object(core_conn.socket, 'socket', return_value=channel):
            with self.assertRaises(ValueError) as result:
                core_conn.run('/unused', '/unused', 'read')
        failure = {'status': 'failed', 'transport': result.exception.native_failure}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'raw.gz'
            transcript = native_transcript.Transcript(path)
            reference = transcript.append(failure)
            final = transcript.close()
            self.assertGreater(reference['record_bytes'], 3 * 1024 * 1024)
            self.assertEqual(final['records'], 1)
            self.assertEqual(json.loads(gzip.decompress(path.read_bytes())), failure)

    def test_rotation_after_open_refuses_same_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for ship in ('zod', 'bus', 'nec', 'bud'):
                (root / (ship + '.log')).write_bytes(b'old normal\n')
            transcript = native_transcript.Transcript(root / 'raw.gz')
            logs = native_transcript.RuntimeLogs(root, transcript)
            cursor = logs()['cursor']
            old = (root / 'bus.log').stat()
            actual_fstat = os.fstat
            changed = False

            def rotate_after_open(fd):
                nonlocal changed
                value = actual_fstat(fd)
                if not changed and (value.st_ino, value.st_dev) == (old.st_ino, old.st_dev):
                    changed = True
                    (root / 'bus.log').rename(root / 'bus.old')
                    (root / 'bus.log').write_bytes(b'need-mark stead-result-2\n')
                return value

            try:
                with patch.object(native_transcript.os, 'fstat', side_effect=rotate_after_open):
                    with self.assertRaisesRegex(ValueError, 'rotated during observation'):
                        logs(cursor)
            finally:
                transcript.close()
            self.assertTrue(changed)


if __name__ == '__main__':
    unittest.main(verbosity=2)

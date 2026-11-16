"""Actual helper with only synthetic command/log effects; no native child."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts/urbit')]
from team_check import build_probe


class BuildProbeTests(unittest.TestCase):
    def test_exact_command_failure_retains_only_new_interval_and_reraises(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'zod.log'; log.write_bytes(b'older unrelated text\n')
            report, checkpoints, calls = {}, [], []
            def command(*args):
                calls.append(args)
                with log.open('ab') as stream: stream.write(b'new probe compiler result\n')
                raise AssertionError('original probe assertion')
            with self.assertRaisesRegex(AssertionError, '^original probe assertion$'):
                build_probe('zod', command, report, checkpoints.append, Path(directory))
            self.assertEqual(calls, [('zod', '+stead-build-probe', '%stead-builds-pass')])
            row = report['build_probe_transcripts'][0]
            self.assertEqual(bytes.fromhex(row['log_hex']), b'new probe compiler result\n')
            self.assertEqual(row['log_offset'], len(b'older unrelated text\n'))
            self.assertEqual(checkpoints, ['build-probe-output'])

    def test_transport_failure_preserves_failure_and_captures_before_pure_units(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'zod.log').write_bytes(b'')
            report = {}
            def command(*args): raise TimeoutError('transport deadline')
            with self.assertRaisesRegex(TimeoutError, '^transport deadline$'):
                build_probe('zod', command, report, lambda stage: None, Path(directory))
            self.assertEqual(report['build_probe_transcripts'][0]['log_bytes'], 0)

    def test_oversized_interval_refuses_and_success_retains_original_return(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'zod.log'; log.write_bytes(b'')
            def too_big(*args): log.write_bytes(b'x' * 262145)
            with self.assertRaisesRegex(ValueError, '^Native build probe log byte bound$'):
                build_probe('zod', too_big, {}, lambda stage: None, Path(directory))
            log.write_bytes(b'')
            self.assertEqual(build_probe('zod', lambda *args: '%stead-builds-pass', {},
                                        lambda stage: None, Path(directory)), '%stead-builds-pass')


if __name__ == '__main__':
    unittest.main()

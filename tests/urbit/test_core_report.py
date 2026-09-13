"""Host-only report admission controls. Importing the runner starts no runtime."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import core_test


class ReportBoundsTests(unittest.TestCase):
    def test_incomplete_result_is_not_promoted(self):
        original = {'status': 'fail', 'qa': {'status': 'incomplete'}, 'checks': []}
        report, raw = core_test.bounded_report(original)
        self.assertEqual(report, original)
        self.assertEqual(json.loads(raw), original)

    def test_oversized_green_summary_becomes_explicit_failure(self):
        report, raw = core_test.bounded_report({'status': 'pass', 'big': 'x' * 5000,
            'transport_artifact': {'file': 'retained.jsonl.gz', 'sha256': 'a' * 64}}, maximum=1024)
        self.assertEqual(report['status'], 'fail')
        self.assertEqual(report['qa']['status'], 'incomplete')
        self.assertEqual(report['transport_artifact']['file'], 'retained.jsonl.gz')
        self.assertGreater(report['original_summary_bytes'], 5000)
        self.assertLessEqual(len(raw), 1024)
        self.assertEqual(len(report['original_summary_sha256']), 64)

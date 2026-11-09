"""Synthetic measurement controls. Native evidence comes only from the CLI run."""
from pathlib import Path
import sys
from threading import Event
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import code_local_canary as canary


class CodeCanaryTests(unittest.TestCase):
    def test_workload_counts_and_measures_actual_overlap(self):
        running, read_seen = Event(), Event()
        operations, reads, checks = [], [], []

        def read(kind):
            reads.append(kind)
            if running.is_set():
                read_seen.set()

        def transfer(turn, operation, started):
            operations.append((turn, operation))
            read_seen.clear()
            running.set()
            start = time.monotonic_ns()
            started.set()
            if not read_seen.wait(2):
                raise AssertionError('Transfer did not see a concurrent query')
            end = time.monotonic_ns()
            running.clear()
            return (start, end), {'outcome': 'synthetic'}

        result = canary.measure(read, transfer, lambda: checks.append(1))
        self.assertEqual(operations, [(turn, operation) for turn in range(1, 4)
                                      for operation in ('push', 'fetch', 'clone')])
        self.assertEqual(len(checks), 9)
        self.assertEqual(reads.count('work'), 36)
        self.assertEqual(reads.count('document'), 36)
        self.assertEqual(result['baseline']['work']['samples'], 18)
        self.assertEqual(result['loaded']['document']['samples'], 18)
        self.assertTrue(all(sum(item['overlapping_queries'].values()) > 0
                            for item in result['transfers']))
        self.assertTrue(all(result['overlapping_queries'].values()))

    def test_nonoverlapping_transfer_cannot_report_success(self):
        def transfer(_turn, _operation, started):
            start = time.monotonic_ns()
            end = time.monotonic_ns()
            started.set()
            return (start, end), {}

        with self.assertRaisesRegex(ValueError, 'workload-overlap'):
            canary.measure(lambda _kind: None, transfer, lambda: None)

    def test_nearest_rank_and_insufficient_samples(self):
        windows = [(0, value * 1_000_000) for value in range(1, 19)]
        self.assertEqual(canary.latency(windows), {'samples': 18, 'p50_ms': 9.0,
                                                  'p95_ms': 18.0, 'p99_ms': 18.0})
        with self.assertRaisesRegex(ValueError, 'sample-count'):
            canary.latency(windows[:-1])


if __name__ == '__main__':
    unittest.main()

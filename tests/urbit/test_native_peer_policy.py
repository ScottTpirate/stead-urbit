"""Recorded kernel-readback parser controls, not fresh native/host execution.

Fixture: actual Ubuntu nftables 1.0.9 synthetic table from GitHub run
36364129434, controller dfc05537cbda1339d893eb00007ab871f92cbb8f.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import native_peer_fence as fence


class PacketPolicyReadbackTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / 'tests/urbit/fixtures/nftables-1.0.9-stead-fakes.json').read_text())['nftables']

    def test_observed_ubuntu_declarations_and_alternate_order_preserve_input(self):
        original = copy.deepcopy(self.rows)
        fence.require_policy(self.rows)
        self.assertEqual(self.rows, original)
        # Same declarations and identical packet-rule sequence.
        alternate = [self.rows[0], self.rows[1], self.rows[3], self.rows[4], self.rows[2], *self.rows[5:]]
        fence.require_policy(alternate)

    def test_missing_duplicate_and_unexpected_declarations_fail(self):
        for rows in (self.rows[:2] + self.rows[3:], self.rows + [copy.deepcopy(self.rows[2])],
                     self.rows + [{'unexpected': {}}], self.rows[1:], self.rows + [copy.deepcopy(self.rows[0])]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                fence.require_policy(rows)

    def test_missing_extra_or_reordered_rules_fail(self):
        for rows in (self.rows[:-1], self.rows + [copy.deepcopy(self.rows[-1])],
                     [*self.rows[:5], self.rows[6], self.rows[5], *self.rows[7:]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                fence.require_policy(rows)

    def test_changed_policy_fields_fail(self):
        for index, key, field, value in ((2, 'set', 'timeout', 20), (2, 'set', 'flags', []),
                (3, 'chain', 'hook', 'output'), (3, 'chain', 'prio', 0), (1, 'table', 'family', 'ip')):
            rows = copy.deepcopy(self.rows)
            rows[index][key][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                fence.require_policy(rows)
        for replacement in ('0.0.0.0', '127.0.0.2'):
            rows = copy.deepcopy(self.rows)
            rows[5]['rule']['expr'][1]['match']['right'] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                fence.require_policy(rows)

    def test_counter_and_schema_changes_fail(self):
        for counter in ({'bytes': 0, 'packets': -1}, {'bytes': 0, 'packets': True},
                        {'bytes': 0, 'packets': 0, 'other': 1}):
            rows = copy.deepcopy(self.rows)
            rows[6]['rule']['expr'][1]['counter'] = counter
            with self.subTest(counter=counter), self.assertRaises(ValueError):
                fence.require_policy(rows)
        self.rows[0]['metainfo']['json_schema_version'] = 2
        with self.assertRaises(ValueError):
            fence.require_policy(self.rows)


if __name__ == '__main__':
    unittest.main()

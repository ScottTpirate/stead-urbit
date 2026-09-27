"""Host codec amendment regressions; no native execution or authorization claims."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('contracts_v2', ROOT / 'scripts/urbit/contracts_v2.py')
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)


class ContractAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.command = copy.deepcopy(json.loads((ROOT / 'specs/urbit/fixtures/native-cases.json').read_text())['commands']['project_create'])
        self.command['protocol'] = 'stead.command/2'

    def test_domain_separates_versions_without_changing_canonical_rules(self):
        raw = v2.canonical(self.command)
        self.assertEqual(v2.parse(raw), self.command)
        self.assertEqual(v2.digest(self.command), hashlib.sha256(b'stead.command/2\0' + raw).hexdigest())
        self.assertNotEqual(v2.digest(self.command), hashlib.sha256(b'stead.command/1\0' + raw).hexdigest())

    def test_new_submission_reference_rejects_legacy_future_and_caller_actor(self):
        for version in ('stead.command/1', 'stead.command/3'):
            command = dict(self.command, protocol=version)
            with self.assertRaises(ValueError):
                v2.canonical(command)
        with self.assertRaises(ValueError):
            v2.canonical(dict(self.command, actor='zod'))

    def test_preserves_raw_duplicate_keys_and_bounds(self):
        raw = v2.canonical(self.command)
        with self.assertRaises(ValueError):
            v2.parse(raw.replace(b'{', b'{"protocol":"stead.command/2",', 1))
        with self.assertRaises(ValueError):
            v2.parse(raw + b' ' * 65536)

    def test_both_freezes_remain_intact(self):
        v2.verify_freeze()

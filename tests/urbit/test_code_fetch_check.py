"""Host-only integrity of the fixed fetch proof inventory and synthetic oracle."""
import copy
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import code_fetch_check as fetch


class FetchProofIntegrity(unittest.TestCase):
    def test_native_inventory_and_imports_match_fixed_driver(self):
        source = (ROOT / fetch.TESTS).read_text()
        self.assertEqual(tuple(re.findall(r'^\+\+  (test-[a-z0-9-]+)$', source, re.M)), fetch.ARMS)
        self.assertEqual(len(fetch.ARMS), 43)
        self.assertEqual(source.count('++  failure-control\n'), 1)
        self.assertEqual(len(fetch.EXPECTED), len(set(fetch.EXPECTED)))
        self.assertEqual(len(fetch.EXPECTED), 59)
        for name, declaration in fetch.IMPORTS.items():
            text = (ROOT / f'native/core/desk/lib/{name}.hoon').read_text()
            self.assertEqual(re.findall(r'^/\+  .*\n', text, re.M), [declaration] if declaration else [])

    def test_independent_oracle_fixture_identity_is_fixed(self):
        objects, first, tip, tag = fetch.fixture()
        self.assertEqual(set(objects), {
            'f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f',
            '9fa83729202aaf6a5987743942e82921fd306c93',
            '7b0d20a5669435d817020be49c29f66e0411fa6e',
            'adb053935e98aa1282b44c571ea3e0bcce994c0f',
            '59e233a53674ca00efbea1103db3cbdc08c3f00e',
        })
        self.assertEqual((first, tip, tag), (
            '7b0d20a5669435d817020be49c29f66e0411fa6e',
            'adb053935e98aa1282b44c571ea3e0bcce994c0f',
            '59e233a53674ca00efbea1103db3cbdc08c3f00e',
        ))
        self.assertEqual(objects['f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f'], ('blob', b'abc'))
        self.assertEqual(objects['9fa83729202aaf6a5987743942e82921fd306c93'],
                         ('tree', b'100644 file.txt\0' + bytes.fromhex('f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f')))

    def test_report_cannot_omit_controls_or_either_stock_path(self):
        complete = {'status': 'passed', 'checks': [{'name': name, 'passed': True} for name in fetch.EXPECTED]}
        fetch.vectors.validate_report(complete, fetch.EXPECTED)
        for name in fetch.EXTRA:
            incomplete = copy.deepcopy(complete)
            incomplete['checks'] = [row for row in incomplete['checks'] if row['name'] != name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                fetch.vectors.validate_report(incomplete, fetch.EXPECTED)


if __name__ == '__main__':
    unittest.main()

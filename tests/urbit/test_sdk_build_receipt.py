"""Synthetic SDK metadata controls; no compilation, custody or native claim."""
from dataclasses import FrozenInstanceError
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import sdk_build_receipt as receipt
import sdk_artifacts


class StagedReceiptTests(unittest.TestCase):
    def setUp(self):
        self.value = {'protocol': 'stead.sdk-build-staged/1', 'status': 'export_queued',
            'builder': '~wes', 'desk': 'base', 'clay_case': '~2026.9.28..03.49.13..abcd',
            'artifacts': {name: {'bytes': str(index + 1), 'sha256': hashlib.sha256(name.encode()).hexdigest()}
                          for index, name in enumerate(sorted(sdk_artifacts.ARTIFACTS))}}

    def raw(self, value=None):
        return json.dumps(self.value if value is None else value).encode()

    def parse(self, value=None):
        return receipt.parse(self.raw(value), builder='~wes', desk='base')

    def test_staged_metadata_is_immutable_and_pin_copies_do_not_share_state(self):
        result = self.parse()
        self.assertEqual(result.response_sha256, hashlib.sha256(self.raw()).hexdigest())
        self.assertEqual(result.clay_case, self.value['clay_case'])
        self.assertEqual(sdk_artifacts.inventory(result.pins()),
            {name: (int(pin['bytes']), pin['sha256']) for name, pin in self.value['artifacts'].items()})
        with self.assertRaises(FrozenInstanceError):
            result.builder = '~zod'
        changed = result.pins()
        changed['sample.jam']['bytes'] = 999
        self.assertNotEqual(changed, result.pins())
        self.assertFalse(hasattr(result, 'accepted'))

    def test_wrong_context_status_protocol_and_extra_fields_are_rejected(self):
        for change in ({'protocol': 'stead.sdk-build-staged/2'}, {'status': 'pass'},
                       {'builder': '~zod'}, {'desk': 'other'}, {'accepted': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.parse(self.value | change)
        for builder, desk in [('~zod', 'base'), ('~wes', 'other')]:
            with self.assertRaisesRegex(ValueError, 'context'):
                receipt.parse(self.raw(), builder=builder, desk=desk)

    def test_missing_misnamed_duplicate_or_extra_mark_is_rejected(self):
        for name in sdk_artifacts.ARTIFACTS:
            value = copy.deepcopy(self.value)
            value['artifacts'].pop(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.parse(value)
        value = copy.deepcopy(self.value)
        value['artifacts']['wrong.jam'] = value['artifacts'].pop('stead-query-3.jam')
        with self.assertRaises(ValueError):
            self.parse(value)
        raw = self.raw().replace(b'"bytes": "1"', b'"bytes": "1", "bytes": "2"')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            receipt.parse(raw, builder='~wes', desk='base')

    def test_decimal_lexemes_and_file_or_total_limits_are_not_normalized(self):
        for size in (True, 1, '0', '-1', '+1', '01', '1.0', '1e2', ' 1', '\u0661', '9' * 9,
                     str(sdk_artifacts.MAX_ARTIFACT + 1)):
            value = copy.deepcopy(self.value)
            value['artifacts']['sample.jam']['bytes'] = size
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.parse(value)
        value = copy.deepcopy(self.value)
        for pin in value['artifacts'].values():
            pin['bytes'] = str(sdk_artifacts.MAX_ARTIFACT)
        with self.assertRaisesRegex(ValueError, 'total byte bound'):
            self.parse(value)

    def test_bad_digests_shapes_cases_and_unknown_file_fields_are_rejected(self):
        for item in ([], {'bytes': '1', 'sha256': 'a' * 63}, {'bytes': '1', 'sha256': 'A' * 64},
                     {'bytes': '1', 'sha256': 1}, {'bytes': '1', 'sha256': 'a' * 64, 'path': '/private'}):
            value = copy.deepcopy(self.value)
            value['artifacts']['sample.jam'] = item
            with self.subTest(shape=type(item).__name__), self.assertRaises(ValueError):
                self.parse(value)
        for case in (None, 123, '~', '~' + '1' * 128, '~2026/other', '~2026\nsecret'):
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.parse(self.value | {'clay_case': case})

    def test_empty_oversized_duplicate_invalid_utf8_nonfinite_and_truncated_input(self):
        duplicate = self.raw().replace(b'"status": "export_queued"',
                                      b'"status": "export_queued", "status": "pass"')
        for raw in (b'', b'x' * (receipt.MAX_RESPONSE + 1), self.raw().decode(), b'\xff',
                    b'[]', b'{"bytes": NaN}', duplicate, self.raw()[:-1]):
            with self.subTest(kind=type(raw).__name__), self.assertRaises((ValueError, UnicodeError)):
                receipt.parse(raw, builder='~wes', desk='base')


if __name__ == '__main__':
    unittest.main()

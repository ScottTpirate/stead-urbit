"""Host replay of one retained native diagnostic; no native execution here."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/sdk_native'), str(ROOT / 'scripts/urbit')]
SPEC = importlib.util.spec_from_file_location('sdk_consumer_import', ROOT / 'scripts/sdk_native/consumer.py')
CONSUMER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONSUMER)
OBSERVED = json.loads((ROOT / 'docs/urbit/evidence/2026-09-29/phase2-preparation/sdk-import-diagnostic.json').read_text())
RESPONSE = OBSERVED['observed']['generator_response']
TRACE = OBSERVED['observed']['missing_dependency_line'].encode() + b'\r\n'


class SDKImportTests(unittest.TestCase):
    def setUp(self):
        # Retained display spelling, independent synthetic atom. The native
        # receipt emits both representations from the same captured p.case.
        self.compiled = {'clay_case': '~2026.09.29..05.15.04..cbe0', 'clay_case_atom': '0x1234.5678'}

    def test_invocation_preserves_fyrd_sample_case_binding_mode_and_bytes(self):
        value = {'mode': 'query', 'raw': '{}', 'binding': '019939ba-4000-7000-8000-0000000000ca'}
        self.assertEqual(CONSUMER.invoke_sample(self.compiled, value),
            '[0x1234.5678 ~zod '
            '0x6163.3030.3030.3030.3030.3030.2d30.3030.382d.3030.3037.2d30.3030.342d.6162.3933.3939.3130 '
            '1 %query 0x7d7b]')

    def test_invocation_rejects_extra_fields_unknown_mode_and_oversized_carrier(self):
        value = {'mode': 'query', 'raw': '{}', 'binding': '019939ba-4000-7000-8000-0000000000ca'}
        for change in ({'mode': 'configure'}, {'extra': 'field'}, {'raw': 'x' * 65538}, {'binding': 'bad'}):
            with self.subTest(change=list(change)), self.assertRaises(ValueError):
                CONSUMER.invoke_sample(self.compiled, value | change)

    def test_captured_case_rejects_display_dates_and_noncanonical_or_unbounded_atoms(self):
        invalid = (None, True, 123, '', '0x0', '0x01', '0X1', '0xA', '0x12345',
                   '0x1.abc', '0x1.00000', '0x1.0000.0000.0000.0000.0000.0000.0000.0000',
                   ' 0x1', '0x1\n', '(add 1 1)', self.compiled['clay_case'])
        for atom in invalid:
            with self.subTest(atom=atom), self.assertRaises(ValueError):
                CONSUMER.captured_case_atom(self.compiled | {'clay_case_atom': atom})
        for compiled in ({'clay_case': self.compiled['clay_case']}, None, '0x1'):
            with self.subTest(compiled=compiled), self.assertRaises(ValueError):
                CONSUMER.captured_case_atom(compiled)

    def test_captured_case_atom_bounds(self):
        for atom in ('0x1', '0xffff.ffff.ffff.ffff.ffff.ffff.ffff.ffff'):
            with self.subTest(atom=atom):
                self.assertEqual(CONSUMER.captured_case_atom({'clay_case_atom': atom}), atom)

    def test_retained_pinned_clay_failure(self):
        CONSUMER.verify_private_import(RESPONSE, TRACE)

    def test_generic_failure_timeout_or_other_generator_cannot_pass(self):
        for response in ('%generator-build-fail\n', 'timeout', '%sdk-import-control-compiled\n',
                         RESPONSE.replace('stead-sdk-private', 'another-generator'),
                         RESPONSE + 'unexpected extra output\n'):
            with self.subTest(response=response), self.assertRaises(ValueError):
                CONSUMER.verify_private_import(response, TRACE)

    def test_absent_wrong_or_only_mentioned_dependency_cannot_pass(self):
        for trace in (b'', b'file-not-found\nstead-core\n',
                      TRACE.replace(b'stead-core', b'stead-codec'),
                      b'quoted: ' + TRACE, TRACE.replace(b'/hoon', b'/hoon-extra')):
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                CONSUMER.verify_private_import(RESPONSE, trace)

    def test_oversized_trace_cannot_pass(self):
        with self.assertRaises(ValueError):
            CONSUMER.verify_private_import(RESPONSE, TRACE + b' ' * 262144)


if __name__ == '__main__':
    unittest.main()

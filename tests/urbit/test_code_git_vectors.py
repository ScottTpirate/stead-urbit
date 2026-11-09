"""Host oracle/evidence parser checks. These do not execute or qualify Hoon."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
spec = importlib.util.spec_from_file_location('code_git_vectors', ROOT / 'scripts/urbit/code_git_vectors.py')
vectors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vectors)


class CodeGitPacketControls(unittest.TestCase):
    def test_literal_preserves_atom_value(self):
        for value in (0, 1, 0xffff, 0x10000, 0x123456789, (1 << 160) - 1):
            self.assertEqual(int(vectors.literal(value)[2:].replace('.', ''), 16), value)

    def test_decimal_uses_hoon_group_separators(self):
        self.assertEqual(vectors.decimal(2440), '2.440')
        self.assertEqual(vectors.decimal(8388608), '8.388.608')
        self.assertEqual(vectors.decimal(0), '0')

    def test_explicit_width_preserves_zero_bytes(self):
        self.assertEqual(vectors.native_bytes('0', '0x0'), b'')
        self.assertEqual(vectors.native_bytes('2', '0x0'), b'\0\0')
        self.assertEqual(vectors.native_bytes('2', '0xff'), b'\xff\0')

    def test_native_bytes_rejects_overflow_and_non_numbers(self):
        for width, value in [('0', '0x1'), ('65.521', '0x0'), ('-1', '0x0'), ('1', '0xnothex'), ('1', '1')]:
            with self.subTest(width=width, value=value), self.assertRaises(ValueError):
                vectors.native_bytes(width, value)

    def test_complete_native_rows(self):
        self.assertEqual(vectors.parse_rows('~[[~.test-one ~.0] [~.failure-control ~.1]]', 2),
                         [('test-one', '0'), ('failure-control', '1')])
        self.assertEqual(vectors.parse_rows('[[~.data ~.2 ~.0xff ~.6] ~]', 4), [('data', '2', '0xff', '6')])

    def test_native_output_cannot_hide_errors_or_missing_cases(self):
        for output in ('~', '[~.one]', '~[[~.one ~.0]] syntax error', '~[[~.one ~.0]]\x00', '[' * 10,
                       '~[[~.one ~.0]]]', '~[[~.one ~.0]] ~', '[[~.one ~.0] ~ ~]', '[~.one ~.0]'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                vectors.parse_rows(output, 2)

    def test_controls_distinct_from_empty_data(self):
        self.assertEqual(vectors.reference_packets(b'0000000100020004'),
                         [('flush', b'', 4), ('delim', b'', 8), ('response-end', b'', 12), ('data', b'', 16)])

    def test_binary_and_line_endings_unchanged(self):
        self.assertEqual(vectors.reference_packets(b'0006\xff\x000007a\r\n0005a'),
                         [('data', b'\xff\0', 6), ('data', b'a\r\n', 13), ('data', b'a', 18)])

    def test_oracle_rejects_truncated_and_reserved_packets(self):
        for raw in (b'0', b'000', b'0003', b'fff1', b'gggg', b'0007ab', b'0000x'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                vectors.reference_packets(raw)

    def test_oracle_bounds_and_uppercase(self):
        self.assertEqual(vectors.reference_packets(b'000Aabcdef'), [('data', b'abcdef', 10)])
        self.assertEqual(len(vectors.reference_packets(b'fff0' + b'\0' * 65_516)[0][1]), 65_516)
        for raw in (b'0000' * 129, b'\0' * 1_048_577):
            with self.assertRaises(ValueError):
                vectors.reference_packets(raw)

    def test_report_requires_exact_named_successes(self):
        report = {'status': 'passed', 'checks': [{'name': name, 'passed': True} for name in vectors.EXPECTED_CHECKS]}
        self.assertIs(vectors.validate_report(report), report)
        variants = [copy.deepcopy(report) for _ in range(5)]
        variants[0]['checks'].pop()
        variants[1]['checks'][0]['passed'] = False
        variants[2]['checks'][0]['name'] = variants[2]['checks'][1]['name']
        variants[3]['status'] = 'failed'
        variants[4]['checks'][0]['passed'] = 1
        for value in variants:
            with self.assertRaises(ValueError):
                vectors.validate_report(value)

    def test_focused_inflater_inventory_is_separate(self):
        report = {'status': 'passed', 'checks': [{'name': name, 'passed': True} for name in vectors.INFLATE_CHECKS]}
        self.assertIs(vectors.validate_report(report, vectors.INFLATE_CHECKS), report)
        with self.assertRaises(ValueError):
            vectors.validate_report(report)
        report['checks'].pop()
        with self.assertRaises(ValueError):
            vectors.validate_report(report, vectors.INFLATE_CHECKS)


if __name__ == '__main__':
    unittest.main()

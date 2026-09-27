"""Host-only verifier negatives using synthetic transcripts, not native tests."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('native_units_under_test', ROOT / 'scripts/urbit/native_units.py')
UNITS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UNITS)


class NativeUnitVerifierTests(unittest.TestCase):
    def setUp(self):
        self.path = '/tests/stead-session'
        self.arms = ['test-session-one', 'test-session-two']
        self.positive = ('built   /tests/stead-session/hoon\n'
                         'OK /tests/stead-session/test-session-one\n'
                         'OK /tests/stead-session/test-session-two\n[32 %avow 0 %noun 0]\n')
        self.control_path = '/controls/stead-unit-failure'
        self.control_arms = ['test-deliberate-failure']
        self.marker = 'stead-intentional-native-unit-failure'
        self.negative = ('built   /controls/stead-unit-failure/hoon\n'
                         'stead-intentional-native-unit-failure\n'
                         'FAILED /controls/stead-unit-failure/test-deliberate-failure\n[32 %avow 0 %noun 1]\n')
        self.inventory = json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_text())

    def positive_check(self, raw):
        return UNITS.verify_output(raw, path=self.path, expected=self.arms, succeeds=True)

    def negative_check(self, raw):
        return UNITS.verify_output(raw, path=self.control_path, expected=self.control_arms,
                                   succeeds=False, failure_marker=self.marker)

    def test_complete_synthetic_transcripts(self):
        self.assertEqual(self.positive_check(self.positive)['observed'], self.arms)
        self.assertEqual(self.negative_check(self.negative)['outcome'], 'expected-failure')

    def test_empty_nominal_success_rejected(self):
        with self.assertRaises(ValueError):
            self.positive_check('[32 %avow 0 %noun 0]\n')

    def test_missing_duplicate_or_extra_arm_rejected(self):
        variants = [self.positive.replace('OK /tests/stead-session/test-session-two\n', ''),
                    self.positive + 'OK /tests/stead-session/test-session-one\n',
                    self.positive + 'OK /tests/stead-session/test-session-hidden\n']
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.positive_check(raw)

    def test_malformed_outcome_verdict_and_build_rejected(self):
        for line in ['OK /tests/stead-session/test-hidden trailing', '[32 %avow 0 %noun 0] trailing',
                     'built   /tests/unexpected/hoon', 'UNKNOWN RECORD',
                     '> test-unexpected: took ms/1.2']:
            with self.subTest(line=line), self.assertRaises(ValueError):
                self.positive_check(self.positive + line + '\n')

    def test_diagnostic_rejected_in_both_lanes(self):
        for diagnostic in ['nest-fail', 'syntax error at [1 1]', 'mint-vain',
                           'CRASHED /controls/stead-unit-failure/test-deliberate-failure',
                           '[%dojo-lame %kick]']:
            for raw, verify in [(self.positive, self.positive_check), (self.negative, self.negative_check)]:
                with self.subTest(diagnostic=diagnostic), self.assertRaises(ValueError):
                    verify(raw + diagnostic + '\n')

    def test_deliberate_failure_message_required_once(self):
        for raw in [self.negative.replace(self.marker + '\n', ''), self.negative + self.marker + '\n']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.negative_check(raw)

    def test_wrong_outcome_cannot_be_relabelled(self):
        with self.assertRaises(ValueError):
            self.positive_check(self.positive.replace('OK ', 'FAILED '))
        with self.assertRaises(ValueError):
            self.negative_check(self.negative.replace('FAILED ', 'OK '))

    def test_oversized_output_rejected(self):
        with self.assertRaises(ValueError):
            self.positive_check(self.positive + 'x' * 262144)

    def test_valid_inventory(self):
        self.assertEqual(UNITS.validate_inventory(self.inventory)['expected_arm_count'], 31)

    def test_inventory_empty_or_missing_suite(self):
        for suites in [[], self.inventory['suites'][:1]]:
            value = copy.deepcopy(self.inventory)
            value['suites'] = suites
            with self.assertRaises(ValueError):
                UNITS.validate_inventory(value)

    def test_inventory_duplicate_suite(self):
        value = copy.deepcopy(self.inventory)
        value['suites'][1] = value['suites'][0]
        with self.assertRaises(ValueError):
            UNITS.validate_inventory(value)

    def test_inventory_duplicate_or_cross_suite_arm(self):
        for cross in [False, True]:
            value = copy.deepcopy(self.inventory)
            value['suites'][0]['arms'][0] = value['suites'][int(cross)]['arms'][1]
            with self.assertRaises(ValueError):
                UNITS.validate_inventory(value)

    def test_inventory_count_mismatch(self):
        value = copy.deepcopy(self.inventory)
        value['expected_arm_count'] = 27
        with self.assertRaises(ValueError):
            UNITS.validate_inventory(value)

    def test_inventory_negative_control_marker_required(self):
        value = copy.deepcopy(self.inventory)
        del value['negative_control']['marker']
        with self.assertRaises(ValueError):
            UNITS.validate_inventory(value)


if __name__ == '__main__':
    unittest.main()

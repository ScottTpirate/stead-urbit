"""Host-only failure-path checks; no native process or native proof is created."""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import gall_schedule as G


class GallScheduleRunnerHostTests(unittest.TestCase):
    def test_actual_native_dojo_tang_is_the_specific_runtime_control(self):
        captured = json.loads((Path(__file__).parent / 'fixtures/gall-negative-dojo-tang.json').read_text())
        self.assertTrue(G.intended_negative(captured['result'], captured['diagnostic']))
        # An actual runtime error is required, not the hint string in arbitrary
        # output, compiler source context, a success result, or a different count.
        result = captured['result']
        for altered in (
            result.replace("2 '1'", "2 '10'"),
            result.replace('pending-control', 'another-control'),
            result.replace('dojo: generator failure', '%.y'),
            result.replace('dojo: generator failure', 'nest-fail'),
            result + "[%stead-core-result '7b7d']\n",
            result.replace("[%stead-scheduled-gall-pending-control 2 '1']", ''),
            'syntax error\n' + result,
            result + 'x' * 65536,
        ):
            with self.subTest(output=altered[-120:]):
                self.assertFalse(G.intended_negative(altered, captured['diagnostic']))
        self.assertFalse(G.intended_negative(result, 'x' * 65537))

    def test_negative_control_requires_exact_expected_and_actual_counts(self):
        for text in ("[stead-scheduled-gall-pending-control 2 '1']",
                     '[%stead-scheduled-gall-pending-control 2 1]'):
            self.assertTrue(G.intended_negative('~\n', text))
            self.assertFalse(G.intended_negative('unexpected success', text))
        for text in ("[stead-scheduled-gall-pending-control 2 '10']",
                     '[stead-scheduled-gall-pending-control 2 11]',
                     '[stead-scheduled-gall-pending-control 20 1]',
                     '[stead-scheduled-gall-pending-control 2 1x]',
                     '[other-stead-scheduled-gall-pending-control 2 1]',
                     'syntax error before intended runtime assertion'):
            with self.subTest(text=text):
                self.assertFalse(G.intended_negative('~', text))

    def test_missing_input_and_final_binding_failures_are_retained_uniquely(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'logs').mkdir()
            host = {'STATE': root}
            with patch.object(G, 'inputs', side_effect=FileNotFoundError('synthetic missing input')), \
                    patch.object(G.time, 'strftime', return_value='fixed-time'), redirect_stderr(io.StringIO()):
                results = [G.run(host), G.run(host)]
            self.assertEqual(len(list((root / 'logs').glob('*.json'))), 2)
            self.assertNotEqual(results[0]['evidence_file'], results[1]['evidence_file'])
            for result in results:
                self.assertEqual(result['status'], 'fail')
                report = json.loads((root / 'logs' / Path(result['evidence_file']).name).read_text())
                self.assertEqual(report['stage'], 'failed')
                self.assertIn('synthetic missing input', report['error'])
                self.assertIn('synthetic missing input', report['final_binding_error'])


if __name__ == '__main__':
    unittest.main()

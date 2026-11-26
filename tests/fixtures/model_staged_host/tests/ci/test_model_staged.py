"""Six inert byte/data cases; no Hoon evaluator, children or model calls."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/ci/pure_eval'))
import codec
import stage_codec as S

FIXTURES = ROOT / 'tests/fixtures/model-staged'


class ModelStagedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.composition = (FIXTURES / 'composition.json').read_bytes()
        cls.base = (FIXTURES / 'original-composition.json').read_bytes()
        cls.document = json.loads(cls.base)
        cls.files = {path: (FIXTURES / path).read_bytes() for path in cls.document['sources']}
        cls.files[codec.HELPER_PATH] = (FIXTURES / codec.HELPER_PATH).read_bytes()
        cls.jobs = codec.jobs(cls.files, cls.composition)

    def output(self, index, core=123, formula=456, tang=0):
        rows = [('stage-core', core)]
        if index:
            rows.append(('stage-mint', formula))
        if index == 2:
            rows.append((S.ARM, tang))
        return ('~[' + '\n'.join('[~.' + name + ' ~.' + format(value, ',').replace(',', '.') + ']'
                                for name, value in rows) + ']').encode()

    def record(self, index, *, core=123, formula=456, tang=0):
        job = self.jobs[index]
        out = self.output(index - 2, core, formula, tang)
        return {'label': job['label'], 'observation': codec.observe(job, 0, out, codec.BOOT.encode())}

    def test_fixed_five_jobs_preserve_original_core_controls_and_one_arm(self):
        old = codec.jobs(self.files, self.base)
        self.assertEqual(self.jobs[:2], old[:2])
        self.assertEqual(tuple(job['label'] for job in self.jobs),
                         ('compiler-control', 'failing-tang-control') + S.LABELS)
        self.assertEqual(tuple(job['timeout_seconds'] for job in self.jobs), (15, 15, 85, 85, 85))
        self.assertEqual(sum(len(job['arms']) for job in self.jobs), 1)
        self.assertEqual(codec.job_profile(self.jobs)['positive_arms'], 1)
        self.assertEqual(codec.job_profile(old)['positive_arms'], 18)
        suite = self.document['composition']['suites'][0]
        original_body = self.files[S.SUITE_PATH].replace(suite['import_header'].encode(), b'', 1)
        cores = []
        for job in self.jobs[2:]:
            atom = re.search(rb'  0x([0-9a-f]{1,4}(?:\.[0-9a-f]{4})*)\n', job['source']).group(1)
            self.assertIn(b'=/  source=@t\n  ^-  @\n  0x' + atom + b'\n', job['source'])
            value = int(atom.replace(b'.', b''), 16)
            core = value.to_bytes((value.bit_length() + 7) // 8, 'little')
            cores.append(core)
            self.assertIn(original_body, core)
            self.assertEqual(tuple(name.decode() for name in re.findall(rb'^\+\+  (test-[a-z0-9-]+)$', core, re.M)),
                             tuple(suite['arms']))
            self.assertTrue(job['source'].startswith(b'=/  original-vase=vase  !>(.)\n'))
            self.assertIn(b'(slap original-vase (rain /eval source))', job['source'])
            self.assertNotIn(b'%slog', job['source'])
            self.assertLessEqual(len(job['source']), 1048576)
            self.assertEqual(hashlib.sha256(job['source']).hexdigest(), job['source_sha256'])
        self.assertEqual(cores, [cores[0]] * 3)
        # Canonical qex/qix groups preserve exact little-endian source bytes.
        for raw, expected in ((b'\x00\x01', b'0x100'), (b'\x00\x00\x01', b'0x1.0000'),
                              (b'hello', b'0x6f.6c6c.6568')):
            with self.subTest(literal=expected):
                self.assertIn(b'=/  source=@t\n  ^-  @\n  ' + expected + b'\n', S.source(raw, 0))
        self.assertNotIn(b'formula=nock', self.jobs[2]['source'])
        self.assertIn(b'q:(~(mint ut p.core) p:!>(*tang) [%limb %' + S.ARM.encode(), self.jobs[3]['source'])
        self.assertNotIn(b'result=tang', self.jobs[3]['source'])
        self.assertIn(b';;(tang .*(q.core formula))', self.jobs[4]['source'])

    def test_exact_source_and_composition_pins_refuse_crossed_profiles(self):
        for path in self.files:
            with self.subTest(path=path):
                altered = dict(self.files)
                altered[path] += b'\n'
                with self.assertRaises(ValueError):
                    codec.jobs(altered, self.composition)
        for raw in (self.composition + b'\n', self.composition.replace(b'core-ready', b'core-ready-x', 1)):
            with self.assertRaises(ValueError):
                codec.jobs(self.files, raw)
        for jobs in (self.jobs[:-1], self.jobs[:2] + codec.jobs(self.files, self.base)[2:],
                     self.jobs[:2] + (self.jobs[3], self.jobs[2], self.jobs[4])):
            # The complete original model profile remains valid; only its crossed
            # combination with staged identity must be refused.
            if jobs == codec.jobs(self.files, self.base):
                self.assertNotEqual(codec.job_profile(jobs)['name'], S.PROFILE_NAME)
            else:
                with self.assertRaises(ValueError):
                    codec.job_profile(jobs)
        bad = dict(self.jobs[2], arms=(S.ARM,))
        with self.assertRaises(ValueError):
            codec.observe(bad, 0, self.output(0), codec.BOOT.encode())

    def test_complete_boundaries_and_actual_arm_result_are_distinct(self):
        for index, job in enumerate(self.jobs[2:]):
            out = self.output(index, S.MAX_MUG, 0)
            observed = codec.observe(job, 0, b'\x1b[38;5;244m' + out.replace(b'\n', b'\r\n') + b'\x1b[0m\r\n',
                                     (codec.CORE_LIMIT_WARNING + codec.BOOT).encode())
            self.assertEqual(observed['stage'], {'boundary': S.BOUNDARIES[index], 'core_mug': S.MAX_MUG,
                                                'formula_mug': 0 if index else None})
            self.assertEqual(len(observed['arms']), int(index == 2))
            self.assertEqual(observed['status'], 'pass')
        failed = codec.observe(self.jobs[4], 0, self.output(2, tang=1000), codec.BOOT.encode())
        self.assertEqual(failed['arms'], ({'name': S.ARM, 'tang_length': 1000, 'passed': False},))
        self.assertEqual((failed['status'], failed['compiler_failure']), ('fail', False))

    def test_partial_malformed_unknown_and_numeric_aliases_never_complete(self):
        good = self.output(2)
        malformed = [good[:-1], good + good, good.replace(b'stage-core', b'unknown'),
                     good.replace(b'~.123', b'~.0123'), good.replace(b'~.123', b'~.1000'),
                     good.replace(b'~.123', b'~.1.00'), good.replace(b'~.123', b'~.2.147.483.648'),
                     good.replace(b'~.0]', b'~.1.000.001]'), b'\xc2\x9b' + good,
                     good.replace(b'\n', b'\n[~.stage-core ~.123]\n', 1), self.output(1)]
        for raw in malformed:
            with self.subTest(raw=raw[:60]):
                with self.assertRaises(ValueError):
                    codec.observe(self.jobs[4], 0, raw, codec.BOOT.encode())
        for exit_code in (True, False, 0.0, 1, -9):
            with self.assertRaises(ValueError):
                codec.observe(self.jobs[4], exit_code, good, codec.BOOT.encode())

    def test_completed_refusal_preserves_original_bytes_without_phase_or_arm(self):
        raw = b'\x1b[31mmint-vain\x1b[0m\n'
        for job in self.jobs[2:]:
            observed = codec.observe(job, 0, raw, codec.EXIT_STDERR.encode())
            self.assertEqual((observed['status'], observed['arms'], observed['stage'], observed['compiler_failure']),
                             ('fail', (), None, True))
            self.assertEqual(observed['stdout_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(observed['stdout_bytes'], len(raw))
        for out, err in [(b'', codec.EXIT_STDERR.encode()), (raw, b'eval: bail: %exit'),
                         (raw, codec.EXIT_STDERR.encode() + b' extra')]:
            with self.assertRaises(ValueError):
                codec.observe(self.jobs[2], 0, out, err)

    def test_completed_prefix_cross_phase_consistency_and_refusal_boundaries(self):
        records = [{'label': job['label'], 'observation': None} for job in self.jobs[:2]]
        records += [self.record(index) for index in range(2, 5)]
        for length in range(6):
            S.validate_records(records[:length])
        S.validate_records(json.loads(json.dumps(records)))
        for index, key, value in [(3, 'core_mug', 124), (4, 'formula_mug', 457),
                                  (2, 'core_mug', True), (3, 'formula_mug', 456.0),
                                  (2, 'formula_mug', 0), (3, 'boundary', 'first-arm-ran')]:
            altered = copy.deepcopy(records)
            altered[index]['observation']['stage'][key] = value
            with self.assertRaises(ValueError):
                S.validate_records(altered)
        altered = copy.deepcopy(records)
        altered[2]['observation'] = None
        with self.assertRaises(ValueError):
            S.validate_records(altered)
        altered = copy.deepcopy(records)
        altered[3]['label'] = S.LABELS[2]
        with self.assertRaises(ValueError):
            S.validate_records(altered)


if __name__ == '__main__':
    unittest.main()

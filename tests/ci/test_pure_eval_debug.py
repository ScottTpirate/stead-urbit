"""Six inert catalog diagnostic boundaries; synthetic traces are not Hoon results."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'scripts/ci/pure_eval'


def load(name):
    spec = importlib.util.spec_from_file_location('catalog_debug_' + name, DIRECTORY / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CODEC = load('codec')
ADAPTER = load('service_adapter')
WORKER = load('worker')
DEBUG = '81085d13ec4a79a5b75f7e2bcaa4226eb48dd630e9d23e84af4068a3164b44c3'
REPO = '29f23ddb8849c5b182fca693a993a0634463e12104b47433ba3525adf93dfe31'
MODEL = 'c23002a6a5d1423167a0ef2caa9c35bc86b5ccc64ba3fff640dc73edfd9dfaa6'


class CatalogDebugTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = set()
        for digest in (REPO, MODEL, DEBUG):
            code, sources, _ = ADAPTER.selected_paths(digest)
            paths.update(code.values())
            paths.update(sources.values())
        cls.captured = {name: (ROOT / name).read_bytes() for name in paths}
        cls.hosted = types.SimpleNamespace(CONTROLLER_FILES=cls.captured)
        cls.selected = {digest: ADAPTER.fixed_data(cls.hosted, CODEC, digest)
                        for digest in (REPO, MODEL, DEBUG)}

    def composition(self, digest):
        paths, _, _ = ADAPTER.selected_paths(digest)
        return self.captured[paths['composition.json']]

    def test_exact_three_byte_prefix_preserves_original_bytes_and_offset_mapping(self):
        original = self.selected[REPO][1][2]
        diagnostic = self.selected[DEBUG][1][2]
        self.assertEqual(diagnostic['source'], b'!:\n' + original['source'])
        self.assertEqual((len(diagnostic['source']), diagnostic['source_sha256']),
                         (131344, '22d1fbebf744e9a035bb5cc4322f77db3e3306e8c378dbf9b702a6efba99299b'))
        old = json.loads(self.composition(REPO))['composition']['suites'][0]
        new = json.loads(self.composition(DEBUG))['composition']['suites'][0]
        self.assertEqual(new['source_offsets'][0], {'kind': 'fixed-debug-prefix',
            'generated_start_byte': 0, 'generated_end_byte': 3,
            'generated_start_line': 1, 'generated_newlines': 1})
        shifted = copy.deepcopy(old['source_offsets'])
        for row in shifted:
            row['generated_start_byte'] += 3
            row['generated_end_byte'] += 3
            row['generated_start_line'] += 1
        self.assertEqual(new['source_offsets'][1:], shifted)
        self.assertEqual(self.selected[REPO][0], self.selected[DEBUG][0])

    def test_fixed_three_jobs_six_arms_and_controls_do_not_expand_original_profiles(self):
        files, jobs, hashes = self.selected[DEBUG]
        self.assertEqual(tuple(job['label'] for job in jobs),
                         ('compiler-control', 'failing-tang-control', 'catalog-debug'))
        self.assertEqual((len(files), len(hashes), tuple(len(j['arms']) for j in jobs)), (55, 55, (0, 0, 6)))
        self.assertEqual(tuple(j['timeout_seconds'] for j in jobs), (15, 15, 85))
        self.assertEqual(jobs[:2], self.selected[REPO][1][:2])
        self.assertEqual(jobs[:2], self.selected[MODEL][1][:2])
        self.assertEqual(CODEC.job_profile(jobs)['name'], 'repository-catalog-debug/1')
        self.assertEqual((len(self.selected[REPO][1]), len(self.selected[MODEL][1])), (6, 5))
        for wrong in (jobs[:-1], jobs[::-1], jobs[:2] + self.selected[REPO][1][2:3],
                      jobs + jobs[2:]):
            with self.assertRaises(ValueError): CODEC.job_profile(wrong)

    def test_source_and_composition_changes_or_additional_debug_data_refuse(self):
        files = self.selected[DEBUG][0]
        raw = self.composition(DEBUG)
        changed = dict(files)
        changed['native/core/desk/tests/stead-repository-catalog.hoon'] += b'\n'
        for sources, composition in ((changed, raw), ({**files, 'extra.hoon': b'0'}, raw),
                                     (files, raw + b'\n'), (self.selected[MODEL][0], raw)):
            with self.assertRaises(ValueError): CODEC.jobs(sources, composition)
        extra = types.SimpleNamespace(CONTROLLER_FILES={**self.captured,
            'scripts/ci/pure_eval/debug_data/unreviewed.hoon': b'0'})
        with self.assertRaises(ValueError): ADAPTER.fixed_data(extra, CODEC, DEBUG)
        for digest in ('0' * 64, DEBUG.upper(), False, {'sha256': DEBUG}):
            with self.assertRaises(ValueError): ADAPTER.selected_paths(digest)

    def test_worker_checks_third_interface_codec_pin_and_crossed_pairing(self):
        for digest in (REPO, MODEL, DEBUG):
            paths, _, _ = ADAPTER.selected_paths(digest)
            code = {name: self.captured[path] for name, path in paths.items()}
            self.assertEqual(WORKER.input_profile(code), digest)
            interface = json.loads(code['interface.json'])
            self.assertEqual(interface['codec'], {'bytes': len(code['codec.py']),
                'sha256': hashlib.sha256(code['codec.py']).hexdigest()})
            for field in ('codec.py', 'interface.json', 'composition.json'):
                changed = dict(code); changed[field] += b'\n'
                with self.assertRaises(ValueError): WORKER.input_profile(changed)
            for other in (REPO, MODEL, DEBUG):
                if other != digest:
                    crossed = dict(code)
                    selected, _, _ = ADAPTER.selected_paths(other)
                    crossed['interface.json'] = self.captured[selected['interface.json']]
                    with self.assertRaises(ValueError): WORKER.input_profile(crossed)
        self.assertEqual(json.loads(self.captured['scripts/ci/pure_eval/debug-interface.json'])['resources'],
                         json.loads(self.captured['scripts/ci/pure_eval/interface.json'])['resources'])

    def test_literal_outer_entry_and_identity_mismatch_stop_before_data_or_process(self):
        args = types.SimpleNamespace(mode='pure-repository-debug', control=None,
                                     candidate='c' * 40, controller='c' * 40, workflow='a' * 40)
        identity = {'workflow_sha': 'a' * 40}
        binding = {'controller_commit': 'c' * 40}
        with patch.object(ADAPTER, '_outer', return_value='inert') as outer:
            self.assertEqual(ADAPTER.outer_repository_debug(self.hosted, args, identity, binding), 'inert')
            outer.assert_called_once_with(self.hosted, args, identity, binding, DEBUG)
        modules = {'owner_boundary': object(), 'owner_collection': object(),
                   'pure_intake': object(), 'codec': CODEC}
        for field, value in (('mode', 'pure'), ('mode', 'pure-model-simple'),
                             ('control', 'compiler'), ('candidate', 'd' * 40), ('workflow', 'b' * 40)):
            bad = copy.copy(args); setattr(bad, field, value)
            with patch.object(ADAPTER, 'load', return_value=modules), \
                    patch.object(ADAPTER, 'fixed_data') as data, self.assertRaises(ValueError):
                ADAPTER.outer_repository_debug(self.hosted, bad, identity, binding)
            data.assert_not_called()

    def test_completed_failure_trace_retains_exact_hashes_without_arm_success(self):
        job = self.selected[DEBUG][1][2]
        stdout = b'\x1b[31m/eval\r\n{4 2}\r\nmint-vain\x1b[0m\r\n'
        stderr = (CODEC.CORE_LIMIT_WARNING + CODEC.EXIT_STDERR).encode()
        observed = CODEC.observe(job, 0, stdout, stderr)
        self.assertEqual((observed['status'], observed['arms'], observed['compiler_failure']), ('fail', (), True))
        self.assertEqual((observed['stdout_sha256'], observed['stdout_bytes']),
                         (hashlib.sha256(stdout).hexdigest(), len(stdout)))
        for code, out, err in ((1, stdout, stderr), (0, stdout, stderr + b'unknown'),
                               (0, b'', stderr), (0, b'~[[~.unregistered ~.0]]', CODEC.BOOT.encode())):
            with self.assertRaises(ValueError): CODEC.observe(job, code, out, err)


if __name__ == '__main__':
    unittest.main()

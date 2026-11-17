"""Eight authored source/byte boundaries; no evaluator, model, process or namespace runs.

Rendered evaluator output below is synthetic grammar input, never an observation
of these native arms. Root/service custody and actual repository26 qualification
remain separate prerequisites for the prospective model18 profile.
"""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'scripts/ci/pure_eval'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CODEC = load('profile_codec', DIRECTORY / 'codec.py')
BOUNDARY = load('profile_boundary', DIRECTORY / 'owner_boundary.py')
with patch.dict(sys.modules, {'owner_boundary': BOUNDARY}):
    COLLECTION = load('profile_collection', DIRECTORY / 'owner_collection.py')
ADAPTER = load('profile_adapter', DIRECTORY / 'service_adapter.py')
WORKER = load('profile_worker', DIRECTORY / 'worker.py')
REPOSITORY = '1c1f04d82fcfc4eac6f5edf5d00b39f29bbbeb541687fb5df5a431726810a280'
MODEL = 'c23002a6a5d1423167a0ef2caa9c35bc86b5ccc64ba3fff640dc73edfd9dfaa6'


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def rows(job):
    names = job['arms'] or ('failure-control',)
    count = 0 if job['arms'] else 1
    return ('~[' + '\n'.join(f'[~.{name} ~.{count}]' for name in names) + ']').encode()


def stream(raw):
    return {'present': True, **pin(raw), 'base64': base64.b64encode(raw).decode()}


class FixedProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        captured = set()
        for digest in (REPOSITORY, MODEL):
            source_paths, data_paths, _ = ADAPTER.selected_paths(digest)
            captured.update(source_paths.values())
            captured.update(data_paths.values())
        cls.captured = {name: (ROOT / name).read_bytes() for name in captured}
        cls.hosted = types.SimpleNamespace(CONTROLLER_FILES=cls.captured)
        cls.selected = {digest: ADAPTER.fixed_data(cls.hosted, CODEC, digest)
                        for digest in (REPOSITORY, MODEL)}

    def report(self, digest):
        _, jobs, hashes = self.selected[digest]
        records = []
        for job in jobs:
            stdout = CODEC.COMPILER_STDOUT.encode() if job['kind'] == 'compiler-control' else rows(job)
            stderr = CODEC.EXIT_STDERR.encode() if job['kind'] == 'compiler-control' else CODEC.BOOT.encode()
            observation = CODEC.observe(job, 0, stdout, stderr)
            records.append({'label': job['label'], 'source_sha256': job['source_sha256'],
                            'source_bytes': len(job['source']), 'exit_code': 0,
                            'stdout': stream(stdout), 'stderr': stream(stderr),
                            'observation': json.loads(COLLECTION.canonical(observation))})
        return {'protocol': 'stead.fixed-pure-eval-report/1', 'status': 'pass',
                'qualifies_phase': False, 'composition_sha256': digest,
                'runtime_sha256': WORKER.RUNTIME_SHA, 'records': records,
                'source_hashes_before': hashes, 'source_hashes_after': hashes,
                'budget_stop': None, 'error_class': 'none', 'children_reaped': True,
                'namespace_baseline_restored': True,
                'expected_positive_arms': 26 if digest == REPOSITORY else 18,
                'expected_controls': 2, 'native_application_executed': False}

    def envelope(self, digest):
        paths, _, _ = ADAPTER.selected_paths(digest)
        owner = {'host_uid': 1001, 'host_gid': 1002,
                 'sources': {name: pin(self.captured[path]) for name, path in paths.items()},
                 'runtime': {'sha256': WORKER.RUNTIME_SHA}}
        namespaces = {name: name + ':[2]' for name in ('user', 'mnt', 'pid', 'net')}
        owner_sha = hashlib.sha256(COLLECTION.canonical(owner)).hexdigest()
        ready = {'namespaces': namespaces, 'owner_sha256': owner_sha}
        proof = {'uid': 1000, 'gid': 1000, 'host_uid': 1001, 'host_gid': 1002,
                 'namespace_maps': {'uid': [1000, 0, 1], 'gid': [1000, 0, 1]},
                 'namespaces': namespaces, 'source_uid': 65534, 'capabilities_empty': True,
                 'no_new_privileges': True, 'private_loopback_only': True,
                 'owner_sha256': owner_sha, 'sources': owner['sources'],
                 'runtime_sha256': WORKER.RUNTIME_SHA, 'guardian_lease_required': True}
        raw = COLLECTION.canonical(self.report(digest))
        final = {'protocol': 'stead.fixed-pure-eval-worker-result/1', 'status': 'pass',
                 'phase': 'complete', 'error_class': 'none', 'cleanup_error_class': 'none',
                 'report': pin(raw), 'admission': proof, 'outer_cleanup_required': True,
                 'children_reaped': True, 'namespace_baseline_restored': True,
                 'jobs_retained': 6 if digest == REPOSITORY else 5, 'elapsed_ms': 10,
                 'qualifies_phase': False, 'native_application_executed': False}
        return owner, ready, final

    def test_original_default_keeps_six_jobs_twenty_six_arms_and_control_bytes(self):
        files, jobs, hashes = ADAPTER.fixed_data(self.hosted, CODEC)
        self.assertEqual((files, jobs, hashes), self.selected[REPOSITORY])
        self.assertEqual(tuple(j['label'] for j in jobs),
                         ('compiler-control', 'failing-tang-control', 'catalog', 'import', 'authority', 'store'))
        self.assertEqual((len(files), sum(len(j['arms']) for j in jobs)), (55, 26))
        self.assertEqual(tuple(j['timeout_seconds'] for j in jobs), (15, 15, 85, 85, 85, 85))
        self.assertEqual(jobs[0]['source'], b'(invalid-unterminated\n')
        self.assertEqual(jobs[1]['source_sha256'],
                         '6ccdf445296a66cac869b95ff3a7d068421309cf7b541e2cf5adbc79589e0639')
        self.assertEqual(tuple(j['source_sha256'] for j in jobs[2:]), (
            '8c377fa822ef4d1808e203ff8ae578f309f1ce6157b7d1adba37bb7224283cdb',
            '83becaaa829e8d77f19e2e3d70f26d51023b9ecd3e820c420625efd84371fb1b',
            '28efeacc16ca0e1cee091726c95817b1b7972fecba97a0a5c1fc5542cafcdb7a',
            '61c1d4c5bb5d3217735f9a808d7cf170cdb38ae209fa8e56333780ced212ccd4'))

    def test_model_five_jobs_eighteen_arms_exact_sources_and_same_controls(self):
        files, jobs, _ = self.selected[MODEL]
        self.assertEqual(tuple(j['label'] for j in jobs),
                         ('compiler-control', 'failing-tang-control', 'model-codec', 'model-reply', 'model-turn-codec'))
        self.assertEqual((len(files), tuple(len(j['arms']) for j in jobs)), (21, (0, 0, 6, 6, 6)))
        self.assertEqual(jobs[:2], self.selected[REPOSITORY][1][:2])
        self.assertEqual(tuple(j['timeout_seconds'] for j in jobs), (15, 15, 85, 85, 85))
        self.assertEqual(tuple((len(j['source']), j['source_sha256']) for j in jobs[2:]), (
            (232002, '234f119ef4636c2cc4e9fcc3a1f9ba1d3f556c13b2d1d5cffa951f0492ffae03'),
            (219399, 'd9d3fdd036fcc869159a686bd96a35da6aa07c1c1bbf38b4481ed68b8920d8ed'),
            (192770, '17bfc6d95c6fa975487ba893b8a873f08ece870c200c75b8249a3426699e6ed2')))
        self.assertEqual(CODEC.job_profile(jobs)['name'], 'native-model-simple/1')

    def test_unknown_and_cross_profile_compositions_or_source_sets_refuse(self):
        for digest in ('0' * 64, MODEL.upper(), False, 18, {'sha256': MODEL}):
            with self.subTest(digest=digest), self.assertRaises(ValueError): CODEC.profile(digest)
        repo_files = self.selected[REPOSITORY][0]
        model_files = self.selected[MODEL][0]
        for digest, files in ((MODEL, repo_files), (REPOSITORY, model_files)):
            paths, _, _ = ADAPTER.selected_paths(digest)
            with self.assertRaises(ValueError): CODEC.jobs(files, self.captured[paths['composition.json']])
        paths, _, _ = ADAPTER.selected_paths(MODEL)
        raw = self.captured[paths['composition.json']]
        for files, changed in ((model_files, raw + b'\n'),
                               ({**model_files, 'extra.hoon': b'0'}, raw),
                               ({name: value for name, value in model_files.items() if name != CODEC.HELPER_PATH}, raw)):
            with self.assertRaises(ValueError): CODEC.jobs(files, changed)

    def test_mixed_reordered_partial_and_forged_job_sequences_refuse(self):
        repo, model = self.selected[REPOSITORY][1], self.selected[MODEL][1]
        for jobs in (model[:-1], model + (repo[2],), repo[:2] + model[2:],
                     model[:2] + tuple(reversed(model[2:])), list(model),
                     model[:2] + ({**model[2], 'source': repo[2]['source']},) + model[3:]):
            # The shared controls plus exact three model jobs are the valid model
            # sequence; selecting controls from the other profile is harmless.
            if jobs == model: continue
            with self.assertRaises(ValueError): CODEC.job_profile(jobs)
        self.assertEqual(CODEC.job_profile(repo[:2] + model[2:])['composition_sha256'], MODEL)

    def test_report_identity_counts_and_complete_jobs_are_not_child_selected(self):
        for digest in (REPOSITORY, MODEL):
            _, jobs, hashes = self.selected[digest]
            report = self.report(digest)
            self.assertEqual(COLLECTION.validate_report(COLLECTION.canonical(report), CODEC, jobs, hashes), report)
            edits = [('composition_sha256', MODEL if digest == REPOSITORY else REPOSITORY),
                     ('expected_positive_arms', 18 if digest == REPOSITORY else 26),
                     ('expected_positive_arms', float(report['expected_positive_arms'])),
                     ('expected_controls', True), ('records', report['records'][:-1])]
            for key, value in edits:
                changed = copy.deepcopy(report); changed[key] = value
                with self.subTest(digest=digest, field=key), self.assertRaises(ValueError):
                    COLLECTION.validate_report(COLLECTION.canonical(changed), CODEC, jobs, hashes)
            other = self.selected[MODEL if digest == REPOSITORY else REPOSITORY][1]
            with self.assertRaises(ValueError):
                COLLECTION.validate_report(COLLECTION.canonical(report), CODEC, other, hashes)

    def test_final_count_is_bound_to_original_owner_composition_not_claimed_proof(self):
        for digest in (REPOSITORY, MODEL):
            owner, ready, final = self.envelope(digest)
            self.assertEqual(COLLECTION.worker_result(final, owner, ready, CODEC), final)
            for count in (5 if digest == REPOSITORY else 6, True, float(final['jobs_retained'])):
                changed = copy.deepcopy(final); changed['jobs_retained'] = count
                with self.assertRaises(ValueError): COLLECTION.worker_result(changed, owner, ready, CODEC)
            changed = copy.deepcopy(final)
            changed['admission']['sources']['composition.json']['sha256'] = MODEL if digest == REPOSITORY else REPOSITORY
            with self.assertRaises(ValueError): COLLECTION.worker_result(changed, owner, ready, CODEC)

    def test_exact_model_map_has_no_ambient_fallback_or_extra_namespace_file(self):
        paths, mapping, prefix = ADAPTER.selected_paths(MODEL)
        self.assertEqual(prefix, 'scripts/ci/pure_eval/model_data/')
        self.assertEqual((len(mapping), sum(path.startswith(prefix) for path in mapping.values())), (21, 7))
        target = 'native/core/desk/lib/stead-model-codec.hoon'
        for mutate in ('wrong', 'fallback', 'extra'):
            changed = dict(self.captured)
            if mutate == 'wrong': changed[mapping[target]] += b'\n'
            elif mutate == 'fallback': changed[target] = changed.pop(mapping[target])
            else: changed[prefix + 'unexpected.hoon'] = b'0'
            with self.assertRaises((ValueError, KeyError)):
                ADAPTER.fixed_data(types.SimpleNamespace(CONTROLLER_FILES=changed), CODEC, MODEL)
        self.assertEqual(ADAPTER.selected_paths()[0], ADAPTER.SOURCE_PATHS)
        self.assertEqual(paths['interface.json'], 'scripts/ci/pure_eval/model-interface.json')

    def test_worker_refuses_crossed_interface_composition_and_tampered_code_pins(self):
        bundles = {}
        for digest in (REPOSITORY, MODEL):
            paths, _, _ = ADAPTER.selected_paths(digest)
            bundles[digest] = {name: self.captured[path] for name, path in paths.items()}
            self.assertEqual(WORKER.input_profile(bundles[digest]), digest)
        for digest in (REPOSITORY, MODEL):
            other = MODEL if digest == REPOSITORY else REPOSITORY
            for field in ('interface.json', 'composition.json'):
                changed = dict(bundles[digest]); changed[field] = bundles[other][field]
                with self.assertRaises(ValueError): WORKER.input_profile(changed)
            for field in ('codec.py', 'owned_child.py'):
                changed = dict(bundles[digest]); changed[field] += b'\n'
                with self.assertRaises(ValueError): WORKER.input_profile(changed)


if __name__ == '__main__':
    unittest.main()

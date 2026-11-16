"""Authored export boundaries only; the whole native journey remains unrun."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PREPARED = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT
sys.path[:0] = [str(ROOT / 'scripts/ci'), str(ROOT / 'scripts/urbit'), str(ROOT / 'scripts')]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fixtures = load('authored_product_fixtures', CONTROLLER / 'tests/test_product_result.py')
projection = load('product_failure', PREPARED / 'scripts/ci/product_failure.py')
verifier = fixtures.verifier


def authored():
    report, inputs = fixtures.incomplete_outer()
    run_id = '9' * 32
    policy = {'profile': 'github-hosted-native/1', 'authored': 'not execution evidence'}
    for name in ('scripts/sdk_native/native.py', 'specs/urbit/toolchain.lock.json', 'scripts/ci/hosted.py'):
        inputs['controller_files'][name] = {'sha256': verifier.hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
    inputs['controller_files']['scripts/ci/product_failure.py'] = {'sha256': verifier.hashlib.sha256(Path(projection.__file__).read_bytes()).hexdigest()}
    import doc_worker_proof
    for name in ('scripts/ci/doc_worker_proof.py', 'scripts/urbit/doc_run_worker.py'):
        inputs['controller_files'][name] = {'sha256': verifier.hashlib.sha256((ROOT/name).read_bytes()).hexdigest()}
    job, context, _, expected = doc_worker_proof.fixture()
    doc_proof = {'protocol': 'stead.doc-worker-isolation-proof/1', 'status': 'pass',
        'worker_sha256': inputs['controller_files']['scripts/urbit/doc_run_worker.py']['sha256'],
        'proof_sha256': inputs['controller_files']['scripts/ci/doc_worker_proof.py']['sha256'],
        'job_sha256': verifier.hashlib.sha256(job).hexdigest(),
        'context_sha256': verifier.hashlib.sha256(context).hexdigest(),
        'artifact_sha256': verifier.hashlib.sha256(expected).hexdigest(),
        'checks': list(doc_worker_proof.CHECKS),
        'crashes': [{'point': name, 'parent_exit': -9,
            'files': {'before-child': [], 'before-output': [], 'after-output': ['proposal.md'],
                'after-receipt': ['proposal.md', 'result.json']}[name],
            'overwrite_refused': name != 'before-child'} for name in doc_worker_proof.CUTS],
        'classification': 'actual-isolated-deterministic-child-with-publication-fault-injection',
        'native_publication': False, 'model_execution': False, 'qualifies_g3': False}
    sources = inputs['controller_files']
    mounts = {prefix: {name[len(prefix) + 1:]: item['sha256'] for name, item in sources.items()
                      if name.startswith(prefix + '/')}
              for prefix in ('scripts/urbit', 'scripts/ci', 'specs/urbit', 'web/dev')}
    for name in ('scripts/release_install.py', 'scripts/sdk_native/native.py'):
        mounts[name] = sources[name]['sha256']
    mounts['native'] = {name.removeprefix('native/'): item['sha256'] for name, item in inputs['composed_files'].items()}
    mount_hash = verifier.hashlib.sha256(projection.canonical(mounts)).hexdigest()
    unit = 'stead-hosted-' + run_id + '.service'
    admission = {'status': 'admitted', 'run_id': run_id, 'profile': policy['profile'], 'authenticated_host': True, 'unit': unit}
    report['execution_guard'] = {'run_id': run_id, 'generation': 10,
        'guard_sha256': sources['scripts/ci/hosted.py']['sha256'],
        'policy_sha256': verifier.hashlib.sha256(projection.json.dumps(policy, sort_keys=True).encode()).hexdigest(), 'policy': policy}
    guard = {'status': 'fail', 'error': 'ValueError: Native worker process failed', 'run_id': run_id,
        'policy': policy, 'collector': {'overflow': False, 'error': None, 'eof': True, 'completed': True},
        'cleanup_errors': [], 'child_terminated': True, 'exit_code': 1, 'admission': admission}
    cleanup = {'verified': True, 'unit': unit, 'empty': True, 'active_state': 'failed'}
    observed = {'format': 'stead.product-journey-observation/1', 'status': 'observed', 'qualifies_phase': False,
        'scope': 'authored stub; no native execution', 'full_product_partial_restore': 'not-observed', 'browser': 'not-observed',
        'assertions': 80, 'callbacks': 70,
        'old_captures': {target: {'protocol': 'stead.v10-capture-record/1', 'target': target,
            'capture_pin': 'a' * 64, 'native_vase_fingerprint': 'b' * 64,
            'type_pin': 'c' * 64, 'payload_pin': 'd' * 64,
            'artifact_sha256': 'e' * 64, 'artifact_bytes': 1} for target in ('predecessor', 'product')},
        'result': {'profile': 'native-human-doc/1', 'scope': 'actual native Gall; HTTP/browser/agent-run not included',
            'project_id': 'PRIVATE-PROJECT-MUST-NOT-LEAK', 'work_id': 'PRIVATE-WORK-MUST-NOT-LEAK',
            'change_id': 'PRIVATE-CHANGE-MUST-NOT-LEAK', 'document_id': 'PRIVATE-DOC-MUST-NOT-LEAK',
            'accepted_markdown_sha256': 'a' * 64,
            'final_fingerprints': {'release_authority': 'b' * 64, 'review_authority': 'b' * 64,
                                   'release_vase': 'c' * 64, 'lifecycle_vase': 'c' * 64}}}
    value = {'format': 'stead.local-ci-worker/1', 'status': 'fail', 'cleanup': True,
        'error': 'ValueError: Native team suite failed', 'run_id': run_id,
        'inputs_sha256': verifier.hashlib.sha256(projection.canonical(inputs)).hexdigest(),
        'mounts_before': mount_hash, 'mounts_after': mount_hash,
        'isolation': {'private_network': True, 'host_credentials_absent': True, 'fresh_state': True, 'external_route_absent': True},
        'fresh_seeds': {'format': 1, 'toolchain_sha256': sources['specs/urbit/toolchain.lock.json']['sha256'],
                        'ships': {ship: 'd' * 64 for ship in verifier.SHIPS}},
        'admission': admission, 'native': report, 'product_observation': observed, 'doc_worker': doc_proof}
    return value, inputs, run_id, guard, cleanup, policy, observed


def raw(value):
    return (projection.PREFIX + projection.canonical(value).decode() + '\n').encode()


class ExportTests(unittest.TestCase):
    def run_projection(self, data):
        value, inputs, run_id, guard, cleanup, policy, observed = data
        with patch.object(projection.product_result, 'verify_observation', return_value=observed):
            return projection.project(raw(value), inputs, run_id=run_id, guard=guard, cleanup=cleanup,
                policy=policy, release_fingerprint=fixtures.release_install.saved_home_fingerprint)

    def test_inspection_cannot_omit_or_weaken_required_doc_child_proof(self):
        for kind in ('absent', 'wrong-source', 'missing-check', 'failed', 'claim-model'):
            data = list(authored())
            if kind == 'absent': data[0].pop('doc_worker')
            elif kind == 'wrong-source': data[0]['doc_worker']['worker_sha256'] = '0' * 64
            elif kind == 'missing-check': data[0]['doc_worker']['checks'].pop()
            elif kind == 'failed': data[0]['doc_worker']['status'] = 'fail'
            else: data[0]['doc_worker']['model_execution'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.run_projection(data)

    def test_authored_public_shape_exports_no_native_strings_or_credentials(self):
        value = self.run_projection(authored())
        self.assertFalse(value['qualifies_phase'])
        self.assertFalse(value['full_product_partial_restore'])
        self.assertFalse(value['browser'])
        self.assertEqual(value['owned_cold_restarts'], 16)
        self.assertNotIn('PRIVATE', projection.json.dumps(value))
        self.assertNotIn('nonce', projection.json.dumps(value))
        self.assertNotIn('pid', projection.json.dumps(value))

    def test_worker_cleanup_outer_cleanup_and_collector_eof_are_independent(self):
        for which in ('worker', 'outer', 'empty', 'eof', 'overflow'):
            data = list(authored())
            if which == 'worker':
                data[0]['cleanup'] = False
            elif which in ('outer', 'empty'):
                data[4]['verified' if which == 'outer' else 'empty'] = False
            elif which == 'eof':
                data[3]['collector']['eof'] = False
            else:
                data[3]['collector']['overflow'] = True
            with self.subTest(which=which), self.assertRaises(ValueError):
                self.run_projection(data)

    def test_exact_run_source_mount_and_policy_bindings_required(self):
        for which in ('run', 'source', 'mount', 'policy', 'unit'):
            data = list(authored())
            if which == 'run':
                data[0]['run_id'] = '8' * 32
            elif which == 'source':
                data[0]['native']['execution_guard']['guard_sha256'] = '0' * 64
            elif which == 'mount':
                data[0]['mounts_after'] = '0' * 64
            elif which == 'policy':
                data[3]['policy'] = {'profile': 'another'}
            else:
                data[4]['unit'] = 'stead-hosted-' + '8' * 32 + '.service'
            with self.subTest(which=which), self.assertRaises(ValueError):
                self.run_projection(data)

    def test_numeric_bool_float_aliases_are_not_accepted(self):
        for which in ('exit-float', 'exit-bool', 'seed', 'generation', 'empty', 'isolation'):
            data = list(authored())
            if which.startswith('exit'):
                data[3]['exit_code'] = 1.0 if which == 'exit-float' else True
            elif which == 'seed':
                data[0]['fresh_seeds']['format'] = True
            elif which == 'generation':
                data[0]['native']['execution_guard']['generation'] = 10.0
            elif which == 'empty':
                data[4]['empty'] = 1
            else:
                data[0]['isolation']['private_network'] = 1
            with self.subTest(which=which), self.assertRaises(ValueError):
                self.run_projection(data)

    def test_worker_must_fail_intentionally_and_host_replay_must_agree(self):
        for which in ('worker-pass', 'guardian-pass', 'different-observation', 'expanded-scope'):
            data = list(authored())
            if which == 'worker-pass':
                data[0]['status'] = 'pass'
            elif which == 'guardian-pass':
                data[3]['status'] = 'pass'
            elif which == 'different-observation':
                data[0]['product_observation'] = copy.deepcopy(data[6]) | {'assertions': 81}
            else:
                data[6]['full_product_partial_restore'] = 'observed'
            with self.subTest(which=which), self.assertRaises(ValueError):
                self.run_projection(data)

    def test_duplicate_truncated_or_nonfinal_frames_are_rejected(self):
        value, inputs, run_id, guard, cleanup, policy, _ = authored()
        for encoded in (raw(value) + raw(value), raw(value)[:-10], raw(value) + b'late output\n'):
            with self.subTest(length=len(encoded)), self.assertRaises((ValueError, projection.json.JSONDecodeError)):
                projection._worker(encoded, inputs, run_id, guard, cleanup, policy)

    def test_capture_metadata_cannot_export_extra_content_or_change_scope(self):
        for mutation in ('extra', 'raw', 'target', 'count-float', 'pin', 'missing'):
            data = list(authored())
            captures = data[6]['old_captures']
            if mutation == 'extra': captures['elsewhere'] = captures['product']
            elif mutation == 'raw': captures['product']['data_hex'] = 'SECRET-MUST-NOT-EXPORT'
            elif mutation == 'target': captures['product']['target'] = 'predecessor'
            elif mutation == 'count-float': captures['product']['artifact_bytes'] = 1.0
            elif mutation == 'pin': captures['product']['payload_pin'] = 'SECRET-MUST-NOT-EXPORT'
            else: captures.pop('predecessor')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.run_projection(data)


if __name__ == '__main__':
    unittest.main()

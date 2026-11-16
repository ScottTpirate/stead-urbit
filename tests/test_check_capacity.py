"""Authored global check-count boundaries, not complete native qualification.

The worker/product positives reach the next deliberate semantic refusal using
their real validators. No validator or proof routine is mocked; no child runs.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts/ci'), str(ROOT / 'scripts/urbit'), str(ROOT / 'scripts')]
import worker_result
import worker_failure
import doc_worker_proof
import release_install


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


fixtures = load('check_capacity_authored_product', ROOT / 'tests/test_product_result.py')


def frame(value):
    return (worker_result.PREFIX + worker_result.canonical(value).decode() + '\n').encode()


def check_rows(count):
    return [{'name': 'authored-boundary-' + str(index), 'passed': True} for index in range(count)]


def authored_worker(count):
    """Reach the check-count gate, then lack mandatory named native evidence."""
    run_id = '9' * 32
    paths = ['scripts/release_install.py', 'scripts/sdk_native/native.py',
             'specs/urbit/toolchain.lock.json', 'scripts/ci/migration.hoon',
             'scripts/urbit/doc_run_worker.py', 'scripts/ci/doc_worker_proof.py']
    sources = {name: {'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()} for name in paths}
    inputs = {'controller_files': sources, 'composed_files': {},
              'expected_native_inputs': {'toolchain': sources['specs/urbit/toolchain.lock.json']['sha256']}}
    mounts = {prefix: {name[len(prefix) + 1:]: row['sha256'] for name, row in sources.items()
                      if name.startswith(prefix + '/')}
              for prefix in ('scripts/urbit', 'scripts/ci', 'specs/urbit', 'web/dev')}
    for path in ('scripts/release_install.py', 'scripts/sdk_native/native.py'):
        mounts[path] = sources[path]['sha256']
    mounts['native'] = {}
    job, context, _, expected = doc_worker_proof.fixture()
    proof = {'protocol': 'stead.doc-worker-isolation-proof/1', 'status': 'pass',
        'worker_sha256': sources['scripts/urbit/doc_run_worker.py']['sha256'],
        'proof_sha256': sources['scripts/ci/doc_worker_proof.py']['sha256'],
        'job_sha256': hashlib.sha256(job).hexdigest(), 'context_sha256': hashlib.sha256(context).hexdigest(),
        'artifact_sha256': hashlib.sha256(expected).hexdigest(), 'checks': list(doc_worker_proof.CHECKS),
        'crashes': [{'point': name, 'parent_exit': -9,
            'files': {'before-child': [], 'before-output': [], 'after-output': ['proposal.md'],
                      'after-receipt': ['proposal.md', 'result.json']}[name],
            'overwrite_refused': name != 'before-child'} for name in doc_worker_proof.CUTS],
        'classification': 'actual-isolated-deterministic-child-with-publication-fault-injection',
        'native_publication': False, 'model_execution': False, 'qualifies_g3': False}
    native = {'status': 'pass', 'stage': 'completed',
        'classification': 'local-real-configured-gall-development',
        'inputs_before': inputs['expected_native_inputs'], 'inputs_after': inputs['expected_native_inputs'],
        'execution_guard': {'run_id': run_id}, 'installed': {ship: {} for ship in ('zod', 'bus', 'nec', 'bud')},
        'checks': check_rows(count)}
    value = {'format': 'stead.local-ci-worker/1', 'status': 'pass', 'cleanup': True,
        'inputs_sha256': hashlib.sha256(worker_result.canonical(inputs)).hexdigest(), 'run_id': run_id,
        'admission': {'status': 'admitted', 'run_id': run_id},
        'mounts_before': hashlib.sha256(worker_result.canonical(mounts)).hexdigest(),
        'mounts_after': hashlib.sha256(worker_result.canonical(mounts)).hexdigest(),
        'isolation': dict.fromkeys(('private_network', 'host_credentials_absent', 'fresh_state', 'external_route_absent'), True),
        'fresh_seeds': {'format': 1, 'toolchain_sha256': inputs['expected_native_inputs']['toolchain'],
                        'ships': dict.fromkeys(('zod', 'bus', 'nec', 'bud'), 'd' * 64)},
        'native': native, 'migration': {'source_sha256': sources['scripts/ci/migration.hoon']['sha256'],
                                      'output': '%stead-ci-supported-migration-pass'},
        'filesystem_controls': {}, 'negative_controls': {}, 'doc_worker': proof}
    return value, inputs, run_id


class CheckCapacityTests(unittest.TestCase):
    def test_worker_2020_and_4096_reach_next_gate_4097_or_nontrue_refuse(self):
        for count in (2020, 4096):
            value, inputs, run_id = authored_worker(count)
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, '^Native allow/deny/replay/restart evidence missing$'):
                worker_result.verify(frame(value), inputs, run_id=run_id, inventory={})
        value, inputs, run_id = authored_worker(4097)
        with self.assertRaisesRegex(ValueError, '^Failed or empty native checks$'):
            worker_result.verify(frame(value), inputs, run_id=run_id, inventory={})
        value, inputs, run_id = authored_worker(2020)
        for flag in (False, 1, 1.0, 'true'):
            value['native']['checks'][-1]['passed'] = flag
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, '^Failed or empty native checks$'):
                worker_result.verify(frame(value), inputs, run_id=run_id, inventory={})

    def test_product_2020_and_4096_reach_callback_gate_4097_refuses(self):
        for count in (2020, 4096, 4097):
            report, inputs = fixtures.incomplete_outer()
            report['checks'] = check_rows(count)
            expected = '^Journey traversal bounds$' if count == 4097 else '^Exact ordered callback correlation$'
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, expected):
                fixtures.verifier.verify_observation(report, inputs,
                    release_fingerprint=release_install.saved_home_fingerprint)

    def test_failure_4096_keeps_exact_true_false_counts_4097_refuses(self):
        run_id = '9' * 32
        inputs = {'expected_native_inputs': {'authored': 'no native execution'}}
        value = {'format': 'stead.local-ci-worker/1', 'status': 'fail', 'cleanup': True,
            'run_id': run_id, 'inputs_sha256': hashlib.sha256(worker_result.canonical(inputs)).hexdigest(),
            'error': 'AssertionError: authored', 'native': {'checks': check_rows(4096)}}
        # Failure metadata counts exact booleans; numeric lookalikes do not
        # become passing checks and this path never returns qualification.
        value['native']['checks'][-3]['passed'] = False
        value['native']['checks'][-2]['passed'] = 1
        value['native']['checks'][-1]['passed'] = 0
        observed = worker_failure.project(frame(value), inputs, run_id=run_id)
        self.assertEqual(observed['native']['checks_recorded'], 4096)
        self.assertEqual(observed['native']['checks_passed'], 4093)
        self.assertEqual(observed['native']['checks_failed'], 1)
        self.assertIs(observed['qualifies_phase'], False)
        value['native']['checks'].append({'name': 'extra', 'passed': True})
        with self.assertRaisesRegex(ValueError, '^Failure check bound$'):
            worker_failure.project(frame(value), inputs, run_id=run_id)


if __name__ == '__main__':
    unittest.main()

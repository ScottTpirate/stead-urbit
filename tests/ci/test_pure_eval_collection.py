"""Inert collector checks: real canonical bytes, synthetic processes and kernel metadata."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch
import sys

DIRECTORY = Path(__file__).resolve().parents[2] / 'scripts/ci/pure_eval'
def load(label, path):
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
B = load('pure_boundary_under_test', DIRECTORY / 'owner_boundary.py')
with patch.dict(sys.modules, {'owner_boundary': B}):
    C = load('pure_collection_under_test', DIRECTORY / 'owner_collection.py')


def selected():
    return tuple({'label': label, 'kind': 'suite', 'source': b'x',
                  'source_sha256': hashlib.sha256(b'x').hexdigest(), 'timeout_seconds': 85,
                  'arms': ('test-one',)} for label in ('compiler-control', 'failing-tang-control', 'catalog', 'import', 'authority', 'store'))


def observe(job, code, stdout, stderr):
    if stdout == b'unknown': raise ValueError('inert malformed terminal')
    return {'label': job['label'], 'kind': job['kind'], 'status': 'fail' if stdout == b'failed' else 'pass',
            'exit_code': code, 'arms': ({'name': 'test-one', 'tang_length': 0, 'passed': True},),
            'stdout_sha256': hashlib.sha256(stdout).hexdigest(), 'stdout_bytes': len(stdout),
            'stderr_sha256': hashlib.sha256(stderr).hexdigest(), 'stderr_bytes': len(stderr),
            'compiler_failure': False}
PROFILE = {'composition_sha256': '3d42cb1788ddbe5bdf6f9643bbbe4d2bfa7245a24431b851ef247c525c9ead72',
           'positive_arms': 26, 'jobs': 6}
# These lifecycle doubles remain synthetic. test_pure_eval_profiles uses the real
# codec and both complete source maps to verify cross-profile admission.
def profile(digest):
    if digest != PROFILE['composition_sha256']: raise ValueError('inert wrong profile')
    return dict(PROFILE)
CODEC = types.SimpleNamespace(observe=observe, profile=profile, job_profile=lambda _: dict(PROFILE))
HASHES = {'fixed-source': 'a' * 64}


def stream_row(raw):
    return {'present': True, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'base64': base64.b64encode(raw).decode('ascii')}


def report(failed=False):
    records = []
    for i, job in enumerate(selected()):
        stdout = b'failed' if failed and i == 2 else b'\x00\xff\n'
        observation = observe(job, 0, stdout, b'')
        records.append({'label': job['label'], 'source_sha256': job['source_sha256'],
                        'source_bytes': 1, 'exit_code': 0, 'stdout': stream_row(stdout),
                        'stderr': stream_row(b''), 'observation': json.loads(C.canonical(observation))})
    return {'protocol': 'stead.fixed-pure-eval-report/1', 'status': 'fail' if failed else 'pass',
            'qualifies_phase': False, 'composition_sha256': '3d42cb1788ddbe5bdf6f9643bbbe4d2bfa7245a24431b851ef247c525c9ead72',
            'runtime_sha256': 'f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833',
            'records': records, 'source_hashes_before': HASHES, 'source_hashes_after': HASHES,
            'budget_stop': None, 'error_class': 'ValueError' if failed else 'none',
            'children_reaped': True, 'namespace_baseline_restored': True, 'expected_positive_arms': 26,
            'expected_controls': 2, 'native_application_executed': False}


def envelope(failed=False):
    owner = {'host_uid': 1001, 'host_gid': 1002, 'sources': {'worker.py': {'bytes': 10, 'sha256': 'a' * 64},
                 'composition.json': {'bytes': 240147, 'sha256': PROFILE['composition_sha256']}},
             'runtime': {'sha256': 'f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833'}}
    namespaces = {name: name + ':[2]' for name in ('user', 'mnt', 'pid', 'net')}
    digest = hashlib.sha256(C.canonical(owner)).hexdigest()
    ready = {'protocol': 'stead.fixed-pure-eval-ready/1', 'pid': 1234, 'uid': 1000, 'gid': 1000,
             'namespaces': namespaces, 'owner_sha256': digest}
    proof = {'uid': 1000, 'gid': 1000, 'host_uid': 1001, 'host_gid': 1002,
             'namespace_maps': {'uid': [1000, 0, 1], 'gid': [1000, 0, 1]}, 'namespaces': namespaces,
             'source_uid': 65534, 'capabilities_empty': True, 'no_new_privileges': True,
             'private_loopback_only': True, 'owner_sha256': digest, 'sources': owner['sources'],
             'runtime_sha256': owner['runtime']['sha256'], 'guardian_lease_required': True}
    raw = C.canonical(report(failed))
    final = {'protocol': 'stead.fixed-pure-eval-worker-result/1', 'status': 'fail' if failed else 'pass',
             'phase': 'source-after' if failed else 'complete', 'error_class': 'ValueError' if failed else 'none',
             'cleanup_error_class': 'none', 'report': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
             'admission': proof, 'outer_cleanup_required': True, 'children_reaped': True,
             'namespace_baseline_restored': True, 'jobs_retained': 6, 'elapsed_ms': 10,
             'qualifies_phase': False, 'native_application_executed': False}
    return owner, ready, final, raw


class Stream:
    def __init__(self, fd, events, broken=False): self.fd, self.events, self.closed, self.broken = fd, events, False, broken
    def fileno(self): return self.fd
    def write(self, raw): self.events.append(('go', raw))
    def flush(self): self.events.append(('flush',))
    def close(self):
        self.events.append(('close', self.fd))
        if self.broken: raise BrokenPipeError('inert closed pipe')
        self.closed = True


class Selector:
    def __init__(self): self.entries = {}
    def register(self, stream, _, name): self.entries[stream.fd] = types.SimpleNamespace(fileobj=stream, data=name)
    def unregister(self, stream): self.entries.pop(stream.fd)
    def select(self, _): return [(value, 1) for value in list(self.entries.values())]
    def get_map(self): return self.entries
    def close(self): self.entries.clear()


class PureEvalCollectionTests(unittest.TestCase):
    def test_report_replays_all_raw_bytes_and_zero_output_without_promoting_failed_suite(self):
        for failed in (False, True):
            source = report(failed); raw = C.canonical(source)
            self.assertEqual(C.validate_report(raw, CODEC, selected(), HASHES), source)
            self.assertEqual(base64.b64decode(source['records'][0]['stdout']['base64']), b'\x00\xff\n')
            self.assertIs(source['records'][0]['stderr']['present'], True)
            self.assertEqual(source['records'][0]['stderr']['bytes'], 0)
        forged = report(True); forged['status'] = 'pass'
        with self.assertRaises(ValueError): C.validate_report(C.canonical(forged), CODEC, selected(), HASHES)

    def test_report_rejects_alias_types_raw_drift_order_and_unsafe_budget_claim(self):
        mutations = [lambda r: r['records'][0]['observation']['arms'][0].update(tang_length=False),
                     lambda r: r['records'][0]['observation']['arms'][0].update(tang_length=0.0),
                     lambda r: r['records'][0]['observation']['arms'][0].update(passed=1),
                     lambda r: r['records'][0].update(exit_code=False),
                     lambda r: r['records'][0]['stdout'].update(bytes=True),
                     lambda r: r['records'][0]['stdout'].update(sha256='f' * 64),
                     lambda r: r['records'][0].update(label='store'),
                     lambda r: r.update(expected_positive_arms=26.0),
                     lambda r: r.update(children_reaped=1),
                     lambda r: r.update(source_hashes_after={}),
                     lambda r: r.update(budget_stop={'label': 'catalog', 'bytes': 4063232, 'sha256': 'f' * 64})]
        for mutate in mutations:
            value = report(); mutate(value)
            with self.assertRaises(ValueError): C.validate_report(C.canonical(value), CODEC, selected(), HASHES)
        value = report(True); value['records'] = value['records'][:2]; value['source_hashes_after'] = {}
        value['budget_stop'] = {'label': 'catalog', 'bytes': 4063233, 'sha256': 'f' * 64}
        self.assertEqual(len(C.validate_report(C.canonical(value), CODEC, selected(), HASHES)['records']), 2)
        self.assertEqual(C.WORKER_REPORT_LIMIT, 4063232)
        with self.assertRaises(ValueError): C.validate_report(b' ' * 4063233, CODEC, selected(), HASHES)

    def test_worker_proof_requires_exact_scalar_and_nested_identity_types(self):
        owner, ready, final, _ = envelope()
        self.assertEqual(C.worker_result(final, owner, ready, CODEC), final)
        mutations = [lambda f: f['admission'].update(host_uid=1001.0),
                     lambda f: f['admission'].update(host_gid=1002.0),
                     lambda f: f['admission']['namespace_maps']['uid'].__setitem__(2, True),
                     lambda f: f['admission']['namespace_maps']['gid'].__setitem__(0, 1000.0),
                     lambda f: f['admission']['sources']['worker.py'].update(bytes=10.0),
                     lambda f: f.update(jobs_retained=6.0),
                     lambda f: f.update(elapsed_ms=True),
                     lambda f: f.update(children_reaped=1)]
        for mutate in mutations:
            value = copy.deepcopy(final); mutate(value)
            with self.assertRaises(ValueError): C.worker_result(value, owner, ready, CODEC)

    def collect(self, failed=False, missing_eof=False, duplicate=False, cleanup_ok=True):
        owner, ready, final, raw = envelope(failed); events = []
        stdin, stdout, stderr = (Stream(fd, events) for fd in (700, 701, 702))
        process = types.SimpleNamespace(stdin=stdin, stdout=stdout, stderr=stderr,
            returncode=1 if failed else 0, poll=lambda: (1 if failed else 0) if stdout.closed and stderr.closed else None,
            wait=Mock(return_value=1 if failed else 0))
        payload = C.canonical(ready) + b'\n' + C.canonical(final) + b'\n'
        if duplicate: payload += C.canonical(final) + b'\n'
        chunks = {701: [payload, b''], 702: [b'']}
        def read(fd, _):
            if missing_eof and fd == 701 and len(chunks[701]) == 1: raise OSError('inert missing EOF')
            return chunks[fd].pop(0)
        def cleanup(*_): events.append(('cleanup',)); return cleanup_ok
        def retained(*_):
            self.assertTrue(stdout.closed and stderr.closed)
            self.assertIn(('cleanup',), events); events.append(('artifact',)); return raw
        anchor = {'pidfd': 777}
        with contextlib_exit() as stack:
            patches = [(C.selectors, 'DefaultSelector', Mock(return_value=Selector())),
                       (C.os, 'set_blocking', Mock()), (C.os, 'read', read),
                       (C, 'service_current', Mock()), (C, 'cleanup', cleanup),
                       (C.select, 'select', Mock(return_value=([777], [], []))),
                       (B, 'pin_ready', Mock(return_value=anchor)),
                       (B, 'loopback_observation', Mock(return_value={'fixed': True})),
                       (B, 'current', Mock()), (B, 'monitor_current', Mock(return_value=False)),
                       (B, 'read_output', Mock(side_effect=retained)),
                       (B, 'close_anchor', Mock(side_effect=lambda _: events.append(('anchor-close',))))]
            for module, name, value in patches: stack.enter_context(patch.object(module, name, value))
            result, artifact = C.run(process, Path('/inert'), {}, owner, Mock(), CODEC, selected(), HASHES)
        return result, artifact, events

    def test_collector_drains_completed_worker_and_reads_only_after_cleanup_and_eof(self):
        for failed in (False, True):
            result, artifact, events = self.collect(failed)
            self.assertEqual(result['status'], 'fail' if failed else 'pass')
            self.assertEqual(artifact, C.canonical(report(failed)))
            self.assertTrue(result['parent_admitted'] and result['child_streams_eof'] and result['owned_children_empty'])
            self.assertLess(events.index(('cleanup',)), events.index(('artifact',)))
            self.assertLess(events.index(('artifact',)), events.index(('anchor-close',)))
            self.assertEqual([event for event in events if event[0] == 'go'], [('go', b'go\n')])

    def test_missing_eof_duplicate_final_and_unconfirmed_cleanup_never_read_artifact(self):
        for arguments in ({'missing_eof': True}, {'duplicate': True}, {'cleanup_ok': False}):
            result, artifact, events = self.collect(**arguments)
            self.assertEqual(result['status'], 'fail'); self.assertIsNone(artifact)
            self.assertNotIn(('artifact',), events); self.assertIn(('cleanup',), events)
            self.assertIn(('anchor-close',), events)

    def test_initial_fault_and_broken_stdin_preserve_error_and_cleanup(self):
        events = []; stdin = Stream(700, events, broken=True)
        process = types.SimpleNamespace(stdin=stdin, stdout=Stream(701, events), stderr=Stream(702, events))
        with patch.object(C.selectors, 'DefaultSelector', return_value=Selector()), patch.object(C, 'service_current', side_effect=ValueError('inert first cause')), patch.object(C, 'cleanup', side_effect=lambda *_: events.append(('cleanup',)) or True), patch.object(B, 'read_output') as reader:
            result, artifact = C.run(process, Path('/inert'), {}, {}, Mock(), CODEC, selected(), HASHES)
        self.assertEqual(result['error_class'], 'ValueError'); self.assertEqual(result['cleanup_error_class'], 'stdin-close')
        self.assertEqual(result['status'], 'fail'); self.assertTrue(result['owned_children_empty'])
        self.assertIn(('cleanup',), events); self.assertIsNone(artifact); reader.assert_not_called()


def contextlib_exit():
    from contextlib import ExitStack
    return ExitStack()


if __name__ == '__main__':
    unittest.main()

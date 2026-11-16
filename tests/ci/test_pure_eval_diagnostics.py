"""Authored inert diagnostics boundaries; no actual evaluator or failure replay.

The unchanged collector fixture provides synthetic streams/processes only. The
long traces below are explicit authored Python data, not observed native faults.
"""
import copy
from contextlib import ExitStack
import hashlib
import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pure_diagnostic_fixture', HERE / 'test_pure_eval_collection.py')
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
C, B = F.C, F.B
SECRET = 'PRIVATE_EXCEPTION_LOCAL_RAW_OUTPUT_DO_NOT_EXPORT'


def sources():
    paths = {'owner_collection': Path(C.__file__), 'owner_boundary': Path(B.__file__),
             'service_adapter': F.DIRECTORY / 'service_adapter.py'}
    return {name: {'raw': path.read_bytes(), 'filename': str(path)} for name, path in paths.items()}


def caught(call):
    try:
        call()
    except BaseException as error:
        return error
    raise AssertionError('Authored fault did not occur')


def synthetic_trace(raw, function, *args):
    """Create only the test's own inert traceback; no candidate operations."""
    filename = '/authored-inert/owner_boundary.py'
    namespace = {}
    exec(compile(raw, filename, 'exec'), namespace)
    return caught(lambda: namespace[function](*args)), {'raw': raw, 'filename': filename}


class PureEvalDiagnosticTests(unittest.TestCase):
    def test_exact_captured_locations_exclude_messages_locals_and_unrelated_frames(self):
        pinned = sources()
        for call, expected in ((lambda: B.require(False), 'owner_boundary'),
                               (lambda: C.parse(('{' + SECRET).encode(), 1000), 'owner_collection')):
            private_local = SECRET
            error = caught(call)
            error.args = (SECRET,)
            result = C.failure_positions(error, 'final', pinned)
            self.assertEqual(result['protocol'], 'stead.fixed-pure-eval-collector-failure/1')
            self.assertEqual(result['source_sha256'], {
                name: hashlib.sha256(row['raw']).hexdigest() for name, row in pinned.items()})
            self.assertIn(expected, {row['source'] for row in result['locations']})
            for row in result['locations']:
                self.assertEqual(set(row), {'source', 'function', 'line'})
                self.assertIs(type(row['line']), int)
                self.assertTrue(1 <= row['line'] <= len(pinned[row['source']]['raw'].splitlines()))
            encoded = C.canonical(result)
            self.assertNotIn(private_local.encode(), encoded)
            self.assertNotIn(str(HERE).encode(), encoded)
            self.assertNotIn(str(F.DIRECTORY).encode(), encoded)
            self.assertLessEqual(len(encoded), 8192)

    def test_same_filename_foreign_code_and_malformed_source_inputs_are_not_admitted(self):
        pinned = sources()
        forged = {}
        exec(compile('def require(ok):\n    raise ValueError("' + SECRET + '")\n',
                     B.__file__, 'exec'), forged)
        error = caught(lambda: forged['require'](False))
        result = C.failure_positions(error, 'current-worker', pinned)
        self.assertEqual(result['locations'], [])
        self.assertNotIn(SECRET.encode(), C.canonical(result))
        for mutate in (lambda p: p.update(unregistered=p['owner_boundary']),
                       lambda p: p['owner_boundary'].update(raw='not bytes'),
                       lambda p: p['owner_boundary'].update(raw=b' ' * 262145),
                       lambda p: p['owner_boundary'].update(filename='/inert/other.py'),
                       lambda p: p['owner_boundary'].update(extra='not admitted')):
            value = copy.deepcopy(pinned); mutate(value)
            with self.assertRaises(ValueError): C.failure_positions(error, 'final', value)
        for phase in ([], {}, None, True, 'unknown-stage'):
            with self.assertRaises(ValueError): C.failure_positions(error, phase, pinned)

    def test_trace_location_and_code_node_caps_remain_explicit_and_bounded(self):
        pinned = sources()
        lines = []
        for index in range(20):
            body = 'f_' + str(index + 1) + '()' if index < 19 else 'raise ValueError("' + SECRET + '")'
            lines += ['def f_' + str(index) + '():', '    ' + body]
        error, controlled = synthetic_trace(('\n'.join(lines) + '\n').encode(), 'f_0')
        pinned['owner_boundary'] = controlled
        result = C.failure_positions(error, 'final', pinned)
        self.assertEqual(len(result['locations']), 16)
        self.assertIs(result['truncated'], True)
        self.assertLessEqual(result['frames_inspected'], 64)
        self.assertNotIn(SECRET.encode(), C.canonical(result))
        raw = b'def walk(n):\n    if n:\n        return walk(n-1)\n    raise ValueError("inert")\n'
        error, controlled = synthetic_trace(raw, 'walk', 80)
        pinned['owner_boundary'] = controlled
        result = C.failure_positions(error, 'final', pinned)
        self.assertEqual(result['frames_inspected'], 64)
        self.assertIs(result['truncated'], True)
        self.assertLessEqual(len(result['locations']), 16)
        pinned['owner_boundary']['raw'] = b''.join(
            ('def f_' + str(index) + '():\n    return None\n').encode() for index in range(256))
        with self.assertRaises(ValueError): C.failure_positions(error, 'final', pinned)

    def test_rejected_final_summary_is_closed_nullable_metadata_and_never_authority(self):
        _, _, final, _ = F.envelope(True)
        expected_keys = {'presence', 'status', 'phase', 'error_class', 'cleanup_error_class',
                         'children_reaped', 'namespace_baseline_restored', 'jobs_retained', 'report_presence'}
        self.assertEqual(C.final_summary(None), {'presence': 'absent'})
        self.assertEqual(C.final_summary(SECRET), {'presence': 'unrecognized'})
        extra = dict(final, arbitrary_output=SECRET)
        self.assertEqual(C.final_summary(extra), {'presence': 'unrecognized'})
        final['admission'] = {'worker_controlled_secret': SECRET}
        final['elapsed_ms'] = SECRET
        good = C.final_summary(final)
        self.assertEqual(set(good), expected_keys)
        self.assertEqual(good['presence'], 'recognized-envelope')
        self.assertEqual(good['report_presence'], 'descriptor')
        self.assertNotIn(SECRET.encode(), C.canonical(good))
        for field in ('status', 'phase', 'error_class', 'cleanup_error_class'):
            for invalid in (SECRET, [], 1, None):
                row = copy.deepcopy(final); row[field] = invalid
                summary = C.final_summary(row)
                self.assertIsNone(summary[field])
                self.assertNotIn(SECRET.encode(), C.canonical(summary))
        for field in ('children_reaped', 'namespace_baseline_restored', 'jobs_retained'):
            for invalid in (1.0, '1', None, SECRET):
                row = copy.deepcopy(final); row[field] = invalid
                self.assertIsNone(C.final_summary(row)[field])
        for field in ('children_reaped', 'namespace_baseline_restored'):
            for invalid in (0, 1):
                row = copy.deepcopy(final); row[field] = invalid
                self.assertIsNone(C.final_summary(row)[field])
        for invalid in (False, True, -1, 7):
            row = copy.deepcopy(final); row['jobs_retained'] = invalid
            self.assertIsNone(C.final_summary(row)['jobs_retained'])
        for invalid in ({'bytes': True, 'sha256': 'a' * 64}, {'bytes': 1, 'sha256': SECRET},
                        {'bytes': 4063233, 'sha256': 'a' * 64}, SECRET, {}):
            row = copy.deepcopy(final); row['report'] = invalid
            self.assertEqual(C.final_summary(row)['report_presence'], 'malformed')
        row = copy.deepcopy(final); row['report'] = None
        self.assertEqual(C.final_summary(row)['report_presence'], 'absent')

    def collect(self, *, rejected_final=False, current_fault=False, diagnostic_fault=False, cleanup_fault=False):
        owner, ready, final, raw = F.envelope(True)
        if rejected_final:
            final.update(cleanup_error_class='baseline-or-temporary-files', report=None,
                         children_reaped=False, namespace_baseline_restored=False)
            final['admission']['not_exported'] = SECRET
        events = []
        stdin, stdout, stderr = (F.Stream(fd, events) for fd in (1700, 1701, 1702))
        process = types.SimpleNamespace(stdin=stdin, stdout=stdout, stderr=stderr,
            returncode=1, poll=lambda: 1 if stdout.closed and stderr.closed else None,
            wait=Mock(return_value=1))
        ready_bytes = C.canonical(ready) + b'\n'
        final_bytes = C.canonical(final) + b'\n'
        chunks = {1701: [ready_bytes, final_bytes, b''] if current_fault else [ready_bytes + final_bytes, b''],
                  1702: [b'']}
        def read(fd, maximum): return chunks[fd].pop(0)
        def cleanup(*_):
            events.append(('cleanup',))
            if cleanup_fault: raise OSError(SECRET)
            return True
        current_calls = 0
        def current(*_):
            nonlocal current_calls
            current_calls += 1
            if current_fault and current_calls > 1:
                events.append(('current-fault',)); B.require(False)
        def retained(*_):
            self.assertIn(('cleanup',), events)
            self.assertTrue(stdout.closed and stderr.closed)
            events.append(('artifact',)); return raw
        actual_positions = C.failure_positions
        def diagnostic(*args):
            events.append(('diagnostic',))
            if diagnostic_fault: raise RuntimeError(SECRET)
            return actual_positions(*args)
        with ExitStack() as stack:
            for target, name, replacement in (
                    (C.selectors, 'DefaultSelector', F.Selector), (C.os, 'set_blocking', Mock()),
                    (C.os, 'read', read), (C.select, 'select', Mock(return_value=([], [], []))),
                    (C, 'service_current', Mock()), (C, 'cleanup', cleanup),
                    (C, 'failure_positions', diagnostic),
                    (B, 'pin_ready', Mock(return_value={'pidfd': 1900})),
                    (B, 'loopback_observation', Mock(return_value={'proof_descriptors_closed': True})),
                    (B, 'current', current), (B, 'monitor_current', current),
                    (B, 'read_output', retained),
                    (B, 'close_anchor', lambda *_: events.append(('anchor-close',)))):
                stack.enter_context(patch.object(target, name, replacement))
            result, artifact = C.run(process, Path('/inert'), {}, owner, Mock(), F.CODEC,
                                     F.selected(), F.HASHES, diagnostic_sources=sources())
        return result, artifact, events

    def test_rejected_final_is_diagnosed_without_artifact_or_cleanup_bypass(self):
        result, artifact, events = self.collect(rejected_final=True)
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['error_class'], 'ValueError')
        self.assertIs(result['parent_admitted'], True)
        self.assertIs(result['owned_children_empty'], True)
        self.assertIsNone(result['worker_result'])
        self.assertIsNone(artifact)
        self.assertNotIn(('artifact',), events)
        self.assertLess(events.index(('diagnostic',)), events.index(('cleanup',)))
        self.assertLess(events.index(('cleanup',)), events.index(('anchor-close',)))
        observation = result['failure_observation']
        self.assertEqual(observation['phase'], 'final')
        self.assertIn('worker_result', {r['function'] for r in observation['locations']})
        self.assertEqual(observation['attempted_final']['cleanup_error_class'], 'baseline-or-temporary-files')
        self.assertEqual(observation['attempted_final']['report_presence'], 'absent')
        self.assertNotIn(SECRET.encode(), C.canonical(result))
        # Existing fully correlated failed-suite evidence still follows the same
        # strict EOF/reap/read path; diagnostics do not turn it into success.
        result, artifact, events = self.collect()
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['error_class'], 'none')
        self.assertIsNone(result['failure_observation'])
        self.assertIsNotNone(artifact)
        self.assertLess(events.index(('cleanup',)), events.index(('artifact',)))

    def test_post_go_guard_and_diagnostic_faults_preserve_first_error_and_cleanup(self):
        for diagnostic_fault, cleanup_fault in ((False, False), (True, False), (True, True)):
            result, artifact, events = self.collect(current_fault=True,
                diagnostic_fault=diagnostic_fault, cleanup_fault=cleanup_fault)
            self.assertEqual(result['status'], 'fail')
            self.assertEqual(result['error_class'], 'ValueError')
            self.assertEqual(result['cleanup_error_class'], 'owned-cleanup' if cleanup_fault else 'none')
            self.assertIs(result['parent_admitted'], True)
            self.assertIsNone(artifact)
            self.assertNotIn(('artifact',), events)
            self.assertIn(('cleanup',), events)
            self.assertIn(('anchor-close',), events)
            self.assertLess(events.index(('current-fault',)), events.index(('cleanup',)))
            self.assertNotIn(SECRET.encode(), C.canonical(result))
            if diagnostic_fault:
                self.assertIsNone(result['failure_observation'])
            else:
                self.assertEqual(result['failure_observation']['phase'], 'current-worker')
                self.assertEqual(result['failure_observation']['attempted_final'], {'presence': 'absent'})


if __name__ == '__main__':
    unittest.main()

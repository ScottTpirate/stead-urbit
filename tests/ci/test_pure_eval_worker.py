"""Inert host checks for the exact pure worker; no evaluator or namespace runs."""
import base64
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[2] / 'scripts/ci/pure_eval/worker.py'
spec = importlib.util.spec_from_file_location('pure_worker_under_test', SOURCE)
W = importlib.util.module_from_spec(spec)
spec.loader.exec_module(W)


def job(label='catalog', kind='suite', timeout=85):
    source = b'tiny inert source\n'
    return dict(label=label, kind=kind, source=source,
                source_sha256=hashlib.sha256(source).hexdigest(),
                timeout_seconds=timeout, arms=('test-one',))


def jobs():
    return tuple(job(label, 'compiler-control' if i == 0 else 'failing-tang-control' if i == 1 else 'suite',
                     15 if i < 2 else 85)
                 for i, label in enumerate(('compiler-control', 'failing-tang-control', 'catalog', 'import', 'authority', 'store')))


class Process:
    pid = 12345
    def __init__(self, running=False):
        self.returncode = None if running else 0
        self.waits = []
        self.killed = False
    def poll(self):
        return self.returncode
    def wait(self, timeout):
        self.waits.append(timeout)
        self.returncode = 0
        return 0
    def kill(self):
        self.killed = True
        self.returncode = -9


class PureEvalWorkerTests(unittest.TestCase):
    def test_source_inventory_exact_helper_path_and_no_extra_or_missing_input(self):
        names = ['native/core/desk/lib/f%d.hoon' % i for i in range(54)]
        helper = 'pkg/base-dev/lib/test.hoon'
        rows = {name: {'bytes': 1, 'sha256': W.sha(b'x')} for name in names}
        composition = {'sources': rows, 'composition': {'test_helper': dict(path=helper, bytes=1, sha256=W.sha(b'x'))}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in names + [helper]:
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'x')
            def exact(path, expected):
                raw = path.read_bytes()
                self.assertEqual({'bytes': len(raw), 'sha256': W.sha(raw)}, expected)
                return raw
            # Directory traversal and privileged metadata checks are mocked;
            # file bytes and hash checks are real.
            walked = [(str(root), [], names + [helper])]
            with patch.object(W, 'SOURCES', root), patch.object(W.os, 'walk', return_value=walked), patch.object(W, 'exact_file', side_effect=exact):
                files, hashes = W.source_inventory(composition)
                self.assertEqual(set(files), set(names + [helper])); self.assertEqual(len(hashes), 55)
                for bad in (names, names + [helper, 'ambient.hoon'], names + ['test-helper.hoon']):
                    with patch.object(W.os, 'walk', return_value=[(str(root), [], bad)]):
                        with self.assertRaises(ValueError): W.source_inventory(composition)

                # The repository default remains 55; model selection must reject it.
                with self.assertRaises(ValueError):
                    W.source_inventory(composition, W.MODEL_COMPOSITION_SHA)

        # Actual frozen model21 files and their original declared bytes/hashes.
        # Directory traversal and privileged metadata checks are mocked;
        # file bytes and hash checks are real.
        source_root = SOURCE.parents[3]
        model_root = source_root / 'scripts/ci/pure_eval/model_data'
        raw = (model_root / 'composition.json').read_bytes()
        self.assertEqual(W.sha(raw), W.MODEL_COMPOSITION_SHA)
        model = json.loads(raw)
        private_sources = {
            'native/core/desk/lib/stead-model-codec.hoon',
            'native/core/desk/lib/stead-model-material.hoon',
            'native/core/desk/lib/stead-model-reply.hoon',
            'native/core/desk/lib/stead-model-turn-codec.hoon',
            'native/core/desk/tests/stead-model-codec.hoon',
            'native/core/desk/tests/stead-model-reply.hoon',
            'native/core/desk/tests/stead-model-turn-codec.hoon',
        }
        originals = {name: ((model_root if name in private_sources else source_root) / name).read_bytes()
                     for name in model['sources']}
        helper = model['composition']['test_helper']
        originals[helper['path']] = (source_root / 'scripts/ci/pure_eval/data' / helper['path']).read_bytes()
        expected = {**model['sources'], helper['path']: helper}
        self.assertEqual(len(originals), 21)
        for name, data in originals.items():
            self.assertEqual({'bytes': len(data), 'sha256': W.sha(data)},
                             {key: expected[name][key] for key in ('bytes', 'sha256')})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, data in originals.items():
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            def pinned_file(path, expected):
                data = path.read_bytes()
                W.require({'bytes': len(data), 'sha256': W.sha(data)} == expected)
                return data
            walked = [(str(root), [], list(originals))]
            with patch.object(W, 'SOURCES', root), patch.object(W.os, 'walk', return_value=walked), patch.object(W, 'exact_file', side_effect=pinned_file):
                files, hashes = W.source_inventory(model, W.MODEL_COMPOSITION_SHA)
                self.assertEqual(files, originals)
                self.assertEqual(hashes, {name: W.sha(data) for name, data in originals.items()})
                for wrong in (W.COMPOSITION_SHA, '0' * 64, W.MODEL_COMPOSITION_SHA.upper(), True, 21, {'source_files': 21}):
                    with self.subTest(profile=wrong), self.assertRaises(ValueError):
                        W.source_inventory(model, wrong)
                for names in (list(originals)[:-1], [*originals, 'ambient.hoon']):
                    with patch.object(W.os, 'walk', return_value=[(str(root), [], names)]), self.assertRaises(ValueError):
                        W.source_inventory(model, W.MODEL_COMPOSITION_SHA)
                mixed = copy.deepcopy(model)
                mixed['sources']['ambient.hoon'] = {'bytes': 1, 'sha256': W.sha(b'x')}
                with self.assertRaises(ValueError): W.source_inventory(mixed, W.MODEL_COMPOSITION_SHA)
                changed = copy.deepcopy(model)
                changed['sources']['native/core/desk/lib/stead-model-codec.hoon']['sha256'] = 'f' * 64
                with self.assertRaises(ValueError): W.source_inventory(changed, W.MODEL_COMPOSITION_SHA)
                target = root / 'native/core/desk/lib/stead-model-codec.hoon'
                original = target.read_bytes()
                try:
                    target.write_bytes(original + b'\n')
                    with self.assertRaises(ValueError): W.source_inventory(model, W.MODEL_COMPOSITION_SHA)
                finally:
                    target.write_bytes(original)

    def test_parent_go_requires_exact_bytes_and_eof_with_current_lease(self):
        selector = Mock(); selector.select.return_value = [object()]
        for pieces, accepted in (([b'g', b'o\n', b''], True), ([b''], False), ([b'go\n', b'x'], False), ([b'no\n'], False)):
            lease = Mock()
            with patch.object(W.selectors, 'DefaultSelector', return_value=selector), patch.object(W.os, 'set_blocking'), patch.object(W.os, 'read', side_effect=pieces), patch.object(W.time, 'monotonic', return_value=1):
                if accepted: W.await_go(lease, 2)
                else:
                    with self.assertRaises(ValueError): W.await_go(lease, 2)
            self.assertGreater(lease.check.call_count, 0)
        with patch.object(W.selectors, 'DefaultSelector', return_value=selector), patch.object(W.os, 'set_blocking'):
            with self.assertRaises(TimeoutError): W.await_go(types.SimpleNamespace(check=Mock(side_effect=TimeoutError())), 2)
        self.assertEqual(selector.close.call_count, 5)

    def test_anonymous_regular_capture_is_exact_reaped_and_source_bound(self):
        original_temp = tempfile.TemporaryFile
        process = Process(); lease = Mock(); owned = Mock(); owned.command.return_value = ['inert-wrapper']
        opened = []
        with tempfile.TemporaryDirectory() as directory:
            def launch(argv, **kw):
                self.assertEqual(argv, ['inert-wrapper']); self.assertEqual(kw['stdin'].read(), job()['source'])
                self.assertIs(kw['preexec_fn'], W.child_limits)
                self.assertTrue(kw['close_fds'] and kw['start_new_session'])
                self.assertEqual(kw['env'], W.ENV)
                kw['stdout'].write(b'original\x00bytes'); kw['stdout'].flush()
                kw['stderr'].write(b''); kw['stderr'].flush()
                return process
            def pidfd(_pid, _flags):
                fd = os.open(SOURCE, os.O_RDONLY); opened.append(fd); return fd
            with patch.object(W.tempfile, 'TemporaryFile', side_effect=lambda **_: original_temp(dir=directory)), patch.object(W.subprocess, 'Popen', side_effect=launch), patch.object(W.os, 'pidfd_open', side_effect=pidfd), patch.object(W, 'process_ids', return_value={1, os.getpid()}):
                self.assertEqual(W.evaluate(job(), owned, lease, {1, os.getpid()}, 10**12), (0, b'original\x00bytes', b''))
            self.assertTrue(process.waits)
            with self.assertRaises(OSError): os.fstat(opened[0])
            self.assertEqual(list(Path(directory).iterdir()), [])
        owned.command.assert_called_once_with(['/runtime/vere', 'eval', '--loom', '29'])

    def test_evaluation_lease_deadline_and_output_limits_always_reap(self):
        original_temp = tempfile.TemporaryFile
        for fault in ('lease', 'deadline', 'output', 'baseline'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                process = Process(running=fault in ('deadline', 'output'))
                lease = Mock()
                if fault == 'lease': lease.check.side_effect = [None, TimeoutError()]
                def launch(_argv, **kw):
                    if fault == 'output': kw['stdout'].write(b'x' * (W.LIMIT + 1)); kw['stdout'].flush()
                    return process
                owned = types.SimpleNamespace(command=lambda argv: ['inert'])
                identities = [{1, os.getpid()}, {1, os.getpid(), 9876}] if fault == 'baseline' else None
                with patch.object(W.tempfile, 'TemporaryFile', side_effect=lambda **_: original_temp(dir=directory)), patch.object(W.subprocess, 'Popen', side_effect=launch), patch.object(W.os, 'pidfd_open', side_effect=lambda *_: os.open(SOURCE, os.O_RDONLY)), patch.object(W.signal, 'pidfd_send_signal') as sent, patch.object(W, 'process_ids', side_effect=identities, return_value={1, os.getpid()}), patch.object(W.time, 'monotonic', return_value=1):
                    with self.assertRaises((ValueError, TimeoutError)):
                        W.evaluate(job(), owned, lease, {1, os.getpid()}, 0 if fault == 'deadline' else 100)
                self.assertIsNotNone(process.returncode); self.assertTrue(process.waits)
                if fault in ('deadline', 'output'): self.assertEqual(sent.call_args.args[1], signal.SIGTERM)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_child_limits_and_pidfd_stop_escalation_are_fixed(self):
        with patch.object(W.resource, 'setrlimit') as limits:
            W.child_limits()
        self.assertEqual(limits.call_args_list[0].args, (W.resource.RLIMIT_FSIZE, (1000000, 1000000)))
        self.assertEqual(limits.call_args_list[1].args, (W.resource.RLIMIT_CORE, (0, 0)))
        process = Mock(); process.poll.return_value = None
        process.wait.side_effect = [W.subprocess.TimeoutExpired('inert', 3), 0]
        with patch.object(W.signal, 'pidfd_send_signal') as sent: W.stop(process, 765)
        self.assertEqual([c.args for c in sent.call_args_list], [(765, signal.SIGTERM), (765, signal.SIGKILL)])
        self.assertEqual([c.kwargs for c in process.wait.call_args_list], [{'timeout': 3}, {'timeout': 3}])

    def test_report_file_is_exclusive_bounded_and_unchanged_original_bytes(self):
        self.assertEqual(W.STAGING_LIMIT, 4063232); self.assertEqual(W.REPORT_LIMIT, 4194304)
        with tempfile.TemporaryDirectory() as directory, patch.object(W, 'OUTPUT', Path(directory)):
            value = {'binary': base64.b64encode(b'\x00\xff\n').decode()}
            row = W.atomic_report(value); raw = (Path(directory) / 'report.json').read_bytes()
            self.assertEqual(raw, W.canonical(value)); self.assertEqual(row, {'bytes': len(raw), 'sha256': W.sha(raw)})
            self.assertEqual((Path(directory) / 'report.json').stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError): W.atomic_report(value)
        with tempfile.TemporaryDirectory() as directory, patch.object(W, 'OUTPUT', Path(directory)), patch.object(W, 'STAGING_LIMIT', 8):
            with self.assertRaises(ValueError): W.atomic_report({'long': 'too long'})
            self.assertEqual(list(Path(directory).iterdir()), [])

    def run_main(self, scenario):
        selected = jobs(); before = {'logical-source': 'a' * 64}; captured = []; evaluated = []
        proof = {'owner_sha256': 'a' * 64}; lease = Mock()
        def evaluate(item, *_):
            evaluated.append(item['label'])
            return 0, (b'x' * 1000000 if scenario == 'budget' else item['label'].encode()), b''
        def observe(item, code, stdout, stderr):
            if scenario == 'malformed' and item['label'] == 'catalog': raise ValueError('inert unknown output')
            return {'status': 'fail' if scenario == 'completed-failure' and item['label'] == 'catalog' else 'pass', 'arms': ()}
        profile = {'composition_sha256': W.COMPOSITION_SHA, 'positive_arms': 26, 'jobs': 6}
        codec = types.SimpleNamespace(observe=observe, job_profile=lambda _: profile)
        owner = {'sources': {'composition.json': {'sha256': W.COMPOSITION_SHA}}}
        original_path = Path
        class EmptyTemp:
            def iterdir(self): return iter(())
        def fake_path(value): return EmptyTemp() if value == '/tmp' else original_path(value)
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            for name, value in {'admission': Mock(return_value=(owner, proof, codec, object(), selected, {}, before)), 'process_ids': Mock(return_value={1, os.getpid()}), 'GuardianLease': Mock(return_value=lease), 'namespace_values': Mock(return_value={'pid': 'pid:[1]'}), 'await_go': Mock(), 'evaluate': Mock(side_effect=evaluate), 'source_inventory': Mock(return_value=({}, before)), 'atomic_report': Mock(side_effect=lambda report: captured.append(copy.deepcopy(report)) or {'bytes': len(W.canonical(report)), 'sha256': W.sha(W.canonical(report))}), 'Path': fake_path}.items(): stack.enter_context(patch.object(W, name, value))
            stack.enter_context(patch.object(W.signal, 'signal')); stack.enter_context(patch.object(W.signal, 'setitimer'))
            stack.enter_context(contextlib.redirect_stdout(out)); code = W.main()
        rows = [json.loads(row) for row in out.getvalue().splitlines()]
        self.assertEqual(len(rows), 2); self.assertTrue(rows[-1]['children_reaped']); self.assertTrue(rows[-1]['namespace_baseline_restored'])
        return code, captured[0], rows[-1], evaluated

    def test_main_continues_only_completed_failed_suite_and_never_promotes_it(self):
        for scenario in ('pass', 'completed-failure', 'malformed'):
            with self.subTest(scenario=scenario):
                code, report, final, evaluated = self.run_main(scenario)
                self.assertEqual(code, 0 if scenario == 'pass' else 1)
                self.assertEqual(report['status'], 'pass' if scenario == 'pass' else 'fail')
                self.assertIs(report['qualifies_phase'], False); self.assertIs(report['native_application_executed'], False)
                self.assertEqual(len(evaluated), 3 if scenario == 'malformed' else 6)
                self.assertEqual(report['source_hashes_after'], {} if scenario == 'malformed' else report['source_hashes_before'])
                if scenario == 'malformed': self.assertIsNone(report['records'][-1]['observation'])
                self.assertEqual(final['jobs_retained'], len(report['records']))

    def test_budget_stop_is_before_append_with_no_dropped_suite_pass_claim(self):
        code, report, final, evaluated = self.run_main('budget')
        self.assertEqual(code, 1); self.assertEqual(len(report['records']), 3); self.assertEqual(len(evaluated), 4)
        self.assertEqual(report['budget_stop']['label'], 'import'); self.assertGreater(report['budget_stop']['bytes'], W.STAGING_LIMIT)
        self.assertLessEqual(len(W.canonical(report)), W.STAGING_LIMIT)
        self.assertEqual(report['source_hashes_after'], {}); self.assertEqual(final['status'], 'fail')
        self.assertNotIn('import', [row['label'] for row in report['records']])
        self.assertEqual(len(report['budget_stop']['sha256']), 64)


if __name__ == '__main__':
    unittest.main()

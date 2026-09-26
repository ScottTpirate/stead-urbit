"""Host lifecycle and result-admission regressions; native execution is mocked."""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import fcntl
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import shutil
import socket
import subprocess
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import core_check
import harness
import digests
import execution_policy


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-dev-flow-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / '.piers/fakes'
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in (('ROOT', self.root), ('BASE', self.root / '.piers'), ('STATE', self.state)):
            self.stack.enter_context(patch.object(harness, name, value))
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def test_status_does_not_create_absent_fixture(self):
        self.assertEqual(harness.status()['stage'], 'not-created')
        self.assertFalse(self.state.parent.exists())

    def test_status_distinguishes_stopped_from_unresponsive_owner(self):
        harness.guard(create=True)
        with (self.state / 'lifecycle.lock').open('a+') as owner:
            self.assertEqual(harness.status()['stage'], 'stopped')
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(harness.status()['stage'], 'unresponsive-owner')

    def test_status_refuses_redirected_fixture(self):
        self.state.parent.mkdir()
        self.state.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            harness.status()

    def test_status_does_not_mislabel_timeout_as_stopped(self):
        harness.guard(create=True)
        with patch.object(harness, 'rpc', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                harness.status()

    def test_ready_requires_running_guard(self):
        harness.guard(create=True)
        for value in ({}, {'state': 'stopped'}):
            with self.subTest(value=value), patch.object(harness, 'rpc', return_value={
                    'stage': 'ready', 'ready': True, 'execution_guard': value}):
                with self.assertRaises(RuntimeError):
                    harness.wait_ready()

    def test_terminal_failure_never_retries_start(self):
        harness.guard(create=True)
        with patch.object(harness, 'rpc', return_value={'stage': 'guard-stopped', 'ready': False}) as rpc:
            with patch.object(harness, 'start') as start:
                with self.assertRaises(RuntimeError):
                    harness.wait_ready()
                start.assert_not_called()
                self.assertEqual(rpc.call_count, 1)

    def test_dev_cleans_up_failed_compile(self):
        harness.guard(create=True)
        with patch.object(harness, 'start'), patch.object(harness, 'wait_ready'):
            with patch.object(harness, 'core_check', side_effect=RuntimeError('compile failed')):
                with patch.object(harness, 'stop') as stop:
                    with self.assertRaisesRegex(RuntimeError, 'compile failed'):
                        harness.dev()
                    stop.assert_called_once()

    def test_public_feedback_cli_uses_only_the_fixed_rpc(self):
        harness.guard(create=True)
        with patch.object(harness, 'rpc', return_value={'status': 'pass'}) as rpc:
            harness.skill_feedback('baseline', 'T04', 2)
            rpc.assert_called_once_with('skill-feedback', condition='baseline', task='T04', attempt=2, timeout=3600)
        for condition, task, attempt in (('prequalification', 'T04', 1), ('baseline', '../T04', 1),
                                         ('baseline', 'T04', 0), ('baseline', 'T04', 4),
                                         ('baseline', 'T04', True)):
            with self.subTest(condition=condition, task=task, attempt=attempt), patch.object(harness, 'rpc') as rpc:
                with self.assertRaises(ValueError):
                    harness.skill_feedback(condition, task, attempt)
                rpc.assert_not_called()

    def test_dev_cleans_up_start_failure_and_keyboard_interrupt(self):
        harness.guard(create=True)
        for failing in ('start', 'wait_ready', 'core_check'):
            for error in (RuntimeError('failed'), KeyboardInterrupt()):
                with self.subTest(failing=failing, error=type(error).__name__), ExitStack() as stack:
                    for name in ('start', 'wait_ready', 'core_check'):
                        stack.enter_context(patch.object(harness, name,
                            side_effect=error if name == failing else None))
                    stop = stack.enter_context(patch.object(harness, 'stop'))
                    with self.assertRaises(type(error)):
                        harness.dev()
                    stop.assert_called_once()

    def test_dev_preserves_original_failure_when_cleanup_also_fails(self):
        harness.guard(create=True)
        with patch.object(harness, 'start', side_effect=RuntimeError('original')):
            with patch.object(harness, 'stop', side_effect=ValueError('cleanup')):
                with redirect_stderr(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'original'):
                        harness.dev()

    def test_preflight_never_launches_or_creates_fixture(self):
        cpu = 'thermal_zone0:x86_pkg_temp'
        for temperature, admitted in ((60, True), (80, False)):
            sample = execution_policy.Sample(100, 100, {cpu: temperature}, (cpu,))
            with self.subTest(temperature=temperature), ExitStack() as stack:
                stack.enter_context(patch.object(harness, 'execution_limits', return_value=execution_policy.Policy()))
                stack.enter_context(patch.object(execution_policy, 'sample_temperatures', return_value=sample))
                stack.enter_context(patch.object(execution_policy.time, 'monotonic', return_value=100))
                launch = stack.enter_context(patch.object(subprocess, 'Popen'))
                if admitted:
                    self.assertTrue(harness.preflight()['admitted'])
                else:
                    with self.assertRaises(execution_policy.GuardError):
                        harness.preflight()
                launch.assert_not_called()
                self.assertFalse(self.state.exists())

    def test_failed_launched_supervisor_marks_fixture_and_blocks_next_start(self):
        harness.guard(create=True)
        report = {'status': 'failed', 'launched': True, 'reason': 'child exit 1',
                  'run_directory': str(self.root / 'synthetic-run')}
        with patch.object(harness, 'execution_limits', return_value=execution_policy.Policy()), \
                patch.object(execution_policy, 'run_guarded', return_value=report):
            with self.assertRaisesRegex(RuntimeError, 'without clean completion'):
                harness.guarded_supervisor()
        marker = json.loads((self.state / 'unclean-live.json').read_text())
        self.assertEqual(marker['reason'], 'child exit 1')
        with patch.object(harness.toolchain, 'verify'), patch.object(harness, 'running', return_value=None), \
                patch.object(harness.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                harness.start()
            launch.assert_not_called()


class SupervisorDeveloperTests(unittest.TestCase):
    def setUp(self):
        source = Path(harness.__file__).with_name('supervisor.py')
        spec = importlib.util.spec_from_file_location('stead_dev_supervisor', source)
        self.supervisor = importlib.util.module_from_spec(spec)
        original = Path.read_text

        def read(path, *args, **kwargs):
            return '{}' if path == Path('/toolchain.json') else original(path, *args, **kwargs)

        source_digest = digests.source_sha
        with patch.object(Path, 'read_text', read), patch.object(digests, 'source_sha',
                side_effect=lambda root: source_digest(source.parent if root == Path('/code') else root)):
            spec.loader.exec_module(self.supervisor)
        self.supervisor.PROGRESS.update(stage='ready', ready=True)

    def dispatch(self, request):
        server, client = socket.socketpair()
        with client:
            client.sendall(json.dumps(request).encode() + b'\n')
            self.supervisor.handle(server)
            return json.loads(client.recv(65536))

    def feedback_mocks(self, stack, *, proof=None, outcome=None):
        module = self.supervisor
        if proof is None:
            proof = {'inner': {'path': '/workflow/prior/inner.json', 'sha256': 'a' * 64},
                     'guard': {'path': '/workflow/prior/guard.json', 'sha256': 'b' * 64}}
        stack.enter_context(patch.object(module, 'execution_check', return_value={
            'run_id': 'authored-host', 'generation': 1, 'guard_sha256': 'a' * 64,
            'policy_sha256': 'b' * 64, 'policy': {'authored': True}}))
        source = stack.enter_context(patch.object(module, 'qualified_source', return_value='c' * 40))
        original_read = module.execution_policy.read_json
        stack.enter_context(patch.object(module.execution_policy, 'read_json',
            side_effect=lambda path, **kwargs: proof if path == '/workflow/prequalification.json' else original_read(path, **kwargs)))
        run = stack.enter_context(patch.object(module.skill_evaluation_support, 'run',
                                              return_value=outcome or {'status': 'pass'}))
        stop = stack.enter_context(patch.object(module, 'all_stop'))
        return run, stop, source

    def test_public_rpc_resolves_one_fixed_read_only_snapshot_and_finishes_lifetime(self):
        with ExitStack() as stack:
            run, stop, source = self.feedback_mocks(stack)
            request = {'op': 'skill-feedback', 'condition': 'local_skill_assisted', 'task': 'T05', 'attempt': 3}
            response = self.dispatch(request)
            self.assertTrue(response['ok'], response)
            args, kwargs = run.call_args
            self.assertEqual(args[1:], (Path('/native-tests/skill-evaluation'),
                Path('/workflow/feedback/local_skill_assisted/T05/3'), 'local_skill_assisted'))
            self.assertIn('WORKFLOW_PREQUALIFICATION', args[0])
            self.assertEqual(kwargs, {'prequalify': False, 'feedback_task': 'T05', 'feedback_attempt': 3})
            self.assertEqual(source.call_count, 2)
            stop.assert_called_once()
            self.assertTrue(self.supervisor.NORMAL_STOP.is_set())
            self.assertTrue(self.supervisor.STOP_REQUESTED.is_set())
            self.assertTrue(self.supervisor.STOP.is_set())
            self.assertEqual(self.supervisor.PROGRESS['stage'], 'stopped')
            self.assertFalse(self.supervisor.PROGRESS['ready'])

    def test_public_rpc_rejects_broadened_keys_paths_conditions_and_attempts(self):
        good = {'op': 'skill-feedback', 'condition': 'baseline', 'task': 'T01', 'attempt': 1}
        malformed = [dict(good, candidate='/native-tests/skill-evaluation/reviewer'),
                     dict(good, condition='prequalification'), dict(good, task='../T02'),
                     dict(good, attempt=True), dict(good, attempt='1'), dict(good, attempt=0),
                     dict(good, attempt=4), {key: value for key, value in good.items() if key != 'attempt'}]
        for request in malformed:
            with self.subTest(request=request), ExitStack() as stack:
                run, stop, source = self.feedback_mocks(stack)
                self.assertFalse(self.dispatch(request)['ok'])
                run.assert_not_called()
                stop.assert_not_called()
                source.assert_not_called()

    def test_private_scoring_cannot_be_requested_with_public_task_parameters(self):
        with ExitStack() as stack:
            run, _, _ = self.feedback_mocks(stack)
            self.assertFalse(self.dispatch({'op': 'skill-evaluation', 'condition': 'baseline',
                'task': 'T01', 'attempt': 1})['ok'])
            run.assert_not_called()

    def test_public_prequalification_references_cannot_escape_workflow_mount(self):
        for path in ('/private/inner.json', '/workflow/../private/inner.json', 'workflow/inner.json'):
            with self.subTest(path=path), ExitStack() as stack:
                self.supervisor.PROGRESS.update(stage='ready', ready=True)
                proof = {'inner': {'path': path, 'sha256': 'a' * 64},
                         'guard': {'path': '/workflow/guard.json', 'sha256': 'b' * 64}}
                run, stop, _ = self.feedback_mocks(stack, proof=proof)
                self.assertFalse(self.dispatch({'op': 'skill-feedback', 'condition': 'baseline',
                    'task': 'T01', 'attempt': 1})['ok'])
                run.assert_not_called()
                stop.assert_called_once()
                self.assertTrue(self.supervisor.STOP.is_set())

    def feedback_reports(self, stack):
        temporary = stack.enter_context(tempfile.TemporaryDirectory(prefix='stead-feedback-evidence-host-'))
        state = Path(temporary)
        (state / 'logs').mkdir()
        stack.enter_context(patch.object(self.supervisor, 'STATE', state))
        result = {'status': 'pass', 'evidence_file': '.piers/fakes/logs/skill-evaluation-host.json',
                  'feedback_file': '.piers/fakes/logs/skill-evaluation-host-feedback.json'}
        paths = [state / 'logs' / Path(result[field]).name for field in ('evidence_file', 'feedback_file')]
        for path in paths:
            path.write_text(json.dumps({'status': 'pass', 'protocol': 'authored-host-only',
                                       'outer_guard_status': 'pending'}))
        return result, paths

    def test_late_guard_failure_updates_both_reports_without_private_error_disclosure(self):
        with ExitStack() as stack:
            result, paths = self.feedback_reports(stack)
            stack.enter_context(patch.object(self.supervisor, 'execution_check', side_effect=RuntimeError('PRIVATE guard detail')))
            self.assertEqual(self.supervisor.guarded_result(result)['status'], 'fail')
            private, public = [json.loads(path.read_bytes()) for path in paths]
            self.assertEqual(private['status'], 'fail')
            self.assertEqual(public['status'], 'fail')
            self.assertIn('PRIVATE guard detail', private['error'])
            self.assertNotIn('PRIVATE guard detail', json.dumps(public))
            self.assertTrue(public['infrastructure_error'])
            self.assertEqual(public['outer_guard_status'], 'pending')

    def test_failed_public_compile_with_healthy_guard_remains_a_task_failure(self):
        with ExitStack() as stack:
            result, paths = self.feedback_reports(stack)
            result.update(status='fail', error='AssertionError: selected-public-task-passed')
            public = {'status': 'fail', 'infrastructure_error': None,
                      'tasks': [{'id': 'T01', 'status': 'failed', 'error': 'actual compiler failure'}]}
            paths[1].write_text(json.dumps(public))
            self.feedback_mocks(stack)
            self.assertEqual(self.supervisor.guarded_result(result)['status'], 'fail')
            retained = json.loads(paths[1].read_bytes())
            self.assertEqual(retained['status'], 'fail')
            self.assertIsNone(retained['infrastructure_error'])
            self.assertEqual(retained['tasks'], public['tasks'])

    def test_final_source_or_cleanup_failure_cannot_leave_green_feedback(self):
        for failure in ('source', 'cleanup'):
            with self.subTest(failure=failure), ExitStack() as stack:
                self.supervisor.PROGRESS.update(stage='ready', ready=True)
                result, paths = self.feedback_reports(stack)
                _, stop, source = self.feedback_mocks(stack, outcome=result)
                if failure == 'source':
                    source.side_effect = ['c' * 40, 'd' * 40]
                else:
                    stop.side_effect = RuntimeError('PRIVATE cleanup detail')
                response = self.dispatch({'op': 'skill-feedback', 'condition': 'baseline', 'task': 'T01', 'attempt': 1})
                self.assertEqual(response['ok'], failure == 'source')
                for path in paths:
                    self.assertEqual(json.loads(path.read_bytes())['status'], 'fail')
                public = json.loads(paths[1].read_bytes())
                self.assertNotIn('PRIVATE cleanup detail', json.dumps(public))
                self.assertTrue(public['infrastructure_error'])
                self.assertTrue(self.supervisor.STOP.is_set())
                self.assertFalse(self.supervisor.PROGRESS['ready'])

    def test_failed_check_stops_children_and_clears_ready(self):
        for raised in (False, True):
            with self.subTest(raised=raised), ExitStack() as stack:
                server, client = socket.socketpair()
                stack.callback(client.close)
                stack.enter_context(patch.object(self.supervisor, 'execution_check'))
                stack.enter_context(patch.object(self.supervisor.core_check, 'run',
                    side_effect=RuntimeError('unexpected report failure') if raised else None,
                    return_value={'status': 'fail'}))
                stack.enter_context(patch.object(self.supervisor, 'guarded_result', side_effect=lambda result: result))
                stop = stack.enter_context(patch.object(self.supervisor, 'all_stop'))
                self.supervisor.PROGRESS.update(stage='ready', ready=True)
                client.sendall(b'{"op":"core-check"}\n')
                self.supervisor.handle(server)
                response = json.loads(client.recv(65536))
                self.assertEqual(response['ok'], not raised)
                self.assertFalse(self.supervisor.PROGRESS['ready'])
                self.assertEqual(self.supervisor.PROGRESS['stage'], 'failed')
                stop.assert_called_once()

    def test_shared_module_edit_after_eager_import_changes_supervisor_binding(self):
        # Real copied Python imports and byte mutation in a temporary directory;
        # no native functions, fixture state or runtime binaries execute.
        with tempfile.TemporaryDirectory(prefix='stead-cached-runner-') as temporary:
            copied = Path(temporary) / 'scripts/urbit'; copied.mkdir(parents=True)
            for source in Path(harness.__file__).parent.glob('*.py'):
                shutil.copyfile(source, copied / source.name)
            script = '''
import importlib, pathlib, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import digests
original = pathlib.Path.read_text
source_digest = digests.source_sha
def read(path, *args, **kwargs):
    return '{}' if path == pathlib.Path('/toolchain.json') else original(path, *args, **kwargs)
def source_hash(path):
    return source_digest(pathlib.Path(sys.argv[1]) if path == pathlib.Path('/code') else path)
with patch.object(pathlib.Path, 'read_text', read), patch.object(digests, 'source_sha', side_effect=source_hash):
    import supervisor, core_conn, digests
assert 'core_check' in sys.modules and 'core_test' in sys.modules
old = core_conn.run
path = pathlib.Path(sys.argv[1]) / 'core_conn.py'
path.write_text(path.read_text() + '\\n# changed after import\\n')
for name in ('core_test', 'core_check'):
    runner = importlib.import_module(name)
    assert runner.core_conn.run is old
    assert runner.closure() != runner.LOADED_CLOSURE
assert supervisor.LOADED_SOURCE_DIGEST != digests.source_sha(path.parent)
'''
            result = subprocess.run([sys.executable, '-c', script, str(copied)],
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CompileEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-compile-admission-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / 'native'; self.native.mkdir()
        (self.native / 'synthetic.hoon').write_text('synthetic bytes, not compiled Hoon')
        self.logs = self.root / 'logs'; self.logs.mkdir()
        self.pin = self.root / 'lock.json'; self.pin.write_text('{}')
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(redirect_stderr(io.StringIO()))
        self.stack.enter_context(patch.object(core_check, 'Path', side_effect=lambda path:
            {'/native/core/desk': self.native, '/state/logs': self.logs}.get(str(path), Path(path))))
        self.stack.enter_context(patch.object(core_check, 'sha', side_effect=lambda path:
            digests.sha(self.pin if str(path) == '/toolchain.json' else path)))
        self.closure = self.stack.enter_context(patch.object(core_check, 'closure', return_value={'test': 'current'}))
        self.stack.enter_context(patch.object(core_check, 'LOADED_CLOSURE', {'test': 'current'}))
        self.stack.enter_context(patch.object(core_check, 'source_sha', return_value='harness'))
        self.stack.enter_context(patch.object(core_check.core_conn, 'evaluator_controls', return_value={'status': 'passed'}))
        self.probes = {'+stead-build-probe': '%stead-builds-pass',
                       '+stead-codec-probe': '%stead-codec-six-vectors-pass',
                       '+stead-core-probe': '%stead-core-basic-and-counter-edge-pass',
                       '+stead-reducers-probe': '%stead-native-reducers-pass',
                       '+stead-save-probe': '%stead-save-format2-roundtrip-pass'}
        self.host = {'SHIPS': ('zod', 'bus', 'nec', 'bud'), 'LIVE': self.root / 'live',
                     'LOCK': {'runtime': {'binary': 'synthetic-not-executed'}},
                     'LOADED_SOURCE_DIGEST': 'harness',
                     **{name: Mock() for name in ('execution_check', 'all_stop', 'copy_seed_to_live', 'launch', 'wait_ready')}}
        self.host['dojo'] = Mock(side_effect=lambda ship, source: self.probes.get(source, '%.y'))

    def report(self):
        return json.loads(next(self.logs.glob('*.json')).read_text())

    def test_success_is_explicitly_compile_scope_not_phase_acceptance(self):
        result = core_check.run(self.host)
        self.assertEqual(result['status'], 'pass')
        self.assertFalse(result['qualifies_phase'])
        self.assertEqual(result['classification'], 'local-real-native-compile-probes')
        self.assertGreater(len(self.report()['checks']), 5)

    def test_wrong_compiler_result_is_failure_with_retained_output(self):
        self.probes['+stead-build-probe'] = 'compile error'
        self.assertEqual(core_check.run(self.host)['status'], 'fail')
        self.assertTrue(any(c['result'] == 'compile error' for c in self.report()['commands']))

    def test_required_save_load_probe_cannot_pass_on_empty_or_wrong_result(self):
        for output in ('', '~', '%stead-unsupported-state'):
            with self.subTest(output=output):
                self.probes['+stead-save-probe'] = output
                result = core_check.run(self.host)
                self.assertEqual(result['status'], 'fail')
                report = self.report()
                self.assertIn('+stead-save-probe', report['error'])
                self.assertEqual(report['commands'][-1], {
                    'ship': 'zod', 'dojo': '+stead-save-probe', 'result': output})
                self.assertIn({'name': '+stead-save-probe', 'passed': False}, report['checks'])

    def test_empty_sources_cannot_be_a_successful_build(self):
        (self.native / 'synthetic.hoon').unlink()
        self.assertEqual(core_check.run(self.host)['status'], 'fail')
        self.assertIn('nonempty-native-source', self.report()['error'])

    def test_stale_loaded_runner_cannot_reset_or_execute_fixture(self):
        self.closure.return_value = {'test': 'changed'}
        self.assertEqual(core_check.run(self.host)['status'], 'fail')
        self.host['all_stop'].assert_not_called()
        self.host['launch'].assert_not_called()

    def test_late_guard_failure_overrides_successful_probes(self):
        self.host['execution_check'].side_effect = [None, RuntimeError('guard stopped')]
        self.assertEqual(core_check.run(self.host)['status'], 'fail')
        self.assertIn('guard stopped', self.report()['error'])

    def test_source_change_during_build_is_not_a_pass(self):
        def call(ship, source):
            if source == '+stead-reducers-probe':
                (self.native / 'synthetic.hoon').write_text('changed while running')
            return self.probes.get(source, '%.y')
        self.host['dojo'].side_effect = call
        self.assertEqual(core_check.run(self.host)['status'], 'fail')
        self.assertIn('Source/input changed', self.report()['error'])

    def test_interrupted_native_work_retains_nonpassing_input_checkpoint(self):
        with patch.object(core_check.core_conn, 'evaluator_controls', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                core_check.run(self.host)
        report = self.report()
        self.assertEqual(report['status'], 'fail')
        self.assertFalse(report['qualifies_phase'])
        self.assertEqual(report['stage'], 'evaluator-controls')
        self.assertEqual(report['inputs_before']['runner'], {'test': 'current'})
        self.host['launch'].assert_not_called()


if __name__ == '__main__':
    unittest.main()

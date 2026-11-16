"""Ten authored inert diagnostic boundaries. No native outcome is simulated as proof.

The known 50-byte native refusal was not exported. Its positive recognition
case substitutes only the expected SHA; it is not a replay of that text.
All process/Dojo/guard operations below are inert doubles. These cases have not
been executed by their author; the separately reviewed host owner runs them.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/urbit'), str(ROOT / 'scripts/ci')]
import team_check as diagnostic
import native_units
import worker_failure


class BuildFailureDiagnosticsTests(unittest.TestCase):
    def base(self):
        return {'status': 'fail', 'qualifies_phase': False, 'diagnostic_only': True,
                'commands': [], 'checks': [{'name': 'prior-check', 'passed': True}],
                'installed': {'zod': 249}}

    def probe(self, folder, report, terminal, *, checkpoint=None, guard=None,
              captured=b'bounded synthetic build log\n', dojo_error=None):
        log = folder / 'zod.log'
        log.write_bytes(b'prior unrelated log\n')
        events = []

        def dojo(ship, source):
            self.assertEqual((ship, source), ('zod', '+stead-build-probe'))
            events.append('dojo')
            with log.open('ab') as stream:
                stream.write(captured)
            if dojo_error is not None:
                raise dojo_error
            return terminal

        def persist(stage):
            events.append('checkpoint')
            report['stage'] = stage
            if checkpoint is not None:
                checkpoint(report)

        def current():
            events.append('guard')
            if guard is not None:
                guard()

        host = {'dojo': dojo, 'execution_check': current}
        return host, persist, events

    def inventory(self):
        return json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_bytes())

    def test_completed_build_known_failure_and_success_are_exact(self):
        self.assertEqual(diagnostic.BUILD_FAILURE_SHA,
                         'cd0bbd5af9e06ee8ec5279531dc9a3b89956535a2af3c33f61d5c14c4559998d')
        synthetic = 'S' * 50

        for terminal, wanted, expected in [(synthetic, 'compile-failed', False),
                                            ('%stead-builds-pass\n', 'pass', True)]:
            with self.subTest(outcome=wanted), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                report = self.base()
                host, checkpoint, events = self.probe(folder, report, terminal)
                with patch.object(diagnostic, 'BUILD_FAILURE_SHA', hashlib.sha256(synthetic.encode()).hexdigest()):
                    outcome = diagnostic.completed_build_probe(host, report, checkpoint, folder)
                self.assertEqual(outcome, wanted)
                self.assertEqual(events, ['dojo', 'checkpoint', 'guard'])
                self.assertEqual(report['commands'], [
                    {'ship': 'zod', 'dojo': '+stead-build-probe', 'result': terminal}])
                self.assertIs(report['checks'][-1]['passed'], expected)
                self.assertEqual(report['build_probe_transcripts'][0]['log_offset'],
                                 len(b'prior unrelated log\n'))
                self.assertEqual(bytes.fromhex(report['build_probe_transcripts'][0]['log_hex']),
                                 b'bounded synthetic build log\n')
                self.assertEqual(report['stage'], 'build-probe-output')
                self.assertFalse(report['qualifies_phase'])

    def test_completed_build_wrong_terminal_prior_or_checkpoint_refuses(self):
        terminals = [None, {}, 'S' * 50, '%stead-builds-pass extra', '\u03bb' * 16385]
        for terminal in terminals:
            with self.subTest(terminal_type=type(terminal).__name__), tempfile.TemporaryDirectory() as directory:
                report = self.base()
                host, checkpoint, events = self.probe(Path(directory), report, terminal)
                with self.assertRaises(ValueError):
                    diagnostic.completed_build_probe(host, report, checkpoint, Path(directory))
                self.assertNotIn('guard', events)
        mutations = [
            lambda report: report['checks'].append({'name': 'prior-refusal', 'passed': False}),
            lambda report: report['checks'].append({'name': 'numeric-true', 'passed': 1}),
            lambda report: report['commands'].append({'ship': 'zod', 'dojo': '+stead-build-probe'}),
            lambda report: report.update(build_probe_transcripts=[{'ship': 'zod'}]),
        ]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                report = self.base()
                mutate(report)
                host, checkpoint, events = self.probe(Path(directory), report, '%stead-builds-pass')
                with self.assertRaises(ValueError):
                    diagnostic.completed_build_probe(host, report, checkpoint, Path(directory))
                self.assertEqual(events, [])
        for tamper in [lambda report: report['checks'][-1].update(passed=1),
                       lambda report: report['commands'][-1].update(ship='bus'),
                       lambda report: report.update(stage='running'),
                       lambda report: report['build_probe_transcripts'].append({'ship': 'zod'})]:
            with tempfile.TemporaryDirectory() as directory:
                report = self.base()
                host, checkpoint, events = self.probe(Path(directory), report, '%stead-builds-pass', checkpoint=tamper)
                with self.assertRaises(ValueError):
                    diagnostic.completed_build_probe(host, report, checkpoint, Path(directory))
                self.assertEqual(events, ['dojo', 'checkpoint'])

    def test_probe_transport_log_checkpoint_and_guard_never_continue(self):
        def fail_checkpoint(_):
            raise OSError('private checkpoint detail')

        def fail_guard():
            raise PermissionError('private guardian detail')

        cases = [({'dojo_error': TimeoutError('private transport detail')}, TimeoutError),
                 ({'captured': b'x' * 262145}, ValueError),
                 ({'checkpoint': fail_checkpoint}, OSError),
                 ({'guard': fail_guard}, PermissionError)]
        for options, error in cases:
            with self.subTest(options=list(options)), tempfile.TemporaryDirectory() as directory:
                report = self.base()
                host, checkpoint, events = self.probe(Path(directory), report, '%stead-builds-pass', **options)
                continued = False
                with self.assertRaises(error):
                    diagnostic.completed_build_probe(host, report, checkpoint, Path(directory))
                    continued = True
                self.assertFalse(continued)
                self.assertEqual(report['diagnostic_interruption']['phase'], 'build')
                self.assertNotIn('private ', json.dumps(report['diagnostic_interruption']))
                self.assertNotIn('private ', report['error'])
                self.assertFalse(report['qualifies_phase'])
                if 'dojo_error' in options or 'captured' in options:
                    self.assertEqual(report['commands'], [])

    def test_collector_keeps_completed_failures_and_never_qualifies(self):
        entries = [{'path': 'one'}, {'path': 'two'}, {'path': 'negative'}]
        seen, passed, failed = [], [], []

        def execute(entry):
            seen.append(entry['path'])
            return 'completed:' + entry['path']

        def verify(entry, completed):
            self.assertEqual(completed, 'completed:' + entry['path'])
            if entry['path'] == 'one':
                raise ValueError('completed module build failed')
            return {'path': entry['path']}

        with self.assertRaisesRegex(ValueError, '^Pure-unit diagnostic complete; qualification disabled$'):
            native_units.collect_pure_diagnostics(entries, execute, verify,
                lambda entry, value: passed.append((entry['path'], value)),
                lambda entry: failed.append(entry['path']))
        self.assertEqual(seen, ['one', 'two', 'negative'])
        self.assertEqual(failed, ['one'])
        self.assertEqual([entry[0] for entry in passed], ['two', 'negative'])

    def test_collector_transport_verifier_guard_and_retention_abort(self):
        for where, error in [('execute', ValueError), ('execute', TimeoutError),
                             ('verify', PermissionError), ('passed', ValueError),
                             ('failed', OSError)]:
            with self.subTest(where=where, error=error.__name__):
                seen = []

                def execute(entry):
                    seen.append(entry['path'])
                    if where == 'execute':
                        raise error('inert refusal')
                    return 'complete'

                def verify(entry, completed):
                    if where == 'verify':
                        raise error('inert refusal')
                    if where == 'failed':
                        raise ValueError('completed verdict refusal')
                    return entry

                def retained(entry, value):
                    if where == 'passed':
                        raise error('inert refusal')

                def rejected(entry):
                    if where == 'failed':
                        raise error('inert refusal')

                with self.assertRaises(error):
                    native_units.collect_pure_diagnostics([{'path': 'first'}, {'path': 'later'}],
                        execute, verify, retained, rejected)
                self.assertEqual(seen, ['first'])

    def test_writer_encoding_and_whole_suite_at_exact_budget(self):
        sample = {'unicode': '\u03bb\U0001f642', 'literal': 'line\n"quoted"\\', 'flag': False}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'exact.json'
            diagnostic.execution_policy.write_json(target, sample)
            self.assertEqual(target.read_bytes(), diagnostic.diagnostic_bytes(sample))
        report = self.base()
        staged = copy.deepcopy(report)
        staged.update(native_units=[{'path': '/tests/stead-session'}],
                      native_unit_transcripts=[{'path': '/tests/stead-session', 'terminal': 'complete'}],
                      payload='')
        staged['payload'] = 'x' * (diagnostic.DIAGNOSTIC_BUDGET - len(diagnostic.diagnostic_bytes(staged)))
        self.assertEqual(len(diagnostic.diagnostic_bytes(staged)), diagnostic.DIAGNOSTIC_BUDGET)
        diagnostic.retain_diagnostic(report, staged, 'suite', '/tests/stead-session')
        self.assertEqual(report, staged)
        before = copy.deepcopy(report)
        too_big = copy.deepcopy(staged)
        too_big['payload'] += 'x'
        with self.assertRaisesRegex(ValueError, 'evidence budget reached'):
            diagnostic.retain_diagnostic(report, too_big, 'suite', '/tests/stead-http')
        stop = report.pop('diagnostic_budget_stop')
        self.assertEqual(report, before)
        self.assertEqual(stop['staged_bytes'], diagnostic.DIAGNOSTIC_BUDGET + 1)
        self.assertEqual(stop['staged_sha256'], hashlib.sha256(diagnostic.diagnostic_bytes(too_big)).hexdigest())
        self.assertTrue(stop['omitted'])

    def test_escaped_oversize_suite_retains_neither_rows_nor_verdict(self):
        report = self.base()
        before = copy.deepcopy(report)
        path = '/tests/stead-session'
        staged = copy.deepcopy(report)
        staged['commands'].append({'ship': 'zod', 'native_test': {'stdout': '\U0001f642' * 180000}})
        staged['native_units'] = [{'path': path}]
        staged['native_unit_transcripts'] = [{'path': path, 'log_hex': '00', 'terminal': 'complete'}]
        staged['checks'].append({'name': 'native-unit-arms:' + path, 'passed': True})
        self.assertGreater(len(diagnostic.diagnostic_bytes(staged)), diagnostic.DIAGNOSTIC_BUDGET)
        with self.assertRaises(ValueError):
            diagnostic.retain_diagnostic(report, staged, 'suite', path)
        stop = report.pop('diagnostic_budget_stop')
        self.assertEqual(report, before)
        self.assertEqual(stop['path'], path)
        self.assertEqual(stop['phase'], 'suite')
        self.assertEqual(stop['staged_sha256'], hashlib.sha256(diagnostic.diagnostic_bytes(staged)).hexdigest())
        self.assertNotIn('native_units', report)
        self.assertNotIn('\U0001f642', json.dumps(report))

    def test_final_source_changes_and_overflow_remain_failed(self):
        report = self.base() | {'status': 'pass', 'qualifies_phase': True}
        diagnostic.finalize_diagnostic(report, {'source': 'old'}, {'source': 'new'}, 1.25)
        self.assertEqual(report['status'], 'fail')
        self.assertIs(report['qualifies_phase'], False)
        self.assertIn('source/input changed', report['error'])
        self.assertEqual(report['inputs_after'], {'source': 'new'})
        report = self.base() | {'payload': 'x' * (2 * 1024**2 - 2048)}
        after = {'payload': 'y' * (2 * 1024**2 + 2048)}
        diagnostic.finalize_diagnostic(report, {}, after, 2.5)
        self.assertEqual(report['status'], 'fail')
        self.assertIs(report['qualifies_phase'], False)
        self.assertNotIn('inputs_after', report)
        self.assertEqual(report['diagnostic_budget_stop']['phase'], 'final')
        self.assertEqual(report['diagnostic_budget_stop']['limit_bytes'], diagnostic.DIAGNOSTIC_FINAL_BUDGET)
        self.assertLessEqual(len(diagnostic.diagnostic_bytes(report)), diagnostic.DIAGNOSTIC_FINAL_BUDGET)
        self.assertLess(diagnostic.DIAGNOSTIC_FINAL_BUDGET, 4 * 1024**2)
        huge = self.base() | {'payload': 'z' * (4 * 1024**2)}
        with self.assertRaisesRegex(ValueError, 'final evidence bound'):
            diagnostic.finalize_diagnostic(huge, {}, {}, 3.5)

    def test_closed_limits_reject_type_identity_and_omitted_claims(self):
        inventory = self.inventory()
        path = inventory['suites'][0]['path']
        stop = {'phase': 'suite', 'path': path, 'staged_bytes': diagnostic.DIAGNOSTIC_BUDGET + 1,
                'staged_sha256': 'a' * 64, 'retained_bytes': 200,
                'limit_bytes': diagnostic.DIAGNOSTIC_BUDGET, 'omitted': True}
        interruption = {'phase': 'suite', 'path': path, 'error_class': 'TimeoutError',
                        'evidence_bytes': 0, 'evidence_sha256': None, 'raw_evidence_omitted': True}
        value = {'diagnostic_budget_stop': stop, 'diagnostic_interruption': interruption}
        self.assertEqual(worker_failure.diagnostic_limits(value, inventory),
                         {'budget_stop': stop, 'interruption': interruption})
        malformed = [value | {'diagnostic_budget_stop': stop | {key: wrong}}
                     for key, wrong in [('retained_bytes', True), ('staged_bytes', float(stop['staged_bytes'])),
                                        ('limit_bytes', True), ('omitted', 1), ('phase', 'private phase'),
                                        ('phase', []), ('path', {}),
                                        ('path', '/tests/private-name'), ('staged_sha256', 'raw secret')]]
        malformed += [value | {field: [{'path': path}]} for field in ('native_units', 'native_unit_transcripts')]
        malformed += [value | {'native_unit_failures': [path]}]
        malformed += [value | {'checks': [{'name': prefix + path, 'passed': True}]}
                      for prefix in ('native-unit-arms:', 'native-unit-expected-failure:')]
        malformed += [value | {'diagnostic_budget_stop': stop | {
            'limit_bytes': diagnostic.DIAGNOSTIC_FINAL_BUDGET,
            'staged_bytes': diagnostic.DIAGNOSTIC_FINAL_BUDGET + 1}}]
        malformed += [value | {'diagnostic_budget_stop': stop | {'phase': 'final', 'path': ''}}]
        malformed += [value | {'diagnostic_interruption': interruption | {key: wrong}}
                      for key, wrong in [('evidence_bytes', False), ('raw_evidence_omitted', 1),
                                         ('phase', []), ('path', {}),
                                         ('evidence_sha256', 'a' * 64), ('error_class', 'private exception')]]
        for bad in malformed:
            with self.subTest(keys=list(bad)), self.assertRaises(ValueError):
                worker_failure.diagnostic_limits(bad, inventory)
        report = self.base()
        diagnostic.diagnostic_error(report, RuntimeError('DO-NOT-EXPORT-SECRET'), 'suite', path,
                                    evidence={'private': 'DO-NOT-EXPORT-SECRET'})
        self.assertNotIn('DO-NOT-EXPORT-SECRET', json.dumps(report))
        self.assertGreater(report['diagnostic_interruption']['evidence_bytes'], 0)
        self.assertEqual(len(report['diagnostic_interruption']['evidence_sha256']), 64)

    def test_whole_dedicated_run_stops_after_all_registered_suites(self):
        """Real Python control flow; every native/process operation is inert."""
        inventory = self.inventory()
        self.assertEqual(len(inventory['suites']), 48)
        entries = [*inventory['suites'], inventory['negative_control']]
        self.assertEqual(sum(len(row['arms']) for row in inventory['suites']), 329)
        real_path = Path
        real_probe = diagnostic.completed_build_probe
        synthetic_build_failure = 'S' * 50

        class KernelPath:
            def __truediv__(self, _):
                return self

            def resolve(self, strict=False):
                return self

            def is_relative_to(self, root):
                return root == '/kernel'

        cases = [(True, set()), (False, set()),
                 (False, {entries[0]['path'], entries[2]['path']})]
        for build_passes, failed_paths in cases:
            events, writes = [], []
            with self.subTest(build_passes=build_passes, failed_suites=len(failed_paths)):
                with tempfile.TemporaryDirectory() as directory:
                    folder = real_path(directory)
                    (folder / 'zod.log').write_bytes(b'')

                    def paths(value):
                        if str(value) == '/state/logs':
                            return folder
                        if str(value) == '/state/logs/zod.log':
                            return folder / 'zod.log'
                        if str(value) == '/specs/phase2-pure-units.json':
                            return ROOT / 'specs/urbit/phase2-pure-units.json'
                        if str(value) == '/kernel/pkg/arvo':
                            return KernelPath()
                        return real_path(value)

                    def dojo(ship, source, **kwargs):
                        self.assertEqual(ship, 'zod')
                        events.append(('dojo', source))
                        if source == '+stead-build-probe':
                            return '%stead-builds-pass' if build_passes else synthetic_build_failure
                        if source.startswith('`path`%'):
                            return '/~zod/base/~2026.1.1' + source[len('`path`%'):]
                        self.assertTrue(source.startswith('=/  raw=@t'))
                        return '%.y'

                    def launch(ship, fresh=False):
                        self.assertEqual(ship, 'zod')
                        self.assertTrue(fresh)
                        events.append(('launch', ship))

                    def native_run(binary, socket, path, timeout):
                        events.append(('suite', path, timeout))
                        return {'stdout': '[32 %avow 0 %noun 0]'}

                    def verify(completed, *, path, expected, succeeds, failure_marker=None):
                        if path in failed_paths:
                            raise ValueError('synthetic completed module refusal')
                        return {'path': path, 'synthetic': True}

                    host = {'TEAM': object(), 'execution_check': lambda **kwargs: {'synthetic': True},
                            'LOADED_SOURCE_DIGEST': 'a' * 64,
                            'team_lifecycle': SimpleNamespace(LOADED_INGRESS_DIGEST='a' * 64),
                            'all_stop': lambda: events.append(('stop',)),
                            'copy_seed_to_live': lambda: events.append(('seed',)),
                            'SHIPS': ('zod', 'bus', 'nec', 'bud'), 'launch': launch,
                            'wait_ready': lambda ship: events.append(('ready', ship)),
                            'dojo': dojo, 'record': lambda *args: None, 'LIVE': folder,
                            'LOCK': {'runtime': {'binary': 'inert-never-executed'}}}
                    with patch.object(diagnostic, 'Path', side_effect=paths), \
                         patch.object(diagnostic, 'sha', return_value='a' * 64), \
                         patch.object(diagnostic, 'tree_sha', return_value='a' * 64), \
                         patch.object(diagnostic, 'source_sha', return_value='a' * 64), \
                         patch.object(diagnostic, 'closure', return_value={'source': 'a' * 64}), \
                         patch.object(diagnostic, 'LOADED_CLOSURE', {'source': 'a' * 64}), \
                         patch.object(diagnostic.native_install, 'install', return_value=249), \
                         patch.object(diagnostic.native_units, 'run', side_effect=native_run), \
                         patch.object(diagnostic.native_units, 'verify_output', side_effect=verify), \
                         patch.object(diagnostic, 'BUILD_FAILURE_SHA',
                                      hashlib.sha256(synthetic_build_failure.encode()).hexdigest()), \
                         patch.object(diagnostic, 'completed_build_probe',
                                      side_effect=lambda h, r, c: real_probe(h, r, c, folder)), \
                         patch.object(diagnostic.execution_policy, 'write_json',
                                      side_effect=lambda path, value: writes.append(copy.deepcopy(value))), \
                         patch.object(diagnostic.traceback, 'print_exc'):
                        result = diagnostic.run(host)
                    self.assertEqual([e for e in events if e[0] == 'launch'], [('launch', 'zod')])
                    self.assertEqual([e for e in events if e[0] == 'suite'], [
                        ('suite', '/~zod/base/~2026.1.1' + entry['path'], entry.get('timeout_seconds', 60))
                        for entry in entries])
                    self.assertEqual(result['status'], 'fail')
                    self.assertIs(result['qualifies_phase'], False)
                    self.assertIn('qualification disabled', result['error'])
                    final = writes[-1]
                    self.assertEqual([row for row in final['checks'] if row['name'] == 'zod:+stead-build-probe'],
                                     [{'name': 'zod:+stead-build-probe', 'passed': build_passes}])
                    self.assertEqual([row['path'] for row in final['native_unit_transcripts']],
                                     [entry['path'] for entry in entries])
                    self.assertEqual(len(final['native_units']), 49 - len(failed_paths))
                    self.assertEqual(final['native_unit_failures'], [entry['path'] for entry in entries if entry['path'] in failed_paths])
                    self.assertEqual(final['inputs_before'], final['inputs_after'])
                    self.assertFalse(any(e[0] == 'dojo' and e[1].startswith('|start') for e in events))
                    self.assertNotIn('product_observation', final)
                    self.assertNotIn('captures', final)


if __name__ == '__main__':
    unittest.main()

"""Six inert diagnostic groups; no native, process, namespace or socket effects.

Only authored Python traceback functions, tiny log files and the existing host
frame fixture execute. Native lifecycle, source mounts and leases are explicit
doubles. No exception message, command text, saved noun or raw log is evidence.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'scripts/ci/home_asset_rehearsal'
SECRET = 'PRIVATE_MESSAGE_LOCAL_COMMAND_NOUN_DO_NOT_EXPORT'


def load(name, path):
    missing = object()
    previous = sys.modules.get(name, missing)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is missing:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous


F = load('saved8_diagnostic_fixture', Path(__file__).with_name('test_home_asset_outer.py'))
E, R, W = F.E, F.R, F.W
_package = types.ModuleType('home_asset_rehearsal')
_package.__path__ = [str(PACKAGE)]
_package.evidence = E
with mock.patch.dict(sys.modules, {'home_asset_rehearsal': _package,
                                  'home_asset_rehearsal.evidence': E}):
    U = load('home_asset_rehearsal.runner', PACKAGE / 'runner.py')


def sources():
    paths = {'runner': PACKAGE / 'runner.py', 'evidence': PACKAGE / 'evidence.py',
             'release_install': ROOT / 'scripts/release_install.py',
             'native': ROOT / 'scripts/sdk_native/native.py'}
    return {name: {'raw': path.read_bytes(), 'filename': str(path),
                   'sha256': E.sha(path.read_bytes())} for name, path in paths.items()}


def caught(call):
    try:
        call()
    except BaseException as error:
        return error
    raise AssertionError('Authored fault did not occur')


def authored_trace(raw, function, *args):
    """Only fixed test-created code, never captured production operations."""
    filename = '/authored-inert/saved8.py'
    namespace = {}
    exec(compile(raw, filename, 'exec', dont_inherit=True), namespace)
    return caught(lambda: namespace[function](*args)), {
        'raw': raw, 'filename': filename, 'sha256': E.sha(raw)}


def diagnostic():
    return {'operation': 'seed-ready', 'last_command': U.command_observation('inert', '%.n'),
            'positions': U.failure_positions(caught(lambda: U.command_observation(7)), sources()),
            'native_log': {'bytes': 10, **U.compiler_projection(b'nest-fail\n')}}


class Saved8DiagnosticTests(unittest.TestCase):
    def test_exact_code_positions_reject_spoofs_and_bound_trace_without_private_text(self):
        pinned = sources()
        error = caught(lambda: U.command_observation(7))
        error.args = (SECRET,)
        row = U.failure_positions(error, pinned)
        self.assertEqual(row['source_sha256'], {k: v['sha256'] for k, v in pinned.items()})
        self.assertIn('runner', {v['source'] for v in row['locations']})
        self.assertIn('evidence', {v['source'] for v in row['locations']})
        for item in row['locations']:
            self.assertEqual(set(item), {'source', 'function', 'line'})
            self.assertTrue(1 <= item['line'] <= len(pinned[item['source']]['raw'].splitlines()))
        self.assertNotIn(SECRET.encode(), E.canonical(row))
        self.assertNotIn(str(PACKAGE).encode(), E.canonical(row))
        forged = {}
        exec(compile('def command_observation(source):\n    raise ValueError("' + SECRET + '")\n',
                     str(PACKAGE / 'runner.py'), 'exec', dont_inherit=True), forged)
        spoof = caught(lambda: forged['command_observation']('inert'))
        self.assertEqual(U.failure_positions(spoof, pinned)['locations'], [])
        for mutate in (lambda p: p.update(unknown=p['runner']),
                       lambda p: p['runner'].update(sha256='0' * 64),
                       lambda p: p['runner'].update(raw='not bytes'),
                       lambda p: p['runner'].update(extra=SECRET)):
            bad = deepcopy(pinned); mutate(bad)
            with self.assertRaises(ValueError):
                U.failure_positions(error, bad)
        lines = []
        for i in range(20):
            body = 'f_' + str(i + 1) + '()' if i < 19 else 'raise ValueError("inert")'
            lines += ['def f_' + str(i) + '():', '    ' + body]
        error, fixed = authored_trace(('\n'.join(lines) + '\n').encode(), 'f_0')
        capped = U.failure_positions(error, pinned | {'runner': fixed})
        self.assertEqual(len(capped['locations']), 16)
        self.assertIs(capped['truncated'], True)
        error, fixed = authored_trace(b'def walk(n):\n    if n:\n        return walk(n-1)\n    raise ValueError("inert")\n', 'walk', 80)
        capped = U.failure_positions(error, pinned | {'runner': fixed})
        self.assertEqual(capped['frames_inspected'], 64)
        self.assertIs(capped['truncated'], True)
        raw = b''.join(('def f_' + str(i) + '():\n    return None\n').encode() for i in range(256))
        with self.assertRaises(ValueError):
            U.failure_positions(error, pinned | {'runner': dict(fixed, raw=raw, sha256=E.sha(raw))})

    def test_command_redaction_and_owned_native_telemetry_faults_preserve_original_call(self):
        for output, kind in ((None, 'unobserved'), ('', 'empty'), (' %.y\n', 'yes'),
                             ('%.n', 'no'), ('%release-test', 'release-desk'),
                             ('0xdead.beef', 'hex-atom'), (SECRET, 'other')):
            row = U.command_observation(SECRET, output)
            self.assertEqual(set(row), {'source_sha256', 'source_bytes', 'completed',
                                       'output_sha256', 'output_bytes', 'output_kind'})
            self.assertEqual(row['source_sha256'], E.sha(SECRET.encode()))
            self.assertEqual(row['output_kind'], kind)
            self.assertIs(row['completed'], output is not None)
            self.assertEqual(row['output_sha256'], None if output is None else E.sha(output.encode()))
            self.assertNotIn(SECRET.encode(), E.canonical(row))
        for source, output in (('', None), ('x' * 65537, None), ('x', b'raw'), ('x', 'x' * 1000001)):
            with self.assertRaises(ValueError):
                U.command_observation(source, output)
        events = []
        original = ValueError(SECRET)
        class Base:
            def __init__(self, *_):
                self.commands = []
                self.failure = False
            def dojo(self, source, timeout):
                events.append(('dojo', timeout))
                if self.failure:
                    raise original
                self.commands.append({'source': source, 'output': SECRET})
                return SECRET
            def check(self):
                events.append(('check',))
        Native = U.native_class(types.SimpleNamespace(ReleaseNative=Base))
        for break_diagnostic in (False, True):
            native = Native(lambda: None)
            with ExitStack() as stack:
                if break_diagnostic:
                    stack.enter_context(mock.patch.object(U, 'command_observation', side_effect=RuntimeError('diagnostic only')))
                self.assertEqual(native.dojo(SECRET, timeout=180), SECRET)
                self.assertEqual(events[-2:], [('dojo', 60), ('check',)])
                self.assertEqual(native.commands, [{'source_sha256': E.sha(SECRET.encode()),
                    'source_bytes': len(SECRET), 'output_sha256': E.sha(SECRET.encode()), 'output_bytes': len(SECRET)}])
                self.assertEqual(native.last_command, None if break_diagnostic else U.command_observation(SECRET, SECRET))
                native.failure = True
                self.assertIs(caught(lambda: native.dojo(SECRET)), original)
                self.assertEqual(len(native.commands), 1)
                if not break_diagnostic:
                    self.assertIs(native.last_command['completed'], False)

    def test_native_log_tail_is_stable_bounded_closed_projection(self):
        raw = (SECRET + '\n\x1b[31mnest-fail\x1b[0m\nunknown-error\n'
               '/lib/stead-home-ui-seed/hoon:<[1,234 8].[1,235 9]>\n'
               'prefix /lib/private/hoon:<[1 2].[3 4]>\n').encode()
        raw += b''.join(('/lib/fixed/hoon:<[' + str(i) + ' 2].[' + str(i) + ' 3]>\n').encode()
                        for i in range(1, 22))
        row = U.compiler_projection(raw)
        self.assertEqual(row['tags'], ['nest-fail'])
        self.assertEqual(len(row['locations']), 16)
        self.assertEqual(row['locations'][0], {'path': '/lib/stead-home-ui-seed/hoon',
            'line': 1234, 'column': 8, 'end_line': 1235, 'end_column': 9})
        self.assertEqual(row['tail_sha256'], E.sha(raw))
        self.assertNotIn(SECRET.encode(), E.canonical(row))
        self.assertNotIn(b'/lib/private', E.canonical(row))
        with self.assertRaises(ValueError): U.compiler_projection(b'x' * 65537)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'native.log'
            data = b'x' * 66000 + b'\nnest-fail\n'
            path.write_bytes(data)
            observed = U.log_observation(path)
            self.assertEqual(observed, {'bytes': len(data), **U.compiler_projection(data[-65536:])})
            actual = U.os.fstat
            calls = [0]
            def changed(fd):
                value = actual(fd); calls[0] += 1
                if calls[0] == 2:
                    names = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                             'st_size', 'st_mtime_ns', 'st_ctime_ns')
                    return types.SimpleNamespace(**{k: getattr(value, k) + (1 if k == 'st_mtime_ns' else 0) for k in names})
                return value
            with mock.patch.object(U.os, 'fstat', side_effect=changed):
                with self.assertRaises(ValueError): U.log_observation(path)

    def test_failure_frame_rejects_extra_text_boolean_aliases_and_unbounded_metadata(self):
        _, expected, inputs, context = F.synthetic()
        report = {'status': 'fail', 'error_class': 'ValueError', 'cleanup_error_class': 'none',
                  'phases': [], 'captures': {}, 'commands': [], 'cleanup': dict(R.CLEAN),
                  'diagnostic': diagnostic()}
        value = W.failure_projection(report)
        self.assertEqual(value['protocol'], 'stead.saved8-failure-observation/2')
        frame = R.failure(expected, 'runner-failed', value, cleanup=True)
        parsed, artifacts = R.decode(frame, expected, context_sha=E.sha(E.canonical(context)),
                                     desk_hashes=inputs['desk_hashes'], assets=inputs['assets'])
        self.assertEqual(parsed['report'], value)
        self.assertEqual(artifacts, {})
        self.assertEqual(parsed['status'], 'fail')
        mutations = (
            lambda d: d.update(raw_text=SECRET), lambda d: d.update(operation=SECRET),
            lambda d: d['last_command'].update(source_bytes=True),
            lambda d: d['last_command'].update(completed=1),
            lambda d: d['last_command'].update(output_bytes=1.0),
            lambda d: d['positions'].update(frames_inspected=True),
            lambda d: d['positions'].update(truncated=0),
            lambda d: d['positions']['locations'][0].update(line=True),
            lambda d: d['positions'].update(locations=[d['positions']['locations'][0]] * 17),
            lambda d: d['native_log'].update(bytes=True),
            lambda d: d['native_log'].update(tail_bytes=9),
            lambda d: d['native_log'].update(tags=[SECRET]),
            lambda d: d['native_log'].update(raw=SECRET),
        )
        for mutate in mutations:
            bad = deepcopy(value); mutate(bad['diagnostic'])
            with self.assertRaises(ValueError): R.failure(expected, 'runner-failed', bad, cleanup=True)
            # Worker telemetry refusal drops only the malformed observation;
            # the original native failure and cleanup facts remain exportable.
            broken = deepcopy(report); broken['diagnostic'] = bad['diagnostic']
            preserved = W.failure_projection(broken)
            self.assertEqual(preserved, dict(value, diagnostic=None))
            self.assertEqual(preserved['error_class'], 'ValueError')
            self.assertIs(preserved['native_reaped'], True)
        for field, bad_value in (('command_count', True), ('native_reaped', 1),
                                 ('protocol', 'stead.saved8-failure-observation/1')):
            bad = dict(value); bad[field] = bad_value
            with self.assertRaises(ValueError): R.failed_report(bad)
        self.assertNotIn(SECRET.encode(), frame)

    def test_actual_runner_failure_preserves_first_error_stage_command_and_cleanup_order(self):
        pinned = sources()
        raw_by_path = {str(Path(root) / name): pinned[label]['raw']
                       for label, (root, name) in U.DIAGNOSTIC_SOURCES.items()}
        source_files = {root: {} for root, _ in U.DIAGNOSTIC_SOURCES.values()}
        for label, (root, name) in U.DIAGNOSTIC_SOURCES.items():
            source_files[root][name] = pinned[label]['sha256']
        context = {'run_id': '1' * 32, 'controller_commit': '2' * 40,
                   'inputs_sha256': '3' * 64, 'driver_files': {'fixed': '4' * 64},
                   'source_files': source_files}
        old = {'app/stead-home.hoon': '5' * 64} | {'lib/fixed-' + str(i): '6' * 64 for i in range(115)}
        seed = old | U.SEED
        self.assertEqual((len(old), len(seed)), (116, 117))
        for fault in ('none', 'positions', 'log', 'cleanup'):
            with self.subTest(fault=fault), ExitStack() as stack:
                events = []
                native = types.SimpleNamespace(lock={'runtime': {'binary_sha256': U.RUNTIME},
                    'boot_artifact': {'sha256': U.PILL}, 'kernel': {'commit': U.KERNEL}},
                    commands=[], last_command=None, logpath=Path('/inert/native.log'))
                native.start = mock.Mock(return_value={'inert': True})
                native.install = mock.Mock(return_value=context['driver_files'])
                def wait(*_args, **_kwargs):
                    events.append('wait')
                    native.last_command = U.command_observation('inert-status', SECRET)
                    native.commands.append({k: v for k, v in native.last_command.items()
                                            if k not in ('completed', 'output_kind')})
                    raise ValueError(SECRET)
                def stop():
                    events.append('stop')
                    if fault == 'cleanup': raise RuntimeError('cleanup second error')
                    return dict(R.CLEAN)
                native.stop = mock.Mock(side_effect=stop)
                release = types.ModuleType('release_install')
                release.inventory = mock.Mock(return_value=seed)
                release.asset_delta = mock.Mock(return_value=([], []))
                release.install_desk = mock.Mock(return_value=seed)
                release.wait_agent = mock.Mock(side_effect=wait)
                policy = types.ModuleType('execution_policy')
                policy.read_json = mock.Mock(return_value=context)
                stack.enter_context(mock.patch.dict(sys.modules, {'release_install': release,
                    'execution_policy': policy, 'native_tls': types.ModuleType('native_tls'),
                    'team_conn': types.ModuleType('team_conn')}))
                stack.enter_context(mock.patch.dict(U.os.environ, {'STEAD_RELEASE_INSTALL_CHILD': '1'}))
                stack.enter_context(mock.patch.object(U, 'inputs', return_value=({}, old, {}, old)))
                stack.enter_context(mock.patch.object(U.Path, 'mkdir'))
                stack.enter_context(mock.patch.object(U.shutil, 'copyfile'))
                stack.enter_context(mock.patch.object(U, 'native_class', return_value=lambda guard: native))
                stack.enter_context(mock.patch.object(U, 'read_regular', side_effect=lambda path, bound: raw_by_path[str(path)]))
                stack.enter_context(mock.patch.object(U.time, 'monotonic', return_value=1.0))
                positions = stack.enter_context(mock.patch.object(U, 'failure_positions',
                    side_effect=RuntimeError('diagnostic second error') if fault == 'positions' else None,
                    wraps=None if fault == 'positions' else U.failure_positions))
                def read_log(path):
                    self.assertEqual(events[-1], 'stop')
                    events.append('log')
                    if fault == 'log': raise OSError('diagnostic log error')
                    return {'bytes': 10, **U.compiler_projection(b'nest-fail\n')}
                read = stack.enter_context(mock.patch.object(U, 'log_observation', side_effect=read_log))
                result = U.run(mock.Mock())
                self.assertEqual(result['status'], 'fail')
                self.assertEqual(result['error_class'], 'ValueError')
                self.assertEqual(result['cleanup_error_class'], 'cleanup-refusal' if fault == 'cleanup' else 'none')
                self.assertEqual(result['phases'], [])
                self.assertEqual(result['captures'], {})
                self.assertEqual(result['diagnostic']['operation'], 'seed-ready')
                self.assertEqual(result['diagnostic']['last_command'], native.last_command)
                release.wait_agent.assert_called_once_with(native, 'stead-home', True, timeout=300)
                native.stop.assert_called_once_with()
                if fault == 'cleanup': read.assert_not_called()
                else: read.assert_called_once_with(native.logpath)
                if fault == 'positions': self.assertIsNone(result['diagnostic']['positions'])
                else:
                    # This host imports from its pinned input directory, not
                    # actual /ci mounts. The real locator therefore correctly
                    # excludes that filename while inspecting the real error.
                    self.assertGreater(result['diagnostic']['positions']['frames_inspected'], 0)
                    self.assertEqual(result['diagnostic']['positions']['source_sha256'],
                                     {k: v['sha256'] for k, v in pinned.items()})
                positions.assert_called_once()
                self.assertIs(type(positions.call_args.args[0]), ValueError)
                self.assertEqual({v['filename'] for v in positions.call_args.args[1].values()}, set(raw_by_path))
                if fault in ('log', 'cleanup'): self.assertIsNone(result['diagnostic']['native_log'])
                self.assertNotIn(SECRET.encode(), E.canonical(result))
                R.failed_report(W.failure_projection(result))

    def test_success_frame_remains_closed_and_diagnostics_never_promote_a_verdict(self):
        value, expected, inputs, context = F.synthetic()
        kwargs = {'context_sha': E.sha(E.canonical(context)),
                  'desk_hashes': inputs['desk_hashes'], 'assets': inputs['assets']}
        accepted, files = R.decode(R.encode(value), expected, **kwargs)
        self.assertEqual(accepted, value)
        self.assertEqual(len(files), 10)
        self.assertNotIn('diagnostic', accepted['report'])
        extra = deepcopy(value); extra['report']['diagnostic'] = diagnostic()
        with self.assertRaises(ValueError): R.decode(R.encode(extra), expected, **kwargs)
        self.assertEqual(tuple(U.OPERATIONS), tuple(R.DIAGNOSTIC_OPERATIONS))
        self.assertEqual(tuple(U.COMPILER_TAGS), tuple(R.DIAGNOSTIC_TAGS))
        observed = {'status': 'fail', 'error_class': 'ValueError', 'cleanup_error_class': 'none',
                    'phases': [], 'captures': {}, 'commands': [], 'cleanup': dict(R.CLEAN),
                    'diagnostic': diagnostic()}
        row = W.failure_projection(observed)
        frame = R.failure(expected, 'runner-failed', row, cleanup=True)
        denied, files = R.decode(frame, expected, **kwargs)
        self.assertEqual((denied['status'], files), ('fail', {}))
        # A complete diagnostic, clean child and empty failure tang do not turn
        # a runner failure into an accepted success frame.
        denied['status'] = 'pass'; denied['error_class'] = 'none'
        with self.assertRaises(ValueError): R.decode(R.encode(denied), expected, **kwargs)

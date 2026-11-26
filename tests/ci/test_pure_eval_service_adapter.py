"""Six authored outer-adapter cases for bounded inert host execution only.

The actual adapter runs with fixed privilege/process/network/signal doubles.
Only tiny owned files and readonly source fixtures are real. These cases do not
prove namespace isolation, evaluator completion, native suites or model work.
"""
from contextlib import ExitStack
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    'stage_codec.py': '02d1291d10eed589612a83d5dfb365e53abef7adc88a4487674e9dd69e3e914e',
    'service_adapter.py': '833c7328d49c2bad34ef203c0e7e25e681ffc25961f5d8887225a2b7c3eb0c54',
    'owner_boundary.py': '67a761095b51ec253cae57ee3df66ff29539d07cfa14593e2ce00806c3dcd554',
    'codec.py': '2d1d3c9fba170e15add8458988caa92ecde8eea252ae1dd77f7fa64efdc3bc9f',
}


def load_fixed(name):
    path = ROOT / 'scripts/ci/pure_eval' / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != PINS[name]:
        raise ValueError('Exact pure adapter source required')
    spec = importlib.util.spec_from_file_location('pure_outer_host_' + name[:-3], path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


adapter = load_fixed('service_adapter.py')
boundary_source = load_fixed('owner_boundary.py')
with patch.dict(sys.modules, {'stage_codec': load_fixed('stage_codec.py')}):
    codec_source = load_fixed('codec.py')


class Stream:
    def __init__(self, events, label, fail=False):
        self.events, self.label, self.fail, self.closed = events, label, fail, False

    def close(self):
        self.events.append(self.label)
        self.closed = True
        if self.fail:
            raise BrokenPipeError('inert stream failure')


def guard_for(raw, status='fail'):
    report_pin = adapter.pin(raw)
    return {
        'protocol': 'stead.fixed-pure-eval-guard/1', 'status': status,
        'error_class': 'none', 'cleanup_error_class': 'none',
        'parent_admitted': True, 'owned_children_empty': True,
        'child_streams_eof': True, 'adapter_owned_cleanup': True,
        'qualifies_phase': False, 'report_pin': report_pin,
        'worker_result': {'status': status, 'report': copy.deepcopy(report_pin)},
        'worker_exit_code': 0 if status == 'pass' else 1,
    }


class PureEvalServiceAdapterTests(unittest.TestCase):
    def test_fixed_source_map_requires_captured_pins_and_never_ambient_fallback(self):
        fixtures = ROOT / 'fixtures/pure-eval'
        composition = (fixtures / 'composition.json').read_bytes()
        captured = {adapter.DATA_PREFIX + 'composition.json': composition}
        for logical, path in adapter.FIXED_SOURCE_PATHS.items():
            captured[path] = (fixtures / logical).read_bytes()
        hosted = SimpleNamespace(CONTROLLER_FILES=captured)
        files, jobs, hashes = adapter.fixed_data(hosted, codec_source)
        self.assertEqual(len(files), 55)
        self.assertEqual(tuple(job['label'] for job in jobs),
                         ('compiler-control', 'failing-tang-control', 'catalog', 'import', 'authority', 'store'))
        self.assertEqual(hashes, {name: adapter.sha(raw) for name, raw in files.items()})
        reused = [name for name, path in adapter.FIXED_SOURCE_PATHS.items() if name == path]
        private = [name for name, path in adapter.FIXED_SOURCE_PATHS.items() if name != path]
        self.assertEqual((len(reused), len(private)), (46, 9))
        for logical in (reused[0], private[0], 'pkg/base-dev/lib/test.hoon'):
            path = adapter.FIXED_SOURCE_PATHS[logical]
            for mode in ('missing', 'changed', 'text'):
                changed = dict(captured)
                if mode == 'missing':
                    changed.pop(path)
                elif mode == 'changed':
                    changed[path] += b'\n'
                else:
                    changed[path] = changed[path].decode()
                sink = SimpleNamespace(profile=codec_source.profile, jobs=Mock())
                with self.subTest(logical=logical, mode=mode), self.assertRaises((ValueError, KeyError)):
                    adapter.fixed_data(SimpleNamespace(CONTROLLER_FILES=changed), sink)
                sink.jobs.assert_not_called()
        # A byte-correct ambient copy must not substitute for the declared private path.
        logical = private[0]
        changed = dict(captured)
        changed[logical] = changed.pop(adapter.FIXED_SOURCE_PATHS[logical])
        with self.assertRaises(ValueError):
            adapter.fixed_data(SimpleNamespace(CONTROLLER_FILES=changed), codec_source)
        for changed in ({**captured, adapter.DATA_PREFIX + 'unexpected.hoon': b'0'},
                        {**captured, adapter.DATA_PREFIX + 'composition.json': composition + b'\n'}):
            with self.assertRaises(ValueError):
                adapter.fixed_data(SimpleNamespace(CONTROLLER_FILES=changed), codec_source)

    def test_namespace_prefix_and_service_argv_remain_fixed(self):
        job = Path('/var/lib/stead-pure-eval-proof-1234abcd')
        context = {'host_gid': 1000, 'sources': {name: {} for name in boundary_source.SOURCE_NAMES},
                   'bwrap_sha256': hashlib.sha256(b'fixed-bwrap').hexdigest()}
        def entries(path):
            if path == job / 'lease':
                return iter([path / 'guardian.json'])
            if path == job / 'input':
                return iter(path / name for name in sorted(boundary_source.SOURCE_NAMES | {'owner.json'}))
            raise AssertionError('Unexpected inert directory')
        directories = Mock()
        with ExitStack() as stack:
            stack.enter_context(patch.object(boundary_source, 'directory', directories))
            stack.enter_context(patch.object(boundary_source, 'read_file', return_value=b'fixed-bwrap'))
            stack.enter_context(patch.object(Path, 'iterdir', entries))
            stack.enter_context(patch.object(Path, 'is_dir', return_value=True))
            stack.enter_context(patch.object(Path, 'is_symlink', return_value=False))
            argv = boundary_source.namespace_command(job, context)
            self.assertEqual(argv[-5:], ['--', '/usr/bin/python3', '-I', '-B', '/input/worker.py'])
            self.assertIn(str(job / 'sources'), argv)
            self.assertIn('--unshare-all', argv)
            for wrong in ('/var/lib/stead-model-proof-1234abcd', str(job) + '/child',
                          '/var/lib/stead-pure-eval-proof-1234567', '/tmp/stead-pure-eval-proof-1234abcd'):
                directories.reset_mock()
                with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                    boundary_source.namespace_command(Path(wrong), context)
                directories.assert_not_called()
        unit = 'stead-pure-eval-' + 'a' * 32 + '.service'
        hosted = SimpleNamespace(__file__='/fixed/hosted.py')
        collection = SimpleNamespace(service_properties=Mock(return_value={'CPUQuota': '100%'}))
        command = adapter.service_command(hosted, collection, job, {'unit': unit, 'cpu': 1})
        self.assertEqual(command[-6:], ['/usr/bin/python3', '-I', '-B', '/fixed/hosted.py', '_pure_guardian', str(job)])
        self.assertEqual(command[5], '--unit=' + unit)
        for wrong in (unit + '\n--no-block', 'stead-model-' + 'a' * 32 + '.service', '--unit=other'):
            with self.assertRaises(ValueError):
                adapter.service_command(hosted, collection, job, {'unit': wrong, 'cpu': 1})

    def test_checked_report_refuses_conflicting_guard_before_file_read(self):
        raw = b'{"status":"fail","synthetic":"original retained report"}'
        guard = guard_for(raw)
        with tempfile.TemporaryDirectory() as temporary:
            job = Path(temporary)
            retained = job / 'retained'
            retained.mkdir()
            (retained / 'report.json').write_bytes(raw)
            boundary = SimpleNamespace(directory=Mock(), read_file=Mock(return_value=raw))
            collection = SimpleNamespace(validate_report=Mock(return_value={'status': 'fail'}))
            variants = []
            for key in ('parent_admitted', 'owned_children_empty', 'child_streams_eof', 'adapter_owned_cleanup'):
                for value in (False, 1):
                    row = copy.deepcopy(guard); row[key] = value; variants.append(row)
            for key, value in [('worker_exit_code', True), ('worker_exit_code', 1.0),
                               ('worker_exit_code', '1'), ('worker_exit_code', 0),
                               ('error_class', 'ValueError'), ('cleanup_error_class', 'OSError'),
                               ('qualifies_phase', True), ('status', 'unknown')]:
                row = copy.deepcopy(guard); row[key] = value; variants.append(row)
            row = copy.deepcopy(guard); row['worker_result']['report']['sha256'] = '0' * 64; variants.append(row)
            for value in (True, 0, adapter.REPORT_LIMIT + 1):
                row = copy.deepcopy(guard)
                row['report_pin']['bytes'] = value
                row['worker_result']['report'] = copy.deepcopy(row['report_pin'])
                variants.append(row)
            row = copy.deepcopy(guard); del row['parent_admitted']; variants.append(row)
            # This path now reads the original admitted profile from guardian input.
            # The synthetic fixture owns that read; actual root-file custody is separate.
            context = {'boundary': {'sources': {'composition.json':
                       {'sha256': adapter.REPOSITORY_COMPOSITION}}}}
            with patch.object(adapter, 'fixed_data', return_value=({}, ('fixed-job',), {})), \
                    patch.object(adapter, 'job_context', return_value=context):
                self.assertEqual(adapter.checked_report(None, boundary, collection, None, job, guard), raw)
                for row in variants:
                    boundary.directory.reset_mock(); boundary.read_file.reset_mock()
                    collection.validate_report.reset_mock()
                    with self.subTest(row=row), self.assertRaises((ValueError, KeyError)):
                        adapter.checked_report(None, boundary, collection, None, job, row)
                    boundary.directory.assert_not_called()
                    boundary.read_file.assert_not_called()
                    collection.validate_report.assert_not_called()
                with patch.object(collection, 'validate_report', return_value={'status': 'pass'}):
                    with self.assertRaises(ValueError):
                        adapter.checked_report(None, boundary, collection, None, job, guard)

    def test_guardian_closes_precollector_and_cleanup_failures_before_retention(self):
        for mode in ('collector-error', 'cleanup-error', 'stderr-close-error', 'clean-failed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                job = Path(temporary)
                group = job / 'group'; group.mkdir()
                (group / 'cgroup.procs').write_text(str(os.getpid()) + '\n')
                events, writes = [], {}
                raw = b'{"status":"fail","synthetic":"complete failed evaluator"}'
                guard = guard_for(raw)
                process = SimpleNamespace(stdin=Stream(events, 'stdin'), stdout=Stream(events, 'stdout'),
                    stderr=Stream(events, 'stderr', fail=mode == 'stderr-close-error'))
                def collect(*args, **kwargs):
                    events.append('collect')
                    if mode == 'collector-error':
                        raise ValueError('inert precollector failure')
                    return copy.deepcopy(guard), raw
                def cleanup(*args):
                    events.append('cleanup')
                    if mode == 'cleanup-error':
                        raise OSError('inert cleanup failure')
                    return True
                boundary = SimpleNamespace(group=Mock(return_value=group))
                collection = SimpleNamespace(service_current=Mock(), run=collect, cleanup=cleanup)
                def write(path, value, **kwargs):
                    events.append('write:' + path.name); writes[path.name] = value
                with ExitStack() as stack:
                    stack.enter_context(patch.object(adapter, 'load', return_value={
                        'owner_boundary': boundary, 'owner_collection': collection, 'codec': object()}))
                    # Bind the fixed repository selection required before collector setup.
                    context = {'boundary': {'sources': {'composition.json':
                               {'sha256': adapter.REPOSITORY_COMPOSITION}}}, 'owner': {}}
                    stack.enter_context(patch.object(adapter, 'job_context', return_value=context))
                    stack.enter_context(patch.object(adapter, 'fixed_data', return_value=({}, (), {})))
                    stack.enter_context(patch.object(adapter, 'heartbeat_factory', return_value=(lambda: None, 987)))
                    stack.enter_context(patch.object(adapter.subprocess, 'Popen', return_value=process))
                    close = stack.enter_context(patch.object(adapter.os, 'close'))
                    stack.enter_context(patch.object(adapter, 'write_new', side_effect=write))
                    hosted = SimpleNamespace(__file__='/fixed/hosted.py', CAPTURED=ROOT,
                        CONTROLLER_FILES={adapter.PREFIX + name: (ROOT / adapter.PREFIX / name).read_bytes()
                            for name in ('owner_collection.py', 'owner_boundary.py', 'service_adapter.py')})
                    result = adapter.guardian(hosted, job)
                self.assertEqual(result, 1)
                self.assertTrue(all(stream.closed for stream in (process.stdin, process.stdout, process.stderr)))
                close.assert_called_once_with(987)
                report = json.loads(writes['pure-guard.json'])
                self.assertEqual(report['status'], 'fail')
                self.assertLess(events.index('cleanup'), events.index('write:pure-guard.json'))
                if mode == 'clean-failed':
                    self.assertEqual(writes['report.json'], raw)
                    self.assertLess(events.index('stderr'), events.index('write:report.json'))
                    self.assertTrue(report['adapter_owned_cleanup'])
                else:
                    self.assertEqual(set(writes), {'pure-guard.json'})

    def exercise_outer(self, mode):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events, writes, holder = [], {}, {}
            original = b'{"status":"fail","synthetic":"original failed rows","text":"LF\\nemoji\\ud83c\\udf31"}'
            guard = guard_for(original)
            fixed_path = Path
            def mapped_path(value):
                if str(value).startswith('/var/lib/stead-pure-eval-proof-'):
                    return root / fixed_path(value).name
                if str(value) == '/sys/fs/cgroup/system.slice':
                    return root / 'absent-cgroup'
                return fixed_path(value)
            def prepare(job, check):
                check(); events.append('intake')
                if mode == 'intake-error':
                    raise ValueError('inert intake refusal')
                job.mkdir(mode=0o700); holder['job'] = job
                return {'runtime': {'synthetic': 'inert exact runtime'}}
            def read_file(path, maximum, expected=None):
                if str(path) == '/usr/bin/bwrap':
                    return b'fixed-bwrap'
                raw = path.read_bytes()
                self.assertLessEqual(len(raw), maximum)
                if expected is not None:
                    self.assertEqual(adapter.pin(raw), expected)
                return raw
            boundary = SimpleNamespace(proc_identity=lambda pid: (pid, 42), context=Mock(),
                read_file=read_file, directory=Mock(), NAMESPACES=('pid', 'user'))
            collection = SimpleNamespace(service_properties=Mock(return_value={'CPUQuota': '100%'}),
                validate_report=Mock(return_value={'status': 'fail'}))
            def wait(timeout):
                self.assertEqual(timeout, 5); events.append('caller-reap')
                if mode == 'reap-error':
                    raise TimeoutError('inert unreaped caller')
                return 1
            process = SimpleNamespace(returncode=1, poll=Mock(return_value=1),
                stdin=Stream(events, 'caller-pipe'), wait=Mock(side_effect=wait),
                kill=Mock(side_effect=lambda: events.append('caller-kill')))
            def spawn(command):
                self.assertEqual(command[0], '/usr/bin/systemd-run')
                events.append('spawn')
                job = holder['job']
                (job / 'pure-guard.json').write_bytes(adapter.canonical(guard))
                retained = job / 'retained'; retained.mkdir(mode=0o700)
                (retained / 'report.json').write_bytes(original)
                return process
            reads = 0
            def readback(unit):
                nonlocal reads
                self.assertRegex(unit, '^stead-pure-eval-[0-9a-f]{32}\\.service$')
                reads += 1
                if mode != 'intake-error' and (reads == 1 or mode == 'cleanup-error'):
                    events.append('unit-active'); return {'ActiveState': 'active'}
                events.append('unit-inactive'); return {'ActiveState': 'failed'}
            sources = {path: b'fixed captured source' for path in adapter.SOURCE_PATHS.values()}
            sources[adapter.SOURCE_PATHS['composition.json']] = (ROOT / 'fixtures/pure-eval/composition.json').read_bytes()
            hosted = SimpleNamespace(ROOT=root, __file__='/fixed/hosted.py', CONTROLLER_FILES=sources,
                regular_root=Mock(), hosted_apparmor=SimpleNamespace(prepare=Mock(return_value={})),
                spawn_owned=Mock(side_effect=spawn), readback=Mock(side_effect=readback))
            args = SimpleNamespace(mode='pure', control=None, candidate='a' * 40,
                controller='a' * 40, workflow='b' * 40)
            def command(argv, **kwargs):
                if argv == ['/usr/bin/bwrap', '--version']:
                    return SimpleNamespace(stdout=b'bubblewrap 0.9.0\n')
                self.assertEqual(argv[:2], ['/usr/bin/systemctl', 'stop'])
                events.append('unit-stop'); return SimpleNamespace(stdout=b'')
            def write(path, raw, **kwargs):
                if path.parent == root / 'pure-evidence':
                    events.append('export:' + path.name); writes[path.name] = raw
                # Model root's write to this owned synthetic 0550 input only.
                # The host test UID stays unprivileged; exact mode is restored.
                if path.parent == holder.get('job', root) / 'input':
                    info = path.parent.lstat()
                    self.assertEqual((info.st_uid, stat.S_IMODE(info.st_mode)), (os.getuid(), 0o550))
                    try:
                        os.chmod(path.parent, 0o750); path.write_bytes(raw)
                    finally:
                        os.chmod(path.parent, 0o550)
                    self.assertEqual(stat.S_IMODE(path.parent.lstat().st_mode), 0o550)
                else:
                    path.write_bytes(raw)
            actual_check = adapter.checked_report
            def checked(*args):
                events.append('checked-report')
                self.assertIn('unit-inactive', events)
                self.assertIn('caller-reap', events)
                return actual_check(*args)
            modules = {'owner_boundary': boundary, 'owner_collection': collection,
                       'pure_intake': SimpleNamespace(prepare=prepare),
                       'codec': SimpleNamespace(profile=codec_source.profile)}
            with ExitStack() as stack:
                stack.enter_context(patch.object(adapter, 'load', return_value=modules))
                stack.enter_context(patch.object(adapter, 'fixed_data', return_value=({'fixed.hoon': b'0'}, ('job',), {})))
                # No Git/current-host action: the mocked outer wrote this exact
                # synthetic root-owned context; real context custody is separate.
                stack.enter_context(patch.object(adapter, 'job_context', side_effect=lambda _hosted, _boundary, job: json.loads((job / 'guardian.json').read_bytes())))
                stack.enter_context(patch.object(adapter, 'Path', side_effect=mapped_path))
                stack.enter_context(patch.object(adapter.os, 'geteuid', return_value=0))
                stack.enter_context(patch.object(adapter.os, 'sched_getaffinity', return_value={0}))
                stack.enter_context(patch.object(adapter.os, 'chown'))
                stack.enter_context(patch.object(adapter.os, 'readlink', return_value='inert-namespace'))
                stack.enter_context(patch.object(adapter.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=1000, pw_gid=1000)))
                stack.enter_context(patch.object(adapter.subprocess, 'run', side_effect=command))
                stack.enter_context(patch.object(adapter.signal, 'signal'))
                stack.enter_context(patch.object(adapter.signal, 'setitimer'))
                stack.enter_context(patch.object(adapter, 'lease_publish', side_effect=lambda *a: events.append('inert-lease')))
                stack.enter_context(patch.object(adapter, 'write_new', side_effect=write))
                checked_mock = stack.enter_context(patch.object(adapter, 'checked_report', side_effect=checked))
                if mode == 'budget-error':
                    # Gate arithmetic is exercised with tiny bytes, not a >4MiB allocation.
                    stack.enter_context(patch.object(adapter, 'REPORT_LIMIT', len(original)))
                result = adapter.outer(hosted, args, {'workflow_sha': args.workflow},
                                       {'controller_commit': args.controller})
            self.assertEqual(result, 1)
            report = json.loads(writes['owner-report.json'])
            self.assertEqual(report['status'], 'fail')
            self.assertFalse(report['qualifies_phase'] or report['native_application_executed'])
            if mode == 'intake-error':
                hosted.spawn_owned.assert_not_called()
            else:
                hosted.spawn_owned.assert_called_once()
                self.assertTrue(process.stdin.closed)
                self.assertEqual(report['service_exit_code'], 1)
            return report, writes, events, original, checked_mock.call_count

    def test_intake_refusal_never_launches_or_exports_evaluator_report(self):
        report, writes, events, original, calls = self.exercise_outer('intake-error')
        self.assertEqual(set(writes), {'owner-report.json'})
        self.assertEqual(calls, 0)
        self.assertEqual(report['error_class'], 'ValueError')
        self.assertTrue(report['cleanup']['verified'])
        self.assertFalse(report['cleanup']['service_started'])

    def test_completed_failed_report_export_requires_cleanup_reap_and_budget(self):
        for mode in ('clean', 'cleanup-error', 'reap-error', 'budget-error'):
            with self.subTest(mode=mode):
                report, writes, events, original, calls = self.exercise_outer(mode)
                self.assertEqual(report['guard']['status'], 'fail')
                if mode == 'clean':
                    self.assertEqual(calls, 1)
                    self.assertEqual(set(writes), {'report.json', 'owner-report.json'})
                    self.assertEqual(writes['report.json'], original)
                    self.assertEqual(report['report_pin'], adapter.pin(original))
                    self.assertEqual(report['report_export'], 'collected')
                    self.assertLess(events.index('unit-stop'), events.index('unit-inactive'))
                    self.assertLess(events.index('unit-inactive'), events.index('caller-reap'))
                    self.assertLess(events.index('caller-reap'), events.index('checked-report'))
                    self.assertLess(events.index('checked-report'), events.index('export:report.json'))
                else:
                    self.assertEqual(set(writes), {'owner-report.json'})
                    self.assertNotEqual(report['report_export'], 'collected')
                    if mode == 'budget-error':
                        self.assertEqual(calls, 1)
                        self.assertEqual(report['report_export'], 'refused')
                    else:
                        self.assertEqual(calls, 0)
                        self.assertEqual(report['cleanup_error_class'],
                                         'service-cleanup' if mode == 'cleanup-error' else 'caller-reap')

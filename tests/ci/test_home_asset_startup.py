"""Three inert startup regressions; no namespace, process or native execution.

The real owner writes tiny temporary JSON files through the real hosted writer.
Privilege metadata, process launch, kernel state and custody are explicit doubles.
Worker parsing and byte predicates are real; admission stops before namespace or
network access. These cases do not prove real hosted boot or native rehearsal.
"""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


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


F = load('saved8_startup_fixture', Path(__file__).with_name('test_home_asset_outer.py'))
H = load('saved8_startup_hosted', ROOT / 'scripts/ci/hosted.py')
A, E, W, P = F.A, F.E, F.W, F.P


class ReachedBoundary(Exception):
    pass


def values():
    value = {
        'protocol': 'stead.saved8-hosted-inputs/1', 'profile': 'home-assets-saved8/1',
        'run_id': '1' * 32, 'controller_commit': '2' * 40,
        'candidate_commit': F.R.BASE, 'backend_commit': F.R.BASE, 'target_commit': F.R.TARGET,
        'workflow_binding': {}, 'controller_files': {}, 'owner_uid': 999, 'owner_gid': 987,
        'host_namespaces': {name: name + ':[123]' for name in ('net', 'pid', 'mnt', 'user')},
        'source_files': {path: dict.fromkeys(names, '3' * 64) for path, names in W.SOURCE_NAMES.items()},
        'guardian_files': dict.fromkeys(W.GUARDIAN_NAMES, '4' * 64),
        'driver_files': {}, 'seed_files': {}, 'runtime_sha256': F.R.RUNTIME,
        'pill_sha256': '5' * 64, 'kernel_commit': F.R.KERNEL,
        'kernel_tree_sha256': '6' * 64, 'toolchain_sha256': '7' * 64,
        'archives': {}, 'assets': {}, 'desk_hashes': {},
    }
    context = {'protocol': 'stead.saved8-rehearsal-context/1',
        **{key: value[key] for key in ('run_id', 'controller_commit', 'host_namespaces',
            'driver_files', 'source_files', 'runtime_sha256', 'pill_sha256', 'kernel_commit')},
        'inputs_sha256': E.sha(E.canonical(value))}
    return value, context


class Saved8StartupTests(unittest.TestCase):
    def test_captured_saved8_command_precedes_drop_without_broadening_generic_child(self):
        for profile in ('home-assets-saved8/1', None):
            with self.subTest(profile=profile), ExitStack() as stack:
                events, uid = [], [0]
                context = {'uid': 999, 'gid': 987, 'fixed_profile': profile}
                command = ['/usr/bin/bwrap', '--fixed-inert-test-only']
                def build(job, observed):
                    self.assertEqual(observed, context)
                    # A root-only bootstrap tree is inaccessible after the drop.
                    if profile == 'home-assets-saved8/1' and uid[0] != 0:
                        raise PermissionError('inert captured-tree refusal')
                    events.append(('command', uid[0]))
                    return command
                def drop(value):
                    uid[0] = value
                    events.append(('uid', value))
                def prctl(*args):
                    events.append(('prctl', args[0], uid[0]))
                    return 0
                def execute(path, argv):
                    self.assertEqual((path, argv), (command[0], command))
                    events.append(('exec', uid[0]))
                    raise ReachedBoundary()
                stack.enter_context(mock.patch.object(H, 'regular_root'))
                stack.enter_context(mock.patch.object(H, 'execution_policy',
                    types.SimpleNamespace(read_json=mock.Mock(return_value=context)), create=True))
                stack.enter_context(mock.patch.object(H, 'sandbox_command', side_effect=build))
                stack.enter_context(mock.patch.object(H.os, 'getuid', side_effect=lambda: uid[0]))
                stack.enter_context(mock.patch.object(H.os, 'getppid', return_value=123))
                stack.enter_context(mock.patch.object(H.os, 'setgroups', side_effect=lambda value: events.append(('groups', value))))
                stack.enter_context(mock.patch.object(H.os, 'setgid', side_effect=lambda value: events.append(('gid', value))))
                stack.enter_context(mock.patch.object(H.os, 'setuid', side_effect=drop))
                stack.enter_context(mock.patch.object(H.ctypes, 'CDLL', return_value=types.SimpleNamespace(prctl=prctl)))
                stack.enter_context(mock.patch.object(H, 'hosted_apparmor',
                    types.SimpleNamespace(require_label=lambda: events.append(('label', uid[0]))), create=True))
                stack.enter_context(mock.patch.object(H.os, 'execv', side_effect=execute))
                stack.enter_context(mock.patch.dict(H.os.environ, {}, clear=True))
                with self.assertRaises(ReachedBoundary):
                    H.child(Path('/inert/job'), 123)
                self.assertEqual(events.count(('command', 0 if profile else 999)), 1)
                self.assertEqual(events[-1], ('exec', 999))
                self.assertIn(('groups', []), events)
                self.assertIn(('gid', 987), events)
                self.assertLess(events.index(('uid', 999)), events.index(('prctl', 1, 999)))
                self.assertLess(events.index(('prctl', 1, 999)), events.index(('prctl', 38, 999)))
                self.assertLess(events.index(('prctl', 38, 999)), events.index(('label', 999)))
                if profile:
                    self.assertLess(events.index(('command', 0)), events.index(('groups', [])))
                else:
                    self.assertLess(events.index(('label', 999)), events.index(('command', 999)))

    def owner_bytes(self, folder):
        """Run actual outer through its writes; all privileged edges are inert."""
        value, context = values()
        root = Path(folder)
        job = root / 'job'; job.mkdir()
        account = types.SimpleNamespace(pw_uid=999, pw_gid=987)
        captured = {}
        def spawn(*_args, **_kwargs):
            captured['inputs'] = (job / 'inputs.json').read_bytes()
            captured['context'] = (job / 'control/home-asset-rehearsal.json').read_bytes()
            raise ReachedBoundary()
        fake_toolchain = types.ModuleType('toolchain')
        fake_toolchain.verify = mock.Mock(return_value={'inert': True})
        hosted = types.SimpleNamespace(ROOT=root, __file__=H.__file__, POLICY={'inert': True}, CONTROLLER_FILES={},
            hosted_apparmor=types.SimpleNamespace(prepare=mock.Mock(return_value={}),
                unrelated=mock.Mock(return_value={}), verify_probe=mock.Mock(return_value={})),
            regular_root=mock.Mock(), local=types.SimpleNamespace(materialize=mock.Mock()),
            write=H.write, share_tree=mock.Mock(), service_command=mock.Mock(return_value=['inert']),
            spawn_owned=mock.Mock(side_effect=spawn), readback=mock.Mock(return_value={'ActiveState': 'inactive'}))
        with ExitStack() as stack:
            stack.enter_context(mock.patch.dict(sys.modules, {'toolchain': fake_toolchain}))
            stack.enter_context(mock.patch.object(H, 'execution_policy', P, create=True))
            stack.enter_context(mock.patch.object(H, 'canonical', E.canonical, create=True))
            stack.enter_context(mock.patch.object(A.os, 'geteuid', return_value=0))
            stack.enter_context(mock.patch.object(A.os, 'sched_getaffinity', return_value={0, 1}))
            stack.enter_context(mock.patch.object(A.os, 'chown'))
            stack.enter_context(mock.patch.object(H.os, 'fchown'))
            stack.enter_context(mock.patch.object(A.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)))
            stack.enter_context(mock.patch.object(A.pwd, 'getpwnam', return_value=account))
            stack.enter_context(mock.patch.object(A.tempfile, 'mkdtemp', return_value=str(job)))
            stack.enter_context(mock.patch.object(A, 'intake', return_value=(value, context)))
            stack.enter_context(mock.patch.object(A, 'collected', side_effect=ValueError('inert stop before native')))
            publish = stack.enter_context(mock.patch.object(A, 'publish', return_value='fail'))
            stack.enter_context(mock.patch('builtins.print'))
            args = types.SimpleNamespace(mode='home-assets-saved8', control=None, candidate='2' * 40, controller='2' * 40)
            self.assertEqual(A.outer(hosted, args, {}, {}), 1)
            hosted.spawn_owned.assert_called_once()
            self.assertEqual(publish.call_args.args[1]['status'], 'fail')
            self.assertEqual(publish.call_args.args[3], {})
        self.assertEqual(set(captured), {'inputs', 'context'})
        return value, context, captured

    def reach_context_boundary(self, captured):
        mapped = mock.Mock()
        source = mock.Mock()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(W, 'sys', types.SimpleNamespace(
                flags=types.SimpleNamespace(isolated=1), dont_write_bytecode=True, argv=['worker.py'])))
            for name in ('getuid', 'geteuid', 'getgid', 'getegid'):
                stack.enter_context(mock.patch.object(W.os, name, return_value=0))
            stack.enter_context(mock.patch.object(W.os, 'getgroups', return_value=[]))
            stack.enter_context(mock.patch.dict(W.os.environ,
                {'STEAD_RELEASE_INSTALL_CHILD': '1', 'STEAD_EXECUTION_ID': '1' * 32}))
            def regular(path, _maximum):
                self.assertIn(path, ('/inputs.json', '/execution/home-asset-rehearsal.json'))
                return captured['inputs' if path == '/inputs.json' else 'context']
            stack.enter_context(mock.patch.object(W, 'regular', side_effect=regular))
            stack.enter_context(mock.patch.object(W, 'mapped_owner', mapped))
            stack.enter_context(mock.patch.object(W, 'source_tree', source))
            boundary = stack.enter_context(mock.patch.object(W.os, 'readlink', side_effect=ReachedBoundary()))
            # Nothing beyond this exact post-context boundary may execute.
            network = stack.enter_context(mock.patch.object(W.socket, 'socket', side_effect=AssertionError('network reached')))
            process = stack.enter_context(mock.patch.object(W.subprocess, 'run', side_effect=AssertionError('process reached')))
            try:
                W.admission()
            finally:
                network.assert_not_called(); process.assert_not_called()
        return mapped, source, boundary

    def test_actual_owner_writer_reaches_strict_worker_context_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            value, context, captured = self.owner_bytes(folder)
        self.assertEqual(captured['inputs'], E.canonical(value) + b'\n')
        self.assertEqual(captured['context'], E.canonical(context) + b'\n')
        with self.assertRaises(ReachedBoundary):
            self.reach_context_boundary(captured)

    def test_spaced_truncated_and_duplicate_admission_bytes_still_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            value, context, captured = self.owner_bytes(folder)
            for field, object_value in (('inputs', value), ('context', context)):
                old = Path(folder) / (field + '-old.json')
                P.write_json(old, object_value)
                # Reproduce the real previous writer, not an invented JSON form.
                self.assertNotEqual(old.read_bytes(), captured[field])
                duplicate = b'{"protocol":"x",' + captured[field][1:]
                for raw in (old.read_bytes(), captured[field][:-1], duplicate):
                    with self.subTest(field=field, size=len(raw)), self.assertRaises(ValueError):
                        self.reach_context_boundary({**captured, field: raw})

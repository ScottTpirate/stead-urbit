"""Read-only pilot dependency assessment and fail-closed policy tests."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from execution_policy import GuardError
import pilot_host_preflight as host


class PilotHostPreflightTests(unittest.TestCase):
    def test_effective_cgroup_controls_and_nested_memory_headroom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc, mount = root / 'proc', root / 'cgroup'
            parent, child = mount / 'parent', mount / 'parent' / 'child'
            child.mkdir(parents=True)
            (proc / 'self').mkdir(parents=True)
            (proc / 'self/cgroup').write_text('0::/parent/child\n')
            (mount / 'cgroup.controllers').write_text('cpu io memory pids\n')
            (parent / 'memory.max').write_text('7500\n')
            (parent / 'memory.current').write_text('5500\n')
            (child / 'memory.max').write_text('8000\n')
            (child / 'memory.current').write_text('5000\n')
            for name, value in (('cpu.max', 'max 100000'), ('io.max', ''), ('pids.max', '128')):
                (child / name).write_text(value)
            report = host.cgroups(proc, mount)
            self.assertEqual((report['version'], report['status'], report['memory_headroom_bytes']), (2, 'ready', 2000))
            (child / 'io.max').unlink()
            report = host.cgroups(proc, mount)
            self.assertEqual(report['status'], 'controls-missing')
            self.assertEqual(report['controllers']['io'], {'advertised': True, 'readable': False})
            (proc / 'self/cgroup').write_text('0::/../../escape\n')
            self.assertEqual(host.cgroups(proc, mount)['status'], 'unavailable')

    def test_real_sandbox_function_only_runs_for_exact_account_and_advertised_switches(self):
        version = {'status': 'version-observed', 'version': '0.11.0'}
        switches = '\n'.join(f'  {flag} foo' for flag in host.BWRAP_FLAGS)
        with patch.object(host, '_command', return_value=switches), patch.object(host, 'sandbox_ready') as sandbox:
            self.assertEqual(host.bubblewrap(version, False)['status'], 'account-mismatch')
            sandbox.assert_not_called()
            self.assertEqual(host.bubblewrap(version, True)['actual_sandbox'], 'verified')
            sandbox.assert_called_once_with()
            sandbox.side_effect = GuardError('unavailable')
            report = host.bubblewrap(version, True)
            self.assertEqual((report['status'], report['actual_sandbox']), ('sandbox-rejected', 'rejected'))
        with patch.object(host, '_command', return_value=''), patch.object(host, 'sandbox_ready') as sandbox:
            self.assertEqual(host.bubblewrap(version, True)['status'], 'switches-missing')
            self.assertEqual(host.bubblewrap({'status': 'missing'}, True)['actual_sandbox'], 'not-run')
            sandbox.assert_not_called()

    def test_dependency_and_sensorless_guard_statuses_are_separate(self):
        group = {'status': 'ready', 'memory_headroom_bytes': 6000}
        sandbox = {'status': 'ready', 'actual_sandbox': 'verified'}
        disk = Mock(f_frsize=100, f_bavail=100)
        with patch.object(host, 'cgroups', return_value=group), patch.object(host, 'host_memory', return_value=8000), \
                patch.object(host.os, 'getuid', return_value=1234), patch.object(host.os, 'geteuid', return_value=1234), \
                patch.object(host.os, 'statvfs', return_value=disk), \
                patch.object(host, '_tool', side_effect=lambda name, _: {
                    'status': 'qualified-version' if name == 'git' else 'version-observed'}), \
                patch.object(host, 'bubblewrap', return_value=sandbox) as isolated, \
                patch.object(host, 'sample_temperatures', side_effect=GuardError('no sensors')):
            report = host.preflight('worker', 1234, Path('/'), Path('/usr/bin/git'), 1000, 8000)
            self.assertTrue(report['live_service_dependencies_ready'])
            self.assertFalse(report['local_guard_eligible'])
            self.assertFalse(report['native_admitted'])
            self.assertFalse(report['release_fencing_verified'])
            self.assertEqual(report['memory']['effective_available_bytes'], 6000)
            self.assertTrue(report['disk']['ready'])
            self.assertEqual(report['thermal']['status'], 'unavailable')
            isolated.assert_called_with({'status': 'version-observed'}, True)
            different = host.preflight('relay', 5678, Path('/'), Path('/usr/bin/git'), 7000, 11_000)
            self.assertFalse(different['live_service_dependencies_ready'])
            self.assertFalse(different['target_account_verified'])
            self.assertFalse(different['disk']['ready'])
            isolated.assert_called_with({'status': 'version-observed'}, False)

    def test_unknown_owner_git_executable_never_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'git'
            binary.write_bytes(b'#!/bin/sh\n')
            binary.chmod(0o700)
            with patch.object(host, '_command') as execute:
                self.assertEqual(host._tool('git', binary)['status'], 'unreviewed-executable-path')
                self.assertEqual(host._tool('git', Path(directory) / 'absent')['status'], 'missing')
                execute.assert_not_called()

    @unittest.skipUnless(os.path.exists('/usr/bin/git'), 'Host Git executable required')
    def test_records_unqualified_versions_without_claiming_support(self):
        binary = Path('/usr/bin/git')
        with patch.object(host, '_trusted', return_value=binary):
            with patch.object(host, '_command', return_value='git version 2.43.0'):
                self.assertEqual(host._tool('git', binary), {'status': 'version-unqualified', 'version': '2.43.0'})
            with patch.object(host, '_command', return_value='git version 2.55.0'):
                self.assertEqual(host._tool('git', binary), {'status': 'qualified-version', 'version': '2.55.0'})

"""Real host namespaces/UDP/process controls, not native Urbit acceptance."""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NativePeerFenceTests(unittest.TestCase):
    def execute(self, name, classification, count):
        command = ['bwrap', '--unshare-all', '--uid', '0', '--gid', '0',
                   '--cap-add', 'CAP_NET_ADMIN', '--cap-add', 'CAP_SETPCAP',
                   '--ro-bind', '/usr', '/usr']
        for entry in ('bin', 'sbin', 'lib', 'lib64'):
            path = Path('/') / entry
            if path.is_symlink():
                command += ['--symlink', os.readlink(path), str(path)]
            elif path.exists():
                command += ['--ro-bind', str(path), str(path)]
        command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                    '--ro-bind', str(ROOT / 'scripts/urbit'), '/code',
                    '--ro-bind', str(ROOT / 'tests/urbit/host_network'), '/probes',
                    '--chdir', '/probes', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
                    '--setenv', 'PYTHONPATH', '/code', '--', '/usr/bin/python3', '-B',
                    '/probes/' + name, *([os.readlink('/proc/self/ns/net')]
                                        if name in ('fence-exercise.py', 'fence-close-probe.py') else [])]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stderr, '')
        result = json.loads(completed.stdout)
        self.assertEqual(result['classification'], classification)
        self.assertEqual(len(result['checks']), count)
        if 'passed' in result:
            self.assertIs(result['passed'], True)
        else:
            self.assertTrue(all(row['passed'] is True for row in result['checks']))

    def test_actual_udp_admission_revocation_and_full_policy_failure(self):
        self.execute('fence-exercise.py', 'real-host-private-network-controls', 16)

    def test_inflight_nft_and_late_child_cannot_outlive_controller(self):
        self.execute('fence-death-probe.py', 'real-host-private-network-parent-death', 3)

    def test_long_lived_launcher_survives_request_thread(self):
        self.execute('launcher-exercise.py', 'real-host-child-lifetime-controls', 6)

    def test_failed_close_notifies_cleanup_and_restores_policy(self):
        self.execute('fence-close-probe.py', 'real-host-private-network-close-failure', 3)

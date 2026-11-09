"""Focused host-only process proof regressions; proc reads are mocked."""
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/sdk_native'), str(ROOT / 'scripts/urbit')]
import native


class NativeProofTests(unittest.TestCase):
    def proof(self, links, check=None):
        instance = native.Native.__new__(native.Native)
        instance.process = SimpleNamespace(pid=5)
        instance.port, instance.pier = 31337, Path('/state/zod')
        instance.check = check or Mock()
        status = '\n'.join(name + ': 0000000000000000' for name in ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd'))
        text = {'/proc/5/status': status + '\nNoNewPrivs: 1\nUid: 1000\nGid: 1000',
                '/proc/net/udp': 'header\n0: 0100007F:7A69 x x x x x x x 42\n',
                '/proc/5/uid_map': '1000 0 1', '/proc/5/gid_map': '1000 0 1',
                '/state/zod/.http.ports': '18080 loopback\n'}
        counts = {}
        def readlink(path):
            path = str(path)
            if '/ns/' in path:
                return 'namespace:' + path.rsplit('/', 1)[1]
            counts[path] = counts.get(path, 0) + 1
            value = links[path]
            if isinstance(value, BaseException):
                raise value
            if counts[path] > 1:
                raise FileNotFoundError('Descriptor closed between duplicate reads')
            return value
        with patch.object(Path, 'read_text', lambda path: text[str(path)]), \
                patch.object(Path, 'iterdir', return_value=iter(Path(path) for path in links)), \
                patch.object(os, 'readlink', side_effect=readlink):
            result = instance.proof()
        return result, counts

    def test_reads_each_fd_once_and_tolerates_unrelated_closed_fd(self):
        result, counts = self.proof({'/proc/5/fd/18': 'socket:[42]', '/proc/5/fd/19': FileNotFoundError()})
        self.assertEqual(result['udp'], '0100007F:7A69')
        self.assertEqual(counts, {'/proc/5/fd/18': 1, '/proc/5/fd/19': 1})

    def test_required_ames_socket_disappearing_still_fails(self):
        with self.assertRaisesRegex(ValueError, 'owned fake Ames socket absent'):
            self.proof({'/proc/5/fd/18': FileNotFoundError()})

    def test_permission_failure_is_not_treated_as_closed_fd(self):
        with self.assertRaises(PermissionError):
            self.proof({'/proc/5/fd/18': PermissionError()})

    def test_child_exit_during_enumeration_still_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'child exited'):
            self.proof({'/proc/5/fd/18': 'socket:[42]'}, Mock(side_effect=[None, RuntimeError('child exited')]))


if __name__ == '__main__':
    unittest.main()

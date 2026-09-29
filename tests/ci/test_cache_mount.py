"""Real small mount/permission controls; no Urbit or hosted execution."""
import errno
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROBE = '''import json, os, sys
from pathlib import Path
sys.path[:0] = ['/ci', '/code']
import negative
path = Path('/runtime')
row = {'read_only': bool(os.statvfs(path).f_flag & os.ST_RDONLY)}
try:
    with path.open('r+b'):
        row['opened'] = True
except OSError as error:
    row['open_errno'] = error.errno
try:
    row['result'] = negative.readonly_cache(path)
except ValueError as error:
    row['refusal'] = str(error)
print(json.dumps(row))
'''


class CacheMountControls(unittest.TestCase):
    def observe(self, *, readonly, mode):
        owned = ROOT / '.runtime'
        owned.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cache-control-', dir=owned) as directory:
            source = Path(directory).resolve() / 'runtime'
            source.write_bytes(b'owned harmless cache control\n')
            source.chmod(mode)
            command = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session',
                '--uid', '0', '--gid', '0', '--cap-add', 'CAP_NET_ADMIN', '--cap-add', 'CAP_SETPCAP',
                '--ro-bind', '/usr', '/usr']
            for name in ('bin', 'sbin', 'lib', 'lib64'):
                path = Path('/') / name
                command += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
            command += ['--ro-bind' if readonly else '--bind', str(source), '/runtime',
                '--ro-bind', str(ROOT / 'scripts/ci'), '/ci',
                '--ro-bind', str(ROOT / 'scripts/urbit'), '/code',
                '--proc', '/proc', '--dev', '/dev', '--clearenv', '--',
                '/usr/bin/python3', '-I', '-B', '-c', PROBE]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
            self.assertEqual(result.stderr, '')
            self.assertEqual(source.read_bytes(), b'owned harmless cache control\n')
            return json.loads(result.stdout)

    def test_readonly_mount_with_file_permission_refusal(self):
        self.assertEqual(self.observe(readonly=True, mode=0o550), {
            'read_only': True, 'open_errno': errno.EACCES,
            'result': {'cache_mount_read_only': True, 'cache_write_errno': errno.EACCES}})

    def test_readonly_mount_with_file_write_permission(self):
        self.assertEqual(self.observe(readonly=True, mode=0o660), {
            'read_only': True, 'open_errno': errno.EROFS,
            'result': {'cache_mount_read_only': True, 'cache_write_errno': errno.EROFS}})

    def test_writable_mount_is_refused_even_when_permissions_deny_open(self):
        self.assertEqual(self.observe(readonly=False, mode=0o550), {
            'read_only': False, 'open_errno': errno.EACCES, 'refusal': 'Cache mount is writable'})

    def test_writable_mount_and_writable_file_are_refused_without_changing_bytes(self):
        self.assertEqual(self.observe(readonly=False, mode=0o660), {
            'read_only': False, 'opened': True, 'refusal': 'Cache mount is writable'})


if __name__ == '__main__':
    unittest.main()

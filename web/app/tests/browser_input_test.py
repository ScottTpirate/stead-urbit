"""Real filesystem input refusals; no browser or native qualification."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'web/app'))
SPEC = importlib.util.spec_from_file_location('browser_check_input', ROOT / 'web/app/browser-check.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class PrivateInputTests(unittest.TestCase):
    def test_exact_private_bytes_and_refusals(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as directory:
            path = Path(directory) / 'input.json'
            path.write_bytes(b'{"safe":"synthetic"}\n')
            path.chmod(0o600)
            self.assertEqual(CHECK.private_json(path, 128),
                ({'safe': 'synthetic'}, hashlib.sha256(path.read_bytes()).hexdigest()))
            with self.assertRaises(ValueError):
                CHECK.private_json(path, 4)
            link = path.with_name('link')
            link.symlink_to(path)
            with self.assertRaises(OSError):
                CHECK.private_json(link, 128)
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                CHECK.private_json(path, 128)

    def test_fifo_refusal_has_a_bounded_real_process(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as directory:
            path = Path(directory) / 'pipe'
            os.mkfifo(path, 0o600)
            code = ('import runpy,sys; sys.path.insert(0,sys.argv[1]+"/web/app"); '
                'runpy.run_path(sys.argv[1]+"/web/app/browser-check.py")["private_json"](sys.argv[2],128)')
            child = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT), str(path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            self.assertNotEqual(child.returncode, 0)
            self.assertIn(b'Owned bounded private regular file required', child.stderr)

    def test_nonregular_file_refusal_does_not_leak_descriptors(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as directory:
            before = set(os.listdir('/proc/self/fd'))
            for _ in range(20):
                with self.assertRaises(ValueError):
                    CHECK.private_json(directory, 128)
            self.assertEqual(set(os.listdir('/proc/self/fd')), before)


if __name__ == '__main__':
    unittest.main()

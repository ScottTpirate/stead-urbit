"""Real atomic file replacements; no native execution or CI-cause claim."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import execution_policy as guard


class AtomicControlReaderTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.runtime').mkdir(mode=0o700, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='control-reader-', dir=ROOT / '.runtime')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'lease.json'
        self.path.write_text('{"generation":0}')
        self.original_fstat = os.fstat
        self.replacements = []

    def replace_opened(self, count, *, replacement=None):
        """Place a real rename in the open/fstat window, without a timing race."""
        def inspect(fd):
            info = self.original_fstat(fd)
            if stat.S_ISREG(info.st_mode) and len(self.replacements) < count:
                generation = len(self.replacements) + 1
                next_path = self.root / 'next.json'
                if replacement is None:
                    next_path.write_text(json.dumps({'generation': generation}))
                else:
                    replacement(next_path)
                os.replace(next_path, self.path)
                self.replacements.append(generation)
            return self.original_fstat(fd)
        return patch.object(guard.os, 'fstat', side_effect=inspect)

    def test_atomic_replacements_return_only_the_current_linked_snapshot(self):
        for count in (1, 2):
            with self.subTest(replacements=count):
                self.replacements.clear()
                before = set(os.listdir('/proc/self/fd'))
                with self.replace_opened(count):
                    self.assertEqual(guard.read_json(self.path), {'generation': count})
                self.assertEqual(self.replacements, list(range(1, count + 1)))
                self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def test_continuous_replacement_fails_after_three_reads_without_leaking_fds(self):
        before = set(os.listdir('/proc/self/fd'))
        with self.replace_opened(10), self.assertRaisesRegex(guard.GuardError, 'every bounded read'):
            guard.read_json(self.path)
        self.assertEqual(self.replacements, [1, 2, 3])
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def test_replacement_symlink_remains_refused(self):
        other = self.root / 'other.json'; other.write_text('{"generation":99}')
        with self.replace_opened(1, replacement=lambda p: p.symlink_to(other)), self.assertRaises(OSError):
            guard.read_json(self.path)
        self.assertEqual(other.read_text(), '{"generation":99}')

    def test_replacement_hardlink_remains_refused(self):
        other = self.root / 'other.json'; other.write_text('{"generation":99}')
        with self.replace_opened(1, replacement=lambda p: os.link(other, p)), \
                self.assertRaisesRegex(guard.GuardError, 'singly linked'):
            guard.read_json(self.path)

    def test_replacement_still_enforces_size_and_duplicate_key_bounds(self):
        for body in ('x' * 33, '{"x":1,"x":2}'):
            with self.subTest(body=body):
                self.replacements.clear()
                self.path.write_text('{}')
                with self.replace_opened(1, replacement=lambda p: p.write_text(body)), \
                        self.assertRaises(guard.GuardError):
                    guard.read_json(self.path, maximum=32)


if __name__ == '__main__':
    unittest.main()

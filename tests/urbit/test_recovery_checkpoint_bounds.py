"""Explicit larger file-count profiles retain the exact bounded checkpoint."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import release_install as install


class RecoveryCheckpointBounds(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='stead-checkpoint-bounds-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pier = self.root / 'source'
        for directory in ('.urb', 'base', 'retained-alias'):
            target = self.pier / directory
            target.mkdir(mode=0o700, parents=True)
            (target / 'state').write_bytes(directory.encode())

    def test_explicit_profile_preserves_all_alias_files_and_original(self):
        expected = install.checkpoint_tree(self.pier)
        destination = self.root / 'copy'
        copied = install.checkpoint_tree(self.pier, destination, maximum_files=32768)
        self.assertEqual(copied, expected)
        self.assertEqual(copied['files'], 3)
        self.assertEqual(install.checkpoint_tree(destination), expected)
        self.assertEqual(install.checkpoint_tree(self.pier), expected)
        self.assertEqual((destination / 'retained-alias/state').read_bytes(), b'retained-alias')

    def test_count_limit_is_enforced_with_no_success_receipt(self):
        with self.assertRaisesRegex(ValueError, 'file bound'):
            install.checkpoint_tree(self.pier, maximum_files=2)
        self.assertEqual(install.checkpoint_tree(self.pier, maximum_files=3)['files'], 3)

    def test_profile_rejects_unbounded_noninteger_or_boolean_values_before_access(self):
        for value in (0, -1, 32769, True, False, '32768', 32768.0, None):
            with self.subTest(value=value), patch.object(install.execution_policy, 'directory_fd') as access:
                with self.assertRaisesRegex(ValueError, 'file-count profile'):
                    install.checkpoint_tree(self.pier, maximum_files=value)
                access.assert_not_called()

    def test_larger_profile_still_rejects_links_and_special_files(self):
        for kind in ('symlink', 'hardlink', 'fifo'):
            path = self.pier / 'hostile'
            with self.subTest(kind=kind):
                if kind == 'symlink':
                    path.symlink_to(self.pier / '.urb/state')
                elif kind == 'hardlink':
                    os.link(self.pier / '.urb/state', path)
                else:
                    os.mkfifo(path)
                try:
                    with self.assertRaisesRegex(ValueError, 'redirect|hard link|special'):
                        install.checkpoint_tree(self.pier, maximum_files=32768)
                finally:
                    path.unlink()

    def test_larger_profile_still_rejects_individual_file_bound(self):
        target = self.pier / '.urb/state'
        with target.open('wb') as output:
            output.truncate(512 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(ValueError, 'file bound'):
            install.checkpoint_tree(self.pier, maximum_files=32768)


if __name__ == '__main__':
    unittest.main()

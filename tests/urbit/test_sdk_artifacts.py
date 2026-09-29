"""Real bounded filesystem controls using synthetic bytes, not compiled vases."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import sdk_artifacts as artifacts


class SdkArtifactTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.runtime').mkdir(mode=0o700, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='sdk-artifact-control-', dir=ROOT / '.runtime')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / 'artifacts'
        self.directory.mkdir(mode=0o700)
        self.files = {name: ('synthetic ' + name).encode() + b'\0' for name in artifacts.ARTIFACTS}
        self.pins = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                     for name, raw in self.files.items()}
        for name, raw in self.files.items():
            (self.directory / name).write_bytes(raw)
            (self.directory / name).chmod(0o600)

    def read(self, pins=None):
        return artifacts.read_artifacts(self.root, 'artifacts',
            self.pins if pins is None else pins, owner_uid=os.getuid())

    def test_exact_named_binary_bytes_including_trailing_zero_are_retained(self):
        result = self.read()
        self.assertEqual(result, self.files)
        self.assertEqual(set(result), {'sample.jam', 'stead-command-3.jam',
            'stead-query-3.jam', 'stead-result-3.jam', 'stead-updates-3.jam'})
        # Consumers retain the verified byte strings, not mutable filesystem paths.
        (self.directory / 'sample.jam').write_bytes(b'changed after readback')
        self.assertEqual(result['sample.jam'], self.files['sample.jam'])

    def test_changed_truncated_and_trailing_bytes_fail_original_pins(self):
        path = self.directory / 'sample.jam'
        original = self.files['sample.jam']
        for raw in (b'X' + original[1:], original[:-1], original + b'\0'):
            path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.read()

    def test_missing_extra_or_misnamed_artifact_fails(self):
        path = self.directory / 'stead-command-3.jam'
        path.rename(self.directory / 'wrong-mark.jam')
        with self.assertRaises(ValueError):
            self.read()
        (self.directory / 'wrong-mark.jam').unlink()
        with self.assertRaises(ValueError):
            self.read()

    def test_manifest_alongside_files_cannot_supply_or_override_pins(self):
        (self.directory / 'manifest.json').write_text('{"status":"pass"}')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.read()

    def test_exact_pin_inventory_types_and_bounds_precede_file_reads(self):
        bad = [None, {}, self.pins | {'private.jam': self.pins['sample.jam']}]
        for pin in ({'bytes': True, 'sha256': 'a' * 64},
                    {'bytes': 0, 'sha256': 'a' * 64},
                    {'bytes': artifacts.MAX_ARTIFACT + 1, 'sha256': 'a' * 64},
                    {'bytes': 1, 'sha256': 'A' * 64},
                    {'bytes': 1, 'sha256': 'a' * 64, 'status': 'pass'}):
            bad.append(self.pins | {'sample.jam': pin})
        bad.append({name: {'bytes': artifacts.MAX_ARTIFACT, 'sha256': 'a' * 64}
                    for name in artifacts.ARTIFACTS})
        with patch.object(artifacts, 'read_file') as reader:
            for pins in bad:
                with self.subTest(pins=pins), self.assertRaises(ValueError):
                    artifacts.read_artifacts(self.root, 'artifacts', pins, owner_uid=os.getuid())
            reader.assert_not_called()

    def test_symlink_hardlink_directory_fifo_and_oversized_file_are_refused(self):
        path = self.directory / 'sample.jam'
        target = self.root / 'outside.jam'
        target.write_bytes(self.files['sample.jam'])
        target.chmod(0o600)
        path.unlink()
        path.symlink_to(target)
        with self.assertRaises((ValueError, OSError)):
            self.read()
        path.unlink()
        os.link(target, path)
        with self.assertRaises(ValueError):
            self.read()
        path.unlink()
        path.mkdir(mode=0o700)
        with self.assertRaises((ValueError, OSError)):
            self.read()
        path.rmdir()
        os.mkfifo(path, mode=0o600)
        with self.assertRaises(ValueError):
            self.read()
        path.unlink()
        with path.open('wb') as source:
            source.truncate(artifacts.MAX_ARTIFACT + 1)
        path.chmod(0o600)
        with self.assertRaises(ValueError):
            self.read()

    def test_owner_modes_symlink_parent_and_outside_paths_are_refused(self):
        with self.assertRaises(ValueError):
            artifacts.read_artifacts(self.root, 'artifacts', self.pins, owner_uid=os.getuid() + 1)
        for directory in ('/tmp/artifacts', '../artifacts'):
            with self.assertRaises(ValueError):
                artifacts.read_artifacts(self.root, directory, self.pins, owner_uid=os.getuid())
        self.directory.chmod(0o750)
        with self.assertRaises(ValueError):
            self.read()
        self.directory.chmod(0o700)
        (self.directory / 'sample.jam').chmod(0o640)
        with self.assertRaises(ValueError):
            self.read()
        (self.directory / 'sample.jam').chmod(0o600)
        self.directory.rename(self.root / 'held')
        self.directory.symlink_to(self.root / 'held', target_is_directory=True)
        with self.assertRaises(ValueError):
            self.read()

    def test_parent_replacement_after_read_is_refused(self):
        read_file = artifacts.read_file
        changed = False
        def replace(*args):
            nonlocal changed
            result = read_file(*args)
            if not changed:
                self.directory.rename(self.root / 'held')
                self.directory.mkdir(mode=0o700)
                changed = True
            return result
        with patch.object(artifacts, 'read_file', side_effect=replace), \
                self.assertRaisesRegex(ValueError, 'directory changed'):
            self.read()

    def test_logical_mark_pins_are_not_interchangeable(self):
        pins = copy.deepcopy(self.pins)
        pins['stead-command-3.jam'], pins['stead-query-3.jam'] = (
            pins['stead-query-3.jam'], pins['stead-command-3.jam'])
        with self.assertRaises(ValueError):
            self.read(pins)

    def test_pins_are_frozen_and_late_unlisted_files_are_refused(self):
        read_file = artifacts.read_file
        def mutate_pins(*args):
            self.pins['sample.jam']['sha256'] = '0' * 64
            return read_file(*args)
        with patch.object(artifacts, 'read_file', side_effect=mutate_pins):
            self.assertEqual(self.read(), self.files)
        self.pins['sample.jam']['sha256'] = hashlib.sha256(self.files['sample.jam']).hexdigest()
        def add_file(*args):
            result = read_file(*args)
            (self.directory / 'extra.jam').write_bytes(b'unlisted')
            return result
        with patch.object(artifacts, 'read_file', side_effect=add_file), \
                self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.read()


if __name__ == '__main__':
    unittest.main()

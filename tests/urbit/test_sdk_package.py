"""Real filesystem/archive tests for the offline SDK; no native execution."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('sdk_package_under_test', ROOT / 'scripts/package_sdk.py')
SDK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SDK)


class SdkPackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='stead-sdk-test-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        names = [*SDK.EXPORTS, 'sdk/export-lock.json', 'specs/urbit/toolchain.lock.json']
        for name in names:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        (self.root / 'out').mkdir()

    def change_lock(self, change):
        path = self.root / 'sdk/export-lock.json'
        value = json.loads(path.read_bytes())
        change(value)
        path.write_text(json.dumps(value))

    def test_exact_public_surface_and_notices(self):
        private = self.root / 'native/core/desk/ted/stead-client.hoon'
        private.parent.mkdir()
        private.write_text('private fixture canary; never export this')
        raw, manifest = SDK.archive_bytes(self.root)
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            names = archive.getnames()
            self.assertEqual(names, sorted(names))
            self.assertEqual(set(names), {'stead-sdk-v2/' + x for x in SDK.EXPORTS.values()}
                             | {'stead-sdk-v2/manifest.json'})
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual((member.uid, member.gid, member.mtime, member.mode), (0, 0, 0, 0o644))
            for source, target in SDK.EXPORTS.items():
                self.assertEqual(archive.extractfile('stead-sdk-v2/' + target).read(),
                                 (self.root / source).read_bytes())
            self.assertEqual(json.loads(archive.extractfile('stead-sdk-v2/manifest.json').read()), manifest)
        self.assertNotIn(b'private fixture canary', raw)
        self.assertEqual(len([x for x in manifest['files'] if x['path'].endswith('.hoon')]), 4)

    def test_reproducible_across_metadata_and_output_names(self):
        first, _ = SDK.build(self.root, 'out/first.tar')
        for name in SDK.EXPORTS:
            os.utime(self.root / name, (123456789, 123456789))
            (self.root / name).chmod(0o600)
        second, _ = SDK.build(self.root, 'out/second.tar')
        self.assertEqual(first, second)
        self.assertEqual(SDK.verify(self.root, 'out/first.tar')[0], first)
        with tempfile.TemporaryDirectory(prefix='stead-sdk-other-root-') as other:
            other_root = Path(other)
            for name in [*SDK.EXPORTS, 'sdk/export-lock.json', 'specs/urbit/toolchain.lock.json']:
                target = other_root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((self.root / name).read_bytes())
            self.assertEqual(SDK.archive_bytes(other_root)[0], first)

    def test_corruption_and_trailing_data_rejected(self):
        raw, _ = SDK.archive_bytes(self.root)
        damaged = bytearray(raw)
        damaged[len(raw) // 3] ^= 1
        for data in (bytes(damaged), raw + b'foreign trailing bytes'):
            (self.root / 'out/bad.tar').write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'differs'):
                SDK.verify(self.root, 'out/bad.tar')

    def test_hostile_archive_is_not_extracted(self):
        sentinel = self.root / 'untouched.txt'
        sentinel.write_text('original')
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode='w') as archive:
            entry = tarfile.TarInfo('../untouched.txt')
            entry.type = tarfile.SYMTYPE
            entry.linkname = '/tmp/stead-sdk-outside'
            archive.addfile(entry)
        (self.root / 'out/hostile.tar').write_bytes(payload.getvalue())
        with self.assertRaisesRegex(ValueError, 'differs'):
            SDK.verify(self.root, 'out/hostile.tar')
        self.assertEqual(sentinel.read_text(), 'original')

    def test_changed_source_rejected_before_output(self):
        p = self.root / 'native/core/desk/lib/stead-codec.hoon'
        p.write_bytes(p.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'Pinned export'):
            SDK.build(self.root, 'out/package.tar')
        self.assertFalse((self.root / 'out/package.tar').exists())

    def test_missing_license_rejected(self):
        (self.root / 'LICENSE').unlink()
        with self.assertRaises(OSError):
            SDK.archive_bytes(self.root)

    def test_private_export_cannot_be_added_to_lock(self):
        self.change_lock(lambda lock: lock['files'].update({
            'native/core/desk/ted/stead-client.hoon': {'bytes': 1, 'sha256': '0' * 64}}))
        with self.assertRaisesRegex(ValueError, 'exactly the public files'):
            SDK.archive_bytes(self.root)

    def test_duplicate_lock_key_rejected(self):
        path = self.root / 'sdk/export-lock.json'
        path.write_text(path.read_text().replace('{', '{"api_version": 2,', 1))
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            SDK.archive_bytes(self.root)

    def test_unsupported_versions_rejected(self):
        path = self.root / 'sdk/export-lock.json'
        original = json.loads(path.read_bytes())
        for key, value in [('api_version', 3), ('api_version', True), ('kernel_kelvin', 409),
                           ('sdk_version', '9.0.0')]:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(original)
                changed[key] = value
                path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'Unsupported'):
                    SDK.archive_bytes(self.root)

    def test_toolchain_drift_rejected(self):
        p = self.root / 'specs/urbit/toolchain.lock.json'
        p.write_bytes(p.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'Pinned toolchain'):
            SDK.archive_bytes(self.root)

    def test_symlink_input_and_parent_rejected(self):
        source = self.root / 'LICENSE'
        target = self.root / 'license-target'
        source.rename(target)
        source.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            SDK.archive_bytes(self.root)
        source.unlink()
        target.rename(source)
        parent = self.root / 'native/core/desk/lib'
        parent.rename(parent.with_name('real-lib'))
        parent.symlink_to(parent.with_name('real-lib'), target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            SDK.archive_bytes(self.root)

    def test_outputs_cannot_overwrite_or_escape(self):
        existing = self.root / 'out/existing.tar'
        existing.write_bytes(b'preserve')
        for name in ('out/existing.tar', '../escape.tar', str(self.root / 'absolute.tar')):
            with self.subTest(name=name), self.assertRaises(ValueError):
                SDK.build(self.root, name)
        self.assertEqual(existing.read_bytes(), b'preserve')

        (self.root / 'alias').symlink_to(self.root / 'out', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            SDK.build(self.root, 'alias/package.tar')
        (self.root / 'out/link.tar').symlink_to(existing)
        with self.assertRaises(ValueError):
            SDK.build(self.root, 'out/link.tar')
        self.assertEqual(existing.read_bytes(), b'preserve')

    def test_parent_swap_during_read_cannot_redirect_input(self):
        original = self.root / 'out/payload.bin'
        original.write_bytes(b'inside checkout')
        expected_identity = (original.stat().st_dev, original.stat().st_ino)
        with tempfile.TemporaryDirectory(prefix='stead-sdk-outside-') as outside:
            outside = Path(outside)
            sentinel = outside / 'payload.bin'
            sentinel.write_bytes(b'outside sentinel')
            real_open = os.open
            opened = []

            def swap_then_open(name, flags, *args, **kwargs):
                if name == 'payload.bin' and kwargs.get('dir_fd') is not None:
                    (self.root / 'out').rename(self.root / 'held-out')
                    (self.root / 'out').symlink_to(outside, target_is_directory=True)
                    descriptor = real_open(name, flags, *args, **kwargs)
                    opened.append(SDK.identity(descriptor))
                    return descriptor
                return real_open(name, flags, *args, **kwargs)

            with mock.patch.object(SDK.os, 'open', side_effect=swap_then_open):
                with self.assertRaisesRegex(ValueError, 'Symlink|changed'):
                    SDK.read_bounded(self.root, 'out/payload.bin')
            self.assertEqual(opened, [expected_identity])
            self.assertEqual(sentinel.read_bytes(), b'outside sentinel')

    def test_parent_swap_during_output_cannot_escape_or_report_success(self):
        expected, _ = SDK.archive_bytes(self.root)
        with tempfile.TemporaryDirectory(prefix='stead-sdk-outside-') as outside:
            outside = Path(outside)
            sentinel = outside / 'untouched.txt'
            sentinel.write_bytes(b'outside sentinel')
            real_open = os.open

            def swap_then_open(name, flags, *args, **kwargs):
                if name == 'package.tar' and kwargs.get('dir_fd') is not None:
                    (self.root / 'out').rename(self.root / 'held-out')
                    (self.root / 'out').symlink_to(outside, target_is_directory=True)
                return real_open(name, flags, *args, **kwargs)

            with mock.patch.object(SDK.os, 'open', side_effect=swap_then_open):
                with self.assertRaisesRegex(ValueError, 'Symlink|changed'):
                    SDK.build(self.root, 'out/package.tar')
            self.assertFalse((outside / 'package.tar').exists())
            self.assertEqual(sentinel.read_bytes(), b'outside sentinel')
            self.assertEqual((self.root / 'held-out/package.tar').read_bytes(), expected)

    def test_parent_replaced_with_directory_is_also_rejected(self):
        original = self.root / 'out/payload.bin'
        original.write_bytes(b'inside checkout')
        real_open = os.open

        def swap_then_open(name, flags, *args, **kwargs):
            if name == 'payload.bin' and kwargs.get('dir_fd') is not None:
                (self.root / 'out').rename(self.root / 'held-out')
                (self.root / 'out').mkdir()
                (self.root / 'out/payload.bin').write_bytes(b'replacement')
            return real_open(name, flags, *args, **kwargs)

        with mock.patch.object(SDK.os, 'open', side_effect=swap_then_open):
            with self.assertRaisesRegex(ValueError, 'Parent directory changed'):
                SDK.read_bounded(self.root, 'out/payload.bin')
        self.assertEqual((self.root / 'out/payload.bin').read_bytes(), b'replacement')

    def test_oversized_inputs_rejected(self):
        (self.root / 'out/large.tar').write_bytes(b'x' * (SDK.MAX_ARCHIVE + 1))
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            SDK.verify(self.root, 'out/large.tar')
        (self.root / 'LICENSE').write_bytes(b'x' * (SDK.MAX_FILE + 1))
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            SDK.archive_bytes(self.root)

    def test_directory_input_is_rejected_without_leaking_descriptors(self):
        before = set(Path('/proc/self/fd').iterdir())
        for _ in range(20):
            with self.assertRaisesRegex(ValueError, 'regular file'):
                SDK.read_bounded(self.root, 'out')
        self.assertEqual(set(Path('/proc/self/fd').iterdir()), before)

    def test_cli_build_verify_and_failure_status(self):
        command = [sys.executable, str(ROOT / 'scripts/package_sdk.py'), '--root', str(self.root)]
        for arguments in (['build', '--output', 'out/cli.tar'], ['verify', '--archive', 'out/cli.tar']):
            result = subprocess.run(command + arguments, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertFalse(value['native_execution'])
            self.assertEqual(value['sha256'], hashlib.sha256((self.root / 'out/cli.tar').read_bytes()).hexdigest())
        result = subprocess.run(command + ['build', '--output', 'out/cli.tar'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Output already exists', result.stderr)


if __name__ == '__main__':
    unittest.main()

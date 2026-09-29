"""Real package/Git/filesystem controls, not SDK compilation or isolation."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_sdk_consumer as prepare
import test_sdk_source as source_fixture


class SdkInputTests(unittest.TestCase):
    git = source_fixture.SdkSourceTests.git
    archive = source_fixture.SdkSourceTests.archive

    def setUp(self):
        source_fixture.SdkSourceTests.setUp(self)
        (self.root / '.runtime').mkdir(mode=0o700)
        self.output = '.runtime/sdk-builder-control'

    def run_prepare(self):
        return prepare.prepare(self.root, 'sdk.tar', self.output)

    def test_public_exports_pins_and_fixed_controller_runner_are_prepared(self):
        for name in ('native/core/desk/app/stead-home.hoon', 'private-fixture.hoon', '.runtime/production-pier/key',
                     'scripts/sdk_native/build.hoon'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('PRIVATE-CONTROL-DO-NOT-COPY')
        receipt = self.run_prepare()
        output = self.root / self.output
        self.assertEqual(receipt['classification'], 'real-host-sdk-input-preparation')
        self.assertEqual(receipt['protocol'], 'stead.sdk-builder-inputs/2')
        self.assertFalse(receipt['native_execution'])
        self.assertFalse(receipt['independent_consumer_execution'])
        self.assertEqual(receipt['source_checker_sha256'],
            hashlib.sha256((ROOT / 'scripts/check_sdk_source.py').read_bytes()).hexdigest())
        self.assertEqual(len(receipt['files']), 16)
        runner = 'runner/ted/stead-sdk-build.hoon'
        self.assertEqual(receipt['build_runner'], {'source':'scripts/sdk_native/build.hoon',
            'destination':runner, 'status':'uncompiled-source-preparation'})
        self.assertEqual((output / runner).read_bytes(), (ROOT / 'scripts/sdk_native/build.hoon').read_bytes())
        actual = {str(path.relative_to(output)) for path in output.rglob('*') if path.is_file()}
        self.assertEqual(actual, set(receipt['files']) | {'inputs.json'})
        self.assertEqual(json.loads((output / 'inputs.json').read_bytes()), receipt)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
        for name, pin in receipt['files'].items():
            body = (output / name).read_bytes()
            self.assertNotIn(b'PRIVATE-CONTROL-DO-NOT-COPY', body)
            self.assertEqual({'bytes':len(body), 'sha256':hashlib.sha256(body).hexdigest()}, pin)
            self.assertEqual(stat.S_IMODE((output / name).stat().st_mode), 0o600)

    def test_missing_fixed_controller_runner_refuses_before_creating_output(self):
        # The input root contains no reviewed controller runner. There must be
        # no fallback to a package-supplied hook or a partial ready receipt.
        with patch.object(prepare, 'ROOT', self.root), self.assertRaises(FileNotFoundError):
            self.run_prepare()
        self.assertFalse((self.root / self.output).exists())

    def test_existing_partial_directory_is_preserved(self):
        output = self.root / self.output
        output.mkdir(mode=0o700)
        (output / 'existing').write_text('keep')
        with self.assertRaises(FileExistsError):
            self.run_prepare()
        self.assertEqual([item.name for item in output.iterdir()], ['existing'])
        self.assertEqual((output / 'existing').read_text(), 'keep')

    def test_output_paths_cannot_target_checkout_or_other_directories(self):
        for output in ('source', '/tmp/sdk-builder-outside', '.runtime/../sdk-builder-outside',
                       '.runtime/deeper/sdk-builder-outside', '.runtime/sdk-builder-../escape'):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, 'new .runtime'):
                prepare.prepare(self.root, 'sdk.tar', output)
        self.assertEqual(list((self.root / '.runtime').iterdir()), [])

    def test_runtime_symlink_and_shared_directory_are_refused(self):
        runtime = self.root / '.runtime'
        runtime.chmod(0o750)
        with self.assertRaisesRegex(ValueError, 'Private owned'):
            self.run_prepare()
        runtime.rmdir()
        target = self.root / 'other'
        target.mkdir(mode=0o700)
        runtime.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.run_prepare()
        self.assertEqual(list(target.iterdir()), [])

    def test_changed_archive_after_real_source_check_does_not_release_inputs(self):
        actual_check = prepare.check_sdk_source.check
        def changed(*arguments):
            binding = actual_check(*arguments)
            path = self.root / 'sdk.tar'
            path.write_bytes(path.read_bytes() + b'trailing')
            return binding
        with patch.object(prepare.check_sdk_source, 'check', side_effect=changed), \
             self.assertRaisesRegex(ValueError, 'changed after source verification'):
            self.run_prepare()
        self.assertFalse((self.root / self.output).exists())

    def test_forged_source_and_archive_changes_refuse_before_output_creation(self):
        self.lock['native_source_commit'] = '0' * 40
        self.archive()
        with self.assertRaises(ValueError):
            self.run_prepare()
        self.assertFalse((self.root / self.output).exists())

    def test_partial_write_failure_never_produces_a_receipt_or_overwrites_prior_files(self):
        actual_write = prepare.write_new
        count = 0
        def fail_second(*arguments):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('controlled write failure')
            actual_write(*arguments)
        with patch.object(prepare, 'write_new', side_effect=fail_second), self.assertRaises(OSError):
            self.run_prepare()
        output = self.root / self.output
        self.assertTrue(output.exists())
        self.assertFalse((output / 'inputs.json').exists())
        self.assertEqual(len([path for path in output.rglob('*') if path.is_file()]), 1)
        with self.assertRaises(FileExistsError):
            self.run_prepare()

    def test_later_mutation_of_an_earlier_file_is_refused_before_receipt(self):
        actual_write = prepare.write_new
        def mutate(root_fd, name, raw):
            actual_write(root_fd, name, raw)
            if name == 'toolchain.json':
                path = self.root / self.output / 'sdk/API.md'
                body = path.read_bytes()
                path.write_bytes(bytes([body[0] ^ 1]) + body[1:])
        with patch.object(prepare, 'write_new', side_effect=mutate), \
             self.assertRaisesRegex(ValueError, 'readback differs'):
            self.run_prepare()
        self.assertFalse((self.root / self.output / 'inputs.json').exists())

    def test_unlisted_private_file_is_refused_before_receipt(self):
        actual_write = prepare.write_new
        def inject(root_fd, name, raw):
            actual_write(root_fd, name, raw)
            if name == 'toolchain.json':
                actual_write(root_fd, 'sdk/private-fixture.hoon', b'private control')
        with patch.object(prepare, 'write_new', side_effect=inject), \
             self.assertRaisesRegex(ValueError, 'Unexpected prepared input'):
            self.run_prepare()
        self.assertFalse((self.root / self.output / 'inputs.json').exists())

    def test_output_replacement_during_receipt_write_is_refused_and_preserved(self):
        actual_write = prepare.write_new
        output = self.root / self.output
        held = output.with_name(output.name + '-held')
        def replace(root_fd, name, raw):
            actual_write(root_fd, name, raw)
            if name == 'inputs.json':
                output.rename(held)
                output.mkdir(mode=0o700)
        with patch.object(prepare, 'write_new', side_effect=replace), \
             self.assertRaisesRegex(ValueError, 'Prepared directory changed'):
            self.run_prepare()
        self.assertEqual(list(output.iterdir()), [])
        self.assertTrue((held / 'inputs.json').is_file())

    def test_receipt_mutation_is_refused_by_final_byte_readback(self):
        actual_write = prepare.write_new
        def mutate(root_fd, name, raw):
            actual_write(root_fd, name, raw)
            if name == 'inputs.json':
                path = self.root / self.output / name
                body = path.read_bytes()
                path.write_bytes(bytes([body[0] ^ 1]) + body[1:])
        with patch.object(prepare, 'write_new', side_effect=mutate), \
             self.assertRaisesRegex(ValueError, 'readback differs'):
            self.run_prepare()

    def test_repository_filesystem_directory_opened_before_entries_is_read_fresh(self):
        # The real CLI exposed this on the repository filesystem, while the
        # source fixtures in /tmp did not. Keep this control on that filesystem.
        (ROOT / '.runtime').mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='sdk-enumeration-', dir=ROOT / '.runtime') as directory:
            descriptor = prepare.open_directory(directory)
            try:
                files = {'sdk/public.hoon':b'owned public control', 'toolchain.json':b'{}'}
                for name, raw in files.items():
                    prepare.write_new(descriptor, name, raw)
                prepare.verify_directory(descriptor, files)
                prepare.write_new(descriptor, 'inputs.json', b'{}')
                prepare.verify_directory(descriptor, files | {'inputs.json':b'{}'})
            finally:
                os.close(descriptor)


if __name__ == '__main__':
    unittest.main()

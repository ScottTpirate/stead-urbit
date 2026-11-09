"""Synthetic filesystem/receipt checks only; no native runtime is started."""
import copy
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import release_install as install
import package_release as release


class CleanCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-checkpoint-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prior = self.root / '.runtime/release-install-original'
        self.destination = self.root / '.runtime/release-install-next/work'
        self.control = self.root / '.runtime/execution-runs/release-install-prior/control'
        self.pier = self.prior / 'work/zod'
        self.lockpath = self.root / 'specs/urbit/toolchain.lock.json'
        for path in (self.destination, self.control, self.pier / '.urb', self.pier / 'base', self.lockpath.parent):
            path.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.prior.chmod(0o700)
        (self.pier / '.urb/state').write_bytes(b'stopped synthetic state')
        (self.pier / 'base/kernel.hoon').write_bytes(b'kernel source')
        self.checkpoint_sha = install.checkpoint_tree(self.pier)['sha256']
        self.lock = {'kernel': {'directory': 'pinned-kernel'}}
        self.lockpath.write_text(json.dumps(self.lock))
        self.commit, self.artifact, self.run_id = 'a' * 40, 'b' * 64, 'c' * 32
        self.sources = {'scripts/release_install.py': b'reviewed controller', 'scripts/sdk_native/native.py': b'reviewed native',
                        'scripts/package_release.py': b'reviewed packager', 'scripts/package_sdk.py': b'reviewed shared packager'}
        self.sources.update({'scripts/urbit/' + name: name.encode() for name in install.HELPERS})
        self.sources['specs/urbit/toolchain.lock.json'] = self.lockpath.read_bytes()
        self.pins = {name: release.digest(raw) for name, raw in self.sources.items() if name.startswith('scripts/')}
        groups = {'package': {'manifest.json': b'public candidate'},
                  'controller': {'release_install.py': self.sources['scripts/release_install.py']},
                  'support': {'native.py': self.sources['scripts/sdk_native/native.py']},
                  'helpers': {name: self.sources['scripts/urbit/' + name] for name in install.HELPERS}}
        for group, files in groups.items():
            (self.prior / group).mkdir(mode=0o700)
            for name, data in files.items():
                (self.prior / group / name).write_bytes(data)
        shutil.copytree(self.prior / 'package', self.destination.parent / 'package')
        self.context = {'verifier_source_commit': self.commit, 'artifact_sha256': self.artifact, 'sources': self.pins}
        self.context.update({name: install.inventory(self.prior / name) for name in groups})
        self.guard = {'status': 'failed', 'exit_code': 1, 'launched': True, 'label': 'release-install',
                      'run_directory': str(self.control.parent), 'guard_sha256': self.pins['scripts/urbit/execution_policy.py'],
                      'run_id': self.run_id, 'scope': 'stead-native-' + self.run_id + '.scope',
                      'argv': ['guard-wrapper'] + install.sandbox_command(self.prior, self.control, self.run_id, self.lock, self.lockpath)}
        self.report = {'status': 'fail', 'verifier_source_commit': self.commit, 'artifact_sha256': self.artifact,
                       'checks': [{'name': name, 'passed': True} for name in install.PREINSTALL_CHECKS],
                       'commands': [{'source': 'zuse', 'output': '%408\n'}, {'source': 'our', 'output': '~zod\n'},
                                    {'source': '|mount %base', 'output': '>='}],
                       'error': "FileNotFoundError: [Errno 2] No such file or directory: '/proc/5/fd/19'",
                       'cleanup': {'clean': True, 'exit_code': 0, 'forced': False, 'premature': False, 'reaped': True}}
        self.host = {'source_unchanged': True, 'evidence': str(self.prior / 'work/report.json'),
                     'guard_report': str(self.control.parent / 'report.json'), 'guard_status': 'failed', 'artifact_sha256': self.artifact}
        self.write(self.prior / '.stead-disposable.json', {'format': 1, 'purpose': 'fresh-offline-release-install-only'})
        self.write(self.control.parent / '.stead-disposable.json', {'format': 1, 'purpose': 'host native execution guard', 'run_id': self.run_id})
        self.write(self.control / 'lease.json', {'state': 'stopped', 'run_id': self.run_id, 'guard_sha256': self.pins['scripts/urbit/execution_policy.py']})
        self.write_receipts()
        patches = [patch.object(install, 'ROOT', self.root),
                   patch.object(install, 'CLEAN_RETRY_CONTROLLER', self.pins['scripts/release_install.py']),
                   patch.object(install, 'CLEAN_RETRY_NATIVE', self.pins['scripts/sdk_native/native.py']),
                   patch.object(release, 'source_identity', return_value=self.commit),
                   patch.object(release, 'committed', side_effect=lambda root, commit, name: self.sources[name]),
                   patch.object(install.subprocess, 'run', return_value=SimpleNamespace(stdout='LoadState=not-found\nActiveState=inactive\nControlGroup=\n'))]
        for mock in patches:
            mock.start()
            self.addCleanup(mock.stop)
        self.guard['argv'] = ['guard-wrapper'] + install.sandbox_command(self.prior, self.control, self.run_id, self.lock, self.lockpath)
        self.write_receipts()

    def write(self, path, data):
        path.write_text(json.dumps(data))

    def write_receipts(self):
        for path, data in [(self.prior / 'host-report.json', self.host), (self.prior / 'work/report.json', self.report),
                           (self.control / 'release-context.json', self.context), (self.control.parent / 'report.json', self.guard)]:
            self.write(path, data)

    def perform(self):
        return install.checked_clean_copy('.runtime/release-install-original', self.destination, self.artifact, self.lock, self.lockpath, self.checkpoint_sha)

    def test_exact_preinstall_checkpoint_copied_without_changing_original(self):
        before = install.checkpoint_tree(self.pier)
        result = self.perform()
        self.assertEqual(result['mode'], 'resumed-clean-checkpoint')
        self.assertFalse(result['fresh_boot_acceptance'])
        self.assertEqual(result['pier'], before)
        self.assertEqual(install.checkpoint_tree(self.pier), before)
        self.assertEqual(install.checkpoint_tree(self.destination / 'zod'), before)
        self.assertNotEqual((self.pier / '.urb/state').stat().st_ino, (self.destination / 'zod/.urb/state').stat().st_ino)

    def test_rejects_attempted_install_unclean_stop_or_unbound_receipt(self):
        mutations = [('commands', [{'source': '|new-desk %release-test', 'output': '>='}]),
                     ('cleanup', {'clean': False}), ('artifact_sha256', 'd' * 64),
                     ('error', 'Unrelated failure'), ('installed_files', {}), ('boot', {}), ('watchdog_errors', [])]
        original = copy.deepcopy(self.report)
        for key, value in mutations:
            with self.subTest(key=key):
                self.report = copy.deepcopy(original)
                self.report[key] = value
                self.write_receipts()
                with self.assertRaises(ValueError):
                    self.perform()
                self.assertFalse((self.destination / 'zod').exists())

    def test_rejects_modified_controller_or_package(self):
        for name in ('controller/release_install.py', 'package/manifest.json'):
            path = self.prior / name
            prior = path.read_bytes()
            try:
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'public inputs changed'):
                    self.perform()
            finally:
                path.write_bytes(prior)

    def test_rejects_different_guard_mount_binding(self):
        self.guard['argv'].append('--foreign-mount')
        self.write_receipts()
        with self.assertRaisesRegex(ValueError, 'namespace/mount binding'):
            self.perform()

    def test_rejects_unretired_scope_and_runtime_lock(self):
        with patch.object(install.subprocess, 'run', return_value=SimpleNamespace(stdout='LoadState=loaded\nActiveState=active\nControlGroup=/still-live\n')):
            with self.assertRaisesRegex(ValueError, 'has not retired'):
                self.perform()
        (self.pier / '.vere.lock').write_text('still owned')
        with self.assertRaisesRegex(ValueError, 'runtime ownership lock'):
            self.perform()

    def test_rejects_pier_symlink_hard_link_and_special_file(self):
        path = self.pier / 'base/redirect'
        path.symlink_to(self.pier / '.urb/state')
        with self.assertRaisesRegex(ValueError, 'redirect'):
            self.perform()
        path.unlink()
        os.link(self.pier / '.urb/state', path)
        with self.assertRaisesRegex(ValueError, 'hard link'):
            self.perform()
        path.unlink()
        os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'special file'):
            self.perform()

    def test_rejects_existing_release_desk_and_unowned_path(self):
        (self.pier / install.DESK).mkdir()
        with self.assertRaisesRegex(ValueError, 'uninstalled synthetic pier'):
            self.perform()
        for name in ('.piers/review', '/tmp/release-install-original', '.runtime/../release-install-original'):
            with self.assertRaisesRegex(ValueError, 'owned disposable'):
                install.checked_clean_copy(name, self.destination, self.artifact, self.lock, self.lockpath, self.checkpoint_sha)

    def test_changed_stopped_state_requires_a_new_explicit_review(self):
        (self.pier / '.urb/state').write_text('changed since review')
        with self.assertRaisesRegex(ValueError, 'explicitly reviewed digest'):
            self.perform()
        self.assertFalse((self.destination / 'zod').exists())

    def test_modified_copy_fails_and_preserves_original(self):
        original = install.checkpoint_tree
        def change(pier, copy_to=None):
            value = original(pier, copy_to)
            if copy_to is not None:
                (copy_to / '.urb/state').write_text('bad copy')
            return value
        before = original(self.pier)
        with patch.object(install, 'checkpoint_tree', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'changed while copied'):
                self.perform()
        self.assertEqual(original(self.pier), before)

    def test_sdk_default_rejects_existing_pier_and_retry_uses_no_creation_flags(self):
        fake = install.Native.__new__(install.Native)
        fake.pier = self.pier
        with self.assertRaisesRegex(ValueError, 'new empty pier'):
            fake._check_pier()
        retry = install.CleanCheckpointNative.__new__(install.CleanCheckpointNative)
        retry.binary, retry.port, retry.http_port, retry.pier = '/runtime/vere', 31337, 18080, self.pier
        arguments = retry._arguments()
        self.assertFalse(any(flag in arguments for flag in ('-F', '-c', '-B', '-A')))
        self.assertEqual(arguments[-1], str(self.pier))


if __name__ == '__main__':
    unittest.main()

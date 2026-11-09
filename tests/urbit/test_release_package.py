"""Real offline Git/filesystem/archive checks; no Urbit or release qualification."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release as release


class ReleasePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='stead-offline-release-')
        cls.root = Path(cls.temporary.name)
        shutil.copytree(ROOT / 'native/core/desk', cls.root / 'native/core/desk')
        paths = ['scripts/package_release.py', 'scripts/package_sdk.py', release.CONTRACT,
                 'specs/urbit/toolchain.lock.json', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
                 'docs/urbit/RELEASE_PACKAGING.md']
        for name in paths:
            target = cls.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        contract = json.loads((cls.root / release.CONTRACT).read_bytes())
        lock = json.loads((cls.root / 'specs/urbit/toolchain.lock.json').read_bytes())
        cls.kernel = '.runtime/' + lock['kernel']['directory'] + '/'
        for name, pin in contract['kernel_files'].items():
            target = cls.root / cls.kernel / pin['source']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(release.read_bounded(ROOT, cls.kernel + pin['source'], release.MAX_FILE))
            if name != 'LICENSE.txt':
                alias = cls.root / cls.kernel / 'pkg/arvo' / name
                alias.parent.mkdir(parents=True, exist_ok=True)
                alias.symlink_to('../../base-dev/' + name)
        def git(*args):
            subprocess.run(['git', '-C', str(cls.root), *args], check=True, capture_output=True)
        git('init', '--quiet')
        git('config', 'user.name', 'Synthetic release test')
        git('config', 'user.email', 'synthetic@example.invalid')
        git('add', 'native', *paths)
        git('commit', '--quiet', '-m', 'Synthetic committed offline package inputs')
        cls.home, cls.home_manifest = release.archive_bytes(cls.root, role='home')
        cls.identity, cls.identity_manifest = release.archive_bytes(cls.root, role='identity')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def members(self, raw=None):
        with tarfile.open(fileobj=io.BytesIO(self.home if raw is None else raw), mode='r:') as archive:
            return {member.name.removeprefix(release.PREFIX): archive.extractfile(member).read() for member in archive}

    def verify(self, raw=None, target=None, expected=None):
        raw = self.home if raw is None else raw
        return release.verify_bytes(raw, expected_sha256=expected or release.digest(raw),
            target=target or release.target_profile(self.home_manifest))

    def repack(self, mutate):
        members = self.members()
        manifest = json.loads(members['manifest.json'])
        mutate(members, manifest)
        manifest['files'] = {name: {'bytes': len(body), 'sha256': release.digest(body)}
                             for name, body in sorted(members.items()) if name != 'manifest.json'}
        members['manifest.json'] = release.encoded(manifest)
        return release.canonical_archive(members)

    def test_two_role_specific_complete_candidate_archives(self):
        for role, raw, manifest in (('home', self.home, self.home_manifest), ('identity', self.identity, self.identity_manifest)):
            with self.subTest(role=role):
                verified = release.verify_bytes(raw, expected_sha256=release.digest(raw), target=release.target_profile(manifest))
                self.assertEqual(verified, manifest)
                files = self.members(raw)
                self.assertIn('desk/app/stead-' + role + '.hoon', files)
                other = 'identity' if role == 'home' else 'home'
                self.assertNotIn('desk/app/stead-' + other + '.hoon', files)
                self.assertEqual(files['desk/sys.kelvin'], b'[%zuse 408]\n')
                self.assertIn('desk/lib/default-agent.hoon', files)
                self.assertIn('desk/lib/skeleton.hoon', files)
                self.assertIn('desk/lib/server.hoon', files)
                self.assertIn('desk/mar/kelvin.hoon', files)
                self.assertIn('desk/mar/bill.hoon', files)
                self.assertIn('notices/urbit-kernel-LICENSE.txt', files)
                self.assertEqual(manifest['saved_state_version'], 4 if role == 'home' else 1)
                self.assertEqual('desk/lib/stead-code-home.hoon' in files, role == 'home')
                self.assertFalse(any('/gen/' in name or '/ted/' in name or '/tests/' in name for name in files))
                self.assertEqual(manifest['qualification']['native_install'], False)

    def test_exact_reproduction_ignores_worktree_mutations(self):
        app = self.root / 'native/core/desk/app/stead-home.hoon'
        original = app.read_bytes()
        try:
            app.write_bytes(b'UNCOMMITTED_PRIVATE_SENTINEL')
            os.utime(app, (123456789, 123456789))
            raw, _ = release.archive_bytes(self.root, role='home')
            self.assertEqual(raw, self.home)
            self.assertNotIn(b'UNCOMMITTED_PRIVATE_SENTINEL', raw)
        finally:
            app.write_bytes(original)

    def test_same_commit_reproduces_in_another_checkout(self):
        with tempfile.TemporaryDirectory(prefix='stead-release-clone-') as temporary:
            clone = Path(temporary) / 'checkout'
            subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(self.root), str(clone)], check=True, capture_output=True)
            shutil.copytree(self.root / '.runtime', clone / '.runtime', symlinks=True)
            raw, _ = release.archive_bytes(clone, role='home')
            self.assertEqual(raw, self.home)

    def test_external_digest_rejects_corruption(self):
        changed = bytearray(self.home)
        changed[len(changed) // 3] ^= 1
        with self.assertRaisesRegex(ValueError, 'digest'):
            self.verify(bytes(changed), expected=release.digest(self.home))

    def test_rejects_mismatched_runtime_state_api_role_and_frontend(self):
        for key, value in [('role', 'identity'), ('kernel_kelvin', 409), ('kernel_kelvin', True),
                           ('kernel_commit', 'a' * 40), ('runtime_version', '4.7'),
                           ('runtime_binary_sha256', 'b' * 64), ('api_version', 4),
                           ('saved_state_version', 2), ('saved_state_version', 3), ('frontend_sha256', 'c' * 64)]:
            with self.subTest(key=key):
                target = release.target_profile(self.home_manifest) | {key: value}
                with self.assertRaisesRegex(ValueError, 'Target compatibility'):
                    self.verify(target=target)

    def test_code_home_cannot_be_relabelled_as_historical_v3(self):
        def relabel(members, manifest):
            contract = json.loads(members['source/release-contract.json'])
            contract['saved_state_versions']['home'] = 3
            members['source/release-contract.json'] = release.encoded(contract)
            manifest['contract_sha256'] = release.digest(members['source/release-contract.json'])
            manifest['saved_state_version'] = 3
        with self.assertRaisesRegex(ValueError, 'Home saved-state profile differs'):
            self.verify(self.repack(relabel), target=release.target_profile(self.home_manifest) | {'saved_state_version': 3})

    def test_rejects_missing_pinned_dependency(self):
        raw = self.repack(lambda members, manifest: members.pop('desk/lib/skeleton.hoon'))
        with self.assertRaisesRegex(ValueError, 'dependency is missing'):
            self.verify(raw)

    def test_rejects_changed_standard_library_despite_rewritten_file_pins(self):
        raw = self.repack(lambda members, manifest: members.__setitem__('desk/lib/server.hoon', b'changed standard code'))
        with self.assertRaisesRegex(ValueError, 'kernel dependency differs'):
            self.verify(raw)

    def test_rejects_extra_private_file_despite_rewritten_file_pins(self):
        raw = self.repack(lambda members, manifest: members.__setitem__('desk/.urb/private-key', b'PRIVATE_SENTINEL'))
        with self.assertRaisesRegex(ValueError, 'outside the reviewed desk closure'):
            self.verify(raw)

    def test_rejects_wrong_kelvin_and_agent_bill(self):
        for name, body in [('desk/sys.kelvin', b'[%zuse 409]\n'), ('desk/desk.bill', b':~ %stead-home %stead-identity ==\n')]:
            raw = self.repack(lambda members, manifest: members.__setitem__(name, body))
            with self.assertRaisesRegex(ValueError, 'Desk compatibility/agents'):
                self.verify(raw)

    def test_rejects_claim_of_native_qualification(self):
        raw = self.repack(lambda members, manifest: manifest['qualification'].update(native_install=True))
        with self.assertRaisesRegex(ValueError, 'cannot claim'):
            self.verify(raw)

    def test_rejects_stale_frontend_payload(self):
        name = next(name for name in self.members() if name.endswith('.stead-asset'))
        raw = self.repack(lambda members, manifest: members.__setitem__(name, b'stale frontend'))
        with self.assertRaisesRegex(ValueError, 'Frontend asset digest'):
            self.verify(raw)

    def test_rejects_trailing_data_even_if_outer_hash_matches(self):
        with self.assertRaisesRegex(ValueError, 'trailing bytes'):
            self.verify(self.home + b'unexpected suffix')

    def test_rejects_duplicate_paths_and_links_without_filesystem_extraction(self):
        for kind in ('duplicate', 'symlink', 'traversal'):
            with self.subTest(kind=kind):
                output = io.BytesIO()
                with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                    info = tarfile.TarInfo(release.PREFIX + ('../escape' if kind == 'traversal' else 'file'))
                    info.mode = 0o644
                    if kind == 'symlink':
                        info.type, info.linkname = tarfile.SYMTYPE, '/tmp/stead-unrelated'
                        archive.addfile(info)
                    else:
                        info.size = 1
                        archive.addfile(info, io.BytesIO(b'x'))
                        if kind == 'duplicate':
                            archive.addfile(info, io.BytesIO(b'y'))
                with self.assertRaises(ValueError):
                    self.verify(output.getvalue())

    def test_build_fails_on_cache_tamper_and_never_refreshes_dependencies(self):
        path = self.root / self.kernel / release.KERNEL_SOURCES['lib/default-agent.hoon']
        original = path.read_bytes()
        try:
            path.write_bytes(b'untrusted cache')
            with self.assertRaisesRegex(ValueError, 'Pinned kernel dependency differs'):
                release.archive_bytes(self.root, role='home')
        finally:
            path.write_bytes(original)

    def test_arvo_aliases_are_not_build_inputs_and_regular_sources_are_recorded(self):
        alias = self.root / self.kernel / 'pkg/arvo/lib/default-agent.hoon'
        self.assertTrue(alias.is_symlink())
        self.assertEqual(os.readlink(alias), '../../base-dev/lib/default-agent.hoon')
        alias.unlink()
        alias.symlink_to('/nonexistent/untrusted-alias')
        try:
            raw, manifest = release.archive_bytes(self.root, role='home')
            self.assertEqual(raw, self.home)
            self.assertEqual(manifest['desk_sources']['lib/default-agent.hoon'],
                             'kernel:pkg/base-dev/lib/default-agent.hoon')
        finally:
            alias.unlink()
            alias.symlink_to('../../base-dev/lib/default-agent.hoon')

    def test_selected_regular_source_must_not_be_a_symlink_even_with_matching_bytes(self):
        path = self.root / self.kernel / release.KERNEL_SOURCES['lib/default-agent.hoon']
        original = path.read_bytes()
        target = path.with_name('same-bytes.hoon')
        target.write_bytes(original)
        path.unlink()
        path.symlink_to(target.name)
        try:
            with self.assertRaisesRegex(ValueError, 'Symlink input'):
                release.archive_bytes(self.root, role='home')
        finally:
            path.unlink()
            path.write_bytes(original)
            target.unlink()

    def test_kernel_contract_cannot_select_alias_or_arbitrary_cache_path(self):
        for source in ('pkg/arvo/lib/default-agent.hoon',
                       '../private/default-agent.hoon', 'pkg/base-dev/lib/server.hoon'):
            def change(members, manifest):
                contract = json.loads(members['source/release-contract.json'])
                contract['kernel_files']['lib/default-agent.hoon']['source'] = source
                members['source/release-contract.json'] = release.encoded(contract)
                manifest['contract_sha256'] = release.digest(members['source/release-contract.json'])
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'Kernel dependency source path'):
                self.verify(self.repack(change))

    def test_output_does_not_overwrite_or_follow_symlink(self):
        output = self.root / 'output.tar'
        output.write_bytes(b'keep original')
        with self.assertRaises(OSError):
            release.write_new(self.root, 'output.tar', self.home)
        self.assertEqual(output.read_bytes(), b'keep original')
        link = self.root / 'link.tar'
        link.symlink_to(output)
        with self.assertRaises(OSError):
            release.write_new(self.root, 'link.tar', self.home)
        self.assertEqual(output.read_bytes(), b'keep original')

    def test_archive_size_bound_precedes_parsing(self):
        raw = b'x' * (release.MAX_ARCHIVE + 1)
        with self.assertRaisesRegex(ValueError, 'size'):
            self.verify(raw)

    def test_duplicate_manifest_key_is_rejected(self):
        members = self.members()
        members['manifest.json'] = members['manifest.json'].replace(b'{', b'{"role":"home",', 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            self.verify(release.canonical_archive(members))

    def test_boolean_state_version_does_not_impersonate_identity_version_one(self):
        target = release.target_profile(self.identity_manifest) | {'saved_state_version': True}
        with self.assertRaisesRegex(ValueError, 'Target compatibility'):
            release.verify_bytes(self.identity, expected_sha256=release.digest(self.identity), target=target)

    def test_git_blob_replacement_cannot_reinterpret_recorded_commit(self):
        original = subprocess.run(['/usr/bin/git', '-C', str(self.root), 'rev-parse',
                                   'HEAD:native/core/desk/app/stead-home.hoon'], check=True, capture_output=True).stdout.decode().strip()
        replacement = subprocess.run(['/usr/bin/git', '-C', str(self.root), 'hash-object', '-w', '--stdin'],
                                     input=b'REPLACEMENT_CONTENT_MUST_NOT_ENTER_RELEASE', check=True, capture_output=True).stdout.decode().strip()
        subprocess.run(['/usr/bin/git', '-C', str(self.root), 'replace', original, replacement], check=True, capture_output=True)
        try:
            raw, _ = release.archive_bytes(self.root, role='home')
            self.assertEqual(raw, self.home)
            self.assertNotIn(b'REPLACEMENT_CONTENT_MUST_NOT_ENTER_RELEASE', raw)
        finally:
            subprocess.run(['/usr/bin/git', '-C', str(self.root), 'replace', '-d', original], check=True, capture_output=True)

    def test_inherited_git_directory_and_config_are_ignored(self):
        with patch.dict(os.environ, {'GIT_DIR': '/nonexistent/foreign-repository', 'GIT_WORK_TREE': '/nonexistent',
                                     'GIT_OBJECT_DIRECTORY': '/nonexistent', 'GIT_CONFIG_COUNT': '1',
                                     'GIT_CONFIG_KEY_0': 'include.path', 'GIT_CONFIG_VALUE_0': '/nonexistent/foreign-config'}):
            raw, _ = release.archive_bytes(self.root, role='home')
        self.assertEqual(raw, self.home)


if __name__ == '__main__':
    unittest.main()

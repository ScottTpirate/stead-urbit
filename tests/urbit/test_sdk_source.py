"""Real local Git/package controls; no SDK compilation or native execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_sdk_source as source_check
import package_sdk_v3 as sdk


class SdkSourceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='stead-sdk-source-')
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        for name in (*sdk.EXPORTS, 'specs/urbit/toolchain.lock.json', 'sdk/v3/export-lock.json'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        self.git('init', '--quiet', '--initial-branch=fixture')
        self.git('add', '.')
        self.git('commit', '--quiet', '-m', 'public SDK fixture')
        self.lock = json.loads((self.root / 'sdk/v3/export-lock.json').read_text())
        self.lock['native_source_commit'] = self.git('rev-parse', 'HEAD').decode().strip()
        self.archive()

    def git(self, *arguments):
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 'SDK fixture',
            'GIT_AUTHOR_EMAIL': 'fixture@example.invalid', 'GIT_COMMITTER_NAME': 'SDK fixture',
            'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
        return subprocess.check_output(['/usr/bin/git', '-C', str(self.root), *arguments],
            env=env, stderr=subprocess.PIPE, timeout=5)

    def archive(self):
        (self.root / 'sdk/v3/export-lock.json').write_text(json.dumps(self.lock))
        raw, _ = sdk.archive_bytes(self.root)
        (self.root / 'sdk.tar').write_bytes(raw)

    def test_complete_archive_binds_all_exports_and_toolchain(self):
        result = source_check.check(self.root, 'sdk.tar')
        self.assertEqual(result['status'], 'pass')
        self.assertFalse(result['native_execution'])
        self.assertFalse(result['independent_consumer_execution'])
        self.assertEqual(result['source_commit'], self.lock['native_source_commit'])
        self.assertEqual({row['source'] for row in result['files']},
            set(sdk.EXPORTS) | {'specs/urbit/toolchain.lock.json'})

    def test_consistent_package_lock_cannot_forge_git_source_identity(self):
        name = 'native/core/desk/lib/stead-codec.hoon'
        path = self.root / name
        raw = path.read_bytes() + b'\n'
        path.write_bytes(raw)
        self.lock['files'][name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        self.archive()  # Package and its lock agree, but the claimed Git commit does not.
        with self.assertRaisesRegex(ValueError, 'blob size differs|source bytes differ'):
            source_check.check(self.root, 'sdk.tar')

    def test_same_size_source_substitution_is_rejected(self):
        name = 'LICENSE'
        raw = (self.root / name).read_bytes().replace(b'Apache', b'APACHE', 1)
        (self.root / name).write_bytes(raw)
        self.lock['files'][name]['sha256'] = hashlib.sha256(raw).hexdigest()
        self.archive()
        with self.assertRaisesRegex(ValueError, 'source bytes differ'):
            source_check.check(self.root, 'sdk.tar')

    def test_missing_commit_fails_without_fetching_history(self):
        self.git('config', 'remote.forbidden.url', 'https://invalid.invalid/never-fetch.git')
        self.git('config', 'remote.forbidden.promisor', 'true')
        self.lock['native_source_commit'] = '0' * 40
        self.archive()
        with self.assertRaisesRegex(ValueError, 'Git object read failed'):
            source_check.check(self.root, 'sdk.tar')
        self.assertFalse((self.root / '.git/FETCH_HEAD').exists())

    def test_missing_promisor_blob_cannot_invoke_fetch_helper(self):
        helper = self.root / 'fetch-helper'
        helper.write_text("#!/usr/bin/python3\nfrom pathlib import Path\nPath(__file__).with_name('fetch-called').touch()\nraise SystemExit(1)\n")
        helper.chmod(0o700)
        self.git('config', 'protocol.ext.allow', 'always')
        self.git('config', 'remote.forbidden.url', 'ext::' + str(helper))
        self.git('config', 'remote.forbidden.promisor', 'true')
        oid = self.git('rev-parse', 'HEAD:LICENSE').decode().strip()
        (self.root / '.git/objects' / oid[:2] / oid[2:]).unlink()
        with self.assertRaisesRegex(ValueError, 'Git object read failed'):
            source_check.check(self.root, 'sdk.tar')
        self.assertFalse((self.root / 'fetch-called').exists())
        self.assertFalse((self.root / '.git/FETCH_HEAD').exists())

    def test_tag_object_is_not_a_commit_identity(self):
        self.git('tag', '-a', 'sdk', '-m', 'fixture tag')
        self.lock['native_source_commit'] = self.git('rev-parse', 'sdk').decode().strip()
        self.archive()
        with self.assertRaisesRegex(ValueError, 'not the exact commit'):
            source_check.check(self.root, 'sdk.tar')

    def test_git_symlink_cannot_masquerade_as_regular_export(self):
        path = self.root / 'LICENSE'
        raw = path.read_bytes()
        path.unlink()
        path.symlink_to('THIRD_PARTY_NOTICES.md')
        self.git('add', 'LICENSE')
        self.git('commit', '--quiet', '-m', 'symlink control')
        self.lock['native_source_commit'] = self.git('rev-parse', 'HEAD').decode().strip()
        path.unlink()
        path.write_bytes(raw)
        self.archive()
        with self.assertRaisesRegex(ValueError, 'exact regular source'):
            source_check.check(self.root, 'sdk.tar')

    def test_git_replacement_cannot_change_source_bytes(self):
        original = self.git('rev-parse', 'HEAD:LICENSE').decode().strip()
        replacement = self.git('rev-parse', 'HEAD:THIRD_PARTY_NOTICES.md').decode().strip()
        self.git('replace', original, replacement)
        self.assertEqual(source_check.check(self.root, 'sdk.tar')['status'], 'pass')

    def test_corrupt_object_store_cannot_forge_the_original_blob_oid(self):
        oid = self.git('rev-parse', 'HEAD:LICENSE').decode().strip()
        raw = (self.root / 'LICENSE').read_bytes().replace(b'Apache', b'APACHE', 1)
        (self.root / 'LICENSE').write_bytes(raw)
        self.lock['files']['LICENSE']['sha256'] = hashlib.sha256(raw).hexdigest()
        object_path = self.root / '.git/objects' / oid[:2] / oid[2:]
        object_path.chmod(0o600)
        object_path.write_bytes(zlib.compress(b'blob ' + str(len(raw)).encode() + b'\0' + raw))
        self.archive()
        with self.assertRaisesRegex(ValueError, 'blob object identity differs'):
            source_check.check(self.root, 'sdk.tar')

    def test_oversized_git_output_is_stopped_and_descriptors_closed(self):
        oid = self.git('rev-parse', 'HEAD:LICENSE').decode().strip()
        before = set(Path('/proc/self/fd').iterdir())
        with self.assertRaisesRegex(ValueError, 'output exceeds its bound'):
            source_check.git_bytes(self.root, ['cat-file', 'blob', oid], 32)
        self.assertEqual(set(Path('/proc/self/fd').iterdir()), before)

    def test_altered_archive_fails_before_git_binding(self):
        path = self.root / 'sdk.tar'
        path.write_bytes(path.read_bytes() + b'additional data')
        with self.assertRaisesRegex(ValueError, 'differs from the canonical package'):
            source_check.check(self.root, 'sdk.tar')


if __name__ == '__main__':
    unittest.main()

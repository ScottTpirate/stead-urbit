"""Stock Git and synthetic data coverage for the offline Code archive."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import portable_code as code

PROJECT = '019939ba-4000-7000-8000-000000000001'


class CodeArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repository = self.root / 'source.git'
        self.git = shutil.which('git')
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': temporary.name, 'LANG': 'C.UTF-8',
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                    'GIT_AUTHOR_NAME': 'Fixture', 'GIT_AUTHOR_EMAIL': 'author@stead.invalid',
                    'GIT_COMMITTER_NAME': 'Fixture', 'GIT_COMMITTER_EMAIL': 'committer@stead.invalid',
                    'GIT_AUTHOR_DATE': '1790520000 +0000', 'GIT_COMMITTER_DATE': '1790520000 +0000'}
        self.repository.mkdir(mode=0o700)
        self.run_git('init', '--bare', '--template=', '--object-format=sha1')
        self.first = self.commit(b'old source\n')
        self.main = self.commit(b'new \x00source\r\n', self.first)
        self.side = self.commit(b'side source\n', self.first)
        self.run_git('symbolic-ref', 'HEAD', 'refs/heads/main')
        self.run_git('update-ref', 'refs/heads/main', self.main)
        self.run_git('update-ref', b'refs/heads/topic/\xff', self.side)
        self.run_git('tag', '-a', 'v1', '-m', 'Exact annotated tag', self.first)
        self.run_git('tag', 'current', self.main)
        self.unreachable = self.run_git('hash-object', '-w', '--stdin', data=b'outside snapshot').strip().decode()

    def run_git(self, *args, repository=None, data=None, configured=True):
        argv = [self.git]
        if configured:
            argv += ['--git-dir', str(repository or self.repository)]
        return subprocess.run([*argv, *args], input=data, capture_output=True, check=True,
                              env=self.env, timeout=15).stdout

    def commit(self, body, parent=None):
        blob = self.run_git('hash-object', '-w', '--stdin', data=body).strip()
        tree = self.run_git('mktree', data=b'100644 blob ' + blob + b'\tfile.bin\n').strip()
        parents = ['-p', parent] if parent else []
        return self.run_git('commit-tree', tree, *parents, '-m', 'Fixture commit').strip().decode()

    def collect(self):
        return code.collect(self.repository, PROJECT, self.git)

    def cli(self, *args):
        script = Path(code.__file__).resolve()
        env = {**self.env, 'PATH': f'{Path(self.git).parent}:/usr/bin:/bin'}
        result = subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                                capture_output=True, check=True, env=env, timeout=15)
        return json.loads(result.stdout)

    def test_cli_round_trip_reproduces_refs_ancestry_and_annotated_tag(self):
        clone = self.root / 'clone.git'
        self.run_git('clone', '--no-local', '--bare', self.repository, clone, configured=False)
        clone.chmod(0o700)
        archive = self.root / 'code.json'
        second = self.root / 'copy.json'
        self.assertEqual(self.cli('create', clone, archive, '--project', PROJECT)['status'], 'created')
        self.assertEqual(self.cli('create', clone, second, '--project', PROJECT)['status'], 'created')
        self.assertEqual(archive.read_bytes(), second.read_bytes())
        digest = code.sha(archive.read_bytes())
        value = code.read_archive(archive, digest)
        self.assertNotIn(self.unreachable, value['objects'])
        self.assertEqual(value['refs'][b'refs/heads/topic/\xff'.hex()], self.side)
        self.assertEqual(self.cli('verify', archive, '--sha256', digest)['status'], 'integrity-verified')
        destination = self.root / 'restored.git'
        self.assertEqual(self.cli('restore', archive, destination, '--sha256', digest)['status'], 'offline-git-restored')
        self.assertEqual(destination.stat().st_mode & 0o777, 0o700)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.run_git('for-each-ref'), self.run_git('for-each-ref', repository=destination))
        self.assertEqual(self.run_git('rev-list', '--parents', '--all'),
                         self.run_git('rev-list', '--parents', '--all', repository=destination))
        self.assertEqual(self.run_git('cat-file', 'tag', 'v1'),
                         self.run_git('cat-file', 'tag', 'v1', repository=destination))
        self.assertEqual(self.run_git('show', 'main:file.bin', repository=destination), b'new \x00source\r\n')
        self.run_git('fsck', '--full', '--strict', repository=destination)

        received = self.root / 'received.git'
        received.mkdir(mode=0o700)
        self.run_git('init', '--bare', '--template=', '--object-format=sha1', repository=received)
        self.run_git('push', '--atomic', received, 'refs/heads/*:refs/heads/*',
                     'refs/tags/*:refs/tags/*', repository=destination)
        self.assertEqual(self.run_git('for-each-ref'), self.run_git('for-each-ref', repository=received))

    def test_valid_object_outside_refs_cannot_be_restored(self):
        value = self.collect()
        body = b'unrelated content'
        oid = hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest()
        value['objects'][oid] = {'kind': 'blob', 'bytes_hex': body.hex()}
        destination = self.root / 'new'
        with self.assertRaisesRegex(ValueError, 'object-closure'):
            code.restore(value, destination, self.git)
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.root.glob('.code-restore-*')))

    def test_wrong_digest_and_resealed_object_tamper(self):
        value = self.collect()
        archive = self.root / 'archive'
        original = code.write_archive(archive, value)
        row = value['objects'][self.main]
        row['bytes_hex'] = ('ff' if row['bytes_hex'][:2] == '00' else '00') + row['bytes_hex'][2:]
        raw = code.encoded(value)
        archive.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'archive-digest'):
            code.read_archive(archive, original)
        with self.assertRaisesRegex(ValueError, 'object-digest'):
            code.read_archive(archive, code.sha(raw))

    def test_missing_ancestor_cannot_publish_partial_repository(self):
        value = self.collect()
        self.assertNotIn(self.first, value['refs'].values())
        # The first commit is reached by both branches and the annotated tag.
        del value['objects'][self.first]
        destination = self.root / 'missing'
        with self.assertRaisesRegex(ValueError, 'git-verification-failed'):
            code.restore(value, destination, self.git)
        self.assertFalse(destination.exists())

    def test_redirected_object_database_is_rejected(self):
        original = self.repository / 'objects'
        moved = self.root / 'external'
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'external-source-state'):
            self.collect()

    def test_existing_directory_symlink_and_archive_are_not_replaced(self):
        value = self.collect()
        archive = self.root / 'archive'
        code.write_archive(archive, value)
        with self.assertRaises(FileExistsError):
            code.write_archive(archive, value)
        target = self.root / 'existing'
        target.mkdir()
        with self.assertRaisesRegex(ValueError, 'destination-exists'):
            code.restore(value, target, self.git)
        self.assertEqual(list(target.iterdir()), [])
        alias = self.root / 'symlink'
        alias.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'destination-exists'):
            code.restore(value, alias, self.git)
        alias.unlink()
        alias.symlink_to(archive)
        with self.assertRaises(OSError):
            code.read_archive(alias, code.sha(archive.read_bytes()))

    def test_publication_refuses_a_target_created_after_initial_check(self):
        value = self.collect()
        target = self.root / 'racing-target'
        real_publish = code.publish_directory

        def race(parent, stage, destination):
            os.mkdir(destination, dir_fd=parent)
            real_publish(parent, stage, destination)

        with patch.object(code, 'publish_directory', side_effect=race), self.assertRaises(FileExistsError):
            code.restore(value, target, self.git)
        self.assertEqual(list(target.iterdir()), [])
        self.assertFalse(list(self.root.glob('.code-restore-*')))

    def test_unborn_and_detached_branch_tip_head_round_trip(self):
        self.run_git('update-ref', '--no-deref', 'HEAD', self.main)
        detached = self.collect()
        output = self.root / 'detached.git'
        code.restore(detached, output, self.git)
        self.assertEqual((output / 'HEAD').read_text(), self.main + '\n')
        self.run_git('symbolic-ref', 'HEAD', 'refs/heads/empty')
        for name in ['refs/heads/main', b'refs/heads/topic/\xff', 'refs/tags/v1', 'refs/tags/current']:
            self.run_git('update-ref', '-d', name)
        empty = self.collect()
        self.assertEqual(empty['objects'], {})
        output = self.root / 'empty.git'
        code.restore(empty, output, self.git)
        self.assertEqual((output / 'HEAD').read_bytes(), b'ref: refs/heads/empty\n')

    def test_external_config_alternates_and_unexpected_ref_are_rejected(self):
        alternates = self.repository / 'objects/info/alternates'
        alternates.write_text('/outside\n')
        with self.assertRaisesRegex(ValueError, 'external-source-state'):
            self.collect()
        alternates.unlink()
        self.run_git('config', '--add', 'include.path', '/outside')
        with self.assertRaisesRegex(ValueError, 'unsupported-source-config'):
            self.collect()
        self.run_git('config', '--unset', 'include.path')
        self.run_git('update-ref', 'refs/private/hidden', self.main)
        with self.assertRaisesRegex(ValueError, 'ref-name'):
            self.collect()


if __name__ == '__main__':
    unittest.main()

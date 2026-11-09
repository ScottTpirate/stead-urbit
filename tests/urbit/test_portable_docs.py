"""Offline round trips using stock Git and synthetic Docs histories."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import portable_docs as docs

PROJECT = '019939ba-4000-7000-8000-000000000001'
CONTAINER = '019939ba-4000-7000-8000-000000000002'
DOCUMENT = '019939ba-4000-7000-8000-000000000003'


class DocsArchiveTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.repo = self.root / 'original'
        self.git = shutil.which('git')
        self.env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 'Synthetic author',
                    'GIT_AUTHOR_EMAIL': 'author@stead.invalid', 'GIT_COMMITTER_NAME': 'Synthetic operator',
                    'GIT_COMMITTER_EMAIL': 'operator@stead.invalid',
                    'GIT_AUTHOR_DATE': '1790520000 +0000', 'GIT_COMMITTER_DATE': '1790520000 +0000'}
        self.run_git('init', '--bare', '--template=', '--object-format=sha1', str(self.repo), bare=False)
        self.body = (f'---\nid: {DOCUMENT}\ntype: page\nstate: published\n---\n# Example 東京\n\n  keep spacing\n').encode()
        self.old = self.commit(self.body + b'First revision\n')
        self.head = self.commit(self.body, self.old)
        self.run_git('symbolic-ref', 'HEAD', 'refs/heads/main')
        self.run_git('update-ref', 'refs/heads/main', self.head)

    def run_git(self, *args, body=None, bare=True):
        prefix = [self.git, '--git-dir', str(self.repo)] if bare else [self.git]
        return subprocess.run([*prefix, *args], input=body, capture_output=True, check=True,
                              env=self.env, timeout=15).stdout

    def commit(self, body, parent=None):
        blob = self.run_git('hash-object', '-w', '--stdin', body=body).decode().strip()
        tree = self.run_git('mktree', body=f'100644 blob {blob}\t{DOCUMENT}.md\n'.encode()).decode().strip()
        parents = ['-p', parent] if parent else []
        return self.run_git('commit-tree', tree, *parents, '-m', 'Example change').decode().strip()

    def archive(self):
        return docs.collect(self.repo, PROJECT, CONTAINER, self.head, self.git)

    def test_reproducible_archive_restores_exact_objects_and_history(self):
        archive = self.root / 'docs.json'
        digest = docs.write_archive(archive, self.archive())
        self.assertEqual(docs.write_archive(self.root / 'copy.json', self.archive()), digest)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        data = docs.read_archive(archive, digest)
        output = self.root / 'restored'
        report = docs.recover(data, output, self.git)
        self.assertEqual(report['head'], self.head)
        self.assertEqual(report['commits'][0], f'{self.head} {self.old}')
        self.assertEqual(report['files'], {f'{DOCUMENT}.md': self.body})
        self.assertEqual(docs.git_read(self.git, output, 'cat-file', 'commit', self.head),
                         self.run_git('cat-file', 'commit', self.head))
        with self.assertRaises(FileExistsError):
            docs.write_archive(archive, data)

    def test_wrong_external_digest_and_resealed_object_tamper(self):
        archive = self.root / 'docs.json'
        data = self.archive()
        original = docs.write_archive(archive, data)
        data['objects'][self.head]['hex'] = '00' + data['objects'][self.head]['hex'][2:]
        raw = docs.canonical(data)
        archive.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'Archive SHA-256'):
            docs.read_archive(archive, original)
        with self.assertRaisesRegex(ValueError, 'Git object digest'):
            docs.read_archive(archive, hashlib.sha256(raw).hexdigest())

    def test_ref_mismatch_and_unreachable_object_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'HEAD differs'):
            docs.collect(self.repo, PROJECT, CONTAINER, self.old, self.git)
        data = self.archive()
        body = b'unrelated project content'
        oid = hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest()
        data['objects'][oid] = {'kind': 'blob', 'byte_length': len(body), 'hex': body.hex()}
        with self.assertRaisesRegex(ValueError, 'unreachable'):
            docs.recover(data, self.root / 'restore', self.git)

    def test_output_and_input_refuse_symlinks(self):
        archive = self.root / 'docs.json'
        digest = docs.write_archive(archive, self.archive())
        alias = self.root / 'alias'
        alias.symlink_to(archive)
        with self.assertRaises(OSError):
            docs.read_archive(alias, digest)
        with self.assertRaises(FileExistsError):
            docs.write_archive(alias, self.archive())
        self.assertEqual(docs.read_archive(archive, digest)['head'], self.head)

    def test_git_read_is_offline_and_caps_streamed_output(self):
        probe = self.root / 'git-probe'
        probe.write_text(
            f'#!{sys.executable}\n'
            'import os,sys\n'
            'assert os.environ["GIT_NO_LAZY_FETCH"] == "1"\n'
            'assert os.environ["GIT_ALLOW_PROTOCOL"] == ""\n'
            'sys.stdout.buffer.write(b"x" * 65537)\n'
        )
        probe.chmod(0o700)
        with self.assertRaisesRegex(ValueError, 'output exceeded'):
            docs.git_read(str(probe), self.repo, 'cat-file')


if __name__ == '__main__':
    unittest.main()

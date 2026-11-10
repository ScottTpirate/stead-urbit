"""Stock Git tests for immutable private pack snapshots and offline restore."""
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_store as store
from dogfood_rehearsal import Git


BRANCH = 'refs/heads/main'
TAG = 'refs/tags/v1'
SCOPE = {'home': '~zod', 'project_id': '019939ba-4000-7000-8000-000000000001',
         'repository_id': '019939ba-4000-7000-8000-000000000002', 'authority_epoch': '1'}


class PackStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.storage = self.root / 'store'
        self.storage.mkdir(mode=0o700)
        self.binary = shutil.which('git')
        self.git = Git(self.binary, self.root / 'source.git')
        self.git.init_bare(BRANCH)
        self.first = self.commit(b'binary source\x00\r\n')
        self.tip = self.commit(b'binary source\x00\r\nrevised', self.first)
        self.git.run('update-ref', BRANCH, self.tip)
        self.git.run('tag', '-a', 'v1', self.first, '-m', 'Original annotated tag')
        self.git.run('update-ref', b'refs/heads/topic/\xff', self.first)
        self.refs = {os.fsencode(name).hex(): oid for name, oid in self.git.refs().items()}
        self.roots = ''.join(oid + '\n' for oid in sorted(set(self.refs.values()))).encode('ascii')
        self.pack = self.root / 'source.pack'
        self.write_pack(self.git.run('pack-objects', '--stdout', '--revs', '--delta-base-offset',
                                    data=self.roots).stdout)

    def commit(self, content, parent=None):
        blob = self.git.run('hash-object', '-w', '--stdin', data=content).stdout.strip()
        tree = self.git.run('mktree', data=b'100644 blob ' + blob + b'\tfile.bin\n').stdout.strip()
        parents = ['-p', parent] if parent else []
        return self.git.run('commit-tree', tree, *parents, '-m', 'Fixture commit').stdout.strip().decode()

    def write_pack(self, raw):
        self.pack.write_bytes(raw)
        self.pack.chmod(0o600)
        self.digest = hashlib.sha256(raw).hexdigest()

    def stage(self, *, scope=SCOPE, digest=None):
        return store.stage(self.storage, self.pack, digest or self.digest, scope, self.refs,
                           BRANCH.encode().hex(), self.binary)

    def repository(self):
        return self.storage / '.'.join(SCOPE[key] for key in ('home', 'project_id', 'repository_id'))

    def test_stock_git_restores_exact_refs_pack_and_annotated_tag(self):
        snapshot, value = self.stage()
        self.assertEqual(self.stage(), (snapshot, value))
        entry = self.repository() / snapshot
        self.assertEqual(sorted(p.name for p in entry.iterdir()), ['objects.pack', 'snapshot.json'])
        self.assertEqual((entry / 'objects.pack').read_bytes(), self.pack.read_bytes())
        self.assertEqual(value['object_count'], 7)
        target = self.root / 'restored.git'
        self.assertEqual(store.restore(self.storage, snapshot, SCOPE, target, self.binary), value)
        restored = Git(self.binary, target)
        self.assertEqual(restored.refs(), self.git.refs())
        self.assertEqual(restored.run('cat-file', 'tag', TAG).stdout, self.git.run('cat-file', 'tag', TAG).stdout)
        self.assertEqual(restored.run('show', 'main:file.bin').stdout, b'binary source\x00\r\nrevised')
        restored.run('fsck', '--full', '--strict')
        clone = self.root / 'clone.git'
        restored.run('clone', '--no-local', '--bare', target, clone)
        self.assertEqual(Git(self.binary, clone).refs(), restored.refs())

    def test_rejects_bad_integrity_quota_and_outside_closure(self):
        raw = self.pack.read_bytes()
        with patch.object(store, 'MAX_OBJECT', 4):
            with self.assertRaisesRegex(ValueError, 'object-byte-limit'):
                self.stage()
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            self.stage(digest='0' * 64)
        self.write_pack(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'git-verification-failed'):
            self.stage()
        self.write_pack(raw[:8] + struct.pack('>I', store.MAX_OBJECTS + 1) + raw[12:])
        with self.assertRaisesRegex(ValueError, 'pack-object-limit'):
            self.stage()
        unrelated = self.git.run('hash-object', '-w', '--stdin', data=b'unrelated').stdout.strip()
        extra = self.git.run('pack-objects', '--stdout', '--revs', data=self.roots + unrelated + b'\n').stdout
        self.write_pack(extra)
        with self.assertRaisesRegex(ValueError, 'pack-ref-closure'):
            self.stage()
        self.assertEqual(list(self.repository().iterdir()), [])

    def test_restore_requires_exact_scope_digest_and_untampered_pack(self):
        snapshot, _ = self.stage()
        target = self.root / 'restored.git'
        with self.assertRaisesRegex(ValueError, 'snapshot-scope'):
            store.restore(self.storage, snapshot, SCOPE | {'authority_epoch': '2'}, target, self.binary)
        with self.assertRaises(OSError):
            store.restore(self.storage, '0' * 64, SCOPE, target, self.binary)
        with self.assertRaises(OSError):
            store.restore(self.storage, snapshot, SCOPE | {'home': '~nec'}, target, self.binary)
        stored = self.repository() / snapshot / 'objects.pack'
        raw = stored.read_bytes()
        stored.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            self.stage()
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            store.restore(self.storage, snapshot, SCOPE, target, self.binary)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob('.code-restore-*')))

    def test_atomic_replay_at_capacity_and_concurrent_writer(self):
        snapshot, value = self.stage()
        with patch.object(store, 'MAX_SNAPSHOTS', 1):
            self.assertEqual(self.stage(), (snapshot, value))
            with self.assertRaisesRegex(ValueError, 'snapshot-capacity'):
                self.stage(scope=SCOPE | {'authority_epoch': '2'})
        with store.directory_fd(self.repository()) as directory:
            fcntl.flock(directory, fcntl.LOCK_EX)
            with self.assertRaises(BlockingIOError):
                self.stage()
        self.assertEqual([path.name for path in self.repository().iterdir()], [snapshot])

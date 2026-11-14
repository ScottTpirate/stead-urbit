"""Stock-Git checks for preparing external push snapshots."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from dogfood_rehearsal import Git
import git_pack_push as push
import git_pack_store as store
from portable_recovery import sha


MAIN = b'refs/heads/main'.hex()
TOPIC = b'refs/heads/topic/\xff'.hex()
TAG = b'refs/tags/first'.hex()
NEW_TAG = b'refs/tags/second'.hex()
SCOPE = {'home': '~zod', 'project_id': '019939ba-4000-7000-8000-000000000001',
         'repository_id': '019939ba-4000-7000-8000-000000000001', 'authority_epoch': '1'}
UPLOAD_SHA256 = sha(b'complete fixture wire request')


def update(ref, prior, target):
    return {'ref': ref, 'prior': prior, 'target': target}


class PackPushTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.storage = self.root / 'store'
        self.storage.mkdir(mode=0o700)
        self.binary = shutil.which('git')
        self.source = Git(self.binary, self.root / 'source.git')
        self.source.init_bare('refs/heads/main')
        self.first = self.commit(b'original\0content')
        self.second = self.commit(b'revised\r\ncontent', self.first)
        self.other = self.commit(b'unrelated')
        self.source.run('tag', '-a', 'first', self.first, '-m', 'Original annotated tag')
        self.tag = self.source.run('rev-parse', 'refs/tags/first').stdout.strip().decode()
        self.base_refs = {MAIN: self.first, TAG: self.tag}
        pack, digest = self.pack('base', self.base_refs.values())
        self.base_snapshot, self.base_manifest = store.stage(
            self.storage, pack, digest, SCOPE, self.base_refs, MAIN, self.binary)

    def commit(self, content, parent=None):
        blob = self.source.run('hash-object', '-w', '--stdin', data=content).stdout.strip()
        tree = self.source.run('mktree', data=b'100644 blob ' + blob + b'\tfile.bin\n').stdout.strip()
        parents = ('-p', parent) if parent else ()
        return self.source.run('commit-tree', tree, *parents, '-m', 'Fixture commit').stdout.strip().decode()

    def pack(self, name, roots):
        data = b''.join(oid.encode('ascii') + b'\n' for oid in sorted(set(roots)))
        raw = self.source.run('pack-objects', '--stdout', '--revs', '--delta-base-offset', '--threads=1',
                              data=data).stdout
        path = self.root / (name + '.pack')
        path.write_bytes(raw)
        path.chmod(0o600)
        return path, sha(raw)

    def prepare(self, roots, changes, *, scope=SCOPE):
        pack, digest = self.pack('candidate', roots)
        return push.prepare(self.storage, scope, self.base_snapshot, pack, digest, changes, self.binary,
                            upload_sha256=UPLOAD_SHA256)

    def snapshots(self):
        entries = self.storage / '.'.join(SCOPE[field] for field in ('home', 'project_id', 'repository_id'))
        return {path.name for path in entries.iterdir()}

    def test_verified_candidate_preserves_exact_refs_and_wire_order(self):
        refs = {MAIN: self.second, TAG: self.tag, TOPIC: self.first, NEW_TAG: self.second}
        changes = [update(NEW_TAG, push.ZERO_OID, self.second), update(TOPIC, push.ZERO_OID, self.first),
                   update(MAIN, self.first, self.second)]
        result = self.prepare(refs.values(), changes)
        candidate = result['candidate_snapshot']
        self.assertEqual(result['status'], 'candidate-staged')
        self.assertEqual(result['scope'], SCOPE)
        self.assertEqual(result['base_snapshot'], self.base_snapshot)
        self.assertEqual(result['upload_sha256'], UPLOAD_SHA256)
        self.assertEqual(result['changes'], [
            {**change, 'action': action, 'target_kind': 'commit'}
            for change, action in zip(changes, ('create', 'create', 'fast-forward'))])
        self.assertEqual(result['manifest']['refs'], refs)
        self.assertEqual(self.snapshots(), {self.base_snapshot, candidate})
        self.assertEqual(self.prepare(refs.values(), changes), result)

        for label, snapshot, expected in [('accepted', self.base_snapshot, self.base_refs), ('staged', candidate, refs)]:
            dest = self.root / (label + '.git')
            manifest = store.restore(self.storage, snapshot, SCOPE, dest, self.binary)
            restored = Git(self.binary, dest)
            self.assertEqual(manifest['refs'], expected)
            self.assertEqual({os.fsencode(ref).hex(): oid for ref, oid in restored.refs().items()}, expected)
            restored.run('fsck', '--full', '--strict')

    def test_rejects_stale_duplicate_unchanged_deleted_and_rewritten_tags(self):
        tests = [
            ([update(MAIN, self.second, self.other)], 'stale-ref'),
            ([update(MAIN, self.first, self.second)] * 2, 'duplicate-ref'),
            ([update(MAIN, self.first, self.first)], 'unchanged-ref'),
            ([update(MAIN, self.first, push.ZERO_OID)], 'ref-delete-unsupported'),
            ([update(TAG, self.tag, self.second)], 'tag-replacement'),
        ]
        for changes, error in tests:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.prepare(self.base_refs.values(), changes)
        self.assertEqual(self.snapshots(), {self.base_snapshot})

    def test_rejects_non_fast_forward_and_objects_outside_explicit_transition(self):
        with self.assertRaisesRegex(ValueError, 'non-fast-forward'):
            self.prepare([self.other, self.tag], [update(MAIN, self.first, self.other)])
        with self.assertRaisesRegex(ValueError, 'pack-ref-closure'):
            self.prepare([self.second, self.tag, self.other], [update(MAIN, self.first, self.second)])
        self.assertEqual(self.snapshots(), {self.base_snapshot})

    def test_scope_and_base_integrity_required(self):
        changes = [update(MAIN, self.first, self.second)]
        with self.assertRaisesRegex(ValueError, 'snapshot-scope'):
            self.prepare([self.second, self.tag], changes, scope=SCOPE | {'authority_epoch': '2'})
        entry = self.storage / '.'.join(SCOPE[field] for field in ('home', 'project_id', 'repository_id'))
        base = entry / self.base_snapshot / store.PACK_NAME
        raw = base.read_bytes()
        base.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            self.prepare([self.second, self.tag], changes)
        self.assertEqual(self.snapshots(), {self.base_snapshot})

    def test_expired_preparation_staging_deadline_never_publishes(self):
        pack, digest = self.pack('candidate', [self.second, self.tag])
        with self.assertRaisesRegex(ValueError, 'git-timeout'):
            store.stage(self.storage, pack, digest, SCOPE, {MAIN: self.second, TAG: self.tag}, MAIN,
                        self.binary, deadline=time.monotonic())
        with patch.object(push, 'MAX_GIT_TIME', 0.0):
            with self.assertRaisesRegex(ValueError, 'git-timeout'):
                self.prepare([self.second, self.tag], [update(MAIN, self.first, self.second)])
        sync_tree = store.sync_tree
        deadline = time.monotonic() + 10
        clock = SimpleNamespace(now=deadline - 1)
        def sync_at_deadline(git):
            sync_tree(git)
            clock.now = deadline

        with patch.object(store, 'time', SimpleNamespace(monotonic=lambda: clock.now)), \
                patch.object(store, 'sync_tree', side_effect=sync_at_deadline):
            with self.assertRaisesRegex(ValueError, 'git-timeout'):
                store.stage(self.storage, pack, digest, SCOPE, {MAIN: self.second, TAG: self.tag}, MAIN,
                            self.binary, deadline=deadline)
        self.assertEqual(self.snapshots(), {self.base_snapshot})


if __name__ == '__main__':
    unittest.main()

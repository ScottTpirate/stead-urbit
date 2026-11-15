"""Read-only repository browsing against a local stock Git fixture."""
from hashlib import sha256
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from dogfood_rehearsal import Git
import git_pack_browse as browse
import git_pack_store as store
from portable_recovery import encoded


PROJECT = '019939ba-4000-7000-8000-000000000001'
BRANCH = b'refs/heads/main'
TAG = b'refs/tags/v1'
SCOPE = {'home': '~zod', 'project_id': PROJECT, 'repository_id': PROJECT, 'authority_epoch': '1'}


class PackBrowseTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.store = root / 'store'
        self.store.mkdir(mode=0o700)
        self.binary = shutil.which('git')
        self.git = Git(self.binary, root / 'source.git')
        self.git.init_bare(BRANCH.decode())
        self.first = self.commit(b'First version\n')
        self.current = self.commit('Current version — now accepted\n'.encode(), self.first)
        self.git.run('update-ref', BRANCH, self.current)
        self.git.run('tag', '-a', 'v1', self.first, '-m', 'Original annotated tag')
        self.refs = {name.encode().hex(): oid for name, oid in self.git.refs().items()}
        roots = ''.join(oid + '\n' for oid in self.refs.values()).encode('ascii')
        raw = self.git.run('pack-objects', '--stdout', '--revs', data=roots).stdout
        pack = root / 'source.pack'
        pack.write_bytes(raw)
        pack.chmod(0o600)
        self.snapshot, manifest = store.stage(self.store, pack, sha256(raw).hexdigest(), SCOPE, self.refs,
                                              BRANCH.hex(), self.binary)
        self.report = {'protocol': 'stead.code/1', 'status': 'external', 'snapshot': self.snapshot,
                       'authority_epoch': SCOPE['authority_epoch'], 'object_count': str(manifest['object_count']),
                       'head': BRANCH.hex(), 'refs': encoded(self.refs).decode(), 'request_id': PROJECT,
                       'accepted_at_ms': '123', 'generation': '0', 'generation_limit': '80'}

    def tree(self, entries):
        rows = b''.join(mode + b' ' + kind + b' ' + oid + b'\t' + name + b'\0'
                        for mode, kind, oid, name in entries)
        return self.git.run('mktree', '-z', data=rows).stdout.strip()

    def blob(self, raw):
        return self.git.run('hash-object', '-w', '--stdin', data=raw).stdout.strip()

    def commit(self, raw, parent=None):
        nested = self.tree([(b'100644', b'blob', self.blob(raw), b'--show\xff\t.txt')])
        tree = self.tree([(b'040000', b'tree', nested, b'lib'),
                          (b'100755', b'blob', self.blob(b''), b'empty'),
                          (b'100644', b'blob', self.blob(b'\0binary'), b'image'),
                          (b'100644', b'blob', self.blob(b'\xff'), b'invalid-utf8'),
                          (b'100644', b'blob', self.blob(b'x' * (browse.MAX_TEXT + 1)), b'large'),
                          (b'120000', b'blob', self.blob(b'lib'), b'link')])
        parents = ['-p', parent] if parent else []
        return self.git.run('commit-tree', tree, *parents, '-m', 'Browse fixture').stdout.strip().decode()

    def request(self, ref=BRANCH, path=(), view='tree'):
        return {'protocol': browse.PROTOCOL, 'project_id': PROJECT, 'snapshot': self.snapshot,
                'ref': ref.hex(), 'path': [name.hex() for name in path], 'view': view}

    def read(self, ref=BRANCH, path=(), view='tree'):
        return browse.browse(lambda: self.report, SCOPE['home'], self.request(ref, path, view), self.store, self.binary)

    def test_traverses_raw_tree_names_and_annotation_preserves_revision(self):
        root = self.read()
        self.assertEqual(root['commit'], self.current)
        self.assertFalse(root['truncated'])
        entries = {bytes.fromhex(row['name']): row['kind'] for row in root['entries']}
        self.assertEqual(entries, {b'lib': 'tree', b'empty': 'file', b'image': 'file', b'invalid-utf8': 'file',
                                   b'large': 'file', b'link': 'symlink'})
        raw_name = b'--show\xff\t.txt'
        folder = self.read(path=(b'lib',))
        self.assertEqual(folder['entries'][0]['name'], raw_name.hex())
        current = self.read(path=(b'lib', raw_name), view='file')
        tagged = self.read(ref=TAG, path=(b'lib', raw_name), view='file')
        self.assertEqual((current['commit'], current['preview'], current['text']),
                         (self.current, 'text', 'Current version — now accepted\n'))
        self.assertEqual((tagged['commit'], tagged['preview'], tagged['text']),
                         (self.first, 'text', 'First version\n'))

    def test_bounded_listing_and_text_only(self):
        with patch.object(browse, 'MAX_ENTRIES', 2):
            result = self.read()
            self.assertEqual(len(result['entries']), 2)
            self.assertTrue(result['truncated'])
        for name, status, size in [(b'image', 'binary', 7), (b'invalid-utf8', 'binary', 1),
                                   (b'large', 'too-large', browse.MAX_TEXT + 1)]:
            with self.subTest(name=name):
                result = self.read(path=(name,), view='file')
                self.assertEqual((result['preview'], result['bytes']), (status, size))
                self.assertNotIn('text', result)
        empty = self.read(path=(b'empty',), view='file')
        self.assertEqual((empty['preview'], empty['bytes'], empty['text']), ('text', 0, ''))

    def test_ref_scope_and_link_paths_fail_closed(self):
        for path in [(b'..',), (b'lib/..',), (b'\0',)]:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'browse-path'):
                self.read(path=path, view='file')
        for path in [(b'link',), (b'link', b'--show\xff\t.txt'), (b'missing',)]:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'browse-path-unavailable'):
                self.read(path=path, view='file')
        with self.assertRaisesRegex(ValueError, 'browse-ref'):
            self.read(ref=b'refs/heads/missing')
        with self.assertRaisesRegex(ValueError, 'ref-name'):
            self.read(ref=self.current.encode('ascii'))
        with self.assertRaisesRegex(ValueError, 'record-shape'):
            browse.request_path(self.request() | {'oid': self.current})

    def test_requires_current_accepted_snapshot_and_rechecks_before_return(self):
        for change in [{'status': 'external-staged'}, {'snapshot': 'b' * 64}]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'accepted-pack-required'):
                browse.browse(lambda: self.report | change, SCOPE['home'], self.request(), self.store, self.binary)
        with self.assertRaisesRegex(ValueError, 'snapshot-scope'):
            browse.browse(lambda: self.report | {'authority_epoch': '2'}, SCOPE['home'], self.request(),
                          self.store, self.binary)
        changing = Mock(side_effect=[self.report, self.report | {'generation': '1'}])
        with self.assertRaisesRegex(ValueError, 'home-acceptance-changed'):
            browse.browse(changing, SCOPE['home'], self.request(), self.store, self.binary)
        self.assertEqual(changing.call_count, 2)
        revoked = Mock(side_effect=[self.report, ValueError('denied')])
        with self.assertRaisesRegex(ValueError, 'denied'):
            browse.browse(revoked, SCOPE['home'], self.request(), self.store, self.binary)
        self.assertEqual(revoked.call_count, 2)


if __name__ == '__main__':
    unittest.main()

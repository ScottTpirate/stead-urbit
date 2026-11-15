"""Exact proposal comparisons over synthetic, real stock-Git pack snapshots."""
from hashlib import sha256
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_changes as changes
import git_pack_relay_service as relay_service
import git_pack_store as store
from portable_recovery import RecoveryError, encoded
import test_git_pack_browse as fixture_module
from test_git_pack_browse import PROJECT, BRANCH, SCOPE


class PackChangesTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.PackBrowseTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        fixture = self.fixture
        self.base = self.make_commit(False)
        self.head = self.make_commit(True)
        fixture.git.run('update-ref', BRANCH, self.head)
        refs = {name.encode().hex(): oid for name, oid in fixture.git.refs().items()}
        raw = fixture.git.run('pack-objects', '--stdout', '--revs',
                              data=''.join(oid + '\n' for oid in refs.values()).encode()).stdout
        pack = fixture.store.parent / 'changes.pack'
        pack.write_bytes(raw)
        pack.chmod(0o600)
        snapshot, manifest = store.stage(fixture.store, pack, sha256(raw).hexdigest(), SCOPE, refs,
                                          BRANCH.hex(), fixture.binary)
        self.pack = fixture.report | {'snapshot': snapshot, 'refs': encoded(refs).decode(),
                                      'object_count': str(manifest['object_count'])}
        self.proposal = {'protocol': 'stead.code/1', 'status': 'proposal', 'proposal_id': PROJECT, 'revision': '1',
                         'author': PROJECT, 'work_id': PROJECT, 'work_title': 'Synthetic review',
                         'source_ref': 'refs/heads/feature', 'ref': 'refs/heads/main',
                         'base_oid': self.base, 'head_oid': self.head, 'base_snapshot': snapshot, 'generation': '0',
                         'reviewer': '', 'merged_revision': '', 'merged_snapshot': '', 'merged_request_id': ''}
        self.request = {'protocol': changes.PROTOCOL, 'project_id': PROJECT, 'snapshot': snapshot,
                        'proposal_id': PROJECT, 'revision': '1', 'view': 'files', 'path': ''}

    def make_commit(self, after):
        f = self.fixture
        rows = [(b'100644', b'blob', f.blob(b'new\n' if after else b'old\n'), b'--unusual\xff\t.txt'),
                (b'100644', b'blob', f.blob(b'new\0image' if after else b'old\0image'), b'image'),
                (b'100644', b'blob', f.blob(b'x' * (changes.MAX_BLOB + 1) if after else b'small'), b'large'),
                (b'100644', b'blob', f.blob('left\u202eright\x1b[31m\n'.encode() if after else b'original\n'), b'controls'),
                (b'120000', b'blob', f.blob(b'new-target' if after else b'old-target'), b'link'),
                (b'100755' if after else b'100644', b'blob', f.blob(b'unchanged\n'), b'permissions')]
        rows.append((b'100644', b'blob', f.blob(b'contents\n'), b'added' if after else b'deleted'))
        return f.git.run('commit-tree', f.tree(rows), *(['-p', self.base] if after else []),
                         '-m', 'Synthetic exact revision').stdout.strip().decode()

    def read(self, path=None, authorize=None, **options):
        request = self.request if path is None else self.request | {'view': 'patch', 'path': path.hex()}
        return changes.changes(authorize or (lambda: (self.pack, self.proposal)), SCOPE['home'], request | options,
                               self.fixture.store, self.fixture.binary)

    def test_changed_files_and_literal_patch_match_exact_proposal(self):
        listing = self.read()
        self.assertEqual((listing['base'], listing['head'], listing['status'], listing['truncated']),
                         (self.base, self.head, 'files', False))
        rows = {bytes.fromhex(row['path']): row for row in listing['entries']}
        self.assertEqual(rows[b'added']['status'], 'A')
        self.assertEqual(rows[b'deleted']['status'], 'D')
        self.assertEqual((rows[b'permissions']['old_mode'], rows[b'permissions']['new_mode']), ('100644', '100755'))
        result = self.read(b'--unusual\xff\t.txt')
        self.assertEqual(result['preview'], 'text')
        self.assertIn('-old\n+new\n', result['text'])
        self.assertFalse(result['sanitized'])
        self.assertIn('+contents', self.read(b'added')['text'])
        self.assertIn('-contents', self.read(b'deleted')['text'])

    def test_binary_large_link_and_directional_controls_are_explicit(self):
        for path, expected in [(b'image', 'binary'), (b'large', 'too-large'), (b'link', 'unsupported-type')]:
            with self.subTest(path=path):
                value = self.read(path)
                self.assertEqual(value['preview'], expected)
                self.assertNotIn('text', value)
        value = self.read(b'controls')
        self.assertEqual(value['preview'], 'text')
        self.assertTrue(value['sanitized'])
        self.assertIn('\\u{202e}', value['text'])
        self.assertIn('\\u{1b}', value['text'])
        self.assertNotIn('\u202e', value['text'])

    def test_response_bounds_are_explicit_and_never_look_complete(self):
        with patch.object(changes, 'MAX_FILES', 2):
            value = self.read()
            self.assertEqual(len(value['entries']), 2)
            self.assertTrue(value['truncated'])
        with patch.object(changes, 'MAX_LIST', 1):
            value = self.read()
            self.assertEqual(value['entries'], [])
            self.assertTrue(value['truncated'])
        with patch.object(changes, 'MAX_PATCH', 5):
            self.assertEqual(self.read(b'added')['preview'], 'too-large')
        with patch.object(changes, 'MAX_METADATA', 5), self.assertRaisesRegex(RecoveryError, 'changes-metadata-bound'):
            self.read()
        limit = len(encoded(self.read(b'controls'))) - 1
        with patch.object(changes, 'MAX_RESPONSE', limit):
            value = self.read(b'controls')
            self.assertLessEqual(len(encoded(value)), limit)
            self.assertEqual(value['preview'], 'too-large')

    def test_no_client_oids_or_unlisted_path_and_no_disclosure_after_change(self):
        for options in ({'base_oid': self.base}, {'head_oid': self.head}, {'path': b'../x'}, {'revision': '0'}):
            with self.subTest(options=options), self.assertRaises(RecoveryError):
                self.read(**options)
        with self.assertRaisesRegex(RecoveryError, 'changes-path-unavailable'):
            self.read(b'not-changed')
        with self.assertRaisesRegex(RecoveryError, 'changes-revision-changed'):
            self.read(revision='2')
        for later in ((self.pack | {'generation': '1'}, self.proposal),
                      (self.pack, self.proposal | {'revision': '2'})):
            authorize = Mock(side_effect=[(self.pack, self.proposal), later])
            with self.assertRaisesRegex(RecoveryError, 'home-acceptance-changed'):
                self.read(authorize=authorize)
            self.assertEqual(authorize.call_count, 2)
        authorize = Mock(side_effect=[(self.pack, self.proposal), RecoveryError('membership-removed')])
        with self.assertRaisesRegex(RecoveryError, 'membership-removed'):
            self.read(authorize=authorize)
        self.assertEqual(authorize.call_count, 2)

    def test_only_home_proposal_commits_in_accepted_closure_can_be_read(self):
        with self.assertRaises(RecoveryError):
            self.read(authorize=lambda: (self.pack, self.proposal | {'head_oid': 'f' * 40}))
        with self.assertRaisesRegex(RecoveryError, 'accepted-pack-required'):
            self.read(authorize=lambda: (self.pack | {'snapshot': 'f' * 64}, self.proposal))

    def test_isolated_service_reader_can_render_the_exact_patch(self):
        try:
            relay_service.sandbox_ready()
        except RecoveryError:
            self.skipTest('isolated Git prerequisite unavailable')
        engine = self.fixture.store.parent / 'engine'
        engine.mkdir(mode=0o700)
        reader = relay_service.install_isolated_reader(engine, Path(self.fixture.binary).resolve())
        request = self.request | {'view': 'patch', 'path': b'added'.hex()}
        result = changes.changes(lambda: (self.pack, self.proposal), SCOPE['home'], request,
                                 self.fixture.store, reader)
        self.assertEqual(result['preview'], 'text')
        self.assertIn('+contents', result['text'])


if __name__ == '__main__':
    unittest.main()

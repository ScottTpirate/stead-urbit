"""Exercise accepted source evidence with real stock Git and private output."""
import hashlib
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import test_git_pack_proof as fixtures
from dogfood_rehearsal import Git
import git_pack_build_source as build
import git_pack_store as store
from portable_recovery import RecoveryError, decoded, encoded, sha


HEAD = b'refs/heads/main'
PROPOSAL = '019939ba-4000-7000-8000-000000000010'
REQUEST = '019939ba-4000-7000-8000-000000000011'


class BuildSourceTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix='stead-build-source-test-')
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.storage = self.root / 'packs'
        self.storage.mkdir(mode=0o700)
        self.git = Path(shutil.which('git')).resolve()
        self.repo = Git(str(self.git), self.root / 'input.git')
        self.repo.init_bare(HEAD)
        self.scope = fixtures.SCOPE.copy()
        self.destination = self.root / 'accepted-source'

    def tree(self, entries):
        raw = bytearray()
        for mode, kind, name, value in entries:
            oid = self.repo.run('hash-object', '-w', '--stdin', data=value).stdout.strip() if kind == b'blob' else value
            raw.extend(mode + b' ' + kind + b' ' + oid + b'\t' + name + b'\0')
        return self.repo.run('mktree', '-z', '--missing', data=bytes(raw)).stdout.strip()

    def store(self, tree):
        self.commit = self.repo.run('commit-tree', tree, '-m', 'Synthetic').stdout.strip().decode()
        pack = self.root / 'source.pack'
        raw = self.repo.run('pack-objects', '--stdout', '--revs', data=(self.commit + '\n').encode()).stdout
        pack.write_bytes(raw)
        pack.chmod(0o600)
        self.snapshot, self.manifest = store.stage(self.storage, pack, sha(raw), self.scope,
            {HEAD.hex(): self.commit}, HEAD.hex(), self.git)
        self.receipt = {'protocol': 'stead.code/1', 'status': 'merged', 'request_id': REQUEST,
                        'proposal_id': PROPOSAL, 'snapshot': self.snapshot, 'generation': '2'}

    def export(self, *args, **kwargs):
        position = (self.storage, self.snapshot, self.manifest, self.receipt, self.git, self.destination)
        return build.export(*(args or position), **({'authorize': lambda: True, 'deadline': time.monotonic() + 15,
                                                    'ref': HEAD.hex(), 'commit': self.commit, 'proposal_revision': 3} | kwargs))

    def sample(self):
        scripts = self.tree([(b'100755', b'blob', b'run.sh', b'#!/bin/sh\nexit 1\n'),
                             (b'100644', b'blob', 'café'.encode(), b'')])
        return self.tree([(b'040000', b'tree', b'scripts', scripts),
                          (b'100644', b'blob', b'readme', b'Read\x00\xff'),
                          (b'100644', b'blob', b'.gitattributes', b'readme export-ignore\n')])

    def test_archive_pins_exact_receipt_commit_and_unmodified_blob_bytes(self):
        tree = self.sample()
        self.store(tree)
        authorize = Mock(return_value=True)
        digest = self.export(authorize=authorize)
        self.assertEqual(authorize.call_count, 2)
        raw = (self.destination / build.MANIFEST).read_bytes()
        observed = decoded(raw)
        self.assertEqual(sha(raw), digest)
        self.assertEqual(observed['receipt'], self.receipt)
        self.assertEqual(observed['receipt_sha256'], sha(encoded(self.receipt)))
        self.assertEqual((observed['scope'], observed['snapshot'], observed['commit'], observed['tree']),
                         (self.scope, self.snapshot, self.commit, tree.decode()))
        self.assertEqual(observed['proposal_revision'], 3)
        archive = self.destination / build.ARCHIVE
        packed = archive.read_bytes()
        self.assertEqual(observed['archive'], {'bytes': len(packed), 'sha256': sha(packed)})
        with tarfile.open(archive) as source:
            self.assertEqual(source.getnames(), [row['path'] for row in observed['entries']])
            self.assertEqual(source.getmember('scripts/run.sh').mode, 0o755)
            for entry in observed['entries']:
                item = source.getmember(entry['path'])
                self.assertEqual((item.uid, item.gid, item.mtime), (0, 0, 0))
                if item.isfile():
                    with source.extractfile(item) as blob:
                        body = blob.read()
                    self.assertEqual(entry['sha256'], sha(body))
                    self.assertEqual(entry['bytes'], len(body))
                    oid = hashlib.sha1(f'blob {len(body)}\0'.encode(), usedforsecurity=False)
                    oid.update(body)
                    self.assertEqual(entry['oid'], oid.hexdigest())
            self.assertEqual(source.extractfile('readme').read(), b'Read\x00\xff')
        with self.assertRaisesRegex(RecoveryError, 'build-source-exists'):
            self.export()
        old = self.destination
        self.destination = self.root / 'repeat'
        self.assertEqual(self.export(), digest)
        self.assertEqual((old / build.ARCHIVE).read_bytes(), (self.destination / build.ARCHIVE).read_bytes())

    def test_missing_revoked_wrong_selection_or_contested_destination_fails_closed(self):
        self.store(self.sample())
        for opts, fault in (({'commit': 'a' * 40}, 'ref'), ({'ref': b'refs/heads/topic'.hex()}, 'ref'),
                            ({'proposal_revision': 0}, 'receipt'),
                            ({'authorize': Mock(side_effect=(True, False))}, 'authorization-changed')):
            with self.subTest(opts=opts), self.assertRaisesRegex(RecoveryError, 'build-source-' + fault):
                self.export(**opts)
            self.assertFalse(self.destination.exists())
            self.assertFalse(list(self.root.glob('.code-restore-*')))
        self.receipt = self.receipt | {'snapshot': '0' * 64}
        with self.assertRaisesRegex(RecoveryError, 'build-source-receipt'):
            self.export()

    def test_destination_appearing_during_final_authority_check_is_never_replaced(self):
        self.store(self.sample())
        calls = []

        def check():
            if calls:
                self.destination.mkdir(mode=0o700)
                (self.destination / 'existing').write_bytes(b'reserved destination')
            calls.append(True)
            return True

        with self.assertRaises(FileExistsError):
            self.export(authorize=check)
        self.assertEqual(list(self.destination.iterdir()), [self.destination / 'existing'])
        self.assertEqual((self.destination / 'existing').read_bytes(), b'reserved destination')
        self.assertFalse(list(self.root.glob('.code-restore-*')))

    def test_symlink_submodule_unsafe_portable_paths_and_collision_never_export(self):
        for entries in (
                [(b'120000', b'blob', b'link', b'../../elsewhere')],
                [(b'160000', b'commit', b'child', b'f' * 40)],
                [(b'100644', b'blob', b'bad\\target', b'file')],
                [(b'100644', b'blob', b'aux.txt', b'file')],
                [(b'100644', b'blob', b'Name', b'one'), (b'100644', b'blob', b'name', b'two')],
        ):
            with self.subTest(entries=entries):
                self.store(self.tree(entries))
                with self.assertRaisesRegex(RecoveryError, 'build-source-(entry|path|path-collision)'):
                    self.export()
                self.assertFalse(self.destination.exists())

    def test_entry_and_payload_limits_apply_before_publication(self):
        self.store(self.sample())
        for name, maximum, code in (('MAX_ENTRIES', 3, 'entry-bound'), ('MAX_PAYLOAD', 8, 'byte-bound'),
                                    ('MAX_MANIFEST', 16, 'manifest-bound')):
            with self.subTest(name=name), patch.object(build, name, maximum):
                with self.assertRaisesRegex(RecoveryError, 'build-source-' + code):
                    self.export()
            self.assertFalse(self.destination.exists())

    def test_existing_snapshot_corruption_fails_before_archive(self):
        self.store(self.sample())
        label = '.'.join(self.scope[key] for key in ('home', 'project_id', 'repository_id'))
        pack = self.storage / label / self.snapshot / store.PACK_NAME
        original = pack.read_bytes()
        pack.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        with self.assertRaisesRegex(RecoveryError, 'pack-digest'):
            self.export()
        self.assertFalse(self.destination.exists())

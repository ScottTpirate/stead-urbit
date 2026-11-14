"""Exercise exact accepted pack projection with real stock Git."""
from contextlib import contextmanager
import errno
from io import BytesIO
import os
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch

import test_git_pack_proof as fixtures
from git_pack_http import READ_PROTOCOL, Denied, decision
import git_pack_projection as projection
import git_pack_store as store
from git_pack_upload import authorized_response
from portable_recovery import RecoveryError, encoded, sha


class PackProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GitPackProofTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.scope = fixtures.SCOPE.copy()
        self.snapshot = self.fixture.claim['base_snapshot']
        self.read_store = self.fixture.root / 'relay-read'
        self.read_store.mkdir(mode=0o700)
        self.git = Path(self.fixture.git).resolve()
        self.deadline = time.monotonic() + 30
        with store.repository_directory(self.fixture.storage, self.scope) as (repo, _), \
                store.open_snapshot(repo, self.snapshot) as held:
            self.manifest = store.read_manifest(held, self.snapshot, self.scope)
        label = '.'.join(self.scope[key] for key in ('home', 'project_id', 'repository_id'))
        self.target = self.read_store / label / self.snapshot
        self.worker_source = self.fixture.storage / label / self.snapshot
        self.pack = (self.worker_source / store.PACK_NAME).read_bytes()
        self.observed = self.home_decision(self.manifest, self.snapshot)
        self.decide = Mock(return_value=self.observed)
        self.fetch = Mock(side_effect=self.handoff)

    def home_decision(self, manifest, snapshot):
        actor = fixtures.ACTOR
        return encoded({'protocol': READ_PROTOCOL, **self.scope, 'snapshot': snapshot,
                        'head': manifest['head'], 'refs': encoded(manifest['refs'])[:-1].decode(),
                        **{key: str(manifest[key]) for key in projection.SIZES + projection.DIGESTS},
                        'identity_ship': actor['identity_ship'], 'principal_id': actor['principal_id'],
                        'binding_id': actor['binding_id'], 'binding_revision': actor['binding_revision']})[:-1]

    @contextmanager
    def handoff(self, snapshot, scope, deadline):
        with projection.retained(self.fixture.storage, snapshot, scope, deadline) as artifact:
            with self.assertRaises(OSError) as error:
                os.write(artifact.fileno(), b'x')
            self.assertEqual(error.exception.errno, errno.EBADF)
            # Copy across the handoff as bytes. The importing caller sees no
            # worker path, credentials, store FD, or writable worker handle.
            with BytesIO(artifact.read()) as received:
                yield received

    def project(self, fetch=None, **options):
        return projection.project(self.decide, self.scope['project_id'], self.scope['home'], self.read_store,
                                  self.fetch if fetch is None else fetch, self.git,
                                  **({'deadline': self.deadline} | options))

    def test_valid_exact_snapshot_is_readable_and_idempotent(self):
        self.assertEqual(self.project(), self.snapshot)
        self.fetch.assert_called_once_with(self.snapshot, self.scope, self.deadline)
        self.assertEqual(self.decide.call_count, 2)
        self.assertEqual((self.target / store.PACK_NAME).read_bytes(), self.pack)
        self.assertEqual((self.target / store.MANIFEST_NAME).read_bytes(), encoded(self.manifest))
        before = self.target.stat().st_ino
        self.assertEqual(self.project(Mock(side_effect=AssertionError('retry opened transport'))), self.snapshot)
        self.assertEqual(self.decide.call_count, 4)
        self.assertEqual(self.target.stat().st_ino, before)
        self.assertEqual((self.worker_source / store.PACK_NAME).read_bytes(), self.pack)
        with authorized_response(lambda: decision(self.observed, self.scope['project_id']), self.scope['project_id'],
                                 self.read_store, self.git, 'advertise') as (mime, count, stream):
            payload = stream.read()
        self.assertEqual(mime, 'application/x-git-upload-pack-advertisement')
        self.assertEqual(count, len(payload))
        self.assertIn(self.fixture.base + b' refs/heads/main', payload)

    def test_short_long_or_substituted_artifact_leaves_no_visible_pack(self):
        for raw in (self.pack[:-1], self.pack + b'x', self.pack[:-1] + bytes([self.pack[-1] ^ 1])):
            with self.subTest(length=len(raw)), self.assertRaises(RecoveryError):
                self.project(lambda *_: BytesIO(raw))
            self.assertFalse(self.target.exists())
            self.assertEqual(list(self.target.parent.iterdir()), [])
        self.assertEqual(self.project(), self.snapshot)

    def test_wrong_inventory_cannot_publish_even_with_matching_pack_and_valid_digest(self):
        wrong = self.manifest | {'object_count': self.manifest['object_count'] + 1}
        digest = sha(encoded(wrong))
        self.decide.return_value = self.home_decision(wrong, digest)
        with self.assertRaisesRegex(RecoveryError, 'pack-projection-inventory'):
            self.project(lambda *_: BytesIO(self.pack))
        self.assertEqual(list(self.target.parent.iterdir()), [])

    def test_revocation_change_or_deadline_prevents_publication(self):
        for result in (Denied('revoked'), self.observed + b'\n'):
            self.decide.side_effect = (self.observed, result)
            with self.subTest(result=result), self.assertRaises(RecoveryError):
                self.project()
            self.assertFalse(self.target.exists())
            self.assertEqual(list(self.target.parent.iterdir()), [])
        self.decide.reset_mock(side_effect=True)
        self.fetch.reset_mock()
        with self.assertRaisesRegex(RecoveryError, 'pack-projection-deadline'):
            self.project(deadline=time.monotonic() - 1)
        self.decide.assert_not_called()
        self.fetch.assert_not_called()

    def test_ambiguous_fsync_retry_checks_existing_bytes_without_overwrite(self):
        original = os.fsync

        def interrupt(descriptor):
            if self.target.exists():
                raise OSError('interrupted directory sync')
            return original(descriptor)

        with patch.object(projection.os, 'fsync', side_effect=interrupt), self.assertRaises(OSError):
            self.project()
        self.assertTrue(self.target.exists())
        self.fetch.reset_mock()
        with patch.object(store, 'MAX_SNAPSHOTS', 1):
            self.assertEqual(self.project(), self.snapshot)
        self.fetch.assert_not_called()
        pack = self.target / store.PACK_NAME
        pack.write_bytes(self.pack[:-1] + bytes([self.pack[-1] ^ 1]))
        with self.assertRaisesRegex(RecoveryError, 'pack-digest'):
            self.project()
        self.fetch.assert_not_called()
        self.assertNotEqual(pack.read_bytes(), self.pack)

    def test_scratch_uses_independent_capacity_and_new_snapshot_refuses_when_full(self):
        self.target.parent.mkdir(mode=0o700)
        scratch = self.target.parent / ('.code-restore-' + 'a' * 32)
        scratch.mkdir(mode=0o700)
        with patch.object(store, 'MAX_SNAPSHOTS', 1), patch.object(store, 'MAX_ABANDONED_SCRATCH', 1):
            self.assertEqual(self.project(), self.snapshot)
            self.assertEqual(self.project(), self.snapshot)
            changed = self.manifest | {'refs': self.manifest['refs'] | {b'refs/heads/copy'.hex(): self.fixture.base.decode()}}
            self.decide.return_value = self.home_decision(changed, sha(encoded(changed)))
            self.fetch.reset_mock()
            with self.assertRaisesRegex(RecoveryError, 'snapshot-capacity'):
                self.project()
            self.fetch.assert_not_called()
        self.assertEqual({path.name for path in self.target.parent.iterdir()}, {self.snapshot, scratch.name})

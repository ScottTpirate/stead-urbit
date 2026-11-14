"""Verify selection mailbox custody and credential-free reconciliation."""
import os
from pathlib import Path
import stat
import time
import unittest
from unittest.mock import Mock, patch

import git_pack_projection_lease as lease
import git_pack_projection_reconcile as service
from portable_recovery import RecoveryError, decoded, encoded
import test_git_pack_projection as fixtures


BOOT = 'deadbeef-01ab-4020-8888-feedcafe0001'


class ProjectionLeaseTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PackProjectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        directory = self.fixture.fixture.root / 'mailbox'
        directory.mkdir(mode=0o750)
        directory.chmod(0o750)
        self.now = lease.NANOS * 30
        self.path = directory / 'lease.json'
        self.scope = self.fixture.scope
        self.mailbox = lease.Mailbox(self.path, self.scope, os.getuid(), os.getgid(),
                                     clock=lambda: self.now, boot_id=BOOT)
        self.deadline = time.monotonic() + 30
        self.selection = {'protocol': lease.SELECTION, 'status': 'open', 'incarnation': 'a' * 64,
                          'relay_generation': '1', 'snapshot': self.fixture.snapshot,
                          'manifest': encoded(self.fixture.manifest).decode()}

    def publish(self, observe=None, **options):
        if observe is None:
            observe = lambda _: self.selection
        return self.mailbox.publish(observe, self.deadline, **options)

    def test_publish_and_explicit_close_write_private_nonsecret_record(self):
        selected = self.publish(lambda _: encoded(self.selection)[:-1], ttl=5)
        self.assertEqual(selected.snapshot, self.fixture.snapshot)
        self.assertEqual(selected.manifest, self.fixture.manifest)
        self.assertEqual(self.mailbox.current(self.deadline), selected)
        record = decoded(self.path.read_bytes())
        self.assertEqual(set(record), lease.FIELDS)
        self.assertEqual(record['issued_ns'], str(self.now))
        self.assertEqual(record['expires_ns'], str(self.now + 5 * lease.NANOS))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        prior_inode = self.path.stat().st_ino
        self.assertTrue(self.mailbox.is_selected(selected.snapshot, self.deadline))
        self.assertFalse(self.mailbox.is_selected('0' * 64, self.deadline))
        self.mailbox.close()
        self.assertNotEqual(prior_inode, self.path.stat().st_ino)
        self.assertFalse(self.mailbox.is_selected(selected.snapshot, self.deadline))
        self.assertEqual(decoded(self.path.read_bytes())['status'], 'closed')

    def test_expired_or_slow_owner_observation_closes_existing_lease(self):
        self.publish(ttl=4)
        self.now += 4 * lease.NANOS
        self.assertFalse(self.mailbox.is_selected(self.fixture.snapshot, self.deadline))

        def slow_query(deadline):
            self.assertEqual(deadline, self.deadline)
            self.now += 5 * lease.NANOS
            return self.selection

        self.publish(ttl=10)
        with self.assertRaisesRegex(RecoveryError, 'pack-projection-lease-expired'):
            self.publish(slow_query, ttl=5)
        self.assertEqual(decoded(self.path.read_bytes())['status'], 'closed')
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_bad_selection_or_failed_owner_read_invalidates_previous_value(self):
        for update in ({'snapshot': '0' * 64}, {'relay_generation': '0'}, {'extra': 'forbidden'},
                       {'manifest': self.selection['manifest'] + '\n'},
                       {'manifest': self.selection['manifest'].replace('~zod', '~nec')}):
            with self.subTest(update=update):
                self.publish()
                with self.assertRaises(RecoveryError):
                    self.publish(lambda _: self.selection | update)
                self.assertFalse(self.mailbox.is_selected(self.fixture.snapshot, self.deadline))
        self.publish()
        with self.assertRaises(OSError):
            self.publish(Mock(side_effect=OSError('owner unavailable')))
        self.assertEqual(decoded(self.path.read_bytes())['status'], 'closed')
        self.assertIsNone(self.publish(lambda _: self.selection | {'status': 'closed', 'snapshot': '', 'manifest': ''}))

    def test_wrong_boot_scope_file_type_and_permissions_fail_closed(self):
        self.publish()
        other_boot = lease.Mailbox(self.path, self.scope, os.getuid(), os.getgid(), boot_id=BOOT.replace('dead', 'deaf'))
        other_scope = lease.Mailbox(self.path, self.scope | {'authority_epoch': '2'}, os.getuid(), os.getgid(), boot_id=BOOT)
        for mailbox in (other_boot, other_scope):
            self.assertFalse(mailbox.is_selected(self.fixture.snapshot, self.deadline))
        self.path.chmod(0o660)
        self.assertFalse(self.mailbox.is_selected(self.fixture.snapshot, self.deadline))
        other = self.path.with_name('other')
        self.path.rename(other)
        other.chmod(0o640)
        self.path.symlink_to(other)
        self.assertFalse(self.mailbox.is_selected(self.fixture.snapshot, self.deadline))
        self.path.unlink()
        os.link(other, self.path)
        self.assertFalse(self.mailbox.is_selected(self.fixture.snapshot, self.deadline))

    def test_reconcile_uses_exact_lease_and_refresh_is_not_a_selection_change(self):
        self.publish()
        open_source = self.fixture.fetch

        def refresh(*args):
            self.now += lease.NANOS
            self.publish()
            return open_source(*args)

        self.assertEqual(service.reconcile(self.mailbox, self.fixture.read_store, refresh, self.fixture.git,
                                           deadline=self.deadline), self.fixture.snapshot)
        self.assertEqual((self.fixture.target / 'objects.pack').read_bytes(), self.fixture.pack)
        self.assertEqual(service.reconcile(self.mailbox, self.fixture.read_store, Mock(side_effect=AssertionError()),
                                           self.fixture.git, deadline=self.deadline), self.fixture.snapshot)

    def test_reconcile_cannot_publish_after_revocation_or_incarnation_change(self):
        for change in (self.mailbox.close,
                       lambda: self.publish(lambda _: self.selection | {'incarnation': 'b' * 64})):
            with self.subTest(change=change):
                self.publish()

                def revoked(*args):
                    change()
                    return self.fixture.fetch(*args)

                with self.assertRaises(RecoveryError):
                    service.reconcile(self.mailbox, self.fixture.read_store, revoked, self.fixture.git,
                                      deadline=self.deadline)
                self.assertFalse(self.fixture.target.exists())

    def test_foreground_server_restores_signal_handler_and_exits_context(self):
        self.publish()
        socket_path, worker_store = Path('/private/artifact.sock'), Path('/private/worker')
        signals = []

        def signal_handler(signal_name, fn):
            signals.append((signal_name, fn))
            return object()

        with patch.object(service.signal, 'signal', side_effect=signal_handler), \
                patch.object(service, 'ArtifactSocket') as socket:
            endpoint = socket.return_value
            endpoint.__enter__ = Mock(return_value=endpoint, create=True)
            endpoint.__exit__ = Mock(create=True)

            def stop(_):
                signals[0][1]()

            endpoint.serve_one = stop
            service.serve(self.mailbox, socket_path, worker_store, 100, 101, 102)
        socket.assert_called_once_with(socket_path, worker_store, self.scope, self.mailbox.is_selected,
                                       100, 101, group_gid=102)
        endpoint.__exit__.assert_called_once()
        self.assertEqual(len(signals), 2)

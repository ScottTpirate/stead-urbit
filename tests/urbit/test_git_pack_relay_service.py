"""Check the edge-to-relay configuration without opening a service listener."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_relay_service as service
import git_pack_upload
from portable_recovery import RecoveryError, encoded
from test_git_pack_push_http import PROJECT
import test_git_pack_projection as projection_fixture


class RelayServiceTests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest('relay runs as an unprivileged account')
        directory = tempfile.TemporaryDirectory(prefix='stead-relay-service-')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.path = root / 'profile'
        (root / 'ca.pem').write_text('test pinned CA data', encoding='ascii')
        for name in ('read-store', 'spool'):
            (root / name).mkdir(mode=0o700)
        self.values = {'protocol': service.PROFILE, 'project': PROJECT, 'home': '~zod',
                       'origin': 'https://home.localhost:8443', 'home_port': 18443, 'certificate_sha256': '1' * 64,
                       'ca': str(root / 'ca.pem'), 'capability': '2' * 64, 'relay_uid': os.getuid(),
                       'worker_uid': os.getuid() + 1, 'worker_socket': '/run/stead-worker/worker.sock',
                       'spool': str(root / 'spool'), 'read_store': str(root / 'read-store'),
                       'git': '/usr/bin/git', 'git_sha256': '3' * 64}
        self.write_profile()

    def write_profile(self, **fields):
        self.path.write_bytes(encoded(self.values | fields))
        self.path.chmod(0o600)

    def test_exact_raw_target_and_fixed_transport_metadata_are_required(self):
        with patch.object(service, 'stable_git') as pins, patch.object(service, 'Relay') as relay, \
                patch.object(service, 'sandbox_ready'), patch.object(service, 'private_mount') as mount:
            application = service.create_application(self.path)
        pins.assert_called_once_with(Path('/usr/bin/git'), '3' * 64)
        self.assertEqual(relay.call_args.kwargs['connect_port'], 18443)
        self.assertEqual(relay.call_args.kwargs['ca_data'], 'test pinned CA data')
        self.assertIs(mount.call_args.args[2], relay.return_value.read_decision)
        path = f'/stead/git/{PROJECT}.git/info/refs'
        query = 'service=git-upload-pack'
        environ = {'PATH_INFO': path, 'QUERY_STRING': query, 'HTTP_X_STEAD_EDGE_TARGET': path + '?' + query,
                   'HTTP_X_FORWARDED_PROTO': 'https'}
        start = Mock()
        for foreign in ({'HTTP_X_STEAD_EDGE_TARGET': path}, {'HTTP_X_STEAD_EDGE_TARGET': path + '?' + query + '&x'},
                        {'HTTP_X_FORWARDED_PROTO': 'http'}, {'HTTP_X_FORWARDED_SSL': 'on'},
                        {'HTTP_FORWARDED': 'for=private'}, {'PATH_INFO': path.upper()}):
            self.assertEqual(application(environ | foreign, start), ())
            self.assertEqual(start.call_args.args[0], '400 Bad Request')
        mount.return_value.assert_not_called()
        self.assertIs(application(environ, start), mount.return_value.return_value)
        mount.return_value.assert_called_once_with(environ, start)

    def test_profile_must_be_private_exact_and_disjoint(self):
        with patch.object(service, 'Relay') as relay:
            for field in ({'relay_uid': 0}, {'home_port': True}, {'spool': self.values['read_store']},
                          {'new_field': True}):
                with self.subTest(field=field), self.assertRaises(RecoveryError):
                    self.write_profile(**field)
                    service.create_application(self.path)
            self.write_profile()
            self.path.chmod(0o640)
            with self.assertRaisesRegex(RecoveryError, 'worker-service-private-file'):
                service.create_application(self.path)
            relay.assert_not_called()

    def test_relay_owned_path_cannot_supply_stable_git_pin(self):
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-service-git-parent'):
            service.stable_git(self.path, '0' * 64)

    def test_isolated_reader_serves_real_stock_git_advertisement(self):
        try:
            service.sandbox_ready()
        except RecoveryError:
            self.skipTest('isolated Git prerequisite unavailable')
        fixture = projection_fixture.PackProjectionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.assertEqual(fixture.project(), fixture.snapshot)
        directory = self.path.parent / 'engine'
        directory.mkdir(mode=0o700)
        reader = service.install_isolated_reader(directory, Path(shutil.which('git')).resolve())
        decide = lambda: projection_fixture.decision(fixture.observed, PROJECT)
        with git_pack_upload.authorized_response(decide, PROJECT, fixture.read_store, reader, 'advertise') as (
                mime, size, spool):
            output = spool.read()
        self.assertEqual(mime, 'application/x-git-upload-pack-advertisement')
        self.assertEqual(size, len(output))
        self.assertIn(fixture.fixture.base + b' refs/heads/main', output)

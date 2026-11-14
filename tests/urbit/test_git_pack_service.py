"""Qualify private combined Git route selection without opening a listener."""
from io import BytesIO
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from git_pack_http import FETCH_TYPE, decision
from git_pack_push_http import MIME
from git_pack_relay import Relay
import git_pack_service as service
from portable_recovery import RecoveryError
from test_git_pack_push_http import AUTH, PROJECT, TOKEN, selection


class PackServiceTests(unittest.TestCase):
    def setUp(self):
        self.authority = 'git.localhost:18443'
        self.base = f'/stead/git/{PROJECT}.git'
        self.snapshot = selection()
        self.lease = decision(self.snapshot, PROJECT)
        self.decide = Mock(return_value=self.lease)
        self.relay = Relay('https://home.localhost:8443', '~zod', 'a' * 64, certificate_sha256='b' * 64)
        self.relay.advertise = Mock(return_value=self.snapshot)
        self.relay.push = Mock(side_effect=lambda work: SimpleNamespace(work=work))
        self.config = (f'https://{self.authority}', PROJECT, self.decide, Path('/private/read-store'),
                       Path('/usr/bin/git'), self.relay, Path('/private/relay-spool'), Path('/private/worker/socket'),
                       29999, 29998)
        self.application = service.private_mount(*self.config, fetch_limit=12, push_limit=24)
        self.discovery = {'REQUEST_METHOD': 'GET', 'PATH_INFO': self.base + '/info/refs',
                          'QUERY_STRING': 'service=git-upload-pack', 'HTTP_AUTHORIZATION': AUTH,
                          'HTTP_HOST': self.authority, 'wsgi.url_scheme': 'https'}
        self.fetch = {'REQUEST_METHOD': 'POST', 'PATH_INFO': self.base + '/git-upload-pack', 'QUERY_STRING': '',
                      'CONTENT_TYPE': FETCH_TYPE, 'CONTENT_LENGTH': '4', 'wsgi.input': BytesIO(b'want')}
        self.push = {'REQUEST_METHOD': 'POST', 'PATH_INFO': self.base + '/git-receive-pack', 'QUERY_STRING': '',
                     'CONTENT_TYPE': MIME + 'request', 'CONTENT_LENGTH': '8', 'wsgi.input': BytesIO(b'packwire')}

    def call(self, environ=None):
        headers = Mock()
        body = b''.join(self.application(self.discovery | (environ or {}), headers))
        self.assertEqual(headers.call_count, 1)
        status, fields = headers.call_args.args
        self.assertEqual(dict(fields)['Content-Length'], str(len(body)))
        self.assertEqual(dict(fields)['Cache-Control'], 'no-store')
        return status, body

    def test_only_four_git_operations_take_their_exact_authority_path(self):
        def authorize(check, project, storage, git, operation, body):
            self.assertEqual((project, storage, git), (PROJECT, Path('/private/read-store'), Path('/usr/bin/git')))
            self.assertEqual(check(), self.lease)
            self.assertEqual(body, b'want' if operation == 'fetch' else b'')
            return SimpleNamespace(__enter__=lambda: (FETCH_TYPE, len(operation), BytesIO(operation.encode())),
                                   __exit__=Mock())

        with patch('git_pack_http.authorized_response', side_effect=authorize):
            self.assertEqual(self.call(), ('200 OK', b'advertise'))
            self.assertEqual(self.call(self.fetch), ('200 OK', b'fetch'))
        self.assertEqual(self.decide.call_count, 2)
        self.decide.assert_called_with(AUTH, PROJECT)
        self.relay.advertise.assert_not_called()
        self.relay.push.assert_not_called()
        status, advertised = self.call({'QUERY_STRING': 'service=git-receive-pack'})
        self.assertEqual(status, '200 OK')
        self.assertIn(b'# service=git-receive-pack\n', advertised)
        self.relay.advertise.assert_called_once()
        self.assertEqual(self.relay.advertise.call_args.args, (AUTH, PROJECT))

        with patch('git_pack_push_http.receive_push', return_value=b'finished') as receive:
            self.assertEqual(self.call(self.push), ('200 OK', b'finished'))
            home, worker, spool, project, bearer, body, size = receive.call_args.args
            self.assertIs(home, worker)
            self.assertEqual((spool, project, bearer, body, size),
                             (Path('/private/relay-spool'), PROJECT, TOKEN, self.push['wsgi.input'], 8))
        admission, captured = object(), Path('/private/fake-captured-wire')
        with patch.object(service.worker, 'request', return_value=object()) as request:
            worker.work(admission, captured, 150)
        request.assert_called_once_with(Path('/private/worker/socket'), 29999, 29998,
                                        admission, captured, 150, clock=self.relay.clock)

    def test_invalid_targets_headers_and_separate_upload_sizes_fail_before_callbacks(self):
        good_target = self.base + '/info/refs?service=git-upload-pack'
        for changed, expected in (
                ({'PATH_INFO': '/stead/api/code'}, '404'), ({'PATH_INFO': '/stead/_pack-relay/' + PROJECT}, '404'),
                ({'PATH_INFO': self.base + '/stead-snapshot'}, '404'), ({'PATH_INFO': self.base + '/info/refs/'}, '404'),
                ({'PATH_INFO': self.base.replace(PROJECT, '019939ba-4000-7000-8000-000000000005') + '/info/refs'}, '404'),
                ({'QUERY_STRING': 'service=git-upload-pack&service=git-receive-pack'}, '400'),
                ({'RAW_URI': good_target.replace('/info/', '/%69nfo/')}, '400'),
                ({'REQUEST_URI': good_target + '&more=1'}, '400'), ({'HTTP_X_STEAD_RELAY': ''}, '400'),
                ({'HTTP_TRANSFER_ENCODING': ''}, '400'), ({'HTTP_COOKIE': ''}, '400'),
                ({'HTTP_COOKIE2': ''}, '400'), ({'HTTP_ORIGIN': ''}, '400'),
                ({'HTTP_HOST': 'other.localhost:18443'}, '400'), ({'wsgi.url_scheme': 'http'}, '400'),
                ({'CONTENT_TYPE': FETCH_TYPE}, '400'), ({'SCRIPT_NAME': '/unexpected'}, '400'),
                (self.fetch | {'CONTENT_LENGTH': '13'}, '400'), (self.push | {'CONTENT_LENGTH': '25'}, '400'),
                (self.push | {'CONTENT_LENGTH': '09'}, '400'), (self.fetch | {'wsgi.input': None}, '400'),
                (self.push | {'CONTENT_TYPE': FETCH_TYPE}, '400'), (self.push | {'REQUEST_METHOD': 'GET'}, '400'),
        ):
            with self.subTest(changed=changed):
                status, body = self.call(changed)
                self.assertTrue(status.startswith(expected))
                self.assertEqual(body, b'')
        self.decide.assert_not_called()
        self.relay.advertise.assert_not_called()
        self.relay.push.assert_not_called()

    def test_missing_accepted_snapshot_does_not_fallback_to_write_or_serve_data(self):
        with tempfile.TemporaryDirectory(prefix='stead-empty-read-store-') as directory:
            config = self.config[:3] + (Path(directory),) + self.config[4:]
            self.application = service.private_mount(*config)
            self.assertEqual(self.call(), ('503 Service Unavailable', b''))
        self.decide.assert_called_once_with(AUTH, PROJECT)
        self.relay.advertise.assert_not_called()
        self.relay.push.assert_not_called()

    def test_reject_invalid_mount_configuration(self):
        for limits in ({'fetch_limit': 0}, {'fetch_limit': service.MAX_REQUEST + 1},
                       {'push_limit': True}, {'push_limit': service.MAX_WIRE + 1},
                       {'read_jobs': 0}, {'write_jobs': 5}):
            with self.subTest(limits=limits), self.assertRaises(RecoveryError):
                service.private_mount(*self.config, **limits)
        with self.assertRaises(RecoveryError):
            service.private_mount(*self.config[:-1], self.config[-2])

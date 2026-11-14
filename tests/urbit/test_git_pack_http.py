"""Exercise the verified HTTPS decision and spooled Smart HTTP boundary."""
import base64
from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_http as http
import git_pack_store as store
from portable_recovery import encoded, sha

PROJECT = '019939ba-4000-7000-8000-000000000001'
AUTH = 'Basic ' + base64.b64encode(b'stead:' + b'f' * 64).decode('ascii')
HOST = 'git.localhost:18443'
HEAD = 'refs/heads/main'.encode().hex()


def current_decision():
    scope = {'home': '~zod', 'project_id': PROJECT, 'repository_id': PROJECT, 'authority_epoch': '1'}
    refs = {HEAD: 'a' * 40}
    manifest = {'format': store.FORMAT, 'object_format': 'sha1', 'scope': scope, 'head': HEAD,
                'refs': refs, 'pack_sha256': 'b' * 64, 'pack_bytes': 224, 'object_count': 5,
                'object_bytes': 1024, 'object_ids_sha256': 'c' * 64}
    report = {'protocol': http.READ_PROTOCOL, **scope, 'head': HEAD, 'refs': encoded(refs).decode().rstrip('\n'),
              'snapshot': sha(encoded(manifest)), 'pack_sha256': manifest['pack_sha256'],
              'object_ids_sha256': manifest['object_ids_sha256'], 'pack_bytes': '224',
              'object_count': '5', 'object_bytes': '1024', 'principal_id': PROJECT,
              'binding_id': '019939ba-4000-7000-8000-000000000002', 'binding_revision': '1',
              'identity_ship': '~bus'}
    return scope, report, refs


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.decide = Mock(return_value=current_decision())
        self.app = http.ReadApplication(f'https://{HOST}', self.decide, Path('/unused'), '/usr/bin/git')
        self.route = {'wsgi.url_scheme': 'https', 'HTTP_HOST': HOST, 'HTTP_AUTHORIZATION': AUTH,
                      'REQUEST_METHOD': 'GET', 'PATH_INFO': f'/stead/git/{PROJECT}.git/info/refs',
                      'QUERY_STRING': 'service=git-upload-pack'}

    def result(self, overrides):
        headers = Mock()
        output = b''.join(self.app(self.route | overrides, headers))
        status, values = headers.call_args.args
        return status, dict(values), output

    def test_requires_exact_git_route_host_method_and_bearer(self):
        for overrides, pattern in [({'HTTP_HOST': 'other.localhost'}, '400'),
                                   ({'wsgi.url_scheme': 'http'}, '400'),
                                   ({'HTTP_COOKIE': 'a=b'}, '400'),
                                   ({'HTTP_AUTHORIZATION': 'Basic invalid'}, '401'),
                                   ({'HTTP_AUTHORIZATION': 'Basic ' + 'A' * 95 + 'é'}, '401'),
                                   ({'QUERY_STRING': 'service=git-receive-pack'}, '400'),
                                   ({'CONTENT_LENGTH': '1'}, '400'),
                                   ({'PATH_INFO': f'/stead/git/{PROJECT}.git/git-receive-pack'}, '404')]:
            with self.subTest(overrides=overrides):
                status, headers, body = self.result(overrides)
                self.assertTrue(status.startswith(pattern))
                self.assertEqual(body, b'')
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertEqual('WWW-Authenticate' in headers, pattern == '401')
        self.decide.assert_not_called()

    def test_no_headers_or_spool_until_worker_returns_authorized_response(self):
        calls = []
        def worker(authorize, project, storage, binary, operation, body):
            self.assertEqual((project, storage, binary, operation, body),
                             (PROJECT, Path('/unused'), '/usr/bin/git', 'fetch', b'0000'))
            authorize()
            calls.append('worked')
            authorize()
            return MagicMock(**{'__enter__.return_value': ('application/x-git-upload-pack-result', 4, BytesIO(b'pack'))})
        with patch.object(http, 'authorized_response', side_effect=worker):
            status, headers, output = self.result({'REQUEST_METHOD': 'POST', 'QUERY_STRING': '',
                'PATH_INFO': f'/stead/git/{PROJECT}.git/git-upload-pack', 'CONTENT_TYPE': http.FETCH_TYPE,
                'CONTENT_LENGTH': '4', 'wsgi.input': BytesIO(b'0000')})
        self.assertEqual(calls, ['worked'])
        self.assertEqual(self.decide.call_count, 2)
        self.decide.assert_called_with(AUTH, PROJECT)
        self.assertEqual((status, output, headers['Content-Length']), ('200 OK', b'pack', '4'))

    def test_authorization_denial_and_disconnected_client_release_capacity(self):
        denied = MagicMock(**{'__enter__.side_effect': http.Denied('denied')})
        approved = MagicMock(**{'__enter__.return_value': ('test', 5, BytesIO(b'hello'))})
        with patch.object(http, 'authorized_response', side_effect=[denied, approved, denied]):
            self.assertEqual(self.result({})[0], '401 Unauthorized')
            unopened = self.app(self.route, Mock())
            unopened.close()
            response = self.app(self.route, Mock())
            self.assertEqual(next(response), b'hello')
            self.assertEqual(self.result({})[0], '503 Service Unavailable')
            response.close()
            approved.__exit__.assert_called_once()
            self.assertEqual(self.result({})[0], '401 Unauthorized')

    def test_decision_rebuilds_the_canonical_manifest(self):
        scope, report, refs = current_decision()
        self.assertEqual(http.decision(encoded(report), PROJECT), (scope, report, refs))
        for field, changed in [('snapshot', 'd' * 64), ('pack_bytes', '225'), ('project_id', 'other'),
                               ('binding_revision', '0'), ('refs', '{}'), ('identity_ship', scope['home'])]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                http.decision(encoded(report | {field: changed}), PROJECT)

    def test_fixed_https_route_reads_bounded_native_chunked_result(self):
        result = MagicMock(status=200)
        result.__enter__.return_value = result
        result.getheader.side_effect = lambda key, default='': {'Content-Type': 'application/json'}.get(key, default)
        result.read1.side_effect = [encoded(current_decision()[1]), b'']
        with patch.object(http.http.client, 'HTTPSConnection') as connection:
            client = connection.return_value
            client.getresponse.return_value = result
            self.assertEqual(http.HomeDecision('https://home.localhost:443')(AUTH, PROJECT), current_decision())
            self.assertEqual(connection.call_args.args, ('home.localhost', 443))
            self.assertEqual(client.request.call_args.args, ('GET', f'/stead/git/{PROJECT}.git/stead-snapshot'))
            self.assertEqual(client.request.call_args.kwargs['headers']['Authorization'], AUTH)
            self.assertEqual(client.request.call_args.kwargs['headers']['Host'], 'home.localhost:443')
            client.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()

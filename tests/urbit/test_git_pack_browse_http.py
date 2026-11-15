"""Exercise browser browse admission at the relay's WSGI boundary."""
from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_browse as browse
import git_pack_browse_http as http
from portable_recovery import decoded, encoded


ORIGIN = 'https://home.localhost'
PROJECT = '019939ba-4000-7000-8000-000000000001'
COOKIE = '__Host-stead-session=' + 'd' * 64
CSRF = 'e' * 64
REQUEST = {'protocol': browse.PROTOCOL, 'project_id': PROJECT, 'snapshot': 'a' * 64,
           'ref': 'refs/heads/main'.encode().hex(), 'path': [], 'view': 'tree'}


class BrowseHTTPTests(unittest.TestCase):
    def setUp(self):
        self.relay = Mock(origin=urlsplit(ORIGIN), home_ship='~zod')
        self.application = http.mount(self.relay, PROJECT, Path('/store'), Path('/isolated-git'))

    def request(self, raw=encoded(REQUEST), **options):
        environ = {'PATH_INFO': http.PATH, 'QUERY_STRING': '', 'REQUEST_METHOD': 'POST',
                   'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(raw)),
                   'HTTP_HOST': 'home.localhost', 'HTTP_ORIGIN': ORIGIN, 'HTTP_COOKIE': COOKIE,
                   'HTTP_X_STEAD_CSRF': CSRF, 'wsgi.input': BytesIO(raw)} | options
        reply = Mock()
        body = b''.join(self.application(environ, reply))
        status, headers = reply.call_args.args
        self.assertEqual(dict(headers)['Content-Length'], str(len(body)))
        return int(status.split()[0]), dict(headers), decoded(body)

    def test_rejects_ambiguous_or_mismatched_request_before_calling_home(self):
        for options, expected in (
            ({'HTTP_AUTHORIZATION': 'Basic Zml4dHVyZQ=='}, 400),
            ({'HTTP_X_STEAD_RELAY': 'fixture'}, 400),
            ({'HTTP_CONTENT_ENCODING': 'gzip'}, 400),
            ({'HTTP_TRANSFER_ENCODING': 'chunked'}, 400),
            ({'QUERY_STRING': 'ref=x'}, 400),
            ({'HTTP_HOST': 'other.localhost'}, 400),
            ({'CONTENT_LENGTH': '0'}, 400),
            ({'CONTENT_LENGTH': str(browse.MAX_REQUEST + 1)}, 400),
            ({'HTTP_ORIGIN': 'null'}, 403),
            ({'HTTP_X_STEAD_CSRF': 'missing'}, 403),
            ({'HTTP_COOKIE': COOKIE + '; ' + COOKIE}, 401),
            ({'HTTP_COOKIE': COOKIE + ', ' + COOKIE}, 401),
            ({'HTTP_COOKIE': 'session=' + 'd' * 64}, 401),
        ):
            with self.subTest(options=options):
                self.assertEqual(self.request(**options)[0], expected)
        raw = encoded(REQUEST | {'project_id': '019939ba-4000-7000-8000-000000000009'})
        self.assertEqual(self.request(raw)[0], 404)
        self.assertEqual(self.request(b'{"path":[],"path":[]}')[0], 400)
        self.relay.browser_pack_view.assert_not_called()

    def test_only_named_session_is_bound_to_home_and_success_is_private(self):
        result = {'status': 'tree', 'entries': []}

        def browse_view(authorize, home, request, directory, reader, *, deadline):
            self.assertEqual((home, request, directory, reader), ('~zod', REQUEST, Path('/store'), Path('/isolated-git')))
            authorize()
            self.relay.browser_pack_view.assert_called_once_with(PROJECT, 'd' * 64, CSRF, deadline)
            return result

        with patch.object(browse, 'browse', side_effect=browse_view):
            status, headers, body = self.request(HTTP_COOKIE='urbauth-~zod=fixture; ' + COOKIE)
        self.assertEqual((status, body), (200, result))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['Cross-Origin-Resource-Policy'], 'same-origin')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertNotIn('Set-Cookie', headers)


if __name__ == '__main__':
    unittest.main()

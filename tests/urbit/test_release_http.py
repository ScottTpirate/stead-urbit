"""Role-contract mocks and real local TLS transport; no native Urbit boot."""
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import release_install as install

SYNTHETIC_GUEST_COOKIE = 'urbauth-~zod=0v1.23456.abcde.fghij.klmno.pqrst; Path=/; Max-Age=604800'


class ReleaseHTTPTests(unittest.TestCase):
    def response(self, body=b'public asset', status=200, mime='text/html; charset=utf-8'):
        return {'status': status, 'headers': {**install.SECURITY_HEADERS, 'content-type': mime}, 'body': body}

    def test_synthetic_role_configuration_preserves_separate_home_member_identity(self):
        home = install.role_configuration('home', 10000)
        identity = install.role_configuration('identity', 10000)
        self.assertEqual(home['home'], '~zod')
        self.assertNotIn('~zod', home['bindings'])
        self.assertEqual(home['runtime'], 'isolated-fake')
        self.assertEqual(identity['home'], '~bus')
        self.assertNotEqual(identity['home_origin'].split(':')[1], identity['origin'].split(':')[1])
        with self.assertRaises(ValueError):
            install.role_configuration('foreign', 10000)

    def test_bootstrap_requires_exact_current_owner_acknowledgement(self):
        native = SimpleNamespace(check=Mock())
        def acknowledge(native, role, mode, value, route):
            self.assertEqual(route, '/bootstrap/' + value['nonce'])
            return {**value, 'status': 'ready', 'home': '~zod', 'incarnation': 'a' * 64}
        with patch.object(install, 'owner_call', side_effect=acknowledge):
            self.assertEqual(install.bootstrap_role(native, 'home')['incarnation'], 'a' * 64)
        for invalid in ({'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~zod', 'nonce': 'wrong', 'incarnation': 'a' * 64},
                        {'status': 'ready'}, {'protocol': 'stead.test-terminal/1', 'status': 'failed', 'kind': 'watch-fail'}):
            with patch.object(install, 'owner_call', return_value=invalid), self.assertRaises(ValueError):
                install.bootstrap_role(native, 'home')

    def test_asset_digest_security_headers_redirect_and_denial_payload_fail_closed(self):
        response = self.response()
        install.assert_http(response, 200, mime='text/html; charset=utf-8', digest=hashlib.sha256(b'public asset').hexdigest(), size=12)
        mutations = [lambda x: x.update(status=302), lambda x: x.update(body=b'wrong bytes'),
                     lambda x: x['headers'].pop('content-security-policy'),
                     lambda x: x['headers'].update({'set-cookie': 'unexpected'}),
                     lambda x: x['headers'].update({'access-control-allow-origin': '*'})]
        for change in mutations:
            with self.subTest(change=change):
                invalid = copy.deepcopy(response)
                change(invalid)
                with self.assertRaises(ValueError):
                    install.assert_http(invalid, 200, mime='text/html; charset=utf-8', digest=hashlib.sha256(b'public asset').hexdigest(), size=12)
        denial = self.response(b'{"protocol":"stead.result/3","status":"rejected","error":"owner_required"}', 401, 'application/json')
        install.assert_http(denial, 401, mime='application/json', error='owner_required')
        with self.assertRaises(ValueError):
            install.assert_http(denial, 401, mime='application/json', error='session_required')

    def test_only_exact_canonical_pinned_guest_cookie_is_recognized(self):
        for value in (SYNTHETIC_GUEST_COOKIE, 'urbauth-~zod=0v0; Path=/; Max-Age=604800',
                      'urbauth-~zod=0v7.vvvvv.vvvvv.vvvvv.vvvvv.vvvvv; Path=/; Max-Age=604800'):
            with self.subTest(value=value):
                self.assertTrue(install.kernel_guest_cookie(value))
        for value in (SYNTHETIC_GUEST_COOKIE.replace('604800', '2592000'),
                      SYNTHETIC_GUEST_COOKIE.replace('~zod', '~bus'),
                      SYNTHETIC_GUEST_COOKIE.replace('urbauth-~zod', 'stead-session'),
                      SYNTHETIC_GUEST_COOKIE + '; Secure',
                      SYNTHETIC_GUEST_COOKIE + '; Domain=home.localhost',
                      SYNTHETIC_GUEST_COOKIE.replace('0v1.', '0v01.'),
                      SYNTHETIC_GUEST_COOKIE.replace('0v1.', '0v8.'),
                      SYNTHETIC_GUEST_COOKIE.replace('23456', '2345'),
                      SYNTHETIC_GUEST_COOKIE.replace('0v1.', '0w1.'),
                      SYNTHETIC_GUEST_COOKIE + '\n',
                      'urbauth-~zod=0v00; Path=/; Max-Age=604800'):
            with self.subTest(value=value):
                self.assertFalse(install.kernel_guest_cookie(value))

    def test_cookie_allowance_requires_recognition_and_redaction(self):
        response = self.response()
        response['headers']['set-cookie'] = install.REDACTED_COOKIE
        with self.assertRaises(ValueError):
            install.assert_http(response, 200, mime='text/html; charset=utf-8')
        response['kernel_guest_cookie_observed'] = True
        install.assert_http(response, 200, mime='text/html; charset=utf-8')
        for key, value in [('set-cookie', SYNTHETIC_GUEST_COOKIE), ('set-cookie2', 'synthetic-secret')]:
            invalid = copy.deepcopy(response)
            invalid['headers'][key] = value
            with self.assertRaises(ValueError):
                install.assert_http(invalid, 200, mime='text/html; charset=utf-8')

    def test_failed_evidence_redacts_all_cookie_headers(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            (package / 'source').mkdir()
            (package / 'source/frontend.json').write_text(json.dumps({'routes': [{'route': '/stead/', 'mime': 'text/html; charset=utf-8',
                'sha256': hashlib.sha256(b'public asset').hexdigest(), 'bytes': 12}]}))
            response = self.response()
            response['headers'].update({'set-cookie': SYNTHETIC_GUEST_COOKIE, 'Set-Cookie2': 'synthetic-secret'})
            evidence = {}
            with patch.object(install, 'request_role', return_value=response), self.assertRaises(ValueError):
                install.route_checks(SimpleNamespace(), 'home', Path('/ca'), package, evidence=evidence)
            self.assertNotIn(SYNTHETIC_GUEST_COOKIE, json.dumps(evidence))
            self.assertNotIn('synthetic-secret', json.dumps(evidence))
            self.assertEqual(evidence['last_response']['headers']['set-cookie'], install.REDACTED_COOKIE)
            self.assertEqual(evidence['last_response']['headers']['Set-Cookie2'], install.REDACTED_COOKIE)
            self.assertFalse(evidence['browser_authentication'])

    def test_each_role_checks_assets_and_independent_denials(self):
        for role, prefix in [('home', '/stead/'), ('identity', '/stead-identity/')]:
            with self.subTest(role=role), tempfile.TemporaryDirectory() as temporary:
                package = Path(temporary)
                (package / 'source').mkdir()
                (package / 'source/frontend.json').write_text(json.dumps({'routes': [{'route': prefix, 'mime': 'text/html; charset=utf-8',
                    'sha256': hashlib.sha256(b'public asset').hexdigest(), 'bytes': 12}]}))
                def request(native, ca, method, route, body=None, headers=None, secure=True):
                    if not secure and not headers:
                        return {'status': 301, 'headers': {'location': install.HTTP_ORIGIN + prefix}, 'body': b''}
                    if method == 'GET' and route == prefix and not body and not headers:
                        response = self.response()
                        response['headers']['set-cookie'] = install.REDACTED_COOKIE
                        response['kernel_guest_cookie_observed'] = True
                        return response
                    if route.endswith('/api/query') or route.endswith('/api/list'):
                        return self.response(json.dumps({'protocol': 'stead.result/3', 'status': 'rejected', 'error': 'session_required' if role == 'home' else 'owner_required'}).encode(), 401, 'application/json')
                    if route.endswith('/api/capabilities'):
                        return self.response(json.dumps({'protocol': 'stead.capabilities/3', 'profile': 'configured-team', 'commands': 'stead.command/3',
                            'queries': 'stead.query/3', 'updates': 'stead.updates/3', 'authentication': 'native-approved-browser/1', 'max_request_bytes': '65536',
                            'max_response_bytes': '262144', 'page_size': '20', 'runtime': 'isolated-fake'}).encode(), 200, 'application/json')
                    return self.response(b'{"protocol":"stead.result/3","status":"rejected","error":"invalid_http_request"}', 403, 'application/json')
                with patch.object(install, 'request_role', side_effect=request):
                    evidence = install.route_checks(SimpleNamespace(), role, Path('/ca'), package)
                self.assertEqual(len(evidence['assets']), 1)
                self.assertEqual(len(evidence['denials']), 11)
                self.assertFalse(evidence['browser_authentication'])
                self.assertIn('spoofed-plain-tls', {row['name'] for row in evidence['denials']})
                with patch.object(install, 'request_role', return_value=self.response()):
                    with self.assertRaises(ValueError):
                        install.route_checks(SimpleNamespace(), role, Path('/ca'), package)


class ActualLocalTLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='stead-release-tls-')
        cls.root = Path(cls.temporary.name)
        cls.cert, cls.key = cls.root / 'cert.pem', cls.root / 'key.pem'
        subprocess.run(['/usr/bin/openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost', '-keyout', str(cls.key), '-out', str(cls.cert)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=10)
        cls.requests = []
        cls.request_cookies = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_GET(self):
                cls.requests.append(self.path)
                cls.request_cookies.append(self.headers.get('Cookie'))
                if self.path == '/stead/bad-status':
                    self.wfile.write(('Set-Cookie: ' + SYNTHETIC_GUEST_COOKIE + '\r\n').encode())
                    self.close_connection = True
                    return
                body = b'x' * 524289 if self.path == '/stead/large' else b'local TLS bytes'
                self.send_response(302 if self.path == '/stead/redirect' else 200)
                self.send_header('Content-Length', str(len(body)))
                if self.path == '/stead/redirect':
                    self.send_header('Location', 'https://foreign.invalid/never-follow')
                if self.path == '/stead/duplicate':
                    self.send_header('X-Test', 'one')
                    self.send_header('X-Test', 'two')
                if self.path in ('/stead/cookie', '/stead/invalid-cookie', '/stead/duplicate-cookie'):
                    self.send_header('Set-Cookie', SYNTHETIC_GUEST_COOKIE if self.path != '/stead/invalid-cookie' else 'stead-session=synthetic-secret')
                if self.path == '/stead/duplicate-cookie':
                    self.send_header('Set-Cookie', SYNTHETIC_GUEST_COOKIE)
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.cert, cls.key)
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=lambda: cls.server.serve_forever(poll_interval=.01), daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temporary.cleanup()

    def request(self, route):
        native = SimpleNamespace(check=Mock(), http_port=1)
        with patch.object(install, 'TLS_HOST', 'localhost'), patch.object(install, 'TLS_PORT', self.server.server_port):
            return install.request_role(native, self.cert, 'GET', route)

    def test_trusted_local_tls_read_and_no_redirect_follow(self):
        self.assertEqual(self.request('/stead/')['body'], b'local TLS bytes')
        before = len(self.requests)
        self.assertEqual(self.request('/stead/redirect')['status'], 302)
        self.assertEqual(len(self.requests), before + 1)

    def test_wrong_hostname_and_untrusted_ca_are_rejected(self):
        native = SimpleNamespace(check=Mock(), http_port=1)
        with patch.object(install, 'TLS_PORT', self.server.server_port):
            with self.assertRaises(ssl.SSLCertVerificationError):
                install.request_role(native, self.cert, 'GET', '/stead/')
        with patch.object(install, 'TLS_HOST', 'localhost'), patch.object(install, 'TLS_PORT', self.server.server_port):
            with self.assertRaises(ssl.SSLCertVerificationError):
                install.request_role(native, Path('/etc/ssl/cert.pem'), 'GET', '/stead/')

    def test_duplicate_response_headers_and_oversized_bytes_are_rejected(self):
        for route in ('/stead/duplicate', '/stead/large', '/stead/duplicate-cookie', '/stead/invalid-cookie'):
            with self.subTest(route=route), self.assertRaises(ValueError):
                self.request(route)

    def test_kernel_guest_cookie_is_redacted_and_never_replayed(self):
        response = self.request('/stead/cookie')
        self.assertEqual(response['headers']['set-cookie'], install.REDACTED_COOKIE)
        self.assertTrue(response['kernel_guest_cookie_observed'])
        self.assertNotIn(SYNTHETIC_GUEST_COOKIE, repr(response))
        self.request('/stead/')
        self.assertEqual(self.request_cookies[-2:], [None, None])
        with self.assertRaisesRegex(ValueError, '^Unexpected release HTTP cookie header$'):
            self.request('/stead/invalid-cookie')

    def test_malformed_wire_response_cannot_log_cookie_values(self):
        with self.assertRaisesRegex(ValueError, r'^Release HTTP transport failed \(BadStatusLine\)$') as error:
            self.request('/stead/bad-status')
        self.assertNotIn(SYNTHETIC_GUEST_COOKIE, str(error.exception))

    def test_outgoing_credentials_are_rejected_before_connect(self):
        native = SimpleNamespace(check=Mock(), http_port=1)
        for key in ('Cookie', 'cOoKiE', 'Cookie2', 'Authorization', 'Proxy-Authorization'):
            with self.subTest(key=key), patch.object(install.http.client, 'HTTPConnection') as connection:
                with self.assertRaisesRegex(ValueError, '^Release HTTP probes must remain anonymous$'):
                    install.request_role(native, self.cert, 'GET', '/stead/', headers={key: 'synthetic-secret'})
                connection.assert_not_called()


if __name__ == '__main__':
    unittest.main()

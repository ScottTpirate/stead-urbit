"""Exercise private Home TLS and per-push custody on a local test origin."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
from threading import Thread
import time
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_http as git_http
import git_pack_receive_adapter as adapter
import git_pack_relay as relay
from git_pack_worker_socket import SignedProof
from portable_recovery import RecoveryError, decoded, encoded, sha
from test_git_pack_push_http import AUTH, TOKEN, selection
import test_git_pack_relay_wire as wire_fixtures


PROJECT = '019939ba-4000-7000-8000-000000000001'
CAPABILITY = '9' * 64
GUEST = 'urbauth-~zod=0v1.23456.abcde.fghij.klmno.pqrst; Path=/; Max-Age=604800'


class PushCustodyTests(unittest.TestCase):
    def setUp(self):
        fixture = wire_fixtures.RelayWireTests()
        fixture.setUp()
        self.admitted = fixture.admission
        self.evidence = fixture.evidence
        self.request = fixture.request
        self.receipt = encoded({key: fixture.claim[key] for key in
                               ('request_id', 'scope', 'actor', 'wire_sha256', 'changes', 'update_count')} | {
            'protocol': adapter.RECEIPT_PROTOCOL, 'status': 'accepted', 'admission_sha256': self.admitted.sha256,
            'candidate_snapshot': fixture.result['candidate_snapshot'], 'generation': '1', 'accepted_at_ms': '1250',
        })
        self.home = relay.Relay('https://home.localhost:18443', '~zod', CAPABILITY,
                                certificate_sha256='f' * 64, clock=lambda: 1300)
        self.worker = Mock(return_value=SignedProof(self.evidence, 7, 'ab' * 64))
        self.deadline = time.monotonic() + 5

    def test_only_same_push_can_carry_worker_proof_and_recover(self):
        with patch.object(relay, 'new_id', return_value=decoded(self.admitted.raw)['request_id']), \
                patch.object(self.home, '_exchange', side_effect=(self.admitted.raw, relay.VERIFIED,
                                                                  self.receipt, self.receipt)) as exchange:
            push = self.home.push(self.worker)
            other = self.home.push(self.worker)
            admitted = push.admit(TOKEN, self.request, self.deadline)
            with self.assertRaisesRegex(RecoveryError, 'pack-relay-push-binding'):
                other.verify(TOKEN, admitted, self.evidence, self.deadline)
            with self.assertRaisesRegex(RecoveryError, 'pack-relay-push-binding'):
                push(replace(admitted, sha256='0' * 64), Path('/private/test'), self.deadline)
            self.worker.assert_not_called()
            evidence = push(admitted, Path('/private/test'), self.deadline)
            self.worker.assert_called_once_with(admitted, Path('/private/test'), self.deadline)
            for bearer, body in (('0' * 64, evidence), (TOKEN, evidence + b'\n')):
                with self.assertRaisesRegex(RecoveryError, 'pack-relay-push-binding'):
                    push.verify(bearer, admitted, body, self.deadline)
            self.assertTrue(push.verify(TOKEN, admitted, evidence, self.deadline))
            self.assertEqual(push.commit(TOKEN, admitted, evidence, self.deadline), self.receipt)
            with patch.object(self.home, 'clock', return_value=2000):
                self.assertEqual(push.recover(TOKEN, admitted, evidence, self.deadline), self.receipt)
        calls = exchange.call_args_list
        for call in calls:
            self.assertEqual(call.args[:2], (AUTH, PROJECT))
            self.assertEqual(call.args[3], self.deadline)
        messages = [call.args[2].splitlines(keepends=True) for call in calls]
        self.assertEqual([decoded(item[0])['step'] for item in messages], ['admit', 'verify', 'commit', 'receipt'])
        self.assertTrue(all(message[1:] == [admitted.raw, evidence] for message in messages[1:]))
        self.assertEqual(decoded(messages[1][0])['worker_signature'], 'ab' * 64)
        self.assertNotIn('worker_signature', decoded(messages[-1][0]))

    def test_admission_response_must_match_exact_request_uuid_and_home(self):
        request = decoded(self.admitted.raw)['request_id']
        bogus = decoded(self.admitted.raw)
        bogus['scope']['home'] = '~nec'
        with patch.object(relay, 'new_id', return_value=PROJECT), \
                patch.object(self.home, '_exchange', return_value=self.admitted.raw):
            with self.assertRaisesRegex(RecoveryError, 'pack-relay-admission-scope'):
                self.home.push(self.worker).admit(TOKEN, self.request, self.deadline)
        with patch.object(relay, 'new_id', return_value=request), \
                patch.object(self.home, '_exchange', return_value=encoded(bogus)):
            with self.assertRaisesRegex(RecoveryError, 'pack-relay-admission-scope'):
                self.home.push(self.worker).admit(TOKEN, self.request, self.deadline)

    def test_receive_allocates_new_home_and_worker_custody_each_time(self):
        arguments = (Path('/spool'), PROJECT, TOKEN, object(), 9)
        with patch.object(adapter, 'receive_push', return_value=b'git result') as receive:
            self.assertEqual(self.home.receive(self.worker, *arguments, deadline=self.deadline), b'git result')
            self.assertEqual(self.home.receive(self.worker, *arguments, deadline=self.deadline), b'git result')
        first, second = receive.call_args_list
        for call in (first, second):
            self.assertIs(call.args[0], call.args[1])
            self.assertEqual(call.args[2:], arguments)
            self.assertEqual(call.kwargs, {'deadline': self.deadline, 'clock': self.home.clock})
        self.assertIsNot(first.args[0], second.args[0])


@unittest.skipUnless(Path('/usr/bin/openssl').is_file(), 'Local OpenSSL is required')
class ActualRelayTLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory(prefix='stead-relay-tls-')
        cls.addClassCleanup(directory.cleanup)
        cls.cert = Path(directory.name) / 'cert.pem'
        key = Path(directory.name) / 'key.pem'
        subprocess.run(['/usr/bin/openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
                        '-nodes', '-days', '1', '-subj', '/CN=home.localhost', '-addext',
                        'subjectAltName=DNS:home.localhost', '-out', str(cls.cert), '-keyout', str(key)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        cls.pin = sha(ssl.PEM_cert_to_DER_cert(cls.cert.read_text()))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.cert, key)
        cls.requests, cls.sni = [], []
        context.set_servername_callback(lambda _, name, __: cls.sni.append(name))

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def handle(self):
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_):
                pass

            def do_POST(self):
                request = self.rfile.read(int(self.headers['Content-Length']))
                cls.requests.append((self.path, dict(self.headers), request))
                status, headers, body = cls.reply
                self.send_response(status)
                for name, value in headers:
                    self.send_header(name, value)
                self.end_headers()
                self.close_connection = True
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.addClassCleanup(cls.server.server_close)
        thread = Thread(target=lambda: cls.server.serve_forever(poll_interval=.01), daemon=True)
        thread.start()
        cls.addClassCleanup(thread.join, 2)
        cls.addClassCleanup(cls.server.shutdown)

    def setUp(self):
        self.requests.clear()
        self.sni.clear()
        self.respond(selection())

    def make_relay(self, **options):
        settings = {'certificate_sha256': self.pin, 'ca_file': self.cert, 'connect_port': self.server.server_port}
        origin = options.pop('origin', 'https://home.localhost:8443')
        return relay.Relay(origin, '~zod', CAPABILITY, **(settings | options))

    def respond(self, body, *, status=200, headers=()):
        type(self).reply = status, (('Content-Type', 'application/json'), ('Content-Length', str(len(body))), *headers), body

    def test_posts_fixed_frame_over_pinned_tls_with_no_cookies_or_redirects(self):
        body = selection()
        type(self).reply = (200, [('Content-Type', 'application/json'), ('Transfer-Encoding', 'chunked'),
                                  ('Set-Cookie', GUEST)], f'{len(body):x}\r\n'.encode() + body + b'\r\n0\r\n\r\n')
        connection = self.make_relay()
        self.assertEqual(connection.advertise(AUTH, PROJECT), body)
        self.assertEqual(connection.advertise(AUTH, PROJECT), body)
        self.assertEqual(self.sni, ['home.localhost'] * 2)
        ids = []
        for path, headers, frame in self.requests:
            self.assertEqual(path, '/stead/_pack-relay/' + PROJECT)
            self.assertEqual(headers['Host'], 'home.localhost:8443')
            self.assertEqual(headers['Authorization'], AUTH)
            self.assertEqual(headers['X-Stead-Relay'], CAPABILITY)
            self.assertEqual(headers['Content-Type'], relay.MIME)
            self.assertEqual(headers['Content-Length'], str(len(frame)))
            self.assertNotIn('Cookie', headers)
            self.assertNotIn('Transfer-Encoding', headers)
            params = decoded(frame)
            self.assertEqual(frame, encoded(params))
            self.assertEqual(params['step'], 'advertise')
            ids.append(params['request_id'])
        self.assertEqual(len(set(ids)), 2)
        self.respond(b'redirect', status=302, headers=(('Location', 'https://foreign.invalid/'),))
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-response-unavailable'):
            connection.advertise(AUTH, PROJECT)
        self.assertEqual(len(self.requests), 3)

    def test_certificate_checks_and_deadline_precede_credentials_on_wire(self):
        for options in ({'certificate_sha256': '0' * 64}, {'origin': 'https://wrong.localhost:8443'}, {'ca_file': None}):
            with self.subTest(options=options), self.assertRaises(RecoveryError):
                self.make_relay(**options).advertise(AUTH, PROJECT)
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-deadline'):
            self.make_relay().advertise(AUTH, PROJECT, deadline=time.monotonic() - 1)
        self.assertFalse(self.requests)

    def test_definite_refusal_is_distinct_from_unconfirmed_response(self):
        home = self.make_relay()
        self.respond(b'{"reason":"denied","status":"refused"}')
        with self.assertRaisesRegex(git_http.Denied, 'pack-relay-denied'):
            home.advertise(AUTH, PROJECT)
        for status in (401, 403):
            self.respond(b'ignored', status=status)
            with self.assertRaises(git_http.Denied):
                home.advertise(AUTH, PROJECT)
        self.respond(b'{"status":"refused","reason":"denied"}')
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-refusal-shape') as error:
            home.advertise(AUTH, PROJECT)
        self.assertNotIn(CAPABILITY, str(error.exception))
        self.assertNotIn(AUTH, str(error.exception))

    def test_oversized_ambiguous_and_stateful_headers_fail(self):
        home = self.make_relay()
        for body, headers in ((b'x' * (git_http.MAX_DECISION + 1), ()),
                              (selection(), (('Transfer-Encoding', 'chunked'),)),
                              (selection(), (('Content-Length', str(len(selection()))),)),
                              (selection(), (('Set-Cookie', 'stead-session=synthetic-token'),)),
                              (selection(), (('Set-Cookie', GUEST), ('Set-Cookie', GUEST))),
                              (selection(), (('Content-Encoding', 'gzip'),))):
            with self.subTest(size=len(body), headers=headers), self.assertRaises(RecoveryError):
                self.respond(body, headers=headers)
                home.advertise(AUTH, PROJECT)

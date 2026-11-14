"""Exercise the generated edge using stock nginx and synthetic private upstreams."""
import base64
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
from queue import Queue
import shutil
import socket
from socketserver import UnixStreamServer
import ssl
import subprocess
import sys
import tempfile
from threading import Thread
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
from git_pack_edge import MAX_REQUEST, MAX_WIRE, Profile, render


PROJECT = '019939ba-4000-7000-8000-000000000001'
HOST = 'stead.example'
BASE = f'/stead/git/{PROJECT}.git'
READ = BASE + '/info/refs?service=git-upload-pack'
WRITE = BASE + '/info/refs?service=git-receive-pack'
PUSH = BASE + '/git-receive-pack'
FETCH = BASE + '/git-upload-pack'
RELAY = f'/stead/_pack-relay/{PROJECT}'
GIT_AUTH = 'Basic ' + base64.b64encode(b'stead:' + b'a' * 64).decode()
POST = '/stead/api/code'
PUSH_KIND = 'application/x-git-receive-pack-request'
FETCH_KIND = 'application/x-git-upload-pack-request'


class Backend(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.respond()

    def respond(self):
        data = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        self.server.observed.put({'path': self.path, 'method': self.command, 'headers': dict(self.headers), 'body': data})
        raw = self.server.label
        self.send_response(200)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


class NginxEdgeTests(unittest.TestCase):
    def setUp(self):
        binary = os.environ.get('STEAD_TEST_NGINX') or shutil.which('nginx')
        if not binary:
            self.skipTest('nginx unavailable; set STEAD_TEST_NGINX to a reviewed absolute binary')
        self.binary = str(Path(binary).resolve(strict=True))
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home_certificate, home_key = self.cert('home')
        self.edge_certificate, edge_key = self.cert('edge')
        self.context = ssl.create_default_context(cafile=self.edge_certificate)
        self.home = HTTPServer(('127.0.0.1', 0), Backend)
        native = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        native.load_cert_chain(self.home_certificate, home_key)
        self.sni = []
        native.set_servername_callback(lambda _, name, __: self.sni.append(name))
        self.home.socket = native.wrap_socket(self.home.socket, server_side=True)
        socket_path = self.root / 'edge.sock'
        self.serve(self.home, b'browser home')
        self.profile = Profile(HOST, free_port(), '127.0.0.1', self.home.server_port, socket_path, PROJECT,
                               self.edge_certificate, edge_key, self.home_certificate)
        self.configure_git(socket_path)

    def configure_git(self, socket_path):
        self.git = UnixStreamServer(str(socket_path), Backend)
        self.serve(self.git, b'git relay')

    def cert(self, role):
        crt, key = self.root / (role + '.crt'), self.root / (role + '.key')
        subprocess.run(['/usr/bin/openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
                        '-noenc', '-days', '1', '-subj', f'/CN={HOST}', '-addext', f'subjectAltName=DNS:{HOST}',
                        '-keyout', key, '-out', crt], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=5)
        key.chmod(0o600)
        return crt, key

    def serve(self, server, label):
        server.observed = Queue()
        server.label = label
        thread = Thread(target=server.serve_forever, daemon=True)
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(2)
        self.addCleanup(cleanup)
        thread.start()

    def start(self, profile=None):
        cfg = self.root / 'nginx.conf'
        cfg.write_text(f'pid {self.root}/nginx.pid;\nerror_log stderr;\nworker_processes 1;\n'
                       'events { worker_connections 32; }\nhttp {\n' + render(profile or self.profile, ROOT / 'native/core/desk')
                       + '\n}\n', encoding='ascii')
        command = [self.binary, '-p', str(self.root), '-c', str(cfg)]
        result = subprocess.run(command + ['-t'], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        child = subprocess.Popen(command + ['-g', 'daemon off; master_process off;'], stderr=subprocess.PIPE)
        def cleanup():
            try:
                if child.poll() is None:
                    child.terminate()
                child.wait(3)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(3)
                child.stderr.close()
        self.addCleanup(cleanup)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if child.poll() is not None:
                self.fail(child.stderr.read().decode())
            try:
                with socket.create_connection(('127.0.0.1', self.profile.public_port), timeout=1):
                    return
            except ConnectionRefusedError:
                time.sleep(0.02)
        self.fail('local edge did not begin listening')

    def exchange(self, method, target, headers=(), data=b'', *, host=True, request_version='HTTP/1.1'):
        authority = f'{HOST}:{self.profile.public_port}'
        fields = [('Host', authority)] if host else []
        fields += [('Connection', 'close'), *headers]
        raw = (f'{method} {target} {request_version}\r\n' + ''.join(f'{name}: {value}\r\n' for name, value in fields)
               + '\r\n').encode('ascii') + data
        with socket.create_connection(('127.0.0.1', self.profile.public_port), timeout=3) as connection, \
                self.context.wrap_socket(connection, server_hostname=HOST) as tls:
            tls.sendall(raw)
            with tls.makefile('rb') as response:
                status = int(response.readline().split()[1])
                count = 0
                while (line := response.readline()) != b'\r\n':
                    self.assertTrue(line)
                    if line.lower().startswith(b'content-length:'):
                        count = int(line.partition(b':')[2].strip())
                return status, response.read(count) if status == 200 else b''

    def test_only_exact_routes_to_distinct_backends_and_returns_clean_headers(self):
        self.start()
        for method, target, mime, data, backend in (
            ('GET', '/stead/', '', b'', self.home),
            ('POST', POST, 'application/json', b'{}', self.home),
            ('GET', READ, '', b'', self.git), ('GET', WRITE, '', b'', self.git),
            ('POST', FETCH, FETCH_KIND, b'fetch', self.git),
            ('POST', PUSH, PUSH_KIND, b'upload', self.git),
        ):
            with self.subTest(target=target):
                headers = [('Authorization', GIT_AUTH), ('X-Stead-Relay', 'discard'),
                           ('X-Forwarded-Proto', 'http'), ('Forwarded', 'for=synthetic'), ('X-Stead-Edge-Target', '/untrusted')]
                if backend is self.home:
                    headers += [('Cookie', '__Host-stead-session=fixture'), ('X-Stead-CSRF', 'fixture')]
                if mime:
                    headers += [('Content-Type', mime), ('Content-Length', str(len(data)))]
                self.assertEqual(self.exchange(method, target, headers, data), (200, backend.label))
                observed = backend.observed.get(timeout=2)
                self.assertEqual((observed['method'], observed['path'], observed['body']), (method, target, data))
                self.assertEqual(observed['headers']['Host'], f'{HOST}:{self.profile.public_port}')
                self.assertNotIn('X-Stead-Relay', observed['headers'])
                self.assertNotIn('Forwarded', observed['headers'])
                if backend is self.home:
                    self.assertNotIn('Authorization', observed['headers'])
                    self.assertNotIn('X-Forwarded-Proto', observed['headers'])
                    self.assertIn('Cookie', observed['headers'])
                    self.assertIn('X-Stead-CSRF', observed['headers'])
                else:
                    self.assertEqual(observed['headers']['Authorization'], GIT_AUTH)
                    self.assertEqual(observed['headers']['X-Forwarded-Proto'], 'https')
                    self.assertEqual(observed['headers']['X-Stead-Edge-Target'], target)
                    self.assertNotIn('Cookie', observed['headers'])
        self.assertEqual(self.sni, [HOST, HOST])

    def test_denies_routing_aliases_and_ambiguous_framing_before_upstream(self):
        self.start()
        for method, path, headers, data in (
            ('POST', RELAY, [('Content-Length', '2'), ('Content-Type', 'application/json')], b'{}'),
            ('GET', '/stead//', [], b''), ('GET', '/stead/?', [], b''),
            ('GET', '/stead/%61ssets/app.js', [], b''), ('GET', '/Stead/', [], b''),
            ('GET', '/stead/assets/../', [], b''), ('GET', READ + '&x=1', [], b''),
            ('GET', READ.replace(PROJECT, '019939ba-4000-7000-8000-000000000009'), [], b''),
            ('GET', f'https://{HOST}:{self.profile.public_port}/stead/', [], b''),
            ('GET', '/stead/', [('Host', 'other.example')], b''),
            ('GET', READ, [('Cookie', 'x=1')], b''),
            ('GET', READ, [('Authorization', GIT_AUTH), ('Authorization', GIT_AUTH)], b''),
            ('POST', PUSH, [('Content-Type', PUSH_KIND), ('Transfer-Encoding', 'chunked')], b'0\r\n\r\n'),
            ('POST', PUSH, [('Content-Type', PUSH_KIND), ('Content-Length', '0'), ('Transfer-Encoding', 'chunked')], b''),
            ('POST', PUSH, [('Content-Type', PUSH_KIND), ('Content-Length', '2'), ('Content-Length', '2')], b'{}'),
            ('POST', PUSH, [('Content-Type', PUSH_KIND), ('Content-Type', PUSH_KIND), ('Content-Length', '2')], b'{}'),
            ('POST', PUSH, [('Content-Type', PUSH_KIND), ('Content-Length', '02')], b'{}'),
            ('POST', PUSH, [('Content-Type', PUSH_KIND), ('Content-Length', '8388608'), ('Content-Encoding', 'gzip')], b''),
            ('POST', PUSH, [('Content-Type', PUSH_KIND), ('Content-Length', '8454145')], b''),
            ('POST', FETCH, [('Content-Type', FETCH_KIND), ('Content-Length', '65537')], b''),
            ('POST', POST, [('Content-Type', 'application/json'), ('Content-Length', '65537')], b''),
        ):
            with self.subTest(method=method, path=path, headers=headers):
                self.assertIn(self.exchange(method, path, headers, data)[0], (400, 404, 413))
        self.assertEqual(self.exchange('GET', '/stead/', [('Host', 'other.example')], host=False)[0], 404)
        self.assertTrue(self.home.observed.empty())
        self.assertTrue(self.git.observed.empty())

    def test_browser_backend_requires_trusted_native_tls(self):
        self.start(replace(self.profile, home_ca=self.cert('untrusted')[0]))
        self.assertEqual(self.exchange('GET', '/stead/')[0], 502)
        self.assertTrue(self.home.observed.empty())
        self.assertEqual(self.exchange('GET', READ)[0], 200)

    def test_private_tunnel_preserves_the_canonical_browser_and_git_authority(self):
        origin_port = self.home.server_port
        profile = replace(self.profile, origin_port=origin_port)
        self.start(profile)
        authority = f'{HOST}:{origin_port}'
        for path, backend in (('/stead/', self.home), (READ, self.git)):
            self.assertEqual(self.exchange('GET', path)[0], 404)
            self.assertEqual(self.exchange('GET', path, [('Host', authority)], host=False), (200, backend.label))
            self.assertEqual(backend.observed.get(timeout=2)['headers']['Host'], authority)
        with self.assertRaisesRegex(ValueError, 'edge-private-origin-port'):
            render(replace(profile, listen_ipv4='192.0.2.3'), ROOT / 'native/core/desk')

    def test_real_edge_preserves_exact_maximum_body(self):
        self.start()
        for path, kind, count, backend in ((POST, 'application/json', 65_536, self.home),
                (FETCH, FETCH_KIND, MAX_REQUEST, self.git), (PUSH, PUSH_KIND, MAX_WIRE, self.git)):
            with self.subTest(path=path):
                data = bytes(range(256)) * (count // 256) + b'z' * (count % 256)
                headers = [('Content-Type', kind), ('Content-Length', str(count))]
                self.assertEqual(self.exchange('POST', path, headers, data), (200, backend.label))
                self.assertEqual(backend.observed.get(timeout=2)['body'], data)


class EdgeProfileTests(unittest.TestCase):
    def test_render_validates_static_bindings_and_contains_no_relay_path(self):
        profile = Profile(HOST, 443, '192.0.2.1', 18443, Path('/run/edge.sock'), PROJECT,
                          Path('/run/public.crt'), Path('/run/public.key'), Path('/run/native-ca.crt'))
        desk = ROOT / 'native/core/desk'
        config = render(profile, desk)
        self.assertNotIn('_pack-relay', config)
        self.assertIn('https://127.0.0.1:18443', config)
        self.assertIn('http://unix:/run/edge.sock:', config)
        self.assertIn('proxy_ssl_verify on;', config)
        for changes in ({'hostname': 'stead.example;'}, {'hostname': '*.example'}, {'project': '../a.git'},
                        {'listen_ipv4': '0.0.0.0'}, {'git_socket': Path('/run/edge.sock;')},
                        {'home_port': 443}, {'certificate': Path('/run/../edge')}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                render(replace(profile, **changes), desk)


if __name__ == '__main__':
    unittest.main()

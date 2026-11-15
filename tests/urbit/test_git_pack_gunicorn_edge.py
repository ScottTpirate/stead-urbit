"""Stock Git through nginx, Gunicorn and the actual relay to a synthetic TLS Home."""
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import signal
import ssl
import stat
import subprocess
import sys
import time
import unittest

import test_git_pack_edge as fixtures
import test_git_pack_projection as projection
from git_pack_browse import PROTOCOL as BROWSE_PROTOCOL
from portable_recovery import RecoveryError, decoded, encoded
import git_pack_relay_service as service


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class HomeDecision(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.decisions.append((self.path, self.headers.get('Host'), self.headers.get('Authorization')))
        raw = self.server.decision
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_):
        pass

    def do_POST(self):
        if self.path == fixtures.POST:
            data = self.rfile.read(int(self.headers['Content-Length']))
            self.server.browser_reads.append((dict(self.headers), decoded(data)))
            status = self.server.browser_statuses.pop(0)
            raw = self.server.browser_view if status == 200 else encoded({'error': 'denied_or_not_found'})
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self.server.decisions.append((self.path, self.headers.get('Host'), self.headers.get('Authorization')))
        self.send_response(403)
        self.send_header('Content-Length', '0')
        self.end_headers()


class GunicornEdgeTests(unittest.TestCase):
    def test_stock_read_through_real_edge_and_actual_relay(self):
        dependencies = os.environ.get('STEAD_TEST_GUNICORN')
        if not dependencies or os.getuid() == 0:
            self.skipTest('set STEAD_TEST_GUNICORN to a private pinned Gunicorn import directory; use nonroot')
        dependencies = str(Path(dependencies).resolve(strict=True))

        class RealEdge(fixtures.NginxEdgeTests):
            def configure_git(self, _):
                pass

        edge = RealEdge()
        self.addCleanup(edge.doCleanups)
        edge.setUp()
        cached = projection.PackProjectionTests()
        self.addCleanup(cached.doCleanups)
        cached.setUp()
        self.assertEqual(cached.project(), cached.snapshot)

        home = HTTPServer(('127.0.0.1', 0), HomeDecision)
        home.decision, home.decisions = cached.observed, []
        home.browser_reads, home.browser_statuses = [], []
        home.browser_view = encoded({'protocol': 'stead.code/1', 'status': 'external', 'snapshot': cached.snapshot,
                                     'authority_epoch': cached.scope['authority_epoch'], 'head': cached.manifest['head'],
                                     'refs': encoded(cached.manifest['refs']).decode().strip(), 'request_id': fixtures.PROJECT,
                                     'object_count': str(cached.manifest['object_count']), 'accepted_at_ms': '1000',
                                     'generation': '0', 'generation_limit': '80'})
        native = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        native.load_cert_chain(edge.home_certificate, edge.root / 'home.key')
        home.socket = native.wrap_socket(home.socket, server_side=True)
        edge.serve(home, b'')

        profile = edge.root / 'relay-profile.json'
        spool = edge.root / 'spool'
        spool.mkdir(mode=0o700)
        engine = Path('/usr/bin/git')
        # When host /usr is user-owned (the local Arch fixture), test only
        # transport by replacing the parent-ownership check in the child.
        # Keep the fixture engine byte pin and all other application gates.
        try:
            service.stable_git(engine, file_digest(engine))
        except RecoveryError:
            engine = cached.git
            ownership_fixture = True
        else:
            ownership_fixture = False
        origin = f'https://{fixtures.HOST}:{edge.profile.public_port}'
        config = {'protocol': service.PROFILE, 'project': fixtures.PROJECT, 'home': '~zod', 'origin': origin,
                  'home_port': home.server_port, 'certificate_sha256': hashlib.sha256(ssl.PEM_cert_to_DER_cert(
                      edge.home_certificate.read_text(encoding='ascii'))).hexdigest(),
                  'ca': str(edge.home_certificate), 'capability': 'a' * 64, 'relay_uid': os.getuid(),
                  'worker_uid': os.getuid() + 1, 'worker_socket': str(edge.root / 'worker' / 'worker.sock'),
                  'spool': str(spool), 'read_store': str(cached.read_store), 'git': str(engine), 'git_sha256': file_digest(engine)}
        profile.write_bytes(encoded(config))
        profile.chmod(0o600)
        script = ("from gunicorn.app.wsgiapp import run\n"
                  "from git_pack_relay_service import create_application\n"
                  "run()\n")
        if ownership_fixture:
            script = ("import hashlib\nfrom git_pack_worker_service import held_file, MAX_GIT\n"
                      "import git_pack_relay_service as relay\n"
                      "def fixture_git(binary, digest):\n"
                      "    with held_file(binary, MAX_GIT) as source:\n"
                      "        assert hashlib.file_digest(source, 'sha256').hexdigest() == digest\n"
                      "relay.stable_git = fixture_git\n") + script
        args = [sys.executable, '-B', '-c', script, '--chdir', str(fixtures.ROOT / 'scripts/urbit'),
                '--bind', f'unix:{edge.profile.git_socket}', '--umask', '0007', '--workers', '1', '--timeout', '90',
                f'git_pack_relay_service:create_application({str(profile)!r})']
        environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONPATH':
                       dependencies + os.pathsep + str(fixtures.ROOT / 'scripts/urbit')}
        log = edge.root / 'gunicorn.log'
        with log.open('wb') as output:
            relay = subprocess.Popen(args, env=environment, cwd=edge.root, stderr=output,
                                     stdout=subprocess.DEVNULL, start_new_session=True)
        def terminate():
            if relay.poll() is None:
                os.killpg(relay.pid, signal.SIGTERM)
            try:
                relay.wait(4)
            except subprocess.TimeoutExpired:
                os.killpg(relay.pid, signal.SIGKILL)
                relay.wait(4)
        self.addCleanup(terminate)
        deadline = time.monotonic() + 5
        while not edge.profile.git_socket.is_socket() and relay.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(edge.profile.git_socket.is_socket(), log.read_text())
        self.assertEqual(stat.S_IMODE(edge.profile.git_socket.stat().st_mode), 0o770)
        edge.start()
        self.assertEqual(edge.exchange('GET', fixtures.READ)[0], 401, log.read_text())
        self.assertEqual(edge.exchange('POST', fixtures.RELAY)[0], 404)
        self.assertEqual(home.decisions, [])
        denied = [('Authorization', fixtures.GIT_AUTH), ('X-Stead-Edge-Target', fixtures.RELAY),
                  ('X-Forwarded-Proto', 'http'), ('X-Stead-Relay', 'client-cannot-choose')]
        self.assertEqual(edge.exchange('GET', fixtures.WRITE, denied)[0], 401)
        self.assertEqual(home.decisions, [(fixtures.RELAY, f'{fixtures.HOST}:{edge.profile.public_port}', fixtures.GIT_AUTH)])
        home.decisions.clear()

        destination = edge.root / 'stock-clone'
        git = [str(cached.git), '-c', f'http.curloptResolve={fixtures.HOST}:{edge.profile.public_port}:127.0.0.1',
               '-c', f'http.sslCAInfo={edge.edge_certificate}', '-c', 'http.version=HTTP/1.1', '-c', 'protocol.version=0',
               '-c', 'credential.helper=']
        askpass = edge.root / 'askpass'
        askpass.write_text('#!/bin/sh\ncase "$1" in *Username*) printf "stead\\n" ;;\n'
                           '*Password*) printf "%s\\n" ' + ('a' * 64) + ' ;;\n*) exit 1 ;;\nesac\n', encoding='ascii')
        askpass.chmod(0o700)
        url = origin.replace('https://', 'https://stead@', 1) + fixtures.BASE
        result = subprocess.run(git + ['clone', url, str(destination)], cwd=edge.root, env={
            'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': str(askpass)},
            capture_output=True, timeout=18)
        self.assertEqual(result.returncode, 0, result.stderr.decode() + log.read_text())
        self.assertEqual(subprocess.check_output([str(cached.git), '-C', destination, 'rev-parse', 'HEAD']).strip(),
                         cached.fixture.base)
        subprocess.run([str(cached.git), '-C', destination, 'fsck', '--full', '--strict'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        expected = (fixtures.BASE + '/stead-snapshot', f'{fixtures.HOST}:{edge.profile.public_port}', fixtures.GIT_AUTH)
        self.assertEqual(home.decisions, [expected] * 4)
        self.assertEqual(edge.home.observed.qsize(), 0)

        session, csrf = 'd' * 64, 'e' * 64
        browse = {'protocol': BROWSE_PROTOCOL, 'project_id': fixtures.PROJECT, 'snapshot': cached.snapshot,
                  'ref': cached.manifest['head'], 'path': [], 'view': 'tree'}

        def query(value=browse, **options):
            raw = encoded(value)
            headers = {'Origin': origin, 'Cookie': '__Host-stead-session=' + session, 'X-Stead-CSRF': csrf,
                       'Content-Length': str(len(raw)), 'Content-Type': 'application/json'} | options
            return edge.exchange('POST', fixtures.BROWSE, list(headers.items()), raw)

        self.assertEqual(query(Origin='https://other.invalid')[0], 403)
        self.assertEqual(query(Cookie='irrelevant=sample')[0], 401)
        self.assertEqual(query(browse | {'project_id': '019939ba-4000-7000-8000-000000000009'})[0], 404)
        self.assertEqual(home.browser_reads, [])
        home.browser_statuses[:] = [200, 200]
        status, raw = query()
        self.assertEqual(status, 200, log.read_text())
        fields = {key: value for key, value in browse.items() if key != 'view'}
        self.assertEqual(decoded(raw), fields | {'status': 'tree', 'commit': cached.fixture.base.decode(),
                                                 'entries': [], 'truncated': False})
        home.browser_statuses[:] = [200, 404]
        self.assertEqual(query()[0], 404, 'permission revoked at final Home read')
        self.assertEqual(len(home.browser_reads), 4)
        for headers, body in home.browser_reads:
            self.assertEqual(body, {'protocol': 'stead.code/1', 'action': 'pack-view', 'project_id': fixtures.PROJECT})
            self.assertEqual(headers['Origin'], origin)
            self.assertEqual(headers['Cookie'], '__Host-stead-session=' + session)
            self.assertEqual(headers['X-Stead-CSRF'], csrf)
            self.assertNotIn('Authorization', headers)
            self.assertNotIn('X-Stead-Relay', headers)
        self.assertEqual(home.browser_statuses, [])
        self.assertEqual(edge.home.observed.qsize(), 0)
        home.decisions.clear()
        cached.target.rename(cached.target.with_name('fixture-unavailable'))
        self.assertEqual(edge.exchange('GET', fixtures.READ, [('Authorization', fixtures.GIT_AUTH)])[0], 503)
        self.assertEqual(home.decisions, [expected])
        print('gunicorn edge proof:', 'exact executable ownership' if not ownership_fixture
              else 'fixture substitutes executable-parent ownership only', 'four exact native read decisions')


if __name__ == '__main__':
    unittest.main()

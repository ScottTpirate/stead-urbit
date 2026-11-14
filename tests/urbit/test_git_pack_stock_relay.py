"""One stock HTTPS push through the real relay and a distinct-UID worker."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import shutil
import signal
import ssl
import subprocess
import sys
from threading import Thread
import time
import unittest
from wsgiref.simple_server import WSGIRequestHandler, make_server

import test_git_pack_proof as fixtures
from test_git_pack_push_http import AUTH, selection
from test_git_pack_receive_adapter import accept
from test_git_pack_projection_socket import GROUP_GID, RELAY_UID, WORKER_UID, as_user
from dogfood_rehearsal import ENV, Git
import git_pack_proof as proof
from git_pack_private_worker import PrivatePackWorker
from git_pack_receive_adapter import Admission, proof_snapshot
from git_pack_relay import MIME, VERIFIED, Relay
from git_pack_service import private_mount
import git_pack_worker_signature as signing
from git_pack_worker_socket import WorkerSocket
from portable_recovery import decoded, encoded, sha


CAPABILITY = 'a' * 64
GENERATION = 7
BRANCH = b'refs/heads/topic'.hex()
OS_GIT = '/usr/bin/git'


def openssl(*args):
    return subprocess.check_output(['/usr/bin/openssl', *args], stderr=subprocess.DEVNULL, timeout=5)


def tls_context(certificate, key):
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(certificate, key)
    return tls


class QuietWSGI(WSGIRequestHandler):
    def get_environ(self):
        environ = super().get_environ() | {'HTTPS': 'on', 'RAW_URI': self.path}
        if 'Content-Type' not in self.headers:
            environ.pop('CONTENT_TYPE', None)
        return environ

    def log_message(self, *_):
        pass


class Home:
    def __init__(self, root, claim):
        self.root, self.claim = root, claim
        self.calls, self.errors = [], []
        self.verified = self.committed = None

    def respond(self, content):
        header, *docs = content.splitlines(keepends=True)
        frame = decoded(header)
        assert header == encoded(frame) and frame['protocol'] == 'stead.git-pack-relay/1'
        step = frame['step']
        self.calls.append(step)
        if step == 'advertise':
            assert not docs
            return selection(refs={fixtures.MAIN.hex(): (self.root / 'base').read_text().strip()})
        if step == 'admit':
            assert not docs and frame['update_count'] == '1'
            proposal = frame['changes']['00']
            assert proposal['ref'] == BRANCH and proposal['prior'] == '0' * 40
            assert proposal['target'] == (self.root / 'tip').read_text().strip()
            self.admission = self.claim | {key: frame[key] for key in ('request_id', 'wire_sha256', 'update_count', 'changes')}
            return encoded(self.admission)
        assert len(docs) == 2 and docs[0] == encoded(self.admission)
        admitted = Admission(docs[0], sha(docs[0]))
        assert frame['admission_sha256'] == admitted.sha256 and frame['request_id'] == self.admission['request_id']
        proof_snapshot(docs[1], admitted, self.admission)
        if step == 'receipt':
            assert 'worker_signature' not in frame and self.committed is not None and docs[1] == self.verified
            return self.committed
        assert frame['worker_generation'] == str(GENERATION)
        message = self.root / 'message'
        signature = self.root / 'signature'
        message.write_bytes(signing.message(docs[1], GENERATION))
        signature.write_bytes(bytes.fromhex(frame['worker_signature']))
        openssl('pkeyutl', '-verify', '-rawin', '-pubin', '-inkey', str(self.root / 'worker.pub'),
                '-in', str(message), '-sigfile', str(signature))
        if step == 'verify':
            self.verified = docs[1]
            return VERIFIED
        assert step == 'commit' and docs[1] == self.verified and self.committed is None
        self.committed = accept(admitted, docs[1])
        return None  # Lose the response after the fixture has recorded acceptance.

    def handler(self):
        home = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                try:
                    assert self.path == '/stead/_pack-relay/' + fixtures.PROJECT
                    assert self.headers['Authorization'] == AUTH
                    assert self.headers['X-Stead-Relay'] == CAPABILITY and self.headers['Content-Type'] == MIME
                    assert self.headers['Host'] == 'localhost:8443'
                    raw = home.respond(self.rfile.read(int(self.headers['Content-Length'])))
                    if raw is None:
                        self.close_connection = True
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                except BaseException as error:
                    home.errors.append(error)
                    self.close_connection = True

        return Handler


def child(action):
    pid = os.fork()
    if pid == 0:
        try:
            action()
        except BaseException:
            import traceback
            traceback.print_exc()
            os._exit(1)
        os._exit(0)
    return pid


def read_pipe(fd):
    with os.fdopen(fd, 'rb') as stream:
        return stream.readline().rstrip(b'\n')


def exercise(root):
    worker_root, relay_root = root / 'worker', root / 'relay'
    wire_socket = root / 'run' / 'worker.sock'
    claim = decoded((root / 'claim').read_bytes())
    home = Home(root, claim)
    home_server = HTTPServer(('127.0.0.1', 0), home.handler())
    home_server.socket = tls_context(root / 'tls.crt', root / 'tls.key').wrap_socket(home_server.socket, server_side=True)

    def verify_in_worker():
        home_server.server_close()
        os.close(worker_read)
        as_user(WORKER_UID)
        assert not os.access(relay_root, os.R_OK | os.W_OK | os.X_OK)
        verifier = PrivatePackWorker(root / 'store', Path(OS_GIT).resolve(), clock=lambda: 2000)
        with WorkerSocket(wire_socket, worker_root / 'upload', RELAY_UID, WORKER_UID,
                          verifier, GENERATION, worker_root / 'signing.pem', group_gid=GROUP_GID,
                          clock=lambda: 2000) as server:
            os.write(worker_write, b'ready\n')
            os.close(worker_write)
            assert server.serve_one(time.monotonic() + 25)
        assert not wire_socket.exists() and not list((worker_root / 'upload').iterdir())

    worker_read, worker_write = os.pipe()
    worker = child(verify_in_worker)
    os.close(worker_write)
    assert read_pipe(worker_read) == b'ready'
    relay_read, relay_write = os.pipe()

    def relay_application():
        home_server.server_close()
        os.close(relay_read)
        as_user(RELAY_UID)
        assert not os.access(worker_root, os.R_OK | os.W_OK | os.X_OK)
        assert not os.access(root / 'store', os.R_OK | os.W_OK | os.X_OK)
        certificate = root / 'tls.crt'
        pin = sha(ssl.PEM_cert_to_DER_cert(certificate.read_text()))
        connection = Relay('https://localhost:8443', '~zod', CAPABILITY, certificate_sha256=pin,
                           ca_file=certificate, connect_port=home_server.server_port, clock=lambda: 2000)
        with make_server('127.0.0.1', 0, lambda *_: (), handler_class=QuietWSGI) as server:
            origin = f'https://localhost:{server.server_port}'
            server.set_app(private_mount(origin, fixtures.PROJECT, connection.read_decision, relay_root / 'read',
                                         Path(OS_GIT), connection, relay_root / 'upload', wire_socket, WORKER_UID, RELAY_UID))
            server.socket = tls_context(certificate, relay_root / 'tls.key').wrap_socket(server.socket, server_side=True)
            try:
                os.write(relay_write, f'{server.server_port}\n'.encode())
                os.close(relay_write)
                server.timeout = 12
                server.handle_request()
                server.handle_request()
            finally:
                assert not list((relay_root / 'upload').iterdir())

    relay = child(relay_application)
    os.close(relay_write)
    port = int(read_pipe(relay_read))
    thread = Thread(target=lambda: home_server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    success = False
    try:
        repository = root / 'source.git'
        url = f'https://localhost:{port}/stead/git/{fixtures.PROJECT}.git'
        run = subprocess.run([OS_GIT, '-C', str(repository), '-c', 'http.extraHeader=Authorization: ' + AUTH,
                              '-c', f'http.sslCAInfo={root / "tls.crt"}', '-c', 'http.version=HTTP/1.1',
                              'push', url, 'refs/heads/topic:refs/heads/topic'],
                             env=ENV | {'GIT_ALLOW_PROTOCOL': 'https'}, capture_output=True, timeout=15)
        assert run.returncode == 0, (run.stderr.decode(errors='replace'), home.calls, home.errors)
        assert home.calls == ['advertise', 'admit', 'verify', 'commit', 'receipt'] and not home.errors
        assert decoded(home.committed)['candidate_snapshot'] == decoded(home.verified)['candidate_snapshot']
        assert decoded(home.verified)['updates']['00']['kind'] == 'commit'
        success = True
    finally:
        home_server.shutdown()
        thread.join(timeout=1)
        home_server.server_close()
        for pid in (relay, worker):
            if not success:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            _, status = os.waitpid(pid, 0)
            assert not success or os.waitstatus_to_exitcode(status) == 0


@unittest.skipUnless(shutil.which('unshare'), 'Linux subordinate user namespaces are required')
class StockRelayTests(unittest.TestCase):
    def test_stock_push_uses_actual_distinct_uid_worker_and_recovers_exact_receipt(self):
        command = ['unshare', '--map-root-user', '--map-auto']
        supported = subprocess.run((*command, sys.executable, '-B', '-c', 'import os; os.setuid(2)'),
                                   capture_output=True, timeout=3)
        if supported.returncode:
            self.skipTest('Unprivileged subordinate UID mapping is unavailable')
        fixture = fixtures.GitPackProofTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root = fixture.root
        root.chmod(0o755)
        (root / 'claim').write_bytes(encoded(fixture.claim))
        (root / 'base').write_bytes(fixture.base)
        (root / 'tip').write_bytes(fixture.tip)
        Git(fixture.git, root / 'source.git').run('update-ref', 'refs/heads/topic', fixture.tip)
        for name, mode in (('worker', 0o700), ('worker/upload', 0o700), ('relay', 0o700),
                           ('relay/upload', 0o700), ('relay/read', 0o700), ('run', 0o710)):
            (root / name).mkdir(mode=mode)
            (root / name).chmod(mode)
        openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes', '-days', '1',
                '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost', '-out', str(root / 'tls.crt'),
                '-keyout', str(root / 'tls.key'))
        relay_tls = root / 'relay' / 'tls.key'
        relay_tls.write_bytes((root / 'tls.key').read_bytes())
        relay_tls.chmod(0o600)
        signing_key = root / 'worker' / 'signing.pem'
        openssl('genpkey', '-algorithm', 'Ed25519', '-out', str(signing_key))
        signing_key.chmod(0o600)
        (root / 'worker.pub').write_bytes(openssl('pkey', '-in', str(signing_key), '-pubout'))
        run = subprocess.run((*command, sys.executable, '-B', __file__, str(root)), capture_output=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace'))


if __name__ == '__main__':
    root = Path(sys.argv[1])
    owned = {'worker': WORKER_UID, 'relay': RELAY_UID, 'run': WORKER_UID, 'store': WORKER_UID}
    for name, uid in owned.items():
        path = root / name
        for entry in path.rglob('*'):
            os.chown(entry, uid, GROUP_GID)
        os.chown(path, uid, GROUP_GID)
    try:
        exercise(root)
    finally:
        for name in owned:
            path = root / name
            for entry in path.rglob('*'):
                os.chown(entry, 0, 0)
            os.chown(path, 0, 0)

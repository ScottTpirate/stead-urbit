"""Check private writer discovery and receive-pack framing."""
import base64
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from dogfood_rehearsal import Git
from git_pack_http import READ_PROTOCOL, Denied
import git_pack_push_http as http
import git_pack_store as store
from portable_recovery import encoded, sha


PROJECT = '019939ba-4000-7000-8000-000000000001'
TOKEN = 'f' * 64
AUTH = 'Basic ' + base64.b64encode(b'stead:' + TOKEN.encode()).decode()
HOST = 'git.localhost:18443'
MAIN = b'refs/heads/main'
TOPIC = b'refs/heads/topic'
TAG = b'refs/tags/exact-\xff'
URL = f'/stead/git/{PROJECT}.git'


def selection(*, refs=None, project=PROJECT):
    if refs is None:
        refs = {TAG.hex(): 'c' * 40, MAIN.hex(): 'a' * 40}
    scope = {'home': '~zod', 'project_id': project, 'repository_id': project, 'authority_epoch': '1'}
    inventory = {'pack_sha256': 'b' * 64, 'object_ids_sha256': 'd' * 64,
                 'pack_bytes': 220, 'object_count': 4, 'object_bytes': 2048}
    manifest = {'format': store.FORMAT, 'object_format': 'sha1', 'scope': scope, 'head': MAIN.hex(),
                'refs': refs, **inventory}
    report = {'protocol': READ_PROTOCOL, **scope, 'head': MAIN.hex(), 'refs': encoded(refs)[:-1].decode(),
              'snapshot': sha(encoded(manifest)), **{key: str(value) for key, value in inventory.items()},
              'principal_id': PROJECT, 'binding_id': '019939ba-4000-7000-8000-000000000002',
              'binding_revision': '1', 'identity_ship': '~bus'}
    return encoded(report)[:-1]


class PushHTTPTests(unittest.TestCase):
    def setUp(self):
        self.advertise = Mock(return_value=selection())
        self.home = Mock()
        self.worker = Mock()
        self.app = http.WriteApplication(f'https://{HOST}', self.advertise, self.home, self.worker, Path('/unused'))
        self.discovery = {'wsgi.url_scheme': 'https', 'HTTP_HOST': HOST, 'HTTP_AUTHORIZATION': AUTH,
                          'REQUEST_METHOD': 'GET', 'PATH_INFO': URL + '/info/refs',
                          'QUERY_STRING': 'service=git-receive-pack'}
        self.upload = {'REQUEST_METHOD': 'POST', 'PATH_INFO': URL + '/git-receive-pack', 'QUERY_STRING': '',
                       'CONTENT_TYPE': http.MIME + 'request', 'CONTENT_LENGTH': '4',
                       'wsgi.input': BytesIO(b'0000')}

    def call(self, **env):
        headers = Mock()
        result = b''.join(self.app(self.discovery | env, headers))
        status, values = headers.call_args.args
        return status, dict(values), result

    def test_discovery_orders_real_refs_and_advertises_only_supported_capabilities(self):
        status, headers, body = self.call()
        self.assertEqual((status, headers['Content-Type'], headers['Content-Length'], headers['Cache-Control']),
                         ('200 OK', http.MIME + 'advertisement', str(len(body)), 'no-store'))
        self.assertEqual(body, http.SERVICE + http.packet(b'a' * 40 + b' ' + MAIN + b'\0' +
                         b'report-status atomic ofs-delta object-format=sha1\n') +
                         http.packet(b'c' * 40 + b' ' + TAG + b'\n') + b'0000')
        self.assertEqual(self.advertise.call_args.args, (AUTH, PROJECT))
        self.assertGreater(self.advertise.call_args.kwargs['deadline'], 0)
        self.assertFalse(self.home.mock_calls)

    def test_request_fences_run_before_advertisement_and_uploader(self):
        for env, status in [
            ({'wsgi.url_scheme': 'http'}, '400'), ({'HTTP_HOST': 'other.localhost:18443'}, '400'),
            ({'HTTP_COOKIE': ''}, '400'), ({'HTTP_CONTENT_ENCODING': 'gzip'}, '400'),
            ({'HTTP_TRANSFER_ENCODING': 'chunked'}, '400'), ({'HTTP_ORIGIN': f'https://{HOST}'}, '400'),
            ({'QUERY_STRING': 'service=git-receive-pack&more=1'}, '400'), ({'CONTENT_LENGTH': '1'}, '400'),
            ({'PATH_INFO': URL + '/git-upload-pack'}, '404'), ({'HTTP_AUTHORIZATION': ''}, '401'),
            (self.upload | {'CONTENT_LENGTH': '04'}, '400'),
            (self.upload | {'CONTENT_LENGTH': str(http.MAX_WIRE + 1)}, '400'),
            (self.upload | {'CONTENT_TYPE': http.MIME + 'request; charset=UTF-8'}, '400'),
        ]:
            with self.subTest(env=env):
                observed, headers, body = self.call(**env)
                self.assertTrue(observed.startswith(status))
                self.assertEqual(body, b'')
                self.assertEqual('WWW-Authenticate' in headers, status == '401')
        self.advertise.assert_not_called()
        self.assertFalse(self.home.mock_calls)

    def test_wrong_project_noncanonical_or_denied_discovery_discloses_no_refs(self):
        other = '019939ba-4000-7000-8000-000000000009'
        for reply in (selection(project=other), selection() + b'\n', selection(refs={MAIN.hex(): '0' * 40})):
            self.advertise.return_value = reply
            status, _, body = self.call()
            self.assertEqual((status, body), ('503 Service Unavailable', b''))
        self.advertise.side_effect = Denied('writer-denied')
        status, headers, body = self.call()
        self.assertEqual((status, headers['WWW-Authenticate'], body),
                         ('401 Unauthorized', 'Basic realm="Stead Git"', b''))

    def test_receive_forwards_only_individual_token_and_definite_http_framing(self):
        with patch.object(http, 'receive_push', return_value=b'git result') as receive:
            status, headers, body = self.call(**self.upload)
            self.assertEqual((status, headers['Content-Type'], body), ('200 OK', http.MIME + 'result', b'git result'))
            self.assertEqual(receive.call_args.args, (self.home, self.worker, Path('/unused'), PROJECT,
                                                       TOKEN, self.upload['wsgi.input'], 4))
            self.assertGreater(receive.call_args.kwargs['deadline'], 0)
        self.advertise.assert_not_called()

    def test_busy_adapter_runs_no_discovery_work(self):
        self.assertTrue(self.app.slots.acquire(blocking=False))
        try:
            status, _, body = self.call()
            self.assertEqual((status, body), ('503 Service Unavailable', b''))
        finally:
            self.app.slots.release()
        self.advertise.assert_not_called()

    def test_stock_receive_pack_agrees_on_ref_rows_with_no_synthetic_head(self):
        def unpack(raw):
            rows = []
            while raw[:4] != b'0000':
                size = int(raw[:4], 16)
                rows.append(raw[4:size].split(b'\0', 1)[0].rstrip(b'\n'))
                raw = raw[size:]
            return rows

        with tempfile.TemporaryDirectory() as directory:
            pinned = Path(__file__).resolve().parents[2] / '.runtime/tooling/git-2.55.0/bin/git'
            git = Git(str(pinned) if pinned.is_file() else '/usr/bin/git', Path(directory) / 'fixture.git')
            git.init_bare(MAIN)
            tree = git.run('mktree', data=b'').stdout.strip()
            tip = git.run('commit-tree', tree, '-m', 'Synthetic Git ref').stdout.strip()
            git.run('update-ref', MAIN, tip)
            git.run('update-ref', TOPIC, tip)
            git.run('tag', '-a', '-m', 'Synthetic annotated tag', TAG.removeprefix(b'refs/tags/'), tip)
            tag = git.run('rev-parse', TAG).stdout.strip()
            refs = {MAIN.hex(): tip.decode(), TOPIC.hex(): tip.decode(), TAG.hex(): tag.decode()}
            native = git.run('receive-pack', '--stateless-rpc', '--advertise-refs', './').stdout
            actual = http.advertisement(selection(refs=refs), PROJECT).removeprefix(http.SERVICE)
            self.assertEqual(unpack(actual), unpack(native))
            self.assertEqual(len(unpack(actual)), 3)


if __name__ == '__main__':
    unittest.main()

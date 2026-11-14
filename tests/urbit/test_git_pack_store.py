"""Stock Git tests for immutable private pack snapshots and offline restore."""
from contextlib import redirect_stdout
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_store as store
import git_pack_readback as readback
import git_pack_upload as upload
from dogfood_rehearsal import ENV, Git


BRANCH = 'refs/heads/main'
TAG = 'refs/tags/v1'
SCOPE = {'home': '~zod', 'project_id': '019939ba-4000-7000-8000-000000000001',
         'repository_id': '019939ba-4000-7000-8000-000000000002', 'authority_epoch': '1'}


class PackStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.storage = self.root / 'store'
        self.storage.mkdir(mode=0o700)
        self.binary = shutil.which('git')
        self.git = Git(self.binary, self.root / 'source.git')
        self.git.init_bare(BRANCH)
        self.first = self.commit(b'binary source\x00\r\n')
        self.tip = self.commit(b'binary source\x00\r\nrevised', self.first)
        self.git.run('update-ref', BRANCH, self.tip)
        self.git.run('tag', '-a', 'v1', self.first, '-m', 'Original annotated tag')
        self.git.run('update-ref', b'refs/heads/topic/\xff', self.first)
        self.refs = {os.fsencode(name).hex(): oid for name, oid in self.git.refs().items()}
        self.roots = ''.join(oid + '\n' for oid in sorted(set(self.refs.values()))).encode('ascii')
        self.pack = self.root / 'source.pack'
        self.write_pack(self.git.run('pack-objects', '--stdout', '--revs', '--delta-base-offset',
                                    data=self.roots).stdout)

    def commit(self, content, parent=None):
        blob = self.git.run('hash-object', '-w', '--stdin', data=content).stdout.strip()
        tree = self.git.run('mktree', data=b'100644 blob ' + blob + b'\tfile.bin\n').stdout.strip()
        parents = ['-p', parent] if parent else []
        return self.git.run('commit-tree', tree, *parents, '-m', 'Fixture commit').stdout.strip().decode()

    def write_pack(self, raw):
        self.pack.write_bytes(raw)
        self.pack.chmod(0o600)
        self.digest = hashlib.sha256(raw).hexdigest()

    def stage(self, *, scope=SCOPE, digest=None):
        return store.stage(self.storage, self.pack, digest or self.digest, scope, self.refs,
                           BRANCH.encode().hex(), self.binary)

    def repository(self):
        return self.storage / '.'.join(SCOPE[key] for key in ('home', 'project_id', 'repository_id'))

    def test_stock_git_restores_exact_refs_pack_and_annotated_tag(self):
        snapshot, value = self.stage()
        self.assertEqual(self.stage(), (snapshot, value))
        entry = self.repository() / snapshot
        self.assertEqual(sorted(p.name for p in entry.iterdir()), ['objects.pack', 'snapshot.json'])
        self.assertEqual((entry / 'objects.pack').read_bytes(), self.pack.read_bytes())
        self.assertEqual(value['object_count'], 7)
        target = self.root / 'restored.git'
        self.assertEqual(store.restore(self.storage, snapshot, SCOPE, target, self.binary), value)
        restored = Git(self.binary, target)
        self.assertEqual(restored.refs(), self.git.refs())
        self.assertEqual(restored.run('cat-file', 'tag', TAG).stdout, self.git.run('cat-file', 'tag', TAG).stdout)
        self.assertEqual(restored.run('show', 'main:file.bin').stdout, b'binary source\x00\r\nrevised')
        restored.run('fsck', '--full', '--strict')
        clone = self.root / 'clone.git'
        restored.run('clone', '--no-local', '--bare', target, clone)
        self.assertEqual(Git(self.binary, clone).refs(), restored.refs())

    def test_rejects_bad_integrity_quota_and_outside_closure(self):
        raw = self.pack.read_bytes()
        with patch.object(store, 'MAX_OBJECT', 4):
            with self.assertRaisesRegex(ValueError, 'object-byte-limit'):
                self.stage()
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            self.stage(digest='0' * 64)
        self.write_pack(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'git-verification-failed'):
            self.stage()
        self.write_pack(raw[:8] + struct.pack('>I', store.MAX_OBJECTS + 1) + raw[12:])
        with self.assertRaisesRegex(ValueError, 'pack-object-limit'):
            self.stage()
        unrelated = self.git.run('hash-object', '-w', '--stdin', data=b'unrelated').stdout.strip()
        extra = self.git.run('pack-objects', '--stdout', '--revs', data=self.roots + unrelated + b'\n').stdout
        self.write_pack(extra)
        with self.assertRaisesRegex(ValueError, 'pack-ref-closure'):
            self.stage()
        self.assertEqual(list(self.repository().iterdir()), [])

    def test_restore_requires_exact_scope_digest_and_untampered_pack(self):
        snapshot, _ = self.stage()
        target = self.root / 'restored.git'
        with self.assertRaisesRegex(ValueError, 'snapshot-scope'):
            store.restore(self.storage, snapshot, SCOPE | {'authority_epoch': '2'}, target, self.binary)
        with self.assertRaises(OSError):
            store.restore(self.storage, '0' * 64, SCOPE, target, self.binary)
        with self.assertRaises(OSError):
            store.restore(self.storage, snapshot, SCOPE | {'home': '~nec'}, target, self.binary)
        stored = self.repository() / snapshot / 'objects.pack'
        raw = stored.read_bytes()
        stored.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            self.stage()
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            store.restore(self.storage, snapshot, SCOPE, target, self.binary)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob('.code-restore-*')))

    def test_attestation_reverifies_the_exact_home_snapshot(self):
        home_scope = SCOPE | {'repository_id': SCOPE['project_id']}
        snapshot, value = self.stage(scope=home_scope)
        attestation = store.attest(self.storage, snapshot, home_scope, self.binary)
        self.assertEqual(attestation, {'protocol': store.ATTESTATION_FORMAT, **home_scope,
            'snapshot': snapshot, 'head': value['head'], 'refs': self.refs, 'pack_sha256': self.digest,
            'pack_bytes': str(value['pack_bytes']), 'object_count': str(value['object_count']),
            'object_bytes': str(value['object_bytes']), 'object_ids_sha256': value['object_ids_sha256']})
        with self.assertRaisesRegex(ValueError, 'snapshot-scope'):
            store.attest(self.storage, snapshot, home_scope | {'authority_epoch': '2'}, self.binary)
        entry = self.storage / '.'.join(home_scope[key] for key in ('home', 'project_id', 'repository_id'))
        stored = entry / snapshot / store.PACK_NAME
        raw = stored.read_bytes()
        stored.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'pack-digest'):
            store.attest(self.storage, snapshot, home_scope, self.binary)

    def test_atomic_replay_at_capacity_and_concurrent_writer(self):
        snapshot, value = self.stage()
        with patch.object(store, 'MAX_SNAPSHOTS', 1):
            self.assertEqual(self.stage(), (snapshot, value))
            with self.assertRaisesRegex(ValueError, 'snapshot-capacity'):
                self.stage(scope=SCOPE | {'authority_epoch': '2'})
        with store.directory_fd(self.repository()) as directory:
            fcntl.flock(directory, fcntl.LOCK_EX)
            with self.assertRaises(BlockingIOError):
                self.stage()
        self.assertEqual([path.name for path in self.repository().iterdir()], [snapshot])

    def test_home_readback_rechecks_current_acceptance_before_publication(self):
        scope = SCOPE | {'repository_id': SCOPE['project_id']}
        snapshot, value = self.stage(scope=scope)
        report = {'snapshot': snapshot, 'request_id': '019939ba-4000-7000-8000-000000000003',
                  'object_count': str(value['object_count']), 'head': value['head']}
        observed = (scope, report, value['refs'])
        target = self.root / 'authorized.git'
        with patch.object(readback, 'observe', side_effect=[observed, ValueError('denied')]):
            with self.assertRaisesRegex(ValueError, 'denied'):
                readback.restore(None, None, scope['project_id'], self.storage, target, self.binary)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob('.code-restore-*')))
        with patch.object(readback, 'observe', side_effect=[observed, observed]) as observe:
            result = readback.restore(None, None, scope['project_id'], self.storage, target, self.binary)
        self.assertEqual(observe.call_count, 2)
        self.assertEqual(result['snapshot'], snapshot)
        self.assertEqual(Git(self.binary, target).refs(), self.git.refs())

    def upload_home_view(self):
        project = SCOPE['project_id']
        scope = SCOPE | {'repository_id': project}
        snapshot, value = self.stage(scope=scope)
        return scope, {'snapshot': snapshot, 'object_count': str(value['object_count']),
                       'head': value['head']}, value['refs']

    def test_stock_smart_http_client_reads_exact_accepted_pack(self):
        observed = self.upload_home_view()
        project = SCOPE['project_id']
        operations = []
        errors = []

        class Fixture(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, operation, request=b''):
                operations.append(operation)
                try:
                    with upload.response(None, None, project, self.server.storage,
                                         self.server.binary, operation, request) as (mime, length, spool):
                        self.send_response(200)
                        self.send_header('Content-Type', mime)
                        self.send_header('Content-Length', str(length))
                        self.end_headers()
                        shutil.copyfileobj(spool, self.wfile)
                except Exception as error:
                    errors.append(error)
                    self.send_error(500)

            def do_GET(self):
                if self.path != '/fixture.git/info/refs?service=git-upload-pack':
                    return self.send_error(404)
                self.respond('advertise')

            def do_POST(self):
                if self.path != '/fixture.git/git-upload-pack':
                    return self.send_error(404)
                self.respond('fetch', self.rfile.read(int(self.headers['Content-Length'])))

        clone = self.root / 'wire.git'
        with HTTPServer(('127.0.0.1', 0), Fixture) as server, \
                patch.object(upload, 'observe', return_value=observed) as home:
            server.storage, server.binary = self.storage, self.binary
            thread = Thread(target=server.serve_forever)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/fixture.git'
                with patch.dict(ENV, {'GIT_ALLOW_PROTOCOL': 'http'}):
                    self.git.run('clone', '--bare', url, clone)
                    client = Git(self.binary, clone)
                    # Drop the local tip and its objects so this fetch must ask
                    # the wire peer for the previously accepted commit again.
                    client.run('update-ref', BRANCH, self.first)
                    client.run('repack', '-Ad')
                    client.run('prune', '--expire=now')
                    self.assertNotEqual(client.run('cat-file', '-e', self.tip, check=False).returncode, 0)
                    client.run('fetch', url, f'{BRANCH}:{BRANCH}')
            finally:
                server.shutdown()
                thread.join()
        self.assertFalse(errors)
        self.assertEqual(operations, ['advertise', 'fetch', 'advertise', 'fetch'])
        self.assertEqual(home.call_count, 2 * len(operations))
        self.assertEqual(client.refs(), self.git.refs())
        self.assertEqual(client.run('cat-file', 'tag', TAG).stdout, self.git.run('cat-file', 'tag', TAG).stdout)
        client.run('fsck', '--full', '--strict')

    def test_stock_upload_never_discloses_on_revocation_or_bound_failure(self):
        observed = self.upload_home_view()
        project = SCOPE['project_id']
        with patch.object(upload, 'observe', side_effect=[observed, ValueError('denied')]):
            with self.assertRaisesRegex(ValueError, 'denied'), \
                    upload.response(None, None, project, self.storage, self.binary, 'advertise'):
                self.fail('revoked client received a spool')
        with patch.object(upload, 'observe', return_value=observed) as home:
            with self.assertRaisesRegex(ValueError, 'upload-pack-request'), \
                    upload.response(None, None, project, self.storage, self.binary, 'fetch', b'x' * 65537):
                self.fail('oversized request accepted')
            home.assert_not_called()
            with patch.object(upload, 'MAX_ADVERTISEMENT', 1):
                with self.assertRaisesRegex(ValueError, 'git-output-bound'), \
                        upload.response(None, None, project, self.storage, self.binary, 'advertise'):
                    self.fail('partial response disclosed')

    def test_readback_cli_resolves_relative_git_before_private_restore(self):
        executable = self.root / 'stock-git'
        executable.symlink_to(self.binary)
        relative = os.path.relpath(executable)
        target = self.root / 'authorized.git'
        credentials = {'principal_id': SCOPE['project_id']}
        with patch.object(readback, 'session_file', return_value=credentials), \
                patch.object(readback, 'HTTPSQueries') as https, \
                patch.object(readback, 'restore', return_value={'status': 'restored'}) as restore, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(readback.main([str(self.storage), str(target), '--project', SCOPE['project_id'],
                                           '--session-file', 'session.json', '--git', relative]), 0)
        restore.assert_called_once_with(https.return_value, credentials['principal_id'], SCOPE['project_id'],
                                        self.storage, target, str(Path(self.binary).resolve()))

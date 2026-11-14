"""Stock Git receive bytes yield only verified, immutable staging candidates."""
from hashlib import sha1
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import random
import shutil
import struct
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from dogfood_rehearsal import ENV, Git
import git_pack_receive as receive
import git_pack_store as store
from portable_recovery import sha


MAIN = b'refs/heads/main'
TOPIC = b'refs/heads/topic/\xff'
TAG = b'refs/tags/trial'
ZERO = b'0' * 40
SCOPE = dict.fromkeys(('project_id', 'repository_id'), '019939ba-4000-7000-8000-000000000001') | {
    'home': '~zod', 'authority_epoch': '1',
}


def packet(body):
    return f'{4 + len(body):04x}'.encode('ascii') + body


def pack_with_checksum(body):
    return body + sha1(body, usedforsecurity=False).digest()


def request(changes, pack, capabilities=b' report-status atomic ofs-delta agent=git/test'):
    lines = [b' '.join(row) for row in changes]
    lines[0] += b'\0' + capabilities
    return b''.join(packet(line) for line in lines) + b'0000' + pack


class GitPackReceiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.storage = self.root / 'store'
        self.storage.mkdir(mode=0o700)
        pinned = Path(__file__).resolve().parents[2] / '.runtime/tooling/git-2.55.0/bin/git'
        self.binary = str(pinned) if pinned.is_file() else shutil.which('git')
        self.source = Git(self.binary, self.root / 'source.git')
        self.source.init_bare(MAIN)
        body = random.Random(185).randbytes(32_768)
        self.first = self.commit(body)
        self.second = self.commit(body[:1000] + b'C0d3!' + body[1005:], self.first)
        self.source.run('update-ref', MAIN, self.second)
        self.source.run('update-ref', TAG, self.first)
        self.base_refs = {MAIN.hex(): self.first.decode()}
        initial = self.private('initial.pack', self.pack(self.first))
        self.base, _ = store.stage(self.storage, initial, sha(initial.read_bytes()), SCOPE,
                                   self.base_refs, MAIN.hex(), self.binary)

    def private(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        path.chmod(0o600)
        return path

    def commit(self, contents, parent=None):
        blob = self.source.run('hash-object', '-w', '--stdin', data=contents).stdout.strip()
        tree = self.source.run('mktree', data=b'100644 blob ' + blob + b'\tfile.bin\n').stdout.strip()
        parents = ('-p', parent) if parent else ()
        return self.source.run('commit-tree', tree, *parents, '-m', 'Receive fixture').stdout.strip()

    def pack(self, *revisions, thin=False):
        options = ('--thin',) if thin else ()
        return self.source.run('pack-objects', '--stdout', '--revs', '--delta-base-offset', '--threads=1',
                               *options, data=b'\n'.join(revisions) + b'\n').stdout

    def capture(self, *refspecs):
        received = []
        first = self.first

        class Capture(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, content_type, data):
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path != '/fixture.git/info/refs?service=git-receive-pack':
                    return self.send_error(404)
                self.reply('application/x-git-receive-pack-advertisement',
                    packet(b'# service=git-receive-pack\n') + b'0000' + packet(first + b' ' + MAIN
                        + b'\0report-status delete-refs ofs-delta atomic object-format=sha1 agent=fixture\n') + b'0000')

            def do_POST(self):
                if self.path != '/fixture.git/git-receive-pack' or 'Content-Length' not in self.headers:
                    return self.send_error(400)
                count = int(self.headers['Content-Length'])
                if not 0 < count <= 128 * 1024:
                    return self.send_error(400)
                received.append(self.rfile.read(count))
                # Capture only. The fixture never publishes refs or reports acceptance.
                self.reply('application/x-git-receive-pack-result', packet(b'unpack fixture capture only\n') + b'0000')

        with HTTPServer(('127.0.0.1', 0), Capture) as server:
            thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
            thread.start()
            try:
                with patch.dict(ENV, {'GIT_ALLOW_PROTOCOL': 'http'}):
                    denied = self.source.run('push', '--atomic', f'http://127.0.0.1:{server.server_port}/fixture.git',
                                             *refspecs, check=False)
            finally:
                server.shutdown()
                thread.join()
        self.assertNotEqual(denied.returncode, 0)
        self.assertEqual(len(received), 1, denied.stderr)
        return received[0]

    def prepare(self, wire):
        path = self.private('request.wire', wire)
        return receive.prepare(self.storage, SCOPE, self.base, path, sha(wire), self.binary)

    def snapshots(self):
        scope = '.'.join(SCOPE[key] for key in ('home', 'project_id', 'repository_id'))
        return {path.name for path in (self.storage / scope).iterdir()}

    def test_captured_stock_push_binds_wire_and_exact_ref_order(self):
        wire = self.capture(MAIN, TAG)
        parsed, _ = receive.parse(wire)
        self.assertEqual([(row['prior'], row['target']) for row in parsed],
                         [(self.first.decode(), self.second.decode()), (ZERO.decode(), self.first.decode())])
        result = self.prepare(wire)
        self.assertEqual(result['status'], 'candidate-staged')
        self.assertEqual(result['upload_sha256'], sha(wire))
        self.assertEqual([row['ref'] for row in result['changes']], [row['ref'] for row in parsed])
        expected = {MAIN.hex(): self.second.decode(), TAG.hex(): self.first.decode()}
        restored = self.root / 'candidate.git'
        manifest = store.restore(self.storage, result['candidate_snapshot'], SCOPE, restored, self.binary)
        self.assertEqual(manifest['refs'], expected)
        Git(self.binary, restored).run('fsck', '--full', '--strict')
        self.assertEqual(self.snapshots(), {self.base, result['candidate_snapshot']})

    def test_thin_pack_uses_only_verified_exact_base_and_preserves_ref_bytes(self):
        packed = self.pack(self.second, b'^' + self.first, thin=True)
        empty = Git(self.binary, self.root / 'empty.git')
        empty.init_bare(MAIN)
        thin = empty.run('index-pack', '--stdin', data=packed, check=False)
        self.assertNotEqual(thin.returncode, 0)
        self.assertIn(b'unresolved delta', thin.stderr)
        wire = request([(ZERO, self.first, TOPIC), (self.first, self.second, MAIN)], packed)
        result = self.prepare(wire)
        self.assertEqual(result['manifest']['refs'], {TOPIC.hex(): self.first.decode(), MAIN.hex(): self.second.decode()})
        self.assertEqual([row['ref'] for row in result['changes']], [TOPIC.hex(), MAIN.hex()])

    def test_zero_object_pack_can_create_tag_for_base_object(self):
        empty = pack_with_checksum(struct.pack('>4sII', b'PACK', 2, 0))
        wire = request([(ZERO, self.first, TAG)], empty)
        result = self.prepare(wire)
        self.assertEqual(result['manifest']['refs'], self.base_refs | {TAG.hex(): self.first.decode()})

    def test_wire_digest_and_file_custody_fence_staging(self):
        raw = request([(self.first, self.second, MAIN)], self.pack(self.second))
        ordinary = self.private('request.wire', raw)
        with self.assertRaisesRegex(ValueError, 'receive-wire-digest'):
            receive.prepare(self.storage, SCOPE, self.base, ordinary, '4' * 64, self.binary)
        ordinary.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'receive-private-wire'):
            receive.prepare(self.storage, SCOPE, self.base, ordinary, sha(raw), self.binary)
        ordinary.chmod(0o600)
        alternate = self.root / 'alternate'
        alternate.symlink_to(ordinary)
        with self.assertRaises(OSError):
            receive.prepare(self.storage, SCOPE, self.base, alternate, sha(raw), self.binary)
        alternate.unlink()
        os.link(ordinary, alternate)
        with self.assertRaisesRegex(ValueError, 'receive-private-wire'):
            receive.prepare(self.storage, SCOPE, self.base, ordinary, sha(raw), self.binary)
        self.assertEqual(self.snapshots(), {self.base})

    def test_shared_deadline_and_replaced_source_stop_candidate_staging(self):
        wire = request([(self.first, self.second, MAIN)], self.pack(self.second))
        path = self.private('request.wire', wire)
        with patch.object(receive, 'MAX_GIT_TIME', -1), self.assertRaisesRegex(ValueError, 'git-timeout'):
            receive.prepare(self.storage, SCOPE, self.base, path, sha(wire), self.binary)

        check = receive.push.check_ancestry

        def replace_during_candidate_check(repo, changes):
            checked = check(repo, changes)
            self.private('replacement.wire', wire).replace(path)
            return checked

        with patch.object(receive.push, 'check_ancestry', side_effect=replace_during_candidate_check), \
                self.assertRaisesRegex(ValueError, 'receive-wire-changed'):
            receive.prepare(self.storage, SCOPE, self.base, path, sha(wire), self.binary)
        self.assertEqual(self.snapshots(), {self.base})

    def test_invalid_command_pack_and_unsupported_features_fail_closed(self):
        packed = self.pack(self.second)
        changes = [(self.first, self.second, MAIN)]
        cases = [
            (b'zzzz', 'receive-pkt-line'), (b'0001', 'receive-pkt-line-bound'),
            (b'0000' + packed, 'receive-empty-command-list'),
            (request(changes * 2, packed), 'duplicate-ref'),
            (request([(self.first, ZERO, MAIN)], packed), 'ref-delete-unsupported'),
            (request(changes, packed, b'report-status push-options'), 'receive-capability'),
            (request(changes, packed, b'report-status report-status'), 'receive-capability-duplicate'),
            (request(changes, packed, b'object-format=sha1'), 'receive-report-status'),
            (request(changes, packed[:-1] + bytes([packed[-1] ^ 1])), 'receive-pack-checksum'),
            (request(changes, pack_with_checksum(packed + b'trailing data')), 'git-(output-bound|verification-failed)'),
        ]
        for wire, problem in cases:
            with self.subTest(problem=problem), self.assertRaisesRegex(ValueError, problem):
                self.prepare(wire)
        self.assertEqual(self.snapshots(), {self.base})

    def test_repacking_complete_stock_upload_preserves_accepted_content(self):
        complete = self.pack(self.second)
        wire = request([(self.first, self.second, MAIN)], complete)
        result = self.prepare(wire)
        self.assertEqual(result['manifest']['refs'], {MAIN.hex(): self.second.decode()})
        self.assertEqual(result['manifest']['object_count'], 6)

    def test_git_rejects_missing_or_unreachable_objects_and_trailing_pack(self):
        outside = self.commit(b'unrelated')
        for wire, problem in [
            (request([(self.first, outside, MAIN)], self.pack(self.second)), 'git-verification-failed'),
            (request([(self.first, self.second, MAIN)], self.pack(self.second, outside)), 'pack-object-count'),
            (request([(self.first, self.second, MAIN)], self.pack(outside)), 'git-verification-failed'),
            (request([(self.first, self.second, MAIN)], self.pack(self.second) + self.pack(outside)), 'receive-pack-checksum'),
        ]:
            with self.subTest(problem=problem), self.assertRaisesRegex(ValueError, problem):
                self.prepare(wire)
        self.assertEqual(self.snapshots(), {self.base})


if __name__ == '__main__':
    unittest.main()

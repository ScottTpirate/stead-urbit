"""Exercise exact Git receive reports with a stock worker and a simulated Home."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import os
from pathlib import Path
import time
from threading import Thread
from unittest.mock import Mock, patch

from test_git_pack_proof import GitPackProofTests
from test_git_pack_proof import MAIN, SCOPE, TAG

from dogfood_rehearsal import ENV
import git_pack_receive_adapter as adapter
from git_pack_private_worker import PrivatePackWorker
from portable_recovery import decoded, encoded, sha


def accept(admitted, evidence):
    claim = decoded(admitted.raw)
    result = decoded(evidence)
    record = {key: claim[key] for key in ('request_id', 'scope', 'actor', 'wire_sha256', 'changes', 'update_count')}
    return encoded(record | {'protocol': adapter.RECEIPT_PROTOCOL, 'status': 'accepted',
        'admission_sha256': admitted.sha256, 'candidate_snapshot': result['candidate_snapshot'],
        'generation': str(int(claim['generation']) + 1), 'accepted_at_ms': '1500'})


class PushAdapterTests(GitPackProofTests):
    def setUp(self):
        super().setUp()
        self.spools = self.root / 'spools'
        self.spools.mkdir(mode=0o700)
        self.bearer = 'a' * 64
        self.calls = []
        self.deadline = time.monotonic() + 25
        self.worker = PrivatePackWorker(self.storage, Path(self.git).resolve(), clock=lambda: 2000)

        def admit(bearer, request, deadline):
            self.check_call('admit', bearer, deadline)
            self.assertEqual(request.project, SCOPE['project_id'])
            self.assertEqual(request.wire_sha256, self.claim['wire_sha256'])
            self.assertEqual(request.changes, tuple(adapter.Change(**row) for row in self.claim['changes'].values()))
            raw = encoded(self.claim)
            return adapter.Admission(raw, sha(raw))

        def verify(bearer, admitted, evidence, deadline):
            self.check_call('verify', bearer, deadline)
            self.assertEqual(decoded(evidence)['admission_sha256'], admitted.sha256)
            return True

        def commit(bearer, admitted, evidence, deadline):
            self.check_call('commit', bearer, deadline)
            return accept(admitted, evidence)

        def recover(bearer, admitted, evidence, deadline):
            self.check_call('recover', bearer, deadline)
            return accept(admitted, evidence)

        self.home = Mock(spec=adapter.PushHome, admit=Mock(side_effect=admit), verify=Mock(side_effect=verify),
                         commit=Mock(side_effect=commit), recover=Mock(side_effect=recover))

    def check_call(self, phase, bearer, deadline):
        self.calls.append(phase)
        self.assertEqual(bearer, self.bearer)
        self.assertEqual(deadline, self.deadline)

    def receive(self, source=None, count=None):
        raw = self.wire.read_bytes()
        return adapter.receive_push(self.home, self.worker, self.spools, SCOPE['project_id'], self.bearer,
            BytesIO(raw) if source is None else source, len(raw) if count is None else count,
            deadline=self.deadline, clock=lambda: 2000)

    def test_only_durable_receipt_yields_report_status_in_exact_wire_order(self):
        stock = self.worker

        def inspect_hold(admitted, path, deadline):
            self.calls.append('worker')
            self.assertEqual(path.read_bytes(), self.wire.read_bytes())
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(len(list(self.spools.iterdir())), 1)
            return stock(admitted, path, deadline)

        self.worker = inspect_hold
        result = self.receive()
        self.assertEqual(result, adapter.packet(b'unpack ok\n') + adapter.packet(b'ok ' + TAG + b'\n')
                         + adapter.packet(b'ok ' + MAIN + b'\n') + b'0000')
        self.assertEqual(self.calls, ['admit', 'worker', 'verify', 'commit'])
        self.assertEqual(list(self.spools.iterdir()), [])

    def test_dual_failure_reports_are_correlated_and_commit_is_never_retried(self):
        self.home.commit.side_effect = OSError('reply interrupted')
        result = self.receive()
        self.assertIn(b'ok ' + MAIN, result)
        self.home.commit.assert_called_once()
        self.home.recover.assert_called_once()
        self.assertEqual(self.home.recover.call_args, self.home.commit.call_args)

        self.home.recover.side_effect = lambda *args: None
        with self.assertRaisesRegex(adapter.Uncertain, 'acceptance-unconfirmed'):
            self.receive()
        self.assertEqual(self.home.commit.call_count, 2)
        self.assertEqual(self.home.recover.call_count, 2)
        self.assertEqual(list(self.spools.iterdir()), [])

    def test_definite_refusal_is_ng_or_exception_before_unpack(self):
        self.home.verify.side_effect = lambda *args: False
        verified_refusal = self.receive()
        self.assertIn(b'ng ' + TAG + b' ', verified_refusal)
        self.assertIn(b'ng ' + MAIN + b' ', verified_refusal)
        self.assertNotIn(b'ok refs/', verified_refusal)
        self.home.commit.assert_not_called()
        self.home.verify.side_effect = lambda *args: True
        self.home.commit.side_effect = adapter.Rejected('home-rejected')
        self.assertEqual(self.receive(), verified_refusal)
        self.home.recover.assert_not_called()
        self.home.admit.side_effect = adapter.Rejected('home-rejected')
        with self.assertRaises(adapter.Rejected):
            self.receive()

    def test_receipt_substitution_is_unconfirmed_and_never_reports_success(self):
        def altered(bearer, admitted, evidence, deadline):
            original = decoded(accept(admitted, evidence))
            original['actor']['binding_revision'] = '9'
            return encoded(original)

        self.home.commit.side_effect = altered
        self.home.recover.side_effect = altered
        with self.assertRaisesRegex(adapter.Uncertain, 'acceptance-unconfirmed'):
            self.receive()
        self.home.commit.assert_called_once()
        self.home.recover.assert_called_once()

    def test_admission_or_worker_metadata_substitution_denies_writes(self):
        normal = self.home.admit.side_effect

        def redirected(*args):
            original = normal(*args)
            raw = encoded(decoded(original.raw) | {'wire_sha256': 'f' * 64})
            return replace(original, raw=raw, sha256=sha(raw))

        self.home.admit.side_effect = redirected
        with self.assertRaisesRegex(ValueError, 'admission-response'):
            self.receive()
        self.home.admit.side_effect = normal
        stock = self.worker

        def substituted(*args):
            result = decoded(stock(*args))
            result['updates']['00']['target'] = 'f' * 40
            return encoded(result)

        self.worker = substituted
        with self.assertRaisesRegex(ValueError, 'worker-response'):
            self.receive()
        self.home.verify.assert_not_called()
        self.home.commit.assert_not_called()

    def test_request_and_time_bounds_precede_current_authorization(self):
        with self.assertRaisesRegex(ValueError, 'push-body-bound'):
            self.receive(count=adapter.receive.MAX_WIRE + 1)
        with self.assertRaisesRegex(ValueError, 'push-body-length'):
            self.receive(source=BytesIO(b'a'))
        self.deadline = time.monotonic() - 1
        with self.assertRaisesRegex(ValueError, 'push-deadline'):
            self.receive()
        self.home.admit.assert_not_called()
        self.assertEqual(list(self.spools.iterdir()), [])

    def test_profile_does_not_claim_sideband_or_report_status_v2(self):
        raw = self.wire.read_bytes()
        first = int(raw[:4], 16)
        for suffix in (b' side-band-64k', b'-v2'):
            patched = adapter.packet(raw[4:first] + suffix) + raw[first:]
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'capability-not-advertised'):
                self.receive(source=BytesIO(patched), count=len(patched))
        self.home.admit.assert_not_called()

    def test_worker_requires_private_pinned_paths_and_checks_monotonic_deadline(self):
        raw = encoded(self.claim)
        admitted = adapter.Admission(raw, sha(raw))
        with self.assertRaisesRegex(ValueError, 'push-deadline'):
            self.worker(admitted, self.wire, time.monotonic() - 1)
        with self.assertRaisesRegex(ValueError, 'worker-private-paths'):
            self.worker(admitted, Path('relative.wire'), self.deadline)
        self.storage.rename(self.root / 'old-store')
        self.storage.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, 'worker-store-binding'):
            self.worker(admitted, self.wire, self.deadline)

    def test_worker_fences_replaced_git_and_rejects_altered_output_shape(self):
        original = Path(self.git).resolve()
        executable = self.root / 'stock-git'
        executable.write_bytes(original.read_bytes())
        executable.chmod(0o700)
        worker = PrivatePackWorker(self.storage, executable, clock=lambda: 2000)
        raw = encoded(self.claim)
        admitted = adapter.Admission(raw, sha(raw))
        with patch('git_pack_private_worker.proof.prepare', return_value=b'{"unscoped":"result"}') as verifier:
            with self.assertRaisesRegex(ValueError, 'record-shape'):
                worker(admitted, self.wire, self.deadline)
            _, arguments = verifier.call_args
            self.assertEqual(arguments['deadline'], self.deadline)
        executable.write_bytes(b'changed executable')
        with self.assertRaisesRegex(ValueError, 'worker-git-binding'):
            worker(admitted, self.wire, self.deadline)

    def test_stock_git_consumes_authoritative_success_and_refusal_reports(self):
        case = self
        problems = []
        topic = b'refs/heads/topic'
        self.source.run('update-ref', topic, self.tip)

        def admit(bearer, request, deadline):
            self.check_call('admit', bearer, deadline)
            raw = encoded(self.claim | {'wire_sha256': request.wire_sha256, 'update_count': str(len(request.changes)),
                'changes': {f'{index:02d}': {'ref': row.ref, 'prior': row.prior, 'target': row.target}
                            for index, row in enumerate(request.changes)}})
            return adapter.Admission(raw, sha(raw))

        self.home.admit.side_effect = admit

        def deny(bearer, admitted, evidence, deadline):
            self.check_call('commit', bearer, deadline)
            raise adapter.Rejected('home-rejected')

        class Fixture(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, code, subtype, raw):
                self.send_response(code)
                self.send_header('Content-Type', 'application/x-git-receive-pack-' + subtype)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                advertised = adapter.packet(b'# service=git-receive-pack\n') + b'0000'
                advertised += adapter.packet(case.base + b' ' + MAIN + b'\0' + b' '.join(sorted(adapter.CAPABILITIES)) + b'\n')
                self.reply(200, 'advertisement', advertised + b'0000')

            def do_POST(self):
                try:
                    result = case.receive(self.rfile, int(self.headers['Content-Length']))
                    self.reply(200, 'result', result)
                except Exception as error:
                    problems.append(error)
                    self.reply(500, 'result', b'')

        with HTTPServer(('127.0.0.1', 0), Fixture) as server:
            thread = Thread(target=server.serve_forever, kwargs={'poll_interval': .05})
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/fixture.git'
                with patch.dict(ENV, {'GIT_ALLOW_PROTOCOL': 'http'}):
                    accepted = self.source.run('push', '--atomic', url, topic, check=False)
                    self.home.commit.side_effect = deny
                    rejected = self.source.run('push', '--atomic', url, topic, check=False)
            finally:
                server.shutdown()
                thread.join()
        self.assertFalse(problems)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(b'authoritative Home refused the update', rejected.stderr)
        self.assertEqual(self.calls, ['admit', 'verify', 'commit', 'admit', 'verify', 'commit'])


# The proof suite supplies reusable fixture construction. Its assertions are
# already discovered in its own file, so run only the adapter-specific arms.
def load_tests(loader, _standard, _pattern):
    return loader.suiteClass(PushAdapterTests(name) for name in loader.getTestCaseNames(PushAdapterTests)
                             if name in PushAdapterTests.__dict__)

"""Check isolated worker framing, process identity and signed proof custody."""
from hashlib import sha256
import os
from pathlib import Path
from queue import Queue
import socket
import stat
import subprocess
from threading import Thread, current_thread
import time
import unittest
from unittest.mock import Mock, patch

import test_git_pack_proof as fixtures
from git_pack_private_worker import PrivatePackWorker
from git_pack_receive_adapter import Admission
import git_pack_worker_signature as signing
import git_pack_worker_socket as transport
from portable_recovery import RecoveryError, decoded, encoded, sha


class WorkerSocketTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GitPackProofTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.parent = self.root / 'run'
        self.parent.mkdir(mode=0o710)
        self.parent.chmod(0o710)
        self.address = self.parent / 'worker.sock'
        self.spool = self.root / 'spool'
        self.spool.mkdir(mode=0o700)
        self.uid = os.getuid()
        self.relay_uid = self.uid + 1
        self.generation = 7
        self.claim = self.fixture.claim
        raw = encoded(self.claim)
        self.admission = Admission(raw, sha(raw))
        self.wire = self.fixture.wire.read_bytes()
        self.key = self.root / 'worker.pem'
        self.assertEqual(self.openssl('genpkey', '-algorithm', 'Ed25519', '-out', str(self.key)).returncode, 0)
        self.key.chmod(0o600)
        self.deadline = time.monotonic() + 20

    def openssl(self, *args):
        return subprocess.run((signing.OPENSSL, *args), stdin=subprocess.DEVNULL,
                              capture_output=True, env=signing.ENV, timeout=5)

    def service(self, worker, *, clock=lambda: 2000):
        return transport.WorkerSocket(self.address, self.spool, self.relay_uid, self.uid, worker,
                                      self.generation, self.key, group_gid=os.getgid(), clock=clock)

    def start(self, service):
        output = Queue()

        def serve():
            try:
                output.put(service.serve_one(self.deadline))
            except Exception as error:
                output.put(error)

        runner = Thread(target=serve, daemon=True)
        runner.start()
        return runner, output

    def result(self, runner, output):
        runner.join(timeout=6)
        self.assertFalse(runner.is_alive(), 'worker did not finish')
        status = output.get_nowait()
        if isinstance(status, Exception):
            raise status
        return status

    def exchange(self, worker):
        actual_peer = transport.peer_is
        caller = current_thread()

        def peer(channel, expected):
            # This test process has one UID. Exercise the real kernel check on
            # both descriptors and inject the successful cross-UID test result.
            self.assertEqual(expected, self.uid if current_thread() is caller else self.relay_uid)
            actual_peer(channel, self.uid)

        def getuid():
            return self.relay_uid if current_thread() is caller else self.uid

        local_owner = Mock(wraps=os, getuid=Mock(side_effect=getuid), geteuid=Mock(side_effect=getuid))
        with self.service(worker) as service, patch.object(transport, 'peer_is', side_effect=peer), \
                patch.object(transport, 'os', local_owner):
            runner, output = self.start(service)
            try:
                response = transport.request(self.address, self.uid, self.relay_uid, self.admission,
                                             self.fixture.wire, self.deadline, clock=lambda: 2000)
            finally:
                result = self.result(runner, output)
            self.assertTrue(result)
        return response

    def test_exact_stock_worker_proof_and_independent_signature(self):
        stock = PrivatePackWorker(self.fixture.storage, Path(self.fixture.git).resolve(), clock=lambda: 2000)
        requests = []

        def inspect(admitted, path, deadline):
            self.assertEqual(admitted, self.admission)
            self.assertEqual(path.read_bytes(), self.wire)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(path.parent.parent, self.spool)
            self.assertLessEqual(deadline, self.deadline - transport.SIGN_SECONDS)
            requests.append(path)
            return stock(admitted, path, deadline)

        response = self.exchange(inspect)
        self.assertEqual(response.generation, self.generation)
        result = decoded(response.proof)
        self.assertEqual(result['admission_sha256'], self.admission.sha256)
        self.assertEqual(result['wire_sha256'], self.claim['wire_sha256'])
        self.assertEqual(len(requests), 1)
        self.assertEqual(list(self.spool.iterdir()), [])
        self.assertFalse(self.address.exists())

        certificate = self.root / 'public.pem'
        self.assertEqual(self.openssl('pkey', '-in', str(self.key), '-pubout', '-out', str(certificate)).returncode, 0)
        signature, message = self.root / 'sign.bin', self.root / 'proof.bin'
        signature.write_bytes(bytes.fromhex(response.signature))
        message.write_bytes(b'stead.git-pack-worker-attestation/1\x00' + str(self.generation).encode() + b'\x00'
                            + sha256(response.proof).hexdigest().encode())
        args = ('pkeyutl', '-verify', '-rawin', '-pubin', '-inkey', str(certificate),
                '-sigfile', str(signature), '-in', str(message))
        self.assertEqual(self.openssl(*args).returncode, 0)
        message.write_bytes(message.read_bytes().replace(b'\x007\x00', b'\x008\x00'))
        self.assertNotEqual(self.openssl(*args).returncode, 0)

    def test_real_kernel_rejects_different_relay_uid_before_request(self):
        worker = Mock()
        with self.service(worker) as service, socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            runner, output = self.start(service)
            client.settimeout(2)
            client.connect(str(self.address))
            self.assertEqual(client.recv(1), b'')
            self.assertFalse(self.result(runner, output))
        worker.assert_not_called()

    def test_real_kernel_rejects_different_worker_uid_before_admission_is_sent(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.address))
            listener.listen(1)
            with self.assertRaisesRegex(RecoveryError, 'worker-socket-peer'):
                transport.request(self.address, self.relay_uid, self.uid, self.admission, self.fixture.wire,
                                  self.deadline, clock=lambda: 2000)
            listener.settimeout(2)
            peer, _ = listener.accept()
            with peer:
                self.assertEqual(peer.recv(1), b'')

    def test_malformed_bounds_expiration_trailing_bytes_and_digest_do_not_reach_worker(self):
        worker = Mock()
        admitted = self.admission
        digest = bytes.fromhex(admitted.sha256)
        future = int(self.deadline * 1_000_000_000)
        current = time.monotonic_ns()
        plain = (transport.REQUEST_MAGIC, future, len(admitted.raw), len(self.wire), digest)
        expected = transport.RESPONSE.pack(transport.RESPONSE_MAGIC, transport.REFUSED, 0, 0)
        samples = {
            'admission bound': (transport.REQUEST.pack(*plain[:2], transport.proof.MAX_MESSAGE + 1, *plain[3:]), b''),
            'wire bound': (transport.REQUEST.pack(*plain[:3], transport.receive.MAX_WIRE + 1, digest), b''),
            'deadline': (transport.REQUEST.pack(plain[0], current, *plain[2:]), b''),
            'digest': (transport.REQUEST.pack(*plain), admitted.raw + self.wire[:-1] + b'X'),
            'trailing': (transport.REQUEST.pack(*plain), admitted.raw + self.wire + b'X'),
            'truncated': (transport.REQUEST.pack(*plain), admitted.raw + self.wire[:-1]),
        }
        with self.service(worker) as service, patch.object(transport, 'peer_is'):
            for name, (header, body) in samples.items():
                with self.subTest(name=name), socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    runner, output = self.start(service)
                    client.settimeout(2)
                    client.connect(str(self.address))
                    client.sendall(header + body)
                    client.shutdown(socket.SHUT_WR)
                    self.assertEqual(transport.read_exact(client, len(expected), self.deadline), expected)
                    self.assertFalse(self.result(runner, output))
        worker.assert_not_called()
        self.assertEqual(list(self.spool.iterdir()), [])

    def test_substituted_proof_or_expired_admission_never_gets_signed_reply(self):
        valid = self.fixture.export(self.claim)
        changed = decoded(valid)
        changed['candidate_snapshot'] = 'not-a-snapshot-digest'
        too_late = iter((2000, 2000, 6000))
        header = transport.REQUEST.pack(transport.REQUEST_MAGIC, int(self.deadline * 1_000_000_000),
                                        len(self.admission.raw), len(self.wire), bytes.fromhex(self.admission.sha256))
        for name, evidence, clock, signing_calls in (
            ('invalid proof', encoded(changed), lambda: 2000, 0),
            ('expired before reply', valid, lambda: next(too_late), 1),
        ):
            with self.subTest(name=name), self.service(Mock(return_value=evidence), clock=clock) as service, \
                    patch.object(transport, 'peer_is'), patch.object(signing, 'sign', return_value='c' * 128) as signer, \
                    socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                runner, output = self.start(service)
                client.settimeout(2)
                client.connect(str(self.address))
                client.sendall(header + self.admission.raw + self.wire)
                client.shutdown(socket.SHUT_WR)
                expected = transport.RESPONSE.pack(transport.RESPONSE_MAGIC, transport.REFUSED, 0, 0)
                self.assertEqual(transport.read_exact(client, len(expected), self.deadline), expected)
                self.assertEqual(client.recv(1), b'')
                self.assertFalse(self.result(runner, output))
                self.assertEqual(signer.call_count, signing_calls)
        self.assertEqual(list(self.spool.iterdir()), [])

    def test_same_uid_or_unsafe_parent_refused_and_cleanup_keeps_replacement(self):
        worker = Mock()
        with self.assertRaisesRegex(RecoveryError, 'worker-peer-profile'):
            transport.WorkerSocket(self.address, self.spool, self.uid, self.uid, worker, self.generation,
                                   self.key, group_gid=os.getgid())
        self.parent.chmod(0o770)
        with self.assertRaisesRegex(RecoveryError, 'worker-socket-private-parent'), self.service(worker):
            pass
        self.parent.chmod(0o710)
        with self.service(worker):
            self.assertEqual(stat.S_IMODE(self.address.stat().st_mode), 0o660)
            with self.assertRaises(OSError), self.service(worker):
                pass
            self.address.unlink()
            self.address.write_bytes(b'different object')
        self.assertEqual(self.address.read_bytes(), b'different object')


if __name__ == '__main__':
    unittest.main()

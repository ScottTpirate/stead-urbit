"""Khan control encoding and failures stay local and preserve original bytes."""
import base64
import re
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_local_home as control
import git_pack_proof as proof
from git_pack_receive_adapter import Admission, Change, PushRequest, RECEIPT_PROTOCOL, Rejected
from portable_recovery import RecoveryError, encoded, sha
from test_git_pack_http import current_decision


PROJECT = '019939ba-4000-7000-8000-000000000001'
ID = '019939ba-4000-7000-8000-000000000002'
ACTOR = {'identity_ship': '~bus', 'principal_id': '019939ba-4000-7000-8000-000000000003',
         'binding_id': '019939ba-4000-7000-8000-000000000004', 'binding_revision': '1'}
BEARER = '7' * 64
WIRE = '9' * 64
RAW_REF = b'refs/heads/topic/\xff'
CHANGE = Change(RAW_REF.hex(), '0' * 40, '01' * 19 + 'ff')
CHANGE_VIEW = {'ref': CHANGE.ref, 'prior': CHANGE.prior, 'target': CHANGE.target}
NOUN = re.compile(r'\[32 %fyrd \[%base %stead-code-pack-local %noun \[%noun \[~zod \['
                  r'(0x\S+) (0x\S+) (0x\S+) (0x\S+) \[%(admit|verify|commit|receipt|advertise) (.*)\]\]\]\]\]\]', re.ASCII)


def decode_cord(raw):
    number = int(raw.replace('.', ''), 16)
    return number.to_bytes((number.bit_length() + 7) // 8, 'little')


class LocalHomeTests(unittest.TestCase):
    def setUp(self):
        self.values = {'protocol': proof.ADMISSION, 'scope': {'home': '~zod', 'project_id': PROJECT,
                       'repository_id': PROJECT, 'authority_epoch': '1'}, 'base_snapshot': '0' * 64,
                       'generation': '0', 'attempt': '1', 'incarnation': '1' * 64, 'request_id': ID,
                       'actor': ACTOR, 'wire_sha256': WIRE, 'changes': {'00': CHANGE_VIEW}, 'update_count': '1',
                       'admitted_at_ms': '1000', 'expires_at_ms': '6000'}
        raw = encoded(self.values)
        self.admitted = Admission(raw, sha(raw))
        self.evidence = encoded({'fixture': 'bytes with a quotation mark " and café'})
        self.receipt = encoded({'protocol': RECEIPT_PROTOCOL, 'status': 'accepted'})
        self.deadline = time.monotonic() + 5
        self.exchange = Mock()
        self.home = control.LocalHome(self.exchange, clock=lambda: 2000)

    def check_nouns(self):
        nonces = []
        tasks = []
        for call in self.exchange.call_args_list:
            noun, deadline = call.args
            self.assertEqual(deadline, self.deadline)
            decoded = NOUN.fullmatch(noun)
            self.assertIsNotNone(decoded)
            nonce, project, bearer, request, operation, payload = decoded.groups()
            nonces.append(decode_cord(nonce))
            self.assertEqual(decode_cord(project), PROJECT.encode())
            self.assertEqual(decode_cord(request), ID.encode())
            self.assertEqual(decode_cord(bearer), BEARER.encode())
            tasks.append((operation, payload))
        self.assertEqual(len(set(nonces)), len(nonces))
        self.assertTrue(all(re.fullmatch(rb'[0-9a-f]{64}', nonce) for nonce in nonces))
        return tasks

    def test_khan_atom_arguments_preserve_ref_oid_admission_and_proof_bytes(self):
        self.exchange.side_effect = [self.admitted.raw, control.VERIFIED, self.receipt, self.receipt]
        with patch.object(control, 'new_id', return_value=ID):
            admitted = self.home.admit(BEARER, PushRequest(PROJECT, WIRE, (CHANGE,)), self.deadline)
        self.assertEqual(admitted, self.admitted)
        self.assertIs(self.home.verify(BEARER, admitted, self.evidence, self.deadline), True)
        self.assertEqual(self.home.commit(BEARER, admitted, self.evidence, self.deadline), self.receipt)
        self.assertEqual(self.home.recover(BEARER, admitted, self.evidence, self.deadline), self.receipt)
        tasks = self.check_nouns()
        self.assertEqual([step for step, _ in tasks], ['admit', 'verify', 'commit', 'receipt'])
        wire, ref, old, new = re.fullmatch(r'(0x\S+) \[\[(0x\S+) (0x\S+) (0x[^\]]+)] ~]', tasks[0][1]).groups()
        self.assertEqual(decode_cord(wire), WIRE.encode())
        self.assertEqual(decode_cord(ref), RAW_REF)
        self.assertEqual(int(old.replace('.', ''), 16), 0)
        self.assertEqual(int(new.replace('.', ''), 16), int(CHANGE.target, 16))
        for _, payload in tasks[1:]:
            adm, digest, proof_bytes = map(decode_cord, payload.split())
            self.assertEqual((adm, digest, proof_bytes), (admitted.raw, admitted.sha256.encode(), self.evidence))

    def test_refusal_exactness_and_secret_bearing_transport_errors_are_sanitized(self):
        self.exchange.return_value = b'{"reason":"proof-conflict","status":"refused"}'
        with self.assertRaisesRegex(Rejected, '^local-pack-refused$'):
            self.home.commit(BEARER, self.admitted, self.evidence, self.deadline)
        self.assertIsNone(self.home.recover(BEARER, self.admitted, self.evidence, self.deadline))
        for malformed in (b'{"reason":"proof-conflict","status":"refused"}\n',
                          encoded({'status': 'refused', 'reason': 'secret:' + BEARER}),
                          b'{"status":"refused","status":"verified"}', b'', b'x' * (proof.MAX_MESSAGE + 1)):
            self.exchange.return_value = malformed
            with self.subTest(length=len(malformed)), self.assertRaises(RecoveryError) as caught:
                self.home.commit(BEARER, self.admitted, self.evidence, self.deadline)
            self.assertNotIn(BEARER, str(caught.exception))
            self.assertNotIsInstance(caught.exception, Rejected)

        def noisy(*args):
            raise OSError('secret noun: ' + args[0])

        self.exchange.side_effect = noisy
        with self.assertRaisesRegex(RecoveryError, '^local-pack-exchange-unavailable$') as caught:
            self.home.commit(BEARER, self.admitted, self.evidence, self.deadline)
        self.assertIsNone(caught.exception.__context__)
        self.assertIsNone(caught.exception.__cause__)

    def test_exact_refusal_receipt_and_admission_digests_gate_calls(self):
        with self.assertRaisesRegex(ValueError, 'local-pack-input'):
            self.home.verify(BEARER, Admission(self.admitted.raw, '4' * 64), self.evidence, self.deadline)
        with self.assertRaisesRegex(ValueError, 'local-pack-input'):
            self.home.verify(BEARER, self.admitted, self.evidence.rstrip(), self.deadline)
        with self.assertRaisesRegex(ValueError, 'push-deadline'):
            self.home.verify(BEARER, self.admitted, self.evidence, time.monotonic() - 1)
        self.exchange.assert_not_called()
        self.exchange.return_value = self.receipt.rstrip(b'\n')
        with self.assertRaisesRegex(ValueError, 'local-pack-receipt'):
            self.home.commit(BEARER, self.admitted, self.evidence, self.deadline)

    def test_receipt_recovery_can_use_original_admission_after_expiry(self):
        self.home = control.LocalHome(self.exchange, clock=lambda: 10_000)
        self.exchange.return_value = self.receipt
        with self.assertRaisesRegex(ValueError, 'proof-lease'):
            self.home.commit(BEARER, self.admitted, self.evidence, self.deadline)
        self.exchange.assert_not_called()
        self.assertEqual(self.home.recover(BEARER, self.admitted, self.evidence, self.deadline), self.receipt)
        self.assertEqual(self.check_nouns()[0][0], 'receipt')

    def test_fake_identity_and_issued_request_binding(self):
        foreign = encoded(self.values | {'scope': self.values['scope'] | {'home': '~nec'}})
        with self.assertRaisesRegex(ValueError, 'fake-required'):
            self.home.recover(BEARER, Admission(foreign, sha(foreign)), self.evidence, self.deadline)
        self.exchange.assert_not_called()
        for changed in ({'request_id': ACTOR['principal_id']}, {'wire_sha256': '2' * 64}):
            self.exchange.return_value = encoded(self.values | changed)
            with patch.object(control, 'new_id', return_value=ID), self.assertRaisesRegex(ValueError, 'local-pack-admission'):
                self.home.admit(BEARER, PushRequest(PROJECT, WIRE, (CHANGE,)), self.deadline)

    def test_advertisement_uses_exact_basic_and_write_checked_canonical_metadata(self):
        auth = 'Basic ' + base64.b64encode(('stead:' + BEARER).encode('ascii')).decode('ascii')
        raw = encoded(current_decision()[1])[:-1]
        self.exchange.return_value = raw
        with patch.object(control, 'new_id', return_value=ID):
            self.assertEqual(self.home.advertise(auth, PROJECT, deadline=self.deadline), raw)
        self.assertEqual(self.check_nouns(), [('advertise', '~')])

        self.exchange.return_value = raw + b'\n'
        with self.assertRaisesRegex(ValueError, 'local-pack-advertisement'):
            self.home.advertise(auth, PROJECT)
        self.exchange.return_value = b'{"reason":"denied","status":"refused"}'
        with self.assertRaisesRegex(control.git_pack_http.Denied, '^local-pack-refused$'):
            self.home.advertise(auth, PROJECT)
        prior = self.exchange.call_count
        with self.assertRaises(control.git_pack_http.Denied):
            self.home.advertise(auth + ' ', PROJECT)
        self.assertEqual(self.exchange.call_count, prior)

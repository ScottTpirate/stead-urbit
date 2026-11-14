"""Check the exact private Git relay frame without running a transport."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_proof as proof
from git_pack_push import ZERO_OID
from git_pack_receive_adapter import Admission, Change, PushRequest
import git_pack_relay_wire as wire
from portable_recovery import RecoveryError, decoded, encoded, sha


PROJECT = '019939ba-4000-7000-8000-000000000001'
REQUEST = '019939ba-4000-7000-8000-000000000004'
MAIN = b'refs/heads/main'.hex()
TAG = b'refs/tags/exact-\xff'.hex()
SIGNATURE = 'ab' * 64
CHANGES = (Change(TAG, ZERO_OID, 'b' * 40), Change(MAIN, 'a' * 40, 'c' * 40))


class RelayWireTests(unittest.TestCase):
    def setUp(self):
        self.request = PushRequest(PROJECT, 'd' * 64, CHANGES)
        self.claim = {
            'protocol': proof.ADMISSION,
            'scope': {'home': '~zod', 'authority_epoch': '1', 'project_id': PROJECT, 'repository_id': PROJECT},
            'actor': {'identity_ship': '~bus', 'principal_id': '019939ba-4000-7000-8000-000000000002',
                      'binding_id': '019939ba-4000-7000-8000-000000000003', 'binding_revision': '3'},
            'base_snapshot': 'a' * 64, 'generation': '0', 'attempt': '1', 'incarnation': 'b' * 64,
            'request_id': REQUEST, 'wire_sha256': self.request.wire_sha256,
            'admitted_at_ms': '1000', 'expires_at_ms': '1400', 'update_count': '2',
            'changes': {'00': {'ref': TAG, 'prior': ZERO_OID, 'target': 'b' * 40},
                        '01': {'ref': MAIN, 'prior': 'a' * 40, 'target': 'c' * 40}},
        }
        raw = encoded(self.claim)
        self.admission = Admission(raw, sha(raw))
        self.result = {key: self.claim[key] for key in proof.CLAIM - {'changes'}}
        self.result.update(protocol=proof.PROTOCOL, admission_sha256=self.admission.sha256,
                           candidate_snapshot='c' * 64, head=MAIN,
                           pack={'pack_sha256': 'd' * 64, 'pack_bytes': '128', 'object_count': '2',
                                 'object_bytes': '64', 'object_ids_sha256': 'e' * 64},
                           updates={'00': {**self.claim['changes']['00'], 'kind': 'tag', 'lineage': 'none'},
                                    '01': {**self.claim['changes']['01'], 'kind': 'commit', 'lineage': 'fast-forward'}})
        self.evidence = encoded(self.result)

    def test_advertisement_and_admission_are_one_exact_line(self):
        self.assertEqual(wire.advertise(REQUEST),
            b'{"protocol":"stead.git-pack-relay/1","request_id":"019939ba-4000-7000-8000-000000000004",'
            b'"step":"advertise"}\n')
        body = wire.admit(REQUEST, self.request)
        expected = {'protocol': 'stead.git-pack-relay/1', 'step': 'admit', 'request_id': REQUEST,
                    'wire_sha256': self.request.wire_sha256, 'update_count': '2', 'changes': self.claim['changes']}
        self.assertEqual(body, encoded(expected))
        self.assertEqual(body.count(b'\n'), 1)
        reversed_request = replace(self.request, changes=CHANGES[::-1])
        self.assertEqual(decoded(wire.admit(REQUEST, reversed_request))['changes']['00']['ref'], MAIN)

    def test_verify_commit_and_receipt_use_exact_original_lines(self):
        for step in ('verify', 'commit', 'receipt'):
            with self.subTest(step=step):
                expected = {'admission_sha256': self.admission.sha256, 'protocol': 'stead.git-pack-relay/1',
                            'request_id': REQUEST, 'step': step}
                options = {}
                if step != 'receipt':
                    options = {'now_ms': 1300, 'worker_generation': 7, 'worker_signature': SIGNATURE}
                    expected.update(worker_generation='7', worker_signature=SIGNATURE)
                output = wire.transition(step, self.admission, self.evidence, **options)
                self.assertEqual(output.splitlines(keepends=True), [encoded(expected), self.admission.raw, self.evidence])

    def test_invalid_request_changes_and_header_overflow_are_rejected(self):
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-request-id'):
            wire.advertise(REQUEST.upper())
        invalid = (replace(self.request, project='wrong'), replace(self.request, changes=()),
                   replace(self.request, changes=(CHANGES[0], CHANGES[0])),
                   replace(self.request, changes=(Change(MAIN, 'a' * 40, ZERO_OID),)),
                   replace(self.request, changes=(Change(TAG, 'a' * 40, 'b' * 40),)))
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(RecoveryError):
                wire.admit(REQUEST, request)
        long_refs = tuple(Change((f'refs/heads/{i:02d}'.encode() + b'x' * 1011).hex(), ZERO_OID, 'b' * 40)
                          for i in range(32))
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-frame-bound'):
            wire.admit(REQUEST, replace(self.request, changes=long_refs))

    def test_reject_missing_expired_or_noncanonical_worker_auth_metadata(self):
        options = {'now_ms': 1300, 'worker_generation': 7, 'worker_signature': SIGNATURE}
        for overrides in ({'worker_signature': SIGNATURE.upper()}, {'worker_signature': 'ab' * 63},
                          {'worker_signature': None}, {'worker_generation': 0}, {'worker_generation': True},
                          {'worker_generation': 2**64}, {'now_ms': 1400}, {'now_ms': None}):
            with self.subTest(overrides=overrides), self.assertRaises(RecoveryError):
                wire.transition('verify', self.admission, self.evidence, **(options | overrides))
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-receipt-worker'):
            wire.transition('receipt', self.admission, self.evidence, **options)
        with self.assertRaisesRegex(RecoveryError, 'pack-relay-step'):
            wire.transition('admit', self.admission, self.evidence, **options)

    def test_reject_document_substitution_and_extra_lines(self):
        options = {'now_ms': 1300, 'worker_generation': 2**64 - 1, 'worker_signature': SIGNATURE}
        invalid_evidence = (self.evidence.rstrip(b'\n'), self.evidence + b'\n',
                            b'\n' + self.evidence, b'x' * (proof.MAX_MESSAGE + 1),
                            encoded(self.result | {'request_id': PROJECT}),
                            encoded(self.result | {'admission_sha256': 'f' * 64}),
                            encoded(self.result | {'updates': {'00': self.result['updates']['01'],
                                                               '01': self.result['updates']['00']}}))
        for evidence in invalid_evidence:
            with self.subTest(length=len(evidence)), self.assertRaises(RecoveryError):
                wire.transition('commit', self.admission, evidence, **options)
            with self.assertRaises(RecoveryError):
                wire.transition('receipt', self.admission, evidence)
        wrong_hash = replace(self.admission, sha256='f' * 64)
        with self.assertRaisesRegex(RecoveryError, 'proof-admission-digest'):
            wire.transition('commit', wrong_hash, self.evidence, **options)
        extra_line = self.admission.raw + b'\n'
        with self.assertRaisesRegex(RecoveryError, 'proof-admission-format'):
            wire.transition('receipt', Admission(extra_line, sha(extra_line)), self.evidence)

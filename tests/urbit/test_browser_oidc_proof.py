"""Check Stead proof bytes against the independent published profile vector."""
from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import browser_oidc_proof as proof
from portable_recovery import RecoveryError, decoded, encoded, sha


PIN = proof.VerifierPin('~zod', 'https://home.example.test', '00000000-0000-4000-8000-000000000001',
                        '00000000-0000-4000-8000-000000000002', '1', '00000000-0000-4000-8000-000000000003',
                        'https://idp.example.test', 'test-client',
                        'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')
CHALLENGE = proof.Challenge('11' * 32, '22' * 32, 1_070_000, '33' * 32)
IDENTITY = proof.VerifiedIdentity(PIN.issuer, 'alice', (PIN.client_id,), None, CHALLENGE.nonce, 995_000, 1_060_000)
NOW = 1_000_000
KEY = bytes(range(32))
TAG = '3fd14320b0de7d6bb5f48da4c8d558ab8658c9b24a7d5a41305cdc82b346c4d8'
SIGNATURE = ('21baf7a271d9d2c1c163f5ef35413c5c8da94c7b2b7663967d80164c119caef167'
             '1dd34df4e439dfd4819f08af10a2aca29032183ba300bf4abcf731d6009e04')
PRIVATE = (b'-----BEGIN PRIVATE KEY-----\n'
           b'MC4CAQAwBQYDK2VwBCIEIJ1hsZ3v/VpguoRK9JLsLMREScVpezJpGXA7rAMcrn9g\n'
           b'-----END PRIVATE KEY-----\n')


class OidcProofTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.key = Path(temporary.name) / 'key.pem'
        fd = os.open(self.key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(PRIVATE)

    def test_exact_profile_vector_and_key_validation(self):
        raw = proof.issue(PIN, CHALLENGE, IDENTITY, KEY, self.key, NOW)
        row = decoded(raw)
        self.assertEqual(row.pop('signature'), SIGNATURE)
        self.assertEqual(row['subject_tag'], TAG)
        message = proof.signing_bytes(row)
        self.assertEqual(len(message), 602)
        self.assertEqual(sha(message), '5a8117dfc33b6fddfae133ef811116e9fec5d6f517e481440a8d767f7c57a3f9')
        self.assertEqual(proof.verify(raw, PIN, CHALLENGE, NOW), row)
        mismatched = replace(PIN, public_key='3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c')
        with self.assertRaisesRegex(RecoveryError, 'oidc-key-pin'):
            proof.issue(mismatched, CHALLENGE, IDENTITY, KEY, self.key, NOW)

    def test_no_unicode_normalization_or_alias_collapse_in_exact_subject(self):
        self.assertNotEqual(proof.subject_tag(KEY, PIN.issuer, 'alice'), proof.subject_tag(KEY, PIN.issuer, 'Alice'))
        self.assertNotEqual(proof.subject_tag(KEY, PIN.issuer, 'é'), proof.subject_tag(KEY, PIN.issuer, 'e\u0301'))
        self.assertNotEqual(proof.subject_tag(KEY, PIN.issuer, 'alice'), proof.subject_tag(KEY, PIN.issuer + '/', 'alice'))
        self.assertNotEqual(proof.subject_tag(KEY, PIN.issuer, 'alice'), proof.subject_tag(bytes(32), PIN.issuer, 'alice'))
        for issuer, subject in (('https://user@idp.example.test', 'alice'), (PIN.issuer, ''), (PIN.issuer, '\x00')):
            with self.subTest(issuer=issuer, subject=subject), self.assertRaises(RecoveryError):
                proof.subject_tag(KEY, issuer, subject)

    def test_home_origin_uses_the_native_default_port_spelling(self):
        with self.assertRaisesRegex(RecoveryError, 'oidc-home-origin'):
            proof.profile_fields(replace(PIN, origin=PIN.origin + ':443'), CHALLENGE)
        pin = replace(PIN, origin=PIN.origin + ':8443')
        self.assertEqual(proof.profile_fields(pin, CHALLENGE)['origin'], pin.origin)

    def test_denies_raw_claims_and_mismatched_projection_before_signing(self):
        cases = [{}, replace(IDENTITY, issuer=PIN.issuer + '/'), replace(IDENTITY, nonce='a' * 64),
                 replace(IDENTITY, audiences=('other',)), replace(IDENTITY, audiences=(PIN.client_id, 'other')),
                 replace(IDENTITY, authorized_party='other'), replace(IDENTITY, expires_at_ms=NOW),
                 replace(IDENTITY, issued_at_ms=NOW + 5001), replace(IDENTITY, policy_verified=True)]
        with patch.object(proof, 'openssl', side_effect=AssertionError('unverified input reached signing')):
            for value in cases:
                with self.assertRaises(RecoveryError):
                    proof.issue(PIN, CHALLENGE, value, KEY, self.key, NOW)

    def test_policy_and_expiration_bound(self):
        pin = replace(PIN, policy_assurance=True)
        challenge = replace(CHALLENGE, expires_at_ms=NOW + 5000)
        result = proof.issue(pin, challenge, replace(IDENTITY, policy_verified=True), KEY, self.key, NOW)
        row = proof.verify(result, pin, challenge, NOW + 4999)
        self.assertEqual((row['assurance'], row['expires_at_ms']), ('oidc-policy-verified', str(NOW + 5000)))
        with self.assertRaisesRegex(RecoveryError, 'oidc-proof-time'):
            proof.verify(result, pin, challenge, NOW + 5000)
        with self.assertRaisesRegex(RecoveryError, 'oidc-assurance'):
            proof.verify(result, PIN, challenge, NOW)
        with self.assertRaisesRegex(RecoveryError, 'oidc-proof-time'):
            proof.verify(result, pin, challenge, NOW - 5001)

    def test_wire_rejects_duplicate_noncanonical_malformed_and_substituted_proofs(self):
        raw = proof.issue(PIN, CHALLENGE, IDENTITY, KEY, self.key, NOW)
        row = decoded(raw)
        forged = [raw + b'\n', b' ' * 2049, raw.replace(b'{', b'{"signature":"ignored",', 1),
                  encoded(row | {'challenge_id': '44' * 32})[:-1], encoded(row | {'subject_tag': '44' * 32})[:-1],
                  encoded(row | {'signature': '0' * 128})[:-1],
                  encoded(row | {'signature': SIGNATURE[:64] + proof.L.to_bytes(32, 'little').hex()})[:-1]]
        for value in forged:
            with self.assertRaises(RecoveryError):
                proof.verify(value, PIN, CHALLENGE, NOW)
        with self.assertRaisesRegex(RecoveryError, 'oidc-pin'):
            proof.verify(raw, replace(PIN, public_key='00' * 32), CHALLENGE, NOW)

    def test_key_requires_owned_mode_private_and_no_link(self):
        self.key.chmod(0o640)
        with self.assertRaisesRegex(RecoveryError, 'oidc-key'):
            proof.issue(PIN, CHALLENGE, IDENTITY, KEY, self.key, NOW)
        self.key.chmod(0o600)
        alias = self.key.with_name('alias')
        alias.symlink_to(self.key)
        with self.assertRaisesRegex(RecoveryError, 'oidc-key'):
            proof.issue(PIN, CHALLENGE, IDENTITY, KEY, alias, NOW)


if __name__ == '__main__':
    unittest.main()

"""Check the server-held PKCE ceremony and explicit one-time transitions."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sys
from threading import Barrier
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import browser_oidc_transactions as oidc
from portable_recovery import RecoveryError
from test_browser_oidc_proof import NOW, PIN


CALLBACK = 'https://verifier.example.test/oidc/callback'
RETURN = PIN.origin + '/stead/oidc/complete'
HOME = oidc.HomeAdmission('a' * 64, 'b' * 64, NOW + 9000)


class OidcTransactionTests(unittest.TestCase):
    def setUp(self):
        self.now = NOW
        self.ledger = oidc.Transactions(PIN, CALLBACK, RETURN, capacity=2, clock=lambda: self.now)

    def start(self, home=HOME):
        return self.ledger.start(PIN.origin, home)

    def test_exact_pkce_and_fixed_redirects_with_independent_handles(self):
        values = [f'{index:064x}' for index in (1, 2, 3, 4)]
        with patch.object(oidc.secrets, 'token_hex', side_effect=values) as entropy:
            start = self.start()
        self.assertEqual(entropy.call_count, 4)
        self.assertEqual((start.cookie, start.state, start.nonce, start.redirect_uri), (*values[:3], CALLBACK))
        self.assertNotIn(values[3], repr(start))
        self.assertEqual(start.code_challenge, 'H7SX0Sb1mwRIF40E8KM8qP-UYIdNkAGIIdP1hyvZpzU')
        claim = self.ledger.claim(start.cookie, start.state, PIN.issuer)
        self.assertEqual(claim.pin, PIN)
        self.assertEqual(claim.code_verifier, values[3])
        self.assertEqual(claim.redirect_uri, CALLBACK)
        self.assertEqual(claim.challenge, oidc.Challenge(HOME.challenge_id, HOME.incarnation, HOME.expires_at_ms, start.nonce))
        self.assertNotIn(values[3], repr(claim))
        self.assertEqual(self.ledger.finish(claim), RETURN)
        self.assertEqual(oidc.PKCE_METHOD, 'S256')

    def test_malformed_cookie_wrong_state_issuer_and_origin_deny_uniformly(self):
        for origin, admission in ((PIN.origin + '/', HOME), ('https://unknown.example.test', HOME),
                                  (PIN.origin, replace(HOME, incarnation='invalid')),
                                  (PIN.origin, replace(HOME, expires_at_ms=NOW + 120001))):
            with self.assertRaisesRegex(RecoveryError, '^oidc-transaction-denied$'):
                self.ledger.start(origin, admission)
        start = self.start()
        for cookie, state, issuer in ((start.cookie, 'ff', PIN.issuer), ('f' * 64, start.state, PIN.issuer),
                                     (start.cookie, start.state, PIN.issuer + '/'),
                                     (start.state, start.cookie, PIN.issuer)):
            with self.assertRaisesRegex(RecoveryError, '^oidc-transaction-denied$'):
                self.ledger.claim(cookie, state, issuer)
        self.assertEqual(self.ledger.claim(start.cookie, start.state, PIN.issuer).challenge.nonce, start.nonce)

    def test_competing_callbacks_claim_once_and_only_original_may_finish(self):
        start = self.start()
        barrier = Barrier(2)

        def claim():
            barrier.wait(timeout=2)
            try:
                return self.ledger.claim(start.cookie, start.state, PIN.issuer)
            except RecoveryError:
                return None

        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(claim) for _ in range(2)]
            outcomes = [future.result(timeout=3) for future in futures]
        self.assertEqual(outcomes.count(None), 1)
        exact = next(result for result in outcomes if result is not None)
        with self.assertRaisesRegex(RecoveryError, '^oidc-transaction-denied$'):
            self.ledger.finish(replace(exact))
        self.assertEqual(self.ledger.finish(exact), RETURN)
        for operation in (lambda: self.ledger.finish(exact), self.start,
                          lambda: self.ledger.claim(start.cookie, start.state, PIN.issuer)):
            with self.assertRaisesRegex(RecoveryError, '^oidc-transaction-denied$'):
                operation()

    def test_capacity_claimed_and_finished_expire_without_replay(self):
        start = self.start()
        second = replace(HOME, challenge_id='c' * 64, expires_at_ms=NOW + 20_000)
        new = replace(HOME, challenge_id='d' * 64, expires_at_ms=NOW + 30_000)
        self.start(second)
        with self.assertRaises(RecoveryError):
            self.start(new)
        claim = self.ledger.claim(start.cookie, start.state, PIN.issuer)
        self.ledger.finish(claim)
        with self.assertRaises(RecoveryError):
            self.start(new)
        self.now = HOME.expires_at_ms
        further = self.start(new)
        self.assertNotEqual(further.state, start.state)
        with self.assertRaises(RecoveryError):
            self.ledger.claim(start.cookie, start.state, PIN.issuer)
        self.now -= 1
        with self.assertRaises(RecoveryError):
            self.ledger.claim(further.cookie, further.state, PIN.issuer)

    def test_expired_callback_and_forged_redirect_configuration_are_refused(self):
        start = self.start()
        self.now = HOME.expires_at_ms
        with self.assertRaises(RecoveryError):
            self.ledger.claim(start.cookie, start.state, PIN.issuer)
        for callback, target in ((CALLBACK + '?return=https://other.example', RETURN),
                                 (CALLBACK, 'https://other.example/stead/oidc/complete'),
                                 (PIN.origin + '/oidc/callback', RETURN),
                                 (CALLBACK.replace('https://', 'http://'), RETURN),
                                 (CALLBACK, PIN.origin + '/stead/oidc/../complete')):
            with self.assertRaises(RecoveryError):
                oidc.Transactions(PIN, callback, target)


if __name__ == '__main__':
    unittest.main()

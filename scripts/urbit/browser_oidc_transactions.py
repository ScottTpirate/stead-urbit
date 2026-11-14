"""Bounded in-process OAuth ceremony for the trusted browser OIDC verifier.

The transport must verify the Home admission, exact HTTPS route and presented
Origin before calling start, and only send the cookie as host-only Secure,
HttpOnly, SameSite=Lax. Keep one coordinator in the owning verifier process.
The callback adapter owns provider code exchange and calls finish once on
success or failure. Codes, tokens and ID-token claims never enter this store.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import re
import secrets
from threading import Lock
import time
from urllib.parse import urlsplit

from browser_oidc_proof import Challenge, VerifierPin, WALL_MS, profile_fields, tick
from portable_recovery import TOKEN, RecoveryError, match, origin, require


MAX_TRANSACTIONS = 64
PKCE_METHOD = 'S256'
PATH = re.compile(r'/[A-Za-z0-9_/-]{1,127}')


@dataclass(frozen=True)
class HomeAdmission:
    """A trusted, current Home challenge projected by the handoff adapter."""

    challenge_id: str
    incarnation: str
    expires_at_ms: int


@dataclass(frozen=True, repr=False)
class Start:
    cookie: str
    state: str
    nonce: str
    code_challenge: str
    redirect_uri: str


@dataclass(frozen=True, repr=False)
class Claim:
    challenge: Challenge
    pin: VerifierPin
    redirect_uri: str
    code_verifier: str


@dataclass(frozen=True, repr=False)
class Pending:
    cookie_digest: str
    state_digest: str
    claim: Claim


@dataclass(frozen=True, repr=False)
class Claimed:
    claim: Claim


@dataclass(frozen=True)
class Finished:
    expires_at_ms: int


def redirect(value):
    require(isinstance(value, str) and len(value) <= 384, 'oidc-transaction-config')
    try:
        parts = urlsplit(value)
    except ValueError:
        raise RecoveryError('oidc-transaction-config') from None
    authority = 'https://' + parts.netloc
    origin(authority)
    require(value == authority + parts.path and match(PATH, parts.path) and '//' not in parts.path,
            'oidc-transaction-config')
    return authority


def digest(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()


class Transactions:
    def __init__(self, pin: VerifierPin, redirect_uri: str, return_url: str, *, capacity=MAX_TRANSACTIONS, clock=None):
        profile_fields(pin, Challenge('0' * 64, '1' * 64, 1, '2' * 64))
        callback_origin = redirect(redirect_uri)
        require(redirect(return_url) == pin.origin and callback_origin != pin.origin
                and type(capacity) is int and 1 <= capacity <= MAX_TRANSACTIONS, 'oidc-transaction-config')
        self._pin, self._redirect_uri, self._return_url = pin, redirect_uri, return_url
        self._capacity = capacity
        self._clock = clock if clock is not None else lambda: time.time_ns() // 1_000_000
        self._lock = Lock()
        self._rows: dict[str, Pending | Claimed | Finished] = {}
        self._watermark = 0

    def _prune(self):
        now = self._clock()
        require(tick(now) and now >= self._watermark, 'oidc-transaction-denied')
        self._watermark = now
        for key, row in list(self._rows.items()):
            expiry = row.expires_at_ms if isinstance(row, Finished) else row.claim.challenge.expires_at_ms
            if expiry <= now:
                del self._rows[key]
        return now

    def start(self, presented_origin: str, admission: HomeAdmission) -> Start:
        require(presented_origin == self._pin.origin and type(admission) is HomeAdmission
                and match(TOKEN, admission.challenge_id) and match(TOKEN, admission.incarnation)
                and tick(admission.expires_at_ms), 'oidc-transaction-denied')
        with self._lock:
            now = self._prune()
            key = admission.challenge_id
            require(now < admission.expires_at_ms <= now + WALL_MS and key not in self._rows
                    and len(self._rows) < self._capacity, 'oidc-transaction-denied')
            cookie, state, nonce, verifier = (secrets.token_hex(32) for _ in range(4))
            challenge = Challenge(key, admission.incarnation, admission.expires_at_ms, nonce)
            claim = Claim(challenge, self._pin, self._redirect_uri, verifier)
            self._rows[key] = Pending(digest(cookie), digest(state), claim)
            challenge_bytes = hashlib.sha256(verifier.encode('ascii')).digest()
            code_challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b'=').decode('ascii')
            return Start(cookie, state, nonce, code_challenge, self._redirect_uri)

    def claim(self, cookie: str, state: str, issuer: str) -> Claim:
        require(match(TOKEN, cookie) and match(TOKEN, state) and issuer == self._pin.issuer, 'oidc-transaction-denied')
        cookie_digest, state_digest = digest(cookie), digest(state)
        with self._lock:
            self._prune()
            for key, row in self._rows.items():
                if not isinstance(row, Pending):
                    continue
                cookie_matches = hmac.compare_digest(row.cookie_digest, cookie_digest)
                state_matches = hmac.compare_digest(row.state_digest, state_digest)
                if cookie_matches and state_matches:
                    self._rows[key] = Claimed(row.claim)
                    return row.claim
        raise RecoveryError('oidc-transaction-denied')

    def finish(self, claim: Claim) -> str:
        require(type(claim) is Claim, 'oidc-transaction-denied')
        with self._lock:
            self._prune()
            key = claim.challenge.challenge_id
            row = self._rows.get(key)
            require(isinstance(row, Claimed) and row.claim is claim, 'oidc-transaction-denied')
            self._rows[key] = Finished(claim.challenge.expires_at_ms)
            return self._return_url

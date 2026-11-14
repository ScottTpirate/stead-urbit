"""Issue or verify a Stead proof after an OIDC adapter verifies the provider identity."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from urllib.parse import urlsplit

from execution_policy import directory_fd
from git_pack_worker_signature import ENV, MAX_KEY, OPENSSL, SPKI_ED25519, key_binding
from portable_code import private_directory
from portable_recovery import TOKEN, RecoveryError, decoded, encoded, match, number, origin, require, shape, text


PROTOCOL = 'stead.oidc-proof/1'
SUBJECT_DOMAIN = b'stead.oidc-subject/1\0'
DOMAIN = PROTOCOL.encode('ascii') + b'\0'
MAX_PROOF = 2048
MAX_TIME = 2**64 - 1
PROOF_MS = 30_000
SKEW_MS = 5000
WALL_MS = 120_000
TAG_KEY_BYTES = 32
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
SHIP = re.compile(r'~(?:[a-z]{3}|[a-z]{6}(?:-{1,2}[a-z]{6})*)')
SIGNATURE = re.compile(r'[0-9a-f]{128}')
PROOF_FIELDS = {'protocol', 'home', 'origin', 'organization_id', 'verifier_id', 'verifier_revision', 'issuer_id',
                'challenge_id', 'incarnation', 'subject_tag', 'assurance', 'issued_at_ms', 'expires_at_ms'}
P = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
SMALL_Y = {0, 1, P - 1,
           int.from_bytes(bytes.fromhex('26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05'), 'little'),
           int.from_bytes(bytes.fromhex('c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a'), 'little')}


@dataclass(frozen=True)
class VerifierPin:
    home: str
    origin: str
    organization_id: str
    verifier_id: str
    verifier_revision: str
    issuer_id: str
    issuer: str
    client_id: str
    public_key: str
    policy_assurance: bool = False


@dataclass(frozen=True)
class Challenge:
    """Trusted Home challenge and verifier transaction data, never browser claims."""

    challenge_id: str
    incarnation: str
    expires_at_ms: int
    nonce: str


@dataclass(frozen=True, repr=False)
class VerifiedIdentity:
    """Materialize only from the maintained OIDC adapter's verified ID token.

    The adapter owns token exchange, TLS, state/PKCE, key and algorithm checks
    and any verified authentication-age policy. This type is an interface
    within that trusted process, not a credential that can cross HTTP.
    """

    issuer: str
    subject: str
    audiences: tuple[str, ...]
    authorized_party: str | None
    nonce: str
    issued_at_ms: int
    expires_at_ms: int
    policy_verified: bool = False


def point(raw):
    value = int.from_bytes(raw, 'little') & (2**255 - 1)
    return len(raw) == 32 and value < P and value not in SMALL_Y


def profile_fields(pin, challenge):
    require(type(pin) is VerifierPin and type(challenge) is Challenge, 'oidc-profile')
    require(match(SHIP, pin.home) and len(pin.home) <= 64, 'oidc-home')
    origin(pin.origin)
    for value in (pin.organization_id, pin.verifier_id, pin.issuer_id):
        require(match(UUID, value), 'oidc-profile')
    number(pin.verifier_revision)
    require(type(pin.policy_assurance) is bool and match(TOKEN, pin.public_key) and point(bytes.fromhex(pin.public_key)), 'oidc-pin')
    validate_issuer(pin.issuer)
    require(bool(text(pin.client_id, 256)), 'oidc-profile')
    require(match(TOKEN, challenge.challenge_id) and match(TOKEN, challenge.incarnation)
            and match(TOKEN, challenge.nonce) and tick(challenge.expires_at_ms), 'oidc-challenge')
    return {'protocol': PROTOCOL, 'home': pin.home, 'origin': pin.origin, 'organization_id': pin.organization_id,
            'verifier_id': pin.verifier_id, 'verifier_revision': pin.verifier_revision, 'issuer_id': pin.issuer_id,
            'challenge_id': challenge.challenge_id, 'incarnation': challenge.incarnation}


def validate_issuer(issuer):
    require(bool(text(issuer, 512)) and issuer.isascii() and all(32 < ord(char) < 127 for char in issuer)
            and '\\' not in issuer and '?' not in issuer and '#' not in issuer, 'oidc-issuer')
    try:
        parts = urlsplit(issuer)
        require(parts.scheme == 'https' and issuer.startswith('https://') and bool(parts.hostname) and '@' not in parts.netloc
                and '%' not in parts.netloc and (parts.port is None or 0 < parts.port <= 65535), 'oidc-issuer')
    except ValueError:
        raise RecoveryError('oidc-issuer') from None


def subject_tag(key: bytes, issuer: str, subject: str) -> str:
    require(isinstance(key, bytes) and len(key) == TAG_KEY_BYTES, 'oidc-tag-key')
    validate_issuer(issuer)
    require(bool(text(subject, 1024)), 'oidc-subject')
    values = (issuer.encode('utf-8'), subject.encode('utf-8'))
    return hmac.new(key, SUBJECT_DOMAIN + b''.join(len(value).to_bytes(4, 'big') + value for value in values),
                    hashlib.sha256).hexdigest()


def tick(value):
    return type(value) is int and 0 < value <= MAX_TIME


def signing_bytes(row):
    shape(row, PROOF_FIELDS)
    require(all(isinstance(value, str) and value.isascii() and '\0' not in value for value in row.values())
            and row['protocol'] == PROTOCOL, 'oidc-proof-fields')
    return DOMAIN + encoded(row)[:-1]


def proof_fields(row, pin, challenge, now):
    expected = profile_fields(pin, challenge)
    require(all(row[key] == value for key, value in expected.items()) and match(TOKEN, row['subject_tag']), 'oidc-proof-pin')
    require(row['assurance'] == 'oidc' or row['assurance'] == 'oidc-policy-verified' and pin.policy_assurance,
            'oidc-assurance')
    number(row['issued_at_ms'])
    number(row['expires_at_ms'])
    started, expires = int(row['issued_at_ms']), int(row['expires_at_ms'])
    require(tick(now) and now < expires <= challenge.expires_at_ms <= now + WALL_MS + SKEW_MS
            and started <= now + SKEW_MS and 0 < expires - started <= PROOF_MS, 'oidc-proof-time')


@contextmanager
def signing_key(path):
    path = Path(path)
    require(path.is_absolute(), 'oidc-key')
    with directory_fd(path.parent) as parent:
        owner = private_directory(parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as private:
            info = os.fstat(private.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                    and 0 < info.st_size <= MAX_KEY and stat.S_IMODE(info.st_mode) == 0o600, 'oidc-key')
            key_binding(path, parent, owner, private.fileno(), info)
            yield private.fileno()
            key_binding(path, parent, owner, private.fileno(), info)


def openssl(args, directory, *, pass_fds=()):
    try:
        return subprocess.run([OPENSSL, *args], cwd=directory, env=ENV, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, pass_fds=pass_fds, timeout=3)
    except (OSError, subprocess.SubprocessError):
        raise RecoveryError('oidc-crypto-unavailable') from None


def issue(pin: VerifierPin, challenge: Challenge, identity: VerifiedIdentity, tag_key: bytes,
          key: Path, now: int) -> bytes:
    """Sign a checked projection of an OIDC library result; do not pass claims JSON."""
    row = profile_fields(pin, challenge)
    require(type(identity) is VerifiedIdentity and identity.issuer == pin.issuer and type(identity.audiences) is tuple
            and 0 < len(identity.audiences) <= 8 and all(isinstance(aud, str) and 0 < len(aud) <= 256 for aud in identity.audiences)
            and len(set(identity.audiences)) == len(identity.audiences) and pin.client_id in identity.audiences
            and (identity.authorized_party == pin.client_id or (identity.authorized_party is None and len(identity.audiences) == 1))
            and identity.nonce == challenge.nonce and type(identity.policy_verified) is bool, 'oidc-identity-projection')
    require(tick(now) and tick(identity.expires_at_ms) and tick(identity.issued_at_ms)
            and identity.issued_at_ms <= now + SKEW_MS and now < identity.expires_at_ms
            and identity.issued_at_ms < identity.expires_at_ms, 'oidc-identity-time')
    row.update(subject_tag=subject_tag(tag_key, identity.issuer, identity.subject),
               assurance='oidc-policy-verified' if identity.policy_verified else 'oidc', issued_at_ms=str(now),
               expires_at_ms=str(min(challenge.expires_at_ms, identity.expires_at_ms, now + PROOF_MS)))
    proof_fields(row, pin, challenge, now)
    try:
        with signing_key(key) as fd, tempfile.TemporaryDirectory(prefix='stead-browser-oidc-') as work:
            directory = Path(work)
            (directory / 'message').write_bytes(signing_bytes(row))
            held = f'/proc/self/fd/{fd}'
            public = openssl(['pkey', '-inform', 'PEM', '-in', held, '-passin', 'pass:', '-pubout', '-outform', 'DER'],
                             directory, pass_fds=(fd,))
            require(public.returncode == 0 and public.stdout == SPKI_ED25519 + bytes.fromhex(pin.public_key), 'oidc-key-pin')
            signed = openssl(['pkeyutl', '-sign', '-rawin', '-keyform', 'PEM', '-inkey', held, '-passin', 'pass:',
                              '-in', 'message'], directory, pass_fds=(fd,))
            require(signed.returncode == 0 and len(signed.stdout) == 64, 'oidc-signature')
    except OSError:
        raise RecoveryError('oidc-key') from None
    raw = encoded(row | {'signature': signed.stdout.hex()})[:-1]
    require(len(raw) <= MAX_PROOF, 'oidc-proof-bound')
    return raw


def verify(raw: bytes, pin: VerifierPin, challenge: Challenge, now: int) -> dict[str, str]:
    """Check bounded proof data, pin, ceremony and signature without changing state."""
    proof = decoded(raw, MAX_PROOF)
    shape(proof, PROOF_FIELDS | {'signature'})
    require(encoded(proof)[:-1] == raw and match(SIGNATURE, proof['signature']), 'oidc-proof-wire')
    signature = bytes.fromhex(proof.pop('signature'))
    data = signing_bytes(proof)
    proof_fields(proof, pin, challenge, now)
    require(point(signature[:32]) and int.from_bytes(signature[32:], 'little') < L, 'oidc-signature')
    with tempfile.TemporaryDirectory(prefix='stead-browser-oidc-') as work:
        directory = Path(work)
        (directory / 'message').write_bytes(data)
        (directory / 'signature').write_bytes(signature)
        (directory / 'public.der').write_bytes(SPKI_ED25519 + bytes.fromhex(pin.public_key))
        result = openssl(['pkeyutl', '-verify', '-rawin', '-pubin', '-keyform', 'DER', '-inkey', 'public.der',
                          '-sigfile', 'signature', '-in', 'message'], directory)
        require(result.returncode == 0, 'oidc-signature')
    return proof

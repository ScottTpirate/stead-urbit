"""Authenticate the one reviewed manual GitHub-hosted workflow, before execution.

Only the root controller uses this module. Tokens are never persisted, printed,
or mounted into the native namespace. OpenSSL verifies RS256; no JWT algorithm
or key URL is selected by the token itself.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

ISSUER = 'https://token.actions.githubusercontent.com'
JWKS = ISSUER + '/.well-known/jwks'
REPOSITORY = 'ScottTpirate/stead-urbit'
REPOSITORY_ID, OWNER_ID = '1367847927', '44659733'
WORKFLOW = REPOSITORY + '/.github/workflows/native-hosted.yml@refs/heads/main'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate identity field')
        result[key] = value
    return result


def decode(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]+', value)
            and len(value) <= 32768, 'Invalid base64url')
    raw = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
    require(base64.urlsafe_b64encode(raw).decode().rstrip('=') == value, 'Noncanonical base64url')
    return raw


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError('Identity redirect refused')


def fetch(url, headers=None):
    # No proxy or CA environment is allowed to redirect the request credential
    # or substitute trust for the issuer's key set.
    context = ssl.create_default_context(cafile='/etc/ssl/certs/ca-certificates.crt')
    with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect,
            urllib.request.HTTPSHandler(context=context)).open(
            urllib.request.Request(url, headers=headers or {}), timeout=15) as response:
        require(response.status == 200, 'Identity HTTP status')
        raw = response.read(131073)
    require(len(raw) <= 131072, 'Identity response too large')
    return json.loads(raw, object_pairs_hook=unique)


def der(tag, raw):
    length = len(raw)
    size = bytes([length]) if length < 128 else (lambda b: bytes([128 + len(b)]) + b)(length.to_bytes((length.bit_length() + 7) // 8, 'big'))
    return bytes([tag]) + size + raw


def public_key(key):
    require(key.get('kty') == 'RSA' and key.get('alg') == 'RS256'
            and key.get('use') == 'sig', 'Unsupported identity key')
    modulus, exponent = decode(key['n']), decode(key['e'])
    require(256 <= len(modulus) <= 512 and modulus[0] != 0
            and int.from_bytes(exponent, 'big') == 65537, 'Unexpected RSA parameters')
    integer = lambda raw: der(2, (b'\0' if raw[0] & 128 else b'') + raw)
    rsa = der(48, integer(modulus) + integer(exponent))
    # SubjectPublicKeyInfo: rsaEncryption OID + NULL, then the RSA bit string.
    spki = der(48, bytes.fromhex('300d06092a864886f70d0101010500') + der(3, b'\0' + rsa))
    encoded = base64.b64encode(spki)
    return b'-----BEGIN PUBLIC KEY-----\n' + b'\n'.join(encoded[i:i + 64] for i in range(0, len(encoded), 64)) + b'\n-----END PUBLIC KEY-----\n'


def claims_valid(claims, *, audience, workflow_sha, run_id, attempt, now):
    expected = {'iss': ISSUER, 'aud': audience, 'repository': REPOSITORY,
        'repository_id': REPOSITORY_ID, 'repository_owner_id': OWNER_ID,
        'repository_visibility': 'public', 'runner_environment': 'github-hosted',
        'event_name': 'workflow_dispatch', 'ref': 'refs/heads/main',
        'workflow_ref': WORKFLOW, 'workflow_sha': workflow_sha, 'sha': workflow_sha,
        'run_id': run_id, 'run_attempt': attempt}
    require(all(claims.get(key) == value for key, value in expected.items()), 'GitHub identity claims differ')
    subjects = {f'repo:{REPOSITORY}:ref:refs/heads/main',
        f'repo:ScottTpirate@{OWNER_ID}/stead-urbit@{REPOSITORY_ID}:ref:refs/heads/main'}
    require(claims.get('sub') in subjects, 'Unexpected workflow subject')
    require(all(type(claims.get(key)) is int for key in ('iat', 'nbf', 'exp')), 'Identity time types')
    require(now - 120 <= claims['iat'] <= now + 5 and claims['nbf'] <= now + 5
            and now < claims['exp'] <= claims['iat'] + 600
            and claims['nbf'] <= claims['exp'], 'Stale or future identity token')
    require(isinstance(claims.get('jti'), str) and 0 < len(claims['jti']) <= 256, 'Missing token identity')
    return {key: claims[key] for key in (*expected, 'sub', 'iat', 'nbf', 'exp', 'jti') if key != 'aud'}


def verify(token, keys, *, audience, workflow_sha, run_id, attempt, now=None):
    require(isinstance(token, str) and len(token) <= 32768 and token.count('.') == 2, 'Identity token bound')
    head, body, signature = token.split('.')
    header = json.loads(decode(head), object_pairs_hook=unique)
    require(set(header) <= {'typ', 'alg', 'kid', 'x5t'} and header.get('alg') == 'RS256'
            and header.get('typ') == 'JWT' and isinstance(header.get('kid'), str), 'Identity algorithm/header')
    require(isinstance(keys, dict) and isinstance(keys.get('keys'), list) and len(keys['keys']) <= 16, 'Identity key inventory')
    matches = [key for key in keys['keys'] if key.get('kid') == header['kid']]
    require(len(matches) == 1, 'Identity key is absent or ambiguous')
    with tempfile.TemporaryDirectory(prefix='stead-oidc-') as folder:
        root = Path(folder)
        (root / 'public.pem').write_bytes(public_key(matches[0]))
        (root / 'signature').write_bytes(decode(signature))
        observed = subprocess.run(['/usr/bin/openssl', 'dgst', '-sha256', '-verify', str(root / 'public.pem'),
            '-signature', str(root / 'signature')], input=(head + '.' + body).encode(),
            capture_output=True, timeout=5, env={'PATH': '/usr/bin:/bin'})
        require(observed.returncode == 0, 'Identity signature rejected')
    claims = json.loads(decode(body), object_pairs_hook=unique)
    return claims_valid(claims, audience=audience, workflow_sha=workflow_sha,
        run_id=run_id, attempt=attempt, now=time.time() if now is None else now)


def authenticate(environment, *, workflow_sha, run_id, attempt):
    require(re.fullmatch(r'[0-9a-f]{40}', workflow_sha) and re.fullmatch(r'[1-9][0-9]{0,19}', run_id)
            and re.fullmatch(r'[1-9][0-9]{0,3}', attempt), 'Malformed workflow identity input')
    url = environment.pop('ACTIONS_ID_TOKEN_REQUEST_URL', '')
    credential = environment.pop('ACTIONS_ID_TOKEN_REQUEST_TOKEN', '')
    parts = urllib.parse.urlsplit(url)
    # GitHub selects this endpoint. Refuse arbitrary hosts, HTTP and URL auth;
    # The trusted GitHub job has OIDC permission; the candidate namespace never
    # receives its request credential or token.
    require(parts.scheme == 'https' and parts.hostname is not None
            and (parts.hostname.endswith('.actions.githubusercontent.com') or parts.hostname.endswith('.actions.github.com'))
            and not parts.username and not parts.password and parts.port in (None, 443)
            and not parts.fragment and 0 < len(credential) <= 32768, 'Missing hosted identity endpoint')
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    require(not any(key == 'audience' for key, _ in query), 'Preselected identity audience')
    audience = 'stead-native-ci:' + secrets.token_hex(32)
    url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode([*query, ('audience', audience)])))
    response = fetch(url, {'Authorization': 'Bearer ' + credential})
    return verify(response.get('value'), fetch(JWKS), audience=audience,
        workflow_sha=workflow_sha, run_id=run_id, attempt=attempt)

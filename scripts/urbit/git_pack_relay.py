"""Private TLS client for Home's authoritative Git relay."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import http.client
import io
import math
import re
import socket
import ssl
import time

import git_pack_http as git_http
import git_pack_proof as proof
import git_pack_receive_adapter as receive
import git_pack_relay_wire as wire
from git_pack_store import SHIP
from git_pack_worker_socket import SignedProof
from portable_recovery import MAX_RESPONSE, TOKEN, UUID, RecoveryError, decoded, encoded, match, new_id, origin, require, sha


MIME = 'application/x-stead-git-relay'
VERIFIED = b'{"status":"verified"}'
REASON = re.compile(r'[a-z][a-z0-9-]{0,63}')
LENGTH = re.compile(r'[1-9][0-9]{0,5}')
GUEST_COOKIE = re.compile(r'0v(0|[1-9a-v][0-9a-v]{0,4}(?:\.[0-9a-v]{5}){0,5}); Path=/; Max-Age=604800')
CALL_SECONDS = 5


def remaining(deadline):
    duration = deadline - time.monotonic()
    require(duration > 0, 'pack-relay-deadline')
    return duration


class _DeadlineReader(io.RawIOBase):
    def __init__(self, tls, deadline, limit):
        self.tls = tls
        self.deadline = deadline
        self.budget = limit

    def readable(self):
        return True

    def readinto(self, output):
        require(self.budget > 0, 'pack-relay-response-bound')
        self.tls.settimeout(remaining(self.deadline))
        count = self.tls.recv_into(output, min(len(output), self.budget))
        self.budget -= count
        return count


class _ResponseSocket:
    def __init__(self, tls, deadline, limit):
        self.tls = tls
        self.deadline = deadline
        self.limit = limit

    def makefile(self, mode):
        require(mode == 'rb', 'pack-relay-response-unavailable')
        # Include chunk framing and HTTP headers in the transport budget.
        return io.BufferedReader(_DeadlineReader(self.tls, self.deadline, self.limit * 8 + 65_536))


def _response_body(response, limit, home_ship):
    headers = response.headers
    cookies = headers.get_all('Set-Cookie', [])
    prefix = f'urbauth-{home_ship}='
    if cookies:
        require(len(cookies) == 1 and cookies[0].startswith(prefix), 'pack-relay-response-headers')
        guest = GUEST_COOKIE.fullmatch(cookies[0][len(prefix):])
        require(guest is not None and int(guest[1].replace('.', ''), 32).bit_length() <= 128,
                'pack-relay-response-headers')
    require(headers.get_all('Content-Type') == ['application/json']
            and not any(headers.get_all(key) for key in ('Content-Encoding', 'Set-Cookie2', 'Location')),
            'pack-relay-response-headers')
    declared = headers.get_all('Content-Length')
    transfer = headers.get_all('Transfer-Encoding')
    if declared is None:
        require(transfer == ['chunked'], 'pack-relay-response-framing')
    else:
        require(transfer is None and len(declared) == 1 and match(LENGTH, declared[0])
                and int(declared[0]) <= limit, 'pack-relay-response-framing')
    raw = response.read(limit + 1)
    require(0 < len(raw) <= limit and (declared is None or len(raw) == int(declared[0])),
            'pack-relay-response-bound')
    return raw


class Relay:
    """One reviewed Home origin reachable only over a fixed loopback TLS target."""

    def __init__(self, home_origin, home_ship, capability, *, certificate_sha256, ca_file=None,
                 ca_data=None, connect_ip='127.0.0.1', connect_port=None, clock=None):
        self.origin = origin(home_origin)
        require(match(SHIP, home_ship) and match(TOKEN, capability) and match(TOKEN, certificate_sha256)
                and connect_ip in ('127.0.0.1', '::1')
                and (connect_port is None or type(connect_port) is int and 0 < connect_port <= 65_535),
                'pack-relay-config')
        self.home_ship = home_ship
        self._capability = capability
        self.certificate_sha256 = certificate_sha256
        self.connect_ip = connect_ip
        self.connect_port = connect_port if connect_port is not None else self.origin.port or 443
        self.clock = clock if clock is not None else lambda: time.time_ns() // 1_000_000
        try:
            self.context = ssl.create_default_context(cafile=ca_file, cadata=ca_data)
        except (OSError, ValueError):
            raise RecoveryError('pack-relay-ca-unavailable') from None

    def _exchange(self, authorization, project, body, deadline, *, discovery=False):
        require(match(UUID, project) and isinstance(body, bytes) and 0 < len(body) <= wire.MAX_FRAME,
                'pack-relay-request')
        authorization = git_http.basic(authorization)
        require(deadline is None or type(deadline) in (int, float) and math.isfinite(deadline), 'pack-relay-deadline')
        until = time.monotonic() + CALL_SECONDS
        if deadline is not None:
            until = min(until, deadline)
        limit = git_http.MAX_DECISION if discovery else proof.MAX_MESSAGE
        headers = {
            'Authorization': authorization, 'X-Stead-Relay': self._capability,
            'Host': self.origin.netloc, 'Content-Type': MIME, 'Content-Length': str(len(body)),
            'Accept': 'application/json', 'Accept-Encoding': 'identity', 'Connection': 'close',
        }
        with self._response('POST', f'/stead/_pack-relay/{project}', headers, body, until, limit) as response:
            if response.status == 403 or (response.status == 401 and discovery):
                remaining(until)
                raise receive.Rejected('pack-relay-denied')
            require(response.status == 200, 'pack-relay-response-unavailable')
            raw = _response_body(response, limit, self.home_ship)
        remaining(until)
        result = decoded(raw, limit)
        if isinstance(result, dict) and result.get('status') == 'refused':
            require(set(result) == {'status', 'reason'} and match(REASON, result['reason'])
                    and encoded(result)[:-1] == raw, 'pack-relay-refusal-shape')
            raise receive.Rejected('pack-relay-refused')
        return raw

    @contextmanager
    def _response(self, method, path, headers, body, deadline, limit):
        try:
            with socket.create_connection((self.connect_ip, self.connect_port), timeout=remaining(deadline)) as connection:
                connection.settimeout(remaining(deadline))
                with self.context.wrap_socket(connection, server_hostname=self.origin.hostname) as tls:
                    require(sha(tls.getpeercert(binary_form=True)) == self.certificate_sha256, 'pack-relay-certificate')
                    client = http.client.HTTPConnection(self.origin.hostname, self.connect_port)
                    client.sock = tls
                    tls.settimeout(remaining(deadline))
                    client.request(method, path, body=body, headers=headers)
                    with http.client.HTTPResponse(_ResponseSocket(tls, deadline, limit), method=method) as response:
                        response.begin()
                        yield response
        except (OSError, http.client.HTTPException):
            raise RecoveryError('pack-relay-unavailable') from None

    def read_decision(self, authorization, project):
        authorization = git_http.basic(authorization)
        require(match(UUID, project), 'project-scope')
        until = time.monotonic() + CALL_SECONDS
        headers = {'Authorization': authorization, 'Host': self.origin.netloc, 'Accept': 'application/json',
                   'Accept-Encoding': 'identity', 'Cache-Control': 'no-store', 'Connection': 'close'}
        with self._response('GET', f'/stead/git/{project}.git/stead-snapshot', headers, None, until,
                            git_http.MAX_DECISION) as response:
            if response.status == 401:
                raise git_http.Denied('git-credential-denied')
            require(response.status == 200, 'home-decision-unavailable')
            raw = _response_body(response, git_http.MAX_DECISION, self.home_ship)
        remaining(until)
        scope, value, refs = git_http.decision(raw, project)
        require(scope['home'] == self.home_ship and encoded(value)[:-1] == raw, 'home-decision-response')
        return scope, value, refs

    def browser_pack_view(self, project, session, csrf, deadline):
        require(match(UUID, project) and match(TOKEN, session) and match(TOKEN, csrf), 'browse-credentials')
        until = min(deadline, time.monotonic() + CALL_SECONDS)
        body = encoded({'protocol': 'stead.code/1', 'action': 'pack-view', 'project_id': project})
        headers = {
            'Host': self.origin.netloc, 'Origin': self.origin.geturl(),
            'Cookie': f'__Host-stead-session={session}', 'X-Stead-CSRF': csrf,
            'Content-Type': 'application/json', 'Content-Length': str(len(body)),
            'Accept': 'application/json', 'Accept-Encoding': 'identity', 'Connection': 'close',
        }
        with self._response('POST', '/stead/api/code', headers, body, until, MAX_RESPONSE) as response:
            if response.status == 401:
                raise git_http.Denied('session_required')
            if response.status == 404:
                raise git_http.Denied('denied_or_not_found')
            require(response.status in (200, 403, 409), 'browse-home-unavailable')
            value = decoded(_response_body(response, MAX_RESPONSE, self.home_ship))
            status = response.status
        if status == 403:
            reason = 'invalid_csrf' if isinstance(value, dict) and value.get('error') == 'invalid_csrf' else 'denied_or_not_found'
            raise git_http.Denied(reason)
        if status == 409:
            raise git_http.Denied('stale_selection')
        remaining(until)
        return value

    def advertise(self, authorization, project, *, deadline=None):
        try:
            raw = self._exchange(authorization, project, wire.advertise(new_id()), deadline, discovery=True)
        except receive.Rejected:
            raise git_http.Denied('pack-relay-denied') from None
        scope, result, _ = git_http.decision(raw, project)
        require(scope['home'] == self.home_ship and encoded(result)[:-1] == raw, 'pack-relay-advertisement')
        return raw

    def push(self, signed_worker):
        """Create private custody for one push's admission and signed evidence."""
        return RelayPush(self, signed_worker)

    def receive(self, signed_worker, spool_root, project, bearer, body, content_length, *, deadline):
        push = self.push(signed_worker)
        return receive.receive_push(push, push, spool_root, project, bearer, body, content_length,
                                    deadline=deadline, clock=self.clock)


class RelayPush:
    def __init__(self, relay, signed_worker):
        self.relay = relay
        self.worker = signed_worker
        self._binding = None
        self._signed = None

    def admit(self, bearer, request, deadline):
        require(self._binding is None and match(TOKEN, bearer), 'pack-relay-push-binding')
        request_id = new_id()
        body = wire.admit(request_id, request)
        authorization = 'Basic ' + base64.b64encode(b'stead:' + bearer.encode('ascii')).decode('ascii')
        raw = self.relay._exchange(authorization, request.project, body, deadline)
        admitted = receive.Admission(raw, sha(raw))
        claim = receive.correlate(admitted, request, self.relay.clock())
        require(claim['request_id'] == request_id and claim['scope']['home'] == self.relay.home_ship,
                'pack-relay-admission-scope')
        self._binding = (bearer, admitted, request.project, authorization, claim)
        return admitted

    def __call__(self, admitted, wire_path, deadline):
        require(self._binding is not None and admitted == self._binding[1] and self._signed is None,
                'pack-relay-push-binding')
        signed = self.worker(admitted, wire_path, deadline)
        require(isinstance(signed, SignedProof), 'pack-relay-worker-response')
        self._signed = signed
        return signed.proof

    def _transition(self, step, bearer, admitted, evidence, deadline):
        require(self._binding is not None and self._binding[:2] == (bearer, admitted)
                and self._signed is not None and evidence == self._signed.proof, 'pack-relay-push-binding')
        _, _, project, authorization, claim = self._binding
        options = {} if step == 'receipt' else {'now_ms': self.relay.clock(),
            'worker_generation': self._signed.generation, 'worker_signature': self._signed.signature}
        body = wire.transition(step, admitted, evidence, **options)
        raw = self.relay._exchange(authorization, project, body, deadline)
        if step == 'verify':
            require(raw == VERIFIED, 'pack-relay-verification-response')
        else:
            candidate = receive.proof_snapshot(evidence, admitted, claim)
            receive.receipt(raw, admitted, claim, candidate, self.relay.clock())
        return raw

    def verify(self, bearer, admitted, evidence, deadline):
        self._transition('verify', bearer, admitted, evidence, deadline)
        return True

    def commit(self, bearer, admitted, evidence, deadline):
        return self._transition('commit', bearer, admitted, evidence, deadline)

    def recover(self, bearer, admitted, evidence, deadline):
        try:
            return self._transition('receipt', bearer, admitted, evidence, deadline)
        except receive.Rejected:
            return None

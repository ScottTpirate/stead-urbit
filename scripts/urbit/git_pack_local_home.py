"""Connect the Git push adapter to an isolated fake Home's private Khan thread."""
from __future__ import annotations

import base64
import math
import re
import secrets
import time
from typing import Callable

from core_conn import atom
import git_pack_http
import git_pack_proof as proof
from git_pack_push import MAX_CHANGES
from git_pack_receive_adapter import Admission, Change, PushRequest, RECEIPT_PROTOCOL, Rejected, within
from portable_code import ref_name
from portable_recovery import OID, TOKEN, UUID, RecoveryError, decoded, encoded, match, new_id, require, sha


VERIFIED = b'{"status":"verified"}'
REASON = re.compile(r'[a-z][a-z0-9-]{0,63}')
ADVERTISE_SECONDS = 5


def cord(text: str) -> str:
    return atom(text.encode('ascii'))


def oid(text: str) -> str:
    require(match(OID, text), 'local-pack-oid')
    # Git OIDs are numeric @ux values, unlike byte-preserving @t cords.
    return atom(bytes.fromhex(text)[::-1])


class LocalHome:
    """Use only an injected, caller-owned fake Khan exchange.

    The helper never resolves an address, reads credentials from disk, or
    chooses a pier. Its carrier must suppress diagnostic traces containing
    the request noun and return only the original stead-core-result bytes.
    """

    def __init__(self, exchange: Callable[[str, float], bytes], *, clock: Callable[[], int] | None = None):
        self.exchange = exchange
        self.clock = clock if clock is not None else lambda: time.time_ns() // 1_000_000

    def _exchange(self, bearer: str, project: str, request: str, task: str, deadline: float) -> bytes:
        require(match(TOKEN, bearer) and match(UUID, project) and match(UUID, request), 'local-pack-scope')
        within(deadline)
        nonce = cord(secrets.token_hex(32))
        noun = ('[32 %fyrd [%base %stead-code-pack-local %noun [%noun '
                f'[~zod [{nonce} {cord(project)} {cord(bearer)} {cord(request)} {task}]]]]]')
        try:
            raw = self.exchange(noun, deadline)
        except Exception:
            # This boundary drops transport exceptions (and any native trace)
            # before exposing a diagnostic to the adapter or its caller.
            pass
        else:
            within(deadline)
            require(isinstance(raw, bytes) and 0 < len(raw) <= proof.MAX_MESSAGE, 'local-pack-response')
            response = decoded(raw, proof.MAX_MESSAGE)
            if isinstance(response, dict) and response.get('status') == 'refused':
                require(set(response) == {'status', 'reason'} and match(REASON, response['reason'])
                        and encoded(response)[:-1] == raw, 'local-pack-response')
                raise Rejected('local-pack-refused')
            return raw
        raise RecoveryError('local-pack-exchange-unavailable')

    def advertise(self, authorization: str, project: str, *, deadline: float | None = None) -> bytes:
        require(deadline is None or type(deadline) in (int, float) and math.isfinite(deadline), 'push-deadline')
        limit = time.monotonic() + ADVERTISE_SECONDS
        deadline = limit if deadline is None else min(deadline, limit)
        canonical = git_pack_http.basic(authorization)
        bearer = base64.b64decode(canonical[6:])[6:].decode('ascii')
        try:
            raw = self._exchange(bearer, project, new_id(), '[%advertise ~]', deadline)
        except Rejected:
            raise git_pack_http.Denied('local-pack-refused') from None
        scope, result, _ = git_pack_http.decision(raw, project)
        require(scope['home'] == '~zod' and encoded(result)[:-1] == raw, 'local-pack-advertisement')
        return raw

    def admit(self, bearer: str, request: PushRequest, deadline: float) -> Admission:
        require(isinstance(request, PushRequest) and match(TOKEN, request.wire_sha256)
                and 0 < len(request.changes) <= MAX_CHANGES
                and all(isinstance(change, Change) for change in request.changes), 'local-pack-request')
        updates = (f'[{atom(ref_name(change.ref))} {oid(change.prior)} {oid(change.target)}]'
                   for change in request.changes)
        request_id = new_id()
        task = f'[%admit {cord(request.wire_sha256)} [{" ".join(updates)} ~]]'
        raw = self._exchange(bearer, request.project, request_id, task, deadline)
        admission = Admission(raw, sha(raw))
        view = proof.admission(admission.raw, admission.sha256, self.clock())
        require(view['request_id'] == request_id and view['scope']['home'] == '~zod'
                and view['scope']['project_id'] == request.project and view['wire_sha256'] == request.wire_sha256
                and tuple(Change(**row) for row in proof.ordered_changes(view)) == request.changes,
                'local-pack-admission')
        return admission

    def _transition(self, step: str, bearer: str, admitted: Admission, evidence: bytes, deadline: float) -> bytes:
        require(isinstance(admitted, Admission) and isinstance(admitted.raw, bytes)
                and 0 < len(admitted.raw) <= proof.MAX_MESSAGE
                and isinstance(evidence, bytes) and 0 < len(evidence) <= proof.MAX_MESSAGE
                and evidence.endswith(b'\n') and match(TOKEN, admitted.sha256)
                and sha(admitted.raw) == admitted.sha256, 'local-pack-input')
        if step == 'receipt':
            # A durable receipt may outlive the original worker lease. The
            # native receipt lookup pins the original admission and evidence.
            claim = decoded(admitted.raw, proof.MAX_MESSAGE)
            require(isinstance(claim, dict) and claim.get('protocol') == proof.ADMISSION
                    and encoded(claim) == admitted.raw, 'local-pack-admission')
        else:
            claim = proof.admission(admitted.raw, admitted.sha256, self.clock())
        scope = claim.get('scope')
        require(isinstance(scope, dict) and scope.get('home') == '~zod', 'local-pack-fake-required')
        request = claim.get('request_id')
        task = f'[%{step} {atom(admitted.raw)} {cord(admitted.sha256)} {atom(evidence)}]'
        return self._exchange(bearer, scope.get('project_id'), request, task, deadline)

    def verify(self, bearer: str, admitted: Admission, evidence: bytes, deadline: float) -> bool:
        raw = self._transition('verify', bearer, admitted, evidence, deadline)
        require(raw == VERIFIED, 'local-pack-verification')
        return True

    def commit(self, bearer: str, admitted: Admission, evidence: bytes, deadline: float) -> bytes:
        return self._receipt(self._transition('commit', bearer, admitted, evidence, deadline))

    def recover(self, bearer: str, admitted: Admission, evidence: bytes, deadline: float) -> bytes | None:
        try:
            raw = self._transition('receipt', bearer, admitted, evidence, deadline)
        except Rejected:
            return None
        return self._receipt(raw)

    @staticmethod
    def _receipt(raw: bytes) -> bytes:
        result = decoded(raw, proof.MAX_MESSAGE)
        require(isinstance(result, dict) and result.get('protocol') == RECEIPT_PROTOCOL
                and result.get('status') == 'accepted' and encoded(result) == raw, 'local-pack-receipt')
        return raw

"""Encode bounded requests for the private Home Git carrier."""
from __future__ import annotations

import re

import git_pack_proof as proof
from git_pack_push import MAX_CHANGES
from git_pack_receive_adapter import Admission, Change, PushRequest, proof_snapshot
from git_pack_worker_signature import MAX_GENERATION
from portable_recovery import TOKEN, UUID, decoded, encoded, match, number, require


PROTOCOL = 'stead.git-pack-relay/1'
MAX_HEADER = 65_536
MAX_FRAME = 196_608
SIGNATURE = re.compile(r'[0-9a-f]{128}')


def _frame(step: str, request_id: str, fields: dict, *documents: bytes) -> bytes:
    require(match(UUID, request_id), 'pack-relay-request-id')
    header = encoded({'protocol': PROTOCOL, 'step': step, 'request_id': request_id, **fields})
    require(len(header) <= MAX_HEADER and len(header) + sum(map(len, documents)) <= MAX_FRAME,
            'pack-relay-frame-bound')
    return header + b''.join(documents)


def advertise(request_id: str) -> bytes:
    """The caller allocates a fresh request UUID for writer discovery."""
    return _frame('advertise', request_id, {})


def admit(request_id: str, request: PushRequest) -> bytes:
    """Describe the exact original wire updates in order under a fresh UUID."""
    require(isinstance(request, PushRequest) and match(UUID, request.project)
            and match(TOKEN, request.wire_sha256) and isinstance(request.changes, tuple)
            and 0 < len(request.changes) <= MAX_CHANGES
            and all(isinstance(change, Change) for change in request.changes), 'pack-relay-admit')
    changes = {f'{index:02d}': {'ref': change.ref, 'prior': change.prior, 'target': change.target}
               for index, change in enumerate(request.changes)}
    updates = {'update_count': str(len(changes)), 'changes': changes}
    proof.ordered_changes(updates)
    return _frame('admit', request_id, {'wire_sha256': request.wire_sha256, **updates})


def transition(step: str, admitted: Admission, evidence: bytes, *, now_ms: int | None = None,
               worker_generation: int | None = None, worker_signature: str | None = None) -> bytes:
    """Bind exact admission and proof bytes to one verify, commit or receipt request."""
    require(step in ('verify', 'commit', 'receipt'), 'pack-relay-step')
    require(isinstance(admitted, Admission), 'pack-relay-admission')
    fields = {'admission_sha256': admitted.sha256}
    if step == 'receipt':
        require(worker_generation is None and worker_signature is None, 'pack-relay-receipt-worker')
        historical = decoded(admitted.raw, proof.MAX_MESSAGE)
        require(isinstance(historical, dict), 'pack-relay-admission')
        original_time = historical.get('admitted_at_ms')
        number(original_time)
        # Recovering a saved receipt uses the original admission and remains
        # possible after the worker lease or signing key expires.
        now_ms = int(original_time)
    else:
        require(type(worker_generation) is int and 0 < worker_generation <= MAX_GENERATION
                and match(SIGNATURE, worker_signature), 'pack-relay-worker')
        fields.update(worker_generation=str(worker_generation), worker_signature=worker_signature)
    claim = proof.admission(admitted.raw, admitted.sha256, now_ms)
    proof_snapshot(evidence, admitted, claim)
    return _frame(step, claim['request_id'], fields, admitted.raw, evidence)

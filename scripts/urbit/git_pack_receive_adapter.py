"""Coordinate a stock Git push through an injected private Home and worker."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import tempfile
import time
from typing import BinaryIO, Protocol

from execution_policy import directory_fd
import git_pack_proof as proof
import git_pack_receive as receive
import git_pack_store as store
from portable_code import private_directory, ref_name
from portable_recovery import (TOKEN, UUID, RecoveryError, decoded, encoded, match,
                               number, require, same_entry, same_path, shape)


# Discovery for this adapter must advertise only these response semantics.
CAPABILITIES = frozenset({b'report-status', b'atomic', b'ofs-delta', b'object-format=sha1'})
MAX_SECONDS = 60
RECEIPT_PROTOCOL = 'stead.git-pack-accepted/1'


@dataclass(frozen=True)
class Change:
    ref: str
    prior: str
    target: str


@dataclass(frozen=True)
class PushRequest:
    project: str
    wire_sha256: str
    changes: tuple[Change, ...]


@dataclass(frozen=True)
class Admission:
    raw: bytes
    sha256: str


class PushHome(Protocol):
    """Authenticated Home calls must enforce the passed monotone deadline.

    Reject only with an explicit, definite Home refusal. Network interruption
    and unvalidated replies are ambiguous. Recovery is read-only and must
    independently reauthorize the same individual bearer before receipt lookup.
    """

    def admit(self, bearer: str, request: PushRequest, deadline: float) -> Admission: ...

    def verify(self, bearer: str, admitted: Admission, evidence: bytes, deadline: float) -> bool: ...

    def commit(self, bearer: str, admitted: Admission, evidence: bytes, deadline: float) -> bytes: ...

    def recover(self, bearer: str, admitted: Admission, evidence: bytes, deadline: float) -> bytes | None: ...


class Worker(Protocol):
    """Trusted worker control channel, with no uploader credential in its payload."""

    def __call__(self, admitted: Admission, wire_path: Path, deadline: float) -> bytes: ...


class Rejected(RecoveryError):
    """The authoritative Home positively refused the operation."""


class Uncertain(RecoveryError):
    """The commit might have happened. The transport must withhold Git success."""


def within(deadline):
    require(time.monotonic() < deadline, 'push-deadline')


@contextmanager
def spool(root, body, count, deadline):
    with directory_fd(root) as parent:
        original = private_directory(parent)
        with tempfile.TemporaryDirectory(prefix='stead-receive-', dir=root) as scratch:
            directory = Path(scratch)
            digest = hashlib.sha256()
            with directory_fd(directory) as held:
                info = private_directory(held)
                fd = os.open('receive.wire', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=held)
                with os.fdopen(fd, 'wb') as stream:
                    while count:
                        within(deadline)
                        chunk = body.read(min(count, 65_536))
                        require(isinstance(chunk, bytes) and 0 < len(chunk) <= min(count, 65_536), 'push-body-length')
                        within(deadline)
                        count -= len(chunk)
                        digest.update(chunk)
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                    opened = os.fstat(stream.fileno())

                def check():
                    require(same_path(root, original) and same_entry(parent, directory.name, info)
                            and same_path(directory, info), 'push-spool-moved')
                    try:
                        observed = os.stat('receive.wire', dir_fd=held, follow_symlinks=False)
                    except FileNotFoundError:
                        raise RecoveryError('push-spool-changed') from None
                    require(same_entry(held, 'receive.wire', opened) and observed.st_ctime_ns == opened.st_ctime_ns
                            and observed.st_size == opened.st_size, 'push-spool-changed')

                check()
                yield directory / 'receive.wire', digest.hexdigest(), check


def packet(body):
    return f'{len(body) + 4:04x}'.encode('ascii') + body


def report(changes, accepted):
    error = b'authoritative Home refused the update'
    rows = b''.join(packet((b'ok ' if accepted else b'ng ') + ref_name(change.ref)
                           + (b'' if accepted else b' ' + error) + b'\n') for change in changes)
    return packet(b'unpack ok\n') + rows + b'0000'


def check_profile(wire):
    # The parser has already checked the first packet and canonical capability
    # framing. This gate narrows its offline profile to what we can report.
    size = int(wire[:4], 16)
    options = set(wire[4:size].removesuffix(b'\n').split(b'\0', 1)[1].removeprefix(b' ').split(b' '))
    require(b'report-status' in options and options <= CAPABILITIES, 'push-capability-not-advertised')


def correlate(admitted, request, now_ms):
    require(isinstance(admitted, Admission), 'push-admission-response')
    claim = proof.admission(admitted.raw, admitted.sha256, now_ms)
    require(claim['scope']['project_id'] == request.project and claim['wire_sha256'] == request.wire_sha256
            and tuple(Change(**change) for change in proof.ordered_changes(claim)) == request.changes,
            'push-admission-response')
    return claim


def proof_snapshot(evidence, admitted, claim):
    value = decoded(evidence, proof.MAX_MESSAGE)
    shape(value, (proof.CLAIM - {'changes'}) | {'protocol', 'admission_sha256', 'candidate_snapshot', 'head', 'updates', 'pack'})
    require(encoded(value) == evidence and value['protocol'] == proof.PROTOCOL
            and value['admission_sha256'] == admitted.sha256 and match(TOKEN, value['candidate_snapshot'])
            and all(value[key] == claim[key] for key in proof.CLAIM - {'changes'}), 'push-worker-response')
    ref_name(value['head'], branch=True)
    pack = value['pack']
    shape(pack, proof.PACK)
    require(all(match(TOKEN, pack[key]) for key in ('pack_sha256', 'object_ids_sha256')), 'push-worker-response')
    for key, minimum, maximum in (('pack_bytes', 32, store.MAX_PACK), ('object_count', 1, store.MAX_OBJECTS),
                                  ('object_bytes', 1, store.MAX_OBJECT_BYTES)):
        number(pack[key])
        require(minimum <= int(pack[key]) <= maximum, 'push-worker-response')
    updates = value['updates']
    shape(updates, set(claim['changes']))
    for index, expected in claim['changes'].items():
        row = updates[index]
        shape(row, proof.CHANGE | {'kind', 'lineage'})
        branch = ref_name(expected['ref']).startswith(b'refs/heads/')
        require(all(row[key] == expected[key] for key in proof.CHANGE)
                and row['kind'] in ('commit', 'tree', 'blob', 'tag')
                and (not branch or row['kind'] == 'commit')
                and row['lineage'] == ('none' if expected['prior'] == '0' * 40 else 'fast-forward'),
                'push-worker-response')
    return value['candidate_snapshot']


def receipt(raw, admitted, claim, candidate, now_ms):
    require(isinstance(raw, bytes), 'push-receipt-response')
    value = decoded(raw, proof.MAX_MESSAGE)
    expected = {key: claim[key] for key in ('request_id', 'scope', 'actor', 'wire_sha256', 'changes', 'update_count')}
    expected.update(protocol=RECEIPT_PROTOCOL, status='accepted', admission_sha256=admitted.sha256,
                    candidate_snapshot=candidate, generation=str(int(claim['generation']) + 1))
    shape(value, set(expected) | {'accepted_at_ms'})
    require(encoded(value) == raw and all(value[key] == item for key, item in expected.items()), 'push-receipt-response')
    accepted_at = value['accepted_at_ms']
    require(isinstance(accepted_at, str) and 0 < len(accepted_at) <= 20 and accepted_at.isascii()
            and accepted_at.isdecimal() and str(int(accepted_at)) == accepted_at
            and int(claim['admitted_at_ms']) <= int(accepted_at) < int(claim['expires_at_ms'])
            and int(accepted_at) <= now_ms, 'push-receipt-time')


def accepted_commit(home, bearer, admitted, claim, evidence, candidate, deadline, clock):
    try:
        result = home.commit(bearer, admitted, evidence, deadline)
        within(deadline)
        receipt(result, admitted, claim, candidate, clock())
        return
    except Rejected:
        raise
    except (RecoveryError, OSError):
        pass
    # Only this exact request, proof and same current write bearer may
    # reconcile an ambiguous outcome. Never send a second commit operation.
    try:
        within(deadline)
        result = home.recover(bearer, admitted, evidence, deadline)
        within(deadline)
        receipt(result, admitted, claim, candidate, clock())
    except (RecoveryError, OSError):
        raise Uncertain('push-acceptance-unconfirmed') from None


def receive_push(home: PushHome, worker: Worker, spool_root: Path, project: str, bearer: str,
                 body: BinaryIO, content_length: int, *, deadline: float, clock=None) -> bytes:
    """Process one origin-framed body. Only a matching Home receipt yields `ok`.

    The isolated ingress must pass exactly the framed Content-Length body and
    enforce read deadlines. Neither this adapter nor its worker issues creds.
    A rejected update after valid unpack yields an ordinary `ng` report.
    Before unpack or after ambiguous commit failure the caller must withhold it.
    """
    require(match(UUID, project) and match(TOKEN, bearer), 'push-credential-or-project')
    require(type(content_length) is int and 0 < content_length <= receive.MAX_WIRE, 'push-body-bound')
    require(type(deadline) in (int, float) and math.isfinite(deadline), 'push-deadline')
    deadline = min(deadline, time.monotonic() + MAX_SECONDS)
    if clock is None:
        clock = lambda: time.time_ns() // 1_000_000
    with spool(Path(spool_root), body, content_length, deadline) as (path, digest, check):
        with receive.captured_wire(path, digest) as (wire, recheck):
            parsed, _ = receive.parse(wire)
            check_profile(wire)
            recheck()
        changes = tuple(Change(**change) for change in parsed)
        request = PushRequest(project, digest, changes)
        within(deadline)
        admitted = home.admit(bearer, request, deadline)
        within(deadline)
        claim = correlate(admitted, request, clock())
        check()
        evidence = worker(admitted, path, deadline)
        within(deadline)
        check()
        candidate = proof_snapshot(evidence, admitted, claim)
        try:
            verified = home.verify(bearer, admitted, evidence, deadline)
            within(deadline)
            if verified is False:
                raise Rejected('push-verification-refused')
            require(verified is True, 'push-verification-response')
            check()
            accepted_commit(home, bearer, admitted, claim, evidence, candidate, deadline, clock)
        except Rejected:
            return report(changes, False)
        within(deadline)
        return report(changes, True)

"""Explicit same-host transport for the private Git verification worker."""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import math
import os
from pathlib import Path
import re
import socket
import stat
import struct
from threading import Lock
import time

from execution_policy import directory_fd
import git_pack_proof as proof
import git_pack_receive as receive
from git_pack_receive_adapter import Admission, Worker, proof_snapshot, spool
import git_pack_worker_signature as signing
from portable_code import private_directory
from portable_recovery import TOKEN, RecoveryError, match, require, same_entry, same_path


REQUEST_MAGIC = b'SGPWREQ1'
RESPONSE_MAGIC = b'SGPWRES1'
REQUEST = struct.Struct('!8sQII32s')
RESPONSE = struct.Struct('!8sBIQ')
PEER = struct.Struct('=iII')
MAX_SECONDS = 55
# The signer runs two fixed OpenSSL commands, each with a five-second timeout.
SIGN_SECONDS = 10.5
SIGNED = 0
REFUSED = 1
SIGNATURE = re.compile(r'[0-9a-f]{128}')


@dataclass(frozen=True)
class SignedProof:
    proof: bytes
    generation: int
    signature: str


def identities(relay_uid, worker_uid):
    require(all(type(uid) is int and 0 <= uid < 2**32 - 1 for uid in (relay_uid, worker_uid)), 'worker-peer-profile')
    require(relay_uid != worker_uid, 'worker-peer-profile')


def deadline_for(value):
    require(type(value) is int or type(value) is float and math.isfinite(value), 'worker-socket-deadline')
    return min(value, time.monotonic() + MAX_SECONDS)


def remaining(until):
    duration = until - time.monotonic()
    require(duration > 0, 'worker-socket-deadline')
    return duration


def peer_is(channel, expected):
    pid, uid, _ = PEER.unpack(channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, PEER.size))
    require(pid > 0 and uid == expected, 'worker-socket-peer')


def read_exact(channel, count, deadline):
    data = bytearray()
    while len(data) < count:
        channel.settimeout(remaining(deadline))
        chunk = channel.recv(count - len(data))
        require(chunk, 'worker-socket-incomplete')
        data.extend(chunk)
    return bytes(data)


def send(channel, data, deadline):
    channel.settimeout(remaining(deadline))
    channel.sendall(data)


def end_of_frame(channel, deadline):
    channel.settimeout(remaining(deadline))
    require(channel.recv(1) == b'', 'worker-socket-trailing')


class SocketSource:
    def __init__(self, channel, deadline):
        self.channel, self.deadline = channel, deadline

    def read(self, count):
        return read_exact(self.channel, count, self.deadline)


class WorkerSocket:
    """One foreground worker endpoint. Opening or serving requires explicit calls.

    The parent is worker-owned, with traversal for an operator-selected group
    that can reach the socket. The spool and signing key are worker-private.
    """

    def __init__(self, path: Path, spool_root: Path, relay_uid: int, worker_uid: int,
                 worker: Worker, generation: int, key: Path, *, group_gid: int, clock=None):
        identities(relay_uid, worker_uid)
        require(os.geteuid() == worker_uid == os.getuid(), 'worker-socket-owner')
        require(type(generation) is int and 1 <= generation <= signing.MAX_GENERATION, 'worker-signing-generation')
        require(type(group_gid) is int and 0 <= group_gid < 2**32 - 1, 'worker-socket-group')
        self.path, self.spool_root, self.key = (Path(value) for value in (path, spool_root, key))
        require(all(p.is_absolute() and '..' not in p.parts for p in (self.path, self.spool_root, self.key))
                and len(os.fsencode(self.path)) <= 107 and self.path.name, 'worker-socket-path')
        self.relay_uid, self.worker_uid, self.group_gid = relay_uid, worker_uid, group_gid
        self.worker, self.generation = worker, generation
        self.clock = clock if clock is not None else lambda: time.time_ns() // 1_000_000
        self.serving = Lock()
        self.listener = None

    def __enter__(self):
        require(self.listener is None, 'worker-socket-open')
        with ExitStack() as setup:
            parent = setup.enter_context(directory_fd(self.path.parent))
            spool = setup.enter_context(directory_fd(self.spool_root))
            directory = os.fstat(parent)
            self.spool_binding = private_directory(spool)
            require(directory.st_uid == self.worker_uid and not directory.st_mode & 0o027
                    and directory.st_gid == self.group_gid and directory.st_mode & 0o010,
                    'worker-socket-private-parent')
            require(self.path.parent.resolve(strict=True) == self.path.parent
                    and self.spool_root.resolve(strict=True) == self.spool_root, 'worker-socket-path')
            channel = setup.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
            require(same_path(self.path.parent, directory), 'worker-socket-parent-moved')
            # Bind in the owned directory already opened without symlinks.
            # This local alias remains inside the worker process.
            reference = f'/proc/self/fd/{parent}/{self.path.name}'
            require(len(os.fsencode(reference)) <= 107, 'worker-socket-path')
            channel.bind(reference)
            opened = os.stat(self.path.name, dir_fd=parent, follow_symlinks=False)
            require(stat.S_ISSOCK(opened.st_mode) and opened.st_uid == self.worker_uid, 'worker-socket-owner')

            def cleanup():
                if same_entry(parent, self.path.name, opened):
                    os.unlink(self.path.name, dir_fd=parent)

            setup.callback(cleanup)
            os.chown(self.path.name, -1, self.group_gid, dir_fd=parent, follow_symlinks=False)
            os.chmod(self.path.name, 0o660, dir_fd=parent, follow_symlinks=False)
            require(same_path(self.path.parent, directory) and same_entry(parent, self.path.name, opened),
                    'worker-socket-parent-moved')
            channel.listen(1)
            self.listener = channel
            self.resources = setup.pop_all()
        return self

    def __exit__(self, *_):
        try:
            self.resources.close()
        finally:
            self.listener = None

    def serve_one(self, deadline: float) -> bool:
        require(self.listener is not None and self.serving.acquire(blocking=False), 'worker-socket-busy')
        try:
            until = deadline_for(deadline)
            self.listener.settimeout(remaining(until))
            try:
                channel, _ = self.listener.accept()
            except TimeoutError:
                return False
            with channel:
                try:
                    peer_is(channel, self.relay_uid)
                except (OSError, RecoveryError):
                    return False
                try:
                    return self._serve(channel, until)
                except (RecoveryError, OSError):
                    try:
                        send(channel, RESPONSE.pack(RESPONSE_MAGIC, REFUSED, 0, 0), until)
                    except (OSError, RecoveryError):
                        pass
                    return False
        finally:
            self.serving.release()

    def _serve(self, channel, outer):
        magic, epoch_ns, admission_size, wire_size, digest_bytes = REQUEST.unpack(read_exact(channel, REQUEST.size, outer))
        require(magic == REQUEST_MAGIC and 0 < admission_size <= proof.MAX_MESSAGE
                and 0 < wire_size <= receive.MAX_WIRE, 'worker-socket-request')
        until = min(outer, epoch_ns / 1_000_000_000)
        raw = read_exact(channel, admission_size, until)
        digest = digest_bytes.hex()
        claim = proof.admission(raw, digest, self.clock())
        require(same_path(self.spool_root, self.spool_binding), 'worker-socket-spool-moved')
        with spool(self.spool_root, SocketSource(channel, until), wire_size, until) as (path, checksum, recheck):
            end_of_frame(channel, until)
            require(checksum == claim['wire_sha256'], 'worker-socket-wire-digest')
            authorization = Admission(raw, digest)
            recheck()
            require(same_path(self.spool_root, self.spool_binding), 'worker-socket-spool-moved')
            remaining(until - SIGN_SECONDS)
            result = self.worker(authorization, path, until - SIGN_SECONDS)
            recheck()
            proof_snapshot(result, authorization, claim)
            remaining(until - SIGN_SECONDS)
            proof.admission(raw, digest, self.clock())
            attestation = signing.sign(result, self.generation, self.key)
            remaining(until)
            proof.admission(raw, digest, self.clock())
            require(match(SIGNATURE, attestation), 'worker-socket-signature')
            send(channel, RESPONSE.pack(RESPONSE_MAGIC, SIGNED, len(result), self.generation), until)
            send(channel, result + bytes.fromhex(attestation), until)
        return True


def request(path: Path, worker_uid: int, relay_uid: int, admitted: Admission, wire_path: Path,
            deadline: float, *, clock=None) -> SignedProof:
    """Exchange one request with an independently pinned worker Unix UID."""
    identities(relay_uid, worker_uid)
    require(os.geteuid() == relay_uid == os.getuid(), 'worker-socket-owner')
    path, wire_path = Path(path), Path(wire_path)
    require(path.is_absolute() and '..' not in path.parts and len(os.fsencode(path)) <= 107 and path.name
            and wire_path.is_absolute() and '..' not in wire_path.parts, 'worker-socket-path')
    require(isinstance(admitted, Admission) and match(TOKEN, admitted.sha256), 'worker-socket-admission')
    now = clock if clock is not None else lambda: time.time_ns() // 1_000_000
    claim = proof.admission(admitted.raw, admitted.sha256, now())
    until = deadline_for(deadline)
    remaining(until)
    try:
        with receive.captured_wire(wire_path, claim['wire_sha256']) as (wire, recheck), \
                socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.settimeout(remaining(until))
            channel.connect(str(path))
            peer_is(channel, worker_uid)
            send(channel, REQUEST.pack(REQUEST_MAGIC, int(until * 1_000_000_000), len(admitted.raw),
                                       len(wire), bytes.fromhex(admitted.sha256)), until)
            send(channel, admitted.raw, until)
            send(channel, wire, until)
            channel.shutdown(socket.SHUT_WR)
            magic, status, count, generation = RESPONSE.unpack(read_exact(channel, RESPONSE.size, until))
            require(magic == RESPONSE_MAGIC, 'worker-socket-response')
            if (status, count, generation) == (REFUSED, 0, 0):
                end_of_frame(channel, until)
                raise RecoveryError('worker-socket-refused')
            require(status == SIGNED and 0 < count <= signing.MAX_PROOF
                    and 0 < generation <= signing.MAX_GENERATION, 'worker-socket-response')
            result = read_exact(channel, count, until)
            signature = read_exact(channel, 64, until).hex()
            end_of_frame(channel, until)
            proof_snapshot(result, admitted, claim)
            proof.admission(admitted.raw, admitted.sha256, now())
            recheck()
            return SignedProof(result, generation, signature)
    except OSError:
        raise RecoveryError('worker-socket-unavailable') from None

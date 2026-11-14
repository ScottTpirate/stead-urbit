"""Read-only, peer-checked Unix transport for one project's accepted packs."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import math
import os
from pathlib import Path
import socket
import stat
import struct
from threading import Lock
import time

from execution_policy import directory_fd
import git_pack_projection as projection
import git_pack_store as store
from git_pack_worker_socket import end_of_frame, identities, peer_is, read_exact, remaining, send
from portable_recovery import TOKEN, RecoveryError, encoded, match, require, same_entry, same_path, sha


REQUEST = struct.Struct('!8sQ32s32s')
RESPONSE = struct.Struct('!8sI32s')
REQUEST_MAGIC = b'SGPXRQ01'
RESPONSE_MAGIC = b'SGPXRS01'
COMPLETE = b'\x01'


def _deadline(value):
    require(type(value) is int or type(value) is float and math.isfinite(value), 'pack-projection-socket-deadline')
    return min(value, time.monotonic() + projection.MAX_SECONDS)


def _paths(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and path.name
            and len(os.fsencode(path)) <= 107, 'pack-projection-socket-path')
    return path


def _scope_digest(scope):
    store.validate_scope(scope)
    require(scope['project_id'] == scope['repository_id'], 'pack-projection-socket-scope')
    return bytes.fromhex(sha(encoded(scope)))


class ArtifactSocket:
    """Expose only accepted hashes supplied by an operator-owned selection gate.

    The gate receives the exact snapshot and remaining monotone deadline. It
    must obtain a current selection or test a fixed approved synthetic digest.
    It is checked before bytes and again before a successful close marker.
    """

    def __init__(self, path, storage, scope, is_selected, relay_uid, worker_uid, *, group_gid):
        identities(relay_uid, worker_uid)
        require(os.geteuid() == worker_uid == os.getuid() and callable(is_selected)
                and type(group_gid) is int and 0 <= group_gid < 2**32 - 1, 'pack-projection-socket-owner')
        self.path, self.storage = _paths(path), Path(storage)
        require(self.storage.is_absolute() and '..' not in self.storage.parts, 'pack-projection-socket-path')
        self.scope, self.digest = scope.copy(), _scope_digest(scope)
        self.is_selected = is_selected
        self.relay_uid, self.worker_uid, self.group_gid = relay_uid, worker_uid, group_gid
        self.lock = Lock()
        self.listener = None

    def __enter__(self):
        require(self.listener is None, 'pack-projection-socket-open')
        with ExitStack() as setup:
            parent = setup.enter_context(directory_fd(self.path.parent))
            directory = os.fstat(parent)
            require(directory.st_uid == self.worker_uid and directory.st_gid == self.group_gid
                    and not directory.st_mode & 0o027 and directory.st_mode & 0o010,
                    'pack-projection-socket-parent')
            channel = setup.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
            require(same_path(self.path.parent, directory), 'pack-projection-socket-parent')
            channel.bind(f'/proc/self/fd/{parent}/{self.path.name}')
            opened = os.stat(self.path.name, dir_fd=parent, follow_symlinks=False)
            require(stat.S_ISSOCK(opened.st_mode) and opened.st_uid == self.worker_uid, 'pack-projection-socket-owner')

            def cleanup():
                if same_entry(parent, self.path.name, opened):
                    os.unlink(self.path.name, dir_fd=parent)

            setup.callback(cleanup)
            os.chown(self.path.name, -1, self.group_gid, dir_fd=parent, follow_symlinks=False)
            os.chmod(self.path.name, 0o660, dir_fd=parent, follow_symlinks=False)
            require(same_path(self.path.parent, directory) and same_entry(parent, self.path.name, opened),
                    'pack-projection-socket-parent')
            channel.listen(1)
            self.listener, self.resources = channel, setup.pop_all()
        return self

    def __exit__(self, *_):
        try:
            self.resources.close()
        finally:
            self.listener = None

    def serve_one(self, deadline):
        require(self.listener is not None and self.lock.acquire(blocking=False), 'pack-projection-socket-busy')
        try:
            until = _deadline(deadline)
            self.listener.settimeout(remaining(until))
            with self.listener.accept()[0] as channel:
                peer_is(channel, self.relay_uid)
                self._serve(channel, until)
            return True
        except (OSError, RecoveryError):
            return False
        finally:
            self.lock.release()

    def _serve(self, channel, deadline):
        magic, caller_until, scope, digest = REQUEST.unpack(read_exact(channel, REQUEST.size, deadline))
        require(magic == REQUEST_MAGIC and scope == self.digest, 'pack-projection-socket-scope')
        deadline = min(deadline, caller_until / 1_000_000_000)
        end_of_frame(channel, deadline)
        snapshot = digest.hex()
        require(self.is_selected(snapshot, deadline) is True, 'pack-projection-socket-selection')
        with projection.retained(self.storage, snapshot, self.scope, deadline) as source:
            length = os.fstat(source.fileno()).st_size
            send(channel, RESPONSE.pack(RESPONSE_MAGIC, length, digest), deadline)
            pending = length
            while pending:
                remaining(deadline)
                chunk = source.read(min(pending, projection.CHUNK))
                require(chunk, 'pack-projection-socket-source')
                send(channel, chunk, deadline)
                pending -= len(chunk)
            require(source.read(1) == b'', 'pack-projection-socket-source')
        require(self.is_selected(snapshot, deadline) is True, 'pack-projection-socket-selection')
        send(channel, COMPLETE, deadline)


class _Body:
    def __init__(self, channel, deadline, length):
        self.channel, self.deadline, self.pending = channel, deadline, length
        self.finished = False

    def read(self, count):
        require(type(count) is int and 0 < count <= projection.CHUNK, 'pack-projection-socket-read')
        if self.pending:
            chunk = read_exact(self.channel, min(self.pending, count), self.deadline)
            self.pending -= len(chunk)
            return chunk
        if not self.finished:
            require(read_exact(self.channel, 1, self.deadline) == COMPLETE, 'pack-projection-socket-incomplete')
            end_of_frame(self.channel, self.deadline)
            self.finished = True
        return b''


@contextmanager
def open_artifact(path, worker_uid, relay_uid, snapshot, scope, deadline):
    """Connect as the relay UID and expose only a bounded, finished byte stream."""
    identities(relay_uid, worker_uid)
    require(os.geteuid() == relay_uid == os.getuid() and match(TOKEN, snapshot), 'pack-projection-socket-owner')
    path = _paths(path)
    scope_digest, digest = _scope_digest(scope), bytes.fromhex(snapshot)
    deadline = _deadline(deadline)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.settimeout(remaining(deadline))
            channel.connect(str(path))
            peer_is(channel, worker_uid)
            send(channel, REQUEST.pack(REQUEST_MAGIC, int(deadline * 1_000_000_000), scope_digest, digest), deadline)
            channel.shutdown(socket.SHUT_WR)
            magic, length, echo = RESPONSE.unpack(read_exact(channel, RESPONSE.size, deadline))
            require(magic == RESPONSE_MAGIC and echo == digest and 32 <= length <= store.MAX_PACK,
                    'pack-projection-socket-response')
            stream = _Body(channel, deadline, length)
            yield stream
            require(stream.finished, 'pack-projection-socket-incomplete')
    except OSError:
        raise RecoveryError('pack-projection-socket-unavailable') from None

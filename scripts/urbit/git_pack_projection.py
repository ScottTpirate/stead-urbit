"""Copy one Home-selected immutable pack into a separate private read store.

The worker's export runs under its own UID with read access to its retained
store. The relay imports only a bounded byte stream, under the relay UID, and
the current Home decision pins the complete manifest and original pack hash.
The operator-owned handoff must authenticate its peers, bind this one scope
and digest, and enforce the deadline on every read. It carries no bearer,
peer-supplied paths or write access between stores.
"""
from __future__ import annotations

from contextlib import contextmanager
import math
import os
from pathlib import Path
import stat
import tempfile
import time

from execution_policy import directory_fd
from git_pack_http import decision
import git_pack_store as store
from portable_code import private_directory, publish_directory, staged_repository, sync_tree
from portable_recovery import UUID, encoded, match, require, same_entry, same_path, sha


MAX_SECONDS = 120
CHUNK = 65_536
SIZES = ('pack_bytes', 'object_count', 'object_bytes')
DIGESTS = ('pack_sha256', 'object_ids_sha256')


def _remaining(deadline):
    require(time.monotonic() < deadline, 'pack-projection-deadline')


@contextmanager
def retained(storage, snapshot, scope, deadline):
    """Open one retained worker artifact as a private, read-only byte stream.

    Invoke only through an authenticated handoff for an approved scope and
    digest. The relay authenticates the contents against Home independently.
    """
    _remaining(deadline)
    with store.repository_directory(storage, scope) as (directory, check_store), \
            store.open_snapshot(directory, snapshot) as source:
        value = store.read_manifest(source, snapshot, scope)
        fd = os.open(store.PACK_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=source)
        with os.fdopen(fd, 'rb') as stream:
            original = os.fstat(stream.fileno())
            require(stat.S_ISREG(original.st_mode) and original.st_uid == os.getuid() and original.st_nlink == 1
                    and not original.st_mode & 0o077 and 32 <= original.st_size <= store.MAX_PACK
                    and original.st_size == value['pack_bytes'], 'pack-projection-source')
            _remaining(deadline)
            yield stream
            _remaining(deadline)
            current = os.fstat(stream.fileno())
            require(same_entry(source, store.PACK_NAME, original) and original.st_ctime_ns == current.st_ctime_ns
                    and original.st_size == current.st_size, 'pack-projection-source-changed')
            check_store()


def _copy(source, path, count, deadline):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as file:
        while count:
            _remaining(deadline)
            request = min(count, CHUNK)
            block = source.read(request)
            require(isinstance(block, bytes) and 0 < len(block) <= request, 'pack-projection-transfer-length')
            file.write(block)
            count -= len(block)
        _remaining(deadline)
        require(source.read(1) == b'', 'pack-projection-transfer-length')
        _remaining(deadline)


def _manifest(observed, project_id, home_ship):
    scope, report, refs = decision(observed, project_id)
    require(scope['home'] == home_ship and encoded(report)[:-1] == observed, 'pack-projection-home')
    manifest = {'format': store.FORMAT, 'object_format': 'sha1', 'scope': scope, 'head': report['head'],
                'refs': refs, **{key: int(report[key]) for key in SIZES}, **{key: report[key] for key in DIGESTS}}
    return report['snapshot'], manifest


def project(decide, project_id, home_ship, read_store, open_artifact, git, *, deadline):
    """Verify and publish an exact accepted pack, returning its digest.

    ``decide(deadline)`` makes a fresh native Home read and returns canonical
    response bytes. ``open_artifact(snapshot, scope, deadline)`` yields a
    read-only stream for that one snapshot, framed through EOF. A retry can
    verify a still-selected local copy without reusing the transport.
    """
    require(match(UUID, project_id) and match(store.SHIP, home_ship), 'pack-projection-scope')
    read_store, git = Path(read_store), Path(git)
    require(read_store.is_absolute() and git.is_absolute(), 'pack-projection-path')
    require(type(deadline) in (int, float) and math.isfinite(deadline), 'pack-projection-deadline')
    deadline = min(deadline, time.monotonic() + MAX_SECONDS)
    _remaining(deadline)
    observed = decide(deadline)
    snapshot, expected = _manifest(observed, project_id, home_ship)
    scope = expected['scope']

    def check_current():
        _remaining(deadline)
        require(decide(deadline) == observed, 'pack-projection-home-changed')
        _remaining(deadline)

    with store.repository_directory(read_store, scope, staging=True) as (directory, check_store):
        if os.path.lexists(f'/proc/self/fd/{directory}/{snapshot}'):
            with store.open_snapshot(directory, snapshot) as held:
                require(store.read_manifest(held, snapshot, scope) == expected, 'pack-projection-conflict')
                require(store.copy_pack(held, store.PACK_NAME, expected['pack_sha256'])
                        == (expected['pack_bytes'], expected['object_count']), 'pack-projection-conflict')
                check_current()
                check_store()
                os.fsync(directory)
                _remaining(deadline)
                return snapshot

        with os.scandir(directory) as entries:
            for count, _ in enumerate(entries, 1):
                require(count < store.MAX_SNAPSHOTS, 'snapshot-capacity')
        with tempfile.TemporaryDirectory(prefix='stead-pack-projection-') as temporary:
            scratch = Path(temporary)
            incoming = scratch / store.PACK_NAME
            with open_artifact(snapshot, scope.copy(), deadline) as source:
                _copy(source, incoming, expected['pack_bytes'], deadline)
            with directory_fd(scratch) as source:
                private_directory(source)
                with staged_repository(directory, git, deadline=deadline, command_prefix=store.GIT_LIMITS) as (
                        name, binding, repo):
                    verified, inventory = store.verify_pack(repo, source, store.PACK_NAME, expected['pack_sha256'],
                                                            expected['refs'], expected['head'])
                    require(all(type(expected[key]) is type(value) and expected[key] == value
                                for key, value in inventory.items()), 'pack-projection-inventory')
                    payload = Path(repo.path) / 'payload'
                    payload.mkdir(mode=0o700)
                    verified.rename(payload / store.PACK_NAME)
                    manifest = encoded(expected)
                    require(sha(manifest) == snapshot, 'pack-projection-manifest')
                    with (payload / store.MANIFEST_NAME).open('xb') as file:
                        os.fchmod(file.fileno(), 0o600)
                        file.write(manifest)
                    sync_tree(repo)
                    check_current()
                    check_store()
                    require(same_entry(directory, name, binding), 'pack-projection-store-changed')
                    _remaining(deadline)
                    publish_directory(directory, name + '/payload', snapshot)
                    os.fsync(directory)
                    check_store()
                    _remaining(deadline)
                    return snapshot

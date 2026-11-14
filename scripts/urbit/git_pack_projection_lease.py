"""Publish and read one controller-owned, nonsecret accepted-pack lease."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import re
import secrets
import stat
import time

from execution_policy import directory_fd
from git_pack_projection import _deadline, _remaining, validate_manifest
import git_pack_store as store
from portable_recovery import TOKEN, RecoveryError, decoded, encoded, match, number, require, same_entry, same_path, shape


PROTOCOL = 'stead.git-pack-projection-lease/1'
SELECTION = 'stead.git-pack-projection-selection/1'
FIELDS = {'protocol', 'status', 'scope', 'incarnation', 'relay_generation', 'boot_id',
          'issued_ns', 'expires_ns', 'snapshot', 'manifest'}
OWNER_FIELDS = {'protocol', 'status', 'incarnation', 'relay_generation', 'snapshot', 'manifest'}
BOOT_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
MAX_TTL = 15
NANOS = 1_000_000_000
MAX_RECORD = store.MAX_MANIFEST + 2048
MAX_OWNER = 512 * 1024


def boot_ns():
    return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


@dataclass(frozen=True)
class Selection:
    incarnation: str
    relay_generation: str
    snapshot: str
    manifest: dict


class Mailbox:
    """One atomic record in a controller-owned 0750 directory and group.

    The controller is its only writer. Relay and verifier may read through a
    shared group but have no write permission. Every open rereads the inode.
    """

    def __init__(self, path, scope, controller_uid, group_gid, *, clock=boot_ns, boot_id=None):
        store.validate_scope(scope)
        self.path, self.scope = Path(path), scope.copy()
        require(scope['project_id'] == scope['repository_id'] and self.path.is_absolute()
                and '..' not in self.path.parts and self.path.name
                and all(type(value) is int and 0 <= value < 2**32 - 1 for value in (controller_uid, group_gid)),
                'pack-projection-lease-profile')
        self.controller_uid, self.group_gid, self.clock = controller_uid, group_gid, clock
        self.boot_id = (Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                        if boot_id is None else boot_id)
        require(match(BOOT_ID, self.boot_id), 'pack-projection-lease-boot')

    @contextmanager
    def _parent(self):
        with directory_fd(self.path.parent) as parent:
            info = os.fstat(parent)
            require(info.st_uid == self.controller_uid and info.st_gid == self.group_gid
                    and stat.S_IMODE(info.st_mode) == 0o750, 'pack-projection-lease-parent')
            yield parent, info

    def _record(self, parent, info):
        fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == self.controller_uid
                    and before.st_gid == self.group_gid and before.st_nlink == 1
                    and stat.S_IMODE(before.st_mode) == 0o640 and 0 < before.st_size <= MAX_RECORD,
                    'pack-projection-lease-file')
            raw = stream.read(MAX_RECORD + 1)
            after = os.fstat(stream.fileno())
            require(len(raw) == before.st_size and after.st_ctime_ns == before.st_ctime_ns
                    and same_entry(parent, self.path.name, before) and same_path(self.path.parent, info),
                    'pack-projection-lease-changed')
        value = decoded(raw, MAX_RECORD)
        shape(value, FIELDS)
        require(encoded(value) == raw and value['protocol'] == PROTOCOL and value['scope'] == self.scope
                and value['boot_id'] == self.boot_id, 'pack-projection-lease-record')
        return value

    def current(self, deadline):
        """Return the exact current selection, or raise for any unavailable lease."""
        _remaining(deadline)
        try:
            with self._parent() as (parent, info):
                value = self._record(parent, info)
        except OSError:
            raise RecoveryError('pack-projection-lease-unavailable') from None
        require(value['status'] == 'open' and match(TOKEN, value['incarnation']), 'pack-projection-lease-closed')
        for key in ('issued_ns', 'expires_ns', 'relay_generation'):
            number(value[key])
        issued, expires = int(value['issued_ns']), int(value['expires_ns'])
        require(issued <= self.clock() < expires <= issued + MAX_TTL * NANOS, 'pack-projection-lease-expired')
        selection = Selection(*(value[key] for key in ('incarnation', 'relay_generation', 'snapshot', 'manifest')))
        validate_manifest(selection.snapshot, selection.manifest, self.scope)
        _remaining(deadline)
        require(self.clock() < expires, 'pack-projection-lease-expired')
        return selection

    def is_selected(self, snapshot, deadline):
        try:
            return self.current(deadline).snapshot == snapshot
        except RecoveryError:
            return False

    @contextmanager
    def _writer(self):
        require(os.getuid() == os.geteuid() == self.controller_uid, 'pack-projection-lease-writer')
        with self._parent() as (parent, info):
            fcntl.flock(parent, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield parent, info

    def _write(self, parent, info, value, *, expires=None):
        raw = encoded({'protocol': PROTOCOL, 'scope': self.scope, 'boot_id': self.boot_id, **value})
        require(len(raw) <= MAX_RECORD, 'pack-projection-lease-bound')
        temp = '.projection-' + secrets.token_hex(16)
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        before = os.fstat(fd)
        try:
            with os.fdopen(fd, 'wb') as stream:
                os.fchown(stream.fileno(), -1, self.group_gid)
                os.fchmod(stream.fileno(), 0o640)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                require(same_entry(parent, temp, before) and same_path(self.path.parent, info),
                        'pack-projection-lease-changed')
                require(expires is None or self.clock() < expires, 'pack-projection-lease-expired')
                os.replace(temp, self.path.name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
                require(same_entry(parent, self.path.name, before) and same_path(self.path.parent, info),
                        'pack-projection-lease-changed')
        finally:
            if same_entry(parent, temp, before):
                os.unlink(temp, dir_fd=parent)

    def _close(self, parent, info):
        observed = self.clock()
        self._write(parent, info, {'status': 'closed', 'incarnation': '', 'relay_generation': '0',
                                   'issued_ns': str(observed), 'expires_ns': str(observed),
                                   'snapshot': '', 'manifest': None})

    def close(self):
        """Invalidate any prior authority immediately at the atomic boundary."""
        with self._writer() as (parent, info):
            self._close(parent, info)

    def _selected(self, raw):
        value = decoded(raw, MAX_OWNER) if isinstance(raw, bytes) else raw
        shape(value, OWNER_FIELDS)
        require(all(isinstance(value[key], str) for key in OWNER_FIELDS) and value['protocol'] == SELECTION
                and (not isinstance(raw, bytes) or raw in (encoded(value), encoded(value)[:-1])),
                'pack-projection-owner-record')
        number(value['relay_generation'], positive=False)
        if value['status'] == 'closed':
            require(value['manifest'] == value['snapshot'] == ''
                    and (value['incarnation'] == '' or match(TOKEN, value['incarnation'])),
                    'pack-projection-owner-record')
            return None
        require(value['status'] == 'open' and match(TOKEN, value['incarnation'])
                and value['relay_generation'] != '0' and len(value['manifest']) <= store.MAX_MANIFEST,
                'pack-projection-owner-record')
        require(value['manifest'].isascii(), 'pack-projection-owner-manifest')
        manifest_raw = value['manifest'].encode('ascii')
        manifest = decoded(manifest_raw, store.MAX_MANIFEST)
        canonical = validate_manifest(value['snapshot'], manifest, self.scope)
        require(manifest_raw in (canonical, canonical[:-1]), 'pack-projection-owner-manifest')
        return Selection(value['incarnation'], value['relay_generation'], value['snapshot'], manifest)

    def publish(self, observe, deadline, *, ttl=MAX_TTL):
        """Refresh using direct trusted owner readback, or close on its failure."""
        require(type(ttl) is int and 0 < ttl <= MAX_TTL, 'pack-projection-lease-ttl')
        deadline = _deadline(deadline)
        with self._writer() as (parent, info):
            issued = self.clock()
            expires = issued + ttl * NANOS
            try:
                _remaining(deadline)
                selection = self._selected(observe(deadline))
                _remaining(deadline)
                require(issued <= self.clock() < expires, 'pack-projection-lease-expired')
                if selection is not None:
                    self._write(parent, info, {'status': 'open', 'incarnation': selection.incarnation,
                                               'relay_generation': selection.relay_generation,
                                               'snapshot': selection.snapshot, 'manifest': selection.manifest,
                                               'issued_ns': str(issued), 'expires_ns': str(expires)}, expires=expires)
                    return selection
            except Exception:
                self._close(parent, info)
                raise
            self._close(parent, info)
            return None

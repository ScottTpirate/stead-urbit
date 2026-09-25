"""Bounded read-only reuse of the harness's fixed, stopped fake seed.

Called only from the audit command factory while the shared native lock is
held. No CLI path override, previous audit import, or live-pier import exists.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SHIPS = ('zod', 'bus', 'nec', 'bud')
MARKER = {'format': 1, 'purpose': 'stead-urbit-four-fakes', 'ships': list(SHIPS)}
MAX_FILES, MAX_BYTES = 8192, 2 * 1024 ** 3


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate fake seed JSON key')
        result[key] = value
    return result


def private(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('Redirected fake seed path')
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Fake seed root must be an owned private directory')


def read(path, maximum=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid() or info.st_size > maximum):
            raise ValueError('Invalid bounded seed input')
        with os.fdopen(fd, 'rb', closefd=False) as source:
            value = source.read(maximum + 1)
        if len(value) > maximum:
            raise ValueError('Seed input grew beyond bound')
        return value
    finally:
        os.close(fd)


def tree(path, destination=None):
    """Hash the same canonical tree inventory as digests.tree_sha; copy once."""
    private(path)
    if destination is not None:
        destination.mkdir(mode=0o700)  # Exclusive: never overwrite a pier.
    entries, count, total = [], 0, 0
    for base, dirs, files in os.walk(path, followlinks=False):
        for name in sorted(dirs + files):
            count += 1
            if count > MAX_FILES:
                raise ValueError('Seed entry bound exceeded')
            item = Path(base) / name
            info = item.lstat()
            relative = item.relative_to(path)
            if info.st_uid != os.getuid():
                raise ValueError('Foreign-owned seed entry')
            if stat.S_ISDIR(info.st_mode):
                if destination is not None:
                    (destination / relative).mkdir(mode=0o700)
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('Seed links or special files are forbidden')
            total += info.st_size
            if total > MAX_BYTES:
                raise ValueError('Seed byte bound exceeded')
            fd = os.open(item, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            output = None
            try:
                current = os.fstat(fd)
                if ((current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
                        != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
                        or not stat.S_ISREG(current.st_mode) or current.st_nlink != 1):
                    raise ValueError('Seed changed during bounded read')
                if destination is not None:
                    output = (destination / relative).open('xb')
                digest, size = hashlib.sha256(), 0
                while chunk := os.read(fd, 65536):
                    size += len(chunk)
                    if size > info.st_size:
                        raise ValueError('Seed grew during copy')
                    digest.update(chunk)
                    if output is not None:
                        output.write(chunk)
                if size != info.st_size or os.fstat(fd).st_mtime_ns != info.st_mtime_ns:
                    raise ValueError('Seed changed during copy')
                entries.append((relative.as_posix(), digest.hexdigest()))
            finally:
                if output is not None:
                    output.close()
                os.close(fd)
    return {'sha256': hashlib.sha256(''.join(value + '  ' + name + '\n'
                       for name, value in sorted(entries, key=lambda row: Path(row[0]).parts)).encode()).hexdigest(),
            'files': len(entries), 'bytes': total}


def inventory(root, toolchain_sha):
    state = root / '.piers/fakes'
    for path in (root / '.piers', state, state / 'seed'):
        private(path)
    marker = read(state / '.stead-disposable.json')
    manifest = read(state / 'seed/manifest.json')
    marker_value = json.loads(marker, object_pairs_hook=unique)
    if (not isinstance(marker_value, dict) or type(marker_value.get('format')) is not int
            or marker_value != MARKER):
        raise ValueError('Wrong fake seed marker')
    data = json.loads(manifest, object_pairs_hook=unique)
    if not isinstance(data, dict):
        raise ValueError('Fake seed manifest must be an object')
    if (set(data) != {'format', 'toolchain_sha256', 'ships'}
            or type(data['format']) is not int or data['format'] != 1
            or data['toolchain_sha256'] != toolchain_sha or not isinstance(data['ships'], dict)
            or set(data['ships']) != set(SHIPS)
            or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v)
                   for v in data['ships'].values())):
        raise ValueError('Wrong fake seed manifest or toolchain')
    ships = {ship: tree(state / 'seed' / ship) for ship in SHIPS}
    if any(ships[ship]['sha256'] != data['ships'][ship] for ship in SHIPS):
        raise ValueError('Fake seed hash mismatch')
    return {'marker_sha256': hashlib.sha256(marker).hexdigest(),
            'manifest_sha256': hashlib.sha256(manifest).hexdigest(),
            'toolchain_sha256': toolchain_sha, 'ships': ships}


@contextmanager
def snapshot(root, inputs, toolchain_sha):
    """Hold the harness lifecycle lock through all audit execution and cleanup."""
    state = root / '.piers/fakes'
    seed = state / 'seed'
    for path in (root / '.piers', state, seed):
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError('Redirected fake seed ancestor')
    if not seed.exists() and not seed.is_symlink():
        yield {'mode': 'cold', 'reason': 'fixed stopped fake seed absent'}
        return
    for path in (root / '.piers', state, seed):
        private(path)
    lock = state / 'lifecycle.lock'
    fd = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError('Invalid fake lifecycle lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = inventory(root, toolchain_sha)
        copied = tree(seed / 'zod', inputs / 'seed-zod')
        if copied != before['ships']['zod'] or tree(inputs / 'seed-zod') != copied:
            raise ValueError('Copied fake seed mismatch')
        if inventory(root, toolchain_sha) != before:
            raise ValueError('Fake seed changed during snapshot')
        value = {'mode': 'verified-stopped-fake-seed', 'source': '.piers/fakes/seed/zod',
                 'before': before, 'copied': copied}
        yield value
        if inventory(root, toolchain_sha) != before or tree(inputs / 'seed-zod') != copied:
            raise ValueError('Read-only fake seed changed during audit')
    finally:
        os.close(fd)

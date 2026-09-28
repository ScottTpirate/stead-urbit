"""Bounded SDK artifact readback only; no jam decoding or native qualification.

The future controller must supply pins from its retained builder observations,
after stopping/reaping that builder. A manifest beside the artifacts is not a
trusted source of pins. Consume the returned bytes, never reopen input paths.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat

from package_sdk import held_parent, identity, open_directory, require

ARTIFACTS = frozenset({'sample.jam', 'stead-command-3.jam', 'stead-query-3.jam',
                       'stead-result-3.jam', 'stead-updates-3.jam'})
# New binary-transfer bounds, not changes to existing JSON/evaluator limits.
# Actual compiled sizes remain unmeasured; an excess must fail, never truncate.
MAX_ARTIFACT = 16 * 1024**2
MAX_TOTAL = 64 * 1024**2


def inventory(pins):
    require(isinstance(pins, dict) and set(pins) == ARTIFACTS, 'SDK artifact inventory differs')
    result = {}
    for name in sorted(ARTIFACTS):
        pin = pins[name]
        require(isinstance(pin, dict) and set(pin) == {'bytes', 'sha256'}, 'SDK artifact pin shape')
        size, digest = pin['bytes'], pin['sha256']
        require(type(size) is int and 0 < size <= MAX_ARTIFACT, 'SDK artifact byte bound')
        require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest),
                'SDK artifact digest shape')
        result[name] = (size, digest)
    require(sum(size for size, _ in result.values()) <= MAX_TOTAL, 'SDK artifact total byte bound')
    return result


def directory_entries(descriptor, owner_uid):
    info = os.fstat(descriptor)
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == owner_uid
            and stat.S_IMODE(info.st_mode) == 0o700, 'SDK artifact directory custody differs')
    seen = set()
    fresh = open_directory('.', dir_fd=descriptor)
    try:
        with os.scandir(fresh) as entries:
            for entry in entries:
                require(entry.name in ARTIFACTS and entry.name not in seen,
                        'Unexpected SDK artifact entry')
                seen.add(entry.name)
    finally:
        os.close(fresh)
    require(seen == ARTIFACTS, 'SDK artifact files are missing')


def read_file(descriptor, name, pin, owner_uid):
    child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                    dir_fd=descriptor)
    with os.fdopen(child, 'rb') as source:
        before = os.fstat(source.fileno())
        size, digest = pin
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_uid == owner_uid and stat.S_IMODE(before.st_mode) == 0o600
                and before.st_size == size, 'SDK artifact file custody or size differs')
        raw = source.read(size + 1)
        require(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest,
                'SDK artifact bytes differ')
        after = os.fstat(source.fileno())
        current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        def observed(info):
            return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
                    info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        require(observed(before) == observed(after) == observed(current),
                'SDK artifact changed during readback')
        return raw


def read_artifacts(root, directory, pins, *, owner_uid):
    """Return exactly five immutable byte strings matching external trusted pins.

    This helper cannot prove where pins came from, builder isolation/cleanup,
    canonical jam encoding, vase type, or behavior. Those are controller/native
    obligations; successful readback is not a consumer acceptance receipt.
    """
    require(type(owner_uid) is int and owner_uid >= 0, 'SDK artifact owner identity')
    expected = inventory(pins)  # Freeze pin values before any filesystem access.
    with held_parent(root, directory) as (parent, leaf, check_parent):
        descriptor = open_directory(leaf, dir_fd=parent)
        try:
            directory_entries(descriptor, owner_uid)
            result = {name: read_file(descriptor, name, pin, owner_uid)
                      for name, pin in expected.items()}
            directory_entries(descriptor, owner_uid)
            check_parent()
            current = open_directory(leaf, dir_fd=parent)
            try:
                require(identity(current) == identity(descriptor), 'SDK artifact directory changed')
            finally:
                os.close(current)
            return result
        finally:
            os.close(descriptor)

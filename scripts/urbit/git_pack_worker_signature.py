"""Sign the digest of an exact, previously prepared Git worker proof."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import tempfile

from execution_policy import directory_fd
from portable_code import private_directory
from portable_recovery import RecoveryError, require, same_entry, same_path, sha


DOMAIN = b'stead.git-pack-worker-attestation/1\0'
MAX_PROOF = 65_536
MAX_KEY = 4096
MAX_GENERATION = 2**64 - 1
SPKI_ED25519 = bytes.fromhex('302a300506032b6570032100')
OPENSSL = '/usr/bin/openssl'
ENV = {'LC_ALL': 'C', 'OPENSSL_CONF': '/dev/null'}


def message(proof: bytes, generation: int) -> bytes:
    require(type(generation) is int and 1 <= generation <= MAX_GENERATION, 'worker-signing-generation')
    require(isinstance(proof, bytes) and 0 < len(proof) <= MAX_PROOF, 'worker-signing-proof-bound')
    return DOMAIN + str(generation).encode('ascii') + b'\0' + sha(proof).encode('ascii')


def sign(proof: bytes, generation: int, key: Path) -> str:
    """The caller supplies the worker-owned unencrypted PEM Ed25519 key."""
    data = message(proof, generation)
    key = Path(key)
    try:
        with directory_fd(key.parent) as parent:
            owner = private_directory(parent)
            fd = os.open(key.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, 'rb') as source:
                info = os.fstat(source.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                        and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600
                        and 0 < info.st_size <= MAX_KEY, 'worker-signing-private-key')
                key_binding(key, parent, owner, source.fileno(), info)
                signature = sign_held(source.fileno(), data)
                key_binding(key, parent, owner, source.fileno(), info)
    except (OSError, subprocess.SubprocessError):
        raise RecoveryError('worker-signing-unavailable') from None
    return signature.hex()


def key_binding(path, parent, owner, fd, previous):
    current = os.fstat(fd)
    require(same_path(path.parent, owner) and same_entry(parent, path.name, previous)
            and current.st_ctime_ns == previous.st_ctime_ns and current.st_mtime_ns == previous.st_mtime_ns
            and current.st_size == previous.st_size and current.st_nlink == 1, 'worker-signing-key-changed')


def sign_held(key_fd, data):
    # No second key file is created. Both subprocesses only see the owned
    # descriptor through procfs, never a caller-supplied OpenSSL path or URI.
    key = f'/proc/self/fd/{key_fd}'
    with tempfile.TemporaryDirectory(prefix='stead-worker-signature-') as temporary:
        scratch = Path(temporary)
        fd = os.open(scratch / 'message', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
        options = {'cwd': scratch, 'stdin': subprocess.DEVNULL, 'stdout': subprocess.PIPE,
                   'stderr': subprocess.DEVNULL, 'env': ENV, 'timeout': 5, 'check': False,
                   'pass_fds': (key_fd,)}
        public = subprocess.run([OPENSSL, 'pkey', '-inform', 'PEM', '-in', key, '-passin', 'pass:',
                                 '-pubout', '-outform', 'DER'], **options)
        require(public.returncode == 0 and len(public.stdout) == len(SPKI_ED25519) + 32
                and public.stdout.startswith(SPKI_ED25519), 'worker-signing-key-type')
        result = subprocess.run([OPENSSL, 'pkeyutl', '-sign', '-rawin', '-keyform', 'PEM', '-inkey', key,
                                 '-passin', 'pass:', '-in', 'message'], **options)
    require(result.returncode == 0 and len(result.stdout) == 64, 'worker-signing-failed')
    return result.stdout

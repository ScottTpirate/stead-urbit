"""Byte hashes shared by the host and sandbox without host-path assumptions."""
import hashlib
import os
from pathlib import Path
import stat


def sha(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError('Hash input must be a regular file')
        return hashlib.file_digest(source, 'sha256').hexdigest()


def read_source(path, maximum=16 * 1024 * 1024):
    from execution_policy import directory_fd
    path = Path(path)
    with directory_fd(path.parent) as parent:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
                raise ValueError('Source must be a bounded singly linked regular file')
            raw = source.read(maximum + 1)
            if len(raw) > maximum:
                raise ValueError('Source exceeded bounded input size')
            return raw


def source_inventory(root, *, ignore_python_cache=True):
    """Bind all helper files; only interpreter-generated cache directories omit."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Source inventory requires a real directory')
    files, count, total = {}, 0, 0
    for base, directories, names in os.walk(root, followlinks=False):
        if ignore_python_cache:
            directories[:] = [name for name in directories if name != '__pycache__']
        for name in directories + names:
            count += 1
            if count > 8192:
                raise ValueError('Source inventory entry bound')
            path = Path(base) / name
            if path.is_symlink():
                raise ValueError('Redirected source inventory entry')
            if path.is_dir():
                continue
            raw = read_source(path)
            total += len(raw)
            if total > 64 * 1024 * 1024:
                raise ValueError('Source inventory byte bound')
            files[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
    if not files:
        raise ValueError('Source inventory is empty')
    return files


def tree_sha(root, *, source_links=False):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Hash root must be a real directory')
    entries = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink() and source_links:
            target = path.readlink()
            if target.is_absolute() or not path.resolve().is_relative_to(root.resolve()) or not path.exists():
                raise ValueError('Only pinned internal aliases are allowed in source')
            entries.append('symlink:' + str(target) + '  ' + path.relative_to(root).as_posix() + '\n')
            continue
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError(f'Unsupported link or special file in hashed tree: {path}')
        if path.is_file():
            entries.append(sha(path) + '  ' + path.relative_to(root).as_posix() + '\n')
    return hashlib.sha256(''.join(entries).encode()).hexdigest()


def source_sha(root):
    # Both native runners load eagerly with the supervisor. Bind their shared
    # modules too: a cached import must never acquire a newer file's identity.
    # Planning/contracts/Urgit programs are not part of this process closure.
    names = ('conn.py', 'digests.py', 'execution_policy.py', 'harness.py', 'namespace_check.py',
             'supervisor.py', 'toolchain.py', 'core_check.py', 'core_test.py', 'core_conn.py',
             'core_cases_v2.py', 'core_export.py', 'delivery_cases.py', 'delivery_suite.py',
             'qualification_cases.py', 'qualification_gate.py', 'native_transcript.py',
             'gall_schedule.py', 'gall_schedule_proof.py', 'skill_evaluation_support.py',
             'team_check.py', 'team_conn.py', 'native_install.py',
             'team_lifecycle.py', 'native_peer_fence.py', 'native_tls.py', 'owned_child.py')
    entries = [sha(root / name) + '  ' + name + '\n' for name in names]
    return hashlib.sha256(''.join(entries).encode()).hexdigest()

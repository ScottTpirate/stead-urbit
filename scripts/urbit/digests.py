"""Byte hashes shared by the host and sandbox without host-path assumptions."""
import hashlib
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


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
    entries = [sha(p) + '  ' + p.name + '\n' for p in sorted(root.glob('*.py'))]
    return hashlib.sha256(''.join(entries).encode()).hexdigest()

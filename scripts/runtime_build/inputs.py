"""Bind extracted compiler/source and dependency cache to reviewed archives."""
import hashlib
from pathlib import Path
import tarfile


def digest(stream):
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree(root, ignore_git=False):
    result = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if ignore_git and name.split('/')[0] == '.git': continue
        if path.is_symlink():
            assert path.resolve().is_relative_to(root.resolve()) and path.exists()
            result[name] = {'link': str(path.readlink())}
        elif path.is_file():
            with path.open('rb') as stream: result[name] = {'sha256': digest(stream)}
        else: assert path.is_dir()
        assert len(result) < 100000
    assert result
    return result


def archive(path):
    result = {}
    with tarfile.open(path) as source:
        members = source.getmembers()
        assert len(members) < 100000 and sum(m.size for m in members) < 1024 * 1024 * 1024
        prefix = members[0].name.split('/')[0]
        for member in members:
            parts = member.name.split('/')
            assert parts[0] == prefix and '..' not in parts
            name = '/'.join(parts[1:])
            if member.isdir(): continue
            assert name and name not in result
            if member.issym(): result[name] = {'link': member.linkname}
            else:
                assert member.isfile()
                with source.extractfile(member) as stream: result[name] = {'sha256': digest(stream)}
    return result


def verify():
    compiler = archive(Path('/inputs/zig-0.15.2.tar.xz'))
    source = archive(Path('/inputs/vere-4.6.tar.gz'))
    assert source['pkg/vere/newt.c']['sha256'] == 'f18f203e823ad64433e2fb57a5959189c6cdec624a2a1d448738ee8354e0a833'
    source['pkg/vere/newt.c'] = {'sha256': '7926e9b0f83387595ad65b689a56439c73c48b35ce0c9226ecce2001d27f8e0b'}
    assert tree(Path('/zig')) == compiler
    assert tree(Path('/source'), ignore_git=True) == source
    with Path('/source/.git/logs/HEAD').open('rb') as stream: source['.git/logs/HEAD'] = {'sha256': digest(stream)}
    return {'source': source, 'compiler': compiler}


def current():
    source = tree(Path('/source'), ignore_git=True)
    with Path('/source/.git/logs/HEAD').open('rb') as stream: source['.git/logs/HEAD'] = {'sha256': digest(stream)}
    return {'source': source, 'compiler': tree(Path('/zig'))}

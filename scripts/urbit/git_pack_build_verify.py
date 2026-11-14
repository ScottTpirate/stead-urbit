"""Verify one digest-pinned accepted-source archive without extracting it."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

from execution_policy import GuardError, directory_fd
import git_pack_build_source as source
import git_pack_store as store
from portable_code import private_directory, ref_name
from portable_recovery import OID, TOKEN, UUID, decoded, encoded, match, number, require, same_entry, same_path, sha, shape


PROTOCOL = 'stead.git-build-source-verification/1'
RECIPE = 'stead.build.verify-source-archive/1'
FIELDS = {'protocol', 'scope', 'snapshot', 'receipt', 'receipt_sha256', 'proposal_revision',
          'ref', 'commit', 'tree', 'archive', 'entries'}
ENTRY = {'path', 'mode', 'oid'}
FILE = ENTRY | {'bytes', 'sha256'}
BLOCK = 512
RECORD = 10_240
CHUNK = 65_536
MAX_SECONDS = 60


def _remaining(deadline):
    require(time.monotonic() < deadline, 'build-source-verification-deadline')


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


@contextmanager
def _held(directory, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                and not info.st_mode & 0o077 and 0 < info.st_size <= limit, 'build-source-verification-file')
        yield stream, info.st_size
        require(_identity(os.fstat(stream.fileno())) == _identity(info) and same_entry(directory, name, info),
                'build-source-verification-file-changed')


def _oid(value):
    return match(OID, value) and value != '0' * 40


def _meta(raw, expected):
    require(match(TOKEN, expected) and sha(raw) == expected, 'build-source-verification-input-digest')
    manifest = decoded(raw, source.MAX_MANIFEST)
    shape(manifest, FIELDS)
    require(manifest['protocol'] == source.PROTOCOL and raw == encoded(manifest), 'build-source-verification-schema')
    scope = manifest['scope']
    store.validate_scope(scope)
    ref_name(manifest['ref'], branch=True)
    require(scope['project_id'] == scope['repository_id'] and match(TOKEN, manifest['snapshot'])
            and _oid(manifest['commit']) and _oid(manifest['tree']) and type(manifest['proposal_revision']) is int
            and 1 <= manifest['proposal_revision'] <= 64, 'build-source-verification-source')
    receipt = manifest['receipt']
    shape(receipt, source.RECEIPT_FIELDS)
    number(receipt['generation'])
    require(receipt['protocol'] == 'stead.code/1' and receipt['status'] == 'merged'
            and all(match(UUID, receipt[key]) for key in ('request_id', 'proposal_id'))
            and receipt['snapshot'] == manifest['snapshot'] and sha(encoded(receipt)) == manifest['receipt_sha256'],
            'build-source-verification-receipt')
    archive = manifest['archive']
    shape(archive, {'sha256', 'bytes'})
    require(match(TOKEN, archive['sha256']) and type(archive['bytes']) is int
            and 0 < archive['bytes'] <= source.MAX_ARCHIVE, 'build-source-verification-archive')
    return manifest


def _entries(manifest):
    entries = manifest['entries']
    require(isinstance(entries, list) and len(entries) <= source.MAX_ENTRIES, 'build-source-verification-entries')
    by_directory = {'': []}
    seen = set()
    total = 0
    for row in entries:
        require(isinstance(row, dict) and isinstance(row.get('path'), str)
                and row.get('mode') in ('040000', '100644', '100755'), 'build-source-verification-entry')
        is_directory = row['mode'] == '040000'
        shape(row, ENTRY if is_directory else FILE)
        path, key = source._path(row['path'].encode('utf-8'))
        require(key not in seen and _oid(row['oid']), 'build-source-verification-entry')
        seen.add(key)
        parent, _, name = path.rpartition('/')
        require(parent in by_directory, 'build-source-verification-directory')
        by_directory[parent].append((name.encode('utf-8') + (b'/' if is_directory else b''), row))
        if is_directory:
            by_directory[path] = []
        else:
            size = row['bytes']
            require(type(size) is int and 0 <= size <= store.MAX_OBJECT and match(TOKEN, row['sha256']),
                    'build-source-verification-entry')
            total += size
            require(total <= source.MAX_PAYLOAD, 'build-source-verification-payload')
    return by_directory, total


def _verify_tree(directory, by_directory, order, deadline):
    _remaining(deadline)
    content = bytearray()
    for name, row in sorted(by_directory[directory], key=lambda item: item[0]):
        order.append(row)
        is_directory = row['mode'] == '040000'
        mode = b'40000' if is_directory else row['mode'].encode('ascii')
        if is_directory:
            require(row['oid'] == _verify_tree(row['path'], by_directory, order, deadline),
                    'build-source-verification-tree')
        content.extend(mode + b' ' + name.removesuffix(b'/') + b'\0' + bytes.fromhex(row['oid']))
    tree = hashlib.sha1(f'tree {len(content)}\0'.encode('ascii'), usedforsecurity=False)
    tree.update(content)
    return tree.hexdigest()


class _Archive:
    def __init__(self, stream, deadline):
        self.stream = stream
        self.deadline = deadline
        self.digest = hashlib.sha256()
        self.count = 0

    def read(self, count):
        _remaining(self.deadline)
        block = self.stream.read(count)
        require(len(block) == count, 'build-source-verification-tar-length')
        self.digest.update(block)
        self.count += count
        return block


def _verify_tar(stream, length, manifest, deadline):
    archive = _Archive(stream, deadline)
    files = 0
    for row in manifest['entries']:
        is_directory = row['mode'] == '040000'
        info = tarfile.TarInfo(row['path'])
        info.type = tarfile.DIRTYPE if is_directory else tarfile.REGTYPE
        info.mode = 0o755 if row['mode'] in ('040000', '100755') else 0o644
        info.size = row.get('bytes', 0)
        # Check the complete wire representation instead of accepting permissive
        # tar aliases, extra PAX extensions or unbounded declared header sizes.
        header = info.tobuf(tarfile.PAX_FORMAT, encoding='utf-8')
        require(archive.read(len(header)) == header, 'build-source-verification-tar-header')
        if not is_directory:
            size = info.size
            oid = hashlib.sha1(f'blob {size}\0'.encode('ascii'), usedforsecurity=False)
            digest = hashlib.sha256()
            while size:
                block = archive.read(min(CHUNK, size))
                size -= len(block)
                oid.update(block)
                digest.update(block)
            require(oid.hexdigest() == row['oid'] and digest.hexdigest() == row['sha256'],
                    'build-source-verification-blob')
            files += 1
            padding = -info.size % BLOCK
            require(archive.read(padding) == bytes(padding), 'build-source-verification-tar-padding')
    end = 2 * BLOCK
    end += -(archive.count + end) % RECORD
    require(archive.read(end) == bytes(end) and archive.count == length and stream.read(1) == b''
            and archive.digest.hexdigest() == manifest['archive']['sha256'], 'build-source-verification-tar-digest')
    return files


def verify(path, expected):
    """Return bounded integrity evidence under an independently supplied source pin."""
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'build-source-verification-path')
    deadline = time.monotonic() + MAX_SECONDS
    with directory_fd(path) as directory:
        original = private_directory(directory)
        with _held(directory, source.MANIFEST, source.MAX_MANIFEST) as (index, length), \
                _held(directory, source.ARCHIVE, source.MAX_ARCHIVE) as (archive, archive_bytes):
            raw = index.read(length + 1)
            require(len(raw) == length, 'build-source-verification-file-changed')
            manifest = _meta(raw, expected)
            require(archive_bytes == manifest['archive']['bytes'], 'build-source-verification-tar-length')
            by_directory, total = _entries(manifest)
            order = []
            require(_verify_tree('', by_directory, order, deadline) == manifest['tree']
                    and order == manifest['entries'], 'build-source-verification-tree')
            files = _verify_tar(archive, archive_bytes, manifest, deadline)
        require(same_path(path, original), 'build-source-verification-file-changed')
    _remaining(deadline)
    return {'protocol': PROTOCOL, 'recipe': RECIPE, 'status': 'verified', 'source_manifest_sha256': expected,
            **{key: manifest[key] for key in ('scope', 'snapshot', 'commit', 'tree', 'ref', 'receipt_sha256',
                                               'proposal_revision', 'archive')},
            **{key: manifest['receipt'][key] for key in ('request_id', 'proposal_id', 'generation')},
            'entry_count': len(order), 'file_count': files, 'file_bytes': total}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Private accepted-source export directory')
    parser.add_argument('--sha256', required=True, help='Independently trusted source.json SHA-256')
    args = parser.parse_args(argv)
    try:
        result = verify(args.source, args.sha256)
    except (OSError, ValueError, GuardError):
        print('Accepted Git source verification failed.', file=sys.stderr)
        return 1
    print(encoded(result).decode('utf-8'), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Export a deterministic source tree from one exact, authorized Git merge.

The caller authenticates the existing Home promotion response and binds its
proposal revision separately. A fresh caller-supplied check precedes delivery.
Only bounded, config-isolated stock Git plumbing reads the verified pack.
Project code, Git checkout filters and archive attributes never run.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import tarfile
import tempfile
import time
import unicodedata

from execution_policy import directory_fd
import git_pack_projection as projection
import git_pack_store as store
from portable_code import private_directory, publish_directory, ref_name, staged_repository, sync_tree
from portable_recovery import OID, UUID, RecoveryError, encoded, match, number, require, same_entry, same_path, sha, shape


PROTOCOL = 'stead.git-build-source/1'
ARCHIVE = 'source.tar'
MANIFEST = 'source.json'
MAX_ENTRIES = 8192
MAX_PAYLOAD = 128 * 1024 * 1024
MAX_PATH = 1024
MAX_MANIFEST = 12 * 1024 * 1024
MAX_ARCHIVE = MAX_PAYLOAD + MAX_ENTRIES * 4096 + 10_240
MODE = {b'040000': ('tree', 0o755), b'100644': ('blob', 0o644), b'100755': ('blob', 0o755)}
RECEIPT_FIELDS = {'protocol', 'status', 'request_id', 'proposal_id', 'snapshot', 'generation'}
ENTRY = re.compile(rb'([0-7]{6}) (blob|tree) ([0-9a-f]{40}) +(-|[0-9]{1,8})\t(.+)')
DEVICE = re.compile(r'(?i)(?:aux|con|nul|prn|com[1-9]|lpt[1-9])(?:\..*)?')


@dataclass(frozen=True)
class Entry:
    path: str
    mode: bytes
    oid: bytes
    size: int


def _path(raw):
    require(0 < len(raw) <= MAX_PATH, 'build-source-path')
    try:
        value = raw.decode('utf-8')
    except UnicodeError:
        raise RecoveryError('build-source-path') from None
    parts = value.split('/')
    require(len(parts) <= 32 and all(0 < len(part.encode('utf-8')) <= 255 for part in parts), 'build-source-path')
    canonical = [unicodedata.normalize('NFKC', part).casefold() for part in parts]
    for part in canonical:
        require(part not in ('.', '..', '.git') and not part.endswith((' ', '.')) and DEVICE.fullmatch(part) is None
                and not any(char in '/\\:<>"|?*' or unicodedata.category(char) in ('Cc', 'Cf') for char in part),
                'build-source-path')
    return value, '/'.join(canonical)


def _tree(repo, commit):
    tree = repo.run('rev-parse', '--verify', commit + '^{tree}', limit=41)
    require(re.fullmatch(rb'[0-9a-f]{40}\n', tree) is not None, 'build-source-tree')
    rows = repo.run('ls-tree', '-rtlz', '--full-tree', tree[:-1], limit=MAX_ENTRIES * (MAX_PATH + 76))
    require(not rows or rows.endswith(b'\0'), 'build-source-tree')
    raw_entries = rows[:-1].split(b'\0', MAX_ENTRIES) if rows else []
    require(len(raw_entries) <= MAX_ENTRIES, 'build-source-entry-bound')
    entries, paths, total = [], set(), 0
    for raw in raw_entries:
        found = ENTRY.fullmatch(raw)
        require(found is not None, 'build-source-entry')
        mode, kind, oid, size, address = found.groups()
        require(mode in MODE and kind.decode('ascii') == MODE[mode][0] and (kind == b'tree') == (size == b'-'),
                'build-source-entry')
        path, key = _path(address)
        require(key not in paths, 'build-source-path-collision')
        paths.add(key)
        count = 0 if kind == b'tree' else int(size)
        require(count <= store.MAX_OBJECT, 'build-source-blob-bound')
        total += count
        require(total <= MAX_PAYLOAD, 'build-source-byte-bound')
        entries.append(Entry(path, mode, oid, count))
    return tree[:-1].decode('ascii'), entries, total


class _Blob:
    def __init__(self, source, size):
        self.source = source
        self.strong = hashlib.sha256()
        self.oid = hashlib.sha1(f'blob {size}\0'.encode('ascii'), usedforsecurity=False)

    def read(self, count):
        raw = self.source.read(count)
        self.strong.update(raw)
        self.oid.update(raw)
        return raw


def _archive(repo, output, entries, total):
    files = [entry for entry in entries if entry.mode != b'040000']
    wanted = b''.join(entry.oid + b'\n' for entry in files)
    with tempfile.TemporaryFile() as batch:
        if wanted:
            repo.run_to(batch, 'cat-file', '--batch', data=wanted, limit=total + 64 * len(files))
        batch.seek(0)
        with tarfile.open(fileobj=output, mode='w|', format=tarfile.PAX_FORMAT, encoding='utf-8') as archive:
            for entry in entries:
                projection._remaining(repo.deadline)
                info = tarfile.TarInfo(entry.path)
                info.mode = MODE[entry.mode][1]
                info.size = entry.size
                kind = MODE[entry.mode][0]
                row = {'path': entry.path, 'mode': entry.mode.decode('ascii'), 'oid': entry.oid.decode('ascii')}
                if kind == 'tree':
                    info.type = tarfile.DIRTYPE
                    archive.addfile(info)
                else:
                    header = b'%s blob %d\n' % (entry.oid, entry.size)
                    require(batch.readline(64) == header, 'build-source-blob-header')
                    blob = _Blob(batch, entry.size)
                    archive.addfile(info, blob)
                    require(blob.oid.hexdigest().encode('ascii') == entry.oid and batch.read(1) == b'\n',
                            'build-source-blob-integrity')
                    row.update(bytes=entry.size, sha256=blob.strong.hexdigest())
                yield row
        require(batch.read(1) == b'', 'build-source-blob-trailing')


def export(storage, snapshot, expected_manifest, accepted, git, destination, *, ref, commit, proposal_revision,
           authorize, deadline):
    """Write a private manifest and TAR after exact stock and authority checks.

    ``accepted`` is the authenticated Home external merge response. The caller
    supplies its exact reviewed proposal revision and must reauthorize the
    same receipt and revision in ``authorize()``. The result is source
    evidence only. Output uses fixed names and no filesystem extraction.
    """
    require(isinstance(expected_manifest, dict) and 'scope' in expected_manifest, 'build-source-snapshot')
    scope = expected_manifest['scope']
    manifest = projection.validate_manifest(snapshot, expected_manifest, scope)
    ref_name(ref, branch=True)
    require(ref == expected_manifest['head'] and match(OID, commit) and commit != '0' * 40
            and commit == expected_manifest['refs'][ref], 'build-source-ref')
    shape(accepted, RECEIPT_FIELDS)
    number(accepted['generation'])
    require(accepted['protocol'] == 'stead.code/1' and accepted['status'] == 'merged'
            and all(match(UUID, accepted[key]) for key in ('request_id', 'proposal_id'))
            and accepted['snapshot'] == snapshot and type(proposal_revision) is int and 1 <= proposal_revision <= 64
            and callable(authorize), 'build-source-receipt')
    git, storage, destination = map(Path, (git, storage, destination))
    require(all(path.is_absolute() and '..' not in path.parts for path in (git, storage, destination))
            and bool(destination.name), 'build-source-output')
    deadline = projection._deadline(deadline)
    projection._remaining(deadline)
    require(authorize() is True, 'build-source-authorization-changed')

    with directory_fd(destination.parent) as parent:
        output_parent = private_directory(parent)
        require(not os.path.lexists(f'/proc/self/fd/{parent}/{destination.name}'), 'build-source-exists')
        with staged_repository(parent, git, deadline=deadline, command_prefix=store.GIT_LIMITS) as (name, held, repo):
            with store.repository_directory(storage, scope) as (directory, check_store), \
                    store.open_snapshot(directory, snapshot) as source:
                value = store.read_manifest(source, snapshot, scope)
                require(manifest == encoded(value), 'build-source-snapshot')
                _, inventory = store.verify_pack(repo, source, store.PACK_NAME, value['pack_sha256'], value['refs'], ref)
                require(all(type(value[key]) is type(item) and value[key] == item for key, item in inventory.items()),
                        'build-source-snapshot')
                check_store()
            tree, entries, total = _tree(repo, commit)
            payload = Path(repo.path) / 'payload'
            payload.mkdir(mode=0o700)
            with (payload / ARCHIVE).open('x+b') as output:
                os.fchmod(output.fileno(), 0o600)
                rows = list(_archive(repo, output, entries, total))
                length = output.tell()
                require(length <= MAX_ARCHIVE, 'build-source-archive-bound')
                output.seek(0)
                digest = hashlib.file_digest(output, 'sha256').hexdigest()
            source_manifest = {'protocol': PROTOCOL, 'scope': scope, 'snapshot': snapshot,
                               'receipt': accepted, 'receipt_sha256': sha(encoded(accepted)),
                               'proposal_revision': proposal_revision, 'ref': ref, 'commit': commit, 'tree': tree,
                               'archive': {'sha256': digest, 'bytes': length}, 'entries': rows}
            raw = encoded(source_manifest)
            require(len(raw) <= MAX_MANIFEST, 'build-source-manifest-bound')
            with (payload / MANIFEST).open('xb') as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(raw)
            sync_tree(repo)
            projection._remaining(deadline)
            require(authorize() is True, 'build-source-authorization-changed')
            require(same_entry(parent, name, held) and same_path(destination.parent, output_parent),
                    'build-source-output-changed')
            projection._remaining(deadline)
            publish_directory(parent, name + '/payload', destination.name)
            os.fsync(parent)
            require(same_path(destination.parent, output_parent), 'build-source-output-changed')
    return sha(raw)

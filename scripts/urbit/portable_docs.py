#!/usr/bin/env python3
"""Archive and recover an already authorized Docs Git snapshot offline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from selectors import DefaultSelector, EVENT_READ
import shutil
import stat
import subprocess
import tempfile
import time

from execution_policy import directory_fd
from team_git import KINDS, OID, UUID, document_edges, materialize, require, unique

FORMAT = 'stead.docs-archive/1'
MAX_ARCHIVE = 20 * 1024 * 1024
MAX_OBJECT_BYTES = 8 * 1024 * 1024
MAX_OBJECTS = 512
MAX_BODY = 65536
SHA256 = re.compile(r'[0-9a-f]{64}')
SIZE = re.compile(rb'(0|[1-9][0-9]{0,4})\n')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode() + b'\n'


def validate_scope(project, container, head):
    require(isinstance(project, str) and UUID.fullmatch(project)
            and isinstance(container, str) and UUID.fullmatch(container)
            and isinstance(head, str) and OID.fullmatch(head), 'Expected a project, container and exact SHA-1 head')


def git_read(binary, repository, *args):
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1',
           'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0',
           'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': ''}
    argv = [binary, '--git-dir', str(repository), *args]
    with subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env) as git:
        deadline = time.monotonic() + 15
        output = bytearray()
        try:
            with DefaultSelector() as ready:
                ready.register(git.stdout, EVENT_READ)
                while True:
                    require(ready.select(max(0, deadline - time.monotonic())), 'Git snapshot read timed out')
                    chunk = os.read(git.stdout.fileno(), min(8192, MAX_BODY + 1 - len(output)))
                    if not chunk:
                        break
                    output.extend(chunk)
                    require(len(output) <= MAX_BODY, 'Git snapshot output exceeded bounds')
            require(git.wait(timeout=max(0, deadline - time.monotonic())) == 0, 'Git snapshot read failed')
        finally:
            if git.poll() is None:
                git.kill()
                git.wait()
    return bytes(output)


def verified_object(oid, kind, body):
    return hashlib.sha1(f'{kind} {len(body)}\0'.encode() + body).hexdigest() == oid


def collect(repository, project, container, head, binary):
    validate_scope(project, container, head)
    with directory_fd(repository):
        require(git_read(binary, repository, 'rev-parse', '--is-bare-repository') == b'true\n'
                and git_read(binary, repository, 'rev-parse', '--show-object-format') == b'sha1\n',
                'Expected a bare SHA-1 Docs export')
        require(git_read(binary, repository, 'rev-parse', '--verify', 'HEAD') == head.encode() + b'\n',
                'Git export HEAD differs from the selected snapshot')
        require(not (repository / 'objects/info/alternates').exists(), 'Git alternates are outside the export profile')
        objects, total, commits = {}, 0, 0
        pending = [(head, 'commit')]
        while pending:
            oid, kind = pending.pop()
            require(OID.fullmatch(oid), 'Malformed Git edge')
            if oid in objects:
                require(objects[oid]['kind'] == kind, 'Contradictory Git edge')
                continue
            require(len(objects) < MAX_OBJECTS, 'Git object count bound')
            actual = git_read(binary, repository, 'cat-file', '-t', oid)
            require(actual == kind.encode() + b'\n', 'Git object type differs')
            size = git_read(binary, repository, 'cat-file', '-s', oid)
            require(SIZE.fullmatch(size) and int(size) <= MAX_BODY, 'Git body size bound')
            total += int(size)
            commits += kind == 'commit'
            require(total <= MAX_OBJECT_BYTES and commits <= 128, 'Git snapshot size or history bound')
            body = git_read(binary, repository, 'cat-file', kind, oid)
            require(len(body) == int(size) and verified_object(oid, kind, body), 'Git object identity differs')
            objects[oid] = {'kind': kind, 'byte_length': len(body), 'hex': body.hex()}
            pending.extend(document_edges(kind, body))
    return {'format': FORMAT, 'project_id': project, 'container_id': container, 'head': head, 'objects': objects}


def validate(value):
    require(isinstance(value, dict) and set(value) == {'format', 'project_id', 'container_id', 'head', 'objects'}
            and value['format'] == FORMAT, 'Unsupported Docs archive format')
    validate_scope(value['project_id'], value['container_id'], value['head'])
    objects = value['objects']
    require(isinstance(objects, dict) and 0 < len(objects) <= MAX_OBJECTS, 'Git object count bound')
    total = 0
    for oid, row in objects.items():
        require(OID.fullmatch(oid) and isinstance(row, dict) and set(row) == {'kind', 'byte_length', 'hex'},
                'Invalid Git object inventory')
        kind, size, encoded = row['kind'], row['byte_length'], row['hex']
        require(isinstance(kind, str) and kind in KINDS and type(size) is int and 0 <= size <= MAX_BODY
                and isinstance(encoded, str) and len(encoded) == size * 2 and re.fullmatch(r'[0-9a-f]*', encoded),
                'Invalid Git object body')
        total += size
        require(total <= MAX_OBJECT_BYTES and verified_object(oid, kind, bytes.fromhex(encoded)),
                'Git object digest differs or total size exceeded')
    return value


def recover(value, directory, binary):
    validate(value)
    project, container, head, objects = (value[k] for k in ('project_id', 'container_id', 'head', 'objects'))

    def read(oid):
        if oid is None:
            return {'protocol': 'stead.fixture-git/3', 'project_id': project, 'container_id': container,
                    'snapshot_commit_oid': head, 'objects': {key: row['kind'] for key, row in objects.items()}}
        row = objects[oid]
        return {'protocol': 'stead.fixture-git-object/3', 'snapshot_commit_oid': head, 'oid': oid,
                'kind': row['kind'], 'byte_length': str(row['byte_length']), 'hex': row['hex']}

    return materialize(read, directory, project, container, head, git_binary=binary)


def private_root(parent):
    with directory_fd(parent) as descriptor:
        info = os.fstat(descriptor)
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'Use an owned mode-0700 directory')


def read_archive(path, expected):
    require(SHA256.fullmatch(expected), 'An independently recorded SHA-256 is required')
    with directory_fd(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and not info.st_mode & 0o077 and 0 < info.st_size <= MAX_ARCHIVE,
                    'Expected a bounded private archive file')
            raw = stream.read(MAX_ARCHIVE + 1)
    require(len(raw) == info.st_size and hashlib.sha256(raw).hexdigest() == expected, 'Archive SHA-256 differs')
    value = validate(json.loads(raw, object_pairs_hook=unique))
    require(raw == canonical(value), 'Archive bytes are not canonical')
    return value


def write_archive(path, value):
    private_root(path.parent)
    raw = canonical(value)
    require(len(raw) <= MAX_ARCHIVE, 'Archive byte bound')
    with directory_fd(path.parent) as parent:
        temporary = '.archive-' + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.fsync(parent)
        finally:
            os.unlink(temporary, dir_fd=parent)
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    create = actions.add_parser('create')
    for arg in ('repository', 'archive'):
        create.add_argument(arg, type=Path)
    for arg in ('project', 'container', 'head'):
        create.add_argument('--' + arg, required=True)
    restore = actions.add_parser('restore')
    restore.add_argument('archive', type=Path)
    restore.add_argument('destination', type=Path, help='Private directory for a new bare repository')
    restore.add_argument('--sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    binary = shutil.which('git')
    require(binary and Path(binary).is_absolute(), 'Stock Git is required')
    if args.action == 'create':
        value = collect(args.repository.absolute(), args.project, args.container, args.head, binary)
        private_root(args.archive.parent)
        with tempfile.TemporaryDirectory(prefix='.docs-check-', dir=args.archive.parent) as stage:
            recover(value, Path(stage) / 'repo', binary)
        print(json.dumps({'sha256': write_archive(args.archive, value), 'head': value['head']}))
    else:
        value = read_archive(args.archive, args.sha256)
        private_root(args.destination)
        stage = Path(tempfile.mkdtemp(prefix='docs-recovery-', dir=args.destination))
        try:
            repo = stage / 'repo'
            recovered = recover(value, repo, binary)
        except BaseException:
            shutil.rmtree(stage)
            raise
        print(json.dumps({'repository': str(repo), 'head': recovered['head'],
                          'objects': len(recovered['objects']), 'git_version': recovered['git_version']}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit('Docs archive: ' + str(error)) from None

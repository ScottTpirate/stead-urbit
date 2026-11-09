#!/usr/bin/env python3
"""Archive and restore the reachable history of an authorized bare Code clone."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import ctypes
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
import sys
import tempfile
import time

from execution_policy import GuardError, directory_fd
from portable_recovery import (OID, TOKEN, UUID, RecoveryError, decoded, encoded,
                               match, require, same_entry, same_path, sha, shape)

FORMAT = 'stead.code-archive/1'
KINDS = {'blob', 'commit', 'tree', 'tag'}
MAX_REFS = 64
MAX_REF_BYTES = 1024
MAX_OBJECTS = 512
MAX_OBJECT_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE = 18 * 1024 * 1024
MAX_GIT_TIME = 45
MAX_SOURCE_ENTRIES = 4096
HEX = re.compile(r'(?:[0-9a-f]{2})*')
LOSSES = [
    'Only objects reachable from the exported branch and tag refs are retained.',
    'Home grants, branch protection, acceptance receipts, reviews, builds and credentials are omitted.',
    'The project ID is an operator label, not an attestation or a grant of authority.',
]


def private_directory(fd):
    info = os.fstat(fd)
    require(info.st_uid == os.getuid() and not info.st_mode & 0o077, 'private-directory-required')
    return info


def read_file(parent, name, limit, *, private=False):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_nlink == 1 and info.st_size <= limit, 'file-boundary')
        require(not private or not info.st_mode & 0o077, 'private-file-required')
        raw = stream.read(limit + 1)
        require(len(raw) == info.st_size and same_entry(parent, name, info), 'file-changed')
    return raw


class Git:
    """Use Git plumbing with bounded output and without inherited config or I/O."""
    def __init__(self, binary, repository, *, deadline=None):
        self.binary = binary
        self.repository = repository
        self.path = f'/proc/self/fd/{repository}'
        self.deadline = time.monotonic() + MAX_GIT_TIME
        if deadline is not None:
            self.deadline = min(self.deadline, deadline)

    def run(self, *args, data=None, limit=8192, read_config=False):
        env = {'PATH': '/usr/bin:/bin', 'HOME': '/', 'LANG': 'C.UTF-8',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
               'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_OPTIONAL_LOCKS': '0',
               'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': ''}
        location = [] if read_config else ['--git-dir', self.path]
        argv = [self.binary, *location, '-c', 'core.hooksPath=/dev/null',
                '-c', 'core.fsmonitor=false', *args]
        with (tempfile.TemporaryFile() if data is not None else nullcontext()) as input_file:
            if data is not None:
                input_file.write(data)
                input_file.seek(0)
            require(time.monotonic() < self.deadline, 'git-timeout')
            with subprocess.Popen(argv, stdin=input_file if data is not None else subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  env=env, cwd='/', pass_fds=(self.repository,)) as child:
                output = bytearray()
                try:
                    with DefaultSelector() as ready:
                        ready.register(child.stdout, EVENT_READ)
                        while True:
                            require(ready.select(max(0, self.deadline - time.monotonic())), 'git-timeout')
                            chunk = os.read(child.stdout.fileno(), min(65536, limit + 1 - len(output)))
                            if not chunk:
                                break
                            output.extend(chunk)
                            require(len(output) <= limit, 'git-output-bound')
                    require(child.wait(timeout=max(0, self.deadline - time.monotonic())) == 0,
                            'git-verification-failed')
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait()
        return bytes(output)


def ref_name(value, *, branch=False):
    require(isinstance(value, str) and 0 < len(value) <= MAX_REF_BYTES * 2
            and match(HEX, value), 'ref-name')
    name = bytes.fromhex(value)
    prefixes = (b'refs/heads/',) if branch else (b'refs/heads/', b'refs/tags/')
    require(name.startswith(prefixes) and len(name.split(b'/', 2)[-1]) > 0
            and all(byte > 32 and byte != 127 for byte in name), 'ref-name')
    return name


def validate(value):
    shape(value, {'format', 'project_id', 'head', 'refs', 'objects', 'losses'})
    require(value['format'] == FORMAT and match(UUID, value['project_id'])
            and value['losses'] == LOSSES, 'archive-format')
    refs, objects, head = (value[key] for key in ('refs', 'objects', 'head'))
    require(isinstance(refs, dict) and len(refs) <= MAX_REFS
            and isinstance(objects, dict) and len(objects) <= MAX_OBJECTS, 'inventory-bound')
    total = 0
    for oid, row in objects.items():
        shape(row, {'kind', 'bytes_hex'})
        kind, raw = row['kind'], row['bytes_hex']
        require(match(OID, oid) and isinstance(kind, str) and kind in KINDS
                and isinstance(raw, str) and len(raw) <= MAX_OBJECT_BYTES * 2
                and match(HEX, raw), 'object-shape')
        body = bytes.fromhex(raw)
        total += len(body)
        require(total <= MAX_TOTAL_BYTES, 'object-byte-bound')
        require(hashlib.sha1(f'{kind} {len(body)}\0'.encode() + body).hexdigest() == oid, 'object-digest')
    for ref, oid in refs.items():
        name = ref_name(ref)
        require(match(OID, oid) and oid in objects
                and (not name.startswith(b'refs/heads/') or objects[oid]['kind'] == 'commit'),
                'ref-object')
    if isinstance(head, dict) and 'name_hex' in head:
        shape(head, {'name_hex'})
        ref_name(head['name_hex'], branch=True)
    else:
        shape(head, {'oid'})
        require(match(OID, head['oid']) and any(
            oid == head['oid'] and ref_name(ref).startswith(b'refs/heads/')
            for ref, oid in refs.items()), 'detached-head-outside-branch-tips')
    return value


def observed_refs(git):
    out = git.run('for-each-ref', '--format=%(refname)%00%(objectname)%00%(symref)',
                  limit=MAX_REFS * (MAX_REF_BYTES + 45))
    refs = {}
    for row in out.split(b'\n')[:-1]:
        parts = row.split(b'\0')
        require(len(parts) == 3 and not parts[2] and len(refs) < MAX_REFS, 'ref-inventory')
        name, oid, _ = parts
        ref = name.hex()
        require(ref_name(ref) == name and ref not in refs and re.fullmatch(rb'[a-f0-9]{40}', oid),
                'ref-inventory')
        refs[ref] = oid.decode('ascii')
    require(not out or out.endswith(b'\n'), 'ref-inventory')
    raw = read_file(git.repository, 'HEAD', MAX_REF_BYTES + 7)
    require(raw.endswith(b'\n'), 'head-shape')
    if raw.startswith(b'ref: '):
        name = raw[5:-1].hex()
        ref_name(name, branch=True)
        head = {'name_hex': name}
    else:
        require(re.fullmatch(rb'[a-f0-9]{40}\n', raw), 'head-shape')
        head = {'oid': raw[:-1].decode('ascii')}
    return refs, head


def reachable(git, refs):
    if not refs:
        return set()
    # Root only at the captured refs, never reflogs, all local objects or an
    # ambient revision expression. This also enumerates annotated tag objects.
    data = ''.join(oid + '\n' for oid in sorted(set(refs.values()))).encode('ascii')
    out = git.run('rev-list', '--objects', '--no-object-names', '--stdin',
                  data=data, limit=MAX_OBJECTS * 41)
    require(re.fullmatch(rb'(?:[0-9a-f]{40}\n)+', out), 'reachable-graph')
    objects = set(out.decode('ascii').splitlines())
    require(0 < len(objects) <= MAX_OBJECTS, 'object-inventory')
    return objects


def source_layout(git):
    # The exported source is the operator's freshly cloned, private
    # repository. Reject external stores and redirected ref/object files.
    entries = 0

    def check(info, kind):
        require(kind(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o022,
                'external-source-state')

    for name in ('objects', 'refs', 'info'):
        try:
            info = os.stat(name, dir_fd=git.repository, follow_symlinks=False)
        except FileNotFoundError:
            if name == 'info':
                continue
            raise
        check(info, stat.S_ISDIR)
        for _, directories, files, directory in os.fwalk(name, dir_fd=git.repository):
            entries += len(directories) + len(files)
            require(entries <= MAX_SOURCE_ENTRIES, 'source-entry-bound')
            for part in directories:
                check(os.stat(part, dir_fd=directory, follow_symlinks=False), stat.S_ISDIR)
            for part in files:
                info = os.stat(part, dir_fd=directory, follow_symlinks=False)
                check(info, stat.S_ISREG)
                require(info.st_nlink == 1, 'external-source-state')
    if os.path.lexists(f'{git.path}/packed-refs'):
        read_file(git.repository, 'packed-refs', MAX_REFS * (MAX_REF_BYTES + 100))


def source_guard(git):
    # A fresh stock bare clone has a local config but needs no includes,
    # external object database, replace objects, shallow state or extensions.
    config = read_file(git.repository, 'config', 8192)
    for name in ('objects/info/alternates', 'objects/info/http-alternates', 'shallow',
                 'info/grafts', 'commondir', 'config.worktree'):
        require(not os.path.lexists(f'{git.path}/{name}'), 'external-source-state')
    settings = git.run('config', '--file', f'{git.path}/config', '--no-includes',
                       '--null', '--list', read_config=True)
    for setting in settings.split(b'\0')[:-1]:
        key = setting.partition(b'\n')[0]
        require(key in {b'core.repositoryformatversion', b'core.filemode', b'core.bare',
                        b'core.logallrefupdates', b'core.symlinks', b'core.ignorecase',
                        b'core.precomposeunicode'} or
                re.fullmatch(rb'remote\.[^.\0\n]+\.(?:url|fetch|mirror|tagopt)', key),
                'unsupported-source-config')
    require(config == read_file(git.repository, 'config', 8192), 'source-config-changed')
    require(git.run('rev-parse', '--is-bare-repository', '--show-object-format')
            == b'true\nsha1\n', 'bare-sha1-required')
    return config


def collect(repository, project, binary, *, deadline=None):
    require(match(UUID, project), 'project-id')
    with directory_fd(repository) as fd:
        private_directory(fd)
        git = Git(binary, fd, deadline=deadline)
        source_layout(git)
        config = source_guard(git)
        refs, head = observed_refs(git)
        objects = {}
        total = 0
        for oid in sorted(reachable(git, refs)):
            kind = git.run('cat-file', '-t', oid, limit=8).strip().decode('ascii')
            size = git.run('cat-file', '-s', oid, limit=16)
            require(kind in KINDS and re.fullmatch(rb'(?:0|[1-9][0-9]{0,6})\n', size), 'object-shape')
            count = int(size)
            total += count
            require(count <= MAX_OBJECT_BYTES and total <= MAX_TOTAL_BYTES, 'object-byte-bound')
            body = git.run('cat-file', kind, oid, limit=count)
            require(len(body) == count, 'object-size')
            objects[oid] = {'kind': kind, 'bytes_hex': body.hex()}
        source_layout(git)
        require(observed_refs(git) == (refs, head) and source_guard(git) == config, 'source-snapshot-changed')
    return validate({'format': FORMAT, 'project_id': project, 'refs': refs, 'head': head,
                     'objects': objects, 'losses': LOSSES})


def materialize(value, git):
    git.run('init', '--bare', '--template=', '--object-format=sha1')
    for oid, row in sorted(value['objects'].items()):
        stored = git.run('hash-object', '-w', '-t', row['kind'], '--stdin',
                         data=bytes.fromhex(row['bytes_hex']))
        require(stored == oid.encode('ascii') + b'\n', 'stock-object-identity')
    refs = value['refs']
    commands = []
    for ref, oid in sorted(refs.items()):
        name = ref_name(ref)
        git.run('check-ref-format', name)
        commands.append(b'create ' + name + b' ' + oid.encode('ascii') + b'\n')
    if commands:
        git.run('update-ref', '--stdin', data=b''.join(commands))
    head = value['head']
    if 'name_hex' in head:
        name = ref_name(head['name_hex'], branch=True)
        git.run('check-ref-format', name)
        git.run('symbolic-ref', 'HEAD', name)
    else:
        git.run('update-ref', '--no-deref', 'HEAD', head['oid'])
    require(observed_refs(git) == (refs, head), 'stock-ref-identity')
    git.run('fsck', '--full', '--strict', '--no-reflogs', limit=MAX_OBJECTS * 80)
    require(reachable(git, refs) == set(value['objects']), 'object-closure')


@contextmanager
def staged_repository(parent, binary, *, deadline=None):
    name = '.code-restore-' + secrets.token_hex(16)
    os.mkdir(name, mode=0o700, dir_fd=parent)
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    opened = os.fstat(fd)
    try:
        yield name, opened, Git(binary, fd, deadline=deadline)
    finally:
        os.close(fd)
        if same_entry(parent, name, opened):
            shutil.rmtree(name, dir_fd=parent)


def verify_graph(value, binary):
    with tempfile.TemporaryDirectory(prefix='stead-code-verify-') as scratch, directory_fd(scratch) as parent:
        with staged_repository(parent, binary) as (_, _, git):
            materialize(value, git)


def write_archive(path, value):
    raw = encoded(value)
    require(len(raw) <= MAX_ARCHIVE, 'archive-bound')
    with directory_fd(path.parent) as parent:
        opened_parent = private_directory(parent)
        name = '.code-archive-' + secrets.token_hex(16)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        opened = os.fstat(fd)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                require(same_entry(parent, name, opened) and same_path(path.parent, opened_parent),
                        'output-binding')
                os.link(name, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                require(same_entry(parent, path.name, opened) and same_path(path.parent, opened_parent),
                        'output-binding')
                os.fsync(parent)
        finally:
            if same_entry(parent, name, opened):
                os.unlink(name, dir_fd=parent)
    return sha(raw)


def read_archive(path, digest):
    require(match(TOKEN, digest), 'expected-digest-required')
    with directory_fd(path.parent) as parent:
        raw = read_file(parent, path.name, MAX_ARCHIVE, private=True)
    require(sha(raw) == digest, 'archive-digest')
    value = validate(decoded(raw, MAX_ARCHIVE))
    require(encoded(value) == raw, 'archive-not-canonical')
    return value


def sync_tree(git):
    for _, _, names, directory in os.fwalk('.', topdown=False, dir_fd=git.repository):
        for name in names:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        os.fsync(directory)


def publish_directory(parent, source, destination):
    # Linux renameat2 provides atomic publication and rejects every existing
    # target, including an empty directory that plain rename could replace.
    rename = ctypes.CDLL(None, use_errno=True).renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent, os.fsencode(source), parent, os.fsencode(destination), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def restore(value, path, binary, *, deadline=None):
    validate(value)
    with directory_fd(path.parent) as parent:
        opened_parent = private_directory(parent)
        require(not os.path.lexists(f'/proc/self/fd/{parent}/{path.name}'), 'destination-exists')
        with staged_repository(parent, binary, deadline=deadline) as (stage, opened, git):
            materialize(value, git)
            sync_tree(git)
            require(same_entry(parent, stage, opened) and same_path(path.parent, opened_parent),
                    'output-binding')
            publish_directory(parent, stage, path.name)
            require(same_entry(parent, path.name, opened) and same_path(path.parent, opened_parent),
                    'output-binding')
            os.fsync(parent)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    create = commands.add_parser('create', help='Archive an authorized private bare clone')
    create.add_argument('repository', type=Path)
    create.add_argument('archive', type=Path)
    create.add_argument('--project', required=True)
    for action in ('verify', 'restore'):
        command = commands.add_parser(action)
        command.add_argument('archive', type=Path)
        command.add_argument('--sha256', required=True)
        if action == 'restore':
            command.add_argument('destination', type=Path)
    args = parser.parse_args(argv)
    try:
        binary = shutil.which('git')
        require(binary and os.path.isabs(binary), 'stock-git-required')
        os.umask(0o077)
        if args.action == 'create':
            value = collect(args.repository, args.project, binary)
            verify_graph(value, binary)
            digest = write_archive(args.archive, value)
            status = 'created'
        else:
            digest = args.sha256
            value = read_archive(args.archive, digest)
            if args.action == 'verify':
                verify_graph(value, binary)
                status = 'integrity-verified'
            else:
                restore(value, args.destination, binary)
                status = 'offline-git-restored'
        print(json.dumps({'status': status, 'sha256': digest, 'refs': len(value['refs']),
                          'objects': len(value['objects']), 'losses': LOSSES}, sort_keys=True))
        return 0
    except RecoveryError as error:
        print(f'Code archive operation failed ({error}).', file=sys.stderr)
    except (OSError, GuardError, subprocess.SubprocessError, UnicodeError, AttributeError, RecursionError):
        print('Code archive operation failed at the local filesystem or Git boundary.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

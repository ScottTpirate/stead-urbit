#!/usr/bin/env python3
"""Stage and recover private, immutable Git pack snapshots for Stead."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile

from execution_policy import GuardError, directory_fd
from portable_code import (MAX_REFS, observed_refs, private_directory, publish_directory,
                           read_file, ref_name, staged_repository, sync_tree)
from portable_recovery import (OID, TOKEN, UUID, RecoveryError, decoded, encoded, match,
                               number, require, same_entry, same_path, sha, shape)


FORMAT = 'stead.git-pack-snapshot/1'
MAX_PACK = 64 * 1024 * 1024
MAX_OBJECTS = 16_384
MAX_OBJECT = 16 * 1024 * 1024
MAX_OBJECT_BYTES = 256 * 1024 * 1024
MAX_SNAPSHOTS = 8
MAX_MANIFEST = 192 * 1024
GIT_LIMITS = ('/usr/bin/prlimit', '--as=805306368', '--cpu=30', f'--fsize={MAX_PACK}', '--')
INDEX_ROW = re.compile(rb'([0-9a-f]{40}) (blob|commit|tree|tag) ([0-9]{1,9})')
SHIP = re.compile(r'~[a-z][a-z-]{2,62}')
PACK_NAME = 'objects.pack'
MANIFEST_NAME = 'snapshot.json'
ATTESTATION_FORMAT = 'stead.code-pack-attestation/1'
MAX_ATTESTATION = 65_536


def validate_scope(scope):
    shape(scope, {'home', 'project_id', 'repository_id', 'authority_epoch'})
    require(match(SHIP, scope['home'])
            and all(match(UUID, scope[key]) for key in ('project_id', 'repository_id')), 'repository-scope')
    number(scope['authority_epoch'])


def validate_refs(refs, head):
    require(isinstance(refs, dict) and 0 < len(refs) <= MAX_REFS, 'ref-inventory')
    ref_name(head, branch=True)
    require(head in refs, 'default-branch')
    for name, oid in refs.items():
        ref_name(name)
        require(match(OID, oid), 'ref-inventory')


@contextmanager
def repository_directory(store, scope, *, staging=False):
    validate_scope(scope)
    label = '.'.join(scope[key] for key in ('home', 'project_id', 'repository_id'))
    with directory_fd(store) as root:
        opened_root = private_directory(root)
        if staging:
            try:
                os.mkdir(label, mode=0o700, dir_fd=root)
                os.fsync(root)
            except FileExistsError:
                pass
        directory = os.open(label, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        try:
            opened = private_directory(directory)
            fcntl.flock(directory, (fcntl.LOCK_EX if staging else fcntl.LOCK_SH) | fcntl.LOCK_NB)

            def check_binding():
                require(same_entry(root, label, opened) and same_path(store, opened_root), 'store-binding')

            yield directory, check_binding
        finally:
            os.close(directory)


def copy_pack(parent, name, expected, *, destination=None):
    require(match(TOKEN, expected), 'pack-digest-required')
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                and not info.st_mode & 0o077, 'private-pack-required')
        require(32 <= info.st_size <= MAX_PACK, 'pack-size')
        header = stream.read(12)
        require(len(header) == 12, 'pack-header')
        signature, version, objects = struct.unpack('>4sII', header)
        require(signature == b'PACK' and version in (2, 3), 'pack-header')
        require(0 < objects <= MAX_OBJECTS, 'pack-object-limit')
        checksum = hashlib.sha256(header)
        if destination is not None:
            destination.write(header)
        remaining = info.st_size - 12
        while remaining:
            block = stream.read(min(remaining, 1024 * 1024))
            require(block, 'pack-changed')
            checksum.update(block)
            if destination is not None:
                destination.write(block)
            remaining -= len(block)
        require(not stream.read(1) and same_entry(parent, name, info), 'pack-changed')
    require(checksum.hexdigest() == expected, 'pack-digest')
    return info.st_size, objects


def verify_closure(git, pack_count, refs):
    rows = git.run('cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype) %(objectsize)',
                   limit=MAX_OBJECTS * 60).splitlines()
    objects = set()
    total = 0
    for row in rows:
        match_row = INDEX_ROW.fullmatch(row)
        require(match_row is not None, 'object-inventory')
        oid, _, size = match_row.groups()
        count = int(size)
        total += count
        require(oid not in objects and count <= MAX_OBJECT and total <= MAX_OBJECT_BYTES, 'object-byte-limit')
        objects.add(oid)
    require(len(objects) == pack_count, 'pack-object-count')
    roots = ''.join(oid + '\n' for oid in sorted(set(refs.values()))).encode('ascii')
    reachable = git.run('rev-list', '--objects', '--no-object-names', '--stdin', data=roots,
                        limit=MAX_OBJECTS * 41)
    require(set(reachable.splitlines()) == objects, 'pack-ref-closure')
    ids = b'\n'.join(sorted(objects)) + b'\n'
    return {'object_count': pack_count, 'object_bytes': total, 'object_ids_sha256': sha(ids)}


def verify_pack(git, source, name, expected, refs, head):
    git.run('init', '--bare', '--template=', '--object-format=sha1')
    path = Path(git.path)
    incoming = path / 'incoming.pack'
    with incoming.open('xb') as target:
        pack_bytes, pack_count = copy_pack(source, name, expected, destination=target)
    os.chmod(incoming, 0o600)
    result = git.run('index-pack', '--strict', '--threads=1', f'--max-input-size={MAX_PACK}',
                     incoming, limit=41)
    require(re.fullmatch(rb'[0-9a-f]{40}\n', result), 'stock-pack-id')
    base = path / 'objects' / 'pack' / ('pack-' + result.strip().decode('ascii'))
    incoming.rename(base.with_suffix('.pack'))
    incoming.with_suffix('.idx').rename(base.with_suffix('.idx'))

    commands = []
    for ref, oid in sorted(refs.items()):
        name = ref_name(ref)
        git.run('check-ref-format', name)
        commands.append(b'create ' + name + b' ' + oid.encode('ascii') + b'\n')
    git.run('update-ref', '--stdin', data=b''.join(commands))
    git.run('symbolic-ref', 'HEAD', ref_name(head, branch=True))
    require(observed_refs(git) == (refs, {'name_hex': head}), 'stock-ref-identity')
    inventory = verify_closure(git, pack_count, refs)
    git.run('fsck', '--full', '--strict', '--no-reflogs', '--no-dangling', limit=MAX_OBJECTS * 80)
    return base.with_suffix('.pack'), {'pack_sha256': expected, 'pack_bytes': pack_bytes, **inventory}


def read_manifest(directory, snapshot, scope):
    raw = read_file(directory, MANIFEST_NAME, MAX_MANIFEST, private=True)
    require(sha(raw) == snapshot, 'snapshot-digest')
    value = decoded(raw, MAX_MANIFEST)
    shape(value, {'format', 'object_format', 'scope', 'head', 'refs', 'pack_sha256', 'pack_bytes',
                  'object_count', 'object_bytes', 'object_ids_sha256'})
    require(encoded(value) == raw and value['format'] == FORMAT and value['object_format'] == 'sha1'
            and value['scope'] == scope, 'snapshot-scope')
    validate_refs(value['refs'], value['head'])
    return value


@contextmanager
def open_snapshot(directory, snapshot):
    require(match(TOKEN, snapshot), 'snapshot-digest-required')
    fd = os.open(snapshot, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
    try:
        opened = private_directory(fd)
        yield fd
        require(same_entry(directory, snapshot, opened), 'snapshot-binding')
    finally:
        os.close(fd)


def stage(store, pack, expected, scope, refs, head, binary):
    validate_refs(refs, head)
    with repository_directory(store, scope, staging=True) as (directory, check_binding):
        with os.scandir(directory) as entries:
            existing = set()
            for entry in entries:
                require(len(existing) < MAX_SNAPSHOTS, 'snapshot-capacity')
                existing.add(entry.name)
        with staged_repository(directory, binary, command_prefix=GIT_LIMITS) as (scratch, opened, git):
            with directory_fd(pack.parent) as source:
                verified, inventory = verify_pack(git, source, pack.name, expected, refs, head)
            value = {'format': FORMAT, 'object_format': 'sha1', 'scope': scope,
                     'head': head, 'refs': refs, **inventory}
            raw = encoded(value)
            snapshot = sha(raw)
            if snapshot in existing:
                with open_snapshot(directory, snapshot) as old:
                    require(read_manifest(old, snapshot, scope) == value, 'snapshot-conflict')
                    require(copy_pack(old, PACK_NAME, expected) == (value['pack_bytes'], value['object_count']),
                            'snapshot-conflict')
                check_binding()
                return snapshot, value
            require(len(existing) < MAX_SNAPSHOTS, 'snapshot-capacity')
            check_binding()
            payload = Path(git.path) / 'payload'
            payload.mkdir(mode=0o700)
            verified.rename(payload / PACK_NAME)
            with (payload / MANIFEST_NAME).open('xb') as file:
                os.fchmod(file.fileno(), 0o600)
                file.write(raw)
            sync_tree(git)
            check_binding()
            require(same_entry(directory, scratch, opened), 'staging-binding')
            publish_directory(directory, scratch + '/payload', snapshot)
            os.fsync(directory)
            check_binding()
            return snapshot, value


def restore(store, snapshot, scope, destination, binary, *, authorize=None):
    """Restore exact authorized roots selected by the offline operator."""
    require(destination.name not in ('', '.', '..'), 'destination-path')
    with repository_directory(store, scope) as (directory, check_store):
        with open_snapshot(directory, snapshot) as source, directory_fd(destination.parent) as parent:
            opened_parent = private_directory(parent)
            value = read_manifest(source, snapshot, scope)
            require(not os.path.lexists(f'/proc/self/fd/{parent}/{destination.name}'), 'destination-exists')
            with staged_repository(parent, binary, command_prefix=GIT_LIMITS) as (scratch, opened, git):
                _, inventory = verify_pack(git, source, PACK_NAME, value['pack_sha256'], value['refs'], value['head'])
                require(all(type(value[key]) is type(actual) and value[key] == actual
                            for key, actual in inventory.items()), 'snapshot-inventory')
                sync_tree(git)
                if authorize is not None:
                    authorize(value)
                check_store()
                require(same_entry(directory, snapshot, os.fstat(source))
                        and same_entry(parent, scratch, opened)
                        and same_path(destination.parent, opened_parent), 'restore-binding')
                publish_directory(parent, scratch, destination.name)
                os.fsync(parent)
    return value


def attest(store, snapshot, scope, binary):
    """Reverify retained pack bytes before issuing a Home staging input."""
    with repository_directory(store, scope) as (directory, check_store):
        require(scope['project_id'] == scope['repository_id'], 'home-repository-scope')
        with open_snapshot(directory, snapshot) as source:
            value = read_manifest(source, snapshot, scope)
            with tempfile.TemporaryDirectory(prefix='stead-pack-attest-') as work:
                with directory_fd(Path(work)) as parent:
                    with staged_repository(parent, binary, command_prefix=GIT_LIMITS) as (_, _, git):
                        _, inventory = verify_pack(git, source, PACK_NAME, value['pack_sha256'], value['refs'], value['head'])
                        require(all(type(value[key]) is type(actual) and value[key] == actual
                                    for key, actual in inventory.items()), 'snapshot-inventory')
            check_store()
            require(same_entry(directory, snapshot, os.fstat(source)), 'snapshot-binding')
    wire = {'protocol': ATTESTATION_FORMAT, **scope, 'snapshot': snapshot, 'head': value['head'],
            'refs': value['refs'], 'pack_sha256': value['pack_sha256'],
            'pack_bytes': str(value['pack_bytes']), 'object_count': str(value['object_count']),
            'object_bytes': str(value['object_bytes']), 'object_ids_sha256': value['object_ids_sha256']}
    require(len(encoded(wire)) <= MAX_ATTESTATION, 'attestation-bound')
    return wire


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    for action in ('stage', 'restore', 'attest'):
        command = actions.add_parser(action)
        command.add_argument('store', type=Path, help='Existing private storage directory')
        command.add_argument('--home', required=True)
        command.add_argument('--project', required=True)
        command.add_argument('--repository', required=True)
        command.add_argument('--epoch', required=True)
        command.add_argument('--git', default='git')
    stage_command = actions.choices['stage']
    stage_command.add_argument('pack', type=Path)
    stage_command.add_argument('--sha256', required=True)
    stage_command.add_argument('--head-hex', required=True)
    stage_command.add_argument('--ref-hex', action='append', required=True, metavar='REF_HEX=OID')
    restore_command = actions.choices['restore']
    restore_command.add_argument('destination', type=Path)
    restore_command.add_argument('--snapshot', required=True, help='Independently authorized manifest SHA-256')
    actions.choices['attest'].add_argument('--snapshot', required=True, help='Reviewed staged manifest SHA-256')
    args = parser.parse_args(argv)
    try:
        binary = shutil.which(args.git)
        require(binary, 'stock-git-required')
        binary = str(Path(binary).resolve(strict=True))
        os.umask(0o077)
        scope = {'home': args.home, 'project_id': args.project, 'repository_id': args.repository,
                 'authority_epoch': args.epoch}
        if args.action == 'stage':
            refs = {}
            for ref in args.ref_hex:
                name, separator, oid = ref.partition('=')
                require(separator and name not in refs, 'ref-inventory')
                refs[name] = oid
            snapshot, value = stage(args.store, args.pack, args.sha256, scope, refs, args.head_hex, binary)
            status = 'candidate-staged'
        elif args.action == 'restore':
            snapshot = args.snapshot
            value = restore(args.store, snapshot, scope, args.destination, binary)
            status = 'offline-git-restored'
        else:
            sys.stdout.buffer.write(encoded(attest(args.store, args.snapshot, scope, binary)))
            return 0
        print(json.dumps({'status': status, 'snapshot': snapshot, **value}, sort_keys=True))
        return 0
    except RecoveryError as error:
        print(f'Git pack operation denied ({error}).', file=sys.stderr)
    except (OSError, GuardError, subprocess.SubprocessError):
        print('Git pack operation failed at the local filesystem or Git boundary.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

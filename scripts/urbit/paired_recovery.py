#!/usr/bin/env python3
"""Bind and verify sealed Home checkpoint bytes with one selected Git pack.

Offline integrity only. A separately trusted operator-evidence digest is the
builder's authority prerequisite; the result is not a Home signature, restore,
source-retirement check or stock-Git object verification. See the capture
contract in docs/urbit/PAIRED_RECOVERY_PROFILE.md before preparing evidence.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat
import struct
import sys
import time

from execution_policy import GuardError, directory_fd
from git_pack_projection import validate_manifest
import git_pack_store as store
from portable_code import private_directory
from portable_recovery import (TOKEN, UUID, decoded, encoded, match,
                               number, require, same_entry, same_path, sha, shape)


FORMAT = 'stead.paired-recovery/1'
CAPTURE_FORMAT = 'stead.home-pack-capture/1'
MAX_CHECKPOINT = 1024 * 1024 * 1024
MAX_EVIDENCE = 384 * 1024
MAX_BINDING = 1024 * 1024
MAX_SECONDS = 60
CHUNK = 65_536
SELECTION_FIELDS = {'protocol', 'status', 'snapshot', 'authority_epoch', 'object_count',
                    'head', 'refs', 'request_id', 'accepted_at_ms'}


def remaining(deadline):
    require(time.monotonic() < deadline, 'paired-recovery-deadline')


def file_state(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_uid, info.st_nlink)


@contextmanager
def retained(path, limit, deadline):
    """Keep the opened inode and its no-follow directory binding until exit."""
    path = Path(path).absolute()
    remaining(deadline)
    with directory_fd(path.parent) as parent:
        parent_info = private_directory(parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as source:
            before = os.fstat(source.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                    and before.st_nlink == 1 and not before.st_mode & 0o077,
                    'paired-recovery-private-file')
            require(0 < before.st_size <= limit, 'paired-recovery-file-bound')
            yield source, before.st_size
            remaining(deadline)
            require(file_state(os.fstat(source.fileno())) == file_state(before)
                    and same_entry(parent, path.name, before)
                    and same_path(path.parent, parent_info), 'paired-recovery-input-changed')


def read_small(opened, deadline):
    source, size = opened
    remaining(deadline)
    raw = source.read(size + 1)
    require(len(raw) == size, 'paired-recovery-input-changed')
    remaining(deadline)
    return raw


def hash_stream(opened, deadline, *, pack=False):
    source, size = opened
    digest = hashlib.sha256()
    count = 0
    objects = None
    if pack:
        header = source.read(12)
        require(len(header) == 12 and size >= 32, 'paired-recovery-pack-header')
        signature, version, objects = struct.unpack('>4sII', header)
        require(signature == b'PACK' and version in (2, 3)
                and 0 < objects <= store.MAX_OBJECTS, 'paired-recovery-pack-header')
        digest.update(header)
        count = len(header)
    while count < size:
        remaining(deadline)
        block = source.read(min(CHUNK, size - count))
        require(block, 'paired-recovery-input-changed')
        digest.update(block)
        count += len(block)
    require(source.read(1) == b'', 'paired-recovery-input-changed')
    remaining(deadline)
    return {'sha256': digest.hexdigest(), 'bytes': count}, objects


def capture(raw):
    value = decoded(raw, MAX_EVIDENCE)
    shape(value, {'protocol', 'capture_id', 'source_commit', 'saved_state',
                  'checkpoint', 'handoff', 'scope', 'selection'})
    require(value['protocol'] == CAPTURE_FORMAT and match(UUID, value['capture_id'])
            and isinstance(value['source_commit'], str)
            and re.fullmatch(r'[0-9a-f]{40}', value['source_commit']), 'paired-recovery-capture')
    shape(value['saved_state'], {'version', 'durable_sha256'})
    require(type(value['saved_state']['version']) is int and value['saved_state']['version'] in (7, 8, 9)
            and match(TOKEN, value['saved_state']['durable_sha256']), 'paired-recovery-saved-state')
    shape(value['checkpoint'], {'sha256', 'bytes'})
    require(match(TOKEN, value['checkpoint']['sha256'])
            and type(value['checkpoint']['bytes']) is int
            and 0 < value['checkpoint']['bytes'] <= MAX_CHECKPOINT, 'paired-recovery-checkpoint')
    status, scope, selected = (value[key] for key in ('handoff', 'scope', 'selection'))
    shape(status, {'protocol', 'home', 'phase', 'generation'})
    require(status['protocol'] == 'stead.home-handoff/1' and status['phase'] == 'sealed',
            'paired-recovery-sealed-required')
    number(status['generation'])
    require(int(status['generation']) >= 2, 'paired-recovery-sealed-generation')
    store.validate_scope(scope)
    require(scope['home'] == status['home'] and scope['project_id'] == scope['repository_id'],
            'paired-recovery-home-scope')
    shape(selected, SELECTION_FIELDS)
    require(selected['protocol'] == 'stead.code/1' and selected['status'] == 'external'
            and match(TOKEN, selected['snapshot']) and match(UUID, selected['request_id'])
            and selected['authority_epoch'] == scope['authority_epoch'], 'paired-recovery-selection')
    number(selected['object_count'])
    number(selected['accepted_at_ms'])
    require(int(selected['object_count']) <= store.MAX_OBJECTS
            and isinstance(selected['refs'], str) and selected['refs'].isascii()
            and len(selected['refs']) <= store.MAX_MANIFEST, 'paired-recovery-selection-bound')
    refs = decoded(selected['refs'].encode('ascii'), store.MAX_MANIFEST)
    store.validate_refs(refs, selected['head'])
    return value, refs


def binding(raw, expected):
    require(match(TOKEN, expected) and sha(raw) == expected, 'paired-recovery-binding-digest')
    value = decoded(raw, MAX_BINDING)
    shape(value, {'protocol', 'operator_evidence_json', 'operator_evidence_sha256', 'snapshot_manifest'})
    require(value['protocol'] == FORMAT and isinstance(value['operator_evidence_json'], str),
            'paired-recovery-binding')
    evidence = value['operator_evidence_json'].encode('utf-8')
    require(match(TOKEN, value['operator_evidence_sha256'])
            and sha(evidence) == value['operator_evidence_sha256'], 'paired-recovery-evidence-digest')
    observed, refs = capture(evidence)
    selected, manifest = observed['selection'], value['snapshot_manifest']
    validate_manifest(selected['snapshot'], manifest, observed['scope'])
    require(manifest['refs'] == refs and manifest['head'] == selected['head']
            and manifest['object_count'] == int(selected['object_count']), 'paired-recovery-selection-differs')
    return value, observed


def artifacts(stack, observed, manifest, checkpoint_path, snapshot_path, pack_path, deadline):
    snapshot = stack.enter_context(retained(snapshot_path, store.MAX_MANIFEST, deadline))
    checkpoint = stack.enter_context(retained(checkpoint_path, MAX_CHECKPOINT, deadline))
    pack = stack.enter_context(retained(pack_path, store.MAX_PACK, deadline))
    require(read_small(snapshot, deadline) == encoded(manifest), 'paired-recovery-snapshot-differs')
    require(checkpoint[1] == observed['checkpoint']['bytes'] and pack[1] == manifest['pack_bytes'],
            'paired-recovery-artifact-length')
    require(hash_stream(checkpoint, deadline)[0] == observed['checkpoint'], 'paired-recovery-checkpoint-differs')
    digest, objects = hash_stream(pack, deadline, pack=True)
    require(digest == {'sha256': manifest['pack_sha256'], 'bytes': manifest['pack_bytes']}
            and objects == manifest['object_count'], 'paired-recovery-pack-differs')


def report(value, observed, digest):
    return {'protocol': 'stead.paired-recovery-verification/1', 'status': 'integrity-verified',
            'binding_sha256': digest, 'operator_evidence_sha256': value['operator_evidence_sha256'],
            'capture_id': observed['capture_id'], 'home': observed['handoff']['home'],
            'handoff_generation': observed['handoff']['generation'], 'scope': observed['scope'],
            'checkpoint': observed['checkpoint'], 'snapshot': observed['selection']['snapshot'],
            'request_id': observed['selection']['request_id'],
            'authority_basis': 'externally-pinned-operator-evidence',
            'native_execution': False, 'home_replayed': False, 'git_objects_verified': False,
            'source_retirement_verified': False, 'decryption_verified': False,
            'fresh_host_qualified': False, 'qualifies_phase': False}


def build(evidence_path, expected_evidence, checkpoint_path, snapshot_path, pack_path):
    """Require trusted capture bytes before constructing a new integrity binding."""
    deadline = time.monotonic() + MAX_SECONDS
    with ExitStack() as stack:
        evidence = stack.enter_context(retained(evidence_path, MAX_EVIDENCE, deadline))
        raw = read_small(evidence, deadline)
        require(match(TOKEN, expected_evidence) and sha(raw) == expected_evidence,
                'paired-recovery-evidence-digest')
        observed, _ = capture(raw)
        snapshot = stack.enter_context(retained(snapshot_path, store.MAX_MANIFEST, deadline))
        manifest = decoded(read_small(snapshot, deadline), store.MAX_MANIFEST)
        value = {'protocol': FORMAT, 'operator_evidence_json': raw.decode('utf-8'),
                 'operator_evidence_sha256': expected_evidence, 'snapshot_manifest': manifest}
        payload = encoded(value)
        value, observed = binding(payload, sha(payload))
        artifacts(stack, observed, value['snapshot_manifest'], checkpoint_path, snapshot_path, pack_path, deadline)
    return payload, report(value, observed, sha(payload))


def verify(binding_path, expected_binding, checkpoint_path, snapshot_path, pack_path):
    deadline = time.monotonic() + MAX_SECONDS
    with ExitStack() as stack:
        retained_binding = stack.enter_context(retained(binding_path, MAX_BINDING, deadline))
        raw = read_small(retained_binding, deadline)
        value, observed = binding(raw, expected_binding)
        artifacts(stack, observed, value['snapshot_manifest'], checkpoint_path, snapshot_path, pack_path, deadline)
    return report(value, observed, sha(raw))


def write_new(path, raw):
    """Publish only to an absent private file; never replace a prior binding."""
    path = Path(path).absolute()
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BINDING, 'paired-recovery-binding-bound')
    with directory_fd(path.parent) as parent:
        before = private_directory(parent)
        name = '.paired-recovery-' + secrets.token_hex(16)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        opened = os.fstat(fd)
        try:
            with os.fdopen(fd, 'wb') as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
                require(same_entry(parent, name, opened) and same_path(path.parent, before),
                        'paired-recovery-output-changed')
                os.link(name, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                require(same_entry(parent, path.name, opened) and same_path(path.parent, before),
                        'paired-recovery-output-changed')
                os.unlink(name, dir_fd=parent)
                os.fsync(parent)
                require(same_entry(parent, path.name, opened) and same_path(path.parent, before),
                        'paired-recovery-output-changed')
        finally:
            if same_entry(parent, name, opened):
                os.unlink(name, dir_fd=parent)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    for action in ('build', 'verify'):
        command = actions.add_parser(action)
        command.add_argument('--checkpoint', type=Path, required=True)
        command.add_argument('--snapshot', type=Path, required=True, help='Exact canonical snapshot.json')
        command.add_argument('--pack', type=Path, required=True, help='Exact original objects.pack')
    create = actions.choices['build']
    create.add_argument('--evidence', type=Path, required=True)
    create.add_argument('--evidence-sha256', required=True, help='Independently trusted operator capture digest')
    create.add_argument('--output', type=Path, required=True, help='New private binding file')
    inspect = actions.choices['verify']
    inspect.add_argument('--binding', type=Path, required=True)
    inspect.add_argument('--sha256', required=True, help='Independently retained binding digest')
    args = parser.parse_args(argv)
    try:
        if args.action == 'build':
            payload, result = build(args.evidence, args.evidence_sha256, args.checkpoint, args.snapshot, args.pack)
            write_new(args.output, payload)
        else:
            result = verify(args.binding, args.sha256, args.checkpoint, args.snapshot, args.pack)
    except (OSError, ValueError, TypeError, KeyError, GuardError):
        print('Paired recovery verification failed; preserve the inputs for inspection.', file=sys.stderr)
        return 1
    print(encoded(result).decode('utf-8'), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

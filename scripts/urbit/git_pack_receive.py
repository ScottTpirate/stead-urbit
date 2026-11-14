"""Verify original SHA-1 receive-pack bytes into an immutable snapshot candidate."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
import time

from execution_policy import directory_fd
import git_pack_push as push
import git_pack_store as store
from portable_code import MAX_GIT_TIME, MAX_REF_BYTES, private_directory, ref_name, staged_repository
from portable_recovery import TOKEN, match, require, same_entry, same_path, sha


MAX_PREFIX = 65_536
MAX_UPLOAD_PACK = 8 * 1024 * 1024
MAX_WIRE = MAX_PREFIX + MAX_UPLOAD_PACK
MAX_CAPABILITIES = 1024
# The installed thin-pack repair and the verified base are the only packs
# inside the scratch repository. Repacking writes one separately bounded file.
MAX_WORK_PACK_BYTES = 2 * store.MAX_PACK
CAPABILITIES = {b'report-status', b'report-status-v2', b'delete-refs', b'ofs-delta',
                b'atomic', b'object-format=sha1', b'side-band-64k', b'quiet'}
PKT_SIZE = re.compile(rb'[0-9a-f]{4}')
COMMAND = re.compile(rb'([0-9a-f]{40}) ([0-9a-f]{40}) (.+)')
CAPABILITY = re.compile(rb'[!-~]{1,128}')


def capabilities(value):
    require(len(value) <= MAX_CAPABILITIES, 'receive-capability-bound')
    tokens = value.removeprefix(b' ').split(b' ')
    require(len(tokens) <= 12, 'receive-capability-bound')
    keys = set()
    for token in tokens:
        require(CAPABILITY.fullmatch(token) is not None, 'receive-capability')
        if token.startswith(b'agent='):
            require(len(token) > len(b'agent='), 'receive-capability')
            key = b'agent'
        else:
            require(token in CAPABILITIES, 'receive-capability')
            key = token
        require(key not in keys, 'receive-capability-duplicate')
        keys.add(key)
    require(len(keys & {b'report-status', b'report-status-v2'}) == 1, 'receive-report-status')


def parse(wire):
    require(isinstance(wire, bytes) and 0 < len(wire) <= MAX_WIRE, 'receive-wire-bound')
    changes = []
    seen = set()
    offset = 0
    while True:
        require(offset + 4 <= min(len(wire), MAX_PREFIX), 'receive-prefix-bound')
        header = wire[offset:offset + 4]
        require(PKT_SIZE.fullmatch(header) is not None, 'receive-pkt-line')
        size = int(header, 16)
        if size == 0:
            require(changes, 'receive-empty-command-list')
            pack = wire[offset + 4:]
            break
        require(4 < size <= 4 + 82 + MAX_REF_BYTES + 1 + MAX_CAPABILITIES + 1
                and offset + size <= min(len(wire), MAX_PREFIX), 'receive-pkt-line-bound')
        require(len(changes) < push.MAX_CHANGES, 'update-bound')
        line = wire[offset + 4:offset + size].removesuffix(b'\n')
        offset += size
        command, separator, offered = line.partition(b'\0')
        require(bool(separator) == (not changes), 'receive-capability-position')
        if separator:
            capabilities(offered)
        parsed = COMMAND.fullmatch(command)
        require(parsed is not None, 'receive-command')
        prior, target, raw_ref = parsed.groups()
        ref = raw_ref.hex()
        ref_name(ref)
        require(ref not in seen, 'duplicate-ref')
        require(target != b'0' * 40, 'ref-delete-unsupported')
        changes.append({'ref': ref, 'prior': prior.decode('ascii'), 'target': target.decode('ascii')})
        seen.add(ref)
    require(32 <= len(pack) <= MAX_UPLOAD_PACK, 'receive-pack-bound')
    signature, version, count = struct.unpack('>4sII', pack[:12])
    require(signature == b'PACK' and version in (2, 3) and count <= store.MAX_OBJECTS, 'receive-pack-header')
    require(hashlib.sha1(memoryview(pack)[:-20], usedforsecurity=False).digest() == pack[-20:], 'receive-pack-checksum')
    return changes, pack


@contextmanager
def captured_wire(path, expected):
    require(match(TOKEN, expected), 'receive-digest-required')
    with directory_fd(path.parent) as parent:
        directory = private_directory(parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            initial = os.fstat(stream.fileno())
            require(stat.S_ISREG(initial.st_mode) and initial.st_uid == os.getuid()
                    and initial.st_nlink == 1 and stat.S_IMODE(initial.st_mode) == 0o600, 'receive-private-wire')
            require(0 < initial.st_size <= MAX_WIRE, 'receive-wire-bound')
            wire = stream.read(MAX_WIRE + 1)
            require(len(wire) == initial.st_size and sha(wire) == expected, 'receive-wire-digest')

            def check_binding():
                final = os.fstat(stream.fileno())
                require(initial.st_mtime_ns == final.st_mtime_ns and initial.st_ctime_ns == final.st_ctime_ns
                        and initial.st_size == final.st_size and same_entry(parent, path.name, initial)
                        and same_path(path.parent, directory), 'receive-wire-changed')

            check_binding()
            yield wire, check_binding


def prepare(storage, scope, base_snapshot, wire_path, expected_wire_sha256, git, *, deadline=None):
    """Use an admitted wire digest and exact base. Return staging evidence only."""
    store.validate_scope(scope)
    require(scope['project_id'] == scope['repository_id'] and match(TOKEN, base_snapshot), 'receive-base-scope')
    own_deadline = time.monotonic() + MAX_GIT_TIME
    deadline = own_deadline if deadline is None else min(own_deadline, deadline)
    require(time.monotonic() < deadline, 'git-timeout')
    with captured_wire(Path(wire_path), expected_wire_sha256) as capture, \
            tempfile.TemporaryDirectory(prefix='stead-git-receive-') as work:
        wire, check_wire = capture
        changes, incoming = parse(wire)
        directory = Path(work)
        output = directory / 'candidate.pack'
        with directory_fd(directory) as parent:
            workspace = private_directory(parent)
            with staged_repository(parent, git, deadline=deadline, command_prefix=store.GIT_LIMITS) as (scratch, opened, repo):
                with store.repository_directory(storage, scope) as (repository, check_store):
                    with store.open_snapshot(repository, base_snapshot) as source:
                        base = store.read_manifest(source, base_snapshot, scope)
                        refs, ordered = push.proposed_refs(base['refs'], base['head'], changes)
                        _, inventory = store.verify_pack(repo, source, store.PACK_NAME, base['pack_sha256'],
                                                         base['refs'], base['head'])
                        require(all(base[key] == value for key, value in inventory.items()), 'receive-base-inventory')
                        check_store()
                for change in ordered:
                    repo.run('check-ref-format', ref_name(change['ref']))
                # Only the verified base repo is visible to REF_DELTA lookup.
                # index-pack forwards trailing input, so require its exact receipt.
                indexed = repo.run('index-pack', '--stdin', '--fix-thin', '--strict', '--threads=1',
                                   f'--max-input-size={MAX_UPLOAD_PACK}', data=incoming, limit=46)
                require(re.fullmatch(rb'pack\t[0-9a-f]{40}\n', indexed) is not None, 'receive-pack-index')
                installed = Path(repo.path) / 'objects' / 'pack' / ('pack-' + indexed[5:-1].decode('ascii') + '.pack')
                compressed = installed.stat().st_size
                require(32 <= compressed <= store.MAX_PACK and compressed + base['pack_bytes'] <= MAX_WORK_PACK_BYTES,
                        'receive-installed-pack-bound')
                roots = ''.join(oid + '\n' for oid in sorted(set(refs.values()))).encode('ascii')
                reachable = repo.run('rev-list', '--objects', '--no-object-names', '--stdin',
                                     data=roots, limit=store.MAX_OBJECTS * 41)
                # Stock Git enumerates unique objects across both indexes. A
                # repeat of an accepted object cannot hide unrelated new ones.
                store.verify_closure(repo, len(set(reachable.splitlines())), refs)
                fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as packed:
                    repo.run_to(packed, 'pack-objects', '--stdout', '--revs', '--delta-base-offset', '--threads=1',
                                data=roots, limit=store.MAX_PACK)
                require(same_entry(parent, scratch, opened), 'receive-workspace-changed')
            fd = os.open(output.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, 'rb') as packed:
                output_info = os.fstat(packed.fileno())
                require(stat.S_ISREG(output_info.st_mode) and output_info.st_nlink == 1
                        and stat.S_IMODE(output_info.st_mode) == 0o600
                        and 32 <= output_info.st_size <= store.MAX_PACK, 'receive-candidate-pack-bound')
                candidate_digest = hashlib.file_digest(packed, 'sha256').hexdigest()

            def recheck():
                check_wire()
                require(same_path(directory, workspace) and same_entry(parent, output.name, output_info),
                        'receive-workspace-changed')

            require(time.monotonic() < deadline, 'git-timeout')
            recheck()
            result = push.prepare(storage, scope, base_snapshot, output, candidate_digest, ordered, git,
                                  upload_sha256=expected_wire_sha256, deadline=deadline, recheck=recheck)
            recheck()
            require(time.monotonic() < deadline, 'git-timeout')
            return result

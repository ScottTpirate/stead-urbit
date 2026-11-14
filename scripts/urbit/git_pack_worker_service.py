#!/usr/bin/env python3
"""Explicit foreground launcher for the private Stead Git worker."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import time

from execution_policy import GuardError, directory_fd
from git_pack_private_worker import PrivatePackWorker
import git_pack_review
from git_pack_worker_signature import MAX_GENERATION, sign
from git_pack_worker_socket import MAX_SECONDS, WorkerSocket, identities
from portable_code import private_directory
from portable_recovery import TOKEN, UUID, RecoveryError, decoded, encoded, match, number, require, same_entry, same_path, shape, text


PROFILE = 'stead.git-pack-worker-service/1'
FIELDS = {'protocol', 'worker_uid', 'relay_uid', 'socket_gid', 'socket', 'spool', 'store',
          'git', 'git_sha256', 'key', 'key_generation'}
MAX_PROFILE = 8192
MAX_GIT = 32 * 1024 * 1024
ACCEPT_SECONDS = 1
POLL_SECONDS = 5
BWRAP = '/usr/bin/bwrap'
GIT_ENV = ('PATH', 'HOME', 'LANG', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL', 'GIT_NO_REPLACE_OBJECTS',
           'GIT_OPTIONAL_LOCKS', 'GIT_TERMINAL_PROMPT', 'GIT_NO_LAZY_FETCH', 'GIT_ALLOW_PROTOCOL')


@dataclass(frozen=True)
class Profile:
    worker_uid: int
    relay_uid: int
    socket_gid: int
    socket: Path
    spool: Path
    store: Path
    git: Path
    git_sha256: str
    key: Path
    key_generation: int


def exact_path(value):
    raw = text(value, 4096)
    path = Path(raw)
    require(path.is_absolute() and len(path.parts) > 1 and '..' not in path.parts
            and all(ord(character) >= 32 and ord(character) != 127 for character in raw)
            and str(path) == raw, 'worker-service-path')
    return path


def disjoint(paths):
    for i, path in enumerate(paths):
        require(all(not (path == peer or path in peer.parents or peer in path.parents)
                    for peer in paths[i + 1:]), 'worker-service-path-overlap')


def unchanged(stream, path, parent, before):
    info = os.fstat(stream.fileno())
    require(same_entry(parent, path.name, before) and info.st_nlink == 1 and info.st_size == before.st_size
            and info.st_ctime_ns == before.st_ctime_ns and info.st_mtime_ns == before.st_mtime_ns,
            'worker-service-file-changed')


@contextmanager
def held_file(path, size, *, secret=False):
    with directory_fd(path.parent) as parent:
        if secret:
            private_directory(parent)
        owner = os.fstat(parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= size,
                    'worker-service-file')
            if secret:
                require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600,
                        'worker-service-private-file')
            else:
                require(info.st_uid in (0, os.getuid()) and not info.st_mode & 0o022 and info.st_mode & 0o111,
                        'worker-service-executable')
            yield stream
            unchanged(stream, path, parent, info)
            require(same_path(path.parent, owner), 'worker-service-parent-changed')


def load(path):
    path = exact_path(str(path))
    with held_file(path, MAX_PROFILE, secret=True) as stream:
        value = decoded(stream.read(MAX_PROFILE + 1), MAX_PROFILE)
    shape(value, FIELDS)
    require(value['protocol'] == PROFILE, 'worker-service-profile')
    identities(value['relay_uid'], value['worker_uid'])
    require(0 < os.getuid() == os.geteuid() == value['worker_uid'] and value['relay_uid'] > 0,
            'worker-service-owner')
    require(type(value['socket_gid']) is int and 0 < value['socket_gid'] < 2**32 - 1
            and value['socket_gid'] in {os.getgid(), *os.getgroups()}, 'worker-service-group')
    require(type(value['key_generation']) is int and 1 <= value['key_generation'] <= MAX_GENERATION
            and match(TOKEN, value['git_sha256']), 'worker-service-pins')
    for name in ('socket', 'spool', 'store', 'git', 'key'):
        value[name] = exact_path(value[name])
    require(value['socket'].name == 'worker.sock', 'worker-service-socket-name')
    disjoint((value['socket'].parent, value['spool'], value['store'], value['git'], value['key'], path))
    require(all(not in_runtime(item) for item in (value['socket'], value['spool'], value['store'], value['key'], path)),
            'worker-service-runtime-path')
    return Profile(**{key: value[key] for key in FIELDS - {'protocol'}})


def in_runtime(path):
    return path.parts[1] in ('usr', 'bin', 'sbin', 'lib', 'lib64', 'proc', 'dev')


def sandbox_flags():
    command = [BWRAP, '--unshare-all', '--unshare-user', '--disable-userns', '--new-session',
               '--die-with-parent', '--clearenv', '--cap-drop', 'ALL',
               '--ro-bind', '/usr/bin/python3', '/usr/bin/python3']
    for name in ('/usr/lib', '/usr/lib64', '/lib', '/lib64'):
        path = Path(name)
        if path.is_symlink():
            command += ['--symlink', os.readlink(path), str(path)]
        elif path.exists():
            command += ['--ro-bind', str(path), str(path)]
    return command + ['--proc', '/proc', '--dev', '/dev', '--size', '33554432', '--tmpfs', '/tmp']


def sandbox_ready():
    checks = ('import os,socket; from pathlib import Path; '
              'status=dict(row.split(":",1) for row in Path("/proc/self/status").read_text().splitlines() if ":" in row); '
              'assert [name for _,name in socket.if_nameindex()]==["lo"]; '
              'assert status["NoNewPrivs"].strip()=="1"; '
              'assert all(int(status[k].strip(),16)==0 for k in ("CapEff","CapPrm","CapBnd")); '
              'assert not any(Path(p).exists() for p in ("/home","/root","/run","/etc")); '
              'assert os.statvfs("/").f_flag & os.ST_RDONLY')
    command = sandbox_flags() + ['--remount-ro', '/', '--', '/usr/bin/python3', '-I', '-S', '-c', checks]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, env={}, timeout=POLL_SECONDS)
    require(result.returncode == 0, 'worker-service-isolation-unavailable')


def copy_engine(profile, destination):
    with held_file(profile.git, MAX_GIT) as source, destination.open('xb') as output:
        digest = hashlib.sha256()
        left = MAX_GIT
        while chunk := source.read(min(65_536, left + 1)):
            left -= len(chunk)
            require(left >= 0, 'worker-service-engine-bound')
            digest.update(chunk)
            output.write(chunk)
        require(digest.hexdigest() == profile.git_sha256, 'worker-service-engine-digest')
        os.fchmod(output.fileno(), 0o500)


def wrapper(engine):
    # Only portable_code.Git calls this executable. Its repository descriptor
    # is remapped to /repo, including the generated index-pack path argument.
    return '''#!/usr/bin/python3 -I
import os, stat, sys

flags = %a
variables = %a
argv = sys.argv[1:]
if len(argv) < 3 or argv[0] != '--git-dir' or not argv[1].startswith('/proc/self/fd/'):
    sys.exit(1)
inside = os.fsencode(argv[1])
tail = argv[1].removeprefix('/proc/self/fd/')
if not tail.isascii() or not tail.isdecimal() or len(tail) > 8:
    sys.exit(1)
fd = int(tail)
if fd < 3 or not stat.S_ISDIR(os.fstat(fd).st_mode):
    sys.exit(1)
options = [value for key in variables for value in ('--setenv', key, os.environ[key])]
args = []
for value in map(os.fsencode, argv[2:]):
    if value.startswith(inside + b'/'):
        value = b'/repo' + value[len(inside):]
    args.append(value)
os.execve(flags[0], flags + options + ['--bind-fd', tail, '/repo', '--remount-ro', '/',
           '--', '/engine/git', '--git-dir', '/repo'] + args, {})
''' % (sandbox_flags() + ['--ro-bind', str(engine), '/engine/git', '--symlink', '/engine/git', '/usr/bin/git'], GIT_ENV)


@contextmanager
def worker(profile):
    # Provisioned directories must already exist before proof service can bind.
    for path in (profile.spool, profile.store):
        with directory_fd(path) as fd:
            private_directory(fd)
    sandbox_ready()
    # Check the configured key as Ed25519 and ready for this generation, before
    # clients can connect. The self-check signature never leaves this process.
    sign(b'stead.git-pack-worker-service/1 startup\n', profile.key_generation, profile.key)
    with tempfile.TemporaryDirectory(prefix='stead-worker-engine-', dir=profile.spool) as scratch:
        directory = Path(scratch)
        binary, command = directory / 'git', directory / 'git-isolated'
        copy_engine(profile, binary)
        with command.open('x', encoding='ascii') as output:
            output.write(wrapper(binary))
            os.fchmod(output.fileno(), 0o500)
        yield PrivatePackWorker(profile.store, command)


@contextmanager
def shutdown_requested():
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    previous = {kind: signal.signal(kind, stop) for kind in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield lambda: stopped
    finally:
        for kind, handler in previous.items():
            signal.signal(kind, handler)


def serve(profile):
    with shutdown_requested() as stopped, worker(profile) as verify:
        if stopped():
            return
        with WorkerSocket(profile.socket, profile.spool, profile.relay_uid, profile.worker_uid, verify,
                          profile.key_generation, profile.key, group_gid=profile.socket_gid) as endpoint:
            while not stopped():
                endpoint.serve_one(time.monotonic() + MAX_SECONDS, accept_seconds=ACCEPT_SECONDS, stopping=stopped)


def review_request(value, scope, verify, profile):
    shape(value, {'protocol', 'request_id', 'proposal_id', 'revision', 'work_id', 'source_ref', 'ref',
                  'base_oid', 'head_oid', 'base_snapshot', 'generation'})
    require(value['protocol'] == 'stead.git-pack-review-request/1' and match(UUID, value['request_id']),
            'worker-review-request')
    source = text(value['source_ref'], 1024).encode('utf-8')
    target = text(value['ref'], 1024).encode('utf-8')
    number(value['revision'])
    number(value['generation'], positive=False)
    result = git_pack_review.prepare(verify.storage, scope, value['base_snapshot'], source, target,
                                     value['base_oid'], value['head_oid'], verify.git,
                                     proposal_id=value['proposal_id'], proposal_revision=int(value['revision']),
                                     work_id=value['work_id'], generation=int(value['generation']))
    proof = git_pack_review.proof(result, value['request_id'])
    signature = sign(proof, profile.key_generation, profile.key)
    return {'worker_generation': str(profile.key_generation), 'worker_signature': signature,
            'proof': proof.decode('ascii')}


def write_review(path, artifact):
    with directory_fd(path.parent) as parent:
        private_directory(parent)
        temporary = '.stead-review-' + secrets.token_hex(12)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb') as output:
                output.write(encoded(artifact))
                output.flush()
                os.fsync(output.fileno())
            os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        finally:
            os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--review-request', type=Path)
    parser.add_argument('--review-output', type=Path)
    parser.add_argument('--home')
    parser.add_argument('--project')
    parser.add_argument('--authority-epoch')
    args = parser.parse_args(argv)
    review_args = (args.review_request, args.review_output, args.home, args.project, args.authority_epoch)
    if any(review_args) and not all(review_args):
        parser.error('A reviewed promotion needs the request, output, Home, project and authority epoch.')
    try:
        profile = load(args.profile)
        if args.review_request:
            scope = {'home': args.home, 'project_id': args.project, 'repository_id': args.project,
                     'authority_epoch': args.authority_epoch}
            with held_file(exact_path(str(args.review_request)), MAX_PROFILE, secret=True) as source:
                value = decoded(source.read(MAX_PROFILE + 1), MAX_PROFILE)
            with worker(profile) as verify:
                artifact = review_request(value, scope, verify, profile)
            write_review(exact_path(str(args.review_output)), artifact)
        else:
            serve(profile)
    except (OSError, RecoveryError, GuardError, subprocess.SubprocessError):
        print('Stead Git worker could not start or continue with the selected private profile.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

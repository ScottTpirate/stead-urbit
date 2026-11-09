#!/usr/bin/env python3
"""Run an allowlisted exact-Git recipe on a separately provisioned worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import socket
import stat
import subprocess
import sys
import tempfile

JOB_FIELDS = {
    'protocol', 'project_id', 'proposal_id', 'proposal_revision', 'job_id',
    'attempt', 'commit', 'source', 'recipe', 'bundle_sha256',
}
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
SHA256 = re.compile(r'[0-9a-f]{64}')
OID = re.compile(r'[0-9a-f]{40}')
RECIPE = 'stead.build.git-tree-manifest/1'
RECIPE_SHA256 = hashlib.sha256(RECIPE.encode('ascii')).hexdigest()
MAX_BUNDLE = 2 * 1024 * 1024
MAX_OBJECT_BYTES = 4 * 1024 * 1024
MAX_OBJECTS = 256
MAX_BLOB = 256 * 1024
MAX_GIT_OUTPUT = 128 * 1024
MAX_ARTIFACT = 8192
NAMESPACES = ('net', 'mnt', 'pid', 'user')
GIT_ENV = {
    'PATH': '/usr/bin:/bin',
    'HOME': '/nonexistent',
    'LANG': 'C.UTF-8',
    'GIT_CONFIG_NOSYSTEM': '1',
    'GIT_CONFIG_GLOBAL': '/dev/null',
    'GIT_CONFIG_SYSTEM': '/dev/null',
    'GIT_ALLOW_PROTOCOL': '',
    'GIT_NO_REPLACE_OBJECTS': '1',
    'GIT_NO_LAZY_FETCH': '1',
    'GIT_TERMINAL_PROMPT': '0',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key')
        value[key] = item
    return value


def match(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def read_input(path, limit, *, private=True):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        owners, forbidden = ({os.getuid()}, 0o077) if private else ({0, os.getuid()}, 0o022)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in owners or info.st_nlink != 1
                or info.st_mode & forbidden or not 0 < info.st_size <= limit):
            raise ValueError('Worker input has unsafe ownership, permissions, file type or size')
        raw = stream.read(limit + 1)
        final = os.fstat(stream.fileno())
        if len(raw) != info.st_size or final.st_mtime_ns != info.st_mtime_ns or final.st_size != info.st_size:
            raise ValueError('Worker input changed during read')
    return raw


def load_job(raw, expected):
    if not match(SHA256, expected) or digest(raw) != expected:
        raise ValueError('Trusted build job digest differs')
    job = json.loads(raw, object_pairs_hook=unique)
    if (not isinstance(job, dict) or job.keys() != JOB_FIELDS or job['protocol'] != 'stead.build-job/1'
            or any(not match(UUID, job[key]) for key in ('project_id', 'proposal_id', 'job_id'))
            or any(type(job[key]) is not int or not 0 < job[key] <= 2 ** 31 - 1
                   for key in ('proposal_revision', 'attempt'))
            or not match(OID, job['commit'])
            or any(not match(SHA256, job[key]) for key in ('source', 'recipe', 'bundle_sha256'))):
        raise ValueError('Invalid exact build job')
    if job['recipe'] != RECIPE_SHA256:
        raise ValueError('Recipe is outside the worker allowlist')
    return job


def check_bundle(raw, job):
    if not raw.startswith(b'# v2 git bundle\n') or digest(raw) != job['bundle_sha256']:
        raise ValueError('Expected a digest-bound Git bundle v2 with SHA-1 objects')


def namespaces():
    return {key: os.readlink('/proc/self/ns/' + key) for key in NAMESPACES}


def sandbox_command(stage, job_sha256, git_sha256, host):
    command = ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--die-with-parent',
               '--clearenv', '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        if path.is_symlink():
            command += ['--symlink', os.readlink(path), str(path)]
        elif path.exists():
            command += ['--ro-bind', str(path), str(path)]
    command += ['--proc', '/proc', '--dev', '/dev', '--size', str(32 * 1024 * 1024), '--tmpfs', '/tmp',
                '--ro-bind', str(stage), '/input', '--chdir', '/tmp',
                '--', '/usr/bin/python3', '-I', '-S', '/input/worker.py', '_isolated',
                job_sha256, git_sha256, encoded(host).decode('utf-8')]
    return command


def verify_isolation(host):
    current = namespaces()
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    caps = ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd')
    if (host.keys() != current.keys() or any(current[key] == host[key] for key in current)
            or [name for _, name in socket.if_nameindex()] != ['lo']
            or any(int(status[key].strip(), 16) != 0 for key in caps) or status['NoNewPrivs'].strip() != '1'
            or set(os.environ) - {'LC_CTYPE', 'PWD'} or os.environ.get('PWD', '/tmp') != '/tmp'
            or any(Path(name).exists() for name in ('/home', '/root', '/etc', '/run', '/authority', '/piers'))
            or not os.statvfs('/input').f_flag & os.ST_RDONLY):
        raise ValueError('Worker namespace, mount or environment isolation differs')
    return {'interfaces': ['lo'], 'namespaces': current, 'read_only_input': True, 'no_capabilities': True}


def limit_resources():
    for key, value in ((resource.RLIMIT_CPU, 8), (resource.RLIMIT_AS, 512 * 1024 * 1024),
                       (resource.RLIMIT_FSIZE, 16 * 1024 * 1024),
                       (resource.RLIMIT_NOFILE, 64), (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(key, (value, value))


def git(*args, limit=MAX_GIT_OUTPUT):
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(['/input/git', '-c', 'pack.threads=1', '-c', 'core.hooksPath=/nonexistent',
                                 '--git-dir=/tmp/source.git', *args],
                                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.DEVNULL,
                                check=False, timeout=6, env=GIT_ENV)
        if result.returncode != 0 or output.tell() > limit:
            raise ValueError('Isolated Git operation failed or exceeded its output bound: ' + args[0])
        output.seek(0)
        return output.read(limit + 1)


def object_sizes():
    raw = git('cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype) %(objectsize)')
    sizes, total = {}, 0
    for line in raw.decode('ascii').splitlines():
        oid, kind, length = line.split(' ')
        size = int(length)
        if (not match(OID, oid) or oid in sizes or kind not in ('commit', 'tree', 'blob', 'tag')
                or len(sizes) >= MAX_OBJECTS or not 0 <= size <= MAX_BLOB):
            raise ValueError('Git object type, count or size exceeds worker profile')
        sizes[oid] = kind, size
        total += size
        if total > MAX_OBJECT_BYTES:
            raise ValueError('Git source exceeds worker object byte bound')
    return sizes


def tree_manifest(commit):
    git('init', '--bare', '--object-format=sha1', '--template=')
    git('bundle', 'verify', '/input/source.bundle')
    git('bundle', 'unbundle', '/input/source.bundle')
    sizes = object_sizes()
    if sizes.get(commit, (None, 0))[0] != 'commit':
        raise ValueError('Exact reviewed Git commit is missing')
    git('update-ref', 'refs/heads/worker', commit)
    git('fsck', '--full', '--strict', commit)
    tree = git('rev-parse', '--verify', commit + '^{tree}').decode('ascii').strip()
    if sizes.get(tree, (None, 0))[0] != 'tree':
        raise ValueError('Exact reviewed Git tree is missing')
    entries, seen, blobs = [], set(), {}
    data = git('ls-tree', '-rtz', '--full-tree', tree)
    if data and not data.endswith(b'\x00'):
        raise ValueError('Truncated Git tree inventory')
    inventory = data.split(b'\x00')[:-1]
    if len(inventory) > 127:
        raise ValueError('Git tree occurrence bound exceeded')
    for row in inventory:
        meta, raw_path = row.split(b'\t', 1)
        mode, kind, oid = meta.decode('ascii').split(' ')
        path = raw_path.decode('utf-8')
        if (path in seen or not 0 < len(raw_path) <= 512 or any(part in ('', '.', '..') for part in path.split('/'))
                or any(ord(char) < 32 or ord(char) == 127 for char in path)
                or sizes.get(oid, (None, 0))[0] != kind):
            raise ValueError('Git tree entry is outside the worker source profile')
        seen.add(path)
        if kind == 'tree' and mode == '040000':
            continue
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('Git tree entry is outside the worker source profile')
        if oid not in blobs:
            size = sizes[oid][1]
            blob = git('cat-file', 'blob', oid, limit=size)
            if len(blob) != size:
                raise ValueError('Git blob size differs from verified inventory')
            blobs[oid] = {'bytes': size, 'sha256': digest(blob)}
        entries.append({'path': path, 'mode': mode, 'oid': oid, **blobs[oid]})
    return {'protocol': 'stead.build.git-tree-manifest/1', 'object_format': 'sha1',
            'commit': commit, 'tree': tree, 'files': entries}


def run_isolated(job_sha256, git_sha256, host):
    limit_resources()
    isolation = verify_isolation(host)
    # Paths are fixed by the sealed mount and checked again in the sandbox.
    job = load_job(Path('/input/job.json').read_bytes(), job_sha256)
    if digest(Path('/input/git').read_bytes()) != git_sha256:
        raise ValueError('Isolated Git binary differs from the trusted pin')
    check_bundle(Path('/input/source.bundle').read_bytes(), job)
    manifest = tree_manifest(job['commit'])
    if len(encoded(manifest)) > MAX_ARTIFACT:
        raise ValueError('Recipe artifact exceeds the worker output bound')
    return {'manifest': manifest, 'isolation': isolation}


def write_new(fd, name, value):
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def run(args):
    if os.getuid() == 0 or not sys.platform.startswith('linux'):
        raise ValueError('Use an unprivileged Linux build worker')
    raw = read_input(args.job, 8192)
    job = load_job(raw, args.job_sha256)
    bundle = read_input(args.bundle, MAX_BUNDLE)
    check_bundle(bundle, job)
    git_bytes = read_input(args.git_binary, 32 * 1024 * 1024, private=False)
    if not match(SHA256, args.git_sha256) or digest(git_bytes) != args.git_sha256:
        raise ValueError('Worker Git binary differs from the trusted pin')
    output = args.output.absolute()
    parent = output.parent.resolve(strict=True)
    if output.parent != parent or output.name in ('', '.', '..'):
        raise ValueError('Worker output requires an exact path under an owned directory')
    directory = os.open(parent, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Worker output parent must be private and owned')
        if os.path.lexists(output):
            raise ValueError('Worker output already exists')
        host = namespaces()
        worker = Path(__file__).read_bytes()
        with tempfile.TemporaryDirectory(prefix='stead-build-input-', dir=parent) as temporary:
            stage = Path(temporary)
            for name, value in (('job.json', raw), ('source.bundle', bundle), ('git', git_bytes),
                                ('worker.py', worker)):
                path = stage / name
                path.write_bytes(value)
                path.chmod(0o500 if name == 'git' else 0o400)
            # Keep the result in a regular file so the sandbox's file-size
            # limit also caps writes to this descriptor. Read only a small
            # bounded response even if a recipe process misbehaves.
            with tempfile.TemporaryFile(dir=stage) as stream:
                result = subprocess.run(sandbox_command(stage, args.job_sha256, args.git_sha256, host),
                                        stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.DEVNULL,
                                        check=False, timeout=20, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
                stream.seek(0)
                response_raw = stream.read(MAX_ARTIFACT + 8193)
        if not 0 < len(response_raw) <= MAX_ARTIFACT + 8192:
            raise ValueError('Isolated worker returned no bounded result')
        response = json.loads(response_raw, object_pairs_hook=unique)
        if result.returncode != 0:
            raise ValueError('Isolated recipe failed: ' + response.get('error', 'worker failure'))
        artifact = encoded(response['manifest'])
        if response['manifest']['commit'] != job['commit'] or len(artifact) > MAX_ARTIFACT:
            raise ValueError('Worker artifact differs from reviewed commit or exceeds its bound')
        artifact_sha256 = digest(artifact)
        receipt = {
            'protocol': 'stead.build-result/1',
            'job': job,
            'job_sha256': args.job_sha256,
            'git_sha256': args.git_sha256,
            'worker_sha256': digest(worker),
            'attestation': {'source': job['source'], 'recipe': job['recipe'],
                            'output': artifact_sha256, 'outcome': 'passed'},
            'artifact': {'name': 'tree-manifest.json', 'bytes': len(artifact), 'sha256': artifact_sha256},
            'isolation': response['isolation'],
        }
        os.mkdir(output.name, 0o700, dir_fd=directory)
        destination = os.open(output.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=directory)
        try:
            # The receipt is published last. An interrupted write does not
            # become a successful worker result or replace a previous one.
            write_new(destination, 'tree-manifest.json', artifact)
            write_new(destination, 'result.json', encoded(receipt))
            os.fsync(destination)
        finally:
            os.close(destination)
        os.fsync(directory)
    finally:
        os.close(directory)
    return receipt


def main():
    os.umask(0o077)
    if sys.argv[1:2] == ['_isolated']:
        if len(sys.argv) != 5:
            raise SystemExit(2)
        try:
            value = run_isolated(sys.argv[2], sys.argv[3], json.loads(sys.argv[4], object_pairs_hook=unique))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            # Only static diagnostics and Git operation names may leave
            # the sandbox. Raw Git diagnostics and source stay private.
            sys.stdout.buffer.write(encoded({'error': str(error) if type(error) is ValueError else type(error).__name__}))
            raise SystemExit(1)
        sys.stdout.buffer.write(encoded(value))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest='command', required=True)
    operations.add_parser('describe')
    worker = operations.add_parser('run')
    for key in ('job', 'bundle', 'git-binary', 'output'):
        worker.add_argument('--' + key, type=Path, required=True)
    for key in ('job-sha256', 'git-sha256'):
        worker.add_argument('--' + key, required=True)
    args = parser.parse_args()
    if args.command == 'describe':
        value = {'protocol': 'stead.build-worker/1', 'recipe': RECIPE, 'recipe_sha256': RECIPE_SHA256}
    else:
        try:
            value = run(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            parser.exit(1, 'Build worker failed: ' + str(error) + '\n')
    sys.stdout.buffer.write(encoded(value))


if __name__ == '__main__':
    main()

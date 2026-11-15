#!/usr/bin/env python3
"""Rehearse Git recovery and one-way mirroring using only private local repositories."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


OID = re.compile(r'[0-9a-f]{40}')
REF_PREFIXES = ('refs/heads/', 'refs/tags/')
ENV = {
    'PATH': '/usr/bin:/bin',
    'LANG': 'C.UTF-8',
    'GIT_CONFIG_NOSYSTEM': '1',
    'GIT_CONFIG_GLOBAL': '/dev/null',
    'GIT_ALLOW_PROTOCOL': 'file',
    'GIT_NO_REPLACE_OBJECTS': '1',
    'GIT_NO_LAZY_FETCH': '1',
    'GIT_OPTIONAL_LOCKS': '0',
    'GIT_TERMINAL_PROMPT': '0',
    'GIT_AUTHOR_NAME': 'Stead Rehearsal',
    'GIT_AUTHOR_EMAIL': 'rehearsal@example.invalid',
    'GIT_AUTHOR_DATE': '2000-01-01T00:00:00Z',
    'GIT_COMMITTER_NAME': 'Stead Rehearsal',
    'GIT_COMMITTER_EMAIL': 'rehearsal@example.invalid',
    'GIT_COMMITTER_DATE': '2000-01-01T00:00:00Z',
}


class RehearsalError(ValueError):
    pass


class Git:
    def __init__(self, binary, path):
        self.binary = binary
        self.path = path

    def run(self, *args, data=None, check=True):
        command = [self.binary, '-C', self.path, '-c', 'core.hooksPath=/dev/null',
                   '-c', 'core.fsmonitor=false', '-c', 'maintenance.auto=false',
                   '-c', 'gc.auto=0', *args]
        executable = Path(self.binary)
        env = ENV.copy()
        if executable.is_absolute() and executable.name == 'git':
            helpers = executable.parent
            if helpers.name == 'bin' and not (helpers / 'git-remote-http').is_file():
                # Installed clients may keep helpers under the same prefix.
                # Never use a different installation's compiled-in path.
                prefix = helpers.parent
                installed = (prefix / 'libexec/git-core', prefix / 'lib/git-core')
                helpers = next((path for path in installed if (path / 'git-remote-http').is_file()), helpers)
            env['GIT_EXEC_PATH'] = str(helpers)
        result = subprocess.run(command, input=data, capture_output=True, env=env,
                                timeout=120, umask=0o077, check=False)
        if check and result.returncode:
            reason = result.stderr.decode(errors='replace').strip()
            raise RehearsalError(f'Git {args[0]} failed ({result.returncode}): {reason}')
        return result

    def init_bare(self, default_branch):
        self.path.mkdir(mode=0o700)
        self.run('init', '--bare', '--template=', '--object-format=sha1')
        self.run('symbolic-ref', 'HEAD', default_branch)

    def refs(self):
        lines = self.run('for-each-ref', '--format=%(objectname) %(refname)').stdout.splitlines()
        return ref_rows(lines)


def ref_rows(lines):
    refs = {}
    for line in lines:
        oid, name = os.fsdecode(line).split(' ', 1)
        if not OID.fullmatch(oid) or name in refs:
            raise RehearsalError('Invalid Git ref inventory')
        refs[name] = oid
    return refs


def validate_source(git, refs, default_branch):
    if default_branch not in refs or not default_branch.startswith('refs/heads/'):
        raise RehearsalError('Pin the default branch in the ref inventory')
    if git.run('rev-parse', '--show-object-format', '--is-shallow-repository').stdout != b'sha1\nfalse\n':
        raise RehearsalError('Use a complete SHA-1 source repository')
    for name, oid in refs.items():
        if not name.startswith(REF_PREFIXES) or not OID.fullmatch(oid):
            raise RehearsalError('Pin each full branch or tag name to its full SHA-1 OID')
        git.run('check-ref-format', name)
        actual = git.run('show-ref', '--verify', '--hash', '--', name).stdout.strip().decode('ascii')
        if actual != oid:
            raise RehearsalError(f'Source ref changed: {name}')


def bundle_digest(path):
    with path.open('rb') as file:
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': digest}


def export_bundle(git, path, refs):
    git.run('bundle', 'create', '--version=2', path, *sorted(refs))
    path.chmod(0o600)
    lines = git.run('bundle', 'list-heads', path).stdout.splitlines()
    if ref_rows(lines) != refs:
        raise RehearsalError('Bundle refs differ from pinned refs')
    return bundle_digest(path)


def recover_bundle(git, path, expected, refs, default_branch):
    if bundle_digest(path) != expected:
        raise RehearsalError('Bundle digest changed before recovery')
    git.init_bare(default_branch)
    git.run('bundle', 'verify', path)
    git.run('fetch', '--atomic', '--no-tags', '--no-write-fetch-head', path,
            *(f'{name}:{name}' for name in sorted(refs)))
    if git.refs() != refs:
        raise RehearsalError('Recovered refs differ from pinned refs')
    git.run('fsck', '--full', '--strict', '--no-reflogs', '--no-dangling')


def reachable_workload(git, refs):
    roots = ''.join(f'{oid}\n' for oid in sorted(set(refs.values()))).encode('ascii')
    objects = git.run('rev-list', '--objects', '--no-object-names', '--stdin', data=roots).stdout
    oids = sorted(objects.splitlines())
    sizes_raw = git.run('cat-file', '--batch-check=%(objecttype) %(objectsize)', data=objects).stdout
    counts = {'blob': 0, 'commit': 0, 'tree': 0, 'tag': 0}
    sizes = []
    for line in sizes_raw.splitlines():
        kind, size = line.decode('ascii').split(' ')
        if kind not in counts or not size.isdecimal():
            raise RehearsalError('Reachable object is unavailable')
        counts[kind] += 1
        sizes.append(int(size))
    if not sizes or len(sizes) != len(oids):
        raise RehearsalError('Reachable object inventory is incomplete')
    return {'object_count': len(sizes), 'object_kinds': counts,
            'object_ids_sha256': hashlib.sha256(b'\n'.join(oids) + b'\n').hexdigest(),
            'total_object_bytes': sum(sizes), 'largest_object_bytes': max(sizes)}


def add_test_commit(git, branch, prior, message):
    tree = git.run('rev-parse', f'{prior}^{{tree}}').stdout.strip().decode('ascii')
    oid = git.run('commit-tree', tree, '-p', prior, '-m', message).stdout.strip().decode('ascii')
    git.run('update-ref', branch, oid, prior)
    return oid


def mirror_advance(authority, mirror, branch, previous, current):
    # Check all tracked refs before this local operation. The lease also checks
    # the destination branch at the time receive-pack accepts the update.
    if mirror.refs() != previous or authority.refs() != current:
        return False
    authority.run('merge-base', '--is-ancestor', previous[branch], current[branch])
    authority.run('push', '--atomic', f'--force-with-lease={branch}:{previous[branch]}',
                  mirror.path, f'{current[branch]}:{branch}')
    if mirror.refs() != current:
        raise RehearsalError('Mirror refs differ after publication')
    return True


def rehearse(binary, source, output, refs, default_branch):
    source_git = Git(binary, source.resolve(strict=True))
    validate_source(source_git, refs, default_branch)
    output.mkdir(mode=0o700)
    output = output.resolve(strict=True)
    initial = output / 'source.bundle'
    final = output / 'rehearsal.bundle'
    source_archive = export_bundle(source_git, initial, refs)
    with tempfile.TemporaryDirectory(prefix='peers-', dir=output) as directory:
        authority = Git(binary, Path(directory) / 'authority.git')
        mirror = Git(binary, Path(directory) / 'mirror.git')
        for repo in (authority, mirror):
            recover_bundle(repo, initial, source_archive, refs, default_branch)
        workload = reachable_workload(authority, refs)
        accepted = add_test_commit(authority, default_branch, refs[default_branch],
                                   'Rehearse a Stead-accepted ref advance')
        mirrored_refs = refs | {default_branch: accepted}
        if not mirror_advance(authority, mirror, default_branch, refs, mirrored_refs):
            raise RehearsalError('Expected local mirror update was refused')
        next_commit = add_test_commit(authority, default_branch, accepted,
                                      'Rehearse the next Stead-accepted ref advance')
        drift = add_test_commit(mirror, default_branch, accepted, 'Simulate an unexpected mirror write')
        accepted_refs = refs | {default_branch: next_commit}
        if mirror_advance(authority, mirror, default_branch, mirrored_refs, accepted_refs):
            raise RehearsalError('Unexpected mirror write was overwritten')
        if mirror.refs() != refs | {default_branch: drift} or authority.refs() != accepted_refs:
            raise RehearsalError('Ref changed after the refused mirror update')
        accepted_workload = reachable_workload(authority, accepted_refs)
        recovery_archive = export_bundle(authority, final, accepted_refs)

    # Both local peers are now gone. Restore without a GitHub or Stead app.
    with tempfile.TemporaryDirectory(prefix='recovery-', dir=output) as directory:
        recovered = Git(binary, Path(directory) / 'recovered.git')
        recover_bundle(recovered, final, recovery_archive, accepted_refs, default_branch)
        final_workload = reachable_workload(recovered, accepted_refs)
    if final_workload != accepted_workload or final_workload['object_count'] != workload['object_count'] + 2:
        raise RehearsalError('Recovered history differs from source plus two test commits')

    report = {
        'format': 'stead.dogfood-git-rehearsal/1',
        'status': 'passed',
        'scope': 'local-stock-git-only',
        'git_version': source_git.run('--version').stdout.decode('ascii').strip(),
        'default_branch': default_branch,
        'source': {'refs': refs, 'bundle': source_archive, **workload},
        'mirror': {'published_refs': mirrored_refs, 'drift_oid': drift, 'drift_refused': True},
        'recovery': {'refs': accepted_refs, 'bundle': recovery_archive, **final_workload},
    }
    fd = os.open(output / 'report.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, help='New private directory for bundles and the report')
    parser.add_argument('--ref', action='append', required=True, metavar='REF=OID')
    parser.add_argument('--default-branch', default='refs/heads/main')
    parser.add_argument('--git', default='git', help='Stock Git executable')
    args = parser.parse_args()
    try:
        binary = shutil.which(args.git)
        if binary is None:
            raise RehearsalError('Git executable is unavailable')
        refs = {}
        for item in args.ref:
            name, separator, oid = item.rpartition('=')
            if not separator or name in refs:
                raise RehearsalError('Supply each ref once as REF=OID')
            refs[name] = oid
        rehearse(Path(binary).resolve(strict=True), args.source, args.output, refs, args.default_branch)
    except (OSError, subprocess.TimeoutExpired, RehearsalError) as error:
        parser.exit(1, f'{error}\n')
    print(args.output / 'report.json')


if __name__ == '__main__':
    main()

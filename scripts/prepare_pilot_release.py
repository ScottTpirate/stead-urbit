#!/usr/bin/env python3
"""Prepare locally verified pilot artifacts from a reviewed Git commit.

Both native packages use the release profiles declared by that commit. Commit
the intended desk and frontend assets and prepare the pinned kernel cache first.
The output contains the archives, target profiles, verification records, and
receipt.json. Live host compatibility and installation require separate checks.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

from package_release import ROOT, digest, git, source_identity, write_new
from package_sdk import encoded, held_parent, require, unique


TOOLS = ('scripts/urbit', 'scripts/package_release.py', 'scripts/package_sdk.py')
TOOL_PATH = re.compile(r'scripts/(?:urbit/(?:[a-z0-9_]+/)*[a-z0-9_]+\.py|package_(?:release|sdk)\.py)')
RELAY_IMPORTS = {'scripts/urbit/' + name for name in (
    'git_pack_browse.py', 'git_pack_browse_http.py', 'git_pack_changes.py', 'git_pack_relay_service.py',
)}
MAX_TOOLS = 16 * 1024 * 1024
MAX_TOOL = 2 * 1024 * 1024


def tools_archive(source):
    objects = {}
    for row in git(ROOT, 'ls-tree', '-r', '-l', '-z', source, '--', *TOOLS).split(b'\0')[:-1]:
        metadata, name = row.decode().split('\t', 1)
        mode, kind, oid, size = metadata.split()
        require(kind == 'blob' and mode in ('100644', '100755') and TOOL_PATH.fullmatch(name),
                'Unexpected relay tool input: ' + name)
        require(int(size) <= MAX_TOOL, 'Relay tool exceeds its byte limit: ' + name)
        objects[name] = (oid, int(size))
    require(RELAY_IMPORTS.union(TOOLS[1:]) <= objects.keys() and len(objects) <= 300,
            'Incomplete or oversized relay tool inventory')
    require(sum(size for _, size in objects.values()) <= MAX_TOOLS, 'Relay tool files exceed their total byte limit')
    directories = {str(parent) for name in objects for parent in Path(name).parents if parent.parts}
    raw = git(ROOT, '-c', 'tar.umask=0022', 'archive', '--format=tar', source, '--', *TOOLS)
    require(len(raw) <= MAX_TOOLS, 'Relay tools archive exceeds its byte limit')
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for entry in archive:
            require(entry.name not in seen, 'Duplicate relay tool archive entry')
            seen.add(entry.name)
            if entry.isdir():
                require(entry.name in directories, 'Unexpected relay tool archive directory')
                continue
            require(entry.isfile() and entry.name in objects, 'Unexpected relay tool archive file')
            expected_oid, expected_size = objects[entry.name]
            require(entry.size == expected_size, 'Relay tool size differs from its committed blob')
            with archive.extractfile(entry) as stream:
                content = stream.read()
            header = f'blob {len(content)}\0'.encode()
            oid = hashlib.sha1(header + content, usedforsecurity=False).hexdigest()
            require(oid == expected_oid, 'Relay tool content differs from its committed blob')
    require(objects.keys() <= seen, 'Relay tool archive omitted committed files')
    return raw, len(objects)


def package(*args):
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/package_release.py'), *args],
                            cwd=ROOT, stdout=subprocess.PIPE, check=True, timeout=120)
    return json.loads(result.stdout, object_pairs_hook=unique)


def prepare_role(source, output, role):
    archive = output / f'{role}.tar'
    target = output / f'{role}-target.json'
    verification = output / f'{role}-verify.json'
    built = package('build', '--role', role, '--source', source, '--output', archive)
    profile = built['target_profile']
    require(built['source_commit'] == source and profile['role'] == role,
            'Built package has an unexpected source or role')
    write_new(ROOT, target, encoded(profile))
    verified = package('verify', '--archive', archive, '--sha256', built['sha256'], '--target', target)
    require(verified == {**built, 'operation': 'verify'} and verified['native_execution'] is False
            and verified['qualification'] is False, 'Package verification does not match the build')
    write_new(ROOT, verification, encoded(verified))
    return {'archive': archive.name, 'bytes': verified['bytes'], 'sha256': verified['sha256'],
            'target': target.name, 'verification': verification.name}


def create_output(output):
    (ROOT / output.parent).mkdir(mode=0o700, exist_ok=True)
    with held_parent(ROOT, output) as (parent, leaf, check_binding):
        info = os.fstat(parent)
        require(info.st_uid == os.geteuid() and info.st_mode & 0o022 == 0,
                'The .runtime directory must be owned by the operator and protected from other writers')
        os.mkdir(leaf, mode=0o700, dir_fd=parent)
        check_binding()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Exactly 40 lowercase hex characters for a reviewed commit')
    parser.add_argument('--output', required=True, help='New private checkout-relative directory, .runtime/NAME')
    args = parser.parse_args()
    try:
        require(re.fullmatch(r'[0-9a-f]{40}', args.source) and source_identity(ROOT, args.source) == args.source,
                'Supply the full commit ID of the reviewed source')
        require(re.fullmatch(r'\.runtime/[A-Za-z0-9][A-Za-z0-9_.-]*', args.output),
                'Output must be a new directory named .runtime/NAME')
        output = Path(args.output)
        create_output(output)
        tools, count = tools_archive(args.source)
        artifacts = {role: prepare_role(args.source, output, role) for role in ('home', 'identity')}
        write_new(ROOT, output / 'tools.tar', tools)
        artifacts['relay_tools'] = {'archive': 'tools.tar', 'bytes': len(tools), 'sha256': digest(tools),
                                   'committed_files': count}
        receipt = {'protocol': 'stead.pilot-preparation/1', 'classification': 'offline-package-integrity-only',
                   'source_commit': args.source, 'artifacts': artifacts, 'native_execution': False,
                   'qualification': False}
        write_new(ROOT, output / 'receipt.json', encoded(receipt))
        print(json.dumps(receipt, sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Pilot preparation failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()

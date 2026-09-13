#!/usr/bin/env python3
"""Fetch only reviewed pins. Hash mismatch is fatal; there is no latest fallback."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from digests import sha, tree_sha

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.runtime'
LOCK_PATH = ROOT / 'specs/urbit/toolchain.lock.json'


def lock():
    data = json.loads(LOCK_PATH.read_text())
    if data['format'] != 1 or data['profile'] != 'linux-x86_64-fake-only':
        raise ValueError('Unsupported executable lock')
    return data


def checked(path, expected):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or sha(path) != expected:
        raise ValueError(f'Missing or changed pinned file: {path}')


def verify():
    data = lock()
    if CACHE.is_symlink():
        raise ValueError('Refusing symlinked runtime cache')
    for key in ('runtime', 'kernel', 'boot_artifact', 'frontend'):
        item = data[key]
        checked(CACHE / 'downloads' / item['archive'], item['sha256'])
    checked(CACHE / data['runtime']['binary'], data['runtime']['binary_sha256'])
    kernel = CACHE / data['kernel']['directory']
    if tree_sha(kernel, source_links=True) != data['kernel']['source_tree_sha256']:
        raise ValueError('Pinned Arvo/desk source tree changed')
    checked(ROOT / data['frontend']['lockfile'], data['frontend']['lock_sha256'])
    checked(ROOT / data['protocol_corpus']['path'], data['protocol_corpus']['sha256'])
    git = subprocess.check_output(['git', '--version'], text=True).strip()
    if git != 'git version ' + data['host_tools']['git']:
        raise ValueError(f'Git version differs from tested corpus: {git}')
    node = CACHE / data['frontend']['directory'] / 'bin/node'
    checked(node, data['frontend']['binary_sha256'])
    version = subprocess.check_output([str(node), '--version'], text=True).strip()
    if version != 'v' + data['frontend']['node']:
        raise ValueError('Node version mismatch')
    return data


def fetch():
    if CACHE.is_symlink():
        raise ValueError('Refusing symlinked runtime cache')
    CACHE.mkdir(mode=0o700, exist_ok=True)
    downloads = CACHE / 'downloads'
    if downloads.is_symlink() or (CACHE / 'bin').is_symlink():
        raise ValueError('Refusing redirected cache directory')
    downloads.mkdir(exist_ok=True)
    data = lock()
    for key in ('runtime', 'kernel', 'boot_artifact', 'frontend'):
        item = data[key]
        path = downloads / item['archive']
        if not path.exists():
            print('Downloading', item['url'], flush=True)
            # Exclusive unpredictable file in the checked directory, never an
            # attacker-prepared predictable .partial symlink.
            with tempfile.NamedTemporaryFile(dir=downloads, delete=False) as out:
                partial = Path(out.name)
                try:
                    with urllib.request.urlopen(item['url'], timeout=60) as src:
                        shutil.copyfileobj(src, out)
                    out.flush()
                    os.fsync(out.fileno())
                    checked(partial, item['sha256'])
                    partial.replace(path)
                finally:
                    partial.unlink(missing_ok=True)
        checked(path, item['sha256'])
        if key == 'runtime':
            destination = CACHE / 'bin'
            destination.mkdir(exist_ok=True)
            target = CACHE / item['binary']
        elif key in ('kernel', 'frontend'):
            destination = CACHE
            target = CACHE / item['directory']
        else:
            continue
        if target.is_symlink():
            raise ValueError('Refusing redirected extraction target')
        if not target.exists():
            with tarfile.open(path) as archive:
                archive.extractall(destination, filter='data')
    verify()
    print('PASS pinned downloads, binary, Arvo tree, Git and Node versions')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['fetch', 'verify'])
    args = parser.parse_args()
    try:
        fetch() if args.command == 'fetch' else verify()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f'FAIL: {error}\n')

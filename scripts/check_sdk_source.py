"""Bind the canonical v3 SDK archive to committed public Git blobs, without Urbit.

This verifies source/package identity, not a publisher signature or native
consumer conformance. No archive member is extracted or executed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

import package_sdk_v3 as sdk
from package_sdk import ROOT, MAX_ARCHIVE, MAX_FILE, read_bounded, require


def git_bytes(root, arguments, maximum):
    """Bounded raw object reads with replacements and lazy fetching disabled."""
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
        'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_NO_LAZY_FETCH': '1',
        'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
    command = ['/usr/bin/git', '--no-replace-objects', '--no-lazy-fetch', '--literal-pathspecs',
        '-c', 'core.fsmonitor=false', '-C', str(root), *arguments]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
    deadline = time.monotonic() + 10
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    limits = {'stdout': maximum, 'stderr': 4096}
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
            selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
            while selector.get_map():
                remaining = deadline - time.monotonic()
                require(remaining > 0, 'SDK Git read timed out')
                for key, _ in selector.select(remaining):
                    name = key.data
                    data = os.read(key.fd, min(4096, limits[name] - len(output[name]) + 1))
                    if not data:
                        selector.unregister(key.fileobj)
                    output[name].extend(data)
                    require(len(output[name]) <= limits[name], 'SDK Git output exceeds its bound')
        require(process.wait(timeout=max(.001, deadline - time.monotonic())) == 0
            and not output['stderr'], 'SDK Git object read failed')
        return bytes(output['stdout'])
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        process.stdout.close()
        process.stderr.close()


def check(root, archive):
    root = Path(root).resolve(strict=True)
    expected, manifest = sdk.archive_bytes(root)
    raw = read_bounded(root, archive, MAX_ARCHIVE)
    require(raw == expected, 'SDK archive differs from the canonical package')
    commit = manifest['native_source_commit']
    require(git_bytes(root, ['rev-parse', '--verify', commit + '^{commit}'], 64)
        == (commit + '\n').encode(), 'SDK source identity is not the exact commit')
    records = [*manifest['files'], {'source': 'specs/urbit/toolchain.lock.json',
        'bytes': len(read_bounded(root, 'specs/urbit/toolchain.lock.json')),
        'sha256': manifest['runtime_lock_sha256']}]
    bindings = []
    for record in records:
        source = record['source']
        entry = git_bytes(root, ['ls-tree', '-z', commit, '--', source], 1024)
        require(entry.endswith(b'\0') and entry.count(b'\0') == 1, 'SDK Git entry missing or ambiguous')
        header, name = entry[:-1].split(b'\t')
        mode, kind, oid = header.decode('ascii').split(' ')
        require(mode == '100644' and kind == 'blob' and name == source.encode(), 'SDK Git entry is not the exact regular source')
        size = git_bytes(root, ['cat-file', '-s', oid], 32)
        require(size == (str(record['bytes']) + '\n').encode(), 'SDK Git blob size differs')
        data = git_bytes(root, ['cat-file', 'blob', oid], MAX_FILE)
        require(len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256'],
            'SDK Git source bytes differ: ' + source)
        require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid,
            'SDK Git blob object identity differs')
        bindings.append({'source': source, 'git_blob_oid': oid, 'bytes': len(data), 'sha256': record['sha256']})
    return {'status': 'pass', 'classification': 'real-host-sdk-package-and-git-source-binding',
        'native_execution': False, 'independent_consumer_execution': False,
        'source_commit': commit, 'package_sha256': hashlib.sha256(raw).hexdigest(),
        'package_bytes': len(raw), 'files': bindings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--archive', required=True, help='Checkout-relative canonical v3 archive')
    args = parser.parse_args()
    print(json.dumps(check(args.root, args.archive), sort_keys=True))


if __name__ == '__main__':
    main()

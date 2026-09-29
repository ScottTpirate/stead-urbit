"""Canonical public SDK v3 package; independent of the preserved v2 lock."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile
from package_sdk import ROOT, MAX_ARCHIVE, MAX_FILE, encoded, held_parent, read_bounded, require, unique

VERSION = '0.2.0-alpha'
EXPORTS = {
    **{'native/core/desk/lib/' + name + '.hoon': 'desk-dev/lib/' + name + '.hoon'
       for name in ('stead-codec', 'stead-team-codec', 'stead-update-codec', 'stead-delivery')},
    **{'native/core/desk/mar/' + name + '.hoon': 'desk-dev/mar/' + name + '.hoon'
       for name in ('stead-command-3', 'stead-query-3', 'stead-updates-3', 'stead-result-3')},
    'sdk/v3/desk-dev/ted/stead-sdk-call.hoon': 'desk-dev/ted/stead-sdk-call.hoon',
    'sdk/v3/README.md': 'README.md', 'sdk/v3/API.md': 'API.md',
    'LICENSE': 'LICENSE', 'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
}


def archive_bytes(root=ROOT):
    raw_lock = read_bounded(root, 'sdk/v3/export-lock.json', 65536)
    lock = json.loads(raw_lock, object_pairs_hook=unique)
    require(set(lock) == {'protocol', 'sdk_version', 'native_source_commit', 'api_version',
                         'kernel_kelvin', 'runtime_lock_sha256', 'files'}, 'SDK v3 lock shape')
    require(lock['protocol'] == 'stead.sdk-exports/1' and lock['sdk_version'] == VERSION
            and type(lock['api_version']) is int and lock['api_version'] == 3
            and type(lock['kernel_kelvin']) is int and lock['kernel_kelvin'] == 408
            and isinstance(lock['native_source_commit'], str)
            and re.fullmatch(r'[0-9a-f]{40}', lock['native_source_commit']), 'SDK v3 identity')
    require(set(lock['files']) == set(EXPORTS), 'SDK v3 exact export list')
    toolchain_raw = read_bounded(root, 'specs/urbit/toolchain.lock.json')
    require(hashlib.sha256(toolchain_raw).hexdigest() == lock['runtime_lock_sha256'], 'SDK v3 toolchain differs')
    toolchain = json.loads(toolchain_raw, object_pairs_hook=unique)
    require(toolchain['kernel']['kelvin'] == 408, 'SDK v3 Kelvin')
    members, inventory = {}, []
    for source, target in sorted(EXPORTS.items()):
        raw = read_bounded(root, source)
        pin = lock['files'][source]
        require(set(pin) == {'bytes', 'sha256'} and type(pin['bytes']) is int
                and 0 < pin['bytes'] <= MAX_FILE and pin['bytes'] == len(raw)
                and pin['sha256'] == hashlib.sha256(raw).hexdigest(), 'SDK v3 export differs: ' + source)
        members[target] = raw
        inventory.append({'source': source, 'path': target, **pin})
    manifest = {'protocol': 'stead.sdk-package/1', 'sdk_version': VERSION, 'api_version': 3,
        'kind': 'desk-dev-library-fragment', 'command_protocol': 'stead.command/3',
        'query_protocol': 'stead.query/3', 'update_protocol': 'stead.updates/3', 'receipt_protocol': 'stead.receipt/3',
        'native_source_commit': lock['native_source_commit'], 'runtime_lock_sha256': lock['runtime_lock_sha256'],
        'export_lock_sha256': hashlib.sha256(raw_lock).hexdigest(),
        'packager_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'shared_packager_sha256': hashlib.sha256(Path(__file__).with_name('package_sdk.py').read_bytes()).hexdigest(),
        'kernel_kelvin': 408, 'kernel_commit': toolchain['kernel']['commit'], 'runtime_version': toolchain['runtime']['version'],
        'files': sorted(inventory, key=lambda item: item['path']),
        'qualification': 'Package integrity only; native consumer conformance is separate evidence.'}
    members['manifest.json'] = encoded(manifest)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in sorted(members.items()):
            item = tarfile.TarInfo('stead-sdk-v3/' + name)
            item.size, item.mode, item.mtime = len(raw), 0o644, 0
            item.uid = item.gid = 0
            item.uname = item.gname = ''
            archive.addfile(item, io.BytesIO(raw))
    raw = buffer.getvalue()
    require(len(raw) <= MAX_ARCHIVE, 'SDK v3 archive bound')
    return raw, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('build', 'verify'))
    parser.add_argument('--archive', required=True, help='Checkout-relative archive path; existing parent required')
    args = parser.parse_args()
    raw, manifest = archive_bytes()
    if args.operation == 'verify':
        require(read_bounded(ROOT, args.archive, MAX_ARCHIVE) == raw, 'SDK v3 archive differs')
    else:
        with held_parent(ROOT, args.archive) as (parent, leaf, check_binding):
            descriptor = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(raw)
            check_binding()
    print(json.dumps({'status': 'passed', 'classification': 'real-host-offline-package', 'native_execution': False,
        'sdk_version': manifest['sdk_version'], 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}))


if __name__ == '__main__':
    main()

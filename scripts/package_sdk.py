"""Build or verify the pinned public SDK fragment without starting Urbit.

Verification compares the complete canonical archive to this checkout's reviewed
export lock. It never extracts or executes an input archive and is not a signature
or a native consumer-conformance test.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-preview'
KELVIN = 408
MAX_FILE = 128 * 1024
MAX_ARCHIVE = 1024 * 1024
EXPORTS = {
    'native/core/desk/lib/stead-codec.hoon': 'desk-dev/lib/stead-codec.hoon',
    'native/core/desk/lib/stead-delivery.hoon': 'desk-dev/lib/stead-delivery.hoon',
    'native/core/desk/mar/stead-command-2.hoon': 'desk-dev/mar/stead-command-2.hoon',
    'native/core/desk/mar/stead-result-2.hoon': 'desk-dev/mar/stead-result-2.hoon',
    'LICENSE': 'LICENSE',
    'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
    'sdk/README.md': 'README.md',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def checked_path(root, name, *, output=False):
    relative = Path(name)
    require(not relative.is_absolute() and bool(relative.parts)
            and '..' not in relative.parts, 'Path must be relative to the checkout')
    root = Path(root).resolve(strict=True)
    current = root
    for index, part in enumerate(relative.parts):
        current /= part
        last = index == len(relative.parts) - 1
        if output and last:
            require(not current.exists() and not current.is_symlink(), 'Output already exists')
            break
        mode = current.lstat().st_mode
        require(not stat.S_ISLNK(mode), 'Symlink input or parent is not permitted')
        require(stat.S_ISREG(mode) if last else stat.S_ISDIR(mode), 'Wrong input file type')
    return current


def read_bounded(root, name, limit=MAX_FILE):
    path = checked_path(root, name)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'Input must be a regular file')
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'Input exceeds its byte limit: ' + str(name))
    return raw


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def archive_bytes(root=ROOT):
    lock_raw = read_bounded(root, 'sdk/export-lock.json', 64 * 1024)
    lock = json.loads(lock_raw, object_pairs_hook=unique)
    require(isinstance(lock, dict) and set(lock) == {
        'protocol', 'sdk_version', 'native_source_commit', 'api_version',
        'kernel_kelvin', 'runtime_lock_sha256', 'files'}, 'Unknown SDK lock shape')
    require(lock['protocol'] == 'stead.sdk-exports/1' and lock['sdk_version'] == VERSION
            and type(lock['api_version']) is int and lock['api_version'] == 2
            and type(lock['kernel_kelvin']) is int and lock['kernel_kelvin'] == KELVIN,
            'Unsupported SDK, API or Kelvin version')
    require(isinstance(lock['native_source_commit'], str)
            and re.fullmatch(r'[0-9a-f]{40}', lock['native_source_commit']), 'Invalid source identity')
    require(isinstance(lock['files'], dict) and set(lock['files']) == set(EXPORTS),
            'Export lock must contain exactly the public files and notices')
    toolchain_raw = read_bounded(root, 'specs/urbit/toolchain.lock.json')
    require(hashlib.sha256(toolchain_raw).hexdigest() == lock['runtime_lock_sha256'],
            'Pinned toolchain bytes changed')
    toolchain = json.loads(toolchain_raw, object_pairs_hook=unique)
    require(toolchain['kernel']['kelvin'] == KELVIN, 'Unsupported toolchain Kelvin')
    members, inventory = {}, []
    for source, target in sorted(EXPORTS.items()):
        pin = lock['files'][source]
        require(isinstance(pin, dict) and set(pin) == {'bytes', 'sha256'}
                and type(pin['bytes']) is int and 0 < pin['bytes'] <= MAX_FILE
                and isinstance(pin['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']),
                'Invalid export pin: ' + source)
        raw = read_bounded(root, source)
        require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
                'Pinned export bytes changed: ' + source)
        members[target] = raw
        inventory.append({'path': target, 'source': source, **pin})
    manifest = {
        'protocol': 'stead.sdk-package/1', 'sdk_version': VERSION,
        'kind': 'desk-dev-library-fragment', 'api_version': 2,
        'command_protocol': 'stead.command/2', 'receipt_protocol': 'stead.receipt/2',
        'native_source_commit': lock['native_source_commit'],
        'export_lock_sha256': hashlib.sha256(lock_raw).hexdigest(),
        'packager_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime_lock_sha256': lock['runtime_lock_sha256'],
        'kernel_kelvin': KELVIN, 'kernel_commit': toolchain['kernel']['commit'],
        'runtime_version': toolchain['runtime']['version'],
        'files': sorted(inventory, key=lambda row: row['path']),
        'qualification': 'Package integrity only; independent consumer compilation and full API conformance remain unexecuted.',
    }
    members['manifest.json'] = encoded(manifest)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in sorted(members.items()):
            info = tarfile.TarInfo('stead-sdk-v2/' + name)
            info.size, info.mode, info.mtime = len(raw), 0o644, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            archive.addfile(info, io.BytesIO(raw))
    raw = buffer.getvalue()
    require(len(raw) <= MAX_ARCHIVE, 'SDK archive exceeds its byte limit')
    return raw, manifest


def build(root, output):
    raw, manifest = archive_bytes(root)
    target = checked_path(root, output, output=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
    return raw, manifest


def verify(root, archive):
    expected, manifest = archive_bytes(root)
    actual = read_bounded(root, archive, MAX_ARCHIVE)
    require(actual == expected, 'Archive differs from this checkout\'s pinned canonical package')
    return actual, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Reviewed checkout root')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('build').add_argument('--output', required=True, help='New checkout-relative .tar path; parent must exist')
    commands.add_parser('verify').add_argument('--archive', required=True, help='Checkout-relative .tar path')
    args = parser.parse_args(argv)
    try:
        raw, manifest = (build(args.root, args.output) if args.command == 'build'
                         else verify(args.root, args.archive))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('SDK package failed: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps({'status': 'passed', 'operation': args.command,
        'classification': 'real-host-offline-package', 'native_execution': False,
        'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'public_hoon_files': 4, 'sdk_version': manifest['sdk_version']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

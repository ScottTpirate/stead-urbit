"""Prepare public-only SDK builder inputs; this does not start or qualify Urbit."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import tarfile

import check_sdk_source
import package_sdk_v3 as sdk
from package_sdk import ROOT, MAX_ARCHIVE, MAX_FILE, encoded, held_parent, identity, open_directory, read_bounded, require


def members(raw, manifest):
    """Unpack only already source-bound canonical bytes, never tar.extract."""
    expected = {row['path']: row for row in manifest['files']}
    expected['manifest.json'] = {'bytes':len(encoded(manifest)), 'sha256':hashlib.sha256(encoded(manifest)).hexdigest()}
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for item in archive:
            require(item.name.startswith('stead-sdk-v3/'), 'SDK archive prefix differs')
            name = item.name.removeprefix('stead-sdk-v3/')
            require(name in expected and 'sdk/' + name not in result and item.isfile()
                and 0 < item.size <= MAX_FILE, 'SDK archive member differs')
            with archive.extractfile(item) as source:
                body = source.read(MAX_FILE + 1)
            pin = expected[name]
            require(len(body) == item.size == pin['bytes'] and hashlib.sha256(body).hexdigest() == pin['sha256'],
                'SDK archive member identity differs')
            result['sdk/' + name] = body
    require(set(result) == {'sdk/' + name for name in expected}, 'SDK archive member inventory differs')
    return result


def write_new(root_fd, name, raw):
    parts = Path(name).parts
    require(parts and not Path(name).is_absolute() and not {'.', '..'} & set(parts), 'Invalid prepared input path')
    parent = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
            child = open_directory(part, dir_fd=parent)
            os.close(parent)
            parent = child
        descriptor = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=parent)
        with os.fdopen(descriptor, 'wb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    finally:
        os.close(parent)


def verify_directory(root_fd, files):
    """Bounded exact tree readback through held, nonredirectable descriptors."""
    expected = {}
    for name, raw in files.items():
        branch = expected
        for part in Path(name).parts[:-1]:
            branch = branch.setdefault(part, {})
        branch[Path(name).name] = raw

    def visit(descriptor, branch):
        info = os.fstat(descriptor)
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
                'Prepared directory is not private and owned')
        seen = set()
        with os.scandir(descriptor) as entries:
            for entry in entries:
                require(entry.name in branch and entry.name not in seen, 'Unexpected prepared input')
                seen.add(entry.name)
                expected = branch[entry.name]
                if isinstance(expected, dict):
                    child = open_directory(entry.name, dir_fd=descriptor)
                    try:
                        visit(child, expected)
                    finally:
                        os.close(child)
                else:
                    child = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=descriptor)
                    with os.fdopen(child, 'rb') as source:
                        info = os.fstat(source.fileno())
                        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                                and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600
                                and info.st_size == len(expected), 'Prepared input metadata differs')
                        require(source.read(len(expected) + 1) == expected, 'Prepared input readback differs')
        require(seen == set(branch), 'Prepared input inventory differs')
    visit(root_fd, expected)


def prepare(root, archive, output):
    root = Path(root).resolve(strict=True)
    relative = Path(output)
    require(relative.parent == Path('.runtime') and re.fullmatch(r'sdk-builder-[a-z0-9-]{1,64}', relative.name),
            'Output must be a new .runtime/sdk-builder-NAME directory')
    binding = check_sdk_source.check(root, archive)
    raw = read_bounded(root, archive, MAX_ARCHIVE)
    expected, manifest = sdk.archive_bytes(root)
    require(raw == expected and hashlib.sha256(raw).hexdigest() == binding['package_sha256']
            and len(raw) == binding['package_bytes'], 'SDK package changed after source verification')
    files = members(raw, manifest)
    files['toolchain.json'] = read_bounded(root, 'specs/urbit/toolchain.lock.json')
    require(hashlib.sha256(files['toolchain.json']).hexdigest() == manifest['runtime_lock_sha256'],
            'SDK toolchain changed after source verification')
    receipt = {'protocol':'stead.sdk-builder-inputs/1', 'classification':'real-host-sdk-input-preparation',
        'native_execution':False, 'independent_consumer_execution':False,
        'preparer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_checker_sha256':hashlib.sha256(Path(check_sdk_source.__file__).read_bytes()).hexdigest(),
        'source_binding':binding,
        'files':{name:{'bytes':len(body), 'sha256':hashlib.sha256(body).hexdigest()} for name, body in sorted(files.items())}}
    with held_parent(root, output) as (parent, leaf, check_binding):
        info = os.fstat(parent)
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'Private owned .runtime required')
        os.mkdir(leaf, mode=0o700, dir_fd=parent)  # Existing and partial outputs are never overwritten.
        prepared = open_directory(leaf, dir_fd=parent)
        try:
            def check_prepared():
                check_binding()
                current = open_directory(leaf, dir_fd=parent)
                try:
                    require(identity(prepared) == identity(current), 'Prepared directory changed')
                finally:
                    os.close(current)
            for name, body in sorted(files.items()):
                check_prepared()
                write_new(prepared, name, body)
                require(read_bounded(root, relative / name, MAX_FILE) == body, 'Prepared input readback differs')
            check_prepared()
            verify_directory(prepared, files)
            # A receipt appears only after every intended byte has been read back.
            receipt_bytes = encoded(receipt)
            write_new(prepared, 'inputs.json', receipt_bytes)
            os.fsync(prepared)
            check_prepared()
            verify_directory(prepared, files | {'inputs.json':receipt_bytes})
            check_prepared()
        finally:
            os.close(prepared)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--archive', required=True, help='Checkout-relative source-bound v3 SDK archive')
    parser.add_argument('--output', required=True, help='New .runtime/sdk-builder-NAME directory; never overwritten')
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.archive, args.output), sort_keys=True))


if __name__ == '__main__':
    main()

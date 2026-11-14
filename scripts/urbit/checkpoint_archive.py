"""Bounded exact checkpoint archives and pinned GnuPG AES256-OCB streams.

This module launches no native runtime. The caller must fence and stop the
source and schedule large I/O under the normal execution guard. Encryption is
performed entirely by the installed pinned GnuPG executable, never Python.
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import secrets
from selectors import DefaultSelector, EVENT_READ
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import release_install as install
from execution_policy import directory_fd
from portable_code import private_directory, publish_directory
from portable_recovery import TOKEN, match, require, same_entry, same_path
import paired_recovery as pair

MAX_FILES = 32768
MAX_DIRECTORIES = 4096
MAX_FILE = 512 * 1024 * 1024
MAX_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE = 960 * 1024 * 1024
MAX_CIPHER = 1024 * 1024 * 1024
MAX_SECONDS = 120
NAME = re.compile(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*')


@contextmanager
def new_file(path):
    """Private scratch inode, fsynced before atomic no-replace publication."""
    path = Path(path).absolute()
    with directory_fd(path.parent) as parent:
        before = private_directory(parent)
        name = '.checkpoint-' + secrets.token_hex(16)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        opened = os.fstat(fd)
        try:
            with os.fdopen(fd, 'wb') as output:
                yield output
                output.flush()
                os.fsync(output.fileno())
                require(same_entry(parent, name, opened) and same_path(path.parent, before), 'checkpoint-output-changed')
                os.link(name, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                os.unlink(name, dir_fd=parent)
                os.fsync(parent)
                require(same_entry(parent, path.name, opened) and same_path(path.parent, before), 'checkpoint-output-changed')
        finally:
            if same_entry(parent, name, opened):
                os.unlink(name, dir_fd=parent)


def fingerprint(path, *, installed=False):
    return install.checkpoint_tree(path, installed=installed, maximum_files=MAX_FILES)


def archive_tree(source, destination, *, installed=False):
    source = Path(source).absolute()
    require(not (source / '.vere.lock').exists(), 'checkpoint-source-running')
    expected = fingerprint(source, installed=installed)
    require(expected['bytes'] <= MAX_ARCHIVE - 32 * 1024 * 1024, 'checkpoint-archive-bound')
    deadline = time.monotonic() + MAX_SECONDS
    files = directories = total = 0

    def visit(parent, prefix, archive):
        nonlocal files, directories, total
        for name in sorted(os.listdir(parent)):
            pair.remaining(deadline)
            require(NAME.fullmatch(name) and '/' not in name and name not in ('.', '..'), 'checkpoint-path')
            relative = prefix + name
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            require(info.st_uid == os.getuid() and not info.st_mode & 0o022, 'checkpoint-source-permission')
            header = tarfile.TarInfo(relative)
            header.mtime = 0
            if stat.S_ISDIR(info.st_mode):
                directories += 1
                require(directories <= MAX_DIRECTORIES, 'checkpoint-directory-bound')
                header.type, header.mode = tarfile.DIRTYPE, 0o700
                archive.addfile(header)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                try:
                    require(same_entry(parent, name, os.fstat(child)), 'checkpoint-input-changed')
                    visit(child, relative + '/', archive)
                    require(same_entry(parent, name, os.fstat(child)), 'checkpoint-input-changed')
                finally:
                    os.close(child)
            else:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'checkpoint-special-file')
                files += 1
                total += info.st_size
                require(files <= MAX_FILES and info.st_size <= MAX_FILE and total <= MAX_BYTES, 'checkpoint-file-bound')
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(descriptor, 'rb') as stream:
                    require(pair.file_state(os.fstat(stream.fileno())) == pair.file_state(info), 'checkpoint-input-changed')
                    header.size, header.mode = info.st_size, 0o600
                    archive.addfile(header, stream)
                    require(pair.file_state(os.fstat(stream.fileno())) == pair.file_state(info)
                            and same_entry(parent, name, info), 'checkpoint-input-changed')

    with new_file(destination) as output:
        with directory_fd(source) as parent:
            opened = os.fstat(parent)
            with tarfile.open(fileobj=output, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
                visit(parent, '', archive)
            require(same_path(source, opened), 'checkpoint-input-changed')
        require(output.tell() <= MAX_ARCHIVE and fingerprint(source, installed=installed) == expected
                and not (source / '.vere.lock').exists(), 'checkpoint-source-changed')
        pair.remaining(deadline)
    return expected


def extract_tree(archive_path, destination, expected, *, installed=False):
    require(isinstance(expected, dict) and set(expected) == {'sha256', 'bytes', 'files'}
            and match(TOKEN, expected['sha256']) and type(expected['bytes']) is int
            and 0 < expected['bytes'] <= MAX_BYTES and type(expected['files']) is int
            and 0 < expected['files'] <= MAX_FILES, 'checkpoint-expected-tree')
    destination = Path(destination).absolute()
    deadline = time.monotonic() + MAX_SECONDS
    with directory_fd(destination.parent) as parent:
        parent_info = private_directory(parent)
        name = '.checkpoint-tree-' + secrets.token_hex(16)
        os.mkdir(name, 0o700, dir_fd=parent)
        root = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        opened = os.fstat(root)
        seen, directories, total, files = set(), 0, 0, 0
        try:
            with pair.retained(archive_path, MAX_ARCHIVE, deadline) as (source, _):
                with tarfile.open(fileobj=source, mode='r|') as archive:
                    for member in archive:
                        pair.remaining(deadline)
                        path = member.name
                        require(NAME.fullmatch(path) and all(x not in ('.', '..') for x in path.split('/'))
                                and path not in seen and not member.pax_headers and member.sparse is None,
                                'checkpoint-archive-path')
                        require(member.type in (tarfile.REGTYPE, tarfile.DIRTYPE), 'checkpoint-archive-special')
                        seen.add(path)
                        parts = path.split('/')
                        current = os.dup(root)
                        try:
                            for part in parts[:-1]:
                                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
                                os.close(current)
                                current = child
                            if member.isdir():
                                directories += 1
                                require(directories <= MAX_DIRECTORIES and member.size == 0, 'checkpoint-directory-bound')
                                os.mkdir(parts[-1], 0o700, dir_fd=current)
                            else:
                                files += 1
                                total += member.size
                                require(files <= MAX_FILES and 0 <= member.size <= MAX_FILE and total <= MAX_BYTES,
                                        'checkpoint-file-bound')
                                fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=current)
                                with os.fdopen(fd, 'wb') as output, archive.extractfile(member) as input_file:
                                    remaining = member.size
                                    while remaining:
                                        pair.remaining(deadline)
                                        block = input_file.read(min(pair.CHUNK, remaining))
                                        require(block, 'checkpoint-truncated-archive')
                                        output.write(block)
                                        remaining -= len(block)
                                    output.flush()
                                    os.fsync(output.fileno())
                        finally:
                            os.close(current)
                    while block := archive.fileobj.read(pair.CHUNK):
                        pair.remaining(deadline)
                        require(not block.strip(b'\0'), 'checkpoint-archive-trailing-data')
                # Ignore only tar's conventional zero padding after EOF.
                while block := source.read(pair.CHUNK):
                    pair.remaining(deadline)
                    require(not block.strip(b'\0'), 'checkpoint-archive-trailing-data')
            scratch = destination.parent / name
            require(fingerprint(scratch, installed=installed) == expected
                    and same_entry(parent, name, opened) and same_path(destination.parent, parent_info),
                    'checkpoint-restored-tree-differs')
            for directory, _, _, fd in os.fwalk('.', topdown=False, dir_fd=root):
                os.fsync(fd)
            pair.remaining(deadline)
            publish_directory(parent, name, destination.name)
            os.fsync(parent)
            require(same_entry(parent, destination.name, opened) and same_path(destination.parent, parent_info),
                    'checkpoint-output-changed')
        finally:
            os.close(root)
            # Keep an unpublished private partial tree for inspection on failure.
    return expected


def crypt_file(source, destination, key_path, binary, expected_binary_sha256, *, decrypt=False):
    """Pinned GnuPG streaming AES256-OCB; publish only after authentication."""
    binary = Path(binary).absolute()
    require(match(TOKEN, expected_binary_sha256), 'checkpoint-gpg-pin')
    deadline = time.monotonic() + MAX_SECONDS
    with directory_fd(binary.parent) as directory:
        binary_fd = os.open(binary.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        try:
            before = os.fstat(binary_fd)
            require(stat.S_ISREG(before.st_mode) and before.st_uid in (0, os.getuid())
                    and not before.st_mode & 0o022 and before.st_size <= 16 * 1024 * 1024, 'checkpoint-gpg-boundary')
            digest = hashlib.sha256()
            while block := os.read(binary_fd, pair.CHUNK):
                digest.update(block)
            require(digest.hexdigest() == expected_binary_sha256
                    and pair.file_state(before) == pair.file_state(os.fstat(binary_fd)), 'checkpoint-gpg-pin')
            with pair.retained(source, MAX_CIPHER if decrypt else MAX_ARCHIVE, deadline) as (input_file, _), \
                    pair.retained(key_path, 65, deadline) as (password, key_size), \
                    tempfile.TemporaryDirectory(prefix='stead-gpg-checkpoint-') as home:
                require(key_size == 65 and re.fullmatch(rb'[0-9a-f]{64}\n', password.read()), 'checkpoint-key-format')
                password.seek(0)
                status_read, status_write = os.pipe()
                try:
                    with new_file(destination) as output:
                        command = ['/usr/bin/prlimit', '--as=536870912', '--cpu=90', f'--fsize={MAX_CIPHER}', '--',
                                   f'/proc/self/fd/{binary_fd}', '--no-options', '--homedir', home, '--batch', '--no-tty',
                                   '--no-autostart', '--disable-dirmngr', '--no-auto-key-locate', '--no-auto-key-retrieve',
                                   '--pinentry-mode', 'loopback', '--no-symkey-cache', '--no-random-seed-file',
                                   '--passphrase-fd', str(password.fileno()), '--status-fd', str(status_write),
                                   '--max-output', str(MAX_ARCHIVE)]
                        command += (['--decrypt'] if decrypt else ['--force-aead', '--aead-algo', 'OCB', '--cipher-algo', 'AES256',
                                    '--s2k-mode', '3', '--s2k-digest-algo', 'SHA512', '--s2k-count', '65536',
                                    '--compress-algo', 'none', '--set-filename', '', '--symmetric'])
                        with subprocess.Popen(command, stdin=input_file, stdout=output, stderr=subprocess.DEVNULL,
                                              pass_fds=(binary_fd, password.fileno(), status_write), start_new_session=True,
                                              env={'PATH': '/usr/bin:/bin', 'HOME': home, 'LANG': 'C'}) as process:
                            os.close(status_write)
                            status_write = None
                            raw = bytearray()
                            try:
                                with DefaultSelector() as ready:
                                    ready.register(status_read, EVENT_READ)
                                    while True:
                                        pair.remaining(deadline)
                                        require(ready.select(deadline - time.monotonic()), 'checkpoint-gpg-timeout')
                                        block = os.read(status_read, min(4096, 65537 - len(raw)))
                                        if not block:
                                            break
                                        raw.extend(block)
                                        require(len(raw) <= 65536, 'checkpoint-gpg-status-bound')
                                status = process.wait(timeout=max(.001, deadline - time.monotonic()))
                                pair.remaining(deadline)
                            except BaseException:
                                process.kill()
                                process.wait()
                                raise
                        required = ([b'[GNUPG:] DECRYPTION_INFO 0 9 2', b'[GNUPG:] DECRYPTION_OKAY', b'[GNUPG:] GOODMDC', b'[GNUPG:] END_DECRYPTION']
                                    if decrypt else [b'[GNUPG:] BEGIN_ENCRYPTION 0 9 2', b'[GNUPG:] END_ENCRYPTION'])
                        lines = bytes(raw).splitlines()
                        require(status == 0 and all(lines.count(line) == 1 for line in required)
                                and not any(line.startswith((b'[GNUPG:] FAILURE', b'[GNUPG:] ERROR', b'[GNUPG:] BADMDC')) for line in lines)
                                and 0 < os.fstat(output.fileno()).st_size <= (MAX_ARCHIVE if decrypt else MAX_CIPHER),
                                'checkpoint-gpg-authentication')
                finally:
                    os.close(status_read)
                    if status_write is not None:
                        os.close(status_write)
            require(pair.file_state(before) == pair.file_state(os.fstat(binary_fd))
                    and same_entry(directory, binary.name, before), 'checkpoint-gpg-changed')
        finally:
            os.close(binary_fd)
    return {'algorithm': 'GnuPG-AES256-OCB', 'gpg_sha256': expected_binary_sha256, 'decrypt': decrypt}

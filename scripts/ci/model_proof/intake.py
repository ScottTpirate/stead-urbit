"""Fixed root-only artifact intake for a future disposable model proof.

No executable is invoked and no global package, service or policy is changed.
The caller must authenticate the reviewed hosted profile before calling this
helper. A returned inventory is source custody, not permission to run a model.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import socket
import tarfile
import time
import urllib.parse
import urllib.request

RUNTIME = {
    'url': 'https://github.com/ggml-org/llama.cpp/releases/download/b12359/llama-b12359-bin-ubuntu-x64.tar.gz',
    'bytes': 23311084,
    'sha256': '0bc1f091e8916102b6d8f2cf944233a620e90a0f856c72d0ce41150c65c2e72e',
}
MODEL = {
    'url': 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf',
    'bytes': 1117320736,
    'sha256': '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e',
}
MODEL_NAME = 'qwen2.5-1.5b-instruct-q4_k_m.gguf'
MAX_MEMBERS = 512
MAX_EXPANDED = 512 * 1024**2
MAX_FILE = 200 * 1024**2


def require(ok):
    if not ok:
        raise ValueError('Fixed model intake refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ordinary_directory(path, mode):
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
            and stat.S_IMODE(info.st_mode) == mode)


def new_directory(path, mode=0o755):
    path.mkdir(mode=mode)
    path.chmod(mode)
    ordinary_directory(path, mode)


RUNTIME_HOSTS = frozenset(('github.com', 'release-assets.githubusercontent.com'))
MODEL_HOSTS = frozenset(('huggingface.co', 'cas-bridge.xethub.hf.co', 'us.aws.cdn.hf.co'))
MAX_REDIRECTS = 5


def destination(url, allowed):
    require(type(url) is str and 0 < len(url) <= 8192 and url.isascii()
            and all(32 < ord(char) < 127 for char in url) and "\\" not in url)
    target = urllib.parse.urlsplit(url)
    require(target.scheme == 'https' and target.hostname in allowed
            and target.username is None and target.password is None
            and target.port in (None, 443) and not target.fragment
            and target.netloc in (target.hostname, target.hostname + ':443'))
    return target.hostname


class PublicHTTPSConnection(http.client.HTTPSConnection):
    """Connect to an already validated public address; TLS keeps the fixed DNS name."""
    def connect(self):
        require(self.host in RUNTIME_HOSTS | MODEL_HOSTS and self.port == 443
                and not self._tunnel_host and self.source_address is None)
        addresses = socket.getaddrinfo(self.host, 443, type=socket.SOCK_STREAM,
                                       proto=socket.IPPROTO_TCP)
        require(0 < len(addresses) <= 16)
        for family, kind, protocol, _, address in addresses:
            require(family in (socket.AF_INET, socket.AF_INET6)
                    and kind == socket.SOCK_STREAM and protocol == socket.IPPROTO_TCP
                    and ipaddress.ip_address(address[0]).is_global
                    and address[1] == 443)
        for family, kind, protocol, _, address in addresses:
            connection = socket.socket(family, kind, protocol)
            try:
                connection.settimeout(self.timeout)
                connection.connect(address)
                self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
                return
            except BaseException:
                connection.close()
                raise  # No fallback/retry to an independently changing destination.
        raise ValueError('Fixed model intake refused')


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, allowed):
        super().__init__()
        self.allowed = allowed

    def https_open(self, request):
        destination(request.full_url, self.allowed)
        return self.do_open(PublicHTTPSConnection, request,
                            context=self._context)


class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed):
        self.allowed, self.redirects = allowed, 0

    def redirect_request(self, request, fp, code, message, headers, new_url):
        destination(request.full_url, self.allowed)
        destination(new_url, self.allowed)
        self.redirects += 1
        require(self.redirects <= MAX_REDIRECTS)
        return super().redirect_request(request, fp, code, message, headers, new_url)


def download(path, pin, guard):
    """Only the two module constants can select an intake resource."""
    require(pin is RUNTIME or pin is MODEL)
    guard()
    allowed = RUNTIME_HOSTS if pin is RUNTIME else MODEL_HOSTS
    destination(pin['url'], allowed)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                         | os.O_CLOEXEC, 0o600)
    digest, count, started = hashlib.sha256(), 0, time.monotonic()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                         HTTPSOnly(allowed), PublicHTTPSHandler(allowed))
    request = urllib.request.Request(pin['url'], headers={'Accept-Encoding': 'identity',
                                                         'User-Agent': 'stead-fixed-model-proof/1'})
    try:
        with os.fdopen(descriptor, 'wb', closefd=False) as output:
            with opener.open(request, timeout=20) as response:
                require(response.status == 200
                        and response.headers.get('Content-Encoding', 'identity') == 'identity')
                length = response.headers.get('Content-Length')
                require(length is None or length == str(pin['bytes']))
                while True:
                    guard()
                    require(time.monotonic() - started < 300)
                    raw = response.read(min(1024**2, pin['bytes'] + 1 - count))
                    if not raw:
                        break
                    count += len(raw)
                    require(count <= pin['bytes'])
                    digest.update(raw)
                    output.write(raw)
                require(count == pin['bytes'] and digest.hexdigest() == pin['sha256'])
                output.flush()
                os.fsync(descriptor)
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == info.st_gid == 0
                and info.st_nlink == 1 and info.st_size == count)
        guard()
    finally:
        os.close(descriptor)


def relative(name):
    require(type(name) is str and 0 < len(name) <= 256
            and re.fullmatch(r'[A-Za-z0-9_.+\-/]+', name) is not None)
    # A single conventional leading ./ is harmless only after normalization.
    clean = name[2:] if name.startswith('./') else name
    clean = clean.rstrip('/')
    require(clean and not clean.startswith('/')
            and all(part not in ('', '.', '..') for part in clean.split('/')))
    return clean


def link_target(name, target):
    require(type(target) is str and 0 < len(target) <= 256
            and re.fullmatch(r'[A-Za-z0-9_.+\-/]+', target) is not None
            and not target.startswith('/'))
    parts = list(PurePosixPath(name).parent.parts)
    for part in target.split('/'):
        require(part not in ('', '.'))
        if part == '..':
            require(bool(parts))
            parts.pop()
        else:
            parts.append(part)
    require(bool(parts))
    return '/'.join(parts)


class OrdinaryTarInfo(tarfile.TarInfo):
    """Reject extension headers before tarfile reads their hidden payloads."""
    def _proc_member(self, archive):
        require(self.type in (tarfile.REGTYPE, tarfile.AREGTYPE,
                              tarfile.DIRTYPE, tarfile.SYMTYPE))
        return super()._proc_member(archive)


def regular_link_target(name, members):
    """At most eight in-tree links, ending in an admitted ordinary file."""
    current, seen = name, set()
    for hop in range(9):
        require(current in members and current not in seen)
        item = members[current]
        if item.isfile():
            return current
        require(hop < 8 and item.issym())
        seen.add(current)
        current = link_target(current, item.linkname)
    raise ValueError('Fixed model intake refused')


def extract_runtime(archive, directory, guard):
    """Inspect pinned vendor data, then write only bounded fixed-root members."""
    new_directory(directory)
    guard()
    with tarfile.open(archive, mode='r:gz', tarinfo=OrdinaryTarInfo) as tar:
        members, total, headers = {}, 0, 0
        for item in tar:
            guard()
            headers += 1
            require(headers <= MAX_MEMBERS)
            # Ignore only the archive's explicit root directory entry.
            if item.name in ('.', './'):
                require(item.isdir())
                continue
            name = relative(item.name)
            require(name not in members and len(members) < MAX_MEMBERS)
            require(item.isdir() or item.isfile() or item.issym())
            require(not item.islnk() and not item.isdev() and not item.isfifo())
            require(type(item.size) is int and 0 <= item.size <= MAX_FILE)
            total += item.size
            require(total <= MAX_EXPANDED)
            members[name] = item
        require(bool(members))
        directories = set()
        for name, item in members.items():
            parts = name.split('/')
            directories.update('/'.join(parts[:index]) for index in range(1, len(parts)))
            if item.isdir():
                directories.add(name)
        require(len(directories) + sum(not item.isdir() for item in members.values()) <= MAX_MEMBERS)
        require(all(name not in members or members[name].isdir() for name in directories))
        for name in sorted(directories, key=lambda item: (item.count('/'), item)):
            new_directory(directory / name)
        entries, executable = {}, []
        for name, item in sorted(members.items()):
            guard()
            if item.isdir():
                continue
            path = directory / name
            if item.issym():
                regular_link_target(name, members)
                os.symlink(item.linkname, path)
                entries[name] = {'kind': 'symlink', 'mode': 0o777, 'target': item.linkname}
                continue
            stream = tar.extractfile(item)
            require(stream is not None)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                                 | os.O_CLOEXEC, 0o644)
            digest, count, prefix = hashlib.sha256(), 0, b''
            try:
                with os.fdopen(descriptor, 'wb', closefd=False) as output:
                    while raw := stream.read(min(1024**2, item.size + 1 - count)):
                        guard()
                        count += len(raw)
                        require(count <= item.size)
                        digest.update(raw)
                        prefix = (prefix + raw)[:64]
                        output.write(raw)
                    require(count == item.size)
                    output.flush()
                    os.fsync(descriptor)
                mode = 0o644
                if PurePosixPath(name).name == 'llama-server':
                    # Exact Linux ELF64 little-endian x86-64, not a script.
                    require(len(prefix) == 64 and prefix[:7] == b'\x7fELF\x02\x01\x01'
                            and prefix[18:20] == b'\x3e\x00')
                    mode = 0o755
                    executable.append(name)
                os.fchmod(descriptor, mode)
                entries[name] = {'kind': 'file', 'mode': mode, 'bytes': count,
                                 'sha256': digest.hexdigest()}
            finally:
                stream.close()
                os.close(descriptor)
        require(len(executable) == 1)
        for name in directories:
            entries[name] = {'kind': 'directory', 'mode': 0o755}
    guard()
    return {'protocol': 'stead.fixed-model-runtime-tree/1', 'entries': entries,
            'server': executable[0], 'expanded_file_bytes': total,
            'runtime_archive_sha256': RUNTIME['sha256'],
            'tree_sha256': sha(canonical(entries))}


def prepare(directory, guard):
    """Called only by a separately admitted root setup; no standalone entry."""
    require(os.geteuid() == 0 and callable(guard))
    path = Path(directory)
    require(re.fullmatch(r'/var/lib/stead-model-proof-[a-z0-9]{8}', str(path)) is not None)
    ordinary_directory(path.parent, 0o755)
    new_directory(path, 0o700)
    download(path / 'runtime.tar.gz', RUNTIME, guard)
    runtime = extract_runtime(path / 'runtime.tar.gz', path / 'runtime', guard)
    download(path / MODEL_NAME, MODEL, guard)
    os.chmod(path / MODEL_NAME, 0o644)
    value = {'protocol': 'stead.fixed-model-intake/1', 'directory': str(path),
             'model': dict(MODEL, filename=MODEL_NAME), 'runtime': runtime,
             'runtime_executed': False, 'model_executed': False}
    raw = canonical(value)
    require(len(raw) <= 262144)
    descriptor = os.open(path / 'intake.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    guard()
    return value

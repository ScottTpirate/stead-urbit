"""Fixed root-only artifact intake for a future disposable pure evaluator.

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

RUNTIME = {'url': 'https://github.com/ScottTpirate/stead-urbit/releases/download/runtime-v4.6-newt-c0a35c6/vere-v4.6-newt-linux-x86_64.tgz', 'bytes': 9724624, 'sha256': 'd00669a0bdc9fe0be15d519bdf508208b0676f84e1a9f02be12ecc03f4576a01'}


def require(ok):
    if not ok:
        raise ValueError('Fixed pure evaluator intake refused')


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
        require(self.host in RUNTIME_HOSTS and self.port == 443
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
        raise ValueError('Fixed pure evaluator intake refused')


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
    """Only the one fixed runtime constant can select an intake resource."""
    require(pin is RUNTIME)
    guard()
    allowed = RUNTIME_HOSTS
    destination(pin['url'], allowed)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                         | os.O_CLOEXEC, 0o600)
    digest, count, started = hashlib.sha256(), 0, time.monotonic()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                         HTTPSOnly(allowed), PublicHTTPSHandler(allowed))
    request = urllib.request.Request(pin['url'], headers={'Accept-Encoding': 'identity',
                                                         'User-Agent': 'stead-fixed-pure-eval/1'})
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



ENTRIES = {'vere-v4.6-newt-linux-x86_64': {'bytes': 23703328, 'sha256': 'f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833', 'mode': 493}, 'vere-v4.6-newt-LICENSE.txt': {'bytes': 1071, 'sha256': 'b5d62c0a6f6b17ff490de29606527bf77b6509998ef07048488d659e2b719e52', 'mode': 420}, 'vere-v4.6-newt-SOURCE.txt': {'bytes': 826, 'sha256': '847c8d36630d3c52786a7b2a0da689eda341ccf2c45cb21b87828e6e9682fe5c', 'mode': 420}}


class OrdinaryTarInfo(tarfile.TarInfo):
    def _proc_member(self, archive):
        require(self.type in (tarfile.REGTYPE, tarfile.AREGTYPE))
        return super()._proc_member(archive)


def extract_runtime(archive, directory, metadata, guard):
    """Exactly three ordinary pinned members; only the binary is mounted for execution."""
    new_directory(directory)
    new_directory(metadata)
    fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as source:
        before = os.fstat(source.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 0
                and before.st_nlink == 1 and before.st_size == RUNTIME['bytes']
                and stat.S_IMODE(before.st_mode) == 0o600)
        raw = source.read(RUNTIME['bytes'] + 1)
        require(len(raw) == RUNTIME['bytes'] and sha(raw) == RUNTIME['sha256'])
        source.seek(0)
        seen = set()
        with tarfile.open(fileobj=source, mode='r:gz', tarinfo=OrdinaryTarInfo) as bundle:
            for member in bundle:
                guard()
                require(member.name in ENTRIES and member.name not in seen and len(seen) < 3
                        and member.isfile() and not member.issym() and not member.islnk()
                        and member.uid == member.gid == 0 and member.mode == ENTRIES[member.name]['mode']
                        and member.size == ENTRIES[member.name]['bytes'])
                seen.add(member.name)
                target = directory / 'vere' if member.name == 'vere-v4.6-newt-linux-x86_64' else metadata / member.name
                output_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
                try:
                    digest, count = hashlib.sha256(), 0
                    with bundle.extractfile(member) as stream, os.fdopen(output_fd, 'wb', closefd=False) as output:
                        while True:
                            guard()
                            part = stream.read(min(65536, member.size + 1 - count))
                            if not part:
                                break
                            count += len(part)
                            require(count <= member.size)
                            digest.update(part); output.write(part)
                        require(count == member.size and digest.hexdigest() == ENTRIES[member.name]['sha256'])
                        output.flush(); os.fsync(output_fd)
                    os.fchmod(output_fd, member.mode)
                    info = os.fstat(output_fd)
                    require(stat.S_ISREG(info.st_mode) and info.st_uid == info.st_gid == 0
                            and info.st_nlink == 1 and info.st_size == member.size)
                finally:
                    os.close(output_fd)
        after = os.fstat(source.fileno())
        require(seen == set(ENTRIES) and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns))
    guard()
    return {key: ENTRIES['vere-v4.6-newt-linux-x86_64'][key] for key in ('bytes', 'sha256')}


def prepare(directory, guard):
    require(os.geteuid() == 0 and callable(guard))
    path = Path(directory)
    require(re.fullmatch(r'/var/lib/stead-pure-eval-proof-[a-z0-9]{8}', str(path)) is not None)
    ordinary_directory(path.parent, 0o755)
    new_directory(path, 0o700)
    download(path / 'runtime.tar.gz', RUNTIME, guard)
    runtime = extract_runtime(path / 'runtime.tar.gz', path / 'runtime', path / 'runtime-metadata', guard)
    return {'protocol': 'stead.fixed-pure-eval-intake/1', 'runtime': runtime,
            'archive': RUNTIME, 'members': ENTRIES, 'runtime_executed': False}

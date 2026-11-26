"""Fixed isolated model proof worker; no Home, credentials or native authority.

Root owns intake, the initial namespace process and cgroup admission. This worker
checks that boundary before its ready/go handshake, then owns one fixed server
and one fixed client. Its report never certifies the root's final cgroup cleanup.
No import-time execution, downloads, source lookup or caller-selected commands.
"""
from __future__ import annotations

import fcntl
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import time

INPUT = Path('/input')
OUTPUT = Path('/output')
RUNTIME = Path('/runtime')
MODEL_NAME = 'qwen2.5-1.5b-instruct-q4_k_m.gguf'
MODEL_SHA = '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'
MODEL_BYTES = 1117320736
ARCHIVE_SHA = '0bc1f091e8916102b6d8f2cf944233a620e90a0f856c72d0ce41150c65c2e72e'
SOURCE_PINS = {
    'client.py': '101b2b21a56d8ff6bf677d6f488656c60d5feed5808538b1748158b146ab304d',
    'model_connections.py': '6f65a2d6c0dcb666c6ed621f914dc8392b01637d488f4a1c4d33fb043cdb5400',
    'owned_child.py': 'a01fc92a0b5f000f5ddee505d475127681ac47ea9a7aa4d8b450594cd50ec229',
    'interface.json': 'f7649162343289cbc26800fbf8f600f23b43e8cb26ece1f13221b1c8377587cf',
}
NAMESPACES = ('user', 'mnt', 'pid', 'net')
ENV = {'PATH': '/usr/bin', 'HOME': '/tmp', 'TMPDIR': '/tmp', 'LC_ALL': 'C',
       'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
LOG_LIMIT = 65536
TOTAL_SECONDS = 540
READY_SECONDS = 360
CLIENT_SECONDS = 65
CLIENT_FILES = {'request.json': 8192, 'response.bin': 32768,
                'proposal.json': 65536, 'report.json': 16384}
PHASES = ('admission', 'parent-admission', 'server-start', 'server-readiness',
          'client', 'client-output', 'cleanup', 'complete')
ERRORS = {'ValueError', 'TypeError', 'TimeoutError', 'OSError', 'PermissionError',
          'FileNotFoundError', 'FileExistsError', 'ProcessLookupError', 'ChildProcessError',
          'ConnectionRefusedError', 'ConnectionResetError', 'BrokenPipeError',
          'RemoteDisconnected', 'IncompleteRead', 'BadStatusLine', 'LineTooLong',
          'HTTPException', 'JSONDecodeError', 'UnicodeDecodeError'}


def require(ok):
    if not ok:
        raise ValueError('Fixed model worker refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def parse(raw):
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    require(canonical(value) == raw)
    return value


def lease_bytes(path, expected_uid, expected_gid, expected_mode):
    """Read one immutable published inode, including an atomically unlinked old one."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        def admitted(info):
            return (stat.S_ISREG(info.st_mode) and info.st_uid == expected_uid
                    and info.st_gid == expected_gid and stat.S_IMODE(info.st_mode) == expected_mode
                    and info.st_nlink in (0, 1) and 0 < info.st_size <= 1024)
        def stable(info):
            return (info.st_dev, info.st_ino, info.st_uid, info.st_gid,
                    info.st_mode, info.st_size, info.st_mtime_ns)
        require(admitted(before))
        raw = os.read(fd, 1025)
        after = os.fstat(fd)
        require(admitted(after) and stable(before) == stable(after) and len(raw) == before.st_size)
        return raw
    finally:
        os.close(fd)


class GuardianLease:
    """Root-owned read-only current lease; no native authority is inferred."""
    def __init__(self, owner_sha256):
        require(type(owner_sha256) is str and re.fullmatch('[a-f0-9]{64}', owner_sha256))
        self.owner_sha256 = owner_sha256
        self.last = (0, 0)

    def check(self):
        directory = Path('/lease')
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 65534
                and stat.S_IMODE(info.st_mode) == 0o550
                and {p.name for p in directory.iterdir()} == {'guardian.json'}
                and os.statvfs(directory).f_flag & os.ST_RDONLY)
        path = directory / 'guardian.json'
        row = parse(lease_bytes(path, 65534, 1000, 0o440))
        require(type(row) is dict and set(row) == {'protocol', 'owner_sha256', 'generation', 'issued_ns', 'expires_ns'}
                and row['protocol'] == 'stead.fixed-model-lease/1'
                and row['owner_sha256'] == self.owner_sha256
                and all(type(row[k]) is int for k in ('generation', 'issued_ns', 'expires_ns'))
                and 0 < row['generation'] <= 10000000
                and row['expires_ns'] - row['issued_ns'] == 5000000000
                and 0 < row['issued_ns'] <= time.monotonic_ns() < row['expires_ns'])
        current = (row['generation'], row['issued_ns'])
        require(current == self.last or (current[0] > self.last[0] and current[1] > self.last[1]))
        self.last = current


def pin_shape(value, maximum):
    require(type(value) is dict and set(value) == {'bytes', 'sha256'}
            and type(value['bytes']) is int and 0 < value['bytes'] <= maximum
            and type(value['sha256']) is str and re.fullmatch('[a-f0-9]{64}', value['sha256']))


def identity(info):
    # Reading a writable client artifact may update atime; custody is inode,
    # ownership, mode, links, size and write/change times, not read access time.
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def ordinary(path, *, owner, maximum, readonly=True):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == owner and info.st_nlink == 1
            and not info.st_mode & 0o022 and 0 < info.st_size <= maximum)
    if readonly:
        require(os.statvfs(path).f_flag & os.ST_RDONLY)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        require(identity(os.fstat(fd)) == identity(info))
        raw = bytearray()
        while part := os.read(fd, min(65536, maximum + 1 - len(raw))):
            raw.extend(part)
            require(len(raw) <= maximum)
        require(identity(os.fstat(fd)) == identity(info) and len(raw) == info.st_size)
        return bytes(raw)
    finally:
        os.close(fd)


def exact_file(path, expected, *, owner=65534, readonly=True):
    pin_shape(expected, 4 * 1024**2)
    raw = ordinary(path, owner=owner, maximum=expected['bytes'], readonly=readonly)
    require(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'])
    return raw


def hash_file(path, count, digest):
    """Bounded streaming custody for runtime/model; never load a model here."""
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 65534 and info.st_nlink == 1
            and not info.st_mode & 0o022 and info.st_size == count
            and os.statvfs(path).f_flag & os.ST_RDONLY)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        require(identity(os.fstat(fd)) == identity(info))
        total, result = 0, hashlib.sha256()
        while raw := os.read(fd, min(1024**2, count + 1 - total)):
            total += len(raw)
            require(total <= count)
            result.update(raw)
        require(total == count and result.hexdigest() == digest and identity(os.fstat(fd)) == identity(info))
    finally:
        os.close(fd)


def namespace_values():
    return {name: os.readlink('/proc/self/ns/' + name) for name in NAMESPACES}


def current_status():
    return dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines()
                if ':' in line)


def check_loopback():
    require([name for _, name in socket.if_nameindex()] == ['lo'])
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        raw = fcntl.ioctl(control.fileno(), 0x8913, struct.pack('16sH14x', b'lo', 0))
    require(struct.unpack('16sH14x', raw)[1] & 1)  # Observe IFF_UP, never set flags/capabilities.


def descriptors():
    # listdir's own ephemeral descriptor is gone before fstat; no inherited
    # guardian/proof/socket handles may reach this worker or its children.
    found = []
    for name in os.listdir('/proc/self/fd'):
        fd = int(name)
        try:
            os.fstat(fd)
        except OSError:
            continue
        found.append(fd)
    return sorted(found)


def relative(value):
    require(type(value) is str and 0 < len(value) <= 1024 and '\\' not in value
            and not value.startswith('/') and all(c.isalnum() or c in '/._+-' for c in value))
    parts = value.split('/')
    require(len(parts) <= 16 and all(part not in ('', '.', '..') for part in parts)
            and str(PurePosixPath(value)) == value)
    return value


def runtime_check(value):
    require(type(value) is dict and set(value) == {'protocol', 'entries', 'server',
            'expanded_file_bytes', 'runtime_archive_sha256', 'tree_sha256'}
            and value['protocol'] == 'stead.fixed-model-runtime-tree/1'
            and value['runtime_archive_sha256'] == ARCHIVE_SHA)
    entries = value['entries']
    require(type(entries) is dict and 0 < len(entries) <= 512
            and value['tree_sha256'] == sha(canonical(entries)))
    actual = set()
    for path in RUNTIME.rglob('*'):
        actual.add(str(path.relative_to(RUNTIME)))
        require(len(actual) <= 512)
    require(actual == set(entries))
    total, servers, library_dirs = 0, [], set()
    for name, row in sorted(entries.items()):
        path = RUNTIME / relative(name)
        require(type(row) is dict and type(row.get('mode')) is int)
        info = path.lstat()
        require(info.st_uid == 65534 and stat.S_IMODE(info.st_mode) == row['mode']
                and os.statvfs(path.parent).f_flag & os.ST_RDONLY)
        if row.get('kind') == 'directory':
            require(set(row) == {'kind', 'mode'} and row['mode'] == 0o755
                    and stat.S_ISDIR(info.st_mode))
        elif row.get('kind') == 'symlink':
            require(set(row) == {'kind', 'mode', 'target'} and row['mode'] == 0o777
                    and stat.S_ISLNK(info.st_mode) and os.readlink(path) == row['target'])
            target = path.resolve(strict=True)
            require(target.is_relative_to(RUNTIME) and target.is_file()
                    and entries[str(target.relative_to(RUNTIME))]['kind'] == 'file')
        else:
            require(set(row) == {'kind', 'mode', 'bytes', 'sha256'} and row['kind'] == 'file'
                    and row['mode'] in (0o644, 0o755) and type(row['bytes']) is int
                    and 0 <= row['bytes'] <= 200 * 1024**2
                    and re.fullmatch('[a-f0-9]{64}', row['sha256']))
            hash_file(path, row['bytes'], row['sha256'])
            total += row['bytes']
            require(total <= 512 * 1024**2)
            if path.name == 'llama-server':
                require(row['mode'] == 0o755)
                servers.append(name)
            else:
                require(row['mode'] == 0o644)
            if '.so' in path.name:
                library_dirs.add(str(path.parent))
    require(servers == [value['server']] and type(value['expanded_file_bytes']) is int
            and total == value['expanded_file_bytes'])
    return str(RUNTIME / relative(value['server'])), ':'.join(sorted(library_dirs))


def admission():
    require(len(sys.argv) == 1 and os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000)
    require(descriptors() == [0, 1, 2] and all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (0, 1, 2)))
    require(Path(__file__).resolve() == INPUT / 'worker.py')
    require(set(path.name for path in INPUT.iterdir()) == {*SOURCE_PINS, 'worker.py', 'owner.json'})
    raw = ordinary(INPUT / 'owner.json', owner=65534, maximum=262144)
    owner = parse(raw)
    require(type(owner) is dict and set(owner) == {'protocol', 'host_uid', 'host_gid',
            'outer_namespaces', 'sources', 'runtime', 'model', 'server_argv'}
            and owner['protocol'] == 'stead.fixed-model-worker-input/1')
    require(type(owner['host_uid']) is int and 0 < owner['host_uid'] < 65534
            and type(owner['host_gid']) is int and 0 < owner['host_gid'] < 65534)
    maps = {}
    # --dev requires devpts: pinned unprivileged bwrap first maps host->0,
    # then creates the final namespace mapping1000->parent0. The external
    # guardian must separately verify the composed map into the HOST account.
    for name in ('uid', 'gid'):
        mapping = Path('/proc/self/' + name + '_map').read_text().split()
        require(mapping == ['1000', '0', '1'])
        maps[name] = [1000, 0, 1]
    state = current_status()
    require(all(state[key].strip() == '0000000000000000'
                for key in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb'))
            and state['NoNewPrivs'].strip() == '1')
    observed = namespace_values()
    outer = owner['outer_namespaces']
    require(type(outer) is dict and set(outer) == set(NAMESPACES)
            and all(type(outer[key]) is str and re.fullmatch(key + r':\[[0-9]+\]', outer[key])
                    and observed[key] != outer[key] for key in NAMESPACES))
    check_loopback()
    require(os.statvfs('/usr').f_flag & os.ST_RDONLY)
    require(not any(Path(name).exists() for name in ('/home', '/root', '/etc', '/run', '/ci',
            '/native', '/execution', '/code', '/var', '/sys')))
    # bwrap --dev creates this ordinary private empty directory. It is not
    # a host shared-memory bind; the guardian independently proves /dev's mount.
    shm, dev = Path('/dev/shm').lstat(), Path('/dev').lstat()
    require(stat.S_ISDIR(shm.st_mode) and shm.st_uid == 1000
            and stat.S_IMODE(shm.st_mode) == 0o755 and shm.st_dev == dev.st_dev
            and list(Path('/dev/shm').iterdir()) == [])
    for path in (OUTPUT, Path('/tmp')):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 1000
                and stat.S_IMODE(info.st_mode) == 0o700 and list(path.iterdir()) == [])
    pins = owner['sources']
    require(type(pins) is dict and set(pins) == {*SOURCE_PINS, 'worker.py'})
    for name, pin in pins.items():
        content = exact_file(INPUT / name, pin)
        if name in SOURCE_PINS:
            require(sha(content) == SOURCE_PINS[name])
    interface = json.loads((INPUT / 'interface.json').read_bytes(), object_pairs_hook=unique)
    require(owner['server_argv'] == interface['runtime']['server_argv_after_pinned_executable'])
    require(owner['model'] == {'filename': MODEL_NAME, 'bytes': MODEL_BYTES, 'sha256': MODEL_SHA})
    require(set(path.name for path in Path('/model').iterdir()) == {MODEL_NAME})
    hash_file(Path('/model') / MODEL_NAME, MODEL_BYTES, MODEL_SHA)
    executable, library_path = runtime_check(owner['runtime'])
    module = importlib.util.spec_from_file_location('stead_owned_child', INPUT / 'owned_child.py')
    owned = importlib.util.module_from_spec(module)
    module.loader.exec_module(owned)
    proof = {'uid': 1000, 'gid': 1000, 'host_uid': owner['host_uid'], 'host_gid': owner['host_gid'],
             'source_uid': 65534, 'namespace_maps': maps, 'namespaces': observed, 'capabilities_empty': True,
             'no_new_privileges': True, 'private_loopback_only': True,
             'owner_sha256': sha(raw), 'runtime_tree_sha256': owner['runtime']['tree_sha256'],
             'model_sha256': MODEL_SHA, 'sources': pins, 'guardian_lease_required': True}
    return owner, proof, executable, library_path, owned


class Owned:
    def __init__(self):
        self.selector = selectors.DefaultSelector()
        self.children, self.logs = {}, {}

    def start(self, name, arguments, owned):
        require(name in ('server', 'client') and name not in self.children)
        process = subprocess.Popen(owned.command(arguments), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
            start_new_session=True, env=ENV)
        self.children[name] = {'process': process, 'pidfd': None}
        try:
            self.children[name]['pidfd'] = os.pidfd_open(process.pid, 0)
            for label, stream in (('stdout', process.stdout), ('stderr', process.stderr)):
                os.set_blocking(stream.fileno(), False)
                key = name + '-' + label
                self.logs[key] = {'bytes': bytearray(), 'eof': False, 'overflow': False}
                self.selector.register(stream, selectors.EVENT_READ, key)
            return process
        except BaseException:
            process.kill()
            process.wait(timeout=5)
            raise

    def pump(self, seconds=0.05):
        for event, _ in self.selector.select(seconds):
            row = self.logs[event.data]
            raw = os.read(event.fileobj.fileno(), 8192)
            if not raw:
                row['eof'] = True
                self.selector.unregister(event.fileobj)
                event.fileobj.close()
                continue
            row['bytes'].extend(raw[:max(0, LOG_LIMIT + 1 - len(row['bytes']))])
            if len(row['bytes']) > LOG_LIMIT:
                row['overflow'] = True
                raise ValueError('Fixed model log bound')

    def cleanup(self):
        okay = True
        for row in self.children.values():
            process = row['process']
            if process.poll() is None:
                try:
                    if row['pidfd'] is not None:
                        signal.pidfd_send_signal(row['pidfd'], signal.SIGTERM)
                    else:
                        process.terminate()
                except ProcessLookupError:
                    pass
        end = time.monotonic() + 3
        while time.monotonic() < end and any(row['process'].poll() is None for row in self.children.values()):
            try:
                self.pump()
            except BaseException:
                okay = False
        for row in self.children.values():
            process = row['process']
            if process.poll() is None:
                try:
                    if row['pidfd'] is not None:
                        signal.pidfd_send_signal(row['pidfd'], signal.SIGKILL)
                    else:
                        process.kill()
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=3)
            except BaseException:
                okay = False
        end = time.monotonic() + 2
        while self.selector.get_map() and time.monotonic() < end:
            try:
                self.pump()
            except BaseException:
                okay = False
        okay = okay and not self.selector.get_map() and all(
            row['process'].returncode is not None for row in self.children.values())
        summary = {}
        for name, row in self.children.items():
            summary[name] = {'exit_code': row['process'].returncode}
            for label in ('stdout', 'stderr'):
                log = self.logs.get(name + '-' + label)
                if log is None:
                    okay = False
                    continue
                summary[name][label] = {'bytes': len(log['bytes']), 'sha256': sha(log['bytes']),
                                       'eof': log['eof'], 'overflow': log['overflow']}
                okay = okay and log['eof'] and not log['overflow']
            if row['pidfd'] is not None:
                os.close(row['pidfd'])
        for event in list(self.selector.get_map().values()):
            event.fileobj.close()
        self.selector.close()
        return okay, summary


def healthy():
    http.client._MAXLINE = 8192
    http.client._MAXHEADERS = 32
    connection = http.client.HTTPConnection('127.0.0.1', 8088, timeout=0.5)
    began = time.monotonic()
    previous = signal.getitimer(signal.ITIMER_REAL)
    require(previous[0] > 0 and previous[1] == 0)
    signal.setitimer(signal.ITIMER_REAL, min(1, previous[0]))
    try:
        connection.request('GET', '/health', headers={'Connection': 'close', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        require(response.status in (200, 503))
        raw = response.read(2049)
        require(len(raw) <= 2048)
        if response.status == 503:
            return False
        require(json.loads(raw, object_pairs_hook=unique) == {'status': 'ok'})
        return True
    except (ConnectionRefusedError, TimeoutError, ConnectionResetError):
        return False
    finally:
        connection.close()
        signal.setitimer(signal.ITIMER_REAL, max(0.001, previous[0] - (time.monotonic() - began)))


def result_files():
    directory = OUTPUT / 'client'
    info = directory.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == 1000
            and stat.S_IMODE(info.st_mode) == 0o700
            and {path.name for path in directory.iterdir()} == set(CLIENT_FILES))
    raw = {name: ordinary(directory / name, owner=1000, maximum=maximum, readonly=False)
           for name, maximum in CLIENT_FILES.items()}
    pins = {name: {'bytes': len(value), 'sha256': sha(value)} for name, value in raw.items()}
    report = parse(raw['report.json'])
    require(type(report) is dict and set(report) == {'protocol', 'status', 'classification',
            'model_adapter_sha256', 'model', 'attempted_requests', 'completed_responses',
            'native_authority_supplied', 'tool_executed', 'document_mutated', 'qualifies_g3',
            'artifacts', 'error_class', 'connection_digest', 'request_digest', 'proposal_state',
            'observed_usage', 'semantic_edit_proposed', 'revision_checks', 'elapsed_ms'})
    require(report['protocol'] == 'stead.synthetic-model-doc-revision/1'
            and report['status'] == 'pass' and report['error_class'] == 'none'
            and report['classification'] == 'actual-local-inference-with-synthetic-public-document'
            and report['model_adapter_sha256'] == SOURCE_PINS['model_connections.py']
            and report['model'] == 'qwen2.5-1.5b-stead-compat2'
            and type(report['attempted_requests']) is int and report['attempted_requests'] == 1
            and type(report['completed_responses']) is int and report['completed_responses'] == 1
            and all(report[key] is False for key in ('native_authority_supplied', 'tool_executed', 'document_mutated', 'qualifies_g3'))
            and report['semantic_edit_proposed'] is True and report['proposal_state'] == 'tool-proposals'
            and type(report['elapsed_ms']) is int and 0 <= report['elapsed_ms'] <= 65000)
    require(report['artifacts'] == {name: pins[name] for name in ('request.json', 'response.bin', 'proposal.json')})
    proposal = parse(raw['proposal.json'])
    require(type(proposal) is dict and proposal['state'] == 'tool-proposals')
    calls = proposal['tool_proposals']
    require(type(calls) is list and len(calls) == 1 and calls[0]['name'] == 'propose_doc_update'
            and calls[0]['tool_id'] == '00000000-0000-7000-8000-000000000006'
            and calls[0]['revision'] == '1' and type(calls[0]['arguments']) is dict
            and set(calls[0]['arguments']) == {'markdown'})
    # Recheck the retained argument with the exact admitted verifier. A child
    # report's success flag cannot substitute for the original output bytes.
    client_raw = ordinary(INPUT / 'client.py', owner=65534, maximum=65536)
    require(sha(client_raw) == SOURCE_PINS['client.py'])
    module_spec = importlib.util.spec_from_file_location('stead_doc_revision', INPUT / 'client.py')
    client = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(client)
    checks = client.assess_revision(calls[0]['arguments']['markdown'])
    require(report['revision_checks'] == checks and client.accepted_revision(checks))
    return pins, sha(raw['report.json'])


def process_ids():
    return {int(path.name) for path in Path('/proc').iterdir() if path.name.isascii() and path.name.isdecimal()}


def check_processes(baseline, children):
    allowed = baseline | {row['process'].pid for row in children.children.values()}
    require(process_ids() <= allowed)


def timeout(_signum, _frame):
    raise TimeoutError('Fixed model worker deadline')


def main():
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (131072, 131072))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, TOTAL_SECONDS)
    started, phase = time.monotonic(), 'admission'
    children, proof, client_complete = None, None, False
    report = {'protocol': 'stead.fixed-model-worker-result/1', 'status': 'fail',
              'error_class': 'none', 'phase': phase, 'native_executed': False,
              'qualifies_g3': False, 'model_launches': 0, 'client_launches': 0,
              'children_reaped': False, 'outer_cleanup_required': True, 'artifacts': {},
              'children': {}, 'namespace_baseline_restored': False,
              'client_report_sha256': None, 'cleanup_error_class': 'none'}
    try:
        owner, proof, executable, libraries, owned = admission()
        phase = 'parent-admission'
        print(canonical({'protocol': 'stead.fixed-model-ready/1', 'pid': os.getpid(),
                         'uid': 1000, 'gid': 1000, 'namespaces': proof['namespaces'],
                         'owner_sha256': proof['owner_sha256']}).decode(), flush=True)
        require(sys.stdin.buffer.read(4) == b'go\n')  # exact go plus EOF, no polling authority.
        lease = GuardianLease(proof['owner_sha256'])
        lease.check()
        require(namespace_values() == proof['namespaces'])
        check_loopback()
        baseline = process_ids()
        require(baseline == {1, os.getpid()})
        children = Owned()
        phase = 'server-start'
        environment = dict(ENV)
        if libraries:
            environment['LD_LIBRARY_PATH'] = libraries
        # Apply vendor loader paths only after the trusted lifetime launcher.
        server_argv = ['/usr/bin/env', '-i', *[key + '=' + value for key, value in sorted(environment.items())],
                       executable, *owner['server_argv']]
        lease.check()
        server = children.start('server', server_argv, owned)
        report['model_launches'] = 1
        phase, deadline = 'server-readiness', min(started + TOTAL_SECONDS - 80, time.monotonic() + READY_SECONDS)
        while True:
            lease.check()
            children.pump(0.1)
            check_processes(baseline, children)
            require(server.poll() is None and time.monotonic() < deadline)
            ready = healthy()
            lease.check()
            if ready:
                break
        phase = 'client'
        lease.check()
        client = children.start('client', ['/usr/bin/python3', '-I', '-B', '/input/client.py'], owned)
        report['client_launches'] = 1
        deadline = min(started + TOTAL_SECONDS - 12, time.monotonic() + CLIENT_SECONDS)
        while client.poll() is None:
            lease.check()
            require(server.poll() is None and time.monotonic() < deadline)
            children.pump(0.1)
            check_processes(baseline, children)
        lease.check()
        require(client.returncode == 0 and server.poll() is None)
        client_complete = True
    except BaseException as error:
        name = type(error).__name__
        report['error_class'] = name if name in ERRORS else 'unrecognized'
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        report['phase'] = phase if phase in PHASES else 'admission'
        try:
            if children is None:
                report['children_reaped'], report['children'] = True, {}
            else:
                report['children_reaped'], report['children'] = children.cleanup()
                report['namespace_baseline_restored'] = process_ids() <= baseline
                report['children_reaped'] = report['children_reaped'] and report['namespace_baseline_restored']
            if client_complete and report['children_reaped'] and report['error_class'] == 'none':
                lease.check()
                report['phase'] = 'client-output'
                report['artifacts'], report['client_report_sha256'] = result_files()
                report['status'] = 'pass'
                report['phase'] = 'complete'
        except BaseException as error:
            report['children_reaped'] = False
            report['cleanup_error_class'] = type(error).__name__ if type(error).__name__ in ERRORS else 'unrecognized'
        if not report['children_reaped']:
            report['status'] = 'fail'
        report['elapsed_ms'] = int((time.monotonic() - started) * 1000)
        report['admission'] = proof
        require(len(canonical(report)) <= 32768)
        print(canonical(report).decode(), flush=True)
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

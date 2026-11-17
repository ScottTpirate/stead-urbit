"""Private fixed pure evaluator worker draft. No runtime admission or entry through model mode."""
from __future__ import annotations
import base64
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time

INPUT = Path('/input')
OUTPUT = Path('/output')
SOURCES = Path('/sources')
RUNTIME = Path('/runtime/vere')
NAMESPACES = ('user','mnt','pid','net')
COMPOSITION_SHA = '29f23ddb8849c5b182fca693a993a0634463e12104b47433ba3525adf93dfe31'
RUNTIME_SHA = 'f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833'
OWNED_SHA = 'a01fc92a0b5f000f5ddee505d475127681ac47ea9a7aa4d8b450594cd50ec229'
# Exact fixed codec/interface bytes; the outer profile still requires independent admission.
CODEC_SHA = 'dbc610914c8f38cc1724c932f10383a7fee7824ab54e85f61061e45e042e9bcb'
INTERFACE_SHA = '7c55126c6394794fea1c58143b03c86d54f33b566084d71cbd4955fb6f0ad958'
MODEL_COMPOSITION_SHA = 'c23002a6a5d1423167a0ef2caa9c35bc86b5ccc64ba3fff640dc73edfd9dfaa6'
MODEL_INTERFACE_SHA = '1714e10ef6c746b76b43e61cdca770e1bd168572994bfdc58b467752665c8913'
DEBUG_COMPOSITION_SHA = '81085d13ec4a79a5b75f7e2bcaa4226eb48dd630e9d23e84af4068a3164b44c3'
DEBUG_INTERFACE_SHA = '8cb3a5a81a8d3179150beb65ba61ed51a1ec35c0ada1d274a49ee9c6c678c0cb'
ENV = {'PATH':'/usr/bin','HOME':'/tmp','TMPDIR':'/tmp','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'}
LIMIT = 1000000
TOTAL_SECONDS = 540
REPORT_LIMIT = 4194304
STAGING_LIMIT = 4063232
ERRORS = {'ValueError','TypeError','TimeoutError','OSError','PermissionError','FileNotFoundError','FileExistsError','ProcessLookupError','ChildProcessError','UnicodeDecodeError','JSONDecodeError'}

def require(ok):
    if not ok:
        raise ValueError('Fixed pure evaluator worker refused')


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
                and row['protocol'] == 'stead.fixed-pure-eval-lease/1'
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


def process_ids():
    return {int(path.name) for path in Path('/proc').iterdir() if path.name.isascii() and path.name.isdecimal()}


def load(name, raw):
    """Load only bytes that passed exact fixed-input custody."""
    import types
    require(name not in sys.modules)
    module = types.ModuleType(name)
    module.__file__ = str(INPUT / (name + '.py'))
    sys.modules[name] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def source_inventory(composition, composition_sha256=COMPOSITION_SHA):
    # The owner-pinned digest selects the source count; a child supplies no count.
    require(type(composition_sha256) is str and composition_sha256 in
            (COMPOSITION_SHA, MODEL_COMPOSITION_SHA, DEBUG_COMPOSITION_SHA))
    expected_count = 21 if composition_sha256 == MODEL_COMPOSITION_SHA else 55
    expected = {name: {k: row[k] for k in ('bytes', 'sha256')}
                for name, row in composition['sources'].items()}
    helper = composition['composition']['test_helper']
    expected[helper['path']] = {k: helper[k] for k in ('bytes', 'sha256')}
    require(len(expected) == expected_count)
    actual = set()
    for parent, directories, names in os.walk(SOURCES, followlinks=False):
        for name in directories:
            info = (Path(parent) / name).lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == 65534 and not info.st_mode & 0o022)
        for name in names:
            actual.add(str((Path(parent) / name).relative_to(SOURCES)))
    require(actual == set(expected))
    files = {name: exact_file(SOURCES / name, pin) for name, pin in expected.items()}
    return files, {name: sha(raw) for name, raw in files.items()}


def input_profile(code):
    """Check fixed code/interface/composition pairing after root-pinned file custody."""
    require(type(code) is dict and set(code) ==
            {'worker.py', 'codec.py', 'owned_child.py', 'interface.json', 'composition.json'}
            and all(type(raw) is bytes for raw in code.values()))
    composition_sha = sha(code['composition.json'])
    interfaces = {COMPOSITION_SHA: INTERFACE_SHA, MODEL_COMPOSITION_SHA: MODEL_INTERFACE_SHA,
                  DEBUG_COMPOSITION_SHA: DEBUG_INTERFACE_SHA}
    require(composition_sha in interfaces and sha(code['codec.py']) == CODEC_SHA
            and sha(code['interface.json']) == interfaces[composition_sha]
            and sha(code['owned_child.py']) == OWNED_SHA)
    return composition_sha


def admission():
    require(sys.argv == ['/input/worker.py'] and os.getuid() == os.geteuid() == 1000
            and os.getgid() == os.getegid() == 1000 and descriptors() == [0, 1, 2])
    require(all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (0, 1, 2)))
    names = {'worker.py', 'codec.py', 'owned_child.py', 'interface.json', 'composition.json'}
    require({p.name for p in INPUT.iterdir()} == names | {'owner.json'})
    raw = ordinary(INPUT / 'owner.json', owner=65534, maximum=262144)
    owner = parse(raw)
    require(type(owner) is dict and set(owner) == {'protocol', 'host_uid', 'host_gid',
            'outer_namespaces', 'sources', 'runtime'}
            and owner['protocol'] == 'stead.fixed-pure-eval-worker-input/1'
            and type(owner['sources']) is dict and set(owner['sources']) == names)
    require(all(type(owner[k]) is int and 0 < owner[k] < 65534 for k in ('host_uid', 'host_gid')))
    for name in ('uid', 'gid'):
        require(Path('/proc/self/' + name + '_map').read_text().split() == ['1000', '0', '1'])
    state = current_status()
    require(state['NoNewPrivs'].strip() == '1' and all(state[k].strip() == '0000000000000000'
            for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')))
    observed, outer = namespace_values(), owner['outer_namespaces']
    require(type(outer) is dict and set(outer) == set(NAMESPACES)
            and all(type(outer[k]) is str and re.fullmatch(k + r':\[[0-9]+\]', outer[k])
                    and observed[k] != outer[k] for k in NAMESPACES))
    check_loopback()
    require(not any(Path(p).exists() for p in ('/home', '/root', '/etc', '/run', '/ci',
            '/native', '/execution', '/code', '/var', '/sys', '/model')))
    for directory in ('/usr', '/input', '/sources', '/runtime'):
        require(os.statvfs(directory).f_flag & os.ST_RDONLY)
    shm, dev = Path('/dev/shm').lstat(), Path('/dev').lstat()
    require(stat.S_ISDIR(shm.st_mode) and shm.st_uid == 1000
            and stat.S_IMODE(shm.st_mode) == 0o755 and shm.st_dev == dev.st_dev
            and not list(Path('/dev/shm').iterdir()))
    for path in (OUTPUT, Path('/tmp')):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 1000
                and stat.S_IMODE(info.st_mode) == 0o700 and not list(path.iterdir()))
    code = {name: exact_file(INPUT / name, expected) for name, expected in owner['sources'].items()}
    composition_sha = input_profile(code)
    composition = json.loads(code['composition.json'], object_pairs_hook=unique)
    files, before = source_inventory(composition, composition_sha)
    require(type(owner['runtime']) is dict and set(owner['runtime']) == {'bytes', 'sha256'}
            and owner['runtime']['sha256'] == RUNTIME_SHA
            and type(owner['runtime']['bytes']) is int and 0 < owner['runtime']['bytes'] <= 128 * 1024**2)
    require({p.name for p in RUNTIME.parent.iterdir()} == {'vere'}
            and stat.S_IMODE(RUNTIME.lstat().st_mode) == 0o755)
    hash_file(RUNTIME, owner['runtime']['bytes'], RUNTIME_SHA)
    codec, owned = load('codec', code['codec.py']), load('owned_child', code['owned_child.py'])
    jobs = codec.jobs(files, code['composition.json'])
    selected = codec.profile(composition_sha)
    require(codec.job_profile(jobs) == selected)
    proof = {'uid': 1000, 'gid': 1000, 'host_uid': owner['host_uid'], 'host_gid': owner['host_gid'],
             'namespace_maps': {'uid': [1000, 0, 1], 'gid': [1000, 0, 1]},
             'namespaces': observed, 'source_uid': 65534, 'capabilities_empty': True,
             'no_new_privileges': True, 'private_loopback_only': True,
             'owner_sha256': sha(raw), 'sources': owner['sources'], 'runtime_sha256': RUNTIME_SHA,
             'guardian_lease_required': True}
    return owner, proof, codec, owned, jobs, composition, before


def await_go(lease, deadline):
    selector = selectors.DefaultSelector()
    raw = bytearray()
    try:
        os.set_blocking(0, False)
        selector.register(0, selectors.EVENT_READ)
        while True:
            lease.check()
            require(time.monotonic() < deadline)
            if not selector.select(0.05):
                continue
            part = os.read(0, 4)
            if not part:
                require(raw == b'go\n')
                return
            raw.extend(part)
            require(len(raw) <= 3 and b'go\n'.startswith(raw))
    finally:
        selector.close()


def child_limits():
    # Runs only in the fresh single-thread child before the trusted owned-child wrapper.
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def stop(process, pidfd):
    if process.poll() is None:
        try:
            signal.pidfd_send_signal(pidfd, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)


def evaluate(job, owned, lease, baseline, deadline):
    """Regular anonymous output files avoid pinned Vere's large-pipe truncation."""
    require(type(job) is dict and set(job) == {'label', 'kind', 'source', 'source_sha256', 'timeout_seconds', 'arms'}
            and type(job['source']) is bytes and 0 < len(job['source']) <= 1048576
            and sha(job['source']) == job['source_sha256']
            and type(job['timeout_seconds']) is int and job['timeout_seconds'] in (15, 85))
    process = None
    pidfd = None
    with tempfile.TemporaryFile(dir='/tmp') as source, tempfile.TemporaryFile(dir='/tmp') as output, tempfile.TemporaryFile(dir='/tmp') as errors:
        source.write(job['source']); source.flush(); source.seek(0)
        require(process_ids() == baseline and len(list(Path('/proc/self/task').iterdir())) == 1)
        lease.check()
        try:
            process = subprocess.Popen(owned.command([str(RUNTIME), 'eval', '--loom', '29']),
                stdin=source, stdout=output, stderr=errors, close_fds=True,
                start_new_session=True, env=ENV, preexec_fn=child_limits)
            try:
                pidfd = os.pidfd_open(process.pid, 0)
            except BaseException:
                process.kill(); process.wait(timeout=3)
                raise
            end = min(deadline, time.monotonic() + job['timeout_seconds'])
            while process.poll() is None:
                lease.check()
                if not time.monotonic() < end:
                    raise TimeoutError('Fixed evaluator job deadline')
                require(os.fstat(output.fileno()).st_size <= LIMIT and os.fstat(errors.fileno()).st_size <= LIMIT)
                time.sleep(0.05)
            process.wait(timeout=1)
            require(process_ids() == baseline)
            lease.check()
            captured = []
            for stream in (output, errors):
                before = os.fstat(stream.fileno())
                require(0 <= before.st_size <= LIMIT)
                stream.seek(0); raw = stream.read(LIMIT + 1)
                require(len(raw) == before.st_size and stream.read(1) == b''
                        and identity(os.fstat(stream.fileno())) == identity(before))
                captured.append(raw)
            return process.returncode, captured[0], captured[1]
        finally:
            if process is not None and pidfd is not None:
                stop(process, pidfd)
            if pidfd is not None:
                os.close(pidfd)


def atomic_report(value):
    raw = canonical(value)
    require(0 < len(raw) <= STAGING_LIMIT and not list(OUTPUT.iterdir()))
    path = OUTPUT / 'report.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw); stream.flush(); os.fsync(fd)
    finally:
        os.close(fd)
    return {'bytes': len(raw), 'sha256': sha(raw)}


def main():
    started = time.monotonic()
    def alarm(_signum, _frame):
        raise TimeoutError('Fixed pure evaluator deadline')
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, TOTAL_SECONDS)
    phase, failed, cleanup, baseline = 'admission', 'none', 'none', None
    proof = None
    report_pin = None
    report = {'protocol': 'stead.fixed-pure-eval-report/1', 'status': 'fail',
              'qualifies_phase': False, 'composition_sha256': COMPOSITION_SHA,
              'runtime_sha256': RUNTIME_SHA, 'records': [], 'source_hashes_before': {},
              'source_hashes_after': {}, 'budget_stop': None, 'error_class': 'none',
              'children_reaped': False, 'namespace_baseline_restored': False,
              'expected_positive_arms': 26, 'expected_controls': 2, 'native_application_executed': False}
    try:
        owner, proof, codec, owned, jobs, composition, before = admission()
        selected = codec.job_profile(jobs)
        require(selected['composition_sha256'] == owner['sources']['composition.json']['sha256'])
        report['composition_sha256'] = selected['composition_sha256']
        report['expected_positive_arms'] = selected['positive_arms']
        baseline = process_ids(); require(baseline == {1, os.getpid()})
        report['source_hashes_before'] = before
        reserve = dict(report, source_hashes_after=before,
                       budget_stop={'label': max((j['label'] for j in jobs), key=len),
                                    'bytes': 99999999, 'sha256': 'f' * 64})
        require(len(canonical(reserve)) <= REPORT_LIMIT - STAGING_LIMIT)
        lease = GuardianLease(proof['owner_sha256']); lease.check()
        print(canonical({'protocol': 'stead.fixed-pure-eval-ready/1', 'pid': os.getpid(),
              'uid': 1000, 'gid': 1000, 'namespaces': namespace_values(),
              'owner_sha256': proof['owner_sha256']}).decode(), flush=True)
        phase = 'parent-admission'; await_go(lease, min(started + 90, started + TOTAL_SECONDS))
        phase = 'evaluations'
        for job in jobs:
            code, stdout, stderr = evaluate(job, owned, lease, baseline, started + TOTAL_SECONDS - 15)
            record = {'label': job['label'], 'source_sha256': job['source_sha256'],
                      'source_bytes': len(job['source']), 'exit_code': code,
                      'stdout': {'present': True, 'bytes': len(stdout), 'sha256': sha(stdout),
                                 'base64': base64.b64encode(stdout).decode('ascii')},
                      'stderr': {'present': True, 'bytes': len(stderr), 'sha256': sha(stderr),
                                 'base64': base64.b64encode(stderr).decode('ascii')},
                      'observation': None}
            observation_error = None
            try:
                record['observation'] = codec.observe(job, code, stdout, stderr)
            except BaseException as error:
                observation_error = error
            staged = dict(report, records=report['records'] + [record])
            # Measure the same encoding with all final worker metadata reserved.
            # These predicted fields are measurement-only, never retained as observations.
            measured = dict(staged, status='fail', source_hashes_after=before,
                            error_class=max(ERRORS, key=len), children_reaped=False,
                            namespace_baseline_restored=False,
                            budget_stop={'label': max((j['label'] for j in jobs), key=len),
                                         'bytes': 99999999, 'sha256': 'f' * 64})
            raw = canonical(measured)
            if len(raw) > STAGING_LIMIT:
                report['budget_stop'] = {'label': job['label'], 'bytes': len(raw), 'sha256': sha(raw)}
                raise ValueError('Fixed report budget')
            report['records'].append(record)
            if observation_error is not None:
                raise observation_error
            lease.check()
        phase = 'source-after'
        _, after = source_inventory(composition, owner['sources']['composition.json']['sha256'])
        require(after == before); report['source_hashes_after'] = after
        lease.check(); require(process_ids() == baseline)
        require(len(report['records']) == selected['jobs'] and all(r['observation']['status'] == 'pass' for r in report['records']))
        report['status'] = 'pass'
        phase = 'complete'
    except BaseException as error:
        failed = type(error).__name__ if type(error).__name__ in ERRORS else 'unrecognized'
        report['error_class'] = failed
        report['status'] = 'fail'
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            require(baseline is not None and process_ids() == baseline and not list(Path('/tmp').iterdir()))
            report['children_reaped'] = report['namespace_baseline_restored'] = True
        except BaseException:
            cleanup = 'baseline-or-temporary-files'
            report['status'] = 'fail'
        try:
            if proof is not None and cleanup == 'none':
                report_pin = atomic_report(report)
        except BaseException:
            cleanup = 'report-retention'
            report['status'] = 'fail'
        final = {'protocol': 'stead.fixed-pure-eval-worker-result/1', 'status': report['status'],
                 'phase': phase, 'error_class': failed, 'cleanup_error_class': cleanup,
                 'report': report_pin, 'admission': proof, 'outer_cleanup_required': True,
                 'children_reaped': report['children_reaped'],
                 'namespace_baseline_restored': report['namespace_baseline_restored'],
                 'jobs_retained': len(report['records']), 'elapsed_ms': int((time.monotonic() - started) * 1000),
                 'qualifies_phase': False, 'native_application_executed': False}
        require(len(canonical(final)) <= 16384)
        print(canonical(final).decode(), flush=True)
    return 0 if report['status'] == 'pass' and cleanup == 'none' else 1


if __name__ == '__main__':
    raise SystemExit(main())


"""One fixed saved8 hosted worker; no local CLI or supplied saved noun.

Executed only as /guardian/worker.py in the authenticated owner's namespace.
The frozen /ci inventory stays exactly three files. Native logs remain private;
one bounded trusted frame is the only stdout. Root decides final acceptance.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
import types

def fixed_package():
    """Bind the captured child package without extending its three-file view."""
    package = types.ModuleType('home_asset_rehearsal')
    package.__package__ = 'home_asset_rehearsal'
    package.__path__ = ['/ci/home_asset_rehearsal']
    sys.modules['home_asset_rehearsal'] = package


if __name__ == '__main__':
    fixed_package()

sys.path[:0] = ['/guardian', '/helpers', '/ci', '/code']
import hosted_lease
import result as R
from home_asset_rehearsal import evidence as E

GUARDIAN_NAMES = {'worker.py', 'result.py', 'hosted.py', 'hosted_lease.py', 'hosted_apparmor.py', 'digests.py'}
SOURCE_NAMES = {'/ci': {'home_asset_rehearsal/runner.py', 'home_asset_rehearsal/evidence.py',
    'home_asset_rehearsal/capture.hoon'}, '/code': {'release_install.py'},
    '/helpers': {'execution_policy.py', 'core_conn.py', 'conn.py', 'owned_child.py', 'native_tls.py', 'team_conn.py'},
    '/support': {'native.py'}}
STOP = threading.Event()


def require(ok):
    if not ok:
        raise ValueError('Fixed saved8 worker admission refused')


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def identity(info):
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode',
        'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def regular(path, maximum, *, captured=False):
    path = Path(path)
    before_path = path.lstat()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 < before.st_size <= maximum and identity(before) == identity(before_path))
        if captured:
            require(before.st_uid == os.getuid() and stat.S_IMODE(before.st_mode) == 0o600)
        else:
            require(before.st_uid == 65534 and not stat.S_IMODE(before.st_mode) & 0o022
                    and os.statvfs(path).f_flag & os.ST_RDONLY)
        data = bytearray()
        while chunk := os.read(fd, min(65536, maximum + 1 - len(data))):
            data.extend(chunk); require(len(data) <= maximum)
        require(len(data) == before.st_size and identity(before) == identity(os.fstat(fd)) == identity(path.lstat()))
        return bytes(data)
    finally:
        os.close(fd)


def source_tree(path, expected):
    path = Path(path)
    require(type(expected) is dict and expected and len(expected) <= 16
            and all(type(k) is str and E.digest(v) for k, v in expected.items()))
    actual = {}
    for value in path.rglob('*'):
        info = value.lstat()
        require(not stat.S_ISLNK(info.st_mode) and (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)))
        if stat.S_ISREG(info.st_mode):
            name = value.relative_to(path).as_posix()
            require(name in expected and len(actual) < len(expected))
            actual[name] = E.sha(regular(value, 262144))
    R.exact(actual, expected)


def runtime_inputs(value):
    # Reuse the existing mounted runtime/kernel hash implementation, not a
    # weaker name/version check. The root owner verifies the same pins.
    import digests
    lock_raw = regular('/toolchain.json', 65536)
    require(E.sha(lock_raw) == value['toolchain_sha256'])
    lock = json.loads(lock_raw, object_pairs_hook=E.unique)
    require(lock['runtime']['binary'] == 'bin/vere-v4.6-newt-linux-x86_64'
            and lock['runtime']['binary_sha256'] == value['runtime_sha256'] == R.RUNTIME
            and lock['boot_artifact']['archive'] == 'brass-408k-2.pill'
            and lock['boot_artifact']['sha256'] == value['pill_sha256']
                == 'b4babd14e9f1acbdb421b3c31c215ee637ad6691b7e382b99c6fd8991e623708'
            and lock['kernel']['commit'] == value['kernel_commit'] == R.KERNEL
            and lock['kernel']['source_tree_sha256'] == value['kernel_tree_sha256']
                == '33b397d659f7686be86d12f59c968f7613a5dc2851916ca512b6f18aa0ec231b')
    for path, expected in ((Path('/runtime') / lock['runtime']['binary'], R.RUNTIME),
                          (Path('/runtime/downloads') / lock['boot_artifact']['archive'], value['pill_sha256'])):
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 65534
                and not stat.S_IMODE(before.st_mode) & 0o022 and os.statvfs(path).f_flag & os.ST_RDONLY)
        require(digests.sha(path) == expected and identity(before) == identity(path.lstat()))
    require(os.statvfs('/kernel').f_flag & os.ST_RDONLY
            and digests.tree_sha(Path('/kernel'), source_links=True) == value['kernel_tree_sha256'])


class FixedProvider(hosted_lease.HostedProvider):
    """Only the fixed guard-source path differs from the pinned initializer."""
    def __init__(self):
        self.control = Path('/execution')
        hosted_lease.require(os.statvfs(self.control).f_flag & os.ST_RDONLY, 'Hosted control must be read-only')
        self.run_id = os.environ.get('STEAD_EXECUTION_ID', '')
        hosted_lease.require(re.fullmatch(r'[0-9a-f]{32}', self.run_id), 'Missing hosted execution identity')
        self.cpus = sorted(os.sched_getaffinity(0))
        self.guard_sha256 = E.sha(regular('/guardian/hosted.py', 262144))
        self.previous = None
        self.lock = threading.Lock()
        self.require(preflight=True)


def mapped_owner(value):
    # Same reader perspective and one-entry maps as pinned
    # doc_worker_proof.read_admission. Namespace root is not host root.
    require(os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 0 and not os.getgroups())
    for kind in ('uid', 'gid'):
        owner = R.integer(value['owner_' + kind], 1, 2**32 - 2)
        with Path('/proc/self/' + kind + '_map').open('rt', encoding='ascii') as source:
            raw = source.read(4097)
        require(len(raw) <= 4096)
        rows = [[int(v) for v in row.split()] for row in raw.splitlines()]
        R.exact(rows, [[0, owner, 1]])


def admission():
    require(sys.flags.isolated and sys.dont_write_bytecode and len(sys.argv) == 1
            and os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 0
            and not os.getgroups() and os.environ.get('STEAD_RELEASE_INSTALL_CHILD') == '1')
    raw = regular('/inputs.json', 1048576)
    value = json.loads(raw, object_pairs_hook=E.unique)
    require(raw == E.canonical(value) + b'\n' and type(value) is dict and set(value) == {
        'protocol', 'profile', 'run_id', 'controller_commit', 'candidate_commit', 'backend_commit',
        'target_commit', 'workflow_binding', 'controller_files', 'host_namespaces', 'owner_uid', 'owner_gid',
        'source_files', 'guardian_files', 'driver_files', 'seed_files', 'runtime_sha256', 'pill_sha256',
        'kernel_commit', 'kernel_tree_sha256', 'toolchain_sha256', 'archives', 'assets', 'desk_hashes'})
    require(value['protocol'] == 'stead.saved8-hosted-inputs/1' and value['profile'] == 'home-assets-saved8/1'
            and value['backend_commit'] == value['candidate_commit'] == R.BASE and value['target_commit'] == R.TARGET
            and value['runtime_sha256'] == R.RUNTIME and value['kernel_commit'] == R.KERNEL
            and value['run_id'] == os.environ.get('STEAD_EXECUTION_ID'))
    for key in ('owner_uid', 'owner_gid'):
        R.integer(value[key], 1, 2**32 - 2)
    mapped_owner(value)
    require(type(value['guardian_files']) is dict and set(value['guardian_files']) == GUARDIAN_NAMES
            and type(value['source_files']) is dict and set(value['source_files']) == set(SOURCE_NAMES))
    source_tree('/guardian', value['guardian_files'])
    for path, names in SOURCE_NAMES.items():
        require(set(value['source_files'][path]) == names)
        source_tree(path, value['source_files'][path])
    expected = {'run_id': value['run_id'], 'controller_commit': value['controller_commit'],
        'inputs_sha256': E.sha(E.canonical(value)), 'worker_sha256': value['guardian_files']['worker.py'],
        'guardian_sources_sha256': E.sha(E.canonical(value['guardian_files']))}
    R.bindings(expected)
    context_raw = regular('/execution/home-asset-rehearsal.json', 1048576)
    context = json.loads(context_raw, object_pairs_hook=E.unique)
    context_expected = {'protocol': 'stead.saved8-rehearsal-context/1',
        **{k: value[k] for k in ('run_id', 'controller_commit', 'host_namespaces', 'driver_files', 'source_files',
                               'runtime_sha256', 'pill_sha256', 'kernel_commit')},
        'inputs_sha256': expected['inputs_sha256']}
    require(context_raw == E.canonical(context_expected) + b'\n')
    R.exact(context, context_expected)
    require(type(value['host_namespaces']) is dict and set(value['host_namespaces']) == {'net', 'pid', 'mnt', 'user'})
    for name, prior in value['host_namespaces'].items():
        require(type(prior) is str and re.fullmatch(name + r':\[[0-9]{1,20}\]', prior)
                and os.readlink('/proc/self/ns/' + name) != prior)
    require(not any(Path(name).exists() for name in ('/home', '/piers', '/root/.ssh', '/run/user', '/native'))
            and list(Path('/state').iterdir()) == [] and [name for _, name in socket.if_nameindex()] == ['lo'])
    # Same existing native network setup; no route, host interface or extra capability.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as channel:
        channel.settimeout(.2)
        try:
            channel.connect(('192.0.2.1', 9))
        except OSError as error:
            require(error.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH))
        else:
            raise ValueError('Fixed saved8 external route refused')
    subprocess.run(['/usr/bin/ip', 'link', 'set', 'lo', 'up'], check=True, timeout=3,
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    provider = FixedProvider()
    admitted = json.loads(regular('/execution/ci-admission.json', 16384), object_pairs_hook=E.unique)
    lease = provider.require()
    R.exact(admitted, {**{k: lease[k] for k in ('run_id', 'unit', 'cgroup', 'limits', 'cpus')},
        'status': 'admitted', 'profile': hosted_lease.POLICY['profile'], 'authenticated_host': True})
    runtime_inputs(value)
    return value, expected, E.sha(E.canonical(context)), provider


def capture_files():
    root = Path('/state/home-captures')
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(directory)
        require(before.st_uid == os.getuid() and stat.S_IMODE(before.st_mode) == 0o700
                and set(os.listdir(directory)) == set(R.NAMES))
        values = {name: R.file_value(regular(root / name,
            E.MAX_CAPTURE if name.endswith('.jam') else R.MAX_DESCRIPTOR, captured=True)) for name in R.NAMES}
        require(identity(before) == identity(os.fstat(directory)) == identity(root.lstat())
                and set(os.listdir(directory)) == set(R.NAMES))
        return values
    finally:
        os.close(directory)


def failure_projection(report):
    if not isinstance(report, dict):
        return None
    value = {'protocol': 'stead.saved8-failure-observation/1', 'status': 'fail',
        'error_class': report.get('error_class'), 'cleanup_error_class': report.get('cleanup_error_class'),
        'completed_phases': report.get('phases'),
        'captures_observed': [stage for stage in E.STAGES if stage in report.get('captures', {})],
        'command_count': len(report.get('commands', [])),
        'native_reaped': report.get('cleanup', {}).get('reaped') is True}
    R.failed_report(value)
    return value


def main():
    os.umask(0o077)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    expected = report = provider = frame = None
    error, clean = 'admission-refusal', False
    try:
        inputs, expected, context_sha, provider = admission()
        def current():
            require(not STOP.is_set())
            return provider.require()
        current()
        from home_asset_rehearsal import runner
        error = 'runner-failed'
        report = runner.run(current)
        clean = type(report) is dict and E.canonical(report.get('cleanup')) == E.canonical(R.CLEAN)
        current()
        require(report.get('status') == 'pass' and clean)
        error = 'artifact-refusal'
        files = capture_files()
        current()
        # Root repeats this complete validation independently after owned cleanup.
        R.passed_report(report, expected, context_sha, inputs['desk_hashes'], inputs['assets'])
        R.artifacts(report, files, expected, context_sha)
        for path in SOURCE_NAMES:
            source_tree(path, inputs['source_files'][path])
        source_tree('/guardian', inputs['guardian_files'])
        mapped_owner(inputs)
        runtime_inputs(inputs)
        frame = R.encode({'protocol': 'stead.saved8-hosted-worker/1', **expected, 'status': 'pass',
            'error_class': 'none', 'cleanup': True, 'report': report, 'artifacts': files})
        current()
    except BaseException as caught:
        if type(caught) is OverflowError:
            error = 'frame-overflow'
        if expected is not None:
            try:
                frame = R.failure(expected, error, failure_projection(report), cleanup=clean)
            except BaseException:
                frame = R.failure(expected, error, None, cleanup=clean)
        else:
            frame = None
    if frame is None:
        sys.stderr.write('Fixed saved8 admission refused before bound frame\n')
        return 1
    sys.stdout.buffer.write(frame)
    sys.stdout.buffer.flush()
    # A completed frame is never a substitute for root EOF/reap/unit cleanup.
    value = json.loads(frame[len(R.PREFIX):-1], object_pairs_hook=E.unique)
    return 0 if value['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

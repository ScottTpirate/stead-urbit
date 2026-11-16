"""Root boundary for a separately admitted disposable model-proof guardian.

This module has no execution entry point. The future reviewed hosted profile
must supply its authenticated heartbeat and finite service owner. Neither an
intake receipt nor a worker message is runtime admission on its own.
"""
from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import select
import signal
import socket
import stat
import struct


NAMESPACES = ('user', 'mnt', 'pid', 'net')
SOURCE_NAMES = {'worker.py', 'client.py', 'model_connections.py', 'owned_child.py', 'interface.json'}
MODEL_NAME = 'Qwen3-0.6B-Q8_0.gguf'
MODEL_SHA = '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031'
MODEL_BYTES = 639446688
APPARMOR = 'stead-hosted-ci-userns-v1'
LIMITS = {'cpu.max': '100000 100000', 'memory.max': '2147483648',
          'memory.swap.max': '0', 'pids.max': '128'}


def require(ok):
    if not ok:
        raise ValueError('Fixed model owner refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_file(path, maximum, expected=None):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_nlink == 1
            and not before.st_mode & 0o022 and 0 < before.st_size <= maximum)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        require(identity(os.fstat(fd)) == identity(before))
        raw = bytearray()
        while part := os.read(fd, min(65536, maximum + 1 - len(raw))):
            raw.extend(part)
            require(len(raw) <= maximum)
        require(identity(os.fstat(fd)) == identity(before) and len(raw) == before.st_size)
        if expected is not None:
            require(set(expected) == {'bytes', 'sha256'} and type(expected['bytes']) is int
                    and expected['bytes'] == len(raw)
                    and hashlib.sha256(raw).hexdigest() == expected['sha256'])
        return bytes(raw)
    finally:
        os.close(fd)


def context(value):
    require(os.geteuid() == 0 and type(value) is dict and set(value) == {
        'protocol', 'run_id', 'unit', 'cpu', 'host_uid', 'host_gid', 'sources', 'bwrap_sha256'})
    require(value['protocol'] == 'stead.fixed-model-owner-context/1'
            and type(value['run_id']) is str and re.fullmatch('[a-f0-9]{32}', value['run_id'])
            and value['unit'] == 'stead-model-' + value['run_id'] + '.service'
            and type(value['cpu']) is int and 0 <= value['cpu'] < 1024
            and all(type(value[name]) is int and 0 < value[name] < 65534
                    for name in ('host_uid', 'host_gid'))
            and type(value['sources']) is dict and set(value['sources']) == SOURCE_NAMES
            and type(value['bwrap_sha256']) is str and re.fullmatch('[a-f0-9]{64}', value['bwrap_sha256']))
    for pin in value['sources'].values():
        require(type(pin) is dict and set(pin) == {'bytes', 'sha256'}
                and type(pin['bytes']) is int and 0 < pin['bytes'] <= 4 * 1024**2
                and type(pin['sha256']) is str and re.fullmatch('[a-f0-9]{64}', pin['sha256']))
    account = pwd.getpwnam('runner')
    require((value['host_uid'], value['host_gid']) == (account.pw_uid, account.pw_gid)
            and Path('/proc/sys/kernel/overflowuid').read_text().strip() == '65534'
            and Path('/proc/sys/kernel/overflowgid').read_text().strip() == '65534')
    return value


def group(value):
    context(value)
    expected = '/system.slice/' + value['unit']
    require(Path('/proc/self/cgroup').read_text().splitlines() == ['0::' + expected])
    path = Path('/sys/fs/cgroup' + expected)
    require(path.is_dir() and not path.is_symlink())
    for name, limit in LIMITS.items():
        require((path / name).read_text().strip() == limit)
    require((path / 'cpuset.cpus.effective').read_text().strip() == str(value['cpu'])
            and os.sched_getaffinity(0) == {value['cpu']}
            and Path('/proc/self/attr/current').read_text().strip() == APPARMOR + ' (unconfined)')
    return path


def directory(path, mode, gid=0):
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and info.st_gid == gid
            and stat.S_IMODE(info.st_mode) == mode)
    return info


def namespace_command(job, value):
    """Fixed arguments only; the caller has already verified the exact intake."""
    require(re.fullmatch('/var/lib/stead-model-proof-[a-z0-9]{8}', str(job)) is not None)
    directory(job, 0o750, value['host_gid'])
    directory(job / 'input', 0o550, value['host_gid'])
    directory(job / 'lease', 0o550, value['host_gid'])
    require({p.name for p in (job / 'lease').iterdir()} == {'guardian.json'})
    directory(job / 'model', 0o755)
    directory(job / 'runtime', 0o755)
    require({p.name for p in (job / 'input').iterdir()} == SOURCE_NAMES | {'owner.json'})
    require({p.name for p in (job / 'model').iterdir()} == {MODEL_NAME})
    for name, pin in value['sources'].items():
        read_file(job / 'input' / name, 4 * 1024**2, pin)
    read_file(job / 'input/owner.json', 262144)
    require(hashlib.sha256(read_file(Path('/usr/bin/bwrap'), 4 * 1024**2)).hexdigest()
            == value['bwrap_sha256'])
    argv = ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--die-with-parent',
            '--uid', '1000', '--gid', '1000', '--cap-drop', 'ALL', '--clearenv',
            '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        argv += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
    for name in ('input', 'runtime', 'model', 'lease'):
        argv += ['--ro-bind', str(job / name), '/' + name]
    return argv + ['--proc', '/proc', '--dev', '/dev',
        '--perms', '0700', '--size', str(8 * 1024**2), '--tmpfs', '/output',
        '--perms', '0700', '--size', str(16 * 1024**2), '--tmpfs', '/tmp',
        '--chdir', '/output', '--', '/usr/bin/python3', '-I', '-B', '/input/worker.py']


def launch_child(job, value, parent):
    """Use only in a new single-threaded root child of the admitted guardian."""
    context(value)
    require(type(parent) is int and parent > 1 and os.getppid() == parent
            and len(list(Path('/proc/self/task').iterdir())) == 1)
    command = namespace_command(job, value)
    os.setgroups([])
    os.setgid(value['host_gid'])
    os.setuid(value['host_uid'])
    # UID change clears PDEATHSIG. Re-arm immediately and close the parent race;
    # the finite KillMode=control-group service covers even this setup interval.
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(1, signal.SIGKILL, 0, 0, 0) == 0
            and libc.prctl(38, 1, 0, 0, 0) == 0 and os.getppid() == parent)
    require(Path('/proc/self/attr/current').read_text().strip() == APPARMOR + ' (unconfined)')
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', LANG='C.UTF-8')
    os.execv(command[0], command)


def proc_identity(pid):
    raw = Path('/proc', str(pid), 'stat').read_text()
    fields = raw[raw.rindex(')') + 2:].split()
    return (pid, int(fields[19]))


def alive(fd):
    require(not select.select([fd], [], [], 0)[0])


def pin_ready(job, value, ready, owner_sha256, heartbeat):
    """Discover the actual worker; message PID is only its inner namespace PID."""
    heartbeat()
    cgroup = group(value)
    require(type(ready) is dict and set(ready) == {'protocol', 'pid', 'uid', 'gid', 'namespaces', 'owner_sha256'}
            and ready['protocol'] == 'stead.fixed-model-ready/1'
            and type(ready['pid']) is int and ready['pid'] > 1
            and type(ready['uid']) is int and ready['uid'] == 1000
            and type(ready['gid']) is int and ready['gid'] == 1000
            and ready['owner_sha256'] == owner_sha256
            and type(ready['namespaces']) is dict and set(ready['namespaces']) == set(NAMESPACES))
    matches = []
    for text in (cgroup / 'cgroup.procs').read_text().splitlines():
        pid = int(text)
        if pid == os.getpid():
            continue
        root = Path('/proc', text)
        try:
            state = dict(line.split(':', 1) for line in (root / 'status').read_text().splitlines() if ':' in line)
            if ((root / 'cmdline').read_bytes() == b'/usr/bin/python3\0-I\0-B\0/input/worker.py\0'
                    and state['Uid'].split() == [str(value['host_uid'])] * 4
                    and state['Gid'].split() == [str(value['host_gid'])] * 4
                    and int(state['NSpid'].split()[-1]) == ready['pid']):
                matches.append(pid)
        except FileNotFoundError:
            continue
    require(len(matches) == 1)
    pid = matches[0]
    pidfd = os.pidfd_open(pid, 0)
    rootfd = outputfd = None
    try:
        anchor = proc_identity(pid)
        root = Path('/proc', str(pid))
        state = dict(line.split(':', 1) for line in (root / 'status').read_text().splitlines() if ':' in line)
        require(state['NoNewPrivs'].strip() == '1' and all(state[name].strip() == '0000000000000000'
                for name in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')))
        for name in NAMESPACES:
            observed = os.readlink(root / 'ns' / name)
            require(observed == ready['namespaces'][name] and observed != os.readlink('/proc/self/ns/' + name))
        for name, host in (('uid', value['host_uid']), ('gid', value['host_gid'])):
            require((root / (name + '_map')).read_text().split() == ['1000', str(host), '1'])
        require((root / 'cgroup').read_text().splitlines() == ['0::/system.slice/' + value['unit']])
        rootfd = os.open(root / 'root', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        rootinfo = os.fstat(rootfd)
        require((rootinfo.st_dev, rootinfo.st_ino) != (Path('/').stat().st_dev, Path('/').stat().st_ino))
        expected_names = {'usr', 'bin', 'sbin', 'lib', 'lib64', 'proc', 'dev', 'input', 'runtime', 'model', 'lease', 'tmp', 'output'}
        require(set(os.listdir(rootfd)) == expected_names)
        for name in ('input', 'runtime', 'model', 'lease'):
            observed = os.stat(name, dir_fd=rootfd, follow_symlinks=False)
            original = (job / name).lstat()
            require((observed.st_dev, observed.st_ino) == (original.st_dev, original.st_ino))
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=rootfd)
            try:
                require(os.fstatvfs(fd).f_flag & os.ST_RDONLY)
            finally:
                os.close(fd)
        for name in ('tmp', 'output'):
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=rootfd)
            try:
                info = os.fstat(fd)
                require(info.st_uid == value['host_uid'] and stat.S_IMODE(info.st_mode) == 0o700
                        and not os.listdir(fd) and not os.fstatvfs(fd).f_flag & os.ST_RDONLY)
            finally:
                os.close(fd)
        # Retain the actual output mount itself, not only its parent root mount.
        # Its files remain readable after the private namespace is reaped.
        outputfd = os.open('output', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                           | os.O_CLOEXEC, dir_fd=rootfd)
        devfd = os.open('dev', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                        | os.O_CLOEXEC, dir_fd=rootfd)
        try:
            dev = os.fstat(devfd)
            host_dev = Path('/dev').stat()
            require(dev.st_dev != host_dev.st_dev)
            shm = os.stat('shm', dir_fd=devfd, follow_symlinks=False)
            require(stat.S_ISDIR(shm.st_mode) and shm.st_uid == value['host_uid']
                    and stat.S_IMODE(shm.st_mode) == 0o755 and shm.st_dev == dev.st_dev)
        finally:
            os.close(devfd)
        heartbeat()
        group(value)
        alive(pidfd)
        require(proc_identity(pid) == anchor)
        return {'pid': pid, 'pidfd': pidfd, 'rootfd': rootfd, 'outputfd': outputfd, 'identity': anchor,
                'root_identity': (rootinfo.st_dev, rootinfo.st_ino), 'namespaces': ready['namespaces']}
    except BaseException:
        if outputfd is not None:
            os.close(outputfd)
        if rootfd is not None:
            os.close(rootfd)
        os.close(pidfd)
        raise


def close_anchor(anchor):
    first = None
    for name in ('outputfd', 'rootfd', 'pidfd'):
        try:
            os.close(anchor[name])
        except BaseException as error:
            if first is None:
                first = error
    if first is not None:
        raise first


def current(anchor, value, heartbeat):
    heartbeat()
    group(value)
    alive(anchor['pidfd'])
    require(proc_identity(anchor['pid']) == anchor['identity'])
    root = Path('/proc', str(anchor['pid']))
    require((root / 'cgroup').read_text().splitlines() == ['0::/system.slice/' + value['unit']])
    require({name: os.readlink(root / 'ns' / name) for name in NAMESPACES} == anchor['namespaces'])
    observed = (root / 'root').stat()
    require((observed.st_dev, observed.st_ino) == anchor['root_identity'])
    state = dict(line.split(':', 1) for line in (root / 'status').read_text().splitlines() if ':' in line)
    require(state['Uid'].split() == [str(value['host_uid'])] * 4
            and state['Gid'].split() == [str(value['host_gid'])] * 4
            and state['NoNewPrivs'].strip() == '1'
            and all(state[name].strip() == '0000000000000000'
                    for name in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')))


def loopback_observation(anchor, value, heartbeat):
    """Observe only links/flags in the pinned network namespace, then restore.

    No user/mount/PID namespace switch, address change or connection occurs.
    The guardian is single threaded and all proof descriptors close before go.
    """
    current(anchor, value, heartbeat)
    require(len(list(Path('/proc/self/task').iterdir())) == 1)
    prior = {name: os.readlink('/proc/self/ns/' + name) for name in NAMESPACES}
    own = os.open('/proc/self/ns/net', os.O_RDONLY | os.O_CLOEXEC)
    target = None
    entered = False
    try:
        target = os.open('/proc/' + str(anchor['pid']) + '/ns/net', os.O_RDONLY | os.O_CLOEXEC)
        require('net:[' + str(os.fstat(target).st_ino) + ']' == anchor['namespaces']['net'])
        entered = True  # Restore even if setns raises after changing the namespace.
        os.setns(target, os.CLONE_NEWNET)
        require(os.readlink('/proc/self/ns/net') == anchor['namespaces']['net'])
        require([name for _, name in socket.if_nameindex()] == ['lo'])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
            raw = fcntl.ioctl(control.fileno(), 0x8913, struct.pack('16sH14x', b'lo', 0))
        require(struct.unpack('16sH14x', raw)[1] & 1)
    finally:
        if entered:
            try:
                os.setns(own, os.CLONE_NEWNET)
                require({name: os.readlink('/proc/self/ns/' + name) for name in NAMESPACES} == prior)
            except BaseException:
                # The finite KillMode service owns all descendants even when
                # restoration itself fails. Never continue in the wrong netns.
                os._exit(125)
        if target is not None:
            os.close(target)
        os.close(own)
    current(anchor, value, heartbeat)
    return {'sole_loopback_up': True, 'network_namespace': anchor['namespaces']['net'],
            'guardian_namespace_restored': True, 'proof_descriptors_closed': True}


def read_output(anchor, value, name, expected):
    """Only called after owned descendants are reaped and all streams reach EOF."""
    require(name in {'request.json', 'response.bin', 'proposal.json', 'report.json'})
    limits = {'request.json': 8192, 'response.bin': 32768,
              'proposal.json': 65536, 'report.json': 16384}
    require(type(expected) is dict and set(expected) == {'bytes', 'sha256'}
            and type(expected['bytes']) is int and 0 < expected['bytes'] <= limits[name]
            and type(expected['sha256']) is str and re.fullmatch('[a-f0-9]{64}', expected['sha256']))
    require(set(os.listdir(anchor['outputfd'])) == {'client'})
    directory = os.open('client', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                        | os.O_CLOEXEC, dir_fd=anchor['outputfd'])
    fd = None
    try:
        info = os.fstat(directory)
        require(info.st_uid == value['host_uid'] and info.st_gid == value['host_gid']
                and stat.S_IMODE(info.st_mode) == 0o700 and set(os.listdir(directory)) == set(limits))
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == value['host_uid']
                and before.st_gid == value['host_gid'] and before.st_nlink == 1
                and stat.S_IMODE(before.st_mode) == 0o600 and before.st_size == expected['bytes'])
        raw = os.read(fd, limits[name] + 1)
        require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
                and identity(os.fstat(fd)) == identity(before))
        return raw
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


FAILURE_LIMITS = {'request.json': 8192, 'response.bin': 32768, 'report.json': 16384}


def read_failed_output(anchor, value):
    """Forensic read after admission, EOF and reaping; never a proposal receipt.

    The retained descriptor is the exact private output mount pinned before go.
    None denotes absence; a present empty file retains its zero length and hash.
    """
    missing = {name: {'present': False, 'bytes': None, 'sha256': None}
               for name in FAILURE_LIMITS}
    output = anchor['outputfd']
    before_output = os.fstat(output)
    require(stat.S_ISDIR(before_output.st_mode) and before_output.st_uid == value['host_uid']
            and before_output.st_gid == value['host_gid']
            and stat.S_IMODE(before_output.st_mode) == 0o700)
    entries = set(os.listdir(output))
    require(entries <= {'client'})
    if not entries:
        require(identity(os.fstat(output)) == identity(before_output))
        return missing, {}
    directory = os.open('client', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                        | os.O_CLOEXEC, dir_fd=output)
    try:
        before_directory = os.fstat(directory)
        require(stat.S_ISDIR(before_directory.st_mode)
                and before_directory.st_uid == value['host_uid']
                and before_directory.st_gid == value['host_gid']
                and stat.S_IMODE(before_directory.st_mode) == 0o700)
        limits = {**FAILURE_LIMITS, 'proposal.json': 65536}
        names = set(os.listdir(directory))
        require(names <= set(limits))
        retained = {}
        for name in sorted(names):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                         | os.O_CLOEXEC, dir_fd=directory)
            try:
                before = os.fstat(fd)
                require(stat.S_ISREG(before.st_mode) and before.st_uid == value['host_uid']
                        and before.st_gid == value['host_gid'] and before.st_nlink == 1
                        and stat.S_IMODE(before.st_mode) == 0o600
                        and 0 <= before.st_size <= limits[name])
                raw = os.read(fd, limits[name] + 1)
                require(len(raw) == before.st_size and identity(os.fstat(fd)) == identity(before))
                if name in FAILURE_LIMITS:
                    retained[name] = raw
                    missing[name] = {'present': True, 'bytes': len(raw),
                                     'sha256': hashlib.sha256(raw).hexdigest()}
            finally:
                os.close(fd)
        require(set(os.listdir(directory)) == names
                and identity(os.fstat(directory)) == identity(before_directory)
                and identity(os.fstat(output)) == identity(before_output))
        return missing, retained
    finally:
        os.close(directory)


def read_failed_retained(path, maximum, expected):
    """Root-retained diagnostic bytes; success read_file remains unchanged."""
    require(type(expected) is dict and set(expected) == {'bytes', 'sha256'}
            and type(expected['bytes']) is int and 0 <= expected['bytes'] <= maximum
            and type(expected['sha256']) is str and re.fullmatch('[a-f0-9]{64}', expected['sha256']))
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_gid == 0
            and before.st_nlink == 1 and stat.S_IMODE(before.st_mode) == 0o600
            and before.st_size == expected['bytes'])
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        require(identity(os.fstat(fd)) == identity(before))
        raw = os.read(fd, maximum + 1)
        require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
                and identity(os.fstat(fd)) == identity(before))
        return raw
    finally:
        os.close(fd)

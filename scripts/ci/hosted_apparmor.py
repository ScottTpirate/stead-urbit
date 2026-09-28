"""Explicit AppArmor setup for the authenticated disposable Ubuntu CI VM.

This named userns allowance is not an AppArmor confinement sandbox. Ordinary
profile transitions are hardened VM-wide; the existing UID, namespace, mount,
capability and cgroup boundaries still provide the worker's isolation.
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess

PROFILE = 'stead-hosted-ci-userns-v1'
POLICY = ('abi <abi/4.0>,\nprofile ' + PROFILE + ' flags=(unconfined) {\n  userns,\n}\n').encode()
POLICY_SHA256 = hashlib.sha256(POLICY).hexdigest()
POLICY_PATH = Path('/var/lib/stead-ci-controller/hosted-apparmor.profile')
SYSCTLS = ('apparmor_restrict_unprivileged_userns', 'apparmor_restrict_unprivileged_unconfined')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path, maximum=4096):
    with Path(path).open('rb') as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, 'AppArmor observation bound')
    return raw.decode().strip()


def label():
    return read('/proc/self/attr/current')


def require_label():
    actual = label()
    require(actual == PROFILE + ' (unconfined)', 'AppArmor task label differs')
    return actual


def settings():
    require(read('/sys/module/apparmor/parameters/enabled') == 'Y', 'AppArmor is not active')
    return {name: read('/proc/sys/kernel/' + name) for name in SYSCTLS}


def policy_bytes():
    descriptor = os.open(POLICY_PATH, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
            and not info.st_mode & 0o022, 'AppArmor policy custody differs')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(4097)
        require(len(raw) <= 4096, 'AppArmor policy byte bound')
        return raw
    finally:
        os.close(descriptor)


def observe():
    values = settings()
    require(values == dict.fromkeys(SYSCTLS, '1'), 'AppArmor hardening changed')
    require(policy_bytes() == POLICY, 'AppArmor policy file changed')
    profiles = read('/sys/kernel/security/apparmor/profiles', 1048576).splitlines()
    require(PROFILE + ' (unconfined)' in profiles, 'AppArmor allowance is not loaded')
    return {'profile': PROFILE, 'policy_sha256': POLICY_SHA256, 'settings': values}


def prepare(regular_root):
    """Called only after signed hosted admission; never on the workstation."""
    require(os.getuid() == 0, 'AppArmor setup requires root')
    before = settings()
    require(before[SYSCTLS[0]] == '1' and before[SYSCTLS[1]] in ('0', '1'), 'Unsupported AppArmor settings')
    if before[SYSCTLS[1]] == '0':
        Path('/proc/sys/kernel/' + SYSCTLS[1]).write_text('1\n')
    require(settings() == dict.fromkeys(SYSCTLS, '1'), 'AppArmor hardening was not applied')
    regular_root(POLICY_PATH.parent)
    try:
        descriptor = os.open(POLICY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        regular_root(POLICY_PATH)
        require(policy_bytes() == POLICY, 'Existing AppArmor policy differs')
    else:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(POLICY)
    parser = '/usr/sbin/apparmor_parser'
    version = subprocess.check_output([parser, '--version'], timeout=3).decode().strip()
    subprocess.run([parser, '--replace', '--skip-cache', str(POLICY_PATH)],
        check=True, capture_output=True, timeout=10)
    abi = read('/etc/apparmor.d/abi/4.0', 65536)
    return {'before': before, 'after': observe(), 'policy_text': POLICY.decode(),
        'parser_version': version, 'kernel': os.uname().release,
        'abi_4_0_text_sha256': hashlib.sha256(abi.encode()).hexdigest()}


# No native/runtime code or candidate input enters this fixed negative probe.
# It tests actual capability use after a profile transition, not only its exit.
# Earlier mapping/socket failures remain diagnostics, never ioctl evidence.
UNRELATED_PROBE = r'''
import ctypes, fcntl, json, os, pathlib, socket, struct, sys, time
def read(path):
    with open(path) as stream:
        text = stream.read(8193)
    if len(text) > 8192:
        raise ValueError('Fixed process observation bound')
    return text.strip()
def snapshot():
    state = dict(line.split(':', 1) for line in read('/proc/self/status').splitlines() if ':' in line)
    return {'uid': os.getuid(), 'gid': os.getgid(), 'label': read('/proc/self/attr/current'),
        'nnp': state['NoNewPrivs'].strip(), 'cap_eff': state['CapEff'].strip(),
        'user_ns': os.readlink('/proc/self/ns/user'), 'net_ns': os.readlink('/proc/self/ns/net'),
        'uid_map': [list(map(int, line.split())) for line in read('/proc/self/uid_map').splitlines()],
        'gid_map': [list(map(int, line.split())) for line in read('/proc/self/gid_map').splitlines()]}
value = {'pid': os.getpid(), 'started_ns': time.time_ns(), 'stage': 'initial', 'network_attempts': []}
def stage(name):
    value['stage'] = name
    value['stage_started_ns'] = time.time_ns()
try:
    value['before'] = snapshot()
    uid, gid = os.getuid(), os.getgid()
    aa = ctypes.CDLL('libapparmor.so.1', use_errno=True)
    aa.aa_change_profile.argtypes = [ctypes.c_char_p]
    stage('transition')
    ctypes.set_errno(0)
    value['transition'] = aa.aa_change_profile(sys.argv[1].encode())
    value['transition_errno'] = ctypes.get_errno()
    value['after_transition'] = read('/proc/self/attr/current')
    libc = ctypes.CDLL(None, use_errno=True)
    stage('unshare')
    ctypes.set_errno(0)
    value['unshare'] = libc.unshare(0x10000000 | 0x40000000)
    value['unshare_errno'] = ctypes.get_errno()
    value['after_unshare'] = snapshot()
    if value['unshare'] == 0:
        stage('mapping')
        pathlib.Path('/proc/self/setgroups').write_text('deny\n')
        pathlib.Path('/proc/self/uid_map').write_text('0 ' + str(uid) + ' 1\n')
        pathlib.Path('/proc/self/gid_map').write_text('0 ' + str(gid) + ' 1\n')
        value['mapped'] = snapshot()
        mapped = value['mapped']
        if (mapped['uid'] != 0 or mapped['gid'] != 0 or mapped['uid_map'] != [[0, uid, 1]]
                or mapped['gid_map'] != [[0, gid, 1]] or mapped['nnp'] != '1'
                or not int(mapped['cap_eff'], 16) & (1 << 12)):
            raise ValueError('Mapped namespace identity differs')
        # Device ioctls also work through AF_UNIX. Both sockets are created
        # inside the new namespace; neither is bound or connected anywhere.
        for family, number in (('AF_INET', socket.AF_INET), ('AF_UNIX', socket.AF_UNIX)):
            attempt = {'family': family, 'started_ns': time.time_ns()}
            value['network_attempts'].append(attempt)
            try:
                stage('socket-create')
                with socket.socket(number, socket.SOCK_DGRAM) as channel:
                    attempt['socket_errno'] = 0
                    stage('flags-read')
                    current = fcntl.ioctl(channel.fileno(), 0x8913, struct.pack('16sH14x', b'lo', 0))
                    flags = struct.unpack_from('H', current, 16)[0]
                    attempt['flags_read_errno'] = 0
                    attempt['flags_before'] = flags
                    if flags & 1:
                        raise ValueError('New network namespace loopback is already up')
                    attempt['before_write'] = snapshot()
                    stage('flags-write')
                    try:
                        fcntl.ioctl(channel.fileno(), 0x8914, struct.pack('16sH14x', b'lo', flags | 1))
                        attempt['flags_write_errno'] = 0
                    except OSError as error:
                        attempt['flags_write_errno'] = error.errno
            except OSError as error:
                attempt['failed_stage'] = value['stage']
                attempt['errno'] = error.errno
            finally:
                attempt['finished_ns'] = time.time_ns()
            if 'flags_write_errno' in attempt:
                break
except Exception as error:
    value['probe_error'] = {'type': type(error).__name__, 'errno': getattr(error, 'errno', None),
        'message': str(error)[:256]}
finally:
    try:
        value['after'] = snapshot()
    except Exception as error:
        value['snapshot_error'] = type(error).__name__
    value['finished_ns'] = time.time_ns()
    print(json.dumps(value), flush=True)
'''


def verify_unrelated(value, uid, gid):
    import errno
    require(not value.get('probe_error') and not value.get('snapshot_error'), 'Unrelated control stopped before the intended check')
    before, after = value['before'], value['after']
    require({key: before[key] for key in ('uid', 'gid', 'label', 'nnp', 'cap_eff')}
        == {'uid': uid, 'gid': gid, 'label': 'unconfined', 'nnp': '1',
            'cap_eff': '0000000000000000'}, 'Unrelated control initial identity differs')
    require(type(value['pid']) is int and value['pid'] > 0
        and value['started_ns'] <= value['stage_started_ns'] <= value['finished_ns'], 'Unrelated control observation identity differs')
    require(value['transition'] == 0 or (value['transition'] == -1
        and value['transition_errno'] in (errno.EPERM, errno.EACCES)), 'Unexpected profile transition failure')
    require(all(label != PROFILE + ' (unconfined)' for label in
        (value['after_transition'], after['label'])), 'Unrelated task acquired CI allowance')
    refused_namespace = value['stage'] == 'unshare' and value['unshare'] == -1 and value['unshare_errno'] in (errno.EPERM, errno.EACCES)
    # No exec occurs after unshare: lost capabilities cannot explain refusal.
    mapped = value.get('mapped', {})
    correct_mapping = (mapped.get('uid_map') == [[0, uid, 1]] and mapped.get('gid_map') == [[0, gid, 1]]
        and after.get('uid_map') == [[0, uid, 1]] and after.get('gid_map') == [[0, gid, 1]]
        and mapped.get('uid') == mapped.get('gid') == after['uid'] == after['gid'] == 0
        and mapped.get('nnp') == '1' and int(mapped.get('cap_eff', '0'), 16) & (1 << 12))
    attempts = value['network_attempts']
    require([item['family'] for item in attempts] in ([], ['AF_INET'], ['AF_INET', 'AF_UNIX']),
        'Unrelated control socket sequence differs')
    require(not any(item.get('flags_write_errno') == 0 for item in attempts), 'Unrelated privileged write succeeded')
    refused_writes = [item for item in attempts if item.get('flags_write_errno') in (errno.EPERM, errno.EACCES)
        and item.get('socket_errno') == item.get('flags_read_errno') == 0 and not item['flags_before'] & 1
        and item['before_write'] == mapped]
    refused_capability = (value['stage'] == 'flags-write' and value['unshare'] == 0 and correct_mapping
        and before['user_ns'] != after['user_ns'] and before['net_ns'] != after['net_ns']
        and int(after['cap_eff'], 16) & (1 << 12)
        and mapped == after and len(refused_writes) == 1)
    require(after['nnp'] == '1', 'Unrelated control lost no-new-privileges')
    require(refused_namespace or refused_capability, 'Unrelated namespace capability was not denied')
    return value


def unrelated(account):
    parent = os.getpid()
    def confine():
        os.setgroups([])
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
        libc = ctypes.CDLL(None, use_errno=True)
        if (libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0
                or os.getppid() != parent):
            os._exit(126)
    process = subprocess.Popen(['/usr/bin/python3', '-I', '-B', '-c', UNRELATED_PROBE, PROFILE],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        preexec_fn=confine, start_new_session=True, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    try:
        stdout, stderr = process.communicate(timeout=5)
        return {'classification': 'pre-native-unrelated-control-only', 'exit_code': process.returncode,
            'stdout': stdout[:8192].decode('utf-8', errors='replace'),
            'stderr': stderr[:8192].decode('utf-8', errors='replace'),
            'truncated': len(stdout) > 8192 or len(stderr) > 8192}
    finally:
        # The fixed probe performs its ioctl itself and starts no descendants.
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        process.stdout.close()
        process.stderr.close()


def verify_probe(result, uid, gid):
    require(result['classification'] == 'pre-native-unrelated-control-only'
        and result['exit_code'] == 0 and not result['stderr'] and not result['truncated']
        and result['stdout'], 'Unrelated AppArmor probe did not produce bounded evidence')
    return verify_unrelated(json.loads(result['stdout']), uid, gid)

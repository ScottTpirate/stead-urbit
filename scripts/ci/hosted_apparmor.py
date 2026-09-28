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


# This fixed probe creates namespaces but never modifies mounts, opens network
# sockets, writes mappings, execs or starts descendants. Revision 2 measures a
# direct SYS_ADMIN namespace-operation refusal, not the earlier ioctl probe.
PROBE_PROTOCOL = 'stead.hosted-unrelated-namespace/2'
UNRELATED_PROBE = r'''
import ctypes, json, os, sys, time
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
        'mnt_ns': os.readlink('/proc/self/ns/mnt'),
        'uid_map': [list(map(int, line.split())) for line in read('/proc/self/uid_map').splitlines()],
        'gid_map': [list(map(int, line.split())) for line in read('/proc/self/gid_map').splitlines()]}
value = {'protocol': 'stead.hosted-unrelated-namespace/2', 'pid': os.getpid(),
    'started_ns': time.time_ns(), 'stage': 'initial'}
def stage(name):
    value['stage'] = name
    value['stage_started_ns'] = time.time_ns()
try:
    value['before'] = snapshot()
    aa = ctypes.CDLL('libapparmor.so.1', use_errno=True)
    aa.aa_change_profile.argtypes = [ctypes.c_char_p]
    stage('transition')
    ctypes.set_errno(0)
    value['transition'] = aa.aa_change_profile(sys.argv[1].encode())
    value['transition_errno'] = ctypes.get_errno()
    value['after_transition'] = read('/proc/self/attr/current')
    libc = ctypes.CDLL(None, use_errno=True)
    stage('unshare')
    value['unshare_flags'] = 0x10000000 | 0x40000000
    ctypes.set_errno(0)
    value['unshare'] = libc.unshare(value['unshare_flags'])
    value['unshare_errno'] = ctypes.get_errno()
    value['after_unshare'] = snapshot()
    if value['unshare'] == 0:
        value['before_mount'] = snapshot()
        value['mount_flags'] = 0x00020000
        stage('mount-unshare')
        ctypes.set_errno(0)
        value['mount_unshare'] = libc.unshare(value['mount_flags'])
        value['mount_errno'] = ctypes.get_errno()
        value['mount_finished_ns'] = time.time_ns()
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
    require(value['protocol'] == PROBE_PROTOCOL, 'Unrelated control protocol differs')
    require(not value.get('probe_error') and not value.get('snapshot_error'), 'Unrelated control stopped before the intended check')
    before, after = value['before'], value['after']
    require({key: before[key] for key in ('uid', 'gid', 'label', 'nnp', 'cap_eff')}
        == {'uid': uid, 'gid': gid, 'label': 'unconfined', 'nnp': '1',
            'cap_eff': '0000000000000000'}, 'Unrelated control initial identity differs')
    require(type(value['pid']) is int and value['pid'] > 0
        and value['started_ns'] <= value['stage_started_ns'] <= value['finished_ns'], 'Unrelated control observation identity differs')
    require((value['transition'] == 0 and value['transition_errno'] == 0) or (value['transition'] == -1
        and value['transition_errno'] in (errno.EPERM, errno.EACCES)), 'Unexpected profile transition failure')
    require(all(label != PROFILE + ' (unconfined)' for label in
        (value['after_transition'], after['label'])), 'Unrelated task acquired CI allowance')
    require(value['unshare_flags'] == 0x50000000 and after['nnp'] == '1', 'Unrelated control namespace flags or NNP differ')
    refused_namespace = (value['stage'] == 'unshare' and value['unshare'] == -1
        and value['unshare_errno'] in (errno.EPERM, errno.EACCES) and 'mount_unshare' not in value
        and all(before[key] == after[key] for key in ('user_ns', 'net_ns', 'mnt_ns')))
    # The second call uses only CLONE_NEWNS: Linux checks SYS_ADMIN in the
    # current (new) user namespace. No mapping or exec can confound that check.
    middle = value.get('before_mount', {})
    restricted = ('unprivileged_userns (enforce)', PROFILE + '//&unprivileged_userns (mixed)')
    refused_capability = (value['stage'] == 'mount-unshare' and value['unshare'] == 0
        and value['unshare_errno'] == 0 and value.get('mount_flags') == 0x00020000
        and value.get('mount_unshare') == -1 and value.get('mount_errno') in (errno.EPERM, errno.EACCES)
        and middle == value['after_unshare'] == after and middle.get('label') in restricted
        and before['user_ns'] != after['user_ns'] and before['net_ns'] != after['net_ns']
        and before['mnt_ns'] == after['mnt_ns'] and int(after['cap_eff'], 16) & (1 << 21)
        and value['stage_started_ns'] <= value['mount_finished_ns'] <= value['finished_ns'])
    require(refused_namespace or refused_capability, 'Unrelated namespace capability was not denied')
    return {**value, 'observed_control': 'namespace-create-denied' if refused_namespace else 'sys-admin-unshare-denied'}


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
        # The fixed probe performs its syscalls itself and starts no descendants.
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

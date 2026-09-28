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
UNRELATED_PROBE = r'''
import ctypes, errno, fcntl, json, os, pathlib, socket, struct, sys
def label():
    return pathlib.Path('/proc/self/attr/current').read_text().strip()
state = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
before = {'uid': os.getuid(), 'label': label(), 'nnp': state['NoNewPrivs'].strip(),
          'cap_eff': state['CapEff'].strip()}
aa = ctypes.CDLL('libapparmor.so.1', use_errno=True)
aa.aa_change_profile.argtypes = [ctypes.c_char_p]
ctypes.set_errno(0)
transition = aa.aa_change_profile(sys.argv[1].encode())
transition_errno = ctypes.get_errno()
after_transition = label()
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
unshare = libc.unshare(0x10000000 | 0x40000000)
unshare_errno = ctypes.get_errno()
network_errno = None
if unshare == 0:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as channel:
        current = fcntl.ioctl(channel.fileno(), 0x8913, struct.pack('16sH14x', b'lo', 0))
        flags = struct.unpack_from('H', current, 16)[0]
        try:
            fcntl.ioctl(channel.fileno(), 0x8914, struct.pack('16sH14x', b'lo', flags | 1))
            network_errno = 0
        except OSError as error:
            network_errno = error.errno
state = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
print(json.dumps({'before': before, 'transition': transition, 'transition_errno': transition_errno,
    'after_transition': after_transition, 'unshare': unshare, 'unshare_errno': unshare_errno,
    'after_unshare': label(), 'network_errno': network_errno, 'cap_eff_after': state['CapEff'].strip(),
    'nnp_after': state['NoNewPrivs'].strip()}), flush=True)
'''


def verify_unrelated(value, uid):
    import errno
    require(value['before'] == {'uid': uid, 'label': 'unconfined', 'nnp': '1',
        'cap_eff': '0000000000000000'}, 'Unrelated control initial identity differs')
    require(value['transition'] == 0 or (value['transition'] == -1
        and value['transition_errno'] in (errno.EPERM, errno.EACCES)), 'Unexpected profile transition failure')
    require(value['after_transition'] != PROFILE + ' (unconfined)', 'Unrelated task acquired CI allowance')
    refused_namespace = value['unshare'] == -1 and value['unshare_errno'] in (errno.EPERM, errno.EACCES)
    # No exec occurs after unshare: lost capabilities cannot explain refusal.
    refused_capability = (value['unshare'] == 0 and int(value['cap_eff_after'], 16) & (1 << 12)
        and value['network_errno'] in (errno.EPERM, errno.EACCES))
    require(value['nnp_after'] == '1', 'Unrelated control lost no-new-privileges')
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


def verify_probe(result, uid):
    require(result['classification'] == 'pre-native-unrelated-control-only'
        and result['exit_code'] == 0 and not result['stderr'] and not result['truncated']
        and result['stdout'], 'Unrelated AppArmor probe did not produce bounded evidence')
    return verify_unrelated(json.loads(result['stdout']), uid)

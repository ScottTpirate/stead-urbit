"""Report read-only prerequisites from one private Stead service account."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

from execution_policy import GuardError, Policy, sample_temperatures, validate_sample
from git_pack_worker_service import BWRAP, sandbox_ready
from portable_recovery import encoded


MIB = 1024 * 1024
QUALIFIED_GIT = '2.55.1'
CONTROLS = {'cpu': 'cpu.max', 'memory': 'memory.max', 'pids': 'pids.max', 'io': 'io.max'}
BWRAP_FLAGS = ('--bind-fd', '--ro-bind-fd', '--disable-userns')
TOOLS = {'git': ('--version',), 'bubblewrap': ('--version',), 'nginx': ('-v',),
         'gunicorn': ('--version',), 'gpg': ('--no-options', '--homedir', '/nonexistent', '--version')}
VERSION = re.compile(r'(?<!\d)\d{1,4}(?:\.\d{1,5}){1,3}(?!\d)')
CONTROL_SCALAR = re.compile(r'(?:max|[0-9]{1,20})')
ENV = {'PATH': '/usr/bin:/usr/sbin', 'HOME': '/nonexistent', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}


def _read(path, maximum=16_384):
    with path.open('rb') as source:
        raw = source.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('preflight input bound')
    return raw.decode('ascii')


def _scalar(path):
    value = _read(path, 64).strip()
    if not CONTROL_SCALAR.fullmatch(value):
        raise ValueError('preflight cgroup control')
    return None if value == 'max' else int(value)


def cgroups(proc=Path('/proc'), mounted=Path('/sys/fs/cgroup')):
    result = {'version': None, 'controllers': {}, 'memory_headroom_bytes': None, 'status': 'unavailable'}
    try:
        listed = set(_read(mounted / 'cgroup.controllers').split())
        paths = [row[3:] for row in _read(proc / 'self/cgroup').splitlines() if row.startswith('0::')]
        if len(paths) != 1 or not paths[0].startswith('/'):
            return result
        path = Path(paths[0])
        if '..' in path.parts or len(path.parts) > 64:
            return result
        group = mounted.joinpath(*path.parts[1:])
        result['version'] = 2
        limits = {}
        for key, name in CONTROLS.items():
            active = False
            try:
                _read(group / name)
                active = True
            except (OSError, ValueError):
                pass
            limits[key] = {'advertised': key in listed, 'readable': active}
        result['controllers'] = limits
        available = []
        for parent in (group, *group.parents):
            if parent == mounted:
                break
            limit = _scalar(parent / 'memory.max')
            if limit is not None:
                used = _scalar(parent / 'memory.current')
                if used is None:
                    raise ValueError('preflight cgroup control')
                available.append(max(0, limit - used))
        result['memory_headroom_bytes'] = min(available, default=None)
        result['status'] = 'ready' if all(all(value.values()) for value in limits.values()) else 'controls-missing'
    except (OSError, ValueError):
        pass
    return result


def host_memory(proc=Path('/proc')):
    try:
        raw = _read(proc / 'meminfo')
        lines = re.findall(r'^MemAvailable:\s+([0-9]{1,18}) kB$', raw, re.MULTILINE)
        return int(lines[0]) * 1024 if len(lines) == 1 else None
    except (OSError, ValueError):
        return None


def _command(binary, args):
    try:
        result = subprocess.run((str(binary), *args), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env=ENV, timeout=5, check=False)
        if result.returncode == 0 and len(result.stdout) <= 65_536:
            return result.stdout.decode('utf-8', errors='replace')
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _trusted(binary):
    try:
        binary = Path(binary).resolve(strict=True)
        info = binary.stat()
        trusted = info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o022
        trusted = trusted and all(path.stat().st_uid == 0 and not path.stat().st_mode & 0o022
                                  for path in binary.parents)
    except OSError:
        return None
    return binary if trusted else None


def _tool(name, git):
    binary = git if name == 'git' else BWRAP if name == 'bubblewrap' else shutil.which(name, path=ENV['PATH'])
    if binary is None or not Path(binary).is_file() or not os.access(binary, os.X_OK):
        return {'status': 'missing', 'version': None}
    binary = _trusted(binary)
    if binary is None:
        return {'status': 'unreviewed-executable-path', 'version': None}
    raw = _command(binary, TOOLS[name])
    version = VERSION.search(raw) if raw else None
    if version is None:
        return {'status': 'version-unavailable', 'version': None}
    version = version.group()
    state = 'version-observed'
    if name == 'git':
        state = 'qualified-version' if version == QUALIFIED_GIT else 'version-unqualified'
    return {'status': state, 'version': version}


def bubblewrap(tool, account_ready):
    result = {'status': tool['status'], 'switches': {}, 'actual_sandbox': 'not-run'}
    if tool['status'] != 'version-observed':
        return result
    help_text = _command(BWRAP, ('--help',))
    flags = set(re.findall(r'(?m)^\s+(--[a-z-]+)\b', help_text or ''))
    result['switches'] = {flag: flag in flags for flag in BWRAP_FLAGS}
    if not all(result['switches'].values()):
        return result | {'status': 'switches-missing'}
    if not account_ready:
        return result | {'status': 'account-mismatch'}
    try:
        sandbox_ready()
    except (OSError, ValueError, GuardError, subprocess.SubprocessError):
        return result | {'status': 'sandbox-rejected', 'actual_sandbox': 'rejected'}
    return result | {'status': 'ready', 'actual_sandbox': 'verified'}


def thermal():
    try:
        sample = sample_temperatures()
    except GuardError:
        return {'status': 'unavailable', 'cpu_sensors': 0}
    try:
        validate_sample(sample, Policy(), preflight=True)
    except GuardError:
        return {'status': 'blocked', 'cpu_sensors': len(sample.cpu_sensors)}
    return {'status': 'ready', 'cpu_sensors': len(sample.cpu_sensors)}


def preflight(role, expected_uid, storage, git, minimum_memory, minimum_disk):
    nonroot = sys.platform.startswith('linux') and os.getuid() == os.geteuid() == expected_uid > 0
    group = cgroups()
    available = host_memory()
    ceiling = group['memory_headroom_bytes']
    memory = min(available, ceiling) if available is not None and ceiling is not None else available
    try:
        stat = os.statvfs(storage)
        disk = stat.f_frsize * stat.f_bavail
        storage_ready = storage.is_dir() and disk >= minimum_disk
    except OSError:
        disk, storage_ready = None, False
    tools = {name: _tool(name, git) for name in TOOLS}
    sandbox = bubblewrap(tools['bubblewrap'], nonroot)
    heat = thermal()
    resources = nonroot and group['status'] == 'ready' and memory is not None and memory >= minimum_memory and storage_ready
    tools_ready = (tools['git']['status'] == 'qualified-version'
                   and all(tools[name]['status'] == 'version-observed' for name in ('nginx', 'gunicorn')))
    return {'protocol': 'stead.pilot-host-preflight/1', 'role': role, 'expected_uid': expected_uid,
            'uid': os.geteuid(), 'target_account_verified': nonroot, 'cgroup': group,
            'memory': {'host_available_bytes': available, 'effective_available_bytes': memory, 'required_bytes': minimum_memory},
            'disk': {'available_bytes': disk, 'required_bytes': minimum_disk, 'ready': storage_ready},
            'tools': tools, 'sandbox': sandbox, 'thermal': heat,
            'live_service_dependencies_ready': resources and tools_ready and sandbox['actual_sandbox'] == 'verified',
            'local_guard_eligible': resources and heat['status'] == 'ready',
            'release_fencing_verified': False, 'native_admitted': False}


def positive(raw):
    value = int(raw)
    if not 0 < value <= 2**32 - 2:
        raise argparse.ArgumentTypeError('Use a positive integer within range.')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=('relay', 'worker'), required=True)
    parser.add_argument('--expected-uid', type=positive, required=True)
    parser.add_argument('--storage', type=Path, required=True, help='Existing directory on the service storage filesystem')
    parser.add_argument('--min-memory-mib', type=positive, required=True)
    parser.add_argument('--min-disk-mib', type=positive, required=True)
    parser.add_argument('--git', type=Path, default=Path('/usr/bin/git'))
    args = parser.parse_args(argv)
    if not args.git.is_absolute() or not args.storage.is_absolute():
        parser.error('Use absolute paths for the configured Git binary and storage.')
    result = preflight(args.role, args.expected_uid, args.storage, args.git,
                       args.min_memory_mib * MIB, args.min_disk_mib * MIB)
    sys.stdout.buffer.write(encoded(result))
    return 0 if result['live_service_dependencies_ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

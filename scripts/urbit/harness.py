#!/usr/bin/env python3
"""Local synthetic fake ships in ONE private network/filesystem/PID namespace."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time

import toolchain
import execution_policy

ROOT = toolchain.ROOT
BASE = ROOT / '.piers'
STATE = BASE / 'fakes'
SHIPS = ('zod', 'bus', 'nec', 'bud')
MARKER = '.stead-disposable.json'
IDENTITY = {'format': 1, 'purpose': 'stead-urbit-four-fakes', 'ships': list(SHIPS)}


def guard(create=False):
    # No caller-specified deletion path; reject redirects at every owned root.
    for path in (BASE, STATE):
        if path.is_symlink():
            raise ValueError(f'Refusing symlinked fixture root: {path}')
    if not STATE.exists():
        if not create:
            raise ValueError('No fixture; run make start')
        BASE.mkdir(mode=0o700, exist_ok=True)
        STATE.mkdir(mode=0o700)
        (STATE / MARKER).write_text(json.dumps(IDENTITY) + '\n')
    marker = STATE / MARKER
    if marker.is_symlink() or json.loads(marker.read_text()) != IDENTITY:
        raise ValueError('Missing or invalid disposable fixture marker')
    if STATE.resolve() != ROOT / '.piers/fakes':
        raise ValueError('Fixture escaped repository')
    if STATE.stat().st_uid != os.getuid() or STATE.stat().st_mode & 0o077:
        raise ValueError('Fixture must be owned by this user with mode 0700')
    for name in ('live', 'seed', 'logs', 'control.sock', 'lifecycle.lock', 'unclean-live.json'):
        if (STATE / name).is_symlink():
            raise ValueError(f'Refusing redirected fixture entry: {name}')
    return STATE


def rpc(op, timeout=30, **kwargs):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(timeout)
        client.connect(str(STATE / 'control.sock'))
        client.sendall(json.dumps({'op': op, **kwargs}).encode() + b'\n')
        data = b''
        while not data.endswith(b'\n'):
            block = client.recv(65536)
            if not block:
                raise RuntimeError('Harness ended without a response')
            data += block
            if len(data) > 2_000_000:
                raise RuntimeError('Oversized harness response')
    result = json.loads(data)
    if not result['ok']:
        raise RuntimeError(result['error'])
    return result['result']


def running():
    try:
        return rpc('status', timeout=2)
    except (OSError, RuntimeError):
        return None


def sandbox(command, *, execution_control=None, execution_id=None):
    # Only fixture state is writable. No home, credentials, Docker socket or LAN.
    args = ['bwrap', '--unshare-all', '--new-session', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        if path.is_symlink():
            args += ['--symlink', os.readlink(path), str(path)]
        elif path.exists():
            args += ['--ro-bind', str(path), str(path)]
    args += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/etc',
             '--ro-bind', str(ROOT / 'scripts/urbit'), '/code',
             '--ro-bind', str(ROOT / 'native'), '/native',
             '--ro-bind', str(ROOT / 'specs/urbit'), '/specs',
             '--ro-bind', str(toolchain.LOCK_PATH), '/toolchain.json',
             '--ro-bind', str(ROOT / 'specs/urbit/smoke-corpus.json'), '/corpus.json',
             '--ro-bind', str(ROOT / '.runtime/bin'), '/runtime/bin',
             '--ro-bind', str(ROOT / '.runtime/downloads'), '/runtime/downloads',
             '--ro-bind', str(ROOT / '.runtime' / toolchain.lock()['kernel']['directory']), '/kernel',
             '--bind', str(STATE), '/state', '--chdir', '/state', '--clearenv',
             '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'TERM', 'dumb',
             '--setenv', 'LANG', 'C.UTF-8']
    if execution_control is not None:
        args += ['--ro-bind', str(execution_control), '/execution',
                 '--setenv', 'STEAD_EXECUTION_ID', execution_id]
    args += ['--', *command]
    return args


def execution_limits():
    pin = execution_policy.read_json(ROOT / 'specs/urbit/urgit-candidate.lock.json')
    return execution_policy.policy_from_limits(pin['limits'])


def guarded_supervisor():
    guard()
    report = execution_policy.run_guarded(
        lambda control, run_id: sandbox(['/usr/bin/python3', '/code/supervisor.py'],
                                         execution_control=control, execution_id=run_id),
        root=ROOT, label='four-fakes', policy=execution_limits())
    if report['status'] != 'completed' and report.get('launched'):
        # A forced/disrupted live fixture is never promoted into a clean seed.
        guard()
        execution_policy.write_json(STATE / 'unclean-live.json', {
            'reason': report['reason'], 'guard_report': report['run_directory'] + '/report.json'})
    print(json.dumps({'guard_status': report['status'], 'guard_report': report['run_directory'] + '/report.json'}), flush=True)
    if report['status'] != 'completed':
        raise RuntimeError('Guarded supervisor stopped without clean completion: ' + str(report['reason']))


def doctor():
    if platform.machine() != 'x86_64' or sys.platform != 'linux':
        raise ValueError('Only the pinned Linux x86_64 profile is implemented')
    for name in ('bwrap', 'ip', 'git'):
        if not shutil.which(name):
            raise ValueError(f'Missing prerequisite: {name}')
    toolchain.verify()
    guard(create=True)
    result = subprocess.check_output(sandbox(['/usr/bin/python3', '/code/namespace_check.py']), text=True)
    print(result.strip())
    print(json.dumps({'host': platform.platform(), 'python': platform.python_version(),
                      'git': toolchain.lock()['host_tools']['git'], 'running': running()}, indent=2))


def start():
    guard(create=True)
    toolchain.verify()
    seed_manifest = STATE / 'seed/manifest.json'
    if seed_manifest.exists():
        seed = json.loads(seed_manifest.read_text())
        if seed['toolchain_sha256'] != toolchain.sha(toolchain.LOCK_PATH):
            raise ValueError('Existing fixture toolchain differs; no automatic upgrade')
    current = running()
    if current is not None:
        if not current.get('execution_guard'):
            raise RuntimeError('Loaded supervisor has no common guard; make stop before restart')
        print(json.dumps(current, indent=2))
        return
    if (STATE / 'unclean-live.json').exists():
        raise RuntimeError('Previous live fixture was interrupted; inspect evidence then make reset from verified clean seeds')
    (STATE / 'logs').mkdir(exist_ok=True)
    # The supervisor takes this lifetime lock before launching any ship. A stale
    # socket or PID file alone can never authorize another writer or deletion.
    with (STATE / 'lifecycle.lock').open('a+') as gate:
        try:
            fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Supervisor owns fixture; inspect logs, do not duplicate')
        fcntl.flock(gate, fcntl.LOCK_UN)
    with (STATE / 'logs/supervisor.log').open('ab') as output:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_guarded-supervisor'],
                                   stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                   start_new_session=True)
    for _ in range(100):
        current = running()
        if current is not None:
            print(json.dumps(current, indent=2))
            return
        if process.poll() is not None:
            raise RuntimeError('Supervisor failed; inspect .piers/fakes/logs/supervisor.log')
        time.sleep(.1)
    raise RuntimeError('Supervisor did not open control socket')


def stop():
    guard()
    if running() is not None:
        print(json.dumps(rpc('stop', timeout=180), indent=2))
    with (STATE / 'lifecycle.lock').open('a+') as gate:
        # Kernel-held lock, not a PID that might have been reused.
        deadline = time.monotonic() + 10
        while True:
            try:
                fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise RuntimeError('Supervisor still owns the fixture')
                time.sleep(.1)
    print('STOPPED: fixture lifetime lock released')


def reset():
    guard()
    if running() is not None:
        raise ValueError('Refusing reset while supervisor is running; make stop first')
    with (STATE / 'lifecycle.lock').open('a+') as gate:
        fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard()
        live, seed = STATE / 'live', STATE / 'seed'
        if not (seed / 'manifest.json').is_file():
            raise ValueError('No stopped clean seed; complete the initial boot first')
        manifest = json.loads((seed / 'manifest.json').read_text())
        if manifest['toolchain_sha256'] != toolchain.sha(toolchain.LOCK_PATH):
            raise ValueError('Seed uses a different toolchain; no automatic destructive upgrade')
        for ship in SHIPS:
            pier = seed / ship
            if pier.is_symlink() or not (pier / '.urb').is_dir():
                raise ValueError('Invalid fake seed')
            if toolchain.tree_sha(pier) != manifest['ships'][ship]:
                raise ValueError(f'Seed integrity failure: {ship}')
        if live.exists():
            shutil.rmtree(live)
        live.mkdir()
        for ship in SHIPS:
            shutil.copytree(seed / ship, live / ship, symlinks=True)
        (STATE / 'unclean-live.json').unlink(missing_ok=True)
    print('RESET: restored four stopped, hash-verified synthetic seeds')


def test():
    guard()
    result = rpc('test', timeout=3600)
    print(json.dumps(result, indent=2))
    if result['status'] != 'pass':
        raise RuntimeError('Native smoke failed; retain evidence and fix before claiming success')


def core_test():
    guard()
    result = rpc('core-test', timeout=3600)
    print(json.dumps(result, indent=2))
    if result['status'] != 'pass':
        raise RuntimeError('Native core acceptance failed; retained evidence is not a pass')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['doctor', 'start', 'stop', 'reset', 'status', 'test', 'core-test', '_guarded-supervisor'])
    args = parser.parse_args()
    try:
        if args.command == 'status':
            guard()
            print(json.dumps(rpc('status'), indent=2))
        elif args.command == '_guarded-supervisor':
            guarded_supervisor()
        else:
            globals()[args.command.replace('-', '_')]()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'FAIL: {error}\n')

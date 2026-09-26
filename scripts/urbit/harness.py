#!/usr/bin/env python3
"""Local synthetic fake ships in ONE private network/filesystem/PID namespace."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time

import toolchain
import execution_policy
from digests import source_sha, tree_sha, source_inventory, read_source

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


def status():
    """Read lifecycle state without creating a fixture or assuming a free lock."""
    if not STATE.exists() and not STATE.is_symlink() and not BASE.is_symlink():
        result = {'stage': 'not-created', 'ready': False, 'ships': {}}
    else:
        guard()
        try:
            result = rpc('status', timeout=2)
        except (FileNotFoundError, ConnectionRefusedError):
            result = {'stage': 'stopped', 'ready': False, 'ships': {}}
            try:
                with (STATE / 'lifecycle.lock').open('rb') as gate:
                    fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(gate, fcntl.LOCK_UN)
            except FileNotFoundError:
                pass
            except BlockingIOError:
                result['stage'] = 'unresponsive-owner'
    print(json.dumps(result, indent=2))
    return result


def wait_ready(timeout=1200):
    """Wait for the existing guarded supervisor; never retry a failed start."""
    guard()
    deadline = time.monotonic() + timeout
    previous = None
    while time.monotonic() < deadline:
        current = rpc('status', timeout=5)
        stage = current.get('stage')
        if stage != previous:
            print(json.dumps({'stage': stage, 'ready': current.get('ready')}), flush=True)
            previous = stage
        if current.get('ready') is True:
            if current.get('execution_guard', {}).get('state') != 'running':
                raise RuntimeError('Ready fixture has no running execution guard')
            return current
        if stage in ('failed', 'stopped', 'stopping', 'guard-stopped'):
            raise RuntimeError('Fixture cannot become ready: ' + str(current))
        time.sleep(1)
    raise RuntimeError('Readiness timed out; inspect logs and make stop')


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
             '--ro-bind', str(ROOT / 'tests/urbit/native_gall_schedule'), '/native-tests/gall-schedule',
             '--ro-bind', str(ROOT / 'tests/urbit/skill_evaluation'), '/native-tests/skill-evaluation',
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
    workflow = ROOT / '.runtime/workflow-evaluation'
    if workflow.exists():
        if workflow.is_symlink() or workflow.stat().st_uid != os.getuid() or workflow.stat().st_mode & 0o077:
            raise ValueError('Workflow input root must be owned and private')
        args += ['--ro-bind', str(workflow), '/workflow']
    args += ['--', *command]
    return args


def execution_limits():
    pin = execution_policy.read_json(ROOT / 'specs/urbit/urgit-candidate.lock.json')
    return execution_policy.policy_from_limits(pin['limits'])


def preflight():
    """Read current admission conditions without launching a process or fixture."""
    policy = execution_limits()
    sample = execution_policy.sample_temperatures()
    result = {'classification': 'real-host-thermal-sample',
              'readings_c': sample.readings_c, 'start_limit_c': policy.start_c,
              'stop_limit_c': policy.stop_c, 'admitted': False}
    try:
        execution_policy.validate_sample(sample, policy, preflight=True)
        result['admitted'] = True
    except execution_policy.GuardError as error:
        result['reason'] = str(error)
        raise
    finally:
        print(json.dumps(result, indent=2), flush=True)
    return result


def guarded_supervisor():
    guard()
    def command(control, run_id):
        paths = ['scripts/urbit', 'native', 'specs/urbit',
                 'tests/urbit/native_gall_schedule', 'tests/urbit/skill_evaluation']
        scripts = source_inventory(ROOT / 'scripts/urbit')
        context = {
            'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'dirty_paths': subprocess.check_output(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, text=True).splitlines(),
            'harness_sha256': source_sha(ROOT / 'scripts/urbit'),
            'native_tree_sha256': tree_sha(ROOT / 'native/core/desk'), 'script_files': scripts}
        context['trees'] = {path: tree_sha(ROOT / path) for path in paths if path != 'scripts/urbit'}
        context['committed_files'] = {}
        context['committed_bytes_verified'] = not context['dirty_paths']
        listing = subprocess.check_output(['git', 'ls-tree', '-r', '-z', context['source_commit'], '--', *paths], cwd=ROOT)
        for entry in listing.split(b'\0'):
            if not entry:
                continue
            metadata, raw_path = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            path = raw_path.decode()
            source = ROOT / path
            if kind != 'blob' or mode not in ('100644', '100755') or source.is_symlink():
                raise ValueError('Unsupported redirected qualification source')
            raw = read_source(source)
            actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            context['committed_bytes_verified'] &= actual == oid
            context['committed_files'][path] = hashlib.sha256(raw).hexdigest()
        committed_scripts = {name.removeprefix('scripts/urbit/'): value for name, value in context['committed_files'].items()
                             if name.startswith('scripts/urbit/')}
        context['committed_bytes_verified'] &= committed_scripts == scripts
        for prefix in paths[1:]:
            actual_files = source_inventory(ROOT / prefix, ignore_python_cache=False)
            committed_files = {name[len(prefix) + 1:]: value for name, value in context['committed_files'].items()
                               if name.startswith(prefix + '/')}
            context['committed_bytes_verified'] &= actual_files == committed_files
        if source_inventory(ROOT / 'scripts/urbit') != scripts:
            raise ValueError('Helper source inventory changed during capture')
        if (subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != context['source_commit']
                or subprocess.check_output(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, text=True).splitlines() != context['dirty_paths']):
            raise ValueError('Source checkout changed during provenance capture')
        execution_policy.write_json(control / 'source-context.json', context)
        return sandbox(['/usr/bin/python3', '-X', 'pycache_prefix=/tmp/python-cache', '/code/supervisor.py'],
                       execution_control=control, execution_id=run_id)
    report = execution_policy.run_guarded(
        command,
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
        try:
            print(json.dumps(rpc('stop', timeout=180), indent=2))
        except (FileNotFoundError, ConnectionRefusedError):
            # Workflow runs stop their own supervisor. If its socket vanishes
            # between status and stop, only the lifetime lock below can prove
            # cleanup completed; disappearance alone is never success.
            pass
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
    if result['status'] not in ('pass', 'execution_complete'):
        raise RuntimeError('Native core acceptance failed; retained evidence is not a pass')
    if result['status'] == 'execution_complete':
        print('Native execution completed; independent phase qualification remains required.')


def core_check():
    guard()
    result = rpc('core-check', timeout=1800)
    print(json.dumps(result, indent=2))
    if result['status'] != 'pass':
        raise RuntimeError('Native compilation/probes failed; inspect the recorded evidence')


def gall_schedule():
    guard()
    result = rpc('gall-schedule', timeout=1800)
    print(json.dumps(result, indent=2))
    if result['status'] != 'pass':
        raise RuntimeError('Scheduled Gall native lane failed; inspect retained evidence')


def skill_evaluation(condition):
    guard()
    result = rpc('skill-evaluation', condition=condition, timeout=3600)
    print(json.dumps(result, indent=2))
    if result['status'] != 'pass':
        raise RuntimeError('Workflow native evaluation failed; inspect retained evidence')


def skill_feedback(condition, task, attempt):
    if (condition not in ('baseline', 'local_skill_assisted')
            or task not in ('T01', 'T02', 'T03', 'T04', 'T05', 'T06')
            or type(attempt) is not int or attempt not in (1, 2, 3)):
        raise ValueError('Public feedback requires candidate condition, task and attempt 1 through 3')
    guard()
    result = rpc('skill-feedback', condition=condition, task=task, attempt=attempt, timeout=3600)
    print(json.dumps(result, indent=2))
    if result['status'] != 'pass':
        raise RuntimeError('Public task feedback failed; retain its public and private execution records')


def dev():
    def interrupted(*_):
        raise KeyboardInterrupt('Developer command interrupted')

    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        start()
        wait_ready()
        core_check()
    except BaseException:
        # An interrupted developer operation must not leave a heavy run behind.
        try:
            if STATE.exists():
                stop()
        except (OSError, ValueError, RuntimeError) as cleanup_error:
            print('Cleanup failed; inspect make status: ' + str(cleanup_error), file=sys.stderr)
        raise
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['doctor', 'preflight', 'start', 'stop', 'reset', 'status',
                        'wait-ready', 'dev', 'test', 'core-check', 'core-test', 'gall-schedule',
                        'skill-evaluation', 'skill-feedback', '_guarded-supervisor'])
    parser.add_argument('--condition', choices=['prequalification', 'baseline', 'local_skill_assisted'])
    parser.add_argument('--task', choices=['T01', 'T02', 'T03', 'T04', 'T05', 'T06'])
    parser.add_argument('--attempt', type=int, choices=[1, 2, 3])
    args = parser.parse_args()
    try:
        if args.command == '_guarded-supervisor':
            guarded_supervisor()
        elif args.command == 'skill-evaluation':
            if args.condition is None or args.task is not None or args.attempt is not None:
                raise ValueError('Explicit workflow evaluation condition required')
            skill_evaluation(args.condition)
        elif args.command == 'skill-feedback':
            skill_feedback(args.condition, args.task, args.attempt)
        else:
            globals()[args.command.replace('-', '_')]()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'FAIL: {error}\n')

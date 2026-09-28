#!/usr/bin/env python3
"""Reviewed manual GitHub-hosted profile. Never an alternate local thermal mode."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import select
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types

ROOT = Path(__file__).resolve().parents[2]
CAPTURED = None
CONTROLLER_FILES = None
AUTH_ENVIRONMENT = None
CONTROL_CASES = ('missing-profile', 'wrong-profile', 'parent-death', 'guardian-death', 'changed-limits', 'stale-lease')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bootstrap():
    """Load only fresh, captured Git source; never working-tree pyc or locks."""
    global CAPTURED, CONTROLLER_FILES, AUTH_ENVIRONMENT
    global execution_policy, hosted_identity, hosted_lease, hosted_apparmor, local, canonical, verify, POLICY
    require(os.getuid() == 0 and sys.flags.isolated and sys.dont_write_bytecode, 'Root isolated controller required')
    regular_root(ROOT)
    AUTH_ENVIRONMENT = {key: os.environ.get(key, '') for key in (
        'ACTIONS_ID_TOKEN_REQUEST_URL', 'ACTIONS_ID_TOKEN_REQUEST_TOKEN')}
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', LANG='C.UTF-8', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    git_env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
        GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1')
    def read_git(*arguments):
        command = ['/usr/bin/git', '-C', str(ROOT), *arguments]
        with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, env=git_env) as process:
            raw = bytearray()
            deadline = time.monotonic() + 15
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while True:
                        require(time.monotonic() < deadline, 'Bootstrap Git deadline')
                        if not selector.select(.05):
                            continue
                        chunk = os.read(process.stdout.fileno(), min(65536, 4 * 1024**2 + 1 - len(raw)))
                        if not chunk:
                            break
                        raw.extend(chunk)
                        require(len(raw) <= 4 * 1024**2, 'Bootstrap Git byte bound')
                require(process.wait(timeout=1) == 0, 'Bootstrap Git read failed')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=2)
            return bytes(raw)
    commit = read_git('rev-parse', 'HEAD').decode().strip()
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'Bootstrap commit identity')
    # This entry is invoked only by the reviewed workflow's root-owned fresh
    # checkout. Bind its own bytes, then compile the committed local reader
    # directly, bypassing all working-tree helpers and bytecode caches.
    require(read_git('show', commit + ':scripts/ci/hosted.py') == Path(__file__).read_bytes(), 'Hosted entry differs from Git')
    reader = types.ModuleType('stead_committed_ci_reader')
    reader.__file__ = str(ROOT / 'scripts/ci/local.py')
    exec(compile(read_git('show', commit + ':scripts/ci/local.py'), reader.__file__, 'exec'), reader.__dict__)
    CONTROLLER_FILES = reader.inventory(commit, reader.CONTROLLER_PATHS)
    # These directories are fresh and never contain pre-existing .pyc files.
    CAPTURED = Path(tempfile.mkdtemp(prefix='stead-controller-', dir='/var/lib')) / 'source'
    reader.materialize(CONTROLLER_FILES, CAPTURED)
    sys.path[:0] = [str(CAPTURED / 'scripts/ci'), str(CAPTURED / 'scripts/urbit')]
    import execution_policy as execution_module
    import hosted_identity as identity_module
    import hosted_lease as lease_module
    import hosted_apparmor as apparmor_module
    import local as local_module
    from worker_result import canonical as canonical_function, verify as verify_function
    execution_policy, hosted_identity, hosted_lease = execution_module, identity_module, lease_module
    hosted_apparmor = apparmor_module
    local, canonical, verify = local_module, canonical_function, verify_function
    local.ROOT = ROOT  # Git is data in the original root-owned checkout.
    POLICY = hosted_lease.POLICY


def write(path, value, *, shared=False, gid=None):
    path = Path(path)
    if not shared:
        execution_policy.write_json(path, value)
        return
    # Publish a fully readable replacement once. chmod after replace creates a
    # heartbeat race in which the worker sees a root-only lease and must stop.
    with execution_policy.directory_fd(path.parent) as parent:
        name = '.' + path.name + '.' + secrets.token_hex(12)
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600, dir_fd=parent)
        try:
            os.fchown(descriptor, 0, gid)
            os.fchmod(descriptor, 0o640)
            with os.fdopen(descriptor, 'wb') as output:
                descriptor = None
                output.write(canonical(value) + b'\n')
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(name, dir_fd=parent)
            except FileNotFoundError:
                pass


def regular_root(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'Unsafe root path')
    for item in (path, *path.parents):
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and info.st_uid == 0
                and not info.st_mode & 0o022, 'Hosted input is not root controlled')


def share_tree(root, gid):
    # Only authenticated pins and captured public Git blobs enter these trees.
    for folder, directories, files in os.walk(root, followlinks=False):
        os.chown(folder, 0, gid)
        os.chmod(folder, 0o750)
        for name in [*directories, *files]:
            path = Path(folder) / name
            if path.is_symlink():
                continue  # Reviewed kernel archive links remain inside its RO mount.
            os.chown(path, 0, gid)
            if path.is_file():
                os.chmod(path, 0o550 if path.stat().st_mode & 0o111 else 0o440)


def readback(unit):
    result = subprocess.run(['/usr/bin/systemctl', 'show', unit,
        '--property=LoadState,ActiveState,ControlGroup,MainPID,Result,KillMode,ExitType,RemainAfterExit,Restart,OOMPolicy,RuntimeMaxUSec,TimeoutStopUSec,Delegate,AppArmorProfile,ExecMainCode,ExecMainStatus'],
        capture_output=True, text=True, timeout=3)
    require(result.returncode == 0, 'Hosted unit readback failed')
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def cpu_set(raw):
    result = set()
    for item in raw.strip().split(','):
        require(re.fullmatch(r'[0-9]+(?:-[0-9]+)?', item), 'Invalid CPU set')
        bounds = [int(value) for value in item.split('-')]
        require(len(bounds) == 1 or bounds[0] <= bounds[1] < 4096, 'CPU range bound')
        result.update(range(bounds[0], bounds[-1] + 1))
    return sorted(result)


def observe(job, context):
    apparmor = hosted_apparmor.observe()
    hosted_apparmor.require_label()
    unit = context['unit']
    expected = '/system.slice/' + unit
    require(Path('/proc/self/cgroup').read_text().splitlines() == ['0::' + expected], 'Guardian cgroup differs')
    cg = Path('/sys/fs/cgroup') / expected.lstrip('/')
    service = readback(unit)
    require(service.get('ActiveState') == 'active' and service.get('MainPID') == str(os.getpid())
            and service.get('ControlGroup') == expected, 'Guardian service identity differs')
    expected_service = {'KillMode': 'control-group', 'ExitType': 'main', 'RemainAfterExit': 'no',
        'Restart': 'no', 'OOMPolicy': 'kill', 'RuntimeMaxUSec': '2h', 'TimeoutStopUSec': '15s', 'Delegate': 'no',
        'AppArmorProfile': hosted_apparmor.PROFILE}
    require(all(service.get(key) == value for key, value in expected_service.items()), 'Guardian service policy differs')
    require((cg / 'memory.oom.group').read_text().strip() == '1', 'Whole-cgroup OOM policy absent')
    limits = {key: (cg / key).read_text().strip() for key in ('cpu.max', 'memory.max', 'memory.swap.max', 'pids.max')}
    require(limits == {'cpu.max': POLICY['cpu_max'], 'memory.max': str(POLICY['memory_max']),
        'memory.swap.max': '0', 'pids.max': '256'}, 'Hosted kernel limits changed')
    require(cpu_set((cg / 'cpuset.cpus.effective').read_text()) == context['cpus'], 'Hosted CPU set changed')
    pids = [int(value) for value in (cg / 'cgroup.procs').read_text().splitlines()]
    require(os.getpid() in pids and len(pids) <= 256, 'Guardian membership differs')
    for pid in pids:
        try:
            require(sorted(os.sched_getaffinity(pid)) == context['cpus'], 'Owned process affinity changed')
        except ProcessLookupError:
            continue
    counters = lambda name: dict(line.split() for line in (cg / name).read_text().splitlines())
    memory, tasks = counters('memory.events'), counters('pids.events')
    events = {'oom': int(memory['oom']), 'oom_kill': int(memory['oom_kill']), 'pids_max': int(tasks['max'])}
    require(events == {'oom': 0, 'oom_kill': 0, 'pids_max': 0}, 'Hosted resource event')
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == context['guard_sha256'], 'Guardian source changed')
    return {'unit': unit, 'cgroup': expected, 'limits': limits, 'resource_events': events, 'cpus': context['cpus'],
        'apparmor': apparmor,
        'service': {**expected_service, 'MainPID': str(os.getpid()), 'memory.oom.group': '1'}}


def sandbox_command(job, context):
    base, pins = job / 'controller', context['pins']
    command = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--uid', '0', '--gid', '0',
        '--cap-add', 'CAP_NET_ADMIN', '--cap-add', 'CAP_SETPCAP', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        command += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
    command += ['--proc', '/proc', '--dev', '/dev', '--dir', '/etc', '--size', str(local.TEMP_BYTES),
        '--tmpfs', '/tmp', '--size', str(local.STATE_BYTES), '--tmpfs', '/state']
    for source, target in [
        (base / 'scripts/urbit', '/code'), (base / 'scripts/ci', '/ci'), (base / 'web/dev', '/web-dev'),
        (base / 'specs/urbit', '/specs'), (job / 'composed/native', '/native'),
        (base / 'specs/urbit/toolchain.lock.json', '/toolchain.json'),
        (ROOT / '.runtime' / pins['runtime']['binary'], '/runtime/' + pins['runtime']['binary']),
        (ROOT / '.runtime/downloads' / pins['boot_artifact']['archive'], '/runtime/downloads/' + pins['boot_artifact']['archive']),
        (ROOT / '.runtime' / pins['kernel']['directory'], '/kernel'),
        (job / 'inputs.json', '/ci-inputs.json'), (job / 'control', '/execution')]:
        command += ['--ro-bind', str(source), target]
    entry = ['/ci/hosted_control.py'] if context.get('control_case') else ['/ci/worker.py', '--hosted']
    command += ['--chdir', '/state', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
        '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'TERM', 'dumb',
        '--setenv', 'STEAD_EXECUTION_ID', context['run_id'], '--', '/usr/bin/python3', '-B', *entry]
    return command


def child(job, parent):
    regular_root(job / 'context.json')
    context = execution_policy.read_json(job / 'context.json', maximum=1024 * 1024)
    require(os.getuid() == 0 and os.getppid() == parent, 'Worker launcher parent differs')
    os.setgroups([])
    os.setgid(context['gid'])
    os.setuid(context['uid'])
    # Changing UID clears PDEATHSIG; arm it afterwards and recheck the parent.
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(1, signal.SIGKILL, 0, 0, 0) == 0 and os.getppid() == parent, 'Worker parent lifetime unavailable')
    require(libc.prctl(38, 1, 0, 0, 0) == 0, 'Worker no-new-privileges unavailable')
    hosted_apparmor.require_label()
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', LANG='C.UTF-8')
    command = sandbox_command(job, context)
    os.execv(command[0], command)


def guardian(job):
    require(os.getuid() == 0 and stat.S_ISFIFO(os.fstat(0).st_mode), 'Root guardian requires its private lifetime pipe')
    regular_root(job / 'context.json')
    context = execution_policy.read_json(job / 'context.json', maximum=1024 * 1024)
    control = job / 'control'
    stopped = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopped.set())
    started, generation = time.monotonic(), 0
    process, reader = None, None
    collection = {'overflow': False, 'error': None, 'eof': False, 'completed': False}
    result = {'status': 'fail', 'run_id': context['run_id'], 'classification': 'github-hosted-native-guard',
        'thermal': POLICY['thermal'], 'policy': POLICY, 'collector': collection}

    def heartbeat():
        nonlocal generation
        require(not stopped.is_set(), 'Hosted cancellation')
        readable, _, _ = select.select([0], [], [], 0)
        if readable:
            require(os.read(0, 1) != b'', 'Hosted caller ended')
            raise ValueError('Unexpected lifetime pipe data')
        evidence = observe(job, context)
        now = time.monotonic()
        require(now - started < 7200, 'Hosted deadline')
        generation += 1
        lease = {**evidence, 'format': 'stead.hosted-lease/1', 'state': 'running',
            'run_id': context['run_id'], 'generation': generation, 'started': started,
            'observed_at': now, 'deadline': started + 7200, 'policy': POLICY,
            'policy_sha256': hashlib.sha256(json.dumps(POLICY, sort_keys=True).encode()).hexdigest(),
            'guard_sha256': context['guard_sha256'], 'authenticated_host': True}
        write(control / 'lease.json', lease, shared=True, gid=context['gid'])
        return lease

    try:
        lease = heartbeat()
        admission = {key: lease[key] for key in ('run_id', 'unit', 'cgroup', 'limits', 'cpus')}
        admission.update(status='admitted', profile=POLICY['profile'], authenticated_host=True)
        write(control / 'ci-admission.json', admission, shared=True, gid=context['gid'])
        result['admission'] = admission
        process = subprocess.Popen(['/usr/bin/python3', '-I', '-B', str(Path(__file__)), '_child',
            str(job), str(os.getpid())], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, start_new_session=True, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})

        def collect():
            try:
                total = 0
                with (job / 'console.private.log').open('xb') as output:
                    while raw := process.stdout.read1(65536):
                        total += len(raw)
                        if total <= local.MAX_TREE:
                            output.write(raw)
                            output.flush()
                        else:
                            collection['overflow'] = True
                            stopped.set()
                    collection['eof'] = True
            except BaseException as error:
                collection['error'] = type(error).__name__
                stopped.set()
            finally:
                try:
                    process.stdout.close()
                except BaseException as error:
                    collection['error'] = type(error).__name__
                    stopped.set()
                finally:
                    collection['completed'] = True
        reader = threading.Thread(target=collect, daemon=True)
        reader.start()
        while process.poll() is None:
            heartbeat()
            stopped.wait(.5)
        heartbeat()
        require(process.returncode == 0, 'Native worker process failed')
        result['status'] = 'pass'
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)[:1000]
    finally:
        cleanup_errors = []
        try:
            write(control / 'STOP', {'stopped': True}, shared=True, gid=context['gid'])
        except BaseException as error:
            cleanup_errors.append('Stop receipt: ' + type(error).__name__)
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        except BaseException as error:
            cleanup_errors.append('Child termination: ' + type(error).__name__)
        if reader:
            try:
                reader.join(timeout=5)
            except RuntimeError as error:
                cleanup_errors.append('Collector join: ' + type(error).__name__)
            if reader.is_alive() or not collection['completed'] or not collection['eof']:
                cleanup_errors.append('Output collector did not finish with EOF')
        if process is not None and (reader is None or reader.ident is None):
            try:
                process.stdout.close()
            except BaseException as error:
                cleanup_errors.append('Unstarted collector pipe close: ' + type(error).__name__)
        if collection['overflow'] or collection['error']:
            cleanup_errors.append('Output collection failed')
        if cleanup_errors:
            result['status'] = 'fail'
            # Preserve the refusal that triggered shutdown. Cleanup remains an
            # independent gate; an expected refusal cannot hide incomplete EOF.
            result.setdefault('error', 'Hosted cleanup failed')
        result.update(cleanup_errors=cleanup_errors,
            child_terminated=process is not None and process.returncode is not None,
            elapsed_seconds=round(time.monotonic() - started, 3), generations=generation,
            exit_code=process.returncode if process else None)
        write(job / 'guard.json', result)
    return 0 if result['status'] == 'pass' else 1


def require_collected_child(guard):
    require(guard.get('collector') == {'overflow': False, 'error': None, 'eof': True, 'completed': True}
        and guard.get('cleanup_errors') == [] and guard.get('child_terminated') is True
        and type(guard.get('exit_code')) is int, 'Incomplete hosted child cleanup')


def service_command(job, context):
    cpus, unit = context['cpus'], context['unit']
    require(re.fullmatch(r'stead-hosted-[0-9a-f]{32}\.service', unit), 'Unowned service name')
    profile = hosted_apparmor.PROFILE
    if context.get('control_case') == 'missing-profile':
        profile += '-missing'
    elif context.get('control_case') == 'wrong-profile':
        profile = 'unconfined'
    properties = {'CPUQuota': '200%', 'CPUQuotaPeriodSec': '10ms', 'CPUAffinity': ' '.join(map(str, cpus)),
        'AllowedCPUs': ' '.join(map(str, cpus)), 'MemoryMax': str(local.MEMORY), 'MemorySwapMax': '0',
        'TasksMax': str(local.TASKS), 'RuntimeMaxSec': '7200', 'TimeoutStopSec': '15',
        'KillMode': 'control-group', 'ExitType': 'main', 'RemainAfterExit': 'no', 'Restart': 'no', 'OOMPolicy': 'kill',
        'AppArmorProfile': profile}
    command = ['/usr/bin/systemd-run', '--quiet', '--wait', '--pipe', '--service-type=exec', '--unit=' + unit]
    command += ['--property=' + key + '=' + value for key, value in properties.items()]
    return [*command, '/usr/bin/python3', '-I', '-B', str(Path(__file__)), '_guardian', str(job)]


def launcher(job, parent):
    """A real disposable caller for the parent-SIGKILL control."""
    require(os.getuid() == 0 and os.getppid() == parent, 'Control launcher parent differs')
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(1, signal.SIGKILL, 0, 0, 0) == 0 and os.getppid() == parent, 'Control launcher lifetime differs')
    regular_root(job / 'context.json')
    context = execution_policy.read_json(job / 'context.json', maximum=1024 * 1024)
    require(context.get('control_case') == 'parent-death', 'Launcher is only a parent-death control')
    process = spawn_owned(service_command(job, context), diagnostics=job / 'service-stderr.private.log')
    try:
        return process.wait(timeout=90)
    finally:
        process.stdin.close()


def spawn_owned(command, *, diagnostics=None):
    parent = os.getpid()
    def arm():
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent:
            os._exit(126)
    # These callers have no active threads. A killed caller also kills its
    # systemd-run client, while pipe EOF stops the separately owned service.
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE if diagnostics else subprocess.DEVNULL,
        preexec_fn=arm, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    if diagnostics:
        # This stream contains only the credential-free trusted service/launcher
        # diagnostics. Candidate stdout/stderr has its separate private bound.
        process.stead_diagnostics = {'overflow': False, 'error': None}
        def collect():
            try:
                total = 0
                with diagnostics.open('xb') as output:
                    while raw := process.stderr.read1(4096):
                        remaining = max(0, 8192 - total)
                        output.write(raw[:remaining])
                        output.flush()
                        total += len(raw)
                        if total > 8192:
                            process.stead_diagnostics['overflow'] = True
                            process.terminate()
                            break
            except BaseException as error:
                process.stead_diagnostics['error'] = type(error).__name__
                if process.poll() is None:
                    process.terminate()
            finally:
                process.stderr.close()
        thread = threading.Thread(target=collect, daemon=True)
        process.stead_diagnostic_thread = thread
        try:
            thread.start()
        except BaseException:
            process.stdin.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            process.stderr.close()
            raise
    return process


def control_frame(job, prefix, run_id):
    path = job / 'console.private.log'
    if not path.exists():
        return None
    with path.open('rb') as stream:
        raw = stream.read(8193)
    require(len(raw) <= 8192, 'Control output bound')
    found = [line[len(prefix):] for line in raw.decode('utf-8').split('\n')[:-1] if line.startswith(prefix)]
    require(len(found) <= 1, 'Duplicate control frame')
    if not found:
        return None
    value = json.loads(found[0])
    require(value.get('run_id') == run_id, 'Control belongs to another run')
    return value


def control_diagnostic(job, case):
    """Only the fixed pre-native control can publish its bounded console.

    This entry runs no candidate code, Hoon, identity login or credential
    exchange. Native worker consoles must never enter this diagnostic path.
    """
    if case is None:
        return None
    require(case in CONTROL_CASES,
        'Unknown diagnostic control')
    try:
        descriptor = os.open(job / 'console.private.log', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return {'absent': True}
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Invalid control diagnostic file')
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            raw = source.read(8193)
    finally:
        os.close(descriptor)
    return {'classification': 'pre-native-control-only', 'bytes_total': info.st_size,
        'truncated': len(raw) > 8192, 'text': raw[:8192].decode('utf-8', errors='replace')}


def capture_control_diagnostic(job, case):
    try:
        return control_diagnostic(job, case)
    except Exception as error:
        # A diagnostic error must not prevent the failed primary result and
        # independently observed cleanup from being published.
        return {'capture_error': type(error).__name__}


def execute_control(case, process, job, context):
    started = time.monotonic()
    if case in ('missing-profile', 'wrong-profile'):
        require(process.wait(timeout=15) != 0, 'Invalid AppArmor admission falsely succeeded')
        state = readback(context['unit'])
        require(state.get('ActiveState') == 'failed', 'Invalid-profile service did not fail')
        require(not (job / 'control/ci-admission.json').exists(), 'Invalid profile reached worker admission')
        if case == 'missing-profile':
            require(state.get('AppArmorProfile') == hosted_apparmor.PROFILE + '-missing'
                and state.get('ExecMainCode') == '1' and state.get('ExecMainStatus') == '231',
                'Missing profile did not fail in systemd AppArmor setup')
        else:
            guard = execution_policy.read_json(job / 'guard.json')
            require(state.get('AppArmorProfile') == 'unconfined'
                and guard.get('error') == 'ValueError: AppArmor task label differs'
                and guard.get('exit_code') is None, 'Wrong profile did not fail before worker launch')
        return {'case': case, 'status': 'pass', 'native_execution': False, 'admitted': False,
            'after': state, 'elapsed_seconds': round(time.monotonic() - started, 3)}
    deadline = time.monotonic() + 40
    ready = None
    while ready is None:
        require(process.poll() is None and time.monotonic() < deadline, 'Control failed before admission')
        ready = control_frame(job, 'STEAD_HOSTED_CONTROL_READY ', context['run_id'])
        time.sleep(.1)
    require(ready['detached_descendant'] is True and ready.get('peer_fence_verified') is True and ready['isolation'] == {
        'private_network': True, 'host_credentials_absent': True, 'fresh_state': True,
        'external_route_absent': True}, 'Control isolation incomplete')
    unit = context['unit']
    before = readback(unit)
    require(before.get('ActiveState') == 'active' and int(before.get('MainPID', '0')) > 1
            and before.get('ControlGroup') == '/system.slice/' + unit, 'Control target ownership differs')
    injected = {'case': case, 'at_monotonic': time.monotonic()}
    refusal = None
    if case == 'parent-death':
        injected.update(signal='SIGKILL', owned_caller_pid=process.pid)
        process.kill()
    elif case == 'guardian-death':
        injected.update(signal='SIGKILL', kill_whom='main', unit=unit, observed_main_pid=before['MainPID'])
        subprocess.run(['/usr/bin/systemctl', 'kill', '--kill-whom=main', '--signal=SIGKILL', unit],
            check=True, capture_output=True, timeout=3)
    elif case == 'changed-limits':
        injected.update(unit=unit, property='CPUQuota', value='150%')
        subprocess.run(['/usr/bin/systemctl', 'set-property', '--runtime', unit, 'CPUQuota=150%'],
            check=True, capture_output=True, timeout=3)
    elif case == 'stale-lease':
        injected.update(unit=unit, signal='SIGSTOP', kill_whom='main', stopped_seconds=5,
            resumed_with='SIGCONT', observed_main_pid=before['MainPID'])
        subprocess.run(['/usr/bin/systemctl', 'kill', '--kill-whom=main', '--signal=SIGSTOP', unit],
            check=True, capture_output=True, timeout=3)
        try:
            # SIGSTOP also pauses the guardian's collector thread. Let the
            # worker expire its lease, then resume collection before reading
            # the preserved refusal frame from the pipe.
            time.sleep(5)
        finally:
            subprocess.run(['/usr/bin/systemctl', 'kill', '--kill-whom=main', '--signal=SIGCONT', unit],
                check=True, capture_output=True, timeout=3)
        limit = time.monotonic() + 8
        refusal = None
        while refusal is None:
            require(time.monotonic() < limit, 'Worker did not refuse the stale lease')
            refusal = control_frame(job, 'STEAD_HOSTED_CONTROL_REFUSED ', context['run_id'])
            time.sleep(.1)
        require(refusal['reason'] == 'Hosted lease stale, future, reversed or expired', 'Wrong stale-lease refusal')
    else:
        raise ValueError('Unknown resource control')
    injected['command_completed'] = True
    deadline = time.monotonic() + 25
    while True:
        state = readback(unit)
        group = Path('/sys/fs/cgroup/system.slice') / unit
        empty = not group.exists() or 'populated 0' in (group / 'cgroup.events').read_text().splitlines()
        if state.get('ActiveState') in ('inactive', 'failed') and empty and process.poll() is not None:
            break
        require(time.monotonic() < deadline, 'Control did not clean up all owned descendants')
        time.sleep(.1)
    require(process.returncode != 0, 'Interrupted control falsely exited successfully')
    if case != 'guardian-death':
        # A killed guardian cannot publish a final receipt; that separate case
        # relies on the independent service/cgroup observations above.
        require_collected_child(execution_policy.read_json(job / 'guard.json'))
    if case in ('parent-death', 'changed-limits'):
        guard = execution_policy.read_json(job / 'guard.json')
        expected = 'ValueError: ' + ('Hosted caller ended' if case == 'parent-death' else 'Hosted kernel limits changed')
        require(guard.get('status') == 'fail' and guard.get('error') == expected, 'Wrong control refusal')
    return {'case': case, 'status': 'pass', 'native_execution': False, 'admitted': True,
        'detached_descendant_observed': True, 'unit_inactive': True, 'cgroup_empty': True,
        'caller_exit': process.returncode, 'ready': ready, 'before': before, 'injected': injected,
        'after': state, 'refusal': refusal, 'elapsed_seconds': round(time.monotonic() - started, 3)}


def workflow_binding(workflow_sha, controller_sha):
    manifest_path = 'specs/urbit/hosted-ci-controller.json'
    workflow_path = '.github/workflows/native-hosted.yml'
    files = local.inventory(workflow_sha, (manifest_path, workflow_path))
    require(set(files) == {manifest_path, workflow_path}, 'Incomplete trusted workflow binding')
    raw = files[manifest_path]
    require(len(raw) <= 4096, 'Controller manifest byte bound')
    manifest = json.loads(raw, object_pairs_hook=hosted_identity.unique)
    require(manifest == {'format': 'stead.hosted-controller/1', 'repository': hosted_identity.REPOSITORY,
        'controller_commit': controller_sha}, 'Workflow pins another controller')
    oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    return {'workflow_commit': workflow_sha, 'controller_commit': controller_sha,
        'manifest_path': manifest_path, 'manifest_raw': raw.decode('utf-8'), 'manifest_blob_oid': oid,
        'files': local.hashes(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller', required=True)
    parser.add_argument('--workflow', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--control', choices=CONTROL_CASES)
    args = parser.parse_args()
    require(os.getuid() == 0 and sys.flags.isolated and sys.dont_write_bytecode, 'Root isolated controller required')
    os.umask(0o077)
    regular_root(ROOT)
    # No hosted environment variable by itself can replace this authentication.
    identity = hosted_identity.authenticate(AUTH_ENVIRONMENT, workflow_sha=args.workflow,
        run_id=args.run_id, attempt=args.attempt)
    require(local.git('rev-parse', 'HEAD').decode().strip() == args.controller, 'Controller checkout identity differs')
    binding = workflow_binding(args.workflow, args.controller)
    controller = CONTROLLER_FILES
    candidate = local.inventory(args.candidate, ('native/core/desk',))
    combined, product = local.compose(controller, candidate)
    import toolchain
    toolchain.CACHE = ROOT / '.runtime'
    pins = toolchain.verify()
    cpus = sorted(os.sched_getaffinity(0))[:2]
    require(len(cpus) == 2, 'Hosted profile requires two CPUs')
    run_id = os.urandom(16).hex()
    username = 'steadci-' + run_id[:12]
    unit = 'stead-hosted-' + run_id + '.service'
    result = {'status': 'fail', 'classification': 'actual-github-hosted-disposable-native-ci',
        'qualifies_phase': False, 'controller_commit': args.controller, 'candidate_commit': args.candidate,
        'identity': identity, 'workflow_binding': binding, 'policy': POLICY,
        'run_id': run_id, 'errors': [], 'cleanup': {'verified': False}}
    if args.control:
        result.update(classification='actual-github-hosted-resource-control', native_execution=False)
    process = None
    account = job = inputs = None
    try:
        result['apparmor_setup'] = hosted_apparmor.prepare(regular_root)
        subprocess.run(['/usr/sbin/useradd', '--system', '--user-group', '--no-create-home', '--shell', '/usr/sbin/nologin', username], check=True, capture_output=True, timeout=10)
        account = pwd.getpwnam(username)
        result['unrelated_profile_control'] = hosted_apparmor.unrelated(account)
        result['unrelated_profile_observation'] = hosted_apparmor.verify_probe(result['unrelated_profile_control'], account.pw_uid, account.pw_gid)
        job = Path(tempfile.mkdtemp(prefix='stead-hosted-', dir='/var/lib'))
        os.chown(job, 0, account.pw_gid)
        os.chmod(job, 0o750)
        local.materialize(controller, job / 'controller')
        local.materialize(combined, job / 'composed')
        import digests
        import team_check
        inputs = {'format': 'stead.local-ci-inputs/1', 'execution_profile': POLICY['profile'],
            'workflow_binding': binding,
            'controller_commit': args.controller, 'candidate_commit': args.candidate,
            'controller_files': local.hashes(controller), 'candidate_product_files': local.hashes(product),
            'composed_files': local.hashes(combined), 'runtime_binary_sha256': pins['runtime']['binary_sha256'],
            'host_network_namespace': os.readlink('/proc/self/ns/net'), 'expected_native_inputs': {
                'native': digests.tree_sha(job / 'composed/native/core/desk'), 'runner': team_check.closure(),
                'harness': digests.source_sha(CAPTURED / 'scripts/urbit'), 'ingress': digests.tree_sha(CAPTURED / 'web/dev'),
                'toolchain': digests.sha(CAPTURED / 'specs/urbit/toolchain.lock.json'),
                'native_unit_inventory': digests.sha(CAPTURED / 'specs/urbit/phase2-pure-units.json')}}
        write(job / 'inputs.json', inputs)
        (job / 'control').mkdir()
        context = {'run_id': run_id, 'unit': unit, 'uid': account.pw_uid, 'gid': account.pw_gid,
            'cpus': cpus, 'pins': pins, 'guard_sha256': digests.sha(__file__), 'control_case': args.control}
        write(job / 'context.json', context)
        share_tree(job, account.pw_gid)
        share_tree(ROOT / '.runtime', account.pw_gid)
        # The root service owns the worker lifetime. Exiting MainPID kills the whole
        # unit; loss of this caller closes its unique pipe and is checked each tick.
        command = service_command(job, context)
        if args.control == 'parent-death':
            command = ['/usr/bin/python3', '-I', '-B', str(Path(__file__)), '_launcher', str(job), str(os.getpid())]
        process = spawn_owned(command, diagnostics=job / 'caller-stderr.private.log')
        if args.control:
            result['control'] = execute_control(args.control, process, job, context)
            result['status'] = 'pass'
        else:
            deadline = time.monotonic() + 7230
            while process.poll() is None:
                require(time.monotonic() < deadline, 'Hosted service deadline')
                time.sleep(.5)
            require(process.returncode == 0, 'Hosted service failed')
            result['guard'] = execution_policy.read_json(job / 'guard.json')
            require(result['guard']['status'] == 'pass', 'Hosted guardian failed')
            require_collected_child(result['guard'])
            raw = (job / 'console.private.log').read_bytes()
            worker = verify(raw, inputs, run_id=run_id,
                inventory=json.loads(controller['specs/urbit/phase2-pure-units.json']))
            require(worker['admission'] == result['guard']['admission']
                and worker['native']['execution_guard']['policy'] == POLICY, 'Hosted admission differs')
            result['verification'] = {'native_checks': len(worker['native']['checks']),
                'checks': worker['native']['checks'], 'native_suites': [
                    {key: row[key] for key in ('path', 'expected', 'observed', 'outcome')}
                    for row in worker['native']['native_units']], 'supported_migration': 'pass',
                'negative_controls': 'pass', 'mounts_unchanged': True,
                'worker_sha256': hashlib.sha256(raw).hexdigest(), 'inputs_sha256': hashlib.sha256(canonical(inputs)).hexdigest()}
            # verify() has admitted only the fixed timing/arm/verdict grammar;
            # these complete pure-unit transcripts contain no session +codes.
            result['verification']['native_unit_transcripts'] = worker['native']['native_units']
            result['verification']['native_unit_frames'] = worker['native']['native_unit_transcripts']
            result['status'] = 'pass'
    except BaseException as error:
        result['errors'].append(type(error).__name__ + ': ' + str(error)[:1000])
    finally:
        if process is not None:
            process.stdin.close()
        try:
            observed = readback(unit)
            if observed.get('ActiveState') not in ('inactive', 'failed'):
                subprocess.run(['/usr/bin/systemctl', 'stop', unit], capture_output=True, timeout=20, check=True)
                observed = readback(unit)
            require(observed.get('ActiveState') in ('inactive', 'failed'), 'Owned hosted unit remains active')
            cg = Path('/sys/fs/cgroup/system.slice') / unit
            require(not cg.exists() or 'populated 0' in (cg / 'cgroup.events').read_text().splitlines(), 'Hosted cgroup not empty')
            result['cleanup'] = {'verified': True, 'unit': unit, 'empty': True, 'active_state': observed['ActiveState']}
        except BaseException as error:
            result['errors'].append('Cleanup: ' + type(error).__name__)
            result['status'] = 'fail'
        if process is not None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                result['status'] = 'fail'
            if hasattr(process, 'stead_diagnostic_thread'):
                process.stead_diagnostic_thread.join(timeout=2)
                if process.stead_diagnostic_thread.is_alive():
                    result['errors'].append('Service diagnostic collector did not finish')
                if process.stead_diagnostics['overflow'] or process.stead_diagnostics['error']:
                    result['errors'].append('Service diagnostic collector failed')
        if job is not None and (job / 'guard.json').is_file():
            result['guard'] = execution_policy.read_json(job / 'guard.json')
        try:
            if account is not None:
                subprocess.run(['/usr/sbin/userdel', username], capture_output=True, check=True, timeout=10)
        except BaseException as error:
            result['errors'].append('Account cleanup: ' + type(error).__name__)
            result['status'] = 'fail'
        if result['errors'] or not result['cleanup']['verified']:
            result['status'] = 'fail'
        if job is not None:
            if result['status'] != 'pass':
                if args.control:
                    result['control_diagnostic'] = capture_control_diagnostic(job, args.control)
                elif inputs is not None:
                    try:
                        from worker_failure import project
                        # Collector EOF is required even for diagnostic parsing.
                        # This projection cannot produce or replace acceptance.
                        require_collected_child(result.get('guard', {}))
                        with (job / 'console.private.log').open('rb') as source:
                            raw = source.read(32 * 1024**2 + 1)
                        result['worker_diagnostic'] = project(raw, inputs, run_id=run_id)
                    except Exception:
                        result['worker_diagnostic'] = {'classification': 'failed-worker-diagnostic-unavailable',
                                                       'qualifies_phase': False}
                result['service_diagnostics'] = {}
                for name in ('caller-stderr.private.log', 'service-stderr.private.log'):
                    path = job / name
                    if path.is_file():
                        with path.open('rb') as source:
                            raw = source.read(8193)
                        require(len(raw) <= 8192, 'Service diagnostic output bound')
                        result['service_diagnostics'][name] = raw.decode('utf-8', errors='replace')
            write(job / 'report.json', result)
        public = ROOT / 'hosted-evidence'
        public.mkdir(mode=0o755, exist_ok=True)
        regular_root(public)
        os.chmod(public, 0o755)
        prefix = 'control-' + args.control + '-' if args.control else ''
        write(public / (prefix + 'report.json'), result)
        if inputs is not None:
            write(public / (prefix + 'inputs.json'), inputs)
        for path in public.iterdir():
            os.chmod(path, 0o644)
    print(json.dumps({'status': result['status'], 'evidence': 'hosted-evidence/report.json'}), flush=True)
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    bootstrap()
    if sys.argv[1:2] == ['_guardian'] and len(sys.argv) == 3:
        raise SystemExit(guardian(Path(sys.argv[2])))
    if sys.argv[1:2] == ['_launcher'] and len(sys.argv) == 4:
        raise SystemExit(launcher(Path(sys.argv[2]), int(sys.argv[3])))
    if sys.argv[1:2] == ['_child'] and len(sys.argv) == 4:
        child(Path(sys.argv[2]), int(sys.argv[3]))
        raise AssertionError('Worker exec returned')
    raise SystemExit(main())

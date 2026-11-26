"""Fixed model-only adapter for the existing authenticated hosted controller.

Source preparation only. Call outer() only after hosted.main authenticated the
actual GitHub workflow and its immutable controller binding. Internal dispatch
runs only after the same committed-source bootstrap; no candidate code enters.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import select
import signal
import stat
import subprocess
import sys
import time
import types

PREFIX = 'scripts/ci/model_proof/'
SOURCE_PATHS = {
    'worker.py': PREFIX + 'worker.py',
    'client.py': PREFIX + 'client.py',
    'interface.json': PREFIX + 'interface.json',
    'owned_child.py': 'scripts/urbit/owned_child.py',
    'model_connections.py': 'scripts/urbit/model_connections.py',
    'model_doc_replacement.py': 'scripts/urbit/model_doc_replacement.py',
}
MODULE_PATHS = {'owner_boundary': PREFIX + 'owner_boundary.py',
                'owner_collection': PREFIX + 'owner_collection.py',
                'model_intake': PREFIX + 'intake.py'}
SETUP_SECONDS = 720
UNIT_WAIT_SECONDS = 630


def require(ok):
    if not ok:
        raise ValueError('Fixed hosted model adapter refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(raw):
    return {'bytes': len(raw), 'sha256': sha(raw)}


def load(hosted):
    """Only captured immutable controller bytes; no filesystem import search."""
    require(os.getuid() == 0 and sys.flags.isolated and sys.dont_write_bytecode)
    result = {}
    for name, path in MODULE_PATHS.items():
        require(name not in sys.modules)
        raw = hosted.CONTROLLER_FILES[path]
        require(type(raw) is bytes and 0 < len(raw) <= 262144)
        module = types.ModuleType(name)
        module.__file__ = str(hosted.CAPTURED / path)
        sys.modules[name] = module
        exec(compile(raw, module.__file__, 'exec'), module.__dict__)
        result[name] = module
    return result


def write_new(path, raw, *, mode=0o600, gid=0):
    require(type(raw) is bytes and len(raw) <= 4 * 1024**2)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        os.fchown(fd, 0, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def read_json(boundary, path, maximum):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result
    raw = boundary.read_file(path, maximum)
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    require(canonical(value) == raw)
    return value


def source_map(hosted):
    return {path: pin(raw) for path, raw in hosted.CONTROLLER_FILES.items()}


def setup_failure_positions(hosted, intake, error, phase):
    """Closed positions from captured intake code; never exception text or locals."""
    require(phase in ('admission', 'apparmor', 'bwrap', 'intake', 'input',
                      'launch', 'execution', 'result'))
    path = MODULE_PATHS['model_intake']
    raw = hosted.CONTROLLER_FILES[path]
    filename = str(hosted.CAPTURED / path)
    require(type(raw) is bytes and 0 < len(raw) <= 262144
            and intake.__file__ == filename)
    root = compile(raw, filename, 'exec')  # Inspect code only; no execution.
    admitted, pending = [], [root]
    while pending:
        code = pending.pop()
        require(len(admitted) < 256)
        admitted.append(code)
        pending.extend(value for value in code.co_consts if type(value) is types.CodeType)
    line_count = len(raw.splitlines())
    locations, seen, inspected, truncated = [], set(), 0, False
    trace = error.__traceback__
    while trace is not None and inspected < 64:
        inspected += 1
        code, line = trace.tb_frame.f_code, trace.tb_lineno
        if (code.co_filename == filename and code in admitted
                and type(line) is int and 1 <= line <= line_count
                and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', code.co_name)):
            key = (code.co_name, line)
            if key not in seen:
                seen.add(key)
                if len(locations) < 16:
                    locations.append({'function': key[0], 'line': key[1]})
                else:
                    truncated = True
        trace = trace.tb_next
    return {'protocol': 'stead.fixed-model-setup-failure/1', 'phase': phase,
            'source_sha256': sha(raw), 'locations': locations,
            'frames_inspected': inspected, 'truncated': truncated or trace is not None}


def job_context(hosted, boundary, job):
    require(re.fullmatch('/var/lib/stead-model-proof-[a-z0-9]{8}', str(job)) is not None)
    hosted.regular_root(job)
    value = read_json(boundary, job / 'guardian.json', 2 * 1024**2)
    require(type(value) is dict and set(value) == {'protocol', 'boundary', 'owner', 'identity',
        'workflow_binding', 'controller_files', 'outer_pid', 'outer_start', 'created_monotonic_ns'})
    require(value['protocol'] == 'stead.fixed-model-guardian-input/1'
            and canonical(value['controller_files']) == canonical(source_map(hosted)))
    binding = value['workflow_binding']
    commit = hosted.local.git('rev-parse', 'HEAD').decode().strip()
    require(canonical(binding) == canonical(hosted.workflow_binding(binding['workflow_commit'], commit)))
    require(value['identity']['workflow_sha'] == binding['workflow_commit']
            and value['identity']['repository'] == hosted.hosted_identity.REPOSITORY
            and value['identity']['runner_environment'] == 'github-hosted')
    boundary.context(value['boundary'])
    require(value['boundary']['sources'] == {name: pin(hosted.CONTROLLER_FILES[path])
        for name, path in SOURCE_PATHS.items()})
    require(canonical(value['owner']) == boundary.read_file(job / 'input/owner.json', 262144))
    require(type(value['outer_pid']) is int and value['outer_pid'] > 1
            and type(value['outer_start']) is int and value['outer_start'] > 0
            and type(value['created_monotonic_ns']) is int)
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


def lease_read(boundary, path, owner_sha256, last):
    raw = lease_bytes(path, 0, 0, 0o600)
    row = json.loads(raw)
    require(canonical(row) == raw)
    require(type(row) is dict and set(row) == {'protocol', 'owner_sha256', 'generation', 'issued_ns', 'expires_ns'}
            and row['protocol'] == 'stead.fixed-model-lease/1' and row['owner_sha256'] == owner_sha256
            and all(type(row[k]) is int for k in ('generation', 'issued_ns', 'expires_ns'))
            and 0 < row['generation'] <= 10000000
            and row['expires_ns'] - row['issued_ns'] == 5000000000
            and 0 < row['issued_ns'] <= time.monotonic_ns() < row['expires_ns'])
    current = (row['generation'], row['issued_ns'])
    require(current == last or (current[0] > last[0] and current[1] > last[1]))
    return current


def lease_publish(job, label, owner_sha256, generation, gid):
    require(label in ('caller', 'guardian') and type(generation) is int and 0 < generation <= 10000000)
    now = time.monotonic_ns()
    raw = canonical({'protocol': 'stead.fixed-model-lease/1', 'owner_sha256': owner_sha256,
        'generation': generation, 'issued_ns': now, 'expires_ns': now + 5000000000})
    require(len(raw) <= 1024)
    # The temporary is outside the /lease bind, so its inventory stays closed.
    temporary = job / ('.lease-' + label + '-' + secrets.token_hex(8))
    destination = job / 'caller-lease.json' if label == 'caller' else job / 'lease/guardian.json'
    try:
        write_new(temporary, raw, mode=0o600 if label == 'caller' else 0o440,
                  gid=0 if label == 'caller' else gid)
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def heartbeat_factory(hosted, boundary, value, job):
    """Root-owned source record plus actual parent pidfd/EOF and finite service."""
    require(stat.S_ISFIFO(os.fstat(0).st_mode))
    os.set_blocking(0, False)
    parent = value['outer_pid']
    fd = os.pidfd_open(parent, 0)
    expected = (parent, value['outer_start'])
    try:
        require(boundary.proc_identity(parent) == expected)
    except BaseException:
        os.close(fd)
        raise
    previous = time.monotonic_ns()
    last, generation = (0, 0), 0
    owner_sha256 = sha(canonical(value['owner']))
    def guard():
        nonlocal previous, last, generation
        now = time.monotonic_ns()
        require(previous <= now and 0 <= now - value['created_monotonic_ns'] < 600 * 10**9)
        previous = now
        require(not select.select([fd], [], [], 0)[0]
                and boundary.proc_identity(parent) == expected)
        if select.select([0], [], [], 0)[0]:
            # No bytes are permitted on the lifetime pipe; either bytes or EOF
            # ends admission. It is never the worker's separate go channel.
            os.read(0, 1)
            raise ValueError('Fixed model caller ended')
        hosted.hosted_apparmor.require_label()
        boundary.group(value['boundary'])
        last = lease_read(boundary, job / 'caller-lease.json', owner_sha256, last)
        generation += 1
        lease_publish(job, 'guardian', owner_sha256, generation, value['boundary']['host_gid'])
    return guard, fd


def guardian(hosted, job):
    modules = load(hosted)
    boundary, collection = modules['owner_boundary'], modules['owner_collection']
    value = job_context(hosted, boundary, job)
    context = value['boundary']
    heartbeat, parentfd = heartbeat_factory(hosted, boundary, value, job)
    process = None
    result, artifacts = None, {}
    closed = False
    try:
        heartbeat()
        collection.service_current(context)
        require(set((boundary.group(context) / 'cgroup.procs').read_text().splitlines()) == {str(os.getpid())})
        command = ['/usr/bin/python3', '-I', '-B', str(Path(hosted.__file__)),
                   '_model_child', str(job), str(os.getpid())]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, close_fds=True, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        result, artifacts = collection.run(process, job, context, value['owner'], heartbeat)
    except BaseException as error:
        result = {'protocol': 'stead.fixed-model-adapter-failure/1', 'status': 'fail',
            'error_class': closed_error(error), 'native_executed': False, 'qualifies_g3': False}
    finally:
        # This owner also covers failures before collection.run's try block.
        if process is not None:
            try:
                if process.stdin is not None and not process.stdin.closed:
                    process.stdin.close()
            except BaseException:
                pass
            try:
                closed = collection.cleanup(process, context)
            except BaseException:
                closed = False
            for stream in (process.stdout, process.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except BaseException:
                    closed = False
        else:
            closed = set((boundary.group(context) / 'cgroup.procs').read_text().splitlines()) == {str(os.getpid())}
        os.close(parentfd)
        require(result is not None)
        result['adapter_owned_cleanup'] = closed
        if not closed:
            result['status'] = 'fail'
        if result['status'] == 'pass':
            require(set(artifacts) == set(collection.ARTIFACT_LIMITS))
            export = job / 'retained'
            export.mkdir(mode=0o700)
            os.chmod(export, 0o700)
            for name, raw in artifacts.items():
                write_new(export / name, raw)
        if (result['status'] == 'fail' and closed
                and result.get('failure_artifacts') is not None):
            expected = failure_pins(result, collection)
            require(set(artifacts) == set(expected)
                    and all(pin(raw) == expected[name] for name, raw in artifacts.items()))
            export = job / 'retained-failure'
            export.mkdir(mode=0o700)
            os.chmod(export, 0o700)
            for name, raw in artifacts.items():
                write_new(export / name, raw)
        write_new(job / 'model-guard.json', canonical(result))
    return 0 if result['status'] == 'pass' else 1


def closed_error(error):
    name = type(error).__name__
    return name if name in {'ValueError', 'TypeError', 'OSError', 'TimeoutError', 'PermissionError',
        'FileNotFoundError', 'ProcessLookupError', 'BrokenPipeError', 'CalledProcessError',
        'TimeoutExpired', 'JSONDecodeError', 'UnicodeDecodeError'} else 'unrecognized'


def child(hosted, job, parent):
    modules = load(hosted)
    boundary = modules['owner_boundary']
    value = job_context(hosted, boundary, job)
    boundary.group(value['boundary'])
    boundary.launch_child(job, value['boundary'], parent)
    raise AssertionError('Fixed child exec returned')


def service_command(hosted, collection, job, context):
    require(re.fullmatch('stead-model-[a-f0-9]{32}\\.service', context['unit']) is not None)
    command = ['/usr/bin/systemd-run', '--quiet', '--wait', '--pipe', '--service-type=exec',
               '--unit=' + context['unit']]
    command.extend('--property=' + key + '=' + value
                   for key, value in collection.service_properties(context['cpu']).items())
    return command + ['/usr/bin/python3', '-I', '-B', str(Path(hosted.__file__)), '_model_guardian', str(job)]


def complete_guard(guard, collection):
    require(type(guard) is dict and guard['protocol'] == 'stead.fixed-model-owner-result/1'
            and guard['status'] == 'pass' and guard['error_class'] == 'none'
            and guard['cleanup_error_class'] == 'none'
            and guard['parent_admitted'] is True and guard['child_streams_eof'] is True
            and guard['owned_children_empty'] is True and guard['adapter_owned_cleanup'] is True
            and guard['native_executed'] is False and guard['qualifies_g3'] is False
            and type(guard['artifact_pins']) is dict
            and set(guard['artifact_pins']) == set(collection.ARTIFACT_LIMITS)
            and type(guard['worker_result']) is dict and guard['worker_result']['status'] == 'pass'
            and canonical(guard['worker_result']['artifacts']) == canonical(guard['artifact_pins']))
    for name, row in guard['artifact_pins'].items():
        require(type(row) is dict and set(row) == {'bytes', 'sha256'}
                and type(row['bytes']) is int and 0 < row['bytes'] <= collection.ARTIFACT_LIMITS[name]
                and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}', row['sha256']))


def checked_artifacts(boundary, collection, job, guard):
    """Called only after independently verified whole-unit empty cleanup."""
    complete_guard(guard, collection)
    return {name: boundary.read_file(job / 'retained' / name,
                collection.ARTIFACT_LIMITS[name], expected)
            for name, expected in guard['artifact_pins'].items()}



def failure_pins(guard, collection):
    """Strict failed observation; this cannot satisfy the unchanged pass gate."""
    require(type(guard) is dict and guard.get('protocol') == 'stead.fixed-model-owner-result/1'
            and guard.get('status') == 'fail' and guard.get('error_class') == 'worker-reported-failure'
            and guard.get('cleanup_error_class') == 'none'
            and guard.get('failure_evidence_error_class') == 'none'
            and guard.get('parent_admitted') is True and guard.get('child_streams_eof') is True
            and guard.get('owned_children_empty') is True and guard.get('adapter_owned_cleanup') is True
            and guard.get('native_executed') is False and guard.get('qualifies_g3') is False
            and guard.get('worker_result') is None and guard.get('artifact_pins') == {}
            and type(guard.get('worker_exit_code')) is int and guard['worker_exit_code'] == 1)
    collection.checked_failure_observation(guard.get('worker_failure'))
    metadata = guard.get('failure_artifacts')
    require(type(metadata) is dict and set(metadata) == set(collection.FAILURE_LIMITS))
    pins = {}
    for name, row in metadata.items():
        require(type(row) is dict and set(row) == {'present', 'bytes', 'sha256'}
                and type(row['present']) is bool)
        if row['present']:
            require(type(row['bytes']) is int and 0 <= row['bytes'] <= collection.FAILURE_LIMITS[name]
                    and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}', row['sha256']))
            pins[name] = {key: row[key] for key in ('bytes', 'sha256')}
        else:
            require(row['bytes'] is None and row['sha256'] is None)
    return pins


def checked_failure_artifacts(boundary, collection, job, guard):
    """Called after whole-unit cleanup; retained root bytes, never a proposal."""
    pins = failure_pins(guard, collection)
    directory = job / 'retained-failure'
    before = boundary.directory(directory, 0o700)
    require(before.st_gid == 0 and set(os.listdir(directory)) == set(pins))
    result = {name: boundary.read_failed_retained(directory / name,
                collection.FAILURE_LIMITS[name], expected) for name, expected in pins.items()}
    require(boundary.identity(directory.lstat()) == boundary.identity(before)
            and set(os.listdir(directory)) == set(pins))
    return result


def outer(hosted, args, identity, binding):
    """One authenticated fixed proof; never compose or execute a native desk."""
    modules = load(hosted)
    boundary, collection, intake = (modules[name] for name in ('owner_boundary', 'owner_collection', 'model_intake'))
    require(args.mode == 'model' and args.control is None and args.candidate == args.controller)
    require(binding['controller_commit'] == args.controller and identity['workflow_sha'] == args.workflow)
    started = time.monotonic()
    outer_pid = os.getpid()
    outer_identity = boundary.proc_identity(outer_pid)
    def setup_guard():
        require(os.geteuid() == 0 and boundary.proc_identity(outer_pid) == outer_identity
                and 0 <= time.monotonic() - started < SETUP_SECONDS)
        hosted.regular_root(hosted.ROOT)
    run_id = secrets.token_hex(16)
    job = Path('/var/lib/stead-model-proof-' + secrets.token_hex(4))
    account = pwd.getpwnam('runner')
    require(0 < account.pw_uid < 65534 and 0 < account.pw_gid < 65534 and not job.exists())
    context = {'protocol': 'stead.fixed-model-owner-context/1', 'run_id': run_id,
        'unit': 'stead-model-' + run_id + '.service', 'cpu': min(os.sched_getaffinity(0)),
        'host_uid': account.pw_uid, 'host_gid': account.pw_gid,
        'sources': {name: pin(hosted.CONTROLLER_FILES[path]) for name, path in SOURCE_PATHS.items()},
        'bwrap_sha256': sha(boundary.read_file(Path('/usr/bin/bwrap'), 4 * 1024**2))}
    boundary.context(context)
    result = {'protocol': 'stead.fixed-model-hosted-result/1', 'status': 'fail',
        'classification': 'actual-disposable-standalone-model-compatibility',
        'native_executed': False, 'qualifies_g3': False, 'identity': identity,
        'workflow_binding': binding, 'controller_commit': args.controller,
        'run_id': run_id, 'source_pins': source_map(hosted), 'context': context,
        'error_class': 'none', 'cleanup_error_class': 'none', 'cleanup': {'verified': False}}
    process = None
    service_started = False
    setup_phase = 'admission'
    try:
        setup_guard()
        setup_phase = 'apparmor'
        result['apparmor_setup'] = hosted.hosted_apparmor.prepare(hosted.regular_root)
        setup_phase = 'bwrap'
        result['bwrap_version'] = subprocess.run(['/usr/bin/bwrap', '--version'], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C'}).stdout.decode('ascii').strip()
        require(result['bwrap_version'] == 'bubblewrap 0.9.0')
        def setup_timeout(_signum, _frame):
            raise TimeoutError('Fixed model setup deadline')
        old_alarm = signal.signal(signal.SIGALRM, setup_timeout)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, SETUP_SECONDS - (time.monotonic() - started)))
        try:
            setup_phase = 'intake'
            result['intake'] = intake.prepare(job, setup_guard)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_alarm)
        setup_phase = 'input'
        (job / 'model').mkdir(mode=0o755)
        os.chmod(job / 'model', 0o755)
        os.rename(job / boundary.MODEL_NAME, job / 'model' / boundary.MODEL_NAME)
        # Preserve one link and the exact root-owned download; no model copy.
        model_info = (job / 'model' / boundary.MODEL_NAME).lstat()
        require(stat.S_ISREG(model_info.st_mode) and model_info.st_uid == 0
                and model_info.st_nlink == 1 and model_info.st_size == boundary.MODEL_BYTES)
        (job / 'lease').mkdir(mode=0o550)
        os.chown(job / 'lease', 0, account.pw_gid)
        os.chmod(job / 'lease', 0o550)
        input_dir = job / 'input'
        input_dir.mkdir(mode=0o550)
        os.chown(input_dir, 0, account.pw_gid)
        os.chmod(input_dir, 0o550)
        interface = json.loads(hosted.CONTROLLER_FILES[SOURCE_PATHS['interface.json']])
        owner = {'protocol': 'stead.fixed-model-worker-input/1',
            'host_uid': account.pw_uid, 'host_gid': account.pw_gid,
            'outer_namespaces': {name: os.readlink('/proc/self/ns/' + name) for name in boundary.NAMESPACES},
            'sources': context['sources'], 'runtime': result['intake']['runtime'],
            'model': {key: interface['model'][key] for key in ('filename', 'bytes', 'sha256')},
            'server_argv': interface['runtime']['server_argv_after_pinned_executable']}
        for name, path in SOURCE_PATHS.items():
            write_new(input_dir / name, hosted.CONTROLLER_FILES[path], mode=0o440, gid=account.pw_gid)
        write_new(input_dir / 'owner.json', canonical(owner), mode=0o440, gid=account.pw_gid)
        os.chown(job, 0, account.pw_gid)
        os.chmod(job, 0o750)
        setup_guard()
        guardian_input = {'protocol': 'stead.fixed-model-guardian-input/1', 'boundary': context,
            'owner': owner, 'identity': identity, 'workflow_binding': binding,
            'controller_files': source_map(hosted), 'outer_pid': outer_pid,
            'outer_start': outer_identity[1], 'created_monotonic_ns': time.monotonic_ns()}
        write_new(job / 'guardian.json', canonical(guardian_input))
        caller_generation = 1
        owner_sha256 = sha(canonical(owner))
        lease_publish(job, 'caller', owner_sha256, caller_generation, account.pw_gid)
        lease_publish(job, 'guardian', owner_sha256, 1, account.pw_gid)
        command = service_command(hosted, collection, job, context)
        setup_phase = 'launch'
        service_started = True
        # Existing trusted spawn owns PDEATHSIG plus the unique service stdin.
        # No diagnostic thread is created; no raw service log is exported.
        process = hosted.spawn_owned(command)
        setup_phase = 'execution'
        limit = time.monotonic() + UNIT_WAIT_SECONDS
        while process.poll() is None:
            require(time.monotonic() < limit)
            caller_generation += 1
            lease_publish(job, 'caller', owner_sha256, caller_generation, account.pw_gid)
            time.sleep(0.2)
        result['service_exit_code'] = process.returncode
        require(process.returncode == 0)
        setup_phase = 'result'
        result['guard'] = read_json(boundary, job / 'model-guard.json', 131072)
        complete_guard(result['guard'], collection)
        result['status'] = 'pass'
    except BaseException as error:
        result['error_class'] = closed_error(error)
        try:
            result['setup_failure'] = setup_failure_positions(hosted, intake, error, setup_phase)
        except BaseException:
            result['setup_failure'] = None
    finally:
        if process is not None:
            try:
                process.stdin.close()
            except BaseException:
                result['cleanup_error_class'] = 'caller-pipe-close'
        try:
            state = hosted.readback(context['unit'])
            if state.get('ActiveState') not in ('inactive', 'failed'):
                subprocess.run(['/usr/bin/systemctl', 'stop', context['unit']], check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                state = hosted.readback(context['unit'])
            cg = Path('/sys/fs/cgroup/system.slice') / context['unit']
            require(state.get('ActiveState') in ('inactive', 'failed')
                    and (not cg.exists() or 'populated 0' in (cg / 'cgroup.events').read_text().splitlines()))
            result['cleanup'] = {'verified': True, 'unit': context['unit'], 'empty': True,
                                 'active_state': state['ActiveState'], 'service_started': service_started}
        except BaseException:
            result['cleanup_error_class'] = 'service-cleanup'
        if process is not None:
            try:
                process.wait(timeout=5)
            except BaseException:
                result['cleanup_error_class'] = 'caller-reap'
                try:
                    process.kill()
                    process.wait(timeout=5)
                except BaseException:
                    result['cleanup_error_class'] = 'caller-reap'
        if result['error_class'] != 'none' or result['cleanup_error_class'] != 'none' or not result['cleanup']['verified']:
            result['status'] = 'fail'
        public = hosted.ROOT / 'model-evidence'
        public.mkdir(mode=0o755)
        os.chmod(public, 0o755)
        hosted.regular_root(public)
        if job.is_dir() and (job / 'model-guard.json').is_file():
            result['guard'] = read_json(boundary, job / 'model-guard.json', 131072)
        if result['status'] == 'pass':
            artifacts = checked_artifacts(boundary, collection, job, result['guard'])
            for name, raw in artifacts.items():
                write_new(public / name, raw, mode=0o644)
        if (result['status'] == 'fail' and result['cleanup']['verified'] is True
                and result['cleanup_error_class'] == 'none'
                and type(result.get('guard')) is dict
                and result['guard'].get('failure_artifacts') is not None):
            try:
                artifacts = checked_failure_artifacts(boundary, collection, job, result['guard'])
                for name, raw in artifacts.items():
                    write_new(public / name, raw, mode=0o644)
                result['failed_output_export'] = 'collected'
            except BaseException:
                result['failed_output_export'] = 'refused'
        else:
            result['failed_output_export'] = 'not-collected'
        result['elapsed_ms'] = int((time.monotonic() - started) * 1000)
        write_new(public / 'owner-report.json', canonical(result), mode=0o644)
    return 0 if result['status'] == 'pass' else 1

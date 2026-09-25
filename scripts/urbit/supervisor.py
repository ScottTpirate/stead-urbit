#!/usr/bin/env python3
"""Private fixture administrator. Never expose this socket or Lens as an app API."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import subprocess
import threading
import time
import traceback
import urllib.request
import weakref

from digests import sha, source_sha, tree_sha, source_inventory, read_source
from conn import assert_result, run_thread
import execution_policy
import core_check
import core_test
import gall_schedule
import skill_evaluation_support

STATE = Path('/state')
LIVE = STATE / 'live'
SEED = STATE / 'seed'
SHIPS = ('zod', 'bus', 'nec', 'bud')
LOCK = json.loads(Path('/toolchain.json').read_text())
PROCESSES = {}
LOGS = {}
PROGRESS = {'stage': 'starting', 'ready': False, 'error': None}
MUTEX = threading.Lock()
STOP = threading.Event()
STOP_REQUESTED = threading.Event()
NORMAL_STOP = threading.Event()
FORCED_STOP = threading.Event()
SHUTDOWN_FAILED = threading.Event()
INITIALIZATION_FAILED = threading.Event()
TERMINATION_LOCK = threading.Lock()
TERMINATED = weakref.WeakSet()
EVIDENCE = []
LOADED_SOURCE_DIGEST = source_sha(Path('/code'))


def qualified_source():
    context = execution_policy.read_json('/execution/source-context.json')
    if (context.get('dirty_paths') != [] or context.get('committed_bytes_verified') is not True
            or not context.get('committed_files') or context.get('harness_sha256') != LOADED_SOURCE_DIGEST
            or context.get('native_tree_sha256') != tree_sha(Path('/native/core/desk'))):
        raise ValueError('Qualification requires the exact committed source captured at startup')
    if context.get('script_files') != source_inventory(Path('/code')):
        raise ValueError('Helper file inventory changed after startup')
    mounts = {'scripts/urbit': Path('/code'), 'native': Path('/native'), 'specs/urbit': Path('/specs'),
              'tests/urbit/native_gall_schedule': Path('/native-tests/gall-schedule'),
              'tests/urbit/skill_evaluation': Path('/native-tests/skill-evaluation')}
    for name, digest in context['trees'].items():
        if name not in mounts or tree_sha(mounts[name]) != digest:
            raise ValueError('Qualification source tree changed after startup')
    for name, digest in context['committed_files'].items():
        matched = [(prefix, mount) for prefix, mount in mounts.items() if name.startswith(prefix + '/')]
        if len(matched) != 1:
            raise ValueError('Qualification source is outside fixed read-only mounts')
        prefix, mount = matched[0]
        source = mount / name[len(prefix) + 1:]
        if hashlib.sha256(read_source(source)).hexdigest() != digest:
            raise ValueError('Qualification source no longer matches committed bytes')
    return context['source_commit']


def execution_check(preflight=False):
    if STOP_REQUESTED.is_set():
        raise execution_policy.GuardError('Fixture stop is latched')
    return execution_policy.require_lease(preflight=preflight, read_only=True)


def completion_code():
    # A zero process status must not erase a lease failure or an interrupted
    # initialization simply because runtime SIGTERM persisted its own state.
    return 0 if (NORMAL_STOP.is_set() and not FORCED_STOP.is_set()
                 and not SHUTDOWN_FAILED.is_set() and not INITIALIZATION_FAILED.is_set()) else 1


def terminate_once(process):
    # The watchdog and control handler may both request shutdown. Key by Popen
    # incarnation, not ship name or PID, so a later restart still receives TERM.
    with TERMINATION_LOCK:
        if process.poll() is None and process not in TERMINATED:
            try:
                process.terminate()
            except Exception:
                SHUTDOWN_FAILED.set()
                raise
            TERMINATED.add(process)


def signal_children():
    errors = []
    for process in tuple(PROCESSES.values()):
        try:
            terminate_once(process)
        except Exception as error:
            SHUTDOWN_FAILED.set()
            errors.append(str(error))
    return errors


def execution_watch():
    previous = None
    while not STOP.wait(.25):
        try:
            lease = execution_check()
            if previous is not None and (lease['generation'] < previous['generation']
                    or lease['sample']['finished'] < previous['sample']['finished']):
                raise execution_policy.GuardError('Execution lease moved backwards')
            previous = lease
        except Exception as error:
            normal = NORMAL_STOP.is_set()
            STOP_REQUESTED.set()
            if not normal:
                FORCED_STOP.set()
            PROGRESS.update(stage='stopping' if normal else 'guard-stopped', ready=False,
                            error=None if normal else str(error))
            record('requested fixture stop' if normal else 'execution guard stopped',
                   {'error': None if normal else str(error)})
            # Interrupt our known Popen children immediately, before waiting for
            # an active test's mutex. No PID-file lookup or unrelated signaling.
            for error in signal_children():
                record('guard signal failure', {'error': error})
            with MUTEX:
                try:
                    all_stop()
                except Exception as cleanup_error:
                    SHUTDOWN_FAILED.set()
                    record('guard shutdown failure', {'error': str(cleanup_error)})
                STOP.set()
            return


def guarded_result(result):
    try:
        lease = execution_check()
        result['execution_guard'] = {key: lease[key] for key in (
            'run_id', 'generation', 'guard_sha256', 'policy_sha256', 'policy')}
    except Exception as error:
        result.update(status='fail', error='Execution guard interrupted result: ' + str(error))
    # Persist the same final guarded status, including an interrupted test that
    # completed its own checks just before cancellation. No stale green report.
    if 'evidence_file' in result:
        name = Path(result['evidence_file']).name
        if not (name.startswith(('core-', 'smoke-', 'gall-schedule-', 'skill-evaluation-')) and name.endswith('.json')):
            raise ValueError('Unexpected native evidence target')
        path = STATE / 'logs' / name
        evidence = execution_policy.read_json(path, maximum=16 * 1024 * 1024)
        evidence.update(status=result['status'], execution_guard=result.get('execution_guard'),
                        error=result.get('error'))
        execution_policy.write_json(path, evidence)
    return result


def record(command, result):
    item = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'command': command, 'result': result}
    EVIDENCE.append(item)
    print(json.dumps(item), flush=True)


def dojo(ship, command, timeout=120):
    execution_check()
    lines = (LIVE / ship / '.http.ports').read_text().splitlines()
    port = next(int(line.split()[0]) for line in lines if 'loopback' in line)
    # Lens parses a build expression separately from its sink. Dojo's |hood
    # shorthand is a full command and must be split for this control interface.
    source = '+hood/' + command[1:] if command.startswith('|') else command
    sink = {'app': 'hood'} if command.startswith('|') else {'stdout': None}
    body = json.dumps({'source': {'dojo': source}, 'sink': sink}).encode()
    request = urllib.request.Request(f'http://127.0.0.1:{port}', data=body,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError('Fixture response exceeded limit')
    result = json.loads(raw)
    if not isinstance(result, str):
        raise ValueError(f'Unexpected Lens response: {result}')
    return result


def wait_ready(ship, timeout=1200):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if STOP_REQUESTED.is_set():
            raise InterruptedError('Fixture boot cancelled by stop')
        execution_check()
        if PROCESSES[ship].poll() is not None:
            raise RuntimeError(f'{ship} exited during boot; inspect logs')
        try:
            result = dojo(ship, 'zuse', timeout=30)
            if result.strip() != '%408':
                raise RuntimeError(f'Unexpected kernel: {result}')
            record(f'{ship}: zuse', result)
            return
        except (OSError, StopIteration, ValueError):
            time.sleep(1)
    raise TimeoutError(f'{ship} did not become ready within {timeout}s')


def launch(ship):
    execution_check()
    pier = LIVE / ship
    if pier.is_symlink():
        raise ValueError('Refusing redirected pier')
    command = ['/runtime/' + LOCK['runtime']['binary'], '-t', '-L', '--no-dock',
               '--loom', '31', '-b', '127.0.0.1', '--http-port', str(18080 + SHIPS.index(ship))]
    if not (pier / '.urb').exists():
        command += ['-F', ship, '-B', '/runtime/downloads/' + LOCK['boot_artifact']['archive'],
                    '-A', '/kernel/pkg/arvo', '-c']
    command += [str(pier)]
    log = (STATE / 'logs' / f'{ship}.log').open('ab')
    LOGS[ship] = log
    PROCESSES[ship] = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                      stdout=log, stderr=log, close_fds=True,
                                      pass_fds=(gate.fileno(),))
    record('launch ' + ship, {'argv': command, 'pid': PROCESSES[ship].pid})


def shutdown(ship, timeout=10):
    process = PROCESSES.get(ship)
    if process is None:
        return
    # TERM remains available before Lens starts. A nonzero startup/shutdown
    # result is unclean even when no escalation was needed.
    forced = False
    try:
        if process.poll() is None:
            terminate_once(process)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                forced = True
                FORCED_STOP.set()
                process.kill()
                process.wait(timeout=1)
        record('shutdown ' + ship, {'exit_code': process.returncode, 'forced': forced})
        if forced or process.returncode != 0:
            raise RuntimeError(f'{ship} exit was not clean: {process.returncode}; forced={forced}')
    except Exception:
        SHUTDOWN_FAILED.set()
        raise
    finally:
        if ship in LOGS:
            try:
                LOGS[ship].close()
            except Exception:
                SHUTDOWN_FAILED.set()
                raise


def all_stop():
    deadline = time.monotonic() + 15
    errors = signal_children()
    for ship in SHIPS:
        try:
            shutdown(ship, timeout=max(.05, deadline - time.monotonic()))
        except Exception as error:
            errors.append(str(error))
    if errors:
        SHUTDOWN_FAILED.set()
        raise RuntimeError('; '.join(errors))


def copy_seed_to_live():
    execution_check()
    if any(process.poll() is None for process in PROCESSES.values()):
        raise RuntimeError('Cannot restore while a fake ship is live')
    manifest = json.loads((SEED / 'manifest.json').read_text())
    if manifest['toolchain_sha256'] != sha('/toolchain.json'):
        raise ValueError('Toolchain differs from seed')
    for ship in SHIPS:
        if (SEED / ship).is_symlink() or tree_sha(SEED / ship) != manifest['ships'][ship]:
            raise ValueError('Seed integrity failure: ' + ship)
    if LIVE.is_symlink():
        raise ValueError('Refusing redirected live directory')
    shutil.rmtree(LIVE)
    LIVE.mkdir()
    for ship in SHIPS:
        shutil.copytree(SEED / ship, LIVE / ship, symlinks=True)


def initialize():
    with MUTEX:
        try:
            execution_check(preflight=True)
            if (SEED / 'manifest.json').exists():
                if json.loads((SEED / 'manifest.json').read_text())['toolchain_sha256'] != sha('/toolchain.json'):
                    raise ValueError('Existing fixture toolchain differs')
            LIVE.mkdir(exist_ok=True)
            for ship in SHIPS:
                PROGRESS['stage'] = 'booting ' + ship
                launch(ship)
                wait_ready(ship)
                record(f'{ship}: |mount %base', dojo(ship, '|mount %base'))
                deadline = time.monotonic() + 60
                while not (LIVE / ship / 'base').is_dir():
                    if time.monotonic() > deadline:
                        raise TimeoutError('Base mount absent')
                    time.sleep(.2)
            if not (SEED / 'manifest.json').exists():
                PROGRESS['stage'] = 'creating stopped clean seeds'
                all_stop()
                execution_check()
                if FORCED_STOP.is_set():
                    raise RuntimeError('Interrupted or forcibly stopped state cannot become a clean seed')
                if SEED.exists():
                    raise RuntimeError('Incomplete seed exists; inspect it without overwriting')
                SEED.mkdir()
                manifest = {'format': 1, 'toolchain_sha256': sha('/toolchain.json'), 'ships': {}}
                for ship in SHIPS:
                    shutil.copytree(LIVE / ship, SEED / ship, symlinks=True)
                    manifest['ships'][ship] = tree_sha(SEED / ship)
                (SEED / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
                record('seed stopped copies', manifest)
                for ship in SHIPS:
                    launch(ship)
                    wait_ready(ship)
            execution_check()
            PROGRESS.update(stage='ready', ready=True)
        except Exception as error:
            INITIALIZATION_FAILED.set()
            STOP_REQUESTED.set()
            PROGRESS.update(stage='failed', ready=False, error=str(error))
            traceback.print_exc()


def sync_sources():
    for ship in SHIPS:
        # Base is a disposable mounted development desk in this smoke profile.
        for src in sorted(Path('/native/desk').rglob('*.hoon')):
            target = LIVE / ship / 'base' / src.relative_to('/native/desk')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
        record(f'{ship}: |commit %base', dojo(ship, '|commit %base', timeout=180))
    record('zod: |start %stead-home', dojo('zod', '|start %stead-home'))
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if dojo('zod', '.^(? %gu /=stead-home=/$)').strip() == '%.y':
            return
        time.sleep(1)
    raise RuntimeError('stead-home failed to compile/start; inspect zod log')


def expect(ship, command, positive, rejection=None):
    execution_check()
    response = run_thread('/runtime/' + LOCK['runtime']['binary'],
                          LIVE / ship / '.urb/conn.sock', command)
    record(ship + ': ' + command, response)
    assert_result(response, positive, rejection)


def smoke_test():
    begin = time.monotonic()
    first = len(EVIDENCE)
    result = {'classification': 'local-real-native-fake-ships', 'status': 'fail'}
    native_digest = tree_sha(Path('/native/desk'))
    code_digest = source_sha(Path('/code'))
    try:
        execution_check(preflight=True)
        if code_digest != LOADED_SOURCE_DIGEST:
            raise RuntimeError('Supervisor source changed since load; stop/start before testing')
        # Test owns only this marked synthetic fixture and starts from stopped seeds.
        all_stop()
        copy_seed_to_live()
        for ship in SHIPS:
            launch(ship)
            wait_ready(ship)
        sync_sources()
        if sha('/corpus.json') != LOCK['protocol_corpus']['sha256']:
            raise ValueError('Native corpus differs from lock')
        for case in json.loads(Path('/corpus.json').read_text())['cases']:
            if 'restart' in case:
                shutdown(case['restart'])
                launch(case['restart'])
                wait_ready(case['restart'])
            else:
                expect(**case)
        if native_digest != tree_sha(Path('/native/desk')) or code_digest != source_sha(Path('/code')):
            raise RuntimeError('Source changed during native test; results cannot label new bytes')
        execution_check()
        result['status'] = 'pass'
    except Exception as error:
        result['error'] = str(error)
        traceback.print_exc()
    result.update(elapsed_seconds=round(time.monotonic() - begin, 3),
                  toolchain_sha256=sha('/toolchain.json'), native_tree_sha256=native_digest,
                  harness_tree_sha256=code_digest,
                  commands=EVIDENCE[first:], scope='synthetic counter only; not product/session/Git authorization')
    name = 'smoke-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json'
    (STATE / 'logs' / name).write_text(json.dumps(result, indent=2) + '\n')
    result['evidence_file'] = '.piers/fakes/logs/' + name
    return result


def handle(connection):
    with connection:
        try:
            connection.settimeout(60)
            data = b''
            while not data.endswith(b'\n'):
                block = connection.recv(65536)
                if not block or len(data) + len(block) > 65536:
                    raise ValueError('Invalid control envelope')
                data += block
            request = json.loads(data)
            if request == {'op': 'status'}:
                try:
                    lease = execution_check()
                    execution = {'run_id': lease['run_id'], 'generation': lease['generation'], 'state': 'running'}
                except Exception as error:
                    PROGRESS.update(stage='guard-stopped', ready=False, error=str(error))
                    execution = {'state': 'stopped', 'error': str(error)}
                result = {**PROGRESS, 'execution_guard': execution,
                          'ships': {s: {'pid': p.pid, 'exit': p.poll()} for s, p in PROCESSES.items()}}
            elif request == {'op': 'stop'}:
                NORMAL_STOP.set()
                STOP_REQUESTED.set()
                PROGRESS.update(stage='stopping', ready=False)
                with MUTEX:
                    all_stop()
                    result = {'stopped': True, 'status': 'stopped', 'ready': False}
                    PROGRESS.update(stage='stopped', ready=False)
                    STOP.set()
            elif request == {'op': 'test'}:
                with MUTEX:
                    if not PROGRESS['ready']:
                        raise RuntimeError('Fixture not ready: ' + str(PROGRESS))
                    execution_check(preflight=True)
                    result = guarded_result(smoke_test())
            elif request == {'op': 'core-test'}:
                with MUTEX:
                    if not PROGRESS['ready']:
                        raise RuntimeError('Fixture not ready')
                    execution_check(preflight=True)
                    result = guarded_result(core_test.run(globals()))
            elif request == {'op': 'core-check'}:
                with MUTEX:
                    if not PROGRESS['ready']:
                        raise RuntimeError('Fixture not ready')
                    execution_check(preflight=True)
                    PROGRESS.update(stage='compiling', ready=False, error=None)
                    result = None
                    try:
                        result = guarded_result(core_check.run(globals()))
                    finally:
                        if result is None or result['status'] != 'pass':
                            PROGRESS.update(stage='failed', ready=False,
                                            error='Native compilation/probes failed; make stop before retry')
                            all_stop()
                        else:
                            PROGRESS.update(stage='ready', ready=True, error=None)
            elif request == {'op': 'gall-schedule'}:
                with MUTEX:
                    if not PROGRESS['ready']:
                        raise RuntimeError('Fixture not ready')
                    PROGRESS.update(stage='gall-schedule', ready=False, error=None)
                    result = None
                    try:
                        result = guarded_result(gall_schedule.run(globals()))
                    finally:
                        if result is None or result['status'] != 'pass':
                            PROGRESS.update(stage='failed', ready=False, error='Scheduled Gall lane failed')
                            all_stop()
                        else:
                            PROGRESS.update(stage='ready', ready=True, error=None)
            elif (set(request) == {'op', 'condition'} and request['op'] == 'skill-evaluation'
                  and request['condition'] in ('prequalification', 'baseline', 'local_skill_assisted')):
                with MUTEX:
                    if not PROGRESS['ready']:
                        raise RuntimeError('Fixture not ready')
                    PROGRESS.update(stage='skill-evaluation', ready=False, error=None)
                    condition = request['condition']
                    try:
                        context = dict(globals(), WORKFLOW_SOURCE_COMMIT=qualified_source())
                        if condition != 'prequalification':
                            proof = execution_policy.read_json('/workflow/prequalification.json')
                            if set(proof) != {'inner', 'guard'}:
                                raise ValueError('Exact workflow prequalification references required')
                            for reference in proof.values():
                                path = Path(reference['path'])
                                if not path.is_absolute() or not path.is_relative_to('/workflow') or '..' in path.parts:
                                    raise ValueError('Workflow proof must be inside the fixed read-only mount')
                            context['WORKFLOW_PREQUALIFICATION'] = proof
                        result = guarded_result(skill_evaluation_support.run(context,
                            Path('/native-tests/skill-evaluation'), Path('/workflow') / condition,
                            condition, prequalify=condition == 'prequalification'))
                        try:
                            if qualified_source() != context['WORKFLOW_SOURCE_COMMIT']:
                                raise ValueError('Workflow committed source changed')
                        except Exception as error:
                            result.update(status='fail', error='Workflow final source binding failed: ' + str(error))
                            result = guarded_result(result)
                    finally:
                        # Always finish this owned lifetime, including an
                        # admission exception before the adapter checkpoints.
                        NORMAL_STOP.set()
                        STOP_REQUESTED.set()
                        try:
                            all_stop()
                        finally:
                            PROGRESS.update(stage='stopped', ready=False)
                            STOP.set()
            else:
                raise ValueError('Unknown control command')
            reply = {'ok': True, 'result': result}
        except Exception as error:
            reply = {'ok': False, 'error': str(error)}
        connection.sendall(json.dumps(reply).encode() + b'\n')


if __name__ == '__main__':
    os.umask(0o077)
    execution_check(preflight=True)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP_REQUESTED.set())
    # This fd lives for the entire supervisor lifetime, including every child.
    gate = (STATE / 'lifecycle.lock').open('a+')
    fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for name in ('live', 'seed', 'logs', 'control.sock'):
        if (STATE / name).is_symlink():
            raise ValueError('Redirected fixture entry')
    socket_path = STATE / 'control.sock'
    socket_path.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(str(socket_path))
        server.listen(8)
        server.settimeout(.5)
        threading.Thread(target=execution_watch, daemon=True).start()
        threading.Thread(target=initialize, daemon=True).start()
        while not STOP.is_set():
            try:
                connection, _ = server.accept()
                threading.Thread(target=handle, args=(connection,), daemon=True).start()
            except TimeoutError:
                pass
    socket_path.unlink(missing_ok=True)
    raise SystemExit(completion_code())

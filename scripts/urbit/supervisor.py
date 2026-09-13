#!/usr/bin/env python3
"""Private fixture administrator. Never expose this socket or Lens as an app API."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import traceback
import urllib.request

from digests import sha, source_sha, tree_sha
from conn import assert_result, run_thread

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
EVIDENCE = []
LOADED_SOURCE_DIGEST = source_sha(Path('/code'))


def record(command, result):
    item = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'command': command, 'result': result}
    EVIDENCE.append(item)
    print(json.dumps(item), flush=True)


def dojo(ship, command, timeout=120):
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


def shutdown(ship):
    process = PROCESSES.get(ship)
    if process is None or process.poll() is not None:
        return
    # Pinned Vere king.c handles SIGTERM with u3_king_exit, including bootstrap.
    # Unlike Dojo input this remains available before Lens has started.
    process.terminate()
    process.wait(timeout=120)
    if process.returncode != 0:
        raise RuntimeError(f'{ship} exit was not clean: {process.returncode}')
    LOGS[ship].close()
    record('shutdown ' + ship, {'exit_code': process.returncode})


def all_stop():
    errors = []
    for ship in SHIPS:
        try:
            shutdown(ship)
        except Exception as error:
            errors.append(str(error))
    if errors:
        raise RuntimeError('; '.join(errors))


def copy_seed_to_live():
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
            PROGRESS.update(stage='ready', ready=True)
        except Exception as error:
            PROGRESS.update(stage='failed', error=str(error))
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
                result = {**PROGRESS, 'ships': {s: {'pid': p.pid, 'exit': p.poll()} for s, p in PROCESSES.items()}}
            elif request == {'op': 'stop'}:
                STOP_REQUESTED.set()
                with MUTEX:
                    all_stop()
                    result = {'stopped': True}
                    STOP.set()
            elif request == {'op': 'test'}:
                with MUTEX:
                    if not PROGRESS['ready']:
                        raise RuntimeError('Fixture not ready: ' + str(PROGRESS))
                    result = smoke_test()
            else:
                raise ValueError('Unknown control command')
            reply = {'ok': True, 'result': result}
        except Exception as error:
            reply = {'ok': False, 'error': str(error)}
        connection.sendall(json.dumps(reply).encode() + b'\n')


if __name__ == '__main__':
    os.umask(0o077)
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
        threading.Thread(target=initialize, daemon=True).start()
        while not STOP.is_set():
            try:
                connection, _ = server.accept()
                threading.Thread(target=handle, args=(connection,), daemon=True).start()
            except TimeoutError:
                pass
    socket_path.unlink(missing_ok=True)

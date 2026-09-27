#!/usr/bin/env python3
"""Disposable local native CI with separate immutable controller/candidate inputs.

This entry is trusted code. Run it from the reviewed controller checkout; never
invoke this file, a Makefile, or a workflow from an untrusted candidate checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
MAX_FILES, MAX_FILE, MAX_TREE = 512, 4 * 1024**2, 32 * 1024**2
MEMORY, TASKS, STATE_BYTES, TEMP_BYTES = 12 * 1024**3, 256, 8 * 1024**3, 512 * 1024**2
CONTROLLER_PATHS = ('scripts/ci', 'scripts/urbit', 'web/dev', 'specs/urbit',
                    'native', 'tests/urbit/native_gall_schedule', 'tests/urbit/skill_evaluation',
                    'web/toolchain/package-lock.json')
PRODUCT_APPS = {'app/stead-home.hoon', 'app/stead-identity.hoon'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*arguments, limit=MAX_FILE):
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_NO_REPLACE_OBJECTS': '1',
                   'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
    process = subprocess.Popen(['/usr/bin/git', '-C', str(ROOT), *arguments], env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    output = bytearray()
    deadline = time.monotonic() + 15
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                require(time.monotonic() < deadline, 'Git read deadline')
                if not selector.select(min(.1, max(0, deadline - time.monotonic()))):
                    continue
                raw = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(output)))
                if not raw:
                    break
                output.extend(raw)
                require(len(output) <= limit, 'Git output bound')
        require(process.wait(timeout=1) == 0, 'Git read failed')
        return bytes(output)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
        process.stdout.close()


def inventory(commit, prefixes):
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'Full immutable commit required')
    require(git('rev-parse', commit + '^{commit}').decode().strip() == commit, 'Commit identity differs')
    listing = git('ls-tree', '-r', '-z', commit, '--', *prefixes, limit=256 * 1024)
    require(len(listing) <= 256 * 1024, 'Git tree listing bound')
    files, total = {}, 0
    for entry in listing.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode('ascii').split()
        name = name.decode('ascii')
        parts = PurePosixPath(name)
        require(mode in ('100644', '100755') and kind == 'blob', 'Regular Git blobs only')
        require(not parts.is_absolute() and '..' not in parts.parts
                and re.fullmatch(r'[a-zA-Z0-9_./-]+', name), 'Unsafe input path')
        require(name not in files and len(files) < MAX_FILES, 'File inventory bound')
        size = int(git('cat-file', '-s', oid))
        require(0 <= size <= MAX_FILE and total + size <= MAX_TREE, 'Input byte bound')
        raw = git('cat-file', 'blob', oid)
        require(len(raw) == size, 'Git blob size changed')
        require(hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + raw).hexdigest() == oid, 'Git blob identity differs')
        files[name] = raw
        total += size
    require(files, 'Empty input tree')
    return files


def hashes(files):
    return {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(files.items())}


def materialize(files, destination):
    destination.mkdir(mode=0o700)
    for name, raw in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write(raw)


def compose(controller, candidate):
    prefix = 'native/core/desk/'
    expected = {name[len(prefix):] for name in controller if name.startswith(prefix)}
    product = {name for name in expected if name in PRODUCT_APPS or name.startswith(('lib/', 'web/'))
               or (name.startswith('mar/') and name not in {'mar/stead-control-1.hoon', 'mar/stead-fixture-1.hoon', 'mar/stead-observer-1.hoon'})}
    # The supported predecessor is trusted evidence, never a candidate rewrite.
    reserved = {'lib/stead-codec-v1.hoon', 'lib/stead-core-v1.hoon', 'lib/stead-git.hoon'}
    product -= reserved
    for name in reserved:
        require(prefix + name in candidate and candidate[prefix + name] == controller[prefix + name],
                'Candidate collision with trusted predecessor dependency: ' + name)
    assets = lambda name: re.fullmatch(r'web/stead/asset-[0-9a-f]{64}\.stead-asset', name) is not None
    selected = {}
    for name, raw in candidate.items():
        require(name.startswith(prefix), 'Candidate outside product root')
        relative = name[len(prefix):]
        if relative in product or assets(relative):
            selected[name] = raw
        else:
            require(name in controller and raw == controller[name], 'Candidate collision with trusted test/dependency: ' + relative)
    required = {prefix + name for name in product if not assets(name)}
    require(required <= selected.keys(), 'Missing candidate product file')
    combined = {name: raw for name, raw in controller.items() if name.startswith('native/')
                and not (name.startswith(prefix) and (name[len(prefix):] in product or assets(name[len(prefix):])))}
    require(not combined.keys() & selected.keys(), 'Trusted overlay collision')
    combined.update(selected)
    probe = 'native/core/desk/gen/stead-ci-migration-probe.hoon'
    require(probe not in combined, 'Reserved CI migration probe collision')
    combined[probe] = controller['scripts/ci/migration.hoon']
    for source, destination in (
        ('missing.hoon', 'controls/stead-ci-missing.hoon'),
        ('compiler.hoon', 'controls/stead-ci-compiler.hoon'),
        ('delay.hoon', 'ted/stead-ci-delay.hoon')):
        target = prefix + destination
        require(target not in combined, 'Reserved CI negative control collision')
        combined[target] = controller['scripts/ci/controls/' + source]
    return combined, selected


def readback(unit):
    output = subprocess.check_output(['/usr/bin/systemctl', '--user', 'show', unit,
        '--property=LoadState,ActiveState,ControlGroup,MemoryMax,MemorySwapMax,TasksMax'], text=True, timeout=3)
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def private_runtime():
    path = ROOT / '.runtime'
    for parent in [*reversed(path.parents), path]:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.getuid())
                and not info.st_mode & 0o022, 'Unsafe coordinator ancestor')
    info = path.stat()
    require(info.st_uid == os.getuid() and not info.st_mode & 0o077, 'Runtime root must be owned and private')
    return path


def clean_environment():
    runtime = Path('/run/user') / str(os.getuid())
    info = runtime.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
            and not info.st_mode & 0o077, 'Private user runtime required')
    # Keep no caller-controlled Python, Node, dynamic-loader or Git settings.
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', LANG='C.UTF-8', TERM='dumb',
        XDG_RUNTIME_DIR=str(runtime), PYTHONNOUSERSITE='1',
        PYTHONDONTWRITEBYTECODE='1', PYTHONSAFEPATH='1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller', required=True)
    parser.add_argument('--candidate', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    clean_environment()
    private_runtime()
    common = Path(git('rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip())
    require(common.name == '.git' and common.parent == ROOT, 'Run CI from the primary coordinator checkout, not a linked controller worktree')
    controller = inventory(args.controller, CONTROLLER_PATHS)
    # Verify the host code before importing it. Candidate helpers are never used.
    for name, raw in controller.items():
        if name.startswith(('scripts/ci/', 'scripts/urbit/')):
            current = ROOT / name
            require(not current.is_symlink() and current.read_bytes() == raw, 'Controller checkout differs: ' + name)
    require('scripts/ci/local.py' in controller and 'scripts/ci/worker.py' in controller, 'Incomplete reviewed CI controller')
    candidate = inventory(args.candidate, ('native/core/desk',))
    combined, product = compose(controller, candidate)
    jobs = ROOT / '.runtime/local-ci'
    require(not jobs.is_symlink(), 'Redirected CI root')
    jobs.mkdir(mode=0o700, exist_ok=True)
    require(jobs.stat().st_uid == os.getuid() and not jobs.stat().st_mode & 0o077, 'CI root must be owned and private')
    job = Path(tempfile.mkdtemp(prefix='job-', dir=jobs))
    materialize(controller, job / 'controller')
    materialize(combined, job / 'composed')
    # Import only captured regular .py sources. -I/-B at the entry point avoids
    # PYTHONPATH/site customization; this fresh tree contains no bytecode cache.
    sys.path[:0] = [str(job / 'controller/scripts/ci'), str(job / 'controller/scripts/urbit')]
    import execution_policy
    import toolchain
    toolchain.CACHE = ROOT / '.runtime'
    # toolchain.ROOT and LOCK_PATH remain within the captured controller tree.
    pins = toolchain.verify()
    import digests
    import team_check
    provenance = {'format': 'stead.local-ci-inputs/1', 'controller_commit': args.controller,
                  'candidate_commit': args.candidate, 'controller_files': hashes(controller),
                  'runtime_binary_sha256': pins['runtime']['binary_sha256'],
                  'candidate_product_files': hashes(product), 'composed_files': hashes(combined),
                  'host_network_namespace': os.readlink('/proc/self/ns/net'),
                  'expected_native_inputs': {
                      'native': digests.tree_sha(job / 'composed/native/core/desk'),
                      'runner': team_check.closure(),
                      'harness': digests.source_sha(job / 'controller/scripts/urbit'),
                      'ingress': digests.tree_sha(job / 'controller/web/dev'),
                      'toolchain': digests.sha(job / 'controller/specs/urbit/toolchain.lock.json'),
                      'native_unit_inventory': digests.sha(job / 'controller/specs/urbit/phase2-pure-units.json')}}
    execution_policy.write_json(job / 'inputs.json', provenance)
    stopped = threading.Event()
    admission = {'status': 'pending'}
    thread = None
    group = ''
    ownership = {}

    def factory(control, run_id):
        nonlocal thread, group
        unit = 'stead-native-' + run_id + '.scope'
        ownership.update(unit=unit, run_id=run_id, control=control)
        def admit():
            nonlocal group
            try:
                deadline = time.monotonic() + 10
                while not (control / 'scope.json').exists():
                    require(time.monotonic() < deadline and not stopped.is_set(), 'CI admission deadline')
                    time.sleep(.05)
                proof = execution_policy.read_json(control / 'scope.json')
                require(proof['unit'] == unit, 'Foreign resource proof')
                state = readback(unit)
                group = state.get('ControlGroup', '')
                require(state.get('ActiveState') == 'active' and group.startswith('/user.slice/')
                        and Path(group).name == unit and '..' not in Path(group).parts
                        and proof.get('cgroup') == group, 'Foreign cgroup')
                subprocess.run(['/usr/bin/systemctl', '--user', 'set-property', '--runtime', unit,
                    'MemoryMax=' + str(MEMORY), 'MemorySwapMax=0', 'TasksMax=' + str(TASKS)],
                    check=True, capture_output=True, timeout=5)
                state = readback(unit)
                cg = Path('/sys/fs/cgroup') / group.lstrip('/')
                require(state.get('ActiveState') == 'active' and state.get('ControlGroup') == group
                        and state.get('MemoryMax') == str(MEMORY) and state.get('MemorySwapMax') == '0'
                        and state.get('TasksMax') == str(TASKS), 'CI resource property mismatch')
                actual = {name: (cg / name).read_text().strip() for name in ('memory.max', 'memory.swap.max', 'pids.max', 'cpu.max')}
                require(actual == {'memory.max': str(MEMORY), 'memory.swap.max': '0', 'pids.max': str(TASKS), 'cpu.max': '5000 10000'}, 'CI cgroup limits differ')
                execution_policy.require_lease(control, run_id=run_id)
                require(not stopped.is_set(), 'CI cancelled before admission')
                admission.update(status='admitted', run_id=run_id, unit=unit, cgroup=group, limits=actual)
                execution_policy.write_json(control / 'ci-admission.json', admission)
            except Exception as error:
                admission.update(status='refused', error=type(error).__name__ + ': ' + str(error))
                stopped.set()
        thread = threading.Thread(target=admit, daemon=True)
        thread.start()
        base = job / 'controller'
        command = ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--uid', '0', '--gid', '0',
                   '--cap-add', 'CAP_NET_ADMIN', '--cap-add', 'CAP_SETPCAP', '--ro-bind', '/usr', '/usr']
        for name in ('bin', 'sbin', 'lib', 'lib64'):
            path = Path('/') / name
            command += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
        command += ['--proc', '/proc', '--dev', '/dev', '--dir', '/etc',
                    '--size', str(TEMP_BYTES), '--tmpfs', '/tmp', '--size', str(STATE_BYTES), '--tmpfs', '/state']
        mounts = [(base / 'scripts/urbit', '/code'), (base / 'scripts/ci', '/ci'),
                  (base / 'web/dev', '/web-dev'), (base / 'specs/urbit', '/specs'),
                  (job / 'composed/native', '/native'), (base / 'specs/urbit/toolchain.lock.json', '/toolchain.json'),
                  (ROOT / '.runtime' / pins['runtime']['binary'], '/runtime/' + pins['runtime']['binary']),
                  (ROOT / '.runtime/downloads' / pins['boot_artifact']['archive'], '/runtime/downloads/' + pins['boot_artifact']['archive']),
                  (ROOT / '.runtime' / pins['kernel']['directory'], '/kernel'),
                  (job / 'inputs.json', '/ci-inputs.json'), (control, '/execution')]
        for source, target in mounts:
            command += ['--ro-bind', str(source), target]
        command += ['--chdir', '/state', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
                    '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'TERM', 'dumb',
                    '--setenv', 'STEAD_EXECUTION_ID', run_id,
                    '--', '/usr/bin/python3', '-B', '/ci/worker.py']
        return command

    # Bounded collector: never let a failing runtime fill the host filesystem.
    read_fd, write_fd = os.pipe()
    captured = bytearray()
    collection = {'overflow': False, 'error': None}
    def collect():
        try:
            with os.fdopen(read_fd, 'rb') as source:
                while chunk := source.read(65536):
                    if len(captured) + len(chunk) <= MAX_TREE:
                        captured.extend(chunk)
                    else:
                        collection['overflow'] = True
                        stopped.set()
        except Exception as error:
            collection['error'] = type(error).__name__
            stopped.set()
    reader = threading.Thread(target=collect, daemon=True)
    reader.start()
    result = {'classification': 'local-disposable-native-ci', 'status': 'fail', 'qualifies_phase': False,
              'admission': admission, 'collector': collection, 'errors': [],
              'cleanup': {'verified': False},
              'controller_commit': args.controller, 'candidate_commit': args.candidate}
    guard = None
    try:
        with os.fdopen(write_fd, 'wb') as console:
            guard = execution_policy.run_guarded(factory, root=ROOT, label='local-ci',
                policy=execution_policy.policy_from_limits(json.loads(controller['specs/urbit/urgit-candidate.lock.json'])['limits']),
                timeout=7200, console=console, stop_requested=stopped.is_set)
        result['guard_report'] = guard['run_directory'] + '/report.json'
    except BaseException as error:
        result['errors'].append(type(error).__name__ + ': ' + str(error)[:2000])
    finally:
        stopped.set()
        # Stop only the unpredictable unit created by this invocation. Missing
        # readback is uncertainty, never inferred successful cleanup.
        try:
            if thread:
                thread.join(timeout=12)
                require(not thread.is_alive(), 'CI admission thread still active')
        except BaseException as error:
            result['errors'].append('Admission finalization: ' + type(error).__name__ + ': ' + str(error)[:2000])
        try:
            if ownership:
                unit = ownership['unit']
                try:
                    state = readback(unit)
                except Exception as error:
                    state = {}
                    result['errors'].append('Initial cleanup readback: ' + type(error).__name__)
                if state.get('ActiveState') not in ('inactive', 'failed'):
                    for signum in (signal.SIGTERM, signal.SIGKILL):
                        try:
                            execution_policy.signal_owned_scope(unit, signum)
                        except Exception as error:
                            result['errors'].append('Owned scope signal: ' + type(error).__name__)
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline:
                            try:
                                state = readback(unit)
                            except Exception:
                                state = {}
                            if state.get('ActiveState') in ('inactive', 'failed'):
                                break
                            time.sleep(.1)
                        if state.get('ActiveState') in ('inactive', 'failed'):
                            break
                observed_group = state.get('ControlGroup') or group
                require(state.get('ActiveState') in ('inactive', 'failed'), 'Owned CI unit remains active')
                # An unloaded unit is observed absence; an active unit with an
                # unknown cgroup is never called empty.
                empty = state.get('LoadState') == 'not-found'
                if observed_group:
                    require(observed_group.startswith('/user.slice/') and Path(observed_group).name == unit
                            and '..' not in Path(observed_group).parts, 'Unexpected cleanup cgroup')
                    events = Path('/sys/fs/cgroup') / observed_group.lstrip('/') / 'cgroup.events'
                    empty = not events.exists() or 'populated 0' in events.read_text().splitlines()
                require(empty, 'Owned CI cgroup not proven empty')
                result['cleanup'] = {'verified': True, 'scope': unit, 'empty': empty,
                                     'state': state.get('ActiveState'), 'load': state.get('LoadState')}
            else:
                require(guard is not None and guard['launched'] is False, 'Unknown guard launch outcome')
                result['cleanup'] = {'verified': True, 'not_launched': True}
        except BaseException as error:
            result['errors'].append('Cleanup: ' + type(error).__name__ + ': ' + str(error)[:2000])
        reader.join(timeout=5)
        if reader.is_alive():
            result['errors'].append('CI output collector did not terminate')
        try:
            (job / 'console.log').write_bytes(captured)
            if (guard and guard['status'] == 'completed' and admission['status'] == 'admitted'
                    and result['cleanup']['verified'] and not result['errors']
                    and not collection['overflow'] and collection['error'] is None):
                from worker_result import verify
                result['worker'] = verify(bytes(captured), provenance, run_id=guard['run_id'],
                    inventory=json.loads(controller['specs/urbit/phase2-pure-units.json']))
                require(result['worker']['admission'] == admission, 'Worker admission differs from host')
                result['status'] = 'pass'
        except BaseException as error:
            result['errors'].append('Evidence: ' + type(error).__name__ + ': ' + str(error)[:2000])
            result['status'] = 'fail'
        execution_policy.write_json(job / 'report.json', result)
    print(json.dumps({'status': result['status'], 'evidence': str(job)}))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    require(sys.flags.isolated and sys.dont_write_bytecode, 'Invoke with python3 -I -B')
    raise SystemExit(main())

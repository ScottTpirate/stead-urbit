#!/usr/bin/env python3
"""Guarded clean-fake desk install check; no preserved pier or live identity.

This optional, potentially long native check compiles/loads one verified role on
a fresh isolated fake. It does not configure a company, test upgrades, expose a
browser, publish a release, or qualify M4. The common native lock/thermal guard
owns every native process. No archive is unpacked before offline verification.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time

INSIDE = os.environ.get('STEAD_RELEASE_INSTALL_CHILD') == '1'
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = ['/helpers', '/support'] if INSIDE else [str(ROOT / 'scripts/urbit'), str(ROOT / 'scripts/sdk_native')]
import execution_policy
from native import Native, inventory
import core_conn

DESK = 'release-test'
HELPERS = ('execution_policy.py', 'core_conn.py', 'conn.py', 'owned_child.py')
# This precise audited controller can fail in proof() only after a fresh fake
# boot and before any desk mutation. Other failures need a fresh run or review.
CLEAN_RETRY_CONTROLLER = '744861aef3516ddd0e9fbaae87594c0b21a0a2b5f240e10e3220313188f7664d'
CLEAN_RETRY_NATIVE = '44018860a029a79b32866e532241571d8b9483f86d2893a7226d7bd34424f5a1'
PREINSTALL_CHECKS = ['private-network-and-filesystem', 'exact-public-package-bytes',
                     'exact-controller-and-helper-bytes']


def checkpoint_tree(pier, copy_to=None):
    """Bounded, owned, no-follow regular tree fingerprint and optional new copy."""
    files, directories, total = {}, [], 0
    def visit(source, target, prefix=''):
        nonlocal total
        info = os.fstat(source)
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError('Checkpoint directory is not owned and protected')
        for name in sorted(os.listdir(source)):
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
                raise ValueError('Checkpoint path grammar')
            relative = prefix + name
            info = os.stat(name, dir_fd=source, follow_symlinks=False)
            if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                raise ValueError('Checkpoint has redirect or special file')
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise ValueError('Checkpoint entry is not owned and protected')
            if stat.S_ISDIR(info.st_mode):
                directories.append(relative)
                if len(directories) > 4096:
                    raise ValueError('Checkpoint directory bound')
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source)
                output = None
                try:
                    if target is not None:
                        os.mkdir(name, 0o700, dir_fd=target)
                        output = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=target)
                    visit(child, output, relative + '/')
                finally:
                    os.close(child)
                    if output is not None:
                        os.close(output)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                if len(files) >= 8192 or info.st_size > 512 * 1024 * 1024:
                    raise ValueError('Checkpoint file bound')
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=source)
                output = None
                try:
                    before = os.fstat(descriptor)
                    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns):
                        raise ValueError('Checkpoint entry changed before read')
                    if target is not None:
                        output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=target)
                    sha, size = hashlib.sha256(), 0
                    while chunk := os.read(descriptor, 256 * 1024):
                        size += len(chunk)
                        total += len(chunk)
                        if size > info.st_size or total > 1024 * 1024 * 1024:
                            raise ValueError('Checkpoint total byte bound')
                        sha.update(chunk)
                        if output is not None:
                            remaining = memoryview(chunk)
                            while remaining:
                                remaining = remaining[os.write(output, remaining):]
                    after = os.fstat(descriptor)
                    if size != info.st_size or (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
                        raise ValueError('Checkpoint entry changed during read')
                    files[relative] = {'bytes': size, 'sha256': sha.hexdigest()}
                finally:
                    os.close(descriptor)
                    if output is not None:
                        os.close(output)
            else:
                raise ValueError('Checkpoint has redirect, hard link or special file')
    with execution_policy.directory_fd(pier) as source:
        if copy_to is None:
            visit(source, None)
        else:
            Path(copy_to).mkdir(mode=0o700)
            with execution_policy.directory_fd(copy_to) as target:
                visit(source, target)
    if '.urb' not in directories or not files or any(name == DESK or name.startswith(DESK + '/') for name in directories):
        raise ValueError('Checkpoint is not an uninstalled synthetic pier')
    body = json.dumps({'files': files, 'directories': directories}, sort_keys=True).encode()
    return {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': total, 'files': len(files)}


def retired_checkpoint_scope(run_id):
    if not re.fullmatch(r'[0-9a-f]{32}', run_id):
        raise ValueError('Checkpoint guard identity')
    result = subprocess.run(['/usr/bin/systemctl', '--user', 'show', 'stead-native-' + run_id + '.scope',
                             '--property=LoadState,ActiveState,ControlGroup'], capture_output=True, text=True, timeout=3)
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if (fields.get('LoadState') not in ('not-found', 'loaded') or fields.get('ActiveState') not in ('inactive', 'failed')
            or fields.get('ControlGroup') != ''):
        raise ValueError('Checkpoint guard scope has not retired')


def checked_clean_copy(prior_name, destination, artifact, lock, toolchain_path, expected_checkpoint):
    """Called only by run_guarded's factory while it holds the native lock."""
    import package_release as release
    if not isinstance(expected_checkpoint, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_checkpoint):
        raise ValueError('Explicit reviewed checkpoint digest required')
    if not re.fullmatch(r'\.runtime/release-install-[a-z0-9_]+', prior_name):
        raise ValueError('Retry requires an owned disposable release run path')
    prior = ROOT / prior_name
    with execution_policy.directory_fd(prior) as descriptor:
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Checkpoint run directory must be private and owned')
    read = execution_policy.read_json
    if read(prior / '.stead-disposable.json') != {'format': 1, 'purpose': 'fresh-offline-release-install-only'}:
        raise ValueError('Checkpoint must originate from a fresh release test')
    host, report = read(prior / 'host-report.json'), read(prior / 'work/report.json', 4 * 1024 * 1024)
    guard_path = Path(host.get('guard_report', ''))
    if guard_path.parent.parent != ROOT / '.runtime/execution-runs' or not re.fullmatch(r'release-install-[a-z0-9_]+', guard_path.parent.name) or guard_path.name != 'report.json':
        raise ValueError('Checkpoint guard path binding')
    guard = read(guard_path, 8 * 1024 * 1024)
    control = guard_path.parent / 'control'
    context = read(control / 'release-context.json', 1024 * 1024)
    commit = context.get('verifier_source_commit', '')
    if (release.source_identity(ROOT, commit) != commit or host.get('source_unchanged') is not True
            or host.get('evidence') != str(prior / 'work/report.json')
            or host.get('guard_status') != 'failed' or guard.get('status') != 'failed'
            or guard.get('exit_code') != 1 or guard.get('launched') is not True
            or guard.get('label') != 'release-install' or guard.get('run_directory') != str(guard_path.parent)
            or report.get('status') != 'fail' or report.get('verifier_source_commit') != commit
            or any(record.get('artifact_sha256') != artifact for record in (host, report, context))):
        raise ValueError('Checkpoint report/source/artifact binding')
    pins = context.get('sources', {})
    names = ['scripts/release_install.py', 'scripts/sdk_native/native.py', 'scripts/package_release.py', 'scripts/package_sdk.py']
    names += ['scripts/urbit/' + name for name in HELPERS]
    if (set(pins) != set(names) or pins['scripts/release_install.py'] != CLEAN_RETRY_CONTROLLER
            or pins['scripts/sdk_native/native.py'] != CLEAN_RETRY_NATIVE
            or any(release.digest(release.committed(ROOT, commit, name)) != pin for name, pin in pins.items())
            or guard.get('guard_sha256') != pins['scripts/urbit/execution_policy.py']):
        raise ValueError('Checkpoint controller was not the reviewed preinstall version')
    for group in ('package', 'controller', 'support', 'helpers'):
        if inventory(prior / group) != context.get(group):
            raise ValueError('Checkpoint public inputs changed')
    if (context['controller'] != {'release_install.py': CLEAN_RETRY_CONTROLLER}
            or context['support'] != {'native.py': CLEAN_RETRY_NATIVE}
            or context['helpers'] != {name: pins['scripts/urbit/' + name] for name in HELPERS}
            or inventory(prior / 'package') != inventory(destination.parent / 'package')
            or release.digest(release.committed(ROOT, commit, 'specs/urbit/toolchain.lock.json')) != release.digest(toolchain_path.read_bytes())):
        raise ValueError('Checkpoint package/helper/toolchain identity differs')
    if (report.get('checks') != [{'name': name, 'passed': True} for name in PREINSTALL_CHECKS]
            or report.get('commands') != [{'source': 'zuse', 'output': '%408\n'}, {'source': 'our', 'output': '~zod\n'}, {'source': '|mount %base', 'output': '>='}]
            or not re.fullmatch(r"FileNotFoundError: \[Errno 2\] No such file or directory: '/proc/[0-9]+/fd/[0-9]+'", report.get('error', ''))
            or report.get('cleanup') != {'clean': True, 'exit_code': 0, 'forced': False, 'premature': False, 'reaped': True}
            or any(key in report for key in ('boot', 'installed_files', 'watchdog_errors', 'cleanup_error'))):
        raise ValueError('Checkpoint did not stop cleanly at the exact preinstall proof failure')
    run_id = guard.get('run_id', '')
    lease = read(control / 'lease.json')
    if (guard.get('scope') != 'stead-native-' + run_id + '.scope'
            or read(guard_path.parent / '.stead-disposable.json') != {'format': 1, 'purpose': 'host native execution guard', 'run_id': run_id}
            or lease.get('state') != 'stopped' or lease.get('run_id') != run_id
            or lease.get('guard_sha256') != guard['guard_sha256']):
        raise ValueError('Checkpoint guard is not a stopped owned execution')
    argv = guard.get('argv', [])
    if 'bwrap' not in argv or argv[argv.index('bwrap'):] != sandbox_command(prior, control, run_id, lock, toolchain_path):
        raise ValueError('Checkpoint prior namespace/mount binding differs')
    retired_checkpoint_scope(run_id)
    pier = prior / 'work/zod'
    if (pier / '.vere.lock').exists() or (pier / '.vere.lock').is_symlink():
        raise ValueError('Checkpoint still has a runtime ownership lock')
    before = checkpoint_tree(pier)
    if before['sha256'] != expected_checkpoint:
        raise ValueError('Checkpoint differs from the explicitly reviewed digest')
    copied = checkpoint_tree(pier, destination / 'zod')
    if copied != before or checkpoint_tree(pier) != before or checkpoint_tree(destination / 'zod') != before:
        raise ValueError('Stopped checkpoint changed while copied; original remains preserved')
    retired_checkpoint_scope(run_id)
    return {'mode': 'resumed-clean-checkpoint', 'source_run': prior_name, 'prior_guard_run_id': run_id,
            'prior_guard_report_sha256': release.digest(guard_path.read_bytes()),
            'prior_report_sha256': release.digest((prior / 'work/report.json').read_bytes()),
            'prior_verifier_commit': commit, 'artifact_sha256': artifact, 'pier': before,
            'fresh_boot_acceptance': False}


class CleanCheckpointNative(Native):
    """Release-only extension; SDK qualification still requires a new pier."""
    def _check_pier(self):
        context = execution_policy.read_json('/execution/release-context.json', 1024 * 1024)
        retry = context.get('clean_checkpoint', {})
        if (self.ship != 'zod' or retry.get('mode') != 'resumed-clean-checkpoint'
                or retry.get('artifact_sha256') != context['artifact_sha256']
                or checkpoint_tree(self.pier) != retry.get('pier')):
            raise ValueError('Copied clean checkpoint binding differs before boot')

    def _arguments(self):
        return [self.binary, '-t', '-L', '--no-dock', '--loom', '31', '-b', '127.0.0.1',
                '-p', str(self.port), '--http-port', str(self.http_port), str(self.pier)]


def system_mounts():
    command = ['bwrap', '--unshare-all', '--new-session', '--die-with-parent', '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        if path.is_symlink():
            command += ['--symlink', os.readlink(path), str(path)]
        elif path.exists():
            command += ['--ro-bind', str(path), str(path)]
    return command + ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/etc']


def clay_readback(native, files, agent):
    """Raw Hoon/asset bytes and typed Kelvin/bill values are checked separately."""
    for name, digest in files.items():
        path = Path(name)
        route = '/' + '/'.join([*path.with_suffix('').parts, path.suffix[1:]])
        deadline = time.monotonic() + 60
        while native.dojo(f'=/  arc=arch  .^(arch %cy /={DESK}={route})  ?=(^ -.arc)').strip() != '%.y':
            native.check()
            if time.monotonic() > deadline:
                raise TimeoutError('Release Clay import absent: ' + name)
            time.sleep(.1)
        if name == 'sys.kelvin':
            expression = f'=(.^(* %cx /={DESK}=/sys/kelvin) [%zuse 408])'
        elif name == 'desk.bill':
            expression = f'=(.^(* %cx /={DESK}=/desk/bill) ~[%{agent}])'
        else:
            literal = core_conn.atom(bytes.fromhex(digest)[::-1])
            expression = (f'=/  raw=@t  .^(@t %cx /={DESK}={route})  '
                          f'=({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))')
        if native.dojo(expression).strip() != '%.y':
            raise ValueError('Release Clay content differs: ' + name)


def install_desk(native, agent, package=Path('/package/desk')):
    if agent not in ('stead-home', 'stead-identity'):
        raise ValueError('Only a verified Stead role may be installed')
    expected = inventory(package)
    native.dojo('|new-desk %' + DESK)
    native.dojo('|mount %' + DESK)
    mount = native.pier / DESK
    deadline = time.monotonic() + 30
    while not mount.is_dir():
        native.check()
        if time.monotonic() > deadline:
            raise TimeoutError('Fresh release desk mount absent')
        time.sleep(.1)
    # new-desk imports only its fixed standard marks/sys.kelvin. Those same
    # paths must be supplied by the package; no undeclared source survives.
    if not set(inventory(mount)) <= set(expected):
        raise ValueError('Fresh desk contains undeclared files')
    for hoon in (True, False):
        for name in expected:
            if name.endswith('.hoon') != hoon:
                continue
            target = mount / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package / name, target)
        native.dojo('|commit %' + DESK)
    if inventory(mount) != expected:
        raise ValueError('Release mount differs from candidate bytes')
    clay_readback(native, expected, agent)
    native.dojo('|install our %' + DESK)
    return expected


def wait_agent(native, agent, expected, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = native.dojo(f'.^(? %gu /={agent}=/$)').strip()
        if value not in ('%.y', '%.n'):
            raise ValueError('Native agent status was not a boolean')
        if value == ('%.y' if expected else '%.n'):
            return
        native.check()
        time.sleep(.25)
    raise TimeoutError('Packaged role did not reach its requested lifecycle state')


def inside():
    os.umask(0o077)
    stopped, cleaning, finished = threading.Event(), threading.Event(), threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopped.set())
    report = {'status': 'fail', 'classification': 'local-native-clean-fake-desk-install',
              'qualifies_phase': False, 'checks': [], 'configured_home': False,
              'upgrade_recovery': False, 'canary': False}
    native = None
    failures = []
    context = execution_policy.read_json('/execution/release-context.json', 1024 * 1024)
    manifest = execution_policy.read_json('/package/manifest.json')
    report.update(source_commit=manifest['source_commit'], role=manifest['role'],
                  artifact_sha256=context['artifact_sha256'], verifier_source_commit=context['verifier_source_commit'])

    def guard():
        if stopped.is_set() or failures:
            raise InterruptedError('Release install guard stopped')
        execution_policy.require_lease(run_id=os.environ['STEAD_EXECUTION_ID'], read_only=True)

    def checkpoint(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        execution_policy.write_json('/state/report.json', report)
        if not condition:
            raise ValueError('Release install check failed: ' + name)

    def watch():
        while not finished.wait(.25):
            try:
                guard()
                if not cleaning.is_set() and native is not None and native.process is not None and native.process.poll() is not None:
                    raise RuntimeError('Release native child exited unexpectedly')
            except BaseException as error:
                failures.append(type(error).__name__ + ': ' + str(error))
                if native is not None and native.process is not None and native.process.poll() is None:
                    try:
                        native.process.terminate()
                    except OSError:
                        pass
                return

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        guard()
        checkpoint('private-network-and-filesystem',
            all(os.readlink('/proc/self/ns/' + name) != prior for name, prior in context['host_namespaces'].items())
            and not any(Path(name).exists() for name in ('/native', '/home', '/piers', '/root/.gitconfig'))
            and bool(os.statvfs('/package').f_flag & os.ST_RDONLY))
        checkpoint('exact-public-package-bytes', inventory('/package') == context['package'])
        checkpoint('exact-controller-and-helper-bytes', inventory('/controller') == context['controller']
                   and inventory('/support') == context['support'] and inventory('/helpers') == context['helpers'])
        if context.get('clean_checkpoint'):
            report['clean_checkpoint'] = context['clean_checkpoint']
            report['boot_mode'] = 'resumed-clean-checkpoint'
            native = CleanCheckpointNative('zod', 31337, guard)
        else:
            report['boot_mode'] = 'fresh-fake'
            native = Native('zod', 31337, guard)
        report['boot'] = native.start()
        # No Stead code is installed on base or exposed via a private source mount.
        checkpoint('base-has-no-stead-source', native.dojo('=/  arc=arch  .^(arch %cy /=base=/lib/stead-team/hoon)  ?=(~ -.arc)').strip() == '%.y')
        agent = manifest['agents'][0]
        report['install_attempted'] = True
        execution_policy.write_json('/state/report.json', report)
        expected = install_desk(native, agent)
        report['installed_files'] = expected
        wait_agent(native, agent, True)
        checkpoint('selected-role-live-on-release-desk', native.dojo(f'.^(desk %gd /={agent}=/$)').strip() == '%' + DESK)
        native.dojo(f'|rein %{DESK} [%.n %{agent}]')
        wait_agent(native, agent, False, timeout=60)
        checkpoint('explicit-stop-observed', native.dojo(f'.^(? %gu /={agent}=/$)').strip() == '%.n')
        native.dojo(f'|rein %{DESK} [%.y %{agent}]')
        wait_agent(native, agent, True)
        checkpoint('supported-reload-observed', native.dojo(f'.^(? %gu /={agent}=/$)').strip() == '%.y')
        clay_readback(native, expected, agent)
        checkpoint('package-unchanged-after-load', inventory('/package') == context['package'])
        guard()
        report['status'] = 'pass'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        cleaning.set()
        if native is not None:
            try:
                report['cleanup'] = native.stop()
                if not report['cleanup']['clean']:
                    report['status'] = 'fail'
            except BaseException as error:
                report.update(status='fail', cleanup_error=type(error).__name__ + ': ' + str(error))
            report['commands'] = native.commands
        finished.set()
        watcher.join(timeout=2)
        if watcher.is_alive() or failures:
            report.update(status='fail', watchdog_errors=failures)
        execution_policy.write_json('/state/report.json', report)
    return 0 if report['status'] == 'pass' and report.get('cleanup', {}).get('clean') else 1


def sandbox_command(state, control, run_id, lock, toolchain_path):
    arguments = system_mounts()
    for source, destination in [(state / name, '/' + name) for name in ('package', 'controller', 'support', 'helpers')] + [
            (toolchain_path, '/toolchain.json'), (ROOT / '.runtime/bin', '/runtime/bin'),
            (ROOT / '.runtime/downloads', '/runtime/downloads'),
            (ROOT / '.runtime' / lock['kernel']['directory'], '/kernel'), (control, '/execution')]:
        arguments += ['--ro-bind', str(source), destination]
    arguments += ['--bind', str(state / 'work'), '/state', '--chdir', '/state', '--clearenv',
                  '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'LANG', 'C.UTF-8',
                  '--setenv', 'STEAD_RELEASE_INSTALL_CHILD', '1', '--setenv', 'STEAD_OWNED_EVALUATORS', '1',
                  '--setenv', 'STEAD_EXECUTION_ID', run_id,
                  '--', '/usr/bin/python3', '-B', '/controller/release_install.py', '_inside']
    return arguments


def run(archive, expected_sha256, target_path, retry_clean=None, retry_clean_sha256=None):
    import package_release
    import toolchain
    if (retry_clean is None) != (retry_clean_sha256 is None):
        raise ValueError('Retry requires both the prior run path and its reviewed checkpoint SHA-256')
    if os.getuid() == 0:
        raise ValueError('Release install requires a nonroot local caller')
    if package_release.git(ROOT, 'remote', 'get-url', '--push', 'origin').decode().strip() != 'https://github.com/ScottTpirate/stead-urbit.git':
        raise ValueError('Derivative origin required')
    execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy(), preflight=True)
    raw = package_release.read_bounded(ROOT, archive, package_release.MAX_ARCHIVE)
    target = json.loads(package_release.read_bounded(ROOT, target_path, 8192), object_pairs_hook=package_release.unique)
    manifest = package_release.verify_bytes(raw, expected_sha256=expected_sha256, target=target)
    lock = toolchain.verify()
    if package_release.digest(toolchain.LOCK_PATH.read_bytes()) != manifest['toolchain_sha256']:
        raise ValueError('Current verified runtime differs from release target')
    verifier_commit = package_release.source_identity(ROOT, 'HEAD')
    sources = ['scripts/release_install.py', 'scripts/sdk_native/native.py', 'scripts/package_release.py', 'scripts/package_sdk.py']
    sources += ['scripts/urbit/' + name for name in HELPERS]
    before = {name: package_release.digest(package_release.committed(ROOT, verifier_commit, name)) for name in sources}
    if any(package_release.digest((ROOT / name).read_bytes()) != pin for name, pin in before.items()):
        raise ValueError('Commit the exact release verifier and helper inputs first')
    state = Path(tempfile.mkdtemp(prefix='release-install-', dir=ROOT / '.runtime'))
    state.chmod(0o700)
    execution_policy.write_json(state / '.stead-disposable.json', {'format': 1, 'purpose': 'fresh-offline-release-install-only'})
    for name in ('package', 'controller', 'support', 'helpers', 'work'):
        (state / name).mkdir(mode=0o700)
    # Byte strings have already passed canonical-path, type, size and inventory
    # checks. Write only regular files beneath the newly created owned staging.
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as bundle:
        for item in bundle:
            destination = state / 'package' / item.name.removeprefix(package_release.PREFIX)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(bundle.extractfile(item).read(item.size))
    shutil.copyfile(__file__, state / 'controller/release_install.py')
    shutil.copyfile(ROOT / 'scripts/sdk_native/native.py', state / 'support/native.py')
    for name in HELPERS:
        shutil.copyfile(ROOT / 'scripts/urbit' / name, state / 'helpers' / name)
    context = {'artifact_sha256': expected_sha256, 'verifier_source_commit': verifier_commit,
               'sources': before, 'host_namespaces': {name: os.readlink('/proc/self/ns/' + name) for name in ('net', 'pid', 'mnt', 'user')}}
    context.update({name: inventory(state / name) for name in ('package', 'controller', 'support', 'helpers')})

    def command(control, run_id):
        if retry_clean is not None:
            context['clean_checkpoint'] = checked_clean_copy(retry_clean, state / 'work', expected_sha256, lock, toolchain.LOCK_PATH, retry_clean_sha256)
            execution_policy.write_json(state / 'clean-checkpoint.json', context['clean_checkpoint'])
        execution_policy.write_json(control / 'release-context.json', context)
        # No writable /state alias reaches candidate, controller or helpers.
        return sandbox_command(state, control, run_id, lock, toolchain.LOCK_PATH)

    guard = execution_policy.run_guarded(command, root=ROOT, label='release-install', timeout=3600)
    unchanged = all(package_release.digest((ROOT / name).read_bytes()) == pin for name, pin in before.items())
    result = {'classification': 'local-native-clean-fake-desk-install', 'qualifies_phase': False,
              'guard_status': guard['status'], 'guard_report': guard['run_directory'] + '/report.json',
              'source_unchanged': unchanged, 'evidence': str(state / 'work/report.json'), 'artifact_sha256': expected_sha256,
              'boot_mode': 'resumed-clean-checkpoint' if retry_clean is not None else 'fresh-fake'}
    execution_policy.write_json(state / 'host-report.json', result)
    print(json.dumps(result), flush=True)
    if guard['status'] != 'completed' or not unchanged:
        raise RuntimeError('Release install guard/source checks did not complete cleanly')
    report = execution_policy.read_json(state / 'work/report.json', 4 * 1024 * 1024)
    if report.get('status') != 'pass' or not report.get('checks') or not all(row.get('passed') is True for row in report['checks']):
        raise RuntimeError('Native release install did not pass its bounded checks')
    return result


if __name__ == '__main__':
    if INSIDE:
        raise SystemExit(inside())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--retry-clean', help='Exact prior .runtime/release-install-* run; only reviewed preinstall proof failures qualify')
    parser.add_argument('--retry-clean-sha256', help='Explicit independently reviewed stopped checkpoint tree digest')
    args = parser.parse_args()
    try:
        run(args.archive, args.sha256, args.target, args.retry_clean, args.retry_clean_sha256)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Release install failed: ' + str(error) + '\n')

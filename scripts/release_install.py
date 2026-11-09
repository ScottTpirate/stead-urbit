#!/usr/bin/env python3
"""Guarded clean-fake desk install check; no preserved pier or live identity.

This optional, potentially long native check compiles/loads one verified role on
a fresh isolated fake. It does not configure a company, test upgrades, expose a
browser, publish a release, or qualify M4. The common native lock/thermal guard
owns every native process. No archive is unpacked before offline verification.
"""
from __future__ import annotations
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import signal
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
        native = Native('zod', 31337, guard)
        report['boot'] = native.start()
        # No Stead code is installed on base or exposed via a private source mount.
        checkpoint('base-has-no-stead-source', native.dojo('=/  arc=arch  .^(arch %cy /=base=/lib/stead-team/hoon)  ?=(~ -.arc)').strip() == '%.y')
        agent = manifest['agents'][0]
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


def run(archive, expected_sha256, target_path):
    import package_release
    import toolchain
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
        execution_policy.write_json(control / 'release-context.json', context)
        # No writable /state alias reaches candidate, controller or helpers.
        return sandbox_command(state, control, run_id, lock, toolchain.LOCK_PATH)

    guard = execution_policy.run_guarded(command, root=ROOT, label='release-install', timeout=3600)
    unchanged = all(package_release.digest((ROOT / name).read_bytes()) == pin for name, pin in before.items())
    result = {'classification': 'local-native-clean-fake-desk-install', 'qualifies_phase': False,
              'guard_status': guard['status'], 'guard_report': guard['run_directory'] + '/report.json',
              'source_unchanged': unchanged, 'evidence': str(state / 'work/report.json'), 'artifact_sha256': expected_sha256}
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
    args = parser.parse_args()
    try:
        run(args.archive, args.sha256, args.target)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Release install failed: ' + str(error) + '\n')

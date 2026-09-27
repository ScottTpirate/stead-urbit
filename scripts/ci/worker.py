"""Trusted disposable worker. Only this controller writes its final evidence."""
from __future__ import annotations

import fcntl
import errno
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time

sys.path[:0] = ['/code', '/ci']
import execution_policy
from digests import sha, source_inventory, tree_sha
from worker_result import PREFIX, canonical


def require(condition, message):
    if not condition:
        raise ValueError(message)


def admission(provider=None):
    deadline = time.monotonic() + 15
    while not Path('/execution/ci-admission.json').exists():
        provider.require() if provider is not None else execution_policy.require_lease(read_only=True)
        require(time.monotonic() < deadline, 'CI resource admission absent')
        time.sleep(.05)
    value = execution_policy.read_json('/execution/ci-admission.json')
    require(value['status'] == 'admitted' and value['run_id'] == os.environ['STEAD_EXECUTION_ID'], 'CI admission identity')
    return value


def mounted_inputs(inputs):
    mounts = {'scripts/urbit': '/code', 'scripts/ci': '/ci', 'specs/urbit': '/specs', 'web/dev': '/web-dev'}
    observed = {}
    for prefix, mount in mounts.items():
        actual = source_inventory(Path(mount), ignore_python_cache=False)
        expected = {name[len(prefix) + 1:]: item['sha256'] for name, item in inputs['controller_files'].items()
                    if name.startswith(prefix + '/')}
        require(actual == expected, 'Controller mount differs: ' + prefix)
        require(os.statvfs(mount).f_flag & os.ST_RDONLY, 'Writable controller mount')
        observed[prefix] = actual
    actual = source_inventory(Path('/native'), ignore_python_cache=False)
    require(actual == {name.removeprefix('native/'): item['sha256'] for name, item in inputs['composed_files'].items()}, 'Composed native mount differs')
    require(os.statvfs('/native').f_flag & os.ST_RDONLY, 'Writable product mount')
    observed['native'] = actual
    return hashlib.sha256(canonical(observed)).hexdigest()


def isolation(inputs):
    require(os.readlink('/proc/self/ns/net') != inputs['host_network_namespace'], 'Host network namespace exposed')
    require(not any(Path(path).exists() for path in ('/home', '/run/user', '/root/.ssh', '/var/run/docker.sock')), 'Unexpected host mount')
    require(list(Path('/state').iterdir()) == [], 'CI requires a fresh empty state volume')
    interfaces = json.loads(subprocess.check_output(['/usr/bin/ip', '-j', 'address'], text=True, timeout=3))
    require({item['ifname'] for item in interfaces} == {'lo'}, 'External network interface')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as channel:
        channel.settimeout(.2)
        try:
            channel.connect(('192.0.2.1', 9))
        except OSError as error:
            require(error.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH), 'External route observation failed: ' + str(error.errno))
        else:
            raise ValueError('External network route exists')
    subprocess.run(['/usr/bin/ip', 'link', 'set', 'lo', 'up'], check=True, timeout=3)
    return {'private_network': True, 'host_credentials_absent': True, 'fresh_state': True, 'external_route_absent': True}


def fresh_seeds(host):
    """Boot each pin from nothing, with no capabilities and an owned parent."""
    import owned_child
    launcher = owned_child.ChildLauncher()
    host.LIVE.mkdir(mode=0o700)
    try:
        for index, ship in enumerate(host.SHIPS):
            host.execution_check()
            arguments = ['/runtime/' + host.LOCK['runtime']['binary'], '-t', '-L', '--no-dock',
                '--loom', '31', '-b', '127.0.0.1', '--http-port', str(18080 + index),
                '-F', ship, '-B', '/runtime/downloads/' + host.LOCK['boot_artifact']['archive'],
                '-A', '/kernel/pkg/arvo', '-c', str(host.LIVE / ship)]
            log = (host.STATE / 'logs' / (ship + '.log')).open('ab')
            host.LOGS[ship] = log
            child = launcher.spawn(arguments, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                close_fds=True, pass_fds=(host.gate.fileno(),))
            host.PROCESSES[ship] = child
            host.record('CI fresh boot ' + ship, {'argv': arguments, 'pid': child.pid})
            boot_started = time.monotonic()
            progress_done = threading.Event()
            def progress():
                while not progress_done.wait(30):
                    host.record('CI fresh boot progress', {'ship': ship, 'pid': child.pid,
                        'elapsed_seconds': round(time.monotonic() - boot_started, 3),
                        'log_bytes': os.fstat(log.fileno()).st_size})
            progress_thread = threading.Thread(target=progress, daemon=True)
            progress_thread.start()
            try:
                host.wait_ready(ship)
            finally:
                progress_done.set()
                progress_thread.join(timeout=2)
                require(not progress_thread.is_alive(), 'Fresh boot progress thread did not finish')
            state = dict(line.split(':', 1) for line in Path('/proc', str(child.pid), 'status').read_text().splitlines() if ':' in line)
            require(all(int(state[name].strip(), 16) == 0 for name in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb'))
                    and state['NoNewPrivs'].strip() == '1', 'Fresh runtime kept privileges')
            host.dojo(ship, '|mount %base')
            deadline = time.monotonic() + 60
            while not (host.LIVE / ship / 'base').is_dir():
                host.execution_check()
                require(time.monotonic() < deadline, 'Fresh base mount absent')
                time.sleep(.2)
        host.all_stop()
        host.execution_check()
        host.SEED.mkdir(mode=0o700)
        manifest = {'format': 1, 'toolchain_sha256': sha('/toolchain.json'), 'ships': {}}
        for ship in host.SHIPS:
            shutil.copytree(host.LIVE / ship, host.SEED / ship, symlinks=True)
            manifest['ships'][ship] = tree_sha(host.SEED / ship)
        execution_policy.write_json(host.SEED / 'manifest.json', manifest)
        return manifest
    finally:
        host.all_stop()
        launcher.close()


def wait_start_temperature(host, hosted=False):
    if hosted:
        host.execution_check(preflight=True)
        return
    deadline = time.monotonic() + 300
    while True:
        lease = host.execution_check()
        if max(lease['sample']['readings_c'].values()) <= lease['policy']['start_c']:
            return
        require(time.monotonic() < deadline, 'CI could not cool before native test admission')
        time.sleep(1)


def main(*, hosted=False):
    os.umask(0o077)
    os.environ['STEAD_CONFIGURED'] = '1'
    inputs = execution_policy.read_json('/ci-inputs.json', maximum=1024 * 1024)
    result = {'format': 'stead.local-ci-worker/1', 'status': 'fail',
              'inputs_sha256': hashlib.sha256(canonical(inputs)).hexdigest(),
              'run_id': os.environ['STEAD_EXECUTION_ID'], 'cleanup': False}
    host = None
    watcher = None
    try:
        provider = None
        if hosted:
            from hosted_lease import HostedProvider
            provider = HostedProvider()
        result['admission'] = admission(provider)
        result['mounts_before'] = mounted_inputs(inputs)
        result['isolation'] = isolation(inputs)
        pins = json.loads(Path('/toolchain.json').read_text())
        import negative
        negative.runtime_pin(Path('/runtime') / pins['runtime']['binary'], pins['runtime']['binary_sha256'])
        negative.runtime_pin(Path('/runtime/downloads') / pins['boot_artifact']['archive'], pins['boot_artifact']['sha256'])
        require(tree_sha(Path('/kernel'), source_links=True) == pins['kernel']['source_tree_sha256'], 'Kernel cache poisoned')
        import supervisor as host
        if provider is not None:
            host.select_execution_provider(provider)
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: host.STOP_REQUESTED.set())
        Path('/state/logs').mkdir(mode=0o700)
        host.gate = Path('/state/lifecycle.lock').open('x+')
        fcntl.flock(host.gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
        watcher = threading.Thread(target=host.execution_watch, daemon=True)
        watcher.start()
        # Fresh -F boot for each distinct identity; no host pier or seed enters.
        result['fresh_seeds'] = fresh_seeds(host)
        result['filesystem_controls'] = negative.seed_and_cache(host, pins)
        host.TEAM = host.team_lifecycle.TeamLifecycle(Path('/state/ingress') / result['run_id'],
            inputs['host_network_namespace'], '/runtime/' + pins['runtime']['binary'],
            host.execution_check, host.peer_fence_failed, host.record)
        wait_start_temperature(host, hosted)
        with host.MUTEX:
            summary = host.guarded_result(host.team_check.run(vars(host)))
        report_path = Path('/state/logs') / Path(summary['evidence_file']).name
        result['native'] = execution_policy.read_json(report_path, maximum=4 * 1024 * 1024)
        require(summary['status'] == 'pass', 'Native team suite failed')
        observed = host.dojo('zod', '+stead-ci-migration-probe', timeout=180)
        result['migration'] = {'source_sha256': sha('/native/core/desk/gen/stead-ci-migration-probe.hoon'), 'output': observed}
        require(observed.strip() == '%stead-ci-supported-migration-pass', 'Supported predecessor migration failed')
        result['negative_controls'] = negative.native(host, result['native'])
        result['mounts_after'] = mounted_inputs(inputs)
        require(result['mounts_before'] == result['mounts_after'], 'CI input changed during execution')
        host.execution_check()
        result['status'] = 'pass'
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)[:2000]
        # Failures still destroy the owned namespace; retain bounded raw tails
        # privately before its temporary pier logs disappear. Never call a
        # truncated tail complete or export it without credential redaction.
        result['failure_logs'] = {}
        for ship in ('zod', 'bus', 'nec', 'bud'):
            log_path = Path('/state/logs') / (ship + '.log')
            try:
                descriptor = os.open(log_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                try:
                    info = os.fstat(descriptor)
                    require(stat.S_ISREG(info.st_mode), 'Native diagnostic log is not regular')
                    size = info.st_size
                    with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                        stream.seek(max(0, size - 262144))
                        tail = stream.read(min(size, 262144))
                    require(len(tail) == min(size, 262144), 'Native diagnostic log changed during capture')
                finally:
                    os.close(descriptor)
                result['failure_logs'][ship] = {'bytes_total': size, 'tail_offset': max(0, size - 262144),
                    'tail_sha256': hashlib.sha256(tail).hexdigest(), 'tail_hex': tail.hex(), 'truncated': size > len(tail)}
            except FileNotFoundError:
                result['failure_logs'][ship] = {'absent': True}
            except Exception as capture_error:
                result['failure_logs'][ship] = {'capture_error': type(capture_error).__name__}
    finally:
        if host is not None:
            host.NORMAL_STOP.set()
            host.STOP_REQUESTED.set()
            try:
                with host.MUTEX:
                    host.all_stop()
                if host.TEAM is not None:
                    host.TEAM.close()
                require(all(process.poll() == 0 for process in host.PROCESSES.values()), 'Unclean owned native exit')
                require(not host.FORCED_STOP.is_set() and not host.SHUTDOWN_FAILED.is_set(), 'Native lifetime interrupted')
                result['cleanup'] = True
            except BaseException as error:
                result.update(status='fail', cleanup_error=type(error).__name__ + ': ' + str(error)[:2000])
            finally:
                host.STOP.set()
                if watcher:
                    watcher.join(timeout=2)
                    if watcher.is_alive():
                        result.update(status='fail', cleanup=False)
                if hasattr(host, 'gate'):
                    host.gate.close()
        # Native stdout is confined to pier logs. Only trusted Python emits this
        # framed final result; no candidate file or exit code stands in for it.
        print(PREFIX + canonical(result).decode(), flush=True)
    return 0 if result['status'] == 'pass' and result['cleanup'] else 1


if __name__ == '__main__':
    require(sys.argv[1:] in ([], ['--hosted']), 'Unknown trusted worker profile')
    raise SystemExit(main(hosted=sys.argv[1:] == ['--hosted']))

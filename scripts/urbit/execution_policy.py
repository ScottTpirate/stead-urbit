#!/usr/bin/env python3
"""Host-owned thermal/resource admission for disposable native execution.

The guardian runs outside bwrap. Its control directory is read-only inside the
sandbox; monotonic heartbeat age proves recent reads, not sensor calibration.
No persistent system setting, arbitrary PID selection or unowned unit is used.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time


class GuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class Policy:
    start_c: float = 75
    stop_c: float = 90
    sample_seconds: float = 1
    stale_seconds: float = 3
    cooperative_seconds: float = 10
    terminate_seconds: float = 10
    kill_seconds: float = 5
    cpu_quota_us: int = 5000
    cpu_period_us: int = 10000

    def __post_init__(self):
        # Constructor/test injection cannot raise the existing thermal ceilings.
        if not (0 < self.start_c <= 75 and self.start_c < self.stop_c <= 90):
            raise GuardError('Thermal policy would weaken the reviewed ceilings')
        if not (0 < self.sample_seconds <= 1 and self.sample_seconds < self.stale_seconds <= 3):
            raise GuardError('Invalid fresh-sample policy')
        if any(not 0 <= value <= bound for value, bound in (
                (self.cooperative_seconds, 10), (self.terminate_seconds, 10), (self.kill_seconds, 5))):
            raise GuardError('Invalid bounded shutdown policy')
        if (self.cpu_quota_us, self.cpu_period_us) != (5000, 10000):
            raise GuardError('Only the reviewed transient 50 percent / 10 ms quota is supported')


def policy_from_limits(limits):
    return Policy(start_c=limits['start_temperature_c'], stop_c=limits['stop_temperature_c'])


@dataclass(frozen=True)
class Sample:
    started: float
    finished: float
    readings_c: dict
    cpu_sensors: tuple


CPU_SENSOR = re.compile(r'(?:x86_pkg_temp|TCPU|cpu-thermal|cpu_thermal|coretemp|k10temp)', re.I)
RUN_ID = re.compile(r'[0-9a-f]{32}')


def sample_temperatures(root=Path('/sys/class/thermal')):
    """Read every advertised thermal zone; dropping any malformed zone fails."""
    started = time.monotonic()
    zones = sorted(Path(root).glob('thermal_zone*'))
    if not zones:
        raise GuardError('Thermal sensors unavailable')
    readings, cpu = {}, []
    for zone in zones:
        try:
            label = (zone / 'type').read_text().strip()
            raw = (zone / 'temp').read_text().strip()
        except OSError as error:
            raise GuardError('Thermal sensor read failed: ' + zone.name) from error
        if not label or len(label) > 128 or not label.isprintable() or not re.fullmatch(r'-?[0-9]+', raw):
            raise GuardError('Malformed thermal sensor: ' + zone.name)
        name = zone.name + ':' + label
        if name in readings:
            raise GuardError('Duplicate thermal sensor')
        readings[name] = int(raw) / 1000
        if CPU_SENSOR.fullmatch(label):
            cpu.append(name)
    return Sample(started, time.monotonic(), readings, tuple(cpu))


def validate_sample(sample, policy, *, preflight=False, expected_inventory=None, now=None):
    now = time.monotonic() if now is None else now
    if (not isinstance(sample, Sample) or not isinstance(sample.readings_c, dict)
            or not sample.readings_c or not isinstance(sample.cpu_sensors, (tuple, list))):
        raise GuardError('Missing thermal sample')
    times = (sample.started, sample.finished, now)
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in times):
        raise GuardError('Invalid sample clock')
    if not (0 <= sample.started <= sample.finished <= now) or now - sample.started > policy.stale_seconds:
        raise GuardError('Stale, future or reversed thermal sample')
    if expected_inventory is not None and set(sample.readings_c) != set(expected_inventory):
        raise GuardError('Thermal sensor inventory changed')
    if (not sample.cpu_sensors or len(set(sample.cpu_sensors)) != len(sample.cpu_sensors)
            or any(name not in sample.readings_c or not CPU_SENSOR.fullmatch(name.split(':', 1)[-1])
                   for name in sample.cpu_sensors)):
        raise GuardError('CPU/package thermal evidence missing')
    for name, value in sample.readings_c.items():
        if (not isinstance(name, str) or not name or len(name) > 200
                or type(value) not in (int, float) or not math.isfinite(value) or not -40 <= value <= 150):
            raise GuardError('Invalid thermal value')
    hottest = max(sample.readings_c.values())
    if (preflight and hottest > policy.start_c) or (not preflight and hottest >= policy.stop_c):
        raise GuardError('Start temperature exceeded' if preflight else 'Thermal ceiling reached')
    return hottest


@contextmanager
def directory_fd(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise GuardError('Parent traversal in owned directory')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open('/', flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def write_json(path, value):
    """Host-only atomic output, anchored through no-follow directory handles."""
    path = Path(path)
    payload = (json.dumps(value, sort_keys=True) + '\n').encode()
    with directory_fd(path.parent) as parent:
        temporary = '.' + path.name + '.' + secrets.token_hex(12)
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(payload)
            os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass


def read_json(path, maximum=65536):
    path = Path(path)
    with directory_fd(path.parent) as parent:
        for attempt in range(3):
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1 or info.st_size > maximum:
                    raise GuardError('Control input must be bounded and singly linked')
                if info.st_nlink == 0:
                    # An atomic writer may retire this inode between open and
                    # fstat. Discard it and reopen the same anchored pathname;
                    # never validate or return bytes from the retired inode.
                    if attempt == 2:
                        raise GuardError('Control input replaced during every bounded read')
                    continue
                raw = os.read(descriptor, maximum + 1)
                if len(raw) > maximum:
                    raise GuardError('Oversized control input')
                break
            finally:
                os.close(descriptor)
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise GuardError('Duplicate control key')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


class HeavyRunLock:
    """One repo-wide native owner; never unlink a lock held by another process."""
    def __init__(self, path):
        self.path, self.descriptor = Path(path), None

    def __enter__(self):
        with directory_fd(self.path.parent) as parent:
            descriptor = os.open(self.path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
        try:
            info = os.fstat(descriptor)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                    or info.st_mode & 0o077):
                raise GuardError('Execution lock is not a private owned regular file')
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            os.close(descriptor)
            raise
        self.descriptor = descriptor
        return self

    def __exit__(self, *_):
        os.close(self.descriptor)
        self.descriptor = None


def require_lease(control=Path('/execution'), *, run_id=None, preflight=False, now=None, read_only=False):
    run_id = os.environ.get('STEAD_EXECUTION_ID') if run_id is None else run_id
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise GuardError('Missing guarded execution identity; restart through make start')
    if read_only and not os.statvfs(control).f_flag & os.ST_RDONLY:
        raise GuardError('Sandbox execution control is writable')
    with directory_fd(control) as parent:
        try:
            os.stat('STOP', dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise GuardError('Execution STOP is terminal')
    value = read_json(Path(control) / 'lease.json')
    if (not isinstance(value, dict) or value.get('format') != 1 or value.get('run_id') != run_id
            or value.get('state') != 'running'):
        raise GuardError('Execution lease stopped or belongs to another run')
    inventory = value.get('inventory')
    if (not isinstance(inventory, list) or not inventory
            or any(not isinstance(name, str) or not name for name in inventory)
            or len(set(inventory)) != len(inventory)):
        raise GuardError('Missing or ambiguous required thermal inventory')
    if (value.get('guard_sha256') != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or type(value.get('generation')) is not int or value['generation'] < 1):
        raise GuardError('Execution lease source/generation differs')
    policy_digest = hashlib.sha256(json.dumps(value['policy'], sort_keys=True).encode()).hexdigest()
    if value.get('policy_sha256') != policy_digest:
        raise GuardError('Execution lease policy digest differs')
    policy = Policy(**value['policy'])
    sample = Sample(**value['sample'])
    validate_sample(sample, policy, preflight=preflight, expected_inventory=value['inventory'], now=now)
    return value


def scope_proof(unit, cpu, policy, *, cgroup_root=Path('/sys/fs/cgroup'), proc=Path('/proc/self/cgroup')):
    if not re.fullmatch(r'stead-native-[0-9a-f]{32}\.scope', unit):
        raise GuardError('Unowned transient scope name')
    records = proc.read_text().splitlines()
    paths = [line[3:] for line in records if line.startswith('0::/')]
    if len(paths) != 1 or Path(paths[0]).name != unit or '..' in Path(paths[0]).parts:
        raise GuardError('Child did not enter its owned cgroup')
    group = cgroup_root / paths[0].lstrip('/')
    actual = (group / 'cpu.max').read_text().strip()
    if actual != f'{policy.cpu_quota_us} {policy.cpu_period_us}':
        raise GuardError('Transient CPU quota/period read-back differs')
    if os.sched_getaffinity(0) != {cpu}:
        raise GuardError('Owned child CPU affinity differs')
    return {'unit': unit, 'cgroup': paths[0], 'cpu_max': actual, 'cpu_affinity': [cpu]}


def scope_command(command, control, run_id, cpu, policy, descriptor):
    unit = 'stead-native-' + run_id + '.scope'
    info = os.fstat(descriptor)
    return ['/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--unit=' + unit,
            '--property=CPUQuota=50%', '--property=CPUQuotaPeriodSec=10ms',
            '/usr/bin/python3', str(Path(__file__).resolve()), '_scope', str(control), run_id,
            str(cpu), str(descriptor), str(info.st_dev), str(info.st_ino), '--', *command]


def signal_owned_scope(unit, signum):
    if not re.fullmatch(r'stead-native-[0-9a-f]{32}\.scope', unit):
        raise GuardError('Refusing to signal an unowned scope')
    result = subprocess.run(['/usr/bin/systemctl', '--user', 'kill', '--kill-whom=all',
                             '--signal=' + signal.Signals(signum).name, unit],
                            capture_output=True, timeout=3)
    return {'signal': signal.Signals(signum).name, 'returncode': result.returncode,
            'stderr': result.stderr.decode(errors='replace')[:2048]}


def run_guarded(command_factory, *, root, label, policy=None, timeout=7200,
                console=None, sampler=sample_temperatures, stop_requested=None):
    """Launch only after admission; return completed/failed, never native pass.

    command_factory(control, run_id) must mount control read-only and cannot
    expose a writable alias. The shared lock lasts until owned-scope cleanup.
    """
    policy = Policy() if policy is None else policy
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,40}', label) or not 0 < timeout <= 7200:
        raise GuardError('Invalid bounded execution request')
    root = Path(root)
    base = root / '.runtime'
    with directory_fd(root):
        base.mkdir(mode=0o700, exist_ok=True)
    with directory_fd(base):
        runs = base / 'execution-runs'
        runs.mkdir(mode=0o700, exist_ok=True)
    with directory_fd(runs):
        run = Path(tempfile.mkdtemp(prefix=label + '-', dir=runs))
    control = run / 'control'
    control.mkdir(mode=0o700)
    run_id = secrets.token_hex(16)
    unit = 'stead-native-' + run_id + '.scope'
    report = {'format': 1, 'run_id': run_id, 'label': label, 'status': 'failed',
              'policy': asdict(policy), 'run_directory': str(run), 'scope': unit,
              'guard_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'events': [], 'cleanup': [], 'exit_code': None, 'launched': False}
    write_json(run / '.stead-disposable.json', {'format': 1, 'purpose': 'host native execution guard', 'run_id': run_id})
    cancel = threading.Event()
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, lambda *_: cancel.set())
    process, reason, lease, generation = None, None, None, 0
    started = time.monotonic()
    def event(name, **details):
        row = {'event': name, 'elapsed_seconds': round(time.monotonic() - started, 3), **details}
        report['events'].append(row)
        with (run / 'events.jsonl').open('a') as output:
            output.write(json.dumps(row, sort_keys=True) + '\n')
    def publish(sample, state='running'):
        nonlocal lease, generation
        generation += 1
        lease = {'format': 1, 'run_id': run_id, 'state': state, 'policy': asdict(policy),
                 'inventory': list(initial.readings_c), 'sample': asdict(sample),
                 'guard_sha256': report['guard_sha256'], 'generation': generation,
                 'policy_sha256': hashlib.sha256(json.dumps(asdict(policy), sort_keys=True).encode()).hexdigest()}
        write_json(control / 'lease.json', lease)
    def stop_lease():
        # Cleanup must never depend on evidence or control storage still working.
        try:
            if lease is not None:
                write_json(control / 'lease.json', {**lease, 'state': 'stopped', 'reason': reason})
            write_json(control / 'STOP', {'reason': reason})
        except Exception as error:
            report['cleanup'].append({'control_write_error': type(error).__name__ + ': ' + str(error)})
    try:
        with HeavyRunLock(base / 'native-execution.lock') as owner:
            try:
                initial = sampler()
                event('preflight-sample', sample=asdict(initial))
                validate_sample(initial, policy, preflight=True)
                if cancel.is_set() or (stop_requested is not None and stop_requested()):
                    raise GuardError('Operator stop requested before launch')
                event('preflight-accepted', sample=asdict(initial))
                publish(initial)
                cpu = max(os.sched_getaffinity(0))
                command = command_factory(control, run_id)
                # A verified stopped-seed snapshot may take time. Re-admit at
                # the actual launch boundary; never launch on an aged sample.
                launch_sample = sampler()
                event('launch-sample', sample=asdict(launch_sample))
                validate_sample(launch_sample, policy, preflight=True,
                                expected_inventory=initial.readings_c)
                if cancel.is_set() or (stop_requested is not None and stop_requested()):
                    raise GuardError('Operator stop requested during launch preparation')
                publish(launch_sample)
                argv = scope_command(command, control, run_id, cpu, policy, owner.descriptor)
                report['argv'] = argv
                event('launch', cpu_affinity=[cpu])
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=console,
                                           stderr=subprocess.STDOUT, start_new_session=True,
                                           pass_fds=(owner.descriptor,))
                report['launched'] = True
                stop_at, term_sent, kill_sent = None, False, False
                while process.poll() is None:
                    try:
                        current = sampler()
                        event('sample', sample=asdict(current))
                        validate_sample(current, policy, expected_inventory=initial.readings_c)
                        publish(current, 'stopped' if reason else 'running')
                        if cancel.is_set() or (stop_requested is not None and stop_requested()):
                            raise GuardError('Operator stop requested')
                        if time.monotonic() - started > timeout:
                            raise GuardError('Execution deadline reached')
                    except Exception as error:
                        reason = reason or type(error).__name__ + ': ' + str(error)
                    if reason:
                        if stop_at is None:
                            stop_at = time.monotonic()
                            event('guard-stop', reason=reason)
                            stop_lease()
                        elapsed = time.monotonic() - stop_at
                        if elapsed >= policy.cooperative_seconds and not term_sent:
                            report['cleanup'].append(signal_owned_scope(unit, signal.SIGTERM))
                            term_sent = True
                        if elapsed >= policy.cooperative_seconds + policy.terminate_seconds and not kill_sent:
                            report['cleanup'].append(signal_owned_scope(unit, signal.SIGKILL))
                            kill_sent = True
                        if elapsed >= policy.cooperative_seconds + policy.terminate_seconds + policy.kill_seconds:
                            raise GuardError('Owned scope did not stop by cleanup deadline')
                    time.sleep(policy.sample_seconds)
                process.wait(timeout=1)
                report['exit_code'] = process.returncode
                if process.returncode != 0:
                    reason = reason or 'Owned sandbox exited unsuccessfully'
                if reason is None:
                    report['scope_proof'] = read_json(control / 'scope.json')
                    if report['scope_proof'].get('unit') != unit:
                        reason = 'Missing owned resource proof'
                if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != report['guard_sha256']:
                    reason = reason or 'Guard source changed during execution'
            except Exception as error:
                reason = reason or type(error).__name__ + ': ' + str(error)
            finally:
                # Exceptions, including sensor/evidence errors, still fence only
                # the scope created here. Never infer ownership from a PID file.
                if process is not None and process.poll() is None:
                    reason = reason or 'Guardian cleanup required'
                    stop_lease()
                    for signum, delay in ((signal.SIGTERM, policy.terminate_seconds), (signal.SIGKILL, policy.kill_seconds)):
                        try:
                            report['cleanup'].append(signal_owned_scope(unit, signum))
                            process.wait(timeout=max(delay, .05))
                            break
                        except Exception as error:
                            report['cleanup'].append({'error': type(error).__name__ + ': ' + str(error)})
                if process is not None:
                    report['exit_code'] = process.poll()
                if lease is not None:
                    stop_lease()
    except Exception as error:
        reason = reason or type(error).__name__ + ': ' + str(error)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    report['status'] = 'completed' if reason is None and report['exit_code'] == 0 else 'failed'
    report['reason'] = reason
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    event('final', status=report['status'], reason=reason)
    write_json(run / 'report.json', report)
    write_json(base / 'last-execution.json', {'report': str(run / 'report.json'), 'status': report['status'], 'run_id': run_id})
    return report


def scope_exec(arguments):
    control, run_id, cpu_text, fd_text, device_text, inode_text, separator, *command = arguments
    if separator != '--' or not command or not RUN_ID.fullmatch(run_id):
        raise GuardError('Invalid owned scope invocation')
    cpu = int(cpu_text)
    descriptor = int(fd_text)
    info = os.fstat(descriptor)
    if (info.st_dev != int(device_text) or info.st_ino != int(inode_text)
            or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise GuardError('Owned execution lock was not inherited intact')
    os.set_inheritable(descriptor, True)
    os.sched_setaffinity(0, {cpu})
    value = require_lease(Path(control), run_id=run_id, preflight=True)
    policy = Policy(**value['policy'])
    proof = scope_proof('stead-native-' + run_id + '.scope', cpu, policy)
    write_json(Path(control) / 'scope.json', proof)
    require_lease(Path(control), run_id=run_id, preflight=True)
    if Path(command[0]).name == 'bwrap':
        # bwrap retains this fd for the complete sandbox lifetime. Even if the
        # host guardian crashes, another heavy run cannot overlap live children.
        command[1:1] = ['--sync-fd', str(descriptor), '--die-with-parent']
    os.execvpe(command[0], command, os.environ)


if __name__ == '__main__':
    try:
        if len(sys.argv) < 2 or sys.argv[1] != '_scope':
            raise GuardError('This module is invoked only by an owned guarded runner')
        scope_exec(sys.argv[2:])
    except (GuardError, ValueError, OSError, subprocess.SubprocessError) as error:
        print('GUARD FAIL: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(1)

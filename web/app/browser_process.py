"""Own the complete browser cgroup, including Playwright's detached children.

The service's main process watches a pipe held only by the caller. Caller death
closes it; service exit and its hard deadline both kill the complete cgroup.
Only after systemd termination and an empty cgroup may callers delete profiles.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import select
import subprocess
import sys
import time


def clean_environment(root):
    return {'PATH': '/usr/bin:/bin', 'HOME': str(Path.home()), 'LANG': 'C.UTF-8',
            'XDG_RUNTIME_DIR': '/run/user/' + str(os.getuid()),
            'PLAYWRIGHT_BROWSERS_PATH': str(Path(root) / '.runtime/playwright')}


def properties(unit):
    result = subprocess.run(['/usr/bin/systemctl', '--user', 'show', unit,
        '--property=LoadState,ActiveState,ControlGroup,MainPID,Description,KillMode,RuntimeMaxUSec'],
        capture_output=True, text=True, timeout=3)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def group_empty(group):
    if not group:
        return True
    path = Path('/sys/fs/cgroup') / group.lstrip('/') / 'cgroup.events'
    try:
        return dict(line.split() for line in path.read_text().splitlines()).get('populated') == '0'
    except FileNotFoundError:
        return True


def run(command, *, root, output, healthy, timeout=600):
    if not command or not 0 < timeout <= 600:
        raise ValueError('Bounded browser command required')
    root, output = Path(root), Path(output)
    unit = 'stead-browser-' + secrets.token_hex(16) + '.service'
    description = 'Stead owned browser ' + unit
    if properties(unit).get('LoadState') != 'not-found':
        raise RuntimeError('Browser unit already exists')
    environment = clean_environment(root)
    proof_file = output / (unit + '.json')
    record = {'unit': unit, 'status': 'fail', 'cleanup': None}
    cpu = max(os.sched_getaffinity(0))
    argv = ['/usr/bin/systemd-run', '--user', '--quiet', '--wait', '--pipe',
        '--unit=' + unit, '--description=' + description, '--service-type=exec',
        '--property=KillMode=control-group', '--property=TimeoutStopSec=3s',
        '--property=RuntimeMaxSec=' + str(timeout + 10) + 's',
        '--property=CPUQuota=25%', '--property=CPUQuotaPeriodSec=10ms',
        '--property=CPUAffinity=' + str(cpu), '--property=UMask=0077',
        '--working-directory=' + str(root / 'web/app'),
        '/usr/bin/env', '-i', *[key + '=' + value for key, value in environment.items()],
        '/usr/bin/python3', '-B', str(Path(__file__).resolve()), '_worker',
        str(proof_file), unit, str(cpu), '--', *map(str, command)]
    process, group = None, ''
    started = time.monotonic()
    try:
        healthy()
        with (output / 'browser-console.log').open('xb') as log:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            while not proof_file.exists():
                healthy()
                if process.poll() is not None or time.monotonic() - started > 10:
                    raise RuntimeError('Browser service failed before admission')
                time.sleep(.05)
            proof = json.loads(proof_file.read_text())
            state = properties(unit)
            group = state.get('ControlGroup', '')
            if (state.get('Description') != description or state.get('KillMode') != 'control-group'
                    or state.get('ActiveState') != 'active' or state.get('MainPID') != str(proof['pid'])
                    or not group.startswith('/user.slice/') or Path(group).name != unit
                    or '..' in Path(group).parts or proof['cgroup'] != group
                    or proof['cpu_max'] != '2500 10000' or proof['cpu_affinity'] != [cpu]):
                raise RuntimeError('Browser ownership/resource read-back differs')
            record['proof'] = proof
            healthy()
            process.stdin.write(b'B')
            process.stdin.flush()
            while process.poll() is None:
                healthy()
                if time.monotonic() - started > timeout:
                    raise TimeoutError('Browser deadline reached')
                time.sleep(.2)
            record['exit_code'] = process.wait(timeout=1)
            if record['exit_code'] != 0:
                raise RuntimeError('Native browser journey failed; see private retained evidence')
            record['status'] = 'pass'
    finally:
        # stdin EOF is the worker's parent-death signal. Firefox owns another
        # process group, so kill the verified service cgroup, never just Node.
        if process is not None:
            process.stdin.close()
        state = properties(unit)
        if state.get('LoadState') != 'not-found':
            if state.get('Description') != description:
                raise RuntimeError('Refusing cleanup of a foreign browser service')
            candidate = state.get('ControlGroup', '')
            if candidate:
                if not candidate.startswith('/user.slice/') or Path(candidate).name != unit or '..' in Path(candidate).parts:
                    raise RuntimeError('Unowned browser cgroup path')
                group = candidate
            subprocess.run(['/usr/bin/systemctl', '--user', 'stop', unit], check=True,
                           capture_output=True, timeout=8)
        if process is not None:
            process.wait(timeout=5)
        state = properties(unit)
        if state.get('ActiveState') not in ('inactive', 'failed') or not group_empty(group):
            raise RuntimeError('Owned browser descendants did not terminate')
        record['cleanup'] = {'process_reaped': process is None or process.poll() is not None,
                             'cgroup': group, 'empty': True, 'state': state.get('ActiveState')}
        (output / 'browser-process.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def worker(arguments):
    proof_file, unit, cpu, separator, *command = arguments
    if separator != '--' or not command:
        raise ValueError('Invalid browser worker')
    groups = [line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::/')]
    if len(groups) != 1 or Path(groups[0]).name != unit:
        raise ValueError('Worker is outside owned service')
    group = Path('/sys/fs/cgroup') / groups[0].lstrip('/')
    proof = {'pid': os.getpid(), 'cgroup': groups[0], 'cpu_max': (group / 'cpu.max').read_text().strip(),
             'cpu_affinity': sorted(os.sched_getaffinity(0))}
    if proof['cpu_max'] != '2500 10000' or proof['cpu_affinity'] != [int(cpu)]:
        raise ValueError('Worker resource limits differ')
    temporary = Path(proof_file + '.tmp')
    temporary.write_text(json.dumps(proof))
    temporary.replace(proof_file)
    if not select.select([sys.stdin], [], [], 10)[0] or os.read(0, 1) != b'B':
        raise RuntimeError('Browser controller disappeared before admission')
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL)
    while child.poll() is None:
        if select.select([sys.stdin], [], [], .1)[0]:
            # Only EOF is valid after admission. Exiting the main service causes
            # systemd to kill all detached descendants, even if Node is wedged.
            child.terminate()
            return 1
    return child.wait()


if __name__ == '__main__':
    if sys.argv[1:2] != ['_worker']:
        raise SystemExit('Only the owned worker entry point is executable')
    raise SystemExit(worker(sys.argv[2:]))

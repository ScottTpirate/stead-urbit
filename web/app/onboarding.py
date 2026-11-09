#!/usr/bin/env python3
"""Record a bounded human trial in a separately owned local browser."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
sys.path.insert(0, str(ROOT / 'web/dev'))
import browser_process
import browser_admission
import execution_policy
import harness
from digests import sha, tree_sha
from loopback_bridge import LoopbackBridge, PORTS


def admitted(browser_run):
    harness.guard()
    status = harness.rpc('status')
    prerequisites = browser_admission.require_browser(ROOT, harness.STATE, status, browser_run)
    return status, prerequisites


def owned_service(output):
    if not re.fullmatch(r'onboarding-[0-9]{8}T[0-9]{6}Z-[a-z0-9_]{8}', output.name):
        raise ValueError('Invalid trial evidence directory')
    with execution_policy.directory_fd(output) as descriptor:
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('Trial evidence directory must be owned and private')
    unit = 'stead-trial-' + output.name + '.service'
    groups = [line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::/')]
    state = browser_process.properties(unit)
    if (len(groups) != 1 or not groups[0].startswith('/user.slice/')
            or Path(groups[0]).name != unit or state.get('ControlGroup') != groups[0]
            or state.get('MainPID') != str(os.getpid()) or state.get('KillMode') != 'control-group'):
        raise ValueError('Trial service ownership differs')
    limits = Path('/sys/fs/cgroup') / groups[0].lstrip('/')
    quota = (limits / 'cpu.max').read_text().strip()
    affinity = sorted(os.sched_getaffinity(0))
    if quota != '2500 10000' or len(affinity) != 1:
        raise ValueError('Trial service resource limits differ')
    return {'unit': unit, 'cgroup': groups[0], 'cpu_max': quota, 'cpu_affinity': affinity}


def run_trial(browser_run, output):
    service = owned_service(output)
    status, prerequisites = admitted(browser_run)
    run_id = status['execution_guard']['run_id']
    directory = harness.STATE / 'ingress' / run_id
    fixture = directory / 'browser-fixture.json'
    material, _ = browser_admission.private_json(fixture, 65536)
    if material.get('execution_id') != run_id or material.get('format') != 1:
        raise ValueError('Stale operator fixture')

    def healthy():
        current = harness.rpc('status', timeout=2)
        if (current.get('profile') != 'configured-team' or not current.get('ready')
                or current.get('execution_guard', {}).get('run_id') != run_id
                or current.get('execution_guard', {}).get('state') != 'running'
                or set(current.get('ships', {})) != set(PORTS)
                or any(row['exit'] is not None for row in current['ships'].values())):
            raise ValueError('The owned configured fixture is no longer ready')
        if browser_admission.live_reference(current) != prerequisites['native']:
            raise ValueError('Native prerequisite changed during the human trial')
        execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy())

    source_paths = ('web/app/onboarding.py', 'web/app/browser_process.py', 'web/app/browser_admission.py', 'web/app/tests/onboarding.mjs',
        'web/app/tests/onboarding-evidence.mjs', 'web/dev/loopback_bridge.py',
        'docs/urbit/quickstarts/member.md', 'docs/urbit/quickstarts/onboarding-task.md',
        'specs/urbit/toolchain.lock.json', 'web/app/dist/manifest.json')

    def inputs():
        return {'files': {name: sha(ROOT / name) for name in source_paths},
                'native_tree': tree_sha(ROOT / 'native/core/desk')}

    before = inputs()
    report = {'classification': 'human-local-browser-native-tls-transport', 'status': 'fail',
              'qualifies_phase': False, 'execution_id': run_id, 'inputs_before': before, 'tls': {},
              'prerequisites': prerequisites, 'manual_browser_service': service}
    personal = output / 'personal-fixture.json'
    process = None
    report_path = output / 'transport-report.json'
    try:
        certificates = directory / 'certificates'
        with LoopbackBridge(directory, healthy) as bridge:
            context = ssl.create_default_context(cafile=str(certificates / 'ca.pem'))
            for ship in ('zod', 'bus'):
                hostname = material['identities'][ship]['hostname']
                with socket.create_connection(('127.0.0.1', PORTS[ship]), timeout=3) as raw:
                    with context.wrap_socket(raw, server_hostname=hostname) as secure:
                        actual = hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
                        expected = hashlib.sha256(ssl.PEM_cert_to_DER_cert((certificates / (ship + '.pem')).read_text())).hexdigest()
                        if actual != expected:
                            raise ValueError('Native TLS certificate differs')
                        report['tls'][ship] = {'hostname': hostname, 'certificate_sha256': actual, 'protocol': secure.version()}
            profile = tempfile.mkdtemp(prefix='firefox-private-', dir=output)
            for arguments in (['-N', '--empty-password'],
                ['-A', '-n', 'Stead disposable local CA', '-t', 'C,,', '-i', str(certificates / 'ca.pem')]):
                subprocess.run(['/usr/bin/certutil', '-d', 'sql:' + profile, *arguments], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            with personal.open('x') as stream:
                json.dump({'format': 1, 'execution_id': run_id, 'origin': 'https://home.localhost:8443',
                    'identity_origin': 'https://bus.localhost:8444', 'identity_ship': '~bus',
                    'code': material['identities']['bus']['code']}, stream)
            command = [str(ROOT / '.runtime/node-v24.21.0-linux-x64/bin/node'),
                       str(ROOT / 'web/app/tests/onboarding.mjs'), profile, str(personal), str(output)]
            execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy(), preflight=True)
            with (output / 'browser-console.log').open('xb') as log:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                capture = output / 'onboarding-report.json'
                interruption = output / 'transport-stopped.json'
                startup_deadline = time.monotonic() + 60
                capture_deadline = time.monotonic() + 600
                while not capture.exists():
                    if process.poll() is not None and not capture.exists():
                        raise RuntimeError('Trial browser ended before writing evidence')
                    if bridge.closed.is_set() and not interruption.exists():
                        execution_policy.write_json(interruption, {'status': 'backend-unavailable'})
                    if not (output / 'ready.json').exists() and time.monotonic() > startup_deadline:
                        raise TimeoutError('Trial browser startup deadline reached')
                    if time.monotonic() > capture_deadline:
                        raise TimeoutError('Trial evidence deadline reached')
                    time.sleep(.25)
                trial, trial_sha = browser_admission.private_json(capture, 1024 * 1024)
                report.update(trial_status=trial['status'], trial_sha256=trial_sha, inputs_after=inputs())
                if before != report['inputs_after']:
                    raise ValueError('Source changed during the human trial')
                if bridge.closed.is_set():
                    report['status'] = 'transport-interrupted'
                else:
                    healthy()
                    if admitted(browser_run)[1] != prerequisites:
                        raise ValueError('Automated prerequisites changed during the human trial')
                    report['status'] = 'captured-for-review'
                execution_policy.write_json(report_path, report)
                personal.unlink(missing_ok=True)
                # Evidence collection has ended. The user owns the open window.
                process.wait()
    except Exception as error:
        report['error_type'] = type(error).__name__
        execution_policy.write_json(report_path, report)
        # Once the browser has opened, even a failed capture leaves it visible.
        if process is not None and (output / 'window-open.json').exists():
            execution_policy.write_json(output / 'transport-stopped.json', {'status': 'capture-interrupted'})
            process.wait()
        raise
    finally:
        personal.unlink(missing_ok=True)
        # The profile remains private. Only verified service teardown can
        # establish that no browser descendant still has it open.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--launch', action='store_true')
    mode.add_argument('--service', metavar='OUTPUT', help=argparse.SUPPRESS)
    parser.add_argument('--browser-run', required=True, help='Passed browser-native-YYYYMMDDTHHMMSSZ directory name')
    args = parser.parse_args()
    os.umask(0o077)
    environment = browser_process.clean_environment(ROOT, headed=True)
    if args.service:
        if Path(args.service).name != args.service:
            raise ValueError('Expected a local trial directory name')
        run_trial(args.browser_run, ROOT / '.runtime' / args.service)
        return
    admitted(args.browser_run)
    execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy(), preflight=True)
    output = Path(tempfile.mkdtemp(prefix='onboarding-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-', dir=ROOT / '.runtime'))
    unit = 'stead-trial-' + output.name + '.service'
    cpu = max(os.sched_getaffinity(0))
    subprocess.run(['/usr/bin/systemd-run', '--user', '--quiet', '--unit=' + unit,
        '--service-type=exec', '--property=KillMode=control-group', '--property=TimeoutStopSec=3s',
        '--property=CPUQuota=25%', '--property=CPUQuotaPeriodSec=10ms',
        '--property=CPUAffinity=' + str(cpu), '--property=UMask=0077',
        '/usr/bin/env', '-i', *[key + '=' + value for key, value in environment.items()],
        '/usr/bin/python3', '-B', str(Path(__file__).resolve()), '--service', output.name,
        '--browser-run', args.browser_run], check=True, timeout=15)
    print(json.dumps({'status': 'launching', 'evidence': str(output), 'unit': unit}), flush=True)


if __name__ == '__main__':
    main()

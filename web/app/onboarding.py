#!/usr/bin/env python3
"""Launch a private, bounded, human-operated browser on the native fake fixture."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', action='store_true', required=True)
    parser.add_argument('--browser-run', required=True, help='Passed browser-native-YYYYMMDDTHHMMSSZ directory name')
    args = parser.parse_args()
    os.umask(0o077)
    # Validate the one display socket before creating a profile or opening ports.
    browser_process.clean_environment(ROOT, headed=True)
    harness.guard()
    status = harness.rpc('status')
    if status.get('profile') != 'configured-team' or not status.get('ready'):
        raise ValueError('The configured disposable team must be ready')
    prerequisites = browser_admission.require_browser(ROOT, harness.STATE, status, args.browser_run)
    run_id = status['execution_guard']['run_id']
    directory = harness.STATE / 'ingress' / run_id
    fixture = directory / 'browser-fixture.json'
    if fixture.is_symlink() or fixture.stat().st_mode & 0o077 or fixture.stat().st_size > 65536:
        raise ValueError('Bounded private operator fixture required')
    material = json.loads(fixture.read_text())
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
    output = Path(tempfile.mkdtemp(prefix='onboarding-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-', dir=ROOT / '.runtime'))
    report = {'classification': 'human-local-browser-native-tls-transport', 'status': 'fail',
              'qualifies_phase': False, 'execution_id': run_id, 'inputs_before': before, 'tls': {},
              'prerequisites': prerequisites}
    profile, personal = None, output / 'personal-fixture.json'
    try:
        certificates = directory / 'certificates'
        with LoopbackBridge(directory, healthy):
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
            print(json.dumps({'status': 'launching', 'evidence': str(output), 'participant': 'human-user'}), flush=True)
            report['browser_process'] = browser_process.run(command, root=ROOT, output=output, healthy=healthy, headed=True)
            # Successful launcher execution means only that a human trial was
            # captured. Its receipts, failures and participant report need review.
            trial = json.loads((output / 'onboarding-report.json').read_text())
            report['trial_status'] = trial['status']
            healthy()
        report['inputs_after'] = inputs()
        if before != report['inputs_after']:
            raise ValueError('Source changed during the human trial')
        if browser_admission.require_browser(ROOT, harness.STATE, harness.rpc('status', timeout=2), args.browser_run) != prerequisites:
            raise ValueError('Automated prerequisites changed during the human trial')
        report['status'] = 'captured-for-review'
    except Exception as error:
        report['error_type'] = type(error).__name__
        raise
    finally:
        ownership = output / 'browser-process.json'
        clean = ownership.exists() and json.loads(ownership.read_text()).get('cleanup', {}).get('empty') is True
        if clean:
            if profile is not None:
                shutil.rmtree(profile)
            personal.unlink(missing_ok=True)
            report['private_profile'] = 'removed after verified cgroup termination'
        else:
            report['private_profile'] = 'retained; termination not proven'
        (output / 'transport-report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'status': report['status'], 'evidence': str(output)}), flush=True)


if __name__ == '__main__':
    main()

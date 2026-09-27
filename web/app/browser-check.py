#!/usr/bin/env python3
"""Execute the real local browser path against the already guarded fake ships."""
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
sys.path.insert(0, str(ROOT / 'web/dev'))
import harness
import execution_policy
import browser_process
from digests import sha, tree_sha
from loopback_bridge import LoopbackBridge, PORTS


def main():
    os.umask(0o077)
    if os.environ.get('SSLKEYLOGFILE'):
        raise ValueError('TLS key logging must be absent from this private browser run')
    harness.guard()
    status = harness.rpc('status')
    if status.get('profile') != 'configured-team' or not status.get('ready'):
        raise ValueError('Complete make team-dev before the real browser journey')
    run_id = status['execution_guard']['run_id']
    directory = harness.STATE / 'ingress' / run_id
    fixture = directory / 'browser-fixture.json'
    if fixture.is_symlink() or fixture.stat().st_mode & 0o077:
        raise ValueError('Private operator fixture required')
    material = json.loads(fixture.read_text())
    if material.get('execution_id') != run_id or material.get('format') != 1:
        raise ValueError('Stale private operator fixture')
    def healthy():
        current = harness.rpc('status', timeout=2)
        if (current.get('profile') != 'configured-team' or not current.get('ready')
                or current.get('execution_guard', {}).get('run_id') != run_id
                or current.get('execution_guard', {}).get('state') != 'running'
                or set(current.get('ships', {})) != set(PORTS)
                or any(row['exit'] is not None for row in current['ships'].values())):
            raise ValueError('Owned configured fixture no longer ready')
    output = ROOT / '.runtime' / ('browser-native-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    output.mkdir(mode=0o700)
    before = {'native_tree': tree_sha(ROOT / 'native/core/desk'), 'runner': sha(__file__),
              'process_owner': sha(ROOT / 'web/app/browser_process.py'),
              'browser_test': sha(ROOT / 'web/app/tests/native.mjs'), 'relay': sha(ROOT / 'web/dev/loopback_bridge.py'),
              'toolchain': sha(ROOT / 'specs/urbit/toolchain.lock.json'), 'execution_id': run_id}
    report = {'classification': 'local-real-browser-native-tls', 'status': 'fail', 'qualifies_phase': False,
              'inputs_before': before, 'tls': {}}
    certificates = directory / 'certificates'
    try:
        with LoopbackBridge(directory, healthy):
            context = ssl.create_default_context(cafile=str(certificates / 'ca.pem'))
            for ship, port in PORTS.items():
                host = material['identities'][ship]['hostname']
                with socket.create_connection(('127.0.0.1', port), timeout=3) as raw:
                    with context.wrap_socket(raw, server_hostname=host) as secure:
                        actual = hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
                        expected = hashlib.sha256(ssl.PEM_cert_to_DER_cert((certificates / (ship + '.pem')).read_text())).hexdigest()
                        if actual != expected:
                            raise ValueError('Native leaf fingerprint differs')
                        report['tls'][ship] = {'hostname': host, 'certificate_sha256': actual, 'protocol': secure.version()}
            for label, wrong_context, hostname in (
                ('wrong-ca-rejected', ssl.create_default_context(cafile=str(certificates / 'bus.pem')), 'home.localhost'),
                ('wrong-hostname-rejected', context, 'bus.localhost')):
                try:
                    with socket.create_connection(('127.0.0.1', PORTS['zod']), timeout=3) as raw:
                        with wrong_context.wrap_socket(raw, server_hostname=hostname):
                            raise AssertionError(label)
                except ssl.SSLCertVerificationError:
                    report[label] = True
            profile = tempfile.mkdtemp(prefix='firefox-private-', dir=output)
            try:
                for arguments in (['-N', '--empty-password'],
                    ['-A', '-n', 'Stead disposable local CA', '-t', 'C,,', '-i', str(certificates / 'ca.pem')]):
                    subprocess.run(['/usr/bin/certutil', '-d', 'sql:' + profile, *arguments], check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                command = [str(ROOT / '.runtime/node-v24.21.0-linux-x64/bin/node'),
                           str(ROOT / 'web/app/tests/native.mjs'), profile, str(fixture), str(output)]
                execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy(), preflight=True)
                def admitted():
                    healthy()
                    execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy())
                report['browser_process'] = browser_process.run(command, root=ROOT, output=output, healthy=admitted)
            finally:
                ownership = output / 'browser-process.json'
                if ownership.exists() and json.loads(ownership.read_text()).get('cleanup', {}).get('empty') is True:
                    shutil.rmtree(profile)
                    report['private_profile'] = 'removed after verified cgroup termination'
                else:
                    report['private_profile'] = 'retained; termination not proven'
            healthy()
        report['inputs_after'] = dict(before, native_tree=tree_sha(ROOT / 'native/core/desk'),
            runner=sha(__file__), process_owner=sha(ROOT / 'web/app/browser_process.py'),
            browser_test=sha(ROOT / 'web/app/tests/native.mjs'), relay=sha(ROOT / 'web/dev/loopback_bridge.py'))
        if before != report['inputs_after']:
            raise ValueError('Browser source changed during execution')
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        (output / 'transport-report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'status': report['status'], 'classification': report['classification'], 'evidence': str(output)}))


if __name__ == '__main__':
    main()

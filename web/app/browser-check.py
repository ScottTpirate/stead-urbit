#!/usr/bin/env python3
"""Execute the real local browser path against the already guarded fake ships."""
import hashlib
import json
import os
import re
import stat
from pathlib import Path
import socket
import ssl
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
sys.path.insert(0, str(ROOT / 'web/dev'))
import harness
import execution_policy
import browser_process
import browser_admission
from browser_admission import private_json
from loopback_bridge import LoopbackBridge, PORTS


def main():
    os.umask(0o077)
    followup = None
    if sys.argv[1:]:
        if len(sys.argv) != 3 or sys.argv[1] != '--expiry-from' or not re.fullmatch(r'browser-native-[0-9]{8}T[0-9]{6}Z', sys.argv[2]):
            raise ValueError('Only the fixed native-expiry followup is supported')
        followup = ROOT / '.runtime' / sys.argv[2] / 'expiry-session.json'
        parent = followup.parent.lstat()
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise ValueError('Private bounded prior session evidence required')
        private_json(followup, 8192)
    if os.environ.get('SSLKEYLOGFILE'):
        raise ValueError('TLS key logging must be absent from this private browser run')
    harness.guard()
    status = harness.rpc('status')
    if status.get('profile') != 'configured-team' or not status.get('ready'):
        raise ValueError('Complete make team-dev before the real browser journey')
    prerequisite = browser_admission.require_native(ROOT, harness.STATE, status)
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
        if browser_admission.live_reference(current) != prerequisite:
            raise ValueError('Native prerequisite changed during the browser journey')
    output = ROOT / '.runtime' / (('browser-expiry-' if followup else 'browser-native-') + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    output.mkdir(mode=0o700)
    before = browser_admission.browser_inputs(ROOT, status)
    cases = browser_admission.browser_cases(ROOT)
    if followup:
        session, session_sha = private_json(followup, 8192)
        prior, prior_sha = private_json(followup.parent / 'transport-report.json', 262144)
        journey, journey_sha = private_json(followup.parent / 'browser-report.json', 2 * 1024 * 1024)
        browser_admission.verify_browser(prior, journey, before, cases)
        browser_admission.require_git(harness.STATE, prior['stock_git'], before)
        if (prior.get('status') != 'pass' or journey.get('status') != 'pass'
                or journey.get('execution_id') != run_id
                or prior.get('inputs_before') != before or prior.get('inputs_after') != before
                or prior.get('browser_process', {}).get('cleanup', {}).get('empty') is not True
                or prior.get('journey_sha256') != journey_sha
                or session.get('execution_id') != run_id or session.get('format') != 1):
            raise ValueError('Expiry requires the same passed native browser source and fixture')
        issued, captured = session.get('issued_before_ms'), session.get('captured_at_ms')
        if (type(issued) is not int or type(captured) is not int or not 0 < issued <= captured <= issued + 120000
                or not 28 * 60000 <= time.time() * 1000 - issued <= 29 * 60000):
            raise ValueError('Natural expiry followup must start in its recorded window')
        before.update(expiry_session=session_sha, parent_transport=prior_sha, parent_journey=journey_sha)
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
                           str(ROOT / ('web/app/tests/native-expiry.mjs' if followup else 'web/app/tests/native.mjs')),
                           profile, str(fixture), str(output), *([str(followup)] if followup else [])]
                execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy(), preflight=True)
                def admitted():
                    healthy()
                    execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy())
                report['browser_process'] = browser_process.run(command, root=ROOT, output=output, healthy=admitted)
                child, child_sha = private_json(output / 'browser-report.json', 2 * 1024 * 1024)
                browser_admission.verify_journey(child, run_id, cases, expiry=bool(followup))
                if followup and child.get('session_file_sha256') != before['expiry_session']:
                    raise ValueError('Browser used different expiry session bytes')
                report['journey_sha256'] = child_sha
            finally:
                ownership = output / 'browser-process.json'
                if ownership.exists() and json.loads(ownership.read_text()).get('cleanup', {}).get('empty') is True:
                    shutil.rmtree(profile)
                    report['private_profile'] = 'removed after verified cgroup termination'
                else:
                    report['private_profile'] = 'retained; termination not proven'
            healthy()
        if not followup:
            _, fixture_sha = private_json(output / 'git-fixture.json', 131072)
            if child.get('git_fixture_sha256') != fixture_sha:
                raise ValueError('Browser Git fixture differs from its journey binding')
            name = output.name.replace('browser-native-', 'browser-git-') + '.json'
            target = harness.STATE / 'logs' / name
            with target.open('xb') as stream:
                stream.write((output / 'git-fixture.json').read_bytes())
            observed_git = harness.rpc('team-git-check', fixture=name, sha256=fixture_sha, timeout=300)
            report['stock_git'] = {key: observed_git[key] for key in ('status', 'evidence_file', 'sha256', 'fixture_sha256')}
            browser_admission.require_git(harness.STATE, report['stock_git'], before)
        current = harness.rpc('status', timeout=2)
        if browser_admission.require_native(ROOT, harness.STATE, current) != prerequisite:
            raise ValueError('Native prerequisite changed before browser closeout')
        report['inputs_after'] = browser_admission.browser_inputs(ROOT, current)
        if followup:
            report['inputs_after'].update(expiry_session=private_json(followup, 8192)[1],
                parent_transport=private_json(followup.parent / 'transport-report.json', 262144)[1],
                parent_journey=private_json(followup.parent / 'browser-report.json', 2 * 1024 * 1024)[1])
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

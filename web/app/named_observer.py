"""Own one attended configured-team browser observation, never a native backend.

The operator supplies fresh non-secret admission JSON and a reviewed code-provider
command. Its stdout is connected privately to the observer, inside the owned
browser service. This tool does not provision a member, tunnel or grant.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def private_json(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
            and info.st_size <= 8192, 'Private bounded operator input required')
    return json.loads(path.read_bytes())


def verify_forward(origin, port, expected, ca):
    url = urlsplit(origin)
    require(url.scheme == 'https' and url.hostname and not url.username and not url.password
            and not url.path and not url.query and not url.fragment,
            'Exact HTTPS origin required')
    require(type(port) is int and 1024 <= port <= 65535, 'Fixed loopback forward required')
    require(isinstance(expected, str) and len(base64.b64decode(expected, validate=True)) == 32,
            'Exact public-key pin required')
    # Verify the operator's CA, hostname and validity before any code, then bind
    # the exact admitted public key as well. No ambient certificate exception.
    context = ssl.create_default_context(cafile=str(ca))
    with socket.create_connection(('127.0.0.1', port), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=url.hostname) as stream:
            certificate = stream.getpeercert(binary_form=True)
    require(0 < len(certificate) <= 16384, 'Bounded peer certificate required')
    public = subprocess.check_output(['/usr/bin/openssl', 'x509', '-inform', 'DER', '-pubkey', '-noout'],
        input=certificate, stderr=subprocess.DEVNULL, timeout=5)
    der = subprocess.check_output(['/usr/bin/openssl', 'pkey', '-pubin', '-outform', 'DER'],
        input=public, stderr=subprocess.DEVNULL, timeout=5)
    require(base64.b64encode(hashlib.sha256(der).digest()).decode() == expected, 'Named peer public key changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--code-command', type=Path, required=True,
                        help='Private JSON argument array for a reviewed owner code provider; never a code literal')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ca', type=Path, required=True, help='Independently verified public CA certificate')
    parser.add_argument('--node', type=Path, default=ROOT / '.runtime/node-v24.21.0-linux-x64/bin/node')
    args = parser.parse_args()
    os.umask(0o077)
    require(os.getuid() != 0 and not os.environ.get('SSLKEYLOGFILE'), 'Private ordinary desktop user required')
    config = private_json(args.config)
    stamp = config.get('admission_observed_at_unix')
    require(type(stamp) is int and 0 <= time.time() - stamp <= 600, 'Fresh operator admission required')
    ca = args.ca.resolve(strict=True)
    for name in ('home', 'identity'):
        verify_forward(config['origins'][name], config['forward_ports'][name], config['pins'][name], ca)
    provider = private_json(args.code_command)
    require(isinstance(provider, list) and 1 <= len(provider) <= 16
            and all(isinstance(v, str) and 0 < len(v) <= 2048 and '\x00' not in v for v in provider),
            'Closed code-provider argument array required')
    require(Path(provider[0]).is_absolute() and Path(provider[0]).is_file()
            and os.access(provider[0], os.X_OK), 'Reviewed absolute code-provider executable required')
    require(not any(re.search(r'(?:[a-z]{6}-){3}[a-z]{6}', v) for v in provider), 'Code must never appear in command arguments')
    node = args.node.resolve(strict=True)
    output = args.output.absolute()
    require(not output.exists() and output.parent.is_dir(), 'Fresh output directory required')
    output.mkdir(mode=0o700)
    saved_config = output / 'observer-config.json'
    saved_config.write_text(json.dumps(config) + '\n')
    sources = [HERE / name for name in ('named-observer.mjs', 'namedObserverBoundary.mjs',
        'namedObserverEvidence.mjs', 'namedObserverConfig.mjs', 'named_observer.py', 'named_observer_owner.py',
        'package.json', 'package-lock.json')]
    sources += [ROOT / 'scripts/urbit/execution_policy.py', Path(provider[0]).resolve(strict=True), ca]
    require(all(path.stat().st_size <= 1024 * 1024 for path in sources), 'Bounded source provider required')
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    pins = {str(path): digest(path) for path in sources}
    (output / 'launch-source.json').write_text(json.dumps({'source_hashes': pins, 'node_sha256': digest(node),
        'code_provider_arguments_sha256': hashlib.sha256(json.dumps(provider).encode()).hexdigest(),
        'native_backend_started': False, 'attended_trial_started': False}, indent=2) + '\n')
    sys.path.insert(0, str(ROOT / 'scripts/urbit'))
    import execution_policy
    import named_observer_owner
    initial = execution_policy.sample_temperatures()
    execution_policy.validate_sample(initial, execution_policy.Policy(), preflight=True)
    named_observer_owner.clean_environment(ROOT, headed=True)
    command = 'set -o pipefail; ' + shlex.join(provider) + ' | ' + shlex.join(
        [str(node), str(HERE / 'named-observer.mjs'), str(saved_config), str(output)])

    def healthy():
        execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy(),
                                         expected_inventory=initial.readings_c)
        for name, expected in pins.items():
            require(digest(Path(name)) == expected, 'Owned observer source changed')

    try:
        named_observer_owner.run(['/usr/bin/bash', '--noprofile', '--norc', '-c', command],
            root=ROOT, output=output, healthy=healthy, timeout=900, headed=True)
    finally:
        record = output / 'browser-process.json'
        if record.is_file() and json.loads(record.read_bytes()).get('cleanup', {}).get('empty') is True:
            profiles = [output / name for name in ('participant-profile', 'identity-owner-profile')]
            for profile in profiles:
                if profile.exists():
                    shutil.rmtree(profile)
            (output / 'private-profile-cleanup.json').write_text(json.dumps({
                'after_verified_empty_cgroup': True, 'participant_profile_removed': not profiles[0].exists(),
                'identity_owner_profile_removed': not profiles[1].exists()}) + '\n')


if __name__ == '__main__':
    main()

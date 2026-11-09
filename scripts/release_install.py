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
import http.client
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import ssl
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
HTTP_HELPERS = ('native_tls.py', 'team_conn.py')
HTTP_DRIVERS = ('ted/stead-team-client.hoon', 'ted/stead-local-tls.hoon',
                'lib/stead-codec.hoon', 'lib/stead-delivery.hoon')
TLS_HOST = 'home.localhost'
TLS_PORT = 18443
HTTP_ORIGIN = f'https://{TLS_HOST}:{TLS_PORT}'
REDACTED_COOKIE = '[redacted]'
SECURITY_HEADERS = {
    'cache-control': 'no-store',
    'content-security-policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY',
    'referrer-policy': 'no-referrer', 'cross-origin-resource-policy': 'same-origin',
}
# This precise audited controller can fail in proof() only after a fresh fake
# boot and before any desk mutation. Other failures need a fresh run or review.
CLEAN_RETRY_CONTROLLER = '744861aef3516ddd0e9fbaae87594c0b21a0a2b5f240e10e3220313188f7664d'
CLEAN_RETRY_NATIVE = '44018860a029a79b32866e532241571d8b9483f86d2893a7226d7bd34424f5a1'
PREINSTALL_CHECKS = ['private-network-and-filesystem', 'exact-public-package-bytes',
                     'exact-controller-and-helper-bytes']
RESTORE_CLASS = 'local-native-copied-configured-home-recovery'
UPGRADE_CLASS = 'local-native-copied-home-same-schema-asset-upgrade'
RESTORE_BEFORE_BOOTSTRAP = [*PREINSTALL_CHECKS, 'restored-home-live-on-release-desk',
                            'restored-test-drivers-unchanged', 'pre-bootstrap-network-fenced',
                            'restored-home-saved-schema-v3']
RESTORE_AFTER_BOOTSTRAP = ['restore-changes-owner-incarnation', 'bootstrap-preserves-saved-vase',
                           'packaged-native-https-restored-after-bootstrap',
                           'package-unchanged-after-restore', 'restored-clone-stopped-and-reaped']
RESTORE_CHECKS = [*RESTORE_BEFORE_BOOTSTRAP, *RESTORE_AFTER_BOOTSTRAP]
UPGRADE_CHECKS = [*RESTORE_BEFORE_BOOTSTRAP, 'upgraded-home-suspended-at-reviewed-state',
                  'asset-replacement-matches-clay', 'upgraded-home-fenced-after-reload',
                  *RESTORE_AFTER_BOOTSTRAP]
CLEAN_STOP = {'clean': True, 'exit_code': 0, 'forced': False, 'premature': False, 'reaped': True}


def checkpoint_tree(pier, copy_to=None, *, installed=False):
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
    if '.urb' not in directories or not files or ((DESK in directories) != installed):
        layout = 'installed' if installed else 'uninstalled'
        raise ValueError('Checkpoint is not an ' + layout + ' synthetic pier')
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


class ReleaseNative(Native):
    def _arguments(self):
        arguments = super()._arguments()
        return arguments[:1] + ['--https-port', str(TLS_PORT)] + arguments[1:]


class CleanCheckpointNative(ReleaseNative):
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
                '-p', str(self.port), '--http-port', str(self.http_port), '--https-port', str(TLS_PORT), str(self.pier)]


class RestoredHomeNative(CleanCheckpointNative):
    """Resume only the newly staged configured Home clone."""
    def _check_pier(self):
        context = execution_policy.read_json('/execution/release-context.json', 1024 * 1024)
        restored = context['restore_checkpoint']
        if (self.ship != 'zod' or restored.get('artifact_sha256') != context['artifact_sha256']
                or checkpoint_tree(self.pier, installed=True) != restored.get('pier')):
            raise ValueError('Copied configured Home binding differs before boot')


def stopped_home_checkpoint(pier, expected):
    with execution_policy.directory_fd(pier) as descriptor:
        if '.vere.lock' in os.listdir(descriptor):
            raise ValueError('Restored Home still has a runtime ownership lock')
    if inventory(pier / DESK) != expected:
        raise ValueError('Restored Home desk differs from the verified package')
    return checkpoint_tree(pier, installed=True)


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


def role_configuration(role, now_ms):
    if role == 'identity':
        return {'protocol': 'stead.identity-config/1', 'expected_revision': '0',
                'home': '~bus', 'home_origin': 'https://bus.localhost:18444', 'origin': HTTP_ORIGIN}
    if role != 'home':
        raise ValueError('Unsupported configured release role')
    principal = '019939ba-4000-7000-8000-000000000102'
    return {'protocol': 'stead.team-config/1', 'expected_revision': '0', 'home': '~zod',
            'origin': HTTP_ORIGIN, 'organization_id': '019939ba-4000-7000-8000-000000000005',
            'team_id': '019939ba-4000-7000-8000-000000000006', 'custody': 'local-disposable',
            'runtime': 'isolated-fake', 'bindings': {'~bus': {'principal_id': principal,
            'binding_id': '019939ba-4000-7000-8000-000000000202', 'binding_revision': '1',
            'active': 'yes', 'expires_at_ms': str(now_ms + 7200000), 'display_name': 'Synthetic release member'}},
            'project_creators': {principal: 'yes'}}


def owner_call(native, role, mode, value, route='/'):
    import team_conn
    native.check()
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    result = team_conn.run(native.binary, native.pier / '.urb/conn.sock', mode, route, raw,
                           target='zod', app='stead-' + role, timeout=75)
    native.check()
    outcome = (result.get('outcome') or {}).get('json')
    if not isinstance(outcome, dict):
        raise ValueError('Owner-local release operation has no native terminal response')
    return outcome


def bootstrap_role(native, role):
    nonce = secrets.token_hex(32)
    for _ in range(3):
        value = owner_call(native, role, 'bootstrap', {'protocol': 'stead.bootstrap/1', 'nonce': nonce}, '/bootstrap/' + nonce)
        if (set(value) == {'protocol', 'status', 'home', 'nonce', 'incarnation'}
                and value['protocol'] == 'stead.bootstrap/1' and value['status'] == 'ready'
                and value['home'] == '~zod' and value['nonce'] == nonce
                and isinstance(value['incarnation'], str) and re.fullmatch(r'[0-9a-f]{64}', value['incarnation'])):
            return value
        if not (value.get('protocol') == 'stead.test-terminal/1' and value.get('status') == 'failed'
                and value.get('kind') == 'poke-fail'):
            raise ValueError('Owner-local release bootstrap acknowledgement differs')
        native.check()
        time.sleep(.1)
    raise ValueError('Owner-local release bootstrap did not become ready')


def kernel_guest_cookie(value):
    """Recognize only pinned Eyre's anonymous zod cookie, never authentication.

    +session-cookie-string in the pinned kernel uses a canonical 128-bit @uv
    session key and the seven-day guest timeout. The authenticated timeout,
    other ship names and any extra attributes are deliberately not accepted.
    """
    match = re.fullmatch(r'urbauth-~zod=0v(0|[1-9a-v][0-9a-v]{0,4}(?:\.[0-9a-v]{5}){0,5}); Path=/; Max-Age=604800', value)
    return match is not None and int(match[1].replace('.', ''), 32).bit_length() <= 128


def report_headers(headers):
    # Redact even an unexpected or mocked cookie before recording a failure.
    return {key: REDACTED_COOKIE if 'cookie' in key.lower() else value for key, value in headers.items()}


def request_role(native, ca_file, method, route, *, body=None, headers=None, secure=True):
    """Direct private loopback only: native TLS, CA+hostname checked, no redirects."""
    if method not in ('GET', 'POST', 'PUT') or not route.startswith(('/stead/', '/stead-identity/')) or len(route) > 512:
        raise ValueError('Release HTTP request bound')
    if body is not None and (not isinstance(body, bytes) or len(body) > 65537):
        raise ValueError('Release HTTP request body bound')
    if any('cookie' in key.lower() or key.lower() in ('authorization', 'proxy-authorization') for key in (headers or {})):
        raise ValueError('Release HTTP probes must remain anonymous')
    native.check()
    connection = http.client.HTTPConnection('127.0.0.1', TLS_PORT if secure else native.http_port, timeout=5)
    try:
        connection.connect()
        if secure:
            context = ssl.create_default_context(cafile=str(ca_file))
            connection.sock = context.wrap_socket(connection.sock, server_hostname=TLS_HOST)
        fields = {'Host': f'{TLS_HOST}:{TLS_PORT}', 'Accept-Encoding': 'identity'}
        fields.update(headers or {})
        connection.request(method, route, body=body, headers=fields)
        response = connection.getresponse()
        pairs = response.getheaders()
        if len(pairs) > 64 or sum(len(k) + len(v) for k, v in pairs) > 16384:
            raise ValueError('Release HTTP response header bound')
        response_headers, guest_cookie = {}, False
        for key, value in pairs:
            key = key.lower()
            if key in response_headers:
                raise ValueError('Duplicate release HTTP response header')
            if 'cookie' in key:
                if key != 'set-cookie' or not kernel_guest_cookie(value):
                    raise ValueError('Unexpected release HTTP cookie header')
                guest_cookie, value = True, REDACTED_COOKIE
            response_headers[key] = value
        content = response.read(524289)
        if len(content) > 524288:
            raise ValueError('Release HTTP response byte bound')
        native.check()
        return {'status': response.status, 'headers': response_headers, 'body': content,
                'kernel_guest_cookie_observed': guest_cookie}
    except http.client.HTTPException as error:
        # BadStatusLine and similar parser errors may contain raw wire text.
        raise ValueError('Release HTTP transport failed (' + type(error).__name__ + ')') from None
    finally:
        connection.close()


def assert_http(response, status, *, mime, digest=None, size=None, error=None):
    headers, body = response['headers'], response['body']
    guest_cookie = response.get('kernel_guest_cookie_observed') is True
    cookie_headers = {key: value for key, value in headers.items() if 'cookie' in key.lower()}
    if (response['status'] != status or headers.get('content-type') != mime
            or any(headers.get(key) != value for key, value in SECURITY_HEADERS.items())
            or cookie_headers != ({'set-cookie': REDACTED_COOKIE} if guest_cookie else {})
            or any(key in headers for key in ('location', 'access-control-allow-origin'))):
        raise ValueError('Packaged HTTP status/MIME/security headers differ')
    if digest is not None and (len(body) != size or hashlib.sha256(body).hexdigest() != digest):
        raise ValueError('Packaged HTTP asset bytes differ')
    if error is not None:
        value = json.loads(body)
        if value != {'protocol': 'stead.result/3', 'status': 'rejected', 'error': error}:
            raise ValueError('Packaged HTTP denial payload differs')


def route_checks(native, role, ca_file, package=Path('/package'), *, evidence=None):
    frontend = execution_policy.read_json(package / 'source/frontend.json')
    prefix = '/stead/' if role == 'home' else '/stead-identity/'
    routes = [row for row in frontend['routes'] if row['route'].startswith(prefix)]
    if not 0 < len(routes) <= 32 or not any(row['route'] == prefix for row in routes):
        raise ValueError('Packaged role frontend inventory is incomplete')
    evidence = {} if evidence is None else evidence
    evidence.update(assets=[], denials=[], native_tls=True, browser_authentication=False)
    def observe(method, route, **kwargs):
        evidence['last_request'] = {'method': method, 'route': route, 'secure': kwargs.get('secure', True)}
        evidence.pop('last_response', None)
        response = request_role(native, ca_file, method, route, **kwargs)
        evidence['last_response'] = {'status': response['status'], 'bytes': len(response['body']),
            'sha256': hashlib.sha256(response['body']).hexdigest(), 'headers': report_headers(response['headers']),
            'kernel_guest_cookie_observed': response.get('kernel_guest_cookie_observed') is True}
        return response
    for row in routes:
        response = observe('GET', row['route'])
        assert_http(response, 200, mime=row['mime'], digest=row['sha256'], size=row['bytes'])
        evidence['assets'].append({'route': row['route'], 'sha256': row['sha256'], 'bytes': row['bytes'], 'status': 200})
    common = {'Origin': HTTP_ORIGIN, 'Content-Type': 'application/json'}
    denied = [('wrong-host', 'GET', prefix, None, {'Host': 'foreign.invalid:18443'}, True),
              ('wrong-origin', 'GET', prefix, None, {'Origin': 'https://foreign.invalid'}, True),
              ('unknown-path', 'GET', prefix + 'not-in-package', None, {}, True),
              ('query-string', 'GET', prefix + '?test=1', None, {}, True),
              ('unsupported-method', 'PUT', prefix, b'{}', common, True),
              ('post-to-asset', 'POST', prefix, b'{}', common, True),
              ('get-body', 'GET', prefix, b'{}', {}, True),
              ('forwarded-header', 'GET', prefix, None, {'Forwarded': 'proto=https'}, True),
              ('spoofed-plain-tls', 'GET', prefix, None, {'Forwarded': 'proto=https'}, False)]
    for name, method, route, body, headers, secure in denied:
        response = observe(method, route, body=body, headers=headers, secure=secure)
        assert_http(response, 403, mime='application/json', error='invalid_http_request')
        evidence['denials'].append({'name': name, 'status': 403, 'code': 'invalid_http_request'})
    # Pinned Eyre redirects ordinary cleartext requests once its TLS port is
    # live. Observe that transport barrier without following the redirect.
    plain = observe('GET', prefix, secure=False)
    if plain['status'] != 301 or plain['headers'].get('location') != HTTP_ORIGIN + prefix or plain['body']:
        raise ValueError('Native Eyre cleartext redirect differs')
    evidence['denials'].append({'name': 'plain-http', 'status': 301, 'location': HTTP_ORIGIN + prefix})
    protected = prefix + ('api/query' if role == 'home' else 'api/list')
    response = observe('POST', protected, body=b'{"protocol":"stead.identity/1"}' if role == 'identity' else b'{}', headers=common)
    error = 'session_required' if role == 'home' else 'owner_required'
    assert_http(response, 401, mime='application/json', error=error)
    evidence['denials'].append({'name': 'anonymous-protected-api', 'status': 401, 'code': error})
    if role == 'home':
        response = observe('POST', prefix + 'api/capabilities', body=b'{"protocol":"stead.capabilities/3"}', headers=common)
        assert_http(response, 200, mime='application/json')
        value = json.loads(response['body'])
        if value != {'protocol': 'stead.capabilities/3', 'profile': 'configured-team', 'commands': 'stead.command/3',
                     'queries': 'stead.query/3', 'updates': 'stead.updates/3', 'authentication': 'native-approved-browser/1',
                     'max_request_bytes': '65536', 'max_response_bytes': '262144', 'page_size': '20', 'runtime': 'isolated-fake'}:
            raise ValueError('Packaged public capabilities differ')
        evidence['public_capabilities'] = value
    return evidence


def saved_home_fingerprint(native):
    source = ('=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)  '
              '?>  ?=([%20 %live *] egg)  =/  saved=vase  +.old-state.egg  '
              '?>  ?=([%stead-home %3 *] q.saved)  ^-  @ux  (shax (jam saved))')
    result = native.dojo(source).strip()
    if not re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', result):
        raise ValueError('Restored Home saved vase is not configured schema 3')
    value = int(result.replace('.', ''), 16)
    if value >= 2 ** 256:
        raise ValueError('Saved Home vase fingerprint exceeds SHA-256')
    return f'{value:064x}'


def asset_delta(previous, target):
    changed = {name for name in previous.keys() | target.keys() if previous.get(name) != target.get(name)}
    inventory_path = 'web/stead/inventory.hoon'
    assets = changed - {inventory_path}
    if (inventory_path not in changed or inventory_path not in previous.keys() & target.keys() or not assets
            or any(not re.fullmatch(r'web/stead/asset-[0-9a-f]{64}\.stead-asset', name) for name in assets)):
        raise ValueError('Upgrade must change only generated inventory and content-addressed assets')
    return sorted(changed - target.keys()), sorted(changed & target.keys())


def replace_clay_assets(native, previous, target, package=Path('/package/desk')):
    remove, update = asset_delta(previous, target)
    mount = native.pier / DESK
    if inventory(mount) != previous or inventory(package) != target:
        raise ValueError('Asset upgrade inputs do not match both verified desk inventories')
    obsolete = {name: f'/={DESK}=/{name.removesuffix(".stead-asset")}/stead-asset' for name in remove}
    for name, route in obsolete.items():
        exists = f'.^(? %cu {route})'
        if native.dojo(exists).strip() != '%.y':
            raise ValueError('Expected source asset is missing from Clay: ' + name)
        native.dojo('|rm ' + route)
        deadline = time.monotonic() + 15
        while True:
            found = native.dojo(exists, timeout=5).strip()
            if found == '%.n':
                break
            if found != '%.y' or time.monotonic() >= deadline:
                raise ValueError('Native Clay removal did not complete: ' + name)
            native.check()
            time.sleep(.1)
        (mount / name).unlink(missing_ok=True)
    for name in update:
        shutil.copyfile(package / name, mount / name)
    if inventory(mount) != target:
        raise ValueError('Mounted desk does not match the target package')
    native.dojo(f'|commit %{DESK}')
    clay_readback(native, target, 'stead-home')
    for name, route in obsolete.items():
        if native.dojo(f'.^(? %cu {route})').strip() != '%.n':
            raise ValueError('Superseded asset is still present in Clay: ' + name)
    return {'removed': remove, 'updated': update}


def verify_restored_home(native, context, report, checkpoint):
    import native_tls

    restored = context['restore_checkpoint']
    expected = inventory('/package/desk')
    report['boot'] = native.start()
    wait_agent(native, 'stead-home', True, timeout=60)
    checkpoint('restored-home-live-on-release-desk',
               native.dojo('.^(desk %gd /=stead-home=/$)').strip() == '%' + DESK)
    checkpoint('restored-test-drivers-unchanged',
               inventory('/controller/drivers') == restored['test_drivers']
               and native.readback(restored['test_drivers']))

    certificates = native_tls.create('/state/certificates')
    native_tls.install(native.binary, native.pier / '.urb/conn.sock', certificates, 'zod')
    report['tls'] = native_tls.verify(native.process, certificates, 'zod', native.check)
    interfaces = [name for _, name in socket.if_nameindex()]
    net = os.readlink('/proc/self/ns/net')
    report['pre_bootstrap_fence'] = {'interfaces': interfaces, 'private_namespace': net}
    checkpoint('pre-bootstrap-network-fenced', interfaces == ['lo']
               and net != context['host_namespaces']['net']
               and net == report['boot']['proof']['namespaces']['net'])
    report['saved_home'] = {'schema': 3, 'sha256_before_bootstrap': saved_home_fingerprint(native)}
    checkpoint('restored-home-saved-schema-v3', True)
    upgrade = restored.get('asset_upgrade')
    if upgrade is not None:
        before = upgrade['saved_home_sha256']
        if report['saved_home']['sha256_before_bootstrap'] != before:
            raise ValueError('Restored Home differs from the reviewed saved-state fingerprint')
        native.dojo(f'|rein %{DESK} [%.n %stead-home]')
        wait_agent(native, 'stead-home', False, timeout=60)
        checkpoint('upgraded-home-suspended-at-reviewed-state', saved_home_fingerprint(native) == before)
        report['asset_replacement'] = replace_clay_assets(native, upgrade['source_desk'], expected)
        checkpoint('asset-replacement-matches-clay', native.dojo('.^(? %gu /=stead-home=/$)').strip() == '%.n')
        native.dojo(f'|rein %{DESK} [%.y %stead-home]')
        wait_agent(native, 'stead-home', True, timeout=60)
        unavailable = request_role(native, certificates / 'ca.pem', 'GET', '/stead/')
        assert_http(unavailable, 503, mime='application/json', error='projection_unavailable')
        checkpoint('upgraded-home-fenced-after-reload', saved_home_fingerprint(native) == before)
    report['bootstrap_after_restore'] = bootstrap_role(native, 'home')
    checkpoint('restore-changes-owner-incarnation',
               report['bootstrap_after_restore']['incarnation'] not in restored['prior_incarnations'])
    report['saved_home']['sha256_after_bootstrap'] = saved_home_fingerprint(native)
    checkpoint('bootstrap-preserves-saved-vase', report['saved_home']['sha256_after_bootstrap']
               == report['saved_home']['sha256_before_bootstrap'])
    report['http_after_restore'] = {}
    route_checks(native, 'home', certificates / 'ca.pem', evidence=report['http_after_restore'])
    report['configured_home'] = True
    checkpoint('packaged-native-https-restored-after-bootstrap', True)
    clay_readback(native, expected, 'stead-home')
    report['installed_files'] = expected
    checkpoint('package-unchanged-after-restore', inventory('/package') == context['package'])


def inside():
    os.umask(0o077)
    stopped, cleaning, finished = threading.Event(), threading.Event(), threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopped.set())
    report = {'status': 'fail', 'classification': 'local-native-clean-fake-desk-install',
              'qualifies_phase': False, 'checks': [], 'configured_home': False,
              'upgrade_recovery': False, 'canary': False, 'paired_home_identity': False, 'browser_authentication': False}
    native = None
    failures = []
    context = execution_policy.read_json('/execution/release-context.json', 1024 * 1024)
    manifest = execution_policy.read_json('/package/manifest.json')
    report.update(source_commit=manifest['source_commit'], role=manifest['role'],
                  artifact_sha256=context['artifact_sha256'], verifier_source_commit=context['verifier_source_commit'])
    restore = context.get('restore_checkpoint')
    if restore:
        if restore.get('asset_upgrade') is not None:
            report.update(classification=UPGRADE_CLASS, boot_mode='restored-asset-upgrade')
        else:
            report.update(classification=RESTORE_CLASS, boot_mode='restored-configured-home')
        report['restore_checkpoint'] = restore

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
        if restore:
            native = RestoredHomeNative('zod', 31337, guard)
            verify_restored_home(native, context, report, checkpoint)
        else:
            if context.get('clean_checkpoint'):
                report['clean_checkpoint'] = context['clean_checkpoint']
                report['boot_mode'] = 'resumed-clean-checkpoint'
                native = CleanCheckpointNative('zod', 31337, guard)
            else:
                report['boot_mode'] = 'fresh-fake'
                native = ReleaseNative('zod', 31337, guard)
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
            # Test-only owner adapters are separate from the verified release desk.
            report['test_driver_files'] = native.install(Path('/controller/drivers'))
            import native_tls
            certificates = native_tls.create('/state/certificates')
            native_tls.install(native.binary, native.pier / '.urb/conn.sock', certificates, 'zod')
            report['tls'] = native_tls.verify(native.process, certificates, 'zod', native.check)
            configuration = role_configuration(manifest['role'], int(time.time() * 1000))
            mode = 'configure' if manifest['role'] == 'home' else 'identity-config'
            checkpoint('owner-local-role-configuration', owner_call(native, manifest['role'], mode, configuration) == {})
            report['configured_role'] = manifest['role']
            report['configured_home'] = manifest['role'] == 'home'
            report['bootstrap_before_reload'] = bootstrap_role(native, manifest['role'])
            report['http_before_reload'] = {}
            route_checks(native, manifest['role'], certificates / 'ca.pem', evidence=report['http_before_reload'])
            checkpoint('packaged-native-https-routes-and-assets', True)
            native.dojo(f'|rein %{DESK} [%.n %{agent}]')
            wait_agent(native, agent, False, timeout=60)
            checkpoint('explicit-stop-observed', native.dojo(f'.^(? %gu /={agent}=/$)').strip() == '%.n')
            native.dojo(f'|rein %{DESK} [%.y %{agent}]')
            wait_agent(native, agent, True)
            checkpoint('supported-reload-observed', native.dojo(f'.^(? %gu /={agent}=/$)').strip() == '%.y')
            prefix = '/stead/' if manifest['role'] == 'home' else '/stead-identity/'
            unavailable = request_role(native, certificates / 'ca.pem', 'GET', prefix)
            assert_http(unavailable, 503, mime='application/json',
                        error='projection_unavailable' if manifest['role'] == 'home' else 'unavailable')
            checkpoint('reload-blocks-http-until-owner-bootstrap', True)
            report['bootstrap_after_reload'] = bootstrap_role(native, manifest['role'])
            checkpoint('reload-changes-owner-incarnation', report['bootstrap_after_reload']['incarnation'] != report['bootstrap_before_reload']['incarnation'])
            report['http_after_reload'] = {}
            route_checks(native, manifest['role'], certificates / 'ca.pem', evidence=report['http_after_reload'])
            checkpoint('packaged-native-https-restored-after-bootstrap', True)
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
                if restore and report['status'] == 'pass':
                    report['stopped_clone'] = stopped_home_checkpoint(native.pier, report['installed_files'])
                    checkpoint('restored-clone-stopped-and-reaped', report['cleanup'] == CLEAN_STOP)
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


def run(archive, expected_sha256, target_path, retry_clean=None, retry_clean_sha256=None, *,
        prepare_restore=None, asset_upgrade=False):
    import package_release
    import toolchain
    if (retry_clean is None) != (retry_clean_sha256 is None):
        raise ValueError('Retry requires both the prior run path and its reviewed checkpoint SHA-256')
    if prepare_restore is not None and retry_clean is not None:
        raise ValueError('Installed recovery and preinstall retry are separate modes')
    if asset_upgrade and prepare_restore is None:
        raise ValueError('An asset upgrade requires a verified restored Home clone')
    if os.getuid() == 0:
        raise ValueError('Release install requires a nonroot local caller')
    if package_release.git(ROOT, 'remote', 'get-url', '--push', 'origin').decode().strip() != 'https://github.com/ScottTpirate/stead-urbit.git':
        raise ValueError('Derivative origin required')
    execution_policy.validate_sample(execution_policy.sample_temperatures(), execution_policy.Policy(), preflight=True)
    raw = package_release.read_bounded(ROOT, archive, package_release.MAX_ARCHIVE)
    target = json.loads(package_release.read_bounded(ROOT, target_path, 8192), object_pairs_hook=package_release.unique)
    manifest = package_release.verify_bytes(raw, expected_sha256=expected_sha256, target=target)
    if prepare_restore is not None and manifest['role'] != 'home':
        raise ValueError('Installed recovery requires a verified Home package')
    lock = toolchain.verify()
    if package_release.digest(toolchain.LOCK_PATH.read_bytes()) != manifest['toolchain_sha256']:
        raise ValueError('Current verified runtime differs from release target')
    verifier_commit = package_release.source_identity(ROOT, 'HEAD')
    sources = ['scripts/release_install.py', 'scripts/sdk_native/native.py', 'scripts/package_release.py', 'scripts/package_sdk.py']
    sources += ['scripts/urbit/' + name for name in HELPERS + HTTP_HELPERS]
    sources += ['native/core/desk/' + name for name in HTTP_DRIVERS]
    if prepare_restore is not None:
        sources += ['scripts/release_recovery.py']
    before = {name: package_release.digest(package_release.committed(ROOT, verifier_commit, name)) for name in sources}
    if any(package_release.digest((ROOT / name).read_bytes()) != pin for name, pin in before.items()):
        raise ValueError('Commit the exact release verifier and helper inputs first')
    if asset_upgrade:
        label, purpose = 'release-asset-upgrade', 'offline-synthetic-home-asset-upgrade-only'
    elif prepare_restore is not None:
        label, purpose = 'release-restore-boot', 'offline-restored-synthetic-home-only'
    else:
        label, purpose = 'release-install', 'fresh-offline-release-install-only'
    state = Path(tempfile.mkdtemp(prefix=label + '-', dir=ROOT / '.runtime'))
    state.chmod(0o700)
    execution_policy.write_json(state / '.stead-disposable.json', {'format': 1, 'purpose': purpose})
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
    for name in HELPERS + HTTP_HELPERS:
        shutil.copyfile(ROOT / 'scripts/urbit' / name, state / 'helpers' / name)
    for name in HTTP_DRIVERS:
        destination = state / 'controller/drivers' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(package_release.committed(ROOT, verifier_commit, 'native/core/desk/' + name))
    context = {'artifact_sha256': expected_sha256, 'verifier_source_commit': verifier_commit,
               'sources': before, 'host_namespaces': {name: os.readlink('/proc/self/ns/' + name) for name in ('net', 'pid', 'mnt', 'user')}}
    context.update({name: inventory(state / name) for name in ('package', 'controller', 'support', 'helpers')})

    def command(control, run_id):
        if retry_clean is not None:
            context['clean_checkpoint'] = checked_clean_copy(retry_clean, state / 'work', expected_sha256, lock, toolchain.LOCK_PATH, retry_clean_sha256)
            execution_policy.write_json(state / 'clean-checkpoint.json', context['clean_checkpoint'])
        if prepare_restore is not None:
            context['restore_checkpoint'] = prepare_restore(state, manifest)
            if ('asset_upgrade' in context['restore_checkpoint']) != asset_upgrade:
                raise ValueError('Staged recovery operation differs from the requested mode')
        execution_policy.write_json(control / 'release-context.json', context)
        # No writable /state alias reaches candidate, controller or helpers.
        return sandbox_command(state, control, run_id, lock, toolchain.LOCK_PATH)

    guard = execution_policy.run_guarded(command, root=ROOT, label=label, timeout=3600 if prepare_restore is None else 900)
    unchanged = all(package_release.digest((ROOT / name).read_bytes()) == pin for name, pin in before.items())
    result = {'classification': 'local-native-clean-fake-desk-install', 'qualifies_phase': False,
              'guard_status': guard['status'], 'guard_report': guard['run_directory'] + '/report.json',
              'source_unchanged': unchanged, 'evidence': str(state / 'work/report.json'), 'artifact_sha256': expected_sha256,
              'boot_mode': 'resumed-clean-checkpoint' if retry_clean is not None else 'fresh-fake'}
    if prepare_restore is not None:
        if asset_upgrade:
            result.update(classification=UPGRADE_CLASS, boot_mode='restored-asset-upgrade')
        else:
            result.update(classification=RESTORE_CLASS, boot_mode='restored-configured-home')
    execution_policy.write_json(state / 'host-report.json', result)
    print(json.dumps(result), flush=True)
    if guard['status'] != 'completed' or not unchanged:
        raise RuntimeError('Release install guard/source checks did not complete cleanly')
    report = execution_policy.read_json(state / 'work/report.json', 4 * 1024 * 1024)
    if report.get('status') != 'pass' or not report.get('checks') or not all(row.get('passed') is True for row in report['checks']):
        raise RuntimeError('Native release install did not pass its bounded checks')
    if prepare_restore is not None:
        retired_checkpoint_scope(guard['run_id'])
        restored = stopped_home_checkpoint(state / 'work/zod', inventory(state / 'package/desk'))
        expected_checks = UPGRADE_CHECKS if asset_upgrade else RESTORE_CHECKS
        if (report.get('classification') != result['classification'] or report.get('restore_checkpoint') != context['restore_checkpoint']
                or report.get('checks') != [{'name': name, 'passed': True} for name in expected_checks]
                or report.get('cleanup') != CLEAN_STOP or report.get('stopped_clone') != restored):
            raise RuntimeError('Stopped restored Home evidence differs from the isolated native result')
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

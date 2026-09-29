"""Trusted owner of the synthetic SDK fixture; never installed in the consumer."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

sys.path.insert(0, '/helpers')
import execution_policy
import team_conn
from bridge import Bridge
from native import Native, inventory, sha
from cases import run as conformance, canonical, uid
from results import validate


CONTROL_FILES = ('ted/stead-team-client.hoon', 'lib/stead-codec.hoon', 'lib/stead-delivery.hoon',
                 'mar/stead-command-3.hoon', 'mar/stead-query-3.hoon',
                 'mar/stead-result-3.hoon', 'mar/stead-updates-3.hoon')


def fixture_config(now):
    if type(now) is not int or not 0 < now < 2**64 - 7200000:
        raise ValueError('Native fixture time differs')
    return {'protocol': 'stead.team-config/1', 'expected_revision': '0', 'home': '~zod',
        'origin': 'https://home.localhost:8443', 'organization_id': uid(5), 'team_id': uid(6),
        'custody': 'local-disposable', 'runtime': 'isolated-fake',
        'bindings': {'~' + ship: {'principal_id': uid(principal), 'binding_id': uid(binding), 'binding_revision': '1',
                    'active': 'yes', 'expires_at_ms': str(now + 7200000), 'display_name': name}
                    for ship, principal, binding, name in (('bus', 102, 202, 'Public consumer'), ('nec', 104, 204, 'Control member'))},
        'project_creators': {uid(102): 'yes', uid(104): 'yes'}}


def fixture_call(home, control, mode, value, route=None, *, timeout=75):
    if home is None or home.ship != 'zod':
        raise ValueError('Fixed Home required')
    raw = canonical(value).encode()
    business = mode in ('command', 'query', 'updates')
    if business:
        if control is None or control is home or control.ship != 'nec':
            raise ValueError('Distinct individual control member required')
        if route is not None:
            raise ValueError('Business result route is derived from the actual member')
        sender = control
        digest = hashlib.sha256(('stead.' + mode + '/3').encode() + b'\0' + raw).hexdigest()
        route = '/v3/result/~nec/' + uid(204) + '/1/' + value['request_id'] + '/' + digest
    elif mode in ('configure', 'bootstrap') and route is not None:
        sender = home
    else:
        raise ValueError('Unsupported trusted fixture operation')
    result = team_conn.run(sender.binary, sender.pier / '.urb/conn.sock', mode, route, raw, timeout=timeout)
    sender.commands.append({'owner_mode': mode, 'result': result})
    if result['outcome'] is None:
        raise ValueError('Fixture operation did not return a result')
    value_out = result['outcome']['json']
    if business:
        validate(mode, value, value_out, '~nec')
    return value_out


def bootstrap_home(home, control, guard, attempts):
    # Configuration schedules projection work. Admission waits for the actual
    # bootstrap ACK; only an explicit native poke refusal can be retried.
    deadline = time.monotonic() + 180
    for _ in range(3):
        guard()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        nonce = secrets.token_hex(32)
        value = fixture_call(home, control, 'bootstrap', {'protocol': 'stead.bootstrap/1', 'nonce': nonce},
                             '/bootstrap/' + nonce, timeout=min(75, remaining))
        attempts.append({'nonce': nonce, 'response_sha256': hashlib.sha256(canonical(value).encode()).hexdigest(),
                         **{key: value.get(key) for key in ('protocol', 'status', 'kind')}})
        if time.monotonic() >= deadline:
            raise TimeoutError('Native bootstrap acknowledgement arrived after deadline')
        if (set(value) == {'protocol', 'status', 'home', 'nonce', 'incarnation'}
                and value['protocol'] == 'stead.bootstrap/1' and value['status'] == 'ready'
                and value['home'] == '~zod' and value['nonce'] == nonce
                and isinstance(value['incarnation'], str) and re.fullmatch(r'[0-9a-f]{64}', value['incarnation'])):
            return value
        if not (value.get('protocol') == 'stead.test-terminal/1' and value.get('status') == 'failed'
                and value.get('kind') == 'poke-fail'):
            raise ValueError('Native bootstrap acknowledgement differs')
        time.sleep(.1)
    raise TimeoutError('Native bootstrap readiness not acknowledged')


def close_native(role, native, cleanup, directory=Path('/state')):
    if native is None:
        return True
    clean = True
    try:
        cleanup[role] = native.stop()
        if not cleanup[role]['clean']:
            raise RuntimeError(role + ' native cleanup was not clean')
    except BaseException as error:
        clean = False
        cleanup[role + '_error'] = str(error)
    try:
        (directory / (role + '-transcript.json')).write_text(json.dumps(native.commands))
    except BaseException as error:
        clean = False
        cleanup[role + '_transcript_error'] = str(error)
    return clean


def consumer_command():
    args = ['bwrap', '--unshare-all', '--unshare-user', '--new-session', '--die-with-parent', '--disable-userns', '--uid', '0', '--gid', '0',
            '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        if path.is_symlink():
            args += ['--symlink', os.readlink(path), str(path)]
        elif path.exists():
            args += ['--ro-bind', str(path), str(path)]
    args += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/etc']
    for name in ('public', 'runner', 'runtime', 'kernel', 'toolchain.json'):
        args += ['--ro-bind', '/' + name, '/' + name]
    args += ['--bind', '/state/consumer', '/state', '--chdir', '/state', '--clearenv',
             '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'LANG', 'C.UTF-8',
             '--setenv', 'STEAD_CONFIGURED', '1', '--ro-bind', '/state/consumer-context.json', '/consumer-context.json',
             '--', '/usr/bin/python3', '-B', '/runner/consumer.py']
    return args


def main():
    os.umask(0o077)
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    report = {'status': 'fail', 'classification': 'real-native-public-sdk-three-fresh-fakes',
              'qualifies_phase': False, 'checks': [], 'calls': []}
    path = Path('/state/report.json')
    started = time.monotonic()
    home = control = process = bridge = None
    log = None
    child_done = False
    cleaning = threading.Event()
    watchdog_stop = threading.Event()
    watchdog_errors = []
    before = inventory('/native')
    report['context'] = execution_policy.read_json('/execution/sdk-context.json', 2 * 1024 * 1024)
    sequence = 0

    def checkpoint(stage):
        report['stage'] = stage
        execution_policy.write_json(path, report)
        print(json.dumps({'stage': stage, 'checks': len(report['checks']), 'elapsed_seconds': round(time.monotonic() - started, 1)}), flush=True)

    def guard():
        if watchdog_errors:
            raise RuntimeError('SDK lifetime watchdog failed: ' + watchdog_errors[0])
        if stopped.is_set():
            raise InterruptedError('SDK qualification stopped')
        execution_policy.require_lease(run_id=os.environ['STEAD_EXECUTION_ID'], read_only=True)
        if process is not None and not child_done and process.poll() is not None:
            raise RuntimeError('SDK consumer namespace exited unexpectedly')

    def watch():
        while not watchdog_stop.wait(.25):
            try:
                guard()
                if not cleaning.is_set():
                    for native in (home, control):
                        if native is not None and native.process is not None and native.process.poll() is not None:
                            raise RuntimeError('SDK trusted native child exited unexpectedly')
                if not cleaning.is_set() and bridge is not None:
                    bridge.check()
            except BaseException as error:
                watchdog_errors.append(type(error).__name__ + ': ' + str(error))
                # No native exchange, protocol lock or cleanup wait here.
                if bridge is not None:
                    bridge.opened.clear()
                for child in (process, home.process if home is not None else None,
                              control.process if control is not None else None):
                    try:
                        if child is not None and child.poll() is None:
                            child.terminate()
                    except OSError:
                        pass
                return

    def check(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        checkpoint('checking')
        if not condition:
            raise AssertionError(name)

    def rpc(operation, value=None, timeout=120):
        nonlocal sequence
        guard()
        sequence += 1
        bridge.message({'id': sequence, 'operation': operation, 'value': {} if value is None else value})
        response = bridge.get(timeout, guard)
        if not isinstance(response, dict) or set(response) != {'id', 'result'} or response['id'] != sequence:
            raise ValueError('SDK controller result: ' + str(response)[:300])
        return response['result']

    def owner(mode, value, route=None):
        return fixture_call(home, control, mode, value, route)

    def sdk(mode, value):
        raw = value if isinstance(value, str) else canonical(value)
        start = time.monotonic()
        result = rpc('call', {'mode': mode, 'raw': raw, 'binding': uid(202)})
        validate(mode, value, result)
        report['calls'].append({'mode': mode, 'input_sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'input_bytes': len(raw.encode()), 'result': result, 'elapsed_ms': round((time.monotonic() - start) * 1000, 3)})
        checkpoint('public-call')
        return result

    tcp = socket.socket()
    tcp.bind(('127.0.0.1', 23451))
    tcp.listen(1)
    abstract_name = 'stead-sdk-' + secrets.token_hex(16)
    abstract = socket.socket(socket.AF_UNIX)
    abstract.bind('\0' + abstract_name)
    abstract.listen(1)
    watchdog = threading.Thread(target=watch, daemon=True)
    watchdog.start()
    try:
        guard()
        host_ns = report['context']['host_namespaces']
        outer_ns = {name: os.readlink('/proc/self/ns/' + name) for name in host_ns}
        check('authority-controller-separated-from-host', all(outer_ns[name] != host_ns[name] for name in host_ns))
        context = report['context']
        check('authority-uses-nonroot-caller-id', os.getuid() == context['caller_uid'] != 0 and os.getgid() == context['caller_gid'])
        check('runner-and-package-at-admission', inventory('/runner') == context['runner'] and inventory('/public') == context['public'])
        check('authority-at-admission', inventory('/native') == context['sources']['native/core/desk'])
        execution_policy.write_json('/state/consumer-context.json', {'runner': context['runner'], 'public': context['public']})
        parent, child = socket.socketpair()
        log = Path('/state/consumer-controller.log').open('xb')
        try:
            process = subprocess.Popen(consumer_command(), stdin=child, stdout=child, stderr=log, close_fds=True)
        finally:
            child.close()
        bridge = Bridge(parent, 31519, 31337)
        checkpoint('fresh-public-consumer-compile')
        compiled = rpc('compile', timeout=1500)
        report['consumer_build'] = compiled
        check('public-compilation-precedes-home', not Path('/state/zod').exists()
              and not Path('/state/nec').exists() and home is None and control is None)
        check('public-sample-and-four-marks-compiled', compiled['compiled']['status'] == 'compiled')
        isolation = rpc('isolation', {'ports': [23451], 'abstract': abstract_name})
        report['consumer_isolation_before_home'] = isolation
        check('consumer-has-separate-network-user-mount-pid', all(isolation['namespaces'][name] != outer_ns[name] for name in outer_ns))
        checkpoint('fresh-authoritative-home')
        home = Native('zod', 31337, guard)
        report['home_boot'] = home.start()
        check('fresh-home-has-no-stead-app', home.dojo('(lien ~(tap in .^((set [@tas ?]) %ge /=base=/$)) |=([name=@tas live=?] =(name %stead-home)))').strip() == '%.n')
        report['home_installed'] = home.install('/native')
        home.dojo('|start %stead-home')
        report['home_proof'] = home.proof()
        own_ports = set(compiled['boot']['proof']['lens_ports']) | {18081}
        home_ports = set(report['home_proof']['lens_ports']) | {18080}
        # This existing read-only RPC also keeps the consumer's bounded request
        # wait from spanning two sequential trusted cold boots.
        report['consumer_isolation_after_home'] = rpc('isolation', {
            'ports': [23451, *sorted(home_ports - own_ports)], 'abstract': abstract_name})
        check('control-ingress-stays-in-home-namespace', report['consumer_isolation_after_home']['abstract_denied']
              and report['home_proof']['namespaces']['net'] != isolation['native']['namespaces']['net'])
        checkpoint('fresh-control-member')
        control = Native('nec', 31338, guard)
        report['control_member_boot'] = control.start()
        check('control-member-is-individual', control.dojo('our').strip() == '~nec')
        staging = Path('/state/control-install')
        staging.mkdir()
        for name in CONTROL_FILES:
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path('/native') / name, target)
        report['control_member_installed'] = control.install(staging)
        check('control-member-installed-exact-adapter', report['control_member_installed']
              == {name: before[name] for name in CONTROL_FILES})
        now = int(home.dojo('(div (mul 1.000 (sub now ~1970.1.1)) ~s1)').strip().replace('.', ''))
        check('owner-local-configuration', owner('configure', fixture_config(now), '/') == {})
        report['bootstrap_attempts'] = []
        boot = bootstrap_home(home, control, guard, report['bootstrap_attempts'])
        check('real-home-bootstrap-and-assets', boot.get('status') == 'ready' and boot.get('home') == '~zod'
              and boot.get('nonce') == report['bootstrap_attempts'][-1]['nonce'])
        report['control_member_proof'] = control.proof()
        control_ports = set(report['control_member_proof']['lens_ports']) | {18082}
        # A numeric loopback port can name the consumer's own control listener;
        # prove separate namespace ownership and also test live Home-only ports.
        ports = [23451, *sorted((home_ports | control_ports) - own_ports)]
        report['consumer_isolation_after_control_member'] = rpc('isolation', {'ports': ports, 'abstract': abstract_name})
        check('control-member-stays-in-trusted-namespace', report['consumer_isolation_after_control_member']['abstract_denied']
              and report['control_member_proof']['namespaces'] == report['home_proof']['namespaces'])
        # The trusted relay owns only the fixed two UDP aliases. No queued
        # pre-admission data is released; discarded fake discovery can retry.
        report['consumer_admission'] = rpc('open')
        bridge.admit()
        checkpoint('public-native-conformance')
        conformance(sdk, owner, check, now)
        check('control-member-source-unchanged', inventory(staging) == report['control_member_installed']
              and control.readback(report['control_member_installed']))
        report['status'] = 'pass'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        report['native_failure'] = getattr(error, 'native_failure', None)
        checkpoint('failed')
    finally:
        cleaning.set()
        if bridge is not None:
            bridge.opened.clear()
        cleanup = {}
        try:
            if process is not None and process.poll() is None and bridge is not None and bridge.error is None:
                cleanup['consumer'] = rpc('stop', timeout=40)
                check('consumer-source-unchanged', cleanup['consumer']['inputs_unchanged'] and cleanup['consumer']['installed_unchanged'])
                sequence += 1
                bridge.message({'id': sequence, 'operation': 'finish', 'value': {}})
                child_done = True
                cleanup['controller_exit'] = process.wait(timeout=10)
                if cleanup['controller_exit'] != 0:
                    raise RuntimeError('Consumer controller cleanup failed')
            elif process is not None:
                raise RuntimeError('Consumer failed before clean stop')
        except BaseException as error:
            report['status'] = 'fail'
            cleanup['consumer_error'] = str(error)
        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=25)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                cleanup['controller_reaped'] = process.poll() is not None
            except BaseException as error:
                report['status'] = 'fail'
                cleanup['controller_error'] = str(error)
        if bridge is not None:
            cleanup['datagrams'] = {'sent': bridge.sent, 'received': bridge.received, 'dropped': bridge.dropped}
            try:
                bridge.close()
            except BaseException as error:
                report['status'] = 'fail'
                cleanup['bridge_error'] = str(error)
        for role, native in (('control_member', control), ('home', home)):
            if not close_native(role, native, cleanup):
                report['status'] = 'fail'
        tcp.close()
        abstract.close()
        if log is not None:
            log.close()
        report['cleanup'] = cleanup
        watchdog_stop.set()
        watchdog.join(timeout=2)
        report['watchdog_errors'] = watchdog_errors
        if watchdog.is_alive() or watchdog_errors:
            report['status'] = 'fail'
        report['authority_inputs_unchanged'] = (inventory('/native') == before
            and inventory('/public') == report['context']['public'] and inventory('/runner') == report['context']['runner'])
        if not report['authority_inputs_unchanged']:
            report['status'] = 'fail'
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        checkpoint('completed' if report['status'] == 'pass' else 'failed')
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

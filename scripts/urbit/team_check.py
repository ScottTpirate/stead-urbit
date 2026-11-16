"""Actual configured Gall development lane. Browser/TLS acceptance is separate."""
from __future__ import annotations
import hashlib
import copy
import json
from pathlib import Path
import re
import secrets
import time
import traceback
import urllib.request
import core_conn
import execution_policy
import native_install
import native_tls
import native_units
import team_conn
import team_git
import team_updates_check
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
DEPENDENCIES = ('team_check.py', 'team_conn.py', 'core_conn.py', 'native_install.py',
                'team_lifecycle.py', 'native_peer_fence.py', 'native_tls.py', 'native_units.py', 'owned_child.py', 'execution_policy.py', 'team_updates_check.py', 'team_git.py')


def closure():
    return {name: sha(CODE / name) for name in DEPENDENCIES}


LOADED_CLOSURE = closure()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')


def uid(number):
    return '019939ba-4000-7000-8000-' + f'{number:012x}'


def configuration(now):
    return {'protocol': 'stead.team-config/1', 'expected_revision': '0', 'home': '~zod',
            'origin': 'https://home.localhost:8443', 'organization_id': uid(5), 'team_id': uid(6),
            'custody': 'local-disposable', 'runtime': 'isolated-fake',
            'bindings': {'~' + ship: {'principal_id': uid(102 + i), 'binding_id': uid(202 + i),
                        'binding_revision': '1', 'active': 'yes', 'expires_at_ms': str(now + 7200000),
                        'display_name': name} for i, (ship, name) in enumerate((('bus', 'Alice'), ('nec', 'Zoë')))},
            'project_creators': {uid(102): 'yes'}}


def capabilities_match(value, request_id):
    """The public query contract has opaque row keys, not resource-name keys."""
    if not isinstance(value, dict) or not isinstance(value.get('rows'), dict):
        return False
    return (all(value.get(key) == expected for key, expected in {
        'protocol': 'stead.query-result/3', 'status': 'read', 'request_id': request_id,
        'kind': 'capabilities', 'project_id': '', 'container_id': '', 'resource_id': '',
        'authority_epoch': '0', 'cursor': ''}.items())
        and isinstance(value.get('generation'), str) and bool(value['generation'])
        and list(value['rows'].values()) == [{
            'protocol': 'stead.capabilities/3', 'profile': 'configured-team', 'commands': 'stead.command/3',
            'queries': 'stead.query/3', 'updates': 'stead.updates/3', 'work_contract': 'stead.work-contract/1', 'workspace_queries': 'stead.workspace-queries/1',
            'authentication': 'native-sender/1',
            'max_request_bytes': '65536', 'max_response_bytes': '262144', 'page_size': '20',
            'runtime': 'isolated-fake'}])


def bootstrap_ready(team, ship, call, guard):
    """Wait for an actual owner-local ACK without releasing startup fencing."""
    entry = team.boots[ship]
    process, nonce = entry['process'], entry['nonce']
    deadline = time.monotonic() + 180

    def current():
        guard()
        if (team.boots.get(ship) is not entry or team.children.get(ship) is not process
                or entry.get('process') is not process
                or entry.get('nonce') != nonce or entry.get('acknowledged')
                or not entry.get('suspended') or process.poll() is not None):
            raise ValueError('Native bootstrap owner changed')

    for _ in range(3):
        current()
        # Keep the existing exchange limits: encode 30s, transport 75s,
        # decode 30s. This is an admission deadline, not a new process timer.
        if deadline - time.monotonic() < 135:
            raise TimeoutError('Native bootstrap readiness budget exhausted')
        value = call(ship, 'bootstrap', {'protocol': 'stead.bootstrap/1', 'nonce': nonce},
                     route='/bootstrap/' + nonce, target=ship,
                     app='stead-home' if ship == 'zod' else 'stead-identity', timeout=75)
        current()
        if time.monotonic() >= deadline:
            raise TimeoutError('Native bootstrap acknowledgement arrived after deadline')
        if (isinstance(value, dict)
                and set(value) == {'protocol', 'status', 'home', 'nonce', 'incarnation'}
                and value['protocol'] == 'stead.bootstrap/1' and value['status'] == 'ready'
                and value['home'] == '~' + ship and value['nonce'] == nonce
                and isinstance(value['incarnation'], str)
                and re.fullmatch(r'[0-9a-f]{64}', value['incarnation'])):
            return value
        if not (isinstance(value, dict)
                and set(value) == {'protocol', 'status', 'kind', 'trace', 'trace_jam_hex'}
                and value['protocol'] == 'stead.test-terminal/1' and value['status'] == 'failed'
                and value['kind'] == 'poke-fail' and isinstance(value['trace'], str)
                and isinstance(value['trace_jam_hex'], str)
                and re.fullmatch(r'(?:[0-9a-f]{2})+', value['trace_jam_hex'])):
            raise ValueError('Native bootstrap acknowledgement differs')
        # call() has already retained the completed refusal and native frame.
        time.sleep(.1)
    raise TimeoutError('Native bootstrap readiness not acknowledged')


def build_probe(ship, command, report, checkpoint, logs=Path('/state/logs')):
    """Retain only this fixed probe's bounded native interval for diagnosis."""
    if ship not in ('zod', 'bus', 'nec', 'bud'):
        raise ValueError('Unknown build probe ship')
    log = logs / (ship + '.log')
    offset = log.stat().st_size
    try:
        return command(ship, '+stead-build-probe', '%stead-builds-pass')
    finally:
        with log.open('rb') as stream:
            stream.seek(offset)
            captured = stream.read(262145)
        if len(captured) > 262144:
            raise ValueError('Native build probe log byte bound')
        rows = report.setdefault('build_probe_transcripts', [])
        if len(rows) >= 4 or any(row['ship'] == ship for row in rows):
            raise ValueError('Native build probe duplicate or count bound')
        rows.append({'ship': ship, 'dojo': '+stead-build-probe', 'log_offset': offset,
                     'log_bytes': len(captured), 'log_hex': captured.hex()})
        checkpoint('build-probe-output')


DIAGNOSTIC_BUDGET = 2 * 1024 * 1024
# The unchanged supervisor can subsequently attach a <=64KiB hosted lease
# summary. Reserve twice that bound below the worker's unchanged 4MiB reader.
DIAGNOSTIC_FINAL_BUDGET = 4 * 1024 * 1024 - 128 * 1024
BUILD_FAILURE_SHA = 'cd0bbd5af9e06ee8ec5279531dc9a3b89956535a2af3c33f61d5c14c4559998d'
DIAGNOSTIC_PHASES = ('startup', 'command', 'check', 'checkpoint', 'build', 'suite', 'final')


def diagnostic_bytes(value):
    """Exactly execution_policy.write_json's encoding, including its newline."""
    return (json.dumps(value, sort_keys=True) + '\n').encode()


def budget_stop(report, staged_raw, phase, path, limit):
    if phase not in DIAGNOSTIC_PHASES or not isinstance(path, str):
        raise ValueError('Native diagnostic budget identity')
    report['diagnostic_budget_stop'] = {
        'phase': phase, 'path': path, 'staged_bytes': len(staged_raw),
        'staged_sha256': hashlib.sha256(staged_raw).hexdigest(),
        'retained_bytes': len(diagnostic_bytes(report)), 'limit_bytes': limit,
        'omitted': True}


def retain_diagnostic(report, staged, phase, path=''):
    """Commit a complete bounded row transaction; never append then trim."""
    raw = diagnostic_bytes(staged)
    if len(raw) > DIAGNOSTIC_BUDGET:
        budget_stop(report, raw, phase, path, DIAGNOSTIC_BUDGET)
        raise ValueError('Native diagnostic evidence budget reached')
    report.clear()
    report.update(staged)


def diagnostic_error(report, error, phase, path='', evidence=None):
    """Abort evidence is closed metadata, never a large exception/trace payload."""
    kinds = ('AssertionError', 'ValueError', 'TypeError', 'RuntimeError', 'TimeoutError',
             'OSError', 'ConnectionError', 'ConnectionResetError', 'BrokenPipeError',
             'PermissionError', 'FileNotFoundError', 'InterruptedError', 'GuardError',
             'CalledProcessError', 'TimeoutExpired', 'JSONDecodeError', 'UnicodeDecodeError')
    kind = type(error).__name__
    kind = kind if kind in kinds else 'unrecognized'
    raw = diagnostic_bytes(evidence) if evidence is not None else b''
    report.setdefault('diagnostic_interruption', {
        'phase': phase, 'path': path, 'error_class': kind,
        'evidence_bytes': len(raw), 'evidence_sha256': hashlib.sha256(raw).hexdigest() if raw else None,
        'raw_evidence_omitted': True})
    fixed = ('Pure-unit diagnostic complete; qualification disabled',
             'Native diagnostic evidence budget reached', 'Native diagnostic build result refused')
    message = str(error) if type(error) is ValueError and error.args in [(v,) for v in fixed] else 'Native diagnostic interrupted'
    report['error'] = kind + ': ' + message


def finalize_diagnostic(report, before, after, elapsed):
    staged = copy.deepcopy(report)
    staged.update(status='fail', qualifies_phase=False, inputs_after=after,
                  elapsed_seconds=elapsed, stage='failed')
    if before != after:
        staged['error'] = 'ValueError: Configured source/input changed during execution'
    raw = diagnostic_bytes(staged)
    if len(raw) > DIAGNOSTIC_FINAL_BUDGET:
        budget_stop(report, raw, 'final', '', DIAGNOSTIC_FINAL_BUDGET)
        report.update(status='fail', qualifies_phase=False, stage='failed',
                      elapsed_seconds=elapsed,
                      error='ValueError: Native diagnostic evidence budget reached')
        # inputs_after was omitted; the existing verifier cannot infer equality.
        report.pop('inputs_after', None)
    else:
        report.clear()
        report.update(staged)
    if len(diagnostic_bytes(report)) > DIAGNOSTIC_FINAL_BUDGET:
        raise ValueError('Native diagnostic final evidence bound')


def completed_build_probe(host, report, checkpoint, logs=Path('/state/logs')):
    """Only exact completed zod success/observed compile refusal can continue."""
    if not isinstance(report.get('commands'), list) or not isinstance(report.get('checks'), list):
        raise ValueError('Native diagnostic build result refused')
    if any(not isinstance(row, dict) or row.get('passed') is not True for row in report['checks']):
        raise ValueError('Native diagnostic build result refused')
    if any(row.get('dojo') == '+stead-build-probe' for row in report['commands']):
        raise ValueError('Native diagnostic build result refused')
    if report.get('build_probe_transcripts'):
        raise ValueError('Native diagnostic build result refused')
    if any(row.get('name') == 'zod:+stead-build-probe' for row in report['checks']):
        raise ValueError('Native diagnostic build result refused')
    log = logs / 'zod.log'
    offset = log.stat().st_size
    terminal = None
    captured = b''
    try:
        try:
            terminal = host['dojo']('zod', '+stead-build-probe')
        finally:
            with log.open('rb') as stream:
                stream.seek(offset)
                captured = stream.read(262145)
            if len(captured) > 262144:
                raise ValueError('Native build probe log byte bound')
        if not isinstance(terminal, str) or len(terminal.encode()) > 32768:
            raise ValueError('Native diagnostic build result refused')
        expected = terminal.strip() == '%stead-builds-pass'
        known_failure = (len(terminal.encode()) == 50
                         and hashlib.sha256(terminal.encode()).hexdigest() == BUILD_FAILURE_SHA)
        staged = copy.deepcopy(report)
        staged['commands'].append({'ship': 'zod', 'dojo': '+stead-build-probe', 'result': terminal})
        staged['checks'].append({'name': 'zod:+stead-build-probe', 'passed': expected})
        staged['build_probe_transcripts'] = [{'ship': 'zod', 'dojo': '+stead-build-probe',
            'log_offset': offset, 'log_bytes': len(captured), 'log_hex': captured.hex()}]
        retain_diagnostic(report, staged, 'build')
        checkpoint('build-probe-output')
        if not (expected or known_failure):
            raise ValueError('Native diagnostic build result refused')
        commands = [row for row in report['commands'] if row.get('dojo') == '+stead-build-probe']
        checks = [row for row in report['checks'] if row.get('name') == 'zod:+stead-build-probe']
        if (commands != [{'ship': 'zod', 'dojo': '+stead-build-probe', 'result': terminal}]
                or checks != [{'name': 'zod:+stead-build-probe', 'passed': expected}]
                or type(checks[0].get('passed')) is not bool
                or report.get('build_probe_transcripts') != [{'ship': 'zod', 'dojo': '+stead-build-probe',
                    'log_offset': offset, 'log_bytes': len(captured), 'log_hex': captured.hex()}]
                or report.get('stage') != 'build-probe-output'):
            raise ValueError('Native diagnostic build result refused')
        host['execution_check']()
        return 'pass' if expected else 'compile-failed'
    except Exception as error:
        diagnostic_error(report, error, 'build', evidence={
            'terminal': terminal, 'log_bytes': len(captured),
            'log_sha256': hashlib.sha256(captured).hexdigest()})
        raise


def run(host):
    started = time.monotonic()
    report = {'status': 'fail', 'classification': 'local-real-configured-gall-development',
              'qualifies_phase': False, 'checks': [], 'commands': [], 'installed': {},
              'scope': 'Dedicated build and pure-suite diagnostics only; no later ship startup, Gall journey, capture or qualification.',
              'diagnostic_only': True}
    path = Path('/state/logs') / ('team-check-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')

    def inputs():
        return {'native': tree_sha(Path('/native/core/desk')), 'runner': closure(),
                'harness': source_sha(CODE), 'ingress': tree_sha(Path('/web-dev')),
                'toolchain': sha('/toolchain.json'), 'native_unit_inventory': sha('/specs/phase2-pure-units.json')}

    before = inputs()
    report['inputs_before'] = before

    def checkpoint(stage):
        staged = dict(report, stage=stage)
        retain_diagnostic(report, staged, 'checkpoint')
        execution_policy.write_json(path, report)

    def check(name, condition):
        staged = copy.deepcopy(report)
        staged['checks'].append({'name': name, 'passed': bool(condition)})
        retain_diagnostic(report, staged, 'check')
        checkpoint('running')
        if not condition:
            raise AssertionError(name)

    def command(ship, source, expected=None, *, timeout=None):
        result = host['dojo'](ship, source, **({'timeout': timeout} if timeout is not None else {}))
        staged = copy.deepcopy(report)
        staged['commands'].append({'ship': ship, 'dojo': source, 'result': result})
        retain_diagnostic(report, staged, 'command')
        checkpoint('native-command')
        if expected is not None:
            check(ship + ':' + source, result.strip() == expected)
        return result

    binary = '/runtime/' + host['LOCK']['runtime']['binary']

    def call(ship, mode, value=None, *, target='zod', app='stead-home', route=None, timeout=75):
        host['execution_check']()
        raw = canonical(value) if value is not None else b''
        if route is None and mode in ('command', 'query', 'updates'):
            domain = {'command': 'stead.command/3', 'query': 'stead.query/3', 'updates': 'stead.updates/3'}[mode]
            digest = hashlib.sha256(domain.encode() + b'\0' + raw).hexdigest()
            binding = uid(202 + ('bus', 'nec').index(ship)) if ship in ('bus', 'nec') else uid(299)
            route = '/v3/result/~' + ship + '/' + binding + '/1/' + value['request_id'] + '/' + digest
        result = team_conn.run(binary, host['LIVE'] / ship / '.urb/conn.sock', mode,
                               route or '/', raw, target=target, app=app, timeout=timeout)
        observed = {key: result[key] for key in ('stdout', 'stderr', 'response_frame_sha256',
                    'request', 'request_frame_hex', 'response_frame_hex', 'outcome')}
        report['commands'].append({'ship': ship, 'mode': mode, 'app': app, 'target': target,
            'input_sha256': hashlib.sha256(raw).hexdigest(), 'input_hex': raw.hex(), 'route': route, **observed})
        checkpoint('native-call')
        outcome = (result.get('outcome') or {}).get('json')
        if outcome is None:
            raise RuntimeError('Native thread failed without an explicit observed outcome')
        if outcome.get('protocol') == 'stead.test-terminal/1' and outcome.get('kind') not in ('poke-fail', 'watch-ack-fail'):
            raise RuntimeError('Native thread failure: ' + outcome.get('kind', 'missing kind'))
        return outcome

    def denied(value, kind, marker):
        return (value.get('protocol') == 'stead.test-terminal/1' and value.get('status') == 'failed'
                and value.get('kind') == kind
                and any(line.strip() in (marker, '%' + marker)
                        for line in value.get('trace', '').splitlines()))

    def pure_units():
        inventory = native_units.validate_inventory(json.loads(Path('/specs/phase2-pure-units.json').read_text()))
        for dependency in ('ted/test.hoon', 'mar/path.hoon'):
            pinned = (Path('/kernel/pkg/arvo') / dependency).resolve(strict=True)
            if not pinned.is_relative_to('/kernel'):
                raise ValueError('Pinned unit dependency escapes kernel tree')
            literal = core_conn.atom(bytes.fromhex(sha(pinned))[::-1])
            route = '/' + dependency.replace('.hoon', '/hoon')
            command('zod', f'=/  raw=@t  .^(@t %cx /=base={route})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))', '%.y')
        staged = copy.deepcopy(report)
        staged.update(native_units=[], native_unit_failures=[], native_unit_transcripts=[])
        retain_diagnostic(report, staged, 'startup')
        pending = {}

        def execute(entry):
            host['execution_check']()
            pending.clear()
            source = '`path`%' + entry['path']
            resolved = host['dojo']('zod', source)
            if not isinstance(resolved, str) or len(resolved.encode()) > 32768:
                raise ValueError('Native diagnostic beam result bound')
            resolution = {'ship': 'zod', 'dojo': source, 'result': resolved}
            log = Path('/state/logs/zod.log')
            offset = log.stat().st_size
            terminal, captured = '', b''
            unit_started = time.monotonic()
            host['record']('native unit start', {'path': entry['path'], 'expected_arms': len(entry['arms'])})
            try:
                try:
                    observed = native_units.run(binary, host['LIVE'] / 'zod/.urb/conn.sock',
                        resolved.strip(), timeout=entry.get('timeout_seconds', 60))
                    terminal = observed['stdout']
                finally:
                    with log.open('rb') as stream:
                        stream.seek(offset)
                        captured = stream.read(262145)
                    if len(captured) > 262144:
                        raise ValueError('Native unit log byte bound')
                pending.update(commands=[resolution, {'ship': 'zod', 'native_test': observed}],
                    transcript={'path': entry['path'], 'log_offset': offset,
                        'log_bytes': len(captured), 'log_hex': captured.hex(), 'terminal': terminal})
                return captured.decode('utf-8', errors='strict') + '\n' + terminal
            except Exception as error:
                diagnostic_error(report, error, 'suite', entry['path'], evidence={
                    'native_failure': getattr(error, 'native_failure', None),
                    'log_bytes': len(captured), 'log_sha256': hashlib.sha256(captured).hexdigest()})
                raise
            finally:
                host['record']('native unit captured', {'path': entry['path'], 'log_bytes': len(captured),
                    'elapsed_seconds': round(time.monotonic() - unit_started, 3), 'terminal_present': bool(terminal)})

        def verify(entry, completed):
            return native_units.verify_output(completed, path=entry['path'], expected=entry['arms'],
                succeeds=entry != inventory['negative_control'], failure_marker=entry.get('marker'))

        def retain(entry, verified):
            staged = copy.deepcopy(report)
            staged['commands'].extend(pending['commands'])
            staged['native_unit_transcripts'].append(pending['transcript'])
            if verified is None:
                staged['native_unit_failures'].append(entry['path'])
            else:
                staged['native_units'].append(verified)
                negative = entry == inventory['negative_control']
                staged['checks'].append({'name': 'native-unit-' +
                    ('expected-failure:' if negative else 'arms:') + entry['path'], 'passed': True})
            retain_diagnostic(report, staged, 'suite', entry['path'])
            checkpoint('native-unit-diagnostic-failure' if verified is None else 'native-unit-output')
            pending.clear()

        # The dedicated controller always stops here, even when the app and
        # all49 completed suites pass. No later ship/Gall/journey/capture runs.
        native_units.collect_pure_diagnostics([*inventory['suites'], inventory['negative_control']],
            execute, verify, lambda entry, verified: retain(entry, verified),
            lambda entry: retain(entry, None))

    sequence = 1000

    def query(kind, *, project='', resource='', container='', cursor='', search=''):
        nonlocal sequence
        sequence += 1
        return {'protocol': 'stead.query/3', 'request_id': uid(sequence), 'kind': kind,
                'project_id': project, 'resource_id': resource, 'container_id': container,
                'cursor': cursor, 'search': search}

    def mutation(operation, resource, expected, payload, *, project=None):
        nonlocal sequence
        sequence += 1
        return {'protocol': 'stead.command/3', 'request_id': uid(sequence), 'project_id': project or uid(1),
                'resource_id': resource, 'expected_revision': str(expected), 'authority_epoch': '1',
                'operation': operation, 'payload': payload}

    try:
        checkpoint('admission')
        team = host.get('TEAM')
        check('configured-startup-controller-present', team is not None)
        before_guard = host['execution_check'](preflight=True)
        check('loaded-runner-source', LOADED_CLOSURE == before['runner'])
        check('loaded-supervisor-source', host['LOADED_SOURCE_DIGEST'] == before['harness'])
        check('loaded-ingress-source', host['team_lifecycle'].LOADED_INGRESS_DIGEST == before['ingress'])
        host['all_stop']()
        host['copy_seed_to_live']()
        for ship in host['SHIPS']:
            if ship != 'zod':
                raise ValueError('Dedicated diagnostic cannot start a later ship')
            host['launch'](ship, fresh=True)
            host['wait_ready'](ship)
            installed = native_install.install(host, ship, command, check)
            staged = copy.deepcopy(report)
            staged['installed'][ship] = installed
            retain_diagnostic(report, staged, 'startup')
            completed_build_probe(host, report, checkpoint)
            if ship == 'zod':
                pure_units()
                raise ValueError('Dedicated diagnostic collector unexpectedly returned')
                command('zod', '+stead-team-contract-probe', '%stead-team-contract-basic-pass')
                command('zod', '+stead-team-authority-probe', '%stead-team-authority-basic-pass', timeout=300)
        command('zod', '|start %stead-home')
        command('zod', '|start %stead-http-boundary-probe')
        for ship in ('bus', 'nec', 'bud'):
            command(ship, '|start %stead-identity')
        # This public synthetic probe has no secrets/content and intentionally
        # permits insecure transport to test the actual kernel provenance.
        with urllib.request.urlopen('http://127.0.0.1:18080/stead-boundary-probe/', timeout=10) as response:
            raw = response.read(4097)
            check('bounded-provenance-response', len(raw) <= 4096)
            probe = json.loads(raw)
        report['http_provenance'] = probe
        check('actual-anonymous-eyre-provenance', probe.get('protocol') == 'stead.http-boundary-probe/1'
              and probe.get('src') != '~zod' and probe.get('owner_authenticated') == 'no' and probe.get('secure') == 'no')
        # Installing a certificate enables Eyre's HTTP -> HTTPS redirect. Keep
        # the insecure provenance control above, then verify TLS before admission.
        for ship in host['SHIPS']:
            native_tls.install(binary, host['LIVE'] / ship / '.urb/conn.sock', team.certificates, ship)
            check(ship + '-certificate-task-requested', True)
        now = int(command('zod', '(div (mul 1.000 (sub now ~1970.1.1)) ~s1)').strip().replace('.', ''))
        config = configuration(now)
        check('fake-ship-cannot-configure-live-pilot', denied(call('zod', 'configure', config | {
            'custody': 'operator-pilot', 'runtime': 'live-synthetic'}), 'poke-fail', 'stead-runtime-profile-mismatch'))
        check('owner-configuration-accepted', call('zod', 'configure', config) == {})
        nonce = secrets.token_hex(32)
        status = call('zod', 'operator-status', route='/operator/' + nonce)
        check('startup-operator-status-owner-read', status['protocol'] == 'stead.operator-status/1'
              and status['nonce'] == nonce and status['runtime'] == 'isolated-fake'
              and status['runtime_matches'] == 'yes' and status['available'] == 'no')
        for offset, ship in enumerate(('bus', 'nec', 'bud'), start=8444):
            personal = {'protocol': 'stead.identity-config/1', 'expected_revision': '0',
                        'home': '~zod', 'home_origin': config['origin'],
                        'origin': f'https://{ship}.localhost:{offset}'}
            check(ship + '-owner-identity-configuration', call(ship, 'identity-config', personal,
                  target=ship, app='stead-identity') == {})
        for ship in host['SHIPS']:
            nonce = team.boots[ship]['nonce']
            boot = bootstrap_ready(team, ship, call, host['execution_check'])
            check(ship + '-owner-bootstrap-acknowledged', boot is not None and boot.get('nonce') == nonce
                  and boot.get('home') == '~' + ship and boot.get('status') == 'ready')
            team.admit(ship, boot, host['dojo'])
            check(ship + '-owned-peer-admission', team.boots[ship]['acknowledged'])
        # Prepared inspection-only successor. New fresh fixture, before any
        # Work/Code pilot scenario. This always refuses qualification afterward.
        import sys
        sys.path.insert(0, '/fingerprint/scripts')
        import release_install
        import product_controller
        product_controller.run(host, legacy=call, command=command, check=check,
            checkpoint=checkpoint, report=report, config=config, now=now,
            release_fingerprint=release_install.saved_home_fingerprint,
            release_source_sha256=sha('/fingerprint/scripts/release_install.py'))
        check('remote-configuration-denied', denied(call('bus', 'configure', config | {'expected_revision': '1'}),
              'poke-fail', 'stead-owner-required'))
        check('remote-operator-status-denied', denied(call('bus', 'operator-status', route='/operator/' + secrets.token_hex(32)),
              'watch-ack-fail', 'stead-owner-required'))
        identity = call('bus', 'query', query('identity'))
        check('current-native-member-read', identity is not None and identity.get('status') == 'read')
        check('native-outsider-denied', denied(call('bud', 'query', query('identity')),
              'watch-ack-fail', 'stead-current-member-required'))
        capabilities_query = query('capabilities')
        capabilities = call('bus', 'query', capabilities_query)
        check('native-public-capabilities-current-member',
              capabilities_match(capabilities, capabilities_query['request_id']))
        check('native-capabilities-unbound-sender-denied', denied(call('bud', 'query', query('capabilities')),
              'watch-ack-fail', 'stead-current-member-required'))
        create = mutation('project.create', uid(1), 0, {'organization_id': uid(5), 'owning_team_id': uid(6), 'title': 'Garden α', 'project_key': 'GARDEN', 'preset': 'general'})
        for mode in ('command', 'query', 'updates'):
            domain = {'command': 'stead.command/3', 'query': 'stead.query/3', 'updates': 'stead.updates/3'}[mode]
            for version in ('1', '2', '999'):
                seed = create if mode == 'command' else query('projects')
                if mode == 'updates':
                    seed = {**seed, 'action': 'open', 'watch_id': ''}
                bad = {**seed, 'protocol': domain.rsplit('/', 1)[0] + '/' + version}
                outcome = call('bus', mode, bad)
                check('native-' + mode + '-version-' + version + '-correlated-rejection', outcome == {
                    'protocol': 'stead.result/3', 'status': 'rejected', 'error': 'unsupported_version',
                    'request_id': bad['request_id'],
                    'canonical_sha256': hashlib.sha256(domain.encode() + b'\0' + canonical(bad)).hexdigest()})
        legacy = {**create, 'protocol': 'stead.command/2'}
        legacy_digest = hashlib.sha256(b'stead.command/2\0' + canonical(legacy)).hexdigest()
        legacy_route = '/v2/result/~bus/' + uid(102) + '/' + uid(1) + '/' + legacy['request_id'] + '/' + legacy_digest
        for mode, kind in (('legacy-poke', 'poke-fail'), ('legacy-watch', 'watch-ack-fail')):
            outcome = call('bus', mode, legacy, route=legacy_route)
            check('native-' + mode + '-configured-home-refuses-v2-carrier',
                  outcome.get('protocol') == 'stead.test-terminal/1' and outcome.get('status') == 'failed'
                  and outcome.get('kind') == kind and bool(outcome.get('trace_jam_hex')))
        check('native-unsupported-commands-do-not-create-project', call('bus', 'query', query('projects')).get('rows') == {})
        receipt = call('bus', 'command', create)
        check('explicit-creator-project-accepted', receipt is not None and receipt.get('status') == 'accepted'
              and receipt.get('identity_ship') == '~bus' and receipt.get('authentication') == 'native-sender/1'
              and receipt.get('principal_id') == uid(102))
        check('duplicate-native-command-idempotent', call('bus', 'command', create) == receipt)
        check('ungranted-member-no-project', call('nec', 'query', query('project', project=uid(1))).get('error') == 'denied_or_not_found')
        grant = mutation('policy.grant', uid(1), 1, {'grant_id': uid(21), 'principal_id': uid(103), 'role': 'reader', 'expires_at_ms': str(now + 3600000)})
        check('explicit-reader-grant-accepted', call('bus', 'command', grant).get('status') == 'accepted')
        check('granted-native-reader', call('nec', 'query', query('project', project=uid(1))).get('status') == 'read')
        work = mutation('work.create', uid(10), 0, {'title': 'Native task', 'description': 'Synthetic two-user control', 'type': 'task', 'status': 'todo', 'priority': 'medium'})
        check('native-reader-write-denied', call('nec', 'command', work).get('error') == 'denied_or_not_found')
        check('native-maintainer-write-accepted', call('bus', 'command', work).get('status') == 'accepted')
        rows = call('nec', 'query', query('work', project=uid(1))).get('rows', {})
        check('actual-read-reflects-committed-work', len(rows) == 1 and next(iter(rows.values())).get('title') == 'Native task')
        stale = mutation('work.update', uid(10), 2, work['payload'])
        check('native-stale-revision-rejected', call('bus', 'command', stale).get('error') == 'revision_conflict')
        def git_probe(project, container, head):
            observed = team_git.probe(command, project, container, head)
            report.setdefault('git_export_probes', []).append(observed)
            check('native-git-export-manifest-and-commit-' + str(len(report['git_export_probes'])), True)

        restart_watch = team_updates_check.run(call, check, query, mutation, uid, now, git_probe)
        report['restarts'] = {}
        for ship in host['SHIPS']:
            checkpoint('cold-restart-' + ship)
            old = dict(team.boots[ship])
            saved = team.prepare_restart(ship, host['dojo'])
            host['shutdown'](ship)
            check(ship + '-previous-child-reaped', old['process'].poll() == 0)
            host['launch'](ship)
            host['wait_ready'](ship)
            check(ship + '-saved-app-suspended-before-reload', team.boots[ship]['suspended']
                  and team.boots[ship]['present'] and team.saved_fingerprint(ship, host['dojo']) == saved)
            team.reinstall(ship, host['dojo'])
            nonce = team.boots[ship]['nonce']
            boot = bootstrap_ready(team, ship, call, host['execution_check'])
            check(ship + '-restart-fresh-bootstrap', boot is not None and nonce != old['nonce']
                  and boot.get('nonce') == nonce and boot.get('status') == 'ready')
            team.admit(ship, boot, host['dojo'])
            report['restarts'][ship] = {'saved_vase_sha256': saved,
                                       'new_incarnation': boot['incarnation'], 'passed': True}
        check('restart-preserves-exact-command-receipt', call('bus', 'command', create) == receipt)
        rows = call('nec', 'query', query('work', project=uid(1))).get('rows', {})
        check('restart-preserves-authorized-work', len(rows) == 1 and next(iter(rows.values())).get('title') == 'Native task')
        retired = call('nec', 'updates', restart_watch)
        check('restart-invalidates-native-update-cursor-and-watch', retired.get('status') == 'refresh_required'
              and retired.get('rows') == {} and retired.get('generation') == '' and retired.get('cursor') == '')
        # Public disposable fixture ticket. Never use a live operator's ticket
        # in this runner, which retains raw native request frames.
        checkpoint('sealed-home-restart')
        ticket = 'a' * 64
        challenge = hashlib.sha256(b'stead.home-handoff/1\0~zod/2/' + ticket.encode()).hexdigest()
        handoff_route = '/home-handoff/status'
        state = {'protocol': 'stead.home-handoff/1', 'home': '~zod', 'phase': 'open', 'generation': '1'}
        check('handoff-initial-status', call('zod', 'handoff-status', route=handoff_route) == state)
        check('handoff-owner-only-status', call('bus', 'handoff-status', route=handoff_route).get('kind') == 'watch-ack-fail')
        seal = {'operation': 'seal', 'generation': '1', 'proof': challenge}
        check('handoff-remote-seal-denied', call('bus', 'handoff', seal).get('kind') == 'poke-fail')
        moving = uid(980)
        moving_create = mutation('project.create', moving, 0,
                                 create['payload'] | {'title': 'Moving', 'project_key': 'MOVING'}, project=moving)
        check('project-retirement-source-created', call('bus', 'command', moving_create).get('status') == 'accepted')
        retirement_route = '/project-retirement/' + moving
        active = call('zod', 'project-retirement-status', route=retirement_route)
        check('project-retirement-head-observed', active.get('writer_state') == 'active'
              and active.get('authority_epoch') == '1' and active.get('project_id') == moving
              and re.fullmatch(r'[0-9a-f]{64}', active.get('journal_head', '')))
        check('project-retirement-owner-only-status',
              call('bus', 'project-retirement-status', route=retirement_route).get('kind') == 'watch-ack-fail')
        retirement = {'protocol': 'stead.project-retire/1', 'project_id': moving, 'migration_id': uid(981),
                      'authority_epoch': '1', 'destination_home': '~nec', 'expected_journal_head': active['journal_head']}
        check('project-retirement-owner-only-write', call('bus', 'project-retire', retirement).get('kind') == 'poke-fail')
        check('project-retirement-stale-head',
              call('zod', 'project-retire', retirement | {'expected_journal_head': '0' * 64}).get('kind') == 'poke-fail')
        check('project-retirement-accepted', call('zod', 'project-retire', retirement) == {})
        fenced = call('zod', 'project-retirement-status', route=retirement_route)
        check('project-retirement-observed', fenced.get('writer_state') == 'retired'
              and fenced.get('journal_head') == retirement['expected_journal_head']
              and fenced.get('migration_id') == retirement['migration_id'])
        check('project-retirement-repeat-and-conflict', call('zod', 'project-retire', retirement) == {}
              and call('zod', 'project-retirement-status', route=retirement_route) == fenced
              and call('zod', 'project-retire', retirement | {'migration_id': uid(982)}).get('kind') == 'poke-fail')
        frozen_work = mutation('work.create', uid(983), 0, work['payload'], project=moving)
        check('project-retirement-fresh-write-denied', call('bus', 'command', frozen_work).get('error') == 'authority_retired')
        check('project-retirement-replay-write-denied', call('bus', 'command', moving_create).get('error') == 'authority_retired')
        check('project-retirement-authorized-reads-retained', call('bus', 'query', query('project', project=moving)).get('status') == 'read')
        check('project-retirement-unrelated-write-accepted', call('bus', 'command', mutation('work.create', uid(984), 0, work['payload'])).get('status') == 'accepted')
        rows = call('nec', 'query', query('work', project=uid(1))).get('rows')
        check('handoff-owner-seals', call('zod', 'handoff', seal) == {})
        sealed = state | {'phase': 'sealed', 'generation': '2'}
        check('handoff-seal-observed', call('zod', 'handoff-status', route=handoff_route) == sealed)
        blocked = mutation('work.create', uid(999), 0, work['payload'])
        check('handoff-seal-denies-member-write', call('bus', 'command', blocked).get('kind') == 'watch-ack-fail')
        old = dict(team.boots['zod'])
        saved = team.prepare_restart('zod', host['dojo'])
        host['shutdown']('zod')
        check('handoff-source-child-reaped', old['process'].poll() == 0)
        host['launch']('zod')
        host['wait_ready']('zod')
        check('handoff-sealed-vase-preserved', team.boots['zod']['suspended']
              and team.saved_fingerprint('zod', host['dojo']) == saved)
        team.reinstall('zod', host['dojo'])
        check('handoff-reload-preserves-seal', call('zod', 'handoff-status', route=handoff_route) == sealed)
        nonce = team.boots['zod']['nonce']
        check('handoff-seal-denies-bootstrap', call('zod', 'bootstrap', {'protocol': 'stead.bootstrap/1', 'nonce': nonce},
              route='/bootstrap/' + nonce).get('kind') == 'watch-ack-fail')
        activate = {'operation': 'activate', 'generation': '2', 'proof': ticket}
        check('handoff-wrong-ticket-denied', call('zod', 'handoff', activate | {'proof': 'b' * 64}).get('kind') == 'poke-fail')
        check('handoff-stale-generation-denied', call('zod', 'handoff', activate | {'generation': '1'}).get('kind') == 'poke-fail')
        check('handoff-activates-once', call('zod', 'handoff', activate) == {}
              and call('zod', 'handoff', activate).get('kind') == 'poke-fail')
        check('handoff-open-next-generation', call('zod', 'handoff-status', route=handoff_route) == (sealed | {'phase': 'open'}))
        boot = bootstrap_ready(team, 'zod', call, host['execution_check'])
        check('handoff-fresh-incarnation', boot['incarnation'] != report['restarts']['zod']['new_incarnation'])
        team.admit('zod', boot, host['dojo'])
        check('project-retirement-restart-preserves-record', call('zod', 'project-retirement-status', route=retirement_route) == fenced)
        check('project-retirement-restart-denies-write', call('bus', 'command', frozen_work).get('error') == 'authority_retired')
        check('handoff-original-receipt-preserved', call('bus', 'command', create) == receipt)
        check('handoff-reader-work-preserved', call('nec', 'query', query('work', project=uid(1))).get('rows') == rows)
        # Private operator fixture material. Never put +code/cert keys in the
        # portable report, command transcript, UI bundle or support exports.
        operator = {'format': 1, 'classification': 'private-disposable-browser-fixture',
                    'execution_id': before_guard['run_id'], 'origin': config['origin'],
                    'identities': {ship: {'hostname': native_tls.HOSTS[ship],
                                         'code': host['dojo'](ship, '+code').strip().strip('~')}
                                   for ship in host['SHIPS']}}
        execution_policy.write_json(team.directory / 'browser-fixture.json', operator)
        host['execution_check']()
        report['status'] = 'pass'
    except Exception as error:
        diagnostic_error(report, error, 'final', evidence=getattr(error, 'native_failure', None))
        traceback.print_exc()
    after = inputs()
    finalize_diagnostic(report, before, after, round(time.monotonic() - started, 3))
    execution_policy.write_json(path, report)
    return {key: report[key] for key in ('status', 'classification', 'qualifies_phase', 'scope', 'elapsed_seconds')} | {
        'error': report.get('error'), 'checks_passed': sum(row['passed'] for row in report['checks']),
        'evidence_file': '.piers/fakes/logs/' + path.name}

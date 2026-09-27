"""Actual configured Gall development lane. Browser/TLS acceptance is separate."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
import traceback
import urllib.request
import core_conn
import execution_policy
import native_install
import native_tls
import native_units
import team_conn
import team_updates_check
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
DEPENDENCIES = ('team_check.py', 'team_conn.py', 'core_conn.py', 'native_install.py',
                'team_lifecycle.py', 'native_peer_fence.py', 'native_tls.py', 'native_units.py', 'owned_child.py', 'execution_policy.py', 'team_updates_check.py')


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


def run(host):
    started = time.monotonic()
    report = {'status': 'fail', 'classification': 'local-real-configured-gall-development',
              'qualifies_phase': False, 'checks': [], 'commands': [], 'installed': {},
              'scope': 'Actual configured Gall, owned native TLS and cold restarts; browser acceptance is separate.'}
    path = Path('/state/logs') / ('team-check-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')

    def inputs():
        return {'native': tree_sha(Path('/native/core/desk')), 'runner': closure(),
                'harness': source_sha(CODE), 'ingress': tree_sha(Path('/web-dev')),
                'toolchain': sha('/toolchain.json'), 'native_unit_inventory': sha('/specs/phase2-pure-units.json')}

    before = inputs()
    report['inputs_before'] = before

    def checkpoint(stage):
        report['stage'] = stage
        execution_policy.write_json(path, report)

    def check(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        checkpoint('running')
        if not condition:
            raise AssertionError(name)

    def command(ship, source, expected=None, *, timeout=None):
        result = host['dojo'](ship, source, **({'timeout': timeout} if timeout is not None else {}))
        report['commands'].append({'ship': ship, 'dojo': source, 'result': result})
        checkpoint('native-command')
        if expected is not None:
            check(ship + ':' + source, result.strip() == expected)
        return result

    binary = '/runtime/' + host['LOCK']['runtime']['binary']

    def call(ship, mode, value=None, *, target='zod', app='stead-home', route=None):
        host['execution_check']()
        raw = canonical(value) if value is not None else b''
        if route is None and mode in ('command', 'query', 'updates'):
            domain = {'command': 'stead.command/3', 'query': 'stead.query/3', 'updates': 'stead.updates/3'}[mode]
            digest = hashlib.sha256(domain.encode() + b'\0' + raw).hexdigest()
            binding = uid(202 + ('bus', 'nec').index(ship)) if ship in ('bus', 'nec') else uid(299)
            route = '/v3/result/~' + ship + '/' + binding + '/1/' + value['request_id'] + '/' + digest
        result = team_conn.run(binary, host['LIVE'] / ship / '.urb/conn.sock', mode,
                               route or '/', raw, target=target, app=app)
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
        report['native_units'] = []
        for entry in [*inventory['suites'], inventory['negative_control']]:
            host['execution_check']()
            resolved = command('zod', '`path`%' + entry['path']).strip()
            log = Path('/state/logs/zod.log')
            offset = log.stat().st_size
            terminal = ''
            unit_started = time.monotonic()
            host['record']('native unit start', {'path': entry['path'], 'expected_arms': len(entry['arms'])})
            try:
                observed = native_units.run(binary, host['LIVE'] / 'zod/.urb/conn.sock', resolved, timeout=entry.get('timeout_seconds', 60))
                report['commands'].append({'ship': 'zod', 'native_test': observed})
                terminal = observed['stdout']
            except Exception as error:
                if hasattr(error, 'native_failure'):
                    report['commands'].append({'ship': 'zod', 'native_test_failure': error.native_failure})
                raise
            finally:
                with log.open('rb') as stream:
                    stream.seek(offset)
                    captured = stream.read(262145)
                report.setdefault('native_unit_transcripts', []).append({'path': entry['path'],
                    'log_offset': offset, 'log_bytes': len(captured), 'log_hex': captured.hex(), 'terminal': terminal})
                checkpoint('native-unit-output')
                host['record']('native unit captured', {'path': entry['path'], 'log_bytes': len(captured),
                    'elapsed_seconds': round(time.monotonic() - unit_started, 3), 'terminal_present': bool(terminal)})
            if len(captured) > 262144:
                raise ValueError('Native unit log byte bound')
            negative = entry == inventory['negative_control']
            verified = native_units.verify_output(captured.decode('utf-8', errors='strict') + '\n' + terminal,
                path=entry['path'], expected=entry['arms'], succeeds=not negative,
                failure_marker=entry.get('marker'))
            report['native_units'].append(verified)
            check('native-unit-' + ('expected-failure:' if negative else 'arms:') + entry['path'], True)

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
            host['launch'](ship, fresh=True)
            host['wait_ready'](ship)
            report['installed'][ship] = native_install.install(host, ship, command, check)
            command(ship, '+stead-build-probe', '%stead-builds-pass')
            if ship == 'zod':
                pure_units()
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
        check('owner-configuration-accepted', call('zod', 'configure', config) == {})
        for offset, ship in enumerate(('bus', 'nec', 'bud'), start=8444):
            personal = {'protocol': 'stead.identity-config/1', 'expected_revision': '0',
                        'home': '~zod', 'home_origin': config['origin'],
                        'origin': f'https://{ship}.localhost:{offset}'}
            check(ship + '-owner-identity-configuration', call(ship, 'identity-config', personal,
                  target=ship, app='stead-identity') == {})
        for ship in host['SHIPS']:
            nonce = team.boots[ship]['nonce']
            app = 'stead-home' if ship == 'zod' else 'stead-identity'
            boot = call(ship, 'bootstrap', {'protocol': 'stead.bootstrap/1', 'nonce': nonce},
                        route='/bootstrap/' + nonce, target=ship, app=app)
            check(ship + '-owner-bootstrap-acknowledged', boot is not None and boot.get('nonce') == nonce
                  and boot.get('home') == '~' + ship and boot.get('status') == 'ready')
            team.admit(ship, boot, host['dojo'])
            check(ship + '-owned-peer-admission', team.boots[ship]['acknowledged'])
        check('remote-configuration-denied', denied(call('bus', 'configure', config | {'expected_revision': '1'}),
              'poke-fail', 'stead-owner-required'))
        identity = call('bus', 'query', query('identity'))
        check('current-native-member-read', identity is not None and identity.get('status') == 'read')
        check('native-outsider-denied', denied(call('bud', 'query', query('identity')),
              'watch-ack-fail', 'stead-current-member-required'))
        capabilities = call('bus', 'query', query('capabilities'))
        check('native-public-capabilities-current-member', capabilities.get('rows') == {'capabilities': {
            'protocol': 'stead.capabilities/3', 'profile': 'configured-team', 'commands': 'stead.command/3',
            'queries': 'stead.query/3', 'updates': 'stead.updates/3', 'authentication': 'native-sender/1',
            'max_request_bytes': '65536', 'max_response_bytes': '262144', 'page_size': '20', 'runtime': 'isolated-fake'}})
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
        restart_watch = team_updates_check.run(call, check, query, mutation, uid, now)
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
            app = 'stead-home' if ship == 'zod' else 'stead-identity'
            boot = call(ship, 'bootstrap', {'protocol': 'stead.bootstrap/1', 'nonce': nonce},
                        route='/bootstrap/' + nonce, target=ship, app=app)
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
        report['error'] = type(error).__name__ + ': ' + str(error)
        if hasattr(error, 'native_failure'):
            report['native_failure'] = error.native_failure
        traceback.print_exc()
    report['inputs_after'] = inputs()
    if before != report['inputs_after']:
        report.update(status='fail', error='Configured source/input changed during execution')
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    checkpoint('completed' if report['status'] == 'pass' else 'failed')
    return {key: report[key] for key in ('status', 'classification', 'qualifies_phase', 'scope', 'elapsed_seconds')} | {
        'error': report.get('error'), 'checks_passed': sum(row['passed'] for row in report['checks']),
        'evidence_file': '.piers/fakes/logs/' + path.name}

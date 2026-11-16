"""Closed inspection of the prepared native-human-doc/1 controller report.

This never runs a runtime, starts a child, or turns authored records into native
execution evidence. The outer immutable controller must separately verify the
worker, fresh seeds, isolation, source composition and complete cleanup. This
verifier only reports the exact observed journey; it cannot qualify legacy Code,
full-product partial restore, browser use, service actors or agent execution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import core_conn
from conn import framed_length
from gall_schedule_proof import _atom, _cue, _jam
import product_conn
import product_capture
import product_controller
import product_home_check
import review_prepare
import team_check
import team_lifecycle
import native_peer_fence
import native_tls

HASH = re.compile(r'[0-9a-f]{64}')
SHIPS = ('zod', 'bus', 'nec', 'bud')
# Pinned hoon.hoon +po suffix table (4095–4110); no payload identity resolver.
SHIP_ATOMS = {'zod': 0, 'bus': 182, 'nec': 1, 'bud': 2}
DISABLED = 'RuntimeError: Prepared product controller inspection only: qualification disabled'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(left, right):
    """Closed JSON records must not equate false with 0, or 0.0 with 0."""
    encode = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()
    return encode(left) == encode(right)


def cell(*values):
    require(len(values) >= 2, 'Noun tuple arity')
    result = values[-1]
    for value in reversed(values[:-1]):
        result = (value, result)
    return result


def noun_list(values):
    result = 0
    for value in reversed(values):
        result = (value, result)
    return result


def frame_noun(encoded):
    require(isinstance(encoded, str) and 0 < len(encoded) <= 32778
            and len(encoded) % 2 == 0 and re.fullmatch(r'[0-9a-f]+', encoded), 'Bounded canonical native frame')
    raw = bytes.fromhex(encoded)
    require(len(raw) == 5 + framed_length(raw[:5]), 'Complete exact native frame required')
    return _cue(raw[5:])


def native_call(row, *, family, ship, mode, value, options):
    require(family in ('legacy', 'product') and ship in SHIPS, 'Closed native call family/sender')
    target = options.get('target', 'zod')
    app = options.get('app', 'stead-home')
    route = options.get('route')
    require(target in SHIPS and app in ('stead-home', 'stead-identity')
            and set(options) <= {'target', 'app', 'route', 'timeout'}
            and type(options.get('timeout', 75)) is int and options.get('timeout', 75) == 75,
            'Closed native target and deadline')
    raw = b'' if value is None else product_conn.canonical(value)
    require(len(raw) <= 65536 and not raw.endswith(b'\0'), 'Native input byte bound')
    if family == 'legacy' and route is None and mode in ('command', 'query', 'updates'):
        domain = {'command': 'stead.command/3', 'query': 'stead.query/3', 'updates': 'stead.updates/3'}[mode]
        binding = team_check.uid(202 + ('bus', 'nec').index(ship)) if ship in ('bus', 'nec') else team_check.uid(299)
        route = '/v3/result/~' + ship + '/' + binding + '/1/' + value['request_id'] + '/' + product_conn.digest(domain, raw)
    route = route or '/'
    require(isinstance(route, str) and len(route) <= 1024
            and re.fullmatch(r'/[a-zA-Z0-9~/._-]*', route), 'Native route bound')
    if family == 'legacy':
        require(mode in ('command', 'query', 'bootstrap'), 'Journey legacy mode')
        thread = 'stead-team-client'
    else:
        require(mode in (*product_conn.PROTOCOLS, 'owner-receipt', 'activate-paused')
                and target == 'zod' and app == 'stead-home', 'Journey product mode')
        require(mode != 'activate-paused' or ship == 'zod', 'Paused activation actual owner')
        thread = 'stead-product-checkpoint' if mode == 'activate-paused' else 'stead-product-check'
    require(set(row) == {'ship', 'mode', 'app', 'target', 'input_sha256', 'input_hex', 'route',
            'stdout', 'stderr', 'response_frame_sha256', 'request', 'request_frame_hex',
            'response_frame_hex', 'outcome'}, 'Exact native command observation')
    require(all(row[k] == v for k, v in {'ship': ship, 'mode': mode, 'app': app,
        'target': target, 'input_sha256': hashlib.sha256(raw).hexdigest(),
        'input_hex': raw.hex(), 'route': route}.items()), 'Native request correlation')
    parts = [part for part in route.split('/') if part]
    path = noun_list([_atom(part) for part in parts])
    target_noun = cell(SHIP_ATOMS[target], _atom(app), _atom(mode), path, int.from_bytes(raw, 'little'))
    request_noun = cell(32, _atom('fyrd'), cell(_atom('base'), _atom(thread), _atom('noun'),
                                                cell(_atom('noun'), target_noun)))
    require(frame_noun(row['request_frame_hex']) == request_noun, 'Native request frame differs')
    path_text = '[' + ' '.join(core_conn.atom(part.encode()) for part in parts) + ' ~]' if parts else '~'
    expected_text = f'[32 %fyrd [%base %{thread} %noun [%noun [~{target} %{app} %{mode} {path_text} {core_conn.atom(raw)}]]]]'
    require(row['request'] == expected_text, 'Native request text differs')
    require(isinstance(row['stdout'], str) and len(row['stdout']) <= 32768
            and isinstance(row['stderr'], str) and len(row['stderr']) <= 32768, 'Bounded native terminal text')
    decoded = core_conn.parse_response(row['stdout'])
    require(decoded is not None and same(decoded, row['outcome']), 'Actual native terminal/outcome correlation')
    response = bytes.fromhex(row['response_frame_hex'])
    require(row['response_frame_sha256'] == hashlib.sha256(response).hexdigest(), 'Native response frame hash')
    expected_response = cell(32, _atom('avow'), 0, _atom('noun'), _atom('stead-core-result'),
                             _atom(decoded['raw'].encode().hex()))
    require(frame_noun(row['response_frame_hex']) == expected_response, 'Native response frame differs')
    return decoded['json']


class Commands:
    def __init__(self, rows, start, end):
        require(type(start) is int and type(end) is int and 0 <= start <= end <= len(rows), 'Command slice bounds')
        self.rows, self.index, self.end = rows, start, end

    def next(self):
        require(self.index < self.end, 'Missing actual command observation')
        row = self.rows[self.index]
        self.index += 1
        return row

    def dojo(self, ship, source, **options):
        # The trusted fixed capture generator is the sole larger Dojo result.
        # Ordinary Dojo, Gall frames and aggregate report bounds stay unchanged.
        maximum = 100000 if ship == 'zod' and product_capture.is_source(source) else 32768
        require(not options, 'Unexpected fingerprint Dojo option')
        row = self.next()
        require(set(row) == {'ship', 'dojo', 'result'} and row['ship'] == ship and row['dojo'] == source
                and isinstance(row['result'], str) and len(row['result']) <= maximum, 'Exact actual Dojo source/result correlation')
        return row['result']

    def done(self):
        require(self.index == self.end, 'Extra actual command observation')


def fingerprints(commands, release_fingerprint):
    class Native:
        def dojo(self, source):
            return commands.dojo('zod', source)
    value = {'release_authority': release_fingerprint(Native(), authoritative=True),
             'review_authority': review_prepare.durable_fingerprint('zod', commands.dojo),
             'release_vase': release_fingerprint(Native()),
             'lifecycle_vase': team_lifecycle.TeamLifecycle.saved_fingerprint(None, 'zod', commands.dojo)}
    require(all(isinstance(v, str) and HASH.fullmatch(v) for v in value.values())
            and value['release_authority'] == value['review_authority']
            and value['release_vase'] == value['lifecycle_vase'], 'Actual fingerprint helper agreement')
    return value


def injection(value, ship):
    app = team_lifecycle.APPS[ship]
    source = f'[[%g %stead-startup ~] [%idle %{app}]]'
    encoded = _jam(cell(cell(_atom('g'), _atom('stead-startup'), 0), cell(_atom('idle'), _atom(app))))
    require(set(value) == {'source', 'jam_sha256', 'bytes', 'seals', 'encoder_stderr'}
            and type(value['bytes']) is int and type(value['seals']) is int
            and value['source'] == source and value['bytes'] == len(encoded)
            and value['jam_sha256'] == hashlib.sha256(encoded).hexdigest()
            and value['seals'] == 15 and isinstance(value['encoder_stderr'], str)
            and len(value['encoder_stderr']) <= 8192, 'Exact sealed startup idle injection')


def verify_observation(report, inputs, *, release_fingerprint):
    """Inspect only. Outer worker trust/cleanup is a separate mandatory gate."""
    require(isinstance(report, dict) and len(json.dumps(report).encode()) <= 4 * 1024 * 1024,
            'Bounded product report required')
    require(report.get('status') == 'fail' and report.get('error') == DISABLED
            and report.get('qualifies_phase') is False, 'Prepared report must refuse qualification')
    require(same(report['inputs_before'], report['inputs_after'])
            and same(report['inputs_after'], inputs['expected_native_inputs']), 'Native source/input changed')
    modules = {'scripts/urbit/product_capture.py': product_capture, 'scripts/urbit/product_controller.py': product_controller,
        'scripts/urbit/product_conn.py': product_conn, 'scripts/urbit/product_home_check.py': product_home_check,
        'scripts/urbit/team_check.py': team_check, 'scripts/urbit/team_lifecycle.py': team_lifecycle,
        'scripts/urbit/review_prepare.py': review_prepare, 'scripts/urbit/core_conn.py': core_conn,
        'scripts/urbit/native_peer_fence.py': native_peer_fence, 'scripts/urbit/native_tls.py': native_tls}
    for name, module in modules.items():
        require(hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                == inputs['controller_files'][name]['sha256'], 'Loaded verifier helper source differs: ' + name)
    for name, path in {'scripts/ci/product_result.py': Path(__file__),
                      'scripts/urbit/supervisor.py': Path(team_check.__file__).parent / 'supervisor.py'}.items():
        require(hashlib.sha256(path.read_bytes()).hexdigest() == inputs['controller_files'][name]['sha256'],
                'Verifier/restarter source differs: ' + name)
    require(release_fingerprint.__module__ == 'release_install'
            and release_fingerprint.__name__ == 'saved_home_fingerprint'
            and hashlib.sha256(Path(release_fingerprint.__code__.co_filename).read_bytes()).hexdigest()
                == inputs['controller_files']['scripts/release_install.py']['sha256'], 'Loaded release helper source differs')
    expected_installed = {name.removeprefix('native/core/desk/'): item['sha256']
        for name, item in inputs['composed_files'].items() if name.startswith('native/core/desk/')}
    require(set(report['installed']) == set(SHIPS) and all(same(value, expected_installed)
            for value in report['installed'].values()), 'Exact four-ship composed source required')
    for name in ('ted/stead-product-checkpoint.hoon', 'gen/stead-product-checkpoint.hoon', 'gen/stead-v10-capture.hoon'):
        require(expected_installed[name] == inputs['controller_files']['native/core/desk/' + name]['sha256'],
                'Checkpoint helper must be trusted controller source')
    record = report['product_journey']
    require(set(record) == {'profile', 'status', 'classification', 'qualifies_phase', 'restarts',
        'paused_predecessor', 'old_captures', 'full_product_partial_restore', 'browser', 'config', 'now', 'trace',
        'result', 'initial_owners', 'command_start', 'command_end', 'check_start', 'check_end'}, 'Closed journey report')
    require(record['profile'] == 'native-human-doc/1' and record['status'] == 'observed'
        and record['classification'] == 'prepared-disposable-native-journey' and record['qualifies_phase'] is False
        and record['full_product_partial_restore'] == 'not-observed'
        and record['browser'] == 'separate-fresh-fixture-required', 'Observed scope cannot expand')
    require(type(record['now']) is int and 0 < record['now'] < 2**64
            and same(record['config'], team_check.configuration(record['now'])), 'Exact fresh fixture configuration')
    require(isinstance(record['old_captures'], dict) and set(record['old_captures']) == {'predecessor', 'product'}, 'Two closed old capture records')
    commands, checks, trace = report['commands'], report['checks'], record['trace']
    require(isinstance(commands, list) and len(commands) <= 4096
            and isinstance(checks, list) and len(checks) <= 4096
            and isinstance(trace, list) and 0 < len(trace) <= 256, 'Journey traversal bounds')
    command_at, check_at, trace_at, restart_at = record['command_start'], record['check_start'], 0, 0
    require(all(type(record[k]) is int for k in ('command_start', 'command_end', 'check_start', 'check_end'))
            and 0 <= command_at <= record['command_end'] <= len(commands)
            and 0 <= check_at <= record['check_end'] <= len(checks), 'Journey range bounds')
    owners = record['initial_owners'].copy()
    require(set(owners) == set(SHIPS), 'Initial owned four-ship runtime identity')
    for ship, owner in owners.items():
        require(set(owner) == {'pid', 'nonce'} and type(owner['pid']) is int and owner['pid'] > 0
                and isinstance(owner['nonce'], str) and HASH.fullmatch(owner['nonce']), 'Initial owner process/nonce')
        prior = [r for r in commands[:command_at] if r.get('ship') == ship and r.get('mode') == 'bootstrap']
        require(prior, 'Actual initial bootstrap command required')
        boot = native_call(prior[-1], family='legacy', ship=ship, mode='bootstrap',
            value={'protocol': 'stead.bootstrap/1', 'nonce': owner['nonce']},
            options={'route': '/bootstrap/' + owner['nonce'], 'target': ship,
                     'app': team_lifecycle.APPS[ship], 'timeout': 75})
        require(set(boot) == {'protocol', 'status', 'home', 'nonce', 'incarnation'}
                and boot['protocol'] == 'stead.bootstrap/1' and boot['status'] == 'ready'
                and boot['home'] == '~' + ship and boot['nonce'] == owner['nonce']
                and isinstance(boot['incarnation'], str) and HASH.fullmatch(boot['incarnation']), 'Initial admitted native incarnation')
    seen_nonces = {owner['nonce'] for owner in owners.values()}
    require(len(seen_nonces) == 4 and len({owner['pid'] for owner in owners.values()}) == 4,
            'Four distinct initial runtime owners/nonces')

    def check(name, condition):
        nonlocal check_at
        require(condition is True and check_at < len(checks)
                and same(checks[check_at], {'name': name, 'passed': True}), 'Exact observed assertion differs: ' + name)
        check_at += 1

    def replay(kind):
        def invoke(*args, **options):
            nonlocal command_at, trace_at, restart_at
            require(trace_at < len(trace), 'Missing callback observation')
            event = trace[trace_at]
            trace_at += 1
            require(set(event) == {'kind', 'arguments', 'options', 'command_start', 'command_end',
                'check_start', 'check_end', 'result'} and event['kind'] == kind
                and all(type(event[k]) is int for k in ('command_start', 'command_end', 'check_start', 'check_end'))
                and same(event['arguments'], list(args)) and same(event['options'], options)
                and event['command_start'] == command_at and event['check_start'] == check_at,
                'Exact ordered callback correlation')
            cursor = Commands(commands, command_at, event['command_end'])
            if kind in ('legacy', 'product'):
                value = native_call(cursor.next(), family=kind, ship=args[0], mode=args[1],
                                    value=args[2] if len(args) == 3 else None, options=options)
            elif kind == 'dojo':
                value = cursor.dojo(*args, **options)
            elif kind == 'fingerprints':
                value = fingerprints(cursor, release_fingerprint)
            elif kind == 'paused-predecessor':
                activate = args[0]
                check('product-activation-home-actually-idle', cursor.dojo('zod', '.^(? %gu /=stead-home=/$)').strip() == '%.n')
                before = product_controller.checkpoint_value(cursor.dojo('zod', '+stead-product-checkpoint'), activate)
                first, second = fingerprints(cursor, release_fingerprint), fingerprints(cursor, release_fingerprint)
                check('product-paused-predecessor-double-fingerprint-stable', first == second)
                check('product-paused-predecessor-actual-helper-agreement', first['release_authority'] == first['review_authority']
                      and first['release_vase'] == first['lifecycle_vase'])
                after = product_controller.checkpoint_value(cursor.dojo('zod', '+stead-product-checkpoint'), activate)
                check('product-paused-predecessor-still-exact', before == after)
                require(same(record['paused_predecessor'], {'observation': before, 'first': first, 'second': second}), 'Paused retained observations differ')
                captured = product_capture.collect(cursor.dojo,
                    lambda: team_lifecycle.TeamLifecycle.saved_fingerprint(None, 'zod', cursor.dojo),
                    'predecessor', first['release_vase'])
                require(same(captured, record['old_captures']['predecessor']), 'Exact observed predecessor bytes')
                value = None
            elif kind in ('ready', 'restart'):
                require(restart_at < len(record['restarts']), 'Missing owned restart batch')
                batch = record['restarts'][restart_at]
                restart_at += 1
                require(isinstance(batch, list) and len(batch) == 4, 'Every restart must cover four owned ships')
                for ship, entry in zip(SHIPS, batch):
                    require(entry['old_pid'] == owners[ship]['pid'] and entry['old_nonce'] == owners[ship]['nonce'],
                            'Restart must replace the preceding actual owner')
                    require(entry['new_nonce'] not in seen_nonces
                            and entry['new_pid'] not in {o['pid'] for s, o in owners.items() if s != ship},
                            'New runtime owner cannot alias another admitted incarnation')
                    capture = None
                    if restart_at == 2 and ship == 'zod':
                        def capture(cursor, saved):
                            retained = product_capture.collect(cursor.dojo,
                                lambda: team_lifecycle.TeamLifecycle.saved_fingerprint(None, 'zod', cursor.dojo),
                                'product', saved)
                            require(same(retained, record['old_captures']['product']), 'Exact observed product bytes')
                    verify_restart(cursor, entry, ship, check, capture=capture)
                    owners[ship] = {'pid': entry['new_pid'], 'nonce': entry['new_nonce']}
                    seen_nonces.add(entry['new_nonce'])
                value = None
            else:
                raise ValueError('Unadmitted callback family')
            cursor.done()
            require(same(value, event['result']) and event['check_end'] == check_at, 'Callback result/assertions differ')
            command_at = cursor.index
            return value
        return invoke

    result = product_home_check.run(legacy=replay('legacy'), product=replay('product'), check=check,
        dojo=replay('dojo'), ready=replay('ready'), restart=replay('restart'), fingerprints=replay('fingerprints'),
        paused_predecessor=replay('paused-predecessor'), config=record['config'], now=record['now'], uid=team_check.uid)
    require(trace_at == len(trace) and restart_at == len(record['restarts']) == 4
            and command_at == record['command_end'] == len(commands) and check_at == record['check_end'] == len(checks)
            and same(result, record['result']) and record['paused_predecessor'] is not None, 'Complete exact journey observations required')
    return {'format': 'stead.product-journey-observation/1', 'status': 'observed', 'qualifies_phase': False,
            'scope': 'native human Work/Doc journey and exact predecessor pause; outer worker execution trust required',
            'full_product_partial_restore': 'not-observed', 'browser': 'not-observed',
            'result': result, 'assertions': check_at - record['check_start'], 'callbacks': trace_at,
            'old_captures': {k: product_capture.metadata(v) for k, v in record['old_captures'].items()}}


def verify_restart(commands, entry, ship, check, *, capture=None):
    require(set(entry) == {'ship', 'saved_vase_sha256', 'new_incarnation', 'passed', 'old_pid', 'new_pid',
        'old_nonce', 'new_nonce', 'old_exit_code', 'command_start', 'command_end', 'injection', 'lifecycle'}
        and entry['ship'] == ship and entry['passed'] is True
        and all(type(entry[k]) is int for k in ('command_start', 'command_end', 'old_exit_code'))
        and commands.index == entry['command_start'], 'Exact restart owner/slice')
    require(all(type(entry[k]) is int and entry[k] > 0 for k in ('old_pid', 'new_pid'))
        and entry['old_pid'] != entry['new_pid'] and entry['old_exit_code'] == 0
        and all(isinstance(entry[k], str) and HASH.fullmatch(entry[k]) for k in ('old_nonce', 'new_nonce', 'new_incarnation'))
        and entry['old_nonce'] != entry['new_nonce'], 'Stopped/reaped old owner and fresh bootstrap identity')
    injection(entry['injection'], ship)
    saved = team_lifecycle.TeamLifecycle.saved_fingerprint(None, ship, commands.dojo)
    require(saved == entry['saved_vase_sha256'], 'Restart capture exact saved vase')
    check('product-' + ship + '-previous-child-reaped', entry['old_exit_code'] == 0)
    restored = team_lifecycle.TeamLifecycle.saved_fingerprint(None, ship, commands.dojo)
    check('product-' + ship + '-suspended-exact-saved-vase', saved == restored)
    if capture is not None:
        capture(commands, saved)
    app = team_lifecycle.APPS[ship]
    require(commands.dojo(ship, f'.^(desk %gd /={app}=/$)').strip() == '%base', 'Restart verified desk')
    commands.dojo(ship, f'|rein %base [%.n %{app}]')
    commands.dojo(ship, f'|rein %base [%.y %{app}]')
    for _ in range(601):
        observed = commands.dojo(ship, f'.^(? %gu /={app}=/$)').strip()
        require(observed in ('%.n', '%.y'), 'Actual reinstall liveness boolean')
        if observed == '%.y':
            break
    else:
        raise ValueError('Reinstall observation bound')
    boot = None
    for _ in range(3):
        boot = native_call(commands.next(), family='legacy', ship=ship, mode='bootstrap',
            value={'protocol': 'stead.bootstrap/1', 'nonce': entry['new_nonce']},
            options={'route': '/bootstrap/' + entry['new_nonce'], 'target': ship, 'app': app, 'timeout': 75})
        if set(boot) == {'protocol', 'status', 'home', 'nonce', 'incarnation'}:
            break
        require(boot.get('protocol') == 'stead.test-terminal/1' and boot.get('status') == 'failed'
                and boot.get('kind') == 'poke-fail', 'Only recorded bounded bootstrap refusals may precede ready')
    require(boot == {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~' + ship,
        'nonce': entry['new_nonce'], 'incarnation': entry['new_incarnation']}, 'Actual fresh native bootstrap acknowledgement')
    check('product-' + ship + '-fresh-native-bootstrap', True)
    source = f'(lien ~(tap in .^((set [@tas ?]) %ge /=base=/$)) |=([name=@tas live=?] =(name %{app})))'
    require(commands.dojo(ship, source).strip() == '%.y' and commands.index == entry['command_end'], 'Admitted app inventory and restart command extent')
    events = entry['lifecycle']
    require(isinstance(events, list) and len(events) == 7
        and all(set(e) == {'utc', 'command', 'result'} for e in events)
        and [e['command'] for e in events] == ['configured restart expectation ' + ship, 'shutdown ' + ship,
            'configured launch ' + ship, 'launch ' + ship, ship + ': zuse',
            'configured suspension ' + ship, 'configured admission ' + ship],
        'Ordered actual lifecycle observations required')
    values = [e['result'] for e in events]
    require(same(values[0], {'saved_vase_sha256': saved}) and same(values[1], {'exit_code': 0, 'forced': False})
        and same(values[2]['pid'], entry['new_pid']) and same(values[3]['pid'], entry['new_pid'])
        and same(values[2]['injection'], entry['injection'])
        and values[4] == '%408' and same(values[5], {'pid': entry['new_pid'], 'present_on_base': True})
        and same(values[6]['pid'], entry['new_pid']) and values[6]['incarnation'] == entry['new_incarnation'],
        'Actual lifecycle owner/custody correlation')
    admission = values[6]
    require(set(admission) == {'pid', 'incarnation', 'peer_proof', 'tls'}, 'Closed current-owner admission')
    peer, tls = admission['peer_proof'], admission['tls']
    require(set(peer) == {'capabilities', 'socket'} and isinstance(peer['capabilities'], dict)
            and 0 < len(peer['capabilities']) <= 32 and str(entry['new_pid']) in peer['capabilities'], 'Owned process tree admission')
    for pid, caps in peer['capabilities'].items():
        require(isinstance(pid, str) and re.fullmatch(r'[1-9][0-9]{0,9}', pid)
                and same(caps, {'CapEff': '0000000000000000', 'CapPrm': '0000000000000000',
                             'CapInh': '0000000000000000', 'CapAmb': '0000000000000000',
                             'CapBnd': '0000000000000000', 'NoNewPrivs': '1'}), 'Current owned process privilege fence')
    socket = peer['socket']
    require(set(socket) == {'ship', 'pid', 'endpoint', 'inode', 'network_namespace'}
            and socket['ship'] == ship and same(socket['pid'], entry['new_pid'])
            and socket['endpoint'] == '0100007F:' + f'{native_peer_fence.PORTS[ship]:04X}'
            and isinstance(socket['inode'], str) and re.fullmatch(r'[1-9][0-9]{0,19}', socket['inode'])
            and isinstance(socket['network_namespace'], str)
            and re.fullmatch(r'net:\[[1-9][0-9]{0,19}\]', socket['network_namespace']), 'Current owned native peer socket')
    require(set(tls) == {'hostname', 'certificate_sha256', 'protocol', 'owned_listeners'}
            and tls['hostname'] == native_tls.HOSTS[ship] and isinstance(tls['certificate_sha256'], str)
            and HASH.fullmatch(tls['certificate_sha256']) and tls['protocol'] in ('TLSv1.2', 'TLSv1.3')
            and isinstance(tls['owned_listeners'], list) and 1 <= len(tls['owned_listeners']) <= 2, 'Current owned TLS observation')
    for listener in tls['owned_listeners']:
        require(set(listener) == {'endpoint', 'inode'}
                and isinstance(listener['endpoint'], str)
                and re.fullmatch(r'[0-9A-F]{8}(?:[0-9A-F]{24})?:' + f'{native_tls.PORTS[ship]:04X}', listener['endpoint'])
                and isinstance(listener['inode'], str) and re.fullmatch(r'[1-9][0-9]{0,19}', listener['inode']), 'Owned exact native TLS port')

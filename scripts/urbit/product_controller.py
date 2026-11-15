"""Prepared trusted callbacks; no CLI, startup, qualification or fallback.

Only a separately reviewed hosted controller may call this on four newly seeded,
source-verified fake ships. A completed migration is NOT a partial checkpoint.
The normal legacy/Code scenario and browser fixture must run separately.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace

import product_conn
import product_home_check
import review_prepare
import team_check


def checkpoint_value(output, activate):
    if (not isinstance(output, str) or len(output) > 16384
            or not re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', output.strip())):
        raise ValueError('Paused checkpoint did not return bounded actual bytes')
    atom = int(output.strip().replace('.', ''), 16)
    raw = atom.to_bytes((atom.bit_length() + 7) // 8, 'little')
    value = json.loads(raw)
    expected = {'protocol': 'stead.product-checkpoint/1', 'profile': 'native-human-doc/1',
                'target': 'predecessor', 'expected_config_revision': activate['expected_config_revision'],
                'predecessor_sha256': activate['predecessor_sha256']}
    if value != expected or raw != product_conn.canonical(expected):
        raise ValueError('Actual saved target is not the exact pristine predecessor')
    return value


def run(host, *, legacy, command, check, checkpoint, report, config, now,
        release_fingerprint, release_source_sha256):
    """Call only after exact install, config and bootstrap of a NEW fixture."""
    if tuple(host['SHIPS']) != ('zod', 'bus', 'nec', 'bud'):
        raise ValueError('Exact four-ship fixture required')
    if (config != team_check.configuration(now) or report.get('product_journey')
            or set(report.get('installed', {})) != set(host['SHIPS'])):
        raise ValueError('Fresh exact no-Code configuration and source inventory required')
    installed = report['installed']
    if any(installed[ship] != installed['zod'] for ship in host['SHIPS']):
        raise ValueError('Installed four-ship source differs')
    # Import the actual mounted release module in the controller caller. Never
    # duplicate or AST-extract its implementation, and never create Native().
    module_path = Path(release_fingerprint.__code__.co_filename)
    if (release_fingerprint.__module__ != 'release_install'
            or release_fingerprint.__name__ != 'saved_home_fingerprint'
            or not re.fullmatch(r'[0-9a-f]{64}', release_source_sha256)
            or hashlib.sha256(module_path.read_bytes()).hexdigest() != release_source_sha256):
        raise ValueError('Exact release fingerprint helper source required')
    team = host['TEAM']
    if any(not team.boots[s]['acknowledged'] or team.boots[s]['process'].poll() is not None
           for s in host['SHIPS']):
        raise ValueError('Current owned admitted fixture required')
    record = {'profile': 'native-human-doc/1', 'status': 'running',
              'classification': 'prepared-disposable-native-journey',
              'qualifies_phase': False, 'restarts': [], 'paused_predecessor': None,
              'full_product_partial_restore': 'not-observed', 'browser': 'separate-fresh-fixture-required',
              'config': config, 'now': now, 'trace': [], 'result': None,
              'initial_owners': {s: {'pid': team.boots[s]['process'].pid, 'nonce': team.boots[s]['nonce']}
                                 for s in host['SHIPS']},
              'command_start': len(report['commands']), 'check_start': len(report['checks'])}
    report['product_journey'] = record
    binary = '/runtime/' + host['LOCK']['runtime']['binary']

    def product(ship, mode, value=None, *, route='/', target='zod'):
        host['execution_check']()
        if ship not in host['SHIPS'] or target != 'zod' or (mode == 'activate-paused' and ship != 'zod'):
            raise ValueError('Prepared product carrier actual sender/target scope')
        raw = product_conn.canonical(value) if value is not None else b''
        observed = product_conn.run(binary, host['LIVE'] / ship / '.urb/conn.sock',
                                    mode, route, raw, target=target)
        retained = {k: observed[k] for k in ('stdout', 'stderr', 'response_frame_sha256',
                    'request', 'request_frame_hex', 'response_frame_hex', 'outcome')}
        report['commands'].append({'ship': ship, 'mode': mode, 'app': 'stead-home',
            'target': target, 'input_sha256': hashlib.sha256(raw).hexdigest(),
            'input_hex': raw.hex(), 'route': route, **retained})
        checkpoint('product-native-call')
        outcome = (observed.get('outcome') or {}).get('json')
        if not isinstance(outcome, dict):
            raise ValueError('Actual native product outcome absent')
        if (outcome.get('protocol') == 'stead.test-terminal/1'
                and outcome.get('kind') not in ('poke-fail', 'watch-ack-fail')):
            raise ValueError('Actual product transport failed')
        return outcome

    def fingerprints():
        host['execution_check']()
        native = SimpleNamespace(dojo=lambda source: command('zod', source))
        return {'release_authority': release_fingerprint(native, authoritative=True),
                'review_authority': review_prepare.durable_fingerprint('zod', command),
                'release_vase': release_fingerprint(native),
                'lifecycle_vase': team.saved_fingerprint('zod', command)}

    def paused_predecessor(activate):
        host['execution_check']()
        check('product-activation-home-actually-idle',
              command('zod', '.^(? %gu /=stead-home=/$)').strip() == '%.n')
        before = checkpoint_value(command('zod', '+stead-product-checkpoint'), activate)
        first, second = fingerprints(), fingerprints()
        check('product-paused-predecessor-double-fingerprint-stable', first == second)
        check('product-paused-predecessor-actual-helper-agreement',
              first['release_authority'] == first['review_authority']
              and first['release_vase'] == first['lifecycle_vase'])
        after = checkpoint_value(command('zod', '+stead-product-checkpoint'), activate)
        check('product-paused-predecessor-still-exact', before == after)
        record['paused_predecessor'] = {'observation': before, 'first': first, 'second': second}
        checkpoint('product-paused-predecessor-proved')

    def restart():
        batch = []
        for ship in host['SHIPS']:
            host['execution_check']()
            old = dict(team.boots[ship])
            first_command = len(report['commands'])
            first_lifecycle = len(host['EVIDENCE'])
            saved = team.prepare_restart(ship, command)
            host['shutdown'](ship)
            check('product-' + ship + '-previous-child-reaped', old['process'].poll() == 0)
            host['launch'](ship)
            host['wait_ready'](ship)
            entry = team.boots[ship]
            check('product-' + ship + '-suspended-exact-saved-vase',
                  entry['suspended'] and entry['present'] and not entry['acknowledged']
                  and team.saved_fingerprint(ship, command) == saved)
            team.reinstall(ship, command)
            nonce = entry['nonce']
            boot = team_check.bootstrap_ready(team, ship, legacy, host['execution_check'])
            check('product-' + ship + '-fresh-native-bootstrap',
                  nonce != old['nonce'] and boot.get('nonce') == nonce and boot.get('status') == 'ready')
            team.admit(ship, boot, command)
            batch.append({'ship': ship, 'saved_vase_sha256': saved,
                          'new_incarnation': boot['incarnation'], 'passed': True,
                          'old_pid': old['process'].pid, 'new_pid': entry['process'].pid,
                          'old_nonce': old['nonce'], 'new_nonce': nonce,
                          'old_exit_code': old['process'].poll(),
                          'command_start': first_command, 'command_end': len(report['commands']),
                          'injection': entry['injection'],
                          'lifecycle': host['EVIDENCE'][first_lifecycle:]})
        record['restarts'].append(batch)
        checkpoint('product-cold-restart-verified')

    def traced(kind, function):
        def invoke(*args, **kwargs):
            event = {'kind': kind, 'arguments': list(args), 'options': kwargs,
                     'command_start': len(report['commands']), 'check_start': len(report['checks'])}
            result = function(*args, **kwargs)
            event.update(command_end=len(report['commands']), check_end=len(report['checks']), result=result)
            record['trace'].append(event)
            return result
        return invoke

    record['result'] = product_home_check.run(legacy=traced('legacy', legacy),
        product=traced('product', product), check=check, dojo=traced('dojo', command),
        ready=traced('ready', restart), restart=traced('restart', restart),
        fingerprints=traced('fingerprints', fingerprints),
        paused_predecessor=traced('paused-predecessor', paused_predecessor),
        config=config, now=now, uid=team_check.uid)
    if record['paused_predecessor'] is None:
        raise ValueError('Actual paused predecessor checkpoint is mandatory')
    record['status'] = 'observed'
    record.update(command_end=len(report['commands']), check_end=len(report['checks']))
    checkpoint('product-native-journey-observed')
    # This overlay does NOT amend the independent controller verifier. It must
    # never accidentally certify the legacy full-suite gate or a product gate.
    raise RuntimeError('Prepared product controller inspection only: qualification disabled')

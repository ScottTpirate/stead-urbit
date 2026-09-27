"""Guarded native compilation and pure probes, separate from phase acceptance.

Uses the existing disposable seed and four-ship supervisor. Only the home desk
is compiled here; cross-ship behavior, migrations and the corpus use core-test.
"""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import time
import traceback

import core_conn
import execution_policy
import native_units
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
DEPENDENCIES = ('core_check.py', 'core_conn.py', 'conn.py', 'digests.py', 'execution_policy.py', 'native_units.py')


def closure():
    return {name: sha(CODE / name) for name in DEPENDENCIES}


LOADED_CLOSURE = closure()


def run(host):
    started = time.monotonic()
    report = {'status': 'fail', 'classification': 'local-real-native-compile-probes',
              'qualifies_phase': False, 'checks': [], 'commands': [],
              'scope': 'Exact home desk compilation and pure probes only; no four-ship acceptance.'}
    native = Path('/native/core/desk')

    def inputs():
        return {'native': tree_sha(native), 'runner': closure(),
                'harness': source_sha(CODE), 'toolchain': sha('/toolchain.json'),
                'native_unit_inventory': sha('/specs/phase2-pure-units.json')}

    before = inputs()
    report['inputs_before'] = before
    report_path = Path('/state/logs') / ('core-check-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')

    def checkpoint(stage):
        report['stage'] = stage
        execution_policy.write_json(report_path, report)

    # Preserve exact inputs and the last attempted operation even if the guard
    # must terminate this process before the final report can be written.
    checkpoint('admission')

    def check(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    def command(source, expected=None):
        result = host['dojo']('zod', source, timeout=300) if source == '+stead-team-authority-probe' else host['dojo']('zod', source)
        report['commands'].append({'ship': 'zod', 'dojo': source, 'result': result})
        checkpoint('compile-and-probes')
        if expected is not None:
            check(source, result.strip() == expected)
        return result

    try:
        inventory = native_units.validate_inventory(json.loads(
            Path('/specs/phase2-pure-units.json').read_text()))
        host['execution_check'](preflight=True)
        check('loaded-supervisor-source-matches', before['harness'] == host['LOADED_SOURCE_DIGEST'])
        check('loaded-compile-runner-source-matches', before['runner'] == LOADED_CLOSURE)
        binary = '/runtime/' + host['LOCK']['runtime']['binary']
        checkpoint('evaluator-controls')
        report['evaluator_controls'] = core_conn.evaluator_controls(binary)
        check('evaluator-failure-and-framing-controls', report['evaluator_controls']['status'] == 'passed')
        checkpoint('restore-disposable-fixture')
        host['all_stop']()
        host['copy_seed_to_live']()
        for ship in host['SHIPS']:
            host['launch'](ship)
            host['wait_ready'](ship)
        sources = sorted(path for path in native.rglob('*') if path.is_file())
        check('nonempty-native-source', bool(sources))
        # Import the raw asset mark before files using it. Unix/Clay commit
        # acknowledgement precedes the completed import; wait on a nonthrowing
        # directory scry before exact byte readback.
        for group in ([p for p in sources if p.suffix == '.hoon'],
                      [p for p in sources if p.suffix != '.hoon']):
            if not group:
                continue
            for source in group:
                target = host['LIVE'] / 'zod/base' / source.relative_to(native)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                check('installed-bytes:' + str(source.relative_to(native)), sha(source) == sha(target))
            command('|commit %base')
            deadline = time.monotonic() + 60
            for source in group:
                literal = core_conn.atom(bytes.fromhex(sha(source))[::-1])
                parts = [*source.relative_to(native).with_suffix('').parts, source.suffix[1:]]
                path = '/' + '/'.join(parts)
                exists = f'=/  arc=arch  .^(arch %cy /=base={path})  ?=(^ -.arc)'
                while command(exists).strip() != '%.y':
                    host['execution_check']()
                    if time.monotonic() > deadline:
                        raise TimeoutError('Clay import did not publish ' + str(source.relative_to(native)))
                    time.sleep(.2)
                expression = f'=/  raw=@t  .^(@t %cx /=base={path})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))'
                command(expression, '%.y')
        # Bind the actual seeded unit runner and typed input mark to the pin.
        for dependency in ('ted/test.hoon', 'mar/path.hoon'):
            pinned = (Path('/kernel/pkg/arvo') / dependency).resolve(strict=True)
            if not pinned.is_relative_to('/kernel'):
                raise ValueError('Pinned dependency escapes verified kernel tree')
            literal = core_conn.atom(bytes.fromhex(sha(pinned))[::-1])
            route = '/' + dependency.replace('.hoon', '/hoon')
            command(f'=/  raw=@t  .^(@t %cx /=base={route})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))', '%.y')
        report['native_units'] = []
        def native_test(entry):
            resolved = command('`path`%' + entry['path']).strip()
            log = Path('/state/logs/zod.log')
            offset = log.stat().st_size
            terminal = ''
            try:
                observed = native_units.run(binary, host['LIVE'] / 'zod/.urb/conn.sock', resolved, timeout=entry.get('timeout_seconds', 60))
                report['commands'].append({'ship': 'zod', 'native_test': observed})
                terminal = observed['stdout']
            finally:
                with log.open('rb') as stream:
                    stream.seek(offset)
                    captured = stream.read(262145)
                report.setdefault('native_unit_transcripts', []).append({
                    'path': entry['path'], 'log_offset': offset, 'log_bytes': len(captured),
                    'log_hex': captured.hex(), 'terminal': terminal})
                checkpoint('native-unit-output')
            if len(captured) > 262144:
                raise ValueError('Native unit log byte bound')
            return captured.decode('utf-8', errors='strict') + '\n' + terminal
        for entry in inventory['suites']:
            raw = native_test(entry)
            observed = native_units.verify_output(raw, path=entry['path'],
                                                  expected=entry['arms'], succeeds=True)
            report['native_units'].append(observed)
            check('native-unit-arms:' + entry['path'], True)
        control = inventory['negative_control']
        raw = native_test(control)
        report['native_failure_control'] = native_units.verify_output(
            raw, path=control['path'], expected=control['arms'], succeeds=False,
            failure_marker=control['marker'])
        check('native-unit-deliberate-failure-observed', True)
        host['execution_check']()
        for probe, expected in (
                ('stead-build-probe', '%stead-builds-pass'),
                ('stead-codec-probe', '%stead-codec-six-vectors-pass'),
                ('stead-core-probe', '%stead-core-basic-and-counter-edge-pass'),
                ('stead-reducers-probe', '%stead-native-reducers-pass'),
                ('stead-save-probe', '%stead-save-format2-roundtrip-pass'),
                ('stead-session-probe', '%stead-session-57-controls-pass'),
                ('stead-http-probe', '%stead-http-49-controls-pass'),
                ('stead-team-contract-probe', '%stead-team-contract-basic-pass'),
                ('stead-team-authority-probe', '%stead-team-authority-basic-pass')):
            command('+' + probe, expected)
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        if hasattr(error, 'native_failure'):
            report['native_failure'] = error.native_failure
        traceback.print_exc()
    report['inputs_after'] = inputs()
    if before != report['inputs_after']:
        report.update(status='fail', error='Source/input changed during compilation')
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    checkpoint('completed' if report['status'] == 'pass' else 'failed')
    return {key: report[key] for key in ('status', 'classification', 'qualifies_phase', 'scope',
            'elapsed_seconds')} | {'error': report.get('error'),
            'checks_passed': sum(check['passed'] for check in report['checks']),
            'evidence_file': '.piers/fakes/logs/' + report_path.name}

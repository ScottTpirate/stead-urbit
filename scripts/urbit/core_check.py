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
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
DEPENDENCIES = ('core_check.py', 'core_conn.py', 'conn.py', 'digests.py', 'execution_policy.py')


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
                'harness': source_sha(CODE), 'toolchain': sha('/toolchain.json')}

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
        result = host['dojo']('zod', source)
        report['commands'].append({'ship': 'zod', 'dojo': source, 'result': result})
        checkpoint('compile-and-probes')
        if expected is not None:
            check(source, result.strip() == expected)

    try:
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
        sources = sorted(native.rglob('*.hoon'))
        check('nonempty-native-source', bool(sources))
        for source in sources:
            target = host['LIVE'] / 'zod/base' / source.relative_to(native)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            check('installed-bytes:' + str(source.relative_to(native)), sha(source) == sha(target))
        command('|commit %base')
        for source in sources:
            literal = core_conn.atom(bytes.fromhex(sha(source))[::-1])
            path = '/' + str(source.relative_to(native)).replace('.hoon', '/hoon')
            expression = f'=/  raw=@t  .^(@t %cx /=base={path})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))'
            command(expression, '%.y')
        for probe, expected in (
                ('stead-build-probe', '%stead-builds-pass'),
                ('stead-codec-probe', '%stead-codec-six-vectors-pass'),
                ('stead-core-probe', '%stead-core-basic-and-counter-edge-pass'),
                ('stead-reducers-probe', '%stead-native-reducers-pass'),
                ('stead-save-probe', '%stead-save-format2-roundtrip-pass')):
            command('+' + probe, expected)
        host['execution_check']()
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
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

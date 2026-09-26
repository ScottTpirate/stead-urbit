"""Run the actual pinned Gall schedule; dispatch queue and clock are simulated.

This lane runs inside the existing guarded fake-ship supervisor. It does not
claim Ames/network authentication or replace the four-ship acceptance corpus.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import time
import traceback

import core_conn
import execution_policy
import gall_schedule_proof
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
PACKAGE = Path('/native-tests/gall-schedule')
DEPENDENCIES = ('gall_schedule.py', 'gall_schedule_proof.py', 'delivery_cases.py',
                'core_conn.py', 'digests.py')


def closure():
    return {name: sha(CODE / name) for name in DEPENDENCIES}


LOADED_CLOSURE = closure()


def intended_negative(result, diagnostic):
    if len(result) > 65536 or len(diagnostic) > 65536:
        return False
    hint = r'(?<![\w-])stead-scheduled-gall-pending-control\s+2\s+(?:\x271\x27|1)(?=\s|\])'
    if result.strip() == '~':
        return re.search(hint, diagnostic) is not None
    # Pinned Dojo also returns the runtime tang directly, including its terminal
    # failure line. Only this fixture's location frames and exact control hint
    # are accepted: a compiler error or an arbitrary nonempty result is not it.
    lines = result.strip().splitlines()
    if len(lines) < 3 or lines[-1] != 'dojo: generator failure':
        return False
    control = r'\[%?stead-scheduled-gall-pending-control 2 (?:\x271\x27|1)\]'
    frame = r'/(?:gen|lib)/stead-gall-schedule(?:-negative)?/hoon:<\[[0-9. ]+\]\.\[[0-9. ]+\]>'
    return (sum(re.fullmatch(control, line) is not None for line in lines[:-1]) == 1
            and any(re.fullmatch(frame, line) is not None for line in lines[:-1])
            and all(re.fullmatch(control, line) or re.fullmatch(frame, line) for line in lines[:-1]))


def inputs():
    return {'native': tree_sha(Path('/native/core/desk')),
            'overlay': tree_sha(PACKAGE / 'desk'), 'fixtures': sha(PACKAGE / 'inputs.json'),
            'runner': closure(), 'harness': source_sha(CODE), 'toolchain': sha('/toolchain.json'),
            'corpus': sha('/specs/fixtures/native-cases-v2.json'),
            'freeze': sha('/specs/v2/contract-freeze.json'),
            'gall': sha('/kernel/pkg/arvo/sys/vane/gall.hoon')}


def run(host, *, restore=True):
    started = time.monotonic()
    report = {'status': 'fail', 'classification': 'native-scheduled-gall',
              'requirement': 'delivery-late-old-leave', 'checks': [], 'commands': [],
              'scope': 'Actual pinned Gall and app gates; simulated dispatch queue and fixed clock; no Ames or UDP.'}
    report_path = Path(host['STATE']) / 'logs' / (
        'gall-schedule-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + secrets.token_hex(6) + '.json')
    before = None

    def checkpoint(stage):
        report['stage'] = stage
        execution_policy.write_json(report_path, report)

    def check(name, passed):
        report['checks'].append({'name': name, 'passed': bool(passed)})
        if not passed:
            raise AssertionError(name)

    def command(source, expected=None):
        host['execution_check']()
        log = Path('/state/logs/zod.log')
        offset = log.stat().st_size
        item = {'ship': 'zod', 'dojo': source, 'log_offset': offset}
        report['commands'].append(item)
        checkpoint('executing ' + source[:80])
        try:
            item['result'] = host['dojo']('zod', source, timeout=600)
        finally:
            with log.open('rb') as stream:
                stream.seek(offset)
                raw = stream.read(1_000_001)
            item['log_bytes'] = len(raw)
            item['log_sha256'] = hashlib.sha256(raw).hexdigest()
            item['log'] = raw.decode(errors='replace')
            checkpoint('executed ' + source[:80])
            if len(raw) > 1_000_000:
                raise ValueError('Native schedule diagnostic bound exceeded')
        host['execution_check']()
        if expected is not None:
            check(source, item['result'].strip() == expected)
        return item

    # Reserve a new evidence name exclusively, before any source read can fail.
    report['stage'] = 'admission'
    with report_path.open('x') as destination:
        json.dump(report, destination)
        destination.write('\n')
    try:
        before = inputs()
        report['inputs_before'] = before
        report['source_commit'] = host['qualified_source']()
        checkpoint('input-bindings')
        host['execution_check'](preflight=True)
        check('loaded-supervisor-source-matches', before['harness'] == host['LOADED_SOURCE_DIGEST'])
        check('loaded-schedule-runner-source-matches', before['runner'] == LOADED_CLOSURE)
        if restore:
            host['all_stop']()
            host['copy_seed_to_live']()
            for ship in host['SHIPS']:
                host['launch'](ship)
                host['wait_ready'](ship)
        installed = {}
        for root in (Path('/native/core/desk'), PACKAGE / 'desk'):
            sources = sorted(root.rglob('*.hoon'))
            check('nonempty-source:' + str(root), bool(sources))
            for source in sources:
                relative = source.relative_to(root)
                if str(relative) in installed:
                    raise ValueError('Schedule overlay cannot replace core source')
                target = host['LIVE'] / 'zod/base' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                installed[str(relative)] = sha(source)
                check('installed-bytes:' + str(relative), sha(target) == sha(source))
        report['installed_files'] = installed
        report['installed_by_ship'] = {'zod': dict(installed)}
        report['clay_verified_by_ship'] = {'zod': {}}
        command('|commit %base')
        for relative, digest in sorted(installed.items()):
            literal = core_conn.atom(bytes.fromhex(digest)[::-1])
            path = '/' + relative.replace('.hoon', '/hoon')
            expression = f'=/  raw=@t  .^(@t %cx /=base={path})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))'
            command(expression, '%.y')
            report['clay_verified_by_ship']['zod'][relative] = digest
        positive = command('+stead-gall-schedule')
        match = re.fullmatch(r"\s*\[%stead-core-result\s+'([0-9a-f]+)'\]\s*", positive['result'])
        check('positive-native-result-shape', match is not None)
        outcome = core_conn.parse_response('[32 %avow 0 %noun %stead-core-result ' + repr(match[1]) + ']')
        report['positive'] = outcome['json']
        report['positive_validation'] = gall_schedule_proof.validate(outcome['json'])
        negative = command('+stead-gall-schedule-negative')
        check('wrong-pending-count-is-specific-runtime-failure',
              intended_negative(negative['result'], negative['log']))
        report['negative_control'] = {'status': 'passed', 'expected_pending': 2, 'actual_pending': 1,
                                      'command_index': len(report['commands']) - 1}
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        traceback.print_exc()
    try:
        report['inputs_after'] = inputs()
        report['source_commit_after'] = host['qualified_source']()
        if report.get('source_commit') != report['source_commit_after']:
            raise ValueError('Schedule source commit changed')
        if before != report['inputs_after']:
            report.update(status='fail', error='Schedule source/input changed during execution',
                          prior_error=report.get('error'))
    except Exception as error:
        report.update(status='fail', final_binding_error=f'{type(error).__name__}: {error}')
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    checkpoint('completed' if report['status'] == 'pass' else 'failed')
    return {key: report[key] for key in ('status', 'classification', 'requirement', 'scope', 'elapsed_seconds')} | {
        'error': report.get('error'), 'checks_passed': sum(row['passed'] for row in report['checks']),
        'evidence_file': '.piers/fakes/logs/' + report_path.name}

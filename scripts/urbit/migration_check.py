"""Focused, guarded reproduction of the exact trusted CI migration generator.

This diagnostic uses one synthetic ship and preserves private compiler output.
It does not qualify the configured team, browser, or complete CI suite.
"""
from pathlib import Path
import os
import shutil
import stat
import tempfile
import time

import execution_policy
import native_install
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
PROBE = Path('/migration.hoon')
EXPECTED = '%stead-ci-supported-migration-pass'


def run(host):
    started = time.monotonic()
    report = {'status': 'fail', 'classification': 'local-real-native-migration-diagnostic',
              'qualifies_phase': False, 'checks': [], 'commands': [],
              'scope': 'One trusted supported-predecessor probe; not full CI or team acceptance.'}
    path = host['STATE'] / 'logs' / ('migration-check-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')

    def inputs():
        return {'native': tree_sha(Path('/native/core/desk')), 'harness': source_sha(CODE),
                'migration': sha(PROBE), 'toolchain': sha('/toolchain.json')}

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

    def command(ship, source, expected=None):
        value = host['dojo'](ship, source, timeout=180)
        report['commands'].append({'ship': ship, 'dojo': source, 'result': value})
        checkpoint('native-command')
        if expected is not None:
            check(source, value.strip() == expected)
        return value

    checkpoint('admission')
    try:
        host['execution_check'](preflight=True)
        check('configured-owned-controller', host.get('TEAM') is not None)
        check('loaded-source-matches', before['harness'] == host['LOADED_SOURCE_DIGEST'])
        # Bind the fixed read-only probe to the startup context, independently
        # of the native tree. There is no caller-selected path or Dojo command.
        context = execution_policy.read_json('/execution/source-context.json')
        check('probe-matches-startup', before['migration'] == context.get('migration_sha256'))
        host['all_stop']()
        host['copy_seed_to_live']()
        host['launch']('zod', fresh=True)
        host['wait_ready']('zod')
        with tempfile.TemporaryDirectory(prefix='stead-migration-') as directory:
            native = Path(directory) / 'desk'
            shutil.copytree('/native/core/desk', native)
            target = native / 'gen/stead-ci-migration-probe.hoon'
            check('reserved-probe-absent', not target.exists())
            shutil.copyfile(PROBE, target)
            report['installed'] = native_install.install(host, 'zod', command, check, native=native)
        log = host['STATE'] / 'logs/zod.log'
        offset = log.stat().st_size
        checkpoint('migration')
        command_error = None
        try:
            observed = command('zod', '+stead-ci-migration-probe')
            report['migration'] = {'source_sha256': before['migration'], 'output': observed}
        except BaseException as error:
            command_error = error
            report['initiating_error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            try:
                descriptor = os.open(log, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                try:
                    info = os.fstat(descriptor)
                    if not stat.S_ISREG(info.st_mode) or info.st_size < offset:
                        raise ValueError('Compiler log changed or is not regular')
                    length = min(info.st_size - offset, 262144)
                    with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                        stream.seek(offset)
                        captured = stream.read(length)
                    if len(captured) != length:
                        raise ValueError('Compiler log interval changed during capture')
                finally:
                    os.close(descriptor)
                report['compiler_log'] = {'offset': offset, 'end_offset': info.st_size,
                    'bytes': len(captured), 'hex': captured.hex(), 'truncated': info.st_size - offset > length}
                checkpoint('migration-output')
            except Exception as error:
                report['capture_error'] = type(error).__name__ + ': ' + str(error)
                if command_error is None:
                    raise
        check('bounded-compiler-log', not report['compiler_log']['truncated'])
        check('supported-migration-exact-result', observed.strip() == EXPECTED)
        host['execution_check']()
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        # A focused diagnostic never leaves an admitted team/browser fixture.
        try:
            host['all_stop']()
            report['cleanup'] = True
        except Exception as error:
            report.update(status='fail', cleanup=False, cleanup_error=type(error).__name__ + ': ' + str(error))
        report['inputs_after'] = inputs()
        if before != report['inputs_after']:
            report.update(status='fail', error='Source/input changed during migration')
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        checkpoint('completed' if report['status'] == 'pass' else 'failed')
    return {key: report[key] for key in ('status', 'classification', 'qualifies_phase', 'scope', 'elapsed_seconds')} | {
        'error': report.get('error'), 'evidence_file': '.piers/fakes/logs/' + path.name}

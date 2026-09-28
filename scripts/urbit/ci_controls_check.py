"""One stopped-seed fake reproduces trusted CI negative controls locally.

This is a private diagnostic, not hosted CI or full team acceptance.
"""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import time
from types import SimpleNamespace

import execution_policy
import native_install
from digests import source_sha, tree_sha


def run(host):
    started = time.monotonic()
    path = host['STATE'] / 'logs' / ('core-ci-controls-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')
    report = {'status':'fail', 'classification':'local-real-native-ci-controls-diagnostic', 'qualifies_phase':False,
              'checks':[], 'commands':[]}
    def inputs():
        return {'native':tree_sha(Path('/native/core/desk')), 'harness':source_sha(Path(__file__).parent),
                'ci':tree_sha(Path('/ci'))}
    before = inputs(); report['inputs_before'] = before
    def save(stage):
        report['stage'] = stage
        execution_policy.write_json(path, report)
    def check(name, passed):
        report['checks'].append({'name':name, 'passed':bool(passed)})
        save('checking')
        if not passed: raise ValueError(name)
    def command(ship, source, expected=None):
        observed = host['dojo'](ship, source, timeout=180)
        report['commands'].append({'ship':ship, 'dojo':source, 'result':observed})
        save('native-command')
        if expected is not None: check(source, observed.strip() == expected)
        return observed
    save('admission')
    try:
        host['execution_check'](preflight=True)
        check('configured-owned-controller', host.get('TEAM') is not None)
        check('loaded-source-matches', before['harness'] == host['LOADED_SOURCE_DIGEST'])
        context = execution_policy.read_json('/execution/source-context.json')
        check('ci-matches-startup', before['ci'] == context['trees'].get('scripts/ci'))
        host['all_stop'](); host['copy_seed_to_live']()
        host['launch']('zod', fresh=True); host['wait_ready']('zod')
        with tempfile.TemporaryDirectory(prefix='stead-ci-controls-') as directory:
            native = Path(directory) / 'desk'
            shutil.copytree('/native/core/desk', native)
            for source, destination in (('missing.hoon','controls/stead-ci-missing.hoon'),
                    ('compiler.hoon','controls/stead-ci-compiler.hoon'), ('delay.hoon','ted/stead-ci-delay.hoon')):
                target = native/destination
                check('reserved-control-absent:'+destination, not target.exists())
                shutil.copyfile(Path('/ci/controls')/source, target)
            report['installed'] = native_install.install(host, 'zod', command, check, native=native)
        spec = importlib.util.spec_from_file_location('stead_trusted_ci_negative', '/ci/negative.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        save('native-controls')
        def progress(stage, observation):
            report.setdefault('control_observations', {})[stage] = observation
            save('native-controls:' + stage)
        report['controls'] = module.native(SimpleNamespace(**host), None, progress=progress)
        host['execution_check']()
        report['status'] = 'pass'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        report['native_failure'] = getattr(error, 'native_failure', None)
    finally:
        try:
            host['all_stop'](); report['cleanup'] = True
        except BaseException as error:
            report.update(status='fail', cleanup=False, cleanup_error=type(error).__name__ + ': ' + str(error))
        report['inputs_after'] = inputs()
        if before != report['inputs_after']: report.update(status='fail', error='Native control source changed')
        report['elapsed_seconds'] = round(time.monotonic()-started,3)
        save('completed' if report['status']=='pass' else 'failed')
    return {key:report[key] for key in ('status','classification','qualifies_phase','elapsed_seconds')} | {
        'error':report.get('error'), 'evidence_file':'.piers/fakes/logs/'+path.name}

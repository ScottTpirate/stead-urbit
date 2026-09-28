"""Fail-closed verification of the trusted disposable worker's native evidence."""
from __future__ import annotations
import hashlib
import json
import re

PREFIX = 'STEAD_LOCAL_CI_RESULT '


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate worker JSON key')
        result[key] = value
    return result


def verify(raw, inputs, *, run_id, inventory):
    import native_units
    from conn import framed_length
    from gall_schedule_proof import _cue, _atom
    require(isinstance(raw, bytes) and 0 < len(raw) <= 32 * 1024**2, 'Worker output byte bound')
    lines = raw.decode('utf-8', errors='strict').splitlines()
    framed = [line for line in lines if line.startswith(PREFIX)]
    require(len(framed) == 1 and lines[-1] == framed[0], 'One final complete worker frame required')
    value = json.loads(framed[0][len(PREFIX):], object_pairs_hook=unique)
    require(set(value) == {'format', 'status', 'inputs_sha256', 'run_id', 'cleanup', 'admission',
                          'mounts_before', 'mounts_after', 'isolation', 'fresh_seeds', 'native', 'migration',
                          'filesystem_controls', 'negative_controls'}, 'Worker result schema')
    require(value['format'] == 'stead.local-ci-worker/1' and value['status'] == 'pass' and value['cleanup'] is True, 'Worker did not finish cleanly')
    require(value['run_id'] == run_id and re.fullmatch(r'[0-9a-f]{32}', run_id), 'Worker belongs to another run')
    require(value['inputs_sha256'] == hashlib.sha256(canonical(inputs)).hexdigest(), 'Worker input identity differs')
    expected_mounts = {prefix: {name[len(prefix) + 1:]: item['sha256']
        for name, item in inputs['controller_files'].items() if name.startswith(prefix + '/')}
        for prefix in ('scripts/urbit', 'scripts/ci', 'specs/urbit', 'web/dev')}
    expected_mounts['native'] = {name.removeprefix('native/'): item['sha256'] for name, item in inputs['composed_files'].items()}
    require(value['mounts_before'] == value['mounts_after'] == hashlib.sha256(canonical(expected_mounts)).hexdigest(), 'Worker mount identity differs')
    require(value['isolation'] == {'private_network': True, 'host_credentials_absent': True,
            'fresh_state': True, 'external_route_absent': True}, 'Worker isolation incomplete')
    require(value['admission'].get('status') == 'admitted' and value['admission'].get('run_id') == run_id, 'Worker resource admission missing')
    seeds = value['fresh_seeds']
    require(set(seeds) == {'format', 'toolchain_sha256', 'ships'} and seeds['format'] == 1
            and set(seeds['ships']) == {'zod', 'bus', 'nec', 'bud'}
            and all(re.fullmatch(r'[0-9a-f]{64}', item) for item in seeds['ships'].values()), 'Fresh seed evidence incomplete')
    migration = value['migration']
    require(set(migration) == {'source_sha256', 'output'} and migration['source_sha256'] == inputs['controller_files']['scripts/ci/migration.hoon']['sha256']
            and migration['output'].strip() == '%stead-ci-supported-migration-pass', 'Migration proof missing or different')
    report = value['native']
    require(report['status'] == 'pass' and report['stage'] == 'completed'
            and report['classification'] == 'local-real-configured-gall-development'
            and report['inputs_before'] == report['inputs_after'] == inputs['expected_native_inputs'], 'Native execution incomplete')
    require(seeds['toolchain_sha256'] == report['inputs_before']['toolchain']
            == inputs['controller_files']['specs/urbit/toolchain.lock.json']['sha256'], 'Native toolchain differs')
    require(report.get('execution_guard', {}).get('run_id') == run_id, 'Native evidence belongs to another guard')
    expected_installed = {name.removeprefix('native/core/desk/'): item['sha256']
        for name, item in inputs['composed_files'].items() if name.startswith('native/core/desk/')}
    require(set(report['installed']) == {'zod', 'bus', 'nec', 'bud'}
            and all(files == expected_installed for files in report['installed'].values()), 'Installed source inventory differs')
    checks = report['checks']
    require(isinstance(checks, list) and 0 < len(checks) <= 2000
            and all(set(row) == {'name', 'passed'} and row['passed'] is True and isinstance(row['name'], str) for row in checks), 'Failed or empty native checks')
    names = [row['name'] for row in checks]
    required = {'configured-startup-controller-present', 'explicit-creator-project-accepted',
                'duplicate-native-command-idempotent', 'ungranted-member-no-project',
                'native-reader-write-denied', 'native-maintainer-write-accepted',
                'native-stale-revision-rejected', 'restart-preserves-exact-command-receipt',
                'restart-preserves-authorized-work', 'restart-invalidates-native-update-cursor-and-watch'}
    require(required <= set(names), 'Native allow/deny/replay/restart evidence missing')
    require(set(report['restarts']) == {'zod', 'bus', 'nec', 'bud'}
            and all(item.get('passed') is True for item in report['restarts'].values()), 'Cold restart coverage missing')
    inventory = native_units.validate_inventory(inventory)
    entries = [*inventory['suites'], inventory['negative_control']]
    require(len(report['native_units']) == len(entries), 'Native suite count differs')
    transcripts = report['native_unit_transcripts']
    commands = [row for row in report['commands'] if 'native_test' in row]
    require(len(transcripts) == len(entries) == len(commands), 'Native execution trace inventory differs')
    for actual, expected, transcript, command in zip(report['native_units'], entries, transcripts, commands):
        log = bytes.fromhex(transcript['log_hex'])
        require(transcript['path'] == expected['path'] and len(log) == transcript['log_bytes']
                and len(log) <= 262144, 'Native transcript differs')
        require(actual['raw_output'] == log.decode('utf-8', errors='strict') + '\n' + transcript['terminal'], 'Native claimed output differs from transcript')
        observed = command['native_test']
        require(command['ship'] == 'zod' and observed['resolved_path'].endswith(expected['path'])
                and observed['stdout'] == transcript['terminal']
                and observed['timeout_seconds'] == expected.get('timeout_seconds', 60), 'Native runner record differs')
        frame = bytes.fromhex(observed['response_frame_hex'])
        require(len(frame) == 5 + framed_length(frame[:5]) and hashlib.sha256(frame).hexdigest() == observed['response_frame_sha256'], 'Native response bytes differ')
        exit_code = 1 if expected is inventory['negative_control'] else 0
        require(_cue(frame[5:]) == (32, (_atom('avow'), (0, (_atom('noun'), exit_code))))
                and observed['stdout'] == '[32 %avow 0 %noun ' + str(exit_code) + ']', 'Native encoded terminal differs')
        verified = native_units.verify_output(actual['raw_output'], path=expected['path'], expected=expected['arms'],
            succeeds=expected is not inventory['negative_control'], failure_marker=expected.get('marker'))
        require(actual == verified, 'Native unit claims differ from output')
    from negative_result import verify_controls
    verify_controls(value, inputs)
    return value

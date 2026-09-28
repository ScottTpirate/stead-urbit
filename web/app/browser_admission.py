"""Source-bound prerequisites for local automated and human browser trials.

These checks admit existing evidence; they never start or qualify native work.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from collections import Counter

import execution_policy
import team_check
from digests import read_source, sha, source_inventory, source_sha, tree_sha


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate browser evidence field')
        result[key] = value
    return result


def private_json(path, maximum):
    path = Path(path)
    with execution_policy.directory_fd(path.parent) as parent:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(descriptor)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and not info.st_mode & 0o077 and 0 < info.st_size <= maximum,
                'Owned bounded private regular file required')
            with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                raw = stream.read(maximum + 1)
            require(len(raw) == info.st_size, 'Private evidence changed while reading')
        finally:
            os.close(descriptor)
    return json.loads(raw, object_pairs_hook=unique), hashlib.sha256(raw).hexdigest()


def live_reference(status):
    require(status.get('profile') == 'configured-team' and status.get('ready') is True
        and status.get('stage') == 'ready' and status.get('execution_guard', {}).get('state') == 'running',
        'A ready configured fixture with a running guard is required')
    require(set(status.get('ships', {})) == {'zod', 'bus', 'nec', 'bud'}
        and all(row.get('exit') is None and type(row.get('pid')) is int and row['pid'] > 1
                for row in status['ships'].values()), 'All four owned ships must be live')
    reference = status.get('team_evidence')
    require(isinstance(reference, dict) and set(reference) == {'file', 'sha256'}
        and re.fullmatch(r'team-check-[0-9]{8}T[0-9]{6}Z\.json', str(reference['file']))
        and re.fullmatch(r'[0-9a-f]{64}', str(reference['sha256'])), 'The live fixture has no passed team evidence binding')
    require(re.fullmatch(r'[0-9a-f]{32}', str(status['execution_guard'].get('run_id'))), 'Fixture execution identity required')
    return reference


def native_inputs(root):
    root = Path(root)
    return {'native': tree_sha(root / 'native/core/desk'),
        'runner': {name: sha(root / 'scripts/urbit' / name) for name in team_check.DEPENDENCIES},
        'harness': source_sha(root / 'scripts/urbit'), 'ingress': tree_sha(root / 'web/dev'),
        'toolchain': sha(root / 'specs/urbit/toolchain.lock.json'),
        'native_unit_inventory': sha(root / 'specs/urbit/phase2-pure-units.json')}


def passing_checks(rows):
    return isinstance(rows, list) and 0 < len(rows) <= 8192 and all(
        isinstance(row, dict) and row.get('passed') is True and isinstance(row.get('name'), str)
        and row['name'] for row in rows)


def verify_native(report, status, inputs, installed):
    require(report.get('status') == 'pass' and report.get('stage') == 'completed'
        and report.get('classification') == 'local-real-configured-gall-development'
        and report.get('execution_guard', {}).get('run_id') == status['execution_guard']['run_id'],
        'Passed native team evidence for this execution is required')
    require(report.get('inputs_before') == inputs and report.get('inputs_after') == inputs,
        'Native team inputs differ from current source')
    require(installed and report.get('installed') == {ship: installed for ship in ('zod', 'bus', 'nec', 'bud')},
        'Running fixture was not checked with the exact current native files')
    require(passing_checks(report.get('checks')), 'Native team checks are missing or failed')
    restarts = report.get('restarts', {})
    require(set(restarts) == {'zod', 'bus', 'nec', 'bud'}
        and all(row.get('passed') is True for row in restarts.values()), 'Native restart evidence incomplete')


def require_native(root, state, status):
    reference = live_reference(status)
    report, digest = private_json(Path(state) / 'logs' / reference['file'], 16 * 1024 * 1024)
    require(digest == reference['sha256'], 'Native report differs from live supervisor binding')
    verify_native(report, status, native_inputs(root), source_inventory(Path(root) / 'native/core/desk', ignore_python_cache=False))
    return dict(reference)


def browser_inputs(root, status):
    root = Path(root)
    names = {'runner': 'web/app/browser-check.py', 'process_owner': 'web/app/browser_process.py',
        'browser_test': 'web/app/tests/native.mjs', 'boundary_test': 'web/app/tests/native-boundaries.mjs',
        'expiry_test': 'web/app/tests/native-expiry.mjs', 'relay': 'web/dev/loopback_bridge.py',
        'toolchain': 'specs/urbit/toolchain.lock.json', 'admission': 'web/app/browser_admission.py',
        'browser_cases': 'specs/urbit/phase2-browser-cases.json',
        'docs_controls': 'web/app/tests/native-docs-controls.mjs',
        'response_capture': 'web/app/tests/response-capture.mjs'}
    return {**{key: sha(root / name) for key, name in names.items()},
        'frontend_manifest': frontend_binding(root),
        'native_tree': tree_sha(root / 'native/core/desk'),
        'harness': source_sha(root / 'scripts/urbit'),
        'execution_id': status['execution_guard']['run_id'], 'native_prerequisite': dict(live_reference(status))}


def frontend_binding(root):
    raw = read_source(Path(root) / 'web/app/dist/manifest.json', maximum=65536)
    manifest = json.loads(raw, object_pairs_hook=unique)
    require(type(manifest.get('format')) is int and manifest['format'] == 1 and manifest.get('classification') == 'frontend-build-only'
        and isinstance(manifest.get('files'), dict) and 0 < len(manifest['files']) <= 32
        and 'index.html' in manifest['files'],
        'Bounded frontend build manifest required')
    for name, pin in manifest['files'].items():
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,127}', name) and '..' not in name
            and isinstance(pin, dict) and set(pin) == {'bytes','sha256'}
            and type(pin['bytes']) is int and 0 < pin['bytes'] <= 524288
            and re.fullmatch(r'[0-9a-f]{64}', str(pin['sha256'])), 'Invalid frontend asset pin')
        asset = Path(root) / 'native/core/desk/web/stead' / ('asset-' + pin['sha256'] + '.stead-asset')
        body = read_source(asset, maximum=524288)
        require(len(body) == pin['bytes'] and hashlib.sha256(body).hexdigest() == pin['sha256'],
            'Build and packaged native asset bytes differ')
    return hashlib.sha256(raw).hexdigest()


def browser_cases(root):
    value = json.loads(read_source(Path(root) / 'specs/urbit/phase2-browser-cases.json', maximum=16384), object_pairs_hook=unique)
    require(isinstance(value, dict) and set(value) == {'format', 'classification', 'journey', 'natural_expiry'}
        and type(value['format']) is int and value['format'] == 1
        and value['classification'] == 'native-browser-case-inventory', 'Browser case inventory schema')
    for name in ('journey', 'natural_expiry'):
        cases = value[name]
        require(isinstance(cases, dict) and 0 < len(cases) <= 64 and all(
            re.fullmatch(r'[a-z][a-z0-9-]{0,159}', case) and type(count) is int and 1 <= count <= 4
            for case, count in cases.items()), 'Nonempty bounded browser case inventory required')
    return value


def verify_journey(journey, run_id, cases, *, expiry=False):
    classification = 'real-browser-native-natural-session-expiry' if expiry else 'real-browser-native-gall'
    require(isinstance(journey, dict) and journey.get('classification') == classification
        and journey.get('status') == 'pass' and journey.get('execution_id') == run_id
        and passing_checks(journey.get('checks')), 'Passed native browser journey for this execution is required')
    observed = Counter(row['name'] for row in journey['checks'])
    require(observed == cases['natural_expiry' if expiry else 'journey'], 'Browser case inventory differs')
    if expiry:
        require(journey.get('capture_complete') is True and journey.get('capture_errors') == []
            and journey.get('capture_truncated') is False,
            'Complete natural-expiry capture required')
    else:
        require(journey.get('response_capture_complete') is True
            and journey.get('response_capture_error') is False
            and journey.get('responses_truncated', False) is False, 'Complete native browser capture required')


def verify_browser(transport, journey, expected, cases):
    require(transport.get('classification') == 'local-real-browser-native-tls'
        and transport.get('status') == 'pass' and transport.get('inputs_before') == expected
        and transport.get('inputs_after') == expected
        and transport.get('browser_process', {}).get('cleanup', {}).get('empty') is True,
        'Passed browser transport with matching source and complete cleanup is required')
    verify_journey(journey, expected['execution_id'], cases)
    reference = transport.get('stock_git', {})
    require(set(reference) == {'status', 'evidence_file', 'sha256', 'fixture_sha256'}
        and reference['status'] == 'pass'
        and re.fullmatch(r'\.piers/fakes/logs/team-git-[0-9]{8}T[0-9]{6}Z\.json', str(reference['evidence_file']))
        and re.fullmatch(r'[0-9a-f]{64}', str(reference['sha256']))
        and re.fullmatch(r'[0-9a-f]{64}', str(reference['fixture_sha256']))
        and reference['fixture_sha256'] == journey.get('git_fixture_sha256'),
        'Passed native stock Git verification bound to the browser fixture is required')


def require_git(state, reference, expected):
    name = reference.get('evidence_file', '')
    require(re.fullmatch(r'\.piers/fakes/logs/team-git-[0-9]{8}T[0-9]{6}Z\.json', name),
            'Fixed native Git evidence file required')
    report, digest = private_json(Path(state) / 'logs' / Path(name).name, 262144)
    require(digest == reference.get('sha256') and report.get('status') == 'pass'
        and report.get('classification') == 'actual-stock-git-from-configured-v3-native-stores'
        and report.get('fixture_sha256') == reference.get('fixture_sha256')
        and report.get('execution_id') == expected['execution_id']
        and report.get('execution_guard', {}).get('run_id') == expected['execution_id']
        and report.get('native_prerequisite') == expected['native_prerequisite']
        and report.get('inputs_before') == {'native':expected['native_tree'], 'harness':expected['harness']}
        and report.get('inputs_after') == report.get('inputs_before')
        and report.get('checks') == {'exact_receipt_oids': True, 'exact_markdown_and_trees': True,
            'destination_only_ancestry': True, 'private_history_excluded': True},
        'Native Git evidence is missing, failed, stale or changed')
    exports = report.get('exports', {})
    require(set(exports) == {'source', 'published', 'edited'}
        and all(type(item.get('objects')) is int and item['objects'] > 0
            and item.get('commands') and all(command.get('returncode') == 0 for command in item['commands'])
            for item in exports.values()), 'Executed nonempty stock Git exports required')
    for item in exports.values():
        head = item.get('head')
        require(re.fullmatch(r'[0-9a-f]{40}', str(head)), 'Observed Git snapshot required')
        arguments = [row.get('arguments') for row in item['commands']]
        require(all(required in arguments for required in (
            ['init', '--bare', '--template=', '--object-format=sha1'],
            ['symbolic-ref', 'HEAD', 'refs/heads/main'], ['update-ref', 'refs/heads/main', head],
            ['fsck', '--full', '--strict'], ['rev-list', '--parents', head], ['ls-tree', '-rz', head], ['--version']))
            and any(isinstance(args,list) and args[:3] == ['hash-object','-w','-t'] for args in arguments)
            and any(isinstance(args,list) and args[:2] == ['cat-file','blob'] for args in arguments),
            'Required stock Git operations are missing')


def require_browser(root, state, status, name):
    require(re.fullmatch(r'browser-native-[0-9]{8}T[0-9]{6}Z', name), 'Explicit automated browser run required')
    native = require_native(root, state, status)
    folder = Path(root) / '.runtime' / name
    info = folder.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077,
        'Private browser evidence directory required')
    transport, transport_sha = private_json(folder / 'transport-report.json', 262144)
    journey, journey_sha = private_json(folder / 'browser-report.json', 2 * 1024 * 1024)
    require(transport.get('journey_sha256') == journey_sha, 'Browser journey differs from transport binding')
    verify_browser(transport, journey, browser_inputs(root, status), browser_cases(root))
    require_git(state, transport['stock_git'], browser_inputs(root, status))
    return {'native': native, 'browser_run': name, 'transport_sha256': transport_sha,
        'journey_sha256': journey_sha, 'execution_id': status['execution_guard']['run_id']}

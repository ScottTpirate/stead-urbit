"""Source-bound prerequisites for local automated and human browser trials.

These checks admit existing evidence; they never start or qualify native work.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

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
        'toolchain': 'specs/urbit/toolchain.lock.json', 'admission': 'web/app/browser_admission.py'}
    return {**{key: sha(root / name) for key, name in names.items()},
        'frontend_manifest': frontend_binding(root),
        'native_tree': tree_sha(root / 'native/core/desk'),
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


def verify_browser(transport, journey, expected):
    require(transport.get('classification') == 'local-real-browser-native-tls'
        and transport.get('status') == 'pass' and transport.get('inputs_before') == expected
        and transport.get('inputs_after') == expected
        and transport.get('browser_process', {}).get('cleanup', {}).get('empty') is True,
        'Passed browser transport with matching source and complete cleanup is required')
    require(journey.get('classification') == 'real-browser-native-gall' and journey.get('status') == 'pass'
        and journey.get('execution_id') == expected['execution_id'] and passing_checks(journey.get('checks')),
        'Passed native browser journey for this execution is required')


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
    verify_browser(transport, journey, browser_inputs(root, status))
    return {'native': native, 'browser_run': name, 'transport_sha256': transport_sha,
        'journey_sha256': journey_sha, 'execution_id': status['execution_guard']['run_id']}

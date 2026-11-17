"""Fixed saved8 private frame; data validation does not grant execution authority.

The owner must separately prove captured source, the renewable guardian lease,
EOF/reap and an empty whole unit. No supplied noun is evaluated or loaded.
The frozen runner is the source of native p/q observations; this module checks
their exact original byte/custody associations without inventing a Python cue.
"""
from __future__ import annotations

import json
import math
import re

from home_asset_rehearsal import evidence as E

PREFIX = b'STEAD_SAVED8_REHEARSAL_RESULT_V1 '
MAX_FRAME = 4 * 1024 * 1024
MAX_DESCRIPTOR = 8192
BASE = 'a0e90ef29389077d453ec2a775cd8fd69f711727'
TARGET = 'a670d58c7801a48a92ab66139839fd192abbc53b'
PREVIOUS = 'baa226f22bc1950981628486539fa1f087d2e6544c12a18c1d15e144b082e7da'
NEXT = 'd7aa054ca6110bb1a9d9e5a3bd89e5a662d13edb010e3e77e7a9f0ecef2b7afa'
RUNTIME = 'f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833'
KERNEL = '5a187fededc4582a34fcd6055c67bb63e0917b94'
CLEAN = {'clean': True, 'exit_code': 0, 'forced': False, 'premature': False, 'reaped': True}
PHASES = ['fresh-seed8', 'actual-a0-predecessor', 'cold-repeat', 'assets-and-rollback']
READY = ('bootstrap_a0', 'bootstrap_cold', 'bootstrap_assets', 'bootstrap_rollback', 'bootstrap_rollback_cold')
ROUTES = ('routes_a0', 'routes_assets', 'routes_rollback')
DENIALS = ['wrong-host', 'wrong-origin', 'unknown-path', 'query-string', 'unsupported-method',
          'post-to-asset', 'get-body', 'forwarded-header', 'spoofed-plain-tls', 'plain-http',
          'anonymous-protected-api']
BINDINGS = {'run_id', 'controller_commit', 'inputs_sha256', 'worker_sha256', 'guardian_sources_sha256'}
NAMES = tuple(stage + suffix for stage in E.STAGES for suffix in ('.jam', '.json'))
ERRORS = {'none', 'admission-refusal', 'runner-failed', 'artifact-refusal', 'frame-overflow', 'worker-refusal'}
RUNNER_ERRORS = {'none', 'ValueError', 'TimeoutError', 'RuntimeError', 'OSError', 'InterruptedError', 'other'}


def require(ok):
    if not ok:
        raise ValueError('Fixed saved8 outer evidence refused')


def exact(actual, expected):
    require(E.canonical(actual) == E.canonical(expected))


def integer(value, minimum, maximum):
    require(type(value) is int and minimum <= value <= maximum)
    return value


def bindings(value):
    require(type(value) is dict and set(value) == BINDINGS)
    require(type(value['run_id']) is str and re.fullmatch('[0-9a-f]{32}', value['run_id']))
    require(type(value['controller_commit']) is str and re.fullmatch('[0-9a-f]{40}', value['controller_commit']))
    require(all(E.digest(value[key]) for key in BINDINGS - {'run_id', 'controller_commit'}))
    return value


def file_value(raw):
    require(type(raw) is bytes and raw)
    return {'bytes': len(raw), 'sha256': E.sha(raw), 'data_hex': raw.hex()}


def file_bytes(row, maximum):
    require(type(row) is dict and set(row) == {'bytes', 'sha256', 'data_hex'})
    size = integer(row['bytes'], 1, maximum)
    require(E.digest(row['sha256']) and type(row['data_hex']) is str
            and len(row['data_hex']) == 2 * size and re.fullmatch('[0-9a-f]+', row['data_hex']))
    raw = bytes.fromhex(row['data_hex'])
    require(E.sha(raw) == row['sha256'])
    return raw


def proof(row):
    require(type(row) is dict and set(row) == {'capabilities', 'udp', 'uid_map', 'gid_map',
            'uid', 'gid', 'namespaces', 'lens_ports'})
    exact(row['capabilities'], {**dict.fromkeys(('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd'),
          '0000000000000000'), 'NoNewPrivs': '1'})
    require(row['udp'] == '0100007F:7A69')
    integer(row['uid'], 0, 2**32 - 2); integer(row['gid'], 0, 2**32 - 2)
    for key in ('uid_map', 'gid_map'):
        require(type(row[key]) is list and len(row[key]) == 3
                and all(type(v) is str and re.fullmatch('0|[1-9][0-9]{0,9}', v) for v in row[key]))
        require(row[key][0] == '0' and row[key][2] == '1')
    require(type(row['namespaces']) is dict and set(row['namespaces']) == {'net', 'pid', 'mnt', 'user'})
    require(all(type(v) is str and re.fullmatch(key + r':\[[0-9]{1,20}\]', v)
                for key, v in row['namespaces'].items()))
    require(type(row['lens_ports']) is list and 1 <= len(row['lens_ports']) <= 4
            and len(set(row['lens_ports'])) == len(row['lens_ports']))
    for port in row['lens_ports']:
        integer(port, 1, 65535)


def boot(row):
    require(type(row) is dict and set(row) == {'identity', 'boot_seconds', 'pid', 'proof'}
            and row['identity'] == '~zod' and type(row['boot_seconds']) in (int, float)
            and math.isfinite(row['boot_seconds']) and 0 <= row['boot_seconds'] <= 3600)
    integer(row['pid'], 1, 2**31 - 1)
    proof(row['proof'])


def passed_report(report, expected, context_sha, desk_hashes, assets):
    """Closed exact report from the frozen runner, checked independently by root."""
    keys = {'protocol', 'status', 'classification', 'saved_version', 'qualifies_phase',
        'live_pier_used', 'browser_authentication', 'error_class', 'cleanup_error_class',
        'phases', 'captures', 'capture_custody', 'commands', 'restarts', 'elapsed_ms',
        'run_id', 'controller_commit', 'inputs_sha256', 'previous_artifact', 'target_artifact',
        'asset_delta', 'boot', 'tls', 'cleanup', *READY, *ROUTES}
    require(type(report) is dict and set(report) == keys)
    exact({k: report[k] for k in ('protocol', 'status', 'classification', 'saved_version',
        'qualifies_phase', 'live_pier_used', 'browser_authentication', 'error_class', 'cleanup_error_class')},
        {'protocol': 'stead.saved8-asset-rehearsal/1', 'status': 'pass',
        'classification': 'disposable-synthetic-saved8-only', 'saved_version': 8,
        'qualifies_phase': False, 'live_pier_used': False, 'browser_authentication': False,
        'error_class': 'none', 'cleanup_error_class': 'none'})
    exact({k: report[k] for k in ('run_id', 'controller_commit', 'inputs_sha256')},
          {k: expected[k] for k in ('run_id', 'controller_commit', 'inputs_sha256')})
    require(report['previous_artifact'] == PREVIOUS and report['target_artifact'] == NEXT)
    exact(report['phases'], PHASES); exact(report['cleanup'], CLEAN)
    integer(report['elapsed_ms'], 0, 3600000)
    require(E.digest(context_sha) and type(desk_hashes) is dict and set(desk_hashes) == set(E.STAGES)
            and all(E.digest(v) for v in desk_hashes.values()))
    require(type(report['commands']) is list and 1 <= len(report['commands']) <= 4096)
    for row in report['commands']:
        require(type(row) is dict and set(row) == {'source_sha256', 'source_bytes', 'output_sha256', 'output_bytes'}
                and E.digest(row['source_sha256']) and E.digest(row['output_sha256']))
        integer(row['source_bytes'], 1, 65536); integer(row['output_bytes'], 0, 1000000)
    boot(report['boot'])
    require(type(report['restarts']) is list and len(report['restarts']) == 2)
    for row, stage in zip(report['restarts'], ('cold', 'rollback-cold')):
        require(type(row) is dict and set(row) == {'stage', 'cleanup', 'checkpoint', 'boot'} and row['stage'] == stage)
        exact(row['cleanup'], CLEAN); boot(row['boot'])
        checkpoint = row['checkpoint']
        require(type(checkpoint) is dict and set(checkpoint) == {'sha256', 'bytes', 'files'} and E.digest(checkpoint['sha256']))
        integer(checkpoint['bytes'], 1, 1024**3); integer(checkpoint['files'], 1, 8192)
    process_ids = [report['boot']['pid'], *[r['boot']['pid'] for r in report['restarts']]]
    require(len(set(process_ids)) == 3)
    incarnations, nonces = set(), set()
    for key in READY:
        row = report[key]
        require(type(row) is dict and set(row) == {'protocol', 'status', 'home', 'nonce', 'incarnation'}
                and row['protocol'] == 'stead.bootstrap/1' and row['status'] == 'ready'
                and row['home'] == '~zod' and E.digest(row['nonce']) and E.digest(row['incarnation']))
        incarnations.add(row['incarnation']); nonces.add(row['nonce'])
    require(len(incarnations) == len(nonces) == 5)
    require(type(report['tls']) is dict and set(report['tls']) == {'hostname', 'certificate_sha256', 'protocol', 'owned_listeners'}
            and report['tls']['hostname'] == 'home.localhost' and E.digest(report['tls']['certificate_sha256'])
            and report['tls']['protocol'] in ('TLSv1.2', 'TLSv1.3'))
    listeners = report['tls']['owned_listeners']
    require(type(listeners) is list and 1 <= len(listeners) <= 2)
    for row in listeners:
        require(type(row) is dict and set(row) == {'endpoint', 'inode'}
                and type(row['endpoint']) is str and re.fullmatch(r'[0-9A-F]{8,32}:480B', row['endpoint'])
                and type(row['inode']) is str and re.fullmatch('[1-9][0-9]{0,19}', row['inode']))
    require(type(assets) is dict and set(assets) == {'previous', 'target', 'delta'})
    exact(report['asset_delta'], assets['delta'])
    for key in ROUTES:
        row = report[key]
        require(type(row) is dict and set(row) == {'assets', 'denials', 'native_tls', 'browser_authentication', 'capabilities'})
        exact(row['assets'], assets['target' if key == 'routes_assets' else 'previous'])
        exact(row['denials'], DENIALS); E.capabilities(row['capabilities'])
        require(row['native_tls'] is True and row['browser_authentication'] is False)
    require(type(report['captures']) is dict and set(report['captures']) == set(E.STAGES)
            and type(report['capture_custody']) is dict and set(report['capture_custody']) == set(E.STAGES))
    for stage in E.STAGES:
        row = report['capture_custody'][stage]
        require(type(row) is dict and set(row) == {'pid', 'process_proof_sha256', 'desk_inventory_sha256', 'context_sha256'}
                and E.digest(row['process_proof_sha256']) and row['context_sha256'] == context_sha
                and row['desk_inventory_sha256'] == desk_hashes[stage])
        require(type(row['pid']) is int and row['pid'] == process_ids[0 if stage in ('seed8', 'a0-loaded') else 1])


def artifacts(report, files, expected, context_sha):
    require(type(files) is dict and set(files) == set(NAMES))
    rows, result = {}, {}
    metadata_keys = {'protocol', 'stage', 'saved_version', 'artifact_bytes', 'artifact_sha256', *E.PINS}
    extra = {'run_id', 'controller_commit', 'inputs_sha256', 'previous_artifact_sha256',
        'target_artifact_sha256', 'runtime_sha256', 'kernel_commit', 'capture_custody', 'qualifies_phase', 'classification'}
    for stage in E.STAGES:
        raw = file_bytes(files[stage + '.jam'], E.MAX_CAPTURE)
        descriptor_raw = file_bytes(files[stage + '.json'], MAX_DESCRIPTOR)
        descriptor = json.loads(descriptor_raw, object_pairs_hook=E.unique)
        require(type(descriptor) is dict and set(descriptor) == metadata_keys | extra
                and descriptor_raw == E.canonical(descriptor) + b'\n')
        require(descriptor['previous_artifact_sha256'] == PREVIOUS and descriptor['target_artifact_sha256'] == NEXT
                and descriptor['runtime_sha256'] == RUNTIME and descriptor['kernel_commit'] == KERNEL
                and descriptor['qualifies_phase'] is False and descriptor['classification'] == 'synthetic-actual-saved8-rehearsal')
        exact({k: descriptor[k] for k in ('run_id', 'controller_commit', 'inputs_sha256')},
              {k: expected[k] for k in ('run_id', 'controller_commit', 'inputs_sha256')})
        exact(descriptor['capture_custody'], report['capture_custody'][stage])
        require(descriptor['capture_custody']['context_sha256'] == context_sha)
        row = {k: descriptor[k] for k in metadata_keys} | {'data': raw}
        E.validate_capture(row); require(row['stage'] == stage)
        exact(E.metadata(row), report['captures'][stage])
        rows[stage] = row
        result[stage + '.jam'], result[stage + '.json'] = raw, descriptor_raw
    E.complete_stages(rows)
    return result


def encode(value):
    raw = PREFIX + E.canonical(value) + b'\n'
    if len(raw) > MAX_FRAME:
        raise OverflowError('Fixed saved8 total frame bound')
    return raw


def decode(raw, expected, *, context_sha, desk_hashes, assets):
    bindings(expected)
    require(type(raw) is bytes and 0 < len(raw) <= MAX_FRAME
            and raw.startswith(PREFIX) and raw.endswith(b'\n') and raw.count(b'\n') == 1)
    value = json.loads(raw[len(PREFIX):-1], object_pairs_hook=E.unique)
    require(type(value) is dict and set(value) == {'protocol', *BINDINGS, 'status', 'error_class', 'cleanup', 'report', 'artifacts'})
    require(encode(value) == raw and value['protocol'] == 'stead.saved8-hosted-worker/1')
    exact({k: value[k] for k in BINDINGS}, expected)
    require(type(value['status']) is str and value['status'] in ('pass', 'fail')
            and type(value['error_class']) is str and value['error_class'] in ERRORS
            and type(value['cleanup']) is bool)
    if value['status'] == 'fail':
        require(value['error_class'] != 'none' and value['artifacts'] == {})
        failed_report(value['report'])
        return value, {}
    require(value['error_class'] == 'none' and value['cleanup'] is True)
    passed_report(value['report'], expected, context_sha, desk_hashes, assets)
    return value, artifacts(value['report'], value['artifacts'], expected, context_sha)


def failed_report(row):
    if row is None:
        return
    require(type(row) is dict and set(row) == {'protocol', 'status', 'error_class', 'cleanup_error_class',
            'completed_phases', 'captures_observed', 'command_count', 'native_reaped'})
    require(row['protocol'] == 'stead.saved8-failure-observation/1' and row['status'] == 'fail'
            and type(row['error_class']) is str and row['error_class'] in RUNNER_ERRORS
            and row['cleanup_error_class'] in ('none', 'cleanup-refusal', 'artifact-refusal')
            and type(row['completed_phases']) is list and row['completed_phases'] == PHASES[:len(row['completed_phases'])]
            and type(row['captures_observed']) is list and row['captures_observed'] == list(E.STAGES[:len(row['captures_observed'])])
            and type(row['native_reaped']) is bool)
    integer(row['command_count'], 0, 4096)


def failure(expected, error_class, report=None, *, cleanup=False):
    bindings(expected)
    require(error_class in ERRORS - {'none'} and type(cleanup) is bool)
    failed_report(report)
    return encode({'protocol': 'stead.saved8-hosted-worker/1', **expected, 'status': 'fail',
        'error_class': error_class, 'cleanup': cleanup, 'report': report, 'artifacts': {}})

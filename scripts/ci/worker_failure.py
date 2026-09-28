"""Closed, failed-only public diagnostics. No native text or acceptance result."""
from __future__ import annotations

import hashlib
import json
import re

from worker_result import PREFIX, canonical, require, unique

SHIPS = ('zod', 'bus', 'nec', 'bud')
STAGES = ('admission', 'mounts', 'isolation', 'pins', 'supervisor', 'fresh-boot',
          'fresh-ready', 'fresh-mount', 'fresh-stop', 'fresh-copy', 'filesystem-controls',
          'team-lifecycle', 'team-check', 'migration', 'native-controls', 'final-inputs', 'complete')
FRAME_STAGES = ('encode', 'connect', 'send', 'response-header', 'response-body', 'decode', 'parse-terminal')
ERROR_CLASSES = ('ValueError', 'RuntimeError', 'TimeoutError', 'AssertionError', 'OSError',
                 'FileNotFoundError', 'PermissionError', 'InterruptedError', 'KeyError',
                 'TypeError', 'JSONDecodeError', 'BrokenPipeError', 'ConnectionRefusedError')
LOG_MARKERS = {'http_live': b'http: live', 'http_loopback': b'http: loopback',
               'boot_installed': b'boot: installed', 'boot_complete': b'boot: complete',
               'pier_ready': b'pier: ready', 'ames_live': b'ames: live',
               'loom_mapped': b'loom: mapped', 'assertion': b'Assertion',
               'out_of_memory': b'out of memory', 'permission_denied': b'Permission denied'}


def choice(value, values):
    return value if isinstance(value, str) and value in values else 'unrecognized'


def count(value, maximum):
    return len(value) if isinstance(value, (dict, list)) and len(value) <= maximum else None


def error_kind(value):
    if not isinstance(value, str) or len(value) > 8192:
        return {'class': 'unrecognized', 'reason': 'unrecognized'}
    kind, _, message = value.partition(': ')
    reason = 'unrecognized'
    exact = {'Native team suite failed': 'team-suite', 'Fresh base mount absent': 'base-mount',
             'Supported predecessor migration failed': 'migration',
             'Kernel cache poisoned': 'kernel-pin', 'Native lifetime interrupted': 'lifetime',
             'Unclean owned native exit': 'unclean-exit',
             'Cache mount is writable': 'cache-mount',
             'Shared runtime cache is writable': 'cache-write',
             'Cache write refusal was not read-only enforcement': 'cache-errno',
             'Unexpected cache write refusal': 'cache-errno',
             'Missing or changed runtime pin': 'runtime-pin',
             'Seed control needs stopped ships': 'seed-live',
             'Seed poison did not change identity': 'seed-poison',
             'Unexpected seed refusal': 'seed-refusal',
             'Poisoned seed was accepted': 'seed-accepted',
             'Seed restoration differs': 'seed-restoration',
             'Unexpected cache refusal': 'cache-pin-refusal',
             'Truncated runtime cache accepted': 'cache-pin-accepted'}
    if message in exact:
        reason = exact[message]
    elif re.fullmatch(r'(zod|bus|nec|bud) did not become ready within [0-9]{1,4}s', message):
        reason = 'ready-timeout'
    elif re.fullmatch(r'(zod|bus|nec|bud) exited during boot; inspect logs', message):
        reason = 'boot-exit'
    return {'class': choice(kind, ERROR_CLASSES), 'reason': reason}


def snapshot(host):
    """Private controller observations before stopping the owned children."""
    if host is None:
        return {}
    rows = {}
    for ship in SHIPS:
        process = host.PROCESSES.get(ship)
        rows[ship] = {'started': process is not None,
                      'exit_code': process.poll() if process is not None else None,
                      'ports_present': (host.LIVE / ship / '.http.ports').is_file(),
                      'conn_present': (host.LIVE / ship / '.urb/conn.sock').exists(),
                      # This observation covers this worker's full lifetime,
                      # including earlier seed boots, not only the current PID.
                      'kernel_ready_observed': any(item.get('command') == ship + ': zuse'
                                                   for item in host.EVIDENCE)}
    return rows


def capture_snapshot(host):
    # A diagnostic failure must never skip cleanup or replace the main error.
    try:
        return snapshot(host)
    except BaseException:
        return {}


def project(raw, inputs, *, run_id):
    """Read the one complete bound failed frame, then discard all free text."""
    require(isinstance(raw, bytes) and 0 < len(raw) <= 32 * 1024**2, 'Failure output byte bound')
    lines = raw.decode('utf-8', errors='strict').splitlines()
    framed = [line for line in lines if line.startswith(PREFIX)]
    require(len(framed) == 1 and lines[-1] == framed[0], 'One final complete failure frame required')
    value = json.loads(framed[0][len(PREFIX):], object_pairs_hook=unique)
    require(isinstance(value, dict) and value.get('format') == 'stead.local-ci-worker/1'
            and value.get('status') == 'fail', 'Failed worker frame required')
    require(value.get('run_id') == run_id and re.fullmatch(r'[0-9a-f]{32}', run_id)
            and value.get('inputs_sha256') == hashlib.sha256(canonical(inputs)).hexdigest(),
            'Failure input/run identity differs')
    private = value.get('diagnostic', {})
    require(isinstance(private, dict), 'Failure diagnostic shape')
    result = {'classification': 'failed-worker-diagnostic-only', 'qualifies_phase': False,
              'worker_output_sha256': hashlib.sha256(raw).hexdigest(),
              'stage': choice(private.get('stage'), STAGES),
              'ship': choice(private.get('ship'), SHIPS),
              'error': error_kind(value.get('error')),
              'initiating_error': error_kind(private.get('initiating_error')),
              'cleanup_error': error_kind(value.get('cleanup_error')),
              'worker_cleanup': value.get('cleanup') is True}
    cleanup_errors = private.get('seed_cleanup_errors', [])
    require(isinstance(cleanup_errors, list) and len(cleanup_errors) <= 2, 'Failure seed cleanup shape')
    result['seed_cleanup_errors'] = [error_kind(error) for error in cleanup_errors]
    rows = private.get('pre_cleanup', {})
    require(isinstance(rows, dict), 'Failure process shape')
    result['pre_cleanup'] = {}
    for ship in SHIPS:
        row = rows.get(ship, {})
        require(isinstance(row, dict), 'Failure process row')
        exit_code = row.get('exit_code')
        result['pre_cleanup'][ship] = {
            key: row.get(key) is True for key in ('started', 'ports_present', 'conn_present', 'kernel_ready_observed')}
        result['pre_cleanup'][ship]['exit_code'] = exit_code if type(exit_code) is int and -128 <= exit_code <= 255 else None
    native = value.get('native', {})
    require(isinstance(native, dict), 'Failure native shape')
    checks = native.get('checks', [])
    require(isinstance(checks, list) and len(checks) <= 2000, 'Failure check bound')
    result['native'] = {'present': bool(native), 'error': error_kind(native.get('error')),
                        'checks_recorded': len(checks),
                        'checks_passed': sum(isinstance(row, dict) and row.get('passed') is True for row in checks),
                        'checks_failed': sum(isinstance(row, dict) and row.get('passed') is False for row in checks),
                        'commands_recorded': count(native.get('commands'), 10000),
                        'suites_recorded': count(native.get('native_units'), 100),
                        'transcripts_recorded': count(native.get('native_unit_transcripts'), 100),
                        'inputs_match': native.get('inputs_before') == native.get('inputs_after') == inputs.get('expected_native_inputs')}
    trace = native.get('native_failure', {})
    require(isinstance(trace, dict), 'Failure native trace shape')
    result['native']['frame_stage'] = choice(trace.get('stage'), FRAME_STAGES)
    installed = native.get('installed', {})
    require(isinstance(installed, dict), 'Failure install shape')
    result['native']['installed_counts'] = {ship: count(installed.get(ship), 512) for ship in SHIPS}
    logs = value.get('failure_logs', {})
    require(isinstance(logs, dict), 'Failure log shape')
    result['log_observations'] = {}
    for ship in SHIPS:
        row = logs.get(ship, {})
        require(isinstance(row, dict), 'Failure log row')
        encoded = row.get('tail_hex', '')
        require(isinstance(encoded, str) and len(encoded) <= 524288, 'Failure log tail bound')
        tail = bytes.fromhex(encoded)
        size = row.get('bytes_total')
        result['log_observations'][ship] = {
            'bytes_total': size if type(size) is int and 0 <= size <= 32 * 1024**2 else None,
            'tail_present': bool(tail), 'truncated': row.get('truncated') is True,
            'markers': {name: needle in tail for name, needle in LOG_MARKERS.items()}}
    return result

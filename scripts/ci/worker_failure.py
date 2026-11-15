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
ADMISSION_STEPS = ('startup-checkpoint', 'app-inventory', 'tls-verify', 'ingress-arm', 'peer-release', 'record')
ADMISSION_CHECKS = tuple(ship + '-' + name for ship in SHIPS for name in
                         ('owner-bootstrap-acknowledged', 'owned-peer-admission', 'restart-fresh-bootstrap'))
ERROR_CLASSES = ('ValueError', 'RuntimeError', 'TimeoutError', 'AssertionError', 'OSError',
                 'FileNotFoundError', 'PermissionError', 'InterruptedError', 'KeyError',
                 'TypeError', 'JSONDecodeError', 'BrokenPipeError', 'ConnectionRefusedError',
                 'SSLError', 'SSLCertVerificationError')
LOG_MARKERS = {'http_live': b'http: live', 'http_loopback': b'http: loopback',
               'boot_installed': b'boot: installed', 'boot_complete': b'boot: complete',
               'pier_ready': b'pier: ready', 'ames_live': b'ames: live',
               'loom_mapped': b'loom: mapped', 'assertion': b'Assertion',
               'out_of_memory': b'out of memory', 'permission_denied': b'Permission denied'}
MIGRATION_MARKERS = ('find-fork', 'nest-fail', 'build-fail', 'generator-build-fail', 'dojo-lame', 'exit',
                     'stead-ci-migration-load', 'stead-ci-migration-preserved-state',
                     'stead-ci-migration-grants', 'stead-ci-migration-document-denial',
                     'stead-ci-migration-roundtrip', 'stead-ci-migration-rejections')


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
             'native-public-capabilities-current-member': 'capabilities-member',
             'native-capabilities-unbound-sender-denied': 'capabilities-denial',
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
             'Truncated runtime cache accepted': 'cache-pin-accepted',
             'Missing fresh owned startup checkpoint': 'admission-checkpoint',
             'Native app inventory did not return a boolean': 'app-inventory-response',
             'Missing configured application on verified desk': 'app-inventory-absent',
             'TLS listener is not exclusively owned by the current native child': 'tls-listener-ownership',
             'Native TLS child exited': 'tls-child-exit',
             'Native TLS certificate or child mismatch': 'tls-certificate-child',
             'Stale bootstrap completion': 'bootstrap-stale',
             'Bootstrap does not match this live child incarnation': 'bootstrap-incarnation'}
    exact.update({
        'Native bootstrap owner changed': 'bootstrap-owner-changed',
        'Native bootstrap readiness budget exhausted': 'bootstrap-budget',
        'Native bootstrap acknowledgement arrived after deadline': 'bootstrap-late',
        'Native bootstrap acknowledgement differs': 'bootstrap-ack',
        'Native bootstrap readiness not acknowledged': 'bootstrap-readiness',
        'Missing arm fixture failed before discovery':'control-missing-arm-fixture',
        'Specific compiler failure absent':'control-compiler-diagnostic',
        'Compiler control failed outside native compilation':'control-compiler-terminal',
        'Unexpected missing arm refusal':'control-missing-arm-refusal',
        'Missing native arm accepted':'control-missing-arm-accepted',
        'Finite timer positive control failed':'control-timer-positive',
        'Timeout occurred before the native request':'control-timeout-stage',
        'Native timer ignored client timeout':'control-timeout-absent',
        'Runtime did not recover after client timeout':'control-timeout-recovery',
        'Original native frame invalid':'control-source-frame',
        'Injected malformed native frame accepted':'control-injected-frame',
        'Native discovered/executed arm mismatch':'control-arm-inventory',
        'Native test build failed':'control-build',
        'Pure-unit diagnostic complete; qualification disabled':'pure-diagnostic-complete',
    })
    for ship in SHIPS:
        exact[ship + '-owner-bootstrap-acknowledged'] = ship + '-initial-bootstrap'
        exact[ship + '-restart-fresh-bootstrap'] = ship + '-restart-bootstrap'
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


def source_trace(raw, sources):
    """Closed locations and counters against composed bytes; never trace text."""
    require(isinstance(raw, bytes) and len(raw) <= 262144, 'Failure source trace bound')
    require(sources is None or isinstance(sources, dict) and len(sources) <= 512,
            'Failure source inventory bound')
    admitted = {}
    for path, body in (sources or {}).items():
        match = re.fullmatch(r'native/core/desk/(lib|tests|app)/([a-z][a-z0-9-]{0,95})\.hoon', path)
        if not match:
            continue
        require(isinstance(body, bytes) and len(body) <= 4 * 1024**2,
                'Failure source file bound')
        admitted['/' + match[1] + '/' + match[2] + '/hoon'] = (path, body.split(b'\n'))
    module = rb'(?<![a-zA-Z0-9_./-])(/(?:lib|tests|app)/[a-z][a-z0-9-]{0,95}/hoon)(?![a-zA-Z0-9_./-])'
    # %spot uses a rose ':' separator and a leaf with %ud coordinates.
    # rose/wash may wrap at the separator; %ud groups thousands with dots.
    # Only bounded ASCII whitespace and numeric punctuation are accepted.
    ws = rb'[ \t\r\n]{0,256}'
    space = rb'[ \t\r\n]{1,256}'
    number = rb'([0-9]{1,7}|[1-9][0-9]{0,2}(?:\.[0-9]{3}){1,2})'
    pattern = module + ws + rb':' + ws + rb'<\[' + number + space + number + rb'\]\.\[' + number + space + number + rb'\]>'
    counts = dict.fromkeys(('module_mentions', 'admitted_module_mentions', 'span_patterns', 'admitted_span_patterns', 'bounds_rejected'), 0)
    mentions, mentions_truncated = {}, False
    for match in re.finditer(module, raw):
        counts['module_mentions'] += 1
        source = admitted.get(match[1].decode('ascii'))
        if source is None:
            continue
        counts['admitted_module_mentions'] += 1
        path = source[0]; mentions.pop(path, None); mentions[path] = None
        if len(mentions) > 16:
            del mentions[next(iter(mentions))]; mentions_truncated = True
    observed, truncated = {}, False
    for match in re.finditer(pattern, raw):
        counts['span_patterns'] += 1
        source = admitted.get(match[1].decode('ascii'))
        if source is None:
            continue
        counts['admitted_span_patterns'] += 1
        path, lines = source
        start_line, start_column, end_line, end_column = [int(value.replace(b'.', b'')) for value in match.groups()[1:]]
        if not (1 <= start_line <= end_line <= len(lines)
                and 1 <= start_column <= len(lines[start_line - 1]) + 1
                and 1 <= end_column <= len(lines[end_line - 1]) + 1
                and (start_line, start_column) <= (end_line, end_column)):
            counts['bounds_rejected'] += 1
            continue
        key = (path, start_line, start_column, end_line, end_column)
        observed.pop(key, None)
        observed[key] = dict(zip(('path', 'start_line', 'start_column', 'end_line', 'end_column'), key))
        if len(observed) > 16:
            del observed[next(iter(observed))]
            truncated = True
    return {'locations': list(observed.values()), 'truncated': truncated,
            'referenced_admitted_modules': list(mentions), 'modules_truncated': mentions_truncated,
            'counts': {name: min(value, 4096) for name, value in counts.items()},
            'counts_truncated': any(value > 4096 for value in counts.values())}


def source_spans(raw, sources):
    value = source_trace(raw, sources)
    return {name: value[name] for name in ('locations', 'truncated')}


def unit_structure(raw, path, names):
    """Counts and trusted module/arm labels only, never a line or free text."""
    lines = raw.splitlines()
    counts = dict.fromkeys(('built', 'prompt', 'OK', 'FAILED', 'CRASHED', 'bang', 'source_path', 'other', 'empty'), 0)
    for line in lines[:4096]:
        line = line.lstrip(b' \t')
        category = 'other'
        if not line:
            category = 'empty'
        elif line.startswith(b'>'):
            category = 'prompt'
        elif line.startswith(b'!'):
            category = 'bang'
        elif re.match(rb'/(?:lib|tests|app)/[a-z][a-z0-9-]{0,95}/hoon(?:[: \t]|$)', line):
            category = 'source_path'
        else:
            for label in ('built', 'OK', 'FAILED', 'CRASHED'):
                if re.match(label.encode() + rb'(?:[ \t]|$)', line):
                    category = label
                    break
        counts[category] += 1
    built = failed = False
    compile_arms = []
    if path != 'unrecognized':
        module = re.escape((path + '/hoon').encode())
        built = any(re.fullmatch(rb'[ \t]*built[ \t]+' + module + rb'[ \t]*', line) for line in lines)
        failed = any(re.fullmatch(rb'[ \t]*FAILED[ \t]+' + module + rb'[ \t]+\(build\)[ \t]*', line) for line in lines)
        for name in sorted(names):
            if re.search(rb'\[%?failed-to-compile-test-arm[ \t\r\n]{1,256}%?' + re.escape(name.encode()) + rb'[ \t\r\n]{0,256}\]', raw):
                compile_arms.append(name)
    return {'line_count': len(lines), 'prefix_counts': counts, 'prefix_counts_truncated': len(lines) > 4096,
            'module_built': built, 'module_build_failed': failed, 'compile_failed_registered_arms': compile_arms}


def unit_observation(native, inventory, sources=None):
    """Expose only a registered suite, arm verdicts and fixed compiler markers."""
    import native_units
    entries = []
    if inventory is not None:
        checked = native_units.validate_inventory(inventory)
        entries = [*checked['suites'], checked['negative_control']]
    registered = {entry['path']: set(entry['arms']) for entry in entries}
    transcripts = native.get('native_unit_transcripts', [])
    require(isinstance(transcripts, list) and len(transcripts) <= 100, 'Failure transcript count')
    row = transcripts[-1] if transcripts else {}
    require(isinstance(row, dict), 'Failure transcript shape')
    path = choice(row.get('path'), registered)
    encoded = row.get('log_hex', '')
    require(isinstance(encoded, str) and len(encoded) <= 524288
            and re.fullmatch(r'(?:[0-9a-f]{2})*', encoded), 'Failure transcript byte bound')
    raw = bytes.fromhex(encoded)
    outcomes = []
    for line in raw.decode('utf-8', errors='replace').splitlines():
        matched = re.fullmatch(r'\s*(OK|FAILED|CRASHED)\s+(/[^\s]+)\s*', line)
        if matched and path in registered:
            prefix = path + '/'
            name = matched[2].removeprefix(prefix)
            if matched[2].startswith(prefix) and name in registered[path]:
                outcomes.append({'arm': name, 'outcome': matched[1]})
    names = [row['arm'] for row in outcomes]
    require(len(names) <= len(registered.get(path, ())) and len(names) == len(set(names)),
            'Failure transcript duplicate verdict or suite bound')
    markers = ('find-fork', 'nest-fail', 'build-fail', 'generator-build-fail',
               'mint-vain', 'mint-lost', 'mint-nice', 'nest-need', 'mull-bonk',
               'failed-to-compile-test-arm', 'find-limb', 'find.$', 'dojo-lame', 'syntax error', 'exit')
    return {'path': path, 'log_bytes': len(raw),
            'log_sha256': hashlib.sha256(raw).hexdigest() if raw else None,
            'terminal': choice(row.get('terminal'), ('[32 %avow 0 %noun 0]', '[32 %avow 0 %noun 1]')),
            'registered_arm_observations': outcomes,
            'structure': unit_structure(raw, path, registered.get(path, ())),
            'source_spans': source_spans(raw, sources),
            'source_trace': {key: value for key, value in source_trace(raw, sources).items() if key not in ('locations', 'truncated')},
            'markers': {name: bool(re.search(rb'(?<![a-z0-9-])' + re.escape(name.encode('ascii'))
                                            + rb'(?![a-z0-9-])', raw)) for name in markers}}



def failed_unit_observations(native, inventory, sources=None):
    """Each failed registered suite, with the same closed per-unit schema."""
    diagnostic = native.get('diagnostic_only', False)
    require(type(diagnostic) is bool, 'Failure diagnostic flag')
    failures = native.get('native_unit_failures', [])
    require(isinstance(failures, list), 'Failure diagnostic suite list')
    if not diagnostic:
        require(not failures, 'Normal run cannot claim diagnostic failures')
        return []
    import native_units
    checked = native_units.validate_inventory(inventory)
    entries = [*checked['suites'], checked['negative_control']]
    allowed = {entry['path'] for entry in entries}
    require(len(failures) <= len(entries) and all(isinstance(path, str) and path in allowed for path in failures)
            and len(failures) == len(set(failures)), 'Failure diagnostic suite names')
    transcripts = native.get('native_unit_transcripts', [])
    require(isinstance(transcripts, list) and len(transcripts) <= len(entries), 'Failure diagnostic transcript bound')
    observed = {}
    for row in transcripts:
        require(isinstance(row, dict) and isinstance(row.get('path'), str) and row['path'] in allowed
                and row['path'] not in observed, 'Failure diagnostic transcript identity')
        observed[row['path']] = row
    require(set(failures) <= set(observed), 'Failure diagnostic transcript absent')
    return [unit_observation({'native_unit_transcripts': [observed[path]]}, inventory, sources) for path in failures]


def project(raw, inputs, *, run_id, inventory=None, sources=None):
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
    result['native']['last_unit'] = unit_observation(native, inventory, sources)
    result['native']['diagnostic_only'] = native.get('diagnostic_only') is True
    result['native']['failed_units'] = failed_unit_observations(native, inventory, sources)
    admission = native.get('admission_failure', {})
    require(isinstance(admission, dict), 'Failure admission shape')
    rollbacks = admission.get('rollback_errors', [])
    require(isinstance(rollbacks, list) and len(rollbacks) <= 2, 'Failure admission rollback bound')
    retirement = admission.get('ingress_retirement', {})
    require(isinstance(retirement, dict), 'Failure ingress retirement shape')
    result['native']['admission'] = {
        'ship': choice(admission.get('ship'), SHIPS),
        'mode': choice(admission.get('mode'), ('initial', 'restart')),
        'step': choice(admission.get('step'), ADMISSION_STEPS),
        'error': error_kind(admission.get('error')),
        'rollback_errors': [error_kind(error) for error in rollbacks],
        'ingress_retirement': {
            'cause': choice(retirement.get('cause'), ('guard-refusal', 'child-not-live', 'liveness-error',
                                                     'explicit-disarm', 'invalid-ack', 'close')),
            'error': choice(retirement.get('error'), ('none', 'control-input', 'control-replaced',
                'lease-clock', 'lease-backwards', 'lease-generation', 'lease-stopped',
                'affinity-changed', 'fixture-stopped'))},
        'last_completed_check': next((row['name'] for row in reversed(checks)
                                     if isinstance(row, dict) and row.get('passed') is True
                                     and isinstance(row.get('name'), str)
                                     and row['name'] in ADMISSION_CHECKS), 'unrecognized')}
    installed = native.get('installed', {})
    require(isinstance(installed, dict), 'Failure install shape')
    result['native']['installed_counts'] = {ship: count(installed.get(ship), 512) for ship in SHIPS}
    migration = value.get('migration', {})
    require(isinstance(migration, dict), 'Failure migration shape')
    output = migration.get('output')
    require(output is None or isinstance(output, str) and len(output) <= 1_000_000,
            'Failure migration output bound')
    encoded = output.encode('utf-8', errors='strict') if output is not None else b''
    require(len(encoded) <= 1_000_000, 'Failure migration output byte bound')
    # Only the exact migration response contributes these observations. Earlier
    # deliberate compiler failures in the shared native log cannot taint them.
    result['migration'] = {
        'present': output is not None,
        'output_bytes': len(encoded),
        'output_sha256': hashlib.sha256(encoded).hexdigest() if output is not None else None,
        'markers': {name: bool(re.search(rb'(?<![a-z0-9-])' + re.escape(name.encode('ascii'))
                                         + rb'(?![a-z0-9-])', encoded))
                    for name in MIGRATION_MARKERS}}
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

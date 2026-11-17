"""Closed, failed-only public diagnostics. No native text or acceptance result."""
from __future__ import annotations

import hashlib
import json
import re

from worker_result import PREFIX, canonical, require, unique

SHIPS = ('zod', 'bus', 'nec', 'bud')
STAGES = ('admission', 'mounts', 'isolation', 'pins', 'supervisor', 'doc-worker', 'fresh-boot',
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
    exact = {'Hosted Doc child proof failed': 'doc-worker-proof',
             'Doc proof requires the hosted owner': 'doc-worker-owner',
             'Doc proof custody differs': 'doc-worker-custody',
             'Doc proof admission identity differs': 'doc-worker-identity',
             'Doc proof belongs to another guardian': 'doc-worker-guardian',
             'Doc proof mapped owner differs': 'doc-worker-mapped-owner',
             'Native team suite failed': 'team-suite', 'Fresh base mount absent': 'base-mount',
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
        'Native diagnostic evidence budget reached':'pure-diagnostic-budget',
        'Native diagnostic build result refused':'pure-diagnostic-build-refusal',
        'Native diagnostic interrupted':'pure-diagnostic-interrupted',
    })
    for ship in SHIPS:
        exact[ship + ':+stead-build-probe'] = ship + '-build-probe'
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
    # +mint %dbug uses +show %o: /path::[L C].[L C]>.
    # Runtime +mook %spot instead uses /path:<[L C].[L C]>.
    opening = rb'(?::' + ws + rb'<\[|::' + ws + rb'\[)'
    pattern = module + ws + opening + number + space + number + rb'\]\.\[' + number + space + number + rb'\]>'
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


def parser_positions(raw, sources):
    """+scan positions, explicitly associated by a sole module reference.

    Pinned +scan renders {%d %d} and a separate 'syntax error' leaf. This is
    not a compiler source span. Retain no text, and do not guess among two
    module references or associate a position with an unadmitted module.
    """
    require(isinstance(raw, bytes) and len(raw) <= 262144, 'Failure parser byte bound')
    require(sources is None or isinstance(sources, dict) and len(sources) <= 512,
            'Failure parser inventory bound')
    # Ambiguity detection includes all Hoon namespaces, even those absent
    # from the candidate allowlist. Only exact admitted bytes can be output.
    module = rb'(?<![a-zA-Z0-9_./-])(/[a-z][a-z0-9-]{0,31}/[a-z][a-z0-9-]{0,95}/hoon)(?![a-zA-Z0-9_./-])'
    referenced = {match[1] for match in re.finditer(module, raw)}
    syntax = bool(re.search(rb'(?<![a-z0-9-])syntax error(?![a-z0-9-])', raw))
    source = None
    if syntax and len(referenced) == 1:
        reference = next(iter(referenced)).decode('ascii')
        path = 'native/core/desk' + reference[:-5] + '.hoon'
        body = (sources or {}).get(path)
        if body is not None:
            require(isinstance(body, bytes) and len(body) <= 4 * 1024**2,
                    'Failure parser source bound')
            source = (path, body.split(b'\n'))
    result = {'association': 'sole-referenced-admitted-module' if source else 'unresolved',
              'path': source[0] if source else None, 'syntax_error_observed': syntax,
              'positions': [], 'truncated': False, 'position_patterns': 0,
              'bounds_rejected': 0, 'counts_truncated': False}
    if not syntax:
        return result
    number = rb'([0-9]{1,7}|[1-9][0-9]{0,2}(?:\.[0-9]{3}){1,2})'
    pattern = rb'(?<![a-zA-Z0-9_.{}-])\{' + number + rb'[ \t\r\n]{1,256}' + number + rb'\}(?![a-zA-Z0-9_.{}-])'
    observed = {}
    for match in re.finditer(pattern, raw):
        result['position_patterns'] += 1
        if source is None:
            continue
        line, column = [int(value.replace(b'.', b'')) for value in match.groups()]
        lines = source[1]
        if not (1 <= line <= len(lines) and 1 <= column <= len(lines[line - 1]) + 1):
            result['bounds_rejected'] += 1
            continue
        key = (line, column)
        observed.pop(key, None)
        observed[key] = {'line': line, 'column': column}
        if len(observed) > 16:
            del observed[next(iter(observed))]
            result['truncated'] = True
    result['positions'] = list(observed.values())
    result['counts_truncated'] = any(result[key] > 4096 for key in ('position_patterns', 'bounds_rejected'))
    for key in ('position_patterns', 'bounds_rejected'):
        result[key] = min(result[key], 4096)
    return result


def clay_parser_locations(raw, sources):
    """Pinned Clay +report-error embeds the position and path in one leaf.

    Keep only exact admitted paths and bounded numeric coordinates. The next
    leaves contain source text and a caret; none of that text is retained.
    This direct formatter association is separate from +scan's heuristic.
    """
    require(isinstance(raw, bytes) and len(raw) <= 262144, 'Failure parser byte bound')
    require(sources is None or isinstance(sources, dict) and len(sources) <= 512,
            'Failure parser inventory bound')
    space = rb'[ \t\r\n]{1,256}'
    optional = rb'[ \t\r\n]{0,256}'
    number = rb'([0-9]{1,7}|[1-9][0-9]{0,2}(?:\.[0-9]{3}){1,2})'
    module = rb'(/[a-z][a-z0-9-]{0,31}/[a-z][a-z0-9-]{0,95}/hoon)'
    pattern = (rb'(?<![a-zA-Z0-9_.-])syntax error at' + space + rb'\[' + optional
               + number + space + number + optional + rb'\]' + space + rb'in'
               + space + module + rb'(?![a-zA-Z0-9_./-])')
    counts = dict.fromkeys(('position_patterns', 'admitted_position_patterns', 'bounds_rejected'), 0)
    observed, truncated = {}, False
    for match in re.finditer(pattern, raw):
        counts['position_patterns'] += 1
        path = 'native/core/desk' + match[3].decode('ascii')[:-5] + '.hoon'
        body = (sources or {}).get(path)
        if body is None:
            continue
        require(isinstance(body, bytes) and len(body) <= 4 * 1024**2,
                'Failure parser source bound')
        counts['admitted_position_patterns'] += 1
        line, column = [int(value.replace(b'.', b'')) for value in match.groups()[:2]]
        lines = body.split(b'\n')
        if not (1 <= line <= len(lines) and 1 <= column <= len(lines[line - 1]) + 1):
            counts['bounds_rejected'] += 1
            continue
        key = (path, line, column)
        observed.pop(key, None)
        observed[key] = dict(zip(('path', 'line', 'column'), key))
        if len(observed) > 16:
            del observed[next(iter(observed))]
            truncated = True
    return {'locations': list(observed.values()), 'truncated': truncated,
            'counts': {name: min(value, 4096) for name, value in counts.items()},
            'counts_truncated': any(value > 4096 for value in counts.values())}


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
        if native.get('diagnostic_scope') is not None:
            native_units.validate_restore_scope(native['diagnostic_scope'])
            entries = native_units.restore_entries(inventory)
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
    result = {'path': path, 'log_bytes': len(raw),
            'log_sha256': hashlib.sha256(raw).hexdigest() if raw else None,
            'terminal': choice(row.get('terminal'), ('[32 %avow 0 %noun 0]', '[32 %avow 0 %noun 1]')),
            'registered_arm_observations': outcomes,
            'structure': unit_structure(raw, path, registered.get(path, ())),
            'source_spans': source_spans(raw, sources),
            'parser_positions': parser_positions(raw, sources),
            'clay_parser_locations': clay_parser_locations(raw, sources),
            'source_trace': {key: value for key, value in source_trace(raw, sources).items() if key not in ('locations', 'truncated')},
            'markers': {name: bool(re.search(rb'(?<![a-z0-9-])' + re.escape(name.encode('ascii'))
                                            + rb'(?![a-z0-9-])', raw)) for name in markers}}
    if path == native_units.TRACE_PATH:
        result['stages'] = native_units.trace_progress(raw)
    return result



def build_probe_observations(native, sources=None):
    """Fixed known Dojo probe only; no result text or unrelated log tail."""
    rows = native.get('build_probe_transcripts', [])
    require(isinstance(rows, list) and len(rows) <= 4, 'Build probe count bound')
    commands = native.get('commands', [])
    require(isinstance(commands, list) and len(commands) <= 10000, 'Build probe command bound')
    seen, result = set(), []
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'ship', 'dojo', 'log_offset', 'log_bytes', 'log_hex'},
                'Build probe transcript shape')
        ship = row['ship']
        require(isinstance(ship, str) and ship in SHIPS and ship not in seen
                and row['dojo'] == '+stead-build-probe', 'Build probe identity')
        seen.add(ship)
        encoded = row['log_hex']
        require(type(row['log_offset']) is int and 0 <= row['log_offset'] <= 32 * 1024**2
                and type(row['log_bytes']) is int and 0 <= row['log_bytes'] <= 262144
                and isinstance(encoded, str) and len(encoded) == row['log_bytes'] * 2
                and re.fullmatch(r'(?:[0-9a-f]{2})*', encoded), 'Build probe byte bound')
        matches = [entry for entry in commands if isinstance(entry, dict)
                   and entry.get('ship') == ship and entry.get('dojo') == '+stead-build-probe']
        require(len(matches) <= 1 and (not matches or set(matches[0]) == {'ship', 'dojo', 'result'}),
                'Build probe exact command correspondence')
        terminal = matches[0]['result'] if matches else ''
        require(isinstance(terminal, str), 'Build probe result type')
        raw_terminal = terminal.encode('utf-8', errors='strict')
        require(len(raw_terminal) <= 32768, 'Build probe result byte bound')
        observation = unit_observation({'native_unit_transcripts': [{'log_hex': encoded}]}, None, sources)
        terminal_observation = unit_observation({'native_unit_transcripts': [{'log_hex': raw_terminal.hex()}]}, None, sources)
        result.append({'ship': ship, 'probe': 'stead-build-probe',
            'result_recorded': bool(matches),
            'result_bytes': len(raw_terminal), 'result_sha256': hashlib.sha256(raw_terminal).hexdigest() if matches else None,
            'expected_result_observed': bool(matches) and terminal.strip() == '%stead-builds-pass',
            'result_observation': {key: terminal_observation[key] for key in ('structure', 'source_spans', 'parser_positions', 'clay_parser_locations', 'source_trace', 'markers')},
            **{key: observation[key] for key in ('log_bytes', 'log_sha256', 'structure', 'source_spans', 'parser_positions', 'clay_parser_locations', 'source_trace', 'markers')}})
    return result


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
    if native.get('diagnostic_scope') is not None:
        native_units.validate_restore_scope(native['diagnostic_scope'])
        entries = native_units.restore_entries(inventory)
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
    return [unit_observation({'native_unit_transcripts': [observed[path]], **({'diagnostic_scope': native['diagnostic_scope']} if native.get('diagnostic_scope') is not None else {})}, inventory, sources) for path in failures]


def diagnostic_limits(native, inventory):
    """Closed omitted-evidence metadata; never a replacement suite verdict."""
    import native_units
    checked = native_units.validate_inventory(inventory)
    allowed = {row['path'] for row in [*checked['suites'], checked['negative_control']]}
    phases = ('startup', 'command', 'check', 'checkpoint', 'build', 'suite', 'final')
    stop = native.get('diagnostic_budget_stop')
    interruption = native.get('diagnostic_interruption')
    result = {'budget_stop': None, 'interruption': None}
    scope = native.get('diagnostic_scope')
    if scope is not None:
        result['scope'] = native_units.validate_restore_scope(scope)
        selected_paths = [row['path'] for row in native_units.restore_entries(inventory)]
        selected = set(selected_paths)
        for field in ('native_units', 'native_unit_transcripts'):
            rows = native.get(field, [])
            require(type(rows) is list and len(rows) <= 2
                and all(type(row) is dict and type(row.get('path')) is str
                    and row['path'] in selected for row in rows),
                'Focused diagnostic row scope')
            paths = [row['path'] for row in rows]
            require(len(set(paths)) == len(paths)
                and paths == [path for path in selected_paths if path in paths]
                and (field != 'native_unit_transcripts' or paths == selected_paths[:len(paths)]),
                'Focused diagnostic row order')
        failures = native.get('native_unit_failures', [])
        require(type(failures) is list and len(failures) <= 2
            and all(type(path) is str and path in selected for path in failures),
            'Focused diagnostic failure scope')
        require(len(set(failures)) == len(failures)
            and failures == [path for path in selected_paths if path in failures],
            'Focused diagnostic failure order')
        allowed = selected
    if stop is not None:
        require(isinstance(stop, dict) and set(stop) == {
            'phase', 'path', 'staged_bytes', 'staged_sha256', 'retained_bytes', 'limit_bytes', 'omitted'},
            'Diagnostic budget fields')
        require(isinstance(stop['phase'], str) and isinstance(stop['path'], str)
                and stop['phase'] in phases and stop['path'] in allowed | {''}
                and (stop['phase'] == 'suite') == (stop['path'] in allowed), 'Diagnostic budget identity')
        require(all(type(stop[key]) is int for key in ('staged_bytes', 'retained_bytes', 'limit_bytes'))
                and stop['limit_bytes'] == (4 * 1024**2 - 128 * 1024
                    if stop['phase'] == 'final' else 2 * 1024**2)
                and 0 < stop['retained_bytes'] <= stop['limit_bytes'] < stop['staged_bytes'] <= 64 * 1024**2
                and stop['omitted'] is True
                and isinstance(stop['staged_sha256'], str)
                and re.fullmatch('[0-9a-f]{64}', stop['staged_sha256']), 'Diagnostic budget bounds')
        if stop['path']:
            require(not any(row.get('path') == stop['path'] for row in native.get('native_units', []))
                    and stop['path'] not in native.get('native_unit_failures', [])
                    and not any(row.get('path') == stop['path'] for row in native.get('native_unit_transcripts', []))
                    and not any(isinstance(row, dict) and row.get('passed') is True
                        and row.get('name') in ('native-unit-arms:' + stop['path'],
                                               'native-unit-expected-failure:' + stop['path'])
                        for row in native.get('checks', [])),
                    'Omitted suite cannot claim retained execution verdict')
        result['budget_stop'] = dict(stop)
    if interruption is not None:
        require(isinstance(interruption, dict) and set(interruption) == {
            'phase', 'path', 'error_class', 'evidence_bytes', 'evidence_sha256', 'raw_evidence_omitted'},
            'Diagnostic interruption fields')
        require(isinstance(interruption['phase'], str) and isinstance(interruption['path'], str)
                and interruption['phase'] in phases and interruption['path'] in allowed | {''}
                and (interruption['phase'] == 'suite') == (interruption['path'] in allowed),
                'Diagnostic interruption identity')
        require(interruption['error_class'] in {
            'AssertionError', 'ValueError', 'TypeError', 'RuntimeError', 'TimeoutError', 'OSError',
            'ConnectionError', 'ConnectionResetError', 'BrokenPipeError', 'PermissionError',
            'FileNotFoundError', 'InterruptedError', 'GuardError', 'CalledProcessError',
            'TimeoutExpired', 'JSONDecodeError', 'UnicodeDecodeError', 'unrecognized'}
            and type(interruption['evidence_bytes']) is int
            and 0 <= interruption['evidence_bytes'] <= 64 * 1024**2
            and interruption['raw_evidence_omitted'] is True, 'Diagnostic interruption bounds')
        digest = interruption['evidence_sha256']
        require((interruption['evidence_bytes'] == 0 and digest is None)
                or (interruption['evidence_bytes'] > 0 and isinstance(digest, str)
                    and re.fullmatch('[0-9a-f]{64}', digest)), 'Diagnostic interruption digest')
        result['interruption'] = dict(interruption)
    progress = native.get('diagnostic_unit_interruption')
    if progress is not None:
        require(scope is not None and interruption is not None
            and interruption['phase'] == 'suite', 'Interrupted unit scope required')
        native_units.validate_interrupted_unit(progress, inventory)
        require(progress['path'] == interruption['path'], 'Interrupted unit path differs')
        retained = native.get('native_unit_transcripts', [])
        require(len(retained) < 2 and progress['path'] == selected_paths[len(retained)],
            'Interrupted unit is not the next fixed entry')
        require(not any(row.get('path') == progress['path'] for row in native.get('native_units', []))
            and not any(row.get('path') == progress['path'] for row in native.get('native_unit_transcripts', []))
            and progress['path'] not in native.get('native_unit_failures', [])
            and not any(type(row) is dict and row.get('passed') is True
                and row.get('name') in ('native-unit-arms:' + progress['path'],
                                       'native-unit-expected-failure:' + progress['path'])
                for row in native.get('checks', [])), 'Interrupted unit cannot claim completion')
        result['unit_progress'] = progress
    return result


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
    require(isinstance(checks, list) and len(checks) <= 4096, 'Failure check bound')
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
    if native.get('diagnostic_scope') is not None:
        import native_units
        native_units.validate_restore_scope(native['diagnostic_scope'])
        require(type(sources) is dict, 'Fixed trace source bytes required')
        native_units.verify_trace_sources({name: sources.get(name) for name in native_units.TRACE_SOURCES})
    result['native']['last_unit'] = unit_observation(native, inventory, sources)
    result['native']['build_probes'] = build_probe_observations(native, sources)
    result['native']['diagnostic_only'] = native.get('diagnostic_only') is True
    result['native']['failed_units'] = failed_unit_observations(native, inventory, sources)
    if native.get('diagnostic_only') is True:
        result['native']['diagnostic_limits'] = diagnostic_limits(native, inventory)
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
    result['doc_worker'] = {'status': 'unobserved'}
    if 'doc_worker' in value:
        from doc_worker_proof import verify as verify_doc_worker
        verify_doc_worker(value['doc_worker'],
            inputs['controller_files']['scripts/urbit/doc_run_worker.py']['sha256'],
            inputs['controller_files']['scripts/ci/doc_worker_proof.py']['sha256'])
        result['doc_worker'] = value['doc_worker']
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

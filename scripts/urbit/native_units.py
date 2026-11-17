"""Closed output verification for pinned Arvo's real -test thread.

This parses observations; it cannot execute a Hoon arm or qualify an endpoint.
Missing/duplicate arms and an empty nominally green result are failures.
"""
from __future__ import annotations

import re


RESTORE_PATH = '/tests/stead-product-restore'
NEGATIVE_PATH = '/controls/stead-unit-failure'
RESTORE_ARM = 'test-product-restore-incremental-checkpoint-exposes-no-partial-state'
TRACE_PATH = '/tests/stead-product-restore-checkpoint-trace'
TRACE_THREAD = 'stead-restore-checkpoint-trace'
TRACE_PREFIX = 'stead.restore-checkpoint-trace/1'
TRACE_BODY = ('body-enter', 'begin-complete', 'first-step-complete', 'checkpoint-complete', 'replay-complete')
TRACE_ARMS = ('test-product-restore-old-history-path-retains-predecessor-semantics', 'test-product-restore-mixed-replay-is-exact-and-retains-rejected-attempts', 'test-product-restore-rejects-rehashed-command-receipt-and-completion-changes', 'test-product-restore-rejects-reordered-dropped-and-noncanonical-events', 'test-product-restore-missing-history-and-unrecorded-configuration-fail-closed', 'test-product-restore-boundary-and-current-state-must-match-reconstruction', 'test-product-restore-incremental-checkpoint-exposes-no-partial-state', 'test-product-restore-admission-retains-core-and-sidecar-record-bounds')
TRACE_SOURCES = {'native/core/desk/tests/stead-product-restore.hoon': 'e8e0a1709e5fce6f51d6216e2781242d30f84428b8e2dcca9bb1eb47e0899469', 'native/core/desk/tests/stead-product-restore-checkpoint-trace.hoon': 'e8ea955abb6f38a8f11c75c7563c25e5266e70a445dd20275515b20871024cae', 'native/core/desk/ted/stead-restore-checkpoint-trace.hoon': '0ddc216f38f76df3c40242c7c83d686121f4bf777cd24415947e0d93e6c8e1f7'}
INTERRUPTION_STAGES = ('encode', 'connect', 'send', 'response-header',
                       'response-body', 'decode', 'parse-terminal')


def restore_scope():
    return {'profile': 'restore-checkpoint-trace/1', 'paths': [NEGATIVE_PATH, TRACE_PATH],
            'selected_arm': RESTORE_ARM,
            'positive_suites': 1, 'positive_arms': 1, 'negative_controls': 1,
            'timeout_seconds': 60, 'qualification': False}


def diagnostic_require(value):
    if not value:
        raise ValueError('Closed restore interruption refused')


def validate_restore_scope(value):
    import json
    diagnostic_require(type(value) is dict and
        json.dumps(value, sort_keys=True, allow_nan=False) ==
        json.dumps(restore_scope(), sort_keys=True, allow_nan=False))
    return value


def restore_entries(inventory):
    checked = validate_inventory(inventory)
    entry = next(row for row in checked['suites'] if row['path'] == RESTORE_PATH)
    diagnostic_require(RESTORE_ARM in entry['arms'])
    return [checked['negative_control'], dict(entry, path=TRACE_PATH, arms=[RESTORE_ARM])]


def restore_request_path(entry):
    """Fixed private hint-only copy; original eight bodies and assertions retained."""
    if entry == {'path': NEGATIVE_PATH, 'arms': ['test-deliberate-failure'],
                 'marker': 'stead-intentional-native-unit-failure'}:
        return NEGATIVE_PATH
    diagnostic_require(type(entry) is dict and type(entry.get('timeout_seconds')) is int
                        and entry == {'path': TRACE_PATH, 'arms': [RESTORE_ARM],
                                 'timeout_seconds': 60})
    return TRACE_PATH + '/' + RESTORE_ARM


def verify_trace_sources(files):
    """Closed source bytes; no caller-selected module, thread or original."""
    import hashlib
    diagnostic_require(type(files) is dict and set(files) == set(TRACE_SOURCES))
    diagnostic_require(all(type(raw) is bytes and len(raw) <= 262144
        and hashlib.sha256(raw).hexdigest() == TRACE_SOURCES[name] for name, raw in files.items()))
    original = files['native/core/desk/tests/stead-product-restore.hoon']
    diagnostic = files['native/core/desk/tests/stead-product-restore-checkpoint-trace.hoon']
    removed = b''.join(line for line in diagnostic.splitlines(keepends=True) if TRACE_PREFIX.encode() not in line)
    diagnostic_require(removed == original)
    return dict(TRACE_SOURCES)


def validate_trace_progress(value):
    """All hints remain source-correlated observations, never arm verdicts."""
    import json
    diagnostic_require(type(value) is dict and set(value) == {'protocol', 'sources', 'status', 'markers'}
        and value['protocol'] == 'stead.restore-checkpoint-stages/1'
        and type(value['status']) is str and value['status'] in ('observed', 'malformed')
        and json.dumps(value['sources'], sort_keys=True, allow_nan=False) == json.dumps(TRACE_SOURCES, sort_keys=True)
        and type(value['markers']) is list and len(value['markers']) <= 23)
    pending, compiled, running, ended, body = None, set(), False, False, 0
    for row in value['markers']:
        diagnostic_require(type(row) is dict and set(row) == {'phase', 'arm'}
            and type(row['phase']) is str and type(row['arm']) is str)
        phase, arm = row['phase'], row['arm']
        if phase == 'compile-start':
            diagnostic_require(not running and not ended and pending is None and arm in TRACE_ARMS and arm not in compiled)
            pending = arm
        elif phase == 'compile-end':
            diagnostic_require(not running and not ended and arm == pending)
            compiled.add(arm); pending = None
        elif phase == 'run-start':
            diagnostic_require(arm == RESTORE_ARM and pending is None and compiled == set(TRACE_ARMS)
                and not running and not ended)
            running = True
        elif phase == 'run-end':
            # mule may return CRASHED after any body prefix; return is not pass.
            diagnostic_require(arm == RESTORE_ARM and running and not ended)
            running, ended = False, True
        else:
            diagnostic_require(arm == RESTORE_ARM and running and not ended and body < len(TRACE_BODY)
                and phase == TRACE_BODY[body])
            body += 1
    diagnostic_require(value['status'] != 'malformed' or value['markers'] == [])
    return value


def trace_progress(raw):
    diagnostic_require(type(raw) is bytes and len(raw) <= 262144)
    value = {'protocol': 'stead.restore-checkpoint-stages/1', 'sources': dict(TRACE_SOURCES),
             'status': 'observed', 'markers': []}
    try:
        for encoded in raw.splitlines(keepends=True):
            line = encoded.decode('utf-8', errors='strict')
            if not line.endswith(('\n', '\r')):
                continue
            text = line.strip(' \t\r\n')
            if TRACE_PREFIX not in text:
                continue
            diagnostic_require(text.isascii() and text.startswith(TRACE_PREFIX + ' '))
            suffix = text[len(TRACE_PREFIX) + 1:]
            parts = suffix.split(' ')
            if len(parts) == 2 and parts[0] in ('compile-start', 'compile-end'):
                phase, arm = parts
            else:
                diagnostic_require(len(parts) == 1 and parts[0] in (*TRACE_BODY, 'run-start', 'run-end'))
                phase, arm = parts[0], RESTORE_ARM
            value['markers'].append({'phase': phase, 'arm': arm})
            diagnostic_require(len(value['markers']) <= 23)
        validate_trace_progress(value)
    except (UnicodeError, ValueError):
        value.update(status='malformed', markers=[])
    return value


def trace_completed_output(completed):
    """Remove only validated exact diagnostic hints before existing verdict parsing."""
    diagnostic_require(type(completed) is str and len(completed.encode()) <= 262144 + 32768)
    # The unit log limit remains 262144; appended terminal has no trace marker.
    lines = completed.splitlines(keepends=True)
    diagnostic_require(all(line.endswith(('\n', '\r')) for line in lines if TRACE_PREFIX in line))
    hints = ''.join(line for line in lines if TRACE_PREFIX in line).encode()
    observed = trace_progress(hints)
    diagnostic_require(observed['status'] == 'observed')
    cleaned = ''.join(line for line in lines if TRACE_PREFIX not in line)
    successful = re.search(r'(?m)^\s*OK\s+' + re.escape(TRACE_PATH + '/' + RESTORE_ARM) + r'\s*$', cleaned)
    if successful:
        rows = observed['markers']
        diagnostic_require(len(rows) == 23 and rows[-1] == {'phase': 'run-end', 'arm': RESTORE_ARM}
            and [row['phase'] for row in rows if row['phase'] in TRACE_BODY] == list(TRACE_BODY))
    return cleaned


def interruption_transport(stage, elapsed_ms, received, timeout):
    """Structural progress only. Even a complete frame is no terminal verdict."""
    import hashlib
    diagnostic_require(type(stage) is str and stage in INTERRUPTION_STAGES
        and type(elapsed_ms) is int and 0 <= elapsed_ms <= 180000
        and type(received) is bytes and len(received) <= 1000005
        and type(timeout) is int and timeout == 60)
    count, declared = len(received), None
    if count == 0:
        state = 'empty'
    elif count < 5:
        state = 'partial-header'
    elif received[0] != 0 or not 1 <= int.from_bytes(received[1:5], 'little') <= 1000000:
        state = 'invalid-header'
    else:
        declared = int.from_bytes(received[1:5], 'little')
        state = 'partial-body' if count < declared + 5 else 'complete' if count == declared + 5 else 'overlong'
    return {'protocol': 'stead.native-unit-interruption/1', 'stage': stage,
            'timeout_seconds': timeout, 'elapsed_ms': elapsed_ms, 'received_bytes': count,
            'received_sha256': hashlib.sha256(received).hexdigest(), 'frame_state': state,
            'declared_body_bytes': declared, 'terminal_accepted': False}


def partial_log(entry, raw):
    """Only source-registered complete log lines, never a suite verdict."""
    import hashlib
    diagnostic_require(type(raw) is bytes and len(raw) <= 262144
        and entry['path'] in (TRACE_PATH, NEGATIVE_PATH))
    result = {'log_bytes': len(raw), 'log_sha256': hashlib.sha256(raw).hexdigest(),
              'build_observed': False, 'registered_arm_observations': [],
              'projection_status': 'observed'}
    try:
        # Ignore a trailing incomplete line: it is not a completed observation.
        lines = raw.decode('utf-8', errors='strict').splitlines(keepends=True)
        seen, builds = set(), 0
        for line in lines:
            if not line.endswith(('\n', '\r')):
                continue
            line = line.strip()
            if line == 'built   ' + entry['path'] + '/hoon':
                builds += 1
            match = re.fullmatch(r'(OK|FAILED|CRASHED)\s+(/[^\s]+)', line)
            if match:
                prefix = entry['path'] + '/'
                diagnostic_require(match[2].startswith(prefix))
                name = match[2][len(prefix):]
                diagnostic_require(name in entry['arms'] and name not in seen)
                seen.add(name)
                result['registered_arm_observations'].append({'arm': name, 'outcome': match[1]})
        diagnostic_require(builds <= 1)
        result['build_observed'] = builds == 1
    except (UnicodeDecodeError, ValueError):
        result.update(build_observed=False, registered_arm_observations=[], projection_status='malformed')
    if entry['path'] == TRACE_PATH:
        result['stages'] = trace_progress(raw)
    return result


def validate_interrupted_unit(value, inventory):
    """Validate the closed public projection without upgrading partial evidence."""
    import json
    entries = {row['path']: row for row in restore_entries(inventory)}
    diagnostic_require(type(value) is dict and set(value) == {'path', 'transport', 'log'}
        and type(value['path']) is str and value['path'] in entries)
    transport = value['transport']
    if transport is not None:
        diagnostic_require(type(transport) is dict and set(transport) == {
            'protocol', 'stage', 'timeout_seconds', 'elapsed_ms', 'received_bytes',
            'received_sha256', 'frame_state', 'declared_body_bytes', 'terminal_accepted'})
        diagnostic_require(transport['protocol'] == 'stead.native-unit-interruption/1'
            and type(transport['stage']) is str and transport['stage'] in INTERRUPTION_STAGES
            and type(transport['timeout_seconds']) is int and transport['timeout_seconds'] == 60
            and type(transport['elapsed_ms']) is int and 0 <= transport['elapsed_ms'] <= 180000
            and type(transport['received_bytes']) is int and 0 <= transport['received_bytes'] <= 1000005
            and type(transport['received_sha256']) is str and re.fullmatch('[a-f0-9]{64}', transport['received_sha256'])
            and transport['terminal_accepted'] is False)
        size, declared, state = transport['received_bytes'], transport['declared_body_bytes'], transport['frame_state']
        diagnostic_require(type(state) is str)
        if state in ('empty', 'partial-header', 'invalid-header'):
            diagnostic_require(declared is None and
                (size == 0 if state == 'empty' else 1 <= size < 5 if state == 'partial-header' else size >= 5))
        else:
            diagnostic_require(type(declared) is int and 1 <= declared <= 1000000
                and state in ('partial-body', 'complete', 'overlong')
                and (5 <= size < declared + 5 if state == 'partial-body' else
                     size == declared + 5 if state == 'complete' else size > declared + 5))
    log = value['log']
    extra = {'stages'} if value['path'] == TRACE_PATH else set()
    diagnostic_require(type(log) is dict and set(log) == {'log_bytes', 'log_sha256',
        'build_observed', 'registered_arm_observations', 'projection_status'} | extra
        and type(log['log_bytes']) is int and 0 <= log['log_bytes'] <= 262144
        and type(log['log_sha256']) is str and re.fullmatch('[a-f0-9]{64}', log['log_sha256'])
        and type(log['build_observed']) is bool
        and type(log['projection_status']) is str and log['projection_status'] in ('observed', 'malformed')
        and type(log['registered_arm_observations']) is list)
    if extra:
        validate_trace_progress(log['stages'])
    rows = log['registered_arm_observations']
    diagnostic_require(len(rows) <= len(entries[value['path']]['arms']))
    names = set()
    for row in rows:
        diagnostic_require(type(row) is dict and set(row) == {'arm', 'outcome'}
            and type(row['arm']) is str and row['arm'] in entries[value['path']]['arms']
            and row['arm'] not in names and type(row['outcome']) is str
            and row['outcome'] in ('OK', 'FAILED', 'CRASHED'))
        names.add(row['arm'])
    diagnostic_require(log['projection_status'] != 'malformed' or (not rows and log['build_observed'] is False))
    diagnostic_require(len(json.dumps(value, sort_keys=True).encode()) <= 8192)
    return value


def run(binary, socket_path, resolved_path: str, timeout: float = 60) -> dict:
    """Invoke the pinned runner or its sole fixed diagnostic copy via Khan.

    Dojo resolves the beam separately. The unit runner itself does not pass
    through Dojo/Lens: that path raises a Dojo %kick error after completion on
    this pin. This control socket is confined to disposable test ships.
    """
    import hashlib
    import socket
    import time
    import core_conn
    from conn import framed_length, read_exact

    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 180:
        raise ValueError('Bounded native unit deadline required')
    started = time.monotonic()
    ordinary = re.fullmatch(r'/~zod/base/~[0-9a-zA-Z.:-]+/(tests|controls)/stead-[a-z0-9-]+', resolved_path)
    incremental = re.fullmatch(r'/~zod/base/~[0-9a-zA-Z.:-]+' + re.escape(RESTORE_PATH + '/' + RESTORE_ARM), resolved_path)
    traced = re.fullmatch(r'/~zod/base/~[0-9a-zA-Z.:-]+' + re.escape(TRACE_PATH + '/' + RESTORE_ARM), resolved_path)
    if TRACE_PATH in resolved_path and not traced:
        raise ValueError('Fixed trace arm required')
    if traced and (type(timeout) is not int or timeout != 60):
        raise ValueError('Fixed trace deadline differs')
    if not (ordinary or incremental or traced):
        raise ValueError('Resolved native unit beam required')
    atoms = ' '.join(core_conn.atom(part.encode()) for part in resolved_path.split('/')[1:])
    # Arvo's %path mark preserves the vase type required by /ted/test's !<.
    # A %noun input has the right value but an intentionally erased type and
    # is rejected by the official runner before executing any tests.
    thread = TRACE_THREAD if traced else 'test'
    request = f'[32 %fyrd [%base %{thread} %noun [%path [{atoms} ~]]]]'
    def evaluator_stderr(raw: bytes, mode: str) -> bool:
        # Ordinary startup is exact for the pinned binary/pill.
        return raw.replace(b'\r\n', b'\n') == (
            b'loom: mapped 512MB\nlite: arvo formula 4ce68411\n'
            b'lite: core 641296f\nlite: final state 641296f\n'
            + f'eval ({mode}, newt):\n'.encode())
    trace = {'request': request, 'resolved_path': resolved_path, 'timeout_seconds': timeout, 'stage': 'encode'}
    received = bytearray()
    try:
        frame, encode_stderr = core_conn.evaluate(binary, '-jn', request.encode())
        trace.update(encoded_frame_hex=frame.hex(), encode_stderr_hex=encode_stderr.hex())
        if not evaluator_stderr(encode_stderr, 'jam') or len(frame) != 5 + framed_length(frame[:5]):
            raise ValueError('Native unit request encoding failed')
        with socket.socket(socket.AF_UNIX) as channel:
            class ObservedSocket:
                def settimeout(self, value):
                    channel.settimeout(value)

                def recv(self, size):
                    chunk = channel.recv(size)
                    received.extend(chunk)
                    if len(received) > 1_000_005:
                        raise ValueError('Native unit frame byte bound')
                    return chunk

            deadline = time.monotonic() + timeout
            channel.settimeout(timeout)
            trace['stage'] = 'connect'
            channel.connect(str(socket_path))
            trace['stage'] = 'send'
            channel.sendall(frame)
            trace['stage'] = 'response-header'
            observed = ObservedSocket()
            header = read_exact(observed, 5, deadline)
            trace['stage'] = 'response-body'
            response = header + read_exact(observed, framed_length(header), deadline)
        trace['stage'] = 'decode'
        decoded, decode_stderr = core_conn.evaluate(binary, '-ckn', response)
        trace.update(decoded_hex=decoded.hex(), decode_stderr_hex=decode_stderr.hex())
        stdout = decoded.decode('utf-8', errors='strict').strip()
        observation = {'request': request, 'resolved_path': resolved_path, 'stdout': stdout,
                       'timeout_seconds': timeout, 'elapsed_seconds': round(time.monotonic() - started, 3),
                       'encode_stderr': encode_stderr.decode('utf-8', errors='strict'),
                       'decode_stderr': decode_stderr.decode('utf-8', errors='strict'),
                       'response_frame_sha256': hashlib.sha256(response).hexdigest(),
                       'response_frame_hex': response.hex()}
        trace['stage'] = 'parse-terminal'
        if not evaluator_stderr(decode_stderr, 'cue') or stdout not in ('[32 %avow 0 %noun 0]', '[32 %avow 0 %noun 1]'):
            raise ValueError('Unexpected native unit terminal result')
        return observation
    except Exception as error:
        import subprocess
        # Diagnostic-only attachment cannot replace the initiating exception.
        try:
            error.native_interruption = interruption_transport(trace['stage'],
                round((time.monotonic() - started) * 1000), bytes(received), timeout)
        except Exception:
            error.native_interruption = None
        trace.update(error=type(error).__name__ + ': ' + str(error), received_frame_hex=received.hex(), elapsed_seconds=round(time.monotonic() - started, 3))
        if isinstance(error, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            trace.update(evaluator_output_hex=(error.output or b'').hex(),
                         evaluator_stderr_hex=(error.stderr or b'').hex())
            if isinstance(error, subprocess.CalledProcessError):
                trace['evaluator_exit'] = error.returncode
            else:
                trace['evaluator_timeout'] = True
        if hasattr(error, 'eval_failure'):
            trace['evaluator_limit'] = error.eval_failure
        error.native_failure = trace
        raise


def validate_inventory(value: dict) -> dict:
    if not isinstance(value, dict) or type(value.get('format')) is not int or value.get('format') != 1 or value.get('classification') != 'pure-native-only':
        raise ValueError('Native inventory schema')
    suites = value.get('suites')
    definitions = {'/tests/stead-session': ('test-session-', 19, 60),
                   '/tests/stead-http': ('test-http-', 14, 60),
                   '/tests/stead-identity': ('test-identity-', 11, 60),
                   '/tests/stead-updates': ('test-updates-', 25, 60),
                   '/tests/stead-work-assignment': ('test-work-assignment-', 7, 60),
                   '/tests/stead-work-comments': ('test-work-comments-', 4, 60),
                   '/tests/stead-work-contract': ('test-work-contract-', 6, 60),
                   '/tests/stead-workspace-views': ('test-workspace-', 6, 60),
                   '/tests/stead-product-codec': ('test-product-codec-', 9, 60),
                   '/tests/stead-product-migrate': ('test-product-migrate-', 6, 60),
                   '/tests/stead-product-work': ('test-product-work-', 10, 60),
                   '/tests/stead-principals': ('test-principals-', 6, 60),
                   '/tests/stead-product-views': ('test-product-views-', 8, 60),
                   '/tests/stead-product-restore': ('test-product-restore-', 8, 60),
                   '/tests/stead-product-adapters': ('test-product-adapters-', 4, 60),
                   '/tests/stead-doc-change-codec': ('test-doc-change-codec-', 6, 60),
                   '/tests/stead-product-owner': ('test-product-owner-', 6, 60),
                   '/tests/stead-product-history': ('test-product-history-', 8, 60),
                   '/tests/stead-doc-change': ('test-doc-change-', 14, 60),
                   '/tests/stead-product-doc-history': ('test-product-doc-history-', 6, 60),
                   '/tests/stead-actor': ('test-actor-', 4, 60),
                   '/tests/stead-service-bindings': ('test-service-bindings-', 8, 60),
                   '/tests/stead-doc-change-views': ('test-doc-change-', 7, 60),
                   '/tests/stead-run': ('test-run-', 10, 60),
                   '/tests/stead-run-codec': ('test-run-codec-', 6, 60),
                   '/tests/stead-run-adapters': ('test-run-adapters-', 8, 60),
                   '/tests/stead-run-views': ('test-run-views-', 8, 60),
                   '/tests/stead-product-home': ('test-product-home-', 8, 60),
                   '/tests/stead-home-v10-rehearsal': ('test-home-v10-', 6, 60),
                   '/tests/stead-work-delegations': ('test-work-delegations-', 3, 60),
                   '/tests/stead-creator-renewal': ('test-creator-renewal-', 4, 60),
                   '/tests/stead-project-retirement': ('test-project-retire-', 6, 60),
                   '/tests/stead-code-pack-anchor': ('test-pack-anchor-', 5, 60),
                   '/tests/stead-code-pack-read': ('test-pack-read-', 5, 60),
                   '/tests/stead-code-pack-push': ('test-pack-push-', 5, 60),
                   '/tests/stead-code-pack-review': ('test-pack-review-', 7, 60),
                   '/tests/stead-code-pack-ledger': ('test-pack-ledger-', 5, 60),
                   '/tests/stead-code-pack-proof': ('test-pack-proof-', 4, 60),
                   '/tests/stead-code-pack-carrier': ('test-pack-carrier-', 3, 60),
                   '/tests/stead-code-pack-admit': ('test-pack-admit-', 3, 60),
                   '/tests/stead-code-pack-worker-signature': ('test-pack-worker-signature-', 2, 60),
                   '/tests/stead-code-pack-relay-wire': ('test-pack-relay-wire-', 2, 60),
                   '/tests/stead-code-pack-control': ('test-pack-control-', 3, 60),
                   '/tests/stead-home-v8-rehearsal': ('test-home-v8-', 5, 60),
                   '/tests/stead-code-pack-review-board': ('test-pack-board-', 8, 60),
                   '/tests/stead-home-v9-rehearsal': ('test-home-v9-', 4, 60),
                   '/tests/stead-browser-oidc-proof': ('test-oidc-proof-', 5, 60),
                   '/tests/stead-update-capacity': ('test-updates-', 2, 180)}
    if not isinstance(suites, list) or len(suites) != len(definitions):
        raise ValueError('Native suite count')
    paths = [entry.get('path') for entry in suites if isinstance(entry, dict)]
    if set(paths) != set(definitions) or len(paths) != len(definitions):
        raise ValueError('Native suite paths')
    all_arms = []
    for entry in suites:
        names = entry.get('arms')
        prefix, count, timeout = definitions[entry['path']]
        if set(entry) != {'path', 'arms', 'timeout_seconds'} or type(entry.get('timeout_seconds')) is not int or entry['timeout_seconds'] != timeout:
            raise ValueError('Native suite schema and fixed deadline')
        if not isinstance(names, list) or len(names) != count or any(
                not isinstance(name, str) or not re.fullmatch(prefix + r'[a-z0-9-]{1,64}', name) for name in names):
            raise ValueError('Native suite arms')
        all_arms.extend(names)
    capacity = next(suite for suite in suites if suite['path'] == '/tests/stead-update-capacity')
    if set(capacity['arms']) != {'test-updates-global-watch-cursor-stream-caps', 'test-updates-retained-history-sixty-four-then-trim'}:
        raise ValueError('Capacity inventory must retain both native boundary cases')
    count = sum(definition[1] for definition in definitions.values())
    if len(all_arms) != count or len(set(all_arms)) != count or type(value.get('expected_arm_count')) is not int or value.get('expected_arm_count') != count:
        raise ValueError('Native arm count and uniqueness')
    if value.get('negative_control') != {
            'path': '/controls/stead-unit-failure', 'arms': ['test-deliberate-failure'],
            'marker': 'stead-intentional-native-unit-failure'}:
        raise ValueError('Native negative control schema')
    return value


def verify_output(raw: str, *, path: str, expected: list[str], succeeds: bool,
                  failure_marker: str | None = None) -> dict:
    if not isinstance(raw, str) or not 0 < len(raw.encode()) <= 262144:
        raise ValueError('Native unit output bound')
    if not expected or len(expected) != len(set(expected)):
        raise ValueError('Nonempty unique expected native arms required')
    if any(not re.fullmatch(r'test-[a-z0-9-]{1,80}', arm) for arm in expected):
        raise ValueError('Invalid expected arm name')
    if not re.fullmatch(r'/(tests|controls)/stead-[a-z0-9-]+', path):
        raise ValueError('Invalid native test file')
    lines = raw.replace('\r\n', '\n').splitlines()
    outcomes = []
    timing_arms = []
    wrapped_timing = None
    driver_diagnostics = []
    for index, line in enumerate(lines):
        # Observed pinned Vere UDP callback output can interleave with -test
        # while the fresh CI peer fence is closed. Retain it separately; it
        # establishes no test outcome and cannot satisfy any required record.
        if line == 'ames: send fail: operation not permitted':
            driver_diagnostics.append({'line': index + 1, 'message': line})
            continue
        if wrapped_timing is not None:
            if not re.fullmatch(r'  took (?:µs|ms|s)/[0-9]+(?:\.[0-9]+)*', line):
                raise ValueError('Incomplete wrapped native timing record')
            timing_arms.append(wrapped_timing)
            wrapped_timing = None
            continue
        if re.search(r'\b(?:CRASHED|build-fail|syntax error|nest-fail|mint-vain|find-fork|dojo-lame)\b', line) or line.lstrip().startswith('! '):
            raise ValueError('Unexpected native diagnostic')
        match = re.fullmatch(r'(OK|FAILED|CRASHED)\s+(/[^\s]+)', line.strip())
        if match:
            status, identifier = match.groups()
            prefix = path + '/'
            if not identifier.startswith(prefix):
                raise ValueError('Unexpected native arm path')
            outcomes.append((identifier[len(prefix):], status))
            continue
        timing = re.fullmatch(r'>\s+(test-[a-z0-9-]+): took (?:µs|ms|s)/[0-9]+(?:\.[0-9]+)*', line.strip())
        if timing:
            timing_arms.append(timing[1])
            continue
        # Pinned Arvo's pretty printer wraps a long timing label at its margin.
        # Accept only the observed two-line form, never a loose continuation.
        wrapped = re.fullmatch(r'>     (test-[a-z0-9-]+)', line)
        if wrapped:
            wrapped_timing = wrapped[1]
            continue
        if line.strip() in ('', 'built   ' + path + '/hoon', '[32 %avow 0 %noun 0]', '[32 %avow 0 %noun 1]'):
            continue
        if not succeeds and failure_marker is not None and line.strip() == failure_marker:
            continue
        raise ValueError('Unexpected native output record: ' + line[:200])
    if wrapped_timing is not None:
        raise ValueError('Truncated wrapped native timing record')
    observed = [name for name, _ in outcomes]
    if len(observed) != len(set(observed)) or set(observed) != set(expected):
        raise ValueError('Native discovered/executed arm mismatch')
    expected_status = 'OK' if succeeds else 'FAILED'
    if any(status != expected_status for _, status in outcomes):
        raise ValueError('Unexpected native test outcome')
    if len(timing_arms) != len(set(timing_arms)) or any(arm not in expected for arm in timing_arms):
        raise ValueError('Unexpected native timing record')
    if sum(line.strip() == 'built   ' + path + '/hoon' for line in lines) != 1:
        raise ValueError('Missing or duplicate native build observation')
    verdicts = [line.strip() for line in lines if re.fullmatch(r'\[32 %avow 0 %noun [01]\]', line.strip())]
    if verdicts != ['[32 %avow 0 %noun ' + ('0' if succeeds else '1') + ']']:
        raise ValueError('Native test verdict mismatch')
    if succeeds and any(re.search(r'\bFAILED\b', line) for line in lines):
        raise ValueError('Failure text in successful native output')
    if not succeeds and (failure_marker != 'stead-intentional-native-unit-failure' or
                         sum(line.strip() == failure_marker for line in lines) != 1):
        raise ValueError('Missing deliberate native failure message')
    return {'path': path, 'expected': expected, 'observed': observed,
            'outcome': 'passed' if succeeds else 'expected-failure', 'raw_output': raw,
            'driver_diagnostics': driver_diagnostics}


def collect_pure_diagnostics(entries, execute, verify, passed, failed):
    """Trusted diagnostic controller only. Completion never qualifies a run.

    Only verifier rejection after a completed bounded execution is collected.
    Transport, decoding, timeouts, callbacks and resource guards propagate.
    """
    if not isinstance(entries, list) or not 1 <= len(entries) <= 64:
        raise ValueError('Diagnostic suite count')
    for entry in entries:
        completed = execute(entry)
        try:
            verified = verify(entry, completed)
        except ValueError:
            failed(entry)
        else:
            passed(entry, verified)
    raise ValueError('Pure-unit diagnostic complete; qualification disabled')

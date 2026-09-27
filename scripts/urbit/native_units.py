"""Closed output verification for pinned Arvo's real -test thread.

This parses observations; it cannot execute a Hoon arm or qualify an endpoint.
Missing/duplicate arms and an empty nominally green result are failures.
"""
from __future__ import annotations

import re


def run(binary, socket_path, resolved_path: str, timeout: float = 60) -> dict:
    """Invoke pinned Arvo's unchanged /ted/test through its private Khan API.

    Dojo resolves the beam separately. The unit runner itself does not pass
    through Dojo/Lens: that path raises a Dojo %kick error after completion on
    this pin. This control socket is confined to disposable test ships.
    """
    import hashlib
    import socket
    import time
    import core_conn
    from conn import framed_length, read_exact

    if not re.fullmatch(r'/~zod/base/~[0-9a-zA-Z.:-]+/(tests|controls)/stead-[a-z0-9-]+', resolved_path):
        raise ValueError('Resolved native unit beam required')
    atoms = ' '.join(core_conn.atom(part.encode()) for part in resolved_path.split('/')[1:])
    # Arvo's %path mark preserves the vase type required by /ted/test's !<.
    # A %noun input has the right value but an intentionally erased type and
    # is rejected by the official runner before executing any tests.
    request = f'[32 %fyrd [%base %test %noun [%path [{atoms} ~]]]]'
    def evaluator_stderr(raw: bytes, mode: str) -> bool:
        # Ordinary startup is exact for the pinned binary/pill.
        return raw.replace(b'\r\n', b'\n') == (
            b'loom: mapped 512MB\nlite: arvo formula 4ce68411\n'
            b'lite: core 641296f\nlite: final state 641296f\n'
            + f'eval ({mode}, newt):\n'.encode())
    trace = {'request': request, 'resolved_path': resolved_path, 'stage': 'encode'}
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
        trace.update(error=type(error).__name__ + ': ' + str(error), received_frame_hex=received.hex())
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
    if not isinstance(suites, list) or len(suites) != 2:
        raise ValueError('Exactly two native suites required')
    paths = [entry.get('path') for entry in suites if isinstance(entry, dict)]
    if set(paths) != {'/tests/stead-session', '/tests/stead-http'} or len(paths) != 2:
        raise ValueError('Native suite paths')
    all_arms = []
    for entry in suites:
        names = entry.get('arms')
        prefix = 'test-session-' if entry['path'].endswith('stead-session') else 'test-http-'
        count = 19 if prefix == 'test-session-' else 12
        if not isinstance(names, list) or len(names) != count or any(
                not isinstance(name, str) or not re.fullmatch(prefix + r'[a-z0-9-]{1,64}', name) for name in names):
            raise ValueError('Native suite arms')
        all_arms.extend(names)
    if len(all_arms) != 31 or len(set(all_arms)) != 31 or type(value.get('expected_arm_count')) is not int or value.get('expected_arm_count') != 31:
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
    for line in lines:
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
        if line.strip() in ('', 'built   ' + path + '/hoon', '[32 %avow 0 %noun 0]', '[32 %avow 0 %noun 1]'):
            continue
        if not succeeds and failure_marker is not None and line.strip() == failure_marker:
            continue
        raise ValueError('Unexpected native output record: ' + line[:200])
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
            'outcome': 'passed' if succeeds else 'expected-failure', 'raw_output': raw}

"""Synthetic core client via pinned Vere Khan; no live/browser authentication."""
from __future__ import annotations
import hashlib
import json
import re
import socket
import subprocess
import tempfile
import time
import owned_child
from conn import framed_length, read_exact


def evaluate(binary, flags, data):
    # Pinned Vere 4.6 eval can exit before draining >64 KiB to a pipe. A regular
    # anonymous file preserves the complete native frame/text; size stays bounded.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostics:
        try:
            result = subprocess.run(owned_child.fixture_command([str(binary), 'eval', '--loom', '29', flags]), input=data,
                                    stdout=output, stderr=diagnostics, timeout=30, check=False)
        except subprocess.TimeoutExpired as error:
            output.seek(0)
            diagnostics.seek(0)
            error.output, error.stderr = output.read(1_000_001), diagnostics.read(1_000_001)
            raise
        output.seek(0)
        diagnostics.seek(0)
        raw = output.read(1_000_001)
        stderr = diagnostics.read(1_000_001)
    if len(raw) > 1_000_000 or len(stderr) > 1_000_000:
        error = ValueError('Runtime eval output/diagnostic limit')
        error.eval_failure = {'stdout_prefix_hex': raw.hex(), 'stderr_prefix_hex': stderr.hex(),
                              'complete': False, 'reason': 'Bounded prefixes retained; oversized output cannot pass'}
        raise error
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, result.args, output=raw, stderr=stderr)
    return raw, stderr


def atom(raw):
    digits = format(int.from_bytes(raw, 'little'), 'x')
    first = len(digits) % 4 or 4
    return '0x' + '.'.join([digits[:first]] + [digits[i:i+4] for i in range(first, len(digits), 4)])


def parse_response(output):
    if output.strip() == '[32 %avow 1]':
        return None
    match = re.fullmatch(r"\s*\[32\s+%avow\s+0\s+%noun\s+%stead-core-result\s+'([0-9a-f]+)'\]\s*", output)
    if not match:
        raise ValueError('Unexpected terminal core response shape: ' + output[:300])
    raw = bytes.fromhex(match[1])
    if not 0 < len(raw) <= 262144:
        raise ValueError('Core result byte bound')
    text = raw.decode('utf-8', errors='strict')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate result key')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Non-JSON numeric constant: ' + value)
    result = json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)
    if not isinstance(result, dict):
        raise ValueError('Core result is not an object')
    return {'raw': text, 'json': result}


def evaluator_controls(binary):
    """Actual pinned evaluator controls; caller must already own guarded execution.

    This is framing/evaluator evidence, not a home acceptance or model fixture.
    """
    # This control targets the observed pinned zero-exit parser failure. A
    # crash/signal/nonzero exit is a failed control, never an expected rejection.
    commands = []

    def observed(flags, data):
        output, diagnostics = evaluate(binary, flags, data)
        commands.append({'mode': 'evaluator', 'argv': [str(binary), 'eval', '--loom', '29', flags],
                         'input_hex': data.hex(), 'stdout_hex': output.hex(),
                         'stderr_hex': diagnostics.hex(), 'exit_code': 0})
        return output, diagnostics

    bad, stderr = observed('-jn', b'[')
    try:
        complete = len(bad) == 5 + framed_length(bad[:5])
    except ValueError:
        complete = False
    if complete or not stderr.strip():
        raise AssertionError('Invalid evaluator input lacks its parse failure evidence')
    errors = {'exit': 0, 'encoder_rejected': True, 'stdout_hex': bad.hex(),
              'stderr': stderr.decode(errors='replace')}
    # The JSON travels as hex text inside the noun: 34k source bytes already
    # exceed the 64KiB pipe boundary after encoding. This control establishes
    # framing, not application capacity. Keep the actual frame-size check below.
    expected = {'protocol': 'stead.framing-control/1', 'synthetic_text': 'x' * 34000}
    raw = json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()
    noun = b"[32 %avow 0 %noun %stead-core-result '" + raw.hex().encode() + b"']"
    frame, encode_stderr = observed('-jn', noun)
    if len(frame) <= 65536 or len(frame) != 5 + framed_length(frame[:5]):
        raise AssertionError('Large evaluator control was truncated or not above64KiB')
    text, decode_stderr = observed('-ckn', frame)
    actual = parse_response(text.decode('utf-8'))
    if actual != {'raw': raw.decode(), 'json': expected}:
        raise AssertionError('Large evaluator control did not recover exact bytes')
    return {'status': 'passed', 'classification': 'real-native-evaluator',
            'invalid_input': errors, 'large_frame_bytes': len(frame),
            'large_frame_sha256': hashlib.sha256(frame).hexdigest(),
            'large_frame_hex': frame.hex(), 'decoded_stdout': text.decode('utf-8'),
            'commands': commands,
            'result_sha256': hashlib.sha256(raw).hexdigest(),
            'encode_stderr': encode_stderr.decode(errors='replace'),
            'decode_stderr': decode_stderr.decode(errors='replace')}


def run(binary, socket_path, mode, route='/', raw=b'', *, control=None, timeout=75):
    if mode not in ('command', 'read', 'poke', 'fixture', 'control', 'codec', 'observe', 'observer-read'):
        raise ValueError('Unsupported fixture operation')
    if not re.fullmatch(r'/[a-zA-Z0-9~/._-]*', route) or len(route) > 1024:
        raise ValueError('Invalid literal native fixture path')
    if len(raw) > 70000:
        raise ValueError('Fixture input limit')
    if raw.endswith(b'\0'):
        raise ValueError('NUL-terminated bytes cannot be represented by the frozen cord carrier')
    payload = atom(raw)
    if mode == 'control':
        op, ship, key, value = control
        if op not in ('profile', 'missing', 'active', 'expiry', 'kind', 'binding-drop', 'binding-restore', 'roundtrip', 'load-future', 'load-counter', 'legacy-init', 'legacy-read', 'legacy-batch', 'migrate-legacy', 'load-bad-legacy', 'native-batch', 'hold-outsider-read') or ship not in ('zod', 'bus', 'nec', 'bud'):
            raise ValueError('Unsupported owner fixture control')
        if len(key.encode()) > 1024 or len(value.encode()) > 65536 or '\0' in key or '\0' in value:
            raise ValueError('Owner fixture control byte bound')
        payload = f'(jam [%{op} ~{ship} {atom(key.encode())} {atom(value.encode())}])'
    parts = [atom(part.encode()) for part in route.split('/') if part]
    path_noun = '[' + ' '.join(parts) + ' ~]' if parts else '~'
    noun = f'[32 %fyrd [%base %stead-client %noun [%noun [~zod %{mode} {path_noun} {payload}]]]]'
    return exchange(binary, socket_path, noun, timeout=timeout)


def exchange(binary, socket_path, noun, *, timeout=75):
    """Internal framed Khan exchange; callers own their finite input grammar."""
    trace = {'stage': 'encode', 'request': noun}
    received = bytearray()
    try:
        frame, encode_stderr = evaluate(binary, '-jn', noun.encode())
        trace.update(encode_stderr=encode_stderr.decode(errors='replace'), encoded_frame_hex=frame.hex())
        if len(frame) != 5 + framed_length(frame[:5]):
            raise ValueError('Invalid runtime-encoded core request: ' + str(len(frame)) + ' bytes; ' + encode_stderr.decode(errors='replace')[-1000:])
        with socket.socket(socket.AF_UNIX) as channel:
            class ObservedSocket:
                def settimeout(self, value):
                    channel.settimeout(value)

                def recv(self, size):
                    chunk = channel.recv(size)
                    received.extend(chunk)
                    if len(received) > 1_000_005:
                        raise ValueError('Observed terminal frame bound exceeded')
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
        decoded, decode_stderr = evaluate(binary, '-ckn', response)
        trace.update(decoded_hex=decoded.hex(), decode_stderr=decode_stderr.decode(errors='replace'))
        output = decoded.decode('utf-8', errors='strict')
        details = re.sub(r'\x1b\[[0-9;]*m', '', decode_stderr.decode('utf-8', errors='strict')).strip()
        trace['stage'] = 'parse-terminal'
        return {'outcome': parse_response(output), 'stdout': output.strip(), 'stderr': details,
                'request': noun, 'request_frame_hex': frame.hex(), 'response_frame_hex': response.hex(),
                'response_frame_sha256': hashlib.sha256(response).hexdigest()}
    except Exception as error:
        trace.update(error=type(error).__name__ + ': ' + str(error), received_frame_hex=received.hex())
        if isinstance(error, subprocess.CalledProcessError):
            trace.update(evaluator_exit=error.returncode,
                         evaluator_output_hex=(error.output or b'').hex(),
                         evaluator_stderr=(error.stderr or b'').decode(errors='replace'))
        if isinstance(error, subprocess.TimeoutExpired):
            trace.update(evaluator_timeout=True, evaluator_output_hex=(error.output or b'').hex(),
                         evaluator_stderr=(error.stderr or b'').decode(errors='replace'))
        if hasattr(error, 'eval_failure'):
            trace['evaluator_limit'] = error.eval_failure
        error.native_failure = trace
        raise

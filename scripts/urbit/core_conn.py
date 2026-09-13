"""Synthetic core client via pinned Vere Khan; no live/browser authentication."""
from __future__ import annotations
import hashlib
import json
import re
import socket
import subprocess
import tempfile
import time
from conn import framed_length, read_exact


def evaluate(binary, flags, data):
    # Pinned Vere 4.6 eval can exit before draining >64 KiB to a pipe. A regular
    # anonymous file preserves the complete native frame/text; size stays bounded.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run([str(binary), 'eval', '--loom', '29', flags], input=data,
                                stdout=output, stderr=subprocess.PIPE, timeout=30, check=True)
        output.seek(0)
        raw = output.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError('Runtime eval output limit')
    return raw, result.stderr


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
    result = json.loads(text, object_pairs_hook=unique)
    if not isinstance(result, dict):
        raise ValueError('Core result is not an object')
    return {'raw': text, 'json': result}


def run(binary, socket_path, mode, route='/', raw=b'', *, control=None, timeout=75):
    if mode not in ('command', 'read', 'poke', 'fixture', 'control', 'codec'):
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
        if op not in ('profile', 'missing', 'active', 'expiry', 'kind', 'binding-drop', 'binding-restore', 'roundtrip', 'load-future', 'load-counter') or ship not in ('zod', 'bus', 'nec', 'bud'):
            raise ValueError('Unsupported owner fixture control')
        payload = f'(jam [%{op} ~{ship} {atom(key.encode())} {atom(value.encode())}])'
    parts = [atom(part.encode()) for part in route.split('/') if part]
    path_noun = '[' + ' '.join(parts) + ' ~]' if parts else '~'
    noun = f'[32 %fyrd [%base %stead-client %noun [%noun [~zod %{mode} {path_noun} {payload}]]]]'
    frame, encode_stderr = evaluate(binary, '-jn', noun.encode())
    if len(frame) != 5 + framed_length(frame[:5]):
        raise ValueError('Invalid runtime-encoded core request: ' + str(len(frame)) + ' bytes; ' + encode_stderr.decode(errors='replace')[-1000:])
    with socket.socket(socket.AF_UNIX) as channel:
        deadline = time.monotonic() + timeout
        channel.settimeout(timeout)
        channel.connect(str(socket_path))
        channel.sendall(frame)
        header = read_exact(channel, 5, deadline)
        response = header + read_exact(channel, framed_length(header), deadline)
    decoded, decode_stderr = evaluate(binary, '-ckn', response)
    output = decoded.decode('utf-8', errors='strict')
    details = re.sub(r'\x1b\[[0-9;]*m', '', decode_stderr.decode('utf-8', errors='strict')).strip()
    return {'outcome': parse_response(output), 'stdout': output.strip(), 'stderr': details,
            'request': noun, 'response_frame_sha256': hashlib.sha256(response).hexdigest()}

"""Bounded private Vere conn/Khan fixture control, not a Stead application API.

Uses the pinned runtime's pure jam/cue tools; no independently invented codec.
Framing/request profile comes from Vere 4.6 pkg/vere/io/conn.c.
"""
from __future__ import annotations

import hashlib
import re
import socket
import subprocess

LIMIT = 1_000_000


def framed_length(header):
    if len(header) != 5 or header[0] != 0:
        raise ValueError('Invalid Newt header')
    size = int.from_bytes(header[1:], 'little')
    if not 0 < size <= LIMIT:
        raise ValueError('Newt response length outside fixture bound')
    return size


def read_exact(channel, size):
    data = bytearray()
    while len(data) < size:
        block = channel.recv(size - len(data))
        if not block:
            raise ValueError('EOF before complete terminal conn response')
        data.extend(block)
    return bytes(data)


def run_thread(binary, socket_path, command, timeout=180):
    if not command.startswith('-stead-smoke '):
        raise ValueError('Only the fixed synthetic probe thread is supported')
    arguments = command.removeprefix('-stead-smoke ')
    # Khan prepends the optional thread id (~) to the converted input page.
    noun = f'[32 %fyrd [%base %stead-smoke %noun [%noun [{arguments}]]]]'
    encoded = subprocess.run([str(binary), 'eval', '--loom', '29', '-jn'],
                             input=noun.encode(), capture_output=True, timeout=30, check=True)
    frame = encoded.stdout
    if len(frame) != 5 + framed_length(frame[:5]):
        raise ValueError('Runtime encoder did not return one bounded Newt frame')
    with socket.socket(socket.AF_UNIX) as channel:
        channel.settimeout(timeout)
        channel.connect(str(socket_path))
        channel.sendall(frame)
        header = read_exact(channel, 5)
        response = header + read_exact(channel, framed_length(header))
    # -k renders a terminal Khan goof on stderr; retain it for negative checks.
    decoded = subprocess.run([str(binary), 'eval', '--loom', '29', '-ckn'],
                             input=response, capture_output=True, timeout=30, check=True)
    output = decoded.stdout.decode('utf-8', errors='strict').strip()
    details = re.sub(r'\x1b\[[0-9;]*m', '', decoded.stderr.decode('utf-8', errors='strict')).strip()
    if output not in ('[32 %avow 0 %noun %stead-smoke-ack]', '[32 %avow 1]'):
        raise ValueError('Unexpected terminal conn response: ' + output + '\n' + details)
    return {'stdout': output, 'stderr': details,
            'request': noun, 'response_frame_sha256': hashlib.sha256(response).hexdigest()}

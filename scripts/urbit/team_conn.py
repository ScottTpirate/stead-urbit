"""Finite test adapter for configured native interfaces; no browser identity stub."""
from __future__ import annotations
import re
import core_conn

SHIPS = ('zod', 'bus', 'nec', 'bud')
MODES = ('configure', 'identity-config', 'bootstrap', 'command', 'query', 'approve')


def run(binary, socket_path, mode, route='/', raw=b'', *, target='zod', app='stead-home', timeout=75):
    if mode not in MODES or target not in SHIPS or app not in ('stead-home', 'stead-identity'):
        raise ValueError('Unsupported configured test operation or target')
    if (mode == 'identity-config' and app != 'stead-identity') or (mode not in ('identity-config', 'bootstrap') and app != 'stead-home'):
        raise ValueError('Configured operation/app mismatch')
    if not isinstance(raw, bytes) or len(raw) > 65536 or raw.endswith(b'\0'):
        raise ValueError('Configured input byte bound/carrier')
    if not re.fullmatch(r'/[a-zA-Z0-9~/._-]*', route) or len(route) > 1024:
        raise ValueError('Configured native path bound')
    parts = [core_conn.atom(part.encode()) for part in route.split('/') if part]
    path = '[' + ' '.join(parts) + ' ~]' if parts else '~'
    noun = f'[32 %fyrd [%base %stead-team-client %noun [%noun [~{target} %{app} %{mode} {path} {core_conn.atom(raw)}]]]]'
    return core_conn.exchange(binary, socket_path, noun, timeout=timeout)

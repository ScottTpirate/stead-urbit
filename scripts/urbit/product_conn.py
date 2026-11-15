"""Closed disposable Gall carrier for the reserved native-human-doc/1 rehearsal.

No CLI or authority bootstrap. The supervised runner supplies its admitted fake
ship socket and records the returned actual transport evidence. No result here
is a native qualification verdict by itself.
"""
from __future__ import annotations

import hashlib
import json
import re

import core_conn

SHIPS = ('zod', 'bus', 'nec', 'bud')
PROTOCOLS = {
    'activate': 'stead.product-activate/1',
    'owner-command': 'stead.owner-command/1',
    'command': 'stead.command/4',
    'query': 'stead.query/4',
    'doc-command': 'stead.doc-change/1',
    'doc-query': 'stead.doc-change-query/1',
}
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
TOKEN = re.compile(r'[0-9a-f]{64}')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')


def digest(domain, raw):
    return hashlib.sha256(domain.encode('ascii') + b'\0' + raw).hexdigest()


def result_route(ship, binding, revision, value):
    """The runner supplies known fixture bindings, never a wire actor object."""
    if (ship not in SHIPS or not isinstance(binding, str) or not UUID.fullmatch(binding)
            or type(revision) is not int or not 1 <= revision < 2**64
            or not isinstance(value, dict) or not isinstance(value.get('request_id'), str)
            or not UUID.fullmatch(value['request_id'])
            or value.get('protocol') not in tuple(PROTOCOLS[k] for k in ('command', 'query', 'doc-command', 'doc-query'))):
        raise ValueError('Product result route scope')
    return '/product/result/~' + ship + '/' + binding + '/' + str(revision) + '/' + value['request_id'] + '/' + digest(value['protocol'], canonical(value))


def owner_route(value):
    if (not isinstance(value, dict) or value.get('protocol') != PROTOCOLS['owner-command']
            or not isinstance(value.get('request_id'), str) or not UUID.fullmatch(value['request_id'])):
        raise ValueError('Owner receipt route scope')
    return '/product-owner-receipt/' + value['request_id'] + '/' + digest(PROTOCOLS['owner-command'], canonical(value))


def run(binary, socket_path, mode, route='/', raw=b'', *, target='zod', timeout=75):
    if mode not in (*PROTOCOLS, 'owner-receipt') or target not in SHIPS:
        raise ValueError('Unsupported disposable product operation or target')
    if type(timeout) not in (int, float) or not 0 < timeout <= 75:
        raise ValueError('Product transport deadline bound')
    if not isinstance(raw, bytes) or len(raw) > 65536 or raw.endswith(b'\0'):
        raise ValueError('Product input byte bound/carrier')
    if not isinstance(route, str) or len(route) > 1024 or not re.fullmatch(r'/[a-zA-Z0-9~/._-]*', route):
        raise ValueError('Product native path bound')
    if mode in ('activate', 'owner-command'):
        if route != '/':
            raise ValueError('Product owner poke path')
    elif mode == 'owner-receipt':
        parts = route.split('/')
        if (raw or len(parts) != 4 or parts[1] != 'product-owner-receipt'
                or not UUID.fullmatch(parts[2]) or not TOKEN.fullmatch(parts[3])):
            raise ValueError('Product owner receipt path')
    else:
        parts = route.split('/')
        if (len(parts) != 8 or parts[1:3] != ['product', 'result']
                or parts[3] not in tuple('~' + ship for ship in SHIPS)
                or not UUID.fullmatch(parts[4]) or not re.fullmatch(r'[1-9][0-9]{0,19}', parts[5])
                or int(parts[5]) >= 2**64 or not UUID.fullmatch(parts[6])
                or not TOKEN.fullmatch(parts[7])):
            raise ValueError('Product result path')
    atoms = [core_conn.atom(part.encode('ascii')) for part in route.split('/') if part]
    path = '[' + ' '.join(atoms) + ' ~]' if atoms else '~'
    noun = f'[32 %fyrd [%base %stead-product-check %noun [%noun [~{target} %stead-home %{mode} {path} {core_conn.atom(raw)}]]]]'
    return core_conn.exchange(binary, socket_path, noun, timeout=timeout)

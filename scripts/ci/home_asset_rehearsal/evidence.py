"""Closed saved8 capture/equality checks; supplied data alone proves no runtime.

The exact source-owned generator observes p and q separately. Python verifies
the complete emitted jam bytes and their domain pin without widening the
unrelated 16KiB scheduled-Gall noun decoder. Actual producer, suspension,
current process, source and lease custody remain mandatory runner/guardian
checks. No supplied capture is imported into Gall.
"""
from __future__ import annotations

import hashlib
import json
import re

MAX_CAPTURE = 262144
CHUNK = 16384
STAGES = ('seed8', 'a0-loaded', 'a0-cold', 'assets-loaded', 'rollback-loaded')
TAILS = ('db_pin', 'code_pin', 'handoff_pin', 'retired_pin', 'packs_pin', 'external_pin')
PINS = ('capture_pin', 'vase_fingerprint', 'type_pin', 'payload_pin', 'durable_pin', *TAILS)
FIELDS = frozenset(('protocol', 'offset', 'length', 'total_bytes', 'data_hex', *PINS))
SUSPENDED = '.^(? %gu /=stead-home=/$)'
DESK = '.^(desk %gd /=stead-home=/$)'
FINGERPRINT = ('=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)  '
    '?>  ?=([%20 %live *] egg)  =/  saved=vase  +.old-state.egg  '
    '?>  ?=([%stead-home %8 *] q.saved)  ^-  @ux  (shax (jam saved))')
CAPABILITIES = {
    'protocol': 'stead.capabilities/3', 'profile': 'configured-team',
    'commands': 'stead.command/3', 'queries': 'stead.query/3',
    'updates': 'stead.updates/3', 'authentication': 'native-approved-browser/1',
    'max_request_bytes': '65536', 'max_response_bytes': '262144',
    'page_size': '20', 'runtime': 'isolated-fake',
    'work_contract': 'stead.work-contract/1', 'workspace_queries': 'stead.workspace-queries/1',
}


def require(value):
    if not value:
        raise ValueError('Fixed saved8 rehearsal evidence refused')


def sha(raw):
    require(type(raw) is bytes)
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value)
        value[key] = item
    return value


def decimal(value, bound):
    require(type(value) is str and re.fullmatch('0|[1-9][0-9]{0,5}', value))
    number = int(value)
    require(number <= bound)
    return number


def command(offset, previous):
    require(type(offset) is int and 0 <= offset < MAX_CAPTURE and offset % CHUNK == 0)
    require(previous == '' if offset == 0 else digest(previous))
    return "+home-ui-capture [" + format(offset, ',').replace(',', '.') + " '" + previous + "']"


def atom(output, maximum):
    require(type(output) is str and 0 < len(output) <= maximum
            and re.fullmatch('[0-9a-fx. \\t\\r\\n]+', output))
    token = re.sub('[ \\t\\r\\n]', '', output)
    require(re.fullmatch('0x[0-9a-f]+(?:\\.[0-9a-f]+)*', token))
    return int(token.replace('.', ''), 16)


def fingerprint(dojo):
    value = atom(dojo(FINGERPRINT), 96)
    require(value < 2**256)
    return f'{value:064x}'


def chunk(output, offset, previous, before):
    number = atom(output, 100000)
    raw = number.to_bytes((number.bit_length() + 7) // 8, 'little')
    require(0 < len(raw) <= 40000)
    row = json.loads(raw, object_pairs_hook=unique)
    require(type(row) is dict and set(row) == FIELDS and all(type(v) is str for v in row.values())
            and canonical(row) == raw and row['protocol'] == 'stead.saved8-capture/1')
    total, length = decimal(row['total_bytes'], MAX_CAPTURE), decimal(row['length'], CHUNK)
    require(0 < total and offset < total and decimal(row['offset'], MAX_CAPTURE) == offset
            and length == min(CHUNK, total - offset))
    require(all(digest(row[key]) for key in PINS) and row['vase_fingerprint'] == before
            and (offset == 0 or row['capture_pin'] == previous))
    require(len(row['data_hex']) == length * 2 and re.fullmatch('[0-9a-f]+', row['data_hex']))
    return row, bytes.fromhex(row['data_hex'])


def validate_capture(value):
    require(type(value) is dict and set(value) == {'protocol', 'stage', 'saved_version',
            'artifact_bytes', 'artifact_sha256', 'data', *PINS}
            and value['protocol'] == 'stead.saved8-capture-record/1'
            and value['stage'] in STAGES and type(value['saved_version']) is int and value['saved_version'] == 8
            and type(value['artifact_bytes']) is int and 0 < value['artifact_bytes'] <= MAX_CAPTURE
            and type(value['data']) is bytes and len(value['data']) == value['artifact_bytes']
            and value['data'][-1] != 0 and all(digest(value[k]) for k in (*PINS, 'artifact_sha256')))
    require(sha(value['data']) == value['artifact_sha256']
            and sha(b'stead.saved8-capture/1\0' + value['data'].hex().encode()) == value['capture_pin'])
    return value


def collect(dojo, stage):
    require(type(stage) is str and stage in STAGES)
    require(dojo(SUSPENDED).strip() == '%.n' and dojo(DESK).strip() == '%release-test')
    before = fingerprint(dojo)
    offset, previous, first, parts = 0, '', None, []
    for _ in range(16):
        row, data = chunk(dojo(command(offset, previous)), offset, previous, before)
        if first is None:
            first, previous = row, row['capture_pin']
        require(all(row[k] == first[k] for k in (*PINS, 'total_bytes')))
        parts.append(data)
        offset += len(data)
        if offset == decimal(first['total_bytes'], MAX_CAPTURE):
            break
    else:
        raise ValueError('Fixed saved8 capture chunk bound')
    require(dojo(SUSPENDED).strip() == '%.n' and dojo(DESK).strip() == '%release-test'
            and fingerprint(dojo) == before)
    data = b''.join(parts)
    return validate_capture({'protocol': 'stead.saved8-capture-record/1', 'stage': stage,
        'saved_version': 8, 'artifact_bytes': len(data), 'artifact_sha256': sha(data), 'data': data,
        **{k: first[k] for k in PINS}})


def metadata(value):
    validate_capture(value)
    return {key: item for key, item in value.items() if key != 'data'}


def preserved(before, after, *, complete):
    validate_capture(before)
    validate_capture(after)
    require(type(complete) is bool)
    require(all(before[k] == after[k] for k in ('durable_pin', *TAILS)))
    if complete:
        require(before['data'] == after['data'] and all(before[k] == after[k] for k in PINS))
    return True


def complete_stages(rows):
    require(type(rows) is dict and tuple(rows) == STAGES)
    for stage, row in rows.items():
        validate_capture(row)
        require(row['stage'] == stage)
        preserved(rows['seed8'], row, complete=False)
    preserved(rows['a0-loaded'], rows['a0-cold'], complete=True)
    require(sum(row['artifact_bytes'] for row in rows.values()) <= len(STAGES) * MAX_CAPTURE)
    return {stage: metadata(row) for stage, row in rows.items()}


def capabilities(value):
    require(type(value) is dict and canonical(value) == canonical(CAPABILITIES))
    return dict(value)

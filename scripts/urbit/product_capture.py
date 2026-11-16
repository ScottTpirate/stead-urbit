"""Bounded bytes from the actual old producer; not a state-validity proof.

Only the existing trusted four-fake-ship supervisor calls collect. The outer
verifier must establish immutable sources, real execution and cleanup before
exports() may publish the two fixed synthetic artifacts. No runtime is started.
"""
from __future__ import annotations

import hashlib
import json
import re

MAX_BYTES = 262144
CHUNK = 16384
MAX_CHUNKS = 16
OLD_CANDIDATE = '3b0bcedf57cf7affebf000e1a52de807e5150f84'
GENERATOR = 'native/core/desk/gen/stead-v10-capture.hoon'
HASH = re.compile(r'[0-9a-f]{64}')
DECIMAL = re.compile(r'0|[1-9][0-9]*')
FIELDS = frozenset(('protocol', 'target', 'offset', 'length', 'total_bytes',
                    'capture_pin', 'native_vase_fingerprint', 'type_pin', 'payload_pin', 'data_hex'))
RECORD_FIELDS = frozenset(('protocol', 'target', 'capture_pin', 'native_vase_fingerprint',
                         'type_pin', 'payload_pin', 'artifact_sha256', 'artifact_bytes', 'data_hex'))
METADATA_FIELDS = RECORD_FIELDS - {'data_hex'}


def require(ok, message='V10 capture refused'):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def domain(name, raw):
    return sha(name.encode() + b'\0' + raw)


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate capture field')
        value[key] = item
    return value


def decimal(value, maximum=MAX_BYTES):
    require(isinstance(value, str) and len(value) <= 20 and DECIMAL.fullmatch(value), 'Capture decimal shape')
    number = int(value)
    require(number <= maximum, 'Capture decimal bound')
    return number


def source(target, offset, pin):
    require(target in ('predecessor', 'product') and type(offset) is int
            and 0 <= offset < MAX_BYTES and offset % CHUNK == 0, 'Capture command scope')
    require(pin == '' if offset == 0 else isinstance(pin, str) and HASH.fullmatch(pin), 'Capture command pin')
    literal = format(offset, ',').replace(',', '.')
    return f"+stead-v10-capture [%{target} {literal} '{pin}']"


def is_source(raw):
    """Closed canonical generator spelling; no caller-selected output cap."""
    if not isinstance(raw, str) or len(raw) > 160:
        return False
    match = re.fullmatch(r"\+stead-v10-capture \[%(predecessor|product) ([0-9.]{1,9}) '([0-9a-f]{0,64})'\]", raw)
    if match is None:
        return False
    try:
        return raw == source(match[1], int(match[2].replace('.', '')), match[3])
    except ValueError:
        return False


def chunk(output, target, offset, pin, expected_fingerprint):
    require(isinstance(output, str) and 0 < len(output) <= 100000
            and re.fullmatch(r'[0-9a-fx. \t\r\n]+', output), 'Bounded capture atom')
    token = re.sub(r'[ \t\r\n]', '', output)
    require(re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', token), 'One capture atom')
    number = int(token.replace('.', ''), 16)
    raw = number.to_bytes((number.bit_length() + 7) // 8, 'little')
    require(0 < len(raw) <= 40000, 'Bounded capture JSON')
    row = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(row, dict) and set(row) == FIELDS and all(isinstance(v, str) for v in row.values())
            and canonical(row) == raw, 'Canonical closed capture response')
    require(row['protocol'] == 'stead.v10-capture/1' and row['target'] == target, 'Capture response scope')
    total = decimal(row['total_bytes'])
    length = decimal(row['length'], CHUNK)
    require(0 < total <= MAX_BYTES and offset < total and decimal(row['offset']) == offset
            and length == min(CHUNK, total - offset), 'Exact consecutive capture chunk')
    require(all(HASH.fullmatch(row[k]) for k in ('capture_pin', 'native_vase_fingerprint', 'type_pin', 'payload_pin'))
            and row['native_vase_fingerprint'] == expected_fingerprint, 'Capture fingerprint correlation')
    require(offset == 0 or row['capture_pin'] == pin, 'Snapshot changed during capture')
    require(len(row['data_hex']) == length * 2 and re.fullmatch('[0-9a-f]+', row['data_hex']), 'Exact capture byte encoding')
    return row, bytes.fromhex(row['data_hex'])


def validate_metadata(row):
    require(isinstance(row, dict) and set(row) == METADATA_FIELDS
            and row['protocol'] == 'stead.v10-capture-record/1'
            and row['target'] in ('predecessor', 'product')
            and type(row['artifact_bytes']) is int and 0 < row['artifact_bytes'] <= MAX_BYTES,
            'Closed capture metadata')
    require(all(isinstance(row[k], str) and HASH.fullmatch(row[k]) for k in (
        'capture_pin', 'native_vase_fingerprint', 'type_pin', 'payload_pin', 'artifact_sha256')), 'Capture pin shape')


def validate_record(row):
    require(isinstance(row, dict) and set(row) == RECORD_FIELDS, 'Closed capture record')
    validate_metadata({k: v for k, v in row.items() if k != 'data_hex'})
    require(isinstance(row['data_hex'], str) and len(row['data_hex']) == row['artifact_bytes'] * 2
            and re.fullmatch('[0-9a-f]+', row['data_hex']), 'Bounded retained capture bytes')
    raw = bytes.fromhex(row['data_hex'])
    require(raw[-1] != 0 and sha(raw) == row['artifact_sha256']
            and domain('stead.v10-capture/1', row['data_hex'].encode()) == row['capture_pin'], 'Captured artifact bytes changed')
    # Do not widen the unrelated scheduled-Gall16KiB decoder here. Actual
    # source-bound native capture establishes origin; native successor cue,
    # exact jam roundtrip and full on-load replay remain separate requirements.
    return raw


def collect(dojo, fingerprint, target, expected_fingerprint):
    require(target in ('predecessor', 'product') and isinstance(expected_fingerprint, str)
            and HASH.fullmatch(expected_fingerprint), 'Capture target/fingerprint')
    require(dojo('zod', '.^(? %gu /=stead-home=/$)').strip() == '%.n', 'Actual Home must be idle')
    offset, pin, first, parts = 0, '', None, []
    for _ in range(MAX_CHUNKS):
        row, raw = chunk(dojo('zod', source(target, offset, pin)), target, offset, pin, expected_fingerprint)
        if first is None:
            first, pin = row, row['capture_pin']
        require(all(row[k] == first[k] for k in ('target', 'total_bytes', 'capture_pin',
                    'native_vase_fingerprint', 'type_pin', 'payload_pin')), 'Capture snapshot changed')
        parts.append(raw)
        offset += len(raw)
        if offset == decimal(first['total_bytes']):
            break
    else:
        raise ValueError('Capture exceeded16chunks')
    require(dojo('zod', '.^(? %gu /=stead-home=/$)').strip() == '%.n'
            and fingerprint() == expected_fingerprint, 'Capture final idle/fingerprint changed')
    raw = b''.join(parts)
    retained = {k: first[k] for k in ('target', 'capture_pin', 'native_vase_fingerprint', 'type_pin', 'payload_pin')}
    retained.update(protocol='stead.v10-capture-record/1', artifact_bytes=len(raw),
                    artifact_sha256=sha(raw), data_hex=raw.hex())
    validate_record(retained)
    return retained


def metadata(row):
    validate_record(row)
    return {k: v for k, v in row.items() if k != 'data_hex'}


def exports(rows, inputs, run_id, guard_sha256):
    """Pure fixed artifact map. Caller first verifies whole real inspection."""
    require(isinstance(rows, dict) and set(rows) == {'predecessor', 'product'}, 'Both exact old captures required')
    require(isinstance(inputs, dict) and inputs.get('candidate_commit') == OLD_CANDIDATE
            and isinstance(inputs.get('controller_commit'), str)
            and re.fullmatch('[0-9a-f]{40}', inputs['controller_commit'])
            and isinstance(run_id, str) and re.fullmatch('[0-9a-f]{32}', run_id)
            and isinstance(guard_sha256, str) and HASH.fullmatch(guard_sha256), 'Actual old capture custody')
    require(isinstance(inputs.get('composed_files'), dict) and isinstance(inputs.get('controller_files'), dict),
            'Immutable capture source inventories')
    for path in (GENERATOR, 'specs/urbit/toolchain.lock.json'):
        pin = inputs['controller_files'].get(path)
        require(isinstance(pin, dict) and set(pin) == {'bytes', 'sha256'}
                and type(pin['bytes']) is int and pin['bytes'] > 0
                and isinstance(pin['sha256'], str) and HASH.fullmatch(pin['sha256']), 'Capture source pin shape')
    require(inputs['composed_files'].get(GENERATOR) == inputs['controller_files'][GENERATOR],
            'Trusted capture generator required')
    output = {}
    for target in ('predecessor', 'product'):
        row = rows[target]
        require(row['target'] == target, 'Capture target alias')
        raw = validate_record(row)
        name = 'v10-old-' + target
        descriptor = metadata(row) | {
            'protocol': 'stead.v10-capture-artifact/1', 'producer_candidate': OLD_CANDIDATE,
            'controller_commit': inputs['controller_commit'], 'inputs_sha256': sha(canonical(inputs)),
            'run_id': run_id, 'guard_sha256': guard_sha256,
            'native_source_manifest_sha256': sha(canonical(inputs['composed_files'])),
            'generator_sha256': inputs['controller_files'][GENERATOR]['sha256'],
            'runtime_lock_sha256': inputs['controller_files']['specs/urbit/toolchain.lock.json']['sha256'],
            'capture_stage': 'actual-idle-predecessor' if target == 'predecessor' else 'actual-cold-suspended-product',
            'classification': 'actual-old-producer-bytes-validation-pending', 'qualifies_phase': False}
        output[name + '.jam'] = raw
        output[name + '.json'] = canonical(descriptor) + b'\n'
    require(sum(len(v) for k, v in output.items() if k.endswith('.jam')) <= 2 * MAX_BYTES, 'Total capture artifact cap')
    return output

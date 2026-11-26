"""Closed saved8 capture/equality checks; supplied data alone proves no runtime.

Small source-owned direct expressions observe p and q separately. Python verifies
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
ENCODING_MARKER = 0x736176656438686578
STAGES = ('seed8', 'a0-loaded', 'a0-cold', 'assets-loaded', 'rollback-loaded')
TAILS = ('db_pin', 'code_pin', 'handoff_pin', 'retired_pin', 'packs_pin', 'external_pin')
PINS = ('capture_pin', 'vase_fingerprint', 'type_pin', 'payload_pin', 'durable_pin', *TAILS)
FIELDS = frozenset(('protocol', 'offset', 'length', 'total_bytes', 'data_hex', *PINS))
SUSPENDED = '.^(? %gu /=stead-home=/$)'
DESK = '.^(desk %gd /=stead-home=/$)'
# Exact source-owned direct projection builders; no native library import.
SANITY = '0x73.6176.6564.3868.6578'

EGG = '=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)  '
SAVED = EGG + '?>  ?=([%20 %live *] egg)  =/  saved=vase  +.old-state.egg  '
VERSION = '?=([%stead-home %8 *] q.saved)'
SHAPE = '?=([%stead-home %8 [* *] * * * * *] q.saved)'
STORED = (SAVED + '?>  ' + SHAPE + '  '
    '=/  stored=[team=[db=* projection=*] code=* handoff=* retired=* packs=* external=*]  +>.q.saved  ')
PREFIX = SAVED + '?>  ' + VERSION + '  =/  packed  (jam saved)  '
FINGERPRINT = SAVED + '?>  ' + VERSION + '  ^-  @ux  (shax (jam saved))'
TOTAL = PREFIX + '^-  @ud  (met 3 packed)'

# Each of these returns a loobean. An individual field or compiler failure
# must not hide the other observations from the same suspended fake ship.
CONDITIONS = {
    'ship': '=(~zod our)',
    'fake': '.^(? %j /(scot %p our)/fake/(scot %da now))',
    'egg': EGG + '?=([%20 %live *] egg)',
    'version': SAVED + VERSION,
    'shape': SAVED + SHAPE,
    'code': STORED + '?=(^ code.stored)',
    'code-head': STORED + '?@  code.stored  %.n  ?=(^ -.code.stored)',
    'handoff': STORED + '=(handoff.stored [%open 2 ~])',
    'retired': STORED + '?=(^ retired.stored)',
    'packs': STORED + '?=(^ packs.stored)',
    'external': STORED + '?=(^ external.stored)',
}


COMPILER_WORDS = {'mint-vain', 'mint-nice', 'nest-fail', 'find-fork', 'find-limb', 'seek-loop', 'play-dull', 'syntax error'} | {'dojo', 'ford', 'hoon', 'syntax', 'error', 'failed',
        'trace', 'stack', 'crash', 'expression', 'exit', 'bail', 'fail', 'parse',
        'unexpected', 'token', 'line', 'column', 'evaluation', 'arvo', 'lens',
        'term', 'type', 'path', 'meme', 'hoon-expression', 'poke', 'crude',
        'nest', 'have', 'need', 'reference', 'find', 'limb', 'seed', 'weld'}


def fixed_compiler_terms(text):
    tokens = re.findall(r'[a-z][a-z-]{0,63}', text.lower()[:1024])
    coords = re.findall(r'\[([0-9]{1,5})[ ,]+([0-9]{1,5})\]', text[:1024])
    return {'terms': list(dict.fromkeys(word for word in tokens if word in COMPILER_WORDS))[:12],
        'coordinates': [[int(line), int(column)] for line, column in coords[:4]]}


def projection_checks(dojo):
    observed, diagnostics = {}, {}
    for name, source in CONDITIONS.items():
        output = dojo(source)
        observed[name] = projection_result(output)
        if observed[name] == 'native-error':
            diagnostics[name] = fixed_compiler_terms(output)
    if any(value != 'yes' for value in observed.values()):
        error = ValueError('Saved8 projection check failed')
        error.projection_results = observed
        error.projection_diagnostics = diagnostics
        raise error


def projection_result(output):
    value = output.strip()
    if value in ('%.y', '%.n'):
        return 'yes' if value == '%.y' else 'no'
    return 'native-error' if value else 'empty'


ENCODING_CONTROL = (
    '=/  capture-hex  |=  [size=@ud data=@]  ^-  @t  '
    '?>  (lte (met 3 data) size)  ?:  =(0 size)  \'\'  '
    '(en:base16:mimes:html [size (rev 3 size data)])  '
    '=/  vectors=(list [size=@ud data=@ text=@t])  '
    '~[[0 0 \'\'] [1 0 \'00\'] [2 0 \'0000\'] [1 0xff \'ff\'] '
    '[2 0x100 \'0001\'] [3 0x1234 \'341200\'] '
    '[4 0x102.0304 \'04030201\'] [4 0xff00.ff00 \'00ff00ff\']]  '
    '?>  (levy vectors |=([size=@ud data=@ text=@t] =((capture-hex size data) text)))  '
    '^-  @ux  0x73.6176.6564.3868.6578'
)

NOUNS = {
    'type_pin': ('stead.saved8-type/1', 'p.saved'),
    'payload_pin': ('stead.saved8-payload/1', 'q.saved'),
    'durable_pin': ('stead.saved8-durable/1',
                    '[db.team.stored code.stored handoff.stored retired.stored packs.stored external.stored]'),
    'db_pin': ('stead.saved8-tail/1', 'db.team.stored'),
    'code_pin': ('stead.saved8-tail/1', 'code.stored'),
    'handoff_pin': ('stead.saved8-tail/1', 'handoff.stored'),
    'retired_pin': ('stead.saved8-tail/1', 'retired.stored'),
    'packs_pin': ('stead.saved8-tail/1', 'packs.stored'),
    'external_pin': ('stead.saved8-tail/1', 'external.stored'),
}

def grouped(number, base=10):
    require(type(number) is int and number >= 0 and base in (10, 16))
    digits = str(number) if base == 10 else format(number, 'x')
    width = 3 if base == 10 else 4
    first = len(digits) % width or width
    return digits[:first] + ''.join('.' + digits[i:i + width]
                                  for i in range(first, len(digits), width))

def bound(prefix, fingerprint):
    require(type(fingerprint) is str and re.fullmatch('[0-9a-f]{64}', fingerprint))
    return prefix + '?>  =(0x' + grouped(int(fingerprint, 16), 16) + ' (shax packed))  '

def digest_command(field, fingerprint):
    require(type(field) is str and field in NOUNS)
    domain, noun = NOUNS[field]
    # This is the exact a0 ++hash arithmetic. Return its numeric digest rather
    # than running its64-character output formatter. Python formats064x.
    prefix = PREFIX if field in ('type_pin', 'payload_pin') else STORED + '=/  packed  (jam saved)  '
    return (bound(prefix, fingerprint)
        + '=/  part  (jam ' + noun + ')  =/  width  (met 3 part)  '
        + '=/  text=@t  (en:base16:mimes:html [width (rev 3 width part)])  '
        + '=/  domain=@t  \'' + domain + '\'  =/  prefix  +((met 3 domain))  '
        + '=/  length  (add prefix (met 3 text))  '
        + '=/  data  (mix domain (lsh [3 prefix] text))  '
        + '^-  @ux  (sha-256l:sha [length (rev 3 length data)])')

def chunk_command(total, offset, fingerprint):
    require(type(total) is int and 0 < total <= MAX_CAPTURE
            and type(offset) is int and 0 <= offset < total and offset % CHUNK == 0)
    size = min(CHUNK, total - offset)
    return (bound(PREFIX, fingerprint)
        + '?>  =(' + grouped(total) + ' (met 3 packed))  ^-  @ux  '
        + '(cut 3 [' + grouped(offset) + ' ' + grouped(size) + '] packed)')

def chunk_bytes(value, total, offset):
    """The transport owner's strict @ux parser supplies an integer, not text."""
    require(type(total) is int and 0 < total <= MAX_CAPTURE
            and type(offset) is int and 0 <= offset < total and offset % CHUNK == 0)
    size = min(CHUNK, total - offset)
    require(type(value) is int and 0 <= value < 1 << (8 * size))
    # A zero high byte is part of the original chunk. Never use minimal width.
    return value.to_bytes(size, 'little')

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


def native_decimal(output):
    require(type(output) is str and 0 < len(output) <= 32
            and re.fullmatch('[0-9. \t\r\n]+', output))
    token = re.sub('[ \t\r\n]', '', output)
    require(re.fullmatch('0|[1-9][0-9]{0,2}(?:\\.[0-9]{3})*', token))
    value = int(token.replace('.', ''))
    require(0 < value <= MAX_CAPTURE and token == grouped(value))
    return value


def collect(dojo, stage):
    require(type(stage) is str and stage in STAGES)
    require(dojo(SUSPENDED).strip() == '%.n' and dojo(DESK).strip() == '%release-test')
    # Independent trivial control first. The separate encoder control proves
    # only its eight small vectors; neither compiles a capture generator.
    require(atom(dojo(SANITY), 64) == ENCODING_MARKER)
    require(atom(dojo(ENCODING_CONTROL), 64) == ENCODING_MARKER)
    before = fingerprint(dojo)
    projection_checks(dojo)
    total = native_decimal(dojo(TOTAL))
    pins = {'vase_fingerprint': before}
    for field in NOUNS:
        value = atom(dojo(digest_command(field, before)), 96)
        require(value < 2**256)
        pins[field] = f'{value:064x}'
    parts = []
    for offset in range(0, total, CHUNK):
        number = atom(dojo(chunk_command(total, offset, before)), 100000)
        parts.append(chunk_bytes(number, total, offset))
    require(0 < len(parts) <= 16)
    require(dojo(SUSPENDED).strip() == '%.n' and dojo(DESK).strip() == '%release-test'
            and fingerprint(dojo) == before)
    data = b''.join(parts)
    require(len(data) == total)
    pins['capture_pin'] = sha(b'stead.saved8-capture/1\0' + data.hex().encode())
    return validate_capture({'protocol': 'stead.saved8-capture-record/1', 'stage': stage,
        'saved_version': 8, 'artifact_bytes': len(data), 'artifact_sha256': sha(data), 'data': data,
        **pins})


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

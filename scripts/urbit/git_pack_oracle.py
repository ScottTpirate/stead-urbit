"""Independent bounded SHA-1 pack oracle for conformance tests.

This module expands bytes, not repository graphs or authority. It is not
loaded by the native Git service and never writes a repository.
"""
from dataclasses import dataclass
import hashlib
import struct
import zlib

MAX_PACK = 8 * 1024**2
MAX_BODY = 8 * 1024**2
MAX_EXPANDED = 32 * 1024**2
MAX_OBJECTS = 4096
MAX_DEPTH = 32
KINDS = {1: 'commit', 2: 'tree', 3: 'blob', 4: 'tag'}


class PackError(ValueError):
    pass


class Reader:
    def __init__(self, data):
        self.data = memoryview(data)
        self.pos = 0

    def take(self, length):
        end = self.pos + length
        if end > len(self.data):
            raise PackError('truncated entry')
        chunk = self.data[self.pos:end]
        self.pos = end
        return chunk

    def byte(self):
        return self.take(1)[0]

    def size(self, initial=0, shift=0, continuation=True):
        while continuation:
            part = self.byte()
            initial |= (part & 127) << shift
            continuation = part & 128
            shift += 7
            if initial > MAX_BODY or shift > 32:
                raise PackError('encoded size exceeds bound')
        return initial

    def distance(self):
        part = self.byte()
        distance = part & 127
        while part & 128:
            part = self.byte()
            distance = ((distance + 1) << 7) | (part & 127)
            if distance > MAX_PACK:
                raise PackError('delta offset exceeds bound')
        return distance

    def inflate(self, length):
        inflater = zlib.decompressobj()
        result = bytearray()
        while not inflater.eof:
            count = min(16384, len(self.data) - self.pos)
            if count == 0:
                raise PackError('truncated zlib stream')
            try:
                result.extend(inflater.decompress(self.take(count), length + 1 - len(result)))
            except zlib.error as error:
                raise PackError('invalid zlib stream') from error
            if len(result) > length or inflater.unconsumed_tail:
                raise PackError('inflated size exceeds declaration')
        self.pos -= len(inflater.unused_data)
        if len(result) != length:
            raise PackError('inflated size differs')
        return bytes(result)


@dataclass(frozen=True)
class Entry:
    kind: int
    base: int | bytes | None
    data: bytes


def delta(base, patch, remaining):
    reader = Reader(patch)
    if reader.size() != len(base):
        raise PackError('delta base size differs')
    target = reader.size()
    if target > remaining:
        raise PackError('expanded total exceeds bound')
    output = bytearray()
    while reader.pos < len(patch):
        opcode = reader.byte()
        if opcode & 128:
            offset = sum(reader.byte() << (index * 8) for index in range(4) if opcode & (1 << index))
            size = sum(reader.byte() << (index * 8) for index in range(3) if opcode & (16 << index)) or 65536
            if offset + size > len(base) or len(output) + size > target:
                raise PackError('delta copy exceeds bound')
            output.extend(memoryview(base)[offset:offset + size])
        else:
            if opcode == 0 or len(output) + opcode > target:
                raise PackError('invalid delta literal')
            output.extend(reader.take(opcode))
    if len(output) != target:
        raise PackError('delta result size differs')
    return bytes(output)


def unpack(pack):
    if not 32 <= len(pack) <= MAX_PACK or pack[:4] != b'PACK':
        raise PackError('invalid pack header or length')
    version, count = struct.unpack_from('>II', pack, 4)
    if version not in (2, 3) or count > MAX_OBJECTS:
        raise PackError('unsupported version or object count')
    payload = memoryview(pack)[:-20]
    if hashlib.sha1(payload).digest() != pack[-20:]:
        raise PackError('pack checksum differs')
    reader = Reader(payload)
    reader.pos = 12
    entries = {}
    inflated = 0
    for _ in range(count):
        offset = reader.pos
        first = reader.byte()
        kind = (first >> 4) & 7
        length = reader.size(first & 15, 4, first & 128)
        inflated += length
        if inflated > MAX_EXPANDED:
            raise PackError('inflated total exceeds bound')
        if kind == 6:
            base = offset - reader.distance()
            if base not in entries:
                raise PackError('offset does not identify an earlier entry')
        elif kind == 7:
            base = bytes(reader.take(20))
        elif kind in KINDS:
            base = None
        else:
            raise PackError('unsupported object type')
        entries[offset] = Entry(kind, base, reader.inflate(length))
    if reader.pos != len(payload):
        raise PackError('pack entry count or trailing data differs')

    by_offset, by_oid, objects = {}, {}, {}
    expanded = 0
    # Reference deltas can point forward. Each round resolves at least one
    # depth level in any valid bounded graph. Thin/cyclic packs fail closed.
    for _ in range(MAX_DEPTH + 1):
        for offset, entry in list(entries.items()):
            if entry.base is None:
                kind, body, depth = KINDS[entry.kind], entry.data, 0
            else:
                base = (by_offset if isinstance(entry.base, int) else by_oid).get(entry.base)
                if base is None:
                    continue
                kind, base_body, depth = base
                depth += 1
                if depth > MAX_DEPTH:
                    raise PackError('delta chain exceeds bound')
                body = delta(base_body, entry.data, MAX_EXPANDED - expanded)
            expanded += len(body)
            if expanded > MAX_EXPANDED:
                raise PackError('expanded total exceeds bound')
            sha = hashlib.sha1(f'{kind} {len(body)}\0'.encode())
            sha.update(body)
            oid = sha.digest()
            existing = objects.setdefault(oid.hex(), (kind, body))
            if existing != (kind, body):
                raise PackError('conflicting object bytes for one ID')
            by_offset[offset] = (kind, body, depth)
            by_oid[oid] = (kind, body, min(depth, by_oid.get(oid, (None, None, depth))[2]))
            del entries[offset]
        if not entries:
            return objects
    raise PackError('unresolved or overdeep delta graph')

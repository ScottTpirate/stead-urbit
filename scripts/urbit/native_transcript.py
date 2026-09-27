"""Bounded raw synthetic transport evidence, separate from summary reports."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import re


class Transcript:
    def __init__(self, path, *, total_limit=512 * 1024 * 1024,
                 line_limit=24 * 1024 * 1024):
        # A failed exchange can retain1MiB each of encoded/received/decoded
        # bytes plus both1MiB diagnostic streams. Hex and worst-case JSON
        # escaping require a larger record budget than the native wire limit.
        self.path = Path(path)
        self.total_limit, self.line_limit = total_limit, line_limit
        self.total = self.count = 0
        self.digest = hashlib.sha256()
        self.file = self.path.open('xb')
        self.stream = gzip.GzipFile(fileobj=self.file, mode='wb', mtime=0)
        self.closed = False

    def append(self, record):
        if self.closed:
            raise ValueError('Transport evidence already closed')
        raw = (json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
        if len(raw) > self.line_limit or self.total + len(raw) > self.total_limit:
            raise ValueError('Transport evidence bound exceeded; native result cannot pass')
        self.stream.write(raw)
        self.stream.flush()
        self.digest.update(raw)
        self.total += len(raw)
        self.count += 1
        return {'artifact': self.path.name, 'line': self.count,
                'record_sha256': hashlib.sha256(raw).hexdigest(), 'record_bytes': len(raw)}

    def close(self):
        if not self.closed:
            self.stream.close()
            self.file.close()
            self.closed = True
        with self.path.open('rb') as artifact:
            digest = hashlib.file_digest(artifact, 'sha256').hexdigest()
        return {'file': self.path.name, 'encoding': 'gzip-jsonl', 'records': self.count,
                'uncompressed_bytes': self.total, 'uncompressed_sha256': self.digest.hexdigest(),
                'sha256': digest,
                'scope': 'Exact synthetic decoded transport/input records; native frame digests retained'}


class RuntimeLogs:
    """Actual bounded all-ship log deltas; uncertainty invalidates zero-error claims."""
    ERROR = re.compile(rb'fail|error|bail|nack|crash|need-mark|no mark|unrecognized mark|mint-|nest-', re.I)

    def __init__(self, root, transcript, ships=('zod', 'bus', 'nec', 'bud')):
        self.root, self.transcript, self.ships = Path(root), transcript, tuple(ships)

    def __call__(self, cursor=None):
        if cursor is not None and set(cursor) != set(self.ships):
            raise ValueError('All-ship runtime log cursor required')
        after, segments, errors = {}, [], []
        for ship in self.ships:
            path = self.root / (ship + '.log')
            if path.is_symlink():
                raise ValueError('Redirected runtime log')
            with path.open('rb') as source:
                stat = os.fstat(source.fileno())
                if stat.st_size > 16 * 1024 * 1024:
                    raise ValueError('Runtime log continuity bound exceeded; preserve/rotate logs before a new run')
                content = source.read(stat.st_size)
                if len(content) != stat.st_size:
                    raise ValueError('Runtime log changed while reading its prefix')
                named = path.lstat()
                if (named.st_dev, named.st_ino) != (stat.st_dev, stat.st_ino) or path.is_symlink():
                    raise ValueError('Runtime log rotated during observation')
                current = {'device': stat.st_dev, 'inode': stat.st_ino, 'end': stat.st_size,
                           'prefix_sha256': hashlib.sha256(content).hexdigest(),
                           'partial_hex': content.rsplit(b'\n', 1)[-1][-4096:].hex()}
                after[ship] = current
                if cursor is None:
                    continue
                previous = cursor[ship]
                if (previous['device'], previous['inode']) != (stat.st_dev, stat.st_ino) or previous['end'] > stat.st_size:
                    raise ValueError('Runtime log replaced or truncated during observation')
                if hashlib.sha256(content[:previous['end']]).hexdigest() != previous['prefix_sha256']:
                    raise ValueError('Runtime log prefix changed during observation')
                length = stat.st_size - previous['end']
                if length > 1024 * 1024:
                    raise ValueError('Runtime log observation bound exceeded')
                raw = content[previous['end']:]
                if len(raw) != length:
                    raise ValueError('Runtime log delta disappeared')
            evidence = self.transcript.append({'kind': 'runtime-log-delta', 'ship': ship,
                'path': path.name, 'start': previous['end'], 'end': stat.st_size, 'hex': raw.hex()})
            segments.append({'ship': ship, 'path': path.name, 'start': previous['end'],
                'end': stat.st_size, 'sha256': hashlib.sha256(raw).hexdigest(), 'transcript': evidence})
            # Diagnostic tokens can straddle two reads; retain an incomplete
            # trailing line in the cursor, while raw evidence keeps exact deltas.
            joined = bytes.fromhex(previous['partial_hex']) + raw
            for line in joined.splitlines():
                if self.ERROR.search(line):
                    errors.append({'ship': ship, 'line_sha256': hashlib.sha256(line).hexdigest(),
                                   'text': line.decode(errors='replace')[:4096]})
        return {'cursor': after, 'errors': errors, 'segments': segments,
                'scope': 'All four actual log deltas retained; conservative diagnostic pattern filter, not proof of no runtime bytes'}

"""Parse bounded staged SDK metadata, not builder custody or consumer acceptance.

The caller must obtain these bytes from its owned builder's retained terminal
response. This helper does not authenticate that response, verify the declared
Clay case, prove file materialization, or permit transfer before stop/reap.
Never read the expected artifact pins from a manifest beside artifact files.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from sdk_artifacts import ARTIFACTS, inventory
from package_sdk import require

MAX_RESPONSE = 8192


@dataclass(frozen=True)
class StagedBuild:
    builder: str
    desk: str
    clay_case: str
    response_sha256: str
    artifacts: tuple[tuple[str, int, str], ...]

    def pins(self):
        """Fresh values suitable for read_artifacts after separate custody checks."""
        return {name: {'bytes': size, 'sha256': digest} for name, size, digest in self.artifacts}


def parse(raw, *, builder, desk):
    # These are the fixed planned isolated fixture identities, not arbitrary
    # ship/desk input supplied by the package or metadata under examination.
    require(builder == '~wes' and desk == 'base', 'SDK builder context differs')
    require(type(raw) is bytes and 0 < len(raw) <= MAX_RESPONSE, 'SDK staged response byte bound')

    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, 'Duplicate SDK staged response key')
            result[name] = value
        return result

    def invalid_constant(value):
        raise ValueError('Non-JSON SDK staged response constant')

    value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=unique,
                       parse_constant=invalid_constant)
    require(isinstance(value, dict) and set(value) == {
        'protocol', 'status', 'builder', 'desk', 'clay_case', 'artifacts'}, 'SDK staged response shape')
    require(value['protocol'] == 'stead.sdk-build-staged/1' and value['status'] == 'export_queued',
            'SDK staged response version or status')
    require(value['builder'] == builder and value['desk'] == desk, 'SDK staged builder identity differs')
    case = value['clay_case']
    # Preserve the reported case as an opaque receipt field. This lexical bound
    # is not a calendar parser or evidence that the claimed Clay bytes existed.
    require(isinstance(case, str) and 1 < len(case) <= 128
            and re.fullmatch(r'~[0-9a-z.]+', case), 'SDK staged Clay case shape')
    artifacts = value['artifacts']
    require(isinstance(artifacts, dict) and set(artifacts) == ARTIFACTS, 'SDK staged artifact inventory')
    pins = {}
    for name in sorted(ARTIFACTS):
        item = artifacts[name]
        require(isinstance(item, dict) and set(item) == {'bytes', 'sha256'}, 'SDK staged artifact shape')
        size = item['bytes']
        require(isinstance(size, str) and re.fullmatch(r'[1-9][0-9]{0,7}', size),
                'SDK staged artifact decimal size')
        pins[name] = {'bytes': int(size), 'sha256': item['sha256']}
    expected = inventory(pins)  # Includes strict digest and per-file/total limits.
    return StagedBuild(builder, desk, case, hashlib.sha256(raw).hexdigest(),
        tuple((name, size, digest) for name, (size, digest) in sorted(expected.items())))

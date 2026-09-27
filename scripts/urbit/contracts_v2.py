"""V2 host reference; reuses the unchanged, frozen v1 validator implementation.

Loading a separate module instance preserves v1's schema and tests. This is a
codec reference only, never authentication, native state or migration evidence.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('_stead_frozen_reference_v2',
                                             Path(__file__).with_name('contracts.py'))
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
reference.SCHEMA = json.loads((ROOT / 'specs/urbit/v2/command.schema.json').read_text())
parse = reference.parse
canonical = reference.canonical


def digest(command):
    return hashlib.sha256(b'stead.command/2\0' + canonical(command)).hexdigest()


def verify_freeze():
    """Both freezes remain executable; amendment does not bless mutated v1 files."""
    for name in ('contract-freeze.json', 'v2/contract-freeze.json'):
        manifest = json.loads((ROOT / 'specs/urbit' / name).read_text())
        for path, expected in manifest['files'].items():
            if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
                raise ValueError('Frozen bytes changed: ' + path)


if __name__ == '__main__':
    verify_freeze()
    print('PASS v1 and v2 contract hashes; metadata only, not native qualification')

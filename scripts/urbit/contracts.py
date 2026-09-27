#!/usr/bin/env python3
"""Bounded host reference for frozen contracts; NOT native Stead authorization."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'specs/urbit/command.schema.json').read_text())
POLICY = json.loads((ROOT / 'specs/urbit/policy-contract.json').read_text())
MAX_BYTES = 65536
MAX_U64 = 2**64 - 1


def no_numbers(value):
    raise ValueError('JSON numbers/constants are not part of this protocol')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def validate_schema(value, schema):
    """Closed subset used by our checked-in schema, not a general JSON Schema engine."""
    implemented = {'$schema', '$id', '$comment', '$defs', '$ref', 'title', 'type',
                   'const', 'enum', 'pattern', 'minLength', 'maxLength',
                   'additionalProperties', 'required', 'properties', 'oneOf'}
    if set(schema) - implemented:
        raise ValueError('Unsupported schema keyword')
    if '$ref' in schema:
        prefix = '#/$defs/'
        if not schema['$ref'].startswith(prefix):
            raise ValueError('Only local schema refs supported')
        validate_schema(value, SCHEMA['$defs'][schema['$ref'][len(prefix):]])
    if 'type' in schema:
        expected = {'object': dict, 'string': str}.get(schema['type'])
        if expected is None or type(value) is not expected:
            raise ValueError('Incorrect protocol value type')
    if 'const' in schema and value != schema['const']:
        raise ValueError('Unsupported constant')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError('Unsupported enum value')
    if isinstance(value, str):
        value.encode('utf-8', errors='strict')
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', MAX_BYTES):
            raise ValueError('String length outside profile')
        if 'pattern' in schema and re.fullmatch(schema['pattern'], value) is None:
            raise ValueError('String does not match profile')
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        if set(schema.get('required', [])) - value.keys():
            raise ValueError('Missing required field')
        if schema.get('additionalProperties') is False and value.keys() - properties.keys():
            raise ValueError('Unknown field')
        for key, definition in properties.items():
            if key in value:
                validate_schema(value[key], definition)
    if 'oneOf' in schema:
        valid = 0
        for candidate in schema['oneOf']:
            try:
                validate_schema(value, candidate)
                valid += 1
            except ValueError:
                pass
        if valid != 1:
            raise ValueError('Request does not match exactly one operation')


def parse(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('Envelope too large')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                           parse_int=no_numbers, parse_float=no_numbers,
                           parse_constant=no_numbers)
        validate_schema(value, SCHEMA)
    except (RecursionError, UnicodeError) as error:
        raise ValueError('Invalid encoding or nesting') from error
    for field in ('expected_revision', 'authority_epoch'):
        if int(value[field]) > MAX_U64:
            raise ValueError('Counter overflow')
    operation, payload = value['operation'], value['payload']
    if operation in ('project.create', 'work.create') and value['expected_revision'] != '0':
        raise ValueError('Creation requires absent-resource revision zero')
    if operation in ('work.update', 'policy.grant', 'policy.revoke') and value['expected_revision'] == '0':
        raise ValueError('Existing resource requires positive expected revision')
    if operation.startswith(('project.', 'policy.')) and value['resource_id'] != value['project_id']:
        raise ValueError('Project/policy target must match project')
    for field, bound in (('title', 800), ('description', 8192), ('markdown', 32768)):
        if field in payload and len(payload[field].encode('utf-8')) > bound:
            raise ValueError('Payload UTF-8 byte limit exceeded')
    if 'expires_at_ms' in payload and not 0 < int(payload['expires_at_ms']) <= MAX_U64:
        raise ValueError('Invalid grant expiry')
    return value


def canonical(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    parse(raw)
    return raw


def digest(value):
    return hashlib.sha256(b'stead.command/1\0' + canonical(value)).hexdigest()


def decision(evidence):
    # Reference truth table only: this does NOT resolve or authenticate evidence.
    if type(evidence) is not dict or set(evidence) != set(POLICY['dimensions']):
        return 'denied_or_not_found'
    return 'allow' if all(v == 'allow' for v in evidence.values()) else 'denied_or_not_found'


def role_allows(role, operation, *, project_scope_matches=False,
                organization_scope_matches=False, explicit_project_membership=False,
                affected_grant_role=None):
    """Reference bundle contribution only, NEVER a complete policy decision.

    For revoke, affected_grant_role is resolved from the current grant, not input.
    Scope flags are trusted-fixture inputs here, not a public authorization API.
    """
    bundle = POLICY['role_bundles'].get(role)
    if bundle is None:
        return False
    if operation in bundle.get('organization_operations', []):
        return organization_scope_matches is True
    if project_scope_matches is not True or operation not in bundle['project_operations']:
        return False
    administrator = role == 'organization_administrator'
    if administrator and organization_scope_matches is not True:
        return False
    if operation in ('policy.grant', 'policy.revoke'):
        if not administrator and explicit_project_membership is not True:
            return False
        return affected_grant_role in bundle['grant_roles']
    return explicit_project_membership is True


def test():
    import unittest
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests/urbit'), pattern='test_contracts.py')
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise SystemExit(1)
    print('PASS host reference contract checks; native parity and product authorization remain unimplemented')


if __name__ == '__main__':
    if sys.argv[1:] == ['test']:
        test()
    else:
        raise SystemExit('Usage: contracts.py test')

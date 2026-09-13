"""Host reference corpus only; no mocked/native product authority claim."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import contracts as c


class Contracts(unittest.TestCase):
    def setUp(self):
        self.vectors = json.loads((c.ROOT / 'specs/urbit/fixtures/commands.json').read_text())
        self.request = copy.deepcopy(self.vectors[0]['request'])

    def rejected(self, request):
        with self.assertRaises(ValueError):
            c.parse(json.dumps(request).encode())

    def test_golden_canonical_bytes_and_digests(self):
        for vector in self.vectors:
            with self.subTest(vector['name']):
                self.assertEqual(c.canonical(vector['request']).decode(), vector['canonical_utf8'])
                self.assertEqual(c.digest(vector['request']), vector['sha256'])

    def test_key_order_and_whitespace_are_not_new_commands(self):
        left = c.parse(json.dumps(self.request, indent=4).encode())
        right = c.parse(json.dumps(dict(reversed(list(self.request.items())))).encode())
        self.assertEqual(c.digest(left), c.digest(right))

    def test_changed_payload_under_same_id_has_different_digest(self):
        other = copy.deepcopy(self.request)
        other['payload']['title'] = 'Different operation content'
        self.assertNotEqual(c.digest(self.request), c.digest(other))

    def test_caller_cannot_attach_actor_or_decision(self):
        for field in ('principal_id', 'author', 'session', 'decision', 'authenticated'):
            with self.subTest(field):
                self.rejected({**self.request, field: 'forged'})

    def test_missing_fields_and_unsupported_version_fail(self):
        for field in self.request:
            other = copy.deepcopy(self.request)
            del other[field]
            self.rejected(other)
        self.rejected({**self.request, 'protocol': 'stead.command/2'})

    def test_duplicate_keys_and_non_json_numbers_rejected(self):
        cases = [b'{"project_id":"a","project_id":"b"}', b'NaN', b'Infinity', b'1.2', b'42', b'true', b'null']
        for raw in cases:
            with self.subTest(raw), self.assertRaises(ValueError):
                c.parse(raw)

    def test_ids_are_canonical_and_never_hostnames(self):
        for identifier in ('~bus', 'https://home.invalid/p/1', self.request['project_id'].upper(), '00000000-0000-0000-0000-000000000000'):
            self.rejected({**self.request, 'project_id': identifier})

    def test_revision_and_epoch_bounds(self):
        for field in ('expected_revision', 'authority_epoch'):
            for bad in ('-1', '01', str(2**64), 1, True):
                self.rejected({**self.request, field: bad})
        self.rejected({**self.request, 'authority_epoch': '0'})
        self.rejected({**self.request, 'expected_revision': '1'})
        self.rejected({**self.request, 'operation': 'work.update'})

    def test_fixed_work_ontology_and_closed_payload(self):
        for key, value in (('type', 'bug'), ('status', 'custom_status'), ('priority', 'critical'), ('custom_field', 'anything')):
            other = copy.deepcopy(self.request)
            other['payload'][key] = value
            self.rejected(other)

    def test_project_key_preserves_ten_character_prefix_limit(self):
        request = copy.deepcopy(self.vectors[2]['request'])
        request['payload']['project_key'] = 'ABCDEFGHIJ'
        c.parse(json.dumps(request).encode())
        request['payload']['project_key'] = 'ABCDEFGHIJK'
        self.rejected(request)

    def test_utf8_byte_limits_not_only_character_counts(self):
        other = copy.deepcopy(self.request)
        other['payload']['description'] = '雪' * 3000
        self.rejected(other)
        other = copy.deepcopy(self.vectors[1]['request'])
        other['payload']['markdown'] = '雪' * 11000
        self.rejected(other)

    def test_markdown_encoding_and_envelope_limits(self):
        for text in ('one\r\ntwo', 'null\0byte', '\ud800'):
            other = copy.deepcopy(self.vectors[1]['request'])
            other['payload']['markdown'] = text
            self.rejected(other)
        for raw in (b'\xff', b' ' * (c.MAX_BYTES + 1), b'[' * 2000):
            with self.assertRaises(ValueError):
                c.parse(raw)

    def test_each_policy_dimension_required_and_denies_win(self):
        evidence = {key: 'allow' for key in c.POLICY['dimensions']}
        self.assertEqual(c.decision(evidence), 'allow')
        for dimension in evidence:
            for bad in ('deny', 'missing', 'expired', 'contradictory', 'unsupported', None, True):
                with self.subTest(dimension=dimension, value=bad):
                    self.assertEqual(c.decision({**evidence, dimension: bad}), 'denied_or_not_found')
            incomplete = dict(evidence)
            del incomplete[dimension]
            self.assertEqual(c.decision(incomplete), 'denied_or_not_found')

    def test_hierarchy_role_and_ship_do_not_fill_evidence(self):
        for claimed in ({'role': 'organization_administrator'}, {'ship': '~zod'}, {'parent_team': 'owns-project'}, {}):
            self.assertEqual(c.decision(claimed), 'denied_or_not_found')

    def test_role_bundles_have_explicit_project_scope(self):
        for role in c.POLICY['role_bundles']:
            for operation in ('project.read', 'work.read', 'document.read', 'work.create', 'work.update', 'document.save'):
                kwargs = dict(project_scope_matches=True, organization_scope_matches=True,
                              explicit_project_membership=True)
                expected = role != 'reader' or operation.endswith('.read')
                self.assertEqual(c.role_allows(role, operation, **kwargs), expected)
                for missing in ('project_scope_matches', 'explicit_project_membership'):
                    self.assertFalse(c.role_allows(role, operation, **{**kwargs, missing: False}))

    def test_grant_and_revoke_cannot_escalate_role(self):
        for operation in ('policy.grant', 'policy.revoke'):
            for role in c.POLICY['role_bundles']:
                for affected in (*c.POLICY['role_bundles'], 'unknown', None):
                    allowed = c.role_allows(role, operation, project_scope_matches=True,
                                           organization_scope_matches=True,
                                           explicit_project_membership=True,
                                           affected_grant_role=affected)
                    expected = (role == 'maintainer' and affected in ('reader', 'contributor')) or (role == 'organization_administrator' and affected in ('reader', 'contributor', 'maintainer'))
                    self.assertEqual(allowed, expected, (role, operation, affected))

    def test_admin_grant_does_not_grant_content_access(self):
        kwargs = dict(project_scope_matches=True, organization_scope_matches=True)
        self.assertTrue(c.role_allows('organization_administrator', 'policy.grant', affected_grant_role='maintainer', **kwargs))
        self.assertFalse(c.role_allows('organization_administrator', 'document.read', **kwargs))
        self.assertFalse(c.role_allows('organization_administrator', 'project.create'))
        self.assertTrue(c.role_allows('organization_administrator', 'project.create', organization_scope_matches=True))
        self.assertFalse(c.role_allows('maintainer', 'project.create', organization_scope_matches=True))

    def test_project_grant_schema_cannot_create_org_administrator(self):
        request = {**self.request, 'operation': 'policy.grant', 'expected_revision': '1',
                   'resource_id': self.request['project_id'],
                   'payload': {'grant_id': self.request['request_id'], 'principal_id': self.request['resource_id'],
                               'role': 'organization_administrator', 'expires_at_ms': '1900000000000'}}
        self.rejected(request)
        request['payload']['role'] = 'maintainer'
        c.parse(json.dumps(request).encode())


if __name__ == '__main__':
    unittest.main()

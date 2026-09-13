"""Host-only integrity checks for the proposed independent native QA recipes.

These tests validate inputs and expected-value bookkeeping. They do not run a
ship, implement business authorization, or qualify a native acceptance result.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / 'specs/urbit/fixtures/native-cases.json'
CORPUS = json.loads(CORPUS_PATH.read_text())
FIXTURE = json.loads((ROOT / CORPUS['fixture_path']).read_text())
SPEC = importlib.util.spec_from_file_location('qa_frozen_contracts', ROOT / 'scripts/urbit/contracts.py')
CONTRACTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACTS)
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')


def wire_bytes(case):
    """Materialize explicit QA byte recipes, never expected business outcomes."""
    if 'raw_utf8' in case:
        return case['raw_utf8'].encode('utf-8')
    if 'raw_hex' in case:
        return bytes.fromhex(case['raw_hex'])
    if 'raw_recipe' in case:
        recipe = case['raw_recipe']
        return (recipe['prefix'] + recipe['append_utf8'] * recipe['repeat']).encode('utf-8')
    recipe = case['command_recipe']
    command = json.loads(json.dumps(CORPUS['commands'][recipe['base_command_ref']]))
    for pointer, value in recipe.get('replace', {}).items():
        target = command
        keys = pointer[1:].split('/')
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
    for pointer, value in recipe.get('repeat_string', {}).items():
        target = command
        keys = pointer[1:].split('/')
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value['value'] * value['repeat']
    return json.dumps(command, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def journey_cases():
    return (CORPUS['ordered_cases'] + CORPUS['real_expiry_continuation']['cases']
            + CORPUS['source_review_continuation']['cases']
            + CORPUS['separate_project_journal_lane']['cases'])


class ProposedNativeCasesIntegrity(unittest.TestCase):
    def test_inputs_bind_the_unchanged_contract_freeze(self):
        path = ROOT / CORPUS['contract_freeze']['path']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), CORPUS['contract_freeze']['sha256'])
        for filename, expected in json.loads(path.read_text())['files'].items():
            with self.subTest(filename=filename):
                self.assertEqual(hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(), expected)

    def test_fixed_identity_and_container_scope_is_preserved(self):
        ids = CORPUS['fixture_ids']
        self.assertEqual(ids['organization'], FIXTURE['organization_id'])
        self.assertEqual(ids['owning_team'], FIXTURE['owning_team_id'])
        self.assertEqual(CORPUS['principals'], {b['ship']: b['principal_id'] for b in FIXTURE['bindings']})
        self.assertEqual({ids['bus_container'], ids['zod_container']},
                         {c['container_id'] for c in FIXTURE['private_containers']})
        self.assertEqual({ids['project']}, {c['project_id'] for c in FIXTURE['private_containers']})
        for name, value in ids.items():
            with self.subTest(name=name):
                self.assertIsNotNone(UUID.fullmatch(value))
        self.assertEqual(len(set(ids.values())), len(ids))

    def test_literal_valid_commands_satisfy_frozen_host_profile(self):
        projects = {CORPUS['fixture_ids']['project'],
                    CORPUS['separate_project_journal_lane']['fixture_extension']['project_id']}
        for name, command in CORPUS['commands'].items():
            with self.subTest(command=name):
                raw = CONTRACTS.canonical(command)
                self.assertEqual(CONTRACTS.parse(raw), command)
                self.assertIsNotNone(UUID.fullmatch(command['request_id']))
                self.assertIn(command['project_id'], projects)
                if command['operation'] == 'policy.grant':
                    self.assertIn(command['payload']['principal_id'], CORPUS['principals'].values())

    def test_raw_codec_cases_match_the_frozen_host_oracle(self):
        vectors = CORPUS['codec_lane']['new_vectors']
        self.assertEqual(len({v['name'] for v in vectors}), len(vectors))
        for vector in vectors:
            with self.subTest(vector=vector['name']):
                raw = wire_bytes(vector)
                if vector['expected']['codec'] == 'reject':
                    with self.assertRaises(ValueError):
                        CONTRACTS.parse(raw)
                else:
                    expected = vector['expected']
                    self.assertEqual(CONTRACTS.parse(raw), expected['decoded_command'])
                    canonical = CONTRACTS.canonical(expected['decoded_command'])
                    self.assertEqual(canonical, expected['canonical_utf8'].encode('utf-8'))
                    self.assertEqual(hashlib.sha256(b'stead.command/1\0' + canonical).hexdigest(), expected['sha256'])

    def test_unicode_expectations_preserve_semantics_without_normalizing(self):
        vectors = {v['name']: v for v in CORPUS['codec_lane']['new_vectors']}
        for comparison in CORPUS['codec_lane']['pairwise_assertions']:
            if 'same_sha256' in comparison:
                left, right = comparison['same_sha256']
                self.assertEqual(vectors[left]['expected']['sha256'], vectors[right]['expected']['sha256'])
            else:
                left, right = comparison['different_sha256']
                self.assertNotEqual(vectors[left]['expected']['sha256'], vectors[right]['expected']['sha256'])
        literal = vectors['literal-backslash-u0000']['expected']['decoded_command']['payload']['description']
        self.assertIn('\\u0000', literal)
        self.assertNotIn('\0', literal)
        for name in ('escaped-nul-in-uuid', 'escaped-nul-in-key', 'escaped-nul-in-markdown'):
            self.assertIn(b'\\u0000', wire_bytes(vectors[name]))
        self.assertIn('\\u0070rotocol', vectors['duplicate-escaped-key']['raw_utf8'])
        canonical = vectors['short-controls-and-del-canonical']['expected']['canonical_utf8']
        self.assertIn('\\b\\f\\t\\n\\u0001\\u001f\x7f', canonical)

    def test_journey_references_and_explicit_acceptance_ledger_are_consistent(self):
        cases = journey_cases()
        names = [case['name'] for case in cases]
        self.assertEqual(len(names), len(set(names)))
        seen = set()
        accepted_sequences = {}
        policy_revisions = {}
        for case in cases:
            with self.subTest(case=case['name']):
                action, expected = case['action'], case['expected']
                if 'command_ref' in action:
                    self.assertIn(action['command_ref'], CORPUS['commands'])
                if 'sender' in action:
                    self.assertIn(action['sender'], CORPUS['principals'])
                if 'receipt_equal_to' in expected:
                    self.assertIn(expected['receipt_equal_to'], seen)
                    self.assertIn('no_business_change', expected['assertions'])
                if 'journal_sequence' in expected and action['kind'] == 'mutation':
                    command = CORPUS['commands'][action['command_ref']]
                    project = command['project_id']
                    accepted_sequences.setdefault(project, []).append(int(expected['journal_sequence']))
                    if command['operation'].startswith('policy.'):
                        policy_revisions.setdefault(project, []).append(int(expected['decision_policy_revision']))
                        self.assertEqual(expected['decision_policy_revision'], command['expected_revision'])
                        self.assertEqual(expected['resulting_policy_revision'], expected['resource_revision'])
                    elif command['operation'] == 'project.create':
                        self.assertEqual(expected['decision_policy_revision'], '0')
                        self.assertEqual(expected['resulting_policy_revision'], '1')
                if expected.get('result') == 'rejected':
                    self.assertIn('no_business_change', expected['assertions'])
                seen.add(case['name'])
        primary = CORPUS['fixture_ids']['project']
        secondary = CORPUS['separate_project_journal_lane']['fixture_extension']['project_id']
        self.assertEqual(accepted_sequences, {primary: list(range(1, 33)), secondary: [1]})
        self.assertEqual(policy_revisions, {primary: list(range(1, 20))})

    def test_review_regressions_preserve_the_rejected_state_and_privacy_gates(self):
        cases = {case['name']: case for case in journey_cases()}
        for name in (
            'revoked-creator-equal-retry-hides-receipt',
            'revoked-creator-mismatched-retry-hides-reuse',
            'revoked-creator-recovery-hides-receipt',
            'downgraded-reader-cannot-recover-write-receipt',
            'downgraded-owner-cannot-recover-document-save-receipt',
        ):
            with self.subTest(case=name):
                expected = cases[name]['expected']
                self.assertEqual(expected['error'], 'denied_or_not_found')
                self.assertIn('opaque_denial', expected['assertions'])
                self.assertIn('no_business_change', expected['assertions'])
        deadline = cases['short-maintainer-cannot-issue-longer-authority']
        self.assertEqual(deadline['expected']['error'], 'invalid_command')
        self.assertEqual(CORPUS['commands']['expiry_grant_short']['payload']['role'], 'maintainer')
        second_project = CORPUS['separate_project_journal_lane']
        self.assertIn('second_project_fixture_coordination', second_project['blocked_by'])
        for case in CORPUS['object_admission_lane']['cases']:
            expected = case['expected']
            if isinstance(expected, dict):
                self.assertIn('no_business_change', expected['assertions'])

    def test_proposal_does_not_masquerade_as_native_execution(self):
        self.assertEqual(CORPUS['test_owner'], '/root/qa_review')
        self.assertEqual(CORPUS['execution_status'], 'proposed_not_executed')
        self.assertEqual(CORPUS['native_results'], [])
        frozen_vectors = json.loads((ROOT / CORPUS['codec_lane']['frozen_positive_vectors']).read_text())
        self.assertEqual(len(frozen_vectors), CORPUS['codec_lane']['frozen_vector_count'])
        for case in CORPUS['codec_lane']['new_vectors']:
            self.assertEqual(case['native_execution_status'], 'not_executed')
        for case in journey_cases():
            if case['expected'].get('error') == 'UNSPECIFIED_AUTHORIZED_REJECTION':
                self.assertTrue(case.get('blocked_by'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

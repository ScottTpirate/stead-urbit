"""Mock-adapter tests for QA executor failure propagation, never native evidence."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('qa_core_cases', ROOT / 'scripts/urbit/core_cases.py')
EXECUTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXECUTOR)
CORPUS = json.loads((ROOT / 'specs/urbit/fixtures/native-cases.json').read_text())
CASES = {c['name']: c for c in CORPUS['ordered_cases']}


def subset(*names):
    return {'commands': copy.deepcopy(CORPUS['commands']), 'principals': CORPUS['principals'],
            'fixture_ids': CORPUS['fixture_ids'], 'ordered_cases': [copy.deepcopy(CASES[name]) for name in names]}


def outcome(value):
    return {'raw': EXECUTOR.canonical(value).decode(), 'json': copy.deepcopy(value),
            'native': {'classification': 'mock-only', 'delivery': {'facts': 1, 'kicks': 1,
                       'other_subscriber_content_facts': 0, 'ongoing_subscription': False}}}


def state(digit='0', **counts):
    return {'state_jam_sha256': digit * 64,
            'now_ms': '1900000000000',
            'counts': {'journal': 0, 'receipts': 0, 'objects': 0, 'object_bytes': 0,
                       'projects': 0, 'works': 0, 'documents': 0, 'grants': 0, **counts},
            'revisions': {}}


def created():
    command = CORPUS['commands']['project_create']
    record = {'protocol': 'stead.journal/1', 'sequence': '1', 'previous_digest': '0' * 64,
              'canonical_command': EXECUTOR.canonical(command).decode(),
              'principal_id': CORPUS['principals']['zod'], 'binding_id': EXECUTOR.BINDINGS['zod'],
              'authentication': 'fake-native/1', 'authentication_strength': 'synthetic-native-sender',
              'accepted_at_ms': '1900000000000', 'policy_revision': '0', 'authority_epoch': '1',
              'old_revision': '0', 'new_revision': '1', 'git_commit_oid': ''}
    journal = EXECUTOR.canonical(record).decode()
    digest = hashlib.sha256(b'stead.journal/1\0' + journal.encode()).hexdigest()
    receipt = {'protocol': 'stead.receipt/1', 'status': 'accepted',
               'request_id': command['request_id'], 'canonical_sha256': EXECUTOR.command_digest(EXECUTOR.canonical(command)),
               'project_id': command['project_id'], 'resource_id': command['resource_id'],
               'resource_revision': '1', 'authority_epoch': '1', 'policy_revision': '0',
               'journal_sequence': '1', 'journal_digest': digest, 'principal_id': CORPUS['principals']['zod'],
               'binding_id': EXECUTOR.BINDINGS['zod'], 'authentication': 'fake-native/1',
               'authentication_strength': 'synthetic-native-sender', 'accepted_at_ms': '1900000000000',
               'git_commit_oid': ''}
    after = state('1', journal=1, receipts=1, projects=1, grants=1)
    after['last_journal_record'], after['last_journal_digest'] = journal, digest
    after['revisions'] = {command['project_id']: '1', command['project_id'] + '/' + command['project_id']: '1'}
    return outcome(receipt), after


class ScriptedMockAdapter:
    """Canned transport/state pairs; deliberately contains no policy implementation."""
    def __init__(self, *steps):
        self.steps = list(steps)
        self.state = state()
        self.calls = []

    def call(self, ship, mode, route='/', raw=b''):
        self.calls.append((ship, mode, route, raw))
        response, after = self.steps.pop(0)
        if isinstance(response, Exception):
            raise response
        if after is not None:
            self.state = copy.deepcopy(after)
        return copy.deepcopy(response)

    def snapshot(self):
        return copy.deepcopy(self.state)


def execute(corpus, adapter, **options):
    return EXECUTOR.run(corpus, adapter.call, adapter.snapshot,
                        classification='host-mocked-executor-only', **options)


def git_fixture():
    """Tiny manufactured objects solely for testing verifier rejection logic."""
    ref = 'document_a_1'
    command = CORPUS['commands'][ref]
    name = command['resource_id'] + '.md'
    objects = {}
    def obj(kind, body):
        oid = hashlib.sha1(f'{kind} {len(body)}\0'.encode() + body).hexdigest()
        objects[oid] = {'kind': kind, 'byte_length': len(body), 'hex': body.hex()}
        return oid
    body = command['payload']['markdown'].encode()
    blob = obj('blob', body)
    tree = obj('tree', b'100644 ' + name.encode() + b'\0' + bytes.fromhex(blob))
    head = obj('commit', f'tree {tree}\nauthor Mock <mock@invalid> 1 +0000\ncommitter Mock <mock@invalid> 1 +0000\n\nMock\n'.encode())
    return {'snapshot_commit_oid': head, 'objects': objects,
            'files': {name: {'oid': blob, 'hex': body.hex()}},
            'fsck': {'argv': ['git', '-C', '/mock-disposable', 'fsck', '--full', '--strict'], 'returncode': 0},
            'max_response_bytes': 1234, 'native': [{'classification': 'mock-only'}]}


class CoreCasesMockTests(unittest.TestCase):
    def test_serializer_matches_all_six_frozen_vectors(self):
        vectors = json.loads((ROOT / 'specs/urbit/fixtures/commands.json').read_text())
        self.assertEqual(len(vectors), 6)
        for vector in vectors:
            with self.subTest(vector=vector['name']):
                raw = EXECUTOR.canonical(vector['request'])
                self.assertEqual(raw.decode(), vector['canonical_utf8'])
                self.assertEqual(EXECUTOR.command_digest(raw), vector['sha256'])

    def test_exact_denial_and_unchanged_state_pass_mock_scope(self):
        adapter = ScriptedMockAdapter((outcome(EXECUTOR.DENIAL), None))
        report = execute(subset('nonadministrator-cannot-create'), adapter)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['classification'], 'host-mocked-executor-only')
        ship, mode, route, raw = adapter.calls[0]
        self.assertEqual((ship, mode), ('bus', 'command'))
        self.assertIn('/~bus/' + EXECUTOR.BINDINGS['bus'] + '/', route)
        self.assertTrue(route.endswith(EXECUTOR.command_digest(raw)))

    def test_nack_or_ack_without_result_fails_and_aborts_dependent_cases(self):
        no_result = {'raw': None, 'json': None, 'native': {'classification': 'mock-nack'}}
        adapter = ScriptedMockAdapter((no_result, None))
        report = execute(subset('nonadministrator-cannot-create', 'create-project'), adapter)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['case_counts'], {'failed': 1, 'not_run': 1})
        self.assertEqual(len(adapter.calls), 1)

    def test_raw_json_disagreement_and_duplicate_keys_cannot_pass(self):
        for raw, parsed in ((EXECUTOR.canonical(EXECUTOR.DENIAL).decode(), {'status': 'accepted'}),
                            ('{"protocol":"stead.result/1","status":"rejected","status":"rejected","error":"denied_or_not_found"}', EXECUTOR.DENIAL)):
            with self.subTest(raw=raw):
                result = {'raw': raw, 'json': parsed, 'native': {}}
                report = execute(subset('nonadministrator-cannot-create'), ScriptedMockAdapter((result, None)))
                self.assertEqual(report['status'], 'failed')

    def test_denial_cannot_disclose_extra_metadata(self):
        response = outcome(dict(EXECUTOR.DENIAL, resource_revision='2'))
        report = execute(subset('nonadministrator-cannot-create'), ScriptedMockAdapter((response, None)))
        self.assertEqual(report['status'], 'failed')

    def test_rejected_write_cannot_change_hash_or_counts(self):
        for after in (state('1'), state(receipts=1)):
            with self.subTest(after=after):
                report = execute(subset('nonadministrator-cannot-create'), ScriptedMockAdapter((outcome(EXECUTOR.DENIAL), after)))
                self.assertEqual(report['status'], 'failed')
                self.assertIn('no-business-change', report['cases'][0]['error'])

    def test_accepted_receipt_and_duplicate_preserve_original_exact_bytes(self):
        receipt, after = created()
        adapter = ScriptedMockAdapter((receipt, after), (receipt, None))
        report = execute(subset('create-project', 'duplicate-project-create'), adapter)
        self.assertEqual(report['status'], 'passed', report['cases'])
        self.assertEqual(report['case_counts'], {'passed': 2})
        self.assertTrue(any(c['name'] == 'journal-exact-context-and-project-chain' for c in report['checks']))

    def test_wrong_principal_revision_digest_or_policy_fails(self):
        for field, value in (('principal_id', CORPUS['principals']['bus']), ('resource_revision', '2'),
                             ('canonical_sha256', '0' * 64), ('policy_revision', '1')):
            with self.subTest(field=field):
                receipt, after = created()
                changed = dict(receipt['json'], **{field: value})
                report = execute(subset('create-project'), ScriptedMockAdapter((outcome(changed), after)))
                self.assertEqual(report['status'], 'failed')

    def test_duplicate_timestamp_refresh_is_not_a_duplicate_pass(self):
        receipt, after = created()
        changed = outcome(dict(receipt['json'], accepted_at_ms='1900000000001'))
        report = execute(subset('create-project', 'duplicate-project-create'),
                         ScriptedMockAdapter((receipt, after), (changed, None)))
        self.assertEqual(report['case_counts'], {'passed': 1, 'failed': 1})

    def test_accepted_receipt_without_one_journal_and_receipt_fails(self):
        receipt, after = created()
        after['counts']['receipts'] = 2
        report = execute(subset('create-project'), ScriptedMockAdapter((receipt, after)))
        self.assertEqual(report['status'], 'failed')
        self.assertIn('one-journal-and-receipt', report['cases'][0]['error'])

    def test_missing_clock_skips_whole_dependent_mutation_continuations(self):
        corpus = subset('nonadministrator-cannot-create')
        corpus['real_expiry_continuation'] = CORPUS['real_expiry_continuation']
        corpus['source_review_continuation'] = CORPUS['source_review_continuation']
        adapter = ScriptedMockAdapter((outcome(EXECUTOR.DENIAL), None))
        report = execute(corpus, adapter)
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['case_counts'], {'passed': 1, 'not_run': 27})
        self.assertEqual(len(adapter.calls), 1)

    def test_missing_delivery_evidence_is_visible_incomplete(self):
        response = outcome(EXECUTOR.DENIAL)
        response['native'] = {'classification': 'mock-without-delivery-counters'}
        adapter = ScriptedMockAdapter((response, None), (response, None))
        report = execute(subset('empty-project-known-unknown'), adapter)
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['check_counts']['skipped'], 2)

    def test_empty_corpus_and_harness_exception_cannot_pass(self):
        self.assertEqual(execute(subset(), ScriptedMockAdapter())['status'], 'incomplete')
        report = execute(subset('create-project'), ScriptedMockAdapter((TimeoutError('mock transport timeout'), None)))
        self.assertEqual(report['status'], 'failed')
        self.assertIn('TimeoutError', report['cases'][0]['error'])

    def test_export_verifier_accepts_git_prefix_but_rejects_tamper_and_extra_objects(self):
        def verify(evidence):
            runner = EXECUTOR.Runner(subset(), None, None)
            runner.current = {'name': 'mock-export-verifier', 'checks': []}
            runner.materialized(evidence, ['document_a_1'])
        verify(git_fixture())
        damaged = git_fixture()
        oid = next(iter(damaged['objects']))
        damaged['objects'][oid]['hex'] = '00'
        with self.assertRaises(EXECUTOR.CaseFailure):
            verify(damaged)
        extra = git_fixture()
        body = b'unreachable other-container synthetic bytes'
        oid = hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest()
        extra['objects'][oid] = {'kind': 'blob', 'byte_length': len(body), 'hex': body.hex()}
        with self.assertRaises(EXECUTOR.CaseFailure):
            verify(extra)
        wrong_fsck = git_fixture()
        wrong_fsck['fsck']['argv'][-1] = '--connectivity-only'
        with self.assertRaises(EXECUTOR.CaseFailure):
            verify(wrong_fsck)


if __name__ == '__main__':
    unittest.main(verbosity=2)

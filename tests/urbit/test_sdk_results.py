"""Synthetic corrupted-reply controls; these are not native SDK observations."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('sdk_results', ROOT / 'scripts/sdk_native/results.py')
RESULTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESULTS)
PREFIX = '019939ba-4000-7000-8000-'


class SDKResultTests(unittest.TestCase):
    def command(self):
        request = {'protocol': 'stead.command/3', 'request_id': PREFIX + '000000000001',
            'project_id': PREFIX + '000000000002', 'resource_id': PREFIX + '000000000003',
            'operation': 'work.create', 'expected_revision': '0', 'authority_epoch': '1', 'payload': {}}
        reply = {key: request[key] for key in ('request_id', 'project_id', 'resource_id', 'operation', 'authority_epoch')}
        reply.update(protocol='stead.receipt/3', status='accepted', canonical_sha256=hashlib.sha256(
            ('stead.command/3\0' + RESULTS.canonical(request)).encode()).hexdigest(), resource_kind='work',
            resource_revision='1', container_id='', git_commit_oid='', principal_id=PREFIX + f'{102:012x}',
            binding_id=PREFIX + f'{202:012x}', binding_revision='1', identity_ship='~bus',
            authentication='native-sender/1', authentication_strength='native-sender', session_audit_id='',
            runtime='isolated-fake', accepted_at_ms='1000')
        return request, reply

    def test_valid_native_receipt(self):
        request, reply = self.command()
        RESULTS.validate('command', request, reply)

    def test_distinct_control_member_receipt(self):
        request, reply = self.command()
        reply.update(principal_id=PREFIX + f'{104:012x}', binding_id=PREFIX + f'{204:012x}', identity_ship='~nec')
        RESULTS.validate('command', request, reply, '~nec')
        with self.assertRaises(ValueError):
            RESULTS.validate('command', request, reply, '~bus')

    def test_home_cannot_be_validated_as_a_member(self):
        request, reply = self.command()
        for actor in ('~zod', '~bud', ''):
            with self.subTest(actor=actor), self.assertRaises(ValueError):
                RESULTS.validate('command', request, reply, actor)

    def test_receipt_wrong_correlation_identity_scope_revision_and_extra_fields(self):
        request, reply = self.command()
        for field in ('request_id', 'canonical_sha256', 'project_id', 'resource_id', 'operation', 'authority_epoch',
                      'resource_revision', 'principal_id', 'binding_id', 'binding_revision', 'identity_ship',
                      'authentication', 'authentication_strength', 'session_audit_id', 'runtime', 'git_commit_oid', 'extra'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                RESULTS.validate('command', request, reply | {field: 'wrong'})

    def test_receipt_missing_fields_and_invalid_times(self):
        request, reply = self.command()
        for field in reply:
            altered = reply.copy(); altered.pop(field)
            with self.subTest(field=field), self.assertRaises((ValueError, KeyError)):
                RESULTS.validate('command', request, altered)
        for when in ('0', '01', '-1', str(2**64), 1000):
            with self.subTest(when=when), self.assertRaises(ValueError):
                RESULTS.validate('command', request, reply | {'accepted_at_ms': when})

    def test_rejection_requires_original_digest_and_request(self):
        request, accepted = self.command()
        reply = {'protocol': 'stead.result/3', 'status': 'rejected', 'error': 'revision_conflict',
                 'request_id': request['request_id'], 'canonical_sha256': accepted['canonical_sha256']}
        RESULTS.validate('command', request, reply)
        for field in ('request_id', 'canonical_sha256'):
            with self.assertRaises(ValueError):
                RESULTS.validate('command', request, reply | {field: 'wrong'})
        for field in ('request_id', 'canonical_sha256'):
            altered = reply.copy(); altered.pop(field)
            with self.assertRaises(ValueError):
                RESULTS.validate('command', request, altered)

    def test_sdk_unconfirmed_is_a_closed_transport_outcome(self):
        reply = {'protocol': 'stead.sdk-error/1', 'status': 'failed', 'error': 'request_unconfirmed'}
        RESULTS.validate('command', '{', reply)
        with self.assertRaises(ValueError):
            RESULTS.validate('command', '{', reply | {'accepted': 'yes'})

    def update(self):
        request = {'action': 'poll', 'request_id': 'request', 'watch_id': 'a'*64, 'cursor': 'b'*64}
        reply = {'protocol': 'stead.update-result/3', 'status': 'updated', 'request_id': 'request',
                 'watch_id': 'a'*64, 'cursor': 'c'*64, 'generation': 'd'*64,
                 'rows': {'0': {'sequence': '1', 'generation': 'd'*64}}}
        return request, reply

    def test_valid_update_and_content_free_terminal(self):
        request, reply = self.update()
        RESULTS.validate('updates', request, reply)
        RESULTS.validate('updates', request, reply | {'status': 'refresh_required', 'cursor': '', 'generation': '', 'rows': {}})

    def test_canonical_sixteen_row_reply_uses_numeric_sequence_order(self):
        request, reply = self.update()
        reply['rows'] = {str(i): {'sequence': str(i + 1), 'generation': 'd'*64} for i in range(16)}
        canonical_reply = json.loads(RESULTS.canonical(reply))
        self.assertEqual(list(canonical_reply['rows'])[:4], ['0', '1', '10', '11'])
        RESULTS.validate('updates', request, canonical_reply)

    def test_update_correlation_rotation_order_and_private_payload(self):
        request, reply = self.update()
        alterations = [{'request_id': 'wrong'}, {'watch_id': 'f'*64}, {'cursor': request['cursor']},
            {'rows': {'0': {'sequence': '1', 'generation': 'd'*64, 'markdown': 'private'}}},
            {'rows': {'1': {'sequence': '1', 'generation': 'd'*64}}},
            {'rows': {'0': {'sequence': '1', 'generation': 'd'*64}, '1': {'sequence': '3', 'generation': 'd'*64}}},
            {'generation': 'e'*64}, {'extra': 'body'}]
        for alteration in alterations:
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                RESULTS.validate('updates', request, reply | alteration)
        with self.assertRaises(ValueError):
            RESULTS.validate('updates', request, reply | {'status': 'refresh_required'})

    def test_query_correlation_and_closed_work_rows(self):
        request = {'request_id': 'r', 'kind': 'work', 'project_id': 'p', 'container_id': '', 'resource_id': ''}
        reply = {**request, 'protocol': 'stead.query-result/3', 'status': 'read', 'authority_epoch': '1',
                 'generation': 'a'*64, 'cursor': '', 'rows': {}}
        RESULTS.validate('query', request, reply)
        for alteration in ({'project_id': 'wrong'}, {'request_id': 'wrong'}, {'extra': 'body'},
                           {'rows': {'opaque': {'markdown': 'private'}}}):
            with self.assertRaises(ValueError):
                RESULTS.validate('query', request, reply | alteration)


if __name__ == '__main__':
    unittest.main()

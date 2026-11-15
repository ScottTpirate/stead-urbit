"""Agent handoff binds fresh private scope to an exact native proposal request."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import agent_proposal as agent


def uid(number):
    return '019939ba-4000-7000-8000-' + str(number).zfill(12)


class AgentProposalTests(unittest.TestCase):
    def setUp(self):
        self.project, self.work, self.grant = uid(30), uid(31), uid(32)
        self.origin = 'https://home.localhost:8443'
        self.credentials = {'origin': self.origin, 'principal_id': uid(80)}
        self.person = {'principal_id': uid(80), 'identity_ship': '~nec', 'binding_id': uid(81),
                       'binding_revision': '1', 'session_audit_id': 'a' * 64, 'display_name': 'Worker',
                       'organization_id': uid(1), 'team_id': uid(2), 'home': '~zod', 'can_create': 'no'}
        self.ticket = {'resource_id': self.work, 'kind': 'work', 'resource_revision': '4',
                       'title': 'Add a fixture example', 'description': 'Show one unit test.'}
        self.saved = {'delegation_id': self.grant, 'worker_ship': '~nec', 'ref': 'refs/heads/main',
                      'expires_at_ms': '1800000000000', 'status': 'active', 'proposals': '{}', 'can_revoke': 'no'}
        self.brief = {'protocol': 'stead.agent-brief/1', 'project_id': self.project, 'work_id': self.work,
                      'delegation_id': self.grant, 'worker_ship': '~nec', 'target_ref': self.saved['ref'],
                      'expires_at_ms': self.saved['expires_at_ms'], 'work_revision': '4', 'title': 'Edited local text',
                      'description': 'Edited local description', 'work_url': f'{self.origin}/stead/#work/{self.project}/{self.work}'}
        self.read = Mock()
        self.read.one.side_effect = lambda kind, *args, **kwargs: (('1', 'b' * 64), self.person if kind == 'identity' else self.ticket)
        self.code = Mock(side_effect=self.home_code)
        self.submitted = None
        self.bad_readback = False

    def home_code(self, project, operation, **fields):
        self.assertEqual(project, self.project)
        response = {'protocol': 'stead.code/1'}
        if operation == 'work-delegations':
            self.assertEqual(fields, {'work_id': self.work})
            return response | {'status': 'work-delegations', 'work_id': self.work,
                               'rows': json.dumps({self.grant: self.saved})}
        if operation == 'submit':
            self.assertEqual(fields, {'proposal_id': self.grant, 'revision': '1', 'work_id': self.work,
                                      'ref': 'refs/heads/main', 'base_oid': 'b' * 40, 'head_oid': 'c' * 40,
                                      'delegation_id': self.grant})
            self.submitted = dict(fields)
            return response | {'status': 'accepted'}
        self.assertEqual(operation, 'proposal')
        self.assertEqual(fields, {'proposal_id': self.grant, 'revision': '1'})
        return response | self.submitted | {'status': 'proposal',
                                             'author': uid(99) if self.bad_readback else self.person['principal_id']}

    def handoff(self):
        return agent.propose(self.brief, self.credentials, self.read, self.code, revision='1', base='b' * 40, head='c' * 40)

    def test_reads_exact_current_ticket_then_submits_and_confirms(self):
        checked = agent.context(self.brief, self.credentials, self.read, self.code)
        self.assertEqual(checked['description'], self.ticket['description'])
        self.assertEqual(self.handoff()['status'], 'submitted-for-review')
        self.assertEqual([c.args[1] for c in self.code.call_args_list], ['work-delegations', 'work-delegations', 'submit', 'proposal'])

    def test_revoked_worker_and_changed_work_prevent_submission(self):
        for change, reset in ((lambda: self.saved.update(status='revoked'), lambda: self.saved.update(status='active')),
                              (lambda: self.ticket.update(resource_revision='5'), lambda: self.ticket.update(resource_revision='4')),
                              (lambda: self.person.update(identity_ship='~bus'), lambda: self.person.update(identity_ship='~nec'))):
            change()
            with self.assertRaises(agent.RecoveryError):
                self.handoff()
            reset()
        self.assertIsNone(self.submitted)

    def test_uncorrelated_readback_is_not_reported_as_submitted(self):
        self.bad_readback = True
        with self.assertRaisesRegex(agent.RecoveryError, 'agent-proposal-readback'):
            self.handoff()
        self.assertIsNotNone(self.submitted)

    def contract_brief(self):
        self.ticket.update(execution_contract_protocol='stead.work-contract/1',
                           execution_contract_revision='2', execution_contract_digest='a' * 64)
        self.brief.pop('work_revision')
        self.brief.update(protocol='stead.agent-brief/2', execution_contract_revision='2',
                          execution_contract_digest='a' * 64)

    def test_contract_brief_survives_comment_and_metadata_revisions(self):
        self.contract_brief()
        self.ticket.update(resource_revision='19', status='done', priority='high',
                           comment_count='8', assignee_principal_id=uid(90))
        checked = agent.context(self.brief, self.credentials, self.read, self.code)
        self.assertEqual(checked['title'], self.ticket['title'])
        self.assertEqual(checked['description'], self.ticket['description'])
        self.assertEqual(self.handoff()['status'], 'submitted-for-review')

    def test_contract_brief_requires_current_exact_pin_and_capability(self):
        self.contract_brief()
        for field, changed in (('execution_contract_revision', '3'),
                               ('execution_contract_digest', 'b' * 64),
                               ('execution_contract_protocol', 'stead.work-contract/2')):
            with self.subTest(field=field):
                original = self.ticket[field]
                self.ticket[field] = changed
                with self.assertRaisesRegex(agent.RecoveryError, 'agent-work-contract-changed'):
                    self.handoff()
                self.ticket[field] = original
        self.ticket.pop('execution_contract_revision')
        with self.assertRaisesRegex(agent.RecoveryError, 'agent-work-contract-changed'):
            self.handoff()
        self.assertIsNone(self.submitted)

    def test_contract_brief_remains_scoped_to_work_actor_and_delegation(self):
        self.contract_brief()
        for row, field, changed in ((self.ticket, 'resource_id', uid(99)),
                                    (self.saved, 'status', 'revoked'),
                                    (self.saved, 'ref', 'refs/heads/other'),
                                    (self.person, 'identity_ship', '~bus')):
            with self.subTest(field=field):
                original = row[field]
                row[field] = changed
                with self.assertRaises(agent.RecoveryError):
                    self.handoff()
                row[field] = original
        self.assertIsNone(self.submitted)

    def test_contract_brief_refuses_malformed_pins_and_mixed_versions(self):
        self.contract_brief()
        for field, changed in (('execution_contract_revision', '02'),
                               ('execution_contract_revision', '0'),
                               ('execution_contract_digest', 'A' * 64),
                               ('execution_contract_digest', 'a' * 63),
                               ('protocol', 'stead.agent-brief/3')):
            with self.subTest(field=field):
                original = self.brief[field]
                self.brief[field] = changed
                with self.assertRaises(agent.RecoveryError):
                    self.handoff()
                self.brief[field] = original
        self.brief['work_revision'] = '4'
        with self.assertRaisesRegex(agent.RecoveryError, 'record-shape'):
            self.handoff()
        self.assertEqual(self.read.one.call_count, 0)
        self.assertEqual(self.code.call_count, 0)

    def test_legacy_brief_keeps_aggregate_revision_even_with_contract_fields(self):
        self.ticket.update(execution_contract_protocol='stead.work-contract/1',
                           execution_contract_revision='2', execution_contract_digest='a' * 64,
                           resource_revision='5')
        with self.assertRaisesRegex(agent.RecoveryError, 'agent-work-revision-changed'):
            self.handoff()
        self.assertIsNone(self.submitted)


if __name__ == '__main__':
    unittest.main()

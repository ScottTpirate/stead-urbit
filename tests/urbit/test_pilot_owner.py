import base64
import hashlib
import stat
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import pilot_owner
from test_project_migration import command, event, uid


HOME = '~sampel-palnet'
ORIGIN = 'https://home.example.test'
INCARNATION = 'c' * 64
CERTIFICATE = 'd' * 64


class OwnerExchange:
    pid = 42

    def __init__(self, **changes):
        self.calls = []
        self.booted = False
        self.changes = changes

    def tls(self, host, port, digest):
        self.calls.append(('tls', host, port, digest))

    def call(self, ship, mode, nonce, value):
        self.calls.append((mode, ship, nonce, value))
        if mode == 'operator-status':
            return dict(protocol='stead.operator-status/1', home=ship, nonce=nonce,
                        origin=ORIGIN, custody='operator-pilot', runtime='live-synthetic',
                        config_revision='1', runtime_matches='yes', projection_ready='yes',
                        available='yes' if self.booted else 'no',
                        incarnation=INCARNATION if self.booted else '') | self.changes
        self.booted = True
        return dict(protocol='stead.bootstrap/2', status='ready', home=ship, nonce=nonce,
                    incarnation=INCARNATION, runtime='live-synthetic', config_revision='1')


class PilotAdmission(unittest.TestCase):
    def bootstrap(self, owner, **extra):
        return pilot_owner.bootstrap(owner, HOME, '1', origin=ORIGIN, port=8443,
                                     certificate=CERTIFICATE, **extra)

    def test_live_bootstrap_correlates_readiness_and_uses_same_listener(self):
        owner = OwnerExchange()
        self.assertEqual(self.bootstrap(owner), {'home': HOME, 'pid': 42, 'runtime': 'live-synthetic',
                                                  'config_revision': '1', 'incarnation': INCARNATION})
        self.assertEqual([row[0] for row in owner.calls],
                         ['operator-status', 'tls', 'bootstrap', 'operator-status', 'tls'])
        command = owner.calls[2]
        self.assertEqual(command[3], {'protocol': 'stead.bootstrap/2', 'nonce': command[2], 'expected_revision': '1'})
        self.assertEqual(len({owner.calls[i][2] for i in (0, 2, 3)}), 3)
        self.assertEqual(owner.calls[1], ('tls', 'home.example.test', 8443, CERTIFICATE))
        self.assertEqual(owner.calls[1], owner.calls[4])

    def test_wrong_profile_revision_origin_or_already_available_never_bootstraps(self):
        for changes in ({'runtime': 'isolated-fake'}, {'runtime_matches': 'no'}, {'config_revision': '2'},
                        {'origin': 'https://other.example.test'}, {'nonce': 'f' * 64},
                        {'available': 'yes', 'incarnation': INCARNATION}):
            with self.subTest(changes=changes):
                owner = OwnerExchange(**changes)
                with self.assertRaises(ValueError):
                    self.bootstrap(owner)
                self.assertEqual([row[0] for row in owner.calls], ['operator-status'])

    def test_reused_incarnation_never_passes(self):
        with self.assertRaisesRegex(ValueError, 'acknowledgement did not match'):
            self.bootstrap(OwnerExchange(), previous=INCARNATION)


class PilotHandoff(unittest.TestCase):
    def test_transitions_require_current_phase_and_followup_status(self):
        opened = {'protocol': 'stead.home-handoff/1', 'home': HOME, 'phase': 'open', 'generation': '1'}
        sealed = opened | {'phase': 'sealed', 'generation': '2'}
        for op, before, after in (('seal', opened, sealed), ('activate', sealed, sealed | {'phase': 'open'})):
            with self.subTest(operation=op):
                owner = Mock()
                owner.call.side_effect = [before, {}, after]
                self.assertEqual(pilot_owner.change_handoff(owner, HOME, op, before['generation'], INCARNATION), after)
                self.assertEqual([item.args[1] for item in owner.call.call_args_list], ['handoff-status', 'handoff', 'handoff-status'])
                self.assertEqual(owner.call.call_args_list[1].args[3]['generation'], before['generation'])

    def test_uncertain_ack_stops_and_stale_generation_does_not_send(self):
        opened = {'protocol': 'stead.home-handoff/1', 'home': HOME, 'phase': 'open', 'generation': '1'}
        owner = Mock()
        owner.call.return_value = opened
        with self.assertRaisesRegex(ValueError, 'generation changed'):
            pilot_owner.change_handoff(owner, HOME, 'seal', '2', INCARNATION)
        owner.call.assert_called_once_with(HOME, 'handoff-status', '', None)
        owner.call.reset_mock(side_effect=True)
        owner.call.side_effect = [opened, TimeoutError()]
        with self.assertRaisesRegex(ValueError, 'Read handoff-status'):
            pilot_owner.change_handoff(owner, HOME, 'seal', '1', INCARNATION)
        self.assertEqual(owner.call.call_count, 2)

    def test_activation_ticket_requires_private_unlinked_regular_file(self):
        with tempfile.TemporaryDirectory() as path:
            ticket = Path(path) / 'ticket'
            ticket.write_text(INCARNATION + '\n')
            ticket.chmod(0o600)
            self.assertEqual(pilot_owner.read_handoff_ticket(ticket), INCARNATION)
            ticket.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'mode 0600'):
                pilot_owner.read_handoff_ticket(ticket)
            alias = ticket.with_name('alias')
            alias.symlink_to(ticket)
            with self.assertRaises(OSError):
                pilot_owner.read_handoff_ticket(alias)


class ProjectRetirement(unittest.TestCase):
    def test_owner_compares_project_head_and_reconciles_identical_retry(self):
        project = '019939ba-4000-7000-8000-000000000001'
        migration = '019939ba-4000-7000-8000-000000000002'
        active = {'protocol': 'stead.project-retirement-status/1', 'home': HOME, 'project_id': project,
                  'authority_epoch': '1', 'journal_head': 'a' * 64, 'writer_state': 'active'}
        intent = {'protocol': 'stead.project-retire/1', 'project_id': project, 'migration_id': migration,
                  'authority_epoch': '1', 'expected_journal_head': 'a' * 64, 'destination_home': '~bus'}
        retired = active | {'writer_state': 'retired', 'migration_id': migration,
                            'destination_home': '~bus', 'retired_at_ms': '5'}
        owner = Mock()
        owner.call.return_value = active
        with self.assertRaisesRegex(ValueError, 'journal head changed'):
            pilot_owner.retire_project(owner, HOME, intent | {'expected_journal_head': 'b' * 64})
        owner.call.assert_called_once_with(HOME, 'project-retirement-status', project, None)
        owner.call.reset_mock()
        owner.call.side_effect = [active, {}, retired, retired]
        self.assertEqual(pilot_owner.retire_project(owner, HOME, intent), retired)
        self.assertEqual(pilot_owner.retire_project(owner, HOME, intent), retired)
        self.assertEqual([item.args[1] for item in owner.call.call_args_list],
                         ['project-retirement-status', 'project-retire', 'project-retirement-status', 'project-retirement-status'])


class FrozenJournalExport(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.destination = Path(temporary.name) / 'journal.ndjson'
        migration = pilot_owner.project_migration
        create = command('project.create', 7, 1, {'organization_id': uid(3), 'owning_team_id': uid(4),
                         'title': 'Migration fixture', 'project_key': 'FIX', 'preset': 'general'})
        first = migration.canonical(event(1, '0' * 64, create))
        work = command('work.create', 8, 9, {'title': 'Test Unicode and split records', 'description': 'Ñ\nℤ',
                       'type': 'task', 'status': 'backlog', 'priority': 'medium'})
        second = migration.canonical(event(2, migration.domain_hash(migration.JOURNAL, first), work))
        self.raw = first + b'\n' + second + b'\n'
        head = migration.domain_hash(migration.JOURNAL, second)
        self.intent = {'protocol': 'stead.project-retire/1', 'project_id': uid(1), 'migration_id': uid(10),
                       'authority_epoch': '1', 'destination_home': '~bus', 'expected_journal_head': head}
        self.scope = {'home': '~zod', 'project_id': uid(1), 'migration_id': uid(10),
                      'authority_epoch': '1', 'destination_home': '~bus', 'journal_head': head}
        self.status = self.scope | {'protocol': 'stead.project-retirement-status/1',
                                    'writer_state': 'retired', 'retired_at_ms': '1900000000100'}
        self.owner = Mock()
        self.observations = [self.status, self.status]
        self.page_changes = {}
        self.owner.call.side_effect = self.call

    def call(self, ship, mode, route, value):
        self.assertEqual(ship, '~zod')
        if mode == 'project-retirement-status':
            self.assertEqual((route, value), (uid(1), None))
            return self.observations.pop(0)
        self.assertEqual((mode, value), ('project-journal-page', self.intent))
        offset = int(route)
        end = offset + pilot_owner.JOURNAL_PAGE_BYTES
        return self.scope | {'protocol': 'stead.project-journal-page/1', 'journal_count': '2', 'offset': route,
                             'done': 'yes' if end >= len(self.raw) else 'no',
                             'data_base64': base64.b64encode(self.raw[offset:end]).decode()} | self.page_changes

    def export(self):
        with patch.object(pilot_owner, 'JOURNAL_PAGE_BYTES', 1024):
            return pilot_owner.export_project_journal(self.owner, '~zod', self.intent, self.destination)

    def test_exports_exact_oldest_first_bytes_with_private_atomic_publication(self):
        result = self.export()
        self.assertEqual(result['journal_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(result['journal_head'], self.scope['journal_head'])
        self.assertEqual(result['journal_count'], '2')
        self.assertEqual(self.destination.read_bytes(), self.raw)
        self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode), 0o600)
        self.assertEqual(self.destination.stat().st_nlink, 1)
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])
        self.assertGreater(self.owner.call.call_count, 3)

    def test_mismatched_scope_or_changed_retirement_cannot_publish_partial_file(self):
        self.page_changes = {'destination_home': '~bud'}
        with self.assertRaisesRegex(ValueError, 'Unexpected frozen project journal page'):
            self.export()
        self.assertEqual(list(self.destination.parent.iterdir()), [])
        self.page_changes = {}
        self.observations = [self.status, self.status | {'retired_at_ms': '1900000000101'}]
        with self.assertRaisesRegex(ValueError, 'retirement observation changed'):
            self.export()
        self.assertEqual(list(self.destination.parent.iterdir()), [])

    def test_truncated_chain_cannot_publish_even_with_an_orderly_last_page(self):
        self.raw = self.raw.splitlines(keepends=True)[0]
        with self.assertRaisesRegex(ValueError, 'journal-tip-mismatch'):
            self.export()
        self.assertEqual(list(self.destination.parent.iterdir()), [])

    def test_unretired_source_and_existing_output_are_untouched(self):
        self.observations = [{key: value for key, value in self.status.items()
                              if key not in {'migration_id', 'destination_home', 'retired_at_ms'}}
                             | {'writer_state': 'active'}]
        with self.assertRaisesRegex(ValueError, 'Project must be retired'):
            self.export()
        self.owner.call.assert_called_once()
        self.observations = [self.status]
        self.destination.write_bytes(b'existing')
        with self.assertRaisesRegex(ValueError, 'output already exists'):
            self.export()
        self.assertEqual(self.destination.read_bytes(), b'existing')


if __name__ == '__main__':
    unittest.main()

import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import pilot_owner


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


if __name__ == '__main__':
    unittest.main()

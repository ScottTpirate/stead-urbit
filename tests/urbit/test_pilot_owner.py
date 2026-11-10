import sys
from pathlib import Path
import unittest

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


if __name__ == '__main__':
    unittest.main()

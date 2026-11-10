"""Host routing of disposable team and pilot Khan calls."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import team_conn


class TeamConnTests(unittest.TestCase):
    def test_historic_bootstrap_and_pilot_use_separate_drivers(self):
        with patch.object(team_conn.core_conn, 'exchange') as exchange:
            team_conn.run('vere', '/pier/.urb/conn.sock', 'bootstrap', target='zod')
            team_conn.run('vere', '/pier/.urb/conn.sock', 'handoff-status', '/home-handoff/status')
            team_conn.run('vere', '/pier/.urb/conn.sock', 'operator-status', '/operator/nonce')
            team_conn.run('vere', '/pier/.urb/conn.sock', 'handoff', raw=b'{}')
        nouns = [call.args[2] for call in exchange.call_args_list]
        self.assertIn('%stead-team-client %noun', nouns[0])
        self.assertTrue(all('%stead-pilot-check %noun' in noun for noun in nouns[1:]))

    def test_pilot_mode_cannot_target_identity(self):
        with patch.object(team_conn.core_conn, 'exchange') as exchange:
            with self.assertRaisesRegex(ValueError, 'operation/app mismatch'):
                team_conn.run('vere', '/pier/.urb/conn.sock', 'handoff-status', app='stead-identity')
            exchange.assert_not_called()

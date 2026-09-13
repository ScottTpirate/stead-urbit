"""Host framing regressions; these do not substitute for native execution."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import core_conn


class CoreConnectionTests(unittest.TestCase):
    def wrap(self, raw):
        return "[32 %avow 0 %noun %stead-core-result '" + raw.hex() + "']"

    def test_exact_json_bytes_survive_hoon_renderer_heuristics(self):
        raw = json.dumps({'markdown': 'quote " \\ newline\n café 🛰', 'empty': ''}, ensure_ascii=False).encode()
        result = core_conn.parse_response(self.wrap(raw))
        self.assertEqual(result['raw'].encode(), raw)
        self.assertEqual(result['json'], json.loads(raw))

    def test_nack_or_bare_ack_cannot_become_acceptance(self):
        self.assertIsNone(core_conn.parse_response('[32 %avow 1]'))
        for value in ('>=', '[32 %avow 0]', '[32 %avow 0 %noun %stead-core-result 0x7b7d]',
                      self.wrap(b'{}') + self.wrap(b'{}')):
            with self.assertRaises(ValueError):
                core_conn.parse_response(value)

    def test_malformed_result_never_becomes_business_json(self):
        for raw in (b'{"status":"accepted","status":"rejected"}', b'[]', b'\xff', b'{}\0', b'{} {}'):
            with self.assertRaises((ValueError, UnicodeError)):
                core_conn.parse_response(self.wrap(raw))

    def test_cord_and_path_limits_fail_before_executing_runtime(self):
        with patch.object(core_conn.subprocess, 'run') as process:
            for kwargs in ({'raw': b'{}\0'}, {'raw': b'x' * 70001},
                           {'route': "/v1/' injected"}, {'route': '/' + 'x' * 1024}):
                with self.assertRaises(ValueError):
                    core_conn.run('/unused', '/unused', 'poke', **kwargs)
            process.assert_not_called()

"""Synthetic public-query admission controls; no native execution."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import team_check


class CapabilitiesTests(unittest.TestCase):
    def setUp(self):
        self.request = '019939ba-4000-7000-8000-000000000001'
        self.row = {'protocol': 'stead.capabilities/3', 'profile': 'configured-team',
                    'commands': 'stead.command/3', 'queries': 'stead.query/3',
                    'updates': 'stead.updates/3', 'authentication': 'native-sender/1',
                    'max_request_bytes': '65536', 'max_response_bytes': '262144',
                    'page_size': '20', 'runtime': 'isolated-fake'}
        self.value = {'protocol': 'stead.query-result/3', 'status': 'read',
                      'request_id': self.request, 'kind': 'capabilities',
                      'project_id': '', 'container_id': '', 'resource_id': '',
                      'authority_epoch': '0', 'generation': 'opaque-generation',
                      'cursor': '', 'rows': {'0': self.row}}

    def test_opaque_row_keys_do_not_define_the_payload(self):
        for key in ('0', 'capabilities', 'opaque-row-key'):
            with self.subTest(key=key):
                self.assertTrue(team_check.capabilities_match(
                    self.value | {'rows': {key: self.row}}, self.request))

    def test_missing_duplicate_and_malformed_rows_are_refused(self):
        for rows in (None, [], {}, {'0': self.row, '1': self.row}, {'0': 'capabilities'}):
            with self.subTest(rows=rows):
                self.assertFalse(team_check.capabilities_match(self.value | {'rows': rows}, self.request))
        for value in (None, [], {}, {k: v for k, v in self.value.items() if k != 'rows'}):
            self.assertFalse(team_check.capabilities_match(value, self.request))

    def test_every_declared_capability_is_required_and_exact(self):
        for key in self.row:
            for changed in ({k: v for k, v in self.row.items() if k != key},
                            self.row | {key: 'wrong-or-unsupported'}):
                with self.subTest(key=key, changed=changed):
                    self.assertFalse(team_check.capabilities_match(
                        self.value | {'rows': {'0': changed}}, self.request))
        self.assertFalse(team_check.capabilities_match(
            self.value | {'rows': {'0': self.row | {'unexpected': 'field'}}}, self.request))

    def test_response_must_correlate_to_the_current_metadata_query(self):
        for key in self.value.keys() - {'rows', 'generation'}:
            value = copy.deepcopy(self.value)
            value[key] = 'wrong-query-or-rejected-result'
            with self.subTest(key=key):
                self.assertFalse(team_check.capabilities_match(value, self.request))
        for generation in ('', None, 1):
            self.assertFalse(team_check.capabilities_match(
                self.value | {'generation': generation}, self.request))


if __name__ == '__main__':
    unittest.main()

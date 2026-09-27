"""Adversarial authored records: host-checker regressions, not native execution.

The production Gall observer is not modified. Its event serials are global to
all probes, so gaps within one probe are valid; timestamps on different ships
are not used as a global ordering proof.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery_cases as D
import test_delivery_cases as F


class DeliveryEvidenceRegressionTests(unittest.TestCase):
    def test_request_probe_identity_is_required(self):
        for value in ('missing', None, ''):
            with self.subTest(value=value):
                trace = F.trace()
                if value == 'missing':
                    trace['request'].pop('probe_id')
                else:
                    trace['request']['probe_id'] = value
                with self.assertRaises(D.ObservationError):
                    D.verify_one_shot(trace, F.RAW)

    def test_request_route_is_required(self):
        for value in ('missing', None, ''):
            with self.subTest(value=value):
                trace = F.trace()
                if value == 'missing':
                    trace['request'].pop('route')
                else:
                    trace['request']['route'] = value
                with self.assertRaises(D.ObservationError):
                    D.verify_one_shot(trace, F.RAW)

    def test_request_envelope_must_be_an_object(self):
        for value in (None, [], 'bus'):
            with self.subTest(value=value):
                trace = F.trace()
                trace['request'] = value
                with self.assertRaises(D.ObservationError):
                    D.verify_one_shot(trace, F.RAW)

    def test_reserved_sentinel_requires_complete_route(self):
        original = F.trace()['sentinels'][0]['before']['json']['route']
        variants = ['/v2/result/~bud/', original + '/extra',
                    original.replace(F.PROJECT, 'not-a-project'),
                    original[:-64] + 'not-a-digest']
        for route in variants:
            with self.subTest(route=route):
                trace = F.trace()
                sentinel = trace['sentinels'][0]
                obj = copy.deepcopy(sentinel['before']['json'])
                obj['route'] = route
                sentinel['before'] = F.wrap(obj)
                sentinel['after'] = F.wrap(obj)
                with self.assertRaises(D.ObservationError):
                    D.verify_one_shot(trace, F.RAW)

    def test_sentinel_cannot_have_requested_leave(self):
        for when in ('before', 'after'):
            with self.subTest(when=when):
                trace = F.trace()
                sentinel = trace['sentinels'][0]
                obj = copy.deepcopy(sentinel[when]['json'])
                obj['leave_requested'] = 'true'
                sentinel[when] = F.wrap(obj)
                with self.assertRaises(D.ObservationError):
                    D.verify_one_shot(trace, F.RAW)

    def test_sentinel_after_snapshot_must_still_be_active(self):
        for field, value in (('closed', 'true'), ('watch_requested', 'false')):
            with self.subTest(field=field):
                trace = F.trace()
                sentinel = trace['sentinels'][0]
                obj = copy.deepcopy(sentinel['after']['json'])
                obj[field] = value
                sentinel['after'] = F.wrap(obj)
                with self.assertRaises(D.ObservationError):
                    D.verify_one_shot(trace, F.RAW)

    def test_read_only_proof_cannot_include_poke_work(self):
        trace = F.trace()
        obj = copy.deepcopy(trace['response']['json'])
        obj['pokes_requested'] = '1'
        obj['poke_acks'] = '1'
        obj['events']['4'] = F.event('poke-ack', serial=4)
        obj['events']['4']['after_terminal'] = 'true'
        trace['response'] = F.wrap(obj)
        with self.assertRaises(D.ObservationError):
            D.verify_one_shot(trace, F.RAW)

    def test_terminal_marker_cannot_reverse_after_kick(self):
        obj = F.record(('fact', 'kick', 'watch-ack'))['json']
        # The native observer latched closed at kick. The late ACK must say so.
        with self.assertRaises(D.ObservationError):
            D.observation(F.wrap(obj))

    def test_correct_late_ack_after_kick_remains_valid(self):
        trace = F.trace()
        obj = F.record(('fact', 'kick', 'watch-ack'))['json']
        obj['events']['3']['after_terminal'] = 'true'
        trace['response'] = F.wrap(obj)
        self.assertEqual(D.verify_one_shot(trace, F.RAW)['status'], 'passed')

    def test_global_event_serial_gaps_are_valid(self):
        trace = F.trace()
        obj = copy.deepcopy(trace['response']['json'])
        obj['events'] = {str(serial): event for serial, event in
                         zip((7, 42, 100), obj['events'].values())}
        trace['response'] = F.wrap(obj)
        self.assertEqual(D.verify_one_shot(trace, F.RAW)['status'], 'passed')

    def test_different_ship_clock_order_is_not_assumed(self):
        trace = F.trace()
        sentinel = trace['sentinels'][0]
        obj = copy.deepcopy(sentinel['before']['json'])
        obj['events']['1']['observed_at_ms'] = '1900000099999'
        sentinel['before'] = F.wrap(obj)
        sentinel['after'] = F.wrap(obj)
        self.assertEqual(D.verify_one_shot(trace, F.RAW)['status'], 'passed')


if __name__ == '__main__':
    unittest.main(verbosity=2)

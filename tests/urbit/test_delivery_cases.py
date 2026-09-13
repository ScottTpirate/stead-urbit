"""Authored observer/event records exercise host verification only, never Gall."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import delivery_cases as D

PROBE = '019939ba-4000-7000-8000-000000008001'
SENTINEL = '019939ba-4000-7000-8000-000000008002'
PROJECT = '019939ba-4000-7000-8000-000000000001'
ROUTE = '/v2/project/' + PROJECT
RAW = json.dumps({'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'})


def event(kind, probe=PROBE, serial=1):
    fact = kind == 'fact'
    return {'kind': kind, 'source_ship': '~zod', 'peer_agent': 'stead-home',
            'peer_agent_basis': 'fixed issued Gall wire; sign has no agent field',
            'wire': f"/probe/{probe}/{'poke' if kind.startswith('poke-') else 'watch'}",
            'mark': 'stead-result-2' if fact else '', 'payload_bytes': str(len(RAW.encode())) if fact else '0',
            'payload_sha256': hashlib.sha256(RAW.encode()).hexdigest() if fact else '',
            'source_provenance_sha256': 'c' * 64, 'observed_at_ms': str(1900000000000 + serial),
            'after_terminal': 'false'}


def record(kinds=('watch-ack', 'fact', 'kick'), *, probe=PROBE, route=ROUTE, open_watch=False):
    obj = {'protocol': 'stead.observer/1', 'id': probe, 'status': 'observed', 'fault': '', 'route': route,
           'watch_requested': 'true', 'leave_requested': 'false', 'closed': 'false' if open_watch else 'true',
           'ongoing_subscription': 'true' if open_watch else 'false', 'facts': str(kinds.count('fact')),
           'kicks': str(kinds.count('kick')), 'watch_acks': str(kinds.count('watch-ack')), 'watch_nacks': '0',
           'poke_acks': '0', 'poke_nacks': '0', 'pokes_requested': '0',
           'events': {str(i): event(kind, probe, i) for i, kind in enumerate(kinds, 1)}}
    return wrap(obj)


def wrap(obj):
    return {'raw': json.dumps(obj, sort_keys=True, separators=(',', ':')), 'json': copy.deepcopy(obj),
            'native': {'fixture': 'AUTHORED MOCK native-call-shaped record, not execution'}}


def trace():
    sentinel = record(('watch-ack',), probe=SENTINEL,
                      route=f'/v2/result/~bud/019939ba-4000-7000-8000-000000000204/{PROJECT}/{SENTINEL}/' + 'a' * 64,
                      open_watch=True)
    return {'classification': 'real-native-observer', 'request': {'ship': 'bus', 'probe_id': PROBE, 'route': ROUTE},
            'response': record(), 'sentinels': [{'ship': 'bud', 'before': sentinel, 'after': copy.deepcopy(sentinel)}],
            'runtime_errors': [], 'runtime_log_evidence':[
                {'ship':ship,'path':'mock-only/'+ship+'.log','start':0,'end':0,'sha256':hashlib.sha256(b'').hexdigest()}
                for ship in D.FAKES]}


def receipt():
    value = {'protocol': 'stead.receipt/2', 'status': 'accepted', 'request_id': PROBE,
             'canonical_sha256': 'a' * 64, 'project_id': PROJECT, 'resource_id': SENTINEL,
             'resource_kind': 'work', 'container_id': '', 'resource_revision': '1', 'authority_epoch': '1',
             'principal_id': '019939ba-4000-7000-8000-000000000102',
             'binding_id': '019939ba-4000-7000-8000-000000000202', 'authentication': 'fake-native/1',
             'authentication_strength': 'synthetic-native-sender', 'accepted_at_ms': '1900000000000', 'git_commit_oid': ''}
    correlation = {k: value[k] for k in ('request_id', 'canonical_sha256', 'project_id', 'resource_id', 'resource_kind', 'container_id')}
    return json.dumps(value), correlation


class DeliveryEvidenceHostTests(unittest.TestCase):
    def test_well_formed_authored_trace_verifies_shape_only(self):
        result = D.verify_one_shot(trace(), RAW, ship='bus', route=ROUTE)
        self.assertEqual(result['event_count'], 3)
        self.assertEqual(result['foreign_sentinels'], 1)

    def test_old_host_constants_cannot_stand_in_for_native_events(self):
        old = {'facts': 1, 'kicks': 1, 'other_subscriber_content_facts': 0, 'ongoing_subscription': False}
        with self.assertRaises(D.ObservationError):
            D.verify_one_shot(old, RAW)

    def test_fault_wrong_lane_mark_source_digest_and_terminal_fact_fail(self):
        def alter(field, value):
            t = trace();obj = t['response']['json'];obj['events']['2'][field] = value;t['response'] = wrap(obj);return t
        for field, value in (('wire', f'/probe/{PROBE}/poke'), ('mark', 'unknown-result'),
                             ('source_ship', '~bud'), ('payload_sha256', '0' * 64), ('after_terminal', 'true')):
            with self.subTest(field=field), self.assertRaises(D.ObservationError):
                D.verify_one_shot(alter(field, value), RAW)
        t = trace();obj = t['response']['json'];obj['fault'] = 'invalid fact';t['response'] = wrap(obj)
        with self.assertRaises(D.ObservationError): D.verify_one_shot(t, RAW)

    def test_counter_without_event_and_multiple_facts_fail(self):
        t = trace();obj=t['response']['json'];obj['facts']='2';t['response']=wrap(obj)
        with self.assertRaises(D.ObservationError): D.verify_one_shot(t, RAW)
        t=trace();t['response']=record(('watch-ack','fact','fact','kick'))
        with self.assertRaises(D.ObservationError): D.verify_one_shot(t, RAW)

    def test_foreign_leak_or_unacknowledged_subscriber_fails(self):
        t=trace();other=t['sentinels'][0];before=other['before']['json']
        other['after']=record(('watch-ack','fact'),probe=SENTINEL,route=before['route'],open_watch=True)
        with self.assertRaises(D.ObservationError): D.verify_one_shot(t, RAW)
        for key in ('ongoing_subscription', 'watch_requested'):
            t=trace();obj=t['sentinels'][0]['before']['json'];obj[key]='false';t['sentinels'][0]['before']=wrap(obj)
            with self.subTest(key=key),self.assertRaises(D.ObservationError): D.verify_one_shot(t, RAW)

    def test_missing_raw_query_runtime_errors_and_sentinel_fail(self):
        for change in ('native','raw','sentinels','runtime_errors'):
            t=trace()
            if change in ('native','raw'):t['response'].pop(change)
            else:t.pop(change)
            with self.subTest(change=change),self.assertRaises(D.ObservationError): D.verify_one_shot(t, RAW)
        t=trace();t['runtime_errors']=['mark conversion failed before on-agent']
        with self.assertRaises(D.ObservationError): D.verify_one_shot(t, RAW)

    def test_held_same_path_sentinel_needs_owner_control_record(self):
        t=trace();other=t['sentinels'][0]
        other['before']=record(('watch-ack',),probe=SENTINEL,route=ROUTE,open_watch=True)
        other['after']=copy.deepcopy(other['before'])
        with self.assertRaises(D.ObservationError): D.verify_one_shot(t,RAW)
        other['held_control']={'operation':'hold-outsider-read','ship':'bud','route':ROUTE,'native':{'mock':True}}
        self.assertEqual(D.verify_one_shot(t,RAW)['status'],'passed')

    def test_fact_ack_kick_host_permutations_require_exact_receipt(self):
        raw,correlation=receipt()
        for kinds in (('fact','ack','kick'),('ack','fact','kick'),('fact','kick','ack')):
            events=[{'kind':k,**({'raw':raw} if k=='fact' else {})} for k in kinds]
            with self.subTest(kinds=kinds): self.assertEqual(D.transport_outcome(events,expected_request=correlation),{'status':'accepted','saved':True})

    def test_ack_nack_timeout_partial_missing_and_duplicate_never_saved(self):
        raw,correlation=receipt()
        cases=[[],[{'kind':'ack'}],[{'kind':'nack'}],[{'kind':'timeout'}],
               [{'kind':'ack'},{'kind':'kick'}],[{'kind':'fact','raw':'{"status":"accepted"}'}],
               [{'kind':'fact','raw':raw[:-1]}],[{'kind':'fact','raw':raw},{'kind':'fact','raw':raw}],
               [{'kind':'cancel'},{'kind':'fact','raw':raw}]]
        for events in cases:
            with self.subTest(events=events): self.assertFalse(D.transport_outcome(events,expected_request=correlation)['saved'])
        for expected in (None,{},dict(correlation,request_id=SENTINEL)):
            with self.subTest(expected=expected):self.assertFalse(D.transport_outcome([{'kind':'fact','raw':raw}],expected_request=expected)['saved'])

    def test_owner_control_is_bounded_and_cannot_return_business_acceptance(self):
        calls=[]
        def call(*args,**kwargs):calls.append((args,kwargs));return {'transport':'mock ACK only'}
        observer=D.Observer(call,lambda seconds:None)
        self.assertEqual(observer.control('bus','watch',PROBE,route=ROUTE),{'transport':'mock ACK only'})
        sent=json.loads(calls[0][1]['raw']);self.assertEqual(set(sent),{'action','id','target','route','raw'})
        with self.assertRaises(D.ObservationError):observer.control('ship-owner','watch',PROBE,route=ROUTE)
        with self.assertRaises(D.ObservationError):observer.wait_for('bus',PROBE,lambda obj:False,attempts=0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

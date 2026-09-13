"""Delivery schedule safety/adapter tests, no native or lifecycle execution."""
from __future__ import annotations

import copy
import errno
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/urbit'))
import delivery_suite as S
import delivery_cases as D
from test_delivery_cases import record,RAW,ROUTE,wrap

CORPUS=json.loads((ROOT/'specs/urbit/fixtures/native-cases-v2.json').read_bytes())


def pending(counts=None,ducts='1'):
    counts=counts or dict.fromkeys(D.FAKES,0);entries={}
    for ship,count in counts.items():
        for index in range(count):
            request=f'019939ba-4000-7000-8000-{0x9000+index:012x}'
            route=S.result_route(ship,CORPUS['fixture_ids']['project'],request,'a'*64)
            entries[route]={'sender':'~'+ship,'expires_at_ms':'1900000060000','incoming_ducts':ducts}
    return wrap({'protocol':'stead.fixture-pending/1','now_ms':'1900000000000','total':str(len(entries)),
                 'by_ship':{ship:str(value) for ship,value in counts.items()},'entries':entries})


class DeliveryScheduleHostTests(unittest.TestCase):
    def test_absent_native_callbacks_keep_all8_cases_unrun_and_failed(self):
        report=S.run(CORPUS)
        self.assertEqual(report['status'],'failed');self.assertFalse(report['native_qualified'])
        self.assertEqual([case['name'] for case in report['cases']],list(S.CASE_NAMES))
        self.assertTrue(all(case['status']=='not_run' and not case['assertions'] for case in report['cases']))
        self.assertEqual(report['calls'],[])

    def test_partial_callbacks_do_not_begin_native_mutations(self):
        def forbidden(*args,**kwargs):self.fail('Partial adapter must not execute')
        report=S.run(CORPUS,forbidden,provenance={'mock':True},snapshot=forbidden)
        self.assertFalse(report['native_qualified']);self.assertTrue(all(case['status']=='not_run' for case in report['cases']))

    def test_pending64_actual_ducts_and_per_sender_counts(self):
        value=S.pending_value(pending(dict.fromkeys(D.FAKES,16)))
        self.assertEqual(value['total'],'64')
        for altered in (pending(dict.fromkeys(D.FAKES,17)),pending(dict.fromkeys(D.FAKES,1),ducts='0')):
            with self.assertRaises(D.ObservationError):S.pending_value(altered)
        altered=pending(dict.fromkeys(D.FAKES,1));value=altered['json'];value['by_ship']['bus']='0'
        with self.assertRaises(D.ObservationError):S.pending_value(wrap(value))

    def test_pending_snapshot_cannot_hide_wrong_sender_or_native_record(self):
        altered=pending(dict.fromkeys(D.FAKES,1));value=altered['json'];next(iter(value['entries'].values()))['sender']='~outsider'
        with self.assertRaises(D.ObservationError):S.pending_value(wrap(value))
        altered=pending();altered['native']={}
        with self.assertRaises(D.ObservationError):S.pending_value(altered)

    def test_probe_pool_never_reuses_or_exceeds80(self):
        pool=S.ProbePool();ids=[pool.allocate('bus') for _ in range(80)]
        self.assertEqual(len(set(ids)),80)
        with self.assertRaises(D.ObservationError):pool.allocate('bus')
        self.assertNotEqual(pool.foreign('bus'),'bus')

    def test_missing_real_log_adapter_refuses_before_any_observer_action(self):
        called=[];adapter=S.ReadObserver(lambda *a,**k:called.append(a),lambda delay:None,None)
        with self.assertRaises(D.ObservationError):adapter.delivery_evidence('mock','bus',ROUTE,{'raw':RAW})
        self.assertEqual(called,[])

    def test_read_pair_records_actual_trace_shape_and_cancels_foreign_probe(self):
        calls=[];logcalls=[];pool=S.ProbePool(0x7fff)
        sentinel='019939ba-4000-7000-8000-000000008000';owner='019939ba-4000-7000-8000-000000008001'
        reserved=S.result_route('bud',CORPUS['fixture_ids']['project'],sentinel,'a'*64)
        before=record(('watch-ack',),probe=sentinel,route=reserved,open_watch=True)
        done=record(probe=owner,route=ROUTE)
        gone=copy.deepcopy(before);gone['json']['ongoing_subscription']='false';gone=wrap(gone['json'])
        class MockObserver:
            waits=[before,done,gone]
            def control(self,*args,**kwargs):calls.append((args,kwargs));return {'ACK':'mock control only'}
            def wait_for(self,ship,probe,predicate):
                value=self.waits.pop(0)
                if not predicate(value['json']):raise AssertionError('Canned observation does not meet requested predicate')
                return {'final':value}
            def read(self,*args):return copy.deepcopy(before)
        def logs(cursor=None):
            logcalls.append(cursor)
            if cursor is None:return {'cursor':'mock-cursor','errors':[],'segments':[]}
            return {'errors':[],'segments':[{'ship':ship,'path':'mock-only/'+ship+'.log','start':0,'end':0,
                    'sha256':hashlib.sha256(b'').hexdigest()}for ship in D.FAKES]}
        adapter=S.ReadObserver(None,lambda delay:None,logs,probe_pool=pool);adapter.observer=MockObserver()
        trace=adapter.delivery_evidence('mock','bus',ROUTE,{'raw':RAW})
        self.assertEqual(trace['request']['probe_id'],owner)
        self.assertEqual(calls[-1][0],('bud','leave',sentinel));self.assertEqual(logcalls,[None,'mock-cursor'])

    def test_call_requires_frame_and_consistent_json_before_qualifying_native(self):
        for response in ({'raw':None,'json':None}, {'raw':'{}','json':{},'native':{}},
                         {'raw':'{"status":"no","status":"accepted"}','json':{'status':'accepted'},'native':{'response_frame_sha256':'a'*64}}):
            suite=S.Suite(CORPUS,lambda *a,**k:response,classification='real-native-fake-ships')
            with self.subTest(response=response),self.assertRaises(D.ObservationError):suite.call('bus','read',route=ROUTE,raw=b'')

    def test_bad_evidence_sink_reference_is_not_silent_transcript_loss(self):
        result={'raw':'{}','json':{},'native':{'mock':True}}
        suite=S.Suite(CORPUS,lambda *a,**k:result,sink=lambda row:{'sha256':'unverified'})
        with self.assertRaises(D.ObservationError):suite.call('bus','observe',raw=b'{}')

    def test_unavailable_home_does_not_green_adapter_programming_errors(self):
        def check(error,allowed):
            suite=S.Suite(CORPUS);suite.current={'name':'mock-unavailable','assertions':[]}
            suite.snap=lambda:{'state_jam_sha256':'a'*64};suite.same=lambda before:before
            def lifecycle(attempt):
                def bounded(*args,**kwargs):raise error
                return {'native':{'mock':True},'old_pid':101,'old_exit':0,'replacement_pid':102,'attempt':attempt(bounded)}
            suite.unavailable_home=lifecycle
            if allowed:
                suite.unavailable();self.assertTrue(all(x['status']=='passed' for x in suite.current['assertions']))
            else:
                with self.assertRaises(type(error)):suite.unavailable()
        for error in (ValueError('bad fixture'),AssertionError('adapter defect'),FileNotFoundError('missing executable')):
            with self.subTest(error=error):check(error,False)
        check(TimeoutError('mock bounded native timeout'),True)
        check(OSError(errno.EHOSTUNREACH,'mock route unavailable'),True)


if __name__=='__main__':
    unittest.main(verbosity=2)

"""Bounded, injected native delivery recipes. No lifecycle or native import work.

ReadObserver pairs a normal authorized read with the same path observed by a
distinct native duct. It compares exact response hashes and a foreign active
sentinel, and retains actual all-ship log deltas. This is not observation of the
normal client's own duct. The source is uncompiled/unexecuted until the common
guard permits a coordinated native run.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import errno
import hashlib
import json
import threading
import time

import core_cases_v2 as C
import delivery_cases as D

CASE_NAMES = ('known-mark-and-held-outsider', 'wrong-sender-and-binding',
              'missing-channel-and-wrong-digest', 'leave-and-fresh-retry',
              'lazy-expiry-and-same-path-retirement', 'pending-quotas',
              'home-unavailable', 'ended-leave-attempt')


class ProbePool:
    def __init__(self, start=0x9000):
        self.next_id, self.counts = start, dict.fromkeys(sorted(D.FAKES), 0)
        self.lock = threading.Lock()

    def allocate(self, ship):
        with self.lock:
            D.require(ship in self.counts and self.counts[ship] < 80, 'Observer80-probe bound; no reset/truncation')
            self.counts[ship] += 1
            self.next_id += 1
            D.require(self.next_id < 2**48, 'Probe ID range')
            return f'019939ba-4000-7000-8000-{self.next_id:012x}'

    def foreign(self, ship):
        with self.lock:
            return min((other for other in self.counts if other != ship), key=lambda other:(self.counts[other],other))


def result_route(ship, project, request, digest):
    return f'/v2/result/~{ship}/{C.BINDINGS[ship]}/{project}/{request}/{digest}'


def command_route(ship, command, digest=None):
    return result_route(ship,command['project_id'],command['request_id'],digest or C.command_digest(C.canonical(command)))


def receipt_route(command):
    container = command['payload'].get('container_id',command['project_id'])
    return f"/v2/receipt/{command['project_id']}/{container}/{command['resource_id']}/{command['operation']}/{command['request_id']}"


def correlated(command, ship):
    kind='policy' if command['operation'].startswith('policy.') else command['operation'].split('.')[0]
    return {'request_id':command['request_id'],'canonical_sha256':C.command_digest(C.canonical(command)),
            'project_id':command['project_id'],'resource_id':command['resource_id'],'resource_kind':kind,
            'container_id':command['payload'].get('container_id',''),'binding_id':C.BINDINGS[ship]}


class ReadObserver:
    def __init__(self, call, pause, runtime_errors, *, probe_pool=None):
        self.call, self.runtime_errors = call, runtime_errors
        self.pool = probe_pool or ProbePool()
        self.observer = D.Observer(call,pause)

    def delivery_evidence(self, case, ship, route, result):
        D.require(ship in D.FAKES and isinstance(route,str) and route.startswith('/v2/'),
                  'Exact actor/route required for observed read')
        D.require(callable(self.runtime_errors), 'Actual runtime log delta adapter required')
        begin=self.runtime_errors()
        D.require(isinstance(begin,dict) and 'cursor' in begin, 'Runtime log starting cursor missing')
        project=route.split('/')[3]
        other=self.pool.foreign(ship)
        sentinel=self.pool.allocate(other);probe=self.pool.allocate(ship)
        reserved=result_route(other,project,sentinel,'a'*64)
        self.observer.control(other,'watch',sentinel,route=reserved)
        before=self.observer.wait_for(other,sentinel,
            lambda obj:obj['ongoing_subscription']=='true' and obj['watch_acks']=='1')['final']
        try:
            self.observer.control(ship,'watch',probe,route=route)
            response=self.observer.wait_for(ship,probe,
                lambda obj:obj['closed']=='true' and obj['facts']=='1' and obj['kicks']=='1')['final']
            after=self.observer.read(other,sentinel)
            logs=self.runtime_errors(begin['cursor'])
            D.require(isinstance(logs,dict),'Actual runtime log end cursor missing')
            trace={'classification':'real-native-observer','request':{'ship':ship,'probe_id':probe,'route':route},
                   'response':response,'sentinels':[{'ship':other,'before':before,'after':after}],
                   'runtime_errors':logs.get('errors'),'runtime_log_evidence':logs.get('segments'),
                   'scope':'Paired read-only request on same authoritative path, not the ordinary client duct',
                   'case':case}
            D.verify_one_shot(trace,result['raw'],ship=ship,route=route)
            return trace
        finally:
            self.observer.control(other,'leave',sentinel)
            self.observer.wait_for(other,sentinel,lambda obj:obj['ongoing_subscription']=='false')

    def observe_read(self, ship, route):
        result=copy.deepcopy(self.call(ship,'read',route=route,raw=b''))
        trace=self.delivery_evidence('paired-observed-read',ship,route,result)
        D.require(isinstance(result.get('native'),dict),'Ordinary native read record missing')
        result['native']['delivery']=trace
        return result


def pending_value(result):
    """Owner-only snapshot counts actual incoming Gall ducts, not inferred rows."""
    D.require(isinstance(result,dict) and bool(result.get('native')),'Native pending snapshot evidence missing')
    raw=result.get('raw')
    D.require(isinstance(raw,str) and 0<len(raw.encode())<=262144,'Pending snapshot response bound')
    value=json.loads(raw,object_pairs_hook=D.unique)
    D.require(value==result.get('json') and set(value)=={'protocol','now_ms','total','by_ship','entries'},'Pending snapshot envelope')
    D.require(value['protocol']=='stead.fixture-pending/1','Pending snapshot protocol')
    D.number(value['now_ms'])
    D.require(set(value['by_ship'])==D.FAKES and isinstance(value['entries'],dict),'Pending snapshot maps')
    counts=dict.fromkeys(D.FAKES,0)
    for route,item in value['entries'].items():
        D.require(isinstance(route,str) and route.startswith('/v2/result/') and set(item)=={'sender','expires_at_ms','incoming_ducts'},'Pending row envelope')
        ship=item['sender'].removeprefix('~');D.require(ship in D.FAKES,'Pending sender')
        D.require(route.startswith(f'/v2/result/~{ship}/'),'Pending path/sender mismatch')
        D.number(item['expires_at_ms']);ducts=D.number(item['incoming_ducts'])
        D.require(ducts>0,'Stored pending reservation has no live recipient')
        counts[ship]+=1
    D.require(D.number(value['total'])==len(value['entries'])<=64,'Pending total bound')
    D.require(all(D.number(value['by_ship'][ship])==count<=16 for ship,count in counts.items()),'Pending sender count/bound')
    return value


class Suite:
    def __init__(self, corpus, call=None, *, snapshot=None, pending_snapshot=None, control=None,
                 trusted_now_ms=None, wait_until=None, unavailable_home=None, pause=None,
                 runtime_errors=None, provenance=None, classification='unexecuted', probe_pool=None, sink=None):
        self.corpus,self.base_call,self.snapshot=corpus,call,snapshot
        self.pending_snapshot,self.control_callback=pending_snapshot,control
        self.trusted_now_ms,self.wait_until=trusted_now_ms,wait_until
        self.unavailable_home,self.pause,self.runtime_errors=unavailable_home,pause,runtime_errors
        self.pool=probe_pool or ProbePool(0xa000)
        self.observer=D.Observer(self.call,pause)
        self.sink,self.record_bytes,self.record_lock=sink,0,threading.Lock()
        self.report={'protocol':'stead.delivery-suite/2','status':'failed','native_qualified':False,
                     'classification':classification,'provenance':provenance,'test_owner':'/root/qa_review',
                     'cases':[],'calls':[],'not_qualified':['Abrupt crash','Arbitrary marks/raw peer input history',
                     'Live/browser sessions','Injected late network leave after its original Gall duct has ended']}
        self.current=None
        self.command=copy.deepcopy(corpus['commands']['document_b_2'])
        self.old_completed=None

    def check(self,name,condition,detail=None):
        row={'name':name,'status':'passed' if condition else 'failed'}
        if detail is not None:row['detail']=detail
        self.current['assertions'].append(row)
        D.require(condition,name)

    def call(self,*args,**kwargs):
        result=self.base_call(*args,**kwargs)
        D.require(isinstance(result,dict) and {'raw','json','native'}<=result.keys(),'Native callback outcome record missing')
        if result['json'] is not None:
            D.require(isinstance(result['raw'],str) and 0<len(result['raw'].encode())<=262144
                      and json.loads(result['raw'],object_pairs_hook=D.unique)==result['json'],'Invalid native result bytes')
        if self.report['classification']=='real-native-fake-ships':
            native=result.get('native')
            D.require(isinstance(native,dict) and isinstance(native.get('response_frame_sha256'),str)
                      and bool(C.HEX64.fullmatch(native['response_frame_sha256'])),'Actual native terminal frame digest missing')
        record={'args':list(args),'kwargs':{k:v.hex() if isinstance(v,bytes) else v for k,v in kwargs.items()},'result':result}
        raw=json.dumps(record,sort_keys=True,separators=(',',':')).encode()
        with self.record_lock:
            if self.sink:
                kept=self.sink(record)
                D.require(isinstance(kept,dict) and isinstance(kept.get('sha256'),str)
                          and bool(C.HEX64.fullmatch(kept['sha256'])) and isinstance(kept.get('path'),str)
                          and bool(kept['path']),'Raw call artifact reference missing')
            else:
                self.record_bytes+=len(raw);D.require(self.record_bytes<=16*1024*1024,'Delivery report16MiBbound; no silent transcript truncation')
                kept=record
            self.report['calls'].append(kept)
        return result

    def snap(self):
        value=self.snapshot()
        self.check('native-business-snapshot',isinstance(value,dict) and bool(C.HEX64.fullmatch(value.get('state_jam_sha256',''))))
        return value

    def same(self,before):
        after=self.snap();self.check('no-authoritative-business-change',before['state_jam_sha256']==after['state_jam_sha256']);return after

    def pending(self):
        record=self.pending_snapshot();value=pending_value(record)
        self.current.setdefault('pending_snapshots',[]).append(record);return value

    def wait_pending(self,count):
        for index in range(40):
            value=self.pending()
            if D.number(value['total'])==count:return value
            if index<39:self.pause(.2)
        raise D.ObservationError('Pending count did not reach expected bound')

    def watch(self,ship,route):
        probe=self.pool.allocate(ship);self.observer.control(ship,'watch',probe,route=route)
        row=self.observer.wait_for(ship,probe,lambda obj:D.number(obj['watch_acks'])+D.number(obj['watch_nacks'])==1)['final']
        return probe,row

    def completed(self,ship,probe,raw):
        row=self.observer.wait_for(ship,probe,lambda obj:obj['closed']=='true')['final'];obj,events=D.observation(row)
        self.check('actual-one-fact-kick',obj['facts']=='1' and obj['kicks']=='1' and obj['watch_nacks']=='0' and obj['ongoing_subscription']=='false')
        facts=[event for _,event in events if event['kind']=='fact']
        self.check('exact-correlated-fact-bytes',len(facts)==1 and facts[0]['payload_sha256']==hashlib.sha256(raw.encode()).hexdigest() and D.number(facts[0]['payload_bytes'])==len(raw.encode()))
        self.old_completed=(ship,probe);return row

    def recover(self,command):
        result=self.call('bus','read',route=receipt_route(command),raw=b'')
        outcome=D.transport_outcome([{'kind':'fact','raw':result.get('raw')}],expected_request=correlated(command,'bus'))
        self.check('recovery-is-exact-authorized-receipt',outcome=={'status':'accepted','saved':True})
        return result

    def held_read(self):
        before=self.snap();route=f"/v2/document/{self.command['project_id']}/{self.command['payload']['container_id']}/{self.command['resource_id']}"
        logs_before=self.runtime_errors();D.require('cursor'in logs_before,'Runtime cursor missing')
        control=self.control_callback('hold-outsider-read','bud',route,'')
        outsider,old=self.watch('bud',route)
        self.check('held-outsider-acknowledged-without-content',old['json']['watch_acks']=='1' and old['json']['facts']=='0' and old['json']['ongoing_subscription']=='true')
        owner,owner_before=self.watch('bus',route)
        response=self.call('bus','read',route=route,raw=b'')
        owner_after=self.completed('bus',owner,response['raw'])
        outsider_after=self.observer.read('bud',outsider)
        logs=self.runtime_errors(logs_before['cursor'])
        trace={'classification':'real-native-observer','request':{'ship':'bus','probe_id':owner,'route':route},
               'response':owner_after,'sentinels':[{'ship':'bud','before':old,'after':outsider_after,
               'held_control':{'operation':'hold-outsider-read','ship':'bud','route':route,'native':control.get('native')}}],
               'runtime_errors':logs.get('errors'),'runtime_log_evidence':logs.get('segments')}
        proof=D.verify_one_shot(trace,response['raw'],ship='bus',route=route)
        self.check('known-valid-mark-positive-control',proof['status']=='passed',trace)
        self.observer.control('bud','leave',outsider)
        denial=self.call('bud','read',route=route,raw=b'')
        self.check('fresh-outsider-read-is-exact-denial',denial.get('json')==C.DENIAL)
        self.same(before)

    def wrong_sender(self):
        before=self.snap();baseline=self.pending()
        for ship,route in [('bud',command_route('bus',self.command)),('bus',command_route('bus',self.command).replace(C.BINDINGS['bus'],C.BINDINGS['bud']))]:
            probe,row=self.watch(ship,route)
            self.check('foreign-sender-binding-watch-nack',row['json']['watch_nacks']=='1' and row['json']['facts']=='0' and row['json']['ongoing_subscription']=='false')
        self.check('wrong-sender-does-not-reserve',self.pending()['entries']==baseline['entries']);self.same(before)

    def missing_channel(self):
        before=self.snap();self.check('no-pending-before-missing-channel',self.pending()['total']=='0')
        cmd=copy.deepcopy(self.corpus['commands']['work_a_create']);cmd.update(request_id='019939ba-4000-7000-8000-000000006001',resource_id='019939ba-4000-7000-8000-000000006002')
        cmd['payload']['description']='Synthetic delivery: no result channel; explicit recovery required.'
        transport=self.call('bus','poke',route='/',raw=C.canonical(cmd))
        self.check('poke-ack-does-not-contain-business-acceptance',transport.get('json') in ({},None))
        self.check('ack-alone-never-saved',not D.transport_outcome([{'kind':'ack'}])['saved'])
        after=self.snap()
        def count(value,key):return C.uint(value.get('counts',value).get(key,value.get({'journal':'journal_events'}.get(key,key))))
        self.check('missing-channel-durable-single-acceptance',after['state_jam_sha256']!=before['state_jam_sha256'] and count(after,'journal')==count(before,'journal')+1 and count(after,'receipts')==count(before,'receipts')+1 and after['revisions'].get(C.revision_key(cmd))=='1')
        receipt=self.recover(cmd);self.same(after)
        wrong,baseline=self.watch('bus',command_route('bus',cmd,'0'*64))
        self.observer.control('bus','poke',wrong,raw=C.canonical(cmd).decode())
        observed=self.observer.wait_for('bus',wrong,lambda obj:obj['poke_acks']=='1')['final']
        self.check('wrong-digest-does-not-receive-receipt',observed['json']['facts']=='0' and observed['json']['ongoing_subscription']=='true')
        self.observer.control('bus','leave',wrong);self.wait_pending(0);self.same(after)
        self.current['recovered_receipt']=receipt

    def leave_retry(self):
        before=self.snap();receipt=self.recover(self.command);route=command_route('bus',self.command)
        old,baseline=self.watch('bus',route);self.observer.control('bus','leave',old);self.wait_pending(0)
        self.observer.control('bus','poke',old,raw=C.canonical(self.command).decode())
        ended=self.observer.wait_for('bus',old,lambda obj:obj['poke_acks']=='1')['final']
        self.check('cancelled-duct-never-receives-late-receipt',ended['json']['facts']=='0' and ended['json']['ongoing_subscription']=='false')
        fresh,_=self.watch('bus',route);self.observer.control('bus','poke',fresh,raw=C.canonical(self.command).decode())
        self.completed('bus',fresh,receipt['raw'])
        self.check('old-duct-remains-ended',self.observer.read('bus',old)['json']['facts']=='0')
        self.wait_pending(0);self.same(before)

    def expiry(self):
        before=self.snap();receipt=self.recover(self.command);route=command_route('bus',self.command)
        old,_=self.watch('bus',route);initial=self.pending();deadline=D.number(initial['entries'][route]['expires_at_ms'])
        waited=self.wait_until(deadline);now=C.uint(self.trusted_now_ms())
        self.check('actual-real-expiry-observed',isinstance(waited,dict) and now>=deadline and waited.get('elapsed_seconds',-1)>=0,waited)
        stale=self.pending();self.check('expiration-is-lazy-not-autonomous',route in stale['entries'])
        retired,_=self.watch('bus',route)
        ended=self.observer.wait_for('bus',retired,lambda obj:obj['closed']=='true')['final']
        self.check('expired-same-path-first-retry-retires-only',ended['json']['facts']=='0' and ended['json']['kicks']=='1' and ended['json']['ongoing_subscription']=='false')
        self.wait_pending(0)
        transport=self.call('bus','poke',route='/',raw=C.canonical(self.command))
        self.check('retirement-ack-kick-never-saved',transport.get('json') in ({},None) and not D.transport_outcome([{'kind':'ack'},{'kind':'kick'}])['saved'])
        fresh,_=self.watch('bus',route);self.observer.control('bus','poke',fresh,raw=C.canonical(self.command).decode())
        self.completed('bus',fresh,receipt['raw'])
        for probe in (old,retired):self.check('expired-old-duct-no-late-fact',self.observer.read('bus',probe)['json']['facts']=='0')
        self.wait_pending(0);self.same(before)

    def quotas(self):
        before=self.snap();self.check('quota-baseline-empty',self.pending()['total']=='0')
        allocated={ship:[] for ship in sorted(D.FAKES)}
        def fill(ship):
            for _ in range(17):
                probe=self.pool.allocate(ship);allocated[ship].append(probe)
                self.observer.control(ship,'watch',probe,route=result_route(ship,self.command['project_id'],probe,'a'*64))
        try:
            with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fill,sorted(D.FAKES)))
            full=self.wait_pending(64)
            self.check('actual16-per-sender64total',all(value=='16' for value in full['by_ship'].values()))
            for ship,probes in allocated.items():
                denied=self.observer.wait_for(ship,probes[-1],lambda obj:obj['watch_nacks']=='1')['final']
                self.check('seventeenth-channel-native-nack:'+ship,denied['json']['facts']=='0' and denied['json']['ongoing_subscription']=='false')
        finally:
            def leave(ship):
                for probe in allocated[ship][:-1]:self.observer.control(ship,'leave',probe)
            with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(leave,sorted(D.FAKES)))
        self.wait_pending(0);self.same(before)

    def unavailable(self):
        before=self.snap();route=receipt_route(self.command)
        def attempt(bounded_call):
            try:
                response=bounded_call('bus','read',route=route,raw=b'',timeout=5)
                return {'response':response,'supported_failure':None,
                        'saved':isinstance(response.get('json'),dict) and response['json'].get('status')=='accepted'}
            except TimeoutError as error:
                return {'exception':type(error).__name__+': '+str(error),'supported_failure':'timeout','saved':False}
            except OSError as error:
                if error.errno not in (errno.ECONNREFUSED,errno.EHOSTUNREACH,errno.ENETUNREACH,errno.ETIMEDOUT):
                    raise
                return {'exception':type(error).__name__+': '+str(error),'supported_failure':'unreachable','errno':error.errno,'saved':False}
        evidence=self.unavailable_home(attempt)
        self.check('actual-home-unavailability-lifecycle',isinstance(evidence,dict) and bool(evidence.get('native')) and evidence.get('old_exit')==0 and evidence.get('old_pid')!=evidence.get('replacement_pid') and bool(evidence.get('old_pid')) and bool(evidence.get('replacement_pid')))
        during=evidence.get('attempt',{})
        self.check('unavailable-home-never-saved',during.get('saved') is False
                   and during.get('supported_failure') in ('timeout','unreachable') and 'exception'in during)
        self.current['unavailability']=evidence;self.same(before)

    def ended_leave(self):
        before=self.snap();D.require(self.old_completed is not None,'Prior completed duct required')
        ship,old=self.old_completed;receipt=self.recover(self.command);fresh,_=self.watch(ship,command_route(ship,self.command))
        attempted=self.observer.control(ship,'leave-ended',old)
        self.check('ended-native-leave-attempt-never-business-outcome',attempted.get('json') in ({},None))
        self.current['ended_leave_transport']=attempted
        self.observer.control(ship,'poke',fresh,raw=C.canonical(self.command).decode());self.completed(ship,fresh,receipt['raw'])
        self.wait_pending(0);self.same(before)
        # The fixture emits a real card on the ended original wire. Gall may
        # reject it locally; this does not inject an inbound reordered leave at
        # the home boundary. Record the precise narrower observed result.
        self.current['missing']=['Actual delayed old native leave injection at home remains unavailable; pinned Gall source review is a distinct proof.']

    def run(self):
        required=(self.base_call,self.snapshot,self.pending_snapshot,self.control_callback,self.trusted_now_ms,
                  self.wait_until,self.unavailable_home,self.pause,self.runtime_errors)
        ready=all(callable(callback) for callback in required) and bool(self.report['provenance'])
        methods=(self.held_read,self.wrong_sender,self.missing_channel,self.leave_retry,self.expiry,self.quotas,self.unavailable,self.ended_leave)
        aborted=None;started=time.monotonic()
        for name,method in zip(CASE_NAMES,methods):
            self.current={'name':name,'status':'not_run','assertions':[]};self.report['cases'].append(self.current)
            if not ready or aborted:
                self.current['reason']=aborted or 'Guarded native callbacks/provenance absent; source recipe only'
                continue
            try:
                method();self.check('nonempty-case-evidence',bool(self.current['assertions']))
                self.current['status']='incomplete' if self.current.get('missing') else 'passed'
            except Exception as error:
                self.current.update(status='failed',error=type(error).__name__+': '+str(error));aborted='Dependent native delivery schedule stopped after '+name
        self.report['elapsed_seconds']=round(time.monotonic()-started,6)
        completed=bool(self.report['calls']) and all(case['status']=='passed' for case in self.report['cases'])
        self.report['functional_scope_passed']=completed
        self.report['native_qualified']=completed and self.report['classification']=='real-native-fake-ships'
        deferred=bool(self.report['calls']) and all(case['status'] in ('passed','incomplete') for case in self.report['cases'])
        self.report['status']='passed' if self.report['native_qualified'] else 'host-only' if completed else 'incomplete' if deferred else 'failed'
        return self.report


def run(corpus,call=None,**kwargs):
    return Suite(corpus,call,**kwargs).run()

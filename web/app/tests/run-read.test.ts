import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {canonical} from '../src/protocol';
import {ProductProtocolError} from '../src/productWire';
import {encodeRunQuery, parseRunQuery, parseRunView, runDetails, runResult, RunReadClient, RunReadClientError,
  type RunQuery, type RunPreview, type RunDetail, type RunReadTransport} from '../src/runReadProtocol';
const id = (n: number) => { assert.ok(n >= 100 && n <= 999); return '019939ba-4000-7000-8000-000000000' + n; };
const query = (kind: RunQuery['kind'] = 'runs', changes: Partial<RunQuery> = {}): RunQuery => ({protocol:'stead.run-query/1',request_id:id(700),
  kind,project_id:id(100),work_id:id(101),run_id:kind === 'run' ? id(400) : '',cursor:'',...changes});
const preview: RunPreview = {kind:'run',project_id:id(100),work_id:id(101),run_id:id(400),run_revision:'1',phase:'queued',issued_at_ms:'1000',deadline_ms:'2000',
  requester_principal_id:id(102),requester_display_name:'Alice',owner_principal_id:id(102),owner_display_name:'Alice',worker_principal_id:id(103),worker_display_name:'',
  current_attempt:'0',question_sequence:'0',lease_state:'none',lease_until_ms:'0',result:''};
const version = canonical({definition_id:id(300),definition_revision:'1',runtime_id:id(301),runtime_revision:'2'});
const detail: RunDetail = {...preview,execution_contract_revision:'4',execution_contract_digest:'a'.repeat(64),agent_version:version,
  execution_current:'yes',current_attempt_detail:'',latest_question:''};
const attempt = {attempt:'1',principal_id:id(103),display_name:'',started_at_ms:'1100',heartbeat_at_ms:'1150',lease_until_ms:'1300',disposition:'waiting'};
const question = {sequence:'1',text:'Which wording should I use?',principal_id:id(103),display_name:'',recorded_at_ms:'1160',answer:''};
const waiting: RunDetail = {...detail,run_revision:'3',phase:'waiting',current_attempt:'1',question_sequence:'1',lease_state:'live',lease_until_ms:'1300',
  current_attempt_detail:canonical(attempt),latest_question:canonical(question)};
const reference = {change_id:id(500),result_revision:'2',result_digest:'b'.repeat(64),outcome_id:id(501)};
function wire(request: RunQuery, rows: unknown[] = [], changes: Record<string, unknown> = {}) {
  return JSON.stringify({protocol:'stead.run-query-result/1',status:'read',request_id:request.request_id,kind:request.kind,project_id:request.project_id,
    work_id:request.work_id,run_id:request.run_id,authority_epoch:'1',generation:'c'.repeat(64),cursor:'',rows:Object.fromEntries(rows.map((row,index)=>[String(index),row])),...changes});
}
const invalid = (action: () => unknown) => assert.throws(action, error => error instanceof ProductProtocolError && error.code === 'invalid_response');
const error = (code: RunReadClientError['code']) => (value: unknown) => value instanceof RunReadClientError && value.code === code;
const transport = (changes: Partial<RunReadTransport> = {}): RunReadTransport => ({currentSession:()=> 'session-one',capability:()=> 'stead.run-query/1',
  query:async raw=>wire(parseRunQuery(raw)),...changes});
const page = Array.from({length:20},(_,n)=>({...preview,run_id:id(400+n)}));

test('seven-field query grammar and source-derived canonical vectors stay exact without commands',async()=>{
  const vectors=JSON.parse(await readFile('tests/run-read-vectors.json','utf8'));assert.equal(vectors.classification,'source-derived-expected-values-not-native-execution');
  for(const item of vectors.vectors){assert.equal(encodeRunQuery(item.query),item.canonical);assert.equal(createHash('sha256').update(item.canonical).digest('hex'),item.bytes_sha256);}
  for(const request of [query(),query('run'),query('runs',{cursor:'d'.repeat(64)})])assert.deepEqual(JSON.parse(encodeRunQuery(request)),JSON.parse(JSON.stringify(parseRunQuery(JSON.stringify(request)))));
  for(const changes of [{protocol:'stead.run-command/1'},{kind:'claim'},{work_id:''},{run_id:id(400)},{cursor:'not-opaque'},{secret:''},{request_id:123}])assert.throws(()=>parseRunQuery(JSON.stringify({...query(),...changes})));
  for(const changes of [{run_id:''},{cursor:'d'.repeat(64)}])assert.throws(()=>parseRunQuery(JSON.stringify({...query('run'),...changes})));
  assert.throws(()=>parseRunQuery(encodeRunQuery(query()).replace('"kind":"runs"','"kind":"runs","kind":"runs"')));
});
test('nineteen-field previews are scoped ordered bounded and preserve blank catalog names',()=>{
  const request=query(),view=parseRunView(wire(request,page,{cursor:'d'.repeat(64)}),request);assert.equal(view.status,'read');if(view.status!=='read')throw new Error();
  assert.equal(view.rows.length,20);assert.equal(Object.keys(view.rows[0]!).length,19);assert.equal(view.rows[0]!.worker_display_name,'');assert.equal(Object.isFrozen(view.rows[0]),true);
  for(const changed of [{...preview,work_id:id(999)},{...preview,project_id:id(999)},{...preview,run_id:''},{...preview,kind:'work'},{...preview,context:'secret'},
    {...preview,worker_display_name:'x'.repeat(201)},{...preview,owner_display_name:'bad\nname'},{...preview,owner_principal_id:preview.worker_principal_id}])invalid(()=>parseRunView(wire(request,[changed]),request));
  invalid(()=>parseRunView(wire(request,[preview,preview]),request));invalid(()=>parseRunView(wire(request,[page[1],page[0]]),request));
  invalid(()=>parseRunView(wire(request,Array.from({length:21},(_,n)=>({...preview,run_id:id(400+n)}))),request));
  invalid(()=>parseRunView(wire(request,[preview],{cursor:'d'.repeat(64)}),request));
});
test('twenty-five-field detail retains exact attempt question answer and immutable agent version',()=>{
  const request=query('run'),answer={text:'Use the shared guide.',principal_id:id(102),display_name:'Alice',recorded_at_ms:'1170'};
  const row={...waiting,latest_question:canonical({...question,answer:canonical(answer)})};const view=parseRunView(wire(request,[row]),request);assert.equal(view.status,'read');
  const nested=runDetails(row);assert.equal(Object.keys(row).length,25);assert.equal(nested.agentVersion.runtime_revision,'2');assert.equal(nested.attempt!.display_name,'');
  assert.equal(nested.question!.text,question.text);assert.equal(nested.answer!.text,answer.text);assert.equal(Object.isFrozen(nested.answer),true);
  // Native question prose admits whitespace/control bytes except NUL/CR, and its recorded uint64 may be zero.
  const zero={...waiting,latest_question:canonical({...question,text:'\t\u0001',recorded_at_ms:'0',answer:canonical({...answer,text:' ',recorded_at_ms:'0'})})};
  assert.equal(parseRunView(wire(request,[zero]),request).status,'read');
  assert.equal(runDetails(detail).question,undefined);assert.equal(runDetails(detail).attempt,undefined);
});
test('durable phase lease observation and execution freshness remain independent from business acceptance',()=>{
  const request=query('run');
  for(const lease_state of ['live','expired','unknown-book'] as const)for(const execution_current of ['yes','no'] as const){
    const row={...waiting,lease_state,execution_current};assert.equal(parseRunView(wire(request,[row]),request).status,'read');assert.equal(runResult(row),undefined);
  }
  const submitted={...waiting,phase:'submitted' as const,lease_state:'terminal' as const,result:canonical(reference),current_attempt_detail:canonical({...attempt,disposition:'submitted'})};
  assert.equal(parseRunView(wire(request,[submitted]),request).status,'read');assert.equal(runResult(submitted)!.result_digest,reference.result_digest);
  assert.equal(Object.hasOwn(runResult(submitted)!,'accepted'),false);
  assert.equal(parseRunView(wire(request,[{...detail,phase:'canceled'}]),request).status,'read'); // Canceled before claim has no lease.
  for(const changed of [{...waiting,lease_state:'none'},{...waiting,phase:'done'},{...waiting,lease_state:'active'},{...waiting,execution_current:'allowed'},
    {...waiting,result:canonical(reference)},{...submitted,result:''},{...submitted,lease_state:'expired'}])invalid(()=>parseRunView(wire(request,[changed]),request));
});
test('nested records are canonical duplicate-free bounded and cannot disclose grants or lease secrets',()=>{
  const request=query('run');
  for(const changed of [{...waiting,agent_version:' '+version},{...waiting,agent_version:version.replace('"runtime_revision":"2"','"runtime_revision":"2","runtime_revision":"2"')},
    {...waiting,current_attempt_detail:canonical({...attempt,audit:'secret'})},{...waiting,current_attempt_detail:canonical({...attempt,principal_id:id(999)})},
    {...waiting,current_attempt_detail:canonical({...attempt,attempt:'2'})},{...waiting,current_attempt_detail:canonical({...attempt,heartbeat_at_ms:'999'})},
    {...waiting,latest_question:canonical({...question,sequence:'2'})},{...waiting,latest_question:canonical({...question,text:'x'.repeat(2049)})},
    {...waiting,latest_question:canonical({...question,text:'bad\rtext'})},{...waiting,latest_question:canonical({...question,answer:canonical({text:'answer',principal_id:id(102),display_name:'',recorded_at_ms:'1',grant:'secret'})})},
    {...waiting,latest_question:''},{...detail,current_attempt_detail:canonical(attempt)},{...detail,latest_question:canonical(question)}])invalid(()=>parseRunView(wire(request,[changed]),request));
  const submitted={...waiting,phase:'submitted',lease_state:'terminal',result:canonical({...reference,receipt:'secret'})};invalid(()=>parseRunView(wire(request,[submitted]),request));
});
test('integer limits and exact response envelope reject coercion sparse rows mixed versions and unknown failures',()=>{
  const request=query();
  for(const changed of [{...preview,current_attempt:'4'},{...preview,question_sequence:'4097'},{...preview,run_revision:'01'},{...preview,run_revision:1},
    {...preview,issued_at_ms:'0'},{...preview,deadline_ms:'18446744073709551616'},{...preview,deadline_ms:'999'}])invalid(()=>parseRunView(wire(request,[changed]),request));
  for(const changes of [{protocol:'stead.query-result/4'},{request_id:id(999)},{work_id:id(999)},{authority_epoch:'0'},{authority_epoch:'18446744073709551616'},
    {generation:'not-token'},{rows:{'1':preview}},{rows:[preview]},{authorization:'yes'}])invalid(()=>parseRunView(wire(request,[preview],changes),request));
  invalid(()=>parseRunView(wire(query('run'),[]),query('run')));invalid(()=>parseRunView(wire(query('run'),[detail],{cursor:'d'.repeat(64)}),query('run')));
  invalid(()=>parseRunView(wire(request,[preview]).replace('"status":"read"','"status":"read","status":"read"'),request));
  invalid(()=>parseRunView(wire(request,[preview])+' '.repeat(262144),request));
  const denied={protocol:'stead.run-query-result/1',status:'rejected',request_id:request.request_id,error:'denied_or_not_found'};
  assert.equal(parseRunView(canonical(denied),request).status,'rejected');invalid(()=>parseRunView(canonical({...denied,error:'new-success'}),request));
  invalid(()=>parseRunView(canonical({...denied,rows:{}}),request));
});
test('capability and session are required and late capability withdrawal never publishes rows',async()=>{
  let calls=0,allowed=true,release!:(raw:string)=>void;
  const missing=new RunReadClient(transport({capability:undefined,query:async()=>{calls++;return '';}}));await assert.rejects(missing.read(query()),error('unsupported_operation'));
  const absent=new RunReadClient(transport({currentSession:()=>null,query:async()=>{calls++;return '';}}));await assert.rejects(absent.read(query()),error('session_required'));assert.equal(calls,0);
  const client=new RunReadClient(transport({capability:()=>allowed?'stead.run-query/1':null,query:()=>new Promise(resolve=>{release=resolve;})}));
  const pending=client.read(query());allowed=false;release(wire(query(),[preview]));await assert.rejects(pending,error('unsupported_operation'));
});
test('read failure stays separate from rejection and malformed response without an automatic retry',async()=>{
  let calls=0;const unavailable=new RunReadClient(transport({query:async()=>{calls++;throw new Error('Connection lost');}}));
  await assert.rejects(unavailable.read(query()),error('read_unavailable'));assert.equal(calls,1);
  const rejected=new RunReadClient(transport({query:async raw=>canonical({protocol:'stead.run-query-result/1',status:'rejected',request_id:parseRunQuery(raw).request_id,error:'denied_or_not_found'})}));
  assert.equal((await rejected.readRuns({request_id:id(701),project_id:id(100),work_id:id(101)})).status,'rejected');
  const malformed=new RunReadClient(transport({query:async()=>'{bad'}));await assert.rejects(malformed.read(query()),e=>e instanceof ProductProtocolError&&e.code==='invalid_response');
});
test('opaque session changes suppress late success and failure and query bytes snapshot caller data',async()=>{
  let token:object={},release!:(raw:string)=>void,reject!:(error:Error)=>void,seen='';
  const client=new RunReadClient(transport({currentSession:()=>token,query:raw=>{seen=raw;return new Promise((resolve,fail)=>{release=resolve;reject=fail;});}}));
  const mutable=query(),pending=client.read(mutable);mutable.work_id=id(999);assert.equal(parseRunQuery(seen).work_id,id(101));token={};release(wire(query(),[preview]));
  await assert.rejects(pending,error('session_changed'));
  const failure=client.read(query());token={};reject(new Error('Old connection'));await assert.rejects(failure,error('session_changed'));
});
test('one-use cursor binds Work scope and ordered thirty-two-run native bound',async()=>{
  const cursor='d'.repeat(64);let calls=0;
  const client=new RunReadClient(transport({query:async raw=>{calls++;const request=parseRunQuery(raw);return wire(request,request.cursor?Array.from({length:12},(_,n)=>({...preview,run_id:id(420+n)})):page,{cursor:request.cursor?'':cursor});}}));
  await client.read(query());await assert.rejects(client.read(query('runs',{work_id:id(999),cursor})),error('stale_cursor'));assert.equal(calls,1);
  const next=await client.read(query('runs',{request_id:id(701),cursor}));assert.equal(next.status,'read');if(next.status!=='read')throw new Error();assert.equal(next.rows.length,12);
  await assert.rejects(client.read(query('runs',{cursor})),error('stale_cursor'));assert.equal(calls,2);
  const detailClient=new RunReadClient(transport({query:async raw=>wire(parseRunQuery(raw),[detail])}));assert.equal((await detailClient.readRun({request_id:id(702),project_id:id(100),work_id:id(101),run_id:id(400)})).status,'read');
});
test('cursor epoch generation consumed unknown and cross-page duplicate failures require fresh first page',async()=>{
  const cursor='d'.repeat(64);
  for(const change of [{generation:'e'.repeat(64)},{authority_epoch:'2'},{rows:{'0':preview}},{rows:Object.fromEntries(Array.from({length:13},(_,n)=>[String(n),{...preview,run_id:id(420+n)}]))}]){
    let calls=0;const client=new RunReadClient(transport({query:async raw=>{calls++;const request=parseRunQuery(raw);return request.cursor?wire(request,[],change):wire(request,page,{cursor});}}));
    await client.read(query());await assert.rejects(client.read(query('runs',{cursor})),error('stale_cursor'));await assert.rejects(client.read(query('runs',{cursor})),error('stale_cursor'));assert.equal(calls,2);
  }
  const lost=new RunReadClient(transport({query:async raw=>{const request=parseRunQuery(raw);if(request.cursor)throw new Error('Lost');return wire(request,page,{cursor});}}));
  await lost.read(query());await assert.rejects(lost.read(query('runs',{cursor})),error('read_unavailable'));await assert.rejects(lost.read(query('runs',{cursor})),error('stale_cursor'));
});
test('late old-session response cannot erase current-session continuation',async()=>{
  let token:object={},first=true,release!:(raw:string)=>void;const cursor='d'.repeat(64);
  const client=new RunReadClient(transport({currentSession:()=>token,query:async raw=>{const request=parseRunQuery(raw);if(first){first=false;return new Promise(resolve=>{release=resolve;});}
    return wire(request,request.cursor?[]:page,{cursor:request.cursor?'':cursor});}}));
  const old=client.read(query());token={};await client.read(query('runs',{request_id:id(701)}));release(wire(query(),page,{cursor:'e'.repeat(64)}));await assert.rejects(old,error('session_changed'));
  assert.equal((await client.read(query('runs',{request_id:id(702),cursor}))).status,'read');
});
test('same-session A to B to A list refreshes suppress old success and failure without deleting newest cursor',async()=>{
  const pending:Array<{query:RunQuery;resolve:(raw:string)=>void;reject:(error:Error)=>void}>=[],cursor='f'.repeat(64);let calls=0;
  const client=new RunReadClient(transport({query:raw=>{calls++;const request=parseRunQuery(raw);if(request.cursor)return Promise.resolve(wire(request,[]));
    return new Promise((resolve,reject)=>pending.push({query:request,resolve,reject}));}}));
  const oldA=client.read(query()),oldB=client.read(query('runs',{request_id:id(701),work_id:id(105)})),newA=client.read(query('runs',{request_id:id(702)}));
  pending[2]!.resolve(wire(pending[2]!.query,page,{cursor}));assert.equal((await newA).status,'read');
  pending[0]!.resolve(wire(pending[0]!.query,page,{cursor:'d'.repeat(64)}));await assert.rejects(oldA,error('stale_cursor'));
  pending[1]!.reject(new Error('Old B connection'));await assert.rejects(oldB,error('stale_cursor'));
  assert.equal((await client.read(query('runs',{request_id:id(703),cursor}))).status,'read');assert.equal(calls,4);
});
test('refresh fences in-flight continuation while independent exact detail still publishes',async()=>{
  for(const failOld of [false,true]){
    const cursor='d'.repeat(64),freshCursor='e'.repeat(64);let first=true,resolvePage!:(raw:string)=>void,rejectPage!:(error:Error)=>void,resolveDetail!:(raw:string)=>void;
    const client=new RunReadClient(transport({query:raw=>{const request=parseRunQuery(raw);
      if(request.kind==='run')return new Promise(resolve=>{resolveDetail=resolve;});
      if(request.cursor===cursor)return new Promise((resolve,reject)=>{resolvePage=resolve;rejectPage=reject;});
      if(request.cursor)return Promise.resolve(wire(request,[]));const token=first?cursor:freshCursor;first=false;return Promise.resolve(wire(request,page,{cursor:token}));}}));
    await client.read(query());const old=client.read(query('runs',{request_id:id(701),cursor})),exact=client.read(query('run',{request_id:id(702)}));
    await client.read(query('runs',{request_id:id(703)}));
    if(failOld)rejectPage(new Error('Consumed old page'));else resolvePage(wire(query('runs',{request_id:id(701),cursor}),[]));
    await assert.rejects(old,error('stale_cursor'));resolveDetail(wire(query('run',{request_id:id(702)}),[detail]));assert.equal((await exact).status,'read');
    assert.equal((await client.read(query('runs',{request_id:id(704),cursor:freshCursor}))).status,'read');
  }
});

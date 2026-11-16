import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {ProductProtocolError, productJSON} from '../src/productWire';
import {encodeRunControlCommand, parseRunAnswer, parseRunControlCommand, parseRunControlReceipt, runControlDigest,
  RunControlClient, RunControlClientError, type RunControlCommand, type RunControlTransport} from '../src/runControlProtocol';
const id = (n: number) => '019939ba-4000-7000-8000-' + String(n).padStart(12,'0');
const scope = {request_id:id(700),project_id:id(100),run_id:id(400),expected_revision:'3',expected_attempt:'1'};
const answer = (changes = {}): RunControlCommand => ({...scope,protocol:'stead.run-command/1',operation:'answer',payload:productJSON({question:'1',text:'Use the shared guide.'}),...changes});
const cancel = (): RunControlCommand => ({...answer(),operation:'cancel',payload:'Please stop this attempt.'});
const digest = (command: RunControlCommand) => createHash('sha256').update('stead.run-command/1\0' + encodeRunControlCommand(command)).digest('hex');
function receipt(command: RunControlCommand, changes = {}) { return JSON.stringify({protocol:'stead.run-result/1',status:'accepted',request_id:command.request_id,
  canonical_sha256:digest(command),error:'',run_id:command.run_id,run_revision:String(BigInt(command.expected_revision)+1n),attempt:command.expected_attempt,
  phase:command.operation==='answer'?'waiting':'canceled',...changes}); }
const rejected = (command: RunControlCommand, error = 'denied_or_not_found') => JSON.stringify({protocol:'stead.run-result/1',status:'rejected',request_id:command.request_id,canonical_sha256:digest(command),error});
const invalid = (action: () => unknown) => assert.throws(action, error=>error instanceof ProductProtocolError && error.code==='invalid_response');
const clientError = (code: RunControlClientError['code']) => (value: unknown) => value instanceof RunControlClientError && value.code===code;
const transport = (changes: Partial<RunControlTransport> = {}): RunControlTransport => ({currentSession:()=> 'opaque-session-one',capability:()=> 'stead.run-command/1',
  command:async bytes=>receipt(parseRunControlCommand(bytes)),...changes});

test('human command subset preserves exact eight string fields and domain digest',async()=>{
  for(const command of [answer(),cancel()]){const raw=encodeRunControlCommand(command);assert.equal(Object.keys(JSON.parse(raw)).length,8);
    assert.equal(raw,productJSON(command));assert.equal(await runControlDigest(command),digest(command));assert.equal(Object.isFrozen(parseRunControlCommand(raw)),true);}
  assert.equal(encodeRunControlCommand(cancel()),'{"expected_attempt":"1","expected_revision":"3","operation":"cancel","payload":"Please stop this attempt.","project_id":"019939ba-4000-7000-8000-000000000100","protocol":"stead.run-command/1","request_id":"019939ba-4000-7000-8000-000000000700","run_id":"019939ba-4000-7000-8000-000000000400"}');
});
test('command decoder rejects workers extra keys numeric scalars and invalid scope counters',()=>{
  for(const changes of [{operation:'claim'},{operation:'issue'},{operation:'resume'},{operation:'finish'},{request_id:id(700).toUpperCase()},{project_id:''},
    {expected_revision:'0'},{expected_revision:'01'},{expected_revision:'18446744073709551616'},{expected_attempt:'4'},{expected_attempt:1},{payload:{}},{work_id:id(101)}])assert.throws(()=>parseRunControlCommand(JSON.stringify({...answer(),...changes})));
  assert.throws(()=>parseRunControlCommand(encodeRunControlCommand(answer()).replace('"operation":"answer"','"operation":"answer","operation":"answer"')));
});
test('answer payload is canonical bounded UTF8 and preserves native permitted prose',()=>{
  for(const text of [' ', '\t\u0001', '界'.repeat(682)])assert.equal(parseRunAnswer(productJSON({question:'18446744073709551615',text})).text,text);
  for(const payload of ['{"text":"ok","question":"1"}','{"question":"0","text":"ok"}',productJSON({question:'1',text:''}),productJSON({question:'1',text:'界'.repeat(683)}),'{"question":"1","text":"bad\\rline"}','{"question":"1","text":"bad\\u0000"}','{"question":"1","text":"\\ud800"}'])assert.throws(()=>parseRunControlCommand(JSON.stringify(answer({payload}))));
  assert.throws(()=>parseRunControlCommand(JSON.stringify({...cancel(),payload:'界'.repeat(86)})));
  assert.equal(parseRunControlCommand(JSON.stringify({...cancel(),payload:'界'.repeat(85)})).operation,'cancel');
});
test('accepted answer remains waiting and cancellation is only a durable canceled receipt',()=>{
  for(const command of [answer(),cancel()]){const got=parseRunControlReceipt(receipt(command),command,digest(command));assert.equal(got.status,'accepted');
    assert.equal(got.phase,command.operation==='answer'?'waiting':'canceled');assert.equal(Object.isFrozen(got),true);assert.equal(Object.hasOwn(got,'process_stopped'),false);}
  const queued={...cancel(),expected_attempt:'0'};assert.equal(parseRunControlReceipt(receipt(queued),queued,digest(queued)).status,'accepted');
});
test('full rejected receipts permit changed current revision attempt and phase without accepting',()=>{
  const command=answer();const got=parseRunControlReceipt(receipt(command,{status:'rejected',error:'revision_conflict',run_revision:'8',attempt:'2',phase:'submitted'}),command,digest(command));
  assert.equal(got.status,'rejected');assert.equal(got.run_revision,'8');
  for(const error of ['terminal_run','already_answered','expired_authority','stale_contract_or_authority','invalid_answer','unknown_question'])assert.equal(parseRunControlReceipt(receipt(command,{status:'rejected',error}),command,digest(command)).status,'rejected');
});
test('five-field rejection stays closed and never invents a current head',()=>{
  const command=answer(),got=parseRunControlReceipt(rejected(command),command,digest(command));assert.equal(got.status,'rejected');assert.equal(Object.keys(got).length,5);assert.equal(Object.hasOwn(got,'phase'),false);
  invalid(()=>parseRunControlReceipt(rejected(command,'new_unknown_error'),command,digest(command)));
  invalid(()=>parseRunControlReceipt(JSON.stringify({...JSON.parse(rejected(command)),phase:'waiting'}),command,digest(command)));
});
test('receipts require exact request hash run counters status and phase',()=>{
  const command=answer();for(const changes of [{request_id:id(701)},{canonical_sha256:'a'.repeat(64)},{run_id:id(401)},{run_revision:'3'},{run_revision:'5'},{attempt:'2'},
    {attempt:1},{phase:'running'},{phase:'accepted'},{status:'accepted',error:'revision_conflict'},{status:'rejected',error:''},{secret:'extra'}])invalid(()=>parseRunControlReceipt(receipt(command,changes),command,digest(command)));
  invalid(()=>parseRunControlReceipt(receipt(command).replace('"status":"accepted"','"status":"accepted","status":"accepted"'),command,digest(command)));
  const max={...command,expected_revision:'18446744073709551615'};invalid(()=>parseRunControlReceipt(receipt(max),max,digest(max)));
});
test('preparation snapshots caller data and rejects reconstructed or foreign objects',async()=>{
  const client=new RunControlClient(transport()),mutable=answer(),prepared=await client.prepare(mutable);mutable.payload='changed';assert.equal(prepared.command.payload,answer().payload);
  assert.equal(Object.isFrozen(prepared),true);assert.equal(Object.isFrozen(prepared.command),true);
  await assert.rejects(client.submit({...prepared}),clientError('unrecognized_prepared_command'));
  await assert.rejects(new RunControlClient(transport()).submit(prepared),clientError('unrecognized_prepared_command'));
});
test('answer and cancel helpers only prepare the requested human command',async()=>{
  let calls=0;const client=new RunControlClient(transport({command:async raw=>{calls++;return receipt(parseRunControlCommand(raw));}}));
  const a=await client.prepareAnswer(scope,{question:'1',text:'Clarification'}),c=await client.prepareCancel(scope,'Stop');assert.equal(calls,0);
  assert.equal(parseRunAnswer(a.command.payload).text,'Clarification');assert.equal(c.command.operation,'cancel');assert.equal(c.command.payload,'Stop');
});
test('unknown reply never retries automatically and explicit retry preserves every byte',async()=>{
  const sent:string[]=[];let fail=true;const client=new RunControlClient(transport({command:async raw=>{sent.push(raw);if(fail)throw new Error('lost');return receipt(parseRunControlCommand(raw));}}));
  const prepared=await client.prepare(answer());await assert.rejects(client.submit(prepared),clientError('outcome_unknown'));assert.equal(sent.length,1);
  fail=false;assert.equal((await client.retry(prepared)).status,'accepted');assert.deepEqual(sent,[prepared.bytes,prepared.bytes]);
});
test('malformed and mismatched replies remain unknown while a valid denial is known',async()=>{
  let response='{}';const client=new RunControlClient(transport({command:async()=>response})),prepared=await client.prepare(cancel());
  await assert.rejects(client.submit(prepared),clientError('outcome_unknown'));response=receipt(cancel(),{run_id:id(999)});await assert.rejects(client.retry(prepared),clientError('outcome_unknown'));
  response=rejected(cancel());assert.equal((await client.retry(prepared)).status,'rejected');
});
test('actual token replacement and invalidation fence preparation success and failure',async()=>{
  let token:object={},release!:(raw:string)=>void,reject!:(error:Error)=>void;
  const client=new RunControlClient(transport({currentSession:()=>token,command:()=>new Promise((resolve,fail)=>{release=resolve;reject=fail;})}));
  const p=await client.prepare(answer()),inflight=client.submit(p);token={};release(receipt(answer()));await assert.rejects(inflight,clientError('session_changed'));
  await assert.rejects(client.retry(p),clientError('session_changed'));const next=await client.prepare(answer()),failure=client.submit(next);client.invalidate();reject(new Error('lost'));
  await assert.rejects(failure,clientError('session_changed'));await assert.rejects(client.retry(next),clientError('session_changed'));
  const before=client.prepare(answer());client.invalidate();await assert.rejects(before,clientError('session_changed'));
});
test('missing session capability and withdrawn capability prevent sends without losing prepared bytes',async()=>{
  await assert.rejects(new RunControlClient(transport({currentSession:()=>null})).prepare(answer()),clientError('session_required'));
  await assert.rejects(new RunControlClient(transport({capability:undefined})).prepare(answer()),clientError('unsupported_operation'));
  let enabled=true,calls=0;const client=new RunControlClient(transport({capability:()=>enabled?'stead.run-command/1':null,command:async raw=>{calls++;enabled=false;return receipt(parseRunControlCommand(raw));}}));
  const p=await client.prepare(answer());enabled=false;await assert.rejects(client.submit(p),clientError('unsupported_operation'));assert.equal(calls,0);
  enabled=true;assert.equal((await client.retry(p)).status,'accepted');assert.equal(calls,1);await assert.rejects(client.retry(p),clientError('unsupported_operation'));
});
test('simultaneous submissions of the same prepared command cannot duplicate a send',async()=>{
  let calls=0,release!:(raw:string)=>void;const client=new RunControlClient(transport({command:()=>{calls++;return new Promise(resolve=>{release=resolve;});}}));
  const p=await client.prepare(cancel()),first=client.submit(p);await assert.rejects(client.retry(p),clientError('command_pending'));assert.equal(calls,1);
  release(receipt(cancel()));assert.equal((await first).status,'accepted');
});

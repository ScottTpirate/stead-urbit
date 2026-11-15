// Host protocol tests, not native authorization or a live carrier.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {DocChangeClient, DocChangeClientError, type DocChangeTransport} from '../src/docChangeClient';
import {docChangeCommandDigest, type DocChangeCommand} from '../src/docChangeProtocol';
import {docChangeDetails, docChangeTarget, encodeDocChangeQuery, parseDocChangeQuery, parseDocChangeReceipt, parseDocChangeView, snapshotDocChangeOutput,
  verifyDocChangeBody, type DocChangeBody, type DocChangeDetail, type DocChangePreview, type DocChangeQuery} from '../src/docChangeReadProtocol';
import {canonical} from '../src/protocol';
import {ProductProtocolError} from '../src/productWire';
const id=(n:number)=>'019939ba-4000-7000-8000-'+String(n).padStart(12,'0');
const sha=(raw:string)=>createHash('sha256').update(raw).digest('hex');
const markdown=`---\nid: ${id(201)}\ntype: page\nstate: published\n---\n# Guide\n\nExact λ text.  \n`;
const target={kind:'document',project_id:id(100),collection_id:id(200),document_id:id(201),expected_revision:'1',base_markdown_sha256:sha(markdown)};
const names=['change.request-changes','change.approve','change.adopt','change.accept','change.reject','change.quarantine'];
const actions=canonical(Object.fromEntries(names.map(name=>[name,{status:'eligible',reason:''}])));
const preview:DocChangePreview={kind:'doc-change',project_id:id(100),work_id:id(101),change_id:id(400),change_revision:'3',change_status:'submitted',current_result_revision:'2',current_result_digest:'b'.repeat(64),
  result_revision:'2',result_digest:'b'.repeat(64),is_current_result:'yes',outcome_id:id(401),target:canonical(target),execution_contract_revision:'4',execution_contract_digest:'c'.repeat(64),
  producer_principal_id:id(103),producer_display_name:'Writer agent',summary:'Clarify the guide.',markdown_sha256:sha(markdown),run_id:'',attempt:'0',submitted_at_ms:'1000'};
const detail:DocChangeDetail={...preview,producer_binding_id:id(104),producer_binding_revision:'2',approval:'',adoption:'',acceptance:'',latest_decision:'',producer_authority:'live',contract_current:'yes',actions};
const query=(kind:DocChangeQuery['kind']='changes',changes:Partial<DocChangeQuery>={}):DocChangeQuery=>({protocol:'stead.doc-change-query/1',request_id:id(700),kind,project_id:id(100),work_id:id(101),
  change_id:kind==='changes'?'':id(400),result_revision:kind==='body'?'2':'0',result_digest:kind==='body'?preview.result_digest:'',side:kind==='body'?'after':'',cursor:'',...changes});
const body=(side:'before'|'after'='after'):DocChangeBody=>({kind:'doc-change-body',project_id:id(100),work_id:id(101),change_id:id(400),result_revision:'2',result_digest:preview.result_digest,side,body_status:'ready',markdown,markdown_sha256:sha(markdown)});
function wire(request:DocChangeQuery,rows:unknown[]=[],changes:Record<string,unknown>={}) {return canonical({protocol:'stead.doc-change-query-result/1',status:'read',request_id:request.request_id,kind:request.kind,
  project_id:request.project_id,work_id:request.work_id,change_id:request.change_id,result_revision:request.result_revision,result_digest:request.result_digest,side:request.side,
  authority_epoch:'1',generation:'d'.repeat(64),cursor:'',rows:Object.fromEntries(rows.map((row,index)=>[String(index),row])),...changes});}
const decision=(operation:DocChangeCommand['operation']='change.approve'):DocChangeCommand=>({protocol:'stead.doc-change/1',request_id:id(800),project_id:id(100),work_id:id(101),change_id:id(400),authority_epoch:'1',expected_revision:'3',
  operation:operation as 'change.approve',payload:{result_revision:'2',result_digest:preview.result_digest,note:'Reviewed exact output.'}});
async function receipt(command:DocChangeCommand,changes:Record<string,unknown>={}) {return canonical({protocol:'stead.doc-change-receipt/1',status:'accepted',request_id:command.request_id,canonical_sha256:await docChangeCommandDigest(command),
  project_id:command.project_id,work_id:command.work_id,change_id:command.change_id,authority_epoch:command.authority_epoch,operation:command.operation,expected_revision:command.expected_revision,
  resulting_revision:'4',result_revision:'2',result_digest:preview.result_digest,change_status:'approved',recorded_at_ms:'2000',error:'',...changes});}
const enabled=()=>({queries:'stead.doc-change-query/1' as const,commands:'stead.doc-change/1' as const});
function transport(changes:Partial<DocChangeTransport>={}):DocChangeTransport {return {currentSession:()=> 'session-one',capabilities:enabled,query:async raw=>wire(parseDocChangeQuery(raw)),command:async()=>{throw new Error('Unexpected command');},...changes};}
const invalid=(operation:()=>unknown)=>assert.throws(operation,error=>error instanceof ProductProtocolError&&error.code==='invalid_response');

test('closed query grammar admits four exact purposes and rejects altered pins version duplicates and scalar types',()=>{
  for(const request of [query(),query('results'),query('change'),query('change',{result_revision:'2',result_digest:preview.result_digest}),query('body'),query('body',{side:'before'})]) assert.deepEqual(JSON.parse(encodeDocChangeQuery(request)),JSON.parse(JSON.stringify(parseDocChangeQuery(JSON.stringify(request)))));
  for(const change of [{protocol:'stead.query/3'},{kind:'comments'},{result_revision:'01'},{result_revision:'18446744073709551616'},{result_revision:1},{change_id:id(400)},{side:'before'},{unknown:''},{cursor:'not-opaque'}]) assert.throws(()=>parseDocChangeQuery(JSON.stringify({...query(),...change})));
  for(const change of [{result_revision:'0'},{result_digest:''},{cursor:'a'.repeat(64)},{side:''}]) assert.throws(()=>parseDocChangeQuery(JSON.stringify({...query('body'),...change})));
  assert.throws(()=>parseDocChangeQuery(encodeDocChangeQuery(query()).replace('"kind":"changes"','"kind":"changes","kind":"changes"')));
});
test('source-derived query and receipt canonical vectors match exact bytes and independent SHA256',async()=>{
  const vectors=JSON.parse(await readFile('tests/doc-change-read-vectors.json','utf8'));
  assert.equal(vectors.classification,'source-derived-expected-values-not-native-execution');
  for(const item of vectors.vectors) {assert.equal(canonical(item.value),item.canonical);assert.equal(sha(item.canonical),item.bytes_sha256);}
  assert.equal(encodeDocChangeQuery(vectors.vectors[0].value),vectors.vectors[0].canonical);
  const prior=JSON.parse(await readFile('tests/doc-change-vectors.json','utf8')).vectors[1];
  assert.equal(parseDocChangeReceipt(vectors.vectors[1].canonical,prior.command,prior.sha256).status,'accepted');
});
test('metadata pages remain closed scoped twenty-row previews with ordered immutable results',()=>{
  const request=query(),view=parseDocChangeView(wire(request,[preview]),request);assert.equal(view.status,'read');if(view.status!=='read')throw new Error('Unexpected rejection');
  assert.equal(Object.keys(view.rows[0]!).length,22);assert.equal(Object.isFrozen(view.rows[0]),true);assert.deepEqual(JSON.parse(preview.target),JSON.parse(JSON.stringify(docChangeTarget(preview))));
  for(const row of [{...preview,work_id:id(999)},{...preview,kind:'work'},{...preview,markdown},{...preview,producer_authentication:'secret'},{...preview,attempt:'1'},{...preview,result_digest:'e'.repeat(64)}]) invalid(()=>parseDocChangeView(wire(request,[row]),request));
  invalid(()=>parseDocChangeView(wire(request,[preview,preview]),request));invalid(()=>parseDocChangeView(wire(request,Array(21).fill(preview)),request));
  invalid(()=>parseDocChangeView(wire(request,[preview],{rows:{'1':preview}}),request));invalid(()=>parseDocChangeView(wire(request,[preview],{cursor:'e'.repeat(64)}),request));
  const resultQuery=query('results'),prior={...preview,result_revision:'1',result_digest:'a'.repeat(64),is_current_result:'no'};
  assert.equal(parseDocChangeView(wire(resultQuery,[prior,preview]),resultQuery).status,'read');invalid(()=>parseDocChangeView(wire(resultQuery,[preview,prior]),resultQuery));
});
test('detail uses thirty-one scalars and closed native eligibility without granting prior results current evidence',()=>{
  const request=query('change'),view=parseDocChangeView(wire(request,[detail]),request);assert.equal(view.status,'read');if(view.status!=='read')throw new Error('Unexpected rejection');assert.equal(Object.keys(view.rows[0]!).length,31);
  assert.equal(docChangeDetails(detail).actions['change.accept'].status,'eligible');
  for(const action of [{status:'eligible',reason:'read_only'},{status:'blocked',reason:''},{status:'unsupported',reason:''},{status:'eligible',reason:'',owner:'yes'}]) {
    const changed=JSON.parse(actions);changed['change.accept']=action;invalid(()=>parseDocChangeView(wire(request,[{...detail,actions:canonical(changed)}]),request));
  }
  const prior={...detail,result_revision:'1',result_digest:'a'.repeat(64),is_current_result:'no' as const,actions:canonical(Object.fromEntries(names.map(name=>[name,{status:'blocked',reason:'superseded_result'}])))};
  const pinned=query('change',{result_revision:'1',result_digest:prior.result_digest});assert.equal(parseDocChangeView(wire(pinned,[prior]),pinned).status,'read');
  invalid(()=>parseDocChangeView(wire(pinned,[{...prior,actions}]),pinned));invalid(()=>parseDocChangeView(wire(request,[prior]),request));
});
test('sanitized evidence preserves feedback outcome and exact result while excluding raw receipts and invented request IDs',()=>{
  const base={principal_id:id(102),display_name:'Reviewer',recorded_at_ms:'2000',note:'Review note',result_digest:detail.result_digest};
  const feedback={...base,operation:'change.request-changes',outcome:'accepted',result_revision:'2',change_revision:'3'};
  const value={...detail,approval:canonical(base),latest_decision:canonical(feedback)};
  assert.equal(docChangeDetails(value).latestDecision!.note,'Review note');assert.equal(Object.hasOwn(docChangeDetails(value).approval!,'request_id'),false);
  for(const changed of [{...base,request_id:id(801)},{...base,authentication_context:'secret'},{...base,result_digest:'e'.repeat(64)},{...base,recorded_at_ms:'0'}]) invalid(()=>docChangeDetails({...detail,approval:canonical(changed)}));
  invalid(()=>docChangeDetails({...detail,latest_decision:canonical({...feedback,change_revision:'4'})}));
  assert.equal(docChangeDetails({...detail,latest_decision:canonical({...feedback,outcome:'producer_quarantined'})}).latestDecision!.outcome,'producer_quarantined');
  const acceptance={principal_id:id(102),display_name:'Reviewer',recorded_at_ms:'2000',document_revision:'2',result_digest:detail.result_digest};
  assert.equal(docChangeDetails({...detail,change_status:'accepted',acceptance:canonical(acceptance)}).acceptance!.document_revision,'2');
  invalid(()=>docChangeDetails({...detail,change_status:'accepted',acceptance:canonical({...acceptance,document_revision:'3'})}));
});
test('one exact body verifies metadata hash scoped pins canonical after bytes and explicit unavailable or new base',async()=>{
  const request=query('body');assert.equal(parseDocChangeView(wire(request,[body()]),request).status,'read');assert.equal(await verifyDocChangeBody(body(),preview).then(value=>value.markdown),markdown);
  for(const altered of [{...body(),markdown:markdown+'changed'},{...body(),work_id:id(999)}]) await assert.rejects(verifyDocChangeBody(altered,preview));
  await assert.rejects(verifyDocChangeBody({...body(),markdown:'No canonical header',markdown_sha256:sha('No canonical header')},{...preview,markdown_sha256:sha('No canonical header')}));
  for(const altered of [{...body(),side:'before'},{...body(),body_status:'unavailable',markdown:''},{...body(),markdown:'x'.repeat(32769)},{...body(),markdown:'bad\r\n'}]) invalid(()=>parseDocChangeView(wire(request,[altered]),request));
  const unavailable={...body('before'),body_status:'unavailable' as const,markdown:''};assert.equal((await verifyDocChangeBody(unavailable,preview)).body_status,'unavailable');
  const empty={...body('before'),body_status:'new-document' as const,markdown:'',markdown_sha256:''},newOutput={...preview,target:canonical({...target,expected_revision:'0',base_markdown_sha256:''})};
  assert.equal((await verifyDocChangeBody(empty,newOutput)).body_status,'new-document');await assert.rejects(verifyDocChangeBody(empty,preview));
});
test('receipts distinguish short rejection full acceptance and rejected quarantine lifecycle advancement',async()=>{
  const command=decision(),digest=await docChangeCommandDigest(command);const accepted=parseDocChangeReceipt(await receipt(command),command,digest);assert.equal(accepted.status,'accepted');
  const short=canonical({protocol:'stead.doc-change-receipt/1',status:'rejected',request_id:command.request_id,canonical_sha256:digest,error:'denied_or_not_found'});assert.equal(parseDocChangeReceipt(short,command,digest).status,'rejected');
  const quarantined=parseDocChangeReceipt(await receipt(command,{status:'rejected',error:'producer_quarantined',change_status:'quarantined'}),command,digest);assert.equal(quarantined.status,'rejected');assert.equal('resulting_revision'in quarantined&&quarantined.resulting_revision,'4');
  for(const changes of [{request_id:id(999)},{canonical_sha256:'e'.repeat(64)},{project_id:id(999)},{expected_revision:'2'},{resulting_revision:'3'},{change_status:'submitted'},{result_revision:'1'},{raw_receipt:'secret'}]) invalid(()=>parseDocChangeReceipt(canonical({...JSON.parse(canonical(accepted)),...changes}),command,digest));
  const closed=await receipt(command,{status:'rejected',error:'revision_conflict',resulting_revision:'8',result_revision:'3',result_digest:'e'.repeat(64),change_status:'submitted'});assert.equal(parseDocChangeReceipt(closed,command,digest).status,'rejected');
});
test('uncorrelated command response remains unknown and exact prepared retry keeps bytes and request identity',async()=>{
  const sent:string[]=[];let attempt=0;const command=decision();const client=new DocChangeClient(transport({command:async bytes=>{sent.push(bytes);return receipt(command,++attempt===1?{request_id:id(999)}:{});}}));
  const prepared=await client.prepare(command);assert.equal(Object.isFrozen(prepared.command.payload),true);
  await assert.rejects(client.submit(prepared),error=>error instanceof DocChangeClientError&&error.code==='outcome_unknown');assert.equal((await client.retry(prepared)).status,'accepted');
  assert.equal(sent.length,2);assert.equal(sent[0],sent[1]);await assert.rejects(client.submit({...prepared}),error=>error instanceof DocChangeClientError&&error.code==='unrecognized_prepared_command');
});
test('capabilities default unavailable and read capability withdrawal suppresses late publication',async()=>{
  let calls=0,enabledNow=true,release!:(raw:string)=>void;
  const absent=new DocChangeClient(transport({capabilities:undefined,query:async()=>{calls++;return '';},command:async()=>{calls++;return '';}}));
  await assert.rejects(absent.read(query()),error=>error instanceof DocChangeClientError&&error.code==='unsupported_operation');await assert.rejects(absent.prepare(decision()));assert.equal(calls,0);
  const client=new DocChangeClient(transport({capabilities:()=>enabledNow?enabled():{queries:null,commands:null},query:()=>new Promise(resolve=>{release=resolve;})}));
  const pending=client.read(query());enabledNow=false;release(wire(query(),[preview]));await assert.rejects(pending,error=>error instanceof DocChangeClientError&&error.code==='unsupported_operation');
});
test('opaque session change suppresses stale command and read replies and forbids original retry',async()=>{
  let token:object={},release!:(raw:string)=>void;const command=decision();
  const client=new DocChangeClient(transport({currentSession:()=>token,command:()=>new Promise(resolve=>{release=resolve;})}));const prepared=await client.prepare(command),pending=client.submit(prepared);token={};release(await receipt(command));
  await assert.rejects(pending,error=>error instanceof DocChangeClientError&&error.code==='session_changed');await assert.rejects(client.retry(prepared),error=>error instanceof DocChangeClientError&&error.code==='session_changed');
  const reads=new DocChangeClient(transport({currentSession:()=>token,query:()=>new Promise(resolve=>{release=resolve;})}));const reading=reads.read(query());token={};release(wire(query(),[preview]));await assert.rejects(reading,error=>error instanceof DocChangeClientError&&error.code==='session_changed');
});
test('one-use cursors bind exact purpose scope epoch generation and never silently retry unknown consumption',async()=>{
  const cursor='e'.repeat(64),page=Array.from({length:20},(_,n)=>({...preview,change_id:id(400+n)}));let calls=0;
  const client=new DocChangeClient(transport({query:async raw=>{const request=parseDocChangeQuery(raw);calls++;if(!request.cursor)return wire(request,page,{cursor});return wire(request,[],{generation:'f'.repeat(64)});}}));
  await client.read(query());await assert.rejects(client.read(query('results',{cursor})),error=>error instanceof DocChangeClientError&&error.code==='stale_cursor');assert.equal(calls,1);
  await assert.rejects(client.read(query('changes',{cursor})),error=>error instanceof DocChangeClientError&&error.code==='stale_cursor');assert.equal(calls,2);
  await assert.rejects(client.read(query('changes',{cursor})));assert.equal(calls,2);
  const lost=new DocChangeClient(transport({query:async raw=>{const request=parseDocChangeQuery(raw);if(!request.cursor)return wire(request,page,{cursor});throw new Error('Lost continuation');}}));
  await lost.read(query());await assert.rejects(lost.read(query('changes',{cursor})),error=>error instanceof DocChangeClientError&&error.code==='outcome_unknown');await assert.rejects(lost.read(query('changes',{cursor})),error=>error instanceof DocChangeClientError&&error.code==='stale_cursor');
});
test('late old-session replies cannot erase a newly acquired current-session continuation',async()=>{
  let token:object={},release!:(raw:string)=>void,first=true;const cursor='e'.repeat(64),page=Array.from({length:20},(_,n)=>({...preview,change_id:id(400+n)}));
  const client=new DocChangeClient(transport({currentSession:()=>token,query:async raw=>{const request=parseDocChangeQuery(raw);if(first){first=false;return new Promise(resolve=>{release=resolve;});}return wire(request,request.cursor?[]:page,{cursor:request.cursor?'':cursor});}}));
  const old=client.read(query());token={};await client.read(query('changes',{request_id:id(701)}));release(wire(query(),page,{cursor:'f'.repeat(64)}));await assert.rejects(old);
  assert.equal((await client.read(query('changes',{request_id:id(702),cursor}))).status,'read');
});
test('body requests snapshot expected metadata before transport and never accept retargeted mutable pins',async()=>{
  let calls=0,release!:(raw:string)=>void;const mutable={...preview};const client=new DocChangeClient(transport({query:raw=>{calls++;const request=parseDocChangeQuery(raw);return new Promise(resolve=>{release=()=>resolve(wire(request,[body()]));});}}));
  const pending=client.readBody(id(703),mutable,'after');mutable.markdown_sha256='f'.repeat(64);release('');assert.equal((await pending).status,'read');
  await assert.rejects(client.read(query('body')));assert.equal(calls,1);
  await assert.rejects(client.read(query('body'),{...preview,work_id:id(999)}));assert.equal(calls,1);
  assert.equal(Object.isFrozen(snapshotDocChangeOutput(preview,query('body'))),true);
});
test('read failures keep rejected responses distinct from malformed bodies and forged exact-content hashes',async()=>{
  const denied=new DocChangeClient(transport({query:async raw=>canonical({protocol:'stead.doc-change-query-result/1',status:'rejected',request_id:parseDocChangeQuery(raw).request_id,error:'denied_or_not_found'})}));
  const result=await denied.read(query());assert.equal(result.status,'rejected');
  const forged=new DocChangeClient(transport({query:async raw=>wire(parseDocChangeQuery(raw),[{...body(),markdown:'changed'}])}));await assert.rejects(forged.readBody(id(704),preview,'after'),error=>error instanceof ProductProtocolError&&error.code==='invalid_response');
  const malformed=new DocChangeClient(transport({query:async()=>'{bad'}));await assert.rejects(malformed.read(query()),error=>error instanceof ProductProtocolError&&error.code==='invalid_response');
});
test('nested scalar JSON is canonical duplicate-free bounded and never admits credential or receipt fields',()=>{
  const request=query('change'),raw=wire(request,[detail]);invalid(()=>parseDocChangeView(raw.replace('"status":"read"','"status":"read","status":"read"'),request));
  for(const altered of [{...detail,target:detail.target.replace('"kind":"document"','"kind":"document","kind":"document"')},{...detail,target:' '+detail.target},
    {...detail,summary:'x'.repeat(2049)},{...detail,producer_display_name:'x'.repeat(201)},{...detail,producer_binding_revision:'18446744073709551616'},
    {...detail,actions:canonical({...JSON.parse(actions),authorization:'yes'})},{...detail,approval:'{"authentication_context":"secret"}'}]) invalid(()=>parseDocChangeView(wire(request,[altered]),request));
  invalid(()=>parseDocChangeView(raw+' '.repeat(262144),request));invalid(()=>parseDocChangeView(wire(request,[detail],{request_id:id(999)}),request));
});

// Injected host adapter and static markup tests. No native or live UI acceptance.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {DocChangeClient, DocChangeClientError, type DocChangeTransport} from '../src/docChangeClient';
import {DocChangeReviewAdapter, DocReviewAdapterError, docReviewSubmitter, mapDocReviewDetail, mapDocReviewList, type DocReviewReadRequest} from '../src/docChangeReviewAdapter';
import {DocChangeReview} from '../src/docChangeReview';
import {docChangeCommandDigest, parseDocChangeCommand} from '../src/docChangeProtocol';
import {parseDocChangeQuery, parseDocChangeView, type DocChangeDetail, type DocChangeQuery, type DocChangeView} from '../src/docChangeReadProtocol';
import {canonical} from '../src/protocol';
const id=(n:number)=>'019939ba-4000-7000-8000-'+String(n).padStart(12,'0'),sha=(raw:string)=>createHash('sha256').update(raw).digest('hex');
const markdown=`---\nid: ${id(201)}\ntype: page\nstate: published\n---\n# Exact proposed guide\n`;
const scope={projectId:id(100),workId:id(101),changeId:id(400)},request:DocReviewReadRequest={scope,sessionKey:'session-one'};
const actionNames=['change.request-changes','change.approve','change.adopt','change.accept','change.reject','change.quarantine'];
const row:DocChangeDetail={kind:'doc-change',project_id:scope.projectId,work_id:scope.workId,change_id:scope.changeId,change_revision:'3',change_status:'submitted',current_result_revision:'2',current_result_digest:'b'.repeat(64),result_revision:'2',result_digest:'b'.repeat(64),is_current_result:'yes',
  outcome_id:id(401),target:canonical({kind:'document',project_id:id(100),collection_id:id(200),document_id:id(201),expected_revision:'1',base_markdown_sha256:sha(markdown)}),execution_contract_revision:'4',execution_contract_digest:'c'.repeat(64),producer_principal_id:id(103),producer_display_name:'',summary:'Revise the shared guide.',markdown_sha256:sha(markdown),run_id:'',attempt:'0',submitted_at_ms:'1000',
  producer_binding_id:id(104),producer_binding_revision:'1',approval:'',adoption:'',acceptance:'',latest_decision:'',producer_authority:'live',contract_current:'yes',actions:canonical(Object.fromEntries(actionNames.map(name=>[name,{status:'eligible',reason:''}])))};
function reply(query:DocChangeQuery, changes:Record<string,unknown>={}, overrideRow:unknown=undefined) {
  const content=overrideRow??(query.kind==='change'?{...row,project_id:query.project_id,work_id:query.work_id,change_id:query.change_id}:{kind:'doc-change-body',project_id:query.project_id,work_id:query.work_id,change_id:query.change_id,result_revision:query.result_revision,result_digest:query.result_digest,side:query.side,body_status:'ready',markdown,markdown_sha256:sha(markdown)});
  return canonical({protocol:'stead.doc-change-query-result/1',status:'read',request_id:query.request_id,kind:query.kind,project_id:query.project_id,work_id:query.work_id,change_id:query.change_id,result_revision:query.result_revision,result_digest:query.result_digest,side:query.side,
    authority_epoch:'1',generation:(query.kind==='body'?(query.side==='before'?'e':'f'):'d').repeat(64),cursor:'',rows:{'0':content},...changes});
}
function denied(query:DocChangeQuery){return canonical({protocol:'stead.doc-change-query-result/1',status:'rejected',request_id:query.request_id,error:'denied_or_not_found'});}
function transport(changes:Partial<DocChangeTransport>={}):DocChangeTransport{return {currentSession:()=> 'token-one',capabilities:()=>({queries:'stead.doc-change-query/1',commands:'stead.doc-change/1'}),query:async raw=>reply(parseDocChangeQuery(raw)),command:async()=>{throw new Error('No command expected');},...changes};}
const detailQuery:DocChangeQuery={protocol:'stead.doc-change-query/1',request_id:id(700),kind:'change',project_id:scope.projectId,work_id:scope.workId,change_id:scope.changeId,result_revision:'0',result_digest:'',side:'',cursor:''};
function detailView(value:DocChangeDetail=row){return parseDocChangeView(reply(detailQuery,{},value),detailQuery) as Extract<DocChangeView,{kind:'change'}>;}

test('native detail maps exact pins and eligibility reasons without inventing labels request IDs or acceptance',()=>{
  const values=JSON.parse(row.actions);values['change.accept']={status:'blocked',reason:'read_only'};
  const feedback={operation:'change.approve',outcome:'producer_quarantined',principal_id:id(102),display_name:'Reviewer',recorded_at_ms:'2000',note:'Exact note',result_revision:'2',result_digest:row.result_digest,change_revision:'3'};
  const mapped=mapDocReviewDetail(detailView({...row,actions:canonical(values),latest_decision:canonical(feedback)}),request);
  assert.equal(mapped.eligibility.actions['change.approve'].reason,'none');assert.equal(mapped.eligibility.actions['change.accept'].reason,'read_only');
  assert.equal(mapped.snapshot.output.targetLabel,'');assert.equal(mapped.snapshot.output.producer.displayName,'');assert.equal(mapped.snapshot.feedback!.outcome,'producer_quarantined');
  assert.equal(mapped.snapshot.feedback!.requestId,undefined);assert.equal(mapped.snapshot.acceptance,undefined);
  assert.equal(mapDocReviewDetail(detailView(),{...request,targetLabel:{projectId:id(100),collectionId:id(200),documentId:id(999),label:'Wrong Doc'}}).snapshot.output.targetLabel,'');
  assert.equal(mapDocReviewDetail(detailView(),{...request,targetLabel:{projectId:id(100),collectionId:id(200),documentId:id(201),label:'Shared guide'}}).snapshot.output.targetLabel,'Shared guide');
  const {producer_binding_id,producer_binding_revision,approval,adoption,acceptance,latest_decision,producer_authority,contract_current,actions,...preview}=row;
  const listQuery={...detailQuery,kind:'changes' as const,change_id:''},listView=parseDocChangeView(reply(listQuery,{},preview),listQuery);
  if(listView.status!=='read')throw new Error('Unexpected rejection');const list=mapDocReviewList(listView,{projectId:scope.projectId,workId:scope.workId,sessionKey:request.sessionKey});
  assert.equal(list.rows[0]!.targetLabel,'');assert.equal(list.rows[0]!.changeId,scope.changeId);assert.equal(Object.isFrozen(list.rows),true);
  assert.throws(()=>mapDocReviewList(listView,{projectId:id(999),workId:scope.workId,sessionKey:request.sessionKey}));
});
test('four bounded reads publish fresh authorization only after exact detail and bodies with independent generations',async()=>{
  const calls:DocChangeQuery[]=[];const adapter=new DocChangeReviewAdapter(new DocChangeClient(transport({query:async raw=>{const q=parseDocChangeQuery(raw);calls.push(q);return reply(q);}})),()=>{throw new Error('Unexpected denial');});
  const loaded=await adapter.load(request);assert.deepEqual(calls.map(q=>q.kind),['change','body','body','change']);assert.deepEqual(calls.filter(q=>q.kind==='body').map(q=>q.side),['before','after']);
  assert.equal(loaded.before.state,'ready');assert.equal(loaded.after.state,'ready');assert.equal(loaded.snapshot.generation,'d'.repeat(64));assert.equal(Object.isFrozen(loaded.authorizedReadToken),true);
  const next=await adapter.load(request);assert.notEqual(next.authorizedReadToken,loaded.authorizedReadToken);
  const missing=new DocChangeReviewAdapter(new DocChangeClient(transport({query:async raw=>{const q=parseDocChangeQuery(raw);if(q.kind==='body'&&q.side==='before')return reply(q,{}, {kind:'doc-change-body',project_id:q.project_id,work_id:q.work_id,change_id:q.change_id,result_revision:q.result_revision,result_digest:q.result_digest,side:'before',body_status:'unavailable',markdown:'',markdown_sha256:sha(markdown)});return reply(q);}})),()=>{});
  assert.equal((await missing.load(request)).before.state,'unavailable');
});
test('detail lifecycle drift or same-generation inconsistent metadata cannot publish a fresh review token',async()=>{
  for(const changed of [{generation:'a'.repeat(64)},{}]) {
    let details=0;const adapter=new DocChangeReviewAdapter(new DocChangeClient(transport({query:async raw=>{const q=parseDocChangeQuery(raw);if(q.kind==='change'&&++details===2)return reply(q,changed,Object.keys(changed).length?row:{...row,summary:'Changed despite same generation'});return reply(q);}})),()=>{throw new Error('Unexpected denial');});
    await assert.rejects(adapter.load(request),error=>error instanceof DocReviewAdapterError&&error.code==='read_changed');
  }
});
test('current denied body closes the parent scope and publishes neither body nor a fresh authorization token',async()=>{
  const invalidations:unknown[]=[];let reads=0;const adapter=new DocChangeReviewAdapter(new DocChangeClient(transport({query:async raw=>{reads++;const q=parseDocChangeQuery(raw);return q.kind==='body'?denied(q):reply(q);}})),(scope,session)=>{invalidations.push([scope,session]);});
  await assert.rejects(adapter.load(request),error=>error instanceof DocReviewAdapterError&&error.code==='denied_or_not_found');assert.equal(reads,2);assert.deepEqual(invalidations,[[scope,'session-one']]);
});
test('late A to B to A denied reads cannot invalidate a newer review or publish stale errors',async()=>{
  let first=true,release!:()=>void;let invalidations=0;const adapter=new DocChangeReviewAdapter(new DocChangeClient(transport({query:async raw=>{const q=parseDocChangeQuery(raw);if(first){first=false;return new Promise(resolve=>{release=()=>resolve(denied(q));});}return reply(q);}})),()=>{invalidations++;});
  const old=adapter.load(request);await adapter.load({...request,scope:{...scope,changeId:id(499)}});const current=await adapter.load(request);release();
  await assert.rejects(old,error=>error instanceof DocReviewAdapterError&&error.code==='view_changed');assert.equal(invalidations,0);assert.equal(current.snapshot.scope.changeId,id(400));
  let denyOnce=true,callbackReady!:()=>void,releaseCallback!:()=>void;const callbackStarted=new Promise<void>(resolve=>{callbackReady=resolve;});
  const deferred=new DocChangeReviewAdapter(new DocChangeClient(transport({query:async raw=>{const q=parseDocChangeQuery(raw);if(denyOnce){denyOnce=false;return denied(q);}return reply(q);}})),
    ()=>new Promise<void>(resolve=>{releaseCallback=resolve;callbackReady();}));
  const deniedThenSuperseded=deferred.load(request);await callbackStarted;const fresh=await deferred.load(request);releaseCallback();
  await assert.rejects(deniedThenSuperseded,error=>error instanceof DocReviewAdapterError&&error.code==='view_changed');assert.equal(fresh.snapshot.scope.changeId,id(400));
});
test('session switches and explicit cancellation fence in-flight body reads without parent invalidation',async()=>{
  for(const mode of ['session','cancel']) {
    let token:object={},release!:()=>void,ready!:()=>void;const waiting=new Promise<void>(resolve=>{ready=resolve;});let invalidations=0;
    const adapter=new DocChangeReviewAdapter(new DocChangeClient(transport({currentSession:()=>token,query:async raw=>{const q=parseDocChangeQuery(raw);if(q.kind==='body')return new Promise(resolve=>{release=()=>resolve(denied(q));ready();});return reply(q);}})),()=>{invalidations++;});
    const pending=adapter.load(request);await waiting;if(mode==='session')token={};else adapter.cancel();release();await assert.rejects(pending,error=>error instanceof DocReviewAdapterError&&error.code==='view_changed');assert.equal(invalidations,0);
  }
});
test('review submitter retains the actual frozen client request through unknown retry and rejected quarantine',async()=>{
  const sent:string[]=[];let first=true;const client=new DocChangeClient(transport({command:async raw=>{sent.push(raw);const command=parseDocChangeCommand(raw);if(first){first=false;throw new Error('Unknown transport outcome');}
    return canonical({protocol:'stead.doc-change-receipt/1',status:'rejected',request_id:command.request_id,canonical_sha256:await docChangeCommandDigest(command),project_id:command.project_id,work_id:command.work_id,change_id:command.change_id,
      authority_epoch:command.authority_epoch,operation:command.operation,expected_revision:command.expected_revision,resulting_revision:'4',result_revision:'2',result_digest:row.result_digest,change_status:'quarantined',recorded_at_ms:'2000',error:'producer_quarantined'});}}));
  const submitter=docReviewSubmitter(client),prepared=await submitter.prepare({protocol:'stead.doc-change/1',request_id:id(800),project_id:id(100),work_id:id(101),change_id:id(400),authority_epoch:'1',expected_revision:'3',operation:'change.approve',payload:{result_revision:'2',result_digest:row.result_digest,note:''}});
  await assert.rejects(submitter.submit(prepared),error=>error instanceof DocChangeClientError&&error.code==='outcome_unknown');assert.deepEqual(await submitter.submit(prepared),{status:'rejected',reason:'producer_quarantined'});
  assert.equal(sent[0],sent[1]);assert.equal(Object.isFrozen(prepared.command.payload),true);assert.equal((await client.retry(prepared)).status,'rejected');
});
test('static review keeps distinct evidence without request IDs and labels quarantine as a rejected decision',()=>{
  const base={principal_id:id(102),display_name:'Reviewer',recorded_at_ms:'2000',note:'Approved note',result_digest:row.result_digest};
  const feedback={...base,operation:'change.request-changes',outcome:'producer_quarantined',note:'Latest feedback',result_revision:'2',change_revision:'3'};
  const mapped=mapDocReviewDetail(detailView({...row,approval:canonical(base),latest_decision:canonical(feedback)}),request);
  const html=renderToStaticMarkup(createElement(DocChangeReview,{...mapped,scope,sessionKey:request.sessionKey,supported:true,access:'writable',online:true,authorizedReadToken:{},submitter:docReviewSubmitter(new DocChangeClient(transport())),onDraftState:()=>{},onRefresh:()=>{},onAccessChanged:()=>{},onAccepted:()=>{}}));
  assert.match(html,/Recorded approval/u);assert.match(html,/Output quarantined/u);assert.match(html,/requested decision was rejected/u);assert.doesNotMatch(html,/<dt>Request<\/dt>/u);assert.match(html,/Project member/u);
});

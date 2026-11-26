import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {RunHistoryContent, RunHistoryController, runLeaseLabel, type RunHistorySnapshot} from '../src/RunHistory';
import {parseRunQuery, type RunQuery} from '../src/runReadProtocol';
import {canonical} from '../src/protocol';
import {client, detail, fixtureTime, id, preview, properties, wire} from './run-history-fixture';
function markup(snapshot: RunHistorySnapshot, online = true, selected?: string) { return renderToStaticMarkup(createElement(RunHistoryContent,{snapshot,online,locked:false,now:fixtureTime+10000,selected,
  onRefresh:()=>{},onMore:()=>{},onSelect:()=>{},onOpenChange:()=>{}})); }
const visibleText = (html: string) => html.replace(/<details\b[\s\S]*?<\/details>/gu,'').replace(/<[^>]+>/gu,'');

test('loading unsupported revoked and locked states make no unauthorized read',async()=>{
  let calls=0;const value=client({query:async()=>{calls++;throw new Error();}}),model=new RunHistoryController();
  model.configure(properties(null));assert.equal(model.snapshot().phase,'unsupported');await model.load();
  model.configure(properties(value,{access:'revoked'}));assert.equal(model.snapshot().phase,'revoked');await model.load();
  model.configure(properties(value,{access:'loading'}));assert.equal(model.snapshot().phase,'loading');await model.load();
  model.configure(properties(value,{locked:true}));await model.load();assert.equal(calls,0);
});
test('authorized list and detail publish only exact scoped native-shaped data',async()=>{
  const queries:RunQuery[]=[],value=client({query:async raw=>{const request=parseRunQuery(raw);queries.push(request);return wire(request,request.kind==='run'?[detail()]:[preview()]);}}),model=new RunHistoryController();
  const props=properties(value);model.configure(props);await model.load();assert.equal(model.snapshot().phase,'ready');assert.equal(model.snapshot().rows.length,1);
  assert.equal(queries[0]!.project_id,props.projectId);assert.equal(queries[0]!.work_id,props.workId);
  model.configure({...props,selectedRunId:id(400)});assert.equal(model.snapshot().rows.length,0);assert.equal(model.snapshot().detail,undefined);
  await model.load();assert.equal(model.snapshot().detail!.run_id,id(400));assert.equal(queries[1]!.kind,'run');
});
test('submitted output callback binds exact result and is disabled for locked offline or changed sessions',async()=>{
  let token:object={},opened:string[][]=[];const value=client({currentSession:()=>token,query:async raw=>wire(parseRunQuery(raw),[detail(400,'submitted')])});
  const model=new RunHistoryController(),props=properties(value,{selectedRunId:id(400),onOpenChange:(...args)=>opened.push(args)});
  model.configure(props);await model.load();model.openChange();assert.deepEqual(opened,[[id(100),id(101),id(500),'2','b'.repeat(64)]]);
  model.configure({...props,locked:true});model.openChange();model.configure({...props,online:false});model.openChange();
  token={};model.configure(props);model.openChange();assert.equal(model.snapshot().phase,'revoked');assert.equal(model.snapshot().detail,undefined);assert.equal(opened.length,1);
});
test('selection A to B to A rejects late success and denial without stale callbacks',async()=>{
  const waiting:Array<{request:RunQuery;resolve:(raw:string)=>void;reject:(error:Error)=>void}>=[];let denied=0,errors=0;
  const value=client({query:raw=>new Promise((resolve,reject)=>waiting.push({request:parseRunQuery(raw),resolve,reject}))});
  const model=new RunHistoryController(),props=properties(value,{selectedRunId:id(400),onAccessChanged:()=>{denied++;},onError:()=>{errors++;}});
  model.configure(props);const first=model.load();model.configure({...props,selectedRunId:id(401)});const second=model.load();model.configure(props);const last=model.load();
  waiting[2]!.resolve(wire(waiting[2]!.request,[{...detail(),owner_display_name:'Current owner'}]));await last;
  waiting[0]!.resolve(canonical({protocol:'stead.run-query-result/1',status:'rejected',request_id:waiting[0]!.request.request_id,error:'denied_or_not_found'}));await first;
  waiting[1]!.reject(new Error('Older read failed'));await second;assert.equal(model.snapshot().detail!.owner_display_name,'Current owner');assert.equal(denied,0);assert.equal(errors,0);
});
test('actual token or view scope change hides content immediately and fences in-flight publication',async()=>{
  let token:object={},resolve!:(raw:string)=>void,request!:RunQuery;
  const value=client({currentSession:()=>token,query:raw=>{request=parseRunQuery(raw);return new Promise(done=>{resolve=done;});}}),model=new RunHistoryController(),props=properties(value);
  model.configure(props);const first=model.load();token={};resolve(wire(request,[preview()]));await first;assert.equal(model.snapshot().phase,'revoked');assert.equal(model.snapshot().rows.length,0);
  model.configure({...props,sessionKey:'ui-session-B'});const second=model.load();resolve(wire(request,[preview()]));await second;assert.equal(model.snapshot().rows.length,1);
  model.configure({...props,sessionKey:'ui-session-B',workId:id(105)});assert.equal(model.snapshot().rows.length,0);assert.equal(model.snapshot().phase,'loading');
});
test('offline retains only same-token scope as stale and reconnect requires explicit refresh',async()=>{
  let calls=0;const value=client({query:async raw=>{calls++;return wire(parseRunQuery(raw),[preview()]);}}),model=new RunHistoryController(),props=properties(value);
  model.configure(props);await model.load();model.configure({...props,online:false});assert.equal(model.snapshot().phase,'offline');assert.equal(model.snapshot().rows.length,1);assert.equal(model.canNavigate(),false);
  await model.load();assert.equal(calls,1);model.configure(props);assert.equal(model.snapshot().phase,'offline');assert.equal(calls,1);
  await model.load();assert.equal(calls,2);assert.equal(model.snapshot().phase,'ready');model.configure({...props,online:false,workId:id(105)});assert.equal(model.snapshot().rows.length,0);
});
test('capability withdrawal hides old rows and does not turn unsupported into offline retention',async()=>{
  let allowed=true;const value=client({capability:()=>allowed?'stead.run-query/1':null}),model=new RunHistoryController(),props=properties(value);
  model.configure(props);await model.load();assert.equal(model.snapshot().rows.length,1);allowed=false;
  assert.equal(model.canNavigate(),false);model.configure(props);assert.equal(model.snapshot().phase,'unsupported');assert.equal(model.snapshot().rows.length,0);
  model.configure({...props,online:false});assert.equal(model.snapshot().phase,'unsupported');model.configure({...props,client:null});assert.equal(model.snapshot().rows.length,0);
  let request!:RunQuery,resolve!:(raw:string)=>void;allowed=true;
  const delayed=client({capability:()=>allowed?'stead.run-query/1':null,query:raw=>{request=parseRunQuery(raw);return new Promise(done=>{resolve=done;});}});
  model.configure(properties(delayed));const pending=model.load();allowed=false;resolve(wire(request,[preview()]));await pending;
  assert.equal(model.snapshot().phase,'unsupported');assert.equal(model.snapshot().rows.length,0);
});
test('one-use pagination is single flight and stale cursor clears pages until first-page refresh',async()=>{
  let calls=0,request!:RunQuery,resolve!:(raw:string)=>void;const page=Array.from({length:20},(_,n)=>preview(400+n)),cursor='d'.repeat(64);
  const value=client({query:raw=>{calls++;request=parseRunQuery(raw);if(!request.cursor)return Promise.resolve(wire(request,page,{cursor}));return new Promise(done=>{resolve=done;});}}),model=new RunHistoryController();
  model.configure(properties(value));await model.load();const more=model.load(true);await model.load(true);assert.equal(calls,2);assert.equal(model.snapshot().cursor,'');
  resolve(wire(request,[],{generation:'e'.repeat(64)}));await more;assert.equal(model.snapshot().phase,'expired');assert.equal(model.snapshot().rows.length,0);
  await model.load(true);assert.equal(calls,2);await model.load();assert.equal(calls,3);assert.equal(model.snapshot().rows.length,20);
});
test('current denial clears protected data before scoped callback and ignores late callback completion',async()=>{
  let denial=false,release!:()=>void,started!:()=>void,errors=0,scope:unknown;const model=new RunHistoryController(),entered=new Promise<void>(resolve=>{started=resolve;});
  const value=client({query:async raw=>{const q=parseRunQuery(raw);return denial?canonical({protocol:'stead.run-query-result/1',status:'rejected',request_id:q.request_id,error:'denied_or_not_found'}):wire(q,[preview()]);}});
  const props=properties(value,{onAccessChanged:async found=>{scope=found;assert.equal(model.snapshot().rows.length,0);assert.equal(model.snapshot().phase,'revoked');await new Promise<void>(done=>{release=done;started();});},onError:()=>{errors++;}});
  model.configure(props);await model.load();denial=true;const pending=model.load();await entered;
  assert.deepEqual(scope,{projectId:id(100),workId:id(101)});model.configure({...props,workId:id(105)});release();await pending;assert.equal(errors,0);assert.equal(model.snapshot().phase,'loading');
});
test('static detail keeps IDs in Details and never presents submitted as accepted or exposes execution controls',()=>{
  const row={...detail(400,'submitted'),worker_display_name:''},html=markup({phase:'ready',rows:[],cursor:'',detail:row},true,row.run_id),text=visibleText(html);
  assert.match(text,/Name unavailable/u);assert.match(text,/Owner/u);assert.match(text,/Working on it/u);assert.match(text,/Submitted Doc output/u);
  assert.match(text,/Submission does not mean this output has been accepted or the Work is Done/u);
  for(const value of [row.run_id,row.work_id,row.owner_principal_id,'b'.repeat(64)])assert.ok(!text.includes(value));
  assert.match(html,/<summary>Details<\/summary>/u);assert.match(html,/Open submitted Doc change/u);assert.doesNotMatch(html,/>Claim<|>Answer<\/button|>Stop work<|>Resume<|>Complete<|<progress/u);
});
test('static protected states suppress even accidentally retained rows and expose accessible recovery',()=>{
  for(const phase of ['loading','error','expired','revoked','unsupported'] as const){const html=markup({phase,rows:[preview()],cursor:'d'.repeat(64),detail:detail()},true,id(400));assert.ok(!html.includes('Atlas'));assert.ok(!html.includes(id(400)));}
  const offline=markup({phase:'offline',rows:[],cursor:'',detail:detail(400,'submitted')},false,id(400));assert.match(offline,/role="status"/u);assert.match(offline,/Offline/u);assert.match(offline,/disabled=""[^>]*data-resource-route|data-resource-route="[^"]+"[^>]*disabled=""/u);
  assert.match(markup({phase:'ready',rows:[],cursor:''}),/No runs yet/u);
});
test('lease observations never synthesize progress or make a passed lease look live',()=>{
  const row=detail(400,'running');assert.equal(runLeaseLabel(row,fixtureTime+10000,false),'Lease observed live');assert.equal(runLeaseLabel(row,fixtureTime+120000,false),'Lease check is out of date');
  assert.equal(runLeaseLabel(row,fixtureTime+10000,true),'Lease needs a fresh check');assert.equal(row.phase,'running');assert.equal(runLeaseLabel({...row,lease_state:'expired'},fixtureTime,false),'Lease expired');
  assert.equal(runLeaseLabel({...row,lease_state:'terminal',phase:'canceled'},fixtureTime,false),'No active execution lease');
  const html=markup({phase:'ready',rows:[],cursor:'',detail:detail()},true,id(400));assert.match(html,/Latest clarification/u);assert.match(html,/Clarify the final step/u);assert.doesNotMatch(html,/\d+%/u);
  const queued={...preview(),phase:'queued' as const,current_attempt:'0',lease_state:'none' as const,lease_until_ms:'0'};
  const queuedHtml=markup({phase:'ready',rows:[queued],cursor:''});assert.match(queuedHtml,/Run requested/u);assert.doesNotMatch(queuedHtml,/Run started/u);assert.match(queuedHtml,/No execution lease/u);
});

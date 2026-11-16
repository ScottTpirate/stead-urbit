import test from 'node:test';
import assert from 'node:assert/strict';
import {HomeError, type Query, type Row, type View} from '../src/api';
import {ContextualSearch, contextChoiceKey, type ContextSearchScope} from '../src/contextualSearch';
import type {ProductCarrierMode} from '../src/productCarrier';
const id=(n:number)=>'019939ba-4000-7000-8000-'+String(n).padStart(12,'0');
const cursor=(n:number)=>String(n).padStart(64,'0');
const project=id(100),work=id(101),collection=id(102);
const row=(n:number,kind:'work'|'document'='work'):Row=>({kind,project_id:project,resource_id:id(n),container_id:kind==='work'?'':collection,title:kind==='work'?`Task ${n}`:`# Guide ${n}`});
function response(query:Query,rows:Row[],more='',generation='a'.repeat(64),epoch='1'):View{return{protocol:'stead.query-result/3',request_id:id(900),status:'read',kind:query.kind,project_id:query.project_id,container_id:query.container_id,resource_id:query.resource_id,authority_epoch:epoch,generation,cursor:more,rows:Object.fromEntries(rows.map((r,i)=>[String(i),r]))};}
function deferred<T>(){let resolve!:(value:T)=>void;let reject!:(failure:unknown)=>void;return{promise:new Promise<T>((yes,no)=>{resolve=yes;reject=no;}),resolve,reject};}
function setup(){
 let token:object|null={},mode:ProductCarrierMode={kind:'legacy'};
 const calls:Query[]=[];
 let answer:(query:Query)=>Promise<View>=async query=>response(query,[row(200,'document')]);
 const client={query:async(query:Query)=>{calls.push(query);return answer(query);},currentSessionToken:()=>token,productMode:()=>mode};
 const scope:ContextSearchScope={client,project,work,relation:'support',kind:'document',term:'guide',revision:1,writable:true,locked:false,online:true};
 const search=new ContextualSearch();search.configure(scope);
 return{search,scope,calls,setAnswer(value:typeof answer){answer=value;},setToken(value:object|null){token=value;},setMode(value:ProductCarrierMode){mode=value;}};
}
test('Mixed first page exposes a continuation and the later Doc retains exact scoped identity',async()=>{
 const c=setup();c.setAnswer(async q=>q.cursor?response(q,[row(300,'document')]):response(q,Array.from({length:20},(_,n)=>row(200+n)),cursor(1)));
 assert.equal(await c.search.first(),true);assert.deepEqual(c.search.state().page?.choices,[]);assert.equal(c.search.state().page?.cursor,cursor(1));
 await c.search.next();assert.equal(c.search.state().page?.number,2);assert.equal(contextChoiceKey(c.search.state().page!.choices[0]!),`document/${collection}/${id(300)}`);
 assert.deepEqual(c.calls.map(q=>[q.project_id,q.kind,q.search,q.cursor]),[[project,'search','guide',''],[project,'search','guide',cursor(1)]]);
});
test('Only current-page choices remain and a pending continuation cannot retain an old selected target',async()=>{
 const c=setup(),held=deferred<View>();c.setAnswer(async q=>q.cursor?held.promise:response(q,Array.from({length:20},(_,n)=>row(200+n,'document')),cursor(1)));
 await c.search.first();const pending=c.search.next();assert.equal(c.search.state().phase,'loading');assert.equal(c.search.state().page,undefined);
 held.resolve(response(c.calls.at(-1)!,[row(300)]));await pending;assert.equal(c.search.state().phase,'ready');assert.deepEqual(c.search.state().page?.choices,[]);assert.equal(c.search.state().page?.cursor,'');
});
test('A failed consumed continuation cannot be retried and Start over uses a fresh empty cursor',async()=>{
 const c=setup();c.setAnswer(async q=>{if(q.cursor)throw new HomeError('outcome_unknown');return response(q,Array.from({length:20},(_,n)=>row(200+n)),cursor(1));});
 await c.search.first();await c.search.next();assert.equal(c.search.state().phase,'failed');assert.equal(c.search.state().page,undefined);const count=c.calls.length;assert.equal(await c.search.next(),false);assert.equal(c.calls.length,count);
 await c.search.first();assert.deepEqual(c.calls.map(q=>q.cursor),['',cursor(1),'']);
});
test('Repeated cursors, repeated resources and cross-project rows reject the entire new page',async()=>{
 for(const bad of ['cursor','duplicate','scope','short-page']){
  const c=setup();c.setAnswer(async q=>{if(!q.cursor)return response(q,Array.from({length:20},(_,n)=>row(200+n)),cursor(1));
   return bad==='cursor'?response(q,Array.from({length:20},(_,n)=>row(300+n)),cursor(1)):bad==='duplicate'?response(q,[row(200)]):bad==='scope'?response(q,[{...row(300,'document'),project_id:id(999)}]):response(q,[row(300)],cursor(2));});
  await c.search.first();await c.search.next();assert.equal(c.search.state().phase,'failed',bad);assert.equal(c.search.state().page,undefined,bad);
 }
});
test('Changed generation or authority stops continuation while explicit fresh search adopts a new snapshot',async()=>{
 for(const changed of ['generation','epoch']){
  const c=setup();c.setAnswer(async q=>response(q,Array.from({length:20},(_,n)=>row((q.cursor?300:200)+n)),q.cursor?'':cursor(1),changed==='generation'&&q.cursor?'b'.repeat(64):'a'.repeat(64),changed==='epoch'&&q.cursor?'2':'1'));
  await c.search.first();await c.search.next();assert.equal(c.search.state().phase,'expired');
  c.setAnswer(async q=>response(q,[row(400,'document')],'','c'.repeat(64),'3'));await c.search.first();assert.equal(c.search.state().phase,'ready');assert.equal(c.search.state().page?.epoch,'3');
 }
});
test('Same-session A to B to A suppresses older successful and failed replies',async()=>{
 for(const failed of [false,true]){
  const c=setup(),old=deferred<View>();c.setAnswer(()=>old.promise);const pending=c.search.first();
  c.search.configure({...c.scope,term:'other'});c.search.configure({...c.scope});c.setAnswer(async q=>response(q,[row(301,'document')]));await c.search.first();
  if(failed)old.reject(new HomeError('denied_or_not_found'));else old.resolve(response(c.calls[0]!,[row(300,'document')]));
  assert.equal(await pending,false);assert.equal(c.search.state().page?.choices[0]?.id,id(301));
 }
});
test('Session and capability withdrawal remove choices immediately and suppress delayed old replies',async()=>{
 for(const kind of ['session','capability']){
  const c=setup();await c.search.first();if(kind==='session')c.setToken(null);else c.setMode({kind:'unsupported'});
  assert.equal(c.search.state().page,undefined);assert.equal(c.search.state().phase,kind==='session'?'revoked':'unsupported');
  c.setToken({});c.setMode({kind:'legacy'});c.search.configure(c.scope);const held=deferred<View>();c.setAnswer(()=>held.promise);const pending=c.search.first();c.setToken({});c.search.configure(c.scope);
  c.setAnswer(async q=>response(q,[row(302,'document')]));await c.search.first();held.resolve(response(c.calls.at(-2)!,[row(301,'document')]));assert.equal(await pending,false);assert.equal(c.search.state().page?.choices[0]?.id,id(302));
 }
});
test('Foreground pending preserves current matches but blocks reads; offline and denial withdraw choices',async()=>{
 const c=setup();await c.search.first();const before=c.search.state();c.search.configure({...c.scope,locked:true});assert.equal(c.search.state(),before);assert.equal(await c.search.first(),false);assert.equal(c.calls.length,1);
 c.search.configure({...c.scope,online:false});assert.equal(c.search.state().phase,'offline');assert.equal(c.search.state().page,undefined);
 c.search.configure(c.scope);c.setAnswer(async()=>{throw new HomeError('denied_or_not_found');});await c.search.first();assert.equal(c.search.state().phase,'revoked');assert.equal(c.search.state().page,undefined);
});
test('Unsupported successor profile, readers and oversized search never invoke legacy search',async()=>{
 const c=setup();c.setMode({kind:'native-human-doc'});c.search.configure(c.scope);assert.equal(await c.search.first(),false);
 c.setMode({kind:'legacy'});c.search.configure({...c.scope,writable:false});assert.equal(await c.search.first(),false);
 c.search.configure({...c.scope,term:'東'.repeat(43)});assert.equal(await c.search.first(),false);assert.equal(c.calls.length,0);
});

test('A sibling access denial cancels an in-flight picker without republishing when the same view rerenders',async()=>{
 const c=setup(),held=deferred<View>();c.setAnswer(()=>held.promise);const pending=c.search.first();
 c.search.dispose();c.search.configure(c.scope);assert.equal(c.search.state().phase,'idle');
 held.resolve(response(c.calls[0]!,[row(300,'document')]));assert.equal(await pending,false);assert.equal(c.search.state().page,undefined);
 c.setAnswer(async q=>response(q,[row(301,'document')]));await c.search.first();assert.equal(c.search.state().page?.choices[0]?.id,id(301));
});

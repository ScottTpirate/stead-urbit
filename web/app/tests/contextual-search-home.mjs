// Closed synthetic responses through the real HomeClient; no native acceptance.
import assert from 'node:assert/strict';
import {commandDigest} from '../src/protocol';
export const id=n=>'019939ba-4000-7000-8000-'+String(n).padStart(12,'0');
export const project=id(100),item=id(101),collection=id(201);
export const work=n=>({kind:'work',project_id:project,container_id:'',resource_id:id(n),title:n===101?'Prepare the launch':`Other task ${n}`,description:'Saved launch context',resource_revision:'1',status:'todo',type:'task',priority:'none',assignee_principal_id:''});
export const doc=n=>({kind:'document',project_id:project,container_id:collection,resource_id:id(n),title:n===301?'Release guide':'Original supporting guide',resource_revision:'1',container_head:'d'.repeat(40),markdown:`---\nid: ${id(n)}\ntype: page\nstate: published\n---\n# ${n===301?'Release guide':'Original supporting guide'}\n\nExact saved context.\n`});
export const supporting=(resource=id(700),target=id(302))=>({kind:'relation',project_id:project,container_id:'',resource_id:resource,resource_revision:'1',type:'documents',source_project_id:project,source_kind:'document',source_container_id:collection,source_id:target,target_project_id:project,target_kind:'work',target_container_id:'',target_id:item});
export function createHome(){
 const waiters=[];const state={requests:[],queries:[],commands:[],rawCommands:[],events:0,receipts:new Map(),relations:[],documents:[doc(301),doc(302)],search:[...Array.from({length:20},(_,n)=>work(200+n)),doc(301),...Array.from({length:19},(_,n)=>work(220+n))],
  role:'maintainer',capability:true,audit:'b'.repeat(64),generation:'a'.repeat(64),epoch:'1',pages:new Map(),watches:new Map(),counter:0,sequence:0,expireNext:false,holdRules:[],held:[],failure:'',fault:'',dropCommand:false,receiptUnavailable:false,errors:[]};
 const person=()=>({principal_id:id(900),binding_id:id(901),binding_revision:'1',identity_ship:'~bus',session_audit_id:state.audit,display_name:'Synthetic member',can_create:'yes'});
 const projectRow=()=>({kind:'project',project_id:project,resource_id:project,title:'Launch planning',project_key:'LAUNCH',preset:'general',authority_epoch:state.epoch,resource_revision:'1',policy_revision:'1',role:state.role});
 const token=()=>String(++state.counter).padStart(64,'0');
 const send=(route,body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body),headers:{'cache-control':'no-store'}});
 const envelope=(q,rows,cursor='',generation=state.generation,epoch=state.epoch)=>({protocol:'stead.query-result/3',request_id:q.request_id,status:'read',kind:q.kind,project_id:q.project_id,container_id:q.container_id,resource_id:q.resource_id,authority_epoch:epoch,generation,cursor,rows:Object.fromEntries(rows.map((row,n)=>[String(n),row]))});
 async function hold(kind,q){
  if(state.holdRules[0]!==kind)return null;state.holdRules.shift();let release;const waiting=new Promise(resolve=>{release=resolve;});const held={kind,q,failure:'',release};state.held.push(held);for(const resolve of waiters.splice(0))resolve();await waiting;return held;
 }
 async function route(route){const request=route.request();try{
  assert.equal(request.method(),'POST');const url=new URL(request.url()),q=request.postDataJSON();assert.ok(q&&typeof q==='object'&&!Array.isArray(q));state.requests.push({endpoint:url.pathname,...q});assert.ok(state.requests.length<=300);
  if(url.pathname==='/stead/api/capabilities'){assert.deepEqual(q,{protocol:'stead.capabilities/3'});return send(route,{protocol:'stead.capabilities/3',profile:'configured-team',commands:'stead.command/3',queries:'stead.query/3',updates:'stead.updates/3',work_contract:'stead.work-contract/1',...(state.capability?{}:{product_profile:'unsupported'})});}
  if(url.pathname==='/stead/auth/resume'){assert.deepEqual(q,{protocol:'stead.auth/1'});return send(route,{status:'authenticated',csrf:'c'.repeat(64)});}
  assert.equal(request.headers()['x-stead-csrf'],'c'.repeat(64));
  if(url.pathname==='/stead/api/code'){assert.deepEqual(q,{protocol:'stead.code/1',project_id:project,action:'status'});return send(route,{protocol:'stead.code/1',status:'disabled',write:'no',manage:'no'});}
  if(url.pathname==='/stead/api/updates'){
   assert.equal(q.protocol,'stead.updates/3');assert.deepEqual(Object.keys(q).sort(),['action','container_id','cursor','kind','project_id','protocol','request_id','resource_id','search','watch_id']);const base={protocol:'stead.update-result/3',request_id:q.request_id};
   if(q.action==='open'){assert.ok(['project','work','documents','containers','relations','comments'].includes(q.kind));assert.equal(q.project_id,project);assert.equal(q.watch_id+q.cursor,'');const watch_id=token(),cursor=token();state.watches.set(watch_id,{cursor,sequence:state.sequence});return send(route,{...base,status:'watching',watch_id,cursor,generation:state.generation,rows:{}});}
   assert.equal(q.kind+q.project_id+q.container_id+q.resource_id+q.search,'');
   if(q.action==='cancel'){state.watches.delete(q.watch_id);return send(route,{...base,status:'cancelled',watch_id:q.watch_id,cursor:'',generation:'',rows:{}});}
   assert.equal(q.action,'poll');const watch=state.watches.get(q.watch_id);if(!watch)return send(route,{...base,status:'refresh_required',watch_id:q.watch_id,cursor:'',generation:'',rows:{}});
   assert.equal(q.cursor,watch.cursor);const rows=watch.sequence===state.sequence?{}:{'0':{sequence:String(state.sequence),generation:state.generation}};watch.sequence=state.sequence;watch.cursor=token();return send(route,{...base,status:'updated',watch_id:q.watch_id,cursor:watch.cursor,generation:state.generation,rows});
  }
  if(url.pathname==='/stead/api/command'){
   assert.deepEqual(Object.keys(q).sort(),['authority_epoch','expected_revision','operation','payload','project_id','protocol','request_id','resource_id']);assert.equal(q.protocol,'stead.command/3');assert.equal(q.project_id,project);assert.equal(q.authority_epoch,state.epoch);assert.match(q.request_id,/^[a-f0-9-]{36}$/u);assert.match(q.resource_id,/^[a-f0-9-]{36}$/u);
   assert.ok(['relation.create','relation.delete'].includes(q.operation),'Only reviewed link actions');state.commands.push(q);state.rawCommands.push(request.postData());const prior=state.receipts.get(q.request_id);
   if(prior){assert.equal(state.rawCommands.at(-1),state.rawCommands[state.commands.findIndex(row=>row.request_id===q.request_id)]);return send(route,prior);}
   if(q.operation==='relation.create'){assert.equal(q.expected_revision,'0');assert.deepEqual(q.payload,{type:'documents',source_project_id:project,source_kind:'document',source_container_id:collection,source_id:id(301),target_project_id:project,target_kind:'work',target_container_id:'',target_id:item});assert.equal(state.relations.some(row=>row.source_id===id(301)),false);}
   else{assert.deepEqual(q.payload,{});const existing=state.relations.find(row=>row.resource_id===q.resource_id);assert.ok(existing);assert.equal(q.expected_revision,existing.resource_revision);}
   const held=await hold('command',q);assert.equal(held?.failure??'','');
   const receipt={protocol:'stead.receipt/3',status:'accepted',request_id:q.request_id,canonical_sha256:await commandDigest(q),project_id:project,resource_id:q.resource_id,resource_kind:'relation',container_id:'',resource_revision:String(BigInt(q.expected_revision)+1n),authority_epoch:q.authority_epoch,operation:q.operation,...person(),authentication:'native-approved-browser/1',authentication_strength:'native-approved-browser',runtime:'isolated-fake',accepted_at_ms:'1794770000000',git_commit_oid:''};
   delete receipt.display_name;delete receipt.can_create;
   state.receipts.set(q.request_id,receipt);state.events++;state.sequence++;state.generation=(state.sequence+10).toString(16).padStart(64,'0');
   if(q.operation==='relation.create')state.relations.push(supporting(q.resource_id,id(301)));else state.relations=state.relations.filter(row=>row.resource_id!==q.resource_id);
   if(state.dropCommand){state.dropCommand=false;return route.abort('failed');}return send(route,receipt);
  }
  assert.equal(url.pathname,'/stead/api/query');assert.deepEqual(Object.keys(q).sort(),['container_id','cursor','kind','project_id','protocol','request_id','resource_id','search']);assert.equal(q.protocol,'stead.query/3');
  if(state.expireNext){state.expireNext=false;return send(route,{error:'session_required'},401);}
  if(q.kind==='identity'){assert.equal(q.project_id+q.container_id+q.resource_id+q.search+q.cursor,'');return send(route,envelope(q,[person()]));}
  if(q.kind==='projects'){assert.equal(q.project_id+q.container_id+q.resource_id+q.search+q.cursor,'');return send(route,envelope(q,[projectRow()]));}
  assert.equal(q.project_id,project);state.queries.push(q);
  if(q.kind==='receipt'){if(state.receiptUnavailable)return send(route,{error:'unavailable'},503);const receipt=state.receipts.get(q.resource_id);return send(route,envelope(q,receipt?[receipt]:[]));}
  let rows,cursor='',generation=state.generation,epoch=state.epoch,offset=0;
  if(q.kind==='search'){
   assert.equal(q.container_id+q.resource_id,'');assert.ok(Buffer.byteLength(q.search)<=128);
   if(q.cursor){const next=state.pages.get(q.cursor);assert.ok(next,'Single-use continuation');state.pages.delete(q.cursor);assert.equal(next.term,q.search);offset=next.offset;if(next.generation!==generation)return send(route,{protocol:'stead.result/3',status:'rejected',error:'stale_cursor'});}
   rows=state.search.slice(offset,offset+20).map(row=>({...row}));
   if(state.search.length>offset+20){cursor=state.fault==='repeat-token'&&q.cursor?q.cursor:token();if(!q.cursor)state.pages.clear();state.pages.set(cursor,{offset:offset+20,term:q.search,generation});}
   if(offset&&state.fault==='epoch')epoch='9';if(offset&&state.fault==='generation')generation='e'.repeat(64);
  }else{assert.equal(q.cursor,'');rows=q.kind==='project'?[projectRow()]:q.kind==='work'?(q.resource_id?[work(Number(q.resource_id.slice(-12)))]:[work(101),work(103)]):q.kind==='relations'?state.relations.map(row=>({...row})):q.kind==='containers'?[{kind:'container',project_id:project,resource_id:collection,container_id:collection,title:'Shared pages',visibility:'shared',resource_revision:'1'}]:q.kind==='documents'?state.documents.map(row=>({...row})):q.kind==='document'?state.documents.filter(row=>row.resource_id===q.resource_id&&row.container_id===q.container_id).map(row=>({...row})):['comments','assignees'].includes(q.kind)?[]:null;assert.ok(rows,'Known read only');}
  const held=await hold(q.kind,q);const failure=held?.failure||(['search','relations'].includes(q.kind)?state.failure:'');if(failure)return send(route,{protocol:'stead.result/3',status:'rejected',error:failure});
  return send(route,envelope(q,rows,cursor,generation,epoch));
 }catch(error){if(!request.failure())state.errors.push(String(error).slice(0,512));try{await route.abort();}catch{}}}
 return{state,route,async held(count=1){if(state.held.length>=count)return;await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Expected held read')),5000);waiters.push(()=>{clearTimeout(timer);resolve();});});assert.ok(state.held.length>=count);},release(){for(const held of state.held)held.release();}};
}

// Read-only synthetic Home. Its responses exercise the real App and HomeClient.
import assert from 'node:assert/strict';
export const id=n=>'019939ba-4000-7000-8000-'+String(n).padStart(12,'0');
export const work=n=>({kind:'work',project_id:id(100),project_title:'Garden planning',project_key:'GARDEN',resource_id:id(n),container_id:'',title:`Assigned task ${n}`,status:'todo',assignee_display_name:'Synthetic member',resource_revision:'1',description:'Saved task context',type:'task',priority:'none',assignee_principal_id:id(900)});
export const doc={kind:'document',project_id:id(101),project_title:'Event program',project_key:'EVENT',resource_id:id(301),container_id:id(201),title:'# Accessible event guide',snippet:'Tokyo 東京 — supporting context',resource_revision:'1',container_head:'1',markdown:`---\nid: ${id(301)}\ntype: page\nstate: published\n---\n# Accessible event guide\n\nExact saved event plan.\n`};
export const projects=[100,101].map(n=>({kind:'project',project_id:id(n),resource_id:id(n),title:n===100?'Garden planning':'Event program',project_key:n===100?'GARDEN':'EVENT',preset:'general',authority_epoch:'1',resource_revision:'1',policy_revision:'1',role:'reader'}));
export function createHome(){
 const waiters=[];
 const state={requests:[],reads:[],my:Array.from({length:55},(_,n)=>work(400+n)),search:[...Array.from({length:50},(_,n)=>work(400+n)),doc,...Array.from({length:9},(_,n)=>work(450+n))],
  watches:new Map(),pages:new Map(),counter:0,generation:'a'.repeat(64),audit:'b'.repeat(64),epoch:'0',expireNext:false,holdOffsets:[],held:[],releases:[],failure:'',fault:'',refreshRequired:false,errors:[],activeOpens:0,maximumOpens:0};
 const token=()=>String(++state.counter).padStart(64,'0');
 const send=(route,body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body),headers:{'cache-control':'no-store'}});
 const envelope=(q,rows,epoch='1',generation=state.generation,cursor='')=>({protocol:'stead.query-result/3',request_id:q.request_id,status:'read',kind:q.kind,project_id:q.project_id,container_id:q.container_id,resource_id:q.resource_id,authority_epoch:epoch,generation,cursor,rows:Object.fromEntries(rows.map((row,index)=>[String(index),row]))});
 async function route(route){
  const request=route.request();
  try{
   const url=new URL(request.url()),q=request.postDataJSON();assert.equal(request.method(),'POST');assert.ok(q&&typeof q==='object'&&!Array.isArray(q));
   state.requests.push({endpoint:url.pathname,...q});assert.ok(state.requests.length<=300);
   if(url.pathname==='/stead/api/capabilities'){assert.deepEqual(q,{protocol:'stead.capabilities/3'});return send(route,{protocol:'stead.capabilities/3',profile:'configured-team',queries:'stead.query/3',commands:'stead.command/3',updates:'stead.updates/3',workspace_queries:'stead.workspace-queries/1',work_contract:'stead.work-contract/1'});}
   if(url.pathname==='/stead/auth/resume'){assert.deepEqual(q,{protocol:'stead.auth/1'});return send(route,{status:'authenticated',csrf:'c'.repeat(64)});}
   assert.equal(request.headers()['x-stead-csrf'],'c'.repeat(64));
   if(url.pathname==='/stead/api/code'){assert.deepEqual(Object.keys(q).sort(),['action','project_id','protocol']);assert.equal(q.action,'status');assert.equal(q.protocol,'stead.code/1');assert.ok(projects.some(row=>row.project_id===q.project_id));return send(route,{protocol:'stead.code/1',status:'disabled',write:'no',manage:'no'});}
   if(url.pathname==='/stead/api/updates'){
    assert.equal(q.protocol,'stead.updates/3');assert.deepEqual(Object.keys(q).sort(),['action','container_id','cursor','kind','project_id','protocol','request_id','resource_id','search','watch_id']);const base={protocol:'stead.update-result/3',request_id:q.request_id};
    if(q.action==='open'){
     assert.ok(['my-work','workspace-search','work','documents','containers','project','comments','relations'].includes(q.kind));
     if(['my-work','workspace-search'].includes(q.kind))assert.equal(q.project_id+q.container_id+q.resource_id,'');
     assert.equal(q.watch_id+q.cursor,'');state.activeOpens++;state.maximumOpens=Math.max(state.maximumOpens,state.activeOpens);const watch_id=token(),cursor=token();state.watches.set(watch_id,{scope:q.kind+'/'+q.search,cursor,generation:state.generation,sequence:0});state.activeOpens--;return send(route,{...base,status:'watching',watch_id,cursor,generation:state.generation,rows:{}});
    }
    assert.equal(q.kind+q.project_id+q.container_id+q.resource_id+q.search,'');
    if(q.action==='cancel'){assert.equal(q.cursor,'');state.watches.delete(q.watch_id);return send(route,{...base,status:'cancelled',watch_id:q.watch_id,cursor:'',generation:'',rows:{}});}
    assert.equal(q.action,'poll');const watch=state.watches.get(q.watch_id);
    if(state.refreshRequired||!watch){state.refreshRequired=false;state.watches.delete(q.watch_id);return send(route,{...base,status:'refresh_required',watch_id:q.watch_id,cursor:'',generation:'',rows:{}});}
    assert.equal(q.cursor,watch.cursor);const rows=watch.generation===state.generation?{}:{'0':{sequence:String(++watch.sequence),generation:state.generation}};watch.generation=state.generation;watch.cursor=token();return send(route,{...base,status:'updated',watch_id:q.watch_id,cursor:watch.cursor,generation:watch.generation,rows});
   }
   assert.equal(url.pathname,'/stead/api/query','No business commands or unrelated endpoints');if(state.expireNext){state.expireNext=false;return send(route,{error:'session_required'},401);}assert.equal(q.protocol,'stead.query/3');assert.deepEqual(Object.keys(q).sort(),['container_id','cursor','kind','project_id','protocol','request_id','resource_id','search']);
   if(q.kind==='identity')return send(route,envelope(q,[{principal_id:id(900),binding_id:id(901),binding_revision:'1',identity_ship:'~bus',session_audit_id:state.audit,display_name:'Synthetic member',can_create:'yes'}]));
   if(!['my-work','workspace-search'].includes(q.kind)){
    const all=[...state.my,...state.search].filter(row=>row.kind==='work');const unique=[...new Map(all.map(row=>[row.resource_id,row])).values()];
    const rows=q.kind==='projects'?projects:q.kind==='project'?projects.filter(row=>row.project_id===q.project_id):q.kind==='containers'?(q.project_id===id(101)?[{kind:'container',project_id:id(101),container_id:id(201),resource_id:id(201),resource_revision:'1',title:'Event documents',visibility:'shared'}]:[])
     :['document','documents'].includes(q.kind)?(q.project_id===id(101)&&q.container_id===id(201)&&(!q.resource_id||q.resource_id===id(301))?[doc]:[]):q.kind==='work'?(q.resource_id?unique.filter(row=>row.resource_id===q.resource_id&&row.project_id===q.project_id):unique.filter(row=>row.project_id===q.project_id).slice(0,20)):['comments','relations','assignees'].includes(q.kind)?[]:null;
    assert.ok(rows,'Only exact existing navigation reads');return send(route,envelope(q,rows));
   }
   assert.equal(q.project_id+q.container_id+q.resource_id,'');assert.ok(Buffer.byteLength(q.search)<=128);if(q.kind==='my-work')assert.equal(q.search,'');
   let offset=0;const scope=q.kind+'/'+q.search;
   if(q.cursor){const next=state.pages.get(q.cursor);assert.ok(next,'One live continuation only');assert.equal(next.scope,scope);state.pages.delete(q.cursor);if(next.generation!==state.generation)return send(route,{protocol:'stead.result/3',status:'rejected',error:'stale_cursor'});offset=next.offset;}
   const rows=[...(q.kind==='my-work'?state.my:state.search)].map(row=>({...row}));const generation=state.generation,epoch=state.epoch;
   state.reads.push({scope,cursor:q.cursor,offset,request:q.request_id});
   if(state.holdOffsets[0]===offset){state.holdOffsets.shift();let release;const pending=new Promise(resolve=>{release=resolve;});state.held.push({offset,release,scope});state.releases.push(release);for(const waiter of waiters.splice(0))waiter();await pending;}
   if(state.failure)return send(route,{protocol:'stead.result/3',status:'rejected',error:state.failure});
   let cursor='';if(rows.length>offset+20){cursor=state.fault==='repeat-token'&&q.cursor?q.cursor:token();if(!q.cursor)state.pages.clear();state.pages.set(cursor,{scope,offset:offset+20,generation});}
   const out=rows.slice(offset,offset+20);return send(route,envelope(q,out,state.fault==='epoch'&&offset? '9':epoch,state.fault==='generation'&&offset?'e'.repeat(64):generation,cursor));
  }catch(error){if(!request.failure())state.errors.push(String(error).slice(0,512));try{await route.abort();}catch{}}
 }
 return{state,route,async held(count=1){if(state.held.length>=count)return;await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Missing held workspace read')),5000);waiters.push(()=>{clearTimeout(timer);resolve();});});assert.ok(state.held.length>=count);},release(){for(const release of state.releases.splice(0))release();}};
}

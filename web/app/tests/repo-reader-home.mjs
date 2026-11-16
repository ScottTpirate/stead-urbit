// Synthetic HTTP responses exercise the actual HomeClient browse decoder.
import assert from 'node:assert/strict';
export const id=n=>'019939ba-4000-7000-8000-'+String(n).padStart(12,'0');
export const hex=value=>Buffer.from(value,'utf8').toString('hex');
export const source='---\nid: '+id(123)+'\ntype: page\nstate: draft\n---\n# Repository guide\n\nExact Unicode 雪🪴 and trailing spaces.  \r\n\n- One\n- Two\n\n[Local](guide.md) [Section](#part) [App root](/stead/) [External](https://example.com/docs)\n\n![Unloaded](https://example.com/pixel.png)\n\n<script>alert(1)</script>\n';
export const longName='A very long repository Markdown filename '+ 'with context '.repeat(10)+'.md';
export function createHome(){
 const waiters=[];
 const state={capability:true,person:1,denied:false,error:'',invalid:false,truncated:false,hold:false,held:[],requests:[],blocked:[],releases:[]};
 function response(raw,status=200){return{status,contentType:'application/json',body:JSON.stringify(raw),headers:{'cache-control':'no-store'}};}
 async function route(route){
  try{const request=route.request();assert.equal(request.method(),'POST');const url=new URL(request.url());const q=request.postDataJSON();assert.ok(q&&typeof q==='object'&&!Array.isArray(q));
   if(url.pathname==='/stead/api/capabilities')return route.fulfill(response({protocol:'stead.capabilities/3',profile:'configured-team',...(state.capability?{}:{product_profile:'unsupported'})}));
   if(url.pathname==='/stead/auth/resume')return route.fulfill(response({status:'authenticated',csrf:'c'.repeat(64)}));
   if(url.pathname==='/stead/api/query'){
    assert.match(q.request_id,/^[a-f0-9-]{36}$/u);assert.deepEqual(q,{protocol:'stead.query/3',request_id:q.request_id,kind:'identity',project_id:'',container_id:'',resource_id:'',search:'',cursor:''});
    return route.fulfill(response({protocol:'stead.query-result/3',request_id:q.request_id,status:'read',kind:'identity',project_id:'',container_id:'',resource_id:'',authority_epoch:'0',generation:'b'.repeat(64),cursor:'',rows:{'0':{principal_id:id(110+state.person),binding_id:id(210+state.person),binding_revision:'1',identity_ship:state.person===1?'~bus':'~nec',session_audit_id:String(state.person).repeat(64)}}}));
   }
   assert.equal(url.pathname,'/stead/api/code/browse');assert.equal(request.headers()['x-stead-csrf'],'c'.repeat(64));
   assert.deepEqual(Object.keys(q).sort(),['path','project_id','protocol','ref','snapshot','view']);assert.equal(q.protocol,'stead.git-browse/1');assert.ok([id(100),id(101)].includes(q.project_id));assert.equal(q.snapshot,'a'.repeat(64));
   assert.ok([hex('refs/heads/main'),hex('refs/heads/other')].includes(q.ref));assert.ok(Array.isArray(q.path)&&q.path.length<=12);assert.ok(q.path.every(x=>typeof x==='string'&&/^[a-f0-9]+$/u.test(x)));assert.ok(['tree','file'].includes(q.view));
   state.requests.push(q);assert.ok(state.requests.length<=80);
   const commit=q.ref===hex('refs/heads/main')?'d'.repeat(40):'e'.repeat(40);
   let result;
   if(state.denied)result=response({error:'denied_or_not_found'},403);
   else if(state.error)result=response({error:state.error},409);
   else if(q.view==='tree'){
    const names=q.path.length?['nested.md']:['README.md','docs','notes.txt','empty.md','image.png','large.md',longName];
    result=response({protocol:q.protocol,project_id:q.project_id,snapshot:q.snapshot,ref:q.ref,path:q.path,status:'tree',commit,entries:names.map(name=>({name:hex(name),kind:name==='docs'?'tree':'file',oid:'f'.repeat(40)})),truncated:state.truncated});
   }else{
    const filename=Buffer.from(q.path.at(-1),'hex').toString('utf8');let text=filename==='empty.md'?'':filename==='notes.txt'?'exact raw\r\n雪\t  \r\n':source+(q.project_id===id(101)?'\nProject B source\n':'');
    const preview=filename==='image.png'?'binary':filename==='large.md'?'too-large':'text';
    result=response({protocol:q.protocol,project_id:state.invalid?id(999):q.project_id,snapshot:q.snapshot,ref:q.ref,path:q.path,status:'file',commit,preview,bytes:preview==='text'?Buffer.byteLength(text):40000,...(preview==='text'?{text}:{})});
   }
   if(state.hold){state.hold=false;let release;const done=new Promise(resolve=>{release=resolve;});state.held.push({q,result,release});state.releases.push(release);for(const waiter of waiters.splice(0))waiter();await done;}
   try{return await route.fulfill(result);}catch(error){if(!request.failure())throw error;}
  }catch(error){state.blocked.push(String(error).slice(0,512));try{await route.abort();}catch{}}
 }
 return{state,route,waitHeld(){if(state.held.length)return Promise.resolve();return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Expected held request missing')),5000);waiters.push(()=>{clearTimeout(timer);resolve();});});},release(){for(const value of state.releases.splice(0))value();}};
}

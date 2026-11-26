import test from 'node:test';
import assert from 'node:assert/strict';
import {HomeClient} from '../src/api';
import {createHome,doc} from './workspace-return-home.mjs';
test('Workspace synthetic envelopes pass actual authenticated query/watch decoders with fresh single-use cursors', {timeout:5000},async()=>{
 const home=createHome(),original=globalThis.fetch;
 globalThis.fetch=async(url,init)=>new Promise((resolve,reject)=>{
  const request={method:()=>init?.method,url:()=>new URL(String(url),'http://127.0.0.1:19445').href,postDataJSON:()=>JSON.parse(String(init?.body)),headers:()=>Object.fromEntries(Object.entries(init?.headers??{}).map(([key,value])=>[key.toLowerCase(),value])),failure:()=>null};
  void home.route({request:()=>request,fulfill:async({status,contentType,body,headers})=>{resolve(new Response(body,{status,headers:{...headers,'content-type':contentType}}));},abort:async()=>reject(Error('Unexpected fixture request'))});
 });
 try{const client=new HomeClient();await client.resume();await client.capabilities();const query={kind:'workspace-search' as const,project_id:'',container_id:'',resource_id:'',search:'guide'};
  const watch=await client.watch(query);assert.ok(watch);const first=await client.query({...query,cursor:''});assert.equal(Object.keys(first.rows).length,20);
  const second=await client.query({...query,cursor:first.cursor});assert.equal(Object.keys(second.rows).length,20);
  const third=await client.query({...query,cursor:second.cursor});assert.equal(Object.keys(third.rows).length,20);assert.equal(Object.values(third.rows).some(row=>row.resource_id===doc.resource_id),true);
  assert.notEqual(first.cursor,second.cursor);assert.equal(third.cursor,'');assert.equal((await watch.poll()).status,'updated');await client.retire(watch);assert.deepEqual(home.state.errors,[]);
 }finally{home.release();globalThis.fetch=original;}
});

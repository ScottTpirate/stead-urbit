import test from 'node:test';
import assert from 'node:assert/strict';
import {HomeClient, command} from '../src/api';
import {createHome,project,item,collection,id} from './contextual-search-home.mjs';
test('Contextual fixture passes actual query, command receipt and recovery decoders with exact unchanged relation payload',{timeout:5000},async()=>{
 const home=createHome(),original=globalThis.fetch;
 globalThis.fetch=async(url,init)=>new Promise((resolve,reject)=>{const request={method:()=>init?.method,url:()=>new URL(String(url),'http://127.0.0.1:19445').href,postDataJSON:()=>JSON.parse(String(init?.body)),postData:()=>String(init?.body),headers:()=>Object.fromEntries(Object.entries(init?.headers??{}).map(([key,value])=>[key.toLowerCase(),value])),failure:()=>null};void home.route({request:()=>request,fulfill:async({status,contentType,body,headers})=>resolve(new Response(body,{status,headers:{...headers,'content-type':contentType}})),abort:async()=>reject(Error('Unexpected fixture request'))});});
 try{const client=new HomeClient();await client.resume();await client.capabilities();const scope={kind:'search' as const,project_id:project,container_id:'',resource_id:'',search:'guide'};const first=await client.query({...scope,cursor:''});assert.equal(Object.keys(first.rows).length,20);const second=await client.query({...scope,cursor:first.cursor});assert.equal(Object.values(second.rows).filter(row=>row.kind==='document').length,1);
  const value=command(project,id(701),'0','1','relation.create',{type:'documents',source_project_id:project,source_kind:'document',source_container_id:collection,source_id:id(301),target_project_id:project,target_kind:'work',target_container_id:'',target_id:item});
  const accepted=await client.command(value);assert.equal(accepted.resource_kind,'relation');assert.deepEqual(await client.recover(value),accepted);assert.deepEqual(await client.command(value),accepted);assert.equal(home.state.events,1);assert.equal(home.state.rawCommands[0],home.state.rawCommands[1]);assert.deepEqual(home.state.errors,[]);
 }finally{home.release();globalThis.fetch=original;}
});

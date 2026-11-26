import test from 'node:test';
import assert from 'node:assert/strict';
import {HomeClient,HomeError} from '../src/api';
import {createHome,id,hex,source} from './repo-reader-home.mjs';
test('Synthetic repository envelopes pass the real authenticated client and exact browse scope decoder',async()=>{
 const home=createHome();const original=globalThis.fetch;
 globalThis.fetch=async(url,init)=>new Promise((resolve,reject)=>{
  const request={method:()=>init?.method,url:()=>new URL(String(url),'http://127.0.0.1:19445').href,postDataJSON:()=>JSON.parse(String(init?.body)),headers:()=>Object.fromEntries(Object.entries(init?.headers??{}).map(([key,value])=>[key.toLowerCase(),value])),failure:()=>null};
  void home.route({request:()=>request,fulfill:async({status,contentType,body,headers})=>{resolve(new Response(body,{status,headers:{...headers,'content-type':contentType}}));},abort:async()=>reject(Error('Unexpected fixture request'))});
 });
 try{const client=new HomeClient();await client.resume();await client.capabilities();assert.equal(client.productMode().kind,'legacy');assert.ok(client.currentSessionToken());
  const args=[id(100),'a'.repeat(64),hex('refs/heads/main')] as const;
  const tree=await client.browseCode(...args,[],'tree');assert.equal(tree.status,'tree');if(tree.status==='tree')assert.equal(tree.entries.length,7);
  const file=await client.browseCode(...args,[hex('README.md')],'file');assert.equal(file.status,'file');if(file.status==='file')assert.equal(file.text,source);
  home.state.invalid=true;await assert.rejects(client.browseCode(...args,[hex('README.md')],'file'),(error:unknown)=>error instanceof HomeError&&error.code==='invalid_response');
  home.state.denied=true;await assert.rejects(client.browseCode(...args,[hex('README.md')],'file'),(error:unknown)=>error instanceof HomeError&&error.code==='denied_or_not_found');
  assert.deepEqual(home.state.blocked,[]);
 }finally{home.release();globalThis.fetch=original;}
});

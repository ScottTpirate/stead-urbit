// Fake HTTP responses test the browser-client boundary, never Home authority.
import test from 'node:test';
import assert from 'node:assert/strict';
import {HomeClient} from '../src/api';
import {productCarrierMode} from '../src/productCarrier';
import {parseProductCommand, productCommandDigest} from '../src/productProtocol';
const id = (n: number) => `019939ba-4000-7000-8000-${String(n).padStart(12, '0')}`;
const capabilities: Record<string,string> = {protocol:'stead.capabilities/3',profile:'configured-team',commands:'stead.command/3',queries:'stead.query/3',
  authentication:'native-approved-browser/1',max_request_bytes:'65536',max_response_bytes:'262144',page_size:'20',runtime:'isolated-fake',
  product_profile:'native-human-doc/1',work_commands:'stead.command/4',work_queries:'stead.query/4',doc_change_commands:'stead.doc-change/1',
  doc_change_queries:'stead.doc-change-query/1',refresh:'explicit/1'};
const json = (value: unknown, status=200) => new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json'}});
async function receipt(raw: string) {
  const request=parseProductCommand(raw);
  return {protocol:'stead.receipt/4',status:'accepted',request_id:request.request_id,canonical_sha256:await productCommandDigest(request),
    project_id:request.project_id,resource_id:request.resource_id,authority_epoch:request.authority_epoch,operation:request.operation,
    principal_id:id(101),recorded_at_ms:'1000',error:'',expected:request.expected,
    resulting:{work_revision:'1',execution_contract_revision:'1',discussion_sequence:'1',execution_contract_digest:'a'.repeat(64)}};
}
function fixture() {
  const home=new HomeClient(), sent:{path:string;raw:string;init:RequestInit}[]=[];
  let person=1, caps={...capabilities}, failure=false;
  let command:(raw:string)=>Promise<Response>=async raw=>json(await receipt(raw));
  let query:(raw:string)=>Promise<Response>=async raw=>json({protocol:'stead.query-result/4',status:'rejected',request_id:JSON.parse(raw).request_id,error:'denied_or_not_found'});
  globalThis.fetch=async(url,init)=>{
    const path=String(url),raw=String(init?.body);sent.push({path,raw,init:init!});const request=JSON.parse(raw);
    if(path.endsWith('/capabilities'))return json(caps);
    if(path.endsWith('/resume')){if(failure)throw new Error('Lost resume response');return json({status:'authenticated',csrf:String(person).repeat(64)});}
    if(path.endsWith('/logout'))return json({status:'logged_out'});
    if(request.protocol==='stead.query/3'&&request.kind==='identity')return json({status:'read',...request,
      protocol:'stead.query-result/3',authority_epoch:'1',generation:'a'.repeat(64),rows:{'0':{principal_id:id(100+person),binding_id:id(200+person),binding_revision:'1',
        identity_ship:person===1?'~bus':'~nec',session_audit_id:String(person).repeat(64)}}});
    if(path.endsWith('/command'))return command(raw);
    if(path.endsWith('/query'))return query(raw);
    throw new Error('Unexpected endpoint '+path);
  };
  return {home,sent,person:(n:number)=>{person=n;},caps:(value:Record<string,string>)=>{caps=value;},failResume:(value:boolean)=>{failure=value;},
    command:(value:typeof command)=>{command=value;},query:(value:typeof query)=>{query=value;}};
}
async function prepared(home:HomeClient) {
  return home.productWork.prepareComment({request_id:id(301),project_id:id(100),resource_id:id(110),authority_epoch:'1'},'0','Exact λ "quote"  \n');
}
async function ready() {const value=fixture();await value.home.capabilities();await value.home.resume();return value;}
test('successor capabilities are all-or-nothing and restricted to the qualified rehearsal profile',()=>{
  assert.equal(productCarrierMode(capabilities).kind,'native-human-doc');
  for(const key of Object.keys(capabilities)){const partial={...capabilities};delete partial[key];assert.notEqual(productCarrierMode(partial).kind,'native-human-doc');}
  for(const changed of [{...capabilities,runtime:'live-synthetic'},{...capabilities,updates:'stead.updates/3'},
    {...capabilities,work_commands:'stead.command/5'},{...capabilities,unknown:'yes'}])assert.equal(productCarrierMode(changed).kind,'unsupported');
  assert.equal(productCarrierMode({protocol:'stead.capabilities/3',profile:'configured-team',updates:'stead.updates/3'}).kind,'legacy');
  assert.equal(productCarrierMode({protocol:'stead.capabilities/3',profile:'configured-team',work_commands:'stead.command/4'}).kind,'unsupported');
});
test('canonical commands and lost-response retries preserve exact bytes and authenticated transport settings',async()=>{
  const f=await ready(),p=await prepared(f.home);let calls=0;
  f.command(async raw=>{if(++calls===1)throw new Error('Lost reply');return json(await receipt(raw));});
  await assert.rejects(f.home.productWork.submit(p),{code:'outcome_unknown'});
  assert.equal((await f.home.productWork.retry(p)).status,'accepted');
  const sent=f.sent.filter(row=>row.path.endsWith('/command'));assert.deepEqual(sent.map(row=>row.raw),[p.bytes,p.bytes]);
  for(const row of sent){assert.equal(row.init.credentials,'same-origin');assert.equal(row.init.redirect,'error');assert.equal(row.init.cache,'no-store');
    assert.equal(row.init.referrerPolicy,'no-referrer');assert.equal((row.init.headers as Record<string,string>)['X-Stead-CSRF'],'1'.repeat(64));}
});
test('duplicate capability or receipt keys are rejected before they can alter meaning',async()=>{
  const f=await ready(),p=await prepared(f.home);
  f.command(async raw=>new Response(JSON.stringify(await receipt(raw)).replace('{','{"status":"accepted",'),{headers:{'content-type':'application/json'}}));
  await assert.rejects(f.home.productWork.submit(p),{code:'outcome_unknown'});
  globalThis.fetch=async()=>new Response(JSON.stringify(capabilities).replace('{','{"work_commands":"stead.command/3",'),{headers:{'content-type':'application/json'}});
  await assert.rejects(f.home.capabilities(),{code:'invalid_response'});
  assert.equal(f.home.productMode().kind,'unsupported');
});
test('same confirmed session retains prepared requests while suspension and replacement fence them',async()=>{
  const f=await ready(),token=f.home.currentSessionToken(),p=await prepared(f.home);
  assert.ok(token);await f.home.resume();assert.equal(f.home.currentSessionToken(),token);
  f.failResume(true);await assert.rejects(f.home.resume());assert.equal(f.home.currentSessionToken(),null);
  await assert.rejects(f.home.productWork.retry(p),{code:'session_changed'});
  f.failResume(false);await f.home.resume();assert.equal(f.home.currentSessionToken(),token);
  assert.equal((await f.home.productWork.retry(p)).status,'accepted');
  f.person(2);await f.home.resume();assert.notEqual(f.home.currentSessionToken(),token);
  await assert.rejects(f.home.productWork.retry(p),{code:'session_changed'});
});
test('late results from a cleared session cannot reach a fresh session partition',async()=>{
  const f=await ready(),p=await prepared(f.home);let finish!:(response:Response)=>void;
  f.command(()=>new Promise(resolve=>{finish=resolve;}));const waiting=f.home.productWork.submit(p);waiting.catch(()=>{});
  f.home.clear();await f.home.resume();finish(json(await receipt(p.bytes)));
  await assert.rejects(waiting,{code:'session_changed'});
});
test('invalid UTF8 oversized bodies and HTTP failures cannot become accepted receipts',async()=>{
  const f=await ready(),p=await prepared(f.home);
  for(const make of [()=>new Response(new Uint8Array([255]),{headers:{'content-type':'application/json'}}),
    ()=>new Response(' '.repeat(262145),{headers:{'content-type':'application/json'}}),
    ()=>json({status:'accepted'},500),()=>new Response('<html>proxy</html>',{headers:{'content-type':'text/html'}})]){
    f.command(async()=>make());await assert.rejects(f.home.productWork.submit(p),{code:'outcome_unknown'});
  }
});
test('authoritative non-JSON401 clears the partition before receipt parsing',async()=>{
  const f=await ready(),p=await prepared(f.home);f.command(async()=>new Response('Expired',{status:401}));
  await assert.rejects(f.home.productWork.submit(p),{code:'session_changed'});assert.equal(f.home.currentSessionToken(),null);
  await assert.rejects(prepared(f.home),{code:'session_required'});
});
test('withdrawn capabilities block new effects and stale reads but retain a correlated past receipt',async()=>{
  const f=await ready(),p=await prepared(f.home);let finish!:(response:Response)=>void;
  f.command(()=>new Promise(resolve=>{finish=resolve;}));const sending=f.home.productWork.submit(p);
  f.caps({...capabilities,refresh:'unsupported'});await f.home.capabilities();finish(json(await receipt(p.bytes)));
  assert.equal((await sending).status,'accepted');const count=f.sent.length;
  await assert.rejects(f.home.productWork.retry(p),{code:'outcome_unknown'});assert.equal(f.sent.length,count);
  f.caps({...capabilities});await f.home.capabilities();let readFinish!:(response:Response)=>void;
  f.query(()=>new Promise(resolve=>{readFinish=resolve;}));const reading=f.home.productWork.readWork({request_id:id(400),project_id:id(100)});reading.catch(()=>{});
  f.caps({...capabilities,refresh:'unsupported'});await f.home.capabilities();readFinish(json({protocol:'stead.query-result/4',status:'rejected',request_id:id(400),error:'denied_or_not_found'}));
  await assert.rejects(reading,{code:'outcome_unknown'});
});

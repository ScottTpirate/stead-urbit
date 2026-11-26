// Attended named-pilot observation. No task clicks, fills, or business mutations.
// Identity's owner cookie exists only in a separate hidden, restricted context.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright';
import {acceptedReceipt, personalIdentity, collectionReadback, scope, workBody, sha} from './namedObserverEvidence.mjs';
import {permittedCommand, permittedCodeRead, exactApproval} from './namedObserverBoundary.mjs';
import {validateConfig} from './namedObserverConfig.mjs';

const [configPath, output] = process.argv.slice(2);
assert.equal(process.version, 'v24.21.0');
assert.ok(!process.env.SSLKEYLOGFILE);
const configBytes = await fs.readFile(configPath), config = validateConfig(JSON.parse(configBytes));
const SOURCE=config.source, HOME=config.origins.home, IDENTITY=config.origins.identity;
const profile = path.join(output, 'participant-profile');
const ownerProfile = path.join(output, 'identity-owner-profile');
const report = {protocol:'stead.named-pilot-human-observation/1', classification:'attended-named-pilot-work-docs',
  status:'preparing', source:SOURCE, qualifies_phase:false, historical_m2_qualified:false, t27_onboarding_qualified:false,
  actor_scope:'Authorized existing member planet; independent human participant, not a new native identity',
  setup_scope:'Operator prepares a separate hidden Identity owner session; participant approves only the exact Home sign-in',
  config_sha256:sha(configBytes), project_id:config.project.id, person:config.person,
  started_at:null, elapsed_ms:null, accepted:[], reads:[], readbacks:[], collection_readbacks:[],
  failures:[], feedback:null, human_home_signout:false, cleanup:{identity:'not-started',home:'not-started'}};
const escape = value => value.replace(/[&<>"']/gu, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const args = ['--no-first-run','--disable-background-networking','--disable-sync','--disable-quic','--no-proxy-server',
  '--host-resolver-rules='+['home','identity'].map(name=>{const url=new URL(config.origins[name]);return `MAP ${url.hostname}:${url.port||443} 127.0.0.1:${config.forward_ports[name]}`;}).join(', '),
  '--ignore-certificate-errors-spki-list='+config.pins.home+','+config.pins.identity];
let participant, ownerBrowser, ownerContext, ownerPage, taskPage, home, started=0, finished=false;
let person=null, runtime='', identityLoggedIn=false, identityUsed=false, approvalBusy=false;
let timer, countdown, ownerTimer, readyTimer, fatal=false, resolveDone;
const done = new Promise(resolve => { resolveDone=resolve; });
const pending = new Set(), saved = new Map();
const created={work:new Set(),container:new Set(),document:new Set()};
let writing=Promise.resolve();
function checkpoint() {
  const raw=JSON.stringify({...report,elapsed_ms:started?Math.round(performance.now()-started):null},null,2)+'\n';
  if(Buffer.byteLength(raw)>1024*1024)throw new Error('evidence_bound');
  writing=writing.then(async()=>{await fs.writeFile(path.join(output,'partial.next'),raw,{mode:0o600});
    await fs.rename(path.join(output,'partial.next'),path.join(output,'partial.json'));});
  return writing;
}
function failure(code){if(report.failures.length<64)report.failures.push({code,elapsed_ms:started?Math.round(performance.now()-started):null});}
function finish(status){if(finished)return;finished=true;report.status=status;resolveDone();}
function track(promise){pending.add(promise);promise.finally(()=>pending.delete(promise));}
async function identityLogout(){
  if(!identityLoggedIn)return;
  const status=await ownerPage.evaluate(async()=>{
    await fetch('/~/logout',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'',redirect:'follow'});
    return (await fetch('/stead-identity/api/list',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({protocol:'stead.identity/1'})})).status;
  });
  assert.equal(status,401);identityLoggedIn=false;report.cleanup.identity='logout-confirmed';
  await ownerContext.close();await ownerBrowser.close();ownerContext=ownerBrowser=null;
  await checkpoint();
}
async function observe(response){
  const url=new URL(response.url());
  if(!started||finished||url.origin!==HOME||!['/stead/api/query','/stead/api/command','/stead/auth/logout'].includes(url.pathname))return;
  const request=response.request().postDataBuffer();
  if(!request||request.length>65536)throw new Error('request_bound');
  const raw=await response.body();if(raw.length>262144)throw new Error('response_bound');
  if(!response.headers()['content-type']?.startsWith('application/json'))throw new Error('response_type');
  const sent=JSON.parse(request), value=JSON.parse(raw);
  if(response.status()!==200||value.status==='rejected'){failure('app_request_rejected');return;}
  if(url.pathname==='/stead/auth/logout'){report.human_home_signout=value.status==='logged_out';person=null;return;}
  if(url.pathname==='/stead/api/command'){
    const receipt=acceptedReceipt(sent,value,person);assert.equal(receipt.project_id,config.project.id);
    if(report.accepted.length>=64)throw new Error('receipt_count');
    const kind=sent.operation.split('.')[0];
    if(sent.expected_revision==='0'&&created[kind])created[kind].add(receipt.resource_id);
    const body=kind==='document'?sha(sent.payload.markdown):kind==='work'?workBody(sent.payload):null;
    if(!report.accepted.some(row=>row.request_id===receipt.request_id))report.accepted.push({...receipt,
      ...(body?{body_sha256:body}:{}),response_sha256:sha(raw),elapsed_ms:Math.round(performance.now()-started)});
    if(body)saved.set(scope(receipt.project_id,kind,receipt.container_id,receipt.resource_id),
      {request_id:receipt.request_id,revision:receipt.resource_revision,body});
    return;
  }
  if(value.protocol!=='stead.query-result/3'||value.status!=='read'||value.request_id!==sent.request_id||value.kind!==sent.kind
      ||['project_id','container_id','resource_id'].some(key=>value[key]!==sent[key])||!value.rows||Array.isArray(value.rows)
      ||Object.keys(value.rows).length>20)throw new Error('query_correlation');
  if(sent.kind==='identity'){person=personalIdentity(sent,value,config.person,runtime);report.identity_observed=true;}
  if(report.reads.length<256)report.reads.push({kind:sent.kind,request_id:sent.request_id,project_id:sent.project_id,
    container_id:sent.container_id,resource_id:sent.resource_id,row_count:Object.keys(value.rows).length,response_sha256:sha(raw),
    elapsed_ms:Math.round(performance.now()-started)});
  if(sent.kind==='containers')for(const accepted of report.accepted.filter(row=>row.operation==='container.create')){
    const matched=collectionReadback(sent,value,accepted);
    if(matched&&report.collection_readbacks.length<64)report.collection_readbacks.push({...matched,response_sha256:sha(raw)});
  }
  if(['work','document'].includes(sent.kind)&&sent.resource_id)for(const row of Object.values(value.rows)){
    if(row.kind!==sent.kind||row.resource_id!==sent.resource_id||row.container_id!==sent.container_id)continue;
    const prior=saved.get(scope(sent.project_id,sent.kind,sent.container_id,sent.resource_id));
    const body=sent.kind==='document'?(typeof row.markdown==='string'?sha(row.markdown):''):workBody(row);
    if(prior&&row.resource_revision===prior.revision&&body===prior.body&&report.readbacks.length<64)
      report.readbacks.push({project_id:sent.project_id,resource_id:sent.resource_id,container_id:sent.container_id,
        revision:prior.revision,kind:sent.kind,body_sha256:prior.body,accepted_request_id:prior.request_id,
        query_request_id:sent.request_id,response_sha256:sha(raw)});
  }
}
try{
  // The private pipe is consumed once, never placed in a file or participant UI.
  let code='';for await(const chunk of process.stdin){code+=chunk;assert.ok(Buffer.byteLength(code)<=128);}
  code=code.trim();assert.match(code,/^(?:[a-z]{6}-){3}[a-z]{6}$/u);
  ownerContext=await chromium.launchPersistentContext(ownerProfile,{executablePath:'/usr/bin/chromium',headless:true,
    chromiumSandbox:true,ignoreHTTPSErrors:false,serviceWorkers:'block',args});
  ownerBrowser=ownerContext.browser();
  await ownerContext.route('**/*',route=>{
    const url=new URL(route.request().url());
    const allowed=url.origin===IDENTITY&&(url.pathname==='/~/login'||url.pathname==='/~/logout'
      ||url.pathname.startsWith('/stead-identity/'));
    return allowed?route.continue():route.abort('blockedbyclient');
  });
  ownerPage=await ownerContext.newPage();await ownerPage.goto(IDENTITY+'/stead-identity/');
  const login=await ownerPage.evaluate(async password=>(await fetch('/~/login',{method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({password,redirect:'/stead-identity/'}),redirect:'follow'})).status,code);
  code='';assert.equal(login,200);identityLoggedIn=true;report.cleanup.identity='pending-owned-session';
  await ownerPage.reload();await ownerPage.getByRole('button',{name:'Refresh requests',exact:true}).waitFor();
  // Automatically retire an unused owner approval session; the participant
  // receives only Home's scoped native member cookie after the one approval.
  ownerTimer=setTimeout(()=>{void identityLogout().catch(()=>{failure('identity_cleanup_unconfirmed');finish('setup-expired');});},15*60*1000);
  participant=await chromium.launchPersistentContext(profile,{executablePath:'/usr/bin/chromium',headless:false,
    chromiumSandbox:true,ignoreHTTPSErrors:false,serviceWorkers:'block',viewport:{width:1280,height:900},locale:'en-US',
    args:[...args,'--ozone-platform=wayland']});
  await participant.route('**/*',route=>{
    const request=route.request(),url=new URL(request.url());
    if(url.origin!==HOME)return route.abort('blockedbyclient');
    if(url.pathname==='/~/login'||url.pathname==='/~/logout'||url.pathname.startsWith('/stead-identity/'))return route.abort('blockedbyclient');
    if(url.pathname==='/stead/api/command'){
      let sent;try{sent=request.postDataJSON();}catch{}
      if(!permittedCommand(sent,config.project.id,created,started&&!finished,person)){
        failure('out_of_trial_command_blocked');return route.abort('blockedbyclient');
      }
    }
    if(url.pathname==='/stead/api/code'){
      let sent;try{sent=request.postDataJSON();}catch{}
      // This exact read is already native-authorized; it must not depend on
      // when passive receipt capture learns that a newly saved Work exists.
      if(!permittedCodeRead(sent,config.project.id))return route.abort('blockedbyclient');
    }
    return route.continue();
  });
  participant.on('response',response=>{const work=observe(response).then(checkpoint).catch(()=>{
    failure('receipt_or_read_observation_failed');void checkpoint().catch(()=>{fatal=true;finish('evidence-incomplete');});
  });track(work);});
  participant.on('page',page=>page.on('pageerror',()=>{if(started&&!finished)failure('page_error');}));
  participant.on('close',()=>finish('browser-closed-incomplete'));
  home=await participant.newPage();await home.goto(HOME+'/stead/');
  const capabilities=await home.evaluate(async()=>{
    const reply=await fetch('/stead/api/capabilities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({protocol:'stead.capabilities/3'})});
    if(reply.status!==200)throw new Error('Capability refusal');return reply.json();
  });
  assert.equal(capabilities.protocol,'stead.capabilities/3');assert.equal(capabilities.commands,'stead.command/3');
  assert.equal(capabilities.queries,'stead.query/3');assert.equal(capabilities.authentication,'native-approved-browser/1');
  assert.equal(typeof capabilities.runtime,'string');assert.ok(capabilities.runtime&&capabilities.runtime.length<=128);
  runtime=capabilities.runtime;report.runtime=runtime;report.capabilities_sha256=sha(JSON.stringify(capabilities));
  assert.equal((await participant.cookies(HOME)).some(cookie=>cookie.name==='__Host-stead-session'),false);
  assert.equal((await participant.cookies(IDENTITY)).length,0);
  taskPage=await participant.newPage();
  await taskPage.exposeBinding('startTrial',async({frame})=>{
    if(frame!==taskPage.mainFrame()||taskPage.url()!=='about:blank'||started||finished)throw new Error('Invalid start');
    clearTimeout(readyTimer);started=performance.now();report.started_at=new Date().toISOString();report.status='observing';
    timer=setTimeout(()=>finish('deadline-incomplete'),10*60*1000);await checkpoint();return true;
  });
  await taskPage.exposeBinding('inspectApproval',async({frame})=>{
    if(frame!==taskPage.mainFrame()||taskPage.url()!=='about:blank'||!started||finished||identityUsed||approvalBusy||!identityLoggedIn)throw new Error('Approval unavailable');
    const comparison=(await home.locator('dd.comparison').textContent({timeout:3000}))?.trim();
    assert.match(comparison,/^[0-9a-f]{12}$/u);
    assert.ok((await home.locator('.urbit-approval-summary').innerText()).includes(HOME));
    await ownerPage.getByRole('button',{name:'Refresh requests',exact:true}).click();
    const request=ownerPage.locator('article.identity-request').filter({has:ownerPage.getByRole('heading',{name:comparison,exact:true})});
    assert.equal(await request.count(),1);assert.equal(exactApproval(await request.innerText(),comparison,config.person.identity_ship,HOME),true);
    return {comparison,home:HOME,ship:config.person.identity_ship};
  });
  await taskPage.exposeBinding('approveSignin',async({frame},comparison)=>{
    if(frame!==taskPage.mainFrame()||taskPage.url()!=='about:blank'||!started||finished||identityUsed||approvalBusy||!identityLoggedIn)throw new Error('Approval unavailable');
    approvalBusy=true;
    try{
      assert.match(comparison,/^[0-9a-f]{12}$/u);
      assert.equal((await home.locator('dd.comparison').textContent())?.trim(),comparison);
      const request=ownerPage.locator('article.identity-request').filter({has:ownerPage.getByRole('heading',{name:comparison,exact:true})});
      assert.equal(await request.count(),1);assert.equal(exactApproval(await request.innerText(),comparison,config.person.identity_ship,HOME),true);
      await request.getByRole('button',{name:'Approve sign-in',exact:true}).click();
      await request.getByText('Approval sent. Return to your Stead tab and check approval.',{exact:true}).waitFor();
      identityUsed=true;report.human_requested_scoped_approval=true;
      clearTimeout(ownerTimer);await identityLogout();return true;
    }finally{approvalBusy=false;}
  });
  await taskPage.exposeBinding('finishTrial',async({frame},value)=>{
    if(frame!==taskPage.mainFrame()||taskPage.url()!=='about:blank'||!started||finished||!value||!['yes','no'].includes(value.help)
      ||typeof value.notes!=='string'||value.notes.length>2000||!Array.isArray(value.tasks)||value.tasks.length>5
      ||value.tasks.some(n=>!Number.isInteger(n)||n<1||n>5))throw new Error('Feedback boundary');
    report.feedback={help:value.help,tasks:[...new Set(value.tasks)],notes:value.notes.replace(/(?:[a-z]{6}-){3}[a-z]{6}/gu,'[redacted code]')};
    report.maintainer_coaching=value.help==='no'?'participant-reports-none':'participant-reports-help';
    finish('submitted-for-review');return true;
  });
  await taskPage.setContent(`<!doctype html><html lang="en"><meta charset="utf-8"><title>Stead participant trial</title>
  <style>body{font:18px/1.5 system-ui;max-width:850px;margin:2rem auto;padding:0 1rem;color:#182a2b;background:#f7f6f2}button,input,select,textarea{font:inherit}button{min-height:44px;padding:.6rem 1rem}li{margin:.8rem 0}textarea{width:95%}:focus-visible{outline:3px solid #ac4d00;outline-offset:3px}code{overflow-wrap:anywhere}fieldset{margin:1rem 0}</style>
  <h1>Your Work and Docs trial</h1><p id="state" role="status">Prepared. The timer has not started.</p>
  <p>This uses the named pilot with the owner's permission. Use only invented information in <strong>${escape(config.project.title)}</strong>. The existing member identity is <strong>${escape(config.person.identity_ship)}</strong>. Its private code and owner session are not shared with you. The Home member session keeps this identity's existing native grants; this observer limits only this browser flow, not native authority.</p>
  <p>Recording collects bounded receipt and readback identifiers and content hashes, not keystrokes, screenshots or document contents. Checking a task box is feedback, not proof of success.</p>
  <ol><li>Sign in to the open Stead tab using <strong>${escape(config.person.identity_ship)}</strong>. When it shows a comparison, return here to review and approve just that sign-in, then check approval in Stead.</li>
  <li>Open <strong>${escape(config.project.title)}</strong>. Create a Work item about an invented garden task. Save it, change its description, save again, and reopen it.</li>
  <li>Create a private collection in Docs. Add an invented garden note, save it, then edit, save and reopen it.</li>
  <li>Find your Work item through Search. Open Activity and identify your changes.</li>
  <li>Sign out of Stead. Return here and finish the trial.</li></ol>
  <p>Please try without coaching. If something blocks you, tell us in the feedback; failure is useful evidence.</p>
  <button id="start">Start ten-minute trial</button>
  <fieldset id="approval" disabled><legend>Operator-prepared approval for only your Stead sign-in</legend><button id="inspect">Review pending sign-in</button><p id="comparison" role="status"></p><button id="approve" disabled>Approve this Stead sign-in</button></fieldset>
  <form id="feedback"><fieldset id="feedback-fields" disabled><legend>Finish and give feedback</legend>${[1,2,3,4,5].map(n=>`<label><input type="checkbox" name="task" value="${n}"> Task ${n}</label><br>`).join('')}
  <p><label>Did you need help? <select name="help" required><option value="">Choose</option><option value="no">No</option><option value="yes">Yes</option></select></label></p>
  <label>What was confusing or blocked?<br><textarea name="notes" maxlength="2000" rows="4"></textarea></label><p><button>Finish trial</button></p></fieldset></form>
  <script>let comparison='';document.querySelector('#start').onclick=async e=>{e.target.disabled=true;try{await window.startTrial();document.querySelector('#approval').disabled=false;document.querySelector('#feedback-fields').disabled=false;document.querySelector('#state').textContent='Recording started. Ten minutes are available.';}catch{document.querySelector('#state').textContent='Could not start. Tell the operator.';}};
  document.querySelector('#inspect').onclick=async()=>{try{const r=await window.inspectApproval();comparison=r.comparison;document.querySelector('#comparison').textContent=r.ship+' → '+r.home+' · comparison '+r.comparison;document.querySelector('#approve').disabled=false;}catch{comparison='';document.querySelector('#approve').disabled=true;document.querySelector('#comparison').textContent='No matching pending request yet. Request sign-in in Stead, then try again.';}};
  document.querySelector('#approve').onclick=async e=>{e.target.disabled=true;try{await window.approveSignin(comparison);document.querySelector('#approval').disabled=true;document.querySelector('#comparison').textContent='Approved. The private Identity session is closed. Return to Stead and check approval.';}catch{document.querySelector('#comparison').textContent='Approval was not confirmed. Tell the operator.';}};
  document.querySelector('#feedback').onsubmit=async e=>{e.preventDefault();const d=new FormData(e.target);e.target.querySelector('button').disabled=true;await window.finishTrial({help:d.get('help'),notes:d.get('notes'),tasks:d.getAll('task').map(Number)});};</script></html>`);
  await taskPage.bringToFront();report.status='waiting-for-participant-start';await checkpoint();
  await fs.writeFile(path.join(output,'ready.json'),JSON.stringify({status:report.status,started_at:null,
    source:SOURCE,project_id:config.project.id,identity_owner_hidden:true,participant_owner_cookie:false})+'\n',{flag:'wx',mode:0o600});
  readyTimer=setTimeout(()=>finish('not-started-before-readiness-expired'),180000);
  countdown=setInterval(()=>{if(started&&!finished)void taskPage.locator('#state').evaluate((el,left)=>{el.textContent=Math.ceil(left/60)+' minutes remain. Return here to finish.';},Math.max(0,600-(performance.now()-started)/1000)).catch(()=>{});},30000);
  process.once('SIGTERM',()=>finish('operator-stopped'));process.once('SIGINT',()=>finish('operator-stopped'));
  await done;await Promise.allSettled([...pending]);
}catch{
  fatal=true;failure('observer_setup_or_capture_failed');report.status='evidence-incomplete';
}finally{
  finished=true;clearTimeout(timer);clearTimeout(ownerTimer);clearTimeout(readyTimer);clearInterval(countdown);
  if(started)report.elapsed_ms=Math.round(performance.now()-started);
  try{await identityLogout();}catch{report.cleanup.identity='unconfirmed';fatal=true;}
  try{
    if(home&&!home.isClosed()&&await home.getByRole('button',{name:'Sign out',exact:true}).count()){
      await home.getByRole('button',{name:'Sign out',exact:true}).click();
      await home.getByRole('heading',{name:'Sign in with Urbit',exact:true}).waitFor();
    }
    if(home&&!home.isClosed()){
      const status=await home.evaluate(async()=>(await fetch('/stead/api/query',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status);
      assert.equal(status,401);report.cleanup.home='logout-confirmed';
    }else report.cleanup.home='browser-closed-unconfirmed';
  }catch{report.cleanup.home='unconfirmed';fatal=true;}
  try{await participant?.close();}catch{fatal=true;}
  try{await ownerBrowser?.close();}catch{fatal=true;}
  await writing.catch(()=>{fatal=true;});
  if(fatal)report.status='evidence-incomplete';
  await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx',mode:0o600});
  // The outer owner removes this private profile only after the entire browser cgroup is empty.
}
process.exitCode=fatal?1:0;

// Restore the unchanged cookie and observe natural browser AND native expiry.
// No response mocks, cookie expiry edits, clock overrides or shortened policy.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import https from 'node:https';
import path from 'node:path';
import {firefox} from 'playwright';
const [profile, fixture, output, sessionFile] = process.argv.slice(2);
assert.equal(process.version,'v24.21.0');
const material = JSON.parse(await readFile(fixture,'utf8'));
const sessionBytes = await readFile(sessionFile);
const session = JSON.parse(sessionBytes);
const origin = 'https://home.localhost:8443';
assert.equal(material.origin,origin); assert.equal(session.origin,origin);
assert.equal(session.execution_id,material.execution_id); assert.equal(session.format,1);
const cookie = session.cookie;
assert.equal(cookie.name,'__Host-stead-session'); assert.equal(cookie.domain,'home.localhost');
assert.equal(cookie.path,'/'); assert.equal(cookie.secure,true); assert.equal(cookie.httpOnly,true);
assert.equal(cookie.sameSite,'Strict'); assert.match(cookie.value,/^[0-9a-f]{64}$/u);
const issued = session.issued_before_ms, captured = session.captured_at_ms;
assert.ok(Number.isSafeInteger(issued) && Number.isSafeInteger(captured) && issued > 0
  && captured >= issued && captured - issued <= 120000 && Number.isFinite(cookie.expires));
const expires = cookie.expires * 1000;
assert.ok(expires >= issued + 1800000 - 1000 && expires <= captured + 1800000 + 1000);
const age = Date.now() - issued;
assert.ok(age >= 28 * 60000 && age <= 29 * 60000,'Launch during the recorded natural-expiry window');
const report = {classification:'real-browser-native-natural-session-expiry',status:'fail',qualifies_phase:false,
  execution_id:material.execution_id,issued_before_ms:issued,session_prepared_at_ms:captured,
  cookie_expiry_ms:expires,session_file_sha256:createHash('sha256').update(sessionBytes).digest('hex'),
  checks:[],http:[],capture_errors:[],capture_truncated:false,bearer_controls:[]};
// This TLS control deliberately sends the old bearer after Firefox stops
// sending its expired cookie. It cannot extend or refresh the session.
const ca = await readFile(path.join(path.dirname(fixture),'certificates/ca.pem'));
function unchangedBearer() {
  return new Promise((resolve,reject) => {
    const body = Buffer.from('{}');
    const request = https.request({host:'127.0.0.1',port:8443,servername:'home.localhost',
      ca,rejectUnauthorized:true,method:'POST',path:'/stead/api/query',agent:false,
      headers:{Host:'home.localhost:8443',Origin:origin,'Content-Type':'application/json',
        'Content-Length':body.length,Cookie:cookie.name + '=' + cookie.value}}, response => {
      const chunks = []; let length = 0;
      response.on('data',chunk => { length += chunk.length;
        if (length > 262144) request.destroy(new Error('bounded_bearer_response')); else chunks.push(chunk); });
      response.on('error',reject);
      response.on('end',() => { try {
        assert.equal(response.complete,true);
        assert.ok(response.headers['content-type']?.startsWith('application/json'));
        const value = JSON.parse(Buffer.concat(chunks));
        resolve({status:response.statusCode,error:value.error,at_ms:Date.now()});
      } catch (error) { reject(error); } });
    });
    const deadline = setTimeout(() => request.destroy(new Error('bounded_bearer_deadline')),5000);
    request.on('close',() => clearTimeout(deadline));
    request.on('error',reject); request.end(body);
  });
}
const context = await firefox.launchPersistentContext(profile,{headless:true,ignoreHTTPSErrors:false,serviceWorkers:'block'});
const pending = new Set();
try {
  const liveBearer = await unchangedBearer(); report.bearer_controls.push(liveBearer);
  assert.equal(liveBearer.status,403); assert.equal(liveBearer.error,'invalid_csrf');
  assert.ok(liveBearer.at_ms < issued + 1800000);
  await context.route('**/*',route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort('blockedbyclient'));
  await context.addCookies([cookie]);
  const page = await context.newPage(); page.setDefaultTimeout(25000);
  page.on('response',response => {
    const pathname = new URL(response.url()).pathname;
    if (!['/stead/auth/resume','/stead/api/updates'].includes(pathname)) return;
    if (report.http.length + pending.size >= 128) { report.capture_truncated = true; return; }
    const received = Date.now();
    const task = (async () => {
      const bytes = await response.body(); assert.ok(bytes.length <= 262144);
      const value = JSON.parse(bytes);
      report.http.push({path:pathname,status:response.status(),outcome:value.status ?? '',error:value.error ?? '',at_ms:received});
    })().catch(error => { report.capture_errors.push(error.constructor.name); });
    pending.add(task); void task.finally(() => pending.delete(task));
  });
  await page.goto(origin + '/stead/');
  await page.getByRole('button',{name:/GARDEN.*Garden α/u}).click();
  await page.getByRole('button',{name:'Docs',exact:true}).click();
  await page.getByLabel('Collection',{exact:true}).selectOption({label:'Private notebook α · Private drafts'});
  await page.locator('.resource-row').filter({has:page.getByRole('heading',{name:/UNSELECTED-PRIVATE-CANARY/u})})
    .getByRole('button',{name:'Open page',exact:true}).click();
  const editor = page.getByRole('textbox',{name:'Markdown source',exact:true});
  assert.ok((await editor.inputValue()).includes('UNSELECTED-PRIVATE-CANARY'));
  await editor.fill((await editor.inputValue()) + '\nUnsaved natural expiry canary.');
  await page.locator('#project-content[data-live-updates="connected"]').waitFor();
  report.checks.push({name:'real-session-still-authorized-before-expiry-with-private-draft',passed:true,at_ms:Date.now()});
  await page.getByRole('button',{name:'Request sign-in',exact:true}).waitFor({timeout:240000});
  await Promise.all([...pending]);
  assert.deepEqual(report.capture_errors,[]); assert.equal(report.capture_truncated,false);
  assert.ok(report.http.some(row => row.path === '/stead/auth/resume' && row.status === 200 && row.outcome === 'authenticated'));
  const expiry = report.http.find(row => row.path === '/stead/api/updates' && row.status === 401 && row.error === 'session_required');
  assert.ok(expiry && expiry.at_ms >= issued + 1800000 - 1000 && expiry.at_ms <= captured + 1800000 + 30000);
  assert.ok(report.http.some(row => row.path === '/stead/api/updates' && row.status === 200
    && row.outcome === 'updated' && row.at_ms < expiry.at_ms));
  assert.equal(await editor.count(),0);
  const visible = await page.locator('main').innerText();
  assert.ok(!visible.includes('UNSELECTED-PRIVATE-CANARY') && !visible.includes('Unsaved natural expiry canary'));
  assert.equal(await page.getByRole('button',{name:/GARDEN/u}).count(),0);
  // Wait for the latest possible original issue time without changing clocks.
  const remaining = captured + 1800000 + 1000 - Date.now();
  if (remaining > 0) await new Promise(resolve => setTimeout(resolve,remaining));
  const expiredBearer = await unchangedBearer(); report.bearer_controls.push(expiredBearer);
  assert.equal(expiredBearer.status,401); assert.equal(expiredBearer.error,'session_required');
  assert.ok(expiredBearer.at_ms >= captured + 1800000 && expiredBearer.at_ms <= captured + 1800000 + 40000);
  assert.equal(createHash('sha256').update(await readFile(sessionFile)).digest('hex'),report.session_file_sha256);
  report.checks.push({name:'unchanged-expired-bearer-rejected-by-real-native-authorization',passed:true,at_ms:expiredBearer.at_ms});
  report.checks.push({name:'natural-expiry-clears-rendered-protected-view-and-draft',passed:true,at_ms:expiry.at_ms});
  report.status = 'pass';
} catch (error) {
  report.error_type = error.constructor.name;
  throw new Error('Natural native expiry check failed; inspect private evidence');
} finally {
  await Promise.allSettled([...pending]);
  if (report.capture_errors.length || report.capture_truncated) report.status = 'fail';
  try { await writeFile(output + '/browser-report.json',JSON.stringify(report,null,2)+'\n',{flag:'wx',mode:0o600}); }
  finally { await context.close(); }
  assert.equal(report.status,'pass');
}

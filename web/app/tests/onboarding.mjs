// Human-operated Firefox against the real native fixture. No app clicks/fills.
import assert from 'node:assert/strict';
import {readFile, writeFile, rename} from 'node:fs/promises';
import {firefox} from 'playwright';
import {acceptedReceipt, personalIdentity, sha, scope, workBody} from './onboarding-evidence.mjs';
const [profile, input, output] = process.argv.slice(2);
assert.equal(process.version, 'v24.21.0');
assert.ok(!process.env.SSLKEYLOGFILE);
const material = JSON.parse(await readFile(input, 'utf8'));
assert.equal(material.origin, 'https://home.localhost:8443');
assert.equal(material.identity_origin, 'https://bus.localhost:8444');
assert.equal(material.identity_ship, '~bus');
const task = await readFile(new URL('../../../docs/urbit/quickstarts/onboarding-task.md', import.meta.url), 'utf8');
const guide = await readFile(new URL('../../../docs/urbit/quickstarts/member.md', import.meta.url), 'utf8');
const escape = value => value.replace(/[&<>"']/gu, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const report = {classification: 'independent-human-local-native-browser', status: 'incomplete',
  qualifies_phase: false, participant: 'human-user', maintainer_coaching: 'not-attested',
  execution_id: material.execution_id, started_at: null, elapsed_ms: null,
  accepted: [], reads: [], failures: [], readbacks: [], feedback: null, signed_out: false,
  source: {task: sha(task), guide: sha(guide)}};
const context = await firefox.launchPersistentContext(profile, {headless: false, ignoreHTTPSErrors: false,
  serviceWorkers: 'block', locale: 'en-US', timezoneId: 'America/New_York', viewport: {width: 1180, height: 850}});
report.browser = context.browser().version();
const origins = new Set([material.origin, material.identity_origin]);
await context.route('**/*', route => origins.has(new URL(route.request().url()).origin) ? route.continue() : route.abort('blockedbyclient'));
let person = null, started = 0, finished = false;
const pending = new Set(), saved = new Map();
let persistence = Promise.resolve();
function checkpoint() {
  const bytes = JSON.stringify({...report, checkpoint_status: 'incomplete-until-reviewed',
    elapsed_ms: started ? Math.round(performance.now() - started) : null}, null, 2) + '\n';
  if (Buffer.byteLength(bytes) > 1024 * 1024) throw new Error('evidence_bound');
  persistence = persistence.then(async () => {
    await writeFile(output + '/onboarding-partial.tmp', bytes, {mode:0o600});
    await rename(output + '/onboarding-partial.tmp', output + '/onboarding-partial.json');
  });
  return persistence;
}
const evidenceId = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u.test(value) ? value : '';
function failure(code) { if (report.failures.length < 64) report.failures.push({code, elapsed_ms: started ? Math.round(performance.now() - started) : 0}); }
async function observe(response) {
  const url = new URL(response.url());
  if (!started || finished || url.origin !== material.origin || !['/stead/api/command','/stead/api/query','/stead/auth/logout'].includes(url.pathname)) return;
  const request = response.request().postDataBuffer();
  if (!request || request.length > 65536) throw new Error('request_bound');
  const bytes = await response.body();
  if (bytes.length > 262144 || response.headers()['content-type']?.split(';')[0] !== 'application/json') throw new Error('response_bound');
  const sent = JSON.parse(request), value = JSON.parse(bytes);
  if (response.status() !== 200 || value.status === 'rejected') { failure('app_request_rejected'); return; }
  if (url.pathname === '/stead/auth/logout') { report.signed_out = value.status === 'logged_out'; person = null; return; }
  if (url.pathname === '/stead/api/command') {
    if (report.accepted.length >= 64) throw new Error('receipt_count');
    const receipt = acceptedReceipt(sent, value, person);
    const content = ['work.create','work.update'].includes(sent.operation)
      ? {body_sha256:workBody(sent.payload), description_sha256:sha(sent.payload.description)}
      : sent.operation === 'document.save' ? {body_sha256:sha(sent.payload.markdown)} : {};
    if (!report.accepted.some(row => row.request_id === receipt.request_id)) {
      report.accepted.push({...receipt, ...content, elapsed_ms: Math.round(performance.now() - started), response_sha256: sha(bytes)});
    }
    if (['work.create','work.update','document.save'].includes(sent.operation)) {
      const kind = sent.operation.split('.')[0];
      saved.set(scope(receipt.project_id, kind, receipt.container_id, receipt.resource_id),
        {request_id: receipt.request_id, revision: receipt.resource_revision,
          body: kind === 'document' ? sha(sent.payload.markdown) : workBody(sent.payload)});
    }
    return;
  }
  if (value.protocol !== 'stead.query-result/3' || value.status !== 'read' || value.request_id !== sent.request_id
      || value.kind !== sent.kind || ['project_id','resource_id','container_id'].some(key => value[key] !== sent[key])
      || !value.rows || Array.isArray(value.rows) || Object.keys(value.rows).length > 20) throw new Error('query_correlation');
  if (sent.kind === 'identity') person = personalIdentity(sent, value);
  if (report.reads.length < 256) report.reads.push({kind: sent.kind, request_id: sent.request_id,
    project_id: sent.project_id, container_id: sent.container_id, resource_id: sent.resource_id, response_sha256: sha(bytes),
    observed_rows: Object.values(value.rows).map(row => ({resource_id: evidenceId(row.resource_id),
      container_id: evidenceId(row.container_id), request_id: evidenceId(row.request_id)}))});
  if (['work','document'].includes(sent.kind) && sent.resource_id) {
    for (const row of Object.values(value.rows)) {
      if (row.kind !== sent.kind || row.resource_id !== sent.resource_id || row.container_id !== sent.container_id) continue;
      const prior = saved.get(scope(sent.project_id, sent.kind, sent.container_id, sent.resource_id));
      const body = sent.kind === 'document' ? (typeof row.markdown === 'string' ? sha(row.markdown) : '') : workBody(row);
      if (prior && row.resource_revision === prior.revision && body === prior.body
          && report.readbacks.length < 64) report.readbacks.push({resource_id: row.resource_id, revision: prior.revision,
        project_id: sent.project_id, container_id: sent.container_id, accepted_request_id: prior.request_id,
        query_request_id: sent.request_id, kind: sent.kind, body_sha256: prior.body, response_sha256: sha(bytes)});
    }
  }
}
context.on('response', response => {
  const url = new URL(response.url());
  if (!started || finished || url.origin !== material.origin || !['/stead/api/command','/stead/api/query','/stead/auth/logout'].includes(url.pathname)) return;
  const task = observe(response).catch(error => failure(['request_bound','response_bound','receipt_count','receipt_shape',
    'receipt_correlation','identity_correlation','identity_actor','query_correlation'].includes(error.message) ? error.message : 'observer_error'))
    .then(checkpoint).catch(() => { failure('evidence_write_failed'); finished = true; report.status = 'evidence-incomplete'; resolveFinished(); });
  pending.add(task); task.finally(() => pending.delete(task));
});
function recordFailure(code) {
  failure(code);
  void checkpoint().catch(() => { finished = true; report.status = 'evidence-incomplete'; resolveFinished(); });
}
context.on('page', page => page.on('pageerror', () => recordFailure('page_error')));
context.on('requestfailed', request => {
  const url = new URL(request.url());
  if (!started || finished || !origins.has(url.origin) || report.failures.length >= 64) return;
  const category = url.pathname.startsWith('/stead/api/') ? 'business-api' : url.pathname.startsWith('/stead/auth/')
    ? 'sign-in' : url.pathname.startsWith('/stead-identity/') || url.pathname === '/~/login' ? 'personal-identity' : 'local-resource';
  report.failures.push({code: 'request_failed', origin: url.origin, category,
    method: ['GET','POST','PUT','DELETE'].includes(request.method()) ? request.method() : 'other',
    elapsed_ms: Math.round(performance.now() - started)});
  void checkpoint().catch(() => { finished = true; report.status = 'evidence-incomplete'; resolveFinished(); });
});
let resolveFinished;
const completed = new Promise(resolve => { resolveFinished = resolve; });
let timer, countdown;
try {
  const page = await context.newPage();
  await page.exposeBinding('finishTrial', async ({frame}, value) => {
    if (frame !== page.mainFrame() || finished || !started || !value || !['yes','no'].includes(value.help)
        || typeof value.notes !== 'string' || value.notes.length > 2000
        || !Array.isArray(value.tasks) || value.tasks.length > 5
        || value.tasks.some(item => !Number.isInteger(item) || item < 1 || item > 5)) throw new Error('Invalid trial submission');
    finished = true; report.feedback = {tasks: [...new Set(value.tasks)], notes: value.notes.replaceAll(material.code, '[redacted personal code]'), help: value.help};
    report.maintainer_coaching = value.help === 'no' ? 'participant-reports-none' : 'participant-reports-help';
    report.status = 'submitted-for-review';
    try { await checkpoint(); } finally { resolveFinished(); }
  });
  await page.setContent(`<!doctype html><html lang="en"><meta charset="utf-8"><title>Stead local trial</title>
    <style>body{font:18px/1.5 system-ui;max-width:850px;margin:2rem auto;padding:0 1rem;background:#f7f6f2;color:#182a2b}pre{white-space:pre-wrap;font:inherit}code{background:#e3e8e4;padding:.2rem}button,input,textarea,select{font:inherit}button{padding:.6rem 1rem}textarea{width:95%}fieldset{margin:1rem 0}a{color:#15548c}li{margin:.5rem 0}:focus-visible{outline:3px solid #ac4d00;outline-offset:3px}</style>
    <h1>Stead: your local trial</h1><p id="remaining" role="status">Nine minutes are available after the pages open.</p>
    <p>Your personal identity is <strong>~bus</strong>. Its disposable sign-in code is <code>${escape(material.code)}</code>.</p>
    <p><a href="${material.origin}/stead/" target="_blank" rel="noreferrer">Open Stead home</a> ·
    <a href="${material.identity_origin}/stead-identity/" target="_blank" rel="noreferrer">Open personal identity</a></p>
    <pre>${escape(task)}</pre><details><summary>Member quickstart</summary><pre>${escape(guide)}</pre></details>
    <form id="feedback"><fieldset><legend>Tasks you completed</legend>${[1,2,3,4,5].map(n => `<label><input type="checkbox" name="task" value="${n}"> Task ${n}</label><br>`).join('')}</fieldset>
    <p><label>Did you need help beyond this quickstart? <select name="help" required><option value="">Choose</option><option value="no">No</option><option value="yes">Yes</option></select></label></p>
    <p><label>What was confusing or blocked?<br><textarea name="notes" maxlength="2000" rows="4"></textarea></label></p>
    <button type="submit">Finish trial</button></form><script>
    document.querySelector('#feedback').addEventListener('submit', async event => { event.preventDefault();
      const data = new FormData(event.target); event.target.querySelector('button').disabled = true;
      try { await window.finishTrial({help:data.get('help'),notes:data.get('notes'),tasks:data.getAll('task').map(Number)}); }
      catch { event.target.querySelector('button').disabled = false; }
    });
    </script></html>`);
  const home = await context.newPage(); await home.goto(material.origin + '/stead/');
  const identity = await context.newPage(); await identity.goto(material.identity_origin + '/stead-identity/');
  await page.bringToFront();
  started = performance.now(); report.started_at = new Date().toISOString();
  await checkpoint();
  await writeFile(output + '/ready.json', JSON.stringify({status:'ready', execution_id:material.execution_id,
    started_at:report.started_at, duration_seconds:540}) + '\n', {flag:'wx',mode:0o600});
  timer = setTimeout(() => { finished = true; report.status = 'deadline-incomplete'; resolveFinished(); }, 540000);
  countdown = setInterval(() => { if (!finished) page.locator('#remaining').textContent().then(() => page.evaluate(seconds => {
    document.querySelector('#remaining').textContent = `${Math.ceil(seconds / 60)} minutes remain. Return here to finish.`;
  }, Math.max(0, 540 - (performance.now() - started) / 1000))).catch(() => {}); }, 30000);
  context.on('close', () => { if (!finished) { finished = true; report.status = 'browser-closed-incomplete'; resolveFinished(); } });
  await completed; clearInterval(countdown); clearTimeout(timer);
  await Promise.allSettled([...pending]);
  report.elapsed_ms = Math.round(performance.now() - started);
} finally {
  clearTimeout(timer); clearInterval(countdown);
  if (started && report.elapsed_ms === null) report.elapsed_ms = Math.round(performance.now() - started);
  try {
    await persistence;
    await writeFile(output + '/onboarding-report.json', JSON.stringify(report, null, 2) + '\n', {flag:'wx',mode:0o600});
  } finally { await context.close(); }
}

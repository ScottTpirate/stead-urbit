// Real Firefox -> byte relay -> native Eyre -> configured Gall, synthetic data.
// No response mocks, ignored certificate failures, sandbox bypass, or live +code.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {firefox} from 'playwright';
const [profile, fixture, output] = process.argv.slice(2);
assert.equal(process.version, 'v24.21.0');
assert.ok(!process.env.SSLKEYLOGFILE);
const material = JSON.parse(await readFile(fixture, 'utf8'));
const origin = 'https://home.localhost:8443';
assert.equal(material.origin, origin);
const root = await firefox.launchPersistentContext(profile, {headless: true, ignoreHTTPSErrors: false, serviceWorkers: 'block',
  locale: 'en-US', timezoneId: 'America/New_York', viewport: {width: 1280, height: 900}});
root.setDefaultTimeout(25000);
const browser = root.browser();
const report = {classification: 'real-browser-native-gall', status: 'fail', qualifies_phase: false,
  node: process.version, browser: browser.version(), execution_id: material.execution_id, checks: [], responses: [], failures: []};
const pages = [];
const origins = new Set([origin, 'https://bus.localhost:8444', 'https://nec.localhost:8445', 'https://bud.localhost:8446']);
async function restrict(context) {
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    return origins.has(url.origin) ? route.continue() : route.abort('blockedbyclient');
  });
}
function passed(name, extra = {}) { report.checks.push({name, passed: true, ...extra}); console.log('PASS ' + name); }
async function pageIn(context) {
  const page = await context.newPage(); pages.push(page);
  page.on('response', async response => {
    const url = new URL(response.url());
    if (!origins.has(url.origin) || !url.pathname.startsWith('/stead/') || report.responses.length >= 200) return;
    const row = {origin: url.origin, path: url.pathname, status: response.status()};
    report.responses.push(row);
    if (url.pathname.startsWith('/stead/auth/') || url.pathname === '/stead/api/query') {
      const headers = await response.request().allHeaders();
      row.request = {method: response.request().method(), header_names: Object.keys(headers).sort(),
        origin_matches: headers.origin === origin, host_matches: (headers.host ?? headers[':authority']) === 'home.localhost:8443',
        content_type: headers['content-type'], body_bytes: Buffer.byteLength(response.request().postData() ?? ''),
        csrf_format: headers['x-stead-csrf'] ? /^[0-9a-f]{64}$/u.test(headers['x-stead-csrf']) : null,
        cookies: (headers.cookie ?? '').split(';').filter(Boolean).map(pair => {
          const [name, ...values] = pair.trim().split('='); const value = values.join('=');
          return {name: /^[-_a-zA-Z0-9]{1,80}$/u.test(name) ? name : '[unexpected name]', bytes: Buffer.byteLength(value), token_format: /^[0-9a-f]{64}$/u.test(value)};
        })};
    }
    if (response.headers()['content-type']?.startsWith('application/json')) {
      const value = await response.json().catch(() => ({}));
      for (const key of ['protocol', 'status', 'error']) {
        if (typeof value[key] === 'string' && /^[a-z0-9._/-]{1,64}$/u.test(value[key])) row[key === 'status' ? 'result_status' : key] = value[key];
      }
    }
  });
  page.on('requestfailed', request => {
    const url = new URL(request.url());
    if (origins.has(url.origin) && report.failures.length < 100) report.failures.push({origin: url.origin, path: url.pathname,
      failure: request.failure()?.errorText?.replace(/[^a-zA-Z0-9_: -]/gu, '').slice(0, 120)});
  });
  return page;
}
async function signIn(context, ship, port) {
  const home = await pageIn(context);
  const start = performance.now();
  await home.goto(origin + '/stead/');
  await home.getByRole('textbox', {name: 'Your identity ship', exact: true}).fill('~' + ship);
  await home.getByRole('button', {name: 'Request sign-in', exact: true}).click();
  await home.getByRole('heading', {name: 'Approve on your identity ship', exact: true}).waitFor();
  const code = await home.locator('.comparison').innerText();
  assert.match(code, /^[0-9a-f]{12}$/u);
  const provenance = await home.evaluate(async () => {
    const response = await fetch('/stead-boundary-probe/', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: '{}', credentials: 'same-origin', cache: 'no-store'});
    return response.json();
  });
  assert.equal(provenance.secure, 'yes');
  assert.equal(provenance.owner_authenticated, 'no');
  report.provenance ??= [];
  report.provenance.push({ship, ...provenance});
  const personal = await pageIn(context);
  const personalOrigin = `https://${ship}.localhost:${port}`;
  await personal.goto(personalOrigin + '/stead-identity/');
  await personal.getByRole('link', {name: 'Sign in to my ship', exact: true}).click();
  function requireOwnerLogin() {
    const url = new URL(personal.url());
    assert.equal(url.origin, personalOrigin);
    assert.equal(url.pathname, '/~/login');
  }
  requireOwnerLogin();
  await personal.locator('input#pass').fill(material.identities[ship].code);
  requireOwnerLogin();
  await personal.locator('#local button[type=submit]').click();
  await personal.getByRole('heading', {name: code, exact: true}).waitFor();
  await personal.getByRole('button', {name: 'The code and home match — approve', exact: true}).click();
  await personal.getByText('Approval sent. Refresh to check acknowledgement, or return to Stead to finish signing in.', {exact: true}).waitFor();
  for (let count = 0; count < 20; count++) {
    const observed = home.waitForResponse(response => response.url() === origin + '/stead/auth/status');
    await home.getByRole('button', {name: 'Check approval', exact: true}).click();
    const response = await observed;
    assert.equal(response.status(), 200, 'Native approval-status HTTP response');
    if ((await response.json()).status === 'approved') break;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  await home.getByRole('button', {name: 'Sign out', exact: true}).waitFor();
  await home.getByRole('button', {name: /GARDEN.*Garden α/u}).waitFor();
  passed(ship + '-individual-native-owner-approved-session', {journey_ms: Math.round(performance.now() - start)});
  return {home, personal};
}
try {
  await restrict(root);
  const alice = await signIn(root, 'bus', 8444);
  const bobContext = await browser.newContext({ignoreHTTPSErrors: false, serviceWorkers: 'block', locale: 'en-US', timezoneId: 'Asia/Tokyo', viewport: {width: 1280, height: 900}});
  bobContext.setDefaultTimeout(25000);
  await restrict(bobContext);
  const bob = await signIn(bobContext, 'nec', 8445);
  for (const page of [alice.home, bob.home]) {
    await page.getByRole('button', {name: /GARDEN.*Garden α/u}).click();
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.getByRole('heading', {name: 'Native task', exact: true}).waitFor();
  }
  assert.equal(await bob.home.getByRole('button', {name: 'New work item', exact: true}).count(), 0);
  passed('native-reader-work-view-without-write-control');
  await alice.home.getByRole('button', {name: 'New work item', exact: true}).click();
  await alice.home.getByRole('textbox', {name: 'Title', exact: true}).fill('Browser task — 東京');
  await alice.home.getByRole('textbox', {name: 'Description', exact: true}).fill('Created through the actual TLS browser boundary.');
  const result = alice.home.waitForResponse(response => response.url() === origin + '/stead/api/command');
  await alice.home.getByRole('button', {name: 'Save at home', exact: true}).click();
  const receipt = await (await result).json();
  assert.equal(receipt.status, 'accepted');
  assert.equal(receipt.authentication, 'native-approved-browser/1');
  assert.equal(receipt.identity_ship, '~bus');
  await alice.home.getByText('Saved at home · revision 1', {exact: true}).waitFor();
  passed('browser-command-committed-with-native-approved-attribution', {request_id: receipt.request_id});
  await bob.home.getByRole('button', {name: 'Refresh', exact: true}).click();
  await bob.home.getByRole('heading', {name: 'Browser task — 東京', exact: true}).waitFor();
  passed('second-individual-reads-committed-browser-work');
  await alice.home.screenshot({path: path.join(output, 'native-work.png'), fullPage: true});
  const cookies = await root.cookies(origin);
  const stead = cookies.find(cookie => cookie.name === '__Host-stead-session');
  assert.ok(stead?.secure && stead.httpOnly && stead.sameSite === 'Strict' && stead.path === '/' && stead.domain === 'home.localhost');
  const homeProvenance = await alice.home.evaluate(async () => (await fetch('/stead-boundary-probe/', {cache: 'no-store'})).json());
  // Pinned Eyre creates a guest urbauth cookie even before login. Its presence
  // is not owner authentication; check the actual native provenance instead.
  assert.equal(homeProvenance.owner_authenticated, 'no');
  assert.equal(homeProvenance.secure, 'yes');
  assert.equal((await root.cookies('https://bus.localhost:8444')).some(cookie => cookie.name === '__Host-stead-session'), false);
  passed('member-cookie-is-secure-httponly-host-only-and-not-owner-auth');
  await alice.home.getByRole('button', {name: 'Sign out', exact: true}).click();
  await alice.home.getByRole('button', {name: 'Request sign-in', exact: true}).waitFor();
  assert.equal(await alice.home.getByRole('button', {name: /GARDEN/u}).count(), 0);
  passed('logout-clears-rendered-business-state');
  report.status = 'pass';
} catch (error) {
  // No raw HTML, cookies, request bodies, or personal owner code in diagnostics.
  let safe = String(error);
  for (const identity of Object.values(material.identities)) safe = safe.replaceAll(identity.code, '[redacted owner credential]');
  report.error = safe.replace(/[0-9a-f]{64}/gu, '[redacted token]').slice(0, 4000);
  for (let index = 0; index < pages.length; index++) {
    if (!pages[index].isClosed()) await pages[index].screenshot({path: path.join(output, `failure-${index}.png`), fullPage: true}).catch(() => {});
  }
  throw new Error(report.error);
} finally {
  await writeFile(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2) + '\n');
  await root.close();
}

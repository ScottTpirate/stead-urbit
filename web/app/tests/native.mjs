// Real Firefox -> byte relay -> native Eyre -> configured Gall, synthetic data.
// No response mocks, ignored certificate failures, sandbox bypass, or live +code.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash, randomBytes} from 'node:crypto';
import path from 'node:path';
import {firefox} from 'playwright';
const [profile, fixture, output] = process.argv.slice(2);
assert.equal(process.version, 'v24.21.0');
assert.ok(!process.env.SSLKEYLOGFILE);
const material = JSON.parse(await readFile(fixture, 'utf8'));
const manifestBytes = await readFile(new URL('../dist/manifest.json', import.meta.url));
const manifest = JSON.parse(manifestBytes);
const metafile = JSON.parse(await readFile(new URL('../dist/metafile.json', import.meta.url)));
const lazyFiles = Object.entries(metafile.outputs).filter(([, value]) => Object.hasOwn(value.inputs, 'src/Markdown.tsx'));
assert.equal(lazyFiles.length, 1);
const lazyAsset = path.basename(lazyFiles[0][0]);
assert.ok(manifest.files[lazyAsset]);
const origin = 'https://home.localhost:8443';
assert.equal(material.origin, origin);
const root = await firefox.launchPersistentContext(profile, {headless: true, ignoreHTTPSErrors: false, serviceWorkers: 'block',
  locale: 'en-US', timezoneId: 'America/New_York', viewport: {width: 1280, height: 900}});
root.setDefaultTimeout(25000);
const browser = root.browser();
const report = {classification: 'real-browser-native-gall', status: 'fail', qualifies_phase: false,
  node: process.version, browser: browser.version(), execution_id: material.execution_id, checks: [], responses: [], failures: []};
report.assets = {manifest_sha256: createHash('sha256').update(manifestBytes).digest('hex'), markdown: {path: '/stead/assets/' + lazyAsset, ...manifest.files[lazyAsset]}};
const responseTasks = new Set();
const pages = [];
const origins = new Set([origin, 'https://bus.localhost:8444', 'https://nec.localhost:8445', 'https://bud.localhost:8446']);
async function restrict(context) {
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    return origins.has(url.origin) ? route.continue() : route.abort('blockedbyclient');
  });
}
function passed(name, extra = {}) { report.checks.push({name, passed: true, ...extra}); console.log('PASS ' + name); }
async function keyboardTo(page, target) {
  // Select the actual browser tab before sending physical keyboard events.
  // No focus() shortcut: every control is still reached by Tab or Shift+Tab.
  await page.bringToFront();
  await target.waitFor();
  for (let count = 0; count <= 80; count++) {
    if (await target.evaluate(element => document.activeElement === element)) return;
    const direction = await target.evaluate(element => document.activeElement && Boolean(document.activeElement.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_PRECEDING) ? 'Shift+Tab' : 'Tab');
    await page.keyboard.press(direction);
  }
  throw new Error('Keyboard traversal did not reach ' + String(target) + '; document focus=' + await page.evaluate(() => document.hasFocus()));
}
async function keyboardText(page, target, value) {
  await keyboardTo(page, target); await page.keyboard.press('Control+A'); await page.keyboard.insertText(value);
}
async function keyboardPress(page, target) { await keyboardTo(page, target); await page.keyboard.press('Enter'); }
async function assetTiming(page) {
  return page.evaluate(() => performance.getEntriesByType('resource').filter(entry => new URL(entry.name).pathname.startsWith('/stead/assets/')).map(entry => ({
    path: new URL(entry.name).pathname, encoded_body_bytes: entry.encodedBodySize, decoded_body_bytes: entry.decodedBodySize,
    transfer_bytes: entry.transferSize, duration_ms: Math.round(entry.duration)})));
}
async function inertPreview(page) {
  const preview = page.getByRole('article', {name: 'Document content', exact: true});
  await preview.getByRole('heading', {name: 'Selected Tokyo 東京', exact: true}).waitFor();
  assert.ok((await preview.innerText()).includes('<script>window.steadXss=1</script>'));
  assert.equal(await preview.locator('script,img,iframe,object,embed,[onerror],[onclick],a[href^="javascript:"]').count(), 0);
  assert.equal(await page.evaluate(() => window.steadXss), undefined);
}
async function pageIn(context) {
  const page = await context.newPage(); pages.push(page);
  page.on('response', response => {
    const task = (async () => {
    const url = new URL(response.url());
    if (!origins.has(url.origin) || !url.pathname.startsWith('/stead/')) return;
    if (report.responses.length >= 1000) { report.responses_truncated = true; return; }
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
    })();
    responseTasks.add(task);
    void task.finally(() => responseTasks.delete(task)).catch(() => { report.response_capture_error = true; });
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
async function acceptedClick(page, label) {
  const response = page.waitForResponse(value => value.url() === origin + '/stead/api/command');
  const start = performance.now();
  await page.getByRole('button', {name: label, exact: true}).click();
  const result = await (await response).json();
  assert.equal(result.status, 'accepted');
  assert.equal(result.authentication, 'native-approved-browser/1');
  await page.getByText(`Saved at home · revision ${result.resource_revision}`, {exact: true}).waitFor();
  report.timings ??= [];
  report.timings.push({operation: result.operation, request_id: result.request_id, confirmation_ms: Math.round(performance.now() - start)});
  return result;
}
async function docsJourney(alice, bob) {
  const a = alice.home, b = bob.home;
  await a.getByRole('button', {name: 'Docs', exact: true}).click();
  for (const [title, visibility] of [['Private notebook α', 'private'], ['Shared handbook', 'shared']]) {
    await a.getByRole('button', {name: 'New collection', exact: true}).click();
    await a.getByRole('textbox', {name: 'Title', exact: true}).fill(title);
    await a.getByLabel('Visibility', {exact: true}).selectOption(visibility);
    await acceptedClick(a, 'Save at home');
  }
  await a.getByLabel('Collection', {exact: true}).selectOption({label: 'Private notebook α · Private drafts'});
  const content = '# Selected Tokyo 東京\n\nA shared explanation.\n\n<script>window.steadXss=1</script>\n\n<img src=x onerror="window.steadXss=2">\n\n[Unsafe](javascript:window.steadXss=3)\n';
  let selected;
  const privateIds = [];
  for (const body of [content, '# UNSELECTED-PRIVATE-CANARY\n\nThis page must stay private.\n']) {
    await a.getByRole('button', {name: 'New page', exact: true}).click();
    const editor = a.getByRole('textbox', {name: 'Markdown source', exact: true});
    const draft = (await editor.inputValue()).replace('# Untitled\n', body);
    await editor.fill(draft);
    const receipt = await acceptedClick(a, 'Save page');
    privateIds.push(receipt.resource_id, receipt.container_id);
    assert.match(receipt.git_commit_oid, /^[0-9a-f]{40}$/u);
    selected ??= {id: receipt.resource_id, markdown: draft, container: receipt.container_id};
    if (body === content) {
      await inertPreview(a);
      report.asset_timing.after_first_preview = await assetTiming(a);
      assert.equal(report.asset_timing.before_docs.some(row => row.path === report.assets.markdown.path), false);
      const lazy = report.asset_timing.after_first_preview.filter(row => row.path === report.assets.markdown.path);
      assert.equal(lazy.length, 1); assert.equal(lazy[0].decoded_body_bytes, report.assets.markdown.bytes);
    }
    await a.getByRole('button', {name: 'Discard local changes and close', exact: true}).click();
  }
  passed('native-private-markdown-saves-have-git-oids-and-inert-preview');
  await a.locator('.resource-row').filter({has: a.getByRole('heading', {name: /# Selected Tokyo 東京/u})}).getByRole('button', {name: 'Open page', exact: true}).click();
  assert.equal(await a.getByRole('textbox', {name: 'Markdown source', exact: true}).inputValue(), selected.markdown);
  await a.getByRole('button', {name: 'Publish selected page', exact: true}).click();
  await a.getByLabel('Destination collection', {exact: true}).selectOption({label: 'Shared handbook'});
  const published = await acceptedClick(a, 'Save at home');
  assert.notEqual(published.resource_id, selected.id);
  assert.notEqual(published.container_id, selected.container);
  assert.match(published.git_commit_oid, /^[0-9a-f]{40}$/u);
  await a.getByRole('button', {name: 'Discard local changes and close', exact: true}).click();
  await b.getByRole('button', {name: 'Docs', exact: true}).click();
  assert.equal(await b.getByLabel('Collection', {exact: true}).getByRole('option', {name: /Private notebook/u}).count(), 0);
  await b.getByLabel('Collection', {exact: true}).selectOption({label: 'Shared handbook · Shared'});
  await b.getByRole('heading', {name: /# Selected Tokyo 東京/u}).waitFor();
  assert.equal(await b.getByRole('heading', {name: /UNSELECTED-PRIVATE-CANARY/u}).count(), 0);
  await b.getByRole('button', {name: 'Open page', exact: true}).click();
  const shared = await b.getByRole('textbox', {name: 'Markdown source', exact: true}).inputValue();
  assert.equal(shared, selected.markdown.replace(selected.id, published.resource_id).replace('state: draft', 'state: published'));
  assert.equal(await b.getByRole('button', {name: 'Save page', exact: true}).isDisabled(), true);
  await inertPreview(b);
  await b.screenshot({path: path.join(output, 'native-docs.png'), fullPage: true});
  await b.getByRole('button', {name: 'Discard local changes and close', exact: true}).click();
  passed('selected-page-published-without-private-collection-or-unselected-page', {request_id: published.request_id, git_commit_oid: published.git_commit_oid});
  for (const page of [a, b]) {
    await page.getByRole('navigation', {name: 'Project views'}).getByRole('button', {name: 'Search', exact: true}).click();
    await page.getByRole('textbox', {name: 'Search this project', exact: true}).fill('UNSELECTED-PRIVATE-CANARY');
    await page.getByRole('button', {name: 'Search', exact: true}).last().click();
  }
  await a.getByRole('heading', {name: /UNSELECTED-PRIVATE-CANARY/u}).waitFor();
  await b.getByRole('heading', {name: 'Nothing here yet', exact: true}).waitFor();
  passed('private-canary-search-owner-positive-reader-negative');
  for (const [label, kind] of [['Activity', 'activity'], ['Inbox', 'inbox'], ['Links', 'relations']]) {
    const queried = b.waitForResponse(response => response.url() === origin + '/stead/api/query'
      && response.request().postDataJSON()?.kind === kind
      && response.request().postDataJSON()?.project_id === published.project_id);
    await b.getByRole('button', {name: label, exact: true}).click();
    const response = await queried;
    assert.equal(response.status(), 200);
    const value = await response.json();
    assert.equal(value.status, 'read'); assert.equal(value.kind, kind);
    assert.equal(value.request_id, response.request().postDataJSON().request_id);
    const rows = JSON.stringify(value.rows);
    assert.ok(!rows.includes('UNSELECTED-PRIVATE-CANARY'));
    for (const id of privateIds) assert.ok(!rows.includes(id), 'Private resource identity absent from ' + kind);
    assert.equal(value.cursor, '', 'Entire small projection was inspected');
    await response.finished();
    await b.getByText('Loading authorized view', {exact: true}).waitFor({state: 'detached'});
    await b.locator('#project-content[data-live-updates="connected"]').waitFor();
    assert.equal(await b.locator('main').innerText().then(text => text.includes('UNSELECTED-PRIVATE-CANARY')), false);
  }
  passed('reader-projections-exclude-private-page-canary');
  await a.getByRole('button', {name: 'Links', exact: true}).click();
  await a.getByRole('button', {name: 'Add link', exact: true}).click();
  await a.getByLabel('Link type', {exact: true}).selectOption('documents');
  const from = a.getByLabel('From resource', {exact: true});
  const options = await from.locator('option').allTextContents();
  assert.ok(options.some(text => text.includes('Selected Tokyo 東京')));
  const destination = `${published.resource_kind}/${published.container_id}/${published.resource_id}`;
  await from.selectOption(destination);
  await a.getByLabel('To resource', {exact: true}).selectOption({label: 'Browser task — 東京 · work'});
  const linked = await acceptedClick(a, 'Save at home');
  assert.equal(linked.operation, 'relation.create');
  passed('browser-links-published-page-to-authorized-work', {request_id: linked.request_id});
}
async function conflictsAndRecovery(alice, bob) {
  const a = alice.home, b = bob.home;
  for (const page of [a, b]) {
    await page.getByRole('button', {name: /UPDATES.*Update controls/u}).click();
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.locator('.resource-row').filter({has: page.getByRole('heading', {name: 'Queued before revocation', exact: true})}).getByRole('button', {name: 'Edit', exact: true}).click();
  }
  await a.getByRole('textbox', {name: 'Title', exact: true}).fill('Alice current revision');
  await b.getByRole('textbox', {name: 'Title', exact: true}).fill('Bob local stale draft');
  await acceptedClick(a, 'Save at home');
  const conflict = b.waitForResponse(response => response.url() === origin + '/stead/api/command');
  await b.getByRole('button', {name: 'Save at home', exact: true}).click();
  const refused = await (await conflict).json();
  assert.equal(refused.status, 'rejected'); assert.equal(refused.error, 'revision_conflict');
  assert.equal(await b.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'Bob local stale draft');
  await b.getByRole('button', {name: 'Compare current saved revision', exact: true}).click();
  await b.getByRole('button', {name: 'Keep my edits using this revision', exact: true}).click();
  assert.equal(await b.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'Bob local stale draft');
  const accepted = await acceptedClick(b, 'Save at home');
  assert.equal(accepted.identity_ship, '~nec');
  await a.getByRole('heading', {name: 'Bob local stale draft', exact: true}).waitFor();
  passed('two-native-principals-conflict-compare-explicit-rebase-and-live-refresh');
  await a.getByRole('button', {name: 'New work item', exact: true}).click();
  await a.getByRole('textbox', {name: 'Title', exact: true}).fill('Committed response deliberately lost');
  // Fault injection discards an actual native response after its bytes arrive.
  // No accepted response is invented; receipt recovery still queries the home.
  await a.evaluate(() => {
    const original = window.fetch;
    window.fetch = async (...args) => {
      const response = await original(...args);
      if (String(args[0]) === '/stead/api/command') {
        await response.arrayBuffer(); window.fetch = original;
        throw new TypeError('Controlled loss after real native response');
      }
      return response;
    };
  });
  const observed = a.waitForResponse(response => response.url() === origin + '/stead/api/command');
  await a.getByRole('button', {name: 'Save at home', exact: true}).click();
  const committed = await (await observed).json(); assert.equal(committed.status, 'accepted');
  await a.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor();
  await b.getByRole('heading', {name: 'Committed response deliberately lost', exact: true}).waitFor();
  const recovered = a.waitForResponse(response => response.url() === origin + '/stead/api/query' && response.request().postDataJSON()?.kind === 'receipt');
  await a.getByRole('button', {name: 'Check receipt', exact: true}).click();
  const recoveredResponse = await recovered;
  assert.equal(recoveredResponse.request().postDataJSON().resource_id, committed.request_id);
  const recovery = await recoveredResponse.json();
  assert.equal(recovery.status, 'read'); assert.deepEqual(Object.values(recovery.rows), [committed]);
  await a.getByText(`Saved at home · revision ${committed.resource_revision}`, {exact: true}).waitFor();
  await a.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor({state: 'detached'});
  passed('native-commit-with-injected-response-loss-recovers-original-receipt', {request_id: committed.request_id, fault: 'client-discards-real-native-response'});
}
async function keyboardAndLayout(alice, bob) {
  const page = alice.home;
  await keyboardPress(page, page.getByRole('button', {name: '＋ New project', exact: true}));
  await keyboardText(page, page.getByRole('textbox', {name: 'Title', exact: true}), 'Keyboard garden 東京');
  await keyboardText(page, page.getByRole('textbox', {name: 'Project key', exact: true}), 'KEYBOARD');
  const projectResponse = page.waitForResponse(response => response.url() === origin + '/stead/api/command');
  await keyboardPress(page, page.getByRole('button', {name: 'Save at home', exact: true}));
  const created = await (await projectResponse).json(); assert.equal(created.status, 'accepted');
  await keyboardPress(page, page.getByRole('button', {name: /KEYBOARD.*Keyboard garden 東京/u}));
  await keyboardPress(page, page.getByRole('button', {name: 'Work', exact: true}));
  await keyboardPress(page, page.getByRole('button', {name: 'New work item', exact: true}));
  const title = 'A'.repeat(200);
  await keyboardText(page, page.getByRole('textbox', {name: 'Title', exact: true}), title);
  await keyboardText(page, page.getByRole('textbox', {name: 'Description', exact: true}), 'Unicode: 東京 — Zoë 🙂\nKeyboard-only creation.');
  const workResponse = page.waitForResponse(response => response.url() === origin + '/stead/api/command');
  await keyboardPress(page, page.getByRole('button', {name: 'Save at home', exact: true}));
  const work = await (await workResponse).json(); assert.equal(work.status, 'accepted');
  await page.getByRole('heading', {name: title, exact: true}).waitFor();
  assert.equal(await page.getByRole('button', {name: /^(Code|PRs|Builds)$/u}).count(), 0);
  passed('keyboard-project-and-work-creation-general-profile-unicode-long-title', {request_id: work.request_id});
  for (const width of [390, 1440]) {
    await page.setViewportSize({width, height: 900});
    const dimensions = await page.evaluate(() => ({viewport: innerWidth, body: document.body.scrollWidth, root: document.documentElement.scrollWidth}));
    assert.ok(dimensions.body <= dimensions.viewport && dimensions.root <= dimensions.viewport, 'No page-wide overflow at ' + width);
    await page.screenshot({path: path.join(output, `native-layout-${width}.png`), fullPage: true});
  }
  assert.equal(await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone), 'America/New_York');
  assert.equal(await bob.home.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone), 'Asia/Tokyo');
  passed('native-long-content-at-small-large-layouts-and-distinct-timezones');
  await bob.home.reload();
  await bob.home.getByRole('button', {name: /GARDEN.*Garden α/u}).waitFor();
  assert.equal(await bob.home.getByRole('button', {name: /KEYBOARD.*Keyboard garden/u}).count(), 0);
  passed('new-general-project-does-not-implicitly-grant-another-member');
}
async function offlineJourney(alice, bob) {
  const page = alice.home;
  await page.getByRole('button', {name: /UPDATES.*Update controls/u}).click();
  await page.getByRole('button', {name: 'Work', exact: true}).click();
  await page.locator('#project-content[data-live-updates="connected"]').waitFor();
  await page.getByRole('button', {name: 'New work item', exact: true}).click();
  const title = 'Offline local draft — 東京';
  await page.getByRole('textbox', {name: 'Title', exact: true}).fill(title);
  const attempts = [];
  const capture = request => { if (request.url() === origin + '/stead/api/command') attempts.push(request.postDataJSON()); };
  page.on('request', capture);
  try {
    await page.context().setOffline(true);
    await page.getByRole('button', {name: 'Save at home', exact: true}).click();
    await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), title);
    assert.equal(attempts.length, 1);
    await page.getByText('Support details', {exact: true}).click();
    const preview = await page.getByLabel('Support report preview', {exact: true}).innerText();
    const details = JSON.parse(preview);
    assert.deepEqual(Object.keys(details).sort(), ['app_version', 'command_protocol', 'diagnostic', 'format', 'request_id']);
    assert.equal(details.request_id, attempts[0].request_id);
    assert.ok(!preview.includes(title)); assert.ok(!preview.includes('~bus'));
    const downloaded = page.waitForEvent('download');
    await page.getByRole('button', {name: 'Download these details', exact: true}).click();
    const download = await downloaded;
    assert.equal(download.suggestedFilename(), 'stead-support.json');
    assert.equal(await readFile(await download.path(), 'utf8'), preview);
    await download.delete();
    passed('explicit-support-download-matches-reviewed-content-free-preview');
    await page.context().setOffline(false);
    // Wait across multiple polling periods and assert no automatic mutation replay.
    await page.waitForTimeout(4500);
    assert.equal(attempts.length, 1);
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), title);
    assert.equal(await bob.home.getByRole('heading', {name: title, exact: true}).count(), 0);
    const receipt = page.waitForResponse(response => response.url() === origin + '/stead/api/query'
      && response.request().postDataJSON()?.kind === 'receipt');
    await page.getByRole('button', {name: 'Check receipt', exact: true}).click();
    const unknown = await receipt;
    assert.equal(unknown.request().postDataJSON().resource_id, attempts[0].request_id);
    assert.notEqual((await unknown.json()).status, 'accepted');
    await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor();
    const saved = page.waitForResponse(response => response.url() === origin + '/stead/api/command');
    await page.getByRole('button', {name: 'Retry this request', exact: true}).click();
    const accepted = await (await saved).json();
    assert.equal(accepted.status, 'accepted'); assert.equal(accepted.request_id, attempts[0].request_id);
    assert.equal(attempts.length, 2); assert.deepEqual(attempts[1], attempts[0]);
    await page.getByRole('heading', {name: title, exact: true}).waitFor();
    passed('actual-browser-offline-preserves-draft-and-requires-explicit-original-request-retry', {request_id: accepted.request_id});
  } finally { await page.context().setOffline(false); page.off('request', capture); }
}
async function revokeRenderedScope(alice, bob) {
  const a = alice.home, b = bob.home;
  for (const page of [a, b]) {
    await page.getByRole('button', {name: /UPDATES.*Update controls/u}).click();
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.locator('#project-content[data-live-updates="connected"]').waitFor();
  }
  await b.getByRole('button', {name: 'New work item', exact: true}).click();
  await b.getByRole('textbox', {name: 'Title', exact: true}).fill('Revocation private draft canary');
  const projectRead = a.waitForResponse(response => response.url() === origin + '/stead/api/query'
    && response.request().postDataJSON()?.kind === 'project');
  await a.getByRole('button', {name: 'Refresh', exact: true}).click();
  const response = await projectRead;
  const csrf = (await response.request().allHeaders())['x-stead-csrf'];
  assert.match(csrf, /^[0-9a-f]{64}$/u);
  const metadata = Object.values((await response.json()).rows)[0];
  assert.equal(metadata.role, 'maintainer');
  const command = {protocol: 'stead.command/3', request_id: '019939ba-4000-7000-8000-' + randomBytes(6).toString('hex'),
    project_id: metadata.project_id, resource_id: metadata.project_id, authority_epoch: metadata.authority_epoch,
    expected_revision: metadata.policy_revision, operation: 'policy.revoke',
    payload: {grant_id: '019939ba-4000-7000-8000-' + (23).toString(16).padStart(12, '0')}};
  // Operator control uses the same authenticated, final native browser API.
  // There is no admin socket, altered clock, synthetic response or raw engine.
  const result = await a.evaluate(async ({csrf, command}) => (await fetch('/stead/api/command', {
    method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-Stead-CSRF': csrf},
    body: JSON.stringify(command), cache: 'no-store', redirect: 'error'})).json(), {csrf, command});
  assert.equal(result.status, 'accepted'); assert.equal(result.request_id, command.request_id);
  await b.getByRole('textbox', {name: 'Title', exact: true}).waitFor({state: 'detached'});
  assert.equal(await b.getByRole('heading', {name: 'Update controls', exact: true}).count(), 0);
  assert.ok(!(await b.locator('main').innerText()).includes('Revocation private draft canary'));
  passed('native-grant-revocation-clears-rendered-project-and-local-draft', {request_id: result.request_id});
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
  await bob.home.getByRole('heading', {name: 'Browser task — 東京', exact: true}).waitFor();
  passed('second-individual-receives-live-committed-browser-work');
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
  report.asset_timing = {before_docs: await assetTiming(alice.home)};
  await docsJourney(alice, bob);
  await conflictsAndRecovery(alice, bob);
  await offlineJourney(alice, bob);
  await keyboardAndLayout(alice, bob);
  await revokeRenderedScope(alice, bob);
  report.asset_timing.after_docs = await assetTiming(alice.home);
  report.browser_storage = await alice.home.evaluate(() => ({local_keys: localStorage.length, session_keys: sessionStorage.length, path: location.pathname, query: location.search, fragment: location.hash}));
  assert.equal(report.browser_storage.local_keys, 0); assert.equal(report.browser_storage.session_keys, 0);
  assert.equal(report.browser_storage.query, ''); assert.equal(report.browser_storage.fragment, '');
  passed('native-browser-assets-measured-and-no-business-data-in-url-or-storage');
  await alice.home.getByRole('button', {name: /GARDEN.*Garden α/u}).click();
  await alice.home.getByRole('button', {name: 'Docs', exact: true}).click();
  await alice.home.getByLabel('Collection', {exact: true}).selectOption({label: 'Private notebook α · Private drafts'});
  await alice.home.locator('.resource-row').filter({has: alice.home.getByRole('heading', {name: /UNSELECTED-PRIVATE-CANARY/u})}).getByRole('button', {name: 'Open page', exact: true}).click();
  const privateText = alice.home.getByRole('textbox', {name: 'Markdown source', exact: true});
  assert.ok((await privateText.inputValue()).includes('UNSELECTED-PRIVATE-CANARY'));
  await privateText.fill((await privateText.inputValue()) + '\nUnsaved logout canary.');
  await alice.home.getByRole('button', {name: 'Sign out', exact: true}).click();
  await alice.home.getByRole('button', {name: 'Request sign-in', exact: true}).waitFor();
  assert.equal(await alice.home.getByRole('button', {name: /GARDEN/u}).count(), 0);
  assert.equal(await privateText.count(), 0);
  assert.ok(!(await alice.home.locator('main').innerText()).includes('UNSELECTED-PRIVATE-CANARY'));
  passed('logout-clears-rendered-business-state');
  const switched = await signIn(root, 'nec', 8445);
  await switched.home.getByRole('button', {name: /GARDEN.*Garden α/u}).click();
  await switched.home.getByRole('button', {name: 'Docs', exact: true}).click();
  await switched.home.locator('#project-content[data-live-updates="connected"]').waitFor();
  assert.equal(await switched.home.getByLabel('Collection', {exact: true}).getByRole('option', {name: /Private notebook/u}).count(), 0);
  assert.ok(!(await switched.home.locator('main').innerText()).includes('Unsaved logout canary'));
  passed('explicit-account-change-does-not-restore-former-private-state');
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
  await Promise.allSettled([...responseTasks]);
  await writeFile(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2) + '\n');
  await root.close();
}

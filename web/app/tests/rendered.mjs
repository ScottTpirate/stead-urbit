// Real Firefox + synthetic HTTP responses. This does not qualify native TLS,
// authentication, permissions or the business outcomes represented by fixtures.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { mkdir, readFile, writeFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { firefox } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0', 'Use the pinned frontend Node runtime');
const output = path.resolve(root, '../../.runtime/web-render-tests');
async function inputs() {
  const entries = await readdir(path.join(root, 'src'), {withFileTypes: true});
  assert.ok(entries.length > 0 && entries.length <= 32 && entries.every(entry => entry.isFile()));
  const result = {};
  for (const name of ['tests/rendered.mjs', 'package-lock.json', ...entries.map(entry => 'src/' + entry.name)].sort()) {
    const raw = await readFile(path.join(root, name)); assert.ok(raw.length <= 1024 * 1024);
    result[name] = createHash('sha256').update(raw).digest('hex');
  }
  return result;
}
const requestedCase = process.argv[2] ?? '';
assert.ok(!requestedCase || /^[a-z0-9-]{1,100}$/u.test(requestedCase), 'Bounded case name');
const inputsBefore = await inputs();
await mkdir(output, {recursive: true});
await build({absWorkingDir: root, entryPoints: ['src/main.tsx'], outfile: path.join(output, 'app.js'),
  bundle: true, format: 'esm', target: 'es2022', define: {'process.env.NODE_ENV': '"development"'}});
const server = createServer(async (request, response) => {
  const files = {'/stead/app.js': ['app.js', 'text/javascript'], '/stead/app.css': ['app.css', 'text/css']};
  const file = files[request.url];
  if (file) { response.writeHead(200, {'content-type': file[1]}); response.end(await readFile(path.join(output, file[0]))); }
  else if (request.url === '/stead/') { response.writeHead(200, {'content-type': 'text/html'}); response.end('<!doctype html><html lang="en"><meta charset="utf-8"><title>Stead synthetic UI controls</title><link rel="stylesheet" href="/stead/app.css"><div id="root"></div><script type="module" src="/stead/app.js"></script></html>'); }
  else { response.writeHead(404); response.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await firefox.launch({headless: true});
const report = {classification: 'real-browser-with-mocked-home', node: process.version, browser: browser.version(), checks: [], qualifies_phase: false, requested_case: requestedCase, inputs_before: inputsBefore};
const id = number => '019939ba-4000-7000-8000-' + String(number).padStart(12, '0');
const person = {principal_id: id(102), binding_id: id(202), binding_revision: '1', identity_ship: '~bus',
  session_audit_id: 'a'.repeat(64), organization_id: id(5), team_id: id(6), display_name: 'Synthetic Alice', can_create: 'yes'};
const canonical = value => typeof value === 'string' ? JSON.stringify(value) : '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
const digest = command => createHash('sha256').update('stead.command/3\0' + canonical(command)).digest('hex');

async function fixture(run) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  const state = {failure: '', resumeFailure: false, loseCommand: false, commands: [], recoveryIds: [], receipts: new Map(),
    watches: new Map(), pages: new Map(), requests: [], sequence: 0, token: 0, polls: 0, opens: 0, denied: false,
    holdOpen: false, releaseOpen: null, holdWork: false, releaseWork: null,
    project: {kind: 'project', resource_id: id(1), project_id: id(1), title: 'Garden', project_key: 'GARDEN', preset: 'general', authority_epoch: '1', resource_revision: '1', policy_revision: '1', role: 'maintainer'},
    work: [], activity: [], containers: [], documents: []};
  await page.route(origin + '/stead/**', async route => {
    const request = route.request();
    if (request.method() !== 'POST') return route.continue();
    const value = request.postDataJSON();
    const pathname = new URL(request.url()).pathname;
    state.requests.push({path: pathname, kind: value.kind, action: value.action, search: value.search});
    const send = (body, status = 200) => route.fulfill({status, contentType: 'application/json', body: JSON.stringify(body)});
    if (pathname.endsWith('/capabilities')) return send({protocol: 'stead.capabilities/3', profile: 'configured-team'});
    if (pathname.endsWith('/resume')) {
      if (state.resumeFailure) return send({}, 503);
      state.watches.clear(); state.pages.clear();
      return send({status: 'authenticated', csrf: 'b'.repeat(64)});
    }
    const token = () => (++state.token).toString(16).padStart(64, '0');
    const generation = () => state.sequence.toString(16).padStart(64, '0');
    const denied = () => send({protocol: 'stead.result/3', status: 'rejected', error: 'denied_or_not_found'});
    if (pathname.endsWith('/updates')) {
      if (value.action === 'cancel') {
        state.watches.delete(value.watch_id);
        return send({protocol: 'stead.update-result/3', request_id: value.request_id, status: 'cancelled', watch_id: value.watch_id, cursor: '', generation: '', rows: {}});
      }
      if (state.denied) {
        if (value.action === 'poll') {
          state.watches.delete(value.watch_id);
          return send({protocol: 'stead.update-result/3', request_id: value.request_id, status: 'refresh_required', watch_id: value.watch_id, cursor: '', generation: '', rows: {}});
        }
        return denied();
      }
      if (value.action === 'open') {
        state.opens++;
        assert.ok(state.watches.size + state.pages.size < 4, 'mock shared cursor cap');
        const watch = {id: token(), cursor: token(), sequence: state.sequence};
        state.watches.set(watch.id, watch);
        if (state.holdOpen) {
          state.holdOpen = false;
          await new Promise(resolve => { state.releaseOpen = resolve; });
        }
        return send({protocol: 'stead.update-result/3', request_id: value.request_id, status: 'watching', watch_id: watch.id, cursor: watch.cursor, generation: generation(), rows: {}});
      }
      assert.equal(value.action, 'poll'); state.polls++;
      const watch = state.watches.get(value.watch_id);
      if (!watch || watch.cursor !== value.cursor) return send({protocol: 'stead.update-result/3', request_id: value.request_id, status: 'refresh_required', watch_id: value.watch_id, cursor: '', generation: '', rows: {}});
      const rows = watch.sequence === state.sequence ? {} : {'0': {sequence: String(state.sequence), generation: generation()}};
      watch.sequence = state.sequence; watch.cursor = token();
      return send({protocol: 'stead.update-result/3', request_id: value.request_id, status: 'updated', watch_id: watch.id, cursor: watch.cursor, generation: generation(), rows});
    }
    if (pathname.endsWith('/command')) {
      state.commands.push(value);
      const receipt = {protocol: 'stead.receipt/3', status: 'accepted', request_id: value.request_id,
        canonical_sha256: digest(value), project_id: value.project_id, resource_id: value.resource_id,
        resource_kind: value.operation.split('.')[0], container_id: '', resource_revision: String(BigInt(value.expected_revision) + 1n),
        authority_epoch: value.authority_epoch, operation: value.operation, principal_id: person.principal_id,
        binding_id: person.binding_id, binding_revision: person.binding_revision, identity_ship: person.identity_ship,
        authentication: 'native-approved-browser/1', authentication_strength: 'native-approved-browser',
        session_audit_id: person.session_audit_id, runtime: 'isolated-fake', accepted_at_ms: '1790519400000', git_commit_oid: ''};
      state.receipts.set(value.request_id, receipt);
      state.work = [{...value.payload, kind: 'work', resource_id: value.resource_id, project_id: value.project_id, resource_revision: '1'}];
      return state.loseCommand ? route.abort('failed') : send(receipt);
    }
    assert.equal(pathname, '/stead/api/query');
    if (state.failure) {
      const failure = state.failure; state.failure = '';
      return send({}, failure === 'expired' ? 401 : 503);
    }
    let rows = [];
    if (state.denied && value.kind !== 'identity') return denied();
    if (value.kind === 'identity') rows = [person];
    if (value.kind === 'projects' || value.kind === 'project') rows = [state.project];
    if (value.kind === 'work') {
      rows = value.resource_id ? state.work.filter(row => row.resource_id === value.resource_id) : state.work;
      if (state.holdWork) {
        state.holdWork = false;
        await new Promise(resolve => { state.releaseWork = resolve; });
      }
    }
    if (value.kind === 'activity') rows = state.activity;
    if (value.kind === 'containers') rows = state.containers;
    if (value.kind === 'documents') rows = state.documents;
    if (value.kind === 'receipt') {
      state.recoveryIds.push(value.resource_id);
      rows = state.receipts.has(value.resource_id) ? [state.receipts.get(value.resource_id)] : [];
    }
    let offset = 0; let cursor = '';
    if (value.cursor) {
      const continuation = state.pages.get(value.cursor);
      if (!continuation || continuation.kind !== value.kind || continuation.generation !== generation()) return send({protocol: 'stead.result/3', status: 'rejected', error: 'stale_cursor'});
      offset = continuation.offset; state.pages.delete(value.cursor);
    }
    if (rows.length - offset > 20) {
      if (!value.cursor) state.pages.clear();
      assert.ok(state.watches.size + state.pages.size < 4, 'mock shared cursor cap');
      cursor = token(); state.pages.set(cursor, {kind: value.kind, offset: offset + 20, generation: generation()});
    }
    rows = rows.slice(offset, offset + 20);
    return send({...value, protocol: 'stead.query-result/3', status: 'read', authority_epoch: state.project.authority_epoch,
      generation: generation(), cursor, rows: Object.fromEntries(rows.map((row, i) => [String(i), row]))});
  });
  try {
    await page.goto(origin + '/stead/');
    await page.getByRole('button', {name: /GARDEN.*Garden/u}).click();
    await page.getByRole('heading', {name: 'Garden', exact: true}).first().waitFor();
    await page.getByRole('button', {name: 'Refresh', exact: true}).waitFor();
    await page.locator('#project-content[data-live-updates="connected"]').waitFor();
    await run(page, state, consoleErrors);
  } catch (error) {
    await writeFile(path.join(output, 'failure.html'), await page.content());
    await page.screenshot({path: path.join(output, 'failure.png'), fullPage: true});
    throw error;
  } finally { state.releaseWork?.(); state.releaseOpen?.(); await context.close(); }
}
async function check(name, run) {
  if (requestedCase && name !== requestedCase) return;
  await fixture(run); report.checks.push({name, passed: true});
  console.log('PASS ' + name);
}
async function workForm(page) {
  await page.getByRole('button', {name: 'Work', exact: true}).click();
  await page.getByRole('button', {name: 'New work item', exact: true}).click();
  await page.getByRole('textbox', {name: 'Title', exact: true}).fill('Keep this local title');
  await page.getByRole('textbox', {name: 'Description', exact: true}).fill('Unsaved synthetic text');
}
try {
  await check('authentication-reuses-validated-identity-and-opens-before-one-snapshot', async (page, state) => {
    assert.equal(state.requests.filter(row => row.kind === 'identity').length, 1);
    assert.deepEqual(state.requests.filter(row => row.path === '/stead/api/query' && row.kind === 'project').map(row => row.path), ['/stead/api/query']);
    const open = state.requests.findIndex(row => row.action === 'open');
    const snapshot = state.requests.findIndex(row => row.path === '/stead/api/query' && row.kind === 'project');
    assert.ok(open >= 0 && snapshot > open);
  });
  await check('typing-search-keeps-current-watch-until-explicit-submit', async (page, state) => {
    await page.getByRole('navigation', {name: 'Project views'}).getByRole('button', {name: 'Search', exact: true}).click();
    await page.getByRole('button', {name: 'Refresh', exact: true}).waitFor({state: 'visible'});
    await page.waitForFunction(() => document.querySelector('#project-content')?.dataset.liveUpdates === 'connected'
      && ![...document.querySelectorAll('button')].find(button => button.textContent === 'Refresh')?.disabled);
    const before = state.requests.length, opens = state.opens;
    await page.getByRole('textbox', {name: 'Search this project', exact: true}).pressSequentially('garden');
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(state.opens, opens);
    assert.equal(state.requests.slice(before).filter(row => row.path === '/stead/api/query').length, 0);
    for (let attempt = 0; attempt < 2; attempt++) {
      const start = state.requests.length, previous = state.opens;
      const searched = page.waitForResponse(response => response.url().endsWith('/stead/api/query')
        && response.request().postDataJSON()?.kind === 'search' && response.request().postDataJSON()?.search === 'garden');
      await page.getByRole('button', {name: 'Search', exact: true}).last().click();
      await (await searched).finished();
      await page.waitForFunction(() => document.querySelector('#project-content')?.dataset.liveUpdates === 'connected'
        && ![...document.querySelectorAll('button')].find(button => button.textContent === 'Refresh')?.disabled);
      const requests = state.requests.slice(start);
      assert.equal(state.opens, previous + 1);
      assert.deepEqual(requests.filter(row => row.path === '/stead/api/query').map(row => row.kind), ['project', 'search']);
      assert.ok(requests.findIndex(row => row.action === 'open') < requests.findIndex(row => row.kind === 'project'));
    }
  });
  await check('selected-tab-and-refresh-each-open-before-one-snapshot', async (page, state) => {
    for (const label of ['Work', 'Work', 'Refresh']) {
      const start = state.requests.length, opens = state.opens;
      const snapshot = page.waitForResponse(response => response.url().endsWith('/stead/api/query')
        && response.request().postDataJSON()?.kind === 'work');
      await page.getByRole('button', {name: label, exact: true}).click();
      await (await snapshot).finished();
      await page.waitForFunction(() => document.querySelector('#project-content')?.dataset.liveUpdates === 'connected'
        && ![...document.querySelectorAll('button')].find(button => button.textContent === 'Refresh')?.disabled);
      const requests = state.requests.slice(start);
      assert.equal(state.opens, opens + 1);
      assert.deepEqual(requests.filter(row => row.path === '/stead/api/query').map(row => row.kind), ['project', 'work']);
      assert.ok(requests.findIndex(row => row.action === 'open') < requests.findIndex(row => row.kind === 'project'));
    }
  });
  await check('rapid-scope-changes-retire-one-delayed-open-before-latest-snapshot', async (page, state) => {
    const start = state.requests.length, opens = state.opens;
    state.holdOpen = true;
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    const deadline = Date.now() + 10000;
    while (!state.releaseOpen && Date.now() < deadline) await page.waitForTimeout(20);
    assert.ok(state.releaseOpen, 'first open reached the controlled response hold');
    for (const label of ['Docs', 'Activity', 'Inbox', 'Work', 'Search']) {
      await page.getByRole('navigation', {name: 'Project views'}).getByRole('button', {name: label, exact: true}).click();
    }
    assert.equal(state.opens, opens + 1, 'new scopes wait for ownership of the outstanding open');
    const snapshot = page.waitForResponse(response => response.url().endsWith('/stead/api/query')
      && response.request().postDataJSON()?.kind === 'search');
    state.releaseOpen(); state.releaseOpen = null;
    await (await snapshot).finished();
    await page.locator('#project-content[data-live-updates="connected"]').waitFor();
    assert.equal(state.opens, opens + 2);
    assert.equal(state.watches.size, 1);
    assert.deepEqual(state.requests.slice(start).filter(row => row.path === '/stead/api/query').map(row => row.kind), ['project', 'search']);
  });
  await check('401-during-query-restores-usable-sign-in', async (page, state) => {
    state.failure = 'expired';
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await page.getByRole('button', {name: 'Request sign-in', exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: 'Garden', exact: true}).count(), 0);
  });
  await check('uncertain-resume-preserves-dirty-work-form', async (page, state) => {
    await workForm(page);
    state.failure = 'unavailable';
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    state.resumeFailure = true;
    await page.getByRole('button', {name: 'Resume this tab', exact: true}).click();
    await page.getByRole('button', {name: 'Resume this tab', exact: true}).waitFor();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'Keep this local title');
    assert.equal(await page.getByRole('textbox', {name: 'Description', exact: true}).inputValue(), 'Unsaved synthetic text');
    state.resumeFailure = false;
    await page.getByRole('button', {name: 'Resume this tab', exact: true}).click();
    await page.getByText('Session resumed. Choose whether to retry your pending request.', {exact: true}).waitFor();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'Keep this local title');
  });
  await check('uncertain-resume-preserves-original-pending-receipt', async (page, state) => {
    await workForm(page); state.loseCommand = true;
    await page.getByRole('button', {name: 'Save at home', exact: true}).click();
    await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor();
    assert.equal(state.commands.length, 1);
    const original = state.commands[0].request_id;
    state.resumeFailure = true;
    await page.getByRole('button', {name: 'Resume this tab', exact: true}).click();
    await page.getByRole('button', {name: 'Resume this tab', exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).count(), 1);
    await page.getByRole('button', {name: 'Retry this request', exact: true}).click();
    await page.getByText('Session resumption was not confirmed. Your local changes are still here. Resume this tab before choosing what to retry.', {exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).count(), 1);
    assert.equal(state.commands.length, 1, 'suspended retry retained the pending ID without sending');
    state.resumeFailure = false;
    await page.getByRole('button', {name: 'Resume this tab', exact: true}).click();
    await page.getByText('Session resumed. Choose whether to retry your pending request.', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'Check receipt', exact: true}).click();
    await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor({state: 'detached'});
    assert.deepEqual(state.recoveryIds, [original]);
    assert.equal(state.commands.length, 1, 'recovery did not resend the mutation');
  });
  await check('refresh-adopts-current-project-role-and-authority', async (page, state) => {
    state.project = {...state.project, authority_epoch: '2', role: 'contributor'};
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await page.getByText('contributor', {exact: true}).waitFor();
    await workForm(page);
    await page.getByRole('button', {name: 'Save at home', exact: true}).click();
    await page.getByRole('heading', {name: 'Keep this local title', exact: true}).waitFor();
    assert.equal(state.commands[0].authority_epoch, '2');
    await page.screenshot({path: path.join(output, 'work.png'), fullPage: true});
  });
  await check('activity-keeps-distinct-events-for-one-resource', async (page, state, errors) => {
    state.activity = [1, 2, 3].map(n => ({resource_id: id(50), request_id: id(900 + n), title: 'Event ' + n}));
    await page.getByRole('button', {name: 'Activity', exact: true}).click();
    await page.getByRole('heading', {name: 'Event 3', exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: /^Event /u}).count(), 3);
    state.activity = [4, 5].map(n => ({resource_id: id(50), request_id: id(900 + n), title: 'Event ' + n}));
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await page.getByRole('heading', {name: 'Event 5', exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: /^Event /u}).count(), 2);
    assert.equal(errors.filter(error => /same key|unique.*key/iu.test(error)).length, 0);
  });
  await check('page-two-survives-foreground-actions-and-repeated-paginated-refresh', async (page, state) => {
    state.work = Array.from({length: 22}, (_, n) => ({kind: 'work', resource_id: id(100 + n), title: `Page item ${n + 1}`, resource_revision: '1', description: 'Synthetic', type: 'task', status: 'todo', priority: 'none'}));
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    for (let n = 0; n < 5; n++) {
      await page.getByRole('button', {name: 'Refresh', exact: true}).click();
      await page.waitForFunction(() => [...document.querySelectorAll('button')].some(button => button.textContent === 'Next page' && !button.disabled));
      assert.ok(state.pages.size <= 1); assert.ok(state.watches.size <= 1);
    }
    await page.getByRole('button', {name: 'Next page', exact: true}).click();
    await page.getByRole('heading', {name: 'Page item 21', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Edit', exact: true}).first().click();
    await page.getByRole('heading', {name: 'Edit work item', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Cancel', exact: true}).click();
    await page.waitForTimeout(2500);
    assert.equal(await page.getByRole('heading', {name: 'Page item 1', exact: true}).count(), 0);
    assert.equal(await page.getByRole('heading', {name: 'Page item 21', exact: true}).count(), 1);
  });
  await check('updates-preserve-local-form-and-original-uncertain-save', async (page, state) => {
    await workForm(page);
    state.sequence++;
    await page.getByText('Shared changes loaded from home.', {exact: true}).waitFor();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'Keep this local title');
    assert.equal(state.commands.length, 0);
    state.loseCommand = true;
    await page.getByRole('button', {name: 'Save at home', exact: true}).click();
    await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor();
    const requestId = state.commands[0].request_id;
    state.sequence++;
    await page.getByText('Shared changes loaded from home.', {exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).count(), 1);
    assert.equal(state.commands.length, 1);
    await page.getByRole('button', {name: 'Check receipt', exact: true}).click();
    await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor({state: 'detached'});
    assert.deepEqual(state.recoveryIds, [requestId]); assert.equal(state.commands.length, 1);
  });
  await check('cancelled-quiet-refresh-does-not-leave-docs-loading', async (page, state) => {
    state.work = [{kind: 'work', resource_id: id(500), title: 'Initial Work control', resource_revision: '1'}];
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.getByRole('heading', {name: 'Initial Work control', exact: true}).waitFor();
    await page.waitForTimeout(500);
    state.work = [{kind: 'work', resource_id: id(501), title: 'Stale held Work canary', resource_revision: '1'}];
    state.holdWork = true; state.sequence++;
    const deadline = Date.now() + 10000;
    while (!state.releaseWork && Date.now() < deadline) await page.waitForTimeout(50);
    assert.ok(state.releaseWork, 'invalidation reached the controlled delayed read');
    await page.getByRole('button', {name: 'Docs', exact: true}).click();
    const heldResponse = page.waitForResponse(response => response.url().endsWith('/stead/api/query') && response.request().postDataJSON()?.kind === 'work');
    state.releaseWork(); state.releaseWork = null;
    await (await heldResponse).finished();
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await page.getByRole('heading', {name: 'Choose a collection', exact: true}).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Refresh', exact: true}).isEnabled(), true);
    assert.equal(await page.getByText('Loading authorized view', {exact: true}).count(), 0);
    assert.equal(await page.getByRole('heading', {name: 'Stale held Work canary', exact: true}).count(), 0);
  });
  await check('revoked-update-scope-clears-protected-rendered-state', async (page, state) => {
    await workForm(page); state.sequence++; state.denied = true;
    await page.getByRole('textbox', {name: 'Title', exact: true}).waitFor({state: 'detached'});
    assert.equal(await page.getByRole('heading', {name: 'Garden', exact: true}).count(), 0);
    assert.equal(await page.getByText('Keep this local title', {exact: true}).count(), 0);
    assert.equal(state.commands.length, 0);
  });
  await check('document-page-two-survives-a-paginated-collection-selector', async (page, state) => {
    state.containers = Array.from({length: 22}, (_, n) => ({kind: 'container', resource_id: id(200 + n), container_id: id(200 + n), title: `Collection ${n + 1}`, visibility: 'shared', container_head: ''}));
    state.documents = Array.from({length: 22}, (_, n) => ({kind: 'document', resource_id: id(300 + n), container_id: id(200), title: `Document ${n + 1}`, resource_revision: '1'}));
    await page.getByRole('button', {name: 'Docs', exact: true}).click();
    await page.getByLabel('Collection', {exact: true}).selectOption(id(200));
    await page.waitForFunction(() => [...document.querySelectorAll('button')].some(button => button.textContent === 'Next page' && !button.disabled));
    await page.getByRole('button', {name: 'Next page', exact: true}).click();
    await page.getByRole('heading', {name: 'Document 21', exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: 'Document 1', exact: true}).count(), 0);
    assert.equal(state.pages.size, 0);
  });
  await check('repeated-confirmed-resume-retires-the-old-read-handles', async (page, state) => {
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.locator('#project-content[data-live-updates="connected"]').waitFor();
    for (let n = 0; n < 6; n++) {
      state.failure = 'unavailable';
      await page.getByRole('button', {name: 'Refresh', exact: true}).click();
      const opens = state.opens;
      await page.getByRole('button', {name: 'Resume this tab', exact: true}).click();
      const deadline = Date.now() + 10000;
      while (state.opens === opens && Date.now() < deadline) await page.waitForTimeout(50);
      assert.ok(state.opens > opens, 'confirmed resume opens a fresh watch');
      await page.locator('#project-content[data-live-updates="connected"]').waitFor();
      assert.equal(state.watches.size, 1); assert.equal(state.pages.size, 0);
    }
    assert.equal(state.commands.length, 0);
  });
  await check('keyboard-controls-after-switching-between-two-user-pages', async (page, state) => {
    const other = await browser.newPage();
    try {
      await other.setContent('<button>Another user page</button>');
      await other.getByRole('button').click();
      const before = await page.evaluate(() => document.hasFocus());
      await page.bringToFront();
      const traversal = async (target) => {
        await target.waitFor();
        const focus = [];
        for (let count = 0; count <= 80; count++) {
          if (await target.evaluate(element => element === document.activeElement)) return;
          const direction = await target.evaluate(element => document.activeElement && Boolean(document.activeElement.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_PRECEDING) ? 'Shift+Tab' : 'Tab');
          await page.keyboard.press(direction);
          focus.push(await page.evaluate(() => ({tag: document.activeElement?.tagName, text: document.activeElement?.textContent?.slice(0,60)})));
        }
        console.log(JSON.stringify(focus));
        throw new Error('Keyboard could not reach ' + String(target) + '; focus=' + await page.evaluate(() => document.hasFocus()));
      };
      const press = async target => { await traversal(target); await page.keyboard.press('Enter'); };
      const text = async (name, value) => { await traversal(page.getByRole('textbox', {name, exact: true})); await page.keyboard.insertText(value); };
      await press(page.getByRole('button', {name: '＋ New project', exact: true}));
      await text('Title', 'Keyboard project'); await text('Project key', 'KEYBOARD');
      await press(page.getByRole('button', {name: 'Cancel', exact: true}));
      await press(page.getByRole('button', {name: 'Work', exact: true}));
      await press(page.getByRole('button', {name: 'New work item', exact: true}));
      await text('Title', 'Keyboard-created work'); await text('Description', 'Tokyo 東京 — Zoë');
      await press(page.getByRole('button', {name: 'Save at home', exact: true}));
      await page.getByRole('heading', {name: 'Keyboard-created work', exact: true}).waitFor();
      assert.equal(state.commands.length, 1);
      console.log('Keyboard tab focus before selection: ' + before);
    } finally { await other.close(); }
  });
  assert.ok(report.checks.length > 0, 'At least one named browser case must execute');
  report.status = 'pass';
} catch (error) {
  report.status = 'fail'; report.error = String(error); throw error;
} finally {
  report.inputs_after = await inputs();
  if (JSON.stringify(report.inputs_before) !== JSON.stringify(report.inputs_after)) {
    report.status = 'fail'; report.error = 'Rendered source changed during execution'; process.exitCode = 1;
  }
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close(); await new Promise(resolve => server.close(resolve));
}

// Actual Firefox and HomeClient with synthetic HTTP. No native privacy claim.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import {mkdir, mkdtemp, readFile, readdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {firefox} from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0');
const requested = process.argv.slice(2);
assert.ok(requested.length <= 9 && new Set(requested).size === requested.length && requested.every(name => /^[a-z0-9-]{1,100}$/u.test(name)));
await mkdir(path.resolve(root, '../../.runtime'), {recursive: true});
const output = await mkdtemp(path.resolve(root, '../../.runtime/document-context-reference-'));
async function inputs() {
  const entries = await readdir(path.join(root, 'src'), {withFileTypes: true});
  assert.ok(entries.length > 0 && entries.length <= 64 && entries.every(entry => entry.isFile()));
  const files = [...entries.map(entry => 'src/' + entry.name), 'tests/document-context-reference.tsx',
    'tests/workspace-reference.css', 'tests/document-context-reference.mjs', 'package-lock.json'].sort();
  return Object.fromEntries(await Promise.all(files.map(async name => {
    const raw = await readFile(path.join(root, name)); assert.ok(raw.length <= 1024 * 1024);
    return [name, createHash('sha256').update(raw).digest('hex')];
  })));
}
const report = {classification: 'real-browser-document-context-with-mocked-home', qualifies_phase: false,
  status: 'running', node: process.version, requested_cases: requested, checks: [], inputs_before: await inputs()};
const id = number => '019939ba-4000-7000-8000-' + String(number).padStart(12, '0');
const work = number => ({kind: 'work', resource_id: id(number), container_id: '', resource_revision: '1',
  title: `Authorized work ${number}`, status: number === 101 ? 'done' : 'todo', description: '', type: 'task', priority: 'none'});
const relation = (number, workNumber = 101, docNumber = 301, type = 'documents') => ({kind: 'relation', resource_id: id(number),
  resource_revision: '1', type, title: 'Private relation payload title must never be rendered',
  source_project_id: id(1), source_kind: 'document', source_container_id: id(201), source_id: id(docNumber),
  target_project_id: id(1), target_kind: 'work', target_container_id: '', target_id: id(workNumber)});
const doc = number => ({kind: 'document', resource_id: id(number), container_id: id(201), resource_revision: '1', container_head: '1',
  title: '# Accepted document', markdown: '# Accepted document\n\nAccepted synthetic supporting context.'});
let browser, server;
try {
  await build({absWorkingDir: root, entryPoints: {reference: 'tests/document-context-reference.tsx', app: 'src/main.tsx'}, outdir: output,
    bundle: true, format: 'esm', target: 'es2022', define: {'process.env.NODE_ENV': '"development"'}});
  server = createServer(async (request, response) => {
    const asset = {'/reference.js': ['reference.js', 'text/javascript'], '/reference.css': ['reference.css', 'text/css'],
      '/app.js': ['app.js', 'text/javascript'], '/app.css': ['app.css', 'text/css']}[request.url];
    if (request.method !== 'GET') { response.writeHead(405); response.end(); }
    else if (asset) { response.writeHead(200, {'content-type': asset[1]}); response.end(await readFile(path.join(output, asset[0]))); }
    else if (request.url === '/' || request.url === '/product') {
      const entry = request.url === '/product' ? 'app' : 'reference';
      response.writeHead(200, {'content-type': 'text/html'});
      response.end(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic document relationships</title><link rel="stylesheet" href="/${entry}.css"><div id="root"></div><script type="module" src="/${entry}.js"></script></html>`);
    } else { response.writeHead(404); response.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  browser = await firefox.launch({headless: true, timeout: 15000}); report.browser = browser.version();
  async function check(name, operation, configure = () => {}) {
    if (requested.length && !requested.includes(name)) return;
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce', serviceWorkers: 'block'});
    const page = await context.newPage(); page.setDefaultTimeout(10000);
    const state = {requests: [], relations: [relation(501), relation(502, 102, 301, 'related_to'), relation(503, 103)],
      work: new Map([101, 102, 103].map(number => [id(number), work(number)])), denied: new Set([id(103)]),
      generation: 'a'.repeat(64), audit: 'b'.repeat(64), pages: new Map(), watches: new Map(), counter: 0,
      hold: null, releaseRead: null, heldFailure: '', sourceFailure: '', relationsFailure: '', malformedWork: null,
      mixedGeneration: false, repeatedCursor: false, product: false, errors: [], outside: [], endpointReads: 0, maximumEndpointReads: 0};
    configure(state);
    const token = () => (++state.counter).toString(16).padStart(64, '0');
    page.on('pageerror', error => state.errors.push(String(error)));
    await context.route('**/*', async route => {
      const request = route.request();
      if (!request.url().startsWith(origin + '/')) { state.outside.push(request.url()); return route.abort(); }
      if (request.method() === 'GET') return route.continue();
      const value = request.postDataJSON(), endpoint = new URL(request.url()).pathname;
      state.requests.push({endpoint, ...value});
      const send = body => route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
      const rejected = error => send({protocol: 'stead.result/3', status: 'rejected', error});
      if (endpoint === '/stead/api/capabilities') return send({protocol: 'stead.capabilities/3', profile: 'configured-team'});
      if (endpoint === '/stead/auth/resume') return send({status: 'authenticated', csrf: 'c'.repeat(64)});
      if (endpoint === '/stead/api/updates') {
        assert.ok(state.product, 'The context component owns no watch');
        const base = {protocol: 'stead.update-result/3', request_id: value.request_id};
        if (value.action === 'open') {
          const watch_id = token(), cursor = token(); state.watches.set(watch_id, cursor);
          return send({...base, status: 'watching', watch_id, cursor, generation: state.generation, rows: {}});
        }
        if (value.action === 'cancel') { state.watches.delete(value.watch_id); return send({...base, status: 'cancelled', watch_id: value.watch_id, cursor: '', generation: '', rows: {}}); }
        assert.equal(value.action, 'poll'); assert.equal(state.watches.get(value.watch_id), value.cursor);
        const cursor = token(); state.watches.set(value.watch_id, cursor);
        return send({...base, status: 'updated', watch_id: value.watch_id, cursor, generation: state.generation, rows: {}});
      }
      if (endpoint === '/stead/api/code') { assert.ok(state.product); assert.equal(value.action, 'status'); return send({protocol: 'stead.code/1', status: 'disabled', write: 'no', manage: 'no'}); }
      assert.equal(endpoint, '/stead/api/query', 'Only authorized reads, never mutations');
      let rows, generation = state.generation, cursor = '', failure = '';
      if (value.kind === 'identity') rows = [{principal_id: id(900), binding_id: id(901), binding_revision: '1', identity_ship: '~bus', session_audit_id: state.audit, display_name: 'Synthetic member'}];
      else {
        assert.equal(value.project_id, value.kind === 'projects' ? '' : id(1));
        assert.equal(value.search, '');
        if (value.kind === 'document') { assert.equal(value.container_id, id(201)); rows = [doc(Number(value.resource_id.slice(-12)))]; failure = state.sourceFailure; }
        else if (value.kind === 'relations') {
          assert.equal(value.container_id + value.resource_id, ''); failure = state.relationsFailure;
          let offset = 0;
          if (value.cursor) { const entry = state.pages.get(value.cursor); assert.ok(entry, 'Exact cursor is consumed once'); offset = entry; state.pages.delete(value.cursor); }
          rows = state.relations.slice(offset, offset + 20).map(row => ({...row}));
          if (offset && state.mixedGeneration) generation = 'd'.repeat(64);
          if (state.relations.length > offset + 20) { cursor = state.repeatedCursor && value.cursor ? value.cursor : token(); state.pages.set(cursor, offset + 20); }
        } else if (value.kind === 'work') {
          assert.equal(value.container_id, '');
          if (value.resource_id) { rows = [state.malformedWork || state.work.get(value.resource_id)].filter(Boolean); if (state.denied.has(value.resource_id) || !rows.length) failure = 'denied_or_not_found'; }
          else { assert.ok(state.product); rows = [...state.work.values()].filter(row => !state.denied.has(row.resource_id)); }
        } else {
          assert.ok(state.product, 'No unrelated queries in the component fixture');
          const project = {kind: 'project', project_id: id(1), resource_id: id(1), title: 'Garden planning', project_key: 'GARDEN', preset: 'general', authority_epoch: '1', resource_revision: '1', policy_revision: '1', role: 'reader'};
          rows = ['projects', 'project'].includes(value.kind) ? [project]
            : value.kind === 'containers' ? [{kind: 'container', container_id: id(201), title: 'Guides', visibility: 'shared'}]
            : value.kind === 'documents' ? [doc(301)] : ['assignees', 'comments'].includes(value.kind) ? [] : null;
          assert.ok(rows, 'Only expected canonical Work/Doc route reads');
        }
      }
      const endpointRead = value.kind === 'work' && !!value.resource_id;
      if (endpointRead) { state.endpointReads++; state.maximumEndpointReads = Math.max(state.maximumEndpointReads, state.endpointReads); }
      if (state.hold && Object.entries(state.hold).every(([key, expected]) => value[key] === expected)) {
        state.hold = null; await new Promise(resolve => { state.releaseRead = resolve; });
        if (state.heldFailure) failure = state.heldFailure;
      }
      if (endpointRead) await new Promise(resolve => setTimeout(resolve, 40));
      try { return await (failure ? rejected(failure) : send({...value, protocol: 'stead.query-result/3', status: 'read', authority_epoch: '1', generation, cursor,
        rows: Object.fromEntries(rows.map((row, index) => [String(index), row]))})); }
      finally { if (endpointRead) state.endpointReads--; }
    });
    const result = {name, status: 'running'}; report.checks.push(result);
    try {
      await page.goto(origin + (state.product ? `/product#doc/${id(1)}/${id(201)}/${id(301)}` : ''));
      await page.getByRole('region', {name: 'Related work', exact: true}).waitFor();
      await operation(page, state, context);
      assert.deepEqual(state.errors, []); assert.deepEqual(state.outside, []);
      assert.ok(state.maximumEndpointReads <= 6, 'Endpoint reads are batched at most six at a time');
      result.status = 'pass'; console.log('PASS ' + name);
    } catch (error) {
      result.status = 'fail'; result.error = error.stack ?? String(error);
      result.active_element = await page.evaluate(() => ({tag: document.activeElement?.tagName, text: document.activeElement?.textContent?.slice(0, 160)}));
      await page.screenshot({path: path.join(output, 'failure.png'), fullPage: true}); await writeFile(path.join(output, 'failure.html'), await page.content()); throw error;
    } finally { state.releaseRead?.(); await context.close(); }
  }
  const panel = page => page.getByRole('region', {name: 'Related work', exact: true});
  const readRequests = state => state.requests.filter(request => request.endpoint === '/stead/api/query' && request.kind !== 'identity');
  async function show(page) { await panel(page).getByRole('button', {name: 'Show links', exact: true}).click(); }
  async function held(state) { const deadline = Date.now() + 8000; while (!state.releaseRead && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 25)); assert.ok(state.releaseRead); }
  async function ready(page) { await panel(page).getByRole('button', {name: 'Authorized work 101', exact: true}).waitFor(); }

  await check('lazy-current-endpoints-pagination-keyboard-and-narrow-layout', async (page, state) => {
    assert.equal(readRequests(state).length, 0);
    await show(page); await ready(page);
    assert.equal(readRequests(state)[0].kind, 'document');
    assert.equal(readRequests(state).filter(request => request.kind === 'relations').length, 2);
    assert.equal(readRequests(state).filter(request => request.kind === 'work').length, 8, 'Duplicate backlinks resolve each Work once');
    assert.equal(await panel(page).getByText('Private relation payload title must never be rendered', {exact: true}).count(), 0);
    assert.equal(await panel(page).getByRole('button', {name: 'Authorized work 108', exact: true}).count(), 0);
    await panel(page).getByText('Done', {exact: true}).waitFor();
    const target = panel(page).getByRole('button', {name: 'Authorized work 101', exact: true});
    await target.focus(); await target.press('Enter');
    assert.equal(await page.getByLabel('Fixture opened resource').textContent(), `#work/${id(1)}/${id(101)}`);
    assert.ok(await target.evaluate(node => node === document.activeElement));
    for (const width of [1440, 320]) {
      await page.setViewportSize({width, height: 1000});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      assert.ok(await target.evaluate(node => Math.abs(node.querySelector('span').getBoundingClientRect().left - node.getBoundingClientRect().left) <= 2), 'Title aligns with the start of its row');
      await page.screenshot({path: path.join(output, `document-context-${width}.png`), fullPage: true});
    }
  }, state => {
    state.work = new Map(Array.from({length: 8}, (_, index) => [id(101 + index), work(101 + index)])); state.denied = new Set([id(108)]);
    state.relations = [...Array.from({length: 20}, (_, index) => relation(600 + index, 199, 399)),
      ...Array.from({length: 8}, (_, index) => relation(700 + index, 101 + index)), relation(708, 101, 301, 'related_to')];
  });
  await check('revision-clears-old-titles-and-omits-deleted-or-private-targets', async (page, state) => {
    await show(page); await ready(page);
    state.denied.add(id(101)); state.hold = {kind: 'document'};
    await page.getByRole('button', {name: 'Receive current revision', exact: true}).click(); await held(state);
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
    state.releaseRead(); state.releaseRead = null;
    await panel(page).getByRole('button', {name: 'Authorized work 102', exact: true}).waitFor();
    assert.equal(await panel(page).getByRole('button', {name: 'Authorized work 101', exact: true}).count(), 0);
    assert.equal(await panel(page).getByRole('button', {name: 'Authorized work 103', exact: true}).count(), 0);
  });
  await check('late-endpoint-error-cannot-publish-into-a-different-document', async (page, state) => {
    state.hold = {kind: 'work', resource_id: id(101)}; await show(page); await held(state);
    await page.getByRole('button', {name: 'Switch document', exact: true}).click();
    await panel(page).getByRole('heading', {name: 'No related work', exact: true}).waitFor();
    state.heldFailure = 'stale_cursor'; const response = page.waitForResponse(response => response.url().endsWith('/query') && response.request().postDataJSON().resource_id === id(101));
    state.releaseRead(); state.releaseRead = null; await (await response).finished();
    assert.equal(await page.getByLabel('Fixture error').textContent(), 'No fixture error');
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
  });
  await check('dirty-navigation-pauses-publication-and-offline-needs-fresh-links', async (page, state, context) => {
    state.hold = {kind: 'work', resource_id: id(101)}; await show(page); await held(state);
    await page.getByRole('checkbox', {name: 'Pending edit or navigation', exact: true}).check();
    const response = page.waitForResponse(response => response.url().endsWith('/query') && response.request().postDataJSON().resource_id === id(101));
    state.releaseRead(); state.releaseRead = null; await (await response).finished();
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
    await page.getByRole('checkbox', {name: 'Pending edit or navigation', exact: true}).uncheck(); await ready(page);
    await context.setOffline(true); await panel(page).getByText('Connection interrupted', {exact: true}).waitFor();
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
    const count = readRequests(state).length; await context.setOffline(false);
    await panel(page).getByText('The connection is available. Refresh to check the current links.', {exact: true}).waitFor();
    assert.equal(readRequests(state).length, count);
    await panel(page).getByRole('button', {name: 'Refresh links', exact: true}).click(); await ready(page);
  });
  await check('malformed-relations-and-endpoint-substitution-reject-whole-view', async (page, state) => {
    state.relations[0].target_project_id = id(2); await show(page);
    await panel(page).getByText('Could not verify the current links. Refresh to try again.', {exact: true}).waitFor();
    assert.equal(readRequests(state).filter(request => request.kind === 'work').length, 0);
    state.relations = [relation(501)]; state.malformedWork = work(999);
    await panel(page).getByRole('button', {name: 'Refresh links', exact: true}).click();
    await panel(page).getByText('Could not verify the current links. Refresh to try again.', {exact: true}).waitFor();
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
  });
  await check('source-revocation-and-retry-remain-explicit', async (page, state) => {
    state.relationsFailure = 'projection_unavailable'; await show(page);
    await panel(page).getByText('Could not verify the current links. Refresh to try again.', {exact: true}).waitFor();
    state.relationsFailure = ''; await panel(page).getByRole('button', {name: 'Refresh links', exact: true}).click(); await ready(page);
    state.sourceFailure = 'denied_or_not_found'; await page.getByRole('button', {name: 'Receive current revision', exact: true}).click();
    await panel(page).getByText('Access has changed', {exact: true}).waitFor();
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
  });
  await check('changed-session-hides-old-backlinks-before-new-source-read', async (page, state) => {
    await show(page); await ready(page); state.audit = 'd'.repeat(64); state.hold = {kind: 'document'};
    await page.getByRole('button', {name: 'Resume fixture session', exact: true}).click();
    // The authenticated fixture remounts the panel collapsed, as production does.
    await panel(page).getByRole('button', {name: 'Show links', exact: true}).click(); await held(state);
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
    state.releaseRead(); state.releaseRead = null; await ready(page);
  });
  await check('relation-scan-stops-at-native-bounds-and-rejects-generation-change', async (page, state) => {
    state.relations = Array.from({length: 260}, (_, index) => relation(1000 + index)); await show(page);
    await panel(page).getByText('Could not verify the current links. Refresh to try again.', {exact: true}).waitFor();
    assert.equal(readRequests(state).filter(request => request.kind === 'relations').length, 13);
    assert.equal(readRequests(state).filter(request => request.kind === 'work').length, 0);
    state.relations = Array.from({length: 21}, (_, index) => relation(1000 + index)); state.mixedGeneration = true;
    await panel(page).getByRole('button', {name: 'Refresh links', exact: true}).click();
    await panel(page).getByText('Could not verify the current links. Refresh to try again.', {exact: true}).waitFor();
    assert.equal(await panel(page).locator('button[data-resource-route]').count(), 0);
  });
  await check('production-doc-backlink-opens-canonical-work-and-browser-back-reads-doc', async (page, state) => {
    await show(page); await ready(page);
    await panel(page).getByRole('button', {name: 'Authorized work 101', exact: true}).click();
    await page.locator('#work-detail-panel').getByRole('heading', {name: 'Authorized work 101', exact: true}).waitFor();
    assert.equal(new URL(page.url()).hash, `#work/${id(1)}/${id(101)}`);
    await page.goBack();
    const heading = page.locator('.document-editor').getByRole('heading', {name: 'Accepted document', level: 2, exact: true}); await heading.waitFor();
    await page.locator('.document-reader').getByRole('heading', {name: 'Accepted document', exact: true}).waitFor();
    assert.equal(new URL(page.url()).hash, `#doc/${id(1)}/${id(201)}/${id(301)}`);
    await page.waitForFunction(() => document.activeElement?.matches('.document-editor .editor-heading h2'));
    assert.ok(await heading.evaluate(node => node === document.activeElement));
    assert.equal(await page.locator('#work-detail-panel').count(), 0);
    assert.ok(readRequests(state).filter(request => request.kind === 'document' && request.resource_id === id(301)).length >= 3, 'Return reauthorizes the exact document');
    const preview = page.getByRole('group', {name: 'Document view', exact: true}).getByRole('button', {name: 'Preview', exact: true});
    await preview.focus(); await preview.press('Enter');
    assert.equal(await preview.getAttribute('aria-pressed'), 'true');
    assert.ok(await preview.evaluate(node => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(node === document.activeElement))))), 'Ordinary mode rerenders do not repeat route focus restoration');
  }, state => { state.product = true; });
  assert.equal(report.checks.length, requested.length || 9);
  if (requested.length) assert.deepEqual(report.checks.map(check => check.name).sort(), [...requested].sort());
  report.status = 'pass';
} catch (error) { report.status = 'fail'; report.error = error.stack ?? String(error); process.exitCode = 1; }
finally {
  report.inputs_after = await inputs();
  if (JSON.stringify(report.inputs_before) !== JSON.stringify(report.inputs_after)) { report.status = 'fail'; report.error = 'Document context inputs changed'; process.exitCode = 1; }
  if (browser) await browser.close(); if (server?.listening) await new Promise(resolve => server.close(resolve));
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({status: report.status, checks: report.checks.length, report: path.join(output, 'report.json'), error: report.error}));
}

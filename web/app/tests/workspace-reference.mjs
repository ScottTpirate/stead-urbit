// Actual HomeClient + Firefox, synthetic query/3/update/3 responses only.
// This does not qualify native authorization, project filtering or deployment.
import assert from 'node:assert/strict';
import {webSourceFiles} from './web-source-files.mjs';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import {mkdir, mkdtemp, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {firefox} from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0');
const requested = process.argv.slice(2);
assert.ok(requested.length <= 10 && new Set(requested).size === requested.length && requested.every(name => /^[a-z0-9-]{1,100}$/u.test(name)));
await mkdir(path.resolve(root, '../../.runtime'), {recursive: true});
const output = await mkdtemp(path.resolve(root, '../../.runtime/workspace-reference-'));
async function inputs() {
  const sourceFiles = await webSourceFiles(root);
  const files = [...sourceFiles, 'tests/web-source-files.mjs', 'tests/workspace-reference.tsx',
    'tests/workspace-reference.css', 'tests/workspace-reference.mjs', 'package-lock.json'].sort();
  return Object.fromEntries(await Promise.all(files.map(async name => {
    const raw = await readFile(path.join(root, name)); assert.ok(raw.length <= 1024 * 1024);
    return [name, createHash('sha256').update(raw).digest('hex')];
  })));
}
const report = {classification: 'real-browser-workspace-with-mocked-home', qualifies_phase: false,
  node: process.version, requested_cases: requested, status: 'running', checks: [], inputs_before: await inputs()};
const id = number => '019939ba-4000-7000-8000-' + String(number).padStart(12, '0');
const work = number => ({kind: 'work', project_id: id(1), project_title: 'Garden planning', project_key: 'GARDEN',
  resource_id: id(number), container_id: '', title: `Assigned task ${number}`, status: 'todo', assignee_display_name: 'Synthetic member'});
const doc = {kind: 'document', project_id: id(2), project_title: 'Event program', project_key: 'EVENT',
  resource_id: id(301), container_id: id(201), title: '# Accessible event guide', snippet: 'Tokyo 東京 — keep the supporting context readable.'};
let browser, server;
try {
  await build({absWorkingDir: root, entryPoints: {reference: 'tests/workspace-reference.tsx', app: 'src/main.tsx'}, outdir: output,
    bundle: true, format: 'esm', target: 'es2022', define: {'process.env.NODE_ENV': '"development"'}});
  server = createServer(async (request, response) => {
    const asset = {'/reference.js': ['reference.js', 'text/javascript'], '/reference.css': ['reference.css', 'text/css'],
      '/app.js': ['app.js', 'text/javascript'], '/app.css': ['app.css', 'text/css']}[request.url];
    if (request.method !== 'GET') { response.writeHead(405); response.end(); }
    else if (asset) { response.writeHead(200, {'content-type': asset[1]}); response.end(await readFile(path.join(output, asset[0]))); }
    else if (request.url === '/' || request.url === '/product') {
      response.writeHead(200, {'content-type': 'text/html'});
      const entry = request.url === '/product' ? 'app' : 'reference';
      response.end(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic workspace reference</title><link rel="stylesheet" href="/${entry}.css"><div id="root"></div><script type="module" src="/${entry}.js"></script></html>`);
    } else { response.writeHead(404); response.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  browser = await firefox.launch({headless: true, timeout: 15000}); report.browser = browser.version();
  async function check(name, operation, configure = () => {}) {
    if (requested.length && !requested.includes(name)) return;
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce', serviceWorkers: 'block'});
    const page = await context.newPage(); page.setDefaultTimeout(10000);
    const state = {requests: [], my: Array.from({length: 22}, (_, index) => work(101 + index)), search: [work(101), doc],
      watches: new Map(), pages: new Map(), counter: 0, generation: 'a'.repeat(64), audit: 'b'.repeat(64),
      holdOpen: false, releaseOpen: null, holdRead: false, releaseRead: null, activeOpens: 0, maximumOpens: 0,
      refreshRequired: false, failure: '', errors: [], outside: [], product: false};
    configure(state);
    const token = () => (++state.counter).toString(16).padStart(64, '0');
    page.on('pageerror', error => state.errors.push(String(error)));
    await context.route('**/*', async route => {
      const request = route.request();
      if (!request.url().startsWith(origin + '/')) { state.outside.push(request.url()); return route.abort(); }
      if (request.method() === 'GET') return route.continue();
      const value = request.postDataJSON(); const endpoint = new URL(request.url()).pathname;
      state.requests.push({endpoint, ...value});
      const send = body => route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
      if (endpoint === '/stead/api/capabilities') return send({protocol: 'stead.capabilities/3', profile: 'configured-team', workspace_queries: 'stead.workspace-queries/1'});
      if (endpoint === '/stead/auth/resume') return send({status: 'authenticated', csrf: 'c'.repeat(64)});
      if (endpoint === '/stead/api/query' && value.kind === 'identity') return send({...value, protocol: 'stead.query-result/3', status: 'read',
        authority_epoch: '1', generation: state.generation, cursor: '', rows: {person: {principal_id: id(900), binding_id: id(901), binding_revision: '1',
          identity_ship: '~bus', session_audit_id: state.audit, display_name: 'Synthetic member'}}});
      if (endpoint === '/stead/api/updates') {
        const base = {protocol: 'stead.update-result/3', request_id: value.request_id};
        if (value.action === 'open') {
          assert.ok(['my-work', 'workspace-search', ...(state.product ? ['documents'] : [])].includes(value.kind));
          if (['my-work', 'workspace-search'].includes(value.kind)) assert.equal(value.project_id + value.container_id + value.resource_id, '');
          state.activeOpens++; state.maximumOpens = Math.max(state.maximumOpens, state.activeOpens);
          if (state.holdOpen) { state.holdOpen = false; await new Promise(resolve => { state.releaseOpen = resolve; }); }
          state.activeOpens--;
          const watch_id = token(), cursor = token();
          state.watches.set(watch_id, {scope: value.kind + '/' + value.search, cursor, generation: state.generation, sequence: 0});
          return send({...base, status: 'watching', watch_id, cursor, generation: state.generation, rows: {}});
        }
        if (value.action === 'cancel') {
          state.watches.delete(value.watch_id);
          return send({...base, status: 'cancelled', watch_id: value.watch_id, cursor: '', generation: '', rows: {}});
        }
        assert.equal(value.action, 'poll');
        const watch = state.watches.get(value.watch_id);
        if (state.refreshRequired || !watch) {
          state.refreshRequired = false; state.watches.delete(value.watch_id);
          return send({...base, status: 'refresh_required', watch_id: value.watch_id, cursor: '', generation: '', rows: {}});
        }
        assert.equal(value.cursor, watch.cursor);
        const rows = watch.generation === state.generation ? {} : {'0': {sequence: String(++watch.sequence), generation: state.generation}};
        watch.generation = state.generation; watch.cursor = token();
        return send({...base, status: 'updated', watch_id: value.watch_id, cursor: watch.cursor, generation: watch.generation, rows});
      }
      if (state.product && endpoint === '/stead/api/code') {
        assert.equal(value.action, 'status'); return send({protocol: 'stead.code/1', status: 'disabled', write: 'no', manage: 'no'});
      }
      assert.equal(endpoint, '/stead/api/query', 'No mutation, fan-out or unrelated endpoint');
      if (state.product && !['my-work', 'workspace-search'].includes(value.kind)) {
        const projects = [1, 2].map(number => ({kind: 'project', project_id: id(number), resource_id: id(number), title: number === 1 ? 'Garden planning' : 'Event program',
          project_key: number === 1 ? 'GARDEN' : 'EVENT', preset: 'general', authority_epoch: '1', resource_revision: '1', policy_revision: '1', role: 'reader'}));
        const document = {...doc, resource_revision: '1', container_head: '1', markdown: '# Accessible event guide\n\nRead the accepted event plan.'};
        const collection = {kind: 'container', container_id: id(201), project_id: id(2), title: 'Event documents'};
        const rows = value.kind === 'projects' ? projects : value.kind === 'project' ? projects.filter(row => row.project_id === value.project_id)
          : value.kind === 'containers' ? [collection] : ['document', 'documents'].includes(value.kind) ? [document] : null;
        assert.ok(rows, 'Only expected product navigation reads');
        return send({...value, protocol: 'stead.query-result/3', status: 'read', authority_epoch: '1', generation: state.generation, cursor: '',
          rows: Object.fromEntries(rows.map((row, index) => [String(index), row]))});
      }
      assert.ok(['my-work', 'workspace-search'].includes(value.kind));
      assert.equal(value.project_id + value.container_id + value.resource_id, '');
      assert.ok(new TextEncoder().encode(value.search).length <= 128);
      if (value.kind === 'my-work') assert.equal(value.search, '');
      const rows = [...(value.kind === 'my-work' ? state.my : state.search)].map(row => ({...row}));
      const generation = state.generation;
      let offset = 0;
      if (value.cursor) {
        const page = state.pages.get(value.cursor); assert.ok(page, 'Exact live cursor used once');
        assert.equal(page.scope, value.kind + '/' + value.search); offset = page.offset; state.pages.delete(value.cursor);
      }
      if (state.holdRead) { state.holdRead = false; await new Promise(resolve => { state.releaseRead = resolve; }); }
      if (state.failure) return send({protocol: 'stead.result/3', status: 'rejected', error: state.failure});
      let cursor = '';
      if (rows.length > offset + 20) {
        cursor = token(); state.pages.set(cursor, {scope: value.kind + '/' + value.search, offset: offset + 20});
      }
      return send({...value, protocol: 'stead.query-result/3', status: 'read', authority_epoch: '0', generation, cursor,
        rows: Object.fromEntries(rows.slice(offset, offset + 20).map((row, index) => [String(index), row]))});
    });
    const result = {name, status: 'running'}; report.checks.push(result);
    try {
      await page.goto(origin + (state.product ? '/product' : ''));
      await (state.product ? page.getByRole('navigation', {name: 'Workspace', exact: true}) : page.getByRole('heading', {name: 'My work', exact: true})).waitFor();
      await operation(page, state, context);
      assert.deepEqual(state.errors, []); assert.deepEqual(state.outside, []);
      assert.equal(state.maximumOpens, 1, 'Only one watch open is in flight');
      result.status = 'pass'; console.log('PASS ' + name);
    } catch (error) {
      result.status = 'fail'; result.error = error.stack ?? String(error);
      await page.screenshot({path: path.join(output, 'failure.png'), fullPage: true});
      await writeFile(path.join(output, 'failure.html'), await page.content()); throw error;
    } finally { state.releaseOpen?.(); state.releaseRead?.(); await context.close(); }
  }
  const reads = state => state.requests.filter(request => request.endpoint === '/stead/api/query' && request.kind !== 'identity');
  const opens = state => state.requests.filter(request => request.action === 'open');
  async function held(state, name) {
    const deadline = Date.now() + 8000;
    while (!state[name] && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 25));
    assert.ok(state[name], 'Controlled response hold reached');
  }
  await check('authorized-pages-keyboard-routes-and-narrow-results', async (page, state) => {
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    assert.equal(reads(state).length, 1); assert.equal(state.watches.size, 1);
    assert.deepEqual(state.requests.filter(request => request.action).map(request => request.action).slice(0, 3), ['open', 'cancel', 'open'], 'StrictMode retires the first mount before opening its replacement');
    const opened = opens(state).length;
    assert.ok(state.requests.findIndex(request => request.action === 'open') < state.requests.findIndex(request => request.kind === 'my-work' && request.endpoint.endsWith('/query')));
    assert.equal(await page.locator('.workspace-result').count(), 20);
    await page.getByRole('button', {name: 'Next page', exact: true}).click();
    const target = page.getByRole('button', {name: 'Assigned task 121', exact: true}); await target.waitFor();
    assert.equal(await page.locator('.workspace-result').count(), 2);
    assert.equal(opens(state).length, opened, 'Pagination keeps the watch');
    await target.focus(); await target.press('Enter');
    assert.equal(await page.getByLabel('Fixture opened resource').textContent(), `#work/${id(1)}/${id(121)}`);
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height: 1000});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.screenshot({path: path.join(output, `workspace-${width}.png`), fullPage: true});
    }
  });
  await check('search-typing-is-local-and-submit-has-one-native-scope', async (page, state) => {
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Show Search', exact: true}).click();
    const input = page.getByRole('textbox', {name: 'Search this Home', exact: true});
    const before = reads(state).length, opening = opens(state).length;
    await input.pressSequentially('event');
    assert.equal(reads(state).length, before); assert.equal(opens(state).length, opening);
    await page.getByRole('button', {name: 'Search', exact: true}).click();
    const target = page.getByRole('button', {name: 'Accessible event guide', exact: true}); await target.waitFor();
    assert.equal(reads(state).at(-1).kind, 'workspace-search'); assert.equal(reads(state).at(-1).search, 'event');
    await target.click(); assert.equal(await page.getByLabel('Fixture opened resource').textContent(), `#doc/${id(2)}/${id(201)}/${id(301)}`);
    const queried = reads(state).length, watched = opens(state).length;
    await input.fill('名'.repeat(43)); await page.getByRole('button', {name: 'Search', exact: true}).click();
    await page.getByText('This search is too long. Use fewer or shorter words.', {exact: true}).waitFor();
    assert.equal(reads(state).length, queried); assert.equal(opens(state).length, watched);
  });
  await check('late-watch-open-is-retired-before-the-next-scope', async (page, state) => {
    await held(state, 'releaseOpen');
    await page.getByRole('button', {name: 'Show Search', exact: true}).click();
    await page.getByRole('textbox', {name: 'Search this Home', exact: true}).fill('event');
    await page.getByRole('button', {name: 'Search', exact: true}).click();
    assert.equal(opens(state).length, 1);
    state.releaseOpen(); state.releaseOpen = null;
    await page.getByRole('button', {name: 'Accessible event guide', exact: true}).waitFor();
    assert.deepEqual(state.requests.filter(request => request.action).map(request => request.action).slice(0, 3), ['open', 'cancel', 'open']);
    assert.deepEqual(reads(state).map(request => request.kind), ['workspace-search']);
    state.holdRead = true;
    await page.getByRole('textbox', {name: 'Search this Home', exact: true}).fill('new term');
    await page.getByRole('button', {name: 'Search', exact: true}).click();
    await held(state, 'releaseRead');
    await page.getByRole('button', {name: 'Show My work', exact: true}).click();
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    const response = page.waitForResponse(response => response.url().endsWith('/query') && response.request().postDataJSON().search === 'new term');
    state.releaseRead(); state.releaseRead = null; await (await response).finished();
    assert.equal(await page.getByRole('button', {name: 'Accessible event guide', exact: true}).count(), 0, 'Late search response cannot publish into My work');
  }, state => { state.holdOpen = true; });
  await check('terminal-access-refresh-clears-previews-before-requery', async (page, state) => {
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    state.holdRead = true; state.refreshRequired = true;
    await held(state, 'releaseRead');
    assert.equal(await page.locator('.workspace-result').count(), 0, 'Old protected titles/snippets disappear while current access is checked');
    state.failure = 'denied_or_not_found'; state.releaseRead(); state.releaseRead = null;
    await page.getByText('Access has changed', {exact: true}).waitFor();
    assert.equal(await page.locator('.workspace-result').count(), 0);
  });
  await check('pending-navigation-keeps-consumed-cursor-and-offline-needs-refresh', async (page, state, context) => {
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    state.holdRead = true; await page.getByRole('button', {name: 'Next page', exact: true}).click();
    await held(state, 'releaseRead');
    await page.getByRole('checkbox', {name: 'Pending navigation', exact: true}).check();
    const response = page.waitForResponse(response => response.url().endsWith('/query') && !!response.request().postDataJSON().cursor);
    state.releaseRead(); state.releaseRead = null; await (await response).finished();
    assert.equal(await page.getByRole('button', {name: 'Assigned task 121', exact: true}).count(), 0);
    await page.getByRole('checkbox', {name: 'Pending navigation', exact: true}).uncheck();
    await page.getByRole('button', {name: 'Assigned task 121', exact: true}).waitFor();
    assert.equal(reads(state).filter(request => request.cursor).length, 1, 'Consumed cursor was not replayed');
    await context.setOffline(true); await page.getByText('Connection interrupted', {exact: true}).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Assigned task 121', exact: true}).isDisabled(), true);
    const before = reads(state).length; await context.setOffline(false);
    await page.getByText('The connection is available. Refresh to check your access and current results.', {exact: true}).waitFor();
    assert.equal(reads(state).length, before);
    await page.getByRole('button', {name: 'Refresh results', exact: true}).click();
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
  });
  await check('malformed-scope-and-duplicate-resources-reject-the-whole-page', async (page, state) => {
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    for (const rows of [[{...work(101), project_id: 'invalid'}], [{...work(101), container_id: id(201)}], [doc], [work(101), work(101)]]) {
      state.my = rows;
      await page.getByRole('button', {name: 'Refresh results', exact: true}).click();
      await page.getByText('Home returned results that could not be verified. Refresh to try again.', {exact: true}).waitFor();
      assert.equal(await page.locator('.workspace-result').count(), 0);
    }
  });
  await check('changed-session-hides-old-rows-and-return-focus-waits-for-snapshot', async (page, state) => {
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Hide workspace', exact: true}).click();
    state.holdRead = true;
    await page.getByRole('button', {name: 'Restore workspace', exact: true}).click();
    await held(state, 'releaseRead');
    assert.equal(await page.locator('.workspace-result').count(), 0);
    state.releaseRead(); state.releaseRead = null;
    const first = page.getByRole('button', {name: 'Assigned task 101', exact: true}); await first.waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('data-resource-route')?.endsWith('000000000101'));
    state.audit = 'd'.repeat(64); state.my = [{...work(201), title: 'New session result'}]; state.holdRead = true;
    await page.getByRole('button', {name: 'Resume fixture session', exact: true}).click();
    await held(state, 'releaseRead');
    assert.equal(await first.count(), 0, 'Previous session titles do not remain while its replacement loads');
    state.releaseRead(); state.releaseRead = null;
    await page.getByRole('button', {name: 'New session result', exact: true}).waitFor();
  });
  await check('empty-results-and-unsupported-home-stay-explicit', async (page, state) => {
    await page.getByRole('heading', {name: 'No assigned work', exact: true}).waitFor();
    state.failure = 'unsupported_query';
    await page.getByRole('button', {name: 'Refresh results', exact: true}).click();
    await page.getByText('Not available here', {exact: true}).waitFor();
    assert.equal(await page.locator('.workspace-result').count(), 0);
  }, state => { state.my = []; });
  await check('expired-pagination-clears-page-and-refresh-starts-with-empty-cursor', async (page, state) => {
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    state.failure = 'stale_cursor';
    await page.getByRole('button', {name: 'Next page', exact: true}).click();
    await page.getByText('These results changed. Refresh to start from the first page.', {exact: true}).waitFor();
    assert.equal(await page.locator('.workspace-result').count(), 0);
    state.failure = '';
    await page.getByRole('button', {name: 'Refresh results', exact: true}).click();
    await page.getByRole('button', {name: 'Assigned task 101', exact: true}).waitFor();
    assert.equal(reads(state).at(-1).cursor, ''); assert.equal(reads(state).filter(request => request.cursor).length, 1);
  });
  await check('production-search-opens-canonical-doc-and-back-restores-term-focus', async (page, state) => {
    await page.getByRole('navigation', {name: 'Workspace', exact: true}).getByRole('button', {name: 'Search', exact: true}).click();
    const input = page.getByRole('textbox', {name: 'Search this Home', exact: true});
    await input.fill('event'); await page.locator('form.workspace-search').getByRole('button', {name: 'Search', exact: true}).click();
    const target = page.getByRole('button', {name: 'Accessible event guide', exact: true}); await target.waitFor();
    await input.fill('Unsubmitted local draft');
    await target.click();
    await page.locator('.document-reader').getByRole('heading', {name: 'Accessible event guide', exact: true}).waitFor();
    assert.equal(new URL(page.url()).hash, `#doc/${id(2)}/${id(201)}/${id(301)}`);
    assert.equal(state.requests.filter(request => request.kind === 'projects').length, 2, 'Opening rechecks the current authorized project list');
    state.holdRead = true; await page.goBack(); await held(state, 'releaseRead');
    assert.equal(await page.locator('.workspace-result').count(), 0);
    assert.equal(await input.inputValue(), 'Unsubmitted local draft');
    state.releaseRead(); state.releaseRead = null; await target.waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('data-resource-route')?.startsWith('#doc/'));
    assert.equal(reads(state).filter(request => request.kind === 'workspace-search').at(-1).search, 'event');
    assert.equal(new URL(page.url()).hash, '#search');
  }, state => { state.product = true; });
  assert.equal(report.checks.length, requested.length || 10);
  if (requested.length) assert.deepEqual(report.checks.map(check => check.name).sort(), [...requested].sort());
  report.status = 'pass';
} catch (error) { report.status = 'fail'; report.error = error.stack ?? String(error); process.exitCode = 1; }
finally {
  report.inputs_after = await inputs();
  if (JSON.stringify(report.inputs_before) !== JSON.stringify(report.inputs_after)) { report.status = 'fail'; report.error = 'Workspace reference inputs changed'; process.exitCode = 1; }
  if (browser) await browser.close();
  if (server?.listening) await new Promise(resolve => server.close(resolve));
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({status: report.status, checks: report.checks.length, report: path.join(output, 'report.json'), error: report.error}));
}

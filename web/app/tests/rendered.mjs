// Real Firefox + synthetic HTTP responses. This does not qualify native TLS,
// authentication, permissions or the business outcomes represented by fixtures.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { firefox } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0', 'Use the pinned frontend Node runtime');
const output = path.resolve(root, '../../.runtime/web-render-tests');
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
const report = {classification: 'real-browser-with-mocked-home', node: process.version, browser: browser.version(), checks: [], qualifies_phase: false};
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
    project: {kind: 'project', resource_id: id(1), project_id: id(1), title: 'Garden', project_key: 'GARDEN', preset: 'general', authority_epoch: '1', resource_revision: '1', policy_revision: '1', role: 'maintainer'},
    work: [], activity: []};
  await page.route(origin + '/stead/**', async route => {
    const request = route.request();
    if (request.method() !== 'POST') return route.continue();
    const value = request.postDataJSON();
    const pathname = new URL(request.url()).pathname;
    const send = (body, status = 200) => route.fulfill({status, contentType: 'application/json', body: JSON.stringify(body)});
    if (pathname.endsWith('/capabilities')) return send({protocol: 'stead.capabilities/3', profile: 'configured-team'});
    if (pathname.endsWith('/resume')) return state.resumeFailure ? send({}, 503) : send({status: 'authenticated', csrf: 'b'.repeat(64)});
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
    if (value.kind === 'identity') rows = [person];
    if (value.kind === 'projects' || value.kind === 'project') rows = [state.project];
    if (value.kind === 'work') rows = state.work;
    if (value.kind === 'activity') rows = state.activity;
    if (value.kind === 'receipt') {
      state.recoveryIds.push(value.resource_id);
      rows = state.receipts.has(value.resource_id) ? [state.receipts.get(value.resource_id)] : [];
    }
    return send({...value, protocol: 'stead.query-result/3', status: 'read', authority_epoch: state.project.authority_epoch,
      generation: 'c'.repeat(64), cursor: '', rows: Object.fromEntries(rows.map((row, i) => [String(i), row]))});
  });
  try {
    await page.goto(origin + '/stead/');
    await page.getByRole('button', {name: /GARDEN.*Garden/u}).click();
    await page.getByRole('heading', {name: 'Garden', exact: true}).first().waitFor();
    await page.getByRole('button', {name: 'Refresh', exact: true}).waitFor();
    await run(page, state, consoleErrors);
  } catch (error) {
    await writeFile(path.join(output, 'failure.html'), await page.content());
    await page.screenshot({path: path.join(output, 'failure.png'), fullPage: true});
    throw error;
  } finally { await context.close(); }
}
async function check(name, run) {
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
  report.status = 'pass';
} catch (error) {
  report.status = 'fail'; report.error = String(error); throw error;
} finally {
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close(); await new Promise(resolve => server.close(resolve));
}

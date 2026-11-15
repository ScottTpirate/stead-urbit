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

async function fixture(run, mockRepository = false) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const consoleErrors = [];
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  const state = {failure: '', resumeFailure: false, signedOut: false, unreachable: false, authStarts: [], loseCommand: false, commands: [], recoveryIds: [], receipts: new Map(),
    watches: new Map(), pages: new Map(), requests: [], sequence: 0, token: 0, polls: 0, opens: 0, denied: false,
    holdOpen: false, releaseOpen: null, holdWork: false, releaseWork: null, invalidateCommands: false,
    project: {kind: 'project', resource_id: id(1), project_id: id(1), title: 'Garden', project_key: 'GARDEN', preset: 'general', authority_epoch: '1', resource_revision: '1', policy_revision: '1', role: 'maintainer'},
    work: [], assignees: [], activity: [], containers: [], documents: [], proposals: new Map(), mergeRequests: [], dropMergeResponse: false,
    externalWritable: false, externalReviews: new Map(), externalRequests: [], browseRequests: [], browseFixture: null,
    changesRequests: [], changesFixture: null, comments: new Map(), delegations: new Map(), relations: []};
  await page.route(origin + '/stead/**', async route => {
    const request = route.request();
    if (request.method() !== 'POST') return route.continue();
    const value = request.postDataJSON();
    const pathname = new URL(request.url()).pathname;
    state.requests.push({path: pathname, kind: value.kind, action: value.action, search: value.search});
    const send = (body, status = 200) => route.fulfill({status, contentType: 'application/json', body: JSON.stringify(body)});
    if (state.unreachable) return route.abort('failed');
    if (pathname.endsWith('/capabilities')) return send({protocol: 'stead.capabilities/3', profile: 'configured-team'});
    if (pathname.endsWith('/start')) {
      state.authStarts.push(value.identity_ship);
      return send({status: 'pending', challenge_id: 'c'.repeat(64), comparison_code: 'sample-comparison'});
    }
    if (pathname.endsWith('/resume')) {
      if (state.signedOut) return send({}, 401);
      if (state.resumeFailure) return send({}, 503);
      state.watches.clear(); state.pages.clear();
      return send({status: 'authenticated', csrf: 'b'.repeat(64)});
    }
    const token = () => (++state.token).toString(16).padStart(64, '0');
    if (pathname === '/stead/api/code/changes') {
      state.changesRequests.push(value);
      if (!state.changesFixture) return route.fulfill({status: 404, contentType: 'text/html', body: 'Not found'});
      assert.deepEqual(Object.keys(value).sort(), ['path', 'project_id', 'proposal_id', 'protocol', 'revision', 'snapshot', 'view']);
      assert.equal(value.protocol, 'stead.git-changes/1');
      assert.equal(value.project_id, state.project.project_id);
      const proposal = state.externalReviews.get(value.proposal_id);
      if (!proposal) return send({error: 'denied_or_not_found'}, 404);
      if (value.snapshot !== state.pack?.snapshot || value.revision !== proposal.revision) return send({error: 'stale_selection'}, 409);
      const {status, fields} = await state.changesFixture(value, proposal);
      if (status !== 200) return send(fields, status);
      const {view, path, ...scope} = value;
      return send({...scope, ...(view === 'patch' ? {path} : {}), status: view, base: proposal.base_oid, head: proposal.head_oid, ...fields});
    }
    if (pathname === '/stead/api/code/browse') {
      state.browseRequests.push(value);
      if (!state.browseFixture) return route.fulfill({status: 404, contentType: 'text/html', body: 'Not found'});
      assert.deepEqual(Object.keys(value).sort(), ['path', 'project_id', 'protocol', 'ref', 'snapshot', 'view']);
      assert.equal(value.protocol, 'stead.git-browse/1');
      assert.equal(value.project_id, state.project.project_id);
      assert.equal(value.snapshot, state.pack.snapshot);
      assert.ok(Object.hasOwn(JSON.parse(state.pack.refs), value.ref));
      const {status, fields} = await state.browseFixture(value);
      if (status !== 200) return send(fields, status);
      const {view, ...scope} = value;
      return send({...scope, status: view, ...fields});
    }
    if (pathname === '/stead/api/code') {
      assert.equal(value.project_id, state.project.project_id);
      const respond = fields => send({protocol: 'stead.code/1', ...fields});
      if (!mockRepository) {
        assert.equal(value.action, 'status');
        return respond({status: 'disabled', write: 'no', manage: 'no'});
      }
      if (value.action === 'create') {
        state.repositoryReady = true;
        return respond({status: 'ready'});
      }
      if (value.action === 'status') return respond({status: state.pack?.status ?? (state.repositoryReady ? 'ready' : 'disabled'),
        write: state.pack && !state.externalWritable ? 'no' : 'yes', manage: 'yes'});
      if (value.action === 'work-delegations') {
        const rows = Object.fromEntries([...state.delegations].filter(([, entry]) => entry.work_id === value.work_id)
          .map(([id, {work_id, ...entry}]) => [id, entry]));
        return respond({status: 'work-delegations', work_id: value.work_id, rows: JSON.stringify(rows)});
      }
      if (value.action === 'delegate') {
        const {delegation_id, worker_ship, work_id, ref, expires_at_ms} = value;
        assert.ok(state.work.some(row => row.resource_id === work_id));
        state.delegations.set(delegation_id, {delegation_id, worker_ship, work_id, ref, expires_at_ms,
          status: 'active', can_revoke: 'yes', proposals: '{}'});
        return respond({status: 'accepted', delegation_id});
      }
      if (value.action === 'revoke-delegation') {
        const row = state.delegations.get(value.delegation_id);
        assert.ok(row);
        row.status = 'revoked'; row.can_revoke = 'no';
        return respond({status: 'accepted', delegation_id: value.delegation_id});
      }
      if (value.action === 'pack-view') { assert.ok(state.pack); return respond(state.pack); }
      if (value.action === 'pack-accept') {
        assert.equal(state.pack?.status, 'external-staged');
        assert.equal(value.snapshot, state.pack.snapshot);
        state.pack = {...state.pack, status: 'external', generation: '0', request_id: value.request_id, accepted_at_ms: '1800000000000'};
        return respond(state.pack);
      }
      if (value.action === 'issue') {
        assert.equal(state.pack?.status, 'external');
        assert.ok(value.access === 'read' || (state.externalWritable && value.access === 'write'));
        return respond({status: 'issued', bearer: 'c'.repeat(64), handle: 'd'.repeat(64), expires_at_ms: '1800000900000'});
      }
      if (value.action === 'revoke') {
        assert.equal(value.handle, 'd'.repeat(64));
        return respond({status: 'revoked'});
      }
      if (value.action.startsWith('external-')) {
        state.externalRequests.push(value);
        if (value.action === 'external-list') {
          assert.deepEqual(Object.keys(value).sort(), ['action', 'project_id', 'protocol', ...(value.work_id ? ['work_id'] : [])]);
          const proposals = [...state.externalReviews.values()].filter(row => !value.work_id || row.work_id === value.work_id)
            .map(row => ({protocol: 'stead.code/1', status: 'proposal', ...row,
            work_title: state.work.find(work => work.resource_id === row.work_id)?.title ?? ''}));
          return respond({status: 'proposals', rows: JSON.stringify(proposals)});
        }
        const saved = state.externalReviews.get(value.proposal_id);
        if (value.action === 'external-proposal') {
          assert.deepEqual(Object.keys(value).sort(), ['action', 'project_id', 'proposal_id', 'protocol']);
          return saved ? respond({status: 'proposal', ...saved}) : send({error: 'denied_or_not_found'}, 404);
        }
        const {proposal_id, revision, work_id, source_ref, ref, base_oid, head_oid, request_id} = value;
        if (value.action === 'external-submit') {
          if (value.base_snapshot !== state.pack.snapshot || value.generation !== state.pack.generation) {
            return send({error: 'stale-selection'}, 409);
          }
          state.externalReviews.set(proposal_id, {proposal_id, revision, work_id, source_ref, ref, base_oid, head_oid,
            author: person.principal_id, reviewer: '', base_snapshot: value.base_snapshot, generation: value.generation,
            merged_revision: '', merged_snapshot: '', merged_request_id: ''});
          return respond({status: 'accepted', proposal_id, revision, request_id});
        }
        assert.ok(saved);
        if (value.action === 'external-approve') {
          for (const key of ['revision', 'base_snapshot', 'base_oid', 'head_oid']) assert.equal(saved[key], value[key]);
          saved.reviewer = person.principal_id;
          return respond({status: 'accepted', proposal_id, revision, request_id});
        }
        assert.equal(value.action, 'external-merge');
        const proof = JSON.parse(value.proof);
        assert.equal(value.proof, canonical(proof) + '\n');
        if (state.dropMergeResponse) state.dropMergeResponse = false;
        else {
          if (state.mergeRequests.length > 0) assert.deepEqual(value, state.mergeRequests[0]);
          return respond({status: 'merged', request_id, proposal_id, snapshot: proof.candidate_snapshot, generation: String(Number(proof.generation) + 1)});
        }
        state.mergeRequests.push(value);
        saved.merged_revision = revision;
        saved.merged_snapshot = proof.candidate_snapshot;
        saved.merged_request_id = request_id;
        state.pack = {...state.pack, snapshot: proof.candidate_snapshot, generation: String(Number(proof.generation) + 1), request_id,
          refs: JSON.stringify({...JSON.parse(state.pack.refs), [state.pack.head]: proof.head_oid})};
        return route.abort('failed');
      }
      const key = value.proposal_id + '/' + value.revision;
      if (value.action === 'submit') {
        const {proposal_id, revision, work_id, ref, base_oid, head_oid} = value;
        state.proposals.set(key, {proposal_id, revision, work_id, ref, base_oid, head_oid, author: person.principal_id, reviewer: '', merged_revision: ''});
        return respond({status: 'accepted'});
      }
      const row = state.proposals.get(key);
      assert.ok(row);
      if (value.action === 'proposal') return respond({status: 'proposal', ...row});
      assert.equal(value.action, 'merge');
      const previous = state.mergeRequests.at(-1);
      state.mergeRequests.push(value);
      if (previous) assert.deepEqual(value, previous);
      row.merged_revision = '3';
      if (state.dropMergeResponse) { state.dropMergeResponse = false; return route.abort('failed'); }
      return respond({status: 'replayed', request_id: value.request_id, proposal_id: value.proposal_id, revision: value.revision, repository_revision: '3'});
    }
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
        resource_kind: value.operation.split('.')[0], container_id: value.payload.container_id ?? '', resource_revision: String(BigInt(value.expected_revision) + 1n),
        authority_epoch: value.authority_epoch, operation: value.operation, principal_id: person.principal_id,
        binding_id: person.binding_id, binding_revision: person.binding_revision, identity_ship: person.identity_ship,
        authentication: 'native-approved-browser/1', authentication_strength: 'native-approved-browser',
        session_audit_id: person.session_audit_id, runtime: 'isolated-fake', accepted_at_ms: '1790519400000', git_commit_oid: value.operation.startsWith('document.') ? 'd'.repeat(40) : ''};
      state.receipts.set(value.request_id, receipt);
      if (value.operation === 'work.delete') state.work = state.work.filter(row => row.resource_id !== value.resource_id);
      else if (value.operation === 'work.comment') {
        const row = state.work.find(item => item.resource_id === value.resource_id);
        assert.ok(row);
        assert.equal(value.expected_revision, row.resource_revision);
        row.resource_revision = receipt.resource_revision;
        const thread = state.comments.get(value.resource_id) ?? [];
        thread.push({body: value.payload.body, comment_revision: row.resource_revision,
          principal_id: person.principal_id, identity_ship: person.identity_ship, accepted_at_ms: receipt.accepted_at_ms});
        state.comments.set(value.resource_id, thread);
        row.comment_count = String(thread.length);
      } else if (value.operation === 'relation.create') {
        state.relations.push({kind: 'relation', resource_id: value.resource_id, project_id: value.project_id, container_id: '',
          resource_revision: receipt.resource_revision, title: 'Synthetic relation', ...value.payload});
      } else if (value.operation === 'relation.delete') {
        state.relations = state.relations.filter(link => link.resource_id !== value.resource_id);
      } else if (value.operation.startsWith('work.')) {
        const prior = state.work.find(row => row.resource_id === value.resource_id);
        const row = {...prior, ...value.payload, kind: 'work', resource_id: value.resource_id, project_id: value.project_id,
          resource_revision: receipt.resource_revision};
        if (value.operation === 'work.assign' || Object.hasOwn(value.payload, 'assignee_principal_id')) {
          row.assignee_display_name = state.assignees.find(person => person.principal_id === row.assignee_principal_id)?.display_name ?? '';
        }
        state.work = prior ? state.work.map(item => item.resource_id === row.resource_id ? row : item) : [...state.work, row];
      }
      if (state.invalidateCommands) state.sequence++;
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
    if (value.kind === 'assignees') rows = state.assignees;
    if (value.kind === 'relations') rows = state.relations;
    if (value.kind === 'search') rows = [...state.work, ...state.documents].filter(row => (row.title ?? '').toLowerCase().includes(value.search.toLowerCase()));
    if (value.kind === 'comments') rows = state.comments.get(value.resource_id) ?? [];
    if (value.kind === 'activity') rows = state.activity;
    if (value.kind === 'containers') rows = state.containers;
    if (value.kind === 'documents') rows = state.documents;
    if (value.kind === 'document') rows = state.documents.filter(row => row.resource_id === value.resource_id);
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
  await fixture(run, name.startsWith('code-')); report.checks.push({name, passed: true});
  console.log('PASS ' + name);
}
async function workForm(page) {
  await page.getByRole('button', {name: 'Work', exact: true}).click();
  await page.getByRole('button', {name: 'New work item', exact: true}).click();
  await page.getByRole('textbox', {name: 'Title', exact: true}).fill('Keep this local title');
  await page.getByRole('textbox', {name: 'Description', exact: true}).fill('Unsaved synthetic text');
}
try {
  await check('identity-entry-accepts-optional-tilde-and-rejects-malformed-input', async (page, state) => {
    state.failure = 'expired';
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    const input = page.getByRole('textbox', {name: 'Urbit ID', exact: true});
    for (const value of ['bus', '~bus', '  BUS  ', ' ~bus ']) {
      await input.fill(value);
      const response = page.waitForResponse(response => response.url().endsWith('/auth/start'));
      await page.getByRole('button', {name: 'Continue', exact: true}).click();
      await (await response).finished();
      const approval = page.getByRole('heading', {name: 'Approve on your identity ship', exact: true});
      await approval.waitFor();
      assert.equal(await approval.evaluate(node => node === document.activeElement), true);
      await page.getByRole('button', {name: 'Use a different ID', exact: true}).click();
      assert.equal(await input.evaluate(node => node === document.activeElement), true);
    }
    assert.deepEqual(state.authStarts, ['~bus', '~bus', '~bus', '~bus']);
    for (const value of ['~~bus', 'bus/palnet', 'bus palnet']) {
      await input.fill(value);
      await page.getByRole('button', {name: 'Continue', exact: true}).click();
      await page.getByRole('alert').waitFor();
      assert.equal(state.authStarts.length, 4, 'malformed input is rejected before an auth request');
    }
  });
  await check('unreachable-boot-retries-in-place-without-reloading-the-shell', async (page, state) => {
    state.unreachable = true;
    await page.reload();
    const retry = page.getByRole('button', {name: 'Retry connection', exact: true});
    await retry.waitFor();
    assert.doesNotMatch(await page.getByRole('alert').textContent(), /Check the receipt/u);
    await page.evaluate(() => { window.steadShellMarker = 'retained'; });
    state.unreachable = false;
    await retry.click();
    await page.getByRole('button', {name: /GARDEN.*Garden/u}).waitFor();
    assert.equal(await page.evaluate(() => window.steadShellMarker), 'retained');
    assert.equal(state.commands.length, 0);
  });
  await check('home-navigation-keeps-shell-and-guards-unsaved-work-while-disconnected', async (page, state) => {
    await workForm(page);
    await page.evaluate(() => { window.steadShellMarker = 'retained'; });
    state.unreachable = true;
    await page.getByRole('button', {name: 'Stead home', exact: true}).click();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'Keep this local title');
    assert.equal(await page.evaluate(() => window.steadShellMarker), 'retained');
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('button', {name: 'Discard changes', exact: true}).click();
    await page.getByRole('button', {name: 'Stead home', exact: true}).click();
    await page.getByRole('button', {name: 'Overview', exact: true}).filter({has: page.locator('span')}).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Overview', exact: true}).getAttribute('aria-current'), 'page');
    assert.equal(await page.getByRole('heading', {name: 'Garden', exact: true}).count(), 1);
    assert.equal(await page.evaluate(() => window.steadShellMarker), 'retained');
    assert.equal(state.commands.length, 0);
  });
  await check('code-survives-reopening-project', async page => {
    const code = page.getByRole('button', {name: 'Code', exact: true});
    const project = page.getByRole('button', {name: /GARDEN.*Garden/u});
    const clone = page.getByRole('textbox', {name: 'Clone URL', exact: true});
    assert.equal(await code.count(), 0);
    await page.getByRole('button', {name: 'Enable Git repository', exact: true}).click();
    await page.getByText('Clone', {exact: true}).click();
    await clone.waitFor();
    assert.equal(await clone.inputValue(), origin + '/stead/git/' + id(1) + '.git');
    await project.click();
    assert.equal(await clone.count(), 0);
    await code.click();
    await page.getByText('Clone', {exact: true}).click();
    await clone.waitFor();
  });
  await check('code-discovers-staged-snapshot-without-reloading', async (page, state) => {
    const code = page.getByRole('button', {name: 'Code', exact: true});
    const refresh = page.getByRole('button', {name: 'Refresh', exact: true});
    await page.getByRole('button', {name: 'Enable Git repository', exact: true}).waitFor();
    const head = Buffer.from('refs/heads/main').toString('hex');
    const pack = {status: 'external-staged', snapshot: 'a'.repeat(64), authority_epoch: '1',
      object_count: '3', head, refs: JSON.stringify({[head]: 'b'.repeat(40)})};
    state.pack = pack;
    await refresh.click();
    await code.click();
    await page.getByRole('heading', {name: 'Review Git snapshot', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Accept this snapshot', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Overview', exact: true}).click();
    state.pack = null;
    await refresh.click();
    await code.waitFor({state: 'hidden'});
    state.pack = pack;
    await page.getByRole('button', {name: /GARDEN.*Garden/u}).click();
    await code.waitFor();
    await code.click();
    await page.getByRole('button', {name: 'Accept this snapshot', exact: true}).click();
    await page.getByText('Clone', {exact: true}).click();
    await page.getByRole('button', {name: 'Create read credential', exact: true}).click();
    const credential = page.getByRole('textbox', {name: 'Git credential', exact: true});
    await credential.waitFor();
    assert.equal(await credential.inputValue(), 'c'.repeat(64));
    assert.equal(await page.getByRole('button', {name: 'Create write credential', exact: true}).count(), 0);
    await page.getByText('Manage credentials', {exact: true}).click();
    await page.getByRole('button', {name: 'Revoke credential', exact: true}).click();
    await credential.waitFor({state: 'hidden'});
  });
  await check('code-browses-accepted-branches-and-tags', async (page, state) => {
    const hex = text => Buffer.from(text).toString('hex');
    const main = hex('refs/heads/main');
    const topic = 'topic/' + 'long-branch-name-'.repeat(5) + 'preview';
    state.pack = {status: 'external', snapshot: 'a'.repeat(64), generation: '0', authority_epoch: '1', request_id: id(450),
      accepted_at_ms: '1800000000000', object_count: '8', head: main,
      refs: JSON.stringify({[main]: 'b'.repeat(40), [hex(`refs/heads/${topic}`)]: 'c'.repeat(40), [hex('refs/tags/v1.0')]: 'd'.repeat(40)})};
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await page.getByRole('button', {name: 'Code', exact: true}).click();
    const refPicker = page.getByRole('button', {name: /^Switch branch or tag\./u});
    const branchList = page.getByRole('list', {name: 'Branches', exact: true});
    const tip = page.locator('.repo-tip-actions > code');
    await refPicker.waitFor();
    assert.equal(await branchList.count(), 0, 'references are collapsed initially');
    assert.equal(await tip.getAttribute('title'), 'b'.repeat(40));
    await refPicker.click();
    await branchList.getByRole('button', {name: /main.*Default/u}).waitFor();
    const filter = page.getByRole('searchbox', {name: 'Find a branch', exact: true});
    assert.ok(await filter.evaluate(node => node === document.activeElement), 'opening picker focuses the filter');
    await filter.fill('preview');
    assert.equal(await branchList.getByRole('button').count(), 1);
    await filter.press('ArrowDown');
    const matching = branchList.getByRole('button', {name: new RegExp(topic, 'u')});
    assert.ok(await matching.evaluate(node => node === document.activeElement));
    await matching.press('Enter');
    assert.equal(await tip.getAttribute('title'), 'c'.repeat(40));
    assert.ok(await refPicker.evaluate(node => node === document.activeElement), 'selecting a ref returns focus');
    await refPicker.click();
    await page.getByRole('button', {name: 'Tags 1', exact: true}).click();
    const tag = page.getByRole('list', {name: 'Tags', exact: true}).getByRole('button', {name: /v1\.0/u});
    await tag.waitFor();
    assert.equal(await tip.getAttribute('title'), 'c'.repeat(40), 'switching tabs keeps the active branch');
    await tag.click();
    assert.equal(await tip.getAttribute('title'), 'd'.repeat(40));
    assert.match((await refPicker.getAttribute('aria-label')) ?? '', /Current tag: v1\.0/u);
    await page.getByText('Clone the repository to browse files and commit history.', {exact: true}).waitFor();
    const clone = page.getByRole('textbox', {name: 'Clone URL', exact: true});
    assert.ok(!(await clone.isVisible()));
    for (const width of [1240, 390, 320]) {
      await page.setViewportSize({width, height: 900});
      await refPicker.click();
      const switcher = page.getByRole('dialog', {name: 'Switch branch or tag', exact: true});
      const switcherBox = await switcher.boundingBox();
      assert.ok(switcherBox && switcherBox.x >= 0 && switcherBox.x + switcherBox.width <= width, 'reference picker fully visible');
      await page.screenshot({path: path.join(output, `repo-picker-${width}.png`), fullPage: true});
      await page.keyboard.press('Escape');
      await switcher.waitFor({state: 'hidden'});
      assert.ok(await refPicker.evaluate(node => node === document.activeElement));
      await page.getByText('Clone', {exact: true}).click();
      assert.equal(await clone.inputValue(), origin + '/stead/git/' + id(1) + '.git');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'clone panel stays inside the viewport');
      const panel = await page.locator('.repo-clone-panel').boundingBox();
      assert.ok(panel && panel.x >= 0 && panel.x + panel.width <= width, 'clone panel fully visible');
      await page.screenshot({path: path.join(output, `repository-${width}.png`), fullPage: true});
      await clone.focus();
      await page.keyboard.press('Escape');
      assert.ok(!(await clone.isVisible()));
      assert.ok(await page.getByText('Clone', {exact: true}).evaluate(node => node === document.activeElement));
    }
  });
  await check('code-browses-snapshot-files-and-fences-ref-switches', async (page, state) => {
    const hex = value => Buffer.from(value).toString('hex');
    const main = hex('refs/heads/main');
    const topic = hex('refs/heads/topic');
    const src = hex('src');
    const readme = hex('README.md');
    const script = hex('index.js');
    const binary = hex('sample.png');
    const link = hex('external');
    const longName = 'settings-' + 'abcdef'.repeat(25) + '.json';
    const raw = '<img src="/must-not-load" onerror="alert(1)">\n' + 'x'.repeat(650);
    const entry = (name, kind) => ({name, kind, oid: 'e'.repeat(40)});
    const oldSnapshot = 'a'.repeat(64);
    state.pack = {status: 'external', snapshot: oldSnapshot, generation: '0', authority_epoch: '1', request_id: id(451),
      accepted_at_ms: '1800000000000', object_count: '12', head: main, refs: JSON.stringify({[main]: 'b'.repeat(40), [topic]: 'c'.repeat(40)})};
    let deny = false;
    let stale = false;
    let delayedRead;
    let delayedReply;
    const waitForDelayedRead = new Promise(resolve => { delayedRead = resolve; });
    const releaseDelayedReply = new Promise(resolve => { delayedReply = resolve; });
    let transient = true;
    state.browseFixture = async ({ref, path, view}) => {
      if (deny) return {status: 404, fields: {error: 'denied_or_not_found'}};
      if (stale) return {status: 409, fields: {error: 'stale_selection'}};
      if (transient) return {status: 503, fields: {error: 'browse_unavailable'}};
      const commit = (ref === main ? 'b' : 'c').repeat(40);
      if (view === 'tree') {
        const entries = ref === topic ? [entry(hex('topic.md'), 'file')] : path.length > 0
          ? [entry(script, 'file')] : [entry(src, 'tree'), entry(readme, 'file'), entry(binary, 'file'),
            entry(link, 'symlink'), entry(hex(longName), 'file')];
        return {status: 200, fields: {commit, entries, truncated: false}};
      }
      if (path.at(-1) === binary) return {status: 200, fields: {commit, bytes: 32, preview: 'binary'}};
      if (path.at(-1) === readme) { delayedRead(); await releaseDelayedReply; }
      const text = path.at(-1) === readme ? 'Obsolete branch text' : raw;
      return {status: 200, fields: {commit, bytes: Buffer.byteLength(text), preview: 'text', text}};
    };
    try {
      await page.getByRole('button', {name: 'Refresh', exact: true}).click();
      await page.getByRole('button', {name: 'Code', exact: true}).click();
      const folder = page.getByRole('list', {name: 'Folder contents', exact: true});
      const files = page.getByRole('region', {name: 'Files', exact: true});
      await page.setViewportSize({width: 1240, height: 900});
      await files.getByRole('alert').getByText('Couldn’t load this folder.').waitFor();
      transient = false;
      await files.getByRole('button', {name: 'Retry', exact: true}).click();
      await folder.waitFor();
      await page.screenshot({path: path.join(output, 'repo-folder-1240.png'), fullPage: true});
      await folder.getByRole('button', {name: 'src Folder', exact: true}).focus();
      await page.keyboard.press('Enter');
      await folder.getByRole('button', {name: 'index.js', exact: true}).click();
      const preview = files.locator('pre');
      await preview.waitFor();
      assert.equal(await preview.textContent(), raw);
      assert.equal(await preview.locator('img').count(), 0);
      assert.deepEqual(state.browseRequests.at(-1).path, [src, script]);
      assert.equal(state.browseRequests.at(-1).snapshot, oldSnapshot);
      assert.ok(await page.getByRole('heading', {name: 'Files', exact: true}).evaluate(node => node === document.activeElement));
      await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', {
        configurable: true, value: {writeText(value) { window.copiedValue = value; return Promise.resolve(); }},
      }));
      await files.getByRole('button', {name: 'Copy path', exact: true}).click();
      assert.equal(await page.evaluate(() => window.copiedValue), 'src/index.js');
      await files.getByRole('button', {name: 'Copy contents', exact: true}).click();
      assert.equal(await page.evaluate(() => window.copiedValue), raw);
      for (const width of [1240, 390, 320]) {
        await page.setViewportSize({width, height: 900});
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `file preview fits at ${width}px`);
        await page.screenshot({path: path.join(output, `repo-file-preview-${width}.png`), fullPage: true});
      }
      await page.getByRole('button', {name: 'Back to folder', exact: true}).click();
      const scriptEntry = folder.getByRole('button', {name: 'index.js', exact: true});
      await scriptEntry.waitFor();
      assert.ok(await scriptEntry.evaluate(node => node === document.activeElement), 'returning from a file restores focus');
      await files.getByRole('button', {name: 'Parent folder', exact: true}).click();
      const srcEntry = folder.getByRole('button', {name: 'src Folder', exact: true});
      await srcEntry.waitFor();
      assert.ok(await srcEntry.evaluate(node => node === document.activeElement), 'returning to root restores folder focus');
      await folder.getByRole('button', {name: 'sample.png', exact: true}).click();
      await files.getByText('Binary file. Clone to open it.', {exact: true}).waitFor();
      await page.getByRole('button', {name: 'Back to folder', exact: true}).click();
      assert.equal(await folder.getByRole('button', {name: /external/u}).count(), 0);
      await folder.getByText(longName, {exact: true}).waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'long filename fits at 320px');
      await page.screenshot({path: path.join(output, 'repo-folder-320.png'), fullPage: true});
      const canceledPreview = page.waitForEvent('requestfailed', {predicate: request =>
        new URL(request.url()).pathname === '/stead/api/code/browse' && request.postDataJSON().path.at(-1) === readme});
      await folder.getByRole('button', {name: 'README.md', exact: true}).click();
      await waitForDelayedRead;
      await page.getByRole('button', {name: /^Switch branch or tag\./u}).click();
      await page.getByRole('button', {name: 'Tags 0', exact: true}).click();
      await page.getByText('No tags yet.', {exact: true}).waitFor();
      assert.equal(state.browseRequests.at(-1).ref, main);
      await page.getByRole('button', {name: 'Branches 2', exact: true}).click();
      await page.getByRole('list', {name: 'Branches', exact: true}).getByRole('button', {name: /topic/u}).click();
      await canceledPreview;
      await folder.getByRole('button', {name: 'topic.md', exact: true}).waitFor();
      delayedReply();
      assert.equal(await files.getByText('Obsolete branch text', {exact: true}).count(), 0);
      assert.equal(await preview.count(), 0);
      stale = true;
      await folder.getByRole('button', {name: 'topic.md', exact: true}).click();
      await files.getByRole('alert').getByText('The accepted snapshot changed.').waitFor();
      assert.equal(await files.getByRole('navigation', {name: 'Repository path'}).count(), 0);
      stale = false;
      deny = true;
      state.pack = {...state.pack, snapshot: 'd'.repeat(64), generation: '1'};
      await files.getByRole('button', {name: 'Refresh files', exact: true}).click();
      await files.getByRole('alert').getByText('These repository files are unavailable.').waitFor();
      assert.ok(await page.getByRole('heading', {name: 'Repository', exact: true}).evaluate(node => node === document.activeElement));
      assert.notEqual(state.browseRequests.at(-1).snapshot, oldSnapshot);
      assert.equal(await folder.count(), 0);
      assert.equal(await preview.count(), 0);
    } finally { delayedReply(); }
  });
  await check('code-development-work-branch-and-review', async (page, state) => {
    const hex = text => Buffer.from(text).toString('hex');
    const work = {kind: 'work', resource_id: id(57), title: 'Ship the welcome page', resource_revision: '1',
      status: 'todo', priority: 'medium', type: 'task'};
    const branch = `work/${work.resource_id}`;
    const targetRef = 'refs/heads/main';
    const sourceRef = `refs/heads/${branch}`;
    const main = hex(targetRef);
    const reference = hex(sourceRef);
    const base = 'b'.repeat(40);
    const head = 'c'.repeat(40);
    state.work = [work]; state.externalWritable = true;
    state.pack = {status: 'external', snapshot: 'a'.repeat(64), generation: '0', authority_epoch: '1', request_id: id(452),
      accepted_at_ms: '1800000000000', object_count: '7', head: main, refs: JSON.stringify({[main]: base})};
    const modifiedPath = hex('welcome.md');
    state.changesFixture = async ({view, path}) => view === 'files'
      ? {status: 200, fields: {entries: [{path: modifiedPath, status: 'M', old_mode: '100644', new_mode: '100644'}], truncated: false}}
      : path === modifiedPath ? {status: 200, fields: {preview: 'text', text: '-Welcome\n+Welcome aboard\n', sanitized: false}}
        : {status: 404, fields: {error: 'denied_or_not_found'}};
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', {
      configurable: true, value: {writeText(value) { window.copiedValue = value; return Promise.resolve(); }},
    }));
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.getByRole('button', {name: work.title, exact: true}).click();
    const development = page.getByRole('region', {name: 'Development', exact: true});
    await development.getByText('No matching branch in the accepted Git snapshot.', {exact: true}).waitFor();
    await development.getByRole('button', {name: 'Copy branch name', exact: true}).click();
    assert.equal(await page.evaluate(() => window.copiedValue), branch);
    await development.getByText('Branch commands', {exact: true}).click();
    await development.getByRole('button', {name: 'Copy create command', exact: true}).click();
    assert.equal(await page.evaluate(() => window.copiedValue), `git switch -c ${branch} ${base}`);
    await development.getByRole('button', {name: 'Copy push command', exact: true}).click();
    assert.equal(await page.evaluate(() => window.copiedValue), `git push -u origin ${branch}`);
    assert.equal(await development.getByRole('button', {name: 'View branch', exact: true}).count(), 0);
    assert.equal(state.commands.length, 0);
    assert.equal(state.externalRequests.some(row => row.action === 'external-submit'), false);
    state.pack = {...state.pack, snapshot: 'd'.repeat(64), generation: '1', refs: JSON.stringify({[main]: base, [reference]: base})};
    await development.getByRole('button', {name: 'Check for branch', exact: true}).click();
    await development.getByText('Branch is in the accepted Git snapshot.', {exact: true}).waitFor();
    await development.getByText('Push a change to this branch to start a review.', {exact: true}).waitFor();
    assert.equal(await development.getByRole('button', {name: 'Start change review', exact: true}).count(), 0);
    state.pack = {...state.pack, snapshot: 'e'.repeat(64), generation: '2', refs: JSON.stringify({[main]: base, [reference]: head})};
    await development.getByRole('button', {name: 'Check for branch', exact: true}).click();
    await development.getByRole('button', {name: 'Start change review', exact: true}).waitFor();
    await development.getByRole('button', {name: 'View branch', exact: true}).click();
    await page.getByRole('button', {name: `Switch branch or tag. Current branch: ${branch}`, exact: true}).waitFor();
    assert.equal(page.url().includes(branch), false);
    await page.getByRole('button', {name: 'Return to work item', exact: true}).click();
    await development.getByRole('button', {name: 'Start change review', exact: true}).click();
    const source = page.getByLabel('Source branch', {exact: true});
    await source.waitFor();
    assert.equal(await source.inputValue(), reference);
    assert.equal(await page.getByLabel('Work item', {exact: true}).inputValue(), work.resource_id);
    assert.equal(await page.getByLabel('Work item', {exact: true}).locator('option:checked').textContent(), work.title);
    await page.setViewportSize({width: 320, height: 900});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({path: path.join(output, 'repo-work-development-320.png'), fullPage: true});
    await page.getByRole('button', {name: 'Submit proposal', exact: true}).click();
    const exact = page.getByRole('region', {name: 'Exact proposal', exact: true});
    await exact.getByRole('button', {name: 'View work item', exact: true}).waitFor();
    const submitted = state.externalRequests.findLast(row => row.action === 'external-submit');
    assert.deepEqual({work: submitted.work_id, source: submitted.source_ref, target: submitted.ref,
      head: submitted.head_oid, base: submitted.base_oid, snapshot: submitted.base_snapshot, generation: submitted.generation},
      {work: work.resource_id, source: sourceRef, target: targetRef, head, base, snapshot: 'e'.repeat(64), generation: '2'});
    assert.equal(state.commands.length, 0);
    const changes = exact.getByRole('region', {name: 'Exact revision changes', exact: true});
    await changes.getByRole('button', {name: 'welcome.md Modified', exact: true}).click();
    assert.equal(await changes.getByLabel('Exact file patch').textContent(), '-Welcome\n+Welcome aboard\n');
    assert.equal(state.changesRequests.at(-1).proposal_id, submitted.proposal_id);
    assert.equal(state.changesRequests.at(-1).revision, submitted.revision);
    await exact.getByRole('button', {name: 'View work item', exact: true}).click();
    await page.getByRole('region', {name: 'Linked code changes', exact: true}).getByRole('button', {
      name: new RegExp(`work/${work.resource_id}.*Awaiting review`, 'u'),
    }).waitFor();
    await development.getByRole('button', {name: 'Start change review', exact: true}).click();
    await exact.getByRole('button', {name: 'View work item', exact: true}).waitFor();
    await changes.getByRole('button', {name: 'welcome.md Modified', exact: true}).waitFor();
    assert.equal(state.changesRequests.at(-1).proposal_id, submitted.proposal_id);
    assert.equal(await page.getByRole('button', {name: 'Submit proposal', exact: true}).count(), 0);
    assert.equal(state.externalRequests.filter(row => row.action === 'external-submit').length, 1);
    await exact.getByRole('button', {name: 'View work item', exact: true}).click();
    await development.getByRole('button', {name: 'View branch', exact: true}).waitFor();
    const laterHead = 'f'.repeat(40);
    state.pack = {...state.pack, snapshot: 'f'.repeat(64), generation: '3', refs: JSON.stringify({[main]: base, [reference]: laterHead})};
    await development.getByRole('button', {name: 'Check for branch', exact: true}).click();
    await development.getByRole('button', {name: 'Start change review', exact: true}).click();
    await source.waitFor();
    assert.equal(await source.inputValue(), reference);
    assert.equal(await page.getByLabel('Work item', {exact: true}).inputValue(), work.resource_id);
    assert.equal(await exact.count(), 0);
    await page.getByRole('button', {name: 'Submit proposal', exact: true}).click();
    const proposals = page.getByRole('list', {name: 'Change proposals', exact: true});
    await proposals.getByRole('button', {name: /Snapshot changed · Revision 1.*Target branch main.*Proposed commit c{12}/u}).waitFor();
    await proposals.getByRole('button', {name: /Awaiting review · Revision 1.*Target branch main.*Proposed commit f{12}/u}).waitFor();
    assert.equal(await proposals.getByRole('button').count(), 2, 'both revisions retain their own commit trail');
    assert.equal(state.externalRequests.filter(row => row.action === 'external-submit').length, 2);
    await exact.getByRole('button', {name: 'View work item', exact: true}).click();
    await development.getByRole('button', {name: 'View branch', exact: true}).waitFor();
    state.externalWritable = false;
    await development.getByRole('button', {name: 'Check for branch', exact: true}).click();
    await development.getByRole('button', {name: 'View branch', exact: true}).waitFor();
    assert.equal(await development.getByRole('button', {name: 'Start change review', exact: true}).count(), 0);
    state.pack = {...state.pack, status: 'external-staged'};
    await development.getByRole('button', {name: 'Check for branch', exact: true}).click();
    await development.getByText('The accepted Git snapshot is unavailable.', {exact: true}).waitFor();
    assert.equal(await development.getByRole('button', {name: 'View branch', exact: true}).count(), 0);
  });
  await check('code-proposal-form-and-merge-retry-survive-view-change', async (page, state) => {
    state.work = [{kind: 'work', resource_id: id(50), title: 'Review the source', resource_revision: '1'}];
    await page.getByRole('button', {name: 'Enable Git repository', exact: true}).click();
    await page.getByRole('button', {name: 'New proposal', exact: true}).click();
    await page.getByLabel('Work item', {exact: true}).selectOption({label: state.work[0].title});
    await page.getByLabel('Current target commit', {exact: true}).fill('a'.repeat(40));
    await page.getByLabel('Proposed commit', {exact: true}).fill('b'.repeat(40));
    await page.getByRole('button', {name: 'Submit proposal', exact: true}).click();
    await page.getByText('Awaiting review.', {exact: true}).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Approve this revision', exact: true}).count(), 0);

    const proposal = id(901);
    state.proposals.set(proposal + '/1', {proposal_id: proposal, revision: '1', work_id: id(50), ref: 'refs/heads/main',
      base_oid: 'a'.repeat(40), head_oid: 'b'.repeat(40), author: id(902), reviewer: id(903), merged_revision: ''});
    await page.getByLabel('Proposal ID', {exact: true}).fill(proposal);
    await page.getByRole('button', {name: 'Open proposal', exact: true}).click();
    await page.getByText('Approved for this exact revision.', {exact: true}).waitFor();
    state.dropMergeResponse = true;
    await page.getByRole('button', {name: 'Merge this revision', exact: true}).click();
    await page.getByRole('alert').getByText(/The merge is awaiting confirmation/u).waitFor();
    await page.getByRole('button', {name: 'Overview', exact: true}).click();
    await page.getByRole('button', {name: 'Code', exact: true}).click();
    await page.getByRole('button', {name: 'Retry this merge', exact: true}).click();
    await page.getByRole('status').filter({hasText: 'Merged at repository revision 3.'}).waitFor();
    assert.equal(state.mergeRequests.length, 2);
    assert.deepEqual(state.mergeRequests[0], state.mergeRequests[1]);
    await page.setViewportSize({width: 320, height: 900});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  });
  await check('code-external-review-and-signed-merge', async (page, state, consoleErrors) => {
    const code = page.getByRole('button', {name: 'Code', exact: true});
    const hex = text => Buffer.from(text).toString('hex');
    const base = 'b'.repeat(40); const head = 'c'.repeat(40); const initial = 'a'.repeat(64);
    const targetRef = 'refs/heads/main'; const sourceRef = 'refs/heads/feature';
    const work = {kind: 'work', resource_id: id(50), title: 'Review the change', resource_revision: '1'};
    state.work = [work]; state.externalWritable = true;
    state.pack = {status: 'external', snapshot: initial, generation: '0', generation_limit: '64', authority_epoch: '1', request_id: id(450), accepted_at_ms: '1800000000000',
      object_count: '6', head: hex(targetRef), refs: JSON.stringify({[hex(targetRef)]: base, [hex(sourceRef)]: head})};
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await code.click();
    const panel = page.getByRole('heading', {name: 'Change review', exact: true});
    await panel.waitFor();
    await page.getByText('No proposals to review yet.', {exact: true}).waitFor();
    const cloneMenu = page.getByText('Clone', {exact: true});
    await cloneMenu.click();
    await page.getByRole('button', {name: 'Create write credential', exact: true}).waitFor();
    await cloneMenu.click();
    const prepareDraft = async () => {
      await page.getByRole('button', {name: 'New proposal', exact: true}).click();
      await page.getByLabel('Work item', {exact: true}).selectOption({label: work.title});
      await page.getByLabel('Source branch', {exact: true}).selectOption({label: 'feature'});
    };
    await prepareDraft();
    const unrelated = {...state.pack, generation: '1', snapshot: 'e'.repeat(64),
      refs: JSON.stringify({...JSON.parse(state.pack.refs), [hex('refs/heads/another')]: 'f'.repeat(40)})};
    state.pack = unrelated;
    await page.getByRole('button', {name: 'Submit proposal', exact: true}).click();
    await page.getByRole('alert').getByText(/Git snapshot changed/u).waitFor();
    assert.equal(state.externalReviews.size, 0);
    const attempted = state.externalRequests.find(row => row.action === 'external-submit');
    assert.equal(attempted.base_snapshot, initial); assert.equal(attempted.generation, '0');
    await page.getByRole('button', {name: 'Refresh snapshot', exact: true}).click();
    await page.getByRole('alert').getByText(/Cancel this draft/u).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Submit proposal', exact: true}).isEnabled(), false);
    await page.getByRole('button', {name: 'Cancel', exact: true}).click();
    await prepareDraft();
    await page.getByRole('button', {name: 'Submit proposal', exact: true}).click();
    await page.getByText('Awaiting review.', {exact: true}).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Approve this revision', exact: true}).count(), 0);
    const submitted = state.externalRequests.findLast(row => row.action === 'external-submit');
    assert.equal(submitted.base_snapshot, unrelated.snapshot); assert.equal(submitted.generation, unrelated.generation);
    assert.equal(submitted.base_oid, base); assert.equal(submitted.head_oid, head);
    assert.equal(submitted.ref, targetRef); assert.equal(submitted.source_ref, sourceRef);

    const reviewed = {...state.externalReviews.get(submitted.proposal_id), proposal_id: id(542), author: id(777)};
    state.externalReviews.set(reviewed.proposal_id, reviewed);
    const open = async () => {
      await page.getByText('Open by proposal ID', {exact: true}).click();
      await page.getByLabel('Proposal ID', {exact: true}).fill(reviewed.proposal_id);
      await page.getByRole('button', {name: 'Open proposal', exact: true}).click();
    };
    await page.getByRole('button', {name: 'Refresh snapshot', exact: true}).click();
    const list = page.getByRole('list', {name: 'Change proposals'});
    await list.getByRole('button').nth(1).click();
    await page.getByRole('button', {name: 'Approve this revision', exact: true}).click();
    await page.getByText('Approved.', {exact: true}).waitFor();
    await page.getByText('Merge with signed proof', {exact: true}).click();
    const merge = page.getByRole('button', {name: 'Merge this revision', exact: true});
    assert.equal(await merge.count(), 0);
    const download = async () => {
      const result = page.waitForEvent('download');
      await page.getByRole('button', {name: 'Download proof request', exact: true}).click();
      return JSON.parse(await readFile(await (await result).path(), 'utf8'));
    };
    const downloaded = await download();
    assert.deepEqual(await download(), downloaded);
    assert.equal(downloaded.protocol, 'stead.git-pack-review-request/1');
    assert.equal(downloaded.proposal_id, reviewed.proposal_id);
    assert.equal(downloaded.base_oid, base); assert.equal(downloaded.head_oid, head);
    const evidence = {protocol: 'stead.git-pack-reviewed-proof/1', base_snapshot: unrelated.snapshot, request_id: downloaded.request_id,
      scope: {home: '~zod', authority_epoch: '1', project_id: id(1), repository_id: id(1)},
      proposal_id: reviewed.proposal_id, revision: reviewed.revision, work_id: work.resource_id,
      source: hex(sourceRef), target: hex(targetRef), base_oid: base, head_oid: head, generation: reviewed.generation,
      candidate_snapshot: 'd'.repeat(64)};
    const upload = candidate => page.getByLabel('Signed proof file', {exact: true}).setInputFiles({name: 'proof.json',
      mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({proof: canonical(candidate) + '\n',
        worker_generation: '1', worker_signature: 'a'.repeat(128)}))});
    await upload({...evidence, head_oid: base});
    await page.getByRole('alert').getByText(/does not match/u).waitFor();
    await upload(evidence); await merge.waitFor();
    assert.equal(state.externalRequests.filter(row => row.action === 'external-merge').length, 0);

    state.externalWritable = false;
    await page.getByRole('button', {name: 'Refresh snapshot', exact: true}).click();
    await merge.waitFor({state: 'hidden'});
    await cloneMenu.click();
    assert.equal(await page.getByRole('button', {name: 'Create write credential', exact: true}).count(), 0);
    await cloneMenu.click();
    state.externalWritable = true;
    await page.getByRole('button', {name: 'Refresh snapshot', exact: true}).click();
    await merge.waitFor();

    for (const [width, height] of [[1440, 1000], [390, 900], [320, 900]]) {
      await page.setViewportSize({width, height});
      await panel.scrollIntoViewIfNeeded();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'review has no horizontal overflow');
      await page.screenshot({path: path.join(output, `external-review-${width}.png`), fullPage: true});
    }
    state.dropMergeResponse = true;
    await merge.click();
    await page.getByRole('alert').getByText(/did not confirm the merge/u).waitFor();
    state.pack = {...state.pack, generation: '64'};
    state.externalWritable = false;
    await page.getByRole('button', {name: 'Overview', exact: true}).click();
    await code.click();
    await page.getByText(/reached its 64 update limit/u).waitFor();
    await page.getByText('Clone', {exact: true}).click();
    await page.getByRole('button', {name: 'Create read credential', exact: true}).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Create write credential', exact: true}).count(), 0);
    assert.equal(await page.getByRole('button', {name: 'New proposal', exact: true}).count(), 0);
    assert.equal(state.externalRequests.filter(row => row.action === 'external-merge').length, 1);
    await page.getByRole('button', {name: 'Retry this merge', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Stop retrying', exact: true}).click();
    await page.getByRole('button', {name: 'Keep checking', exact: true}).click();
    const read = state.externalReviews.get(reviewed.proposal_id);
    const initialRequest = read.merged_request_id;
    read.merged_request_id = id(999);
    await page.getByRole('button', {name: 'Check saved status', exact: true}).click();
    await page.getByRole('status').filter({hasText: 'The Home did not confirm this exact merge.'}).waitFor();
    assert.equal(await page.getByRole('button', {name: 'Retry this merge', exact: true}).isEnabled(), true);
    read.merged_request_id = initialRequest;
    await page.getByRole('button', {name: 'Check saved status', exact: true}).click();
    await page.getByRole('status').filter({hasText: 'The Home confirmed the merge.'}).waitFor();
    await open();
    await page.getByText('Merged.', {exact: true}).waitFor();
    assert.equal(await page.getByLabel('Snapshot SHA-256', {exact: true}).inputValue(), evidence.candidate_snapshot);
    assert.equal(state.externalRequests.filter(row => row.action === 'external-merge').length, 1);
    assert.deepEqual(consoleErrors, []);
  });
  await check('authentication-reuses-validated-identity-and-opens-before-one-snapshot', async (page, state) => {
    assert.equal(state.requests.filter(row => row.kind === 'identity').length, 1);
    assert.deepEqual(state.requests.filter(row => row.path === '/stead/api/query' && row.kind === 'project').map(row => row.path), ['/stead/api/query']);
    const open = state.requests.findIndex(row => row.action === 'open');
    const snapshot = state.requests.findIndex(row => row.path === '/stead/api/query' && row.kind === 'project');
    assert.ok(open >= 0 && snapshot > open);
  });
  await check('saved-snapshot-coalesces-own-invalidation-but-keeps-remote-refresh-and-revocation', async (page, state) => {
    await workForm(page);
    await page.locator('#project-content[data-live-updates="connected"]').waitFor();
    state.invalidateCommands = true;
    const reads = () => state.requests.filter(row => row.path === '/stead/api/query').length;
    const beforeSave = reads();
    await page.getByRole('button', {name: 'Save at home', exact: true}).click();
    await page.getByRole('heading', {name: 'Keep this local title', exact: true}).waitFor();
    const afterSave = beforeSave + 2;
    assert.equal(reads(), afterSave, 'save reads metadata and Work exactly once');
    for (let n = 0; n < 2; n++) {
      const response = await page.waitForResponse(response => response.url().endsWith('/stead/api/updates') && response.request().postDataJSON()?.action === 'poll');
      await response.finished();
    }
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(reads(), afterSave, 'the accepted snapshot already includes this invalidation');
    state.work[0].title = 'Changed by another member'; state.sequence++;
    await page.getByRole('heading', {name: 'Changed by another member', exact: true}).waitFor();
    assert.equal(reads(), afterSave + 2, 'a new generation still reads metadata and Work');
    state.denied = true;
    await page.getByRole('heading', {name: 'Garden', exact: true}).waitFor({state: 'detached'});
    assert.equal(await page.getByRole('heading', {name: 'Changed by another member', exact: true}).count(), 0);
  });
  await check('dense-markdown-preview-keeps-full-inert-text-and-bounded-dom', async (page, state) => {
    const body = '<script>window.steadPreviewExecuted=true</script>\n' + '\n'.repeat(31000) + 'Tokyo 東京';
    const markdown = `---\nid: ${id(301)}\ntype: page\nstate: draft\n---\n` + body;
    state.containers = [{kind: 'container', resource_id: id(200), container_id: id(200), title: 'Private notes', visibility: 'private', container_head: ''}];
    state.documents = [{kind: 'document', resource_id: id(301), container_id: id(200), title: 'Dense note', resource_revision: '1', markdown}];
    await page.getByRole('button', {name: 'Docs', exact: true}).click();
    await page.getByLabel('Collection', {exact: true}).selectOption(id(200));
    await page.getByRole('button', {name: 'Open page', exact: true}).click();
    const editor = page.getByRole('textbox', {name: 'Markdown source', exact: true});
    const preview = page.getByRole('article', {name: 'Document content', exact: true});
    await preview.locator('pre').waitFor();
    assert.equal(await editor.inputValue(), body);
    assert.equal(await preview.textContent(), body);
    assert.ok(await preview.locator('*').count() < 1024);
    assert.equal(await preview.locator('script,img,iframe,object,embed').count(), 0);
    assert.equal(await page.evaluate(() => window.steadPreviewExecuted), undefined);
    await editor.fill(body + ' edited');
    await page.waitForFunction(() => document.querySelector('article.markdown')?.textContent.endsWith(' edited'));
    assert.equal(await editor.inputValue(), body + ' edited');
    assert.equal(state.commands.length, 0, 'rendering does not save or normalize the draft');
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('button', {name: 'Discard changes', exact: true}).click();
    state.documents = [{...state.documents[0], resource_id: id(302), title: 'Second note', markdown: `---\nid: ${id(302)}\ntype: page\nstate: draft\n---\n# Second body`}];
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await page.getByRole('button', {name: 'Open page', exact: true}).click();
    await preview.getByRole('heading', {name: 'Second body', exact: true}).waitFor();
    assert.equal((await preview.textContent()).includes('steadPreviewExecuted'), false);
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
    await page.getByRole('button', {name: 'Continue', exact: true}).waitFor();
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
    await page.getByText('Session resumed.', {exact: true}).waitFor();
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
    await page.getByRole('button', {name: 'Page item 21', exact: true}).click();
    await page.getByRole('button', {name: 'Edit work item', exact: true}).click();
    await page.getByRole('heading', {name: 'Edit work item', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Close', exact: true}).click();
    await page.waitForTimeout(2500);
    assert.equal(await page.getByRole('heading', {name: 'Page item 1', exact: true}).count(), 0);
    assert.equal(await page.locator('.work-row').getByRole('heading', {name: 'Page item 21', exact: true}).count(), 1);
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
      await press(page.getByRole('button', {name: 'Discard changes…', exact: true}));
      await press(page.getByRole('button', {name: 'Discard changes', exact: true}));
      await press(page.getByRole('button', {name: 'Work', exact: true}));
      await press(page.getByRole('button', {name: 'New work item', exact: true}));
      await text('Title', 'Keyboard-created work'); await text('Description', 'Tokyo 東京 — Zoë');
      await press(page.getByRole('button', {name: 'Save at home', exact: true}));
      await page.getByRole('heading', {name: 'Keyboard-created work', exact: true}).waitFor();
      assert.equal(state.commands.length, 1);
      console.log('Keyboard tab focus before selection: ' + before);
    } finally { await other.close(); }
  });
  await check('first-project-draft-can-be-discarded-before-project-selection', async (page, state) => {
    await page.reload();
    const newProject = page.getByRole('button', {name: '＋ New project', exact: true});
    await newProject.click();
    await page.getByRole('textbox', {name: 'Title', exact: true}).fill('Unsent first project');
    await page.getByRole('textbox', {name: 'Project key', exact: true}).fill('UNSENT');
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('alertdialog', {name: 'Discard unsaved changes?', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Keep editing', exact: true}).click();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'Unsent first project');
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('button', {name: 'Discard changes', exact: true}).click();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).count(), 0);
    assert.equal(state.commands.length, 0);
    await newProject.click();
    await page.getByRole('button', {name: 'Close', exact: true}).click();
    assert.equal(await page.getByRole('alertdialog').count(), 0);
  });
  await check('work-title-opens-reader-details-without-write-actions', async (page, state) => {
    state.project.role = 'reader';
    state.work = [{kind: 'work', resource_id: id(601), title: 'Read the full context', description: 'A longer explanation available to every project reader.', resource_revision: '3', status: 'in_progress', type: 'task', priority: 'high'}];
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    const title = page.getByRole('button', {name: 'Read the full context', exact: true});
    await title.focus(); await page.keyboard.press('Enter');
    const panel = page.locator('#work-detail-panel');
    await panel.getByRole('heading', {name: 'Read the full context', exact: true}).waitFor();
    await page.waitForFunction(() => document.activeElement?.id === 'work-detail-title');
    assert.equal(await panel.locator('.work-description').textContent(), state.work[0].description);
    assert.equal(await panel.getByRole('textbox').count(), 0);
    assert.equal(await page.getByRole('button', {name: 'Edit work item', exact: true}).count(), 0);
    assert.equal(await page.getByRole('button', {name: 'Delete', exact: true}).count(), 0);
    await title.click({button: 'right'});
    const menu = page.getByRole('menu', {name: 'Work item actions'});
    assert.equal(await menu.getByRole('menuitem').count(), 2);
    assert.equal(await menu.getByRole('menuitem', {name: 'Open details'}).count(), 1);
    assert.equal(await menu.getByRole('menuitem', {name: 'Copy work item link'}).count(), 1);
    await page.keyboard.press('Escape');
    assert.match(await panel.textContent(), /Revision 3 · Read only/u);
    await panel.getByRole('button', {name: 'Close', exact: true}).click();
    await page.waitForFunction(() => document.activeElement?.textContent === 'Read the full context');
    assert.equal(state.commands.length, 0);
  });
  await check('work-details-dirty-close-and-keyboard-secondary-delete', async (page, state) => {
    const title = 'Make the next step clear';
    state.work = [{kind: 'work', resource_id: id(602), title, description: 'Keep important actions close to the work.', resource_revision: '1', status: 'todo', type: 'task', priority: 'medium'}];
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.getByRole('button', {name: title, exact: true}).click();
    await page.getByRole('button', {name: 'Edit work item', exact: true}).click();
    await page.getByRole('textbox', {name: 'Title', exact: true}).fill('My unsaved change');
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('button', {name: 'Keep editing', exact: true}).click();
    assert.equal(await page.getByRole('textbox', {name: 'Title', exact: true}).inputValue(), 'My unsaved change');
    const more = page.locator('summary[aria-label="More work actions"]');
    await more.focus(); await page.keyboard.press('Enter');
    await page.getByRole('button', {name: 'Compare current saved revision', exact: true}).click();
    await page.getByRole('heading', {name: 'Current saved revision 1', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Close comparison', exact: true}).click();
    await page.screenshot({path: path.join(output, 'polish-work-desktop.png'), fullPage: true});
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('button', {name: 'Discard changes', exact: true}).click();
    assert.equal(state.commands.length, 0);
    await page.locator('#work-detail-panel').getByRole('heading', {name: title, exact: true}).waitFor();
    await page.getByRole('button', {name: 'Edit work item', exact: true}).click();
    await page.getByRole('button', {name: 'Close', exact: true}).click();
    await page.waitForFunction(() => document.activeElement?.textContent === 'Make the next step clear');
    assert.equal(await page.getByRole('alertdialog').count(), 0);
    const menu = page.getByRole('button', {name: 'Actions for Make the next step clear'});
    await menu.focus(); await page.keyboard.press('Enter');
    await page.keyboard.press('End');
    assert.equal(await page.getByRole('menuitem', {name: 'Delete…', exact: true}).evaluate(element => element === document.activeElement), true);
    await page.keyboard.press('Escape');
    assert.equal(await menu.evaluate(element => element === document.activeElement), true);
    await page.keyboard.press('Enter'); await page.keyboard.press('End'); await page.keyboard.press('Enter');
    await page.getByRole('heading', {name: 'Delete this work item?', exact: true}).waitFor();
    assert.equal(state.commands.length, 0, 'opening confirmation does not delete');
    await page.getByRole('button', {name: 'Keep it', exact: true}).click();
    await menu.click(); await page.getByRole('menuitem', {name: 'Delete…', exact: true}).click();
    await page.getByRole('button', {name: 'Confirm deletion', exact: true}).click();
    await page.locator('.work-row').getByRole('button', {name: title, exact: true}).waitFor({state: 'detached'});
    await page.locator('#work-detail-panel').waitFor({state: 'detached'});
    assert.equal(state.commands.length, 1); assert.equal(state.commands[0].operation, 'work.delete');
  });
  await check('work-inline-properties-and-project-assignment', async (page, state) => {
    const title = 'Prepare the garden';
    const description = 'Preserve this full description when changing one property.';
    const item = id(607);
    const taylor = {principal_id: id(109), display_name: 'Taylor', identity_ship: '~nec'};
    state.work = [{kind: 'work', resource_id: item, title, description, resource_revision: '1', status: 'todo', type: 'task', priority: 'medium'}];
    state.assignees = [person, taylor];
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    const row = page.locator('.work-row').filter({hasText: title});
    await row.getByRole('button', {name: /Set status/}).click();
    const statusMenu = page.getByRole('menu', {name: 'Set status'});
    const positions = await statusMenu.locator('button > span:nth-child(2)').evaluateAll(labels =>
      labels.map(label => label.getBoundingClientRect().left));
    assert.equal(new Set(positions).size, 1, 'status labels use one left edge');
    await page.keyboard.press('ArrowDown'); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
    await row.getByRole('button', {name: /Set status.*In progress/}).waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('data-work-control') === 'status');
    assert.equal(state.commands[0].operation, 'work.update');
    assert.equal(state.commands[0].expected_revision, '1');
    assert.equal(state.commands[0].payload.description, description);
    await row.click({button: 'right'});
    await page.getByRole('menuitem', {name: 'Assign to'}).click();
    const filter = page.getByRole('textbox', {name: 'Find a project member'});
    await filter.fill('~nec');
    await page.getByRole('menuitemradio', {name: /Taylor/}).waitFor();
    assert.equal(await page.getByRole('menuitemradio').count(), 1);
    await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
    await row.getByRole('button', {name: /Change assignee.*Taylor/}).waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('data-work-control') === 'title');
    assert.equal(state.commands[1].operation, 'work.assign');
    assert.equal(state.commands[1].expected_revision, '2');
    assert.deepEqual(state.commands[1].payload, {assignee_principal_id: taylor.principal_id});
    await row.getByRole('button', {name: title, exact: true}).click();
    const panel = page.locator('#work-detail-panel');
    await panel.getByRole('button', {name: /Change assignee.*Taylor/}).click();
    await page.getByRole('menuitemradio', {name: 'Unassigned', exact: true}).click();
    await panel.getByRole('button', {name: /Change assignee.*Unassigned/}).waitFor();
    assert.equal(state.commands[2].payload.assignee_principal_id, '');
    await panel.getByRole('button', {name: 'Close', exact: true}).click();
    await page.setViewportSize({width:320,height:780});
    await row.getByRole('button', {name: title, exact: true}).focus();
    await page.keyboard.press('Shift+F10');
    await page.getByRole('menu', {name: 'Work item actions'}).waitFor();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path:path.join(output, 'work-quick-actions-mobile.png')});
  });
  await check('work-filter-keyboard-create-and-authorized-links', async (page, state) => {
    const item = id(650);
    const late = {kind: 'work', resource_id: item, title: 'Review the release notes', description: 'Review the exact written changes.',
      resource_revision: '1', status: 'in_progress', type: 'task', priority: 'none', assignee_principal_id: person.principal_id,
      assignee_display_name: person.display_name};
    const taylor = {principal_id: id(109), display_name: 'Taylor', identity_ship: '~nec'};
    state.assignees = [person, taylor];
    state.work = [...Array.from({length: 21}, (_, index) => ({
      kind: 'work', resource_id: id(500 + index), title: `Earlier work ${index + 1}`, description: '', resource_revision: '1',
      status: 'todo', type: 'task', priority: 'none',
    })), late];
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.getByRole('button', {name: 'Filters', exact: true}).click();
    const filters = page.getByRole('region', {name: 'Work filters'});
    const title = filters.getByRole('textbox', {name: 'Find by title'});
    await title.fill('release');
    await page.getByText('1 of 22 work items', {exact: true}).waitFor();
    await filters.getByRole('combobox', {name: 'Filter by status'}).selectOption('todo');
    await page.getByRole('heading', {name: 'No work matches these filters'}).waitFor();
    await filters.getByRole('combobox', {name: 'Filter by status'}).selectOption('in_progress');
    await filters.getByRole('combobox', {name: 'Filter by assignee'}).selectOption('mine');
    await page.getByText('1 of 22 work items', {exact: true}).waitFor();
    const row = page.locator('.work-row').getByRole('button', {name: late.title, exact: true});
    await row.focus(); await page.keyboard.press('s');
    await page.getByRole('menu', {name: 'Set status', exact: true}).waitFor();
    await page.keyboard.press('Escape'); await page.keyboard.press('a');
    await page.getByRole('menu', {name: 'Assign to', exact: true}).waitFor();
    await page.keyboard.press('Escape'); await page.keyboard.press('p');
    await page.getByRole('menu', {name: 'Set priority', exact: true}).waitFor();
    await page.keyboard.press('Escape'); await page.keyboard.press('Enter');
    const panel = page.locator('#work-detail-panel');
    await panel.getByRole('heading', {name: late.title, exact: true}).waitFor();
    assert.equal(new URL(page.url()).hash, `#work/${state.project.project_id}/${item}`);
    await page.evaluate(() => { Object.defineProperty(navigator, 'clipboard', {configurable: true,
      value: {writeText: async value => { window.copiedWorkLink = value; }}}); });
    await panel.getByRole('button', {name: 'Copy link', exact: true}).click();
    assert.equal(await page.evaluate(() => window.copiedWorkLink), page.url());
    await page.goBack();
    await panel.waitFor({state: 'detached'});
    await page.goForward();
    await panel.getByRole('heading', {name: late.title, exact: true}).waitFor();
    await page.reload();
    await panel.getByRole('heading', {name: late.title, exact: true}).waitFor();
    await page.setViewportSize({width: 320, height: 780});
    assert.equal(await panel.locator('.work-metadata').evaluate(node => getComputedStyle(node).display), 'grid');
    assert.equal(await panel.locator('.work-metadata').evaluate(node => getComputedStyle(node).gridTemplateColumns.split(' ').length), 2);
    assert.ok(await panel.locator('.work-property-label').evaluateAll(labels => labels.every(label => label.scrollWidth <= label.clientWidth)));
    await page.screenshot({path:path.join(output, 'work-item-320.png')});
    await panel.getByRole('button', {name: late.title, exact: true}).click();
    await page.waitForFunction(() => document.activeElement?.getAttribute('name') === 'title');
    await page.getByRole('button', {name: 'Close', exact: true}).click();
    await panel.getByRole('heading', {name: late.title, exact: true}).waitFor();
    await panel.getByRole('button', {name: 'Close', exact: true}).click();
    await page.keyboard.press('c');
    const newTitle = page.getByRole('textbox', {name: 'Title', exact: true});
    await newTitle.waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('name') === 'title');
    await page.keyboard.press('c');
    assert.equal(await newTitle.inputValue(), 'c');
    await newTitle.fill('Write the launch checklist');
    await page.getByRole('combobox', {name: 'Assignee', exact: true}).selectOption({label: 'Taylor · ~nec'});
    await page.getByRole('button', {name: 'Save at home', exact: true}).click();
    await page.getByText('Saved at home · revision 1', {exact: true}).waitFor();
    assert.equal(state.commands.length, 1);
    assert.equal(state.commands[0].operation, 'work.create');
    assert.equal(state.commands[0].payload.assignee_principal_id, taylor.principal_id);
    assert.equal(state.work.at(-1).assignee_display_name, 'Taylor');
  });
  await check('work-context-links-docs-and-blockers-with-confirmed-removal', async (page, state) => {
    const project = state.project.project_id;
    const work = (num, title) => ({kind: 'work', project_id: project, container_id: '', resource_id: id(num), title,
      description: '', resource_revision: '1', status: 'todo', type: 'task', priority: 'none'});
    const ticket = work(651, 'Prepare the launch');
    const blocker = {...work(652, 'Review handoff'), status: 'done'};
    const later = work(653, 'Publish the release');
    state.work = [ticket, blocker, later];
    const box = id(200);
    const doc = id(654);
    state.containers = [{kind: 'container', project_id: project, container_id: box, resource_id: box,
      title: 'Shared pages', resource_revision: '1', visibility: 'shared'}];
    state.documents = [{kind: 'document', project_id: project, resource_id: doc, container_id: box, title: 'Release guide', resource_revision: '1',
      markdown: `---\nid: ${doc}\ntype: page\nstate: published\n---\n# Release guide\nAcceptance steps here.`}];
    const relation = (num, source, target, type = 'blocks') => ({kind: 'relation', title: 'Synthetic relation',
      project_id: project, container_id: '', resource_id: id(num), resource_revision: '1', type,
      source_project_id: project, source_kind: 'work', source_container_id: '', source_id: source.resource_id,
      target_project_id: project, target_kind: 'work', target_container_id: '', target_id: target.resource_id});
    state.relations = [...Array.from({length: 20}, (_, n) => relation(680 + n, later, blocker)), relation(655, blocker, ticket)];
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.locator('.work-row').getByRole('button', {name: ticket.title, exact: true}).click();
    const context = page.getByRole('region', {name: 'Relationships', exact: true});
    await context.getByRole('button', {name: 'Show links', exact: true}).waitFor();
    assert.equal(state.requests.filter(row => row.kind === 'relations').length, 0);
    await context.getByRole('button', {name: 'Show links', exact: true}).click();
    await context.getByRole('heading', {name: 'Blocked by', exact: true}).waitFor();
    await context.getByRole('button', {name: blocker.title, exact: true}).waitFor();
    await context.getByText('Done', {exact: true}).waitFor();
    assert.equal(state.requests.filter(row => row.kind === 'relations').length, 2);
    assert.equal(await context.getByRole('button', {name: later.title, exact: true}).count(), 0);
    await context.getByRole('button', {name: 'Add link', exact: true}).click();
    await context.getByRole('combobox', {name: 'Relationship type', exact: true}).selectOption({label: 'Supporting doc'});
    await context.getByRole('textbox', {name: 'Find a resource', exact: true}).fill('release guide');
    await context.getByRole('button', {name: 'Find matches', exact: true}).click();
    await context.getByRole('combobox', {name: 'Choose a resource', exact: true}).selectOption({label: 'Release guide'});
    state.loseCommand = true;
    await context.getByRole('button', {name: 'Save link', exact: true}).click();
    await page.getByRole('heading', {name: 'Save awaiting confirmation', exact: true}).waitFor();
    await page.getByRole('alert').waitFor();
    state.loseCommand = false;
    await page.getByRole('button', {name: 'Check receipt', exact: true}).click();
    await page.getByText('Link added.', {exact: true}).waitFor();
    assert.equal(state.commands.length, 1);
    assert.deepEqual(state.commands.at(-1).payload, {type: 'documents', source_project_id: project, source_kind: 'document',
      source_container_id: box, source_id: doc, target_project_id: project, target_kind: 'work', target_container_id: '', target_id: ticket.resource_id});
    await context.getByRole('button', {name: 'Release guide', exact: true}).click();
    await page.locator('.document-editor').getByRole('heading', {name: 'Release guide', exact: true, level: 2}).waitFor();
    assert.match(await page.getByRole('textbox', {name: 'Markdown source'}).inputValue(), /Acceptance steps here\./u);
    await page.getByRole('button', {name: /Back to work item/u}).click();
    await page.locator('#work-detail-panel').getByRole('heading', {name: ticket.title, exact: true}).waitFor();
    await context.getByRole('button', {name: 'Show links', exact: true}).click();
    await context.getByRole('button', {name: 'Remove link to Release guide', exact: true}).click();
    await page.getByText('This removes only the relationship. Both linked resources stay where they are.', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'Confirm deletion', exact: true}).click();
    await page.getByText('Link removed.', {exact: true}).waitFor();
    await context.getByRole('button', {name: 'Release guide', exact: true}).waitFor({state: 'detached'});
    assert.equal(state.commands.at(-1).operation, 'relation.delete');
    assert.equal(state.documents.length, 1);
    await context.getByRole('button', {name: blocker.title, exact: true}).click();
    await page.locator('#work-detail-panel').getByRole('heading', {name: blocker.title, exact: true}).waitFor();
    state.project.role = 'reader';
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await context.getByRole('button', {name: 'Show links', exact: true}).click();
    await context.getByRole('heading', {name: 'Blocks', exact: true}).waitFor();
    assert.equal(await context.getByRole('button', {name: 'Add link', exact: true}).count(), 0);
    await page.setViewportSize({width: 320, height: 790});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= 320), true);
  });
  await check('code-linked-review-roundtrip-and-missing-work-without-signout', async (page, state) => {
    const item = id(665);
    const title = 'Review the sample change';
    const proposal = id(666);
    const target = 'refs/heads/main';
    const feature = 'refs/heads/feature/welcome';
    const ref = name => Buffer.from(name).toString('hex');
    const base = 'a'.repeat(40);
    const head = 'b'.repeat(40);
    const snapshot = 'c'.repeat(64);
    state.pack = {status: 'external', snapshot, generation: '0', authority_epoch: '1', request_id: id(668),
      accepted_at_ms: '1800000000000', object_count: '8', head: ref(target), refs: JSON.stringify({[ref(target)]: base, [ref(feature)]: head})};
    state.work = [{kind: 'work', resource_id: item, title, description: '', resource_revision: '1', status: 'todo', type: 'task', priority: 'none'}];
    state.externalReviews.set(proposal, {proposal_id: proposal, revision: '1', work_id: item, source_ref: feature, ref: target,
      base_oid: base, head_oid: head, author: id(109), reviewer: '', base_snapshot: snapshot, generation: '0',
      merged_revision: '', merged_snapshot: '', merged_request_id: ''});
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    await page.getByRole('button', {name: 'Code', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.locator('.work-row').getByRole('button', {name: title, exact: true}).click();
    await page.waitForURL(`**/#work/${state.project.project_id}/${item}`);
    const workUrl = page.url();
    const linked = page.getByRole('region', {name: 'Linked code changes'});
    await linked.getByRole('button', {name: /feature\/welcome.*Revision 1/}).click();
    await page.getByRole('button', {name: 'View work item', exact: true}).click();
    await page.waitForFunction(() => document.activeElement?.id === 'work-detail-title');
    assert.equal(page.url(), workUrl);
    assert.ok(state.externalRequests.some(row => row.action === 'external-list' && row.work_id === item));
    assert.ok(state.externalRequests.some(row => row.action === 'external-proposal' && row.proposal_id === proposal));
    state.work = [];
    await page.reload();
    await page.getByRole('alert').getByText('This work link is unavailable or you do not have access.').waitFor();
    assert.equal(await page.locator('#work-detail-panel').count(), 0);
    await page.getByRole('button', {name: 'Sign out', exact: true}).waitFor();
  });
  await check('work-discussion-retains-draft-and-posts-once', async (page, state) => {
    const item = id(713);
    state.work = [{kind: 'work', resource_id: item, title: 'Review ticket context', description: 'Source details.',
      resource_revision: '2', status: 'todo', type: 'task', priority: 'none', comment_count: '1'}];
    state.comments.set(item, [{body: 'Use the sample entry points.', comment_revision: '2',
      principal_id: id(714), identity_ship: '~nec', accepted_at_ms: '1790519400000'}]);
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    const row = page.locator('.work-row').getByRole('button', {name: 'Review ticket context', exact: true});
    await row.click();
    const discussion = page.getByRole('region', {name: 'Discussion'});
    await discussion.getByText('Use the sample entry points.').waitFor();
    await discussion.getByText('~nec', {exact: true}).waitFor();
    const draft = discussion.getByRole('textbox', {name: 'Comment'});
    await draft.fill('I verified the entry points. 東京');
    await page.locator('#work-detail-panel').getByRole('button', {name: 'Close', exact: true}).click();
    await row.click();
    assert.equal(await draft.inputValue(), 'I verified the entry points. 東京');
    state.loseCommand = true;
    await discussion.getByRole('button', {name: 'Post comment'}).click();
    await page.getByRole('heading', {name: 'Save awaiting confirmation'}).waitFor();
    assert.equal(await draft.inputValue(), 'I verified the entry points. 東京');
    await page.getByRole('button', {name: 'Check receipt'}).click();
    await discussion.getByText('I verified the entry points. 東京', {exact: true}).waitFor();
    assert.equal(await draft.inputValue(), '');
    assert.equal(state.commands.length, 1);
    assert.equal(state.commands[0].operation, 'work.comment');
    assert.equal(state.comments.get(item).length, 2);
    await page.reload();
    await discussion.getByText('I verified the entry points. 東京', {exact: true}).waitFor();
  });
  await check('code-work-agent-access-from-ticket-and-review-readback', async (page, state) => {
    const item = id(718);
    state.work = [{kind: 'work', resource_id: item, title: 'Update the readme examples', description: 'Add one simple example.',
      resource_revision: '1', status: 'todo', type: 'task', priority: 'none'}];
    await page.getByRole('button', {name: 'Enable Git repository', exact: true}).click();
    await page.getByRole('button', {name: 'Work', exact: true}).click();
    await page.locator('.work-row').getByRole('button', {name: 'Update the readme examples', exact: true}).click();
    const agent = page.getByRole('region', {name: 'Agent delegation'});
    await agent.getByRole('button', {name: 'Delegate to an agent'}).click();
    await agent.getByRole('textbox', {name: 'Agent Urbit ID'}).fill('nec');
    await agent.getByRole('button', {name: 'Grant proposal access'}).click();
    await agent.getByText('Proposal access granted.', {exact: true}).waitFor();
    const grant = [...state.delegations.values()][0];
    assert.equal(grant.work_id, item);
    assert.equal(grant.worker_ship, '~nec');
    assert.equal(grant.ref, 'refs/heads/main');
    const proposal = id(719);
    grant.proposals = JSON.stringify({[proposal]: '1'});
    state.proposals.set(proposal + '/1', {proposal_id: proposal, revision: '1', work_id: item,
      ref: grant.ref, base_oid: 'a'.repeat(40), head_oid: 'b'.repeat(40), author: id(109), reviewer: '', merged_revision: ''});
    await agent.getByRole('button', {name: 'Refresh agent access'}).click();
    await agent.getByRole('button', {name: 'View proposal · revision 1', exact: true}).waitFor();
    await page.reload();
    await agent.getByRole('button', {name: 'View proposal · revision 1', exact: true}).click();
    await page.getByRole('region', {name: 'Exact proposal'}).getByText('Awaiting review.', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'View work item', exact: true}).click();
    await agent.getByRole('button', {name: 'Revoke access…'}).click();
    await agent.getByRole('button', {name: 'Confirm revoke'}).click();
    await agent.getByText('Proposal access revoked.', {exact: true}).waitFor();
    await agent.getByText('Revoked · main', {exact: true}).waitFor();
    assert.equal(grant.status, 'revoked');
    assert.equal(await agent.getByRole('button', {name: 'Copy agent brief'}).count(), 0);
  });
  await check('page-title-visibility-clean-close-and-confirmed-discard-responsive', async (page, state) => {
    const body = '# A useful page — 東京\n\nKeep this exact Markdown.\n';
    const markdown = `---\nid: ${id(603)}\ntype: page\nstate: draft\n---\n` + body;
    state.containers = [{kind: 'container', resource_id: id(200), container_id: id(200), title: 'Private notes', visibility: 'private', container_head: ''}];
    state.documents = [{kind: 'document', resource_id: id(603), container_id: id(200), title: '# A useful page — 東京', resource_revision: '2', markdown}];
    await page.getByRole('button', {name: 'Docs', exact: true}).click();
    await page.getByLabel('Collection', {exact: true}).selectOption(id(200));
    await page.getByRole('button', {name: 'Open page', exact: true}).click();
    await page.locator('.editor-heading').getByRole('heading', {name: 'A useful page — 東京', exact: true}).waitFor();
    assert.equal(await page.locator('.page-visibility').textContent(), 'Private draft · only you');
    assert.equal(await page.getByRole('button', {name: 'Discard changes…', exact: true}).count(), 0);
    assert.equal(await page.getByRole('textbox', {name: 'Markdown source', exact: true}).inputValue(), body);
    await page.getByRole('button', {name: 'Close', exact: true}).click();
    assert.equal(await page.getByRole('alertdialog').count(), 0);
    await page.getByRole('button', {name: 'Open page', exact: true}).click();
    await page.getByRole('textbox', {name: 'Markdown source', exact: true}).fill(body + 'Unsent local edit.');
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('button', {name: 'Keep editing', exact: true}).click();
    assert.equal(await page.getByRole('textbox', {name: 'Markdown source', exact: true}).inputValue(), body + 'Unsent local edit.');
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height: 900});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.screenshot({path: path.join(output, `polish-docs-${width}.png`), fullPage: true});
    }
    await page.getByRole('button', {name: 'Discard changes…', exact: true}).click();
    await page.getByRole('button', {name: 'Discard changes', exact: true}).click();
    await page.getByRole('button', {name: 'Open page', exact: true}).click();
    assert.equal(await page.getByRole('textbox', {name: 'Markdown source', exact: true}).inputValue(), body);
    assert.equal(state.commands.length, 0);
  });
  await check('page-body-and-full-source-roundtrip-preserves-metadata-and-explicit-save', async (page, state) => {
    const prefix = `---\nid: ${id(604)}\ntype: page\nstate: draft\n---\n`;
    const body = '# Notes — 東京\n\nKeep spacing.  \n';
    state.containers = [{kind: 'container', resource_id: id(200), container_id: id(200), title: 'Private notes', visibility: 'private', container_head: ''}];
    state.documents = [{kind: 'document', resource_id: id(604), container_id: id(200), title: 'Notes — 東京', resource_revision: '2', markdown: prefix + body}];
    await page.getByRole('button', {name: 'Docs', exact: true}).click();
    await page.getByLabel('Collection', {exact: true}).selectOption(id(200));
    await page.getByRole('button', {name: 'Open page', exact: true}).click();
    const editor = page.getByRole('textbox', {name: 'Markdown source', exact: true});
    assert.equal(await editor.inputValue(), body);
    await editor.fill(body + '\nEdited body.\n');
    const show = page.getByRole('button', {name: 'Show full Markdown', exact: true});
    if (!(await show.isVisible())) await page.locator('summary[aria-label="More page actions"]').click();
    await show.click();
    assert.equal(await editor.inputValue(), prefix + body + '\nEdited body.\n');
    assert.equal(state.commands.length, 0, 'changing editor mode never saves');
    await editor.fill(prefix + body + '\nEdited in full source.\n');
    await page.locator('summary[aria-label="More page actions"]').click();
    await page.getByRole('button', {name: 'Hide metadata', exact: true}).click();
    assert.equal(await editor.inputValue(), body + '\nEdited in full source.\n');
    await page.getByRole('button', {name: 'Save page', exact: true}).click();
    await page.getByText('Saved at home · revision 3', {exact: true}).waitFor();
    assert.equal(state.commands.length, 1);
    assert.equal(state.commands[0].operation, 'document.save');
    assert.equal(state.commands[0].payload.markdown, prefix + body + '\nEdited in full source.\n');
    assert.equal(state.commands[0].expected_revision, '2');
  });
  await check('routine-refresh-announcement-expires-without-clearing-save-evidence', async (page, state) => {
    await workForm(page);
    await page.getByRole('button', {name: 'Save at home', exact: true}).click();
    await page.getByText('Saved at home · revision 1', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'Refresh', exact: true}).click();
    const notice = page.locator('.refresh-notice');
    await notice.getByText('View refreshed from home.', {exact: true}).waitFor();
    assert.equal(await notice.getAttribute('role'), 'status');
    await page.waitForFunction(() => document.querySelector('.refresh-notice')?.textContent === '', {timeout: 6000});
    assert.equal(await page.locator('.live').textContent(), 'Saved at home · revision 1');
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

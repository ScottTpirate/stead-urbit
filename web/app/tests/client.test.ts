// Host tests with an explicit fake fetch transport. Not browser/native evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import { newId, commandDigest, canonical } from '../src/protocol';
import { HomeClient, HomeError, command, type Fields } from '../src/api';
const id = (end: string) => `019939ba-4000-7000-8000-${end.padStart(12, '0')}`;
const identity = (person: number): Fields => ({principal_id: id(String(100 + person)), binding_id: id(String(200 + person)), binding_revision: '1', identity_ship: person === 1 ? '~bus' : '~nec', session_audit_id: String(person).repeat(64), display_name: 'Synthetic person', organization_id: id('5'), team_id: id('6')});
const request = {kind: 'identity' as const, project_id: '', container_id: '', resource_id: '', search: '', cursor: ''};
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {status, headers: {'content-type': 'application/json'}});
let person = 1;
let mode = '';
let deferred: ((value: Response) => void) | undefined;
let savedBody: Record<string, unknown> = {};
const bodies: Record<string, unknown>[] = [];
const receipts = new Map<string, Record<string, unknown>>();
const corrupt = (row: Record<string, unknown>) => {
  row = {...row};
  if (mode === 'bad-oid') row.git_commit_oid = 'A'.repeat(40);
  if (mode === 'extra-field') row.extra = 'unexpected';
  if (mode === 'wrong-scope') row.container_id = id('999');
  if (mode === 'wrong-revision') row.resource_revision = '99';
  if (mode === 'wrong-session') row.session_audit_id = 'f'.repeat(64);
  return row;
};
globalThis.fetch = async (url, init) => {
  const raw = JSON.parse(String(init?.body)) as Record<string, unknown>;
  bodies.push(raw); savedBody = raw;
  if (mode === 'defer') return new Promise(resolve => { deferred = resolve; });
  if (mode === '401-html') return new Response('<h1>Expired</h1>', {status: 401, headers: {'content-type': 'text/html'}});
  if (mode === 'oversized') return new Response(' '.repeat(262145), {headers: {'content-type': 'application/json'}});
  if (mode === 'broken-stream') return new Response(new ReadableStream({start(controller) {controller.error(new TypeError('interrupted'));}}), {headers: {'content-type': 'application/json'}});
  if (mode === 'defer-identity' && raw.kind === 'identity') return new Promise(resolve => { deferred = resolve; });
  if (mode === '500') return json({message: 'Unknown'}, 500);
  if (String(url).endsWith('/resume')) return json({status: 'authenticated', csrf: String(person).repeat(64)});
  if (String(url).endsWith('/logout')) {
    if (mode === 'network') throw new TypeError('lost response');
    return json({status: 'logged_out'});
  }
  if (String(url).endsWith('/command')) {
    const payload = raw.payload as Fields;
    const accepted = {protocol: 'stead.receipt/3', status: 'accepted', ...identity(person),
      request_id: raw.request_id, project_id: raw.project_id, resource_id: raw.resource_id,
      operation: raw.operation, authority_epoch: raw.authority_epoch,
      resource_revision: String(BigInt(String(raw.expected_revision)) + 1n),
      canonical_sha256: await commandDigest(raw), container_id: raw.operation === 'container.create' ? raw.resource_id : payload.container_id ?? '',
      resource_kind: String(raw.operation).split('.')[0], runtime: 'isolated-fake', accepted_at_ms: '1790519400000', git_commit_oid: String(raw.operation).startsWith('document.') ? 'a'.repeat(40) : '',
      authentication: 'native-approved-browser/1', authentication_strength: 'native-approved-browser'};
    const {display_name, organization_id, team_id, ...receipt} = accepted;
    if (mode === 'missing-oid') delete (receipt as Partial<typeof receipt>).git_commit_oid;
    if (mode === 'wrong-digest') receipt.canonical_sha256 = '0'.repeat(64);
    if (mode === 'wrong-actor') receipt.principal_id = id('999');
    if (mode === 'uncorrelated-reject') return json({protocol: 'stead.result/3', status: 'rejected', error: 'revision_conflict'});
    if (mode === 'correlated-reject') return json({protocol: 'stead.result/3', status: 'rejected', error: 'revision_conflict', request_id: raw.request_id, canonical_sha256: await commandDigest(raw)});
    receipts.set(String(raw.request_id), receipt);
    return json(corrupt(receipt));
  }
  const headers = init?.headers as Record<string, string>;
  assert.equal(headers['X-Stead-CSRF'], String(person).repeat(64));
  return json({status: 'read', ...raw, protocol: 'stead.query-result/3',
    authority_epoch: '0', generation: '0'.repeat(64), cursor: '', rows: raw.kind === 'receipt' ? (receipts.has(String(raw.resource_id)) ? {'0': corrupt(receipts.get(String(raw.resource_id))!)} : {}) : {'0': identity(person)}});
};
const rejects = (promise: Promise<unknown>, code: string) => assert.rejects(promise, (error: unknown) => error instanceof HomeError && error.code === code);
test('UUIDv7 preserves the 48-bit timestamp, version, variant and uniqueness', () => {
  const old = Date.now; Date.now = () => 0x019939ba4000;
  try {
    const values = new Set(Array.from({length: 1000}, newId));
    assert.equal(values.size, 1000);
    for (const value of values) assert.match(value, /^019939ba-4000-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u);
    Date.now = () => 2 ** 48; assert.throws(newId);
  } finally { Date.now = old; }
});
test('canonical UTF-8 preserves text and rejects NUL/unpaired surrogate', () => {
  assert.equal(canonical({z: 'é🙂', a: 'a\nb'}), '{"a":"a\\nb","z":"é🙂"}');
  assert.throws(() => canonical({x: '\0'}));
  assert.throws(() => canonical({x: '\ud800'}));
});
test('member adoption fences old requests and clears a different identity', async () => {
  const client = new HomeClient(); let clears = 0; client.onInvalidated = () => clears++;
  person = 1; mode = ''; await client.resume(); assert.equal(clears, 1);
  mode = 'defer'; const old = client.query(request); const rejectOld = rejects(old, 'session_changed');
  const respondOld = deferred!; mode = ''; person = 2;
  await client.resume(); assert.equal(clears, 2);
  respondOld(new Response('old unauthorized', {status: 401})); await rejectOld;
  assert.equal(clears, 2, 'old 401 must not invalidate a new session');
  await client.query(request);
});
test('non-JSON 401 clears credentials before attempting to decode it', async () => {
  const client = new HomeClient(); person = 1; mode = ''; await client.resume();
  let clears = 0; client.onInvalidated = () => clears++;
  mode = '401-html'; await rejects(client.query(request), 'session_required');
  assert.equal(clears, 1); mode = ''; await rejects(client.query(request), 'session_required');
});
test('mutation confirmation requires full receipt and correlated rejection', async () => {
  const client = new HomeClient(); person = 1; mode = ''; await client.resume();
  const value = command(id('1'), id('2'), '0', '1', 'work.create', {title: 'Synthetic', description: '', type: 'task', status: 'todo', priority: 'none'});
  await client.command(value);
  mode = 'missing-oid'; await rejects(client.command(value), 'invalid_response');
  mode = 'wrong-digest'; await rejects(client.command(value), 'invalid_response');
  mode = 'wrong-actor'; await rejects(client.command(value), 'invalid_response');
  mode = '500'; await rejects(client.command(value), 'outcome_unknown');
  mode = 'uncorrelated-reject'; await rejects(client.command(value), 'outcome_unknown');
  mode = 'correlated-reject'; await rejects(client.command(value), 'revision_conflict');
  assert.equal(savedBody.request_id, value.request_id);
});
test('failed logout retains a retry path; confirmed logout clears it', async () => {
  const client = new HomeClient(); person = 1; mode = ''; await client.resume();
  mode = 'network'; await rejects(client.logout(), 'logout_unconfirmed');
  mode = ''; await client.query(request); await client.logout();
  await rejects(client.query(request), 'session_required');
});

test('unconfirmed resume retains the identity partition and fences calls until explicit recovery', async () => {
  const client = new HomeClient(); person = 1; mode = ''; await client.resume();
  let clears = 0; client.onInvalidated = () => clears++;
  const value = command(id('1'), id('2'), '0', '1', 'work.create', {title: 'Keep my request', description: '', type: 'task', status: 'todo', priority: 'none'});
  await client.command(value);
  mode = '500'; await rejects(client.resume(), 'outcome_unknown');
  assert.equal(clears, 0, 'transport uncertainty is not identity invalidation');
  mode = ''; const count = bodies.length;
  await rejects(client.query(request), 'resume_required');
  await rejects(client.command(value), 'resume_required');
  assert.equal(bodies.length, count, 'suspended calls never reach the transport');
  await client.resume(); assert.equal(clears, 0);
  assert.equal((await client.recover(value)).request_id, value.request_id);
  mode = '401-html'; await rejects(client.resume(), 'session_required');
  assert.equal(clears, 1, 'confirmed invalidation clears the partition');
});

test('superseded resume and consume failures cannot clear a newer adopted session', async () => {
  for (const kind of ['resume', 'consume']) {
    const client = new HomeClient(); person = 1; mode = ''; await client.resume();
    let clears = 0; client.onInvalidated = () => clears++;
    mode = 'defer'; const old = kind === 'resume' ? client.resume() : client.consume('c'.repeat(64));
    const rejectOld = rejects(old, 'session_changed'); const respondOld = deferred!;
    await rejects(client.query(request), 'session_changed');
    person = 2; mode = ''; await client.resume(); assert.equal(clears, 1);
    respondOld(json({status: 'authenticated', csrf: '1'.repeat(64)})); await rejectOld;
    assert.equal(clears, 1); await client.query(request);
  }
});

test('recovery checks complete document and container receipts against the original command', async () => {
  const client = new HomeClient(); person = 1; mode = ''; await client.resume();
  for (const operation of ['document.save', 'container.create']) {
    const value = command(id('1'), id('2'), '0', '1', operation, operation === 'document.save' ? {container_id: id('3'), markdown: 'Synthetic'} : {visibility: 'private', title: 'Drafts'});
    await client.command(value);
    assert.equal((await client.recover(value)).request_id, value.request_id);
    assert.equal(savedBody.resource_id, value.request_id);
    assert.equal(savedBody.container_id, operation === 'container.create' ? value.resource_id : value.payload.container_id);
    for (const fault of ['bad-oid', 'extra-field', 'wrong-scope', 'wrong-revision', 'wrong-session']) {
      mode = fault; await rejects(client.recover(value), 'invalid_response');
    }
    mode = ''; receipts.delete(value.request_id); await rejects(client.recover(value), 'outcome_unknown');
  }
});
test('a superseded adoption identity query cannot publish or clear a new identity', async () => {
  const client = new HomeClient(); person = 1; mode = ''; await client.resume();
  deferred = undefined; mode = 'defer-identity'; const old = client.resume(); const rejectOld = rejects(old, 'session_changed');
  while (!deferred) await new Promise(resolve => setImmediate(resolve));
  const respondOld = deferred; const oldQuery = {...savedBody};
  mode = ''; person = 2; await client.resume();
  respondOld(json({status: 'read', ...oldQuery, protocol: 'stead.query-result/3', authority_epoch: '0', generation: '0'.repeat(64), cursor: '', rows: {'0': identity(1)}}));
  await rejectOld;
  const current = await client.query(request); assert.equal(current.rows['0']?.principal_id, identity(2).principal_id);
});
test('bounded response parsing distinguishes malformed bytes from lost transport', async () => {
  const client = new HomeClient(); person = 1; mode = ''; await client.resume();
  mode = 'oversized'; await rejects(client.query(request), 'invalid_response');
  mode = 'broken-stream'; await rejects(client.query(request), 'outcome_unknown');
  mode = ''; await client.query(request);
});
test('command hash matches an independent Python hashlib and canonical JSON vector', async () => {
  const value = {protocol: 'stead.command/3', request_id: id('301'), project_id: id('100'), resource_id: id('101'), expected_revision: '0', authority_epoch: '1', operation: 'work.create', payload: {title: 'é🙂', description: 'line\nnext', type: 'task', status: 'todo', priority: 'none'}};
  assert.equal(await commandDigest(value), '0346ca1b87d2430868d09419687891a2d6bd7bae364c92ce133a005a6871d880');
});

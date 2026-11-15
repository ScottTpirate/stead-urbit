// Source-derived protocol expectations and injected transport tests only.
// This is neither native qualification nor evidence of an activated carrier.
import test from 'node:test';
import assert from 'node:assert/strict';
import {canonical, commandDigest} from '../src/protocol';
import {encodeProductCommand, encodeProductQuery, parseProductCommand, parseProductQuery, parseProductView, parseProductReceipt,
  productCommandDigest, productDetailOutcomes, ProductProtocolError, type ProductCommand, type ProductProperties,
  type ProductContract, type ProductQuery, type ProductScope, type ProductWorkDetail} from '../src/productProtocol';
import {ProductWorkClient, type ProductTransport} from '../src/productClient';

const id = (number: number) => '019939ba-4000-7000-8000-' + String(number).padStart(12, '0');
const scope: ProductScope = {request_id: id(301), project_id: id(100), resource_id: id(101), authority_epoch: '1'};
const properties: ProductProperties = {type: 'task', status: 'todo', priority: 'none', owner_principal_id: '', worker_principal_id: '', blocked_reason: ''};
const target = {kind: 'document', project_id: id(100), collection_id: id(200), document_id: id(201), expected_revision: '0', base_markdown_sha256: ''} as const;
const contract: ProductContract = {title: 'Draft', description: 'Exact notes', acceptance_criteria: 'Reviewed and accepted', required_outcomes: {[id(401)]: target}};
const command = (operation: string, expected: unknown, payload: unknown) => ({...scope, protocol: 'stead.command/4', operation, expected, payload});
const create = (payload = {...properties, ...contract}) => command('work.create', {work_revision: '0', execution_contract_revision: '0'}, payload);
const comment = (body = 'Exact λ <text>  \n') => parseProductCommand(JSON.stringify(command('work.comment', {discussion_sequence: '0'}, {body}))) as Extract<ProductCommand, {operation: 'work.comment'}>;
const query: ProductQuery = {protocol: 'stead.query/4', request_id: id(600), kind: 'work', project_id: id(100), container_id: '', resource_id: id(101), search: '', cursor: ''};
const base = {kind: 'work', project_id: id(100), resource_id: id(101), container_id: '', resource_revision: '3', work_revision: '2',
  execution_contract_protocol: 'stead.work-contract/2', execution_contract_revision: '1', execution_contract_digest: 'a'.repeat(64), discussion_sequence: '1',
  title: 'Migrated Work', type: 'task', status: 'todo', priority: 'none', owner_principal_id: '', worker_principal_id: '', owner_display_name: '', worker_display_name: ''};
const detail = {...base, description: 'Exact λ <description>  \n', acceptance_criteria: '', required_outcomes: canonical({[id(401)]: target}),
  blocked_reason: '', completion_basis: '', completion_principal_id: '', completion_request_id: '', completion_note: '',
  legacy_assignment_pending: 'yes', legacy_assignee_principal_id: id(103), legacy_assignee_display_name: 'Bob',
  legacy_blocked_pending: 'no', legacy_blocked_status: '', legacy_prior_status: ''};
const preview = {...base, snippet: 'Exact description'};
const result = (request: ProductQuery, rows: unknown[], cursor = '') => ({protocol: 'stead.query-result/4', status: 'read', request_id: request.request_id,
  kind: request.kind, project_id: request.project_id, container_id: '', resource_id: request.resource_id, authority_epoch: '1', generation: 'b'.repeat(64), cursor,
  rows: Object.fromEntries(rows.map((row, index) => [String(index), row]))});
const note = (sequence: number) => ({kind: 'comment', project_id: id(100), work_id: id(101), sequence: String(sequence), body: `Exact comment ${sequence}  \n`,
  principal_id: id(103), display_name: 'Bob', identity_ship: '~nec', request_id: id(700 + sequence), accepted_at_ms: '1007', legacy_comment_revision: sequence === 1 ? '3' : ''});
function receipt(request: ProductCommand, digest: string, status = 'accepted') {
  return {protocol: 'stead.receipt/4', status, request_id: request.request_id, canonical_sha256: digest,
    project_id: request.project_id, resource_id: request.resource_id, authority_epoch: request.authority_epoch, operation: request.operation,
    principal_id: id(102), recorded_at_ms: '2000', error: status === 'accepted' ? '' : 'revision_conflict', expected: request.expected,
    resulting: {work_revision: '2', execution_contract_revision: '1', discussion_sequence: '1', execution_contract_digest: 'a'.repeat(64)}};
}
const refused = (value: unknown) => assert.throws(() => encodeProductCommand(value), ProductProtocolError);
const badView = (value: unknown, request = query) => assert.throws(() => parseProductView(JSON.stringify(value), request), {code: 'invalid_response'});

test('source-derived command4 canonical hash preserves exact bytes and domain', async () => {
  const value = comment();
  const bytes = encodeProductCommand(value);
  // Copied from the unqualified native decoder test, not a native run receipt.
  assert.equal(await productCommandDigest(value), 'b4e24f08d8bea370485f53b606afc9b04ac919aba93dcd675f45fa41cd532fdb');
  assert.notEqual(await commandDigest(value), await productCommandDigest(value));
  assert.equal(encodeProductCommand(parseProductCommand(' \n' + bytes + '\t')), bytes);
  assert.equal(value.payload.body, 'Exact λ <text>  \n');
  const escaped = create({...properties, ...contract, description: '\b\t\n\f\u001f\u2028😀'});
  assert.ok(encodeProductCommand(escaped).includes('"description":"\\b\\t\\n\\f\\u001f\u2028😀"'));
});
test('independent expected fields and all eight operations stay closed', () => {
  const valid = [create(), command('work.update-properties', {work_revision: '2'}, properties),
    command('work.update-contract', {execution_contract_revision: '3'}, contract),
    command('work.resolve-legacy-blocked', {work_revision: '4'}, {status: 'in_review', blocked_reason: 'Needs reviewer'}),
    command('work.resolve-legacy-assignee', {work_revision: '4'}, {owner_principal_id: '', worker_principal_id: ''}),
    command('work.comment', {discussion_sequence: '0'}, {body: 'Question'}),
    command('work.complete', {work_revision: '4', execution_contract_revision: '3'}, {basis: 'human-note', note: 'Resolved with customer.'}),
    command('work.delete', {work_revision: '4', execution_contract_revision: '3', discussion_sequence: '2'}, {})];
  for (const value of valid) assert.equal(parseProductCommand(encodeProductCommand(value)).operation, value.operation);
  refused({...valid[1], expected: {execution_contract_revision: '2'}});
  refused({...valid[2], expected: {execution_contract_revision: '3', work_revision: '2'}});
  refused({...valid[5], expected: {expected_revision: '2'}});
  refused({...valid[7], expected: {work_revision: '4', execution_contract_revision: '3'}});
  refused({...valid[0], principal_id: id(102)});
  refused({...valid[1], payload: {...properties, title: 'Hidden contract edit'}});
  refused({...valid[5], payload: {body: 'Question', accepted_at_ms: '1000'}});
  refused({...valid[0], protocol: 'stead.command/3'});
});
test('decimal revisions retain uint64 precision and distinguish zero from positive', () => {
  for (const value of ['1', '9007199254740993', '18446744073709551615']) {
    const parsed = parseProductCommand(encodeProductCommand(command('work.update-properties', {work_revision: value}, properties)));
    assert.equal((parsed.expected as {work_revision: string}).work_revision, value);
  }
  for (const value of ['0', '01', '-1', '+1', '1e3', '18446744073709551616', 1]) refused(command('work.update-properties', {work_revision: value}, properties));
  refused({...create(), expected: {work_revision: '1', execution_contract_revision: '0'}});
  assert.equal(comment('Question').expected.discussion_sequence, '0');
});
test('owner worker blocked and completion syntax never invents authority or completion', () => {
  assert.doesNotThrow(() => encodeProductCommand(command('work.update-properties', {work_revision: '2'}, {...properties, status: 'done', owner_principal_id: id(102), worker_principal_id: id(103)})));
  refused(create({...properties, ...contract, status: 'done'}));
  refused(command('work.update-properties', {work_revision: '2'}, {...properties, status: 'blocked'}));
  refused(command('work.update-properties', {work_revision: '2'}, {...properties, status: 'canceled', blocked_reason: 'Waiting'}));
  refused(command('work.update-properties', {work_revision: '2'}, {...properties, owner_principal_id: '~bus'}));
  refused(command('work.resolve-legacy-assignee', {work_revision: '2'}, {owner_principal_id: '', worker_principal_id: '', resolved: 'yes'}));
  refused(command('work.complete', {work_revision: '2', execution_contract_revision: '1'}, {basis: 'legacy', note: ''}));
  refused(command('work.complete', {work_revision: '2', execution_contract_revision: '1'}, {basis: 'human-note', note: ' \n\t'}));
  refused(command('work.complete', {work_revision: '2', execution_contract_revision: '1'}, {basis: 'accepted-outcomes', note: 'Override'}));
});
test('parser rejects duplicate keys arrays scalars excessive nesting and byte limits', () => {
  const raw = encodeProductCommand(comment());
  for (const invalid of [raw.replace('"protocol":', '"protocol":"stead.command/4","pro\\u0074ocol":'),
    raw.replace('"body":', '"body":"Other","body":'), raw.replace('"body":"Exact λ <text>  \\n"', '"body":true'),
    raw.replace('"expected":{"discussion_sequence":"0"}', '"expected":[]'),
    '{"a":{"b":{"c":{"d":{"e":{}}}}}}', ' '.repeat(65537), raw + '{}']) assert.throws(() => parseProductCommand(invalid), ProductProtocolError);
  for (const invalid of ['\u0000', '\ud800', '\udfff', 'carriage\rreturn', 'a'.repeat(2049)]) refused(command('work.comment', {discussion_sequence: '0'}, {body: invalid}));
  assert.doesNotThrow(() => encodeProductCommand(comment('é'.repeat(1024))));
  refused(command('work.comment', {discussion_sequence: '0'}, {body: 'é'.repeat(1025)}));
  assert.doesNotThrow(() => encodeProductCommand(comment('\u00a0'))); // Native tests bytes>32, not JS trim().
  assert.doesNotThrow(() => encodeProductCommand(create({...properties, ...contract, title: ' '})));
  refused(create({...properties, ...contract, title: '😀'.repeat(201)}));
  refused(create({...properties, ...contract, acceptance_criteria: 'é'.repeat(4097)}));
});
test('required outcomes preserve typed exact targets and reject partial malformed contracts', () => {
  const code = {kind: 'code', project_id: id(100), repository_id: id(202), target_ref: 'refs/heads/main', base_oid: 'b'.repeat(40)};
  const note = {kind: 'completion-note', project_id: id(100), work_id: id(101), expected_revision: '0'};
  const make = (required_outcomes: unknown) => command('work.update-contract', {execution_contract_revision: '1'}, {...contract, required_outcomes});
  assert.doesNotThrow(() => encodeProductCommand(make({[id(401)]: target, [id(402)]: code, [id(403)]: note})));
  for (const original of [target, code, note]) refused(make({[id(401)]: original, [id(402)]: {...original}}));
  refused(make({[id(401)]: target, [id(402)]: {...target, expected_revision: '2', base_markdown_sha256: 'a'.repeat(64)}}));
  assert.doesNotThrow(() => encodeProductCommand(make({[id(401)]: target, [id(402)]: {...target, collection_id: id(299)}})));
  for (const changed of [{...target, project_id: id(999)}, {...target, expected_revision: '1'}, {...target, base_markdown_sha256: 'a'.repeat(64)},
    {...target, expected_revision: '1', base_markdown_sha256: 'A'.repeat(64)}, {...target, hidden: 'field'}, {...note, work_id: id(999)}]) refused(make({[id(401)]: changed}));
  for (const ref of ['refs/tags/release', 'refs/heads/a..b', 'refs/heads/.hidden', 'refs/heads/a.lock/b', 'refs/heads/a@{b', 'refs/heads/a\\b', 'refs/heads/a/', 'refs/heads/' + 'é'.repeat(60)]) refused(make({[id(401)]: {...code, target_ref: ref}}));
  const distinct = (count: number) => Object.fromEntries(Array.from({length: count}, (_, index) => [id(400 + index), {...target, document_id: id(600 + index)}]));
  assert.doesNotThrow(() => encodeProductCommand(make(distinct(16))));
  refused(make(distinct(17)));
  refused(make({name: target}));
});
test('query4 scope is exact and never silently accepts query3 or extra filters', () => {
  assert.equal(encodeProductQuery(parseProductQuery(encodeProductQuery(query))), encodeProductQuery(query));
  for (const changed of [{...query, protocol: 'stead.query/3'}, {...query, kind: 'workspace-search'}, {...query, project_id: ''},
    {...query, container_id: id(200)}, {...query, search: 'text'}, {...query, cursor: 'main'}, {...query, owner: id(102)},
    {...query, kind: 'comments', resource_id: ''}]) assert.throws(() => encodeProductQuery(changed), ProductProtocolError);
});
test('exact Work decoding preserves legacy assignment without converting it to owner or worker', () => {
  const parsed = parseProductView(JSON.stringify(result(query, [detail])), query);
  assert.equal(parsed.status, 'read'); if (parsed.status !== 'read' || parsed.kind !== 'work') return;
  const row = parsed.rows[0] as ProductWorkDetail;
  assert.equal(row.owner_principal_id, ''); assert.equal(row.worker_principal_id, ''); assert.equal(row.legacy_assignee_principal_id, id(103));
  assert.equal(row.resource_revision, '3'); assert.equal(row.work_revision, '2'); assert.equal(row.discussion_sequence, '1');
  assert.equal(row.description, detail.description); assert.equal(Object.keys(row).length, 32);
  assert.equal(canonical(productDetailOutcomes(row)), detail.required_outcomes); assert.ok(Object.isFrozen(row));
  badView(result(query, [{...detail, authentication: 'forged'}]));
  badView(result(query, [{...detail, legacy_assignee_principal_id: ''}]));
  badView(result(query, [{...detail, owner_display_name: 'Invented owner'}]));
  badView(result(query, [{...detail, required_outcomes: ' ' + detail.required_outcomes}]));
  const reserved = {...detail, required_outcomes: canonical({[id(401)]: {kind: 'completion-note', project_id: id(100), work_id: id(101), expected_revision: '0'}})};
  assert.throws(() => parseProductView(JSON.stringify(result(query, [reserved])), query), {code: 'unsupported_profile'});
  for (const target of [{kind: 'future-target', project_id: id(100)}, {kind: 'completion-note', project_id: id(100), work_id: id(999), expected_revision: '0'}]) {
    badView(result(query, [{...detail, required_outcomes: canonical({[id(401)]: target})}]));
  }
});
test('query results reject cross-scope rows duplicate resources and partial detail pages', () => {
  for (const changed of [{...detail, project_id: id(999)}, {...detail, resource_id: id(999)}, {...detail, container_id: id(200)}, {...detail, work_revision: '0'}]) badView(result(query, [changed]));
  badView({...result(query, [detail]), request_id: id(999)}); badView({...result(query, [detail]), protocol: 'stead.query-result/3'});
  badView(result(query, [])); badView(result(query, [detail], 'c'.repeat(64)));
  const list = {...query, resource_id: ''};
  assert.equal(parseProductView(JSON.stringify(result(list, [preview])), list).status, 'read');
  badView(result(list, [preview, preview]), list); badView(result(list, [detail]), list);
  badView({...result(list, [preview]), rows: {'00': preview}}, list);
});
test('comments retain ordered twenty-row pages exact bodies and original accepted identity', () => {
  const request = {...query, kind: 'comments' as const};
  const first = parseProductView(JSON.stringify(result(request, Array.from({length: 20}, (_, index) => note(index + 1)), 'c'.repeat(64))), request);
  assert.equal(first.status, 'read'); if (first.status !== 'read' || first.kind !== 'comments') return;
  assert.equal(first.rows[0]!.body, 'Exact comment 1  \n'); assert.equal(first.rows[0]!.legacy_comment_revision, '3');
  assert.equal(first.rows[1]!.legacy_comment_revision, ''); assert.equal(first.rows[19]!.sequence, '20');
  const next = {...request, cursor: first.cursor};
  const second = parseProductView(JSON.stringify(result(next, [note(21), note(22)])), next);
  assert.equal(second.status, 'read');
  badView(result(request, [note(2)]), request); badView(result(request, [note(1), note(3)]), request);
  badView(result(request, [{...note(1), work_id: id(999)}]), request);
  badView(result(request, [{...note(1), receipt: 'secret'}]), request);
  badView(result(request, Array.from({length: 21}, (_, index) => note(index + 1))), request);
});
test('receipts correlate exact request digest scope operation and independent expected revisions', async () => {
  const request = comment(), digest = await productCommandDigest(request), valid = receipt(request, digest);
  assert.equal(parseProductReceipt(JSON.stringify(valid), request, digest).status, 'accepted');
  assert.equal(parseProductReceipt(JSON.stringify({...valid, status: 'rejected', error: 'revision_conflict'}), request, digest).status, 'rejected');
  const unrecorded = {protocol: 'stead.receipt/4', status: 'rejected', request_id: request.request_id, canonical_sha256: digest, error: 'denied_or_not_found'};
  assert.equal(parseProductReceipt(JSON.stringify(unrecorded), request, digest).status, 'rejected');
  for (const changed of [{...valid, protocol: 'stead.receipt/3'}, {...valid, request_id: id(999)}, {...valid, canonical_sha256: 'f'.repeat(64)},
    {...valid, project_id: id(999)}, {...valid, operation: 'work.update-properties'}, {...valid, expected: {discussion_sequence: '1'}},
    {...valid, error: 'revision_conflict'}, {...valid, proof: 'secret'}, {...unrecorded, status: 'accepted'}]) {
    assert.throws(() => parseProductReceipt(JSON.stringify(changed), request, digest), {code: 'invalid_response'});
  }
});
test('prepared retries retain immutable exact bytes without automatic resubmission', async () => {
  let token: string | null = 'session-one', fail = true; const sent: string[] = [];
  const transport: ProductTransport = {currentSession: () => token, query: async () => { throw new Error('Unexpected query'); }, command: async raw => {
    sent.push(raw); if (fail) throw new Error('Response lost'); const request = parseProductCommand(raw); return JSON.stringify(receipt(request, await productCommandDigest(request)));
  }};
  const client = new ProductWorkClient(transport); const draft = {...properties};
  const prepared = await client.prepareProperties(scope, '2', draft); draft.worker_principal_id = id(999);
  assert.equal((prepared.command.payload as ProductProperties).worker_principal_id, '');
  assert.throws(() => { (prepared.command.expected as {work_revision: string}).work_revision = '3'; }, TypeError);
  await assert.rejects(client.submit(prepared), {code: 'outcome_unknown'}); assert.equal(sent.length, 1);
  fail = false; assert.equal((await client.retry(prepared)).status, 'accepted'); assert.deepEqual(sent, [prepared.bytes, prepared.bytes]);
  await assert.rejects(client.submit({...prepared}), {code: 'unrecognized_prepared_command'});
  token = 'session-two'; await assert.rejects(client.retry(prepared), {code: 'session_changed'}); assert.equal(sent.length, 2);
  token = null; await assert.rejects(client.prepareComment(scope, '0', 'Question'), {code: 'session_required'});
});
test('late query and command replies are fenced by the opaque current-session token', async () => {
  let token = {}; let resolve!: (raw: string) => void;
  const transport: ProductTransport = {currentSession: () => token, query: () => new Promise(done => { resolve = done; }), command: () => new Promise(done => { resolve = done; })};
  const client = new ProductWorkClient(transport);
  const pendingRead = client.read(query); token = {}; resolve(JSON.stringify(result(query, [detail])));
  await assert.rejects(pendingRead, {code: 'session_changed'});
  const prepared = await client.prepareComment(scope, '0', 'Question'); const pendingSave = client.submit(prepared);
  token = {}; resolve(JSON.stringify(receipt(prepared.command, prepared.digest))); await assert.rejects(pendingSave, {code: 'session_changed'});
  await assert.rejects(client.retry(prepared), {code: 'session_changed'});
});
test('malformed or cross-request receipts remain unknown and preserve the exact retry', async () => {
  const sent: string[] = [];
  const client = new ProductWorkClient({currentSession: () => 'session', query: async () => { throw new Error('Unexpected query'); }, command: async raw => {
    sent.push(raw);
    if (sent.length === 1) return '{"private-response":"must not appear in error"}';
    const request = parseProductCommand(raw), valid = receipt(request, await productCommandDigest(request));
    return JSON.stringify(sent.length === 2 ? {...valid, request_id: id(999)} : valid);
  }});
  const prepared = await client.prepareComment(scope, '0', 'Question');
  for (let attempt = 0; attempt < 2; attempt++) {
    await assert.rejects(client.retry(prepared), {code: 'outcome_unknown', message: 'outcome_unknown'});
    assert.equal(sent.length, attempt + 1);
  }
  assert.equal((await client.retry(prepared)).status, 'accepted');
  assert.deepEqual(sent, [prepared.bytes, prepared.bytes, prepared.bytes]);
});
test('read scope is snapshotted before transport and typed helpers preserve separate revisions', async () => {
  let resolve!: (raw: string) => void; const sent: string[] = [];
  const client = new ProductWorkClient({currentSession: () => 'session', command: async () => { throw new Error('Unexpected command'); }, query: raw => { sent.push(raw); return new Promise(done => { resolve = done; }); }});
  const mutable = {...query}; const pending = client.read(mutable); mutable.project_id = id(999);
  resolve(JSON.stringify(result(query, [detail]))); assert.equal((await pending).status, 'read'); assert.equal(sent.length, 1);
  const prepared = await Promise.all([client.prepareCreate(scope, properties, contract), client.prepareContract(scope, '7', contract),
    client.prepareLegacyBlocked(scope, '8', 'todo', ''), client.prepareLegacyAssignee(scope, '8', '', ''),
    client.prepareComment(scope, '9', 'Question'), client.prepareCompletion(scope, {work_revision: '8', execution_contract_revision: '7'}, {basis: 'human-note', note: 'Resolved.'}),
    client.prepareDelete(scope, {work_revision: '8', execution_contract_revision: '7', discussion_sequence: '9'})]);
  assert.equal(canonical(prepared[1]!.command.expected), '{"execution_contract_revision":"7"}');
  assert.equal(canonical(prepared[4]!.command.expected), '{"discussion_sequence":"9"}');
});

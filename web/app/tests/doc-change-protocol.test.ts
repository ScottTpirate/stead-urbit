// Source-derived cross-language vectors and host codec checks only.
// No native authorization, read transport or live capability is exercised.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import vectors from './doc-change-vectors.json';
import {DocChangeProtocolError, docChangeCommandDigest, encodeDocChangeCommand, parseDocChangeCommand,
  type DocChangeCommand, type DocChangeDecisionOperation} from '../src/docChangeProtocol';
const id = (n: number) => '019939ba-4000-7000-8000-' + String(n).padStart(12, '0');
const submission = () => structuredClone(vectors.vectors[0]!.command) as Extract<DocChangeCommand, {operation: 'change.submit'}>;
const decision = (operation: DocChangeDecisionOperation = 'change.adopt') => ({...structuredClone(vectors.vectors[1]!.command), operation}) as Exclude<DocChangeCommand, {operation: 'change.submit'}>;
const refused = (value: unknown) => assert.throws(() => encodeDocChangeCommand(value), {code: 'invalid_request'});
const badRaw = (value: string) => assert.throws(() => parseDocChangeCommand(value), DocChangeProtocolError);
const hash = (domain: string, raw: string) => createHash('sha256').update(domain + '\0' + raw).digest('hex');

test('source-derived submission and adoption vectors preserve exact canonical JSON and native hash domain', async () => {
  for (const vector of vectors.vectors) {
    const command = parseDocChangeCommand(JSON.stringify(vector.command));
    assert.equal(encodeDocChangeCommand(command), vector.canonical);
    assert.equal(await docChangeCommandDigest(command), vector.sha256);
    assert.equal(hash('stead.doc-change/1', vector.canonical), vector.sha256);
    assert.notEqual(hash('stead.command/4', vector.canonical), vector.sha256);
    assert.equal(encodeDocChangeCommand(parseDocChangeCommand(' \n' + vector.canonical + '\t')), vector.canonical);
  }
  assert.equal(submission().payload.markdown, 'Exact λ <text>  \n');
  assert.equal(vectors.vectors[0]!.sha256, '8badc6f6292779c5c6b30d119d45fac8b8163647a6a7a6d08029a8efa1764223');
});
test('all seven operations retain closed shapes and explicit decision note rules', () => {
  const first = submission(); assert.equal(parseDocChangeCommand(encodeDocChangeCommand(first)).operation, 'change.submit');
  assert.equal(parseDocChangeCommand(encodeDocChangeCommand({...first, expected_revision: '3'})).expected_revision, '3');
  const operations: DocChangeDecisionOperation[] = ['change.request-changes', 'change.approve', 'change.adopt', 'change.accept', 'change.reject', 'change.quarantine'];
  for (const operation of operations) {
    const value = decision(operation); assert.equal(parseDocChangeCommand(encodeDocChangeCommand(value)).operation, operation);
    const empty = {...value, payload: {...value.payload, note: ''}};
    if (operation === 'change.approve' || operation === 'change.accept') assert.equal(encodeDocChangeCommand(empty).includes('"note":""'), true);
    else refused(empty);
    const missing = structuredClone(value) as any; delete missing.payload.note; refused(missing);
    refused({...value, expected_revision: '0'}); refused({...value, payload: {...value.payload, result_revision: '0'}});
    refused({...value, payload: {...value.payload, note: ' \t\n'}});
  }
  for (const operation of ['change.execute', 'change.publish', 'work.complete', '']) refused({...first, operation});
  refused({...first, protocol: 'stead.command/4'}); refused({...first, protocol: 'stead.doc-change/2'});
});
test('lifecycle result execution and target pins are distinct and all remain in exact request bytes', async () => {
  const value = submission(); value.expected_revision = '7'; value.payload.execution_contract_revision = '3'; value.payload.target.expected_revision = '2';
  const parsed = parseDocChangeCommand(encodeDocChangeCommand(value)); assert.equal(parsed.expected_revision, '7');
  assert.equal(parsed.operation, 'change.submit'); if (parsed.operation !== 'change.submit') throw new Error('Submission expected');
  assert.equal(parsed.payload.execution_contract_revision, '3'); assert.equal(parsed.payload.target.expected_revision, '2');
  const review = decision('change.accept'); review.expected_revision = '9'; review.payload.result_revision = '4';
  assert.equal(parseDocChangeCommand(encodeDocChangeCommand(review)).expected_revision, '9');
  const original = await docChangeCommandDigest(value);
  for (const changed of [{...value, request_id: id(301)}, {...value, work_id: id(102)}, {...value, change_id: id(402)},
    {...value, authority_epoch: '2'}, {...value, expected_revision: '8'}, {...value, payload: {...value.payload, outcome_id: id(403)}},
    {...value, payload: {...value.payload, execution_contract_digest: 'd'.repeat(64)}},
    {...value, payload: {...value.payload, target: {...value.payload.target, base_markdown_sha256: 'e'.repeat(64)}}}]) {
    assert.notEqual(await docChangeCommandDigest(changed), original);
  }
  const reviewed = await docChangeCommandDigest(review);
  assert.notEqual(await docChangeCommandDigest({...review, payload: {...review.payload, result_digest: 'd'.repeat(64)}}), reviewed);
});
test('document targets preserve same-project exact bases and reject alternate kinds or claimed visibility', () => {
  const value = submission(), target = value.payload.target;
  const fresh = {...target, expected_revision: '0', base_markdown_sha256: ''};
  assert.ok(encodeDocChangeCommand({...value, payload: {...value.payload, target: fresh}}));
  for (const changed of [{...target, project_id: id(999)}, {...target, expected_revision: '0'}, {...fresh, expected_revision: '1'},
    {...target, collection_id: ''}, {...target, document_id: 'latest'}, {...target, base_markdown_sha256: 'A'.repeat(64)},
    {...target, kind: 'code'}, {...target, visibility: 'shared'}, {...target, visibility: 'private'},
    {kind: 'completion-note', project_id: value.project_id, work_id: value.work_id, expected_revision: '1'}]) {
    refused({...value, payload: {...value.payload, target: changed}});
  }
  // Collection visibility is resolved by Home, not inferred from this UUID.
  assert.ok(encodeDocChangeCommand({...value, payload: {...value.payload, target: {...target, collection_id: id(202)}}}));
});
test('run pairs carry provenance intent without admitting caller-supplied authority or acceptance context', () => {
  const value = submission(); assert.ok(encodeDocChangeCommand(value));
  assert.ok(encodeDocChangeCommand({...value, payload: {...value.payload, run_id: id(500), attempt: '1'}}));
  for (const pair of [{run_id: id(500), attempt: '0'}, {run_id: '', attempt: '1'}, {run_id: 'latest', attempt: '1'}]) refused({...value, payload: {...value.payload, ...pair}});
  for (const field of ['producer_principal_id', 'principal_kind', 'owner_principal_id', 'authentication', 'recorded_at_ms', 'lease', 'approval', 'checks', 'accept_context', 'proof']) {
    refused({...value, [field]: 'claimed'}); refused({...value, payload: {...value.payload, [field]: 'claimed'}});
    const accept = decision('change.accept'); refused({...accept, payload: {...accept.payload, [field]: 'claimed'}});
  }
});
test('uint64 string pins reject lossy numbers signs leading zeros and overflow at every level', () => {
  const max = '18446744073709551615', value = submission();
  assert.ok(encodeDocChangeCommand({...value, authority_epoch: max, expected_revision: max,
    payload: {...value.payload, execution_contract_revision: max, run_id: id(500), attempt: max, target: {...value.payload.target, expected_revision: max}}}));
  const wrong: unknown[] = ['', '01', '+1', '-1', '1.0', '1e3', ' 1', '1 ', '18446744073709551616', '١', 1, 9007199254740993, null, true];
  for (const pin of wrong) {
    refused({...value, authority_epoch: pin}); refused({...value, expected_revision: pin});
    refused({...value, payload: {...value.payload, attempt: pin}});
    refused({...value, payload: {...value.payload, execution_contract_revision: pin}});
    refused({...value, payload: {...value.payload, target: {...value.payload.target, expected_revision: pin}}});
    const review = decision(); refused({...review, payload: {...review.payload, result_revision: pin}});
  }
  refused({...value, authority_epoch: '0'}); refused({...value, payload: {...value.payload, execution_contract_revision: '0'}});
  for (const field of ['request_id', 'project_id', 'work_id', 'change_id']) {
    refused({...value, [field]: id(100).replace('-7000-', '-4000-')}); refused({...value, [field]: id(100).toUpperCase()});
  }
});
test('bounded parser rejects duplicate decoded keys unknown fields arrays scalars and extra nesting', () => {
  const raw = encodeDocChangeCommand(submission());
  badRaw('{"protocol":"stead.doc-change/1",' + raw.slice(1));
  badRaw(raw.replace('"summary":', '"summary":"first","summary":'));
  badRaw(raw.replace('"kind":', '"kind":"document","k\\u0069nd":'));
  badRaw(raw.replace('"expected_revision":"0"', '"expected_revision":0'));
  badRaw(raw.replace('"markdown":"Exact λ <text>  \\n"', '"markdown":["body"]'));
  badRaw(raw + '{}'); badRaw('[]'); badRaw('{"a":{"b":{"c":{"d":{"e":"x"}}}}}');
  refused({...submission(), payload: {...submission().payload, markdown: {text: 'body'}}});
  refused({...submission(), payload: {...submission().payload, markdown: 'body', extra: ''}});
  const sixteen = Object.fromEntries(Array.from({length: 17}, (_, i) => ['key' + i, 'x'])); badRaw(JSON.stringify(sixteen));
});
test('Markdown explanations and whole wire enforce native UTF-8 byte bounds without text normalization', () => {
  const value = submission();
  for (const markdown of ['', 'x'.repeat(32768), 'λ'.repeat(16384), '\u0001\t\n\b\f\u001f\u2028😀']) {
    const accepted = {...value, payload: {...value.payload, markdown}};
    assert.equal((parseDocChangeCommand(encodeDocChangeCommand(accepted)) as typeof value).payload.markdown, markdown);
  }
  for (const markdown of ['x'.repeat(32769), 'λ'.repeat(16384) + 'x', 'line\r\n', '\0', '\ud800', '\udfff']) refused({...value, payload: {...value.payload, markdown}});
  for (const summary of ['x'.repeat(2048), 'λ'.repeat(1024), '\u00a0']) assert.ok(encodeDocChangeCommand({...value, payload: {...value.payload, summary}}));
  for (const summary of ['', ' \t\n', 'x'.repeat(2049), 'λ'.repeat(1024) + 'x', 'word\r', 'word\u0001', '\ud800']) refused({...value, payload: {...value.payload, summary}});
  const raw = encodeDocChangeCommand(value), size = Buffer.byteLength(raw);
  assert.equal(encodeDocChangeCommand(parseDocChangeCommand(raw + ' '.repeat(65536 - size))), raw);
  badRaw(raw + ' '.repeat(65537 - size));
  const escaped = {...value, payload: {...value.payload, markdown: '\u0001'.repeat(32768)}};
  refused(escaped); // Canonical escape expansion still has the 64KiB envelope bound.
});
test('Unicode escapes and source bytes remain exact while NUL and lone surrogate decoding fail', async () => {
  const value = submission(), raw = encodeDocChangeCommand(value);
  assert.equal(encodeDocChangeCommand(parseDocChangeCommand(raw.replace('λ', '\\u03bb'))), raw);
  assert.equal(encodeDocChangeCommand(parseDocChangeCommand(raw.replace('<text>', '\\u003ctext>'))), raw);
  for (const text of ['\\u0000', '\\ud800', '\\udfff', '\\ud800x', '\\uZZZZ']) badRaw(raw.replace('Exact λ <text>  \\n', text));
  const composed = {...value, payload: {...value.payload, markdown: 'é'}}, decomposed = {...value, payload: {...value.payload, markdown: 'e\u0301'}};
  assert.notEqual(await docChangeCommandDigest(composed), await docChangeCommandDigest(decomposed));
  assert.notEqual(await docChangeCommandDigest({...value, payload: {...value.payload, markdown: value.payload.markdown.trimEnd()}}), await docChangeCommandDigest(value));
});
test('decoded commands are isolated deeply frozen intents and encoding never invokes authored getters', () => {
  const input = submission(), encoded = encodeDocChangeCommand(input), parsed = parseDocChangeCommand(encoded);
  input.payload.markdown = 'Later local edit';
  assert.equal(encodeDocChangeCommand(parsed), encoded); assert.ok(Object.isFrozen(parsed)); assert.ok(Object.isFrozen(parsed.payload));
  if (parsed.operation !== 'change.submit') throw new Error('Submission expected'); assert.ok(Object.isFrozen(parsed.payload.target));
  assert.throws(() => { parsed.payload.markdown = 'Mutation'; }, TypeError);
  let calls = 0; const getter = {...submission()}; Object.defineProperty(getter, 'payload', {enumerable: true, get: () => { calls++; return {}; }});
  refused(getter); assert.equal(calls, 0);
  refused({...submission(), [Symbol('proof')]: 'secret'}); refused(Object.assign(Object.create({authority: 'inherited'}), submission()));
});

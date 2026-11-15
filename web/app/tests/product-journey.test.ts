// Host boundary/state tests. The injected reads are not native authorization.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import type {HomeClient} from '../src/api';
import {DocChangeClient} from '../src/docChangeClient';
import {encodeDocChangeCommand} from '../src/docChangeProtocol';
import {ProductJourneyDraftStore, currentProposalPin, journeyActor, journeyCompletion, journeyDocumentKey, journeyDocuments, journeyPeople,
  journeyRoster, proposalCommand, proposalMatchesWork, restoreDocProposal, type DocProposalDraft} from '../src/productJourneyState';
import {makeProductWorkDraft} from '../src/productWorkState';
import type {DocumentOutcome, ProductPrincipal, ProductView, ProductWorkDetail} from '../src/productProtocol';
import {productJSON} from '../src/productWire';

const id = (n: number) => '019939ba-4000-7000-8000-' + String(n).padStart(12, '0');
const project = id(100), workId = id(101), collection = id(200), documentId = id(201), session = 'current-session';
const markdown = `---\nid: ${documentId}\ntype: page\nstate: published\n---\n# Guide\nExact λ text  \n`;
const digest = createHash('sha256').update(markdown).digest('hex');
const target: DocumentOutcome = {kind: 'document', project_id: project, collection_id: collection, document_id: documentId, expected_revision: '1', base_markdown_sha256: digest};
const work: ProductWorkDetail = {kind: 'work', project_id: project, resource_id: workId, container_id: '', resource_revision: '3', work_revision: '1',
  execution_contract_protocol: 'stead.work-contract/2', execution_contract_revision: '1', execution_contract_digest: 'a'.repeat(64), discussion_sequence: '1',
  title: 'Guide', description: 'Purpose', acceptance_criteria: 'Reviewed', type: 'task', status: 'todo', priority: 'none',
  owner_principal_id: '', worker_principal_id: '', owner_display_name: '', worker_display_name: '', blocked_reason: '', required_outcomes: productJSON({[id(300)]: target}),
  completion_basis: '', completion_principal_id: '', completion_request_id: '', completion_note: '', legacy_assignment_pending: 'no',
  legacy_assignee_principal_id: '', legacy_assignee_display_name: '', legacy_blocked_pending: 'no', legacy_blocked_status: '', legacy_prior_status: ''};
const makeProposal = (): DocProposalDraft => ({scope: {projectId: project, workId, changeId: id(400)}, sessionKey: session,
  base: {authorityEpoch: '1', headRevision: '2', executionContractRevision: '1', executionContractDigest: work.execution_contract_digest, outcomeId: id(300), target: {...target}},
  markdown, summary: 'Exact summary', dirty: true, conflicted: false});
const docClient = () => new DocChangeClient({currentSession: () => session,
  capabilities: () => ({queries: 'stead.doc-change-query/1', commands: 'stead.doc-change/1'}),
  query: async () => { throw new Error('Unexpected query'); }, command: async () => { throw new Error('Unexpected command'); }});
const rows = (values: Record<string, string>[]) => Object.fromEntries(values.map((value, index) => [String(index), value]));
const view = (values: Record<string, string>[], cursor = '', epoch = '1', generation = 'a'.repeat(64)) => ({rows: rows(values), cursor, authority_epoch: epoch, generation});

test('draft partitions reject late writes after session change and preserve resource separation', () => {
  const store = new ProductJourneyDraftStore(); store.bind(session);
  const draft = makeProductWorkDraft({projectId: project, resourceId: workId, authorityEpoch: '1'}, session, work);
  draft.contract.dirty = true; draft.contract.value.description = 'Private local draft';
  assert.equal(store.putWork(draft), true); assert.equal(store.getWork(project, workId), draft);
  assert.equal(store.getWork(project, id(999)), undefined); assert.equal(store.hasDraft(project), true);
  store.bind('new-session'); assert.equal(store.hasDraft(), false); assert.equal(store.putWork(draft), false);
  assert.equal(store.getWork(project, workId), undefined);
});

test('proposal remount and store retain the original unknown request without allowing discard', async () => {
  const draft = makeProposal(), prepared = await docClient().prepare(proposalCommand(draft, id(401)));
  draft.attempt = {phase: 'saving', prepared, message: ''};
  const store = new ProductJourneyDraftStore(); store.bind(session); store.putProposal(draft);
  const restored = restoreDocProposal(draft.scope, session, store.getProposal(draft.scope))!;
  assert.equal(restored.attempt?.phase, 'unknown'); assert.equal(restored.attempt?.prepared, prepared);
  assert.equal(restored.attempt?.prepared?.bytes, prepared.bytes); assert.equal(store.currentPending(project), true);
  assert.equal(store.discard(project), false); assert.equal(store.workProposal(project, workId), draft);
  store.putProposal({...restored, dirty: false, attempt: {phase: 'accepted', prepared, message: '', awaitingReadback: false}});
  assert.equal(store.discard(project), true); assert.equal(store.getProposal(draft.scope), undefined);
});

test('accepted readback and full draft capacity cannot silently evict unresolved Work', () => {
  const store = new ProductJourneyDraftStore(); store.bind(session);
  for (let index = 0; index < 32; index++) {
    const draft = makeProductWorkDraft({projectId: project, resourceId: id(500 + index), authorityEpoch: '1'}, session);
    draft.attempt = {section: 'create', phase: 'accepted', awaitingReadback: true, message: ''}; store.putWork(draft);
  }
  assert.equal(store.hasDraft(), true); assert.equal(store.currentPending(), true); assert.equal(store.discard(), false);
  assert.throws(() => store.putWork(makeProductWorkDraft({projectId: project, resourceId: id(600), authorityEpoch: '1'}, session)), /draft_limit/u);
  assert.equal(store.newWork(project)?.resourceId, id(500)); store.clear(); assert.equal(store.currentPending(), false);
});

test('proposal restoration never crosses session or scope and never turns an unprepared draft into a retry', () => {
  const draft = makeProposal(); draft.attempt = {phase: 'preparing', message: ''};
  assert.equal(restoreDocProposal(draft.scope, 'different', draft), undefined);
  assert.equal(restoreDocProposal({...draft.scope, changeId: id(999)}, session, draft), undefined);
  const restored = restoreDocProposal(draft.scope, session, draft)!;
  assert.equal(restored.attempt, undefined); assert.equal(restored.markdown, markdown); assert.equal(restored.base, draft.base);
});

test('proposal comparison exposes changed target pins while original submit bytes keep exact provenance', () => {
  const draft = makeProposal(); assert.equal(proposalMatchesWork(draft, work, '1'), true);
  const changed = {...work, execution_contract_revision: '2', execution_contract_digest: 'b'.repeat(64),
    required_outcomes: productJSON({[id(300)]: {...target, expected_revision: '2', base_markdown_sha256: 'c'.repeat(64)}})};
  const next = currentProposalPin(draft, changed, '2', '4')!;
  assert.equal(proposalMatchesWork(draft, changed, '2'), false); assert.equal(next.headRevision, '4'); assert.equal(next.target.expected_revision, '2');
  assert.equal(draft.base.target.expected_revision, '1'); assert.equal(currentProposalPin(draft, {...changed, required_outcomes: '{}'}, '2'), undefined);
  const command = proposalCommand(draft, id(402)); assert.equal(command.expected_revision, '2');
  assert.equal(command.operation, 'change.submit'); if (command.operation !== 'change.submit') throw new Error('Wrong operation');
  assert.equal(command.payload.markdown, markdown); assert.equal(command.payload.execution_contract_revision, '1');
  assert.equal(command.payload.run_id, ''); assert.equal(command.payload.attempt, '0');
  const parsed = JSON.parse(encodeDocChangeCommand(command)); assert.equal(parsed.payload.markdown, markdown); assert.equal('producer' in parsed, false);
});

test('typed roster choices never infer a human or agent from a name or legacy role', () => {
  const principal = (n: number, kind: ProductPrincipal['principal_kind'], active: 'yes' | 'no' = 'yes', role: ProductPrincipal['project_role'] = 'contributor'): ProductPrincipal =>
    ({kind: 'principal', principal_id: id(n), display_name: 'Human-looking name', principal_kind: kind, active, project_role: role});
  const roster = [principal(700, 'person'), principal(701, 'agent'), principal(702, 'service'), principal(703, 'unresolved'), principal(704, 'person', 'no'), principal(705, 'person', 'yes', 'reader')];
  assert.deepEqual(journeyPeople(roster).map(row => row.principalId), [id(700), id(701)]);
  assert.equal(journeyActor(roster, id(701)).kind, 'agent'); assert.equal(journeyActor(roster, id(702)).kind, 'unknown');
  assert.equal(journeyActor([], id(700)).kind, 'unknown');
});

test('completion readiness binds exact authority and contract while ordinary discussion remains independent', () => {
  const completion = {kind: 'completion', authority_epoch: '1', rows: [{kind: 'completion', project_id: project, work_id: workId,
    execution_contract_revision: '1', execution_contract_digest: work.execution_contract_digest, ready: 'yes', reason: ''}]} as Extract<ProductView, {kind: 'completion'}>;
  assert.equal(journeyCompletion(completion, {...work, discussion_sequence: '50'}, session, '1').state, 'ready');
  assert.throws(() => journeyCompletion(completion, {...work, execution_contract_revision: '2'}, session, '1'));
  assert.throws(() => journeyCompletion(completion, work, session, '2'));
  assert.throws(() => journeyCompletion(completion, {...work, resource_id: id(999)}, session, '1'));
});

test('shared Doc choices use exact authorized body bytes and never enumerate a private collection', async () => {
  const calls: string[] = [];
  const client = {query: async (query: {kind: string; container_id: string}) => {
    calls.push(query.kind + ':' + query.container_id);
    if (query.kind === 'containers') return view([{container_id: collection, visibility: 'shared'}, {container_id: id(202), visibility: 'private'}]);
    if (query.kind === 'documents') { assert.equal(query.container_id, collection); return view([{resource_id: documentId, resource_revision: '1', title: 'Guide'}]); }
    assert.equal(query.kind, 'document'); return view([{kind: 'document', resource_id: documentId, container_id: collection, resource_revision: '1', markdown}]);
  }} as unknown as HomeClient;
  const result = await journeyDocuments(client, project, '1', () => {});
  assert.equal(result.choices.length, 1); assert.deepEqual(result.choices[0]?.target, target);
  assert.equal(result.markdown.get(journeyDocumentKey(target)), markdown); assert.equal(calls.some(call => call.includes(id(202))), false);
});

test('roster scan rejects repeated cursors, changed epochs and late replies before publishing a partial roster', async () => {
  let count = 0;
  const repeated = {productWork: {readPrincipals: async () => ({status: 'read', kind: 'principals', authority_epoch: '1', generation: 'a'.repeat(64), cursor: 'b'.repeat(64), rows: []})}} as unknown as HomeClient;
  await assert.rejects(journeyRoster(repeated, project, '1', () => { count++; }), /invalid_response/u); assert.equal(count, 2);
  const wrongEpoch = {productWork: {readPrincipals: async () => ({status: 'read', kind: 'principals', authority_epoch: '2', generation: 'a'.repeat(64), cursor: '', rows: []})}} as unknown as HomeClient;
  await assert.rejects(journeyRoster(wrongEpoch, project, '1', () => {}), /stale_cursor/u);
  await assert.rejects(journeyRoster(repeated, project, '1', () => { throw new Error('view_changed'); }), /view_changed/u);
});

test('Doc scan budget counts unsupported bodies and rejects the entire over-budget picker', async () => {
  let exactReads = 0;
  const client = {query: async (query: {kind: string; cursor: string; resource_id: string}) => {
    if (query.kind === 'containers') return view([{container_id: collection, visibility: 'shared'}]);
    if (query.kind === 'documents') {
      const page = query.cursor ? Number(query.cursor) : 0;
      return view(Array.from({length: page === 6 ? 9 : 20}, (_, n) => ({resource_id: id(1000 + page * 20 + n), title: 'Too large'})), page === 6 ? '' : String(page + 1));
    }
    exactReads++;
    return view([{kind: 'document', resource_id: query.resource_id, container_id: collection, resource_revision: '1', markdown: 'x'.repeat(32769)}]);
  }} as unknown as HomeClient;
  await assert.rejects(journeyDocuments(client, project, '1', () => {}), /invalid_response/u);
  assert.equal(exactReads, 128);
});

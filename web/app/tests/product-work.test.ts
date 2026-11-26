// Host state tests only. Injected transport is not native authorization.
import test from 'node:test';
import assert from 'node:assert/strict';
import {ProductWorkClient} from '../src/productClient';
import type {ProductReceipt, ProductWorkDetail} from '../src/productProtocol';
import {advanceProductWorkGeneration, adoptProductWorkBase, makeProductWorkDraft, productWorkConflict, productWorkSectionEpoch, productCompletionReady, productWorkDocuments, productWorkPeople,
  reconcileProductWorkDraft, restoreProductWorkDraft, type ProductWorkChoices, type ProductWorkDocChoice, type ProductWorkPerson} from '../src/productWorkState';
const id = (n: number) => '019939ba-4000-7000-8000-' + String(n).padStart(12, '0');
const scope = {projectId: id(100), resourceId: id(101), authorityEpoch: '1'};
const work: ProductWorkDetail = {kind: 'work', project_id: id(100), resource_id: id(101), container_id: '', resource_revision: '3', work_revision: '1',
  execution_contract_protocol: 'stead.work-contract/2', execution_contract_revision: '1', execution_contract_digest: 'a'.repeat(64), discussion_sequence: '1',
  title: 'Guide', description: 'Exact λ notes  \n', acceptance_criteria: 'Reviewed', type: 'task', status: 'todo', priority: 'none',
  owner_principal_id: '', worker_principal_id: '', owner_display_name: '', worker_display_name: '', blocked_reason: '', required_outcomes: '{}',
  completion_basis: '', completion_principal_id: '', completion_request_id: '', completion_note: '', legacy_assignment_pending: 'no',
  legacy_assignee_principal_id: '', legacy_assignee_display_name: '', legacy_blocked_pending: 'no', legacy_blocked_status: '', legacy_prior_status: ''};
const client = () => new ProductWorkClient({currentSession: () => 'session-one', query: async () => { throw new Error('Unexpected transport'); }, command: async () => { throw new Error('Unexpected transport'); }});
test('new drafts have title-only defaults and never restore another session or resource', () => {
  const draft = makeProductWorkDraft(scope, 'session-one');
  assert.deepEqual(draft.properties.value, {type: 'task', status: 'todo', priority: 'none', owner_principal_id: '', worker_principal_id: '', blocked_reason: ''});
  assert.equal(draft.contract.value.title, ''); assert.deepEqual(draft.contract.value.required_outcomes, {});
  draft.contract.value.description = 'Private local text'; draft.contract.dirty = true;
  assert.equal(restoreProductWorkDraft(scope, 'session-one', undefined, draft), draft);
  assert.equal(restoreProductWorkDraft(scope, 'session-two', undefined, draft).contract.value.description, '');
  assert.equal(restoreProductWorkDraft({...scope, resourceId: id(999)}, 'session-one', undefined, draft).contract.value.description, '');
});
test('remount preserves an unresolved prepared request as unknown with the same object and bytes', async () => {
  const prepared = await client().prepareComment({request_id: id(301), project_id: id(100), resource_id: id(101), authority_epoch: '1'}, '1', 'Exact question  \n');
  const draft = makeProductWorkDraft(scope, 'session-one', work); draft.discussion = {...draft.discussion, value: 'Exact question  \n', dirty: true};
  draft.attempt = {section: 'discussion', phase: 'saving', prepared, message: ''};
  const restored = restoreProductWorkDraft(scope, 'session-one', work, draft);
  assert.equal(restored.attempt?.phase, 'unknown'); assert.equal(restored.attempt?.prepared, prepared);
  assert.equal(restored.attempt?.prepared?.bytes, prepared.bytes); assert.equal(restored.discussion.value, draft.discussion.value);
  const preparing = {...draft, attempt: {section: 'discussion' as const, phase: 'preparing' as const, message: ''}};
  assert.equal(restoreProductWorkDraft(scope, 'session-one', work, preparing).attempt, undefined);
});
test('comment and property refreshes retain an independently edited purpose and its original contract pin', () => {
  const draft = makeProductWorkDraft(scope, 'session-one', work);
  draft.contract = {...draft.contract, dirty: true, value: {...draft.contract.value, description: 'Local purpose  \n'}};
  const next = reconcileProductWorkDraft(draft, {...work, work_revision: '2', discussion_sequence: '2', status: 'in_progress'});
  assert.equal(next.contract, draft.contract); assert.equal(next.contract.base, '1'); assert.equal(next.contract.value.description, 'Local purpose  \n');
  assert.equal(next.properties.base, '2'); assert.equal(next.properties.value.status, 'in_progress'); assert.equal(next.discussion.base, '2');
});
test('accepted property readback clears only that section and keeps purpose and comment drafts intact', async () => {
  const draft = makeProductWorkDraft(scope, 'session-one', work);
  draft.properties = {...draft.properties, dirty: true, value: {...draft.properties.value, priority: 'high'}};
  draft.contract = {...draft.contract, dirty: true, value: {...draft.contract.value, description: 'Unsubmitted purpose'}};
  draft.discussion = {...draft.discussion, value: 'Unposted question', dirty: true};
  const prepared = await client().prepareProperties({request_id: id(302), project_id: id(100), resource_id: id(101), authority_epoch: '1'}, '1', {...draft.properties.value, status: 'todo'});
  const receipt: ProductReceipt = {protocol: 'stead.receipt/4', status: 'accepted', request_id: id(302), canonical_sha256: prepared.digest,
    project_id: id(100), resource_id: id(101), authority_epoch: '1', operation: 'work.update-properties', principal_id: id(102), recorded_at_ms: '1000', error: '',
    expected: {work_revision: '1'}, resulting: {work_revision: '2', execution_contract_revision: '1', discussion_sequence: '1', execution_contract_digest: 'a'.repeat(64)}};
  draft.attempt = {section: 'properties', phase: 'accepted', prepared, receipt, awaitingReadback: true, message: ''};
  const unchanged = reconcileProductWorkDraft(draft, work); assert.equal(unchanged.attempt?.awaitingReadback, true); assert.equal(unchanged.properties.dirty, true);
  const updated = reconcileProductWorkDraft(draft, {...work, work_revision: '2', priority: 'high'});
  assert.equal(updated.properties.dirty, false); assert.equal(updated.properties.value.priority, 'high'); assert.equal(updated.attempt?.awaitingReadback, false);
  assert.equal(updated.contract, draft.contract); assert.equal(updated.discussion, draft.discussion);
});
test('explicit conflict adoption retains text and rejected attempt while changing only the chosen base', async () => {
  const draft = makeProductWorkDraft(scope, 'session-one', work); draft.contract.dirty = true; draft.contract.value.description = 'Exact local draft  \n';
  const prepared = await client().prepareContract({request_id: id(303), project_id: id(100), resource_id: id(101), authority_epoch: '1'}, '1', draft.contract.value);
  draft.attempt = {section: 'contract', phase: 'conflict', prepared, message: 'Changed', receipt: {protocol: 'stead.receipt/4', status: 'rejected', request_id: id(303), canonical_sha256: prepared.digest, error: 'revision_conflict'}};
  const changed = {...work, work_revision: '3', execution_contract_revision: '2', execution_contract_digest: 'b'.repeat(64), discussion_sequence: '4'};
  const adopted = adoptProductWorkBase(draft, 'contract', changed);
  assert.equal(adopted.contract.base, '2'); assert.equal(adopted.contract.digest, changed.execution_contract_digest); assert.equal(adopted.contract.value.description, 'Exact local draft  \n');
  assert.equal(adopted.properties.base, '1'); assert.equal(adopted.discussion.base, '1'); assert.equal(adopted.previousAttempt, draft.attempt);
  assert.equal(adopted.attempt, undefined);
  draft.attempt.phase = 'unknown'; assert.equal(adoptProductWorkBase(draft, 'contract', changed), draft);
});
test('owner worker and shared Doc choices keep eligibility and project session scope distinct', () => {
  const people: ProductWorkChoices<ProductWorkPerson> = {state: 'ready', projectId: id(100), sessionKey: 'session-one', values: [
    {principalId: id(102), displayName: 'Alice', kind: 'person', active: true}, {principalId: id(103), displayName: 'Worker', kind: 'agent', active: true},
    {principalId: id(104), displayName: 'Inactive', kind: 'person', active: false}]};
  assert.deepEqual(productWorkPeople(people, 'owner', id(100), 'session-one').map(row => row.principalId), [id(102)]);
  assert.deepEqual(productWorkPeople(people, 'worker', id(100), 'session-one').map(row => row.principalId), [id(102), id(103)]);
  assert.deepEqual(productWorkPeople(people, 'worker', id(999), 'session-one'), []); assert.deepEqual(productWorkPeople(people, 'worker', id(100), 'session-two'), []);
  const choice: ProductWorkDocChoice = {label: 'Guide', visibility: 'shared', target: {kind: 'document', project_id: id(100), collection_id: id(200), document_id: id(201), expected_revision: '1', base_markdown_sha256: 'c'.repeat(64)}};
  const docs: ProductWorkChoices<ProductWorkDocChoice> = {state: 'ready', projectId: id(100), sessionKey: 'session-one', values: [choice, {...choice, visibility: 'private'} as unknown as ProductWorkDocChoice, {...choice, target: {...choice.target, project_id: id(999)}}]};
  assert.deepEqual(productWorkDocuments(docs, id(100), 'session-one'), [choice]); assert.deepEqual(productWorkDocuments(docs, id(100), 'session-two'), []);
});
test('accepted-output readiness is advisory only for the exact current session and execution pin', () => {
  const ready = {state: 'ready' as const, projectId: id(100), resourceId: id(101), sessionKey: 'session-one', executionContractRevision: '1', executionContractDigest: 'a'.repeat(64)};
  assert.equal(productCompletionReady(undefined, work, 'session-one'), false); assert.equal(productCompletionReady(ready, work, 'session-one'), true);
  for (const changed of [{...ready, state: 'pending' as const}, {...ready, projectId: id(999)}, {...ready, resourceId: id(999)}, {...ready, sessionKey: 'session-two'},
    {...ready, executionContractRevision: '2'}, {...ready, executionContractDigest: 'b'.repeat(64)}]) assert.equal(productCompletionReady(changed, work, 'session-one'), false);
  assert.equal(productCompletionReady(ready, {...work, discussion_sequence: '2'}, 'session-one'), true);
});
test('refresh and base adoption cannot publish a different resource into a retained draft', () => {
  const draft = makeProductWorkDraft(scope, 'session-one', work); draft.contract.dirty = true; draft.contract.value.title = 'Private local title';
  const other = {...work, project_id: id(999), resource_id: id(998), title: 'Other resource', work_revision: '7'};
  assert.equal(reconcileProductWorkDraft(draft, other), draft); assert.equal(adoptProductWorkBase(draft, 'contract', other), draft);
  assert.equal(draft.contract.value.title, 'Private local title'); assert.equal(draft.contract.base, '1');
});

test('a returning view cannot reuse an earlier request generation or clear its newer in-flight owner', async () => {
  const client = {};
  let view = advanceProductWorkGeneration(undefined, 'A', client, '1');
  const oldGeneration = view.generation;
  let release!: () => void;
  const delayed = new Promise<void>(resolve => { release = resolve; });
  let callbacks = 0, running: number | null = oldGeneration;
  const old = delayed.then(() => { if (view.generation === oldGeneration) callbacks++; })
    .finally(() => { if (view.generation === oldGeneration && running === oldGeneration) running = null; });
  view = advanceProductWorkGeneration(view, 'B', client, '1');
  view = advanceProductWorkGeneration(view, 'A', client, '1');
  running = view.generation; release(); await old;
  assert.equal(callbacks, 0); assert.equal(running, view.generation);
  const same = advanceProductWorkGeneration(view, 'A', client, '1'); assert.equal(same, view);
  const newClient = advanceProductWorkGeneration(view, 'A', {}, '1'); assert.ok(newClient.generation > view.generation);
  const newEpoch = advanceProductWorkGeneration(newClient, 'A', newClient.client, '2'); assert.ok(newEpoch.generation > newClient.generation);
});
test('authority conflict needs explicit section adoption even when all Work revisions are unchanged', () => {
  let draft = makeProductWorkDraft(scope, 'session-one', work);
  draft.contract = {...draft.contract, dirty: true, value: {...draft.contract.value, description: 'Exact local purpose'}};
  draft = productWorkConflict(draft, 'contract');
  const refreshed = reconcileProductWorkDraft(draft, work, '2');
  assert.equal(refreshed.contract.base, '1'); assert.equal(productWorkSectionEpoch(refreshed, 'contract'), '1');
  assert.equal(refreshed.conflicts.contract, true); assert.equal(refreshed.properties.authorityEpoch, '2');
  const adopted = adoptProductWorkBase(refreshed, 'contract', work, '2');
  assert.equal(adopted.contract.value.description, 'Exact local purpose'); assert.equal(adopted.contract.base, '1');
  assert.equal(adopted.contract.authorityEpoch, '2'); assert.equal(adopted.conflicts.contract, undefined);
  const untouchedConflict = productWorkConflict(makeProductWorkDraft(scope, 'session-one', work), 'legacy-assignment');
  const currentAccess = reconcileProductWorkDraft(untouchedConflict, {...work, work_revision: '2'}, '2');
  assert.equal(currentAccess.legacyAssignment.base, '1'); assert.equal(currentAccess.legacyAssignment.authorityEpoch, '1');
  assert.equal(currentAccess.conflicts['legacy-assignment'], true);
  const unknown = {...refreshed, attempt: {section: 'contract' as const, phase: 'unknown' as const, message: 'Unconfirmed'}};
  assert.equal(adoptProductWorkBase(unknown, 'contract', work, '2'), unknown);
});

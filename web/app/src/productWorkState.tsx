// Reserved product Work UI state. A reviewed carrier must supply capability,
// current access and scoped reads before a caller mounts these components.
import {useEffect, useRef, useState} from 'react';
import {ProductClientError, type PreparedProductCommand, type ProductWorkClient} from './productClient';
import {productDetailOutcomes, type DocumentOutcome, type ProductCommand, type ProductComment, type ProductContract,
  type ProductProperties, type ProductReceipt, type ProductStatus, type ProductWorkDetail, type UnfinishedStatus} from './productProtocol';

export type ProductWorkScope = {projectId: string; resourceId: string; authorityEpoch: string};
export type ProductWorkPerson = {principalId: string; displayName: string; kind: 'person' | 'agent'; active: boolean};
export type ProductWorkDocChoice = {label: string; visibility: 'shared'; target: DocumentOutcome};
export type ProductWorkChoices<T> = {projectId: string; sessionKey: string} & ({state: 'ready'; values: readonly T[]} | {state: 'loading' | 'unavailable'; values?: never});
export type ProductWorkSection = 'create' | 'properties' | 'contract' | 'discussion' | 'completion' | 'legacy-blocked' | 'legacy-assignment';
export type ProductWorkPropertyDraft = Omit<ProductProperties, 'status'> & {status: ProductStatus | 'legacy-blocked'};
type RevisionDraft<T> = {authorityEpoch: string; base: string; value: T; dirty: boolean};
export type ProductWorkAttempt = {section: ProductWorkSection; phase: 'preparing' | 'saving' | 'unknown' | 'conflict' | 'rejected' | 'accepted' | 'revoked';
  authorityEpoch?: string; prepared?: PreparedProductCommand; receipt?: ProductReceipt; message: string; awaitingReadback?: boolean};
export type ProductWorkDraft = {
  projectId: string; resourceId: string; sessionKey: string; authorityEpoch: string; conflicts: Partial<Record<ProductWorkSection, true>>;
  properties: RevisionDraft<ProductWorkPropertyDraft>;
  contract: RevisionDraft<ProductContract> & {digest: string};
  discussion: RevisionDraft<string>;
  completion: {authorityEpoch: string; workBase: string; contractBase: string; digest: string; note: string; dirty: boolean};
  legacyBlocked: RevisionDraft<{status: '' | UnfinishedStatus; reason: string}>;
  legacyAssignment: RevisionDraft<{owner: string; worker: string}>;
  attempt?: ProductWorkAttempt;
  previousAttempt?: ProductWorkAttempt;
};
export type ProductWorkReadiness = {state: 'loading' | 'ready' | 'pending' | 'unsupported'; projectId: string; resourceId: string; sessionKey: string;
  executionContractRevision: string; executionContractDigest: string};
export type ProductWorkComments = {state: 'loading' | 'ready' | 'unavailable'; projectId: string; resourceId: string; sessionKey: string; rows: readonly ProductComment[]; cursor: string;
  onNext: () => void; onRefresh: () => void};
export type ProductWorkEnvironment = {
  client: ProductWorkClient; scope: ProductWorkScope; sessionKey: string; supported: boolean;
  access: 'writable' | 'read-only' | 'revoked'; online: boolean; refreshing?: boolean;
  actor: {principalId: string; kind: 'person' | 'agent' | 'unknown'};
  people: ProductWorkChoices<ProductWorkPerson>; documents: ProductWorkChoices<ProductWorkDocChoice>;
  onRefresh: () => void | Promise<void>;
  onAccepted: (prepared: PreparedProductCommand, receipt: Extract<ProductReceipt, {status: 'accepted' | 'rejected'; resulting: unknown}>) => void | Promise<void>;
  restoredDraft?: ProductWorkDraft;
  onDraftState: (draft: ProductWorkDraft) => void;
};

const copy = <T,>(value: T): T => structuredClone(value);
export const productWorkScopeKey = (scope: ProductWorkScope, sessionKey: string) => JSON.stringify([scope.projectId, scope.resourceId, sessionKey]);
export function matchesWorkDraft(draft: ProductWorkDraft, scope: ProductWorkScope, sessionKey: string) {
  return draft.projectId === scope.projectId && draft.resourceId === scope.resourceId && draft.sessionKey === sessionKey;
}
export function makeProductWorkDraft(scope: ProductWorkScope, sessionKey: string, work?: ProductWorkDetail): ProductWorkDraft {
  const properties: ProductWorkPropertyDraft = work ? {type: work.type, status: work.status, priority: work.priority,
    owner_principal_id: work.owner_principal_id, worker_principal_id: work.worker_principal_id, blocked_reason: work.blocked_reason}
    : {type: 'task', status: 'todo', priority: 'none', owner_principal_id: '', worker_principal_id: '', blocked_reason: ''};
  const contract: ProductContract = work ? {title: work.title, description: work.description, acceptance_criteria: work.acceptance_criteria,
    required_outcomes: copy(productDetailOutcomes(work))} : {title: '', description: '', acceptance_criteria: '', required_outcomes: {}};
  return {projectId: scope.projectId, resourceId: scope.resourceId, sessionKey, authorityEpoch: scope.authorityEpoch, conflicts: {},
    properties: {authorityEpoch: scope.authorityEpoch, base: work?.work_revision ?? '0', value: properties, dirty: false},
    contract: {authorityEpoch: scope.authorityEpoch, base: work?.execution_contract_revision ?? '0', digest: work?.execution_contract_digest ?? '', value: contract, dirty: false},
    discussion: {authorityEpoch: scope.authorityEpoch, base: work?.discussion_sequence ?? '0', value: '', dirty: false},
    completion: {authorityEpoch: scope.authorityEpoch, workBase: work?.work_revision ?? '0', contractBase: work?.execution_contract_revision ?? '0', digest: work?.execution_contract_digest ?? '', note: '', dirty: false},
    legacyBlocked: {authorityEpoch: scope.authorityEpoch, base: work?.work_revision ?? '0', value: {status: '', reason: ''}, dirty: false},
    legacyAssignment: {authorityEpoch: scope.authorityEpoch, base: work?.work_revision ?? '0', value: {owner: '', worker: ''}, dirty: false}};
}
export function productWorkHasDraft(draft: ProductWorkDraft) {
  return draft.properties.dirty || draft.contract.dirty || draft.discussion.dirty || draft.completion.dirty
    || draft.legacyBlocked.dirty || draft.legacyAssignment.dirty || ['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '');
}
export function restoreProductWorkDraft(scope: ProductWorkScope, sessionKey: string, work: ProductWorkDetail | undefined, restored?: ProductWorkDraft): ProductWorkDraft {
  if (!restored || !matchesWorkDraft(restored, scope, sessionKey)) return makeProductWorkDraft(scope, sessionKey, work);
  if (restored.attempt?.phase === 'saving' && restored.attempt.prepared) return {...restored, attempt: {...restored.attempt,
    phase: 'unknown', message: 'The original request has not been reconciled. Keep this draft and check the same request again.'}};
  if (restored.attempt?.phase === 'preparing' && !restored.attempt.prepared) return {...restored, attempt: undefined};
  return restored;
}
function atLeast(actual: string, expected: string) { return BigInt(actual) >= BigInt(expected); }
export function reconcileProductWorkDraft(draft: ProductWorkDraft, work: ProductWorkDetail, authorityEpoch = draft.authorityEpoch): ProductWorkDraft {
  if (draft.projectId !== work.project_id || draft.resourceId !== work.resource_id) return draft;
  const fresh = makeProductWorkDraft({projectId: draft.projectId, resourceId: draft.resourceId, authorityEpoch}, draft.sessionKey, work);
  const attempt = draft.attempt, receipt = attempt?.receipt;
  const readback = attempt?.phase === 'accepted' && receipt?.status === 'accepted' && 'resulting' in receipt
    && atLeast(work.work_revision, receipt.resulting.work_revision)
    && atLeast(work.execution_contract_revision, receipt.resulting.execution_contract_revision)
    && atLeast(work.discussion_sequence, receipt.resulting.discussion_sequence);
  const cleared = (section: ProductWorkSection) => !!readback && attempt?.section === section;
  const next = {...draft, authorityEpoch,
    properties: (!draft.properties.dirty && !draft.conflicts['properties']) || cleared('properties') ? fresh.properties : draft.properties,
    contract: (!draft.contract.dirty && !draft.conflicts['contract']) || cleared('contract') ? fresh.contract : draft.contract,
    discussion: (!draft.discussion.dirty && !draft.conflicts['discussion']) || cleared('discussion') ? fresh.discussion : draft.discussion,
    completion: (!draft.completion.dirty && !draft.conflicts['completion']) || cleared('completion') ? fresh.completion : draft.completion,
    legacyBlocked: (!draft.legacyBlocked.dirty && !draft.conflicts['legacy-blocked']) || cleared('legacy-blocked') ? fresh.legacyBlocked : draft.legacyBlocked,
    legacyAssignment: (!draft.legacyAssignment.dirty && !draft.conflicts['legacy-assignment']) || cleared('legacy-assignment') ? fresh.legacyAssignment : draft.legacyAssignment,
    ...(readback && attempt ? {attempt: {...attempt, awaitingReadback: false}} : {})};
  // Preserve object identity when a watch repeated the same snapshot.
  return JSON.stringify({...next, attempt: undefined}) === JSON.stringify({...draft, attempt: undefined})
    && next.attempt?.awaitingReadback === draft.attempt?.awaitingReadback ? draft : next;
}
export function adoptProductWorkBase(draft: ProductWorkDraft, section: ProductWorkSection, work: ProductWorkDetail, authorityEpoch = draft.authorityEpoch): ProductWorkDraft {
  if (draft.projectId !== work.project_id || draft.resourceId !== work.resource_id) return draft;
  if (['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '')) return draft;
  const conflicts = {...draft.conflicts}; delete conflicts[section];
  const next = {...draft, authorityEpoch, conflicts, previousAttempt: draft.attempt ?? draft.previousAttempt, attempt: undefined};
  if (section === 'properties') next.properties = {...draft.properties, authorityEpoch, base: work.work_revision};
  if (section === 'contract') next.contract = {...draft.contract, authorityEpoch, base: work.execution_contract_revision, digest: work.execution_contract_digest};
  if (section === 'discussion') next.discussion = {...draft.discussion, authorityEpoch, base: work.discussion_sequence};
  if (section === 'legacy-blocked') next.legacyBlocked = {...draft.legacyBlocked, authorityEpoch, base: work.work_revision};
  if (section === 'legacy-assignment') next.legacyAssignment = {...draft.legacyAssignment, authorityEpoch, base: work.work_revision};
  if (section === 'completion') next.completion = {...draft.completion, authorityEpoch, workBase: work.work_revision,
    contractBase: work.execution_contract_revision, digest: work.execution_contract_digest};
  return next;
}
export function adoptProductWorkCreateAuthority(draft: ProductWorkDraft, scope: ProductWorkScope) {
  if (draft.projectId !== scope.projectId || draft.resourceId !== scope.resourceId
    || ['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '')) return draft;
  const conflicts = {...draft.conflicts}; delete conflicts.create;
  return {...draft, authorityEpoch: scope.authorityEpoch, conflicts, previousAttempt: draft.attempt ?? draft.previousAttempt, attempt: undefined};
}
export function productWorkSectionEpoch(draft: ProductWorkDraft, section: ProductWorkSection) {
  if (section === 'create') return draft.authorityEpoch;
  if (section === 'legacy-blocked') return draft.legacyBlocked.authorityEpoch;
  if (section === 'legacy-assignment') return draft.legacyAssignment.authorityEpoch;
  return draft[section].authorityEpoch;
}
export function productWorkConflict(draft: ProductWorkDraft, section: ProductWorkSection) {
  return {...draft, conflicts: {...draft.conflicts, [section]: true as const}};
}
// A returning resource is a new view even if its textual scope matches an older one.
export function advanceProductWorkGeneration(previous: {key: string; client: object; epoch: string; generation: number} | undefined,
  key: string, client: object, epoch: string) {
  return previous && previous.key === key && previous.client === client && previous.epoch === epoch ? previous
    : {key, client, epoch, generation: (previous?.generation ?? 0) + 1};
}
export function productCompletionReady(readiness: ProductWorkReadiness | undefined, work: ProductWorkDetail, sessionKey: string) {
  return readiness?.state === 'ready' && readiness.projectId === work.project_id && readiness.resourceId === work.resource_id
    && readiness.sessionKey === sessionKey && readiness.executionContractRevision === work.execution_contract_revision && readiness.executionContractDigest === work.execution_contract_digest;
}
export function productWorkPeople(people: ProductWorkChoices<ProductWorkPerson>, role: 'owner' | 'worker', projectId: string, sessionKey: string) {
  return people.state === 'ready' && people.projectId === projectId && people.sessionKey === sessionKey && people.values.length <= 128
    ? people.values.filter(person => person.active === true && ['person', 'agent'].includes(person.kind) && (role === 'worker' || person.kind === 'person')) : [];
}
export function productWorkDocuments(choices: ProductWorkChoices<ProductWorkDocChoice>, projectId: string, sessionKey: string) {
  return choices.state === 'ready' && choices.projectId === projectId && choices.sessionKey === sessionKey && choices.values.length <= 128
    ? choices.values.filter(choice => choice.visibility === 'shared' && choice.target.kind === 'document' && choice.target.project_id === projectId) : [];
}
export function productWorkFailure(code: string) {
  if (code === 'revision_conflict' || code === 'authority_epoch_conflict') return 'This work changed. Refresh and compare the current version before saving your draft.';
  if (code === 'denied_or_not_found' || code === 'session_changed' || code === 'session_required') return 'Your access changed. Your local draft is kept; refresh your sign-in and access before continuing.';
  if (code === 'ineligible_assignment') return 'An owner or worker is no longer eligible. Refresh the people list and choose again.';
  if (code === 'target_unavailable') return 'A required document changed or is unavailable. Refresh its current revision before saving.';
  if (code === 'completion_required' || code === 'missing_outcome_proof' || code === 'human_required') return 'Completion could not be confirmed. Check the required outputs or ask an authorized person to complete this work.';
  return 'Home did not accept this change. Your draft is kept. Refresh the current work before trying again.';
}

export function useProductWorkDraft(environment: ProductWorkEnvironment, work?: ProductWorkDetail) {
  const key = productWorkScopeKey(environment.scope, environment.sessionKey);
  const initial = () => restoreProductWorkDraft(environment.scope, environment.sessionKey, work, environment.restoredDraft);
  const [stored, setStored] = useState(initial);
  const draft = matchesWorkDraft(stored, environment.scope, environment.sessionKey) ? stored : initial();
  const view = useRef<ReturnType<typeof advanceProductWorkGeneration> | undefined>(undefined);
  view.current = advanceProductWorkGeneration(view.current, key, environment.client, environment.scope.authorityEpoch);
  const generation = view.current.generation;
  const current = useRef({key, generation, environment, draft}); current.current = {key, generation, environment, draft};
  const running = useRef<number | null>(null), mounted = useRef(true);
  function change(update: ProductWorkDraft | ((draft: ProductWorkDraft) => ProductWorkDraft)) {
    const value = typeof update === 'function' ? update(current.current.draft) : update;
    if (!matchesWorkDraft(value, current.current.environment.scope, current.current.environment.sessionKey)) return;
    if (value === current.current.draft) return;
    current.current.draft = value; setStored(value); current.current.environment.onDraftState(value);
  }
  useEffect(() => { mounted.current = true; return () => {
    mounted.current = false;
    const currentDraft = current.current.draft;
    if (currentDraft.attempt?.phase === 'saving' && currentDraft.attempt.prepared) current.current.environment.onDraftState({...currentDraft,
      attempt: {...currentDraft.attempt, phase: 'unknown', message: 'Keep this draft until the original request is reconciled.'}});
  }; }, []);
  useEffect(() => { if (!matchesWorkDraft(stored, environment.scope, environment.sessionKey)) { change(initial()); } }, [key]);
  useEffect(() => { change(value => restoreProductWorkDraft(environment.scope, environment.sessionKey, work, value)); }, [generation]);
  useEffect(() => { if (work) change(value => reconcileProductWorkDraft(value, work, environment.scope.authorityEpoch)); }, [key, work, environment.scope.authorityEpoch]);
  const pending = ['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '') || !!draft.attempt?.awaitingReadback;
  const canWrite = environment.supported && environment.access === 'writable' && environment.online && !environment.refreshing;
  async function send(section: ProductWorkSection, prepare: () => Promise<PreparedProductCommand>, retry = false) {
    const start = current.current;
    if (!canWrite || running.current === start.generation || (!retry && (pending || start.draft.conflicts[section]
      || productWorkSectionEpoch(start.draft, section) !== start.environment.scope.authorityEpoch))) return;
    const prior = start.draft.attempt;
    if (retry && (prior?.phase !== 'unknown' || !prior.prepared)) return;
    const live = () => mounted.current && current.current.generation === start.generation;
    running.current = start.generation;
    change(value => ({...value, previousAttempt: !retry && prior?.receipt ? prior : value.previousAttempt,
      attempt: {section, authorityEpoch: start.environment.scope.authorityEpoch, phase: retry ? 'saving' : 'preparing', prepared: retry ? prior?.prepared : undefined, message: ''}}));
    let prepared: PreparedProductCommand | undefined = retry ? prior?.prepared : undefined;
    try {
      prepared ??= await prepare();
      if (!live()) return;
      if (current.current.environment.access !== 'writable' || !current.current.environment.online || !current.current.environment.supported || current.current.environment.refreshing) {
        change(value => ({...value, attempt: {section, authorityEpoch: start.environment.scope.authorityEpoch, phase: retry ? 'unknown' : 'rejected', prepared: retry ? prepared : undefined,
          message: retry ? 'The original request is still unconfirmed. Reconnect and check access before checking it again.' : 'Your draft is kept. Reconnect and check access before saving.'}})); return;
      }
      change(value => ({...value, attempt: {section, authorityEpoch: start.environment.scope.authorityEpoch, phase: 'saving', prepared, message: ''}}));
      const receipt = await start.environment.client.submit(prepared);
      if (!live()) return;
      if (receipt.status === 'rejected') {
        const phase = ['revision_conflict', 'authority_epoch_conflict'].includes(receipt.error) ? 'conflict'
          : receipt.error === 'denied_or_not_found' ? 'revoked' : 'rejected';
        change(value => ({...value, ...(phase === 'conflict' ? {conflicts: {...value.conflicts, [section]: true as const}} : {}),
          attempt: {section, authorityEpoch: start.environment.scope.authorityEpoch, phase, prepared, receipt, message: productWorkFailure(receipt.error)}})); return;
      }
      change(value => ({...value, attempt: {section, authorityEpoch: start.environment.scope.authorityEpoch, phase: 'accepted', prepared, receipt, awaitingReadback: section !== 'create', message: ''}}));
      if (current.current.environment.access !== 'writable' || !current.current.environment.supported) return;
      try { await current.current.environment.onAccepted(prepared, receipt); }
      catch { if (live()) change(value => ({...value, attempt: {...value.attempt!, message: 'Home accepted the change. Refresh to load its current saved version.'}})); }
    } catch (error) {
      if (!live()) return;
      const code = error instanceof ProductClientError ? error.code : '';
      change(value => ({...value, attempt: {section, authorityEpoch: start.environment.scope.authorityEpoch, prepared, phase: code === 'outcome_unknown' || code === 'unrecognized_prepared_command' ? 'unknown'
        : code === 'session_changed' || code === 'session_required' ? 'revoked' : 'rejected',
        message: code === 'unrecognized_prepared_command' ? 'The original request needs reconciliation before another save. Refresh this work; your draft is kept.'
          : code === 'outcome_unknown' ? 'Home has not confirmed whether this saved. Keep this draft and check the same request again.'
          : code ? productWorkFailure(code) : 'Check the title, text lengths and selected people or documents. Your draft is kept.'}}));
    } finally { if (live() && running.current === start.generation) running.current = null; }
  }
  const retry = () => { const attempt = current.current.draft.attempt; if (attempt?.prepared) return send(attempt.section, async () => attempt.prepared!, true); };
  return {draft, change, send, retry, pending, locked: !canWrite || pending};
}

export type ProductWorkPrepared = PreparedProductCommand;
export type ProductWorkSubmitted = ProductCommand;

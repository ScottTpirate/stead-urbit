// One current-session draft partition for the explicit native-human-doc carrier.
// Prepared commands stay as original objects: cloning loses client retry ownership.
import {docReviewHasDraft, type DocReviewDraft, type DocReviewScope} from './docChangeReviewState';
import type {PreparedDocChangeCommand} from './docChangeClient';
import type {DocChangeCommand} from './docChangeProtocol';
import type {DocChangeReceipt} from './docChangeReadProtocol';
import {productDetailOutcomes, type DocumentOutcome, type ProductPrincipal, type ProductView, type ProductWorkDetail} from './productProtocol';
import {ProductProtocolError, productJSON} from './productWire';
import {productWorkHasDraft, type ProductWorkDraft, type ProductWorkPerson, type ProductWorkReadiness} from './productWorkState';
import type {ProductWorkDocChoice} from './productWorkState';
import {HomeError, UUID, type Fields, type HomeClient, type Query} from './api';
import {byteLength, protocolText} from './productWire';
import {newId} from './protocol';
import {productStatusLabels} from './productWorkFields';
import type {ProductRoute} from './productRoutes';

export type ProductWorkEndpointReader = (project: string, work: string) => Promise<{projectId: string; workId: string; authorityEpoch: string; title: string; statusLabel: string}>;
export async function readProductWorkEndpoint(client: HomeClient, project: string, work: string) {
  const view = await client.productWork.readWork({request_id: newId(), project_id: project, resource_id: work});
  if (view.status === 'rejected') throw new HomeError(view.error);
  if (view.kind !== 'work' || view.rows.length !== 1 || !view.rows[0] || !('description' in view.rows[0])) throw new HomeError('invalid_response');
  const row = view.rows[0]; return {projectId: project, workId: work, authorityEpoch: view.authority_epoch, title: row.title, statusLabel: productStatusLabels[row.status]};
}

export type ProductJourneySelection = {kind: 'list'} | {kind: 'work'; workId: string}
  | {kind: 'doc-change'; workId: string; changeId: string; result?: {revision: string; digest: string}};
export type ProductReadNavigationState = {projectId?: string; partition: object | null; currentSession: object | null;
  pending: boolean; legacyPending: boolean; dirtyDocument: boolean; busy: boolean; formOpen: boolean; online: boolean};
// Navigation permission only. Every target still requires a fresh authorized read.
export function productReadNavigationAllowed(state: ProductReadNavigationState, route: ProductRoute | null) {
  return !!state.projectId && !!state.currentSession && state.partition === state.currentSession
    && !state.pending && !state.legacyPending && !state.dirtyDocument && !state.busy && !state.formOpen && state.online
    && !!route && (route.kind === 'work' || route.kind === 'doc' || route.kind === 'doc-change') && route.project === state.projectId;
}
export function productJourneyRoute(project: string, selection: ProductJourneySelection): ProductRoute {
  return selection.kind === 'doc-change' ? {kind: 'doc-change', project, work: selection.workId, change: selection.changeId,
    ...(selection.result ? {result: selection.result} : {})}
    : {kind: 'work', project, ...(selection.kind === 'work' ? {item: selection.workId} : {})};
}

export type DocProposalPin = {authorityEpoch: string; headRevision: string; executionContractRevision: string; executionContractDigest: string;
  outcomeId: string; target: DocumentOutcome};
export type DocProposalDraft = {scope: DocReviewScope; sessionKey: string; base: DocProposalPin; markdown: string; summary: string; dirty: boolean;
  conflicted: boolean; deniedReadToken?: object; attempt?: {phase: 'preparing' | 'saving' | 'unknown' | 'conflict' | 'rejected' | 'accepted';
    prepared?: PreparedDocChangeCommand; receipt?: Extract<DocChangeReceipt, {status: 'accepted'}>; message: string; awaitingReadback?: boolean}};
export const proposalPending = (draft: DocProposalDraft) => ['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '') || !!draft.attempt?.awaitingReadback;
export const proposalHasDraft = (draft: DocProposalDraft) => draft.dirty || proposalPending(draft);
const sameScope = (a: DocReviewScope, b: DocReviewScope) => a.projectId === b.projectId && a.workId === b.workId && a.changeId === b.changeId;
export function restoreDocProposal(scope: DocReviewScope, sessionKey: string, previous?: DocProposalDraft) {
  if (!previous || previous.sessionKey !== sessionKey || !sameScope(previous.scope, scope)) return undefined;
  if (previous.attempt?.phase === 'saving' && previous.attempt.prepared) return {...previous,
    attempt: {...previous.attempt, phase: 'unknown' as const, message: 'The original proposal is not yet confirmed. Check the same request before changing it.'}};
  if (previous.attempt?.phase === 'preparing') return {...previous, attempt: undefined};
  return previous;
}
export function proposalMatchesWork(draft: DocProposalDraft, work: ProductWorkDetail, authorityEpoch: string) {
  if (draft.scope.projectId !== work.project_id || draft.scope.workId !== work.resource_id || draft.base.authorityEpoch !== authorityEpoch
    || draft.base.executionContractRevision !== work.execution_contract_revision || draft.base.executionContractDigest !== work.execution_contract_digest) return false;
  return productJSON(productDetailOutcomes(work)[draft.base.outcomeId] ?? {}) === productJSON(draft.base.target);
}
export function currentProposalPin(draft: DocProposalDraft, work: ProductWorkDetail, authorityEpoch: string, headRevision = draft.base.headRevision): DocProposalPin | undefined {
  if (draft.scope.projectId !== work.project_id || draft.scope.workId !== work.resource_id) return undefined;
  const target = productDetailOutcomes(work)[draft.base.outcomeId];
  if (target?.kind !== 'document' || target.project_id !== work.project_id) return undefined;
  return {authorityEpoch, headRevision, executionContractRevision: work.execution_contract_revision,
    executionContractDigest: work.execution_contract_digest, outcomeId: draft.base.outcomeId, target: {...target}};
}
export function proposalCommand(draft: DocProposalDraft, requestId: string): DocChangeCommand {
  return {protocol: 'stead.doc-change/1', request_id: requestId, project_id: draft.scope.projectId, work_id: draft.scope.workId, change_id: draft.scope.changeId,
    authority_epoch: draft.base.authorityEpoch, expected_revision: draft.base.headRevision, operation: 'change.submit', payload: {
      outcome_id: draft.base.outcomeId, target: {...draft.base.target}, markdown: draft.markdown, summary: draft.summary,
      execution_contract_revision: draft.base.executionContractRevision, execution_contract_digest: draft.base.executionContractDigest, run_id: '', attempt: '0'}};
}
type Stored = {kind: 'work'; value: ProductWorkDraft} | {kind: 'review'; value: DocReviewDraft} | {kind: 'proposal'; value: DocProposalDraft};
const hasDraft = (entry: Stored) => entry.kind === 'work' ? productWorkHasDraft(entry.value)
  : entry.kind === 'review' ? docReviewHasDraft(entry.value) : proposalHasDraft(entry.value);
const pending = (entry: Stored) => ['preparing', 'saving', 'unknown'].includes(entry.value.attempt?.phase ?? '') || !!entry.value.attempt?.awaitingReadback;
const projectOf = (entry: Stored) => entry.kind === 'work' ? entry.value.projectId : entry.value.scope.projectId;
export class ProductJourneyDraftStore {
  private session = '';
  private entries = new Map<string, Stored>();
  bind(sessionKey: string) { if (sessionKey !== this.session) { this.clear(); this.session = sessionKey; } }
  clear() { this.entries.clear(); this.session = ''; }
  hasDraft(projectId?: string) { return [...this.entries.values()].some(entry => (!projectId || projectOf(entry) === projectId) && (hasDraft(entry) || pending(entry))); }
  currentPending(projectId?: string) { return [...this.entries.values()].some(entry => (!projectId || projectOf(entry) === projectId) && pending(entry)); }
  discard(projectId?: string) {
    if (this.currentPending(projectId)) return false;
    for (const [key, entry] of this.entries) if (!projectId || projectOf(entry) === projectId) this.entries.delete(key);
    return true;
  }
  newWork(project: string) {
    const entry = [...this.entries.values()].find(entry => entry.kind === 'work' && entry.value.projectId === project
      && entry.value.contract.base === '0' && (hasDraft(entry) || pending(entry)));
    return entry?.kind === 'work' ? entry.value : undefined;
  }
  workProposal(project: string, work: string) {
    const entry = [...this.entries.values()].find(entry => entry.kind === 'proposal' && entry.value.scope.projectId === project
      && entry.value.scope.workId === work && (hasDraft(entry) || pending(entry)));
    return entry?.kind === 'proposal' ? entry.value : undefined;
  }
  private key(kind: Stored['kind'], project: string, work: string, change = '') { return JSON.stringify([kind, project, work, change]); }
  private put(key: string, entry: Stored) {
    if (!this.session || entry.value.sessionKey !== this.session) return false;
    if (!this.entries.has(key) && this.entries.size >= 32) {
      const clean = [...this.entries].find(([, value]) => !hasDraft(value) && !pending(value));
      if (!clean) throw new Error('draft_limit');
      this.entries.delete(clean[0]);
    }
    this.entries.set(key, entry); return true;
  }
  getWork(project: string, work: string) { const entry = this.entries.get(this.key('work', project, work)); return entry?.kind === 'work' ? entry.value : undefined; }
  putWork(value: ProductWorkDraft) { return this.put(this.key('work', value.projectId, value.resourceId), {kind: 'work', value}); }
  getReview(scope: DocReviewScope) { const entry = this.entries.get(this.key('review', scope.projectId, scope.workId, scope.changeId)); return entry?.kind === 'review' ? entry.value : undefined; }
  putReview(value: DocReviewDraft) { return this.put(this.key('review', value.scope.projectId, value.scope.workId, value.scope.changeId), {kind: 'review', value}); }
  getProposal(scope: DocReviewScope) { const entry = this.entries.get(this.key('proposal', scope.projectId, scope.workId, scope.changeId)); return entry?.kind === 'proposal' ? entry.value : undefined; }
  putProposal(value: DocProposalDraft) { return this.put(this.key('proposal', value.scope.projectId, value.scope.workId, value.scope.changeId), {kind: 'proposal', value}); }
}

export type JourneyPickerState<T> = {state: 'idle' | 'loading' | 'unavailable' | 'revoked'} | {state: 'ready'; value: T};
type JourneyPickerBinding<T> = {view: object; projectId: string; sessionKey: string; authorityEpoch: string; token: object | string;
  current: () => boolean; read: (current: () => void) => Promise<T>; onDenied: () => void | Promise<void>};
// Optional data has its own request owner. It cannot delay a core Work read or
// turn an incomplete/failed roster into an authoritative empty list.
export class JourneyPicker<T> {
  private binding?: JourneyPickerBinding<T>;
  private serial = 0;
  private state: JourneyPickerState<T> = {state: 'idle'};
  private listener?: () => void;
  configure(binding?: JourneyPickerBinding<T>) {
    const previous = this.binding;
    if (previous?.view !== binding?.view || previous?.projectId !== binding?.projectId || previous?.sessionKey !== binding?.sessionKey
      || previous?.authorityEpoch !== binding?.authorityEpoch || previous?.token !== binding?.token) {
      this.serial++; this.state = {state: 'idle'};
    }
    this.binding = binding;
  }
  subscribe(listener: () => void) { this.listener = listener; return () => { this.listener = undefined; this.serial++; this.state = {state: 'idle'}; }; }
  snapshot() { return this.state; }
  private publish(value: JourneyPickerState<T>) { this.state = value; this.listener?.(); }
  async request() {
    const binding = this.binding;
    if (!binding || !binding.current() || ['loading', 'ready', 'revoked'].includes(this.state.state)) return;
    const serial = ++this.serial, active = () => serial === this.serial && this.binding?.view === binding.view && binding.current();
    const current = () => { if (!active()) throw new HomeError('session_changed'); };
    this.publish({state: 'loading'});
    try {
      const value = await binding.read(current);
      if (active()) this.publish({state: 'ready', value});
    } catch (error) {
      if (!active()) return;
      const code = error && typeof error === 'object' && 'code' in error ? String(error.code) : '';
      if (['denied_or_not_found', 'session_required', 'session_changed'].includes(code)) {
        this.publish({state: 'revoked'});
        try { await binding.onDenied(); } catch { /* The parent owns access recovery. */ }
      } else this.publish({state: 'unavailable'});
    }
  }
}

export function journeyPickerDemand(selection: ProductJourneySelection, composerOpen: boolean, purposeRequested: boolean, proposalOpen: boolean) {
  return {people: composerOpen || selection.kind !== 'list', documents: composerOpen || purposeRequested || proposalOpen};
}
export function journeyPeople(rows: readonly ProductPrincipal[]): ProductWorkPerson[] {
  return rows.filter(row => row.active === 'yes' && ['contributor', 'maintainer'].includes(row.project_role)
    && (row.principal_kind === 'person' || row.principal_kind === 'agent')).map(row => ({principalId: row.principal_id,
      displayName: row.display_name, kind: row.principal_kind as 'person' | 'agent', active: true}));
}
export function journeyActor(rows: readonly ProductPrincipal[], principalId: string) {
  const person = journeyPeople(rows).find(row => row.principalId === principalId);
  return {principalId, kind: person?.kind ?? 'unknown' as const};
}
export function journeyCompletion(view: Extract<ProductView, {kind: 'completion'}>, work: ProductWorkDetail, sessionKey: string, authorityEpoch: string): ProductWorkReadiness {
  const row = view.rows[0];
  if (view.authority_epoch !== authorityEpoch || !row || view.rows.length !== 1 || row.project_id !== work.project_id || row.work_id !== work.resource_id
    || row.execution_contract_revision !== work.execution_contract_revision || row.execution_contract_digest !== work.execution_contract_digest) throw new ProductProtocolError('invalid_response');
  return {projectId: work.project_id, resourceId: work.resource_id, sessionKey, executionContractRevision: row.execution_contract_revision,
    executionContractDigest: row.execution_contract_digest, state: row.ready === 'yes' ? 'ready' : 'pending'};
}
const readQuery = (kind: Query['kind'], project: string, collection = '', resource = '', cursor = ''): Query =>
  ({kind, project_id: project, container_id: collection, resource_id: resource, search: '', cursor});
export async function journeyProject(client: HomeClient, project: string, current: () => void): Promise<Fields> {
  const view = await client.query(readQuery('project', project)); current();
  const rows = Object.values(view.rows), row = rows[0];
  if (rows.length !== 1 || view.cursor || !row || row.project_id !== project || !UUID.test(project)
    || !/^[1-9][0-9]{0,19}$/u.test(row.authority_epoch ?? '') || BigInt(row.authority_epoch!) > 18446744073709551615n
    || row.authority_epoch !== view.authority_epoch || !['reader', 'contributor', 'maintainer'].includes(row.role ?? '')) throw new HomeError('invalid_response');
  return row;
}
export async function journeyRoster(client: HomeClient, project: string, epoch: string, current: () => void): Promise<ProductPrincipal[]> {
  const people: ProductPrincipal[] = [], seen = new Set<string>(), used = new Set<string>(); let cursor = '', generation = '';
  do {
    if (used.has(cursor) || used.size >= 7) throw new HomeError('invalid_response'); used.add(cursor);
    const view = await client.productWork.readPrincipals({request_id: newId(), project_id: project, cursor}); current();
    if (view.status === 'rejected') throw new HomeError(view.error);
    if (view.kind !== 'principals' || view.authority_epoch !== epoch || (generation && generation !== view.generation)) throw new HomeError('stale_cursor');
    generation = view.generation;
    for (const row of view.rows) { if (seen.has(row.principal_id) || people.length >= 128) throw new HomeError('invalid_response'); seen.add(row.principal_id); people.push(row); }
    cursor = view.cursor;
  } while (cursor);
  return people;
}
export type JourneyDocuments = {choices: ProductWorkDocChoice[]; markdown: ReadonlyMap<string, string>};
export const journeyDocumentKey = (target: DocumentOutcome) => productJSON(target);
export async function journeyDocuments(client: HomeClient, project: string, epoch: string, current: () => void): Promise<JourneyDocuments> {
  const collections: Fields[] = [], collectionIds = new Set<string>(), collectionCursors = new Set<string>(); let cursor = '', generation = '';
  do {
    if (collectionCursors.has(cursor) || collectionCursors.size >= 2) throw new HomeError('invalid_response'); collectionCursors.add(cursor);
    const view = await client.query(readQuery('containers', project, '', '', cursor)); current();
    if (view.authority_epoch !== epoch || (generation && generation !== view.generation)) throw new HomeError('stale_cursor'); generation = view.generation;
    for (const row of Object.values(view.rows)) {
      if (!UUID.test(row.container_id ?? '') || collectionIds.has(row.container_id!) || collectionIds.size >= 32 || !['shared', 'private'].includes(row.visibility ?? '')) throw new HomeError('invalid_response');
      collectionIds.add(row.container_id!); if (row.visibility === 'shared') collections.push(row);
    }
    cursor = view.cursor;
  } while (cursor);
  const choices: ProductWorkDocChoice[] = [], markdown = new Map<string, string>(); let scanned = 0;
  for (const collection of collections) {
    let next = '', generation = ''; const cursors = new Set<string>(), ids = new Set<string>();
    do {
      if (cursors.has(next) || cursors.size >= 7) throw new HomeError('invalid_response'); cursors.add(next);
      const view = await client.query(readQuery('documents', project, collection.container_id, '', next)); current();
      if (view.authority_epoch !== epoch || (generation && generation !== view.generation)) throw new HomeError('stale_cursor'); generation = view.generation;
      for (const preview of Object.values(view.rows)) {
        if (!UUID.test(preview.resource_id ?? '') || ids.has(preview.resource_id!) || scanned++ >= 128) throw new HomeError('invalid_response'); ids.add(preview.resource_id!);
        const exact = await client.query(readQuery('document', project, collection.container_id, preview.resource_id)); current();
        const rows = Object.values(exact.rows), row = rows[0];
        if (exact.authority_epoch !== epoch || exact.cursor || rows.length !== 1 || row?.kind !== 'document' || row.resource_id !== preview.resource_id
          || row.container_id !== collection.container_id || !/^[1-9][0-9]{0,19}$/u.test(row.resource_revision ?? '')
          || BigInt(row.resource_revision!) > 18446744073709551615n || typeof row.markdown !== 'string') throw new HomeError('invalid_response');
        protocolText(row.markdown);
        if (byteLength(row.markdown) > 32768 || row.markdown.includes('\r') || !row.markdown.startsWith(`---\nid: ${row.resource_id}\ntype: page\nstate: published\n---\n`)) continue;
        const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(row.markdown)))].map(value => value.toString(16).padStart(2, '0')).join(''); current();
        const target: DocumentOutcome = {kind: 'document', project_id: project, collection_id: collection.container_id!, document_id: row.resource_id!,
          expected_revision: row.resource_revision!, base_markdown_sha256: digest};
        choices.push({label: preview.title?.trim() || 'Shared Doc', visibility: 'shared', target}); markdown.set(journeyDocumentKey(target), row.markdown);
      }
      next = view.cursor;
    } while (next);
  }
  return {choices, markdown};
}

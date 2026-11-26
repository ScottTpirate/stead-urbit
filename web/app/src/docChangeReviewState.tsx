// Reserved UI adapters, not a wire format or authorization implementation.
import {useEffect, useRef, useState} from 'react';
import {docChangeCommandDigest, encodeDocChangeCommand, type DocChangeCommand, type DocChangeDecisionOperation} from './docChangeProtocol';
import {byteLength, protocolText} from './productWire';
import {newId} from './protocol';
import type {DocumentOutcome} from './productProtocol';
import type {DocActionReason, DocChangeReceiptError} from './docChangeReadProtocol';

export const docDecisionActions = ['change.request-changes', 'change.approve', 'change.adopt', 'change.accept', 'change.reject', 'change.quarantine'] as const;
export type DocChangeStatus = 'submitted' | 'changes-requested' | 'approved' | 'accepted' | 'rejected' | 'quarantined';
export type DocDecisionReason = 'none' | 'unsupported' | Exclude<DocActionReason, ''> | DocChangeReceiptError;
export type DocReviewScope = {projectId: string; workId: string; changeId: string};
export type DocReviewPin = {authorityEpoch: string; generation: string; headRevision: string; resultRevision: string; resultDigest: string};
export type DocActorLabel = {principalId: string; displayName: string};
export type DocOutputMetadata = {revision: string; digest: string; outcomeId: string; target: DocumentOutcome; targetLabel: string;
  executionContractRevision: string; executionContractDigest: string; markdownSha256: string; summary: string;
  producer: DocActorLabel; runId: string; attempt: string; submittedAtMs: string};
export type DocDecisionEvidence = {operation: DocChangeDecisionOperation; resultRevision: string; resultDigest: string;
  actor: DocActorLabel; note: string; recordedAtMs: string; requestId?: string; outcome?: 'accepted' | 'producer_quarantined'};
export type DocReviewSnapshot = {scope: DocReviewScope; sessionKey: string; authorityEpoch: string; generation: string;
  head: {revision: string; status: DocChangeStatus; resultRevision: string; resultDigest: string}; output: DocOutputMetadata;
  feedback?: DocDecisionEvidence; approval?: DocDecisionEvidence; adoption?: DocDecisionEvidence;
  acceptance?: {actor: DocActorLabel; recordedAtMs: string; requestId?: string; documentRevision: string; resultDigest: string}};
export type DocActionEligibility = {scope: DocReviewScope; sessionKey: string; pin: DocReviewPin;
  actions: Readonly<Record<DocChangeDecisionOperation, {state: 'eligible' | 'blocked' | 'unsupported'; reason: DocDecisionReason}>>};
export type DocReviewBody = {scope: DocReviewScope; sessionKey: string; resultRevision: string; resultDigest: string; side: 'before' | 'after'} & (
  | {state: 'ready'; markdown: string; sha256: string}
  | {state: 'loading' | 'unavailable' | 'new-document'; markdown?: never; sha256?: never}
);
export type VerifiedDocBody = {state: 'ready'; markdown: string} | {state: 'loading'} | {state: 'unavailable'} | {state: 'new-document'};
export type PreparedDocDecision = Readonly<{command: DocChangeCommand; bytes: string; digest: string}>;
export type DocDecisionOutcome = {status: 'accepted'; resultingRevision: string} | {status: 'rejected'; reason: DocDecisionReason};
export type DocSessionToken = object | string;
export interface DocDecisionSubmitter {
  currentSessionToken(): DocSessionToken | null;
  prepare(command: DocChangeCommand): Promise<PreparedDocDecision>;
  // The reviewed adapter owns transport/session checks and receipt correlation.
  // A thrown/uncorrelated response after dispatch has unknown outcome.
  submit(prepared: PreparedDocDecision): Promise<DocDecisionOutcome>;
}
export type DocDecisionDraft = {note: string; base: DocReviewPin; conflicted: boolean};
export type DocReviewAttempt = {operation: DocChangeDecisionOperation; phase: 'preparing' | 'saving' | 'unknown' | 'conflict' | 'rejected' | 'accepted';
  prepared?: PreparedDocDecision; bytes?: string; digest?: string; token: DocSessionToken; message: string;
  outcome?: DocDecisionOutcome; awaitingReadback?: boolean};
export type DocReviewDraft = {scope: DocReviewScope; sessionKey: string; selected?: DocChangeDecisionOperation;
  decisions: Partial<Record<DocChangeDecisionOperation, DocDecisionDraft>>; accessDeniedReadToken?: object; attempt?: DocReviewAttempt; previousAttempt?: DocReviewAttempt};
export type DocReviewEnvironment = {scope: DocReviewScope; sessionKey: string; supported: boolean; access: 'writable' | 'read-only' | 'revoked';
  // The adapter replaces this opaque token only after a fresh authorized read.
  authorizedReadToken: object; online: boolean; refreshing?: boolean; submitter: DocDecisionSubmitter; eligibility?: DocActionEligibility;
  restoredDraft?: DocReviewDraft; onDraftState: (draft: DocReviewDraft) => void;
  onRefresh: () => void | Promise<void>; onAccessChanged: () => void | Promise<void>; onAccepted: (prepared: PreparedDocDecision, outcome: Extract<DocDecisionOutcome, {status: 'accepted'}>) => void | Promise<void>};
const sameScope = (a: DocReviewScope, b: DocReviewScope) => a.projectId === b.projectId && a.workId === b.workId && a.changeId === b.changeId;
export const docReviewScopeKey = (scope: DocReviewScope, session: string) => JSON.stringify([scope.projectId, scope.workId, scope.changeId, session]);
export const docReviewPin = (snapshot: DocReviewSnapshot): DocReviewPin => ({authorityEpoch: snapshot.authorityEpoch, generation: snapshot.generation,
  headRevision: snapshot.head.revision, resultRevision: snapshot.output.revision, resultDigest: snapshot.output.digest});
export const sameDocReviewPin = (a: DocReviewPin, b: DocReviewPin) => a.authorityEpoch === b.authorityEpoch && a.generation === b.generation
  && a.headRevision === b.headRevision && a.resultRevision === b.resultRevision && a.resultDigest === b.resultDigest;
export function currentDocReview(snapshot: DocReviewSnapshot, scope: DocReviewScope, sessionKey: string) {
  return sameScope(snapshot.scope, scope) && snapshot.sessionKey === sessionKey;
}
export const currentDocOutput = (snapshot: DocReviewSnapshot) => snapshot.output.revision === snapshot.head.resultRevision && snapshot.output.digest === snapshot.head.resultDigest;
export function docActionEligible(environment: DocReviewEnvironment, snapshot: DocReviewSnapshot, operation: DocChangeDecisionOperation) {
  const eligibility = environment.eligibility;
  return environment.supported && environment.access === 'writable' && environment.online && !environment.refreshing
    && currentDocReview(snapshot, environment.scope, environment.sessionKey) && currentDocOutput(snapshot)
    && !!eligibility && sameScope(eligibility.scope, environment.scope) && eligibility.sessionKey === environment.sessionKey
    && sameDocReviewPin(eligibility.pin, docReviewPin(snapshot)) && eligibility.actions[operation]?.state === 'eligible'
    && eligibility.actions[operation]?.reason === 'none';
}
export function makeDocReviewDraft(scope: DocReviewScope, sessionKey: string): DocReviewDraft { return {scope: {...scope}, sessionKey, decisions: {}}; }
export function restoreDocReviewDraft(scope: DocReviewScope, sessionKey: string, previous?: DocReviewDraft): DocReviewDraft {
  if (!previous || !sameScope(previous.scope, scope) || previous.sessionKey !== sessionKey) return makeDocReviewDraft(scope, sessionKey);
  if (previous.attempt?.phase === 'saving' && previous.attempt.prepared) return {...previous,
    attempt: {...previous.attempt, phase: 'unknown', message: 'Keep this note until the original request is reconciled.'}};
  if (previous.attempt?.phase === 'preparing') return {...previous, attempt: undefined};
  return previous;
}
export function chooseDocDecision(draft: DocReviewDraft, operation: DocChangeDecisionOperation, snapshot: DocReviewSnapshot): DocReviewDraft {
  if (!sameScope(draft.scope, snapshot.scope) || draft.sessionKey !== snapshot.sessionKey) return draft;
  return {...draft, selected: operation, decisions: {...draft.decisions, [operation]: draft.decisions[operation] ?? {note: '', base: docReviewPin(snapshot), conflicted: false}}};
}
export function adoptDocDecision(draft: DocReviewDraft, operation: DocChangeDecisionOperation, snapshot: DocReviewSnapshot): DocReviewDraft {
  const note = draft.decisions[operation];
  if (!note || !currentDocReview(snapshot, draft.scope, draft.sessionKey) || !currentDocOutput(snapshot)
    || ['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '') || draft.attempt?.awaitingReadback) return draft;
  return {...draft, previousAttempt: draft.attempt ?? draft.previousAttempt, attempt: undefined,
    decisions: {...draft.decisions, [operation]: {...note, base: docReviewPin(snapshot), conflicted: false}}};
}
export function docDecisionCommand(draft: DocReviewDraft, operation: DocChangeDecisionOperation, requestId: string): DocChangeCommand {
  const decision = draft.decisions[operation]; if (!decision) throw new Error('Choose a decision first');
  return {protocol: 'stead.doc-change/1', request_id: requestId, project_id: draft.scope.projectId, work_id: draft.scope.workId, change_id: draft.scope.changeId,
    authority_epoch: decision.base.authorityEpoch, expected_revision: decision.base.headRevision, operation,
    payload: {result_revision: decision.base.resultRevision, result_digest: decision.base.resultDigest, note: decision.note}};
}
export function reconcileDocReviewDraft(draft: DocReviewDraft, snapshot: DocReviewSnapshot): DocReviewDraft {
  const attempt = draft.attempt;
  if (!currentDocReview(snapshot, draft.scope, draft.sessionKey) || attempt?.phase !== 'accepted' || !attempt.awaitingReadback
    || attempt.outcome?.status !== 'accepted' || BigInt(snapshot.head.revision) < BigInt(attempt.outcome.resultingRevision)) return draft;
  const decisions = {...draft.decisions}; delete decisions[attempt.operation];
  return {...draft, decisions, selected: draft.selected === attempt.operation ? undefined : draft.selected, attempt: {...attempt, awaitingReadback: false}};
}
export function docReviewHasDraft(draft: DocReviewDraft) {
  return Object.values(draft.decisions).some(note => !!note.note) || ['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '') || !!draft.attempt?.awaitingReadback;
}
export async function verifyDocReviewBody(body: DocReviewBody | undefined, snapshot: DocReviewSnapshot, side: 'before' | 'after'): Promise<VerifiedDocBody> {
  if (!body || !sameScope(body.scope, snapshot.scope) || body.sessionKey !== snapshot.sessionKey || body.side !== side
    || body.resultRevision !== snapshot.output.revision || body.resultDigest !== snapshot.output.digest) return {state: 'loading'};
  if (body.state === 'new-document') return {state: side === 'before' && snapshot.output.target.expected_revision === '0' ? 'new-document' : 'unavailable'};
  if (body.state !== 'ready') return {state: body.state};
  try {
    protocolText(body.markdown);
    if (byteLength(body.markdown) > 32768 || body.markdown.includes('\r')) return {state: 'unavailable'};
    const expected = side === 'after' ? snapshot.output.markdownSha256 : snapshot.output.target.base_markdown_sha256;
    if (!/^[a-f0-9]{64}$/u.test(expected) || body.sha256 !== expected) return {state: 'unavailable'};
    const actual = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(body.markdown)))].map(n => n.toString(16).padStart(2, '0')).join('');
    return actual === expected ? {state: 'ready', markdown: body.markdown} : {state: 'unavailable'};
  } catch { return {state: 'unavailable'}; }
}
export function useVerifiedDocBody(body: DocReviewBody | undefined, snapshot: DocReviewSnapshot, side: 'before' | 'after') {
  const [verified, setVerified] = useState<{body: DocReviewBody | undefined; snapshot: DocReviewSnapshot; value: VerifiedDocBody}>();
  useEffect(() => { let active = true; void verifyDocReviewBody(body, snapshot, side).then(value => { if (active) setVerified({body, snapshot, value}); }); return () => { active = false; }; }, [body, snapshot, side]);
  return verified && verified.body === body && verified.snapshot === snapshot ? verified.value : {state: 'loading'} as VerifiedDocBody;
}
export type DocDiffLine = {kind: 'same' | 'removed' | 'added'; text: string; before?: number; after?: number};
export function boundedDocDiff(before: string, after: string): {state: 'ready'; lines: DocDiffLine[]; beforeFinalNewline: boolean; afterFinalNewline: boolean} | {state: 'unavailable'} {
  try { protocolText(before); protocolText(after); } catch { return {state: 'unavailable'}; }
  if (byteLength(before) > 32768 || byteLength(after) > 32768) return {state: 'unavailable'};
  const a = before ? before.split('\n') : [], b = after ? after.split('\n') : [];
  if (a.length > 400 || b.length > 400 || (a.length + 1) * (b.length + 1) > 40000) return {state: 'unavailable'};
  const width = b.length + 1, table = new Uint16Array((a.length + 1) * width);
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--) table[i * width + j] = a[i] === b[j]
    ? table[(i + 1) * width + j + 1]! + 1 : Math.max(table[(i + 1) * width + j]!, table[i * width + j + 1]!);
  const lines: DocDiffLine[] = []; let i = 0, j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) { lines.push({kind: 'same', text: a[i]!, before: ++i, after: ++j}); }
    else if (i < a.length && (j === b.length || table[(i + 1) * width + j]! >= table[i * width + j + 1]!)) lines.push({kind: 'removed', text: a[i]!, before: ++i});
    else lines.push({kind: 'added', text: b[j]!, after: ++j});
  }
  return {state: 'ready', lines, beforeFinalNewline: before.endsWith('\n'), afterFinalNewline: after.endsWith('\n')};
}
export function docDecisionReason(reason: DocDecisionReason) {
  const messages: Record<DocDecisionReason, string> = {
    read_only: 'Your current access permits reading only.', superseded_result: 'A newer output is current. Open it to make a decision.',
    invalid_time: 'Home could not record the decision time. Your note is kept.', request_id_reuse: 'Home could not reconcile this request. Your note is kept; refresh before trying again.',
    producer_mismatch: 'Only the original producer can revise this Change.', producer_unavailable: 'The original producer cannot submit with its current access.',
    invalid_document: 'Home could not verify the exact proposed Doc.', content_collision: 'Home could not retain the proposed Doc. Your note is kept.',
    invalid_result: 'Home could not verify this retained output.', invalid_command: 'Home could not recognize this decision.',
    internal_request_id_collision: 'Home could not reserve the Doc save. Your note is kept.', document_save_rejected: 'The Doc could not be saved. Refresh its current version before deciding.', none: '', unsupported: 'This decision is not available here yet.', denied_or_not_found: 'Current access does not permit this decision.',
    human_review_required: 'An authorized person must review this output.', accountable_human_required: 'The accountable Owner or a project maintainer must make this decision.',
    self_review_denied: 'Another authorized person must review this output.', independent_adopter_required: 'Another accountable person must adopt this output.',
    independent_review_required: 'A current independent approval is needed.', explicit_adoption_required: 'The original authority expired. An authorized person must explicitly adopt this exact output.',
    adoption_requires_expiry: 'Adoption is available only after the original authority expires.', execution_contract_conflict: 'The Work purpose changed. Compare the current requirements.',
    target_base_conflict: 'The target Doc changed. This output needs a new exact base.', producer_quarantined: 'Original producer access changed. This output cannot be accepted.',
    change_closed: 'This Change is closed.', result_conflict: 'A newer output is available. Compare it before deciding.', revision_conflict: 'This Change changed. Refresh and compare it.',
    authority_epoch_conflict: 'Project access changed. Refresh and compare before deciding.', capacity_exceeded: 'Home cannot retain this decision yet. Your note is kept.', migration_required: 'This Home is not ready for Doc review yet.'};
  return messages[reason];
}
export function advanceDocReviewGeneration(previous: {key: string; submitter: DocDecisionSubmitter; token: DocSessionToken | null; readToken: object; generation: number} | undefined,
  key: string, submitter: DocDecisionSubmitter, token: DocSessionToken | null, readToken: object) {
  return previous && previous.key === key && previous.submitter === submitter && previous.token === token && previous.readToken === readToken ? previous
    : {key, submitter, token, readToken, generation: (previous?.generation ?? 0) + 1};
}
export function useDocReviewDraft(environment: DocReviewEnvironment, snapshot: DocReviewSnapshot, bodyReady: boolean) {
  const scopeKey = docReviewScopeKey(environment.scope, environment.sessionKey), pin = docReviewPin(snapshot);
  const key = scopeKey + '/' + JSON.stringify([pin, environment.access, environment.supported]), token = environment.submitter.currentSessionToken();
  const view = useRef<ReturnType<typeof advanceDocReviewGeneration> | undefined>(undefined);
  view.current = advanceDocReviewGeneration(view.current, key, environment.submitter, token, environment.authorizedReadToken); const generation = view.current.generation;
  const [stored, setStored] = useState(() => restoreDocReviewDraft(environment.scope, environment.sessionKey, environment.restoredDraft));
  const draft = sameScope(stored.scope, environment.scope) && stored.sessionKey === environment.sessionKey ? stored
    : restoreDocReviewDraft(environment.scope, environment.sessionKey, environment.restoredDraft);
  const current = useRef({environment, snapshot, draft, generation, bodyReady}); current.current = {environment, snapshot, draft, generation, bodyReady};
  const mounted = useRef(true), running = useRef<number | null>(null);
  function change(update: (draft: DocReviewDraft) => DocReviewDraft) {
    const next = update(current.current.draft); if (next === current.current.draft) return;
    if (!sameScope(next.scope, current.current.environment.scope) || next.sessionKey !== current.current.environment.sessionKey) return;
    current.current.draft = next; setStored(next); current.current.environment.onDraftState(next);
  }
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; current.current.environment.onDraftState(restoreDocReviewDraft(current.current.environment.scope,
    current.current.environment.sessionKey, current.current.draft)); }; }, []);
  useEffect(() => { change(value => restoreDocReviewDraft(environment.scope, environment.sessionKey, value)); }, [generation]);
  useEffect(() => { if (!sameScope(stored.scope, environment.scope) || stored.sessionKey !== environment.sessionKey) setStored(draft); }, [scopeKey]);
  useEffect(() => { change(value => reconcileDocReviewDraft(value, snapshot)); }, [snapshot]);
  const locallyRevoked = draft.accessDeniedReadToken === environment.authorizedReadToken;
  const pending = ['preparing', 'saving', 'unknown'].includes(draft.attempt?.phase ?? '') || !!draft.attempt?.awaitingReadback;
  async function send(operation: DocChangeDecisionOperation, retry = false) {
    const start = current.current, activeToken = start.environment.submitter.currentSessionToken(), note = start.draft.decisions[operation], prior = start.draft.attempt;
    if (start.draft.accessDeniedReadToken === start.environment.authorizedReadToken || !activeToken || running.current === start.generation || (!retry && !start.bodyReady) || start.environment.access !== 'writable' || !start.environment.online || !start.environment.supported) return;
    if (retry ? prior?.phase !== 'unknown' || !prior.prepared || prior.token !== activeToken
      : pending || !note || note.conflicted || !sameDocReviewPin(note.base, docReviewPin(start.snapshot)) || !docActionEligible(start.environment, start.snapshot, operation)) return;
    const live = () => mounted.current && current.current.generation === start.generation && start.environment.submitter.currentSessionToken() === activeToken;
    running.current = start.generation;
    let prepared = retry ? prior?.prepared : undefined, dispatched = false;
    change(value => ({...value, previousAttempt: !retry ? prior ?? value.previousAttempt : value.previousAttempt,
      attempt: {operation, phase: retry ? 'saving' : 'preparing', token: activeToken, prepared, bytes: retry ? prior?.bytes : undefined, digest: retry ? prior?.digest : undefined, message: ''}}));
    try {
      const expectedBytes = retry ? prior!.bytes! : encodeDocChangeCommand(docDecisionCommand(start.draft, operation, newId()));
      prepared ??= await start.environment.submitter.prepare(docDecisionCommand(start.draft, operation, JSON.parse(expectedBytes).request_id));
      if (!live()) return;
      if (!Object.isFrozen(prepared) || !Object.isFrozen(prepared.command) || !Object.isFrozen(prepared.command.payload) || prepared.bytes !== expectedBytes || encodeDocChangeCommand(prepared.command) !== expectedBytes
        || prepared.digest !== await docChangeCommandDigest(prepared.command) || (retry && prepared.digest !== prior!.digest)) throw new Error('Prepared request changed');
      if (!live()) return;
      const now = current.current;
      if (now.environment.access !== 'writable' || !now.environment.online || !now.environment.supported || now.environment.refreshing
        || (!retry && (!now.bodyReady || !docActionEligible(now.environment, now.snapshot, operation)))) throw new Error('Current view changed before dispatch');
      change(value => ({...value, attempt: {operation, phase: 'saving', token: activeToken, prepared, bytes: prepared!.bytes, digest: prepared!.digest, message: ''}}));
      dispatched = true; const outcome = await start.environment.submitter.submit(prepared); if (!live()) return;
      if (outcome.status === 'rejected') {
        if (outcome.reason === 'none' || !docDecisionReason(outcome.reason)) throw new Error('Uncorrelated rejection');
        const conflict = ['revision_conflict', 'result_conflict', 'authority_epoch_conflict', 'execution_contract_conflict', 'target_base_conflict', 'producer_quarantined'].includes(outcome.reason);
        change(value => ({...value, accessDeniedReadToken: outcome.reason === 'denied_or_not_found' ? start.environment.authorizedReadToken : value.accessDeniedReadToken, decisions: conflict && value.decisions[operation] ? {...value.decisions, [operation]: {...value.decisions[operation]!, conflicted: true}} : value.decisions,
          attempt: {...value.attempt!, phase: conflict ? 'conflict' : 'rejected', outcome, message: docDecisionReason(outcome.reason)}}));
        if (outcome.reason === 'denied_or_not_found') { try { await current.current.environment.onAccessChanged(); } catch { /* Keep content closed until a fresh authorized read. */ } }
        return;
      }
      if (outcome.status !== 'accepted' || !/^[1-9][0-9]{0,19}$/u.test(outcome.resultingRevision) || BigInt(outcome.resultingRevision) > 18446744073709551615n || BigInt(outcome.resultingRevision) !== BigInt(prepared.command.expected_revision) + 1n) throw new Error('Uncorrelated outcome');
      change(value => ({...value, attempt: {...value.attempt!, phase: 'accepted', outcome, awaitingReadback: true, message: ''}}));
      if (current.current.environment.access !== 'writable' || !current.current.environment.supported) return;
      try { await current.current.environment.onAccepted(prepared, outcome); }
      catch { if (live()) change(value => ({...value, attempt: {...value.attempt!, message: 'Home accepted the decision. Refresh its saved state.'}})); }
    } catch {
      if (!live()) return;
      change(value => ({...value, attempt: {...value.attempt!, prepared, phase: dispatched || retry ? 'unknown' : 'rejected',
        message: dispatched || retry ? 'Home has not confirmed this decision. Keep the note and check the same request again.' : 'This decision was not sent. Refresh the current output; your note is kept.'}}));
    } finally { if (live() && running.current === start.generation) running.current = null; }
  }
  return {draft, change, send, pending, locallyRevoked, locked: locallyRevoked || pending || !environment.online || environment.access !== 'writable' || !environment.supported || !!environment.refreshing};
}

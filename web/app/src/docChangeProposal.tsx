import {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {Button, OutcomeState, Surface, TextField} from './primitives';
import {DocumentBody} from './DocumentBody';
import {newId} from './protocol';
import type {DocChangeClient, PreparedDocChangeCommand} from './docChangeClient';
import type {DocChangeReceipt} from './docChangeReadProtocol';
import {docDecisionReason, type DocReviewScope} from './docChangeReviewState';
import {proposalCommand, proposalMatchesWork, proposalPending, restoreDocProposal, type DocProposalDraft, type DocProposalPin} from './productJourneyState';
import type {ProductWorkDetail} from './productProtocol';
import {productJSON} from './productWire';
import './docChangeProposal.css';

export type DocChangeProposalProps = {client: DocChangeClient; scope: DocReviewScope; sessionKey: string; work: ProductWorkDetail;
  pin: DocProposalPin; targetCurrent: boolean; initialMarkdown: string; authorizedReadToken: object; actorKind: 'person' | 'agent' | 'unknown'; access: 'writable' | 'read-only' | 'revoked';
  online: boolean; refreshing: boolean; restoredDraft?: DocProposalDraft; onDraftState: (draft: DocProposalDraft) => void;
  onRefresh: () => void | Promise<void>; onAccessChanged: () => void | Promise<void>; onClose: () => void;
  onAccepted: (prepared: PreparedDocChangeCommand, receipt: Extract<DocChangeReceipt, {status: 'accepted'}>) => void | Promise<void>};
export function DocChangeProposal(props: DocChangeProposalProps) {
  if (props.access === 'revoked' || props.restoredDraft?.deniedReadToken === props.authorizedReadToken) return <OutcomeState state="permission_revoked"/>;
  return <Proposal key={JSON.stringify([props.scope, props.sessionKey])} {...props}/>;
}
function Proposal(props: DocChangeProposalProps) {
  const initial = restoreDocProposal(props.scope, props.sessionKey, props.restoredDraft) ?? {scope: {...props.scope}, sessionKey: props.sessionKey,
    base: structuredClone(props.pin), markdown: props.initialMarkdown, summary: '', dirty: false, conflicted: false};
  const [draft, setDraft] = useState<DocProposalDraft>(initial), [denied, setDenied] = useState(false), [fullSource, setFullSource] = useState(false);
  const draftRef = useRef(draft), mounted = useRef(true), title = useRef<HTMLInputElement>(null);
  const current = useRef({props, generation: 0, pin: productJSON(props.pin)}), previous = current.current;
  const pin = productJSON(props.pin);
  current.current = {props, pin, generation: previous.generation + (previous.props.client !== props.client || previous.pin !== pin
    || previous.props.access !== props.access || previous.props.authorizedReadToken !== props.authorizedReadToken ? 1 : 0)};
  useLayoutEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { title.current?.focus(); }, []);
  function change(next: DocProposalDraft) { draftRef.current = next; setDraft(next); props.onDraftState(next); }
  useEffect(() => { props.onDraftState(draftRef.current); }, []);
  const changed = !proposalMatchesWork(draft, props.work, props.pin.authorityEpoch) || productJSON(draft.base) !== pin;
  const pending = proposalPending(draft), unavailable = denied || props.access !== 'writable' || props.actorKind !== 'person';
  const locked = unavailable || !props.online || props.refreshing || pending;
  const header = `---\nid: ${draft.base.target.document_id}\ntype: page\nstate: published\n---\n`;
  const validTarget = draft.base.target.project_id === props.scope.projectId && props.work.project_id === props.scope.projectId
    && props.work.resource_id === props.scope.workId && draft.markdown.startsWith(header) && props.targetCurrent;
  const sameTarget = draft.base.target.project_id === props.pin.target.project_id && draft.base.target.collection_id === props.pin.target.collection_id
    && draft.base.target.document_id === props.pin.target.document_id;
  async function send(retry = false) {
    if (unavailable || !props.online || props.refreshing || (!retry && (pending || changed || draft.conflicted || !validTarget || !draft.dirty))) return;
    const captured = current.current, token = props.client.currentSessionToken();
    const live = () => mounted.current && current.current.generation === captured.generation
      && current.current.props.client === captured.props.client && current.current.props.client.currentSessionToken() === token;
    let prepared = retry ? draftRef.current.attempt?.prepared : undefined, accepted = false;
    if (retry && (draftRef.current.attempt?.phase !== 'unknown' || !prepared)) return;
    try {
      if (!prepared) {
        change({...draftRef.current, attempt: {phase: 'preparing', message: ''}});
        prepared = await props.client.prepare(proposalCommand(draftRef.current, newId()));
        if (!live()) return;
      }
      change({...draftRef.current, attempt: {phase: 'saving', prepared, message: ''}});
      const receipt = await props.client.submit(prepared);
      if (!live()) return;
      if (receipt.status === 'rejected') {
        const lostAccess = receipt.error === 'denied_or_not_found';
        const conflict = ['revision_conflict', 'authority_epoch_conflict', 'execution_contract_conflict', 'target_base_conflict', 'result_conflict', 'producer_quarantined'].includes(receipt.error);
        change({...draftRef.current, ...(lostAccess ? {deniedReadToken: props.authorizedReadToken} : {}), conflicted: conflict,
          attempt: {phase: conflict ? 'conflict' : 'rejected', prepared, message: docDecisionReason(receipt.error)}});
        if (lostAccess) { setDenied(true); try { await props.onAccessChanged(); } catch { /* The definite denial stays closed. */ } }
        return;
      }
      accepted = true;
      change({...draftRef.current, attempt: {phase: 'accepted', prepared, receipt, awaitingReadback: true,
        message: 'Home recorded the proposal. The shared Doc changes only after accountable acceptance.'}});
      if (live() && current.current.props.access === 'writable') await props.onAccepted(prepared, receipt);
    } catch (error) {
      if (!live()) return;
      if (accepted) {
        change({...draftRef.current, attempt: {...draftRef.current.attempt!, phase: 'accepted', awaitingReadback: true,
          message: 'Home recorded the proposal. Refresh to load its saved version.'}}); return;
      }
      const code = error && typeof error === 'object' && 'code' in error ? String(error.code) : '';
      change({...draftRef.current, attempt: {phase: prepared ? 'unknown' : 'rejected', ...(prepared ? {prepared} : {}),
        message: prepared ? 'The proposal outcome is not confirmed. Check the original request without changing its contents.'
          : code === 'session_required' || code === 'session_changed' ? 'Refresh your sign-in before submitting this proposal.' : 'Review the summary and exact Markdown before submitting.'}});
    }
  }
  if (denied) return <OutcomeState state="permission_revoked"/>;
  return <Surface className="doc-change-proposal" aria-label="Propose Doc change">
    <header><h2>Propose a Doc change</h2><Button variant="quiet" disabled={pending} onClick={props.onClose}>{draft.dirty ? 'Keep draft and close' : 'Close'}</Button></header>
    <p>This proposes an exact revision for independent review. Accepting the proposal is a separate decision.</p>
    {unavailable && <OutcomeState state="read_only" description="Only an authorized person can submit a proposal here."/>}
    {!props.online && <OutcomeState state="disconnected_or_stale" description="Your draft is kept. Reconnect and refresh before submitting."/>}
    {draft.attempt && <OutcomeState state={draft.attempt.phase === 'accepted' ? 'accepted' : draft.attempt.phase === 'unknown' ? 'outcome_unknown'
      : draft.attempt.phase === 'conflict' ? 'conflict' : ['saving', 'preparing'].includes(draft.attempt.phase) ? 'saving' : 'retryable_error'} description={draft.attempt.message}
      action={draft.attempt.phase === 'unknown' ? <Button disabled={unavailable || !props.online || props.refreshing} onClick={() => void send(true)}>Check same proposal</Button>
        : draft.attempt.awaitingReadback ? <Button onClick={() => void props.onRefresh()}>Refresh recorded proposal</Button> : undefined}/>}
    {(changed || draft.conflicted) && <div className="doc-proposal-comparison"><p>The saved purpose, target, access or proposal changed. Your local text is kept.</p>
      <details><summary>Compare current proposal pins</summary><dl><div><dt>Draft purpose revision</dt><dd>{draft.base.executionContractRevision}</dd></div>
        <div><dt>Current purpose revision</dt><dd>{props.pin.executionContractRevision}</dd></div><div><dt>Draft expected Doc revision</dt><dd>{draft.base.target.expected_revision}</dd></div>
        <div><dt>Current expected Doc revision</dt><dd>{props.pin.target.expected_revision}</dd></div></dl></details>
      <Button disabled={locked || !props.targetCurrent || !sameTarget} onClick={() => change({...draft, base: structuredClone(props.pin), conflicted: false, attempt: undefined})}>Keep draft using current version</Button>
      <Button disabled={pending} onClick={() => void props.onRefresh()}>Refresh current version</Button></div>}
    <TextField ref={title} label="Change summary" value={draft.summary} disabled={locked} onChange={event => change({...draft, summary: event.target.value, dirty: true})}/>
    {!validTarget && <OutcomeState state="unsupported_operation" description={!props.targetCurrent
      ? 'This required output is no longer current. Keep this draft and return to Work to compare the saved purpose and target.'
      : 'The proposal must keep this shared Doc’s exact identity metadata.'}/>}
    <DocumentBody text={draft.markdown} header={header} isNew editable={!unavailable} locked={locked} fullSource={fullSource} onFullSource={setFullSource}
      onChange={markdown => change({...draft, markdown, dirty: true})}/>
    <Button variant="primary" disabled={locked || changed || draft.conflicted || !validTarget || !draft.dirty || !draft.summary.trim()}
      onClick={() => void send()}>Submit for review</Button>
    <details><summary>Details</summary><dl><div><dt>Change</dt><dd>{props.scope.changeId}</dd></div><div><dt>Expected proposal revision</dt><dd>{draft.base.headRevision}</dd></div>
      <div><dt>Execution contract</dt><dd>{draft.base.executionContractRevision}</dd></div><div><dt>Expected Doc revision</dt><dd>{draft.base.target.expected_revision}</dd></div>
      {draft.attempt?.prepared && <div><dt>Request</dt><dd>{draft.attempt.prepared.command.request_id}</dd></div>}</dl></details>
  </Surface>;
}

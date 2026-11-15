import {useEffect, useId, useRef, useState, type ReactNode} from 'react';
import {Button, LoadingState, OutcomeState, PropertyPicker, Surface, TextField} from './primitives';
import {Markdown} from './Markdown';
import {newId} from './protocol';
import {productDetailOutcomes, type ProductProperties, type ProductWorkDetail as Work, type UnfinishedStatus} from './productProtocol';
import {ProductWorkAttemptState, ProductWorkContractFields, ProductWorkDetails, ProductWorkPeoplePicker, ProductWorkProperties, productStatusLabels} from './productWorkFields';
import {adoptProductWorkBase, productCompletionReady, productWorkDocuments, productWorkSectionEpoch, productWorkScopeKey, useProductWorkDraft, type ProductWorkComments, type ProductWorkDraft,
  type ProductWorkEnvironment, type ProductWorkReadiness, type ProductWorkSection} from './productWorkState';
import './productWork.css';

export type ProductWorkDetailProps = ProductWorkEnvironment & {
  snapshot?: {work: Work; sessionKey: string; authorityEpoch: string};
  comments: ProductWorkComments; completionReadiness?: ProductWorkReadiness; context?: ReactNode;
  mode?: 'preview' | 'page'; onClose?: (draft: ProductWorkDraft) => void;
};
export function ProductWorkDetail(props: ProductWorkDetailProps) {
  if (!props.supported) return <OutcomeState state="unsupported_operation" description="This Home does not support this Work view yet."/>;
  if (props.access === 'revoked') return <OutcomeState state="permission_revoked"/>;
  const snapshot = props.snapshot;
  if (!snapshot || snapshot.sessionKey !== props.sessionKey || snapshot.authorityEpoch !== props.scope.authorityEpoch
    || snapshot.work.project_id !== props.scope.projectId || snapshot.work.resource_id !== props.scope.resourceId) return <LoadingState label="Loading current work"/>;
  try { productDetailOutcomes(snapshot.work); } catch { return <OutcomeState state="unsupported_operation" description="This work contains outputs this view cannot read safely."/>; }
  return <ActiveDetail {...props} work={snapshot.work}/>;
}
function ActiveDetail(props: ProductWorkDetailProps & {work: Work}) {
  const labels = useId();
  const {work} = props, state = useProductWorkDraft(props, work), {draft, change, locked} = state;
  const [editingContract, setEditingContract] = useState(!!props.restoredDraft?.contract.dirty);
  const heading = useRef<HTMLHeadingElement>(null), title = useRef<HTMLInputElement>(null);
  const key = productWorkScopeKey(props.scope, props.sessionKey);
  useEffect(() => { const frame = requestAnimationFrame(() => heading.current?.focus()); return () => cancelAnimationFrame(frame); }, [key]);
  useEffect(() => { if (editingContract) title.current?.focus(); }, [editingContract]);
  useEffect(() => { if (draft.attempt?.section === 'contract' && draft.attempt.phase === 'accepted' && !draft.attempt.awaitingReadback) setEditingContract(false); }, [draft.attempt]);
  const scope = () => ({request_id: newId(), project_id: props.scope.projectId, resource_id: props.scope.resourceId, authority_epoch: props.scope.authorityEpoch});
  const outcomes = productDetailOutcomes(work);
  const documentChoices = productWorkDocuments(props.documents, work.project_id, props.sessionKey);
  const unfinishedPurpose = draft.contract.dirty || draft.properties.dirty || draft.legacyAssignment.dirty || draft.legacyBlocked.dirty;
  const mayComplete = work.status !== 'done' && work.status !== 'canceled' && work.legacy_blocked_pending !== 'yes';
  const completionReady = productCompletionReady(props.completionReadiness, work, props.sessionKey);
  const commentsCurrent = props.comments.sessionKey === props.sessionKey && props.comments.projectId === work.project_id && props.comments.resourceId === work.resource_id
    && props.comments.rows.length <= 20 && new Set(props.comments.rows.map(row => row.sequence)).size === props.comments.rows.length
    && props.comments.rows.every(row => row.project_id === work.project_id && row.work_id === work.resource_id);
  function baseChanged(section: ProductWorkSection) {
    if (productWorkSectionEpoch(draft, section) !== props.scope.authorityEpoch) return true;
    if (section === 'properties') return draft.properties.base !== work.work_revision;
    if (section === 'contract') return draft.contract.base !== work.execution_contract_revision;
    if (section === 'discussion') return draft.discussion.base !== work.discussion_sequence;
    if (section === 'legacy-blocked') return draft.legacyBlocked.base !== work.work_revision;
    if (section === 'legacy-assignment') return draft.legacyAssignment.base !== work.work_revision;
    if (section === 'completion') return draft.completion.workBase !== work.work_revision || draft.completion.contractBase !== work.execution_contract_revision;
    return false;
  }
  function conflict(section: ProductWorkSection) {
    const rejected = draft.conflicts[section] === true;
    if (!baseChanged(section) && !rejected) return null;
    return <div className="product-work-conflict"><p>Your draft is kept. Compare it with the current saved version before using that version as its base.</p>
      <details><summary>Current saved {section === 'contract' || section === 'completion' ? 'purpose' : section === 'discussion' ? 'conversation' : 'properties'}</summary>
        {section === 'contract' || section === 'completion' ? <><strong>{work.title}</strong><Markdown text={work.description}/><h4>Acceptance criteria</h4><Markdown text={work.acceptance_criteria}/></>
          : section === 'discussion' ? <p>Read the current conversation below. Your unposted comment is unchanged.</p>
            : <dl><div><dt>Status</dt><dd>{productStatusLabels[work.status]}</dd></div><div><dt>Priority</dt><dd>{work.priority}</dd></div>
              <div><dt>Owner</dt><dd>{work.owner_display_name || (work.owner_principal_id ? 'Project member' : 'Unassigned')}</dd></div>
              <div><dt>Working on it</dt><dd>{work.worker_display_name || (work.worker_principal_id ? 'Project member' : 'Unassigned')}</dd></div></dl>}
      </details>
      <Button disabled={locked || (rejected && !baseChanged(section))} onClick={() => change(current => adoptProductWorkBase(current, section, work, props.scope.authorityEpoch))}>Keep draft using current version</Button></div>;
  }
  return <Surface className="product-work-detail" data-mode={props.mode ?? 'preview'} aria-labelledby="product-work-title">
    <header className="product-work-heading"><div><span className="row-kind">Work item</span><h2 id="product-work-title" ref={heading} tabIndex={-1}>{work.title}</h2></div>
      {props.onClose && <Button variant="quiet" onClick={() => props.onClose?.(draft)}>Close</Button>}</header>
    <ProductWorkAttemptState environment={props} draft={draft} retry={state.retry}/>
    <section className="product-work-section" aria-label="Purpose and acceptance criteria">
      {editingContract && work.status !== 'done' ? <><ProductWorkContractFields environment={props} value={draft.contract.value} disabled={locked} titleRef={title}
        onChange={value => change(current => ({...current, contract: {...current.contract, value, dirty: true}}))}/>
        {conflict('contract')}<div className="product-work-actions"><Button variant="primary" disabled={locked || !draft.contract.dirty || baseChanged('contract') || draft.conflicts.contract}
          onClick={() => void state.send('contract', () => props.client.prepareContract(scope(), draft.contract.base, draft.contract.value))}>Save purpose</Button>
          <Button disabled={state.pending} onClick={() => setEditingContract(false)}>Keep draft and return to reading</Button></div></>
        : <><h3>Purpose</h3>{work.description ? <Markdown text={work.description}/> : <p className="muted">No purpose added yet.</p>}
          <h3>Acceptance criteria</h3>{work.acceptance_criteria ? <Markdown text={work.acceptance_criteria}/> : <p className="muted">No acceptance criteria added yet.</p>}
          {work.status === 'done' && <p>Reopen this work with an unfinished status before changing its purpose or required outputs.</p>}
          {props.access === 'writable' && <Button disabled={locked || work.status === 'done'} onClick={() => setEditingContract(true)}>{draft.contract.dirty ? 'Continue editing purpose' : 'Edit purpose'}</Button>}</>}
    </section>
    <section className="product-work-section" aria-label="Properties and progress"><h3>Working on it</h3>
      <ProductWorkProperties environment={props} value={draft.properties.value} disabled={locked || work.legacy_blocked_pending === 'yes' || work.legacy_assignment_pending === 'yes'}
        onChange={value => change(current => ({...current, properties: {...current.properties, value, dirty: true}}))}/>
      {conflict('properties')}{draft.properties.dirty && <Button disabled={locked || (baseChanged('properties') || draft.conflicts['properties']) || work.legacy_blocked_pending === 'yes' || work.legacy_assignment_pending === 'yes'} onClick={() => {
        if (draft.properties.value.status !== 'legacy-blocked') void state.send('properties', () => props.client.prepareProperties(scope(), draft.properties.base, draft.properties.value as ProductProperties));
      }}>Save properties</Button>}
    </section>
    {work.legacy_blocked_pending === 'yes' && <section className="product-work-section"><h3>Resolve older blocked status</h3>
      <p>This work retained its older blocked status. Choose its current stage and an optional reason it is blocked.</p>
      <PropertyPicker label="Resolved status" value={draft.legacyBlocked.value.status} placeholder="Choose a status" disabled={locked}
        options={(['backlog', 'todo', 'in_progress', 'in_review'] as const).map(value => ({value, label: productStatusLabels[value]}))}
        onChange={status => change(current => ({...current, legacyBlocked: {...current.legacyBlocked, dirty: true, value: {...current.legacyBlocked.value, status: status as UnfinishedStatus}}}))}/>
      <TextField label="Blocking reason" value={draft.legacyBlocked.value.reason} disabled={locked} onChange={event => change(current => ({...current,
        legacyBlocked: {...current.legacyBlocked, dirty: true, value: {...current.legacyBlocked.value, reason: event.target.value}}}))}/>
      {conflict('legacy-blocked')}<Button disabled={locked || !draft.legacyBlocked.value.status || (baseChanged('legacy-blocked') || draft.conflicts['legacy-blocked'])} onClick={() => {
        const value = draft.legacyBlocked.value; if (value.status) void state.send('legacy-blocked', () => props.client.prepareLegacyBlocked(scope(), draft.legacyBlocked.base, value.status as UnfinishedStatus, value.reason));
      }}>Resolve blocked status</Button></section>}
    {work.legacy_assignment_pending === 'yes' && <section className="product-work-section"><h3>Resolve older assignment</h3>
      <p>Previously assigned to {work.legacy_assignee_display_name || 'a project member'}. Choose an accountable Owner and who is Working on it, or explicitly leave them unassigned.</p>
      <ProductWorkPeoplePicker environment={props} role="owner" value={draft.legacyAssignment.value.owner} disabled={locked} onChange={owner => change(current => ({...current,
        legacyAssignment: {...current.legacyAssignment, dirty: true, value: {...current.legacyAssignment.value, owner}}}))}/>
      <ProductWorkPeoplePicker environment={props} role="worker" value={draft.legacyAssignment.value.worker} disabled={locked} onChange={worker => change(current => ({...current,
        legacyAssignment: {...current.legacyAssignment, dirty: true, value: {...current.legacyAssignment.value, worker}}}))}/>
      {conflict('legacy-assignment')}<Button disabled={locked || (baseChanged('legacy-assignment') || draft.conflicts['legacy-assignment'])} onClick={() => void state.send('legacy-assignment', () => props.client.prepareLegacyAssignee(scope(),
        draft.legacyAssignment.base, draft.legacyAssignment.value.owner, draft.legacyAssignment.value.worker))}>Resolve assignment</Button></section>}
    {(!editingContract || work.status === 'done') && <section className="product-work-section"><h3>Required outputs</h3>{Object.keys(outcomes).length ? Object.entries(outcomes).map(([id, target]) =>
      <p key={id}>{target.kind === 'document' ? documentChoices.find(choice => choice.target.document_id === target.document_id
        && choice.target.collection_id === target.collection_id)?.label || 'Shared document' : 'Unsupported output'}
        {target.kind === 'document' && <span className="muted"> · {target.expected_revision === '0' ? 'New Doc' : `Expected revision ${target.expected_revision}`}</span>}</p>)
      : <p className="muted">No required outputs.</p>}</section>}
    {props.context}
    {mayComplete && <section className="product-work-section"><h3>Complete work</h3>
      {unfinishedPurpose && <p>Save or resolve the local purpose and property changes before completing this work.</p>}
      {Object.keys(outcomes).length ? <><p>{completionReady ? 'Required outputs are accepted for this purpose. Home will check them again when you complete this work.'
        : props.completionReadiness?.state === 'loading' ? 'Checking required outputs…' : 'Required outputs must be accepted for the current purpose before completion.'}</p>
        {!props.completionReadiness || props.completionReadiness.state === 'unsupported' ? <OutcomeState state="unsupported_operation" description="Completion from accepted outputs is not available here yet."/>
          : <Button disabled={locked || unfinishedPurpose || !completionReady || (baseChanged('completion') || draft.conflicts['completion'])} onClick={() => void state.send('completion', () => props.client.prepareCompletion(scope(),
            {work_revision: draft.completion.workBase, execution_contract_revision: draft.completion.contractBase}, {basis: 'accepted-outcomes', note: ''}))}>Complete with accepted outputs</Button>}</>
        : props.actor.kind === 'person' ? <><label><span id={`${labels}-completion`}>Completion note</span><textarea aria-labelledby={`${labels}-completion`} value={draft.completion.note} disabled={locked} onChange={event => change(current => ({...current,
          completion: {...current.completion, note: event.target.value, dirty: true}}))}/></label>
          <p className="muted">Explain the outcome. Home will confirm your current authority before completing this work.</p>
          <Button disabled={locked || unfinishedPurpose || !draft.completion.note || (baseChanged('completion') || draft.conflicts['completion'])} onClick={() => void state.send('completion', () => props.client.prepareCompletion(scope(),
            {work_revision: draft.completion.workBase, execution_contract_revision: draft.completion.contractBase}, {basis: 'human-note', note: draft.completion.note}))}>Complete with note</Button></>
          : <p>An authorized person can complete this work with a note.</p>}
      {conflict('completion')}
    </section>}
    <section className="product-work-section product-work-conversation" aria-label="Conversation"><h3>Conversation</h3>
      {!commentsCurrent || props.comments.state === 'loading' ? <LoadingState label="Loading conversation"/>
        : props.comments.state === 'unavailable' ? <OutcomeState state="retryable_error" description="The current conversation could not be loaded." action={<Button onClick={props.comments.onRefresh}>Refresh conversation</Button>}/>
          : <>{!props.comments.rows.length && <p className="muted">No comments yet.</p>}{props.comments.rows.map(comment => <article key={comment.sequence}><header><strong>{comment.display_name || 'Project member'}</strong></header>
            <p>{comment.body}</p><details><summary>Details</summary><dl><div><dt>Accepted time</dt><dd>{comment.accepted_at_ms}</dd></div><div><dt>Request ID</dt><dd>{comment.request_id}</dd></div></dl></details></article>)}
            {props.comments.cursor && <Button disabled={state.pending || !props.online} onClick={props.comments.onNext}>More comments</Button>}</>}
      <label><span id={`${labels}-comment`}>Comment</span><textarea aria-labelledby={`${labels}-comment`} value={draft.discussion.value} disabled={locked} onChange={event => change(current => ({...current,
        discussion: {...current.discussion, value: event.target.value, dirty: !!event.target.value}}))}/></label>
      {conflict('discussion')}<Button disabled={locked || !draft.discussion.value || (baseChanged('discussion') || draft.conflicts['discussion'])} onClick={() => void state.send('discussion', () => props.client.prepareComment(scope(), draft.discussion.base, draft.discussion.value))}>Post comment</Button>
    </section>
    <ProductWorkDetails work={work} draft={draft}/>
  </Surface>;
}

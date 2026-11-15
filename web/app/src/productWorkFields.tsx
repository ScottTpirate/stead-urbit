import {useId, useState} from 'react';
import {Button, Combobox, OutcomeState, PropertyPicker, TextField, type PickerOption} from './primitives';
import {newId} from './protocol';
import type {ProductContract, ProductProperties, ProductWorkDetail} from './productProtocol';
import {productWorkDocuments, productWorkPeople, type ProductWorkDraft, type ProductWorkEnvironment, type ProductWorkPropertyDraft} from './productWorkState';

export const productStatusLabels = {backlog: 'Backlog', todo: 'To do', in_progress: 'In progress', in_review: 'In review', done: 'Done', canceled: 'Canceled', 'legacy-blocked': 'Blocked (legacy)'};
export const productPriorityLabels = {none: 'No priority', low: 'Low', medium: 'Normal', high: 'High', urgent: 'Urgent'};
export function ProductWorkPeoplePicker({environment, role, value, onChange, disabled}: {environment: ProductWorkEnvironment; role: 'owner' | 'worker'; value: string; onChange: (value: string) => void; disabled: boolean}) {
  const people = productWorkPeople(environment.people, role, environment.scope.projectId, environment.sessionKey);
  const options: PickerOption[] = [{value: '', label: 'Unassigned'}, ...people.map(person => ({value: person.principalId,
    label: person.displayName || 'Project member', kind: person.kind === 'agent' ? 'agent' as const : 'human' as const}))];
  if (value && !people.some(person => person.principalId === value)) options.push({value, label: 'Current assignment unavailable', disabled: true});
  return <Combobox label={role === 'owner' ? 'Owner' : 'Working on it'} value={value} options={options} onChange={onChange} disabled={disabled}
    loading={environment.people.state === 'loading'} error={environment.people.state === 'unavailable' ? 'The current people list is unavailable.' : undefined}
    onRetry={() => void environment.onRefresh()}/>;
}
export function ProductWorkProperties({environment, value, onChange, disabled, creating = false}: {environment: ProductWorkEnvironment; value: ProductWorkPropertyDraft;
  onChange: (value: ProductWorkPropertyDraft) => void; disabled: boolean; creating?: boolean}) {
  const blockerLabel = useId();
  const patch = (next: Partial<ProductWorkPropertyDraft>) => onChange({...value, ...next});
  const statuses: PickerOption[] = Object.entries(productStatusLabels).filter(([status]) => status !== 'done' && status !== 'legacy-blocked')
    .map(([value, label]) => ({value, label}));
  if (value.status === 'done' || value.status === 'legacy-blocked') statuses.push({value: value.status, label: productStatusLabels[value.status], disabled: true});
  const mayAssignMe = productWorkPeople(environment.people, 'owner', environment.scope.projectId, environment.sessionKey).some(person => person.principalId === environment.actor.principalId);
  return <div className="product-work-properties">
    <PropertyPicker label="Type" value={value.type} options={[{value: 'task', label: 'Task'}, {value: 'deliverable', label: 'Deliverable'}, {value: 'problem', label: 'Problem'}]}
      disabled={disabled} onChange={type => patch({type: type as ProductProperties['type']})}/>
    <PropertyPicker label="Status" value={value.status} options={statuses} disabled={disabled} onChange={status => patch({status: status as ProductProperties['status'],
      ...(status === 'canceled' ? {blocked_reason: ''} : {})})}/>
    <PropertyPicker label="Priority" value={value.priority} options={Object.entries(productPriorityLabels).map(([value, label]) => ({value, label}))}
      disabled={disabled} onChange={priority => patch({priority: priority as ProductProperties['priority']})}/>
    <ProductWorkPeoplePicker environment={environment} role="owner" value={value.owner_principal_id} disabled={disabled} onChange={owner_principal_id => patch({owner_principal_id})}/>
    <ProductWorkPeoplePicker environment={environment} role="worker" value={value.worker_principal_id} disabled={disabled} onChange={worker_principal_id => patch({worker_principal_id})}/>
    {creating && <Button variant="quiet" disabled={disabled || !mayAssignMe} onClick={() => patch({owner_principal_id: environment.actor.principalId})}>Assign to me</Button>}
    {!['done', 'canceled'].includes(value.status) && <label className="product-work-blocker"><span id={blockerLabel}>Blocked by</span><textarea aria-labelledby={blockerLabel} value={value.blocked_reason} disabled={disabled}
      placeholder="Optional reason this work cannot move forward" onChange={event => patch({blocked_reason: event.target.value})}/></label>}
  </div>;
}
export function ProductWorkContractFields({environment, value, onChange, disabled, titleRef}: {environment: ProductWorkEnvironment; value: ProductContract;
  onChange: (value: ProductContract) => void; disabled: boolean; titleRef?: React.RefObject<HTMLInputElement | null>}) {
  const labels = useId();
  const [selected, setSelected] = useState('');
  const allChoices = productWorkDocuments(environment.documents, environment.scope.projectId, environment.sessionKey);
  const choices = allChoices.filter(choice => !Object.values(value.required_outcomes).some(target => target.kind === 'document'
    && target.project_id === choice.target.project_id && target.collection_id === choice.target.collection_id && target.document_id === choice.target.document_id));
  const patch = (next: Partial<ProductContract>) => onChange({...value, ...next});
  const choiceKey = (choice: typeof choices[number]) => [choice.target.project_id, choice.target.collection_id, choice.target.document_id,
    choice.target.expected_revision, choice.target.base_markdown_sha256].join('/');
  const selectedChoice = choices.find(choice => choiceKey(choice) === selected);
  return <div className="product-work-contract">
    <TextField ref={titleRef} label="Title" value={value.title} required disabled={disabled} onChange={event => patch({title: event.target.value})}/>
    <label><span id={`${labels}-purpose`}>Purpose</span><textarea aria-labelledby={`${labels}-purpose`} value={value.description} disabled={disabled} onChange={event => patch({description: event.target.value})}/></label>
    <label><span id={`${labels}-criteria`}>Acceptance criteria</span><textarea aria-labelledby={`${labels}-criteria`} value={value.acceptance_criteria} disabled={disabled} onChange={event => patch({acceptance_criteria: event.target.value})}/></label>
    <fieldset className="product-work-outcomes" disabled={disabled}><legend>Required outputs</legend>
      <p>Choose shared Docs this work must produce. Their expected saved revisions are kept with this purpose.</p>
      {Object.entries(value.required_outcomes).map(([id, target]) => {
        const label = target.kind === 'document' ? allChoices.find(choice => choice.target.collection_id === target.collection_id && choice.target.document_id === target.document_id)?.label ?? 'Shared document' : 'Unsupported output';
        return <div className="product-work-outcome" key={id}><span>{label}{target.kind === 'document' && <small>{target.expected_revision === '0' ? 'Create a new document' : `Expected Doc revision ${target.expected_revision}`}</small>}</span>
          <Button variant="quiet" disabled={disabled} aria-label={`Remove required output ${label}`} onClick={() => {
            const remaining = {...value.required_outcomes}; delete remaining[id]; patch({required_outcomes: remaining});
          }}>Remove</Button></div>;
      })}
      {!Object.keys(value.required_outcomes).length && <p>No required outputs. An authorized person can complete this work with a note.</p>}
      <div className="product-work-outcome-add"><Combobox label="Shared Doc" value={selected} disabled={disabled || Object.keys(value.required_outcomes).length >= 16}
        options={choices.map(choice => ({value: choiceKey(choice), label: choice.label,
          description: choice.target.expected_revision === '0' ? 'New shared Doc' : `Saved revision ${choice.target.expected_revision}`}))}
        loading={environment.documents.state === 'loading'} error={environment.documents.state === 'unavailable' ? 'Current shared Docs are unavailable.' : undefined}
        onRetry={() => void environment.onRefresh()} onChange={setSelected}/>
        <Button disabled={disabled || !selectedChoice || Object.keys(value.required_outcomes).length >= 16} onClick={() => {
          const choice = selectedChoice; if (!choice) return;
          patch({required_outcomes: {...value.required_outcomes, [newId()]: {...choice.target}}}); setSelected('');
        }}>Add required Doc</Button></div>
    </fieldset>
  </div>;
}
export function ProductWorkAttemptState({environment, draft, retry}: {environment: ProductWorkEnvironment; draft: ProductWorkDraft; retry: () => unknown}) {
  const attempt = draft.attempt;
  if (environment.access === 'revoked' || attempt?.phase === 'revoked') return <OutcomeState state="permission_revoked" description={attempt?.message}/>;
  if (!environment.online) return <OutcomeState state="disconnected_or_stale" description="Your local draft is kept. Reconnect and refresh before saving."/>;
  if (environment.access === 'read-only') return <OutcomeState state="read_only"/>;
  if (!attempt) return null;
  if (attempt.phase === 'preparing' || attempt.phase === 'saving') return <OutcomeState state="saving"/>;
  if (attempt.phase === 'unknown') return <OutcomeState state="outcome_unknown" description={attempt.message}
    action={<Button disabled={!environment.online || environment.access !== 'writable'} onClick={() => void retry()}>Check same request</Button>}/>;
  if (attempt.phase === 'accepted') return <OutcomeState state="accepted" description={attempt.message || (attempt.awaitingReadback ? 'Home accepted the change. Loading its current saved version…' : 'Home accepted this change.')}
    action={attempt.awaitingReadback ? <Button onClick={() => void environment.onRefresh()}>Refresh saved work</Button> : undefined}/>;
  return <OutcomeState state={attempt.phase === 'conflict' ? 'conflict' : 'retryable_error'} description={attempt.message}
    action={<Button onClick={() => void environment.onRefresh()}>Refresh current work</Button>}/>;
}
export function ProductWorkDetails({work, draft}: {work?: ProductWorkDetail; draft: ProductWorkDraft}) {
  return <details className="product-work-details"><summary>Details</summary><dl>
    <div><dt>Work ID</dt><dd>{draft.resourceId}</dd></div>
    {work && <><div><dt>Work revision</dt><dd>{work.work_revision}</dd></div><div><dt>Execution contract revision</dt><dd>{work.execution_contract_revision}</dd></div>
      <div><dt>Discussion sequence</dt><dd>{work.discussion_sequence}</dd></div></>}
    {draft.attempt?.prepared && <><div><dt>Request ID</dt><dd>{draft.attempt.prepared.command.request_id}</dd></div><div><dt>Operation</dt><dd>{draft.attempt.prepared.command.operation}</dd></div></>}
    {draft.previousAttempt?.prepared && <div><dt>Previous request</dt><dd>{draft.previousAttempt.prepared.command.request_id} · {draft.previousAttempt.receipt?.status ?? 'Not confirmed'}</dd></div>}
  </dl></details>;
}

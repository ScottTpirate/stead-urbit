// Synthetic interaction reference only. No Home, credentials, API or worker.
import { StrictMode, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Button, Combobox, Dialog, EmptyState, Menu, OutcomeState, PersonBadge, PropertyPicker, StatusBadge, TextField, type OutcomeStateKind } from '../src/primitives';
import {DocumentBody} from '../src/DocumentBody';
import {Icon} from '../src/Icon';
import {Markdown} from '../src/Markdown';
import '../src/style.css';
import '../src/work.css';
import './interaction-reference.css';

const statuses = [
  {value: 'todo', label: 'To do'}, {value: 'in_progress', label: 'In progress'},
  {value: 'in_review', label: 'In review'}, {value: 'done', label: 'Done'},
];
const people = [
  {value: '', label: 'Unassigned'},
  {value: 'maya', label: 'Maya Chen', description: 'Project steward', kind: 'human' as const},
  {value: 'sam', label: 'Sam Rivera', description: 'Designer', kind: 'human' as const},
  {value: 'inactive', label: 'Unavailable member', disabled: true, kind: 'human' as const},
  {value: 'docs-agent', label: 'Docs editor', description: 'Drafts and document changes', kind: 'agent' as const},
];
const stateNames: OutcomeStateKind[] = ['read_only', 'dirty_draft', 'saving', 'accepted', 'disconnected_or_stale', 'outcome_unknown', 'conflict', 'permission_revoked', 'retryable_error', 'unsupported_operation'];

function Reference() {
  const [status, setStatus] = useState('todo');
  const [owner, setOwner] = useState('');
  const [worker, setWorker] = useState('docs-agent');
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('Prepare the launch guide');
  const [title, setTitle] = useState(draft);
  const [readOnly, setReadOnly] = useState(false);
  const [variant, setVariant] = useState('normal');
  const [layout, setLayout] = useState('preview');
  const [documentText, setDocumentText] = useState('This document is a readable reference surface. Start with a clear purpose, keep the steps short, and link supporting context beside the work.\n\n## Your first day\n\n1. Meet the project steward.\n2. Read the event brief.\n3. Choose a task and ask a question.\n\n- [x] Read the project purpose.\n- [ ] Choose a first task.\n\n> Everyone should know what to do next.\n\n![Document diagram](https://attachments.example/document.svg)\n\n![Unavailable document image](relative-diagram.svg)');
  const [fullSource, setFullSource] = useState(false);
  const [action, setAction] = useState('No reference action selected');
  const titleInput = useRef<HTMLInputElement>(null);
  const crowded = variant === 'crowded';
  return <main className="interaction-reference">
    <header className="reference-heading"><p className="reference-notice">Synthetic interaction reference · No Home connection or saved business data</p>
      <h1>Work, Docs and review</h1><p>Representative controls and states for keyboard, focus and layout inspection.</p>
      <div className="reference-controls">
        <PropertyPicker label="Reference data" value={variant} onChange={setVariant} options={[
          {value: 'normal', label: 'Normal'}, {value: 'empty', label: 'Empty'}, {value: 'crowded', label: 'Crowded'},
        ]}/>
        <PropertyPicker label="Work layout" value={layout} onChange={setLayout} options={[
          {value: 'preview', label: 'Preview'}, {value: 'list', label: 'List'}, {value: 'full', label: 'Full detail'}, {value: 'composer', label: 'Create'},
        ]}/>
        <label className="reference-checkbox"><input type="checkbox" checked={readOnly} onChange={event => setReadOnly(event.target.checked)}/>Read-only reference</label>
        <Button onClick={() => setOpen(true)} disabled={readOnly}>Edit reference work</Button>
      </div>
    </header>
    <section className="reference-panel" aria-labelledby="work-reference-title">
      <div className="reference-section-heading"><h2 id="work-reference-title">Work</h2>
        <Menu label="More reference actions" triggerLabel={<Icon name="ellipsis"/>} items={[
          {value: 'inspect', label: 'Inspect reference', onSelect: () => setAction('Inspect reference selected')},
        ]}/>
        <Menu label="Work actions" items={[
          {value: 'copy', label: 'Copy link', onSelect: () => setAction('Copy link selected')},
          {value: 'unavailable', label: 'Unavailable action', disabled: true, onSelect: () => setAction('Invalid disabled action')},
          {value: 'open', label: 'Open details', onSelect: () => setAction('Open details selected')},
          {value: 'delete', label: 'Delete…', danger: true, disabled: readOnly, onSelect: () => setAction('Delete selected — reference only')},
        ]}/></div>
      {variant === 'empty' ? <EmptyState title="Start with an outcome" description="Create the first task for this project." action={<Button onClick={() => setOpen(true)} disabled={readOnly}>Create reference work</Button>}/>
        : <div className={`work-view${layout === 'list' ? '' : layout === 'composer' ? ' with-detail with-composer' : layout === 'full' ? ' with-detail full-detail' : ' with-detail'}`}>
          <div className="view-list" aria-label="Synthetic work list">{Array.from({length: crowded ? 12 : 3}, (_, index) => <div className="resource-row work-row" key={index}>
            <div className="resource-summary"><span className="work-key">DEMO-{142 + index}</span>
              <h2><button type="button" className="work-title" onClick={() => setLayout('preview')}>{index === 0 ? title : crowded ? 'Gather accessible event guidance for contributors with long names and multilingual requirements — 東京' : ['Arrange the launch event', 'Collect feedback'][index - 1]}</button></h2></div>
            <div className="work-properties"><span className="work-property">{index === 0 ? statuses.find(item => item.value === status)!.label : 'To do'}</span><span className="work-property work-assignee">Unassigned</span></div>
            <div className="row-actions"><button type="button" className="work-property work-overflow" aria-label={`Reference actions for DEMO-${142 + index}`} disabled><Icon name="ellipsis"/></button></div>
          </div>)}</div>
          {layout === 'composer' ? <article className="stead-surface creation work-detail" aria-label="Synthetic create Work"><h2>Create work</h2><TextField label="New work title" placeholder="What needs to happen?" disabled={readOnly}/><p>Task · To do · No priority · Unassigned</p><Button variant="primary" disabled>Create work</Button></article>
          : layout !== 'list' && <article className="stead-surface work-detail reference-work-detail"><p className="reference-work-key">DEMO-142 · Synthetic Work</p><h3>{title}</h3>
            <p>Help new members understand how to join the project and find the context they need.</p>
            <h4>Acceptance criteria</h4><ul><li>Explain the first three steps.</li><li>Include an accessible checklist.</li></ul>
            <div className="reference-properties">
              <PropertyPicker label="Status" value={status} options={statuses} onChange={setStatus} disabled={readOnly}/>
              <Combobox label="Owner" value={owner} options={people.filter(person => person.kind !== 'agent')} onChange={setOwner} disabled={readOnly}/>
              <Combobox label="Working on it" value={worker} options={people} onChange={setWorker} disabled={readOnly}/>
            </div>
            <PersonBadge name={crowded ? 'Alexandria Montgomery-Rivera with a deliberately long display name' : 'Maya Chen'} inherited/>
            <p><PersonBadge name="Docs editor" kind="agent"/></p>
            <OutcomeState state={readOnly ? 'read_only' : 'outcome_unknown'}/>
          </article>}
        </div>}
      <p role="status" className="reference-action-result">{action}</p>
    </section>
    <section className="reference-panel reference-doc" aria-labelledby="doc-reference-title"><p className="reference-work-key">Synthetic Docs read reference</p><h2 id="doc-reference-title">Welcome to the project</h2>
      <DocumentBody text={documentText} header="" editable={!readOnly} locked={false} isNew={false} fullSource={fullSource} onFullSource={setFullSource} onChange={setDocumentText}/>
    </section>
    <section className="reference-panel reference-doc" aria-labelledby="attachment-reference-title">
      <p className="reference-work-key">Synthetic repository Markdown · Read only · No attachment fetching</p>
      <h2 id="attachment-reference-title">Repository attachments</h2>
      <Markdown origin="repository" text={`![Repository diagram](./assets/diagram.svg)\n\n![External diagram](https://attachments.example/repository.svg)\n\n![Unavailable repository image](//attachments.example/blocked.svg)\n\n![${crowded ? 'A deliberately long image description — 雪 🪴 '.repeat(15) : 'Linked diagram'}](../images/linked.svg)\n\n[![Related diagram](../related.svg)](https://attachments.example/guide)`}/>
    </section>
    <section className="reference-panel" aria-labelledby="review-reference-title"><p className="reference-work-key">Synthetic review reference · No submitted change</p><h2 id="review-reference-title">Clarify the onboarding guide</h2>
      <p><PersonBadge name="Docs editor" kind="agent"/> <StatusBadge label="Ready for review" tone="active"/></p>
      <div className="reference-diff"><p><span>Removed</span> <del>Ask someone for access.</del></p><p><span>Added</span> <ins>Ask the project steward for the access you need.</ins></p></div>
      <p className="muted">Decision controls are disabled in this visual reference.</p><div className="reference-controls"><Button disabled>Request changes</Button><Button variant="primary" disabled>Accept change</Button></div>
    </section>
    <section className="reference-panel" aria-labelledby="states-reference-title"><h2 id="states-reference-title">Outcome states</h2><p>All states below are synthetic examples, including Saved.</p>
      <div className="reference-states">{stateNames.map(state => <OutcomeState key={state} state={state}/>)}</div>
      <div className="reference-controls"><Combobox label="Unavailable members" value="" options={[]} onChange={() => {}} error="Project members could not be loaded."/>
        <Combobox label="Loading members" value="" options={[]} onChange={() => {}} loading/>
        <Combobox label="Empty members" value="" options={[]} onChange={() => {}}/></div>
    </section>
    <Dialog open={open} title="Edit reference work" description="Changes update only this synthetic preview." onClose={() => setOpen(false)} initialFocus={titleInput}
      footer={<><Button onClick={() => setOpen(false)}>Cancel</Button><Button variant="primary" disabled={!draft.trim()} onClick={() => { setTitle(draft); setOpen(false); }}>Update preview</Button></>}>
      <TextField ref={titleInput} label="Title" value={draft} onChange={event => setDraft(event.target.value)}/>
      <PropertyPicker label="Dialog status" value={status} options={statuses} onChange={setStatus}/>
    </Dialog>
  </main>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><Reference/></StrictMode>);

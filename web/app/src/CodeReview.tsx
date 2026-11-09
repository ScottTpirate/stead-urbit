import { useId, useState } from 'react';
import { HomeError, type CodeReviewKey, type Fields, type HomeClient } from './api';
import { Button, Surface, TextField } from './primitives';
import { newId } from './protocol';

const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u;
const OID = /^[a-f0-9]{40}$/u;
const validKey = (key: CodeReviewKey) => UUID.test(key.proposal_id) && /^(?:[1-9]|[1-5][0-9]|6[0-4])$/u.test(key.revision);
const initialDraft = { work_id: '', ref: 'refs/heads/main', base_oid: '', head_oid: '', delegation_id: '' };
type WorkChoice = { id: string; title: string };

export function CodeReview({ client, project, writable, manage, principal }: {
  client: HomeClient; project: string; writable: boolean; manage: boolean; principal: string;
}) {
  const workPicker = useId();
  const [mode, setMode] = useState<'find' | 'propose'>('find');
  const [selection, setSelection] = useState<CodeReviewKey>({ proposal_id: '', revision: '1' });
  const [draft, setDraft] = useState(initialDraft);
  const [proposal, setProposal] = useState<Fields | null>(null);
  const [work, setWork] = useState<WorkChoice[]>([]);
  const [cursor, setCursor] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const pending = client.pendingCodeMerge(project);

  async function perform(operation: () => Promise<void>, failure: string) {
    setBusy(true); setNotice(''); setError('');
    try { await operation(); }
    catch (error) {
      const uncertain = client.pendingCodeMerge(project);
      setError(uncertain ? 'The merge is awaiting confirmation. Retry the same request after reconnecting.'
        : error instanceof HomeError && error.code === 'stale-target'
          ? 'The target branch moved. Open the current commit and submit a new revision.'
          : failure);
    } finally { setBusy(false); }
  }
  async function listWork(next = '') {
    const result = await client.query({ kind: 'work', project_id: project, container_id: '', resource_id: '', search: '', cursor: next });
    const rows = Object.values(result.rows).flatMap(row => row.resource_id && row.title ? [{ id: row.resource_id, title: row.title }] : []);
    setWork(current => next ? [...current, ...rows.filter(row => !current.some(prior => prior.id === row.id))] : rows);
    setCursor(result.cursor);
  }
  function beginProposal(prior?: Fields) {
    const edit = !!prior;
    setSelection(edit ? { proposal_id: prior.proposal_id!, revision: String(Number(prior.revision) + 1) }
      : { proposal_id: newId(), revision: '1' });
    setDraft(edit ? { work_id: prior.work_id!, ref: prior.ref!, base_oid: prior.merged_revision ? prior.head_oid! : prior.base_oid!,
      head_oid: '', delegation_id: '' } : initialDraft);
    setMode('propose'); setProposal(null);
    void perform(() => listWork(), 'The Home could not list this project’s Work items.');
  }
  async function find(key: CodeReviewKey) {
    const row = await client.code(project, { action: 'proposal', ...key });
    setSelection(key); setProposal(row); setMode('find');
  }
  async function merge(key?: CodeReviewKey) {
    const receipt = await client.mergeCode(project, key);
    setNotice('Merged at repository revision ' + receipt.repository_revision + '.');
    // The receipt already confirms the write. Reload the selected proposal if
    // available, without turning a later read failure into a second merge.
    const selected = key ?? pending;
    if (selected) await find({ proposal_id: selected.proposal_id, revision: selected.revision }).catch(() => setProposal(null));
  }
  const canReview = manage && !!proposal && proposal.author !== principal && !proposal.merged_revision;
  const canSubmit = validKey(selection) && UUID.test(draft.work_id) && draft.ref.startsWith('refs/heads/')
    && OID.test(draft.base_oid) && OID.test(draft.head_oid)
    && (draft.delegation_id ? UUID.test(draft.delegation_id) : writable);

  return <Surface className="code-review-panel">
    <h2>Change review</h2>
    <p>Propose a pushed commit against a specific branch and link it to a Work item.</p>
    <div className="actions">
      {mode === 'propose' ? <Button disabled={busy} onClick={() => { setMode('find'); setError(''); }}>Find a proposal</Button>
        : <Button disabled={busy} onClick={() => beginProposal()}>{writable ? 'New proposal' : 'Use proposal delegation'}</Button>}
    </div>
    {pending && <div role="status">
      <p>Merge awaiting confirmation for proposal {pending.proposal_id}, revision {pending.revision}.</p>
      <Button disabled={busy} onClick={() => void perform(() => merge(), 'The merge could not be confirmed.')}>Retry this merge</Button>
    </div>}
    {mode === 'find' && <form onSubmit={event => {
      event.preventDefault();
      void perform(() => find(selection), 'The Home could not open that proposal revision.');
    }}>
      <TextField label="Proposal ID" value={selection.proposal_id} disabled={busy} required maxLength={36} spellCheck={false}
        onChange={event => { setSelection({ ...selection, proposal_id: event.target.value }); setProposal(null); }} />
      <TextField label="Proposal revision" type="number" min={1} max={64} required value={selection.revision} disabled={busy}
        onChange={event => { setSelection({ ...selection, revision: event.target.value }); setProposal(null); }} />
      <Button type="submit" disabled={!validKey(selection)} pending={busy} pendingLabel="Checking the Home">Open proposal</Button>
    </form>}
    {mode === 'propose' && <form onSubmit={event => {
      event.preventDefault();
      if (!canSubmit) return;
      void perform(async () => {
        await client.code(project, { action: 'submit', ...selection, ...draft });
        setNotice('Proposal revision accepted.');
        await find(selection);
      }, 'The Home could not confirm this proposal. Check the Work item, branch, and commit IDs.');
    }}>
      <p>Submitting proposal revision {selection.revision}. Share its ID with your reviewer.</p>
      <TextField label="Proposal ID" value={selection.proposal_id} readOnly />
      <div className="stead-field">
        <label htmlFor={workPicker}>Work item</label>
        <select id={workPicker} value={draft.work_id} disabled={busy} required
          onChange={event => setDraft({ ...draft, work_id: event.target.value })}>
          <option value="">Choose a Work item</option>
          {draft.work_id && !work.some(item => item.id === draft.work_id) && <option value={draft.work_id}>{draft.work_id}</option>}
          {work.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
      </div>
      {cursor && <Button disabled={busy} onClick={() => void perform(() => listWork(cursor), 'The Home could not load more Work items.')}>More Work items</Button>}
      <TextField label="Target branch ref" value={draft.ref} required maxLength={128} disabled={busy}
        onChange={event => setDraft({ ...draft, ref: event.target.value })} />
      <TextField label="Current target commit" description="Use its full Git ID, or forty zeroes for a new branch." value={draft.base_oid}
        required minLength={40} maxLength={40} disabled={busy} spellCheck={false} onChange={event => setDraft({ ...draft, base_oid: event.target.value })} />
      <TextField label="Proposed commit" description="Push the commit on a separate branch before proposing it." value={draft.head_oid}
        required minLength={40} maxLength={40} disabled={busy} spellCheck={false} onChange={event => setDraft({ ...draft, head_oid: event.target.value })} />
      <TextField label="Delegation ID" description={writable ? 'Optional for a contributor.' : 'Required for delegated proposal access.'}
        value={draft.delegation_id} disabled={busy} required={!writable} maxLength={36} spellCheck={false}
        onChange={event => setDraft({ ...draft, delegation_id: event.target.value })} />
      <Button type="submit" variant="primary" disabled={!canSubmit} pending={busy} pendingLabel="Submitting revision">Submit proposal</Button>
    </form>}
    {proposal && <section aria-label="Exact proposal">
      <h3>Revision {proposal.revision}</h3>
      <p>{proposal.merged_revision ? 'Merged at repository revision ' + proposal.merged_revision + '.'
        : proposal.reviewer ? 'Approved for this exact revision.' : 'Awaiting review.'}</p>
      <TextField label="Linked Work item ID" value={proposal.work_id ?? ''} readOnly />
      <TextField label="Reviewed target branch" value={proposal.ref ?? ''} readOnly />
      <TextField label="Reviewed base commit" value={proposal.base_oid ?? ''} readOnly />
      <TextField label="Reviewed head commit" value={proposal.head_oid ?? ''} readOnly />
      <div className="actions">
        {proposal.author === principal && Number(proposal.revision) < 64 && <Button disabled={busy} onClick={() => beginProposal(proposal)}>Propose a new revision</Button>}
        {canReview && !proposal.reviewer && <Button disabled={busy} onClick={() => void perform(async () => {
          await client.code(project, { action: 'approve', ...selection });
          await find(selection);
        }, 'The Home could not confirm approval for this exact revision.')}>Approve this revision</Button>}
        {canReview && proposal.reviewer && <Button disabled={busy || !!pending} variant="primary"
          onClick={() => void perform(() => merge(selection), 'The Home rejected the merge. Check the branch protection and current target.')}>Merge this revision</Button>}
        {manage && !proposal.merged_revision && <Button disabled={busy} onClick={() => void perform(async () => {
          const result = await client.code(project, { action: 'protect', ref: proposal.ref! });
          if (result.status !== 'protected') throw new HomeError('invalid_response');
          setNotice('Target branch protected.');
        }, 'The Home could not confirm branch protection.')}>Protect target branch</Button>}
      </div>
    </section>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </Surface>;
}

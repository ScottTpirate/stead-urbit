import { useEffect, useId, useRef, useState } from 'react';
import { HomeError, UUID, packRefs, type ExternalMerge, type Fields, type HomeClient } from './api';
import { MAX_ARTIFACT_BYTES, parseReviewArtifact, refLabel, reviewBranches, reviewRequest } from './externalReview';
import { Button, Surface, TextField } from './primitives';
import { newId } from './protocol';

type WorkItem = { id: string; title: string };
type Draft = { proposal_id: string; revision: string; work_id: string; source: string; base_snapshot: string; generation: string };

function ReviewFact({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd><code>{value}</code></dd></div>;
}

function reviewStatus(row: Fields, snapshot: Fields) {
  if (row.merged_revision) return 'Merged';
  if (row.base_snapshot !== snapshot.snapshot || row.generation !== snapshot.generation) return 'Snapshot changed';
  return row.reviewer ? 'Approved' : 'Awaiting review';
}

export function CodeExternalReview({ client, project, writable, manage, atCapacity, principal, snapshot, refreshSnapshot }: {
  client: HomeClient; project: string; writable: boolean; manage: boolean; atCapacity: boolean; principal: string;
  snapshot: Fields; refreshSnapshot: () => Promise<void>;
}) {
  const workPicker = useId();
  const branchPicker = useId();
  const [lookup, setLookup] = useState('');
  const [proposal, setProposal] = useState<Fields | null>(null);
  const [reviews, setReviews] = useState<Fields[] | null>(null);
  const [reviewListFailed, setReviewListFailed] = useState(false);
  const [reviewListVersion, setReviewListVersion] = useState(0);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [work, setWork] = useState<WorkItem[]>([]);
  const [cursor, setCursor] = useState('');
  const [artifact, setArtifact] = useState<ExternalMerge | null>(null);
  const [merged, setMerged] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const request = useRef<{ key: string; id: string } | null>(null);
  const proofRequest = useRef<{ key: string; id: string } | null>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const lookupDisclosure = useRef<HTMLDetailsElement>(null);
  const pending = client.pendingExternalMerge(project);
  const refs = packRefs(snapshot);
  const target = snapshot.head!;
  const sourceChoices = reviewBranches(refs, target);
  const targetName = refLabel(target);
  const source = sourceChoices.find(row => row.key === draft?.source);
  const snapshotAvailable = snapshot.generation !== undefined;
  const current = snapshotAvailable && proposal?.base_snapshot === snapshot.snapshot && proposal?.generation === snapshot.generation;
  const draftCurrent = snapshotAvailable && draft?.base_snapshot === snapshot.snapshot && draft?.generation === snapshot.generation;
  const accepted = !!proposal && (merged === `${proposal.proposal_id}/${proposal.revision}` || !!proposal.merged_revision);
  const editable = writable && !atCapacity;
  const canReview = manage && editable && !!proposal && current && proposal.author !== principal && !accepted;
  const canSubmit = editable && !pending && draftCurrent && !!draft && UUID.test(draft.work_id) && !!source
    && targetName.startsWith('refs/heads/');
  const selectedTitle = proposal?.work_title || reviews?.find(row => row.proposal_id === proposal?.proposal_id)?.work_title;

  useEffect(() => {
    let active = true;
    setReviewListFailed(false);
    void client.externalReviews(project).then(rows => {
      if (active) setReviews(rows);
    }).catch(() => {
      if (active) { setReviews(null); setReviewListFailed(true); }
    });
    return () => { active = false; };
  }, [client, project, snapshot, reviewListVersion]);

  useEffect(() => { if (proposal && !draft) detailHeading.current?.focus(); }, [proposal?.proposal_id, proposal?.revision, !!draft]);

  async function perform(operation: () => Promise<void>, failure: string) {
    setBusy(true); setError(''); setNotice('');
    try { await operation(); }
    catch (reason) {
      setError(client.pendingExternalMerge(project)
        ? 'The Home did not confirm the merge. You can retry the same request after reconnecting.'
        : reason instanceof HomeError && ['stale-selection', 'stale_selection', 'stale-target', 'source-conflict', 'stale-review', 'stale_review'].includes(reason.code)
          ? 'The proposal or Git snapshot changed. Refresh the snapshot and open the latest revision.' : failure);
    } finally { setBusy(false); }
  }

  function requestId(fields: Fields) {
    const key = JSON.stringify(fields);
    if (request.current?.key !== key) request.current = { key, id: newId() };
    return request.current.id;
  }

  async function listWork(next = '') {
    const view = await client.query({ kind: 'work', project_id: project, container_id: '', resource_id: '', search: '', cursor: next });
    const rows = Object.values(view.rows).flatMap(row => row.resource_id && row.title ? [{ id: row.resource_id, title: row.title }] : []);
    setWork(prior => next ? [...prior, ...rows.filter(row => !prior.some(item => item.id === row.id))] : rows);
    setCursor(view.cursor);
  }

  async function open(id: string) {
    const selected = await client.code(project, { action: 'external-proposal', proposal_id: id });
    setLookup(id); setProposal(selected); setDraft(null); setArtifact(null);
  }

  function propose(prior?: Fields) {
    if (!editable || snapshot.generation === undefined) return;
    request.current = null;
    setArtifact(null);
    setDraft({ proposal_id: prior?.proposal_id ?? newId(), revision: prior ? String(Number(prior.revision) + 1) : '1',
      work_id: prior?.work_id ?? '', source: sourceChoices.find(row => row.name === prior?.source_ref)?.key ?? '',
      base_snapshot: snapshot.snapshot!, generation: snapshot.generation });
    void perform(() => listWork(), 'The Home could not load this project’s Work items.');
  }

  async function submit() {
    if (!canSubmit || !draft || !source) return;
    const payload = { action: 'external-submit' as const, proposal_id: draft.proposal_id, revision: draft.revision,
      work_id: draft.work_id, source_ref: source.name, ref: targetName, base_oid: refs[target]!, head_oid: source.oid,
      base_snapshot: draft.base_snapshot, generation: draft.generation };
    await client.code(project, { ...payload, request_id: requestId(payload) });
    request.current = null;
    setLookup(payload.proposal_id); setDraft(null); setProposal(null);
    setNotice('Proposal submitted for review.');
    setReviewListVersion(version => version + 1);
    await open(payload.proposal_id).catch(() => {});
  }

  async function approve() {
    if (!canReview || !proposal || proposal.reviewer) return;
    const payload = { action: 'external-approve' as const, proposal_id: proposal.proposal_id!, revision: proposal.revision!,
      base_snapshot: proposal.base_snapshot!, base_oid: proposal.base_oid!, head_oid: proposal.head_oid! };
    await client.code(project, { ...payload, request_id: requestId(payload) });
    request.current = null;
    setProposal({ ...proposal, reviewer: principal });
    setNotice('Approved this exact revision.');
    setReviewListVersion(version => version + 1);
    await open(payload.proposal_id).catch(() => {});
  }

  async function loadArtifact(file: File) {
    setArtifact(null);
    if (!proposal || !file.size || file.size > MAX_ARTIFACT_BYTES) throw new HomeError('invalid_review_artifact');
    const raw = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(await file.arrayBuffer());
    setArtifact(parseReviewArtifact(raw, project, snapshot, proposal));
    setNotice('Signed proof loaded for this revision.');
  }

  function downloadRequest(row: Fields) {
    const key = [row.proposal_id, row.revision, row.base_snapshot].join('/');
    if (proofRequest.current?.key !== key) proofRequest.current = { key, id: newId() };
    const file = new Blob([JSON.stringify(reviewRequest(row, proofRequest.current.id), null, 2) + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url; link.download = 'stead-review-request.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function merge(input?: ExternalMerge) {
    if (input && !canReview) return;
    const receipt = await client.mergeExternalCode(project, input);
    setMerged(`${receipt.proposal_id}/${receipt.revision}`);
    setArtifact(null);
    setNotice('The Home confirmed the merge.');
    setReviewListVersion(version => version + 1);
    await refreshSnapshot();
  }

  return <Surface className="code-review-panel">
    <h2>Change review</h2>
    {pending && <div role="status">
      <p>Merge awaiting confirmation for proposal {pending.proposal_id}, revision {pending.revision}.</p>
      <Button disabled={busy || !manage} onClick={() => void perform(() => merge(), 'The Home could not confirm this merge.')}>Retry this merge</Button>
    </div>}
    {draft ? <form onSubmit={event => { event.preventDefault(); void perform(submit, 'The Home could not confirm this proposal.'); }}>
      <h3>{Number(draft.revision) > 1 ? `New revision ${draft.revision}` : 'New proposal'}</h3>
      <div className="stead-field">
        <label htmlFor={workPicker}>Work item</label>
        <select id={workPicker} value={draft.work_id} disabled={busy} required
          onChange={event => setDraft({ ...draft, work_id: event.target.value })}>
          <option value="">Choose a Work item</option>
          {draft.work_id && !work.some(row => row.id === draft.work_id) && <option value={draft.work_id}>{draft.work_id}</option>}
          {work.map(row => <option key={row.id} value={row.id}>{row.title}</option>)}
        </select>
      </div>
      {cursor && <Button disabled={busy} onClick={() => void perform(() => listWork(cursor), 'The Home could not load more Work items.')}>More Work items</Button>}
      <div className="stead-field">
        <label htmlFor={branchPicker}>Source branch</label>
        <select id={branchPicker} value={draft.source} disabled={busy} required
          onChange={event => setDraft({ ...draft, source: event.target.value })}>
          <option value="">Choose a pushed branch</option>
          {sourceChoices.map(row => <option key={row.key} value={row.key}>{row.name.replace(/^refs\/heads\//u, '')}</option>)}
        </select>
      </div>
      <p>Target <code>{targetName}</code></p>
      {!draftCurrent && <p role="alert">The repository snapshot changed. Cancel this draft and start again from the current one.</p>}
      <div className="actions">
        <Button type="submit" variant="primary" disabled={!canSubmit} pending={busy} pendingLabel="Submitting proposal">Submit proposal</Button>
        <Button disabled={busy} onClick={() => { setDraft(null); setError(''); }}>Cancel</Button>
      </div>
    </form> : <>
      <div className="actions">
        {editable && !pending && <Button disabled={busy || !snapshotAvailable || !sourceChoices.length} onClick={() => propose()}>New proposal</Button>}
        {reviewListFailed && <Button disabled={busy} onClick={() => setReviewListVersion(version => version + 1)}>Retry review list</Button>}
      </div>
      {reviewListFailed && <p role="alert">The Home could not load change reviews.</p>}
      {!reviewListFailed && !reviews && <p role="status">Loading reviews…</p>}
      {reviews?.length === 0 && <p>No proposals to review yet.</p>}
      {!!reviews?.length && <ul className="external-review-list" aria-label="Change proposals">{reviews.map(row => <li key={row.proposal_id}>
        <Button variant="quiet" disabled={busy} aria-pressed={proposal?.proposal_id === row.proposal_id}
          onClick={() => void perform(() => open(row.proposal_id!), 'The Home could not open that proposal.')}>
          <strong>{row.work_title || row.source_ref!.slice(11)}</strong>
          <span>{reviewStatus(row, snapshot)} · Revision {row.revision}</span>
        </Button>
      </li>)}</ul>}
      <details ref={lookupDisclosure}><summary>Open by proposal ID</summary>
        <form onSubmit={event => {
          event.preventDefault();
          if (UUID.test(lookup.trim())) void perform(async () => {
            await open(lookup.trim());
            if (lookupDisclosure.current) lookupDisclosure.current.open = false;
          }, 'The Home could not open that proposal.');
        }}>
          <TextField label="Proposal ID" value={lookup} disabled={busy} required maxLength={36} spellCheck={false}
            onChange={event => setLookup(event.target.value)} />
          <Button type="submit" disabled={busy || !UUID.test(lookup.trim())}>Open proposal</Button>
        </form>
      </details>
      {editable && !snapshotAvailable && <p>Refresh the snapshot to start a proposal or review.</p>}
      {editable && snapshotAvailable && !sourceChoices.length && <p>Push a feature branch with changes to start a proposal.</p>}
      {proposal && <section aria-label="Exact proposal">
        <h3 ref={detailHeading} tabIndex={-1}>{selectedTitle ? `${selectedTitle} · ` : ''}Revision {proposal.revision}</h3>
        <p>{accepted ? 'Merged.' : !current ? 'The repository snapshot changed.' : proposal.reviewer ? 'Approved.' : 'Awaiting review.'}</p>
        <details open={canReview}><summary>Reviewed branches and commits</summary>
          <dl className="code-review-facts">
            <ReviewFact label="Source branch" value={proposal.source_ref!} />
            <ReviewFact label="Target branch" value={proposal.ref!} />
            <ReviewFact label="Proposed commit" value={proposal.head_oid!} />
            <ReviewFact label="Target commit" value={proposal.base_oid!} />
            <ReviewFact label="Linked Work item ID" value={proposal.work_id!} />
            <ReviewFact label="Proposal ID" value={proposal.proposal_id!} />
            <ReviewFact label="Base snapshot SHA-256" value={proposal.base_snapshot!} />
            {proposal.merged_snapshot && <ReviewFact label="Merged snapshot SHA-256" value={proposal.merged_snapshot} />}
          </dl>
        </details>
        <div className="actions">
          {editable && snapshotAvailable && !pending && !accepted && proposal.author === principal && Number(proposal.revision) < 64
            && <Button disabled={busy || !sourceChoices.length} onClick={() => propose(proposal)}>Propose a new revision</Button>}
          {canReview && !proposal.reviewer && !pending && <Button disabled={busy}
            onClick={() => void perform(approve, 'The Home could not confirm approval.')}>Approve this revision</Button>}
        </div>
        {canReview && !!proposal.reviewer && !pending && <details className="code-proof" open={!!artifact || undefined}>
          <summary>Merge with signed proof</summary>
          <p>Give the request file to your workspace operator to prepare the signed proof.</p>
          <Button disabled={busy} onClick={() => downloadRequest(proposal)}>Download proof request</Button>
          <TextField label={artifact ? 'Replace signed proof file' : 'Signed proof file'} type="file" accept=".json,application/json" disabled={busy}
            description="Import the verification artifact prepared for this exact revision."
            onChange={event => {
              const file = event.target.files?.[0];
              event.target.value = '';
              if (file) void perform(() => loadArtifact(file), 'This signed proof does not match the selected revision and snapshot.');
            }} />
          {artifact && <Button variant="primary" disabled={busy}
            onClick={() => void perform(() => merge(artifact), 'The Home declined this merge. Check the current snapshot and signed proof.')}>Merge this revision</Button>}
        </details>}
      </section>}
    </>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </Surface>;
}

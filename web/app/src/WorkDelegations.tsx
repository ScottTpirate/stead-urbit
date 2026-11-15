import { useEffect, useState } from 'react';
import { AcceptedTime } from './AcceptedTime';
import { HomeError, SHIP, type CodeInput, type CodeReviewKey, type HomeClient, type Row, type WorkDelegation } from './api';
import { Button, TextField } from './primitives';
import { newId } from './protocol';
import { agentBrief } from './agentBrief';

type Delegate = Extract<CodeInput, {action: 'delegate' | 'revoke-delegation'}>;
const statusLabel = {active: 'Proposal access granted', expired: 'Expired', revoked: 'Revoked', unavailable: 'Access unavailable'};
const awaitConfirmation = (error: unknown) => error instanceof HomeError &&
  ['outcome_unknown', 'invalid_response', 'resume_required', 'session_changed', 'invalid_csrf'].includes(error.code);

export function WorkDelegations({client, project, work, manage, locked, onReview}: {
  client: HomeClient; project: string; work: Row; manage: boolean; locked: boolean;
  onReview: (key: CodeReviewKey) => void;
}) {
  const item = work.resource_id!;
  const [rows, setRows] = useState<WorkDelegation[] | null>();
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState(false);
  const [ship, setShip] = useState('');
  const [target, setTarget] = useState('main');
  const [minutes, setMinutes] = useState('30');
  const [pending, setPending] = useState<Delegate | null>(null);
  const [busy, setBusy] = useState(false);
  const [stopping, setStopping] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{text: string; error?: boolean} | null>(null);
  useEffect(() => {
    let current = true;
    let poll: ReturnType<typeof setTimeout> | undefined;
    function schedule() {
      poll = setTimeout(() => {
        if (document.visibilityState === 'visible') void refresh();
        else schedule();
      }, 12000);
    }
    async function refresh() {
      try {
        const value = await client.workDelegations(project, item);
        if (!current) return;
        setRows(value);
        if (pending) {
          const row = value.find(row => row.id === pending.delegation_id);
          const confirmed = pending.action === 'revoke-delegation' ? row?.status === 'revoked'
            : row?.worker === pending.worker_ship && row.ref === pending.ref && row.expires === pending.expires_at_ms;
          if (confirmed) {
            setPending(null); setStopping(null); setEditing(false);
            setFeedback({text: pending.action === 'delegate' ? 'Proposal access confirmed.' : 'Revocation confirmed.'});
          }
        }
      } catch { if (current) setRows(null); }
      if (current) schedule();
    }
    if (!busy) void refresh();
    return () => { current = false; clearTimeout(poll); };
  }, [client, project, item, attempt, busy, pending]);

  async function save(input: Delegate) {
    setBusy(true); setFeedback(null);
    try {
      await client.code(project, input);
      setPending(null); setStopping(null); setEditing(false);
      setFeedback({text: input.action === 'delegate' ? 'Proposal access granted.' : 'Proposal access revoked.'});
    } catch (error) {
      const uncertain = !!pending || awaitConfirmation(error);
      setPending(uncertain ? input : null);
      setFeedback({error: true, text: uncertain
        ? 'The result is unconfirmed. Refresh the list or retry this same request.'
        : 'Home rejected this request. Check the agent’s project access and the target branch.'});
    } finally {
      setBusy(false); setAttempt(value => value + 1);
    }
  }
  async function copyBrief(row: WorkDelegation) {
    try {
      await navigator.clipboard.writeText(agentBrief(project,work,row,location.origin));
      setFeedback({text: 'Agent brief copied. A worker has not been started.'});
    } catch (error) {
      setFeedback({text: error instanceof HomeError ? 'The current task contract could not be verified. Refresh the work item before copying a brief.'
        : 'Clipboard access is unavailable in this browser.', error: true});
    }
  }
  const worker = ('~' + ship.trim().replace(/^~/u, '')).toLowerCase();
  const branch = target.trim().replace(/^refs\/heads\//u, '');
  const valid = worker.length <= 64 && SHIP.test(worker)
    && /^(?:[A-Za-z0-9][A-Za-z0-9._-]*\/)*[A-Za-z0-9][A-Za-z0-9._-]*$/u.test(branch)
    && branch.length <= 117;
  const disabled = busy || locked || !!pending;
  return <section className="work-section" aria-label="Agent proposal access">
    <h3>Agent proposal access</h3>
    {rows === undefined ? <p role="status">Loading delegations…</p>
      : rows === null ? <p className="muted">Delegation is unavailable on this Home.</p>
      : rows.length === 0 ? <p className="muted">No agent has proposal access for this item.</p>
        : <ul className="work-agent-list">{rows.map(row => <li key={row.id}>
          <strong>{row.worker}</strong>
          <span>{statusLabel[row.status]} · {row.ref.replace(/^refs\/heads\//u, '')}</span>
          <span className="muted">Expires <AcceptedTime milliseconds={row.expires}/></span>
          <div className="actions">
            {row.status === 'active' && <Button variant="quiet" disabled={disabled} onClick={() => void copyBrief(row)}>Copy agent brief</Button>}
            {row.proposals.map(key => <Button key={key.proposal_id} variant="quiet" disabled={disabled}
              onClick={() => onReview(key)}>View proposal · revision {key.revision}</Button>)}
            {row.revocable && stopping !== row.id && <Button variant="quiet" disabled={disabled}
              onClick={() => setStopping(row.id)}>Revoke access…</Button>}
            {stopping === row.id && <>
              <Button variant="danger" disabled={disabled} onClick={() => void save({action: 'revoke-delegation', delegation_id: row.id})}>Confirm revoke</Button>
              <Button variant="quiet" disabled={disabled} onClick={() => setStopping(null)}>Keep access</Button>
            </>}
          </div>
        </li>)}</ul>}
    {rows && manage && (editing ? <form onSubmit={event => {
      event.preventDefault();
      if (!valid || disabled) return;
      void save({action: 'delegate', delegation_id: newId(), worker_ship: worker, work_id: item,
        ref: 'refs/heads/' + branch, expires_at_ms: String(Date.now() + Number(minutes) * 60000)});
    }}>
      <p>Allow a project member’s agent to propose a change for this item. Granting access does not start a worker.</p>
      <TextField label="Agent Urbit ID" value={ship} onChange={event => setShip(event.target.value)} required maxLength={64}
        disabled={disabled} spellCheck={false}/>
      <TextField label="Target branch" value={target} onChange={event => setTarget(event.target.value)} required maxLength={128}
        disabled={disabled} spellCheck={false}/>
      <label>Proposal access expires in<select value={minutes} disabled={disabled} onChange={event => setMinutes(event.target.value)}>
        <option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">1 hour</option>
      </select></label>
      <div className="actions">
        <Button type="submit" variant="primary" disabled={!valid || disabled}>Grant proposal access</Button>
        <Button variant="quiet" disabled={disabled} onClick={() => setEditing(false)}>Cancel</Button>
      </div>
    </form> : <Button variant="quiet" disabled={disabled} onClick={() => setEditing(true)}>Grant agent proposal access</Button>)}
    {feedback && <p role={feedback.error ? 'alert' : 'status'}>{feedback.text}</p>}
    <div className="actions">
      <Button variant="quiet" disabled={busy || locked} onClick={() => setAttempt(value => value + 1)}>Refresh agent access</Button>
      {pending &&
      <Button disabled={busy || locked} onClick={() => void save(pending)}>Retry same request</Button>
      }
    </div>
  </section>;
}

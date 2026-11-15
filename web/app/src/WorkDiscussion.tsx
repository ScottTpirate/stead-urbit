import { useEffect, useState } from 'react';
import { AcceptedTime } from './AcceptedTime';
import { HomeError, SHIP, UUID, type HomeClient } from './api';
import { Button } from './primitives';

type Comment = { revision: string; body: string; ship: string; principal: string; accepted: string };

async function discussion(client: HomeClient, project: string, work: string) {
  const comments = new Map<string, Comment>();
  let cursor = '';
  let generation: string | undefined;
  for (let page = 0; page < 2; page++) {
    const view = await client.query({kind: 'comments', project_id: project, resource_id: work, container_id: '', search: '', cursor});
    if (generation && generation !== view.generation) throw new HomeError('stale_cursor');
    generation = view.generation;
    for (const row of Object.values(view.rows)) {
      const {comment_revision: revision, body, identity_ship: ship, principal_id: principal, accepted_at_ms: accepted} = row;
      if (!revision || !/^[1-9][0-9]{0,19}$/u.test(revision) || comments.has(revision)
        || !body || !/[^\u0000-\u0020]/u.test(body) || /[\u0000-\u0008\u000B-\u001F]/u.test(body)
        || new TextEncoder().encode(body).length > 2048 || !ship || ship.length > 64 || !SHIP.test(ship)
        || !principal || !UUID.test(principal) || !accepted || !/^\d{1,16}$/u.test(accepted)) throw new HomeError('invalid_response');
      comments.set(revision, {revision, body, ship, principal, accepted});
    }
    if (comments.size > 32) throw new HomeError('invalid_response');
    cursor = view.cursor;
    if (!cursor) return [...comments.values()].sort((a, b) => BigInt(a.revision) < BigInt(b.revision) ? -1 : 1);
  }
  throw new HomeError('invalid_response');
}

export function WorkDiscussion({client, project, work, revision, principal, name, writable, locked, draft, onChange, onSubmit}: {
  client: HomeClient; project: string; work: string; revision: string; principal: string; name?: string;
  writable: boolean; locked: boolean; draft: string; onChange: (body: string) => void; onSubmit: (body: string) => void;
}) {
  const [result, setResult] = useState<{revision: string; rows: Comment[] | null} | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let current = true;
    const read = () => discussion(client, project, work);
    void read().catch(error => {
      if (current && error instanceof HomeError && error.code === 'stale_cursor') return read();
      throw error;
    }).then(rows => { if (current) setResult({revision, rows}); },
      () => { if (current) setResult({revision, rows: null}); });
    return () => { current = false; };
  }, [client, project, work, revision, attempt]);
  const current = result?.revision === revision ? result : null;
  const bytes = new TextEncoder().encode(draft).length;
  const full = current?.rows?.length === 32;
  return <section className="work-section" aria-label="Discussion">
    <h3>Discussion{current?.rows?.length ? ` · ${current.rows.length}` : ''}</h3>
    {!current ? <p role="status">Loading discussion…</p> : current.rows === null ? <div className="actions">
      <p role="status">Couldn’t load the discussion.</p>
      <Button variant="quiet" onClick={() => { setResult(null); setAttempt(value => value + 1); }}>Retry</Button>
    </div> : current.rows.length ? <ol className="work-discussion-list">{current.rows.map(row => <li key={row.revision}>
      <div><strong>{row.principal === principal && name ? name : row.ship}</strong><AcceptedTime milliseconds={row.accepted}/></div>
      <p>{row.body}</p>
    </li>)}</ol> : <p className="muted">No comments yet.</p>}
    {writable && <form onSubmit={event => {
      event.preventDefault();
      if (!locked && !full && draft.trim() && bytes <= 2048) onSubmit(draft);
    }}>
      <label>Comment<textarea value={draft} placeholder="Add context, ask a question, or share an update…"
        disabled={locked || full} maxLength={2048} onChange={event => onChange(event.target.value)}/></label>
      {bytes > 2048 && <p role="alert">This comment exceeds the 2,048-byte limit.</p>}
      {full && <p role="status">This discussion has reached its 32-comment limit.</p>}
      <Button type="submit" variant="primary" disabled={locked || full || !draft.trim() || bytes > 2048}>Post comment</Button>
    </form>}
  </section>;
}

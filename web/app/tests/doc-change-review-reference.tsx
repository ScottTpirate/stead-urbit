// Prepared synthetic browser fixture. Never connects to a Home or asserts authority.
import {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {DocChangeList, DocChangeReview} from '../src/docChangeReview';
import {Button} from '../src/primitives';
import type {DocDecisionOutcome, DocDecisionSubmitter, DocReviewBody, DocReviewDraft, DocReviewEnvironment, DocReviewSnapshot} from '../src/docChangeReviewState';
import {eligibility, fixture, hash, id, prepare} from './doc-change-review-fixture';
import '../src/style.css';
import './doc-change-review-reference.css';

const initial = await fixture();
const observation = {sent: [] as string[], acceptedCallbacks: 0, deniedCallbacks: 0, holding: false, opened: [] as string[]};
Object.assign(window, {docChangeReference: observation});
function Reference() {
  const [snapshot, setSnapshot] = useState(initial.snapshot), server = useRef(initial.snapshot);
  const [before, setBefore] = useState(initial.before), [after, setAfter] = useState(initial.after);
  const [access, setAccess] = useState<DocReviewEnvironment['access']>('writable'), [supported, setSupported] = useState(true);
  const [hasEligibility, setHasEligibility] = useState(true), [online, setOnline] = useState(true), [open, setOpen] = useState(true);
  const [sessionKey, setSessionKey] = useState(initial.snapshot.sessionKey), session = useRef(initial.snapshot.sessionKey);
  const [readToken, setReadToken] = useState({});
  const drafts = useRef(new Map<string, DocReviewDraft>()), mode = useRef('normal'), held = useRef<(() => void) | null>(null);
  const outcomes = useRef(new Map<string, DocDecisionOutcome>()), submitter = useRef<DocDecisionSubmitter | null>(null);
  if (!submitter.current) submitter.current = {currentSessionToken: () => session.current, prepare, submit: async prepared => {
    observation.sent.push(prepared.bytes); const known = outcomes.current.get(prepared.command.request_id); if (known) return known;
    const selected = mode.current; mode.current = 'normal';
    if (selected === 'denied') { const outcome = {status: 'rejected' as const, reason: 'denied_or_not_found' as const}; outcomes.current.set(prepared.command.request_id, outcome); return outcome; }
    if (selected === 'epoch') { server.current = {...server.current, authorityEpoch: '2', generation: 'd'.repeat(64)}; return {status: 'rejected', reason: 'authority_epoch_conflict'}; }
    if (selected === 'quarantine') { server.current = {...server.current, generation: 'e'.repeat(64), head: {...server.current.head, revision: '4', status: 'quarantined'}}; return {status: 'rejected', reason: 'producer_quarantined'}; }
    const next = String(BigInt(prepared.command.expected_revision) + 1n);
    server.current = {...server.current, head: {...server.current.head, revision: next, status: 'approved'}};
    const outcome: DocDecisionOutcome = {status: 'accepted', resultingRevision: next}; outcomes.current.set(prepared.command.request_id, outcome);
    if (selected === 'lost') throw new Error('Synthetic lost response');
    if (selected === 'held') { observation.holding = true; await new Promise<void>(resolve => { held.current = resolve; }); observation.holding = false; }
    return outcome;
  }};
  const draftKey = (value: DocReviewDraft) => value.scope.changeId + '/' + value.sessionKey;
  const refresh = () => { setSnapshot({...server.current}); setReadToken({}); };
  const replaceBodies = (next: DocReviewSnapshot, original: string, proposed: string) => {
    const body = (side: 'before' | 'after', markdown: string): DocReviewBody => ({scope: next.scope, sessionKey: next.sessionKey, resultRevision: next.output.revision,
      resultDigest: next.output.digest, side, state: 'ready', markdown, sha256: side === 'before' ? next.output.target.base_markdown_sha256 : next.output.markdownSha256});
    server.current = next; setSnapshot(next); setBefore(body('before', original)); setAfter(body('after', proposed)); setReadToken({});
  };
  const environment: DocReviewEnvironment = {scope: snapshot.scope, sessionKey, supported, access, online, authorizedReadToken: readToken, submitter: submitter.current,
    eligibility: hasEligibility ? eligibility(snapshot) : undefined, restoredDraft: drafts.current.get(snapshot.scope.changeId + '/' + sessionKey),
    onDraftState: draft => drafts.current.set(draftKey(draft), draft), onRefresh: refresh, onAccessChanged: () => { observation.deniedCallbacks++; },
    onAccepted: () => { observation.acceptedCallbacks++; refresh(); }};
  return <main className="doc-review-reference"><h1>Reserved Doc review interaction reference</h1><p>Explicitly synthetic data and decisions. This does not connect to a Home.</p>
    <section aria-label="Reference controls" className="doc-review-reference-controls">
      <Button onClick={() => { mode.current = 'lost'; }}>Lose next response</Button><Button onClick={() => { mode.current = 'held'; }}>Hold next response</Button>
      <Button onClick={() => { held.current?.(); held.current = null; }}>Release held response</Button>
      <Button onClick={() => { mode.current = 'epoch'; }}>Change access before response</Button><Button onClick={() => { mode.current = 'denied'; }}>Deny next decision</Button>
      <Button onClick={() => { mode.current = 'quarantine'; }}>Quarantine next decision</Button>
      <Button onClick={() => setBefore({...initial.before, state: 'unavailable', markdown: undefined, sha256: undefined})}>Before unavailable</Button>
      <Button onClick={() => setAfter({...initial.after, state: 'ready', markdown: 'Mismatched content', sha256: initial.snapshot.output.markdownSha256})}>Corrupt proposed content</Button>
      <Button onClick={() => setHasEligibility(false)}>Remove eligibility</Button><Button onClick={() => setHasEligibility(true)}>Restore eligibility</Button>
      <Button onClick={() => setAccess('revoked')}>Revoke access</Button><Button onClick={() => setAccess('writable')}>Restore access</Button>
      <Button onClick={() => setAccess('read-only')}>Read only</Button><Button onClick={() => setOnline(false)}>Offline</Button>
      <Button onClick={() => setSupported(false)}>Unsupported Home</Button><Button onClick={refresh}>Fresh authorized read</Button>
      <Button onClick={() => setOpen(false)}>Close fixture</Button><Button onClick={() => setOpen(true)}>Reopen fixture</Button>
      <Button onClick={() => { session.current = 'synthetic-session-two'; setSessionKey(session.current); }}>Change session</Button>
      <Button onClick={() => { const next = {...snapshot, scope: {...snapshot.scope, changeId: id(499)}, output: {...snapshot.output, targetLabel: 'Other proposed Doc'}}; setSnapshot(next); }}>Switch change</Button>
      <Button onClick={() => setSnapshot({...initial.snapshot})}>Return original change</Button>
      <Button onClick={() => setSnapshot({...snapshot, head: {...snapshot.head, resultRevision: '3', resultDigest: 'f'.repeat(64)}})}>View prior output</Button>
      <Button onClick={() => void (async () => { const original = 'Original line\n'.repeat(210), proposed = 'Proposed line\n'.repeat(210);
        const next = {...snapshot, output: {...snapshot.output, markdownSha256: await hash(proposed), target: {...snapshot.output.target, base_markdown_sha256: await hash(original)}}};
        replaceBodies(next, original, proposed); })()}>Large comparison</Button>
    </section>
    <DocChangeList projectId={snapshot.scope.projectId} workId={snapshot.scope.workId} sessionKey={sessionKey} locked={!online || access === 'revoked'}
      data={{projectId: snapshot.scope.projectId, workId: snapshot.scope.workId, sessionKey: snapshot.sessionKey, state: access === 'revoked' ? 'revoked' : 'ready', cursor: '', rows: [
        {projectId: snapshot.scope.projectId, workId: snapshot.scope.workId, changeId: snapshot.scope.changeId, summary: snapshot.output.summary,
          targetLabel: snapshot.output.targetLabel, status: snapshot.head.status, resultRevision: snapshot.output.revision, producerLabel: snapshot.output.producer.displayName}]}}
      onOpen={changeId => { observation.opened.push(changeId); setOpen(true); }} onMore={() => { throw new Error('Unexpected page'); }} onRefresh={refresh}/>
    {open && <DocChangeReview {...environment} snapshot={snapshot} before={before} after={after} onClose={() => setOpen(false)} onOpenWork={() => setOpen(false)}/>}
  </main>;
}
createRoot(document.getElementById('root')!).render(<Reference/>);

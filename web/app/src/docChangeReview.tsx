import {useEffect, useRef, useState} from 'react';
import {Button, EmptyState, LoadingState, OutcomeState, Surface} from './primitives';
import {Markdown} from './Markdown';
import {AcceptedTime} from './AcceptedTime';
import {encodeDocChangeCommand, type DocChangeDecisionOperation} from './docChangeProtocol';
import {adoptDocDecision, boundedDocDiff, chooseDocDecision, currentDocOutput, currentDocReview, docActionEligible, docDecisionActions,
  docDecisionCommand, docDecisionReason, docReviewHasDraft, docReviewPin, docReviewScopeKey, sameDocReviewPin,
  useDocReviewDraft, useVerifiedDocBody, type DocChangeStatus, type DocDecisionEvidence, type DocReviewBody,
  type DocReviewDraft, type DocReviewEnvironment, type DocReviewSnapshot, type VerifiedDocBody} from './docChangeReviewState';
import './docChangeReview.css';

const actionLabels: Record<DocChangeDecisionOperation, string> = {'change.request-changes': 'Request changes', 'change.approve': 'Approve output',
  'change.adopt': 'Adopt output', 'change.accept': 'Accept into Doc', 'change.reject': 'Reject output', 'change.quarantine': 'Quarantine output'};
const statusLabels: Record<DocChangeStatus, string> = {submitted: 'Submitted', 'changes-requested': 'Changes requested', approved: 'Approved', accepted: 'Accepted', rejected: 'Rejected', quarantined: 'Quarantined'};
const actorLabel = (value: {displayName: string}) => value.displayName || 'Project member';
export type DocChangePreview = {projectId: string; workId: string; changeId: string; summary: string; targetLabel: string;
  status: DocChangeStatus; resultRevision: string; producerLabel: string};
export function DocChangeList({projectId, workId, sessionKey, data, locked, onOpen, onMore, onRefresh}: {
  projectId: string; workId: string; sessionKey: string; locked: boolean;
  data: {projectId: string; workId: string; sessionKey: string; state: 'ready' | 'loading' | 'unavailable' | 'revoked' | 'unsupported'; rows: readonly DocChangePreview[]; cursor: string};
  onOpen: (changeId: string) => void; onMore: () => void; onRefresh: () => void;
}) {
  if (data.state === 'revoked') return <OutcomeState state="permission_revoked"/>;
  if (data.state === 'unsupported') return <OutcomeState state="unsupported_operation" description="Doc Changes are not available on this Home yet."/>;
  const scoped = data.projectId === projectId && data.workId === workId && data.sessionKey === sessionKey && data.rows.length <= 20
    && new Set(data.rows.map(row => row.changeId)).size === data.rows.length && data.rows.every(row => row.projectId === projectId && row.workId === workId
      && row.summary.length <= 2048 && row.targetLabel.length <= 512 && row.producerLabel.length <= 512);
  if (!scoped || data.state === 'loading') return <LoadingState label="Loading proposed Doc changes"/>;
  if (data.state === 'unavailable') return <OutcomeState state="retryable_error" description="The current Doc changes could not be loaded." action={<Button onClick={onRefresh}>Refresh changes</Button>}/>;
  return <section className="doc-change-list" aria-label="Proposed Doc changes"><h3>Proposed Doc changes</h3>
    {!data.rows.length ? <EmptyState title="No proposed Doc changes" description="Submitted Doc outputs will appear with their exact versions here."/>
      : <ul>{data.rows.map(row => <li key={row.changeId}><button type="button" disabled={locked} onClick={() => onOpen(row.changeId)}>
        <span><strong>{row.targetLabel || 'Shared Doc'}</strong><span>{row.summary}</span></span>
        <span className="doc-change-preview-meta">{statusLabels[row.status]} · Output {row.resultRevision}<small>{row.producerLabel || 'Project member'}</small></span>
      </button></li>)}</ul>}
    {!!data.cursor && <Button disabled={locked} onClick={onMore}>More changes</Button>}
  </section>;
}
export type DocChangeReviewProps = DocReviewEnvironment & {snapshot?: DocReviewSnapshot; before?: DocReviewBody; after?: DocReviewBody;
  onClose?: (draft: DocReviewDraft) => void; onOpenWork?: () => void};
export function DocChangeReview(props: DocChangeReviewProps) {
  if (!props.supported) return <OutcomeState state="unsupported_operation" description="This Home does not support Doc review yet."/>;
  if (props.access === 'revoked') return <OutcomeState state="permission_revoked"/>;
  if (!props.snapshot || !currentDocReview(props.snapshot, props.scope, props.sessionKey)) return <LoadingState label="Loading current Doc change"/>;
  return <ActiveReview {...props} snapshot={props.snapshot}/>;
}
function Evidence({value, label}: {value: DocDecisionEvidence; label: string}) {
  return <div className="doc-change-evidence"><strong>{label}</strong><p>{actorLabel(value.actor)} · <AcceptedTime milliseconds={value.recordedAtMs}/></p>
    {value.note && <p className="doc-change-note">{value.note}</p>}
    <details><summary>Decision details</summary><dl><div><dt>Request</dt><dd>{value.requestId}</dd></div><div><dt>Output digest</dt><dd>{value.resultDigest}</dd></div>
      <div><dt>Recorded time</dt><dd>{value.recordedAtMs}</dd></div></dl></details></div>;
}
function Body({body, source = false, side}: {body: VerifiedDocBody; source?: boolean; side: 'before' | 'after'}) {
  if (body.state === 'loading') return <LoadingState label={side === 'after' ? 'Loading exact proposed Doc' : 'Loading exact original Doc'}/>;
  if (body.state === 'unavailable') return <p role="status">{side === 'before' ? 'Original version unavailable. The latest Doc is not substituted for this exact base.' : 'The exact proposed Doc is unavailable. Refresh before making a decision.'}</p>;
  if (body.state === 'new-document') return <p>New Doc—no previous content.</p>;
  return source ? <pre className="doc-change-source" tabIndex={0} aria-label={side === 'after' ? 'Proposed Markdown source' : 'Original Markdown source'}>{body.markdown}</pre> : <Markdown text={body.markdown}/>;
}
function Diff({before, after}: {before: VerifiedDocBody; after: VerifiedDocBody}) {
  if (before.state === 'loading' || after.state === 'loading') return <LoadingState label="Loading exact comparison"/>;
  if (before.state === 'unavailable') return <p role="status">Original version unavailable. Read the proposed Doc in After or Source; no comparison is shown.</p>;
  if (after.state !== 'ready' || (before.state !== 'ready' && before.state !== 'new-document')) return <p role="status">The exact comparison is unavailable.</p>;
  const difference = boundedDocDiff(before.state === 'new-document' ? '' : before.markdown, after.markdown);
  if (difference.state === 'unavailable') return <p role="status">Line comparison is unavailable for this size. Read the exact Before and After versions or proposed Source.</p>;
  if (difference.lines.every(line => line.kind === 'same')) return <p>No text changes in this exact output.</p>;
  return <div className="doc-change-diff" role="region" aria-label="Exact Markdown changes" tabIndex={0}>
    {difference.lines.map((line, index) => <div className="doc-change-diff-line" data-kind={line.kind} key={index}>
      <span className="doc-change-line-number" aria-label={line.before ? `Original line ${line.before}` : undefined}>{line.before ?? ''}</span>
      <span className="doc-change-line-number" aria-label={line.after ? `Proposed line ${line.after}` : undefined}>{line.after ?? ''}</span>
      <span aria-label={line.kind === 'added' ? 'Added' : line.kind === 'removed' ? 'Removed' : 'Unchanged'}>{line.kind === 'added' ? '+' : line.kind === 'removed' ? '−' : ' '}</span><pre>{line.text}</pre>
    </div>)}
    {!difference.afterFinalNewline && <p className="muted">Proposed source has no final newline.</p>}
    {before.state === 'ready' && !difference.beforeFinalNewline && <p className="muted">Original source has no final newline.</p>}
  </div>;
}
function ActiveReview(props: DocChangeReviewProps & {snapshot: DocReviewSnapshot}) {
  const snapshot = props.snapshot, before = useVerifiedDocBody(props.before, snapshot, 'before'), after = useVerifiedDocBody(props.after, snapshot, 'after');
  const state = useDocReviewDraft(props, snapshot, after.state === 'ready'), {draft, change, locked, pending} = state;
  const [mode, setMode] = useState<'changes' | 'before' | 'after' | 'source'>('after'), heading = useRef<HTMLHeadingElement>(null);
  const key = docReviewScopeKey(props.scope, props.sessionKey);
  useEffect(() => { setMode('after'); const frame = requestAnimationFrame(() => heading.current?.focus()); return () => cancelAnimationFrame(frame); }, [key]);
  const current = currentDocOutput(snapshot), attempt = draft.attempt, selected = draft.selected, decision = selected && draft.decisions[selected];
  const changed = !!decision && !sameDocReviewPin(decision.base, docReviewPin(snapshot));
  const eligibilityMatches = !!props.eligibility && currentDocReview({...snapshot, scope: props.eligibility.scope, sessionKey: props.eligibility.sessionKey}, props.scope, props.sessionKey)
    && sameDocReviewPin(props.eligibility.pin, docReviewPin(snapshot));
  let validNote = false;
  if (selected && decision) try { encodeDocChangeCommand(docDecisionCommand(draft, selected, '019939ba-4000-7000-8000-000000000300')); validNote = true; } catch { /* A note must satisfy the same closed command grammar. */ }
  const relevant = (value: DocDecisionEvidence | undefined) => value && value.resultRevision === snapshot.output.revision && value.resultDigest === snapshot.output.digest;
  if (state.locallyRevoked) return <OutcomeState state="permission_revoked" action={<Button onClick={() => void props.onRefresh()}>Refresh access</Button>}/>;
  return <Surface className="doc-change-review" aria-labelledby="doc-change-heading">
    <header><div>{props.onOpenWork && <Button variant="quiet" disabled={pending || docReviewHasDraft(draft) || !props.online} onClick={props.onOpenWork}>Back to Work</Button>}
      <h2 ref={heading} id="doc-change-heading" tabIndex={-1}>{snapshot.output.targetLabel || 'Shared Doc'}</h2>
      <p>Output {snapshot.output.revision} · {actorLabel(snapshot.output.producer)} · <AcceptedTime milliseconds={snapshot.output.submittedAtMs}/></p>
      <p className="muted">Current Change: {statusLabels[snapshot.head.status]}</p></div>{props.onClose && <Button variant="quiet" onClick={() => props.onClose?.(draft)}>Close</Button>}</header>
    <p className="doc-change-note">{snapshot.output.summary}</p>
    {!current && <OutcomeState state="read_only" description="This is an older immutable output. Open the current output to make a decision."/>}
    {props.access === 'read-only' && <OutcomeState state="read_only"/>}
    {!props.online && <OutcomeState state="disconnected_or_stale" description="This copy may be out of date. Your notes are kept; reconnect before deciding."/>}
    <nav className="doc-change-modes" aria-label="Doc review view">{(['changes', 'before', 'after', 'source'] as const).map(value =>
      <Button key={value} variant={mode === value ? 'primary' : 'quiet'} aria-pressed={mode === value} onClick={() => setMode(value)}>{value[0]!.toUpperCase() + value.slice(1)}</Button>)}</nav>
    <div className="doc-change-content">{mode === 'changes' ? <Diff before={before} after={after}/>
      : mode === 'before' ? <Body body={before} side="before"/> : <Body body={after} side="after" source={mode === 'source'}/>}</div>
    <section aria-label="Review decisions" className="doc-change-decisions"><h3>Review this output</h3>
      {relevant(snapshot.feedback) && <Evidence value={snapshot.feedback!} label={actionLabels[snapshot.feedback!.operation]}/>}
      {relevant(snapshot.approval) && snapshot.approval?.requestId !== snapshot.feedback?.requestId && <Evidence value={snapshot.approval!} label="Recorded approval"/>}
      {relevant(snapshot.adoption) && snapshot.adoption?.requestId !== snapshot.feedback?.requestId && <Evidence value={snapshot.adoption!} label="Recorded adoption"/>}
      {snapshot.acceptance?.resultDigest === snapshot.output.digest && <p>Accepted into Doc revision {snapshot.acceptance.documentRevision} by {actorLabel(snapshot.acceptance.actor)}. Later Doc edits do not change this recorded outcome.</p>}
      {current && <><p>An independent person reviews the output. An accountable Owner or maintainer accepts it after Home checks the current requirements.</p>
        {!eligibilityMatches && <p role="status">Current decision availability has not been loaded. Refresh to check it.</p>}
        <div className="doc-change-actions">{docDecisionActions.map(operation => {
          const eligible = docActionEligible(props, snapshot, operation), supplied = eligibilityMatches ? props.eligibility!.actions[operation] : undefined;
          return <div key={operation}><Button disabled={locked || after.state !== 'ready' || !eligible} aria-pressed={selected === operation}
            onClick={() => change(value => chooseDocDecision(value, operation, snapshot))}>{actionLabels[operation]}</Button>
            {supplied && supplied.state !== 'eligible' && <small>{docDecisionReason(supplied.reason)}</small>}</div>;
        })}</div>
        {selected && decision && <div className="doc-change-decision-draft"><h4>{actionLabels[selected]}</h4>
          <label>Decision note<textarea value={decision.note} disabled={locked} onChange={event => change(value => ({...value,
            decisions: {...value.decisions, [selected]: {...value.decisions[selected]!, note: event.target.value}}}))}/></label>
          <p className="muted">{selected === 'change.approve' || selected === 'change.accept' ? 'A note is optional for this decision.' : 'Explain this decision so the next person knows what to do.'}</p>
          {(changed || decision.conflicted) && <div className="doc-change-compare"><p>Your note is kept with its original output. Read the current version above before changing its base.</p>
            <Button disabled={locked || !changed || after.state !== 'ready'} onClick={() => change(value => adoptDocDecision(value, selected, snapshot))}>Use current output for this decision</Button></div>}
          <Button variant={selected === 'change.reject' || selected === 'change.quarantine' ? 'danger' : 'primary'} disabled={locked || changed || decision.conflicted || !validNote
            || after.state !== 'ready' || !docActionEligible(props, snapshot, selected)} onClick={() => void state.send(selected)}>Confirm {actionLabels[selected].toLowerCase()}</Button>
        </div>}
      </>}
      {attempt && (attempt.phase === 'preparing' || attempt.phase === 'saving') && <OutcomeState state="saving"/>}
      {attempt?.phase === 'unknown' && <OutcomeState state="outcome_unknown" description={attempt.message} action={<Button disabled={!props.online || props.access !== 'writable'
        || props.submitter.currentSessionToken() !== attempt.token} onClick={() => void state.send(attempt.operation, true)}>Check same request</Button>}/>}
      {attempt?.phase === 'accepted' && <OutcomeState state="accepted" description={attempt.message || (attempt.awaitingReadback ? 'Home accepted this decision. Refreshing its saved state…' : 'Home accepted this decision.')}
        action={attempt.awaitingReadback ? <Button onClick={() => void props.onRefresh()}>Refresh saved decision</Button> : undefined}/>}
      {attempt && (attempt.phase === 'conflict' || attempt.phase === 'rejected') && <OutcomeState state={attempt.phase === 'conflict' ? 'conflict' : 'retryable_error'} description={attempt.message}
        action={<Button onClick={() => void props.onRefresh()}>Refresh current output</Button>}/>}
      {!pending && <Button variant="quiet" onClick={() => void props.onRefresh()}>Refresh review</Button>}
    </section>
    <details className="doc-change-details"><summary>Details</summary><dl>
      <div><dt>Change</dt><dd>{props.scope.changeId}</dd></div><div><dt>Current lifecycle revision</dt><dd>{snapshot.head.revision}</dd></div>
      <div><dt>Selected output</dt><dd>{snapshot.output.revision} · {snapshot.output.digest}</dd></div>
      <div><dt>Work execution contract</dt><dd>{snapshot.output.executionContractRevision} · {snapshot.output.executionContractDigest}</dd></div>
      <div><dt>Exact Doc base</dt><dd>{snapshot.output.target.expected_revision} · {snapshot.output.target.base_markdown_sha256 || 'New document'}</dd></div>
      <div><dt>Proposed Markdown hash</dt><dd>{snapshot.output.markdownSha256}</dd></div>
      {snapshot.output.runId && <div><dt>Original run and attempt</dt><dd>{snapshot.output.runId} · {snapshot.output.attempt}</dd></div>}
      {attempt?.prepared && <div><dt>Decision request</dt><dd>{attempt.prepared.command.request_id}</dd></div>}
      {draft.previousAttempt?.prepared && <div><dt>Previous request</dt><dd>{draft.previousAttempt.prepared.command.request_id}</dd></div>}
    </dl></details>
  </Surface>;
}

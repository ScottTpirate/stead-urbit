import {useEffect, useId, useRef, useState, type RefObject} from 'react';
import {Button, EmptyState, LoadingState, OutcomeState, StatusBadge, Surface} from './primitives';
import {newId} from './protocol';
import {encodeProductRoute} from './productRoutes';
import {RunReadClient, RunReadClientError, runDetails, runResult, type RunDetail, type RunPhase, type RunPreview, type RunQueryError, type RunSessionToken} from './runReadProtocol';
import './run-history.css';

export type RunHistoryScope = {projectId: string; workId: string; runId?: string};
export interface RunHistoryProps {
  readonly client: RunReadClient | null;
  readonly projectId: string;
  readonly workId: string;
  readonly sessionKey: string;
  readonly selectedRunId?: string;
  readonly onSelectRun: (id?: string) => void;
  readonly online: boolean;
  readonly access: 'loading' | 'readable' | 'revoked';
  readonly locked?: boolean;
  readonly viewRevision?: string | number;
  readonly onAccessChanged: (scope: RunHistoryScope) => void | Promise<void>;
  readonly onError?: (failure: unknown) => void;
  readonly onOpenChange: (project: string, work: string, change: string, revision: string, digest: string) => void;
}
export type RunHistoryPhase = 'loading' | 'loading-more' | 'ready' | 'offline' | 'error' | 'expired' | 'revoked' | 'unsupported';
export type RunHistorySnapshot = Readonly<{phase: RunHistoryPhase; rows: readonly RunPreview[]; cursor: string; detail?: RunDetail; authorityEpoch?: string; generation?: string}>;
const empty = (phase: RunHistoryPhase): RunHistorySnapshot => Object.freeze({phase, rows: [], cursor: ''});
class RunHistoryFailure extends Error { constructor(readonly code: RunQueryError) { super(code); } }

// One component-local request owner. A route may return to the same ID, so
// matching scope strings alone never permits an earlier response to publish.
export class RunHistoryController {
  private props?: RunHistoryProps;
  private identity: unknown[] = [];
  private serial = 0;
  private currentRequest = 0;
  private token: RunSessionToken | null = null;
  private binding?: {client: RunReadClient | null; sessionKey: string; token: RunSessionToken | null};
  private state: RunHistorySnapshot = empty('loading');
  private listener?: () => void;
  configure(props: RunHistoryProps) {
    const token = props.client?.currentSessionToken() ?? null;
    const supported = props.client?.supportsReads() ?? false;
    if (!this.binding || this.binding.client !== props.client || this.binding.sessionKey !== props.sessionKey) this.binding = {client: props.client, sessionKey: props.sessionKey, token};
    const identity = [props.client, props.projectId, props.workId, props.sessionKey, props.selectedRunId, props.viewRevision, props.access, token, supported];
    const changed = identity.length !== this.identity.length || identity.some((value, index) => value !== this.identity[index]);
    const onlineChanged = this.props !== undefined && this.props.online !== props.online;
    this.props = props; this.token = token;
    if (changed) {
      this.identity = identity; this.serial++; this.currentRequest = 0;
      this.state = empty(props.access === 'revoked' ? 'revoked' : !supported ? 'unsupported'
        : props.access === 'loading' ? 'loading' : !token || !props.sessionKey || token !== this.binding.token ? 'revoked' : props.online ? 'loading' : 'offline');
    } else if (onlineChanged) {
      this.serial++; this.currentRequest = 0;
      if (this.state.phase !== 'revoked' && this.state.phase !== 'unsupported') this.state = Object.freeze({...this.state, phase: 'offline', cursor: ''});
    }
    return this.serial;
  }
  subscribe(listener: () => void) { this.listener = listener; return () => { this.listener = undefined; this.serial++; this.currentRequest = 0; }; }
  snapshot() { return this.state; }
  private publish(state: RunHistorySnapshot) { this.state = Object.freeze(state); this.listener?.(); }
  private authorized() {
    const props = this.props;
    return !!props?.client && props.client.supportsReads() && props.access === 'readable' && !!props.sessionKey && !!this.token
      && props.client.currentSessionToken() === this.token && this.binding?.token === this.token;
  }
  private active(serial: number) {
    if (serial !== this.serial) return false;
    if (!this.authorized()) { this.publish(empty(this.props?.client?.supportsReads() ? 'revoked' : 'unsupported')); return false; }
    return !!this.props?.online;
  }
  canNavigate() { return this.authorized() && !!this.props?.online && !this.props.locked && this.state.phase === 'ready'; }
  select(id?: string) { if (this.canNavigate()) this.props!.onSelectRun(id); }
  openChange() {
    if (!this.canNavigate() || !this.state.detail) return;
    const row = this.state.detail, result = runResult(row); if (!result) return;
    this.props!.onOpenChange(row.project_id, row.work_id, result.change_id, result.result_revision, result.result_digest);
  }
  async load(more = false) {
    const props = this.props;
    if (props?.client && !props.client.supportsReads()) { this.publish(empty('unsupported')); return; }
    if (!props?.client || !this.authorized() || !props.online || props.locked || this.currentRequest) return;
    if (more && (props.selectedRunId || this.state.phase !== 'ready' || !this.state.cursor)) return;
    const previous = this.state, cursor = more ? previous.cursor : '', serial = ++this.serial;
    this.currentRequest = serial;
    this.publish(more ? {...previous, phase: 'loading-more', cursor: ''} : empty('loading'));
    try {
      const scope = {request_id: newId(), project_id: props.projectId, work_id: props.workId};
      const view = props.selectedRunId ? await props.client.readRun({...scope, run_id: props.selectedRunId}) : await props.client.readRuns({...scope, cursor});
      if (!this.active(serial)) return;
      if (view.status === 'rejected') throw new RunHistoryFailure(view.error);
      if (view.kind === 'run') this.publish({phase: 'ready', rows: [], cursor: '', detail: view.rows[0]!, authorityEpoch: view.authority_epoch, generation: view.generation});
      else {
        if (more && (view.generation !== previous.generation || view.authority_epoch !== previous.authorityEpoch)) throw new RunReadClientError('stale_cursor');
        const rows = more ? [...previous.rows, ...view.rows] : view.rows;
        if (rows.length > 32 || new Set(rows.map(row => row.run_id)).size !== rows.length) throw new RunReadClientError('stale_cursor');
        this.publish({phase: 'ready', rows: Object.freeze(rows), cursor: view.cursor, authorityEpoch: view.authority_epoch, generation: view.generation});
      }
    } catch (failure) {
      if (!this.active(serial)) return;
      const code = failure instanceof RunReadClientError || failure instanceof RunHistoryFailure ? failure.code : '';
      const phase = ['denied_or_not_found','session_required','session_changed'].includes(code) ? 'revoked'
        : ['unsupported_operation','migration_required'].includes(code) ? 'unsupported' : code === 'stale_cursor' ? 'expired' : 'error';
      this.publish(empty(phase));
      if (phase === 'revoked') {
        try { await this.props!.onAccessChanged({projectId: props.projectId, workId: props.workId, ...(props.selectedRunId ? {runId: props.selectedRunId} : {})}); } catch { /* Parent owns its own recovery. */ }
      }
      if (this.active(serial)) this.props!.onError?.(failure);
    } finally { if (serial === this.serial) this.currentRequest = 0; }
  }
}

const phaseLabels: Record<RunPhase, string> = {queued: 'Queued', running: 'Running', waiting: 'Waiting for input', submitted: 'Submitted', failed: 'Failed', canceled: 'Canceled'};
function time(value: string) {
  const number = Number(value); if (!Number.isSafeInteger(number)) return 'Recorded time unavailable';
  const date = new Date(number); return Number.isFinite(date.getTime()) ? date.toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'}) : 'Recorded time unavailable';
}
export function runLeaseLabel(row: RunPreview, now: number, stale: boolean) {
  if (row.lease_state === 'none') return 'No execution lease';
  if (row.lease_state === 'terminal') return 'No active execution lease';
  if (stale) return 'Lease needs a fresh check';
  if (row.lease_state === 'expired') return 'Lease expired';
  if (row.lease_state === 'unknown-book') return 'Lease status unavailable';
  return Number.isFinite(now) && BigInt(Math.floor(now)) >= BigInt(row.lease_until_ms) ? 'Lease check is out of date' : 'Lease observed live';
}
const person = (name: string) => name.trim() ? name : 'Name unavailable';
function People({row}: {row: RunPreview}) { return <dl className="run-history-people">
  <div><dt>Owner</dt><dd>{person(row.owner_display_name)}</dd></div><div><dt>Working on it</dt><dd>{person(row.worker_display_name)}</dd></div></dl>; }
function Pins({row}: {row: RunPreview}) { const result = runResult(row); return <details className="run-history-details"><summary>Details</summary><dl>
  <div><dt>Run ID</dt><dd>{row.run_id}</dd></div><div><dt>Project ID</dt><dd>{row.project_id}</dd></div><div><dt>Work ID</dt><dd>{row.work_id}</dd></div>
  <div><dt>Run revision</dt><dd>{row.run_revision}</dd></div><div><dt>Requester ID</dt><dd>{row.requester_principal_id}</dd></div>
  <div><dt>Owner ID</dt><dd>{row.owner_principal_id}</dd></div><div><dt>Worker ID</dt><dd>{row.worker_principal_id}</dd></div>
  <div><dt>Issued time</dt><dd>{row.issued_at_ms}</dd></div><div><dt>Deadline</dt><dd>{row.deadline_ms}</dd></div><div><dt>Lease until</dt><dd>{row.lease_until_ms}</dd></div>
  {result && <><div><dt>Change ID</dt><dd>{result.change_id}</dd></div><div><dt>Output revision</dt><dd>{result.result_revision}</dd></div>
    <div><dt>Output digest</dt><dd>{result.result_digest}</dd></div><div><dt>Outcome ID</dt><dd>{result.outcome_id}</dd></div></>}
  {'execution_contract_revision' in row && <><div><dt>Execution contract revision</dt><dd>{String(row.execution_contract_revision)}</dd></div>
    <div><dt>Execution contract digest</dt><dd>{String((row as RunDetail).execution_contract_digest)}</dd></div>
    <div><dt>Agent version pins</dt><dd>{(row as RunDetail).agent_version}</dd></div></>}
  </dl></details>; }

export function RunHistoryContent({snapshot, selected, online, locked, now, onRefresh, onMore, onSelect, onOpenChange, headingRef}: {
  snapshot: RunHistorySnapshot; selected?: string; online: boolean; locked: boolean; now: number;
  onRefresh: () => void; onMore: () => void; onSelect: (id?: string) => void; onOpenChange: () => void;
  headingRef?: RefObject<HTMLHeadingElement | null>;
}) {
  const heading = useId(), state = snapshot.phase, stale = state === 'offline' || !online;
  const canOpen = !locked && online && state === 'ready', canRefresh = !locked && online && !['loading','loading-more','revoked','unsupported'].includes(state);
  const refresh = <Button variant="quiet" disabled={!canRefresh} onClick={onRefresh}>Refresh runs</Button>;
  const visible = ['ready','loading-more','offline'].includes(state), rows = visible ? snapshot.rows : [];
  const detail = visible ? snapshot.detail : undefined, nested = detail ? runDetails(detail) : undefined, result = detail ? runResult(detail) : undefined;
  return <Surface className="run-history" aria-labelledby={heading}>
    <div className="run-history-heading"><div><h3 id={heading} ref={headingRef} tabIndex={-1}>{selected ? 'Run details' : 'Run history'}</h3><p>Recorded execution for this work item.</p></div>
      <div className="run-history-actions">{selected && <Button variant="quiet" disabled={!canOpen} onClick={() => onSelect()}>Back to runs</Button>}{refresh}</div></div>
    {state === 'unsupported' && <OutcomeState state="unsupported_operation" description="Run history is unavailable on this Home."/>}
    {state === 'revoked' && <OutcomeState state="permission_revoked"/>}
    {state === 'loading' && (locked ? <p role="status">Finish your current action to load run history.</p> : <LoadingState label="Loading authorized runs"/>)}
    {stale && !['revoked','unsupported'].includes(state) && <OutcomeState state="disconnected_or_stale" description={online
      ? 'Refresh to check current access and run status.' : 'Offline. Any retained run details are from the last read. Reconnect and refresh to continue.'}/>}
    {state === 'error' && <OutcomeState state="retryable_error" description="Could not verify run history. Refresh to try again."/>}
    {state === 'expired' && <OutcomeState state="disconnected_or_stale" description="This page is no longer current. Refresh to start from the first page."/>}
    {state === 'ready' && !selected && snapshot.rows.length === 0 && <EmptyState title="No runs yet" description="There are no runs you can currently read for this work item."/>}
    {rows.length > 0 && <ul className="run-history-list">{rows.map(row => <li key={row.run_id}>
      <div className="run-history-row-heading"><Button variant="quiet" data-run-id={row.run_id} disabled={!canOpen} onClick={() => onSelect(row.run_id)}>Run requested {time(row.issued_at_ms)}</Button>
        <StatusBadge label={phaseLabels[row.phase]} tone={row.phase === 'failed' ? 'danger' : row.phase === 'waiting' ? 'warning' : 'neutral'}/></div>
      <People row={row}/><p className="run-history-observation">{runLeaseLabel(row, now, stale)}</p><Pins row={row}/>
    </li>)}</ul>}
    {detail && nested && <article className="run-history-current" aria-label="Selected run">
      <div className="run-history-row-heading"><h4>Run requested {time(detail.issued_at_ms)}</h4><StatusBadge label={phaseLabels[detail.phase]} tone={detail.phase === 'failed' ? 'danger' : detail.phase === 'waiting' ? 'warning' : 'neutral'}/></div>
      <People row={detail}/><p>Requested by {person(detail.requester_display_name)}</p>
      <dl className="run-history-observations"><div><dt>Execution lease</dt><dd>{runLeaseLabel(detail, now, stale)}</dd></div>
        <div><dt>Work inputs at last read</dt><dd>{detail.execution_current === 'yes' ? 'Matched the current Work' : 'Changed or no longer available for execution'}</dd></div></dl>
      <p className="run-history-note">Status is from the last read. Refresh to check for changes.</p>
      {nested.attempt && <section aria-label="Current attempt"><h4>Attempt {nested.attempt.attempt}</h4><dl className="run-history-observations">
        <div><dt>Started</dt><dd>{time(nested.attempt.started_at_ms)}</dd></div><div><dt>Last heartbeat</dt><dd>{time(nested.attempt.heartbeat_at_ms)}</dd></div>
        <div><dt>Lease until</dt><dd>{time(nested.attempt.lease_until_ms)}</dd></div></dl></section>}
      {nested.question && <section className="run-history-conversation" aria-label="Latest clarification"><h4>Latest clarification</h4>
        <p className="run-history-byline">{person(nested.question.display_name)} · {time(nested.question.recorded_at_ms)}</p><p>{nested.question.text}</p>
        {nested.answer ? <div><h5>Answer</h5><p className="run-history-byline">{person(nested.answer.display_name)} · {time(nested.answer.recorded_at_ms)}</p><p>{nested.answer.text}</p></div>
          : <p className="run-history-note">No answer was recorded at the last read.</p>}</section>}
      {result && <section aria-label="Submitted output"><h4>Submitted Doc output</h4><p>Submission does not mean this output has been accepted or the Work is Done.</p>
        <Button variant="quiet" disabled={!canOpen} data-resource-route={encodeProductRoute({kind:'doc-change',project:detail.project_id,work:detail.work_id,change:result.change_id,result:{revision:result.result_revision,digest:result.result_digest}})} onClick={onOpenChange}>Open submitted Doc change</Button></section>}
      <Pins row={detail}/>
    </article>}
    {state === 'loading-more' && <LoadingState label="Loading more runs" lines={1}/>}
    {visible && snapshot.cursor && <Button disabled={!canOpen} onClick={onMore}>Load more runs</Button>}
  </Surface>;
}

export function RunHistory(props: RunHistoryProps) {
  const model = useRef<RunHistoryController | null>(null); if (!model.current) model.current = new RunHistoryController();
  const controller = model.current, [, redraw] = useState(0), [now, setNow] = useState(Date.now);
  const heading = useRef<HTMLHeadingElement>(null), container = useRef<HTMLDivElement>(null);
  const focus = useRef({key: '', scope: '', prior: undefined as string | undefined, target: '', done: false});
  const focusScope = JSON.stringify([props.sessionKey, props.projectId, props.workId]);
  const focusKey = JSON.stringify([props.sessionKey, props.projectId, props.workId, props.selectedRunId]);
  if (focus.current.key !== focusKey) focus.current = {key: focusKey, scope: focusScope, prior: props.selectedRunId,
    target: props.selectedRunId ? 'heading' : focus.current.scope === focusScope ? focus.current.prior ?? '' : '', done: false};
  const revision = controller.configure(props), snapshot = controller.snapshot();
  useEffect(() => controller.subscribe(() => redraw(value => value + 1)), [controller]);
  useEffect(() => { if (controller.snapshot().phase === 'loading') void controller.load(); }, [controller, revision, props.locked]);
  useEffect(() => {
    if (focus.current.done || !focus.current.target || snapshot.phase !== 'ready' || !controller.canNavigate()) return;
    const frame = requestAnimationFrame(() => {
      if (focus.current.key !== focusKey || focus.current.done || !controller.canNavigate()) return;
      const target = focus.current.target === 'heading' ? heading.current
        : [...(container.current?.querySelectorAll<HTMLButtonElement>('button[data-run-id]') ?? [])].find(button => button.dataset.runId === focus.current.target);
      target?.focus({preventScroll: true}); focus.current.done = true;
    }); return () => cancelAnimationFrame(frame);
  }, [controller, focusKey, snapshot, props.locked]);
  useEffect(() => {
    const live = [...snapshot.rows, ...(snapshot.detail ? [snapshot.detail] : [])].filter(row => row.lease_state === 'live').map(row => Number(row.lease_until_ms)).filter(value => Number.isSafeInteger(value) && value > Date.now());
    if (!live.length) return; const delay = Math.max(1, Math.min(2147483647, Math.min(...live) - Date.now() + 1));
    const timer = setTimeout(() => setNow(Date.now()), delay); return () => clearTimeout(timer);
  }, [snapshot]);
  return <div ref={container}><RunHistoryContent snapshot={snapshot} selected={props.selectedRunId} online={props.online} locked={!!props.locked} now={Math.max(now, Date.now())} headingRef={heading}
    onRefresh={() => void controller.load()} onMore={() => void controller.load(true)} onSelect={id => controller.select(id)} onOpenChange={() => controller.openChange()}/></div>;
}

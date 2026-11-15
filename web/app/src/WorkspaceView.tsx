import {useEffect, useRef, useState, type RefObject} from 'react';
import {HomeError, UUID, type HomeClient, type HomeWatch, type Query, type Row, type View} from './api';
import {Button, EmptyState, LoadingState, OutcomeState, StatusBadge, TextField} from './primitives';
import {encodeProductRoute} from './productRoutes';
import {workStateLabel} from './productModel';
import './workspace.css';

export type WorkspaceQueryView = 'my-work' | 'workspace-search';
export type WorkspaceSearch = {draft: string; term: string};
type Snapshot = {rows: Row[]; cursor: string; generation: string; page: number};
type Phase = 'loading' | 'ready' | 'refreshing' | 'offline' | 'error' | 'expired' | 'revoked' | 'unsupported';
type State = {key: string; phase: Phase; snapshot?: Snapshot};
export interface WorkspaceViewProps {
  readonly client: HomeClient;
  readonly view: WorkspaceQueryView;
  readonly search: WorkspaceSearch;
  readonly onSearchChange: (search: WorkspaceSearch) => void;
  readonly sessionKey: string;
  readonly locked: boolean;
  readonly openingWatchRef: RefObject<Promise<void> | null>;
  readonly onOpen: (row: Row) => void;
  readonly onError: (failure: unknown) => void;
  readonly restoreNavigation?: {scroll: number; selection?: string};
}

function resourceRoute(row: Row): string {
  return encodeProductRoute(row.kind === 'work'
    ? {kind: 'work', project: row.project_id!, item: row.resource_id!}
    : {kind: 'doc', project: row.project_id!, collection: row.container_id!, document: row.resource_id!});
}

// A page is published whole or rejected whole. This is shape checking after
// Home authorization, never a client-side replacement for its query/filter.
function workspaceRows(result: View, view: WorkspaceQueryView): Row[] {
  const rows = Object.values(result.rows);
  if (rows.length > 20) throw new HomeError('invalid_response');
  const seen = new Set<string>();
  for (const row of rows) {
    if (!UUID.test(row.project_id ?? '') || !UUID.test(row.resource_id ?? '')
        || !['work', 'document'].includes(row.kind ?? '')
        || (view === 'my-work' && row.kind !== 'work')
        || (row.kind === 'document' ? !UUID.test(row.container_id ?? '') : !!row.container_id)) {
      throw new HomeError('invalid_response');
    }
    const key = resourceRoute(row);
    if (seen.has(key)) throw new HomeError('invalid_response');
    seen.add(key);
  }
  return rows;
}

export function WorkspaceView({client, view, search, onSearchChange, sessionKey, locked, openingWatchRef,
  onOpen, onError, restoreNavigation}: WorkspaceViewProps) {
  const term = view === 'workspace-search' ? search.term : '';
  const key = JSON.stringify([sessionKey, view, term]);
  const searchReady = view !== 'workspace-search' || !!term.trim();
  const validTerm = new TextEncoder().encode(term).length <= 128;
  const [state, setState] = useState<State>({key, phase: 'loading'});
  const [attempt, setAttempt] = useState(0);
  const [searchError, setSearchError] = useState('');
  const [online, setOnline] = useState(() => navigator.onLine);
  const current = useRef({locked, onError, onOpen});
  current.current = {locked, onError, onOpen};
  const actions = useRef<{next: () => void} | null>(null);
  const restored = useRef('');
  const results = useRef<HTMLDivElement>(null);
  // Scope identity is checked during render, before cleanup/effects can run.
  const visible = state.key === key ? state : {key, phase: 'loading' as const};
  const snapshot = searchReady && validTerm ? visible.snapshot : undefined;

  useEffect(() => {
    let active = true;
    let watch: HomeWatch | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let reading = false;
    let serial = 0;
    let shown: Snapshot | undefined;
    let deferred: Snapshot | undefined;
    let pendingRefresh = false;
    let stopped = false;
    const scope = {kind: view, project_id: '', container_id: '', resource_id: '', search: term};
    function change(phase: Phase, keep = true) {
      if (active) setState({key, phase, ...(keep && shown ? {snapshot: shown} : {})});
    }
    function clear(phase: Phase) {
      serial++; shown = undefined; deferred = undefined; pendingRefresh = false;
      change(phase, false);
    }
    function schedule(operation: () => Promise<void>, delay = 2000) {
      if (!active || stopped) return;
      clearTimeout(timer); timer = setTimeout(operation, delay);
    }
    function failed(failure: unknown) {
      if (!active) return;
      stopped = true; clearTimeout(timer);
      const code = failure instanceof HomeError ? failure.code : '';
      if (['denied_or_not_found', 'session_required', 'session_changed'].includes(code)) clear('revoked');
      else if (code === 'stale_cursor') clear('expired');
      else if (['unsupported_operation', 'unsupported_query', 'invalid_request'].includes(code)) clear('unsupported');
      else if (code === 'invalid_response') clear('error');
      else change('offline');
      current.current.onError(failure);
    }
    function publish(next: Snapshot) {
      shown = next; deferred = undefined; change('ready');
    }
    async function read(cursor = '', page = 1) {
      if (!active || stopped || reading || current.current.locked) return;
      reading = true; const request = ++serial;
      change(shown ? 'refreshing' : 'loading');
      try {
        const query: Query = {...scope, cursor};
        const result = await client.query(query);
        if (!active || stopped || request !== serial) return;
        const next = {rows: workspaceRows(result, view), cursor: result.cursor, generation: result.generation, page};
        if (!navigator.onLine) { deferred = next; stopped = true; change('offline'); return; }
        // Keep an already-consumed pagination result while foreground navigation
        // is pending. Do not replay its cursor or publish into a different scope.
        if (current.current.locked) deferred = next;
        else publish(next);
      } catch (failure) { failed(failure); }
      finally { reading = false; }
    }
    async function poll() {
      if (!active || stopped || !watch) return;
      if (current.current.locked || reading) { schedule(poll, 200); return; }
      try {
        if (deferred) publish(deferred);
        if (pendingRefresh) { pendingRefresh = false; await read(); }
        if (!active || stopped || !watch) return;
        if (current.current.locked) { schedule(poll, 200); return; }
        const update = await watch.poll();
        if (!active || stopped) return;
        if (update.status === 'refresh_required') {
          watch = null; clear('loading'); schedule(connect, 0); return;
        }
        pendingRefresh = Object.keys(update.rows).length > 0 && update.generation !== shown?.generation;
        schedule(poll, pendingRefresh ? 0 : 2000);
      } catch (failure) { failed(failure); }
    }
    async function connect() {
      if (!active || stopped) return;
      if (!navigator.onLine) { stopped = true; change('offline'); return; }
      if (current.current.locked) { schedule(connect, 200); return; }
      try {
        while (openingWatchRef.current) {
          await openingWatchRef.current;
          if (!active || stopped) return;
        }
        if (current.current.locked) { schedule(connect, 200); return; }
        let release!: () => void;
        const opening = new Promise<void>(resolve => { release = resolve; });
        openingWatchRef.current = opening;
        try {
          const opened = await client.watch(scope);
          if (!active || stopped) { if (opened) await client.retire(opened); return; }
          watch = opened;
          if (!watch) { clear('loading'); schedule(connect); return; }
        } finally {
          if (openingWatchRef.current === opening) openingWatchRef.current = null;
          release();
        }
        await read();
        if (!shown && !deferred) pendingRefresh = true;
        schedule(poll, deferred || pendingRefresh ? 200 : 2000);
      } catch (failure) { failed(failure); }
    }
    const ownedActions = {next: () => {
      if (!shown?.cursor || stopped || reading || current.current.locked) return;
      void read(shown.cursor, shown.page + 1).then(() => schedule(poll));
    }};
    actions.current = ownedActions;
    const offline = () => {
      setOnline(false); stopped = true; clearTimeout(timer); change('offline');
    };
    const connected = () => setOnline(true); // Explicit refresh revalidates access.
    window.addEventListener('offline', offline); window.addEventListener('online', connected);
    setState({key, phase: 'loading'});
    if (searchReady && validTerm && sessionKey) void connect();
    return () => {
      active = false; serial++; clearTimeout(timer);
      window.removeEventListener('offline', offline); window.removeEventListener('online', connected);
      if (actions.current === ownedActions) actions.current = null;
      if (watch) void client.retire(watch).catch(() => {});
    };
  }, [client, view, term, sessionKey, key, searchReady, validTerm, attempt, openingWatchRef]);

  useEffect(() => {
    if (!snapshot || !restoreNavigation || restored.current === key || visible.phase !== 'ready') return;
    const frame = requestAnimationFrame(() => {
      restored.current = key;
      if (restoreNavigation.selection) {
        const button = [...(results.current?.querySelectorAll<HTMLButtonElement>('button[data-resource-route]') ?? [])]
          .find(item => item.dataset.resourceRoute === restoreNavigation.selection);
        button?.focus({preventScroll: true});
      }
      if (Number.isFinite(restoreNavigation.scroll) && restoreNavigation.scroll >= 0) window.scrollTo({top: restoreNavigation.scroll});
    });
    return () => cancelAnimationFrame(frame);
  }, [snapshot, restoreNavigation, key, visible.phase]);

  const refresh = <Button disabled={locked || !online} onClick={() => setAttempt(value => value + 1)}>Refresh results</Button>;
  const canOpen = !locked && online && visible.phase === 'ready';
  return <section className="workspace-view" aria-labelledby="workspace-view-title">
    <p className="workspace-breadcrumb">Home <span aria-hidden="true">/</span> {view === 'my-work' ? 'My work' : 'Search'}</p>
    <div className="workspace-heading"><div><h1 id="workspace-view-title">{view === 'my-work' ? 'My work' : 'Search'}</h1>
      <p>{view === 'my-work' ? 'Unfinished work assigned to you' : 'Find work and documents on this Home'}</p></div>
      {searchReady && validTerm && visible.phase === 'ready' && refresh}</div>
    {view === 'workspace-search' && <form className="workspace-search" onSubmit={event => {
      event.preventDefault();
      if (locked) return;
      if (new TextEncoder().encode(search.draft).length > 128) { setSearchError('This search is too long. Use fewer or shorter words.'); return; }
      setSearchError(''); onSearchChange({...search, term: search.draft});
      if (search.draft === search.term && search.draft.trim()) setAttempt(value => value + 1);
    }}><TextField label="Search this Home" value={search.draft} disabled={locked} error={searchError || undefined}
        onChange={event => { setSearchError(''); onSearchChange({...search, draft: event.target.value}); }}/>
      <Button type="submit" disabled={locked || !online}>Search</Button></form>}
    {!searchReady ? <EmptyState title="Search this Home" description="Enter a title or words from the work or document you need."/>
      : !validTerm ? <OutcomeState state="retryable_error" description="This search is too long. Use fewer or shorter words."/>
      : <>
        {(visible.phase === 'loading' || visible.phase === 'refreshing') && <LoadingState label={snapshot ? 'Updating results from Home' : 'Loading authorized results'}/>}
        {visible.phase === 'offline' && <OutcomeState state="disconnected_or_stale" description={online
          ? 'The connection is available. Refresh to check your access and current results.' : 'These results may be out of date. Reconnect and refresh before opening them.'} action={refresh}/>}
        {visible.phase === 'revoked' && <OutcomeState state="permission_revoked"/>}
        {visible.phase === 'unsupported' && <OutcomeState state="unsupported_operation" description="This Home does not currently support this workspace view."/>}
        {visible.phase === 'error' && <OutcomeState state="retryable_error" description="Home returned results that could not be verified. Refresh to try again." action={refresh}/>}
        {visible.phase === 'expired' && <OutcomeState state="retryable_error" description="These results changed. Refresh to start from the first page." action={refresh}/>}
        {snapshot && <div ref={results} className="workspace-results" aria-busy={visible.phase === 'refreshing'}>
          {snapshot.rows.map(row => {
            const route = resourceRoute(row);
            const title = row.title?.split('\n', 1)[0]?.replace(/^#{1,6} +/u, '') || (row.kind === 'work' ? 'Untitled work' : 'Untitled document');
            return <article className="workspace-result" key={route}>
              <div className="workspace-result-project">{row.project_key && <span>{row.project_key}</span>}{row.project_title || 'Project'}</div>
              <Button variant="quiet" disabled={!canOpen} data-resource-route={route} onClick={() => current.current.onOpen(row)}>{title}</Button>
              <div className="workspace-result-properties"><span>{row.kind === 'work' ? 'Work' : 'Document'}</span>
                {row.kind === 'work' && row.status && <StatusBadge label={workStateLabel(row.status)}/>}
                {row.kind === 'work' && row.assignee_display_name && <span>Assigned to {row.assignee_display_name}</span>}</div>
              {row.snippet && <p>{row.snippet}</p>}
            </article>;
          })}
          {visible.phase === 'ready' && !snapshot.rows.length && <EmptyState title={view === 'my-work' ? 'No assigned work' : 'No results'}
            description={view === 'my-work' ? 'No unfinished work is assigned to you on this Home.' : 'Try different words. Only content you can access is included.'}/>}
          {snapshot.rows.length > 0 && <div className="workspace-pagination"><p>Page {snapshot.page} · {snapshot.rows.length} {snapshot.rows.length === 1 ? 'result' : 'results'}</p>
            {snapshot.cursor && <Button disabled={!canOpen} onClick={() => actions.current?.next()}>Next page</Button>}</div>}
        </div>}
      </>}
  </section>;
}

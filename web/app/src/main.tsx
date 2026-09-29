import { newId } from './protocol';
import { StrictMode, Suspense, lazy, useEffect, useRef, useState, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import { HomeClient, HomeError, command, type Command, type Fields, type HomeWatch, type Query, type Row, type UpdateScope, type ViewKind } from './api';
import { Button, EmptyState, LoadingState, Surface, TextField } from './primitives';
import { SupportDetails } from './SupportDetails';
import { AcceptedTime } from './AcceptedTime';
import './style.css';
const Markdown = lazy(() => import('./Markdown').then(module => ({ default: module.Markdown })));
const client = new HomeClient();
const blankQuery = (kind: ViewKind, project_id = '', container_id = '', resource_id = '', search = '', cursor = ''): Query =>
  ({ kind, project_id, container_id, resource_id, search, cursor });
const scopeKey = (session: string | undefined, scope: UpdateScope) => JSON.stringify([session, scope.kind, scope.project_id, scope.container_id, scope.resource_id, scope.search]);
const messages: Record<string, string> = {
  search_too_long: 'Search is limited to 128 UTF-8 bytes. Shorten the phrase.',
  logout_unconfirmed: 'Sign-out was not confirmed. Keep this tab open and retry Sign out; your server session may still be active.',
  session_required: 'Your session has ended. Sign in again.',
  denied_or_not_found: 'This resource is unavailable or you do not have access.',
  revision_conflict: 'Someone saved a newer revision. Your draft is still here. Load the current version before choosing what to save.',
  authority_epoch_conflict: 'The project authority has changed. Refresh before submitting again.',
  stale_cursor: 'This view changed. Refresh to get the current page.',
  capacity_exceeded: 'This home has reached an alpha limit. No change was saved.',
  outcome_unknown: 'The home did not confirm the outcome. Check the receipt or retry the same request before making another change.',
  invalid_response: 'The home returned an unsupported response. No save has been confirmed.',
  unsupported_version: 'This home does not support this version of Stead.',
  projection_unavailable: 'This view is rebuilding. Try refreshing shortly.',
  invalid_csrf: 'Another tab refreshed your session. Resume this tab, then explicitly retry your request.',
  resume_required: 'Session resumption was not confirmed. Your local changes are still here. Resume this tab before choosing what to retry.',
};
const explain = (error: unknown) => error instanceof HomeError ? messages[error.code] ?? `The home rejected this request (${error.code}).` : 'The request could not be completed.';
function App() {
  const [identity, setIdentity] = useState<Fields | null>(null);
  const [ship, setShip] = useState('');
  const [challenge, setChallenge] = useState<Fields | null>(null);
  const [projects, setProjects] = useState<Row[]>([]);
  const [project, setProject] = useState<Row | null>(null);
  const [containers, setContainers] = useState<Row[]>([]);
  const [container, setContainer] = useState<Row | null>(null);
  const [tab, setTab] = useState<ViewKind>('project');
  const [rows, setRows] = useState<Row[]>([]);
  const [cursor, setCursor] = useState('');
  const [search, setSearch] = useState('');
  const [searchDraft, setSearchDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [updatesRevision, setUpdatesRevision] = useState(0);
  const [updatesConnected, setUpdatesConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [diagnostic, setDiagnostic] = useState('none');
  const [notice, setNotice] = useState('');
  const [editor, setEditor] = useState<{ id: string; revision: string; head: string; text: string; dirty: boolean } | null>(null);
  const [currentVersion, setCurrentVersion] = useState<{scope: string; row: Row} | null>(null);
  const [work, setWork] = useState<Row | null>(null);
  const [form, setForm] = useState<'' | 'project' | 'work' | 'container' | 'relation' | 'publish'>('');
  const [targets, setTargets] = useState<Row[]>([]);
  const [targetFilter, setTargetFilter] = useState('');
  const [confirmation, setConfirmation] = useState<{command: Command; label: string} | null>(null);
  const [pending, setPending] = useState<Command | null>(null);
  const comparisonScope = `${identity?.session_audit_id}/${project?.project_id}/${container?.container_id ?? ''}/${editor?.id ?? work?.resource_id ?? ''}`;
  const activeQuery = useRef(0);
  const displayedSnapshot = useRef<{scope: string; generation: string} | null>(null);
  const openingWatch = useRef<Promise<void> | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const clearViews = () => {
    activeQuery.current++;
    displayedSnapshot.current = null;
    setLoading(false);
    setProjects([]); setProject(null); setContainers([]); setContainer(null); setRows([]);
    setSearch(''); setSearchDraft(''); setCursor(''); setEditor(null); setWork(null); setForm(''); setPending(null); setTargets([]); setTargetFilter(''); setConfirmation(null); setCurrentVersion(null); setNotice('');
  };
  client.onInvalidated = () => { clearViews(); setIdentity(null); setChallenge(null); };
  async function identify(admitted?: Fields) {
    // consume/resume already validate identity in HomeClient.adopt().
    const person = admitted ?? Object.values((await client.query(blankQuery('identity'))).rows)[0];
    if (!person) throw new HomeError('invalid_response');
    setIdentity(person);
    const list = await client.query(blankQuery('projects'));
    setProjects(Object.values(list.rows));
  }
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await client.capabilities();
        if (!active) return;
        const person = await client.resume();
        if (active) await identify(person);
      }
      catch (failure) { if (active && (!(failure instanceof HomeError) || failure.code !== 'session_required')) { setError(explain(failure)); setDiagnostic(failure instanceof HomeError ? failure.code : 'unexpected_error'); } }
      finally { if (active) setLoading(false); }
    })();
    const connection = () => setOnline(navigator.onLine);
    window.addEventListener('online', connection); window.addEventListener('offline', connection);
    return () => { active = false; window.removeEventListener('online', connection); window.removeEventListener('offline', connection); };
  }, []);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (busy || editor?.dirty || pending || form) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [editor?.dirty, pending, form, busy]);
  const actionBusy = useRef(false);
  async function action(callback: () => Promise<unknown>) {
    if (actionBusy.current) return;
    actionBusy.current = true;
    setBusy(true); setError('');
    try { await callback(); }
    catch (failure) {
      if (failure instanceof HomeError && failure.code === 'denied_or_not_found') clearViews();
      setDiagnostic(failure instanceof HomeError ? failure.code : 'unexpected_error');
      setError(explain(failure));
    } finally { actionBusy.current = false; setBusy(false); }
  }
  async function collections(projectId: string): Promise<Row[]> {
    const found: Row[] = [];
    let next = ''; const seen = new Set<string>();
    do {
      if (seen.has(next) || seen.size >= 2) throw new HomeError('invalid_response');
      seen.add(next); const result = await client.query(blankQuery('containers', projectId, '', '', '', next));
      found.push(...Object.values(result.rows)); next = result.cursor;
      if (found.length > 32) throw new HomeError('invalid_response');
    } while (next);
    return found;
  }
  async function findTargets(term = targetFilter) {
    if (!project) return;
    const result = await client.query(blankQuery('search', project.project_id, '', '', term));
    setTargets(Object.values(result.rows));
    if (result.cursor) setNotice('Showing the first 20 matches. Refine the search to choose a resource.');
  }
  function adoptProject(view: { rows: Record<string, Row> }, projectId: string) {
    const values = Object.values(view.rows);
    const current = values[0];
    if (values.length !== 1 || !current || current.project_id !== projectId
      || !current.authority_epoch || !['reader', 'contributor', 'maintainer'].includes(current.role ?? '')) throw new HomeError('invalid_response');
    setProject(current);
    setProjects(previous => previous.map(row => row.project_id === projectId ? current : row));
  }
  async function refresh(nextTab = tab, nextContainer = container, nextCursor = '', term = search, applies = () => true, announce = true) {
    if (!project || !applies()) return false;
    if (nextTab === 'search' && new TextEncoder().encode(term).byteLength > 128) throw new HomeError('search_too_long');
    const generation = ++activeQuery.current;
    if (announce) setLoading(true);
    try {
      const metadata = await client.query(blankQuery('project', project.project_id));
      if (generation !== activeQuery.current || !applies()) return false;
      adoptProject(metadata, project.project_id!);
      if (nextTab === 'documents' && !nextCursor) {
        const boxes = await collections(project.project_id!);
        if (generation !== activeQuery.current || !applies()) return false;
        setContainers(boxes);
        if (!nextContainer) { displayedSnapshot.current = null; setRows([]); setCursor(''); return true; }
      }
      const query = blankQuery(nextTab, project.project_id, nextTab === 'documents' ? nextContainer?.container_id ?? '' : '', '', nextTab === 'search' ? term : '', nextCursor);
      const view = nextTab === 'project' ? metadata : await client.query(query);
      if (generation !== activeQuery.current || !applies()) return false;
      displayedSnapshot.current = {scope: scopeKey(identity?.session_audit_id, query), generation: view.generation};
      setRows(Object.values(view.rows)); setCursor(view.cursor); if (announce) setNotice('View refreshed from home.');
      return true;
    } finally { if (announce && generation === activeQuery.current) setLoading(false); }
  }
  useEffect(() => {
    setUpdatesConnected(false);
    if (!identity || !project
      || new TextEncoder().encode(search).byteLength > 128) return;
    let active = true;
    let watch: HomeWatch | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let pendingRefresh = false;
    let pendingGeneration: string | null = null;
    setLoading(true);
    const scope = {kind: tab === 'documents' && !container ? 'containers' as const : tab, project_id: project.project_id!, container_id: tab === 'documents' ? container?.container_id ?? '' : '', resource_id: '', search: tab === 'search' ? search : ''};
    const alreadyShown = (generation: string) => displayedSnapshot.current?.scope === scopeKey(identity.session_audit_id, scope)
      && displayedSnapshot.current.generation === generation;
    const refreshScope = async (initial = false) => {
      const applied = await refresh(tab, container, '', search, () => active && !actionBusy.current, false);
      if (applied && active) {
        setLoading(false);
        if (initial) setNotice('View refreshed from home.');
      }
      return applied;
    };
    const schedule = (callback: () => Promise<void>, delay = 2000) => { if (active) timer = setTimeout(callback, delay); };
    const failed = (failure: unknown) => {
      if (!active) return;
      setUpdatesConnected(false);
      setLoading(false);
      setDiagnostic(failure instanceof HomeError ? failure.code : 'updates_unavailable');
      if (failure instanceof HomeError && failure.code === 'denied_or_not_found') {
        clearViews(); setError(explain(failure));
      } else if (!(failure instanceof HomeError && ['session_required', 'session_changed'].includes(failure.code))) {
        setError('Live updates are unavailable. Resume this tab to reconnect. Your local edits and pending requests are still here.');
      }
    };
    async function poll() {
      if (!active || !watch) return;
      if (actionBusy.current) { schedule(poll, 200); return; }
      try {
        // A foreground save may have loaded this exact scoped generation
        // while a queued invalidation waited. The authenticated poll remains.
        if (pendingGeneration && alreadyShown(pendingGeneration)) pendingRefresh = false;
        if (pendingRefresh) {
          if (!await refreshScope()) { schedule(poll, 200); return; }
          pendingRefresh = false;
          if (active) setNotice('Shared changes loaded from home.');
        }
        pendingGeneration = null;
        const update = await watch.poll();
        if (!active) return;
        if (update.status === 'refresh_required') {
          watch = null; setUpdatesConnected(false); schedule(connect, 0); return;
        }
        pendingRefresh = Object.keys(update.rows).length > 0 && !alreadyShown(update.generation);
        pendingGeneration = pendingRefresh ? update.generation : null;
        schedule(poll, pendingRefresh ? 0 : 2000);
      } catch (failure) { failed(failure); }
    }
    async function connect() {
      if (!active) return;
      if (actionBusy.current) { schedule(connect, 200); return; }
      try {
        // Coalesce fast navigation while an old open is unresolved. Retire its
        // eventual handle before admitting the latest scope, so abandoned
        // opens cannot consume the home’s bounded watch slots.
        while (openingWatch.current) {
          await openingWatch.current;
          if (!active) return;
        }
        if (actionBusy.current) { schedule(connect, 200); return; }
        let release!: () => void;
        const opening = new Promise<void>(resolve => { release = resolve; });
        openingWatch.current = opening;
        try {
          watch = await client.watch(scope);
          if (!active) { if (watch) await client.retire(watch); return; }
          if (!watch) throw new HomeError('refresh_required');
        } finally {
          if (openingWatch.current === opening) openingWatch.current = null;
          release();
        }
        // Open before the first snapshot. Foreground actions keep this watch;
        // they do not reopen it and silently reset a user's current page.
        pendingRefresh = !await refreshScope(true);
        if (active) { setUpdatesConnected(true); schedule(poll, pendingRefresh ? 200 : 2000); }
      } catch (failure) { failed(failure); }
    }
    void connect();
    return () => { active = false; if (timer) clearTimeout(timer); if (watch) void client.retire(watch).catch(() => {}); };
  }, [identity?.session_audit_id, project?.project_id, tab, container?.container_id, search, updatesRevision]);
  useEffect(() => { if (project) heading.current?.focus(); }, [project?.project_id]);
  function reloadScope() {
    activeQuery.current++;
    displayedSnapshot.current = null;
    setError(''); setLoading(true);
    setUpdatesRevision(value => value + 1);
  }
  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    if (new TextEncoder().encode(searchDraft).byteLength > 128) {
      setError(messages.search_too_long!); setDiagnostic('search_too_long'); return;
    }
    setSearch(searchDraft);
    reloadScope();
  }
  async function openProject(row: Row) {
    if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft before switching projects.'); return; }
    setWork(null); setForm(''); setTargets([]); setConfirmation(null); setCurrentVersion(null); setProject(row); setContainer(null); setEditor(null); setRows([]); setContainers([]); setTab('project'); setCursor('');
    reloadScope();
  }
  async function completed(value: Command, receipt: Fields) {
    setPending(null);
    if (value.operation === 'document.save' && editor?.id === value.resource_id) setEditor({ ...editor, revision: receipt.resource_revision!, head: receipt.git_commit_oid ?? '', dirty: false });
    setForm(''); setWork(null); setConfirmation(null); setCurrentVersion(null);
    if (value.operation === 'document.delete') setEditor(null);
    if (value.operation === 'project.create') await identify();
    else if (value.operation === 'container.create' && project) setContainers(await collections(project.project_id!));
    else if (project) await refresh();
    setNotice(`Saved at home · revision ${receipt.resource_revision}`);
  }
  async function save(value: Command) {
    setPending(value); setNotice('Pending confirmation from home…');
    try { await completed(value, await client.command(value)); }
    catch (failure) {
      // A stale CSRF token rejects this attempt, not an earlier uncertain save.
      // Keep the original request through explicit resume and receipt recovery.
      if (failure instanceof HomeError && !['outcome_unknown', 'invalid_response', 'session_changed', 'resume_required', 'invalid_csrf'].includes(failure.code)) setPending(null);
      throw failure;
    }
  }
  async function checkReceipt() {
    if (pending) await completed(pending, await client.recover(pending));
  }
  async function openDocument(row: Row) {
    if (!project || !container) return;
    if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft first.'); return; }
    const generation = ++activeQuery.current;
    const view = await client.query(blankQuery('document', project.project_id, container.container_id, row.resource_id));
    if (generation !== activeQuery.current) return;
    const page = Object.values(view.rows)[0];
    if (!page?.markdown || !page.resource_revision) throw new HomeError('invalid_response');
    setCurrentVersion(null);
    setEditor({ id: row.resource_id!, revision: page.resource_revision, head: page.container_head ?? '', text: page.markdown, dirty: false });
  }
  async function openWork(row: Row) {
    if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft first.'); return; }
    if (!project) return; const generation = ++activeQuery.current;
    const view = await client.query(blankQuery('work', project.project_id, '', row.resource_id));
    if (generation !== activeQuery.current) return;
    const item = Object.values(view.rows)[0]; if (!item) throw new HomeError('denied_or_not_found');
    setWork(item); setForm('work'); setCurrentVersion(null);
  }
  async function loadCurrentVersion() {
    if (!project) return;
    const generation = ++activeQuery.current; const scope = comparisonScope;
    if (editor && container) {
      if (editor.revision === '0') return;
      const view = await client.query(blankQuery('document', project.project_id, container.container_id, editor.id));
      if (generation === activeQuery.current) setCurrentVersion(Object.values(view.rows)[0] ? {scope, row: Object.values(view.rows)[0]!} : null);
    } else if (work) {
      const view = await client.query(blankQuery('work', project.project_id, '', work.resource_id));
      if (generation === activeQuery.current) setCurrentVersion(Object.values(view.rows)[0] ? {scope, row: Object.values(view.rows)[0]!} : null);
    }
  }
  const canEdit = project && ['contributor', 'maintainer'].includes(project.role ?? '');
  const draftMode = container?.visibility === 'private';
  function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (form === 'publish' && (!editor || editor.dirty)) { setError('Save the page before choosing its publication destination.'); return; }
    if (!identity) return;
    const data = new FormData(event.currentTarget);
    const text = (key: string) => String(data.get(key) ?? '');
    if (new TextEncoder().encode(text('description')).byteLength > 8192) { setError('Description is limited to 8,192 UTF-8 bytes. Shorten it before saving.'); return; }
    let next: Command;
    if (form === 'project') {
      const id = newId();
      next = command(id, id, '0', '1', 'project.create', { organization_id: identity.organization_id!, owning_team_id: identity.team_id!, title: text('title'), project_key: text('project_key'), preset: 'general' });
    } else {
      if (!project) return;
      const id = form === 'work' && work ? work.resource_id! : newId();
      if (form === 'work') next = command(project.project_id!, id, work?.resource_revision ?? '0', project.authority_epoch!, work ? 'work.update' : 'work.create',
        { title: text('title'), description: text('description'), type: text('type'), status: text('status'), priority: text('priority') });
      else if (form === 'container') next = command(project.project_id!, id, '0', project.authority_epoch!, 'container.create', { title: text('title'), visibility: text('visibility') });
      else if (form === 'publish') {
        const destination = containers.find(row => row.container_id === text('destination') && row.visibility === 'shared');
        if (!editor || !container || !destination) return;
        next = command(project.project_id!, id, '0', project.authority_epoch!, 'document.publish', {
          source_project_id: project.project_id!, source_container_id: container.container_id!, source_document_id: editor.id,
          source_revision: editor.revision, source_head: editor.head, container_id: destination.container_id!, expected_head: destination.container_head ?? '' });
      } else {
        const source = targets.find(row => `${row.kind}/${row.container_id}/${row.resource_id}` === text('source'));
        const target = targets.find(row => `${row.kind}/${row.container_id}/${row.resource_id}` === text('target'));
        if (!source || !target) return;
        next = command(project.project_id!, id, '0', project.authority_epoch!, 'relation.create', {
          type: text('relation_type'), source_project_id: project.project_id!, source_kind: source.kind!, source_container_id: source.container_id!, source_id: source.resource_id!,
          target_project_id: project.project_id!, target_kind: target.kind!, target_container_id: target.container_id!, target_id: target.resource_id! });
      }
    }
    void action(() => save(next));
  }
  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="/stead/" aria-label="Stead home">s<span>stead</span></a><span className="alpha">Team alpha</span><div className="account">{identity ? <><span>{identity.display_name} <small className="muted">{identity.identity_ship}</small></span><Button variant="quiet" disabled={busy} onClick={() => void action(() => client.logout())}>Sign out</Button></> : <span>Work, with context.</span>}</div></header>
    {!online && <div className="banner" role="status">You’re offline. Drafts stay in this tab; nothing is saved until the home confirms it.</div>}
    <main id="main"><a className="skip-link" href="#project-content">Skip to project content</a>
      {error && <div className="error" role="alert"><p>{error}</p>{identity && <Button onClick={() => void action(async () => { const person = await client.resume(); await identify(person); if (project && person.session_audit_id === identity?.session_audit_id) reloadScope(); setNotice('Session resumed. Choose whether to retry your pending request.'); })}>Resume this tab</Button>}</div>}
      <div className="live" role="status" aria-live="polite">{notice}</div>
      {loading && !identity && <LoadingState label="Connecting to your home"/>}
      {!identity && !loading && <Surface className="login"><p className="eyebrow">YOUR TEAM’S HOME</p><h1>Make room for good work.</h1><p>Sign in with your individual identity. Work and documents stay at this home.</p>
        <form onSubmit={event => { event.preventDefault(); void action(async () => { const value = await client.start(ship); setChallenge(value); }); }}>
          <TextField label="Your identity ship" placeholder="~sampel-palnet" value={ship} onChange={event => setShip(event.target.value)} autoComplete="off" required maxLength={64}/>
          <Button type="submit" variant="primary" pending={busy} pendingLabel="Requesting approval">Request sign-in</Button>
        </form>
        {challenge && <div className="approval"><h2>Approve on your identity ship</h2><p>Open its Stead identity page. Check this home and the comparison code before approving.</p><p><strong>Home</strong> {location.origin}</p><p className="comparison">{challenge.comparison_code}</p><Button disabled={busy} onClick={() => void action(async () => { const status = await client.status(challenge.challenge_id!); if (status.status === 'approved') { const person = await client.consume(challenge.challenge_id!); setChallenge(null); await identify(person); } else setNotice('Approval is still pending on your identity ship.'); })}>Check approval</Button></div>}
      </Surface>}
      {identity && <div className="workspace">
        <aside className="sidebar"><p className="eyebrow">YOUR WORKSPACE</p><h2>Projects</h2>{projects.length === 0 && <p className="muted">No projects are shared with you yet.</p>}<nav aria-label="Projects">{projects.map(row => <button disabled={busy} key={row.project_id} className={project?.project_id === row.project_id ? 'selected' : ''} onClick={() => void action(() => openProject(row))}><span className="project-key">{row.project_key}</span>{row.title}</button>)}</nav>{identity.can_create === 'yes' && <Button variant="quiet" disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => { setEditor(null); setWork(null); setCurrentVersion(null); setForm('project'); }}>＋ New project</Button>}<p className="sidebar-note">Only projects explicitly shared with you appear here.</p></aside>
        <section className="content" id="project-content" data-live-updates={updatesConnected ? 'connected' : 'unavailable'}>
          {pending && <Surface className="pending"><h2>Save awaiting confirmation</h2><p>Keep this tab open. Retrying uses the same request ID and cannot create a second accepted change.</p>{pending.operation === 'project.create' && <p>Use Retry this request to confirm a new project. Receipt lookup needs access to an existing project.</p>}<div className="actions">{pending.operation !== 'project.create' && <Button disabled={busy} onClick={() => void action(checkReceipt)}>Check receipt</Button>}<Button disabled={busy} onClick={() => void action(() => save(pending))}>Retry this request</Button></div></Surface>}
          {!project && <div className="welcome"><p className="eyebrow">START WITH WHAT MATTERS</p><h1 ref={heading} tabIndex={-1}>A clear place for your work.</h1><p>Choose a project to see its work and knowledge.</p></div>}
          {project && <><div className="project-heading"><div><p className="eyebrow">{project.project_key} / GENERAL PROJECT</p><h1 ref={heading} tabIndex={-1}>{project.title}</h1></div><span className="role-badge">{project.role}</span></div>
          <nav className="tabs" aria-label="Project views">{([['project','Overview'],['work','Work'],['documents','Docs'],['relations','Links'],['activity','Activity'],['inbox','Inbox'],['search','Search']] as const).map(([kind,label]) => <Button disabled={busy} key={kind} variant={tab === kind ? 'primary' : 'quiet'} aria-current={tab === kind ? 'page' : undefined} onClick={() => { if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft first.'); return; } activeQuery.current++; setEditor(null); setWork(null); setCurrentVersion(null); setConfirmation(null); setForm(''); setTab(kind); setRows([]); setCursor(''); reloadScope(); }}>{label}</Button>)}</nav>
          <div className="toolbar"><div>{tab === 'documents' && <label>Collection <select aria-label="Collection" disabled={busy} value={container?.container_id ?? ''} onChange={event => { const selected = containers.find(row => row.container_id === event.target.value) ?? null; if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft first.'); return; } activeQuery.current++; setContainer(selected); setEditor(null); setWork(null); setCurrentVersion(null); setConfirmation(null); setForm(''); setRows([]); setCursor(''); reloadScope(); }}><option value="">Choose a collection</option>{containers.map(row => <option key={row.container_id} value={row.container_id}>{row.title} · {row.visibility === 'private' ? 'Private drafts' : 'Shared'}</option>)}</select></label>}{tab === 'search' && <form className="search" onSubmit={submitSearch}><TextField label="Search this project" value={searchDraft} onChange={event => setSearchDraft(event.target.value)} maxLength={128}/><Button type="submit" disabled={busy}>Search</Button></form>}</div><div className="actions">
          <Button disabled={busy || loading} onClick={reloadScope}>Refresh</Button>
          {canEdit && tab === 'work' && <Button variant="primary" disabled={busy || !!pending || !!form} onClick={() => { setWork(null); setCurrentVersion(null); setForm('work'); }}>New work item</Button>}
          {canEdit && tab === 'relations' && <Button variant="primary" disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => void action(async () => { await findTargets(''); setTargetFilter(''); setForm('relation'); })}>Add link</Button>}
          {canEdit && tab === 'documents' && <><Button disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => { setEditor(null); setWork(null); setCurrentVersion(null); setForm('container'); }}>New collection</Button>{container && <Button variant="primary" disabled={busy || loading || !!pending || !!form || !!editor?.dirty} onClick={() => { activeQuery.current++; const id = newId(); setWork(null); setCurrentVersion(null); setEditor({ id, revision: '0', head: container.container_head ?? '', dirty: true, text: `---\nid: ${id}\ntype: page\nstate: ${draftMode ? 'draft' : 'published'}\n---\n# Untitled\n` }); }}>New page</Button>}</>}
          </div></div>
          {((editor && editor.revision !== '0') || work) && <div className="actions"><Button disabled={busy || !!pending} onClick={() => void action(loadCurrentVersion)}>Compare current saved revision</Button></div>}
          {currentVersion && currentVersion.scope === comparisonScope && <Surface className="comparison"><h2>Current saved revision {currentVersion.row.resource_revision}</h2><pre>{currentVersion.row.markdown ?? `${currentVersion.row.title}\n${currentVersion.row.description}`}</pre><p>Your local text has not changed. Choose its base revision before saving again.</p><Button disabled={busy || !!pending} onClick={() => { if (currentVersion.scope !== comparisonScope) { setCurrentVersion(null); return; } if (editor) setEditor({...editor, revision: currentVersion.row.resource_revision!, head: currentVersion.row.container_head ?? '', dirty: true}); else if (work) setWork(currentVersion.row); setCurrentVersion(null); setNotice('Local edits kept. Review them, then explicitly save against the current revision.'); }}>Keep my edits using this revision</Button><Button onClick={() => setCurrentVersion(null)}>Close comparison</Button></Surface>}
          {confirmation && <Surface className="confirmation"><h2>Delete {confirmation.label}?</h2><p>This removes it from current views. Authorized historical Git exports retain earlier page versions; this does not erase copies others already hold.</p><div className="actions"><Button disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => void action(() => save(confirmation.command))}>Confirm deletion</Button><Button disabled={busy} onClick={() => setConfirmation(null)}>Keep it</Button></div></Surface>}
          {editor && container ? <Surface className="document-editor"><div className="editor-heading"><h2>{draftMode ? 'Private draft' : 'Shared page'}</h2><span>{editor.dirty ? 'Local changes · not saved' : `Saved revision ${editor.revision}`}</span></div><label className="editor-label" htmlFor="markdown">Markdown source</label><textarea id="markdown" value={editor.text} readOnly={!canEdit || busy || !!pending || !!form} onChange={event => setEditor({ ...editor, text: event.target.value, dirty: true })} spellCheck/>
          <div className="actions"><Button variant="primary" disabled={!canEdit || !editor.dirty || busy || !!pending || !!form} onClick={() => void action(() => save(command(project.project_id!, editor.id, editor.revision, project.authority_epoch!, 'document.save', { container_id: container.container_id!, markdown: editor.text })))}>Save page</Button>{canEdit && !editor.dirty && editor.revision !== '0' && draftMode && <Button disabled={busy || !!pending || !!form} onClick={() => void action(async () => { setContainers(await collections(project.project_id!)); setForm('publish'); })}>Publish selected page</Button>}{canEdit && editor.revision !== '0' && <Button disabled={busy || !!pending || !!form || editor.dirty} onClick={() => setConfirmation({label: 'this page', command: command(project.project_id!, editor.id, editor.revision, project.authority_epoch!, 'document.delete', {container_id: container.container_id!, expected_head: editor.head})})}>Delete page</Button>}<Button disabled={busy || !!pending || !!form} onClick={() => { setEditor(null); setError(''); }}>Discard local changes and close</Button></div><h3>Preview</h3><Suspense fallback={<p>Loading preview…</p>}><Markdown key={comparisonScope} text={editor.text}/></Suspense></Surface> : <>
          {loading ? <LoadingState label="Loading authorized view"/> : rows.length === 0 ? <EmptyState title={tab === 'documents' && !container ? 'Choose a collection' : 'Nothing here yet'} description={tab === 'documents' ? 'Private drafts stay private until you explicitly publish a page.' : 'This view contains only resources you are allowed to access.'}/> : <div className="rows">{rows.map((row,index) => <Surface key={row.request_id ? `event/${row.request_id}` : `${row.kind ?? tab}/${row.project_id ?? project.project_id}/${row.container_id ?? ''}/${row.resource_id ?? index}`} className="resource-row"><div><span className="row-kind">{row.kind ?? row.type ?? tab}</span><h2>{row.title ?? row.summary ?? row.operation ?? row.resource_id}</h2>{row.description && <p>{row.description}</p>}{row.snippet && row.snippet !== row.description && <p>{row.snippet}</p>}<span className="muted">{row.status}{row.priority ? ` · ${row.priority}` : ''}</span>{row.kind === 'activity' && <p className="muted" data-event-request={row.request_id}>{row.principal_id === identity.principal_id ? 'You' : `Member ${row.principal_id}`} · <AcceptedTime milliseconds={row.accepted_at_ms ?? ''}/></p>}</div><div className="actions">{tab === 'documents' && <Button disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => void action(() => openDocument(row))}>Open page</Button>}{tab === 'work' && canEdit && <Button disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => void action(() => openWork(row))}>Edit</Button>}{canEdit && (tab === 'work' || tab === 'relations') && <Button disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => setConfirmation({label: tab === 'work' ? 'this work item' : 'this link', command: command(project.project_id!, row.resource_id!, row.resource_revision!, project.authority_epoch!, tab === 'work' ? 'work.delete' : 'relation.delete', {})})}>Delete</Button>}</div></Surface>)}</div>}
          {cursor && <Button disabled={busy || loading || !updatesConnected} onClick={() => void action(() => refresh(tab, container, cursor))}>Next page</Button>}</>}
          </>}
          {form && <Surface className="creation"><h2>{form === 'project' ? 'Create a general project' : form === 'container' ? 'Create a collection' : form === 'relation' ? 'Link two resources' : form === 'publish' ? 'Publish a selected page' : work ? 'Edit work item' : 'Create work item'}</h2><form key={form + (work?.resource_id ?? '')} onSubmit={submitForm}><fieldset disabled={busy || !!pending}>
            {form !== 'relation' && form !== 'publish' && <TextField label="Title" name="title" defaultValue={form === 'work' ? work?.title ?? '' : ''} maxLength={200} required/>}
            {form === 'project' && <TextField label="Project key" description="A short uppercase key, such as GARDEN." name="project_key" pattern="[A-Z][A-Z0-9]{1,9}" maxLength={10} required/>}
            {form === 'container' && <label>Visibility<select name="visibility" aria-label="Visibility"><option value="private">Private drafts · only you</option>{project?.role === 'maintainer' && <option value="shared">Shared with project members</option>}</select></label>}
            {form === 'work' && <><label>Description<textarea name="description" defaultValue={work?.description ?? ''} maxLength={8192}/></label><div className="form-columns"><label>Type<select name="type" defaultValue={work?.type ?? 'task'}>{['deliverable','task','problem'].map(value => <option key={value}>{value}</option>)}</select></label><label>Status<select name="status" defaultValue={work?.status ?? 'todo'}>{['backlog','todo','in_progress','blocked','done','canceled'].map(value => <option key={value}>{value}</option>)}</select></label><label>Priority<select name="priority" defaultValue={work?.priority ?? 'none'}>{['none','low','medium','high','urgent'].map(value => <option key={value}>{value}</option>)}</select></label></div></>}
            {form === 'publish' && <><p>Publish saved revision {editor?.revision} of page {editor?.id}. Its source is locked while you choose a destination. Copy this saved page into a shared collection. The original and other drafts stay private. Only the selected body is published.</p><label>Destination collection<select name="destination" aria-label="Destination collection" required><option value="">Choose a shared collection</option>{containers.filter(row => row.visibility === 'shared').map(row => <option key={row.container_id} value={row.container_id}>{row.title}</option>)}</select></label></>}
            {form === 'relation' && <><div className="search"><TextField label="Find resources to link" value={targetFilter} onChange={event => setTargetFilter(event.target.value)} maxLength={128}/><Button disabled={busy} onClick={() => void action(() => findTargets())}>Find resources</Button></div><label>Link type<select name="relation_type" aria-label="Link type"><option value="related_to">Related to</option><option value="blocks">Blocks · work to work</option><option value="documents">Documents · page to work</option></select></label>{['source','target'].map(side => <label key={side}>{side === 'source' ? 'From resource' : 'To resource'}<select name={side} aria-label={side === 'source' ? 'From resource' : 'To resource'} required><option value="">Choose an authorized resource</option>{targets.map(row => { const key = `${row.kind}/${row.container_id}/${row.resource_id}`; return <option key={key} value={key}>{row.title} · {row.kind}</option>; })}</select></label>)}</>}

            <div className="actions"><Button type="submit" variant="primary" pending={busy} disabled={!!pending}>Save at home</Button><Button disabled={busy} onClick={() => { setForm(''); setWork(null); }}>Cancel</Button></div>
          </fieldset></form></Surface>}
        </section>
      </div>}
    </main><footer><div>One home for work and knowledge.<SupportDetails code={diagnostic} requestId={pending?.request_id}/></div><span>Local changes become shared only after the home accepts them.</span></footer>
  </div>;
}
const root = document.getElementById('root');
if (!root) throw new Error('Missing application root');
createRoot(root).render(<StrictMode><App/></StrictMode>);

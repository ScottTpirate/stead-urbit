import { newId } from './protocol';
import { StrictMode, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { HomeClient, HomeError, UUID, command, type CodeReviewKey, type Command, type Fields, type HomeWatch, type Query, type Row, type UpdateScope, type ViewKind } from './api';
import { Button, EmptyState, LoadingState, Surface, TextField } from './primitives';
import { SupportDetails } from './SupportDetails';
import { AcceptedTime } from './AcceptedTime';
import { WorkQuickActions, assigneeName, workStatuses, type WorkMenu, type WorkProperty } from './WorkQuickActions';
import { CodeRepository } from './CodeRepository';
import { CodePack } from './CodePack';
import { WorkCodeLinks } from './WorkCodeLinks';
import { WorkDevelopment, type CodeDevelopmentTarget } from './WorkDevelopment';
import { WorkDiscussion } from './WorkDiscussion';
import { WorkDelegations } from './WorkDelegations';
import { WorkContext } from './WorkContext';
import { decodeProductRoute, encodeProductRoute, NavigationMemory, type ProductRoute } from './productRoutes';
import { newWorkDefaults, priorityLabel } from './productModel';
import { UrbitSignIn } from './UrbitSignIn';
import './style.css';
import { DocumentBody } from './DocumentBody';
import {eventPresentation} from './eventPresentation';
import {WorkspaceView} from './WorkspaceView';
import {DocumentContext} from './DocumentContext';
import {Icon} from './Icon';
const client = new HomeClient();
const blankQuery = (kind: ViewKind, project_id = '', container_id = '', resource_id = '', search = '', cursor = ''): Query =>
  ({ kind, project_id, container_id, resource_id, search, cursor });
const scopeKey = (session: string | undefined, scope: UpdateScope) => JSON.stringify([session, scope.kind, scope.project_id, scope.container_id, scope.resource_id, scope.search]);
const messages: Record<string, string> = {
  invalid_ship_name: 'Enter an Urbit ID such as sampel-palnet. The tilde is optional.',
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
const explainConnection = (error: unknown) => error instanceof HomeError && error.code === 'outcome_unknown'
  ? 'Stead cannot reach this home right now. Try again once it is back online.'
  : explain(error);
function ActionMenu({ label, disabled, children }: { label: string; disabled: boolean; children: ReactNode }) {
  const disclosure = useRef<HTMLDetailsElement>(null);
  return <details className="action-menu" ref={disclosure} onKeyDown={event => {
    if (event.key === 'Escape' && disclosure.current?.open) {
      event.preventDefault(); disclosure.current.open = false; disclosure.current.querySelector('summary')?.focus();
    }
  }}><summary aria-label={label} aria-disabled={disabled} onClick={event => { if (disabled) event.preventDefault(); }}><span aria-hidden="true">•••</span></summary>
    <div className="menu-actions" onClick={event => { if ((event.target as HTMLElement).closest('button') && disclosure.current) disclosure.current.open = false; }}>{children}</div>
  </details>;
}
const PAGE_HEADER = /^---\nid: [0-9a-f-]{36}\ntype: page\nstate: (draft|published)\n---\n/u;
const initialWorkFilters = { title: '', status: '', assignee: '' };
const workShortcuts = new Map<string, WorkProperty>([['s', 'status'], ['a', 'assignee'], ['p', 'priority']]);
type WorkRoster = { status: 'loading' | 'unavailable' } | { status: 'ready'; rows: Row[] };
type WorkAddress = { project: string; item?: string };
function decodeWorkAddress(hash: string): WorkAddress | null {
  const route = decodeProductRoute(hash);
  return route?.kind === 'work' ? {project: route.project, item: route.item} : null;
}
function workAddress(project: string, item?: string) {
  const url = new URL(location.pathname, location.origin);
  url.hash = encodeProductRoute({kind: 'work', project, item});
  return url;
}
function pageTitle(text: string) {
  const body = text.replace(PAGE_HEADER, '');
  return body.match(/^#{1,6} +(.+)$/mu)?.[1]?.trim() || 'Untitled page';
}
function App() {
  const [identity, setIdentity] = useState<Fields | null>(null);
  const [ship, setShip] = useState('');
  const [challenge, setChallenge] = useState<Fields | null>(null);
  const [projects, setProjects] = useState<Row[]>([]);
  const [project, setProject] = useState<Row | null>(null);
  const [workspaceView,setWorkspaceView]=useState<'my-work'|'search'|null>(null);
  const [workspaceSupported,setWorkspaceSupported]=useState(false);
  const workspaceAvailable=useRef(false);
  const [workspaceSearch,setWorkspaceSearch]=useState({draft:'',term:''});
  const [containers, setContainers] = useState<Row[]>([]);
  const [container, setContainer] = useState<Row | null>(null);
  const [tab, setTab] = useState<ViewKind>('project');
  const [repository, setRepository] = useState<Fields | null>(null);
  const externalRepository = repository?.status === 'external' || repository?.status === 'external-staged';
  const [showRepository, setShowRepository] = useState(false);
  const [selectedReview, setSelectedReview] = useState<string>();
  const [inlineReview, setInlineReview] = useState<CodeReviewKey>();
  const [development, setDevelopment] = useState<CodeDevelopmentTarget>();
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
  const [refreshNotice, setRefreshNotice] = useState<{text: string; sequence: number} | null>(null);
  const [editor, setEditor] = useState<{ id: string; revision: string; head: string; text: string; dirty: boolean; fullSource?: boolean } | null>(null);
  const pageHeader = editor?.text.match(PAGE_HEADER)?.[0] ?? '';
  const [currentVersion, setCurrentVersion] = useState<{scope: string; row: Row} | null>(null);
  const [work, setWork] = useState<Row | null>(null);
  const [workContextRevision, setWorkContextRevision] = useState(0);
  const [linkedPage, setLinkedPage] = useState<{origin: WorkAddress; collection: string; document: string} | null>(null);
  const linkedPageOrigin = linkedPage?.collection === container?.container_id && linkedPage?.document === editor?.id ? linkedPage?.origin : undefined;
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({});
  const [workMenu, setWorkMenu] = useState<WorkMenu | null>(null);
  const [workFiltersOpen, setWorkFiltersOpen] = useState(false);
  const [workFilters, setWorkFilters] = useState(initialWorkFilters);
  const [workRoster, setWorkRoster] = useState<WorkRoster>({status: 'loading'});
  const [workRosterRetry, setWorkRosterRetry] = useState(0);
  const [editWorkField, setEditWorkField] = useState<'title' | 'description' | null>(null);
  const [form, setForm] = useState<'' | 'project' | 'work' | 'container' | 'relation' | 'publish'>('');
  const [formDirty, setFormDirty] = useState(false);
  const [discard, setDiscard] = useState<'document' | 'form' | null>(null);
  const [targets, setTargets] = useState<Row[]>([]);
  const [targetFilter, setTargetFilter] = useState('');
  const [confirmation, setConfirmation] = useState<{command: Command; label: string} | null>(null);
  const [pending, setPending] = useState<Command | null>(null);
  const comparisonScope = `${identity?.session_audit_id}/${project?.project_id}/${container?.container_id ?? ''}/${editor?.id ?? work?.resource_id ?? ''}`;
  const workScope = `${identity?.session_audit_id}/${project?.project_id}/${project?.authority_epoch}/${work?.resource_id}`;
  const commentDraft = commentDrafts[workScope] ?? '';
  const activeQuery = useRef(0);
  const repositoryGeneration = useRef(0);
  const displayedSnapshot = useRef<{scope: string; generation: string} | null>(null);
  const openingWatch = useRef<Promise<void> | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const workEditorHeading = useRef<HTMLHeadingElement>(null);
  const documentEditorHeading = useRef<HTMLHeadingElement>(null);
  const pendingDocumentFocus = useRef<{project: string; collection: string; document: string; session: string; hash: string} | null>(null);
  const workTitle = useRef<HTMLInputElement>(null);
  const workDescription = useRef<HTMLTextAreaElement>(null);
  const newWorkButton = useRef<HTMLButtonElement>(null);
  const routedIdentity = useRef<string | undefined>(undefined);
  const lastAddress = useRef(decodeProductRoute(location.hash) ? location.hash : '');
  const navigationMemory = useRef(new NavigationMemory());
  const pendingNavigation = useRef<{project:string;scroll:number;focus?:string}|null>(null);
  const workTrigger = useRef<HTMLElement | null>(null);
  const quickActionFocus = useRef<{trigger: HTMLElement; row: string; control: string} | null>(null);
  const feedbackHeading = useRef<HTMLHeadingElement>(null);
  const discardTrigger = useRef<HTMLElement | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const clearViews = () => {
    client.clearCodeMerges();
    activeQuery.current++;
    repositoryGeneration.current++;
    displayedSnapshot.current = null;
    quickActionFocus.current = null;
    pendingDocumentFocus.current = null;
    routedIdentity.current = undefined;
    setLoading(false);
    setProjects([]); setProject(null); setWorkspaceView(null); setWorkspaceSearch({draft:'',term:''}); setContainers([]); setContainer(null); setRows([]);
    setRepository(null); setShowRepository(false); clearCodeSelection();
    setWorkFiltersOpen(false); setWorkFilters(initialWorkFilters); setWorkRoster({status: 'loading'});
    setCommentDrafts({}); navigationMemory.current.clear(); pendingNavigation.current=null;
    setLinkedPage(null);
    setSearch(''); setSearchDraft(''); setCursor(''); setEditor(null); setWork(null); setWorkMenu(null); setForm(''); setFormDirty(false); setDiscard(null); setPending(null); setTargets([]); setTargetFilter(''); setConfirmation(null); setCurrentVersion(null); setNotice(''); setRefreshNotice(null);
  };
  client.onInvalidated = () => { clearViews(); setIdentity(null); setChallenge(null); };
  async function loadRepository(projectId: string, enable = false) {
    const generation = ++repositoryGeneration.current;
    try {
      if (enable) {
        await client.code(projectId, { action: 'create' });
        if (generation !== repositoryGeneration.current) return;
      }
      const value = await client.code(projectId, { action: 'status' });
      if (generation !== repositoryGeneration.current) return;
      setRepository(value);
      if (enable) setShowRepository(true);
    } catch (failure) {
      if (generation !== repositoryGeneration.current) return;
      if (enable) throw failure;
      setRepository(null);
    }
  }
  useEffect(() => {
    const id = project?.project_id;
    if (!id || !identity?.session_audit_id) return;
    void loadRepository(id);
    const generation = repositoryGeneration.current;
    return () => { if (generation === repositoryGeneration.current) repositoryGeneration.current++; };
  }, [project?.project_id, identity?.session_audit_id]);
  async function identify(admitted?: Fields) {
    // consume/resume already validate identity in HomeClient.adopt().
    const person = admitted ?? Object.values((await client.query(blankQuery('identity'))).rows)[0];
    if (!person) throw new HomeError('invalid_response');
    setIdentity(person); navigationMemory.current.bind(person.session_audit_id ?? person.principal_id!);
    const list = await client.query(blankQuery('projects'));
    const allowed = Object.values(list.rows);
    setProjects(allowed);
    if (routedIdentity.current !== person.session_audit_id) {
      routedIdentity.current = person.session_audit_id;
      const address = decodeProductRoute(location.hash);
      if (address) await restoreProductAddress(address, allowed);
    }
  }
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const capabilities=await client.capabilities();
        if (!active) return;
        workspaceAvailable.current=capabilities.workspace_queries==='stead.workspace-queries/1';
        setWorkspaceSupported(workspaceAvailable.current);
        const person = await client.resume();
        if (active) await identify(person);
      }
      catch (failure) { if (active && (!(failure instanceof HomeError) || failure.code !== 'session_required')) { setError(explainConnection(failure)); setDiagnostic(failure instanceof HomeError ? failure.code : 'unexpected_error'); } }
      finally { if (active) setLoading(false); }
    })();
    const connection = () => setOnline(navigator.onLine);
    window.addEventListener('online', connection); window.addEventListener('offline', connection);
    return () => { active = false; window.removeEventListener('online', connection); window.removeEventListener('offline', connection); };
  }, []);
  useEffect(() => {
    if (!refreshNotice) return;
    const timer = setTimeout(() => setRefreshNotice(null), 4500);
    return () => clearTimeout(timer);
  }, [refreshNotice]);
  const announceRefresh = (text: string) => setRefreshNotice(previous => ({text, sequence: (previous?.sequence ?? 0) + 1}));
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (busy || editor?.dirty || pending || formDirty || Object.keys(commentDrafts).length) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [editor?.dirty, pending, formDirty, busy, commentDrafts]);
  useEffect(() => { setFormDirty(false); setDiscard(null); }, [form, work?.resource_id]);
  useEffect(() => { setWorkMenu(null); quickActionFocus.current = null; }, [tab, project?.project_id, project?.role, project?.authority_epoch, identity?.session_audit_id]);
  useEffect(() => {
    const restore = quickActionFocus.current;
    if (busy || loading || !restore) return;
    quickActionFocus.current = null;
    if (document.activeElement !== document.body) return;
    if (restore.trigger.isConnected) restore.trigger.focus();
    else {
      const row = document.querySelector(`[data-work-row="${CSS.escape(restore.row)}"]`);
      row?.querySelector<HTMLButtonElement>(`[data-work-control="${CSS.escape(restore.control)}"]`)?.focus();
    }
  }, [busy, loading, rows]);
  const actionBusy = useRef(false);
  async function action(callback: () => Promise<unknown>, describeFailure = explain) {
    if (actionBusy.current) return;
    actionBusy.current = true;
    setBusy(true); setError(''); setDiagnostic('none');
    try { await callback(); }
    catch (failure) {
      if (failure instanceof HomeError && failure.code === 'denied_or_not_found') clearViews();
      setDiagnostic(failure instanceof HomeError ? failure.code : 'unexpected_error');
      setError(describeFailure(failure));
    } finally { actionBusy.current = false; setBusy(false); }
  }
  async function retryConnection() {
    const capabilities=await client.capabilities();
    workspaceAvailable.current=capabilities.workspace_queries==='stead.workspace-queries/1';setWorkspaceSupported(workspaceAvailable.current);
    try { await identify(await client.resume()); }
    catch (failure) {
      if (!(failure instanceof HomeError) || failure.code !== 'session_required') throw failure;
    }
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
      let nextRows = Object.values(view.rows);
      let cursor = view.cursor;
      if (nextTab === 'work' && workFiltersOpen && !nextCursor) {
        const seen = new Set<string>();
        while (cursor) {
          if (seen.has(cursor) || seen.size >= 6) throw new HomeError('invalid_response');
          seen.add(cursor);
          const page = await client.query({...query, cursor});
          if (generation !== activeQuery.current || !applies()) return false;
          if (page.generation !== view.generation) throw new HomeError('stale_cursor');
          nextRows = [...nextRows, ...Object.values(page.rows)];
          cursor = page.cursor;
        }
        if (nextRows.length > 128 || new Set(nextRows.map(row => row.resource_id)).size !== nextRows.length) {
          throw new HomeError('invalid_response');
        }
      }
      displayedSnapshot.current = {scope: scopeKey(identity?.session_audit_id, query), generation: view.generation};
      setRows(nextRows); setCursor(cursor); if (announce) announceRefresh('View refreshed from home.');
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
        if (initial) announceRefresh('View refreshed from home.');
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
          if (active) announceRefresh('Shared changes loaded from home.');
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
  }, [identity?.session_audit_id, project?.project_id, tab, container?.container_id, search, updatesRevision, workFiltersOpen]);
  useEffect(() => { if (project) heading.current?.focus(); }, [project?.project_id]);
  useEffect(() => {
    const restore=pendingNavigation.current;
    if(!restore||loading||tab!=='work'||project?.project_id!==restore.project
      ||displayedSnapshot.current?.scope!==scopeKey(identity?.session_audit_id,blankQuery('work',restore.project)))return;
    const frame=requestAnimationFrame(()=>{
      if(pendingNavigation.current!==restore)return;
      pendingNavigation.current=null;
      if(restore.focus)document.querySelector<HTMLElement>(`[data-work-row="${CSS.escape(restore.focus)}"] .work-title`)?.focus({preventScroll:true});
      window.scrollTo({top:restore.scroll});
    });
    return ()=>cancelAnimationFrame(frame);
  },[loading,rows,tab,project?.project_id,identity?.session_audit_id]);
  useEffect(() => {
    if (showRepository) return;
    if (form === 'work' && (!work || editWorkField === 'title')) workTitle.current?.focus();
    else if (form === 'work' && editWorkField === 'description') workDescription.current?.focus();
    else if (form === 'work' || work) workEditorHeading.current?.focus();
  }, [form, work?.resource_id, editWorkField, showRepository]);
  useEffect(() => {
    const requested = pendingDocumentFocus.current;
    if (!requested) return;
    if (requested.hash !== location.hash || requested.session !== identity?.session_audit_id) {
      pendingDocumentFocus.current = null; return;
    }
    if (requested.project !== project?.project_id || requested.collection !== container?.container_id
        || requested.document !== editor?.id || editor.dirty || !documentEditorHeading.current) return;
    // Wait for the matching reader to commit. A frame queued by the async
    // route loader can run before React has mounted its heading.
    const frame = requestAnimationFrame(() => {
      if (pendingDocumentFocus.current !== requested || location.hash !== requested.hash) return;
      const target = documentEditorHeading.current;
      if (target?.isConnected) { pendingDocumentFocus.current = null; target.focus(); }
    });
    return () => cancelAnimationFrame(frame);
  }, [editor, project?.project_id, container?.container_id, identity?.session_audit_id]);
  useEffect(() => { if (discard || confirmation || currentVersion) feedbackHeading.current?.focus(); }, [discard, confirmation, currentVersion]);
  function closeDraft(target: 'document' | 'form') {
    if (target === 'document') { if(project?.project_id && container?.container_id)syncResourceAddress({kind:'collection',project:project.project_id,collection:container.container_id},true); setEditor(null); setLinkedPage(null); }
    else {
      const keepDetail = form === 'work' && !!work;
      setForm(''); setEditWorkField(null); setFormDirty(false);
      if (!keepDetail) {
        if (tab === 'work' && project?.project_id && work) syncWorkAddress(project.project_id, undefined, true);
        setWork(null); requestAnimationFrame(() => workTrigger.current?.focus());
      }
    }
    setDiscard(null); setCurrentVersion(null); setConfirmation(null); setError('');
  }
  function requestClose(target: 'document' | 'form') {
    if (target === 'document' ? editor?.dirty : formDirty) { discardTrigger.current = document.activeElement as HTMLElement; setDiscard(target); }
    else closeDraft(target);
  }
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
  function enterProject(row: Row, nextTab: ViewKind) {
    setLinkedPage(null);
    if (row.project_id !== project?.project_id) {
      repositoryGeneration.current++;
      setRepository(null);
      setWorkFiltersOpen(false); setWorkFilters(initialWorkFilters);
    } else if (row.project_id) void loadRepository(row.project_id);
    setShowRepository(false);setWorkspaceView(null);
    clearCodeSelection();
    setWork(null); setForm(''); setTargets([]); setConfirmation(null); setCurrentVersion(null); setProject(row); setContainer(null); setEditor(null); setRows([]); setContainers([]); setTab(nextTab); setCursor('');
    reloadScope();
  }
  async function openProject(row: Row) {
    if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft before switching projects.'); return; }
    syncResourceAddress({kind:'project',project:row.project_id!,view:'overview'});
    enterProject(row, 'project');
  }
  function rememberNavigation() {
    if (project?.project_id && tab === 'work') navigationMemory.current.set({kind:'work',project:project.project_id},
      {filters:workFilters,scroll:window.scrollY,selection:work?.resource_id??navigationMemory.current.get({kind:'work',project:project.project_id})?.selection});
    if(workspaceView)navigationMemory.current.set({kind:'workspace',view:workspaceView},
      {filters:{title:workspaceSearch.term,status:'',assignee:''},scroll:window.scrollY,selection:navigationMemory.current.get({kind:'workspace',view:workspaceView})?.selection});
  }
  function syncResourceAddress(route?: ProductRoute, replace = false) {
    rememberNavigation();
    pendingNavigation.current=null;
    const hash=route?encodeProductRoute(route):'';
    if (!hash && !decodeProductRoute(location.hash)) return;
    lastAddress.current=hash;
    if(hash!==location.hash)history[replace?'replaceState':'pushState'](null,'',location.pathname+hash);
  }
  function syncWorkAddress(projectId?: string, item?: string, replace = false) {
    syncResourceAddress(projectId ? {kind:'work',project:projectId,item} : undefined,replace);
  }
  function enterWorkspace(view:'my-work'|'search'|null) {
    pendingDocumentFocus.current=null;
    activeQuery.current++;repositoryGeneration.current++;pendingNavigation.current=null;displayedSnapshot.current=null;
    setProject(null);setWorkspaceView(view);setRepository(null);setShowRepository(false);clearCodeSelection();setLoading(false);
    setRows([]);setContainers([]);setContainer(null);setWork(null);setEditor(null);setLinkedPage(null);
    setCurrentVersion(null);setConfirmation(null);setCursor('');setTab('project');
  }
  function openWorkspace(view:'my-work'|'search') {
    if(busy||editor?.dirty||pending||form){setError('Finish or discard the current draft before navigating.');return;}
    syncResourceAddress({kind:'workspace',view});enterWorkspace(view);
  }
  async function openWorkspaceResource(row:Row) {
    if(busy||pending||form||editor?.dirty)return;
    const route:ProductRoute=row.kind==='work'?{kind:'work',project:row.project_id!,item:row.resource_id!}
      :{kind:'doc',project:row.project_id!,collection:row.container_id!,document:row.resource_id!};
    const available=await client.query(blankQuery('projects'));
    if(available.cursor)throw new HomeError('unsupported_version');
    const allowed=Object.values(available.rows);
    if(!allowed.some(project=>project.project_id===row.project_id))throw new HomeError('denied_or_not_found');
    setProjects(allowed);
    syncResourceAddress(route);
    if(workspaceView){
      const previous=navigationMemory.current.get({kind:'workspace',view:workspaceView});
      if(previous)navigationMemory.current.set({kind:'workspace',view:workspaceView},{...previous,selection:encodeProductRoute(route)});
    }
    await restoreProductAddress(route,allowed);
  }
  async function restoreProductAddress(address: ProductRoute, allowed=projects) {
    pendingNavigation.current=null;
    if(address.kind==='work')return restoreWorkAddress({project:address.project,item:address.item},allowed);
    if(address.kind==='workspace') {
      if(address.view==='inbox'){setError('This Home does not yet support an actionable Inbox.');return;}
      enterWorkspace(address.view);return;
    }
    const requestedHash=location.hash;
    const row=allowed.find(item=>item.project_id===address.project);
    if(!row){setError('This link is unavailable or you do not have access.');return;}
    if(address.kind==='project') {
      const kind=({overview:'project',work:'work',docs:'documents',code:'project'} as const)[address.view];
      enterProject(row,kind);
      if(address.view==='code')setShowRepository(true);
      return;
    }
    if(address.kind==='doc'||address.kind==='collection') {
      const boxes=await collections(address.project);
      const selected=boxes.find(box=>box.container_id===address.collection);
      if(!selected){setError('This page is unavailable or you do not have access.');return;}
      if(location.hash!==requestedHash)return;
      if(address.kind==='collection'){enterProject(row,'documents');setContainers(boxes);setContainer(selected);return;}
      const view=await client.query(blankQuery('document',address.project,address.collection,address.document));
      const page=Object.values(view.rows).find(item=>item.resource_id===address.document && item.container_id===address.collection);
      if(location.hash!==requestedHash)return;
      if(typeof page?.markdown!=='string'||!page.resource_revision){setError('This page is unavailable or you do not have access.');return;}
      if(address.revision&&address.revision!==page.resource_revision){setError('This exact page revision is not available through the current Home interface.');return;}
      enterProject(row,'documents');setContainers(boxes);setContainer(selected);
      setEditor({id:address.document,revision:page.resource_revision,head:page.container_head??'',text:page.markdown,dirty:false});
      pendingDocumentFocus.current={project:address.project,collection:address.collection,document:address.document,
        session:routedIdentity.current ?? identity?.session_audit_id ?? '',hash:location.hash};return;
    }
    setError('This resource view is not supported by the current Home interface.');
  }
  async function readWorkItem(projectId: string, itemId: string) {
    const view = await client.query(blankQuery('work', projectId, '', itemId));
    const items = Object.values(view.rows);
    const item = items[0];
    if (items.length !== 1 || item?.resource_id !== itemId || item.kind !== 'work') throw new HomeError('denied_or_not_found');
    return item;
  }
  async function restoreWorkAddress(address: WorkAddress, allowed = projects) {
    const requestedHash = location.hash;
    const row = allowed.find(item => item.project_id === address.project);
    if (!row) { setError('This work link is unavailable or you do not have access.'); return; }
    let item: Row | null = null;
    let unavailable = false;
    if (address.item) {
      try { item = await readWorkItem(address.project, address.item); }
      catch (failure) {
        if (!(failure instanceof HomeError) || failure.code !== 'denied_or_not_found') throw failure;
        unavailable = true;
      }
    }
    if (location.hash !== requestedHash) return;
    if (project?.project_id !== row.project_id || tab !== 'work') enterProject(row, 'work');
    else { setShowRepository(false); clearCodeSelection(); }
    const remembered=navigationMemory.current.get({kind:'work',project:address.project});
    if(remembered){setWorkFilters(remembered.filters);setWorkFiltersOpen(!!(remembered.filters.title||remembered.filters.status||remembered.filters.assignee));
      pendingNavigation.current={project:address.project,scroll:remembered.scroll,...(!address.item&&remembered.selection?{focus:remembered.selection}:{})};}
    const previousItem = work?.resource_id;
    if (!item && previousItem && UUID.test(previousItem)) requestAnimationFrame(() =>
      document.querySelector<HTMLElement>(`[data-work-row="${previousItem}"] .work-title`)?.focus());
    workTrigger.current = null;
    setWork(item); setForm(''); setWorkMenu(null); setCurrentVersion(null); setConfirmation(null);
    if (unavailable) setError('This work link is unavailable or you do not have access.');
  }
  useEffect(() => {
    if (!identity) return;
    function restore() {
      const address = decodeProductRoute(location.hash);
      if (!address && !lastAddress.current) return;
      if (lastAddress.current === location.hash) return;
      if (actionBusy.current || editor?.dirty || pending || form) {
        history.pushState(null, '', location.pathname + lastAddress.current);
        setError('Finish or discard the current draft before navigating.');
        return;
      }
      rememberNavigation();
      lastAddress.current = address ? location.hash : '';
      if (address) void action(() => restoreProductAddress(address), explainConnection);
      else {
        enterWorkspace(null);
        if(location.hash)setError('This link is unavailable. Choose a project to continue.');
      }
    }
    window.addEventListener('popstate', restore);
    window.addEventListener('hashchange', restore);
    return () => { window.removeEventListener('popstate', restore); window.removeEventListener('hashchange', restore); };
  });
  async function copyWorkLink(row: Row) {
    if (!project?.project_id || !UUID.test(row.resource_id ?? '')) return;
    try {
      await navigator.clipboard.writeText(workAddress(project.project_id, row.resource_id).href);
      setNotice('Work item link copied.');
    } catch { setError('This browser could not copy the link. Open the item and copy its address.'); }
  }
  function selectProjectTab(kind: ViewKind) {
    if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft first.'); return; }
    if(project?.project_id) {
      if(kind==='work')syncWorkAddress(project.project_id);
      else if(kind==='project'||kind==='documents')syncResourceAddress({kind:'project',project:project.project_id,view:kind==='project'?'overview':'docs'});
      else syncResourceAddress();
    }
    setLinkedPage(null);
    activeQuery.current++; setShowRepository(false); clearCodeSelection(); setEditor(null); setWork(null); setCurrentVersion(null);
    setConfirmation(null); setForm(''); setTab(kind); setRows([]); setCursor(''); reloadScope();
  }
  function clearCodeSelection() { setSelectedReview(undefined); setInlineReview(undefined); setDevelopment(undefined); }
  function openLinkedReview(proposalId: string) {
    if (!UUID.test(proposalId) || workActionsLocked) return;
    syncWorkAddress(); clearCodeSelection(); setSelectedReview(proposalId); setShowRepository(true);
  }
  function openDevelopment(target: CodeDevelopmentTarget) {
    if (workActionsLocked || target.workId !== work?.resource_id) return;
    syncWorkAddress(); clearCodeSelection(); setDevelopment(target); setShowRepository(true);
  }
  function openInlineReview(key: CodeReviewKey) {
    if (workActionsLocked) return;
    syncWorkAddress(); clearCodeSelection(); setInlineReview(key); setShowRepository(true);
  }
  function updateCommentDraft(body: string) {
    setCommentDrafts(drafts => {
      const next = {...drafts};
      if (body) next[workScope] = body;
      else delete next[workScope];
      return next;
    });
  }
  function submitComment(body: string) {
    if (!project?.project_id || !project.authority_epoch || !work?.resource_id || !canEdit || workActionsLocked) return;
    const {project_id, authority_epoch} = project;
    const item = work.resource_id;
    void action(async () => {
      const latest = await readWorkItem(project_id, item);
      await save(command(project_id, item, latest.resource_revision!, authority_epoch, 'work.comment', {body}));
    });
  }
  function openLinkedWork(item: string) {
    const projectId = project?.project_id;
    if (!projectId || !UUID.test(item) || workActionsLocked) return;
    syncWorkAddress(projectId, item);
    void action(() => restoreWorkAddress({project: projectId, item}), explainConnection);
  }
  function openWorkDocument(collection: string, document: string) {
    if (!project?.project_id || !work?.resource_id || workActionsLocked || !UUID.test(collection) || !UUID.test(document)) return;
    const workOrigin = {project: project.project_id, item: work.resource_id};
    void action(async () => {
      const generation = ++activeQuery.current;
      const boxes = await collections(workOrigin.project);
      const selected = boxes.find(box => box.container_id === collection);
      if (!selected) { setError('This linked page is no longer available.'); return; }
      let view;
      try { view = await client.query(blankQuery('document', workOrigin.project, collection, document)); }
      catch (failure) {
        if (failure instanceof HomeError && failure.code === 'denied_or_not_found') { setError('This linked page is no longer available.'); return; }
        throw failure;
      }
      if (generation !== activeQuery.current) return;
      const page = Object.values(view.rows).find(row => row.resource_id === document && row.container_id === collection);
      if (typeof page?.markdown !== 'string' || !page.resource_revision) { setError('This linked page is no longer available.'); return; }
      syncResourceAddress({kind:'doc',project:workOrigin.project,collection,document}); setWork(null); setCurrentVersion(null); setConfirmation(null);
      setTab('documents'); setContainers(boxes); setContainer(selected); setRows([]); setCursor('');
      setLinkedPage({origin: workOrigin, collection, document});
      setEditor({id: document, revision: page.resource_revision, head: page.container_head ?? '', text: page.markdown, dirty: false});
      reloadScope();
      pendingDocumentFocus.current={project:workOrigin.project,collection,document,
        session:routedIdentity.current ?? identity?.session_audit_id ?? '',hash:location.hash};
    }, explainConnection);
  }
  function backToWorkFromDocument() {
    if (!linkedPageOrigin || linkedPageOrigin.project !== project?.project_id || workActionsLocked) return;
    const origin = linkedPageOrigin;
    syncWorkAddress(origin.project, origin.item);
    void action(() => restoreWorkAddress(origin), explainConnection);
  }
  function createWorkContext(payload: Fields) {
    if (!project?.project_id || !project.authority_epoch || !work || !canEdit || workActionsLocked) return;
    void action(() => save(command(project.project_id!, newId(), '0', project.authority_epoch!, 'relation.create', payload)));
  }
  function removeWorkContext(row: Row) {
    if (!project?.project_id || !project.authority_epoch || !work || !canEdit || workActionsLocked || !row.resource_id || !row.resource_revision) return;
    setConfirmation({label: 'this link', command: command(project.project_id, row.resource_id, row.resource_revision, project.authority_epoch, 'relation.delete', {})});
  }
  async function completed(value: Command, receipt: Fields) {
    const refreshDetail = work?.resource_id === value.resource_id && ['work.update', 'work.assign', 'work.comment'].includes(value.operation);
    const refreshContext = !!work && ['relation.create', 'relation.delete'].includes(value.operation);
    setPending(null);
    if (value.operation === 'work.comment') {
      if (commentDraft === value.payload.body) updateCommentDraft('');
      setNotice('Comment posted.');
      if (refreshDetail && work) setWork({...work, resource_revision: receipt.resource_revision!});
    }
    if (value.operation === 'document.save' && editor?.id === value.resource_id) {
      setEditor({ ...editor, revision: receipt.resource_revision!, head: receipt.git_commit_oid ?? '', dirty: false });
      syncResourceAddress({kind:'doc',project:value.project_id,collection:value.payload.container_id!,document:value.resource_id},true);
    }
    setForm(''); setEditWorkField(null); setFormDirty(false); setDiscard(null); if (!refreshDetail && !refreshContext) setWork(null); setConfirmation(null); setCurrentVersion(null);
    if (value.operation === 'document.delete') {
      syncResourceAddress({kind:'collection',project:value.project_id,collection:value.payload.container_id!},true);
      setEditor(null); setLinkedPage(null);
    }
    if (value.operation === 'work.delete' && work?.resource_id === value.resource_id) syncWorkAddress(value.project_id, undefined, true);
    if (refreshContext) {
      setWorkContextRevision(value => value + 1);
      setNotice(value.operation === 'relation.create' ? 'Link added.' : 'Link removed.');
      return;
    }
    if (value.operation === 'project.create') await identify();
    else if (value.operation === 'container.create' && project) setContainers(await collections(project.project_id!));
    else if (project) await refresh();
    if (refreshDetail) {
      const generation = activeQuery.current;
      const view = await client.query(blankQuery('work', value.project_id, '', value.resource_id));
      if (generation === activeQuery.current) setWork(Object.values(view.rows)[0] ?? null);
    }
    if (value.operation === 'relation.create') setNotice('Link added.');
    else if (value.operation === 'relation.delete') setNotice('Link removed.');
    else if (value.operation !== 'work.comment') setNotice(`Saved at home · revision ${receipt.resource_revision}`);
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
    if (typeof page?.markdown !== 'string' || !page.resource_revision) throw new HomeError('invalid_response');
    setCurrentVersion(null);
    setLinkedPage(null);
    syncResourceAddress({kind:'doc',project:project.project_id!,collection:container.container_id!,document:row.resource_id!});
    setEditor({ id: row.resource_id!, revision: page.resource_revision, head: page.container_head ?? '', text: page.markdown, dirty: false });
    pendingDocumentFocus.current={project:project.project_id!,collection:container.container_id!,document:row.resource_id!,
      session:routedIdentity.current ?? identity?.session_audit_id ?? '',hash:location.hash};
  }
  async function openWork(row: Row, trigger: HTMLElement) {
    if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft first.'); return; }
    if (!project) return; const generation = ++activeQuery.current;
    const item = await readWorkItem(project.project_id!, row.resource_id!);
    if (generation !== activeQuery.current) return;
    syncWorkAddress(project.project_id!, item.resource_id);
    workTrigger.current = trigger;
    setWork(item); setForm(''); setCurrentVersion(null); setConfirmation(null);
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
  const workActionsLocked = busy || !!pending || !!form || !!editor?.dirty;
  function startNewWork() {
    if (workActionsLocked || !canEdit) return;
    workTrigger.current = newWorkButton.current;
    setWork(null); setEditWorkField(null); setWorkRoster({status: 'loading'}); setCurrentVersion(null); setConfirmation(null); setForm('work');
  }
  function startEditingWork(field: 'title' | 'description' | null) {
    if (workActionsLocked || !canEdit || !work) return;
    setEditWorkField(field); setForm('work');
  }
  function toggleWorkFilters() {
    if (workActionsLocked) return;
    setWorkFiltersOpen(!workFiltersOpen);
    if (workFiltersOpen) setWorkFilters(initialWorkFilters);
    setRows([]); setCursor('');
    reloadScope();
  }
  useEffect(() => {
    if (tab !== 'work' || showRepository || workActionsLocked || workMenu || !canEdit) return;
    function shortcut(event: KeyboardEvent) {
      if (event.defaultPrevented || event.repeat || event.isComposing || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey
        || event.key.toLowerCase() !== 'c' || !(event.target instanceof HTMLElement)
        || event.target.closest('input,textarea,select,[contenteditable],summary,[role="dialog"]')) return;
      event.preventDefault();
      startNewWork();
    }
    document.addEventListener('keydown', shortcut);
    return () => document.removeEventListener('keydown', shortcut);
  }, [tab, showRepository, workActionsLocked, workMenu, canEdit]);
  function showWorkMenu(row: Row, view: WorkMenu['view'], trigger: HTMLElement, point?: {x: number; y: number}) {
    if (workActionsLocked || !project || (view !== 'actions' && !canEdit)) return;
    const rect = trigger.getBoundingClientRect();
    setWorkMenu(previous => !point && previous?.trigger === trigger && previous.view === view ? null :
      {row, view, trigger, x: Math.max(8, point?.x ?? rect.left), y: Math.max(8, point?.y ?? rect.bottom + 4)});
  }
  function closeWorkMenu(restoreFocus = true) {
    if (restoreFocus) workMenu?.trigger.focus();
    setWorkMenu(null);
  }
  async function loadAssignees(projectId: string) {
    const found: Row[] = [];
    const cursors = new Set<string>();
    let next = '';
    do {
      if (cursors.has(next) || cursors.size >= 8) throw new HomeError('invalid_response');
      cursors.add(next);
      const view = await client.query(blankQuery('assignees', projectId, '', '', '', next));
      for (const row of Object.values(view.rows)) {
        if (!UUID.test(row.principal_id ?? '') || !row.display_name || found.some(person => person.principal_id === row.principal_id)) throw new HomeError('invalid_response');
        found.push(row);
      }
      next = view.cursor;
    } while (next);
    return found;
  }
  useEffect(() => {
    const projectId = project?.project_id;
    if (form !== 'work' || work || !projectId || !canEdit) return;
    let active = true;
    setWorkRoster({status: 'loading'});
    void loadAssignees(projectId).then(rows => {
      if (active) setWorkRoster({status: 'ready', rows});
    }, () => {
      if (active) setWorkRoster({status: 'unavailable'});
    });
    return () => { active = false; };
  }, [form, work?.resource_id, project?.project_id, project?.authority_epoch, identity?.session_audit_id, canEdit, workRosterRetry]);
  async function updateWorkProperty(row: Row, property: WorkProperty, value: string) {
    if (!project || !canEdit || !row.resource_id || !row.resource_revision) return;
    const { resource_id: id, resource_revision: revision } = row;
    const projectId = project.project_id!;
    const epoch = project.authority_epoch!;
    if (property === 'assignee') {
      if ((row.assignee_principal_id ?? '') !== value) await save(command(projectId, id, revision, epoch, 'work.assign', {assignee_principal_id: value}));
      return;
    }
    if ((row[property] ?? 'none') === value) return;
    const view = await client.query(blankQuery('work', projectId, '', id));
    const current = Object.values(view.rows)[0];
    if (!current || current.resource_id !== id) throw new HomeError('denied_or_not_found');
    if (current.resource_revision !== revision) throw new HomeError('revision_conflict');
    await save(command(projectId, id, revision, epoch, 'work.update', {
      title: current.title!, description: current.description ?? '', type: current.type!, status: current.status!, priority: current.priority!, [property]: value,
    }));
  }
  function workProperty(row: Row, property: WorkProperty, title: string, surface = 'list') {
    const value = row[property] ?? '';
    const label = property === 'assignee' ? assigneeName(row) : property === 'status' ? workStatuses.get(value) ?? (value || 'No status') : value === 'none' || !value ? 'No priority' : value;
    const marker = property === 'status' ? <span className="status-marker" data-status={value} aria-hidden="true"/>
      : property === 'assignee' ? <span className="work-person-mark" aria-hidden="true">{row.assignee_display_name?.trim().charAt(0).toUpperCase() || '–'}</span> : null;
    const text = <span className="work-property-label">{label}</span>;
    const className = `work-property work-${property}`;
    if (!canEdit) return <span className={className} title={label}>{marker}{text}</span>;
    return <button type="button" className={className} disabled={workActionsLocked} title={label} data-work-control={property} data-work-surface={surface}
      aria-haspopup="dialog" aria-expanded={workMenu?.trigger.dataset.workSurface === surface
        && workMenu.row.resource_id === row.resource_id && workMenu.view === property}
      aria-label={`${property === 'assignee' ? 'Change assignee' : `Set ${property}`} for ${title}: ${label}`}
      onClick={event => showWorkMenu(row, property, event.currentTarget)}>{marker}{text}</button>;
  }
  function confirmWorkRemoval(row: Row) {
    if (!project || !canEdit) return;
    setConfirmation({label: 'this work item', command: command(project.project_id!, row.resource_id!, row.resource_revision!, project.authority_epoch!, 'work.delete', {})});
  }
  function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (form === 'publish' && (!editor || editor.dirty)) { setError('Save the page before choosing its publication destination.'); return; }
    if (!identity || (form === 'work' && !canEdit)) return;
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
      if (form === 'work') {
        const payload: Fields = {title: text('title'), description: text('description'), type: text('type'), status: text('status'), priority: text('priority')};
        const assignee = work ? '' : text('assignee');
        if (assignee) {
          if (workRoster.status !== 'ready' || !workRoster.rows.some(row => row.principal_id === assignee)) {
            setError('Choose a project member again before creating this item.'); return;
          }
          payload.assignee_principal_id = assignee;
        }
        next = command(project.project_id!, id, work?.resource_revision ?? '0', project.authority_epoch!, work ? 'work.update' : 'work.create', payload);
      }
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
  function resourceRow(row: Row, index: number) {
    const event=row.kind==='activity'?eventPresentation(row,identity?.principal_id):null;
    const inWork = tab === 'work';
    const documentTitle = row.kind === 'document' ? row.title?.split('\n', 1)[0] : undefined;
    const title = event?.summary || documentTitle?.replace(/^#{1,6} +/u, '') || row.title || row.summary || 'Untitled resource';
    const snippet = documentTitle && row.snippet?.startsWith(documentTitle)
      ? row.snippet.slice(documentTitle.length).trimStart()
      : row.snippet;
    const locked = busy || !!pending || !!form || !!editor?.dirty;
    const key = row.request_id ? `event/${row.request_id}`
      : `${row.kind ?? tab}/${row.project_id ?? project?.project_id}/${row.container_id ?? ''}/${row.resource_id ?? index}`;
    return <Surface key={key} className={inWork ? 'resource-row work-row' : 'resource-row'} data-work-row={inWork ? row.resource_id : undefined}
      data-selected={inWork && !!work && row.resource_id === work.resource_id}
      onContextMenu={inWork ? event => {
        if (locked) return;
        event.preventDefault();
        const trigger = event.currentTarget.querySelector<HTMLElement>('.work-title');
        if (trigger) showWorkMenu(row, 'actions', trigger, {x: event.clientX, y: event.clientY});
      } : undefined}
      onKeyDown={inWork ? event => {
        if (locked || event.defaultPrevented || event.repeat || event.nativeEvent.isComposing || event.altKey || event.ctrlKey || event.metaKey) return;
        const trigger = event.target instanceof HTMLElement ? event.target : event.currentTarget;
        if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) {
          event.preventDefault();
          showWorkMenu(row, 'actions', trigger);
        } else if (canEdit && !event.shiftKey && trigger.matches('button')) {
          const property = workShortcuts.get(event.key.toLowerCase());
          if (!property) return;
          event.preventDefault();
          showWorkMenu(row, property, trigger);
        }
      } : undefined}>
      <div className="resource-summary">
        {!inWork && <span className="row-kind">{row.kind === 'document' ? 'Page' : row.kind ?? row.type ?? tab}</span>}
        <h2>{inWork ? <button className="work-title" data-work-control="title" disabled={locked} aria-expanded={work?.resource_id === row.resource_id} aria-controls="work-detail-panel" aria-keyshortcuts={canEdit ? 'S A P Shift+F10' : 'Shift+F10'} onClick={event => { const trigger = event.currentTarget; void action(() => openWork(row, trigger), explainConnection); }}>{title}</button> : title}</h2>
        {!inWork && row.description && <p>{row.description}</p>}
        {!inWork && snippet && snippet !== row.description && <p>{snippet}</p>}
        {!inWork && row.status && <span className="muted">{row.status}</span>}
        {event && <><p className="muted" data-event-request={row.request_id}><AcceptedTime milliseconds={event.acceptedAt}/></p>
          <details><summary>Details</summary><dl>{event.details.map(detail=><div key={detail.label}><dt>{detail.label}</dt><dd>{detail.value}</dd></div>)}</dl></details></>}
      </div>
      {inWork && <div className="work-properties">
        {workProperty(row, 'status', title ?? 'work item')}
        {workProperty(row, 'priority', title ?? 'work item')}
        {workProperty(row, 'assignee', title ?? 'work item')}
      </div>}
      <div className="actions row-actions">
        {tab === 'documents' && <Button disabled={locked} onClick={() => void action(() => openDocument(row), explainConnection)}>Open page</Button>}
        {inWork && <button type="button" className="work-property work-overflow" data-work-control="actions" aria-label={`Actions for ${title}`} aria-haspopup="dialog" disabled={locked}
          onClick={event => showWorkMenu(row, 'actions', event.currentTarget)}><span aria-hidden="true">•••</span></button>}
        {canEdit && project && tab === 'relations' && <ActionMenu label={`Actions for ${title}`} disabled={locked}><Button variant="quiet" disabled={locked} onClick={() => setConfirmation({
          label: 'this link',
          command: command(project.project_id!, row.resource_id!, row.resource_revision!, project.authority_epoch!, 'relation.delete', {}),
        })}>Delete</Button></ActionMenu>}
      </div>
    </Surface>;
  }

  const titleTerm = workFilters.title.trim().toLocaleLowerCase();
  const activeRows = tab !== 'work' || !workFiltersOpen ? rows : rows.filter(row =>
    (!titleTerm || row.title?.toLocaleLowerCase().includes(titleTerm))
    && (!workFilters.status || row.status === workFilters.status)
    && (!workFilters.assignee || (workFilters.assignee === 'unassigned' ? !row.assignee_principal_id
      : row.assignee_principal_id === (workFilters.assignee === 'mine' ? identity?.principal_id : workFilters.assignee))));
  const workPeople = new Map(rows.filter(row => row.assignee_principal_id && row.assignee_display_name)
    .map(row => [row.assignee_principal_id!, row.assignee_display_name!]));
  const workGroups = new Map<string, Row[]>();
  if (tab === 'work') {
    for (const row of activeRows) {
      const status = row.status || 'No status';
      const group = workGroups.get(status);
      if (group) group.push(row);
      else workGroups.set(status, [row]);
    }
  }
  const visibleRows = loading ? <LoadingState label="Loading authorized view"/>
    : tab === 'work' && workFiltersOpen && activeRows.length === 0 && rows.length > 0
      ? <EmptyState title="No work matches these filters" description="Clear one or more filters to see more work."/>
    : activeRows.length === 0 ? <EmptyState title={tab === 'documents' && !container ? 'Choose a collection' : 'Nothing here yet'} description={
      tab === 'documents' ? 'Private drafts stay private until you explicitly publish a page.' : 'This view contains only resources you are allowed to access.'
    }/>
    : tab === 'work' ? <div className="work-groups">{[...new Set([...workStatuses.keys(), ...workGroups.keys()])].map(status => {
      const group = workGroups.get(status);
      if (!group) return null;
      const label = workStatuses.get(status) ?? status;
      return <section className="work-group" key={status} aria-label={label}>
        <div className="work-group-heading">
          <span className="status-marker" data-status={status} aria-hidden="true"/>
          <h3>{label}</h3>
          <span className="group-count" aria-label={`${group.length} items shown`}>{group.length}</span>
        </div>
        {group.map(resourceRow)}
      </section>;
    })}</div> : <div className="rows">{rows.map(resourceRow)}</div>;
  const workPanelOpen = tab === 'work' && (form === 'work' || !!work);
  const formPanel = form && <Surface id={workPanelOpen ? "work-detail-panel" : undefined} className={workPanelOpen ? "creation work-detail" : "creation"} aria-labelledby="form-title"><h2 id="form-title" ref={workPanelOpen ? workEditorHeading : undefined} tabIndex={workPanelOpen ? -1 : undefined}>{form === 'project' ? 'Create a general project' : form === 'container' ? 'Create a collection' : form === 'relation' ? 'Link two resources' : form === 'publish' ? 'Publish a selected page' : work ? 'Edit work item' : 'Create work item'}</h2><form key={form + (work?.resource_id ?? '')} onSubmit={submitForm} onChange={() => setFormDirty(true)}><fieldset disabled={busy || !!pending}>
            {form !== 'relation' && form !== 'publish' && <TextField ref={form === 'work' ? workTitle : undefined} label="Title" name="title" readOnly={form === 'work' && !canEdit} defaultValue={form === 'work' ? work?.title ?? '' : ''} maxLength={200} required/>}
            {form === 'project' && <TextField label="Project key" description="A short uppercase key, such as GARDEN." name="project_key" pattern="[A-Z][A-Z0-9]{1,9}" maxLength={10} required/>}
            {form === 'container' && <label>Visibility<select name="visibility" aria-label="Visibility"><option value="private">Private drafts · only you</option>{project?.role === 'maintainer' && <option value="shared">Shared with project members</option>}</select></label>}
            {form === 'work' && <>
              <label>Description<textarea ref={workDescription} name="description" readOnly={!canEdit} defaultValue={work?.description ?? ''} maxLength={8192}/></label>
              <div className="form-columns">
                <label>Type<select aria-label="Type" name="type" disabled={!canEdit} defaultValue={work?.type ?? newWorkDefaults.type}>{['deliverable','task','problem'].map(value => <option key={value} value={value}>{value[0]?.toUpperCase()}{value.slice(1)}</option>)}</select></label>
                <label>Status<select aria-label="Status" name="status" disabled={!canEdit} defaultValue={work?.status ?? newWorkDefaults.status}>{[...workStatuses].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                <label>Priority<select aria-label="Priority" name="priority" disabled={!canEdit} defaultValue={work?.priority ?? newWorkDefaults.priority}>{['none','low','medium','high','urgent'].map(value => <option key={value} value={value}>{priorityLabel(value)}</option>)}</select></label>
              </div>
              {!work && <><label>Assignee<select name="assignee" disabled={workRoster.status !== 'ready'}>
                <option value="">Unassigned</option>{workRoster.status === 'ready' && workRoster.rows.map(row =>
                  <option key={row.principal_id} value={row.principal_id}>{row.display_name}{row.principal_id === identity?.principal_id ? ' (you)' : ''} · {row.identity_ship}</option>)}
              </select></label>
                {workRoster.status === 'loading' && <p className="muted" role="status">Loading project members…</p>}
                {workRoster.status === 'unavailable' && <div className="work-roster-error"><span role="status">Project members could not be loaded.</span>
                  <Button variant="quiet" onClick={() => setWorkRosterRetry(value => value + 1)}>Retry members</Button></div>}
              </>}
            </>}
            {form === 'publish' && <><p>Publish saved revision {editor?.revision} of page {editor?.id}. Its source is locked while you choose a destination. Copy this saved page into a shared collection. The original and other drafts stay private. Only the selected body is published.</p><label>Destination collection<select name="destination" aria-label="Destination collection" required><option value="">Choose a shared collection</option>{containers.filter(row => row.visibility === 'shared').map(row => <option key={row.container_id} value={row.container_id}>{row.title}</option>)}</select></label></>}
            {form === 'relation' && <><div className="search"><TextField label="Find resources to link" value={targetFilter} onChange={event => setTargetFilter(event.target.value)} maxLength={128}/><Button disabled={busy} onClick={() => void action(() => findTargets())}>Find resources</Button></div><label>Link type<select name="relation_type" aria-label="Link type"><option value="related_to">Related to</option><option value="blocks">Blocks · work to work</option><option value="documents">Documents · page to work</option></select></label>{['source','target'].map(side => <label key={side}>{side === 'source' ? 'From resource' : 'To resource'}<select name={side} aria-label={side === 'source' ? 'From resource' : 'To resource'} required><option value="">Choose an authorized resource</option>{targets.map(row => { const key = `${row.kind}/${row.container_id}/${row.resource_id}`; return <option key={key} value={key}>{row.title} · {row.kind}</option>; })}</select></label>)}</>}

            <div className="actions"><Button type="submit" variant="primary" pending={busy} disabled={!!pending || (form === 'work' && !canEdit)}>Save at home</Button><Button disabled={busy || !!pending} onClick={() => requestClose('form')}>{formDirty ? 'Discard changes…' : 'Close'}</Button>{workPanelOpen && work && <ActionMenu label="More work actions" disabled={busy || !!pending}><Button variant="quiet" disabled={busy || !!pending} onClick={() => void action(loadCurrentVersion)}>Compare current saved revision</Button></ActionMenu>}</div>
          </fieldset></form></Surface>;

  const brand = <><span className="brand-mark" aria-hidden="true">s</span><span>stead</span></>;
  const canReconnect = ['outcome_unknown', 'invalid_csrf', 'resume_required', 'refresh_required', 'updates_unavailable'].includes(diagnostic);
  return <div className={identity ? 'app-shell signed-in' : 'app-shell entry-shell'}>
    <header className="topbar">{project ? <button className="brand" aria-label="Stead home" type="button" disabled={busy}
      onClick={() => void action(() => openProject(project), explainConnection)}>{brand}</button> : <span className="brand">{brand}</span>}
      {identity && <><span className="alpha">Team alpha</span><div className="account"><span className="member-label"><span className="member-name">{identity.display_name}</span><small title={identity.identity_ship}>{identity.identity_ship}</small></span><Button variant="quiet" disabled={busy} onClick={() => void action(() => client.logout())}>Sign out</Button></div></>}</header>
    {!online && <div className="banner" role="status">You’re offline. Drafts stay in this tab; nothing is saved until the home confirms it.</div>}
    <main id="main">{identity ? <a className="skip-link" href="#project-content" onClick={event => {
      event.preventDefault(); document.getElementById('project-content')?.focus();
    }}>Skip to project content</a> : !loading && <a className="skip-link" href="#urbit-sign-in-title">Skip to sign-in</a>}
      {error && <div className="error" role="alert"><p>{error}</p>
        {canReconnect && (identity
          ? <Button disabled={busy} onClick={() => void action(async () => {
            const person = await client.resume();
            await identify(person);
            if (project && person.session_audit_id === identity.session_audit_id) reloadScope();
            setNotice(pending ? 'Session resumed. Choose whether to retry your pending request.' : 'Session resumed.');
          }, explainConnection)}>Resume this tab</Button>
          : <Button disabled={busy} onClick={() => void action(retryConnection, explainConnection)}>Retry connection</Button>)}
      </div>}
      {identity && <div className="live" role="status" aria-live="polite">{notice}</div>}
      <div className="refresh-notice stead-visually-hidden" role="status" aria-live="polite" aria-atomic="true">{refreshNotice && <span key={refreshNotice.sequence}>{refreshNotice.text}</span>}</div>
      {loading && !identity && <LoadingState label="Connecting to your home"/>}
      {!identity && !loading && <UrbitSignIn ship={ship} challenge={challenge} busy={busy} origin={location.origin} notice={notice}
        onShipChange={setShip} onBack={() => { setChallenge(null); setNotice(''); setError(''); }}
        onRequest={() => void action(async () => { setChallenge(await client.start(ship)); }, explainConnection)}
        onCheck={() => {
          if (!challenge) return;
          void action(async () => {
            const status = await client.status(challenge.challenge_id!);
            if (status.status === 'approved') {
              const person = await client.consume(challenge.challenge_id!);
              setChallenge(null);
              await identify(person);
            } else setNotice('Approval is still pending on your identity ship.');
          }, explainConnection);
        }}/>}
      {identity && <div className="workspace">
        <aside className="sidebar"><div className="space-label"><span className="space-mark" aria-hidden="true">~</span><div>Workspace{identity.home && <small>{identity.home}</small>}</div></div>{workspaceSupported&&<nav aria-label="Workspace"><button type="button" disabled={workActionsLocked} aria-current={workspaceView==='my-work'?'page':undefined} onClick={()=>openWorkspace('my-work')}>My work</button><button type="button" disabled={workActionsLocked} aria-current={workspaceView==='search'?'page':undefined} onClick={()=>openWorkspace('search')}>Search</button></nav>}<h2 className="rail-label">Projects</h2>{projects.length === 0 && <p className="muted">No projects are shared with you yet.</p>}<nav aria-label="Projects">{projects.map(row => <button disabled={busy} key={row.project_id} aria-current={project?.project_id === row.project_id ? 'page' : undefined} onClick={() => void action(() => openProject(row))}><span className="project-glyph" aria-hidden="true">◇</span><span className="project-name"><span className="project-key">{row.project_key}</span>{row.title}</span></button>)}</nav>{identity.can_create === 'yes' && <Button variant="quiet" disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => { setEditor(null); setWork(null); setCurrentVersion(null); setForm('project'); }}><Icon name="plus"/>New project</Button>}<p className="sidebar-note">Only projects explicitly shared with you appear here.</p></aside>
        <section className="content" id="project-content" data-live-updates={updatesConnected ? 'connected' : 'unavailable'}>
          {pending && <Surface className="pending"><h2>Save awaiting confirmation</h2><p>Keep this tab open. Retrying uses the same request ID and cannot create a second accepted change.</p>{pending.operation === 'project.create' && <p>Use Retry this request to confirm a new project. Receipt lookup needs access to an existing project.</p>}<div className="actions">{pending.operation !== 'project.create' && <Button disabled={busy} onClick={() => void action(checkReceipt)}>Check receipt</Button>}<Button disabled={busy} onClick={() => void action(() => save(pending))}>Retry this request</Button></div></Surface>}
          {discard && <Surface className="confirmation" role="alertdialog" aria-labelledby="discard-title" aria-describedby="discard-description"><h2 id="discard-title" ref={feedbackHeading} tabIndex={-1}>Discard unsaved changes?</h2><p id="discard-description">Your local edits will be removed. Your last saved version stays at home.</p><div className="actions"><Button variant="danger" disabled={busy || !!pending} onClick={() => closeDraft(discard)}>Discard changes</Button><Button disabled={busy} onClick={() => { setDiscard(null); discardTrigger.current?.focus(); }}>Keep editing</Button></div></Surface>}
          {workspaceView && (workspaceSupported ? <WorkspaceView key={identity.session_audit_id}
            client={client} view={workspaceView==='search'?'workspace-search':'my-work'} search={workspaceSearch}
            onSearchChange={setWorkspaceSearch} sessionKey={identity.session_audit_id!} locked={workActionsLocked}
            openingWatchRef={openingWatch} restoreNavigation={navigationMemory.current.get({kind:'workspace',view:workspaceView})}
            onOpen={row=>void action(()=>openWorkspaceResource(row),explainConnection)}
            onError={failure=>{if(failure instanceof HomeError&&failure.code==='denied_or_not_found')clearViews();setError(explainConnection(failure));}}/>
            : <EmptyState title="Workspace views need a newer Home" description="Choose a project to keep working. This Home does not advertise workspace queries."/>)}
          {!project && !workspaceView && <div className="welcome"><p className="eyebrow">START WITH WHAT MATTERS</p><h1 ref={heading} tabIndex={-1}>A clear place for your work.</h1><p>Choose a project to see its work and knowledge.</p></div>}
          {project && <><div className="project-heading"><div><p className="eyebrow">Projects <span aria-hidden="true">/</span> {project.project_key}</p><h1 ref={heading} tabIndex={-1}>{project.title}</h1></div><span className="role-badge">{project.role}</span></div>
          <nav className="tabs" aria-label="Project views">{([['project','Overview'],['work','Work'],['documents','Docs']] as const).map(([kind,label]) => <Button disabled={busy} key={kind} variant={!showRepository && tab === kind ? 'primary' : 'quiet'} aria-current={!showRepository && tab === kind ? 'page' : undefined} onClick={() => selectProjectTab(kind)}>{label}</Button>)}
          {(repository?.status === 'ready' || externalRepository) && <Button disabled={busy || !!editor?.dirty || !!pending || !!form}
            variant={showRepository ? 'primary' : 'quiet'} aria-current={showRepository ? 'page' : undefined}
            onClick={() => { syncResourceAddress({kind:'project',project:project.project_id!,view:'code'}); clearCodeSelection(); setShowRepository(true); }}>Code</Button>}</nav>
          {showRepository && repository?.status === 'ready' ? <CodeRepository key={`${identity.session_audit_id}/${project.project_id}/${project.authority_epoch}`}
            client={client} project={project.project_id!} writable={repository.write === 'yes'}
            manage={repository.manage === 'yes'} principal={identity.principal_id ?? ''}
            initialProposal={inlineReview} onOpenWork={openLinkedWork}/> :
          showRepository && externalRepository ? <CodePack key={`${identity.session_audit_id}/${project.project_id}/${project.authority_epoch}`} client={client} project={project.project_id!}
            manage={repository?.manage === 'yes'} writable={repository?.write === 'yes'} principal={identity.principal_id ?? ''}
            initialProposal={selectedReview} onOpenWork={openLinkedWork} development={development}/> : <>
          {tab === 'project' && <Surface className="project-overview"><h2>Move this project forward</h2>
            <p>{project.summary || 'Define an outcome in Work, keep its context in Docs, and review the result together.'}</p>
            <div className="actions"><Button variant="primary" disabled={workActionsLocked} onClick={() => selectProjectTab('work')}>Open work</Button>
              <Button disabled={workActionsLocked} onClick={() => selectProjectTab('documents')}>Open docs</Button></div>
            <details><summary>Project activity and relationships</summary><div className="actions">
              <Button variant="quiet" disabled={workActionsLocked} onClick={() => selectProjectTab('activity')}>Activity</Button>
              <Button variant="quiet" disabled={workActionsLocked} onClick={() => selectProjectTab('relations')}>Relationships</Button>
              <Button variant="quiet" disabled={workActionsLocked} onClick={() => selectProjectTab('search')}>Search this project</Button>
            </div></details></Surface>}
          {tab === 'project' && repository?.status === 'disabled' && repository.manage === 'yes'
            && <Button disabled={busy || !!pending || !!form} onClick={() => void action(() => loadRepository(project.project_id!, true))}>Enable Git repository</Button>}
          <div className="toolbar"><div className="view-heading">{tab === 'work' && <h2>Work items</h2>}{tab === 'documents' && <label>Collection <select aria-label="Collection" disabled={busy} value={container?.container_id ?? ''} onChange={event => { const selected = containers.find(row => row.container_id === event.target.value) ?? null; if (busy || editor?.dirty || pending || form) { setError('Finish or discard the current draft first.'); return; } activeQuery.current++; syncResourceAddress(selected?.container_id ? {kind:'collection',project:project.project_id!,collection:selected.container_id} : {kind:'project',project:project.project_id!,view:'docs'}); setContainer(selected); setEditor(null); setWork(null); setCurrentVersion(null); setConfirmation(null); setForm(''); setRows([]); setCursor(''); reloadScope(); }}><option value="">Choose a collection</option>{containers.map(row => <option key={row.container_id} value={row.container_id}>{row.title} · {row.visibility === 'private' ? 'Private drafts' : 'Shared'}</option>)}</select></label>}{tab === 'search' && <form className="search" onSubmit={submitSearch}><TextField label="Search this project" value={searchDraft} onChange={event => setSearchDraft(event.target.value)} maxLength={128}/><Button type="submit" disabled={busy}>Search</Button></form>}</div><div className="actions">
          <Button variant="quiet" disabled={busy || loading} onClick={() => {
            reloadScope();
            if (tab === 'project') void loadRepository(project.project_id!);
          }}>Refresh</Button>
          {tab === 'work' && <Button variant="quiet" disabled={workActionsLocked} aria-expanded={workFiltersOpen}
            aria-controls="work-filters" onClick={toggleWorkFilters}>Filters{workFiltersOpen && ' ▾'}</Button>}
          {canEdit && tab === 'work' && <Button ref={newWorkButton} variant="primary" disabled={workActionsLocked} aria-keyshortcuts="C" title="New work item (C)"
            onClick={startNewWork}><Icon name="plus"/>New work item</Button>}
          {canEdit && tab === 'relations' && <Button variant="primary" disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => void action(async () => { await findTargets(''); setTargetFilter(''); setForm('relation'); })}>Add link</Button>}
          {canEdit && tab === 'documents' && <><Button disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => { setEditor(null); setWork(null); setCurrentVersion(null); setForm('container'); }}>New collection</Button>{container && <Button variant="primary" disabled={busy || loading || !!pending || !!form || !!editor?.dirty} onClick={() => { activeQuery.current++; const id = newId(); setWork(null); setCurrentVersion(null); setEditor({ id, revision: '0', head: container.container_head ?? '', dirty: true, text: `---\nid: ${id}\ntype: page\nstate: ${draftMode ? 'draft' : 'published'}\n---\n# Untitled\n` }); }}>New page</Button>}</>}
          </div></div>
          {tab === 'work' && workFiltersOpen && <section className="work-filters" id="work-filters" aria-label="Work filters">
            <TextField label="Find by title" value={workFilters.title} maxLength={200} onChange={event => setWorkFilters({...workFilters, title: event.target.value})}/>
            <label>Status<select aria-label="Filter by status" value={workFilters.status} onChange={event => setWorkFilters({...workFilters, status: event.target.value})}>
              <option value="">Any status</option>{[...workStatuses].map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            <label>Assignee<select aria-label="Filter by assignee" value={workFilters.assignee} onChange={event => setWorkFilters({...workFilters, assignee: event.target.value})}>
              <option value="">Any assignee</option><option value="mine">Assigned to me</option><option value="unassigned">Unassigned</option>
              {[...workPeople].filter(([id]) => id !== identity.principal_id).sort((a, b) => a[1].localeCompare(b[1])).map(([id, name]) =>
                <option key={id} value={id}>{name}</option>)}
            </select></label>
            <Button variant="quiet" disabled={!workFilters.title && !workFilters.status && !workFilters.assignee} onClick={() => setWorkFilters(initialWorkFilters)}>Clear filters</Button>
            {!loading && <p role="status">{activeRows.length} of {rows.length} work items</p>}
          </section>}
          {currentVersion && currentVersion.scope === comparisonScope && <Surface className="comparison"><h2 ref={feedbackHeading} tabIndex={-1}>Current saved revision {currentVersion.row.resource_revision}</h2><pre>{currentVersion.row.markdown ?? `${currentVersion.row.title}\n${currentVersion.row.description}`}</pre><p>{canEdit ? 'Your local text has not changed. Choose its base revision before saving again.' : 'This is the current revision saved at home.'}</p>{canEdit && <Button disabled={busy || !!pending} onClick={() => { if (currentVersion.scope !== comparisonScope) { setCurrentVersion(null); return; } if (editor) setEditor({...editor, revision: currentVersion.row.resource_revision!, head: currentVersion.row.container_head ?? '', dirty: true}); else if (work) setWork(currentVersion.row); setCurrentVersion(null); setNotice('Local edits kept. Review them, then explicitly save against the current revision.'); }}>Keep my edits using this revision</Button>}<Button onClick={() => setCurrentVersion(null)}>Close comparison</Button></Surface>}
          {confirmation && <Surface className="confirmation"><h2 ref={feedbackHeading} tabIndex={-1}>Delete {confirmation.label}?</h2><p>{confirmation.command.operation === 'relation.delete' ? 'This removes only the relationship. Both linked resources stay where they are.' : 'This removes it from current views. Authorized historical Git exports retain earlier page versions; this does not erase copies others already hold.'}</p><div className="actions"><Button disabled={busy || !!pending || !!form || !!editor?.dirty} onClick={() => void action(() => save(confirmation.command))}>Confirm deletion</Button><Button disabled={busy} onClick={() => setConfirmation(null)}>Keep it</Button></div></Surface>}
          {editor && container ? <Surface className="document-editor">{linkedPageOrigin?.project === project.project_id && !editor.dirty && <Button variant="quiet" disabled={workActionsLocked} onClick={backToWorkFromDocument}>← Back to work item</Button>}<div className="editor-heading"><div><h2 ref={documentEditorHeading} tabIndex={-1}>{pageTitle(editor.text)}</h2><span className="page-visibility">{draftMode ? 'Private draft · only you' : 'Shared with project members'}</span></div><span>{editor.dirty ? 'Local changes · not saved' : `Saved revision ${editor.revision}`}</span></div><DocumentBody key={`${identity.session_audit_id}/${container.container_id}/${editor.id}`} text={editor.text} header={pageHeader}
            editable={!!canEdit} locked={busy || !!pending || !!form} isNew={editor.revision === '0'} fullSource={!!editor.fullSource}
            onFullSource={fullSource => setEditor({...editor,fullSource})}
            onChange={text => setEditor({...editor,text,dirty:true})}/>
          {editor.revision !== '0' && <DocumentContext
            key={`${identity.session_audit_id}/${project.project_id}/${container.container_id}/${editor.id}`}
            client={client} project={project.project_id!} collection={container.container_id!} document={editor.id}
            sessionKey={identity.session_audit_id!}
            viewRevision={`${project.authority_epoch}/${displayedSnapshot.current?.generation ?? ''}/${editor.revision}/${workContextRevision}`}
            locked={workActionsLocked || !online || !updatesConnected} onOpenWork={openLinkedWork}
            onError={failure => { if (failure instanceof HomeError && failure.code === 'denied_or_not_found') clearViews(); setError(explainConnection(failure)); }}/>}
          <div className="actions editor-actions">{canEdit && editor.dirty && <Button variant="primary" disabled={busy || !!pending || !!form} onClick={() => void action(() => save(command(project.project_id!, editor.id, editor.revision, project.authority_epoch!, 'document.save', { container_id: container.container_id!, markdown: editor.text })))}>Save page</Button>}<Button disabled={busy || !!pending || !!form} onClick={() => requestClose('document')}>{editor.dirty ? 'Discard changes…' : 'Close'}</Button>{(editor.revision !== '0' || pageHeader || editor.fullSource) && <ActionMenu label="More page actions" disabled={busy || !!pending || !!form}>
            {canEdit && !editor.dirty && editor.revision !== '0' && draftMode && <Button variant="quiet" disabled={busy || !!pending || !!form} onClick={() => void action(async () => { setContainers(await collections(project.project_id!)); setForm('publish'); })}>Publish selected page</Button>}
            {(pageHeader || editor.fullSource) && <Button variant="quiet" disabled={busy || !!pending || !!form}
              onClick={() => setEditor({ ...editor, fullSource: !editor.fullSource })}>{editor.fullSource ? 'Hide metadata' : 'Show full Markdown'}</Button>}
            {editor.revision !== '0' && <Button variant="quiet" disabled={busy || !!pending || !!form} onClick={() => void action(loadCurrentVersion)}>Compare current saved revision</Button>}
            {editor.revision !== '0' && canEdit && <Button variant="quiet" disabled={busy || !!pending || !!form || editor.dirty} onClick={() => setConfirmation({label: 'this page', command: command(project.project_id!, editor.id, editor.revision, project.authority_epoch!, 'document.delete', {container_id: container.container_id!, expected_head: editor.head})})}>Delete page</Button>}</ActionMenu>}</div></Surface> : <>
          <div className={workPanelOpen ? `work-view with-detail${form === 'work' ? ' with-composer' : ''}` : 'work-view'}>
            <div className="view-list">{tab !== 'project' && visibleRows}</div>
            {workPanelOpen && (form === 'work' ? formPanel : work && <Surface id="work-detail-panel" className="work-detail" aria-labelledby="work-detail-title">
              <div className="detail-heading"><span className="row-kind">Work item</span><Button variant="quiet" disabled={busy} onClick={() => closeDraft('form')}>Close</Button></div>
              <h2 id="work-detail-title" ref={workEditorHeading} tabIndex={-1}>{canEdit
                ? <button className="work-inline-title" title="Edit title" disabled={workActionsLocked} onClick={() => startEditingWork('title')}>{work.title}</button>
                : work.title}</h2>
              <dl className="work-metadata">
                <div><dt>Status</dt><dd>{workProperty(work, 'status', work.title ?? 'work item', 'detail')}</dd></div>
                <div><dt>Assignee</dt><dd>{workProperty(work, 'assignee', work.title ?? 'work item', 'detail')}</dd></div>
                <div><dt>Priority</dt><dd>{workProperty(work, 'priority', work.title ?? 'work item', 'detail')}</dd></div>
                <div><dt>Type</dt><dd>{work.type}</dd></div>
              </dl>
              {canEdit ? <button type="button" className="work-description work-inline-description" title="Edit description" disabled={workActionsLocked}
                onClick={() => startEditingWork('description')}>{work.description || 'Add a description'}</button>
                : <p className="work-description">{work.description || 'No description yet.'}</p>}
              {repository?.status === 'external' && work.resource_id && <WorkDevelopment key={`development/${workScope}`}
                client={client} project={project.project_id!} work={{id: work.resource_id, title: work.title ?? ''}}
                writable={repository.write === 'yes'} onOpenCode={openDevelopment}/>}
              {repository?.status === 'external' && work.resource_id && <WorkCodeLinks key={`reviews/${workScope}`}
                client={client} project={project.project_id!} work={work.resource_id} onOpenReview={openLinkedReview}/>}
              {repository?.status === 'ready' && work.resource_id && <WorkDelegations key={`delegations/${workScope}`}
                client={client} project={project.project_id!} work={work} manage={repository.manage === 'yes'}
                locked={workActionsLocked} onReview={openInlineReview}/>}
              {work.resource_id && <WorkContext key={`context/${workScope}`} client={client} project={project.project_id!} work={work.resource_id}
                writable={!!canEdit} locked={workActionsLocked} viewRevision={workContextRevision}
                onCreate={createWorkContext} onRemove={removeWorkContext} onOpenWork={openLinkedWork} onOpenDoc={openWorkDocument}/>}
              {work.resource_id && <WorkDiscussion key={`discussion/${workScope}`} client={client} project={project.project_id!} work={work.resource_id}
                revision={rows.find(row => row.resource_id === work.resource_id)?.resource_revision ?? work.resource_revision!}
                principal={identity.principal_id!} name={identity.display_name} writable={!!canEdit} locked={workActionsLocked}
                draft={commentDraft} onChange={updateCommentDraft} onSubmit={submitComment}/>}
              <div className="actions">
                {canEdit && <Button disabled={busy || !!pending} onClick={() => startEditingWork(null)}>Edit work item</Button>}
                <Button variant="quiet" disabled={busy} onClick={() => void copyWorkLink(work)}>Copy link</Button>
                <span className="muted">Revision {work.resource_revision}{!canEdit && ' · Read only'}</span>
              </div>
            </Surface>)}
          </div>
          {cursor && <Button disabled={busy || loading || !updatesConnected} onClick={() => void action(() => refresh(tab, container, cursor))}>Next page</Button>}</>}
          </>}
          </>}
          {!workPanelOpen && formPanel}
        </section>
      </div>}
    </main>
    {workMenu && project && <WorkQuickActions key={`${workMenu.row.resource_id}/${workMenu.view}/${workMenu.x}/${workMenu.y}`}
      menu={workMenu} canEdit={!!canEdit} who={identity?.principal_id} loadAssignees={() => loadAssignees(project.project_id!)}
      close={closeWorkMenu} open={() => { closeWorkMenu(false); void action(() => openWork(workMenu.row, workMenu.trigger), explainConnection); }}
      copy={() => { closeWorkMenu(); void copyWorkLink(workMenu.row); }}
      remove={() => { closeWorkMenu(false); confirmWorkRemoval(workMenu.row); }}
      change={(property, value) => {
        quickActionFocus.current = {trigger: workMenu.trigger, row: workMenu.row.resource_id!, control: workMenu.trigger.dataset.workControl ?? 'title'};
        closeWorkMenu();
        void action(() => updateWorkProperty(workMenu.row, property, value), failure =>
        failure instanceof HomeError && failure.code === 'revision_conflict'
          ? 'This item changed. Refresh it and choose the new value again.' : explain(failure)); }}/>}
    <footer><div>{identity && 'One home for work and knowledge.'}<SupportDetails code={diagnostic} requestId={pending?.request_id}/></div>{identity && <span>Local changes become shared only after the home accepts them.</span>}</footer>
  </div>;
}
const root = document.getElementById('root');
if (!root) throw new Error('Missing application root');
createRoot(root).render(<StrictMode><App/></StrictMode>);

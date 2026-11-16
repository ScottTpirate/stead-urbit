import {useEffect, useId, useRef, useState} from 'react';
import {HomeError, UUID, type HomeClient, type Query, type Row, type View} from './api';
import {Button, EmptyState, LoadingState, OutcomeState, StatusBadge} from './primitives';
import {encodeProductRoute} from './productRoutes';
import {workStatuses} from './WorkQuickActions';
import './document-context.css';
import type {ProductWorkEndpointReader} from './productJourneyState';

export interface DocumentContextProps {
  readonly client: HomeClient;
  readonly project: string;
  readonly collection: string;
  readonly document: string;
  readonly sessionKey: string;
  readonly locked: boolean;
  readonly viewRevision: string | number;
  readonly onOpenWork: (id: string) => void;
  readonly onError: (failure: unknown) => void;
  readonly readWork?: ProductWorkEndpointReader;
}
type Endpoint = {kind: 'work' | 'document'; container: string; id: string};
type Link = {id: string; group: 'support' | 'related'; title: string; status?: string};
type State = {key: string; phase: 'loading' | 'ready' | 'failed' | 'revoked' | 'offline'; links?: Link[]};
const revision = (value = '') => /^[1-9][0-9]{0,19}$/u.test(value) && BigInt(value) <= 18446744073709551615n;
const query = (kind: Query['kind'], project: string, container = '', resource = '', cursor = ''): Query =>
  ({kind, project_id: project, container_id: container, resource_id: resource, search: '', cursor});

function endpoint(kind = '', container = '', id = ''): Endpoint {
  if (!UUID.test(id) || (kind !== 'work' && kind !== 'document')
      || (kind === 'work' ? container !== '' : !UUID.test(container))) throw new HomeError('invalid_response');
  return {kind, container, id};
}
function exactRow(view: View, kind: 'work' | 'document', project: string, container: string, id: string): Row {
  const [row, extra] = Object.values(view.rows);
  if (!row || extra || view.cursor || row.kind !== kind || row.resource_id !== id || row.container_id !== container
      || (row.project_id !== undefined && row.project_id !== project) || !revision(row.resource_revision)) {
    throw new HomeError('invalid_response');
  }
  return row;
}

async function readLinks(client: HomeClient, project: string, collection: string, document: string, active: () => boolean, readWork?: ProductWorkEndpointReader): Promise<Link[]> {
  if (![project, collection, document].every(id => UUID.test(id))) throw new HomeError('invalid_request');
  // A visible relation is not a grant. Recheck the Doc and every Work endpoint;
  // never use the relation's display payload to infer a hidden endpoint's name.
  const source = await client.query(query('document', project, collection, document));
  if (!active()) return [];
  exactRow(source, 'document', project, collection, document);
  const seen = new Set<string>(), cursors = new Set<string>();
  const targets = new Map<string, 'support' | 'related'>();
  let cursor = '', generation: string | undefined;
  const isDocument = (value: Endpoint) => value.kind === 'document' && value.container === collection && value.id === document;
  for (let page = 0; page < 13 && active(); page++) {
    const result = await client.query(query('relations', project, '', '', cursor));
    if (!active()) return [];
    if (result.authority_epoch !== source.authority_epoch || (generation && generation !== result.generation)) throw new HomeError('stale_cursor');
    generation = result.generation;
    const rows = Object.values(result.rows);
    for (const row of rows) {
      const from = endpoint(row.source_kind, row.source_container_id, row.source_id);
      const to = endpoint(row.target_kind, row.target_container_id, row.target_id);
      if (row.kind !== 'relation' || !UUID.test(row.resource_id ?? '') || !revision(row.resource_revision)
          || row.source_project_id !== project || row.target_project_id !== project
          || (row.type === 'documents' ? from.kind !== 'document' || to.kind !== 'work'
            : row.type === 'blocks' ? from.kind !== 'work' || to.kind !== 'work' : row.type !== 'related_to')
          || seen.has(row.resource_id!) || seen.size >= 256) throw new HomeError('invalid_response');
      seen.add(row.resource_id!);
      const other = isDocument(from) ? to : isDocument(to) ? from : null;
      if (other?.kind !== 'work') continue;
      const group = row.type === 'documents' ? 'support' : 'related';
      if (!targets.has(other.id) || group === 'support') targets.set(other.id, group);
    }
    cursor = result.cursor;
    if (!cursor) break;
    if (rows.length !== 20 || cursors.has(cursor)) throw new HomeError('invalid_response');
    cursors.add(cursor);
  }
  if (!active()) return [];
  if (cursor) throw new HomeError('invalid_response');
  const links: Link[] = [], entries = [...targets];
  for (let start = 0; start < entries.length && active(); start += 6) {
    const batch = await Promise.all(entries.slice(start, start + 6).map(async ([id, group]) => {
      try {
        if (readWork) {
          const row = await readWork(project, id);
          if (!active()) return null;
          if (row.projectId !== project || row.workId !== id) throw new HomeError('invalid_response');
          if (row.authorityEpoch !== source.authority_epoch) throw new HomeError('stale_cursor');
          return {id, group, title: row.title.trim() || 'Untitled work', status: row.statusLabel};
        }
        const result = await client.query(query('work', project, '', id));
        if (!active()) return null;
        if (result.authority_epoch !== source.authority_epoch) throw new HomeError('stale_cursor');
        const row = exactRow(result, 'work', project, '', id);
        return {id, group, title: row.title?.trim() || 'Untitled work', status: workStatuses.get(row.status ?? '')};
      } catch (failure) {
        if (failure instanceof HomeError && failure.code === 'denied_or_not_found') return null;
        throw failure;
      }
    }));
    if (!active()) return [];
    for (const link of batch) if (link) links.push(link);
  }
  return links;
}

export function DocumentContext({client, project, collection, document, sessionKey, locked, viewRevision, onOpenWork, onError, readWork}: DocumentContextProps) {
  const region = useId();
  const key = JSON.stringify([project, collection, document, sessionKey, viewRevision, readWork ? 'product' : 'legacy']);
  const [expanded, setExpanded] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [online, setOnline] = useState(() => navigator.onLine);
  const [state, setState] = useState<State>({key, phase: 'loading'});
  const current = useRef({key, locked, online, onOpenWork, onError});
  current.current = {key, locked, online, onOpenWork, onError};
  const visible = state.key === key ? state : {key, phase: 'loading' as const};
  const links = visible.phase === 'ready' && online ? visible.links ?? [] : [];

  useEffect(() => {
    const offline = () => {
      current.current.online = false;
      setOnline(false); setState({key: current.current.key, phase: 'offline'});
    };
    const connected = () => setOnline(true);
    window.addEventListener('offline', offline); window.addEventListener('online', connected);
    return () => { window.removeEventListener('offline', offline); window.removeEventListener('online', connected); };
  }, []);

  useEffect(() => {
    if (!expanded) return;
    if (!navigator.onLine) { setState({key, phase: 'offline'}); return; }
    if (locked) return;
    let running = true;
    const active = () => running && current.current.key === key && !current.current.locked && current.current.online;
    setState({key, phase: 'loading'});
    void readLinks(client, project, collection, document, active, readWork).then(value => {
      if (active()) setState({key, phase: 'ready', links: value});
    }, failure => {
      if (!active()) return;
      const revoked = failure instanceof HomeError && ['denied_or_not_found', 'session_required', 'session_changed'].includes(failure.code);
      setState({key, phase: revoked ? 'revoked' : 'failed'});
      current.current.onError(failure);
    });
    return () => { running = false; };
  }, [client, project, collection, document, sessionKey, viewRevision, key, expanded, locked, attempt, readWork]);

  const retry = <Button variant="quiet" disabled={locked || !online} onClick={() => setAttempt(value => value + 1)}>Refresh links</Button>;
  return <section className="document-context" aria-label="Related work">
    <div className="document-context-heading"><h3>Related work</h3>
      <Button variant="quiet" aria-expanded={expanded} aria-controls={region} disabled={locked || !online}
        onClick={() => { setState({key, phase: 'loading'}); setExpanded(value => !value); }}>{expanded ? 'Hide links' : 'Show links'}</Button></div>
    <div id={region} hidden={!expanded}>{expanded && <>
      <p className="document-context-note">Links follow the latest authorized content; no revision is pinned.</p>
      {visible.phase === 'loading' && (locked ? <p role="status">Finish your current action to load related work.</p> : <LoadingState label="Loading related work"/>)}
      {visible.phase === 'offline' && <OutcomeState state="disconnected_or_stale" description={online
        ? 'The connection is available. Refresh to check the current links.' : 'Reconnect and refresh to see current links.'} action={retry}/>}
      {visible.phase === 'failed' && <OutcomeState state="retryable_error" description="Could not verify the current links. Refresh to try again." action={retry}/>}
      {visible.phase === 'revoked' && <OutcomeState state="permission_revoked"/>}
      {visible.phase === 'ready' && !links.length && <EmptyState title="No related work" description="No work you can access is linked to this document."/>}
      {(['support', 'related'] as const).map(group => {
        const found = links.filter(link => link.group === group);
        return found.length > 0 && <section className="document-context-group" key={group}>
          <h4>{group === 'support' ? 'Supported work' : 'Related work'}</h4>
          <ul>{found.map(link => <li key={link.id}><Button variant="quiet" disabled={locked || !online}
            data-resource-route={encodeProductRoute({kind: 'work', project, item: link.id})}
            onClick={() => { if (!current.current.locked && current.current.online && current.current.key === key) current.current.onOpenWork(link.id); }}>{link.title}</Button>
            {link.status && <StatusBadge label={link.status}/>}</li>)}</ul>
        </section>;
      })}
      {visible.phase === 'ready' && retry}
    </>}</div>
  </section>;
}

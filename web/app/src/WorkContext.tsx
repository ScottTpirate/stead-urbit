import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { HomeError, UUID, type Fields, type HomeClient, type Query, type Row } from './api';
import { Button, TextField } from './primitives';
import { workStatuses } from './WorkQuickActions';
import type {ProductWorkEndpointReader} from './productJourneyState';
import {ContextualSearch, CONTEXT_SEARCH_MAX_PAGES, contextChoiceKey} from './contextualSearch';

type Endpoint = {kind: 'work' | 'document'; id: string; container: string};
type Direction = 'support' | 'blocks' | 'blockedBy' | 'related';
type Group = Direction | 'relatedDocs';
type Relation = {row: Row; source: Endpoint; target: Endpoint};
type WorkLink = Relation & {group: Group; other: Endpoint};
type EndpointDetails = {title: string; status?: string};
type TitledLink = WorkLink & EndpointDetails;
type LinkView = {generation: number} & ({status: 'ready'; links: TitledLink[]} | {status: 'failed' | 'revoked'});

const directionLabel: Record<Direction, string> = {
  support: 'Supporting doc', blocks: 'Blocks', blockedBy: 'Blocked by', related: 'Related work',
};
const groupLabel: Record<Group, string> = {
  support: 'Supporting docs', blocks: 'Blocks', blockedBy: 'Blocked by', related: 'Related work', relatedDocs: 'Related docs',
};

function endpoint(kind?: string, id?: string, container?: string): Endpoint | null {
  if (!id || !UUID.test(id)) return null;
  if (kind === 'work' && container === '') return {kind, id, container};
  if (kind === 'document' && container && UUID.test(container)) return {kind, id, container};
  return null;
}

const endpointKey = (value: Endpoint) => `${value.kind}/${value.container}/${value.id}`;
const sameEndpoint = (left: Endpoint, right: Endpoint) =>
  left.kind === right.kind && left.container === right.container && left.id === right.id;

function readScope(kind: Query['kind'], project: string, resource = '', container = '', search = '', cursor = ''): Query {
  return {kind, project_id: project, container_id: container, resource_id: resource, search, cursor};
}

function relation(row: Row, project: string): Relation {
  const source = endpoint(row.source_kind, row.source_id, row.source_container_id);
  const target = endpoint(row.target_kind, row.target_id, row.target_container_id);
  const type = row.type;
  if (row.kind !== 'relation' || !UUID.test(row.resource_id ?? '') || !/^[1-9][0-9]{0,19}$/u.test(row.resource_revision ?? '')
    || row.source_project_id !== project || row.target_project_id !== project || !source || !target
    || (type === 'blocks' ? source.kind !== 'work' || target.kind !== 'work'
      : type === 'documents' ? source.kind !== 'document' || target.kind !== 'work' : type !== 'related_to')) {
    throw new HomeError('invalid_response');
  }
  return {row, source, target};
}

function titleOf(row: Row, kind: Endpoint['kind']) {
  const title = row.title?.trim() || '';
  return kind === 'work' ? (title || 'Untitled work item')
    : (title.split('\n', 1)[0]?.replace(/^#{1,6} +/u, '').trim() || 'Untitled page');
}

async function endpointDetails(client: HomeClient, project: string, value: Endpoint, readWork?: ProductWorkEndpointReader, epoch?: string): Promise<EndpointDetails | null> {
  try {
    if (value.kind === 'work' && readWork) {
      const row = await readWork(project, value.id);
      if (row.projectId !== project || row.workId !== value.id) throw new HomeError('invalid_response');
      if (epoch && row.authorityEpoch !== epoch) throw new HomeError('stale_cursor');
      return {title: row.title.trim() || 'Untitled work item', status: row.statusLabel};
    }
    const view = await client.query(readScope(value.kind, project, value.id, value.container));
    const [row, extra] = Object.values(view.rows);
    if (!row || extra || view.cursor || row.kind !== value.kind || row.resource_id !== value.id
      || row.container_id !== value.container) throw new HomeError('invalid_response');
    return {title: titleOf(row, value.kind), status: value.kind === 'work' ? workStatuses.get(row.status ?? '') : undefined};
  } catch (failure) {
    if (failure instanceof HomeError && failure.code === 'denied_or_not_found') return null;
    throw failure;
  }
}

async function linksFor(client: HomeClient, project: string, work: Endpoint, active: () => boolean, readWork?: ProductWorkEndpointReader) {
  const matching: WorkLink[] = [];
  const seen = new Set<string>();
  const cursors = new Set<string>();
  let cursor = '';
  let stamp: string | undefined;
  for (let page = 0; page < 13 && active(); page++) {
    const view = await client.query(readScope('relations', project, '', '', '', cursor));
    const current = `${view.authority_epoch}/${view.generation}`;
    if (stamp && current !== stamp) throw new HomeError('stale_cursor');
    stamp = current;
    const rows = Object.values(view.rows);
    for (const row of rows) {
      const link = relation(row, project);
      if (seen.has(row.resource_id!) || seen.size >= 256) throw new HomeError('invalid_response');
      seen.add(row.resource_id!);
      const outgoing = sameEndpoint(link.source, work);
      if (!outgoing && !sameEndpoint(link.target, work)) continue;
      const other = outgoing ? link.target : link.source;
      const group = row.type === 'documents' ? 'support' : row.type === 'blocks' ? (outgoing ? 'blocks' : 'blockedBy')
        : other.kind === 'work' ? 'related' : 'relatedDocs';
      matching.push({...link, other, group});
    }
    cursor = view.cursor;
    if (!cursor) break;
    if (rows.length !== 20 || cursors.has(cursor)) throw new HomeError('invalid_response');
    cursors.add(cursor);
  }
  if (!active()) return [];
  if (cursor) throw new HomeError('invalid_response');

  const details = new Map<string, EndpointDetails | null>();
  const endpoints = [...new Map(matching.map(link => [endpointKey(link.other), link.other])).values()];
  for (let offset = 0; offset < endpoints.length && active(); offset += 6) {
    await Promise.all(endpoints.slice(offset, offset + 6).map(async value => {
      details.set(endpointKey(value), await endpointDetails(client, project, value, readWork, stamp?.split('/')[0]));
    }));
  }
  return matching.flatMap(link => {
    const found = details.get(endpointKey(link.other));
    return found ? [{...link, ...found}] : [];
  });
}

function endpointsOf(direction: Direction, work: Endpoint, chosen: Endpoint) {
  const reverse = direction === 'support' || direction === 'blockedBy';
  return {
    type: direction === 'support' ? 'documents' : direction === 'related' ? 'related_to' : 'blocks',
    source: reverse ? chosen : work,
    target: reverse ? work : chosen,
  };
}

function sameRelation(existing: Relation, proposed: ReturnType<typeof endpointsOf>) {
  return existing.row.type === proposed.type &&
    ((sameEndpoint(existing.source, proposed.source) && sameEndpoint(existing.target, proposed.target))
      || (proposed.type === 'related_to' && sameEndpoint(existing.source, proposed.target) && sameEndpoint(existing.target, proposed.source)));
}

type Props = {
  client: HomeClient; project: string; work: string;
  writable: boolean; locked: boolean; viewRevision: number;
  onCreate: (payload: Fields) => void; onRemove: (row: Row) => void;
  onOpenWork: (id: string) => void; onOpenDoc: (containerId: string, id: string) => void;
  readWork?: ProductWorkEndpointReader;
};

export function WorkContext(props: Props) {
  return <WorkContextPanel key={`${props.project}/${props.work}/${props.readWork ? 'product' : 'legacy'}`} {...props}/>;
}

function WorkContextPanel({client, project, work, writable, locked, viewRevision, onCreate, onRemove, onOpenWork, onOpenDoc, readWork}: Props) {
  const id = useId();
  const [expanded, setExpanded] = useState(false);
  const [result, setResult] = useState<LinkView | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [direction, setDirection] = useState<Direction | null>(null);
  const [term, setTerm] = useState('');
  const [selected, setSelected] = useState('');
  const [submittedAt, setSubmittedAt] = useState<number | null>(null);
  const [online, setOnline] = useState(() => navigator.onLine);
  const [searchRender, setSearchRender] = useState(0);
  const token = client.currentSessionToken(), carrier = client.productMode();
  const identity = useRef({client, token, carrier, project, work, viewRevision, readWork, online, generation: 0});
  const previous = identity.current;
  if (previous.client !== client || previous.token !== token || previous.carrier !== carrier || previous.project !== project
    || previous.work !== work || previous.viewRevision !== viewRevision || previous.readWork !== readWork || previous.online !== online) {
    identity.current = {client, token, carrier, project, work, viewRevision, readWork, online, generation: previous.generation + 1};
  }
  const generation = identity.current.generation;
  const authorized = !!token && carrier.kind !== 'unsupported';
  const operationLocked = locked || !online || !authorized;
  const currentAccess = () => identity.current.generation === generation && client.currentSessionToken() === token && client.productMode() === carrier && navigator.onLine;
  const searchController = useRef(new ContextualSearch());
  const searchGeneration = searchController.current.configure({client, project, work, relation: direction ?? '', kind: direction === 'support' ? 'document' : 'work',
    term, revision: viewRevision, writable, locked, online});
  const matchSearch = searchController.current.state();
  const searchRegion = useRef<HTMLDivElement>(null), choiceField = useRef<HTMLSelectElement>(null), addLink = useRef<HTMLButtonElement>(null);
  const returnToAdd = useRef<number | null>(null);
  const focusSearch = useRef<{generation: number; searchGeneration: number} | null>(null);
  const mounted = useRef(false);
  const linkReads = useRef(0);
  const current = authorized && online && result?.generation === generation ? result : null;
  const links = current?.status === 'ready' ? current.links : [];
  const item: Endpoint = {kind: 'work', id: work, container: ''};
  const matches = matchSearch.phase === 'ready' ? matchSearch.page : undefined;

  useEffect(() => {
    mounted.current = true;
    const offline = () => setOnline(false), connected = () => setOnline(true);
    window.addEventListener('offline', offline); window.addEventListener('online', connected);
    return () => { mounted.current = false; searchController.current.dispose(); window.removeEventListener('offline', offline); window.removeEventListener('online', connected); };
  }, []);
  useEffect(() => {
    if (!expanded || !authorized || !online) return;
    let running = true; const read = ++linkReads.current;
    const active = () => running && linkReads.current === read && identity.current.generation === generation && client.currentSessionToken() === token && client.productMode() === carrier;
    void linksFor(client, project, {kind: 'work', id: work, container: ''}, active, readWork).then(
      value => { if (active()) setResult({generation, status: 'ready', links: value}); },
      failure => {
        if (!active()) return;
        const revoked = failure instanceof HomeError && ['denied_or_not_found', 'session_required', 'session_changed'].includes(failure.code);
        if (revoked) { linkReads.current++; searchController.current.dispose(); setSelected(''); focusSearch.current = null; }
        setResult({generation, status: revoked ? 'revoked' : 'failed'});
      },
    );
    return () => { running = false; };
  }, [client, project, work, expanded, attempt, viewRevision, readWork, generation, authorized, online, token, carrier]);

  useEffect(() => {
    if (submittedAt === null || submittedAt === viewRevision) return;
    setSubmittedAt(null); setDirection(null); setTerm(''); setSelected(''); focusSearch.current = null;
  }, [submittedAt, viewRevision]);
  useEffect(() => {
    const request = focusSearch.current;
    if (!request || request.generation !== generation || request.searchGeneration !== searchGeneration || operationLocked || matchSearch.phase === 'loading') return;
    const frame = requestAnimationFrame(() => {
      if (identity.current.generation !== generation || client.currentSessionToken() !== token || client.productMode() !== carrier || focusSearch.current !== request) return;
      (choiceField.current || searchRegion.current)?.focus(); focusSearch.current = null;
    });
    return () => cancelAnimationFrame(frame);
  }, [generation, searchGeneration, operationLocked, matchSearch.phase, searchRender, client, token, carrier]);

  function resetSearch(text = '') {
    searchController.current.dispose(); setTerm(text); setSelected(''); focusSearch.current = null;
  }
  async function readMatches(next = false) {
    if (operationLocked || !currentAccess() || !direction || !writable) return;
    const owner = generation, request = searchGeneration;
    setSelected(''); focusSearch.current = null;
    const pending = next ? searchController.current.next() : searchController.current.first();
    setSearchRender(value => value + 1);
    const currentReply = await pending;
    if (!currentReply || !mounted.current || identity.current.generation !== owner) return;
    if (searchController.current.state().phase === 'revoked') { linkReads.current++; setResult({generation: owner, status: 'revoked'}); }
    focusSearch.current = {generation: owner, searchGeneration: request}; setSearchRender(value => value + 1);
  }
  async function find(event: FormEvent<HTMLFormElement>) { event.preventDefault(); await readMatches(); }
  useEffect(() => {
    if (returnToAdd.current !== generation || direction || operationLocked || !addLink.current) return;
    addLink.current.focus(); returnToAdd.current = null;
  }, [direction, operationLocked, current, generation]);
  const choice = matches?.choices.find(value => contextChoiceKey(value) === selected);
  const proposed = direction && choice ? endpointsOf(direction, item, choice) : null;
  const duplicate = !!proposed && links.some(link => sameRelation(link, proposed));

  function save() {
    if (!proposed || duplicate || operationLocked || !currentAccess() || searchController.current.state() !== matchSearch
      || carrier.kind !== 'legacy' || !writable || current?.status !== 'ready') return;
    setSubmittedAt(viewRevision);
    const {type, source, target} = proposed;
    onCreate({
      type, source_project_id: project, source_kind: source.kind, source_container_id: source.container, source_id: source.id,
      target_project_id: project, target_kind: target.kind, target_container_id: target.container, target_id: target.id,
    });
  }

  return <section className="work-section work-context" aria-label="Relationships">
    <div className="work-context-heading">
      <h3>Relationships</h3>
      <Button variant="quiet" aria-expanded={expanded} aria-controls={id} disabled={operationLocked || !!direction}
        onClick={() => { setResult(null); setExpanded(value => !value); }}>{expanded ? 'Hide links' : 'Show links'}</Button>
    </div>
    <div id={id} hidden={!expanded}>
      {expanded && <>
        <p className="muted work-context-note">Latest authorized content · informational links. No revision is pinned; links do not affect completion.</p>
        {!authorized ? <p role="status">Links are unavailable until current access is confirmed.</p> : !online ? <p role="status">Reconnect to refresh these links.</p> : !current && <p role="status">Loading links…</p>}
        {(current?.status === 'failed' || current?.status === 'revoked') && <div className="actions">
          <p role="status">{current.status === 'revoked' ? 'These links are unavailable with your current access.' : 'Couldn’t load the links.'}</p><Button variant="quiet" disabled={operationLocked}
            onClick={() => { setResult(null); setAttempt(value => value + 1); }}>Retry links</Button>
        </div>}
        {current?.status === 'ready' && links.length === 0 && <p className="muted">No links for this Work item yet.</p>}
        {links.length > 0 && <div className="work-context-groups">
          {(Object.keys(groupLabel) as Group[]).map(group => {
            const rows = links.filter(link => link.group === group);
            return rows.length > 0 && <section key={group} className="work-context-group">
              <h4>{groupLabel[group]}</h4>
              <ul className="work-context-list">{rows.map(link => <li key={link.row.resource_id} className="work-context-row">
                <Button variant="quiet" disabled={operationLocked || !!direction || sameEndpoint(link.other, item)} onClick={() => {
                  if (!currentAccess()) return;
                  if (link.other.kind === 'work') onOpenWork(link.other.id);
                  else onOpenDoc(link.other.container, link.other.id);
                }}>{link.title}</Button>
                {link.status && <span className="work-context-status">{link.status}</span>}
                {writable && <Button variant="quiet" aria-label={`Remove link to ${link.title}`} disabled={operationLocked || !!direction}
                  onClick={() => { if (currentAccess()) onRemove(link.row); }}>Remove</Button>}
              </li>)}</ul>
            </section>;
          })}
        </div>}
        {writable && carrier.kind === 'legacy' && (current?.status === 'ready' || !!direction) && (direction ? <form className="work-context-form" onSubmit={event => void find(event)}>
          <label htmlFor={`${id}-type`}>Relationship type</label><select id={`${id}-type`} value={direction} disabled={operationLocked} onChange={event => {
            setDirection(event.target.value as Direction); resetSearch();
          }}>{(Object.keys(directionLabel) as Direction[]).map(value => <option key={value} value={value}>{directionLabel[value]}</option>)}</select>
          <div className="actions">
            <TextField label="Find a resource" value={term} onChange={event => resetSearch(event.target.value)} maxLength={128}
              disabled={operationLocked} placeholder={direction === 'support' ? 'Search pages' : 'Search Work'}/>
            <Button type="submit" pending={matchSearch.phase === 'loading'} disabled={operationLocked || !term.trim()
              || new TextEncoder().encode(term.trim()).length > 128}>Find matches</Button>
          </div>
          {new TextEncoder().encode(term.trim()).length > 128 && <p role="status">Use a shorter search phrase.</p>}
          {matchSearch.phase !== 'idle' && <div ref={searchRegion} className="work-context-matches" role="region" aria-label="Resource matches" tabIndex={-1} aria-busy={matchSearch.phase === 'loading'}>
            {matchSearch.phase === 'loading' && <p role="status">Finding authorized matches…</p>}
            {matchSearch.phase === 'failed' && <p role="status">Matches could not be verified. Start over to read a fresh first page.</p>}
            {matchSearch.phase === 'expired' && <p role="status">These matches changed. Start over to read the current results.</p>}
            {matchSearch.phase === 'revoked' && <p role="status">Matches are unavailable with your current access. Start over to check again.</p>}
            {matchSearch.phase === 'offline' && <p role="status">Reconnect and start over to read current matches.</p>}
            {matchSearch.phase === 'unsupported' && <p role="status">Resource search is unavailable on this Home.</p>}
            {matches && <>
              <p>Search page {matches.number} · {matches.choices.length} {direction === 'support' ? 'supporting Docs' : 'Work items'} on this page</p>
              {matches.choices.length > 0 ? <div className="work-context-choice"><label htmlFor={`${id}-choice`}>Choose a resource</label><select id={`${id}-choice`} ref={choiceField} value={selected} disabled={operationLocked} onChange={event => setSelected(event.target.value)}>
                <option value="">Select a match</option>
                {matches.choices.map(value => <option key={contextChoiceKey(value)} value={contextChoiceKey(value)}>{value.title}</option>)}
              </select></div> : <p role="status">{matches.cursor ? (direction === 'support' ? 'No supporting Docs on this page. Continue to the next matches.' : 'No other Work on this page. Continue to the next matches.')
                : matches.number === 1 ? 'No matching resources.' : 'No matching resources on this final page.'}</p>}
              {matches.cursor && matches.number < CONTEXT_SEARCH_MAX_PAGES && <Button variant="quiet" disabled={operationLocked} onClick={() => void readMatches(true)}>Next matches</Button>}
              {matches.cursor && matches.number >= CONTEXT_SEARCH_MAX_PAGES && <p role="status">Refine your search to find more specific matches.</p>}
            </>}
            {matchSearch.phase !== 'loading' && <Button variant="quiet" disabled={operationLocked || !term.trim()} onClick={() => void readMatches()}>Start over</Button>}
          </div>}
          {duplicate && <p role="status">This link already exists.</p>}
          <div className="actions">
            <Button variant="primary" disabled={operationLocked || duplicate || !proposed || current?.status !== 'ready'} onClick={save}>Save link</Button>
            <Button variant="quiet" disabled={operationLocked} onClick={() => { returnToAdd.current = generation; setSubmittedAt(null); setDirection(null); resetSearch(); }}>Cancel</Button>
          </div>
        </form> : <Button ref={addLink} variant="quiet" disabled={operationLocked} onClick={() => { resetSearch(); setDirection('support'); }}>Add link</Button>)}
      </>}
    </div>
  </section>;
}

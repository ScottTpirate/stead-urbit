import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { HomeError, UUID, type Fields, type HomeClient, type Query, type Row } from './api';
import { Button, TextField } from './primitives';
import { workStatuses } from './WorkQuickActions';

type Endpoint = {kind: 'work' | 'document'; id: string; container: string};
type Choice = Endpoint & {title: string};
type Direction = 'support' | 'blocks' | 'blockedBy' | 'related';
type Group = Direction | 'relatedDocs';
type Relation = {row: Row; source: Endpoint; target: Endpoint};
type WorkLink = Relation & {group: Group; other: Endpoint};
type EndpointDetails = {title: string; status?: string};
type TitledLink = WorkLink & EndpointDetails;
type LinkView = {revision: number} & ({status: 'ready'; links: TitledLink[]} | {status: 'failed'});
type MatchSearch = {status: 'none' | 'loading' | 'failed'}
  | {status: 'ready'; choices: Choice[]; limited: boolean};

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

async function endpointDetails(client: HomeClient, project: string, value: Endpoint): Promise<EndpointDetails | null> {
  try {
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

async function linksFor(client: HomeClient, project: string, work: Endpoint, active: () => boolean) {
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
      details.set(endpointKey(value), await endpointDetails(client, project, value));
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
};

export function WorkContext(props: Props) {
  return <WorkContextPanel key={`${props.project}/${props.work}`} {...props}/>;
}

function WorkContextPanel({client, project, work, writable, locked, viewRevision, onCreate, onRemove, onOpenWork, onOpenDoc}: Props) {
  const id = useId();
  const [expanded, setExpanded] = useState(false);
  const [result, setResult] = useState<LinkView | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [direction, setDirection] = useState<Direction | null>(null);
  const [term, setTerm] = useState('');
  const [matchSearch, setMatchSearch] = useState<MatchSearch>({status: 'none'});
  const [selected, setSelected] = useState('');
  const [submittedAt, setSubmittedAt] = useState<number | null>(null);
  const searchRevision = useRef(0);
  const current = result?.revision === viewRevision ? result : null;
  const links = current?.status === 'ready' ? current.links : [];
  const item: Endpoint = {kind: 'work', id: work, container: ''};

  useEffect(() => {
    if (!expanded) return;
    let running = true;
    void linksFor(client, project, {kind: 'work', id: work, container: ''}, () => running).then(
      value => { if (running) setResult({revision: viewRevision, status: 'ready', links: value}); },
      () => { if (running) setResult({revision: viewRevision, status: 'failed'}); },
    );
    return () => { running = false; };
  }, [client, project, work, expanded, attempt, viewRevision]);

  useEffect(() => () => { searchRevision.current++; }, []);

  useEffect(() => {
    if (submittedAt === null || submittedAt === viewRevision) return;
    searchRevision.current++;
    setSubmittedAt(null); setDirection(null); setTerm(''); setSelected(''); setMatchSearch({status: 'none'});
  }, [submittedAt, viewRevision]);

  function resetSearch(text = '') {
    searchRevision.current++;
    setTerm(text); setSelected(''); setMatchSearch({status: 'none'});
  }

  async function find(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const search = term.trim();
    if (locked || !direction || !search || new TextEncoder().encode(search).length > 128) return;
    const revision = ++searchRevision.current;
    setSelected(''); setMatchSearch({status: 'loading'});
    try {
      const view = await client.query(readScope('search', project, '', '', search));
      const choices = new Map<string, Choice>();
      for (const row of Object.values(view.rows)) {
        const entry = endpoint(row.kind, row.resource_id, row.container_id);
        if (entry && entry.kind === (direction === 'support' ? 'document' : 'work') && !sameEndpoint(entry, item)) {
          choices.set(endpointKey(entry), {...entry, title: titleOf(row, entry.kind)});
        }
      }
      if (searchRevision.current === revision) setMatchSearch({status: 'ready', choices: [...choices.values()], limited: !!view.cursor});
    } catch {
      if (searchRevision.current === revision) setMatchSearch({status: 'failed'});
    }
  }

  const choice = matchSearch.status === 'ready' ? matchSearch.choices.find(value => endpointKey(value) === selected) : undefined;
  const proposed = direction && choice ? endpointsOf(direction, item, choice) : null;
  const duplicate = !!proposed && links.some(link => sameRelation(link, proposed));

  function save() {
    if (!proposed || duplicate || locked || !writable || current?.status !== 'ready') return;
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
      <Button variant="quiet" aria-expanded={expanded} aria-controls={id} disabled={locked || !!direction}
        onClick={() => { setResult(null); setExpanded(value => !value); }}>{expanded ? 'Hide links' : 'Show links'}</Button>
    </div>
    <div id={id} hidden={!expanded}>
      {expanded && <>
        {!current && <p role="status">Loading links…</p>}
        {current?.status === 'failed' && <div className="actions">
          <p role="status">Couldn’t load the links.</p><Button variant="quiet" disabled={locked}
            onClick={() => { setResult(null); setAttempt(value => value + 1); }}>Retry links</Button>
        </div>}
        {current?.status === 'ready' && links.length === 0 && <p className="muted">No links for this Work item yet.</p>}
        {links.length > 0 && <div className="work-context-groups">
          {(Object.keys(groupLabel) as Group[]).map(group => {
            const rows = links.filter(link => link.group === group);
            return rows.length > 0 && <section key={group} className="work-context-group">
              <h4>{groupLabel[group]}</h4>
              <ul className="work-context-list">{rows.map(link => <li key={link.row.resource_id} className="work-context-row">
                <Button variant="quiet" disabled={locked || !!direction || sameEndpoint(link.other, item)} onClick={() => {
                  if (link.other.kind === 'work') onOpenWork(link.other.id);
                  else onOpenDoc(link.other.container, link.other.id);
                }}>{link.title}</Button>
                {link.status && <span className="work-context-status">{link.status}</span>}
                {writable && <Button variant="quiet" aria-label={`Remove link to ${link.title}`} disabled={locked || !!direction}
                  onClick={() => onRemove(link.row)}>Remove</Button>}
              </li>)}</ul>
            </section>;
          })}
        </div>}
        {writable && current?.status === 'ready' && (direction ? <form className="work-context-form" onSubmit={event => void find(event)}>
          <label>Relationship type<select value={direction} disabled={locked} onChange={event => {
            setDirection(event.target.value as Direction); resetSearch();
          }}>{(Object.keys(directionLabel) as Direction[]).map(value => <option key={value} value={value}>{directionLabel[value]}</option>)}</select></label>
          <div className="actions">
            <TextField label="Find a resource" value={term} onChange={event => resetSearch(event.target.value)} maxLength={128}
              disabled={locked} placeholder={direction === 'support' ? 'Search pages' : 'Search Work'}/>
            <Button type="submit" pending={matchSearch.status === 'loading'} disabled={locked || !term.trim()
              || new TextEncoder().encode(term.trim()).length > 128}>Find matches</Button>
          </div>
          {new TextEncoder().encode(term.trim()).length > 128 && <p role="status">Use a shorter search phrase.</p>}
          {matchSearch.status === 'failed' && <p role="status">Couldn’t find resources. Try the search again.</p>}
          {matchSearch.status === 'ready' && (matchSearch.choices.length > 0
            ? <label>Choose a resource<select value={selected} disabled={locked} onChange={event => setSelected(event.target.value)}>
              <option value="">Select a match</option>
              {matchSearch.choices.map(value => <option key={endpointKey(value)} value={endpointKey(value)}>{value.title}</option>)}
            </select></label> : <p role="status">No matching resources.</p>)}
          {matchSearch.status === 'ready' && matchSearch.limited && <p className="muted">Refine your search to see more specific matches.</p>}
          {duplicate && <p role="status">This link already exists.</p>}
          <div className="actions">
            <Button variant="primary" disabled={locked || duplicate || !proposed} onClick={save}>Save link</Button>
            <Button variant="quiet" disabled={locked} onClick={() => { setSubmittedAt(null); setDirection(null); resetSearch(); }}>Cancel</Button>
          </div>
        </form> : <Button variant="quiet" disabled={locked} onClick={() => { resetSearch(); setDirection('support'); }}>Add link</Button>)}
      </>}
    </div>
  </section>;
}

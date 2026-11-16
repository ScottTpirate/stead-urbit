import {useEffect, useId, useRef} from 'react';
import {Button, OutcomeState} from './primitives';
import {Icon} from './Icon';
import {productPriorityLabels, productStatusLabels} from './productWorkFields';
import type {ProductWorkPreview} from './productProtocol';
import './productWorkList.css';

type Status = ProductWorkPreview['status'];
type Group = {readonly status: Status; readonly rows: readonly ProductWorkPreview[]};
const order: readonly Status[] = ['backlog', 'todo', 'in_progress', 'in_review', 'legacy-blocked', 'done', 'canceled'];
const terminal = (status: Status) => status === 'done' || status === 'canceled';

// This is a presentation of one already-authorized page, never a filtered query
// or an aggregate of cached pages. Refuse a malformed page rather than omit rows.
export function groupProductWorkPage(projectId: string, rows: readonly ProductWorkPreview[]): readonly Group[] | undefined {
  if (!Array.isArray(rows) || rows.length > 20) return undefined;
  const ids = new Set<string>();
  for (const row of rows) {
    if (!row || row.kind !== 'work' || row.project_id !== projectId || row.container_id !== ''
      || typeof row.resource_id !== 'string' || !row.resource_id || ids.has(row.resource_id)
      || typeof row.title !== 'string' || !row.title || typeof row.owner_display_name !== 'string'
      || typeof row.worker_display_name !== 'string' || typeof row.owner_principal_id !== 'string'
      || typeof row.worker_principal_id !== 'string' || !order.includes(row.status)
      || !Object.hasOwn(productPriorityLabels, row.priority)) return undefined;
    ids.add(row.resource_id);
  }
  return order.map(status => ({status, rows: rows.filter(row => row.status === status)})).filter(group => group.rows.length > 0);
}

export type ProductWorkListProps = {projectId: string; pageToken: object; rows: readonly ProductWorkPreview[]; locked: boolean;
  onOpen: (workId: string) => void; onRefresh: () => void};
export function ProductWorkList(props: ProductWorkListProps) {
  const identity = useRef({projectId: props.projectId, pageToken: props.pageToken, epoch: 0});
  const latest = useRef(props), mounted = useRef(true); latest.current = props;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  if (identity.current.projectId !== props.projectId || identity.current.pageToken !== props.pageToken) {
    identity.current = {projectId: props.projectId, pageToken: props.pageToken, epoch: identity.current.epoch + 1};
  }
  const scope = identity.current, active = () => mounted.current && identity.current === scope && !latest.current.locked;
  // The caller's fresh authorized snapshot token resets disclosures on another
  // page/read. Ordinary lock/draft rerenders keep the current native details state.
  return <WorkPage key={scope.epoch} {...props} onOpen={id => { if (active()) latest.current.onOpen(id); }}
    onRefresh={() => { if (active()) latest.current.onRefresh(); }}/>
}
function WorkPage({projectId, rows, locked, onOpen, onRefresh}: ProductWorkListProps) {
  const id = useId(), groups = groupProductWorkPage(projectId, rows);
  if (!groups) return <OutcomeState state="retryable_error" description="This Work page is unavailable. Refresh to read it again."
    action={<Button disabled={locked} onClick={onRefresh}>Refresh current page</Button>}/>;
  if (!groups.length) return null;
  const list = (group: Group) => <ul className="product-journey-list product-work-page-rows" aria-labelledby={`${id}-${group.status}`}>
    {group.rows.map(row => <li key={row.resource_id}><button type="button" className="product-work-page-row" disabled={locked}
      onClick={() => { if (!locked) onOpen(row.resource_id); }}>
      <span className="product-work-page-status"><Icon name={row.status === 'done' ? 'check' : row.status === 'canceled' ? 'x'
        : row.status === 'legacy-blocked' ? 'circle-exclamation-point' : 'circle'}/><span>{productStatusLabels[row.status]}</span></span>
      <span className="product-work-page-title">{row.title}</span>
      <span className="product-work-page-person"><span className="product-work-page-label">Owner: </span>{row.owner_display_name || (row.owner_principal_id ? 'Project member' : 'Unassigned')}</span>
      <span className="product-work-page-person"><span className="product-work-page-label">Working on it: </span>{row.worker_display_name || (row.worker_principal_id ? 'Project member' : 'Unassigned')}</span>
      <span className="product-work-page-priority"><span className="product-work-page-label">Priority: </span>{productPriorityLabels[row.priority]}</span>
    </button></li>)}
  </ul>;
  return <div className="product-work-page">
    <p className="muted product-work-page-note">Grouped by status on this page.</p>
    {groups.map(group => terminal(group.status)
      ? <details className="product-work-page-group product-work-page-closed" key={group.status}>
        <summary id={`${id}-${group.status}`}>{productStatusLabels[group.status]} <span className="product-work-page-count">{group.rows.length} on this page</span></summary>
        {list(group)}
      </details>
      : <section className="product-work-page-group" key={group.status} aria-labelledby={`${id}-${group.status}`}>
        <h3 id={`${id}-${group.status}`}>{productStatusLabels[group.status]} <span className="product-work-page-count">{group.rows.length} on this page</span></h3>
        {list(group)}
      </section>)}
  </div>;
}

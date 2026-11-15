import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import type { Row } from './api';
import './work.css';

export const workStatuses = new Map([
  ['backlog', 'Backlog'], ['todo', 'To do'], ['in_progress', 'In progress'],
  ['blocked', 'Blocked'], ['done', 'Done'], ['canceled', 'Canceled'],
]);
const priorities = [['none', 'No priority'], ['low', 'Low'], ['medium', 'Medium'], ['high', 'High'], ['urgent', 'Urgent']];
export type WorkProperty = 'status' | 'priority' | 'assignee';
export type WorkMenu = { row: Row; view: 'actions' | WorkProperty; x: number; y: number; trigger: HTMLElement };

export function assigneeName(row: Row) {
  return row.assignee_display_name || (row.assignee_principal_id ? 'Unavailable assignee' : 'Unassigned');
}

type Props = {
  menu: WorkMenu;
  canEdit: boolean;
  who?: string;
  loadAssignees: () => Promise<Row[]>;
  close: (restoreFocus?: boolean) => void;
  open: () => void;
  remove: () => void;
  change: (property: WorkProperty, value: string) => void;
};

export function WorkQuickActions({ menu, canEdit, who, loadAssignees, close, open, remove, change }: Props) {
  const [view, setView] = useState(menu.view);
  const [filter, setFilter] = useState('');
  const [people, setPeople] = useState<{ status: 'loading' | 'unavailable' } | { status: 'ready'; rows: Row[] }>({ status: 'loading' });
  const pane = useRef<HTMLDivElement>(null);
  const closeRef = useRef(close);
  closeRef.current = close;
  const loader = useRef(loadAssignees);
  loader.current = loadAssignees;
  const trigger = menu.trigger;

  useEffect(() => {
    function outside(event: PointerEvent) {
      if (event.target instanceof Node && !pane.current?.contains(event.target) && !trigger.contains(event.target)) closeRef.current(false);
    }
    const resize = () => closeRef.current(false);
    document.addEventListener('pointerdown', outside);
    window.addEventListener('resize', resize);
    return () => { document.removeEventListener('pointerdown', outside); window.removeEventListener('resize', resize); };
  }, [trigger]);
  useEffect(() => {
    if (view !== 'assignee') return;
    let current = true;
    setPeople({ status: 'loading' });
    void loader.current().then(rows => { if (current) setPeople({ status: 'ready', rows }); },
      () => { if (current) setPeople({ status: 'unavailable' }); });
    return () => { current = false; };
  }, [view]);
  useLayoutEffect(() => {
    const node = pane.current;
    if (!node) return;
    (node.querySelector<HTMLElement>('input') ?? node.querySelector<HTMLElement>('[role^="menuitem"]') ?? node).focus();
  }, [view]);
  useLayoutEffect(() => {
    const node = pane.current;
    if (!node) return;
    node.style.left = `${Math.min(menu.x, Math.max(8, window.innerWidth - node.offsetWidth - 8))}px`;
    node.style.top = `${Math.min(menu.y, Math.max(8, window.innerHeight - node.offsetHeight - 8))}px`;
  }, [menu.x, menu.y, view, people, filter]);

  function move(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' || event.key === 'Tab') {
      if (event.key === 'Escape') event.preventDefault();
      close();
      return;
    }
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) ||
        (event.target instanceof HTMLInputElement && ['Home', 'End'].includes(event.key))) return;
    const list = [...(pane.current?.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]:enabled') ?? [])];
    if (list.length === 0) return;
    event.preventDefault();
    const focused = list.findIndex(item => item === document.activeElement);
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? list.length - 1
      : event.key === 'ArrowDown' ? (focused + 1) % list.length : (focused < 0 ? list.length - 1 : (focused + list.length - 1) % list.length);
    list[index]?.focus();
  }
  function select(next: 'actions' | WorkProperty) { setFilter(''); setView(next); }
  const option = (property: WorkProperty, value: string, label: string, selected: boolean, note?: string) =>
    <button key={value} type="button" role="menuitemradio" aria-checked={selected} onClick={() => change(property, value)}>
      {property === 'status' && <span className="status-marker" data-status={value} aria-hidden="true"/>}
      <span>{label}{note && <small>{note}</small>}</span>{selected && <span className="work-menu-check" aria-hidden="true">✓</span>}
    </button>;
  const title = view === 'actions' ? 'Work item actions' : view === 'assignee' ? 'Assign to' : view === 'status' ? 'Set status' : 'Set priority';
  const term = filter.trim().toLowerCase();
  const matching = people.status === 'ready' ? people.rows.filter(row =>
    `${row.display_name ?? ''} ${row.identity_ship ?? ''}`.toLowerCase().includes(term)) : [];

  return createPortal(<div className="work-menu" ref={pane} role="dialog" aria-label={title} tabIndex={-1} onKeyDown={move}>
    {view !== 'actions' && <header>
      {menu.view === 'actions' && <button className="work-menu-back" type="button" aria-label="Back to actions" onClick={() => select('actions')}>‹</button>}
      <span>{title}</span>
    </header>}
    {view === 'assignee' && <>
      <input aria-label="Find a project member" placeholder="Find a project member…" value={filter} onChange={event => setFilter(event.target.value)}/>
      {people.status === 'loading' && <p role="status">Loading project members…</p>}
      {people.status === 'unavailable' && <p role="status">Project members could not be loaded.</p>}
      {people.status === 'ready' && matching.length === 0 && <p role="status">{term ? 'No matching members' : 'No eligible members'}</p>}
    </>}
    <div role="menu" aria-label={title}>
    {view === 'actions' && <>
      <button type="button" role="menuitem" onClick={open}>Open details</button>
      {canEdit && <><button type="button" role="menuitem" onClick={() => select('status')}>Set status <span className="work-menu-chevron" aria-hidden="true">›</span></button>
        <button type="button" role="menuitem" onClick={() => select('assignee')}>Assign to <span className="work-menu-chevron" aria-hidden="true">›</span></button>
        <button type="button" role="menuitem" onClick={() => select('priority')}>Set priority <span className="work-menu-chevron" aria-hidden="true">›</span></button>
        <button className="work-menu-delete" type="button" role="menuitem" onClick={remove}>Delete…</button></>}
    </>}
    {view === 'status' && [...workStatuses].map(([value, label]) => option(view, value, label, menu.row.status === value))}
    {view === 'priority' && priorities.map(([value, label]) => option(view, value!, label!, (menu.row.priority || 'none') === value))}
    {view === 'assignee' && <>
      {!term && option(view, '', 'Unassigned', !menu.row.assignee_principal_id)}
      {matching.map(row => option(view, row.principal_id!, row.principal_id === who ? `${row.display_name} (you)` : row.display_name ?? row.identity_ship ?? 'Member',
        menu.row.assignee_principal_id === row.principal_id, row.identity_ship !== row.display_name ? row.identity_ship : undefined))}
    </>}
    </div>
  </div>, document.body);
}

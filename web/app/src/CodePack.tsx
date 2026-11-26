import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { UUID, packRefs, type Fields, type ExternalRepositoryRead, type HomeClient } from './api';
import { newId } from './protocol';
import { AcceptedTime } from './AcceptedTime';
import { CopyValue, GitCredentials, repositoryUrl } from './CodeRepository';
import { CodeExternalReview } from './CodeExternalReview';
import { RepoBrowser } from './RepoBrowser';
import { refLabel } from './externalReview';
import { Button, Surface, TextField } from './primitives';
import { workBranchRef, type CodeDevelopmentTarget } from './WorkDevelopment';

const TAG_PREFIX = '726566732f746167732f';
const shortRef = (key: string) => refLabel(key).replace(/^refs\/(?:heads|tags)\//u, '')
  .replace(/[\p{Cc}\p{Cf}]/gu, character => `\\u{${character.codePointAt(0)?.toString(16)}}`);

function RepositoryRefs({ snapshot, client, project, browse, refresh, initialReference }: {
  snapshot: Fields; client: HomeClient; project: string; browse: boolean; refresh: () => void;
  initialReference?: string;
}) {
  const [section, setSection] = useState<'branch' | 'tag'>('branch');
  const [selection, setSelection] = useState(initialReference ?? '');
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('');
  const picker = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const choices = useRef<HTMLUListElement>(null);
  const refs = Object.entries(packRefs(snapshot)).sort(([left], [right]) => {
    if (left === snapshot.head) return -1;
    if (right === snapshot.head) return 1;
    return shortRef(left).localeCompare(shortRef(right));
  });
  const branches = refs.filter(([key]) => !key.startsWith(TAG_PREFIX));
  const tags = refs.filter(([key]) => key.startsWith(TAG_PREFIX));
  const selected = refs.find(([key]) => key === selection) ?? branches[0]!;
  const selectedKind = selected[0].startsWith(TAG_PREFIX) ? 'tag' : 'branch';
  const available = (section === 'branch' ? branches : tags).filter(([key]) =>
    shortRef(key).toLowerCase().includes(filter.trim().toLowerCase()));

  useEffect(() => {
    if (!open) return;
    search.current?.focus();
    function dismiss(event: PointerEvent) {
      if (event.target instanceof Node && !picker.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, [open]);

  function select(key: string) {
    setSelection(key);
    trigger.current?.focus();
    setOpen(false);
  }
  function pickerKeys(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' && open) {
      event.preventDefault();
      trigger.current?.focus();
      setOpen(false);
      return;
    }
    if (event.currentTarget === event.target || !open || !['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter'].includes(event.key)) return;
    const buttons = Array.from(choices.current?.querySelectorAll('button') ?? []);
    const active = buttons.findIndex(button => button === event.target);
    if (event.target === search.current) {
      if (event.key === 'Enter' && available.length === 1) {
        event.preventDefault();
        select(available[0]![0]);
      }
      if (event.key === 'ArrowDown' && buttons[0]) {
        event.preventDefault();
        buttons[0].focus();
      }
      return;
    }
    if (active < 0 || event.key === 'Enter') return;
    event.preventDefault();
    if (event.key === 'ArrowUp' && active === 0) search.current?.focus();
    else {
      const index = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
        : active + (event.key === 'ArrowDown' ? 1 : -1);
      buttons[index]?.focus();
    }
  }

  return <>
    <div className="repo-ref-tip">
      <div className="repo-ref-picker" ref={picker} onKeyDown={pickerKeys} onBlur={event => {
        if (event.relatedTarget instanceof Node && !event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}>
        <Button ref={trigger} className="repo-ref-trigger" aria-haspopup="dialog" aria-expanded={open}
          aria-label={`Switch branch or tag. Current ${selectedKind}: ${shortRef(selected[0])}`}
          onClick={() => {
            if (!open) { setSection(selectedKind); setFilter(''); }
            setOpen(!open);
          }}>
          <span aria-hidden="true" className="repo-ref-kind">{selectedKind === 'branch' ? 'Branch' : 'Tag'}</span>
          <bdi>{shortRef(selected[0])}</bdi>
        </Button>
        {open && <div className="repo-ref-panel" role="dialog" aria-label="Switch branch or tag">
          <nav className="repo-ref-tabs" aria-label="Reference type">
            <Button variant="quiet" aria-pressed={section === 'branch'} onClick={() => setSection('branch')}>
              Branches <span className="repo-count">{branches.length}</span>
            </Button>
            <Button variant="quiet" aria-pressed={section === 'tag'} onClick={() => setSection('tag')}>
              Tags <span className="repo-count">{tags.length}</span>
            </Button>
          </nav>
          <div className="repo-ref-search">
            <TextField ref={search} label={section === 'branch' ? 'Find a branch' : 'Find a tag'}
              type="search" value={filter} maxLength={256} onChange={event => setFilter(event.target.value)}
              spellCheck={false} autoComplete="off" />
          </div>
          {available.length > 0 ? <ul ref={choices} className="repo-ref-list" aria-label={section === 'branch' ? 'Branches' : 'Tags'}>
            {available.map(([key, oid]) => <li key={key}>
              <button type="button" className="repo-ref-row" aria-pressed={key === selected[0]} onClick={() => select(key)}>
                <span className="repo-ref-name"><bdi>{shortRef(key)}</bdi>{key === snapshot.head && <small>Default</small>}</span>
                <code title={oid}>{oid.slice(0, 7)}</code>
              </button>
            </li>)}
          </ul> : <p role="status" className="repo-ref-empty">{filter.trim() ? 'No matching references.' : 'No tags yet.'}</p>}
        </div>}
      </div>
      <div className="repo-tip-actions">
        <code title={selected[1]}>{selected[1].slice(0, 12)}</code>
        <CopyValue key={selected[1]} value={selected[1]} label={selectedKind === 'branch' ? 'Copy commit ID' : 'Copy object ID'} />
      </div>
    </div>
    {browse && snapshot.snapshot && <RepoBrowser key={`${project}/${snapshot.snapshot}/${selected[0]}`} client={client} project={project}
      snapshot={snapshot.snapshot} reference={selected[0]} refresh={refresh} />}
  </>;
}

export function CodePack({ client, project, principal, initialProposal, onOpenWork, development, gitAccess = true }: {
  client: HomeClient; project: string; principal: string;
  initialProposal?: string; onOpenWork?: (workId: string) => void;
  development?: CodeDevelopmentTarget; gitAccess?: boolean;
}) {
  const [repository, setRepository] = useState<ExternalRepositoryRead | null>(null);
  const details = repository?.snapshot;
  const [busy, setBusy] = useState(true);
  const [failure, setFailure] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const focusedDevelopment = useRef<CodeDevelopmentTarget | null>(null);
  const request = useRef<{ snapshot: string; epoch: string; id: string } | null>(null);
  const readSequence = useRef(0);
  const refresh = useCallback(async () => {
    const sequence = ++readSequence.current;
    setBusy(true);
    setFailure('');
    try {
      const value = await client.externalRepository(project);
      if (sequence === readSequence.current) setRepository(value);
    } catch {
      if (sequence === readSequence.current) {
        setRepository(null);
        setFailure('This Git snapshot is unavailable.');
      }
    } finally {
      if (sequence === readSequence.current) setBusy(false);
    }
  }, [client, project]);

  useEffect(() => {
    void refresh();
    return () => { readSequence.current++; };
  }, [refresh, development]);

  async function accept() {
    const snapshot = details?.snapshot;
    const epoch = details?.authority_epoch;
    if (!repository?.access.manage || details?.status !== 'external-staged' || !snapshot || !epoch) return;
    if (request.current?.snapshot !== snapshot || request.current.epoch !== epoch) {
      request.current = { snapshot, epoch, id: newId() };
    }
    setBusy(true); setFailure('');
    try {
      await client.code(project, { action: 'pack-accept', snapshot, authority_epoch: epoch,
        request_id: request.current.id });
      await refresh();
    } catch {
      setFailure('The Home did not confirm acceptance. Retry this snapshot or refresh to review the current one.');
    } finally { setBusy(false); }
  }

  const staged = details?.status === 'external-staged';
  const atCapacity = repository?.atCapacity === true;
  const canWrite = repository?.access.writable === true && !busy && !failure;
  const canManage = repository?.access.manage === true;
  const workBranch = development && UUID.test(development.workId) && workBranchRef(development.workId) === development.ref
    ? development : undefined;
  const hasWorkBranch = !!workBranch && details?.status === 'external' && Object.hasOwn(packRefs(details), workBranch.ref);
  useEffect(() => {
    if (workBranch?.mode !== 'browse' || !details || busy || focusedDevelopment.current === workBranch) return;
    focusedDevelopment.current = workBranch;
    heading.current?.focus();
  }, [workBranch, details, busy]);
  return <div className="external-code repo-page"><Surface className="repo-overview" aria-labelledby="repo-heading">
    <div className="repo-toolbar">
      <h2 id="repo-heading" ref={heading} tabIndex={-1}>{staged ? 'Review Git snapshot' : 'Repository'}</h2>
      <div className="repo-actions">
        <Button variant="quiet" disabled={busy} onClick={() => void refresh()}>Refresh snapshot</Button>
        {gitAccess && details?.status === 'external' && <GitCredentials client={client} project={project}
          writable={canWrite && !atCapacity} cloneUrl={repositoryUrl(project)} />}
      </div>
    </div>
    {busy && !details && <p className="repo-help" role="status">Loading repository…</p>}
    {details && <>
      {workBranch && <div className="repo-work-context">
        {hasWorkBranch ? <p>Work item <strong><bdi>{workBranch.title}</bdi></strong></p>
          : <p role="status">The Work branch is absent from the accepted Git snapshot.</p>}
        {onOpenWork && <Button variant="quiet" onClick={() => onOpenWork(workBranch.workId)}>Return to work item</Button>}
      </div>}
      <RepositoryRefs snapshot={details} client={client} project={project}
        initialReference={hasWorkBranch ? workBranch.ref : undefined}
        browse={details.status === 'external' && !busy && !failure} refresh={() => {
          heading.current?.focus();
          void refresh();
        }} />
      <details className="repo-snapshot"><summary>Snapshot details</summary>
        <p>{details.object_count} Git objects{!staged && <> · Accepted <AcceptedTime milliseconds={details.accepted_at_ms ?? ''} /></>}</p>
        <TextField label="Snapshot SHA-256" value={details.snapshot ?? ''} readOnly spellCheck={false} />
      </details>
      {staged && canManage && <Button variant="primary" disabled={busy} onClick={() => void accept()}>Accept this snapshot</Button>}
      {atCapacity && <p className="repo-help" role="status">This repository reached its {details.generation_limit} update limit. Reviews and Git history are still available.</p>}
    </>}
    {failure && <p role="alert">{failure}</p>}
  </Surface>{details?.status === 'external' && <CodeExternalReview client={client} project={project} writable={canWrite}
      manage={canManage} atCapacity={atCapacity} principal={principal} snapshot={details} refreshSnapshot={refresh}
      initialProposal={initialProposal} onOpenWork={onOpenWork} development={workBranch} />}
  </div>;
}

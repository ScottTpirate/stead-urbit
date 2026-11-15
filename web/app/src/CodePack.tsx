import { useEffect, useRef, useState } from 'react';
import { packRefs, type Fields, type HomeClient } from './api';
import { newId } from './protocol';
import { AcceptedTime } from './AcceptedTime';
import { CopyValue, GitCredentials, repositoryUrl } from './CodeRepository';
import { CodeExternalReview } from './CodeExternalReview';
import { RepoBrowser } from './RepoBrowser';
import { refLabel } from './externalReview';
import { Button, Surface, TextField } from './primitives';

const TAG_PREFIX = '726566732f746167732f';
const shortRef = (key: string) => refLabel(key).replace(/^refs\/(?:heads|tags)\//u, '');

function RepositoryRefs({ snapshot, client, project, browse, refresh }: {
  snapshot: Fields; client: HomeClient; project: string; browse: boolean; refresh: () => void;
}) {
  const [section, setSection] = useState<'branches' | 'tags'>('branches');
  const [selection, setSelection] = useState<{ branches?: string; tags?: string }>({});
  const refs = Object.entries(packRefs(snapshot)).sort(([left], [right]) => {
    if (left === snapshot.head) return -1;
    if (right === snapshot.head) return 1;
    return shortRef(left).localeCompare(shortRef(right));
  });
  const branches = refs.filter(([key]) => !key.startsWith(TAG_PREFIX));
  const tags = refs.filter(([key]) => key.startsWith(TAG_PREFIX));
  const active = section === 'branches' ? branches : tags;
  const selected = active.find(([key]) => key === selection[section]) ?? active[0];
  return <>
    <nav className="repo-ref-tabs" aria-label="Git references">
      <Button variant="quiet" aria-current={section === 'branches' ? 'page' : undefined}
        onClick={() => setSection('branches')}>Branches <span className="repo-count">{branches.length}</span></Button>
      <Button variant="quiet" aria-current={section === 'tags' ? 'page' : undefined}
        onClick={() => setSection('tags')}>Tags <span className="repo-count">{tags.length}</span></Button>
    </nav>
    {selected ? <>
      <div className="repo-ref-tip">
        <div>
          <span>{section === 'branches' ? 'Branch tip' : 'Tag target'}</span>
          <strong><bdi>{shortRef(selected[0])}</bdi></strong>
        </div>
        <div className="repo-tip-actions">
          <code title={selected[1]}>{selected[1].slice(0, 12)}</code>
          <CopyValue key={selected[1]} value={selected[1]} label={section === 'branches' ? 'Copy commit ID' : 'Copy object ID'} />
        </div>
      </div>
      <ul className="repo-ref-list" aria-label={section === 'branches' ? 'Branches' : 'Tags'}>
        {active.map(([key, oid]) => <li key={key}>
          <button type="button" className="repo-ref-row" aria-pressed={key === selected[0]}
            onClick={() => setSelection(current => ({ ...current, [section]: key }))}>
            <span className="repo-ref-name"><bdi>{shortRef(key)}</bdi>{key === snapshot.head && <small>Default</small>}</span>
            <code title={oid}>{oid.slice(0, 12)}</code>
          </button>
        </li>)}
      </ul>
      {browse && snapshot.snapshot && <RepoBrowser key={`${project}/${snapshot.snapshot}/${selected[0]}`} client={client} project={project}
        snapshot={snapshot.snapshot} reference={selected[0]} refresh={refresh} />}
    </> : <p className="repo-ref-empty">No tags yet.</p>}
  </>;
}

export function CodePack({ client, project, manage, writable, principal }: {
  client: HomeClient; project: string; manage: boolean; writable: boolean; principal: string;
}) {
  const [details, setDetails] = useState<Fields | null>(null);
  const [access, setAccess] = useState<{ writable: boolean; manage: boolean } | null>(null);
  const [busy, setBusy] = useState(true);
  const [failure, setFailure] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const request = useRef<{ snapshot: string; epoch: string; id: string } | null>(null);
  useEffect(() => {
    let current = true;
    void client.code(project, { action: 'pack-view' }).then(value => {
      if (current) setDetails(value);
    }).catch(() => {
      if (current) setFailure('This Git snapshot is unavailable.');
    }).finally(() => { if (current) setBusy(false); });
    return () => { current = false; };
  }, [client, project]);

  async function refresh() {
    setBusy(true); setFailure('');
    try {
      const [pack, status] = await Promise.all([client.code(project, { action: 'pack-view' }), client.code(project, { action: 'status' })]);
      setDetails(pack);
      setAccess({ writable: status.write === 'yes', manage: status.manage === 'yes' });
    }
    catch {
      setDetails(null);
      setAccess(null);
      setFailure('This Git snapshot is unavailable.');
    }
    finally { setBusy(false); }
  }

  async function accept() {
    const snapshot = details?.snapshot;
    const epoch = details?.authority_epoch;
    if (!(access?.manage ?? manage) || details?.status !== 'external-staged' || !snapshot || !epoch) return;
    if (request.current?.snapshot !== snapshot || request.current.epoch !== epoch) {
      request.current = { snapshot, epoch, id: newId() };
    }
    setBusy(true); setFailure('');
    try {
      const accepted = await client.code(project, { action: 'pack-accept', snapshot, authority_epoch: epoch,
        request_id: request.current.id });
      setDetails(accepted);
      await refresh();
    } catch {
      setFailure('The Home did not confirm acceptance. Retry this snapshot or refresh to review the current one.');
    } finally { setBusy(false); }
  }

  const staged = details?.status === 'external-staged';
  const atCapacity = !!details?.generation_limit && details.generation === details.generation_limit;
  const canWrite = (access?.writable ?? writable) && !busy && !failure;
  const canManage = access?.manage ?? manage;
  return <div className="external-code repo-page"><Surface className="repo-overview" aria-labelledby="repo-heading">
    <div className="repo-toolbar">
      <h2 id="repo-heading" ref={heading} tabIndex={-1}>{staged ? 'Review Git snapshot' : 'Repository'}</h2>
      <div className="repo-actions">
        <Button variant="quiet" disabled={busy} onClick={() => void refresh()}>Refresh snapshot</Button>
        {details?.status === 'external' && <GitCredentials client={client} project={project}
          writable={canWrite && !atCapacity} cloneUrl={repositoryUrl(project)} />}
      </div>
    </div>
    {busy && !details && <p className="repo-help" role="status">Loading repository…</p>}
    {details && <>
      <RepositoryRefs snapshot={details} client={client} project={project}
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
      manage={canManage} atCapacity={atCapacity} principal={principal} snapshot={details} refreshSnapshot={refresh} />}
  </div>;
}

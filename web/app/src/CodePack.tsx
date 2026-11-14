import { useEffect, useRef, useState } from 'react';
import { packRefs, type Fields, type HomeClient } from './api';
import { newId } from './protocol';
import { AcceptedTime } from './AcceptedTime';
import { GitCredentials } from './CodeRepository';
import { CodeExternalReview } from './CodeExternalReview';
import { refLabel } from './externalReview';
import { Button, Surface, TextField } from './primitives';

export function CodePack({ client, project, manage, writable, principal }: {
  client: HomeClient; project: string; manage: boolean; writable: boolean; principal: string;
}) {
  const [details, setDetails] = useState<Fields | null>(null);
  const [access, setAccess] = useState<{ writable: boolean; manage: boolean } | null>(null);
  const [busy, setBusy] = useState(true);
  const [failure, setFailure] = useState('');
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
    catch { setFailure('This Git snapshot is unavailable.'); }
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
  const refs = details ? Object.entries(packRefs(details)) : [];
  const atCapacity = !!details?.generation_limit && details.generation === details.generation_limit;
  const canWrite = (access?.writable ?? writable) && !busy && !failure;
  const canManage = access?.manage ?? manage;
  return <div className="external-code"><Surface className="repository-panel">
    <h2>Git snapshot</h2>
    {details && <>
      <p>{staged ? 'Ready for maintainer review' : 'Accepted by the project Home'}</p>
      <TextField label="Snapshot SHA-256" value={details.snapshot ?? ''} readOnly spellCheck={false} />
      <p>Default branch <code>{refLabel(details.head ?? '')}</code> · {details.object_count} Git objects</p>
      <details><summary>Refs ({refs.length})</summary><ul>{refs.map(([name, oid]) => <li key={name} style={{overflowWrap:'anywhere'}}>
        <code>{refLabel(name)}</code> <code>{oid}</code>
      </li>)}</ul></details>
      {!staged && <p>Accepted <AcceptedTime milliseconds={details.accepted_at_ms ?? ''} />. An authorized operator can restore this exact snapshot from the private pack store.</p>}
      {staged && canManage && <Button variant="primary" disabled={busy} onClick={() => void accept()}>Accept this snapshot</Button>}
      {atCapacity && <p role="status">This repository reached its {details.generation_limit} update limit. You can still read reviews and fetch Git history. Contact your workspace operator for next steps.</p>}
    </>}
    <Button variant="quiet" disabled={busy} onClick={() => void refresh()}>Refresh snapshot</Button>
    {failure && <p role="alert">{failure}</p>}
  </Surface>
    {details?.status === 'external' && <>
      <CodeExternalReview client={client} project={project} writable={canWrite} manage={canManage} atCapacity={atCapacity}
        principal={principal} snapshot={details} refreshSnapshot={refresh} />
      <GitCredentials client={client} project={project} writable={canWrite && !atCapacity} />
    </>}
  </div>;
}

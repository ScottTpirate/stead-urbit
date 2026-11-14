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
    try { setDetails(await client.code(project, { action: 'pack-view' })); }
    catch { setFailure('This Git snapshot is unavailable.'); }
    finally { setBusy(false); }
  }

  async function accept() {
    const snapshot = details?.snapshot;
    const epoch = details?.authority_epoch;
    if (!manage || details?.status !== 'external-staged' || !snapshot || !epoch) return;
    if (request.current?.snapshot !== snapshot || request.current.epoch !== epoch) {
      request.current = { snapshot, epoch, id: newId() };
    }
    setBusy(true); setFailure('');
    try {
      const accepted = await client.code(project, { action: 'pack-accept', snapshot, authority_epoch: epoch,
        request_id: request.current.id });
      setDetails(accepted);
    } catch {
      setFailure('The Home did not confirm acceptance. Retry this snapshot or refresh to review the current one.');
    } finally { setBusy(false); }
  }

  const staged = details?.status === 'external-staged';
  const refs = details ? Object.entries(packRefs(details)) : [];
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
      {staged && manage && <Button variant="primary" disabled={busy} onClick={() => void accept()}>Accept this snapshot</Button>}
    </>}
    <Button variant="quiet" disabled={busy} onClick={() => void refresh()}>Refresh snapshot</Button>
    {failure && <p role="alert">{failure}</p>}
  </Surface>
    {details?.status === 'external' && <>
      <CodeExternalReview client={client} project={project} writable={writable && !busy && !failure} manage={manage}
        principal={principal} snapshot={details} refreshSnapshot={refresh} />
      <GitCredentials client={client} project={project} writable={writable} />
    </>}
  </div>;
}

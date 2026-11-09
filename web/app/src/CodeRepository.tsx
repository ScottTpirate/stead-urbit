import { useState } from 'react';
import type { Fields, HomeClient } from './api';
import { Button, Surface, TextField } from './primitives';

export function CodeRepository({ client, project, writable }: { client: HomeClient; project: string; writable: boolean }) {
  const [credential, setCredential] = useState<Fields | null>(null);
  const [handle, setHandle] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(false);
  const [notice, setNotice] = useState('');
  async function issue(access: 'read' | 'write') {
    setBusy(true); setFailure(false); setNotice(''); setCredential(null);
    try {
      const next = await client.code(project, { action: 'issue', access });
      setCredential(next); setHandle(next.handle ?? '');
    } catch { setFailure(true); } finally { setBusy(false); }
  }
  async function revoke() {
    setBusy(true); setFailure(false); setNotice('');
    try {
      await client.code(project, { action: 'revoke', handle });
      setHandle(''); setCredential(null); setNotice('Git credential revoked.');
    } catch { setFailure(true); } finally { setBusy(false); }
  }
  return <Surface className="repository-panel">
    <h2>Git repository</h2>
    <TextField label="Clone URL" value={new URL(`/stead/git/${project}.git`, location.origin).href} readOnly />
    <p>Use <code>stead</code> as the username and enter an individual credential when Git prompts for a password.</p>
    <div className="actions">
      <Button disabled={busy} onClick={() => void issue('read')}>Create read credential</Button>
      {writable && <Button disabled={busy} onClick={() => void issue('write')}>Create write credential</Button>}
    </div>
    {credential && <>
      <TextField label="Git credential" value={credential.bearer ?? ''} readOnly autoComplete="off" spellCheck={false} />
      <p>This credential expires within 15 minutes. Copy it before closing this view.</p>
      <Button variant="quiet" onClick={() => setCredential(null)}>Hide credential</Button>
    </>}
    <TextField label="Revocation handle" value={handle} onChange={event => setHandle(event.target.value)} maxLength={64} spellCheck={false} />
    <Button disabled={busy || !/^[a-f0-9]{64}$/u.test(handle)} onClick={() => void revoke()}>Revoke credential</Button>
    {failure && <p role="alert">The Home could not confirm this credential request.</p>}
    {notice && <p role="status">{notice}</p>}
  </Surface>;
}

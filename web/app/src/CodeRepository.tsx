import { useRef, useState } from 'react';
import type { Fields, HomeClient } from './api';
import { Button, Surface, TextField } from './primitives';
import { CodeReview } from './CodeReview';
import './repository.css';

export function repositoryUrl(project: string) {
  return new URL(`/stead/git/${project}.git`, location.origin).href;
}

export function CopyValue({ value, label, onUnavailable }: {
  value: string; label: string; onUnavailable?: () => void;
}) {
  const [result, setResult] = useState<'copied' | 'fallback' | null>(null);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setResult('copied');
    } catch {
      onUnavailable?.();
      setResult('fallback');
    }
  }
  return <>
    <Button variant="quiet" onClick={() => void copy()}>{label}</Button>
    {result && <span className="repo-copy-notice" role="status">
      {result === 'copied' ? 'Copied.' : onUnavailable ? 'Copy the selected text.' : 'Select the full ID to copy it.'}
      {result === 'fallback' && !onUnavailable && <code className="repo-full-id">{value}</code>}
    </span>}
  </>;
}

export function GitCredentials({ client, project, writable, cloneUrl }: {
  client: HomeClient; project: string; writable: boolean; cloneUrl: string;
}) {
  const panel = useRef<HTMLDetailsElement>(null);
  const urlField = useRef<HTMLInputElement>(null);
  const secretField = useRef<HTMLInputElement>(null);
  const [credential, setCredential] = useState<Fields | null>(null);
  const [handle, setHandle] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(false);
  const [notice, setNotice] = useState('');
  async function issue(access: 'read' | 'write') {
    setBusy(true); setFailure(false); setNotice(''); setCredential(null);
    try {
      const next = await client.code(project, { action: 'issue', access });
      if (panel.current?.open) setCredential(next);
      setHandle(next.handle ?? '');
    } catch { setFailure(true); } finally { setBusy(false); }
  }
  async function revoke() {
    setBusy(true); setFailure(false); setNotice('');
    try {
      await client.code(project, { action: 'revoke', handle });
      setHandle(''); setCredential(null); setNotice('Git credential revoked.');
    } catch { setFailure(true); } finally { setBusy(false); }
  }
  return <details className="repo-clone" ref={panel} onToggle={event => {
    if (!event.currentTarget.open) setCredential(null);
  }} onKeyDown={event => {
    if (event.key === 'Escape' && panel.current?.open) {
      event.preventDefault();
      panel.current.open = false;
      panel.current.querySelector('summary')?.focus();
    }
  }}>
    <summary>Clone</summary>
    <div className="repo-clone-panel">
      <h3>Clone with HTTPS</h3>
      <div className="repo-copy-field">
        <TextField ref={urlField} label="Clone URL" value={cloneUrl} readOnly spellCheck={false} />
        <CopyValue value={cloneUrl} label="Copy URL" onUnavailable={() => { urlField.current?.focus(); urlField.current?.select(); }} />
      </div>
      <p>Use <code>stead</code> as the username and your Git credential as the password.</p>
      <div className="actions">
        <Button disabled={busy} onClick={() => void issue('read')}>Create read credential</Button>
        {writable && <Button disabled={busy} onClick={() => void issue('write')}>Create write credential</Button>}
      </div>
      {credential && <>
        <div className="repo-copy-field">
          <TextField ref={secretField} label="Git credential" value={credential.bearer ?? ''} readOnly autoComplete="off" spellCheck={false} />
          <CopyValue value={credential.bearer!} label="Copy credential" onUnavailable={() => { secretField.current?.focus(); secretField.current?.select(); }} />
        </div>
        <p>Expires within 15 minutes. Copy it before closing.</p>
        <Button variant="quiet" onClick={() => setCredential(null)}>Hide credential</Button>
      </>}
      <details className="repo-revoke">
        <summary>Manage credentials</summary>
        <TextField label="Revocation handle" value={handle} onChange={event => setHandle(event.target.value)} maxLength={64} spellCheck={false} />
        <Button disabled={busy || !/^[a-f0-9]{64}$/u.test(handle)} onClick={() => void revoke()}>Revoke credential</Button>
      </details>
      {failure && <p role="alert">The Home could not confirm this credential request.</p>}
      {notice && <p role="status">{notice}</p>}
    </div>
  </details>;
}

export function CodeRepository({ client, project, writable, manage, principal }: {
  client: HomeClient; project: string; writable: boolean; manage: boolean; principal: string;
}) {
  return <div className="repo-page">
    <Surface className="repo-overview" aria-labelledby="repo-heading">
      <div className="repo-toolbar">
        <h2 id="repo-heading">Repository</h2>
        <GitCredentials client={client} project={project} writable={writable} cloneUrl={repositoryUrl(project)} />
      </div>
      <p className="repo-help">Clone the repository to browse files and commit history.</p>
    </Surface>
    <CodeReview client={client} project={project} writable={writable} manage={manage} principal={principal} />
  </div>;
}

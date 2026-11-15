import { useEffect, useRef, useState } from 'react';
import { HomeError, type GitChangesResult, type HomeClient } from './api';
import { Button } from './primitives';
import './repo-browser.css';

type State = { scope: string; path: string } & (
  { phase: 'loading' }
  | { phase: 'ready'; data: GitChangesResult }
  | { phase: 'failed'; reason: string }
);
const statusNames = { A: 'Added', M: 'Modified', D: 'Deleted', T: 'Type changed' } as const;

function pathLabel(hex: string) {
  let name: string;
  try {
    name = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true })
      .decode(Uint8Array.from(hex.match(/../gu) ?? [], byte => Number.parseInt(byte, 16)));
  } catch { return `Raw path: 0x${hex}`; }
  return name.replace(/[\p{Cc}\p{Cf}]/gu, char => `\\u{${char.codePointAt(0)?.toString(16)}}`);
}

export function ReviewChanges({ client, project, snapshot, proposal, revision, base, head }: {
  client: HomeClient; project: string; snapshot: string; proposal: string; revision: string; base: string; head: string;
}) {
  const scope = [project, snapshot, proposal, revision, base, head].join('/');
  const [selection, setSelection] = useState({ scope, path: '' });
  const path = selection.scope === scope ? selection.path : '';
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<State>({ scope, path, phase: 'loading' });
  const title = useRef<HTMLHeadingElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const returnTo = useRef('');
  const current = state.scope === scope && state.path === path ? state : null;
  const data = current?.phase === 'ready' ? current.data : null;

  useEffect(() => {
    const controller = new AbortController();
    setState({ scope, path, phase: 'loading' });
    void client.reviewChanges(project, snapshot, proposal, revision, path ? 'patch' : 'files', path, controller.signal)
      .then(result => {
        if (controller.signal.aborted) return;
        if (result.base !== base || result.head !== head) throw new HomeError('stale_selection');
        setState({ scope, path, phase: 'ready', data: result });
      }).catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ scope, path, phase: 'failed',
          reason: error instanceof HomeError ? error.code : 'changes_unavailable' });
      });
    return () => controller.abort();
  }, [client, project, snapshot, proposal, revision, base, head, scope, path, attempt]);

  useEffect(() => {
    if (data?.status !== 'files' || !returnTo.current) return;
    const target = returnTo.current;
    returnTo.current = '';
    if (document.activeElement === title.current) {
      Array.from(list.current?.querySelectorAll('button') ?? []).find(button => button.dataset.changePath === target)?.focus();
    }
  }, [data]);

  function select(next: string) {
    returnTo.current = next ? '' : path;
    title.current?.focus();
    setSelection({ scope, path: next });
  }
  const reason = current?.phase === 'failed' ? current.reason : '';
  const stale = reason === 'stale_selection';
  const denied = ['denied_or_not_found', 'session_required', 'session_changed', 'resume_required', 'invalid_csrf'].includes(reason);
  const large = reason === 'changes_too_large';

  return <section className="repo-browser review-changes" aria-label="Exact revision changes">
    <div className="repo-browser-bar">
      <h4 ref={title} tabIndex={-1}>{path ? 'File changes' : 'Changed files'}</h4>
      {path && <Button variant="quiet" onClick={() => select('')}>Back to changed files</Button>}
    </div>
    <p className="repo-browser-note">Comparison for proposal revision {revision}. Approval applies to this exact revision.</p>
    {(!current || current.phase === 'loading') && <p className="repo-browser-note" role="status">Loading {path ? 'file changes' : 'changed files'}…</p>}
    {current?.phase === 'failed' && <div className="repo-browser-note">
      <p role="alert">{stale ? 'The proposal or accepted snapshot changed. Refresh the repository and reopen this proposal.'
        : denied ? 'These changes are unavailable for this session.'
          : large ? 'This comparison exceeds the bounded preview. Review the exact commits with Git.'
            : reason === 'changes_busy' ? 'Repository reads are busy. Try again shortly.'
              : 'Changes could not be loaded. Review the exact commits with Git, or try again.'}</p>
      {!stale && !denied && !large && <Button variant="quiet" onClick={() => setAttempt(value => value + 1)}>Retry changes</Button>}
    </div>}
    {data?.status === 'files' && <>
      {data.entries.length ? <ul className="repo-browser-list" aria-label="Changed files" ref={list}>
        {data.entries.map(entry => <li key={entry.path}>
          <button type="button" className="repo-file-row" data-change-path={entry.path} onClick={() => select(entry.path)}>
            <bdi>{pathLabel(entry.path)}</bdi><span className="repo-file-kind">{statusNames[entry.status]}</span>
            {entry.old_mode !== entry.new_mode && <span className="repo-file-kind">{entry.old_mode} → {entry.new_mode}</span>}
          </button>
        </li>)}
      </ul> : !data.truncated && <p className="repo-browser-note">No file differences between these exact commits.</p>}
      {data.truncated && <p role="status" className="repo-browser-note">Only {data.entries.length} changed files are shown. This is an incomplete comparison; use Git to review all changes.</p>}
    </>}
    {data?.status === 'patch' && <>
      <p className="repo-browser-note"><bdi>{pathLabel(data.path)}</bdi></p>
      {data.preview === 'text' ? <>
        {data.sanitized && <p className="repo-browser-note">Control and direction characters are shown as visible escapes.</p>}
        {data.text ? <pre className="repo-file-preview" tabIndex={0} aria-label="Exact file patch">{data.text}</pre>
          : <p className="repo-browser-note">No text changes.</p>}
      </> : <p className="repo-browser-note">{data.preview === 'binary' ? 'Binary or non-UTF-8 file.'
        : data.preview === 'unsupported-type' ? 'Symbolic link, submodule or unsupported file type.'
          : 'This file or patch exceeds the preview limit.'} Review this change with Git; its contents are not shown here.</p>}
    </>}
  </section>;
}

import { useEffect, useRef, useState } from 'react';
import { HomeError, type GitBrowseResult, type GitBrowseView, type HomeClient } from './api';
import { CopyValue } from './CodeRepository';
import { Button } from './primitives';
import './repo-browser.css';

type Location = { path: string[]; view: GitBrowseView };
type BrowseState = { location: Location } & (
  { status: 'loading' | 'unsupported' | 'unavailable' | 'stale' }
  | { status: 'failed'; busy: boolean }
  | { status: 'ready'; data: GitBrowseResult }
);

function decodeName(hex: string) {
  try {
    const decoder = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });
    return decoder.decode(Uint8Array.from(hex.match(/../gu) ?? [], byte => Number.parseInt(byte, 16)));
  } catch { return null; }
}

const CONTROL = /[\p{Cc}\p{Cf}]/u;
function displayName(hex: string) {
  const name = decodeName(hex) ?? `0x${hex}`;
  return name.replace(/[\p{Cc}\p{Cf}]/gu, character => `\\u{${character.codePointAt(0)?.toString(16)}}`);
}

const glyph = { tree: 'folder', file: 'file', symlink: 'link', submodule: 'submodule' } as const;

export function RepoBrowser({ client, project, snapshot, reference, refresh }: {
  client: HomeClient; project: string; snapshot: string; reference: string; refresh: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const listing = useRef<HTMLUListElement>(null);
  const preview = useRef<HTMLPreElement>(null);
  const returnTo = useRef('');
  const [current, setCurrent] = useState<BrowseState>({ location: { path: [], view: 'tree' }, status: 'loading' });
  const { location } = current;

  useEffect(() => {
    const controller = new AbortController();
    function finish(next: BrowseState) {
      if (!controller.signal.aborted) setCurrent(previous => previous.location === location ? next : previous);
    }
    void client.browseCode(project, snapshot, reference, location.path, location.view, controller.signal).then(data => {
      finish({ location, status: 'ready', data });
    }).catch((error: unknown) => {
      const code = error instanceof HomeError ? error.code : '';
      if (code === 'browse_unsupported') finish({ location, status: 'unsupported' });
      else if (code === 'stale_selection') {
        finish({ location, status: 'stale' });
      } else if (['denied_or_not_found', 'session_required', 'session_changed', 'resume_required', 'invalid_csrf'].includes(code)) {
        finish({ location, status: 'unavailable' });
      } else finish({ location, status: 'failed', busy: code === 'browse_busy' });
    });
    return () => controller.abort();
  }, [client, project, snapshot, reference, location]);

  useEffect(() => {
    if (current.status !== 'ready' || current.data.status !== 'tree' || !returnTo.current) return;
    const key = returnTo.current;
    returnTo.current = '';
    if (document.activeElement !== heading.current) return;
    const rows = Array.from(listing.current?.querySelectorAll('button') ?? []);
    rows.find(button => button.dataset.repoEntry === key)?.focus();
  }, [current]);

  function go(path: string[], view: GitBrowseView, child = '') {
    returnTo.current = child;
    heading.current?.focus();
    setCurrent({ location: { path, view }, status: 'loading' });
  }
  function goToAncestor(depth: number) {
    go(location.path.slice(0, depth), 'tree', location.path[depth]);
  }
  function selectContents() {
    const element = preview.current;
    if (!element) return;
    element.focus();
    window.getSelection()?.selectAllChildren(element);
  }

  if (current.status === 'unsupported') return <p className="repo-help">Clone the repository to browse files and commit history.</p>;
  const showPath = current.status !== 'unavailable' && current.status !== 'stale';
  const data = current.status === 'ready' ? current.data : null;
  const segments = location.path.map(decodeName);
  const exactPath = segments.every(name => name !== null && !CONTROL.test(name)) ? segments.join('/') : '';
  return <section className="repo-browser" aria-labelledby="repo-browser-heading">
    <div className="repo-browser-bar">
      <h3 id="repo-browser-heading" ref={heading} tabIndex={-1}>Files</h3>
      {showPath && location.path.length > 0 && <nav aria-label="Repository path" className="repo-browser-path">
        <Button variant="quiet" onClick={() => goToAncestor(0)}>Root</Button>
        {location.path.map((part, index) => <span className="repo-path-part" key={index}>
          <span aria-hidden="true" className="repo-path-separator">/</span>
          {index === location.path.length - 1 ? <bdi aria-current="page">{displayName(part)}</bdi>
            : <Button variant="quiet" onClick={() => goToAncestor(index + 1)}><bdi>{displayName(part)}</bdi></Button>}
        </span>)}
      </nav>}
      {showPath && location.path.length > 0 && <div className="repo-browser-actions">
        <Button variant="quiet" onClick={() => goToAncestor(location.path.length - 1)}>
          {location.view === 'file' ? 'Back to folder' : 'Parent folder'}
        </Button>
        {data && exactPath && <CopyValue value={exactPath} label="Copy path" fallbackLabel="Select the path to copy it." />}
        {data?.status === 'file' && data.preview === 'text' && data.text && <CopyValue
          value={data.text} label="Copy contents" onUnavailable={selectContents} />}
      </div>}
    </div>
    {current.status === 'loading' && <p role="status" className="repo-browser-note">Loading {location.view === 'tree' ? 'folder' : 'file'}…</p>}
    {current.status === 'unavailable' && <p role="alert" className="repo-browser-note">These repository files are unavailable.</p>}
    {current.status === 'stale' && <div className="repo-browser-note repo-browser-error">
      <span role="alert">The accepted snapshot changed.</span><Button variant="quiet" onClick={refresh}>Refresh files</Button>
    </div>}
    {current.status === 'failed' && <div className="repo-browser-note repo-browser-error">
      <span role="alert">{current.busy ? 'File browsing is busy.' : `Couldn’t load this ${location.view === 'tree' ? 'folder' : 'file'}.`}</span>
      <Button variant="quiet" onClick={() => go(location.path, location.view)}>Retry</Button>
    </div>}
    {data?.status === 'tree' && <>
      {data.entries.length > 0 ? <ul ref={listing} className="repo-browser-list" aria-label="Folder contents">
        {data.entries.map(entry => {
          const name = <><span className={`repo-file-icon repo-file-${glyph[entry.kind]}`} aria-hidden="true" />
            <bdi>{displayName(entry.name)}</bdi></>;
          const path = [...location.path, entry.name];
          const withinBrowseLimit = path.length <= 12 && path.reduce((bytes, part) => bytes + part.length / 2, 0) <= 1024;
          return <li key={entry.name}>{withinBrowseLimit && (entry.kind === 'tree' || entry.kind === 'file')
            ? <button type="button" className="repo-file-row"
                data-repo-entry={entry.name}
                onClick={() => go(path, entry.kind === 'tree' ? 'tree' : 'file')}>
                {name}{entry.kind === 'tree' && <span className="repo-file-kind">Folder</span>}
              </button>
            : <span className="repo-file-row">{name}<span className="repo-file-kind">{entry.kind === 'symlink' ? 'Symbolic link'
                : entry.kind === 'submodule' ? 'Submodule' : 'Open with Git'}</span></span>}
          </li>;
        })}
      </ul> : <p className="repo-browser-note">This folder is empty.</p>}
      {data.truncated && <p className="repo-browser-note">Clone to see the rest of this folder.</p>}
    </>}
    {data?.status === 'file' && <>
      {data.preview === 'text' ? data.text ? <pre ref={preview} className="repo-file-preview" tabIndex={0} aria-label="File contents">{data.text}</pre>
        : <p className="repo-browser-note">This file is empty.</p>
        : <p className="repo-browser-note">{data.preview === 'binary' ? 'Binary file.' : 'This file is too large to preview.'} Clone to open it.</p>}
    </>}
  </section>;
}

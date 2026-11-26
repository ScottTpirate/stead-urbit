import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { HomeError, type GitBrowseResult, type GitBrowseView, type HomeClient } from './api';
import { CopyValue } from './CodeRepository';
import { Button } from './primitives';
import { Markdown } from './Markdown';
import './repo-browser.css';

type Location = { path: string[]; view: GitBrowseView };
type BrowseState = { location: Location } & (
  { status: 'loading' | 'unsupported' | 'unavailable' | 'stale' }
  | { status: 'failed'; busy: boolean }
  | { status: 'ready'; data: GitBrowseResult; readme?: {name: string; text: string} }
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

export function repositoryMarkdown(path: readonly string[]): boolean {
  const name = path.length ? decodeName(path[path.length - 1]!) : null;
  return name !== null && !CONTROL.test(name) && /\.(md|markdown)$/iu.test(name);
}

type TreeData = Extract<GitBrowseResult, {status: 'tree'}>;
type TreeEntry = TreeData['entries'][number];
const readmeNames = ['README.md', 'README.markdown', 'README'];

function rootReadme(entries: TreeEntry[]) {
  // Git names are byte strings. Prefer the customary exact spelling, then a stable case variant.
  for (const wanted of readmeNames) {
    const matches = entries.filter(entry => entry.kind === 'file'
      && decodeName(entry.name)?.toLowerCase() === wanted.toLowerCase());
    const file = matches.find(entry => decodeName(entry.name) === wanted)
      ?? matches.sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0)[0];
    if (file) return file;
  }
}

type FileData = Extract<GitBrowseResult, {status: 'file'}>;
export function RepositoryFile({data, path}: {data: FileData; path: readonly string[]}) {
  const readAvailable = data.preview === 'text' && repositoryMarkdown(path);
  const [mode, setMode] = useState<'read' | 'raw'>(readAvailable ? 'read' : 'raw');
  const preview = useRef<HTMLPreElement>(null);
  const selection = useRef(false);
  const mounted = useRef(true);
  const id = useId();
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useLayoutEffect(() => {
    if (!selection.current || mode !== 'raw' || !preview.current) return;
    selection.current = false;
    preview.current.focus();
    window.getSelection()?.selectAllChildren(preview.current);
  });
  function selectContents() {
    if (!mounted.current) return;
    if (mode === 'raw' && preview.current) {
      preview.current.focus(); window.getSelection()?.selectAllChildren(preview.current);
    } else { selection.current = true; setMode('raw'); }
  }
  return <div className="repo-file-reader">
    <div className="repo-file-toolbar">
      {readAvailable && <div role="tablist" aria-label="File display" onKeyDown={event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        const next = event.key === 'Home' ? 'read' : event.key === 'End' ? 'raw' : mode === 'read' ? 'raw' : 'read';
        setMode(next);
        event.currentTarget.querySelector<HTMLButtonElement>(`[data-file-mode="${next}"]`)?.focus();
      }}>
        {(['read', 'raw'] as const).map(value => <Button key={value} variant="quiet" role="tab"
          id={`${id}-${value}`} aria-controls={`${id}-content`} aria-selected={mode === value}
          tabIndex={mode === value ? 0 : -1} data-file-mode={value} onClick={() => setMode(value)}>
          {value === 'read' ? 'Read' : 'Raw'}
        </Button>)}
      </div>}
      <span className="repo-file-readonly">Read-only</span>
      {data.preview === 'text' && data.text && <CopyValue value={data.text} label="Copy contents" onUnavailable={selectContents}/>}
      <details className="repo-file-details"><summary>Details</summary>
        <dl><dt>Commit</dt><dd><code>{data.commit}</code></dd><dt>File size</dt><dd>{data.bytes} bytes</dd></dl>
      </details>
    </div>
    {data.preview === 'text' ? <div id={`${id}-content`} role={readAvailable ? 'tabpanel' : undefined}
      aria-labelledby={readAvailable ? `${id}-${mode}` : undefined}>
      {mode === 'read' ? <div className="repo-file-rendered">
        <Markdown text={data.text ?? ''} origin="repository"/>
        {!data.text && <p className="repo-browser-note">This file is empty.</p>}
        <p className="repo-file-link-note">Links within this repository are shown as text. Open them in a clone.</p>
      </div> : <>
        {!data.text && <p className="repo-browser-note">This file is empty.</p>}
        <pre ref={preview} className="repo-file-preview" tabIndex={0} aria-label="File contents">{data.text ?? ''}</pre>
      </>}
    </div> : <p className="repo-browser-note">{data.preview === 'binary' ? 'Binary file.' : 'This file is too large to preview.'} Clone to open it.</p>}
  </div>;
}

type RepoBrowserProps = {
  client: HomeClient; project: string; snapshot: string; reference: string; refresh: () => void;
};
export function RepoBrowser(props: RepoBrowserProps) {
  const {client, project, snapshot, reference} = props;
  const token = client.currentSessionToken();
  const mode = client.productMode().kind;
  const scope = useRef({client, project, snapshot, reference, token, mode, generation: 0});
  const prior = scope.current;
  if (prior.client !== client || prior.project !== project || prior.snapshot !== snapshot || prior.reference !== reference
    || prior.token !== token || prior.mode !== mode) {
    scope.current = {client, project, snapshot, reference, token, mode, generation: prior.generation + 1};
  }
  if (!token) return <p className="repo-browser-note" role="alert">These repository files are unavailable.</p>;
  if (mode !== 'legacy') return <p className="repo-browser-note">Repository file browsing is unavailable on this Home.</p>;
  return <RepoBrowserScope key={scope.current.generation} {...props} token={token}/>;
}

function RepoBrowserScope({client, project, snapshot, reference, refresh, token}: RepoBrowserProps & {token: object}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const listing = useRef<HTMLUListElement>(null);
  const returnTo = useRef('');
  const [current, setCurrent] = useState<BrowseState>({ location: { path: [], view: 'tree' }, status: 'loading' });
  const { location } = current;
  const [connection, setConnection] = useState({online: navigator.onLine, stale: !navigator.onLine});
  const online = useRef(connection.online);
  // The mounted scope fixes the client, session, project, snapshot and ref. Share a root
  // preview with an explicit open of that file, even if its read is still pending.
  const cachedReadme = useRef<{entry: TreeEntry; commit: string; controller: AbortController; result: Promise<FileData>} | null>(null);
  function forgetReadme() {
    cachedReadme.current?.controller.abort();
    cachedReadme.current = null;
  }
  useEffect(() => forgetReadme, []);
  useEffect(() => {
    function changed() { forgetReadme(); online.current = navigator.onLine; setConnection({online: online.current, stale: true}); }
    window.addEventListener('offline', changed); window.addEventListener('online', changed);
    return () => { window.removeEventListener('offline', changed); window.removeEventListener('online', changed); };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    if (!online.current) return () => controller.abort();
    function finish(next: BrowseState) {
      if (!controller.signal.aborted && client.currentSessionToken() === token && client.productMode().kind === 'legacy') {
        setCurrent(previous => previous.location === location ? next : previous);
      }
    }
    const cached = cachedReadme.current;
    const reuse = location.view === 'file' && location.path.length === 1 && location.path[0] === cached?.entry.name;
    const read = reuse && cached ? cached.result : client.browseCode(project, snapshot, reference,
      location.path, location.view, controller.signal);
    void read.then(async data => {
      finish({ location, status: 'ready', data });
      if (controller.signal.aborted || !online.current || client.currentSessionToken() !== token
        || client.productMode().kind !== 'legacy' || location.path.length || data.status !== 'tree') return;
      const entry = rootReadme(data.entries);
      if (!entry) { forgetReadme(); return; }
      let preview = cachedReadme.current;
      if (!preview || preview.entry.name !== entry.name || preview.entry.oid !== entry.oid || preview.commit !== data.commit) {
        forgetReadme();
        const request = new AbortController();
        const result = client.browseCode(project, snapshot, reference, [entry.name], 'file', request.signal).then(file => {
          if (file.status !== 'file' || file.commit !== data.commit) throw new HomeError('stale_selection');
          return file;
        });
        preview = {entry, commit: data.commit, controller: request, result};
        cachedReadme.current = preview;
      }
      try {
        const file = await preview.result;
        if (cachedReadme.current === preview && online.current && file.preview === 'text') {
          finish({location, status: 'ready', data, readme: {name: entry.name, text: file.text ?? ''}});
        }
      } catch {
        // A missing or unreadable optional README leaves the confirmed folder available.
        if (cachedReadme.current === preview) forgetReadme();
      }
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
  }, [client, project, snapshot, reference, location, token]);

  useEffect(() => {
    if (current.status !== 'ready' || current.data.status !== 'tree' || !returnTo.current) return;
    const key = returnTo.current;
    returnTo.current = '';
    if (document.activeElement !== heading.current) return;
    const rows = Array.from(listing.current?.querySelectorAll('button') ?? []);
    rows.find(button => button.dataset.repoEntry === key)?.focus();
  }, [current]);

  function go(path: string[], view: GitBrowseView, child = '') {
    if (!online.current || client.currentSessionToken() !== token || client.productMode().kind !== 'legacy') return;
    if (connection.stale || (path.length && !(view === 'file' && path.length === 1 && path[0] === cachedReadme.current?.entry.name))) {
      forgetReadme();
    }
    setConnection({online: true, stale: false});
    returnTo.current = child;
    heading.current?.focus();
    setCurrent({ location: { path, view }, status: 'loading' });
  }
  function goToAncestor(depth: number) {
    go(location.path.slice(0, depth), 'tree', location.path[depth]);
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
        <Button variant="quiet" disabled={connection.stale} onClick={() => goToAncestor(0)}>Root</Button>
        {location.path.map((part, index) => <span className="repo-path-part" key={index}>
          <span aria-hidden="true" className="repo-path-separator">/</span>
          {index === location.path.length - 1 ? <bdi aria-current="page">{displayName(part)}</bdi>
            : <Button variant="quiet" disabled={connection.stale} onClick={() => goToAncestor(index + 1)}><bdi>{displayName(part)}</bdi></Button>}
        </span>)}
      </nav>}
      {showPath && location.path.length > 0 && <div className="repo-browser-actions">
        <Button variant="quiet" disabled={connection.stale} onClick={() => goToAncestor(location.path.length - 1)}>
          {location.view === 'file' ? 'Back to folder' : 'Parent folder'}
        </Button>
        {data && exactPath && <CopyValue value={exactPath} label="Copy path" fallbackLabel="Select the path to copy it." />}

      </div>}
    </div>
    {connection.stale && <div className="repo-browser-note repo-browser-error" role="status">
      <span>{connection.online ? 'Connection restored. Refresh files to confirm current access.' : data ? 'Offline. These are the last loaded files.' : 'Offline. Connect to load repository files.'}</span>
      {connection.online && <Button variant="quiet" onClick={() => go(location.path, location.view)}>Refresh files</Button>}
    </div>}
    {!connection.stale && current.status === 'loading' && <p role="status" className="repo-browser-note">Loading {location.view === 'tree' ? 'folder' : 'file'}…</p>}
    {current.status === 'unavailable' && <p role="alert" className="repo-browser-note">These repository files are unavailable.</p>}
    {current.status === 'stale' && <div className="repo-browser-note repo-browser-error">
      <span role="alert">The accepted snapshot changed.</span><Button variant="quiet" disabled={!connection.online} onClick={refresh}>Refresh files</Button>
    </div>}
    {current.status === 'failed' && <div className="repo-browser-note repo-browser-error">
      <span role="alert">{current.busy ? 'File browsing is busy.' : `Couldn’t load this ${location.view === 'tree' ? 'folder' : 'file'}.`}</span>
      <Button variant="quiet" disabled={!connection.online} onClick={() => go(location.path, location.view)}>Retry</Button>
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
                data-repo-entry={entry.name} disabled={connection.stale}
                onClick={() => go(path, entry.kind === 'tree' ? 'tree' : 'file')}>
                {name}{entry.kind === 'tree' && <span className="repo-file-kind">Folder</span>}
              </button>
            : <span className="repo-file-row">{name}<span className="repo-file-kind">{entry.kind === 'symlink' ? 'Symbolic link'
                : entry.kind === 'submodule' ? 'Submodule' : 'Open with Git'}</span></span>}
          </li>;
        })}
      </ul> : <p className="repo-browser-note">This folder is empty.</p>}
      {data.truncated && <p className="repo-browser-note">Clone to see the rest of this folder.</p>}
      {!connection.stale && current.status === 'ready' && current.readme &&
        <section className="repo-root-readme" aria-label="Repository README">
          <h4>{displayName(current.readme.name)}</h4>
          <div className="repo-file-rendered">{current.readme.text
            ? <Markdown text={current.readme.text} origin="repository"/>
            : <p className="repo-browser-note">This file is empty.</p>}</div>
        </section>}
    </>}
    {data?.status === 'file' && <RepositoryFile key={`${data.commit}/${location.path.join('/')}`} data={data} path={location.path}/>}
  </section>;
}

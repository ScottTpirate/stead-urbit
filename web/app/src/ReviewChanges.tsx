import {useEffect, useRef, useState} from 'react';
import {HomeError, type GitChangesResult, type HomeClient} from './api';
import {Button} from './primitives';
import {UnifiedPatch} from './UnifiedPatch';
import './repo-browser.css';

type ReviewProps = {client: HomeClient; project: string; snapshot: string; proposal: string;
  revision: string; base: string; head: string};
type Identity = ReviewProps & {token: object | null; mode: string};
type Stamp = {readonly generation: number};

// An observed scope change permanently retires the prior lifetime, including
// A→B→A and temporary capability loss. Equality of labels cannot revive it.
export class ReviewScopeFence {
  private prior: Identity | undefined;
  private stamp: Stamp = {generation: 0};
  update(next: Identity): Stamp {
    const prior = this.prior;
    if (!prior || prior.client !== next.client || prior.token !== next.token || prior.mode !== next.mode
        || prior.project !== next.project || prior.snapshot !== next.snapshot || prior.proposal !== next.proposal
        || prior.revision !== next.revision || prior.base !== next.base || prior.head !== next.head) {
      this.prior = next; this.stamp = {generation: this.stamp.generation + 1};
    }
    return this.stamp;
  }
  current(stamp: Stamp): boolean { return this.stamp === stamp; }
}

// Selection identity and each request are separate from path text. Retrying or
// returning to the same path cannot publish an earlier response.
export class ReviewReadFence {
  private request: object | undefined;
  begin(): object { return this.request = {}; }
  current(request: object): boolean { return request === this.request; }
  retire(): void { this.request = undefined; }
}

type Location = {readonly path: string};
type State = {location: Location} & ({phase: 'loading'} | {phase: 'ready'; data: GitChangesResult}
  | {phase: 'failed'; reason: string});
const statusNames = {A: 'Added', M: 'Modified', D: 'Deleted', T: 'Type changed'} as const;
const deniedCodes = ['denied_or_not_found', 'session_required', 'session_changed', 'resume_required', 'invalid_csrf'];

function pathLabel(hex: string) {
  let name: string;
  try { name = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true})
    .decode(Uint8Array.from(hex.match(/../gu) ?? [], byte => Number.parseInt(byte, 16))); }
  catch { return `Raw path: 0x${hex}`; }
  return name.replace(/[\p{Cc}\p{Cf}]/gu, char => `\\u{${char.codePointAt(0)?.toString(16)}}`);
}

export function ReviewChanges(props: ReviewProps) {
  const token = props.client.currentSessionToken(), mode = props.client.productMode().kind;
  const fence = useRef(new ReviewScopeFence());
  const stamp = fence.current.update({...props, token, mode});
  if (!token) return <p className="repo-browser-note" role="alert">These changes are unavailable for this session.</p>;
  if (mode !== 'legacy') return <p className="repo-browser-note">Code changes are unavailable on this Home.</p>;
  const current = () => fence.current.current(stamp) && props.client.currentSessionToken() === token
    && props.client.productMode().kind === 'legacy';
  return <ReviewChangesScope key={stamp.generation} {...props} current={current}/>;
}

function ReviewChangesScope({client, project, snapshot, proposal, revision, base, head, current}: ReviewProps & {current: () => boolean}) {
  const [location, setLocation] = useState<Location>({path: ''});
  const [state, setState] = useState<State>({location, phase: 'loading'});
  const [connection, setConnection] = useState({online: navigator.onLine, stale: !navigator.onLine});
  const connectionRef = useRef(connection); connectionRef.current = connection;
  const currentRef = useRef(current); currentRef.current = current;
  const liveLocation = useRef(location); liveLocation.current = location;
  const mounted = useRef(true), requests = useRef(new ReviewReadFence());
  const heading = useRef<HTMLHeadingElement>(null), list = useRef<HTMLUListElement>(null);
  const returnTo = useRef('');
  const visible = state.location === location ? state : undefined;
  const data = visible?.phase === 'ready' ? visible.data : null;
  const reason = visible?.phase === 'failed' ? visible.reason : '';
  const denied = deniedCodes.includes(reason), stale = reason === 'stale_selection', large = reason === 'changes_too_large';
  const unsupported = ['unsupported_operation', 'changes_unsupported'].includes(reason);

  useEffect(() => {
    mounted.current = true;
    function changed() {
      const next = {online: navigator.onLine, stale: true};
      connectionRef.current = next; setConnection(next);
    }
    window.addEventListener('offline', changed); window.addEventListener('online', changed);
    return () => { mounted.current = false; requests.current.retire();
      window.removeEventListener('offline', changed); window.removeEventListener('online', changed); };
  }, []);

  useEffect(() => {
    const controller = new AbortController(), request = requests.current.begin();
    if (!connectionRef.current.online || connectionRef.current.stale) return () => {controller.abort(); requests.current.retire();};
    const live = () => mounted.current && !controller.signal.aborted && requests.current.current(request)
      && currentRef.current() && liveLocation.current === location;
    void client.reviewChanges(project, snapshot, proposal, revision, location.path ? 'patch' : 'files', location.path, controller.signal)
      .then(result => {
        if (!live()) return;
        if (result.base !== base || result.head !== head || result.status !== (location.path ? 'patch' : 'files')
            || (result.status === 'patch' && result.path !== location.path)) throw new HomeError('stale_selection');
        // A response received offline is not a new authorized visible snapshot.
        // Explicit Refresh performs a fresh read when connectivity returns.
        if (connectionRef.current.stale || !navigator.onLine) return;
        setState({location, phase: 'ready', data: result});
      }).catch((error: unknown) => {
        if (!live()) return;
        const reason = error instanceof HomeError ? error.code : 'changes_unavailable';
        setState({location, phase: 'failed', reason});
      });
    return () => { controller.abort(); if (requests.current.current(request)) requests.current.retire(); };
  }, [client, project, snapshot, proposal, revision, base, head, location]);

  useEffect(() => {
    if (data?.status !== 'files' || !returnTo.current) return;
    const target = returnTo.current; returnTo.current = '';
    if (document.activeElement === heading.current && currentRef.current()) {
      Array.from(list.current?.querySelectorAll('button') ?? []).find(button => button.dataset.changePath === target)?.focus();
    }
  }, [data]);

  function select(path: string, refresh = false) {
    if (!mounted.current || !currentRef.current() || !connectionRef.current.online || (!refresh && connectionRef.current.stale)
        || denied || stale || unsupported) return;
    requests.current.retire();
    returnTo.current = path ? '' : location.path;
    heading.current?.focus();
    const next = {path}; liveLocation.current = next; setLocation(next); setState({location: next, phase: 'loading'});
    const nextConnection = {online: true, stale: false}; connectionRef.current = nextConnection; setConnection(nextConnection);
  }
  const canNavigate = connection.online && !connection.stale && !denied && !stale && !unsupported;
  if (!current()) return <p className="repo-browser-note" role="alert">These changes are unavailable for this session.</p>;
  return <section className="repo-browser review-changes" aria-label="Exact revision changes">
    <div className="repo-browser-bar">
      <h4 ref={heading} tabIndex={-1}>{location.path && !denied && !stale ? 'File changes' : 'Changed files'}</h4>
      {location.path && !denied && !stale && !unsupported && <Button variant="quiet" disabled={!canNavigate} onClick={() => select('')}>Back to changed files</Button>}
      {!denied && !stale && !unsupported && <Button variant="quiet" disabled={!connection.online || visible?.phase === 'loading' && !connection.stale}
        onClick={() => select(location.path, true)}>Refresh changes</Button>}
    </div>
    {!denied && !stale && <p className="repo-browser-note">Comparison for proposal revision {revision}. Approval applies to this exact revision.</p>}
    {connection.stale && !denied && !stale && !unsupported && <p className="repo-browser-note" role="status">{connection.online
      ? 'Connection restored. Refresh changes to confirm current access.'
      : data ? 'Offline. These are the last loaded changes.' : 'Offline. Connect to load changes.'}</p>}
    {!connection.stale && (!visible || visible.phase === 'loading') && <p className="repo-browser-note" role="status">Loading {location.path ? 'file changes' : 'changed files'}…</p>}
    {visible?.phase === 'failed' && <div className="repo-browser-note">
      <p role="alert">{stale ? 'The proposal or accepted snapshot changed. Refresh the repository and reopen this proposal.'
        : denied ? 'These changes are unavailable for this session.'
          : unsupported ? 'Change previews are unavailable on this Home.'
            : large ? 'This comparison exceeds the bounded preview. Review the exact commits with Git.'
              : reason === 'changes_busy' ? 'Repository reads are busy. Try again shortly.'
                : 'Changes could not be loaded. Review the exact commits with Git, or refresh changes.'}</p>
    </div>}
    {data?.status === 'files' && <>
      {data.entries.length ? <ul className="repo-browser-list" aria-label="Changed files" ref={list}>
        {data.entries.map(entry => <li key={entry.path}><button type="button" className="repo-file-row" data-change-path={entry.path}
          disabled={!canNavigate} onClick={() => select(entry.path)}><bdi>{pathLabel(entry.path)}</bdi>
          <span className="repo-file-kind">{statusNames[entry.status]}</span>
          {entry.old_mode !== entry.new_mode && <span className="repo-file-kind">{entry.old_mode} → {entry.new_mode}</span>}
        </button></li>)}
      </ul> : !data.truncated && <p className="repo-browser-note">No file differences between these exact commits.</p>}
      {data.truncated && <p role="status" className="repo-browser-note">Only {data.entries.length} changed files are shown. This is an incomplete comparison; use Git to review all changes.</p>}
    </>}
    {data?.status === 'patch' && <>
      <p className="repo-browser-note"><bdi>{pathLabel(data.path)}</bdi></p>
      {data.preview === 'text' ? <UnifiedPatch key={data.path} text={data.text ?? ''} sanitized={!!data.sanitized}/>
        : <p className="repo-browser-note">{data.preview === 'binary' ? 'Binary or non-UTF-8 file.'
          : data.preview === 'unsupported-type' ? 'Symbolic link, submodule or unsupported file type.'
            : 'This file or patch exceeds the preview limit.'} Review this change with Git; its contents are not shown here.</p>}
    </>}
  </section>;
}

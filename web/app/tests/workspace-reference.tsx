// Synthetic workspace fixture. All Home responses are supplied by the test.
import {StrictMode, useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {HomeClient, HomeError} from '../src/api';
import {WorkspaceView, type WorkspaceQueryView, type WorkspaceSearch} from '../src/WorkspaceView';
import {Button} from '../src/primitives';
import {encodeProductRoute} from '../src/productRoutes';
import '../src/style.css';
import './workspace-reference.css';

const client = new HomeClient();
function Reference() {
  const [session, setSession] = useState('');
  const [view, setView] = useState<WorkspaceQueryView>('my-work');
  const [search, setSearch] = useState<WorkspaceSearch>({draft: '', term: ''});
  const [locked, setLocked] = useState(false);
  const [mounted, setMounted] = useState(true);
  const [opened, setOpened] = useState('');
  const [error, setError] = useState('');
  const [restore, setRestore] = useState<{scroll: number; selection?: string}>();
  const opening = useRef<Promise<void> | null>(null);
  const resumeRequest = useRef(0);
  client.onInvalidated = () => { setSession(''); setOpened(''); };
  async function resume() {
    const request = ++resumeRequest.current;
    try { const person = await client.resume(); if (request === resumeRequest.current) setSession(person.session_audit_id!); }
    catch (failure) { if (request === resumeRequest.current) setError(failure instanceof HomeError ? failure.code : 'fixture_error'); }
  }
  useEffect(() => { void resume(); }, []);
  return <main className="workspace-reference">
    <p className="workspace-reference-notice">Synthetic workspace reference · Mocked Home · No real account or business data</p>
    <div className="workspace-reference-controls">
      <Button onClick={() => setView('my-work')}>Show My work</Button>
      <Button onClick={() => setView('workspace-search')}>Show Search</Button>
      <Button onClick={() => void resume()}>Resume fixture session</Button>
      <Button onClick={() => setMounted(false)}>Hide workspace</Button>
      <Button onClick={() => { setRestore({scroll: 0, selection: opened || '#work/019939ba-4000-7000-8000-000000000001/019939ba-4000-7000-8000-000000000101'}); setMounted(true); }}>Restore workspace</Button>
      <label><input type="checkbox" checked={locked} onChange={event => setLocked(event.target.checked)}/>Pending navigation</label>
    </div>
    <p aria-label="Fixture opened resource">{opened || 'No resource opened'}</p>
    <p aria-label="Fixture error">{error || 'No fixture error'}</p>
    {session && mounted && <WorkspaceView client={client} view={view} search={search} onSearchChange={setSearch}
      sessionKey={session} locked={locked} openingWatchRef={opening} restoreNavigation={restore}
      onError={failure => setError(failure instanceof HomeError ? failure.code : 'fixture_error')}
      onOpen={row => setOpened(encodeProductRoute(row.kind === 'work'
        ? {kind: 'work', project: row.project_id!, item: row.resource_id!}
        : {kind: 'doc', project: row.project_id!, collection: row.container_id!, document: row.resource_id!}))}/>}
  </main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><Reference/></StrictMode>);

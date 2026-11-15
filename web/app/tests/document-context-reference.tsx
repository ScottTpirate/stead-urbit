// Synthetic fixture: the runner supplies every Home response.
import {StrictMode, useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {HomeClient, HomeError} from '../src/api';
import {DocumentContext} from '../src/DocumentContext';
import {Button} from '../src/primitives';
import {encodeProductRoute} from '../src/productRoutes';
import '../src/style.css';
import './workspace-reference.css';

const client = new HomeClient();
const id = (number: number) => '019939ba-4000-7000-8000-' + String(number).padStart(12, '0');
function Reference() {
  const [session, setSession] = useState('');
  const [document, setDocument] = useState(id(301));
  const [revision, setRevision] = useState(0);
  const [locked, setLocked] = useState(false);
  const [opened, setOpened] = useState('');
  const [error, setError] = useState('');
  const request = useRef(0);
  client.onInvalidated = () => { setSession(''); setOpened(''); };
  async function resume() {
    const ticket = ++request.current;
    try { const person = await client.resume(); if (ticket === request.current) setSession(person.session_audit_id!); }
    catch (failure) { if (ticket === request.current) setError(failure instanceof HomeError ? failure.code : 'fixture_error'); }
  }
  useEffect(() => { void resume(); }, []);
  return <main className="workspace-reference">
    <p className="workspace-reference-notice">Synthetic document relationships · Mocked Home · No real account or business data</p>
    <div className="workspace-reference-controls">
      <Button onClick={() => setDocument(value => value === id(301) ? id(302) : id(301))}>Switch document</Button>
      <Button onClick={() => setRevision(value => value + 1)}>Receive current revision</Button>
      <Button onClick={() => void resume()}>Resume fixture session</Button>
      <label><input type="checkbox" checked={locked} onChange={event => setLocked(event.target.checked)}/>Pending edit or navigation</label>
    </div>
    <p aria-label="Fixture opened resource">{opened || 'No resource opened'}</p>
    <p aria-label="Fixture error">{error || 'No fixture error'}</p>
    <h1>Accepted document</h1><p>This fixture displays only authorized relationship responses supplied by the runner.</p>
    {session && <DocumentContext key={session} client={client} project={id(1)} collection={id(201)} document={document}
      sessionKey={session} viewRevision={revision} locked={locked}
      onOpenWork={work => setOpened(encodeProductRoute({kind: 'work', project: id(1), item: work}))}
      onError={failure => setError(failure instanceof HomeError ? failure.code : 'fixture_error')}/>}
  </main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><Reference/></StrictMode>);

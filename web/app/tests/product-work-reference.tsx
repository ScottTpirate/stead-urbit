// Inactive UI reference with a deliberately synthetic in-memory transport.
// No Home, native identity, accepted proof or runtime capability is exercised.
import {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ProductWorkClient} from '../src/productClient';
import {parseProductCommand, productCommandDigest, type ProductCommand, type ProductComment, type ProductReceipt, type ProductWorkDetail as Work} from '../src/productProtocol';
import {canonical} from '../src/protocol';
import {ProductWorkComposer} from '../src/productWorkComposer';
import {ProductWorkDetail} from '../src/productWorkDetail';
import type {ProductWorkDraft, ProductWorkEnvironment, ProductWorkReadiness} from '../src/productWorkState';
import {Button} from '../src/primitives';
import '../src/style.css';
import './product-work-reference.css';

const id = (n: number) => '019939ba-4000-7000-8000-' + String(n).padStart(12, '0');
const initial: Work = {kind: 'work', project_id: id(100), resource_id: id(101), container_id: '', resource_revision: '3', work_revision: '1',
  execution_contract_protocol: 'stead.work-contract/2', execution_contract_revision: '1', execution_contract_digest: 'a'.repeat(64), discussion_sequence: '1',
  title: 'Guide', description: 'Saved purpose', acceptance_criteria: 'Reviewed', type: 'task', status: 'todo', priority: 'none',
  owner_principal_id: '', worker_principal_id: '', owner_display_name: '', worker_display_name: '', blocked_reason: '', required_outcomes: '{}',
  completion_basis: '', completion_principal_id: '', completion_request_id: '', completion_note: '', legacy_assignment_pending: 'no',
  legacy_assignee_principal_id: '', legacy_assignee_display_name: '', legacy_blocked_pending: 'no', legacy_blocked_status: '', legacy_prior_status: ''};
const target = {kind: 'document' as const, project_id: id(100), collection_id: id(200), document_id: id(201), expected_revision: '1', base_markdown_sha256: 'c'.repeat(64)};
const note = (sequence: string, body: string, request_id = id(300)): ProductComment => ({kind: 'comment', project_id: id(100), work_id: id(101), sequence,
  body, principal_id: id(102), display_name: 'Alice', identity_ship: '~bus', request_id, accepted_at_ms: '2000', legacy_comment_revision: ''});
const observation = {sent: [] as string[], acceptedCallbacks: 0, holding: false};
Object.assign(window, {productWorkReference: observation});
function Reference() {
  const serverEpoch = useRef('1');
  const [epoch, setEpoch] = useState('1');
  const session = useRef('session-one'), server = useRef<Work>(initial), serverComments = useRef([note('1', 'Saved discussion')]);
  const receipts = useRef(new Map<string, string>()), mode = useRef('normal'), held = useRef<(() => void) | null>(null);
  const drafts = useRef(new Map<string, ProductWorkDraft>());
  const [snapshot, setSnapshot] = useState({work: initial, sessionKey: 'session-one', authorityEpoch: '1'});
  const [comments, setComments] = useState(serverComments.current);
  const [view, setView] = useState<'detail' | 'composer' | 'closed'>('detail');
  const [access, setAccess] = useState<ProductWorkEnvironment['access']>('writable');
  const [supported, setSupported] = useState(true), [revision, setRevision] = useState(1), [sessionKey, setSessionKey] = useState(session.current);
  const [readiness, setReadiness] = useState<ProductWorkReadiness['state']>('unsupported');
  const client = useRef<ProductWorkClient | null>(null);
  if (!client.current) client.current = new ProductWorkClient({currentSession: () => session.current,
    query: async () => { throw new Error('The synthetic reference does not query a Home'); }, command: async bytes => {
      observation.sent.push(bytes); const command = parseProductCommand(bytes), known = receipts.current.get(command.request_id); if (known) return known;
      const selected = mode.current; mode.current = 'normal';
      if (selected === 'conflict') server.current = {...server.current, work_revision: '2', priority: 'urgent'};
      if (selected === 'epoch-conflict') serverEpoch.current = '2';
      let error = selected === 'conflict' ? 'revision_conflict' : selected === 'epoch-conflict' ? 'authority_epoch_conflict' : '';
      if (!error) {
        const before = server.current;
        if (command.operation === 'work.create') server.current = {...initial, ...command.payload, resource_id: command.resource_id,
          required_outcomes: canonical(command.payload.required_outcomes), resource_revision: '1', work_revision: '1', execution_contract_revision: '1', discussion_sequence: '0'};
        if (command.operation === 'work.update-properties') server.current = {...before, ...command.payload, work_revision: String(BigInt(before.work_revision) + 1n)};
        if (command.operation === 'work.update-contract') server.current = {...before, ...command.payload, required_outcomes: canonical(command.payload.required_outcomes),
          execution_contract_revision: String(BigInt(before.execution_contract_revision) + 1n), execution_contract_digest: 'b'.repeat(64)};
        if (command.operation === 'work.comment') {
          const sequence = String(BigInt(before.discussion_sequence) + 1n); server.current = {...before, discussion_sequence: sequence};
          serverComments.current = [...serverComments.current, {...note(sequence, command.payload.body, command.request_id), work_id: command.resource_id}];
        }
        if (command.operation === 'work.resolve-legacy-blocked') server.current = {...before, status: command.payload.status, blocked_reason: command.payload.blocked_reason,
          legacy_blocked_pending: 'no', work_revision: String(BigInt(before.work_revision) + 1n)};
        if (command.operation === 'work.resolve-legacy-assignee') server.current = {...before, ...command.payload, legacy_assignment_pending: 'no', work_revision: String(BigInt(before.work_revision) + 1n)};
        if (command.operation === 'work.complete') server.current = {...before, status: 'done', completion_basis: command.payload.basis,
          completion_note: command.payload.note, completion_principal_id: id(102), completion_request_id: command.request_id, work_revision: String(BigInt(before.work_revision) + 1n)};
      }
      const current = server.current;
      const response: ProductReceipt = {protocol: 'stead.receipt/4', status: error ? 'rejected' : 'accepted', request_id: command.request_id, canonical_sha256: await productCommandDigest(command),
        project_id: command.project_id, resource_id: command.resource_id, authority_epoch: command.authority_epoch, operation: command.operation,
        principal_id: id(102), recorded_at_ms: '2000', error, expected: command.expected,
        resulting: {work_revision: current.work_revision, execution_contract_revision: current.execution_contract_revision, execution_contract_digest: current.execution_contract_digest, discussion_sequence: current.discussion_sequence}};
      const raw = JSON.stringify(response); receipts.current.set(command.request_id, raw);
      if (selected === 'lost') throw new Error('Synthetic response loss after synthetic acceptance');
      if (selected === 'held') { observation.holding = true; await new Promise<void>(resolve => { held.current = resolve; }); observation.holding = false; }
      return raw;
    }});
  const refresh = () => { setEpoch(serverEpoch.current); setSnapshot({work: server.current, sessionKey: session.current, authorityEpoch: serverEpoch.current}); setComments([...serverComments.current]); };
  const resourceId = view === 'composer' ? id(111) : snapshot.work.resource_id;
  const draftKey = (resource: string, token: string) => resource + '/' + token;
  const environment: ProductWorkEnvironment = {client: client.current, scope: {projectId: id(100), resourceId, authorityEpoch: epoch}, sessionKey, supported, access, online: true,
    actor: {principalId: id(102), kind: 'person'}, people: {state: 'ready', projectId: id(100), sessionKey, values: [
      {principalId: id(102), displayName: 'Alice', kind: 'person', active: true}, {principalId: id(103), displayName: 'Writer agent', kind: 'agent', active: true}]},
    documents: {state: 'ready', projectId: id(100), sessionKey, values: [{label: 'Shared guide', visibility: 'shared', target: {...target, expected_revision: String(revision), base_markdown_sha256: (revision === 1 ? 'c' : 'd').repeat(64)}}]},
    restoredDraft: drafts.current.get(draftKey(resourceId, sessionKey)), onDraftState: draft => drafts.current.set(draftKey(draft.resourceId, draft.sessionKey), draft),
    onRefresh: refresh, onAccepted: (prepared, receipt) => { observation.acceptedCallbacks++; refresh(); if (prepared.command.operation === 'work.create' && receipt.status === 'accepted') setView('detail'); }};
  return <main className="product-reference"><h1>Reserved Work interaction reference</h1><p>Explicitly synthetic responses. This does not connect to a Home.</p>
    <section aria-label="Reference controls" className="product-reference-controls">
      <Button onClick={() => setView('composer')}>New work</Button><Button onClick={() => setView('detail')}>Reopen detail</Button>
      <Button onClick={() => { mode.current = 'lost'; }}>Lose next response</Button><Button onClick={() => { mode.current = 'conflict'; }}>Conflict next response</Button>
      <Button onClick={() => { mode.current = 'epoch-conflict'; }}>Change access before response</Button>
      <Button onClick={() => { mode.current = 'held'; }}>Hold next response</Button><Button onClick={() => { held.current?.(); held.current = null; }}>Release held response</Button>
      <Button onClick={() => setAccess('revoked')}>Revoke access</Button><Button onClick={() => setAccess('writable')}>Restore access</Button>
      <Button onClick={() => { session.current = 'session-two'; setSessionKey(session.current); }}>Change session</Button>
      <Button onClick={() => setSnapshot({...snapshot, work: {...initial, resource_id: id(112), title: 'Other work'}})}>Switch to other work</Button>
      <Button onClick={() => setSnapshot({...snapshot, work: server.current})}>Return to original work</Button>
      <Button onClick={() => setSupported(false)}>Unsupported Home</Button><Button onClick={() => setRevision(2)}>Advance Doc choice</Button>
      <Button onClick={() => { server.current = {...initial, status: 'legacy-blocked', legacy_blocked_pending: 'yes', legacy_blocked_status: 'blocked',
        legacy_assignment_pending: 'yes', legacy_assignee_principal_id: id(103), legacy_assignee_display_name: 'Old assignee'}; refresh(); }}>Load legacy work</Button>
      <Button onClick={() => { server.current = {...server.current, required_outcomes: canonical({[id(401)]: target})}; refresh(); }}>Require Doc output</Button>
      <Button onClick={() => setReadiness('ready')}>Outputs accepted</Button>
    </section>
    {view === 'composer' && <ProductWorkComposer {...environment} open onClose={() => setView('closed')}/>}
    {view === 'detail' && <ProductWorkDetail {...environment} snapshot={snapshot} mode="page" onClose={() => setView('closed')}
      comments={{state: 'ready', rows: comments, projectId: id(100), resourceId: snapshot.work.resource_id, sessionKey: snapshot.sessionKey, cursor: '', onNext: () => {}, onRefresh: refresh}}
      completionReadiness={{state: readiness, projectId: id(100), resourceId: snapshot.work.resource_id, sessionKey,
        executionContractRevision: snapshot.work.execution_contract_revision, executionContractDigest: snapshot.work.execution_contract_digest}}/>}
  </main>;
}
createRoot(document.getElementById('root')!).render(<Reference/>);

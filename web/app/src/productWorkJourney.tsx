import {useEffect, useRef, useState} from 'react';
import {HomeError, type Fields, type HomeClient} from './api';
import {Button, EmptyState, LoadingState, OutcomeState} from './primitives';
import {newId} from './protocol';
import {ProductWorkComposer} from './productWorkComposer';
import {ProductWorkDetail} from './productWorkDetail';
import {productStatusLabels} from './productWorkFields';
import {makeProductWorkDraft, type ProductWorkEnvironment, type ProductWorkReadiness} from './productWorkState';
import {productDetailOutcomes, type DocumentOutcome, type ProductComment, type ProductPrincipal, type ProductWorkDetail as Work, type ProductWorkPreview} from './productProtocol';
import {DocChangeList, DocChangeReview} from './docChangeReview';
import {DocChangeReviewAdapter, docReviewSubmitter, mapDocReviewList, type LoadedDocReview} from './docChangeReviewAdapter';
import {DocChangeProposal} from './docChangeProposal';
import {currentProposalPin, journeyActor, journeyCompletion, journeyDocumentKey, journeyDocuments, journeyPeople, journeyProject, journeyRoster,
  ProductJourneyDraftStore, type DocProposalDraft, type JourneyDocuments, type ProductJourneySelection} from './productJourneyState';
import {readProductWorkEndpoint} from './productJourneyState';
import {WorkContext} from './WorkContext';
import type {DocReviewScope} from './docChangeReviewState';
import type {PreparedDocChangeCommand} from './docChangeClient';
import type {DocChangeReceipt, DocChangePreview} from './docChangeReadProtocol';
import './productWorkJourney.css';

export type ProductWorkJourneyProps = {client: HomeClient; project: {id: string; title: string; authorityEpoch: string; role: string};
  sessionKey: string; principalId: string; online: boolean; locked?: boolean; selection: ProductJourneySelection; drafts: ProductJourneyDraftStore;
  onDraftChange: () => void; onNavigate: (selection: ProductJourneySelection) => void; onOpenDoc: (target: {collectionId: string; documentId: string}) => void;
  onProjectRefresh: (current: Fields) => void; onAccessChanged: () => void; onProjectDenied?: () => void; onRouteDenied?: () => void; refreshRevision?: number};
type ChangeList = ReturnType<typeof mapDocReviewList>;
type Snapshot = {key: string; owner?: object; phase: 'loading' | 'ready' | 'failed' | 'revoked'; project?: Fields; rows?: readonly ProductWorkPreview[]; cursor?: string;
  work?: Work; comments?: readonly ProductComment[]; commentCursor?: string; commentGeneration?: string; changesGeneration?: string; people?: readonly ProductPrincipal[]; documents?: JourneyDocuments;
  readiness?: ProductWorkReadiness; changes?: ChangeList; review?: LoadedDocReview; results?: readonly DocChangePreview[]; resultCursor?: string; resultGeneration?: string; readToken?: object; message?: string};
const failureCode = (error: unknown) => error && typeof error === 'object' && 'code' in error ? String(error.code) : '';
const identityKey = (props: ProductWorkJourneyProps) => JSON.stringify([props.project.id, props.sessionKey]);
const routeKey = (selection: ProductJourneySelection) => JSON.stringify(selection);
export function ProductWorkJourney(props: ProductWorkJourneyProps) {
  if (props.client.productMode().kind !== 'native-human-doc') return <OutcomeState state="unsupported_operation" description="Work and Doc review are unavailable on this Home."/>;
  return <Journey key={identityKey(props)} {...props}/>;
}
function Journey(props: ProductWorkJourneyProps) {
  const selectedKey = routeKey(props.selection), key = JSON.stringify([identityKey(props), selectedKey]);
  const [snapshot, setSnapshot] = useState<Snapshot>({key, phase: 'loading'}), [revision, setRevision] = useState(0), [stale, setStale] = useState(false);
  const [creating, setCreating] = useState<string | undefined>(() => props.drafts.newWork(props.project.id)?.resourceId), [composerOpen, setComposerOpen] = useState(false),
    [proposal, setProposal] = useState<DocProposalDraft | undefined>(() => props.selection.kind === 'list' ? undefined : props.drafts.workProposal(props.project.id, props.selection.workId)), [proposalOpen, setProposalOpen] = useState(false);
  const generation = useRef(0), latest = useRef(props), mounted = useRef(true), nextWorkCursor = useRef(''); latest.current = props;
  const stamp = JSON.stringify([key, props.online, revision, props.refreshRevision]), fence = useRef({stamp, client: props.client});
  if (fence.current.stamp !== stamp || fence.current.client !== props.client) fence.current = {stamp, client: props.client};
  const owner = fence.current;
  const adapter = useRef<{client: HomeClient; value: DocChangeReviewAdapter} | undefined>(undefined);
  const endpointReader = useRef({client: props.client, read: (project: string, work: string) => readProductWorkEndpoint(props.client, project, work)});
  if (endpointReader.current.client !== props.client) endpointReader.current = {client: props.client, read: (project, work) => readProductWorkEndpoint(props.client, project, work)};
  if (!adapter.current || adapter.current.client !== props.client) adapter.current = {client: props.client, value: new DocChangeReviewAdapter(props.client.docChanges,
    (scope, sessionKey) => {
      const active = latest.current, selected = active.selection;
      if (mounted.current && active.sessionKey === sessionKey && scope.projectId === active.project.id && selected.kind !== 'list'
        && scope.workId === selected.workId && (selected.kind !== 'doc-change' || scope.changeId === selected.changeId)) {
        setSnapshot({key: JSON.stringify([identityKey(active), routeKey(selected)]), owner: fence.current, phase: 'revoked'}); active.onAccessChanged();
      }
    })};
  const notifyDraft = () => props.onDraftChange();
  const refresh = () => { nextWorkCursor.current = ''; setStale(false); setRevision(value => value + 1); };
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; generation.current++; adapter.current?.value.cancel(); }; }, []);
  useEffect(() => {
    setComposerOpen(false); setProposalOpen(false);
    setProposal(value => props.selection.kind === 'list' ? undefined : value?.scope.workId === props.selection.workId ? value
      : props.drafts.workProposal(props.project.id, props.selection.workId));
  }, [selectedKey]);
  useEffect(() => {
    const focus = () => { if (document.visibilityState !== 'visible' || latest.current.locked || props.drafts.currentPending(props.project.id)) return;
      if (props.drafts.hasDraft(props.project.id)) setStale(true); else refresh(); };
    window.addEventListener('focus', focus); return () => window.removeEventListener('focus', focus);
  }, [props.drafts, props.project.id]);
  useEffect(() => {
    const id = ++generation.current, token = props.client.currentSessionToken();
    const active = () => mounted.current && fence.current === owner && generation.current === id && props.client.currentSessionToken() === token;
    const current = () => { if (!active()) throw new HomeError('session_changed'); };
    if (!props.online) { setStale(true); return; }
    setSnapshot({key, owner, phase: 'loading'});
    let readingProject = true;
    void (async () => {
      const project = await journeyProject(props.client, props.project.id, current); current(); props.onProjectRefresh(project);
      readingProject = false;
      const writable = ['contributor', 'maintainer'].includes(project.role!);
      const workId = props.selection.kind === 'list' ? '' : props.selection.workId;
      const cursor = workId ? '' : nextWorkCursor.current; nextWorkCursor.current = '';
      const view = await props.client.productWork.readWork({request_id: newId(), project_id: props.project.id, resource_id: workId, cursor}); current();
      if (view.status === 'rejected') throw new HomeError(view.error);
      if (view.kind !== 'work' || view.authority_epoch !== project.authority_epoch) throw new HomeError('stale_cursor');
      const work = workId ? view.rows[0] as Work : undefined;
      if (work && !('description' in work)) throw new HomeError('invalid_response');
      const base: Snapshot = {key, owner, phase: 'ready', project, readToken: Object.freeze({}), ...(work ? {work} : {rows: view.rows as readonly ProductWorkPreview[], cursor: view.cursor})};
      const people = writable ? await journeyRoster(props.client, props.project.id, project.authority_epoch!, current) : []; current(); base.people = people;
      if (props.selection.kind === 'doc-change') {
        base.review = await adapter.current!.value.load({scope: {projectId: props.project.id, workId: props.selection.workId, changeId: props.selection.changeId},
          sessionKey: props.sessionKey, ...(props.selection.result ? {result: props.selection.result} : {})}); current();
        const versions = await props.client.docChanges.readResults({request_id: newId(), project_id: props.project.id, work_id: workId, change_id: props.selection.changeId}); current();
        if (versions.status === 'rejected') throw new HomeError(versions.error);
        if (versions.kind !== 'results' || versions.authority_epoch !== project.authority_epoch) throw new HomeError('stale_cursor');
        base.results = versions.rows; base.resultCursor = versions.cursor; base.resultGeneration = versions.generation;
      } else {
        // Choices are optional. A failed picker read never makes a complete list
        // out of a partial scan and never blocks reading already authorized Work.
        if (writable) {
          try { base.documents = await journeyDocuments(props.client, props.project.id, project.authority_epoch!, current); }
          catch (error) { current(); if (failureCode(error) === 'denied_or_not_found') throw error; }
        }
        if (work) {
          const comments = await props.client.productWork.readComments({request_id: newId(), project_id: props.project.id, resource_id: work.resource_id}); current();
          if (comments.status === 'rejected') throw new HomeError(comments.error);
          if (comments.kind !== 'comments' || comments.authority_epoch !== project.authority_epoch) throw new HomeError('stale_cursor');
          base.comments = comments.rows; base.commentCursor = comments.cursor; base.commentGeneration = comments.generation;
          const completion = await props.client.productWork.readCompletion({request_id: newId(), project_id: props.project.id, resource_id: work.resource_id}); current();
          if (completion.status === 'rejected') throw new HomeError(completion.error);
          if (completion.kind !== 'completion') throw new HomeError('invalid_response');
          base.readiness = journeyCompletion(completion, work, props.sessionKey, project.authority_epoch!);
          const changes = await props.client.docChanges.readChanges({request_id: newId(), project_id: props.project.id, work_id: work.resource_id}); current();
          if (changes.status === 'rejected') throw new HomeError(changes.error);
          base.changes = mapDocReviewList(changes, {projectId: props.project.id, workId: work.resource_id, sessionKey: props.sessionKey});
          base.changesGeneration = changes.generation;
        }
      }
      current(); setSnapshot(base); setStale(false);
    })().catch(error => {
      if (!active()) return;
      const denied = failureCode(error) === 'denied_or_not_found';
      setSnapshot({key, owner, phase: denied ? 'revoked' : 'failed', message: failureCode(error) === 'stale_cursor'
        ? 'This view changed. Refresh to start a current page.' : 'This view could not be refreshed. Your local drafts are kept.'});
      if (denied) { if (readingProject) props.onProjectDenied?.(); else props.onRouteDenied?.(); }
    });
    return () => { generation.current++; adapter.current?.value.cancel(); };
  }, [key, selectedKey, props.online, revision, props.refreshRevision, props.client]);
  const visible = snapshot.key === key && snapshot.owner === owner && snapshot.phase === 'ready' ? snapshot : undefined;
  const project = visible?.project, work = visible?.work, currentAccess = project && ['contributor', 'maintainer'].includes(project.role!) ? 'writable' : 'read-only';
  const unavailable = !!props.locked || !props.online || stale || !visible;
  const workId = composerOpen ? creating ?? '' : work?.resource_id ?? '';
  const environment: ProductWorkEnvironment = {client: props.client.productWork, scope: {projectId: props.project.id, resourceId: workId,
    authorityEpoch: project?.authority_epoch ?? props.project.authorityEpoch}, sessionKey: props.sessionKey, supported: true, access: currentAccess,
    online: props.online, refreshing: unavailable, actor: journeyActor(visible?.people ?? [], props.principalId),
    people: {state: visible ? 'ready' : 'loading', projectId: props.project.id, sessionKey: props.sessionKey, values: journeyPeople(visible?.people ?? [])} as ProductWorkEnvironment['people'],
    documents: visible?.documents ? {state: 'ready', projectId: props.project.id, sessionKey: props.sessionKey, values: visible.documents.choices}
      : {state: visible ? 'unavailable' : 'loading', projectId: props.project.id, sessionKey: props.sessionKey},
    restoredDraft: props.drafts.getWork(props.project.id, workId), onDraftState: draft => { props.drafts.putWork(draft); notifyDraft(); }, onRefresh: refresh,
    onAccepted: async (prepared, receipt) => {
      if (receipt.status !== 'accepted' || fence.current !== owner || !mounted.current || unavailable || currentAccess !== 'writable') return;
      if (prepared.command.operation === 'work.create') {
        const token = props.client.currentSessionToken();
        const fresh = await props.client.productWork.readWork({request_id: newId(), project_id: props.project.id, resource_id: prepared.command.resource_id});
        if (!mounted.current || fence.current !== owner || props.client.currentSessionToken() !== token) return;
        if (fresh.status !== 'read' || fresh.kind !== 'work' || !fresh.rows[0] || !('description' in fresh.rows[0])) throw new HomeError('invalid_response');
        props.drafts.putWork(makeProductWorkDraft({projectId: props.project.id, resourceId: prepared.command.resource_id, authorityEpoch: fresh.authority_epoch}, props.sessionKey, fresh.rows[0]));
        notifyDraft(); setCreating(undefined); setComposerOpen(false); props.onNavigate({kind: 'work', workId: prepared.command.resource_id});
      } else refresh();
    }};
  function startProposal(outcomeId: string, target: DocumentOutcome) {
    if (!work || unavailable || currentAccess !== 'writable' || environment.actor.kind !== 'person' || props.drafts.currentPending(props.project.id)) return;
    if (!visible?.documents?.markdown.has(journeyDocumentKey(target)) || target.project_id !== props.project.id) return;
    const scope: DocReviewScope = {projectId: props.project.id, workId: work.resource_id, changeId: newId()};
    const draft: DocProposalDraft = {scope, sessionKey: props.sessionKey, base: {authorityEpoch: project!.authority_epoch!, headRevision: '0',
      executionContractRevision: work.execution_contract_revision, executionContractDigest: work.execution_contract_digest, outcomeId, target: {...target}},
      markdown: visible!.documents!.markdown.get(journeyDocumentKey(target))!, summary: '', dirty: false, conflicted: false};
    props.drafts.putProposal(draft); notifyDraft(); setProposal(draft); setProposalOpen(true);
  }
  async function recordedProposal(prepared: PreparedDocChangeCommand, receipt: Extract<DocChangeReceipt, {status: 'accepted'}>) {
    if (!mounted.current || fence.current !== owner || unavailable || currentAccess !== 'writable') return;
    const token = props.client.currentSessionToken();
    const scope = {projectId: props.project.id, workId: prepared.command.work_id, changeId: prepared.command.change_id};
    const result = await adapter.current!.value.load({scope, sessionKey: props.sessionKey, result: {revision: receipt.result_revision, digest: receipt.result_digest}});
    if (!mounted.current || fence.current !== owner || props.client.currentSessionToken() !== token || result.scope.projectId !== props.project.id || result.scope.workId !== scope.workId) return;
    const local = props.drafts.getProposal(scope);
    if (local?.attempt?.prepared === prepared) props.drafts.putProposal({...local, dirty: false, attempt: {...local.attempt, phase: 'accepted', awaitingReadback: false}});
    notifyDraft(); setProposal(undefined); setProposalOpen(false); props.onNavigate({kind: 'doc-change', workId: scope.workId, changeId: scope.changeId});
  }
  function reviseProposal() {
    const review = visible?.review;
    if (!work || unavailable || currentAccess !== 'writable' || environment.actor.kind !== 'person' || !review || review.after.state !== 'ready'
      || review.snapshot.output.producer.principalId !== props.principalId || review.snapshot.output.revision !== review.snapshot.head.resultRevision
      || review.snapshot.output.digest !== review.snapshot.head.resultDigest || ['accepted', 'rejected', 'quarantined'].includes(review.snapshot.head.status)) return;
    const stored = props.drafts.getProposal(review.scope);
    const draft: DocProposalDraft = stored && (stored.dirty || stored.attempt?.awaitingReadback || ['saving', 'unknown', 'preparing'].includes(stored.attempt?.phase ?? '')) ? stored
      : {scope: {...review.scope}, sessionKey: props.sessionKey, base: {authorityEpoch: project!.authority_epoch!, headRevision: review.snapshot.head.revision,
        executionContractRevision: review.snapshot.output.executionContractRevision, executionContractDigest: review.snapshot.output.executionContractDigest,
        outcomeId: review.snapshot.output.outcomeId, target: {...review.snapshot.output.target}}, markdown: review.after.markdown,
        summary: review.snapshot.output.summary, dirty: false, conflicted: false};
    props.drafts.putProposal(draft); notifyDraft(); setProposal(draft); setProposalOpen(true);
  }
  async function more(kind: 'comments' | 'changes' | 'results') {
    if (!work || unavailable) return;
    const page = kind === 'comments' ? visible?.commentCursor : kind === 'changes' ? visible?.changes?.cursor : visible?.resultCursor; if (!page) return;
    const id = generation.current, token = props.client.currentSessionToken();
    const current = () => mounted.current && fence.current === owner && generation.current === id && props.client.currentSessionToken() === token;
    setSnapshot(value => kind === 'comments' ? {...value, commentCursor: ''} : kind === 'results' ? {...value, resultCursor: ''}
      : {...value, changes: value.changes ? {...value.changes, cursor: ''} : undefined});
    try {
      if (kind === 'comments') {
        const result = await props.client.productWork.readComments({request_id: newId(), project_id: props.project.id, resource_id: work.resource_id, cursor: page}); if (!current()) return;
        if (result.status === 'rejected') throw new HomeError(result.error);
        if (result.kind !== 'comments' || result.authority_epoch !== project!.authority_epoch || result.generation !== visible!.commentGeneration) throw new HomeError('stale_cursor');
        setSnapshot(value => ({...value, comments: result.rows, commentCursor: result.cursor}));
      } else if (kind === 'changes') {
        const result = await props.client.docChanges.readChanges({request_id: newId(), project_id: props.project.id, work_id: work.resource_id, cursor: page}); if (!current()) return;
        if (result.status === 'rejected') throw new HomeError(result.error);
        if (result.kind !== 'changes' || result.authority_epoch !== project!.authority_epoch || result.generation !== visible!.changesGeneration) throw new HomeError('stale_cursor');
        setSnapshot(value => ({...value, changes: mapDocReviewList(result, {projectId: props.project.id, workId: work.resource_id, sessionKey: props.sessionKey})}));
      } else if (visible?.review) {
        const result = await props.client.docChanges.readResults({request_id: newId(), project_id: props.project.id, work_id: work.resource_id,
          change_id: visible.review.scope.changeId, cursor: page}); if (!current()) return;
        if (result.status === 'rejected') throw new HomeError(result.error);
        if (result.kind !== 'results' || result.authority_epoch !== project!.authority_epoch || result.generation !== visible.resultGeneration) throw new HomeError('stale_cursor');
        setSnapshot(value => ({...value, results: result.rows, resultCursor: result.cursor}));
      }
    } catch (error) { if (current()) { setStale(true); if (failureCode(error) === 'denied_or_not_found') { setSnapshot({key, owner, phase: 'revoked'}); props.onAccessChanged(); } } }
  }
  const proposalPin = work && proposal ? currentProposalPin(proposal, work, project!.authority_epoch!,
    visible?.review?.scope.changeId === proposal.scope.changeId ? visible.review.snapshot.head.revision : proposal.base.headRevision) : undefined;
  const closeContent = () => { if (fence.current === owner) { setSnapshot({key, owner, phase: 'revoked'}); props.onAccessChanged(); } };
  if (snapshot.key === key && snapshot.owner === owner && snapshot.phase === 'revoked') return <OutcomeState state="permission_revoked" action={<Button onClick={refresh}>Refresh access</Button>}/>;
  return <div className="product-work-journey">
    <header className="product-journey-toolbar"><h2>{props.selection.kind === 'doc-change' ? 'Doc change' : 'Work'}</h2>
      <div><Button disabled={props.locked || !props.online || props.drafts.currentPending(props.project.id)} onClick={refresh}>Refresh</Button>
        {props.selection.kind === 'list' && <Button variant="primary" disabled={unavailable || currentAccess !== 'writable' || (!creating && props.drafts.hasDraft(props.project.id))} onClick={() => {
          const id = creating ?? newId(); if (!creating) props.drafts.putWork(makeProductWorkDraft({projectId: props.project.id, resourceId: id, authorityEpoch: project!.authority_epoch!}, props.sessionKey)); notifyDraft(); setCreating(id); setComposerOpen(true);
        }}>{creating ? 'Continue work draft' : 'New work'}</Button>}</div></header>
    <p className="muted">Refresh loads current access and saved changes.</p>
    {(!props.online || stale) && <OutcomeState state="disconnected_or_stale" description="Refresh the current view before making changes. Your local drafts are kept."/>}
    {snapshot.phase === 'loading' && <LoadingState label="Loading current Work and Docs"/>}
    {snapshot.phase === 'failed' && <OutcomeState state="retryable_error" description={snapshot.message} action={<Button onClick={refresh}>Refresh current view</Button>}/>}
    {visible && props.selection.kind === 'list' && <>
      {!visible.rows?.length && <EmptyState title="No work yet" description="Create a work item to define the outcome and who is working on it."/>}
      <ul className="product-journey-list">{visible.rows?.map(row => <li key={row.resource_id}><button disabled={unavailable || props.drafts.hasDraft(props.project.id)}
        onClick={() => props.onNavigate({kind: 'work', workId: row.resource_id})}><span>{row.title}</span><span>{productStatusLabels[row.status]}</span>
        <small>Owner: {row.owner_display_name || (row.owner_principal_id ? 'Project member' : 'Unassigned')} · Working on it: {row.worker_display_name || (row.worker_principal_id ? 'Project member' : 'Unassigned')}</small></button></li>)}</ul>
      {visible.cursor && <Button disabled={unavailable || props.drafts.hasDraft(props.project.id)} onClick={() => { nextWorkCursor.current = visible.cursor!; setRevision(value => value + 1); }}>Next page</Button>}
    </>}
    {creating && composerOpen && visible && <ProductWorkComposer {...environment} open onClose={() => setComposerOpen(false)}/>}
    {visible && work && props.selection.kind === 'work' && <>
      {!proposalOpen && <ProductWorkDetail {...environment} snapshot={{work, sessionKey: props.sessionKey, authorityEpoch: project!.authority_epoch!}}
        comments={{state: 'ready', projectId: props.project.id, resourceId: work.resource_id, sessionKey: props.sessionKey, rows: visible.comments ?? [], cursor: visible.commentCursor ?? '', onNext: () => void more('comments'), onRefresh: refresh}}
        completionReadiness={visible.readiness} mode="page" onClose={() => props.onNavigate({kind: 'list'})}
        context={<><section className="product-journey-output-actions" aria-label="Required Doc actions"><h3>Produce and review Docs</h3>
          {proposal?.scope.workId === work.resource_id && <Button disabled={unavailable} onClick={() => setProposalOpen(true)}>Continue proposal draft</Button>}
          {Object.entries(productDetailOutcomes(work)).map(([outcomeId, target]) => target.kind === 'document' && <div key={outcomeId}>
            <Button disabled={unavailable || props.drafts.hasDraft(props.project.id)} onClick={() => { if (target.project_id === props.project.id) props.onOpenDoc({collectionId: target.collection_id, documentId: target.document_id}); }}>Open required Doc</Button>
            {environment.actor.kind === 'person' && <Button disabled={unavailable || currentAccess !== 'writable' || props.drafts.hasDraft(props.project.id) || !visible.documents?.markdown.has(journeyDocumentKey(target))}
              onClick={() => startProposal(outcomeId, target)}>Propose Doc change</Button>}
            {!visible.documents?.markdown.has(journeyDocumentKey(target)) && <p className="muted">Refresh or update the required output if its saved base changed.</p>}
          </div>)}</section>
          {visible.changes && <DocChangeList projectId={props.project.id} workId={work.resource_id} sessionKey={props.sessionKey} data={visible.changes}
            locked={unavailable || props.drafts.hasDraft(props.project.id)} onOpen={changeId => props.onNavigate({kind: 'doc-change', workId: work.resource_id, changeId})}
            onMore={() => void more('changes')} onRefresh={refresh}/>}
          <WorkContext client={props.client} project={props.project.id} work={work.resource_id} writable={false} locked={unavailable || props.drafts.hasDraft(props.project.id)}
            viewRevision={revision} readWork={endpointReader.current.read} onCreate={() => {}} onRemove={() => {}}
            onOpenWork={workId => props.onNavigate({kind: 'work', workId})} onOpenDoc={(collectionId, documentId) => props.onOpenDoc({collectionId, documentId})}/></>}/>} 
    </>}
    {visible?.review && props.selection.kind === 'doc-change' && !proposalOpen && <>
      {environment.actor.kind === 'person' && visible.review.snapshot.output.producer.principalId === props.principalId
        && visible.review.snapshot.output.revision === visible.review.snapshot.head.resultRevision && visible.review.snapshot.output.digest === visible.review.snapshot.head.resultDigest
        && !['accepted', 'rejected', 'quarantined'].includes(visible.review.snapshot.head.status) && <Button disabled={unavailable || currentAccess !== 'writable' || props.drafts.currentPending(props.project.id)}
          onClick={reviseProposal}>{props.drafts.getProposal(visible.review.scope)?.dirty ? 'Continue proposal draft' : 'Revise proposal'}</Button>}
      <DocChangeReview {...visible.review} scope={visible.review.scope} sessionKey={props.sessionKey} supported access={currentAccess} online={props.online}
        refreshing={unavailable} submitter={docReviewSubmitter(props.client.docChanges)} restoredDraft={props.drafts.getReview(visible.review.scope)}
        onDraftState={draft => { props.drafts.putReview(draft); notifyDraft(); }} onRefresh={refresh} onAccessChanged={closeContent}
        onAccepted={async () => { refresh(); }} onOpenWork={() => props.onNavigate({kind: 'work', workId: visible.review!.scope.workId})}/>
      {visible.review.snapshot.acceptance && <Button disabled={unavailable || props.drafts.hasDraft(props.project.id)} onClick={() => {
        const target = visible.review!.snapshot.output.target; if (target.project_id === props.project.id) props.onOpenDoc({collectionId: target.collection_id, documentId: target.document_id});
      }}>Open accepted Doc</Button>}
      <details className="product-journey-versions"><summary>Proposal versions</summary>
        <Button disabled={unavailable || props.drafts.hasDraft(props.project.id)} onClick={() => props.onNavigate({kind: 'doc-change', workId: visible.review!.scope.workId, changeId: visible.review!.scope.changeId})}>Current version</Button>
        <ul>{visible.results?.map(row => <li key={row.result_revision}><Button disabled={unavailable || props.drafts.hasDraft(props.project.id)} onClick={() => props.onNavigate({kind: 'doc-change',
          workId: row.work_id, changeId: row.change_id, result: {revision: row.result_revision, digest: row.result_digest}})}>Version {row.result_revision} · {row.summary}</Button></li>)}</ul>
        {visible.resultCursor && <Button disabled={unavailable || props.drafts.hasDraft(props.project.id)} onClick={() => void more('results')}>More versions</Button>}
      </details>
    </>}
    {visible && work && proposalOpen && proposal?.scope.workId === work.resource_id && visible.readToken && <DocChangeProposal client={props.client.docChanges}
      scope={proposal.scope} sessionKey={props.sessionKey} work={work} pin={proposalPin ?? proposal.base} targetCurrent={!!proposalPin}
      initialMarkdown={proposal.markdown} authorizedReadToken={visible.readToken} actorKind={environment.actor.kind} access={currentAccess} online={props.online} refreshing={unavailable}
      restoredDraft={props.drafts.getProposal(proposal.scope)} onDraftState={draft => { props.drafts.putProposal(draft); notifyDraft(); }}
      onRefresh={() => { const attempt = props.drafts.getProposal(proposal.scope)?.attempt;
        if (attempt?.phase === 'accepted' && attempt.prepared && attempt.receipt) return recordedProposal(attempt.prepared, attempt.receipt); refresh(); }}
      onAccessChanged={closeContent} onClose={() => setProposalOpen(false)} onAccepted={recordedProposal}/>} 
  </div>;
}

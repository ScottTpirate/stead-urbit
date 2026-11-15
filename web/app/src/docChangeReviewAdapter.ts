// Reserved mapping only. No App integration, live route or authority inference.
import {DocChangeClient, DocChangeClientError} from './docChangeClient';
import {docChangeDetails, docChangeTarget, type DocChangeDetail, type DocChangeEvidence, type DocChangeQueryRejection, type DocChangeView} from './docChangeReadProtocol';
import {docReviewPin, type DocActionEligibility, type DocDecisionEvidence, type DocDecisionSubmitter, type DocReviewBody, type DocReviewScope, type DocReviewSnapshot} from './docChangeReviewState';
import type {DocChangeDecisionOperation} from './docChangeProtocol';
import {newId} from './protocol';
import {freeze, productJSON} from './productWire';
import type {DocChangePreview as DocChangeListRow} from './docChangeReview';
export type DocReviewReadRequest = {scope: DocReviewScope; sessionKey: string; result?: {revision: string; digest: string};
  targetLabel?: {projectId: string; collectionId: string; documentId: string; label: string}};
export type LoadedDocReview = {scope: DocReviewScope; sessionKey: string; snapshot: DocReviewSnapshot; before: DocReviewBody; after: DocReviewBody;
  eligibility: DocActionEligibility; authorizedReadToken: object};
export class DocReviewAdapterError extends Error {
  constructor(readonly code: 'view_changed' | 'read_changed' | DocChangeQueryRejection['error']) { super(code); }
}
export function mapDocReviewList(view: DocChangeView, scope: {projectId: string; workId: string; sessionKey: string}) {
  if(view.kind!=='changes'||view.project_id!==scope.projectId||view.work_id!==scope.workId)throw new DocReviewAdapterError('read_changed');
  const rows: DocChangeListRow[]=view.rows.map(row=>({projectId:row.project_id,workId:row.work_id,changeId:row.change_id,summary:row.summary,targetLabel:'',
    status:row.change_status,resultRevision:row.result_revision,producerLabel:row.producer_display_name}));
  return freeze({...scope,state:'ready' as const,rows,cursor:view.cursor});
}
export function docReviewSubmitter(client: DocChangeClient): DocDecisionSubmitter {
  return {currentSessionToken: () => client.currentSessionToken(), prepare: command => client.prepare(command), submit: async prepared => {
    const receipt = await client.submit(prepared);
    return receipt.status === 'accepted' ? {status:'accepted',resultingRevision:receipt.resulting_revision} : {status:'rejected',reason:receipt.error};
  }};
}
function evidence(value: DocChangeEvidence | null, operation: DocChangeDecisionOperation, resultRevision: string): DocDecisionEvidence | undefined {
  return value ? {operation,resultRevision,resultDigest:value.result_digest,actor:{principalId:value.principal_id,displayName:value.display_name},
    note:value.note,recordedAtMs:value.recorded_at_ms,outcome:'accepted'} : undefined;
}
export function mapDocReviewDetail(view: Extract<DocChangeView,{kind:'change'}>, request: DocReviewReadRequest) {
  const row = view.rows[0];
  if (!row || view.rows.length !== 1 || row.project_id !== request.scope.projectId || row.work_id !== request.scope.workId || row.change_id !== request.scope.changeId
    || (request.result && (row.result_revision !== request.result.revision || row.result_digest !== request.result.digest))) throw new DocReviewAdapterError('read_changed');
  const target = docChangeTarget(row), nested = docChangeDetails(row), label = request.targetLabel;
  const authorizedLabel = label && label.projectId === target.project_id && label.collectionId === target.collection_id && label.documentId === target.document_id
    && new TextEncoder().encode(label.label).length <= 800 && [...label.label].length <= 200 && !/[\u0000-\u001f]/u.test(label.label) ? label.label : '';
  const snapshot: DocReviewSnapshot = {scope:{...request.scope},sessionKey:request.sessionKey,authorityEpoch:view.authority_epoch,generation:view.generation,
    head:{revision:row.change_revision,status:row.change_status,resultRevision:row.current_result_revision,resultDigest:row.current_result_digest},
    output:{revision:row.result_revision,digest:row.result_digest,outcomeId:row.outcome_id,target,targetLabel:authorizedLabel,
      executionContractRevision:row.execution_contract_revision,executionContractDigest:row.execution_contract_digest,markdownSha256:row.markdown_sha256,
      summary:row.summary,producer:{principalId:row.producer_principal_id,displayName:row.producer_display_name},runId:row.run_id,attempt:row.attempt,submittedAtMs:row.submitted_at_ms},
    approval:evidence(nested.approval,'change.approve',row.result_revision),adoption:evidence(nested.adoption,'change.adopt',row.result_revision)};
  if (nested.latestDecision) { const value=nested.latestDecision; snapshot.feedback={operation:value.operation,resultRevision:value.result_revision,resultDigest:value.result_digest,
    actor:{principalId:value.principal_id,displayName:value.display_name},note:value.note,recordedAtMs:value.recorded_at_ms,outcome:value.outcome}; }
  if (nested.acceptance) { const value=nested.acceptance; snapshot.acceptance={actor:{principalId:value.principal_id,displayName:value.display_name},recordedAtMs:value.recorded_at_ms,
    documentRevision:value.document_revision,resultDigest:value.result_digest}; }
  const eligibility: DocActionEligibility = {scope:{...request.scope},sessionKey:request.sessionKey,pin:docReviewPin(snapshot),actions:Object.fromEntries(
    Object.entries(nested.actions).map(([operation,value])=>[operation,{state:value.status,reason:value.reason === ''?'none':value.reason}])) as DocActionEligibility['actions']};
  return freeze({snapshot,eligibility});
}
function mapBody(view: Extract<DocChangeView,{kind:'body'}>, snapshot: DocReviewSnapshot, side: 'before' | 'after'): DocReviewBody {
  const row=view.rows[0];
  if (!row || view.rows.length !== 1 || row.side !== side || row.project_id !== snapshot.scope.projectId || row.work_id !== snapshot.scope.workId || row.change_id !== snapshot.scope.changeId
    || row.result_revision !== snapshot.output.revision || row.result_digest !== snapshot.output.digest) throw new DocReviewAdapterError('read_changed');
  const base={scope:{...snapshot.scope},sessionKey:snapshot.sessionKey,resultRevision:row.result_revision,resultDigest:row.result_digest,side};
  return row.body_status === 'ready' ? {...base,state:'ready',markdown:row.markdown,sha256:row.markdown_sha256} : {...base,state:row.body_status};
}
export class DocChangeReviewAdapter {
  private generation=0;
  readonly submitter: DocDecisionSubmitter;
  constructor(private readonly client: DocChangeClient, private readonly onAccessChanged: (scope: DocReviewScope,sessionKey: string) => void | Promise<void>) {
    this.submitter=docReviewSubmitter(client);
  }
  cancel() { this.generation++; }
  async load(input: DocReviewReadRequest): Promise<LoadedDocReview> {
    const request: DocReviewReadRequest={scope:{...input.scope},sessionKey:input.sessionKey,result:input.result?{...input.result}:undefined,targetLabel:input.targetLabel?{...input.targetLabel}:undefined};
    const generation=++this.generation, token=this.client.currentSessionToken();
    if (token === null || token === '') throw new DocChangeClientError('session_required');
    const current=()=>generation===this.generation&&this.client.currentSessionToken()===token;
    const check=()=>{if(!current())throw new DocReviewAdapterError('view_changed');};
    const detailRequest=()=>({request_id:newId(),project_id:request.scope.projectId,work_id:request.scope.workId,change_id:request.scope.changeId,
      result_revision:request.result?.revision??'0',result_digest:request.result?.digest??''});
    function admitted(value: Awaited<ReturnType<DocChangeClient['read']>>): DocChangeView { if(value.status==='rejected')throw new DocReviewAdapterError(value.error);return value; }
    try {
      const first=admitted(await this.client.readDetail(detailRequest()));check();if(first.kind!=='change')throw new DocReviewAdapterError('read_changed');
      const mapped=mapDocReviewDetail(first,request), output=first.rows[0] as DocChangeDetail;
      const before=admitted(await this.client.readBody(newId(),output,'before'));check();if(before.kind!=='body')throw new DocReviewAdapterError('read_changed');
      const after=admitted(await this.client.readBody(newId(),output,'after'));check();if(after.kind!=='body')throw new DocReviewAdapterError('read_changed');
      const last=admitted(await this.client.readDetail(detailRequest()));check();
      // Compare only repeated detail queries. Body generations include other filters.
      if(last.kind!=='change'||last.generation!==first.generation||last.authority_epoch!==first.authority_epoch)throw new DocReviewAdapterError('read_changed');
      if(productJSON(last.rows[0],{bytes:262144,depth:1,keys:32})!==productJSON(first.rows[0],{bytes:262144,depth:1,keys:32}))throw new DocReviewAdapterError('read_changed');
      const refreshed=mapDocReviewDetail(last,request);
      if(refreshed.snapshot.head.revision!==mapped.snapshot.head.revision||refreshed.snapshot.output.digest!==mapped.snapshot.output.digest||refreshed.snapshot.output.revision!==mapped.snapshot.output.revision)throw new DocReviewAdapterError('read_changed');
      return freeze({scope:{...request.scope},sessionKey:request.sessionKey,...refreshed,before:mapBody(before,refreshed.snapshot,'before'),after:mapBody(after,refreshed.snapshot,'after'),authorizedReadToken:Object.freeze({})});
    } catch(error) {
      if(!current())throw new DocReviewAdapterError('view_changed');
      if(current()&&error instanceof DocReviewAdapterError&&error.code==='denied_or_not_found') {
        try { await this.onAccessChanged({...request.scope},request.sessionKey); } catch { /* The denied read still fails closed. */ }
        if(!current())throw new DocReviewAdapterError('view_changed');
      }
      throw error;
    }
  }
}

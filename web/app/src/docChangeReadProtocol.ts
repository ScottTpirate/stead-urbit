// Reserved native Doc Change query/result/receipt boundary. No carrier exists here.
import {byteLength, freeze, keys, object, parseProductJSON, productJSON, ProductProtocolError, protocolText} from './productWire';
import {encodeDocChangeCommand, parseDocChangeCommand, type DocChangeCommand, type DocChangeDecisionOperation} from './docChangeProtocol';
import type {DocumentOutcome} from './productProtocol';
export type DocChangeQuery = {protocol: 'stead.doc-change-query/1'; request_id: string; kind: 'changes' | 'change' | 'results' | 'body';
  project_id: string; work_id: string; change_id: string; result_revision: string; result_digest: string; side: '' | 'before' | 'after'; cursor: string};
export type DocChangeLifecycle = 'submitted' | 'changes-requested' | 'approved' | 'accepted' | 'rejected' | 'quarantined';
export type DocChangePreview = {kind: 'doc-change'; project_id: string; work_id: string; change_id: string; change_revision: string; change_status: DocChangeLifecycle;
  current_result_revision: string; current_result_digest: string; result_revision: string; result_digest: string; is_current_result: 'yes' | 'no';
  outcome_id: string; target: string; execution_contract_revision: string; execution_contract_digest: string; producer_principal_id: string;
  producer_display_name: string; summary: string; markdown_sha256: string; run_id: string; attempt: string; submitted_at_ms: string};
export type DocChangeDetail = DocChangePreview & {producer_binding_id: string; producer_binding_revision: string; approval: string; adoption: string; acceptance: string;
  latest_decision: string; producer_authority: 'live' | 'expired' | 'revoked' | 'unknown'; contract_current: 'yes' | 'no'; actions: string};
export type DocChangeBody = {kind: 'doc-change-body'; project_id: string; work_id: string; change_id: string; result_revision: string; result_digest: string;
  side: 'before' | 'after'; body_status: 'ready' | 'unavailable' | 'new-document'; markdown: string; markdown_sha256: string};
export type DocChangeEvidence = {principal_id: string; display_name: string; recorded_at_ms: string; note: string; result_digest: string};
export type DocChangeAcceptance = {principal_id: string; display_name: string; recorded_at_ms: string; document_revision: string; result_digest: string};
export type DocChangeFeedback = DocChangeEvidence & {operation: DocChangeDecisionOperation; outcome: 'accepted' | 'producer_quarantined'; result_revision: string; change_revision: string};
export type DocActionReason = '' | 'superseded_result' | 'read_only' | 'human_review_required' | 'change_closed' | 'accountable_human_required'
  | 'execution_contract_conflict' | 'target_base_conflict' | 'producer_quarantined' | 'adoption_requires_expiry' | 'independent_adopter_required'
  | 'independent_review_required' | 'explicit_adoption_required' | 'self_review_denied';
export type DocChangeActions = Readonly<Record<DocChangeDecisionOperation, {status: 'eligible' | 'blocked'; reason: DocActionReason}>>;
type ViewBase = Omit<DocChangeQuery, 'protocol' | 'cursor'> & {protocol: 'stead.doc-change-query-result/1'; status: 'read'; authority_epoch: string; generation: string; cursor: string};
export type DocChangeView = ViewBase & ({kind: 'changes' | 'results'; rows: readonly DocChangePreview[]} | {kind: 'change'; rows: readonly DocChangeDetail[]} | {kind: 'body'; rows: readonly DocChangeBody[]});
export type DocChangeQueryRejection = {protocol: 'stead.doc-change-query-result/1'; status: 'rejected'; request_id: string;
  error: 'invalid_request' | 'denied_or_not_found' | 'migration_required' | 'invalid_product_state' | 'stale_cursor' | 'capacity_exceeded'};
export type DocChangeReceiptError = 'denied_or_not_found' | 'migration_required' | 'invalid_time' | 'authority_epoch_conflict' | 'request_id_reuse' | 'capacity_exceeded'
  | 'revision_conflict' | 'producer_mismatch' | 'change_closed' | 'producer_unavailable' | 'invalid_document' | 'execution_contract_conflict' | 'target_base_conflict'
  | 'content_collision' | 'result_conflict' | 'invalid_result' | 'human_review_required' | 'accountable_human_required' | 'producer_quarantined'
  | 'adoption_requires_expiry' | 'independent_adopter_required' | 'self_review_denied' | 'invalid_command' | 'independent_review_required'
  | 'explicit_adoption_required' | 'internal_request_id_collision' | 'document_save_rejected';
type ReceiptBase = {protocol: 'stead.doc-change-receipt/1'; request_id: string; canonical_sha256: string};
type FullReceipt = ReceiptBase & {project_id: string; work_id: string; change_id: string; authority_epoch: string; operation: DocChangeCommand['operation'];
  expected_revision: string; resulting_revision: string; result_revision: string; result_digest: string; change_status: DocChangeLifecycle | ''; recorded_at_ms: string};
export type DocChangeReceipt = (ReceiptBase & {status: 'rejected'; error: DocChangeReceiptError}) | (FullReceipt & ({status: 'accepted'; error: ''} | {status: 'rejected'; error: DocChangeReceiptError}));
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u, HASH = /^[a-f0-9]{64}$/u;
const queryKeys = ['protocol', 'request_id', 'kind', 'project_id', 'work_id', 'change_id', 'result_revision', 'result_digest', 'side', 'cursor'];
const previewKeys = ['kind','project_id','work_id','change_id','change_revision','change_status','current_result_revision','current_result_digest','result_revision','result_digest','is_current_result','outcome_id','target','execution_contract_revision','execution_contract_digest','producer_principal_id','producer_display_name','summary','markdown_sha256','run_id','attempt','submitted_at_ms'];
const detailKeys = ['producer_binding_id','producer_binding_revision','approval','adoption','acceptance','latest_decision','producer_authority','contract_current','actions'];
const decisionNames = ['change.request-changes','change.approve','change.adopt','change.accept','change.reject','change.quarantine'] as const;
const lifecycle = ['submitted','changes-requested','approved','accepted','rejected','quarantined'];
const actionReasons = ['', 'superseded_result','read_only','human_review_required','change_closed','accountable_human_required','execution_contract_conflict','target_base_conflict','producer_quarantined','adoption_requires_expiry','independent_adopter_required','independent_review_required','explicit_adoption_required','self_review_denied'];
const receiptErrors = ['denied_or_not_found','migration_required','invalid_time','authority_epoch_conflict','request_id_reuse','capacity_exceeded','revision_conflict','producer_mismatch','change_closed','producer_unavailable','invalid_document','execution_contract_conflict','target_base_conflict','content_collision','result_conflict','invalid_result','human_review_required','accountable_human_required','producer_quarantined','adoption_requires_expiry','independent_adopter_required','self_review_denied','invalid_command','independent_review_required','explicit_adoption_required','internal_request_id_collision','document_save_rejected'];
function requireValue(condition: unknown): asserts condition { if (!condition) throw new ProductProtocolError(); }
function text(row: Record<string, unknown>, key: string): string { protocolText(row[key]); return row[key]; }
function uint(value: unknown, positive = false): asserts value is string { protocolText(value); requireValue(/^(?:0|[1-9][0-9]{0,19})$/u.test(value) && BigInt(value) <= 18446744073709551615n && (!positive || value !== '0')); }
function uuid(value: unknown, empty = false): asserts value is string { protocolText(value); requireValue((empty && value === '') || UUID.test(value)); }
function digest(value: unknown, empty = false): asserts value is string { protocolText(value); requireValue((empty && value === '') || HASH.test(value)); }
function prose(value: unknown, bound: number) { protocolText(value); requireValue(byteLength(value) <= bound && !value.includes('\r')); }
function title(value: unknown) { protocolText(value); if (!value) return; requireValue(byteLength(value) <= 800 && [...value].length <= 200 && [...new TextEncoder().encode(value)].every(byte => byte >= 32)); }
function note(value: unknown, empty = false) { protocolText(value); if (empty && value === '') return; const bytes = new TextEncoder().encode(value); requireValue(bytes.length <= 2048 && bytes.every(byte => byte === 9 || byte === 10 || byte >= 32) && bytes.some(byte => byte > 32)); }
function strings(row: Record<string, unknown>) { for (const value of Object.values(row)) protocolText(value); }
function response<T>(operation: () => T): T { try { return operation(); } catch { throw new ProductProtocolError('invalid_response'); } }
function embedded(raw: string, names: readonly string[], nested = false) {
  const row = parseProductJSON(raw, {bytes: 16384, depth: nested ? 2 : 1, keys: 16}); keys(row, names);
  requireValue(productJSON(row) === raw); if (!nested) strings(row); return row;
}
export function parseDocChangeQuery(raw: string): DocChangeQuery {
  const row = parseProductJSON(raw, {bytes: 65536, depth: 1, keys: 16}); keys(row, queryKeys); strings(row);
  requireValue(row.protocol === 'stead.doc-change-query/1'); for (const key of ['request_id','project_id','work_id']) uuid(row[key]);
  uint(row.result_revision); digest(row.cursor, true);
  if (row.kind === 'changes') requireValue(row.change_id === '' && row.result_revision === '0' && row.result_digest === '' && row.side === '');
  else {
    uuid(row.change_id);
    if (row.kind === 'results') requireValue(row.result_revision === '0' && row.result_digest === '' && row.side === '');
    else {
      requireValue(row.cursor === '');
      if (row.kind === 'change') { requireValue(row.side === ''); if (row.result_revision === '0') requireValue(row.result_digest === ''); else digest(row.result_digest); }
      else { requireValue(row.kind === 'body' && ['before','after'].includes(text(row,'side'))); uint(row.result_revision, true); digest(row.result_digest); }
    }
  }
  return freeze(row as unknown as DocChangeQuery);
}
export function encodeDocChangeQuery(value: unknown): string { return productJSON(parseDocChangeQuery(productJSON(value))); }
export function docChangeTarget(value: DocChangePreview): DocumentOutcome {
  return response(() => { const row = embedded(value.target, ['kind','project_id','collection_id','document_id','expected_revision','base_markdown_sha256']);
    requireValue(row.kind === 'document' && row.project_id === value.project_id); uuid(row.project_id); uuid(row.collection_id); uuid(row.document_id); uint(row.expected_revision);
    if (row.expected_revision === '0') requireValue(row.base_markdown_sha256 === ''); else digest(row.base_markdown_sha256);
    return freeze(row as unknown as DocumentOutcome); });
}
function evidence(raw: string, output: DocChangeDetail): DocChangeEvidence | null {
  if (!raw) return null;
  const row = embedded(raw, ['principal_id','display_name','recorded_at_ms','note','result_digest']); uuid(row.principal_id); title(row.display_name); uint(row.recorded_at_ms, true); note(row.note, true);
  requireValue(row.result_digest === output.result_digest); return freeze(row as unknown as DocChangeEvidence);
}
export function docChangeDetails(value: DocChangeDetail): {approval: DocChangeEvidence | null; adoption: DocChangeEvidence | null; acceptance: DocChangeAcceptance | null; latestDecision: DocChangeFeedback | null; actions: DocChangeActions} {
  return response(() => {
    const approval = evidence(value.approval, value), adoption = evidence(value.adoption, value); if (adoption) note(adoption.note);
    let acceptance: DocChangeAcceptance | null = null, latestDecision: DocChangeFeedback | null = null;
    if (value.acceptance) {
      const row = embedded(value.acceptance, ['principal_id','display_name','recorded_at_ms','document_revision','result_digest']); uuid(row.principal_id); title(row.display_name); uint(row.recorded_at_ms, true); uint(row.document_revision, true);
      requireValue(row.result_digest === value.result_digest && BigInt(row.document_revision) === BigInt(docChangeTarget(value).expected_revision) + 1n);
      acceptance = freeze(row as unknown as DocChangeAcceptance);
    }
    if (value.latest_decision) {
      const row = embedded(value.latest_decision, ['operation','outcome','principal_id','display_name','recorded_at_ms','note','result_revision','result_digest','change_revision']);
      requireValue(decisionNames.includes(text(row,'operation') as DocChangeDecisionOperation) && ['accepted','producer_quarantined'].includes(text(row,'outcome')));
      uuid(row.principal_id); title(row.display_name); uint(row.recorded_at_ms, true); uint(row.change_revision, true);
      note(row.note, row.operation === 'change.approve' || row.operation === 'change.accept');
      requireValue(row.result_revision === value.result_revision && row.result_digest === value.result_digest && BigInt(row.change_revision) <= BigInt(value.change_revision));
      latestDecision = freeze(row as unknown as DocChangeFeedback);
    }
    const actions = embedded(value.actions, decisionNames, true);
    for (const operation of decisionNames) {
      const action = object(actions[operation]); keys(action,['status','reason']); strings(action);
      requireValue(['eligible','blocked'].includes(text(action,'status')) && actionReasons.includes(text(action,'reason')) && (action.status === 'eligible') === (action.reason === ''));
      if (value.is_current_result === 'no') requireValue(action.status === 'blocked' && action.reason === 'superseded_result');
    }
    if (value.is_current_result === 'no') requireValue(!approval && !adoption && !acceptance);
    if (acceptance) requireValue(value.change_status === 'accepted');
    return freeze({approval, adoption, acceptance, latestDecision, actions: actions as unknown as DocChangeActions});
  });
}
function metadata(value: unknown, query: DocChangeQuery): DocChangePreview | DocChangeDetail {
  const row = object(value), full = query.kind === 'change'; keys(row,[...previewKeys,...(full ? detailKeys : [])]); strings(row);
  requireValue(row.kind === 'doc-change' && row.project_id === query.project_id && row.work_id === query.work_id); uuid(row.change_id);
  if (query.kind !== 'changes') requireValue(row.change_id === query.change_id);
  for (const key of ['change_revision','current_result_revision','result_revision','execution_contract_revision','submitted_at_ms']) uint(row[key], true);
  for (const key of ['current_result_digest','result_digest','execution_contract_digest','markdown_sha256']) digest(row[key]);
  requireValue(lifecycle.includes(text(row,'change_status')) && ['yes','no'].includes(text(row,'is_current_result')));
  requireValue(BigInt(row.result_revision as string) <= BigInt(row.current_result_revision as string) && BigInt(row.current_result_revision as string) <= BigInt(row.change_revision as string));
  const isCurrent = row.result_revision === row.current_result_revision && row.result_digest === row.current_result_digest;
  if (row.result_revision === row.current_result_revision) requireValue(row.result_digest === row.current_result_digest);
  requireValue((row.is_current_result === 'yes') === isCurrent);
  if (query.kind === 'changes' || (query.kind === 'change' && query.result_revision === '0')) requireValue(isCurrent);
  if (query.kind === 'change' && query.result_revision !== '0') requireValue(row.result_revision === query.result_revision && row.result_digest === query.result_digest);
  uuid(row.outcome_id); uuid(row.producer_principal_id); title(row.producer_display_name); note(row.summary); uuid(row.run_id, true); uint(row.attempt);
  if (row.run_id === '') requireValue(row.attempt === '0'); else uint(row.attempt, true);
  docChangeTarget(row as unknown as DocChangePreview);
  if (full) { uuid(row.producer_binding_id); uint(row.producer_binding_revision, true); requireValue(['live','expired','revoked','unknown'].includes(text(row,'producer_authority')) && ['yes','no'].includes(text(row,'contract_current'))); docChangeDetails(row as unknown as DocChangeDetail); }
  return row as unknown as DocChangePreview | DocChangeDetail;
}
function bodyRow(value: unknown, query: DocChangeQuery): DocChangeBody {
  const row = object(value); keys(row,['kind','project_id','work_id','change_id','result_revision','result_digest','side','body_status','markdown','markdown_sha256']); strings(row);
  requireValue(row.kind === 'doc-change-body'); for (const key of ['project_id','work_id','change_id','result_revision','result_digest','side'] as const) requireValue(row[key] === query[key]);
  requireValue(['ready','unavailable','new-document'].includes(text(row,'body_status'))); prose(row.markdown,32768);
  if (row.body_status === 'ready') digest(row.markdown_sha256);
  else { requireValue(row.side === 'before' && row.markdown === ''); if (row.body_status === 'new-document') requireValue(row.markdown_sha256 === ''); else digest(row.markdown_sha256); }
  return row as unknown as DocChangeBody;
}
export function snapshotDocChangeOutput(value: DocChangePreview, query: DocChangeQuery): DocChangePreview {
  return response(() => {
    const row = parseProductJSON(productJSON(value,{bytes:262144,depth:1,keys:32}),{bytes:262144,depth:1,keys:32});
    const copied = metadata(row,{...query,kind:Object.hasOwn(row,'actions')?'change':'results'});
    for (const key of ['project_id','work_id','change_id','result_revision','result_digest'] as const) requireValue(copied[key] === query[key]);
    return freeze(copied);
  });
}
export function parseDocChangeView(raw: string, request: DocChangeQuery): DocChangeView | DocChangeQueryRejection {
  return response(() => {
    const query = parseDocChangeQuery(encodeDocChangeQuery(request)), row = parseProductJSON(raw,{bytes:262144,depth:3,keys:32});
    requireValue(row.protocol === 'stead.doc-change-query-result/1' && row.request_id === query.request_id);
    if (row.status === 'rejected') { keys(row,['protocol','status','request_id','error']); requireValue(['invalid_request','denied_or_not_found','migration_required','invalid_product_state','stale_cursor','capacity_exceeded'].includes(text(row,'error'))); return freeze(row as unknown as DocChangeQueryRejection); }
    keys(row,['protocol','status','request_id','kind','project_id','work_id','change_id','result_revision','result_digest','side','authority_epoch','generation','cursor','rows']);
    requireValue(row.status === 'read'); for (const key of ['kind','project_id','work_id','change_id','result_revision','result_digest','side'] as const) requireValue(row[key] === query[key]);
    uint(row.authority_epoch,true); digest(row.generation); digest(row.cursor,true);
    const indexed = object(row.rows), count = Object.keys(indexed).length; requireValue(count <= 20 && Object.keys(indexed).every(key => /^(?:0|[1-9][0-9]?)$/u.test(key) && Number(key) < count));
    const rows = Array.from({length:count},(_,index) => query.kind === 'body' ? bodyRow(indexed[String(index)],query) : metadata(indexed[String(index)],query));
    if (query.kind === 'change' || query.kind === 'body') requireValue(count === 1 && row.cursor === '');
    if (row.cursor !== '') requireValue(count === 20);
    if (query.kind === 'changes') requireValue(new Set(rows.map(item => item.change_id)).size === count);
    if (query.kind === 'results') for (let index=1;index<count;index++) requireValue(BigInt(rows[index]!.result_revision)>BigInt(rows[index-1]!.result_revision));
    return freeze({...row,rows} as unknown as DocChangeView);
  });
}
export async function verifyDocChangeBody(body: DocChangeBody, output: DocChangePreview) {
  const target = response(() => { for (const key of ['project_id','work_id','change_id','result_revision','result_digest'] as const) requireValue(body[key] === output[key]); return docChangeTarget(output); });
  const expected = body.side === 'after' ? output.markdown_sha256 : target.base_markdown_sha256;
  if (body.body_status === 'new-document') return response(() => { requireValue(body.side === 'before' && target.expected_revision === '0' && body.markdown === '' && body.markdown_sha256 === ''); return body; });
  response(() => { requireValue(body.markdown_sha256 === expected); });
  if (body.body_status === 'unavailable') return body;
  const actual = [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(body.markdown)))].map(value=>value.toString(16).padStart(2,'0')).join('');
  return response(() => { requireValue(actual === expected); if (body.side === 'after') requireValue(body.markdown.startsWith(`---\nid: ${target.document_id}\ntype: page\nstate: published\n---\n`)); return body; });
}
export function parseDocChangeReceipt(raw: string, request: DocChangeCommand, commandDigest: string): DocChangeReceipt {
  return response(() => {
    const command = parseDocChangeCommand(encodeDocChangeCommand(request)), row = parseProductJSON(raw,{bytes:8192,depth:1,keys:16}); strings(row); digest(commandDigest);
    requireValue(row.protocol === 'stead.doc-change-receipt/1' && row.request_id === command.request_id && row.canonical_sha256 === commandDigest && ['accepted','rejected'].includes(text(row,'status')));
    requireValue(row.status === 'accepted' ? row.error === '' : receiptErrors.includes(text(row,'error')));
    if (row.status === 'rejected' && Object.keys(row).length === 5) { keys(row,['protocol','status','request_id','canonical_sha256','error']); return freeze(row as unknown as DocChangeReceipt); }
    keys(row,['protocol','status','request_id','canonical_sha256','project_id','work_id','change_id','authority_epoch','operation','expected_revision','resulting_revision','result_revision','result_digest','change_status','recorded_at_ms','error']);
    for (const key of ['project_id','work_id','change_id','authority_epoch','operation','expected_revision'] as const) requireValue(row[key] === command[key]);
    uint(row.recorded_at_ms,true); uint(row.resulting_revision); uint(row.result_revision);
    if (row.resulting_revision === '0') requireValue(row.result_revision === '0' && row.result_digest === '' && row.change_status === '' && row.status === 'rejected');
    else { uint(row.result_revision,true); digest(row.result_digest); requireValue(lifecycle.includes(text(row,'change_status')) && BigInt(row.result_revision) <= BigInt(row.resulting_revision)); }
    if (row.status === 'accepted' || row.error === 'producer_quarantined') {
      requireValue(BigInt(row.resulting_revision) === BigInt(command.expected_revision) + 1n);
      if (command.operation !== 'change.submit') requireValue(row.result_revision === command.payload.result_revision && row.result_digest === command.payload.result_digest);
    }
    if (row.status === 'accepted') {
      const status = {'change.submit':'submitted','change.request-changes':'changes-requested','change.approve':'approved','change.accept':'accepted','change.reject':'rejected','change.quarantine':'quarantined'};
      if (command.operation === 'change.adopt') requireValue(['submitted','changes-requested','approved'].includes(text(row,'change_status')));
      else requireValue(row.change_status === status[command.operation]);
    }
    if (row.error === 'producer_quarantined') requireValue(row.change_status === 'quarantined' && command.operation !== 'change.submit');
    return freeze(row as unknown as DocChangeReceipt);
  });
}

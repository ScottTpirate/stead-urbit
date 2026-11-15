// Reserved, read-only per-Work Run boundary. No route, command or capability is
// advertised here. Phase, lease observation and pin freshness grant no authority.
import {byteLength, freeze, keys, object, parseProductJSON, productJSON, ProductProtocolError, protocolText} from './productWire';

export type RunQuery = {protocol: 'stead.run-query/1'; request_id: string; kind: 'runs' | 'run'; project_id: string; work_id: string; run_id: string; cursor: string};
export type RunPhase = 'queued' | 'running' | 'waiting' | 'submitted' | 'failed' | 'canceled';
export type RunLeaseState = 'none' | 'terminal' | 'unknown-book' | 'expired' | 'live';
export type RunResultReference = {change_id: string; result_revision: string; result_digest: string; outcome_id: string};
export type RunAgentVersion = {definition_id: string; definition_revision: string; runtime_id: string; runtime_revision: string};
export type RunAttempt = {attempt: string; principal_id: string; display_name: string; started_at_ms: string; heartbeat_at_ms: string; lease_until_ms: string;
  disposition: 'running' | 'waiting' | 'submitted' | 'failed' | 'canceled' | 'replaced'};
export type RunAnswer = {text: string; principal_id: string; display_name: string; recorded_at_ms: string};
export type RunQuestion = RunAnswer & {sequence: string; answer: string};
export type RunPreview = {kind: 'run'; project_id: string; work_id: string; run_id: string; run_revision: string; phase: RunPhase; issued_at_ms: string; deadline_ms: string;
  requester_principal_id: string; requester_display_name: string; owner_principal_id: string; owner_display_name: string; worker_principal_id: string; worker_display_name: string;
  current_attempt: string; question_sequence: string; lease_state: RunLeaseState; lease_until_ms: string; result: string};
export type RunDetail = RunPreview & {execution_contract_revision: string; execution_contract_digest: string; agent_version: string;
  execution_current: 'yes' | 'no'; current_attempt_detail: string; latest_question: string};
type ViewBase = Omit<RunQuery, 'protocol'> & {protocol: 'stead.run-query-result/1'; status: 'read'; authority_epoch: string; generation: string};
export type RunView = ViewBase & ({kind: 'runs'; rows: readonly RunPreview[]} | {kind: 'run'; rows: readonly RunDetail[]});
export type RunQueryError = 'invalid_request' | 'denied_or_not_found' | 'migration_required' | 'invalid_product_state' | 'stale_cursor' | 'capacity_exceeded';
export type RunQueryRejection = {protocol: 'stead.run-query-result/1'; status: 'rejected'; request_id: string; error: RunQueryError};
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u, HASH = /^[a-f0-9]{64}$/u;
const queryKeys = ['protocol','request_id','kind','project_id','work_id','run_id','cursor'];
const previewKeys = ['kind','project_id','work_id','run_id','run_revision','phase','issued_at_ms','deadline_ms','requester_principal_id','requester_display_name',
  'owner_principal_id','owner_display_name','worker_principal_id','worker_display_name','current_attempt','question_sequence','lease_state','lease_until_ms','result'];
const detailKeys = ['execution_contract_revision','execution_contract_digest','agent_version','execution_current','current_attempt_detail','latest_question'];
const phases = ['queued','running','waiting','submitted','failed','canceled'];
const terminal = ['submitted','failed','canceled'];
function requireValue(value: unknown): asserts value { if (!value) throw new ProductProtocolError(); }
function strings(row: Record<string, unknown>) { for (const value of Object.values(row)) protocolText(value); }
function text(row: Record<string, unknown>, key: string) { protocolText(row[key]); return row[key]; }
function uuid(value: unknown, empty = false): asserts value is string { protocolText(value); requireValue((empty && value === '') || UUID.test(value)); }
function hash(value: unknown, empty = false): asserts value is string { protocolText(value); requireValue((empty && value === '') || HASH.test(value)); }
function uint(value: unknown, positive = false): asserts value is string {
  protocolText(value); requireValue(/^(?:0|[1-9][0-9]{0,19})$/u.test(value) && BigInt(value) <= 18446744073709551615n && (!positive || value !== '0'));
}
function name(value: unknown) { protocolText(value); if (!value) return; requireValue(byteLength(value) <= 800 && [...value].length <= 200 && [...new TextEncoder().encode(value)].every(byte => byte >= 32)); }
function prose(value: unknown) { protocolText(value); requireValue(byteLength(value) > 0 && byteLength(value) <= 2048 && !value.includes('\r')); }
function response<T>(read: () => T): T { try { return read(); } catch { throw new ProductProtocolError('invalid_response'); } }
function embedded(raw: string, names: readonly string[]) {
  const row = parseProductJSON(raw, {bytes: 32768, depth: 1, keys: 16}); keys(row, names); strings(row);
  requireValue(productJSON(row, {bytes: 32768, depth: 1, keys: 16}) === raw); return row;
}
export function parseRunQuery(raw: string): RunQuery {
  const row = parseProductJSON(raw, {bytes: 65536, depth: 1, keys: 16}); keys(row, queryKeys); strings(row);
  requireValue(row.protocol === 'stead.run-query/1'); for (const key of ['request_id','project_id','work_id']) uuid(row[key]); hash(row.cursor, true);
  if (row.kind === 'runs') requireValue(row.run_id === '');
  else { requireValue(row.kind === 'run' && row.cursor === ''); uuid(row.run_id); }
  return freeze(row as unknown as RunQuery);
}
export function encodeRunQuery(value: RunQuery): string { return productJSON(parseRunQuery(productJSON(value))); }
export function runResult(row: RunPreview): Readonly<RunResultReference> | undefined {
  return response(() => {
    if (row.result === '') { requireValue(row.phase !== 'submitted'); return; }
    requireValue(row.phase === 'submitted'); const value = embedded(row.result, ['change_id','result_revision','result_digest','outcome_id']);
    uuid(value.change_id); uuid(value.outcome_id); uint(value.result_revision, true); hash(value.result_digest);
    return freeze(value as unknown as RunResultReference);
  });
}
export function runDetails(row: RunDetail) {
  return response(() => {
    const version = embedded(row.agent_version, ['definition_id','definition_revision','runtime_id','runtime_revision']);
    uuid(version.definition_id); uuid(version.runtime_id); uint(version.definition_revision, true); uint(version.runtime_revision, true);
    let attempt: RunAttempt | undefined, question: RunQuestion | undefined, answer: RunAnswer | undefined;
    if (row.current_attempt === '0') requireValue(row.current_attempt_detail === '');
    else {
      const value = embedded(row.current_attempt_detail, ['attempt','principal_id','display_name','started_at_ms','heartbeat_at_ms','lease_until_ms','disposition']);
      requireValue(value.attempt === row.current_attempt && value.principal_id === row.worker_principal_id && value.lease_until_ms === row.lease_until_ms);
      uuid(value.principal_id); name(value.display_name);
      for (const key of ['started_at_ms','heartbeat_at_ms','lease_until_ms']) uint(value[key], true);
      requireValue(BigInt(row.issued_at_ms) <= BigInt(text(value,'started_at_ms')) && BigInt(text(value,'started_at_ms')) <= BigInt(text(value,'heartbeat_at_ms'))
        && BigInt(text(value,'heartbeat_at_ms')) <= BigInt(text(value,'lease_until_ms')) && BigInt(text(value,'lease_until_ms')) <= BigInt(row.deadline_ms));
      requireValue(['running','waiting','submitted','failed','canceled','replaced'].includes(text(value,'disposition')));
      if (row.lease_state === 'live') requireValue(['running','waiting'].includes(text(value,'disposition')));
      attempt = value as unknown as RunAttempt;
    }
    if (row.question_sequence === '0') requireValue(row.latest_question === '');
    else {
      const value = embedded(row.latest_question, ['sequence','text','principal_id','display_name','recorded_at_ms','answer']);
      requireValue(value.sequence === row.question_sequence); prose(value.text); uuid(value.principal_id); name(value.display_name); uint(value.recorded_at_ms);
      if (value.answer !== '') {
        const replied = embedded(text(value,'answer'), ['text','principal_id','display_name','recorded_at_ms']);
        prose(replied.text); uuid(replied.principal_id); name(replied.display_name); uint(replied.recorded_at_ms); answer = replied as unknown as RunAnswer;
      }
      question = value as unknown as RunQuestion;
    }
    return freeze({agentVersion: version as unknown as RunAgentVersion, attempt, question, answer, result: runResult(row)});
  });
}
function metadata(value: unknown, query: RunQuery): RunPreview | RunDetail {
  const row = object(value); keys(row, [...previewKeys, ...(query.kind === 'run' ? detailKeys : [])]); strings(row);
  requireValue(row.kind === 'run' && row.project_id === query.project_id && row.work_id === query.work_id); uuid(row.run_id);
  if (query.kind === 'run') requireValue(row.run_id === query.run_id);
  for (const key of ['run_revision','issued_at_ms','deadline_ms']) uint(row[key], true);
  for (const key of ['requester_principal_id','owner_principal_id','worker_principal_id']) uuid(row[key]);
  for (const key of ['requester_display_name','owner_display_name','worker_display_name']) name(row[key]);
  requireValue(row.owner_principal_id !== row.worker_principal_id && BigInt(text(row,'deadline_ms')) > BigInt(text(row,'issued_at_ms')));
  requireValue(phases.includes(text(row,'phase'))); uint(row.current_attempt); uint(row.question_sequence); uint(row.lease_until_ms);
  requireValue(BigInt(row.current_attempt) <= 3n && BigInt(row.question_sequence) <= 4096n);
  requireValue(['none','terminal','unknown-book','expired','live'].includes(text(row,'lease_state')));
  if (row.current_attempt === '0') requireValue(row.lease_state === 'none' && row.lease_until_ms === '0');
  else {
    requireValue(row.lease_state !== 'none'); uint(row.lease_until_ms, true);
    requireValue((row.lease_state === 'terminal') === terminal.includes(text(row,'phase')));
    requireValue(BigInt(row.lease_until_ms) <= BigInt(text(row,'deadline_ms')));
  }
  runResult(row as unknown as RunPreview);
  if (query.kind === 'run') {
    uint(row.execution_contract_revision, true); hash(row.execution_contract_digest); requireValue(['yes','no'].includes(text(row,'execution_current')));
    runDetails(row as unknown as RunDetail);
  }
  return row as unknown as RunPreview | RunDetail;
}
export function parseRunView(raw: string, request: RunQuery): RunView | RunQueryRejection {
  return response(() => {
    const query = parseRunQuery(encodeRunQuery(request)), row = parseProductJSON(raw, {bytes: 262144, depth: 3, keys: 32});
    requireValue(row.protocol === 'stead.run-query-result/1' && row.request_id === query.request_id);
    if (row.status === 'rejected') {
      keys(row, ['protocol','status','request_id','error']); requireValue(['invalid_request','denied_or_not_found','migration_required','invalid_product_state','stale_cursor','capacity_exceeded'].includes(text(row,'error')));
      return freeze(row as unknown as RunQueryRejection);
    }
    keys(row, ['protocol','status','request_id','kind','project_id','work_id','run_id','authority_epoch','generation','cursor','rows']); requireValue(row.status === 'read');
    for (const key of ['kind','project_id','work_id','run_id'] as const) requireValue(row[key] === query[key]);
    uint(row.authority_epoch, true); hash(row.generation); hash(row.cursor, true);
    const indexed = object(row.rows), count = Object.keys(indexed).length;
    requireValue(count <= 20 && Object.keys(indexed).every(key => /^(?:0|[1-9][0-9]?)$/u.test(key) && Number(key) < count));
    const rows = Array.from({length: count}, (_, index) => metadata(indexed[String(index)], query));
    if (query.kind === 'run') requireValue(count === 1 && row.cursor === '');
    if (row.cursor !== '') requireValue(count === 20);
    for (let index = 1; index < count; index++) requireValue(rows[index - 1]!.run_id < rows[index]!.run_id);
    return freeze({...row, rows} as unknown as RunView);
  });
}

export type RunSessionToken = string | object;
export interface RunReadTransport {
  currentSession(): RunSessionToken | null;
  capability?(): 'stead.run-query/1' | null;
  query(bytes: string): Promise<string>;
}
export class RunReadClientError extends Error {
  constructor(readonly code: 'session_required' | 'session_changed' | 'unsupported_operation' | 'read_unavailable' | 'stale_cursor') { super(code); }
}
type Cursor = {session: RunSessionToken; sequence: number; filter: string; generation: string; epoch: string; count: number; last: string};
export class RunReadClient {
  private readonly cursors = new Map<string, Cursor>();
  private listSequence = 0;
  constructor(private readonly transport: RunReadTransport) {}
  currentSessionToken() { return this.transport.currentSession(); }
  private capability() { if (this.transport.capability?.() !== 'stead.run-query/1') throw new RunReadClientError('unsupported_operation'); }
  private check(token: RunSessionToken) { if (this.transport.currentSession() !== token) throw new RunReadClientError('session_changed'); }
  private current(token: RunSessionToken, sequence: number | undefined) {
    this.check(token); this.capability(); if (sequence !== undefined && sequence !== this.listSequence) throw new RunReadClientError('stale_cursor');
  }
  async read(value: RunQuery): Promise<RunView | RunQueryRejection> {
    this.capability(); const token = this.transport.currentSession(); if (token === null || token === '') throw new RunReadClientError('session_required');
    for (const [key, record] of this.cursors) if (record.session !== token) this.cursors.delete(key);
    const bytes = encodeRunQuery(value), query = parseRunQuery(bytes), filter = productJSON({...query, request_id: '', cursor: ''});
    // A new list refresh owns the following page sequence even if an older
    // request has not returned. Exact detail reads do not supersede that list.
    const sequence = query.kind === 'runs' ? (query.cursor ? this.listSequence : ++this.listSequence) : undefined;
    if (query.kind === 'runs' && !query.cursor) this.cursors.clear();
    const continuation = query.cursor ? this.cursors.get(query.cursor) : undefined;
    if (query.cursor && (!continuation || continuation.session !== token || continuation.sequence !== sequence || continuation.filter !== filter)) throw new RunReadClientError('stale_cursor');
    // A failed continuation may already have been consumed by Home. Never retry it.
    if (query.cursor) this.cursors.delete(query.cursor);
    let raw: string;
    try { raw = await this.transport.query(bytes); }
    catch { this.current(token, sequence); throw new RunReadClientError('read_unavailable'); }
    this.current(token, sequence); const view = parseRunView(raw, query);
    if (view.status === 'read') {
      if (continuation && (view.generation !== continuation.generation || view.authority_epoch !== continuation.epoch
        || (view.rows.length > 0 && view.rows[0]!.run_id <= continuation.last))) throw new RunReadClientError('stale_cursor');
      const count = (continuation?.count ?? 0) + view.rows.length; if (count > 32) throw new RunReadClientError('stale_cursor');
      if (view.cursor) {
        if (view.cursor === query.cursor || this.cursors.has(view.cursor) || this.cursors.size >= 4) throw new RunReadClientError('stale_cursor');
        this.cursors.set(view.cursor, {session: token, sequence: sequence!, filter, generation: view.generation, epoch: view.authority_epoch, count, last: view.rows.at(-1)!.run_id});
      }
    }
    return view;
  }
  readRuns(request: {request_id: string; project_id: string; work_id: string; cursor?: string}) {
    return this.read({...request, protocol: 'stead.run-query/1', kind: 'runs', run_id: '', cursor: request.cursor ?? ''});
  }
  readRun(request: {request_id: string; project_id: string; work_id: string; run_id: string}) {
    return this.read({...request, protocol: 'stead.run-query/1', kind: 'run', cursor: ''});
  }
}

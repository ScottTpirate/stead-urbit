import { newId, commandDigest } from './protocol';
import {ProductWorkClient} from './productClient';
import {DocChangeClient} from './docChangeClient';
import {productCarrierMode, type ProductCarrierMode} from './productCarrier';
import {parseProductJSON} from './productWire';
// Public HTTPS client. No owner cookies, channels, scries or administrative APIs.
export type Fields = Record<string, string>;
export type Row = Fields;
export type CodeReviewKey = { proposal_id: string; revision: string };
export type GitBrowseView = 'tree' | 'file';
export type GitBrowseResult = { commit: string } & (
  { status: 'tree'; entries: { name: string; kind: 'tree' | 'file' | 'symlink' | 'submodule'; oid: string }[]; truncated: boolean }
  | { status: 'file'; preview: 'text' | 'binary' | 'too-large'; bytes: number; text?: string }
);
export type GitChangesView = 'files' | 'patch';
export type GitChangesResult = { base: string; head: string } & (
  { status: 'files'; entries: { path: string; status: 'A' | 'M' | 'D' | 'T'; old_mode: string; new_mode: string }[]; truncated: boolean }
  | { status: 'patch'; path: string; preview: 'text' | 'binary' | 'too-large' | 'unsupported-type'; text?: string; sanitized?: boolean }
);
export type WorkDelegation = {
  id: string; worker: string; ref: string; expires: string;
  status: 'active' | 'expired' | 'revoked' | 'unavailable'; revocable: boolean;
  proposals: CodeReviewKey[];
};
export type CodeMerge = CodeReviewKey & { action: 'merge'; request_id: string };
export type ExternalMerge = CodeReviewKey & { action: 'external-merge'; request_id: string;
  worker_generation: string; worker_signature: string; proof: string };
export type CodeInput = { action: 'status' | 'create' | 'pack-view' }
  | { action: 'pack-accept'; snapshot: string; authority_epoch: string; request_id: string }
  | { action: 'issue'; access: 'read' | 'write' }
  | { action: 'revoke'; handle: string }
  | { action: 'protect'; ref: string }
  | ({ action: 'proposal' | 'approve' } & CodeReviewKey)
  | ({ action: 'submit'; work_id: string; ref: string; base_oid: string; head_oid: string; delegation_id: string } & CodeReviewKey)
  | { action: 'external-proposal'; proposal_id: string }
  | { action: 'external-list'; work_id?: string }
  | ({ action: 'external-submit'; work_id: string; source_ref: string; ref: string; base_oid: string; head_oid: string;
    base_snapshot: string; generation: string; request_id: string } & CodeReviewKey)
  | ({ action: 'external-approve'; base_snapshot: string; base_oid: string; head_oid: string; request_id: string } & CodeReviewKey)
  | { action: 'delegate'; delegation_id: string; worker_ship: string; work_id: string; ref: string; expires_at_ms: string }
  | { action: 'revoke-delegation'; delegation_id: string }
  | { action: 'work-delegations'; work_id: string }
  | CodeMerge | ExternalMerge;
export type ViewKind = 'identity' | 'projects' | 'project' | 'work' | 'comments' | 'assignees' | 'documents' | 'containers' | 'document' | 'relations' | 'search' | 'workspace-search' | 'my-work' | 'activity' | 'inbox' | 'receipt';
export interface Query {
  kind: ViewKind;
  project_id: string;
  container_id: string;
  resource_id: string;
  search: string;
  cursor: string;
}
export interface View {
  protocol: 'stead.query-result/3';
  status: 'read';
  request_id: string;
  kind: ViewKind;
  project_id: string;
  container_id: string;
  resource_id: string;
  authority_epoch: string;
  generation: string;
  cursor: string;
  rows: Record<string, Row>;
}
export type UpdateScope = Omit<Query, 'cursor'>;
export interface UpdateInput extends Omit<UpdateScope, 'kind'> {
  kind: ViewKind | '';
  action: 'open' | 'poll' | 'cancel' | 'resume';
  watch_id: string;
  cursor: string;
}
export interface UpdateResult {
  protocol: 'stead.update-result/3';
  request_id: string;
  status: 'watching' | 'updated' | 'resumed' | 'cancelled' | 'refresh_required';
  watch_id: string;
  cursor: string;
  generation: string;
  rows: Record<string, {sequence: string; generation: string}>;
}
export interface Command {
  protocol: 'stead.command/3';
  request_id: string;
  project_id: string;
  resource_id: string;
  expected_revision: string;
  authority_epoch: string;
  operation: string;
  payload: Fields;
}
export interface Receipt extends Fields {
  protocol: 'stead.receipt/3';
  status: 'accepted';
  request_id: string;
  project_id: string;
  resource_id: string;
  resource_revision: string;
  operation: string;
}
export class HomeError extends Error {
  constructor(readonly code: string) { super(code); }
}
const TOKEN = /^[0-9a-f]{64}$/u;
const GIT_OID = /^[0-9a-f]{40}$/u;
const DECIMAL = /^(0|[1-9][0-9]{0,19})$/u;
const CODE_GENERATION = /^(?:[0-9]|[1-5][0-9]|6[0-4])$/u;
const GIT_REF_HEX = /^(?:726566732f68656164732f|726566732f746167732f)(?:[0-9a-f]{2})+$/u;
export const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u;
const REVIEW_REVISION = /^(?:[1-9]|[1-5][0-9]|6[0-4])$/u;
export const MAX_EXTERNAL_CODE = 8192;
const EXTERNAL_ACTIONS = new Set(['external-list', 'external-proposal', 'external-submit', 'external-approve', 'external-merge']);
const EXTERNAL_MERGE_DENIALS = new Set(['invalid_request', 'proposal_unavailable', 'stale_review', 'worker_proof_denied',
  'approval-required', 'clock-conflict', 'denied', 'generation-conflict', 'history-capacity', 'history-conflict',
  'invalid-approval', 'invalid-board-context', 'invalid-candidate', 'invalid-intent', 'invalid-principal',
  'invalid-promotion', 'invalid-proposal', 'invalid-selection', 'manifest-conflict', 'merge-denied', 'pack-conflict',
  'pending-conflict', 'promotion-capacity', 'proof-conflict', 'request-capacity', 'request-reused', 'review-change-conflict',
  'review-denied', 'scope-conflict', 'self-merge', 'self-review', 'snapshot-conflict', 'source-conflict', 'stale-base',
  'stale-epoch', 'stale-proposal', 'stale-review', 'stale-revision', 'stale-selection', 'stale-target']);
const MAX_RESPONSE = 262144;
const BROWSE_PATH = '/stead/api/code/browse';
const CHANGES_PATH = '/stead/api/code/changes';
const GIT_NAME = /^(?:[0-9a-f]{2}){1,255}$/u;
const GIT_CHANGE_PATH = /^(?:[0-9a-f]{2}){1,1024}$/u;
const GIT_MODE = /^[0-7]{6}$/u;
export const SHIP = /^~[a-z]+(?:-{1,2}[a-z]+)*$/u;
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new HomeError('invalid_response');
  return value as Record<string, unknown>;
}
function fields(value: unknown): Fields {
  const result = object(value);
  if (Object.keys(result).length > 32 || Object.values(result).some(x => typeof x !== 'string')) throw new HomeError('invalid_response');
  return result as Fields;
}
function externalProposal(value: Fields, id = value.proposal_id): Fields {
  if (value.status !== 'proposal' || value.proposal_id !== id || !UUID.test(value.proposal_id ?? '')
    || !REVIEW_REVISION.test(value.revision ?? '') || !UUID.test(value.work_id ?? '') || !UUID.test(value.author ?? '')
    || value.reviewer === undefined || (value.reviewer !== '' && !UUID.test(value.reviewer))
    || !GIT_OID.test(value.base_oid ?? '') || !GIT_OID.test(value.head_oid ?? '') || !TOKEN.test(value.base_snapshot ?? '')
    || !CODE_GENERATION.test(value.generation ?? '') || !value.source_ref?.startsWith('refs/heads/') || !value.ref?.startsWith('refs/heads/')
    || (value.work_title !== undefined && value.work_title.length > 512)
    || (value.merged_request_id !== undefined && (value.merged_revision ? !UUID.test(value.merged_request_id) : value.merged_request_id !== ''))
    || !((value.merged_revision === '' && value.merged_snapshot === '')
      || (value.merged_revision === value.revision && TOKEN.test(value.merged_snapshot ?? '')))) throw new HomeError('invalid_response');
  return value;
}
export function packRefs(value: Fields): Fields {
  try {
    const refs = object(JSON.parse(value.refs ?? ''));
    const entries = Object.entries(refs);
    if (entries.length < 1 || entries.length > 64 || !value.head?.startsWith('726566732f68656164732f')
      || !Object.hasOwn(refs, value.head) || entries.some(([name, oid]) => name.length > 2048
        || !GIT_REF_HEX.test(name) || typeof oid !== 'string' || !GIT_OID.test(oid))) throw new HomeError('invalid_response');
    return refs as Fields;
  } catch { throw new HomeError('invalid_response'); }
}
async function boundedText(response: Response): Promise<string> {
  if (response.headers.get('content-type')?.split(';')[0] !== 'application/json') throw new HomeError('invalid_response');
  if (!response.body) throw new HomeError('invalid_response');
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let bytes = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      bytes += part.value.byteLength;
      if (bytes > MAX_RESPONSE) throw new HomeError('invalid_response');
      chunks.push(part.value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  finally { reader.releaseLock(); }
  const data = new Uint8Array(bytes);
  let offset = 0;
  for (const chunk of chunks) { data.set(chunk, offset); offset += chunk.length; }
  try { return new TextDecoder('utf-8', { fatal: true }).decode(data); }
  catch { throw new HomeError('invalid_response'); }
}
async function boundedJSON(response: Response, closedCapabilities = false): Promise<unknown> {
  const raw = await boundedText(response);
  try {
    return closedCapabilities ? parseProductJSON(raw, {bytes: MAX_RESPONSE, depth: 2, keys: 32}) : JSON.parse(raw);
  }
  catch { throw new HomeError('invalid_response'); }
}
export class HomeClient {
  // Lives only in memory. A fresh page uses the same-origin resume endpoint.
  private csrf = '';
  private generation = 0;
  private identity: Fields | null = null;
  private partition: object | null = null;
  private productCarrier: ProductCarrierMode = Object.freeze({kind: 'unsupported'});
  private capabilityRead?: object;
  private adopting = 0;
  private suspended = false;
  private inflight = new Set<AbortController>();
  private retired = new Set<HomeWatch>();
  private pendingMerges = new Map<string, CodeMerge>();
  private pendingExternalMerges = new Map<string, ExternalMerge>();
  readonly productWork = new ProductWorkClient({
    currentSession: () => this.currentSessionToken(),
    command: raw => this.postProduct('/stead/api/command', raw),
    query: raw => this.postProduct('/stead/api/query', raw),
  });
  readonly docChanges = new DocChangeClient({
    currentSession: () => this.currentSessionToken(),
    capabilities: () => this.productCarrier.kind === 'native-human-doc'
      ? {commands: 'stead.doc-change/1', queries: 'stead.doc-change-query/1'} : {commands: null, queries: null},
    command: raw => this.postProduct('/stead/api/command', raw),
    query: raw => this.postProduct('/stead/api/query', raw),
  });
  productMode(): ProductCarrierMode { return this.productCarrier; }
  currentSessionToken(): object | null {
    return this.adopting || this.suspended || !TOKEN.test(this.csrf) || !this.identity ? null : this.partition;
  }
  onInvalidated: () => void = () => {};
  private fence() {
    this.generation++;
    for (const controller of this.inflight) controller.abort();
    this.inflight.clear();
  }
  clear() {
    this.fence(); this.csrf = ''; this.identity = null; this.partition = null; this.adopting = 0; this.suspended = false; this.retired.clear(); this.clearCodeMerges(); this.onInvalidated();
  }
  private async postProduct(path: '/stead/api/command' | '/stead/api/query', raw: string): Promise<string> {
    if (this.productCarrier.kind !== 'native-human-doc') throw new HomeError('unsupported_operation');
    if (!this.currentSessionToken()) throw new HomeError(this.suspended ? 'resume_required' : 'session_required');
    if (new TextEncoder().encode(raw).byteLength > 65536) throw new HomeError('request_too_large');
    const generation = this.generation, carrier = this.productCarrier;
    const controller = new AbortController(); this.inflight.add(controller);
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, {method: 'POST', body: raw,
        headers: {'Content-Type': 'application/json', 'X-Stead-CSRF': this.csrf}, credentials: 'same-origin',
        cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer', signal: controller.signal});
      if (generation !== this.generation) throw new HomeError('session_changed');
      if (response.status === 401) { this.clear(); throw new HomeError('session_required'); }
      // Correlated product receipts and query refusals are returned with 200.
      // An HTTP/transport failure does not establish a business command outcome.
      if (response.status !== 200) throw new HomeError('outcome_unknown');
      const result = await boundedText(response);
      if (generation !== this.generation) throw new HomeError('session_changed');
      if (path === '/stead/api/query' && carrier !== this.productCarrier && this.productCarrier.kind !== 'native-human-doc') throw new HomeError('unsupported_operation');
      return result; // Exact bytes go straight to the closed protocol parsers.
    } catch (error) {
      if (error instanceof HomeError) throw error;
      throw new HomeError('outcome_unknown');
    } finally { clearTimeout(timer); this.inflight.delete(controller); }
  }
  private async post(path: string, body: unknown, authenticated: boolean, mutation = false, adoption = false,
    externalCode = '', signal?: AbortSignal): Promise<Record<string, unknown>> {
    if (authenticated && this.adopting && !adoption) throw new HomeError('session_changed');
    if (authenticated && this.suspended && !adoption) throw new HomeError('resume_required');
    if (authenticated && !TOKEN.test(this.csrf)) throw new HomeError('session_required');
    const raw = JSON.stringify(body);
    const browse = path === BROWSE_PATH || path === CHANGES_PATH;
    if (new TextEncoder().encode(raw).byteLength > (externalCode || browse ? MAX_EXTERNAL_CODE : 65536)) throw new HomeError('request_too_large');
    const generation = this.generation;
    const controller = new AbortController();
    const cancel = () => controller.abort();
    signal?.addEventListener('abort', cancel, { once: true });
    if (signal?.aborted) cancel();
    this.inflight.add(controller);
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (authenticated) headers['X-Stead-CSRF'] = this.csrf;
      const response = await fetch(path, { method: 'POST', headers, body: raw,
        credentials: 'same-origin', cache: 'no-store', redirect: 'error',
        referrerPolicy: 'no-referrer', signal: controller.signal });
      if (generation !== this.generation) throw new HomeError('session_changed');
      if (response.status === 401) { this.clear(); throw new HomeError('session_required'); }
      if (browse && response.headers.get('content-type')?.split(';')[0] !== 'application/json') {
        const feature = path === CHANGES_PATH ? 'changes' : 'browse';
        if ([404, 405].includes(response.status)) throw new HomeError(feature + '_unsupported');
        if ([502, 503, 504].includes(response.status)) throw new HomeError(feature + '_unavailable');
      }
      const value = object(await boundedJSON(response, path === '/stead/api/capabilities'));
      if (generation !== this.generation) throw new HomeError('session_changed');
      if (browse && !response.ok && Object.keys(value).length === 1
        && typeof value.error === 'string' && /^[a-z_]{1,64}$/u.test(value.error)) throw new HomeError(value.error);
      if (externalCode) {
        const names = Object.keys(value);
        const bare = names.length === 1 && Object.hasOwn(value, 'error');
        const rejected = names.length === 3 && value.protocol === 'stead.result/3' && value.status === 'rejected';
        if (externalCode === 'external-merge') {
          if (response.status === 409 && (bare || rejected) && typeof value.error === 'string'
            && EXTERNAL_MERGE_DENIALS.has(value.error)) throw new HomeError(value.error);
          if (!response.ok || value.status === 'rejected') throw new HomeError('outcome_unknown');
        } else if ([400, 403, 404, 409].includes(response.status) && (bare || rejected)
          && typeof value.error === 'string' && /^[a-z_-]{1,64}$/u.test(value.error)) throw new HomeError(value.error);
      }
      if (!response.ok && !(value.protocol === 'stead.result/3'
        && ((response.status === 403 && value.error === 'invalid_csrf') || path === '/stead/api/code'))) throw new HomeError('outcome_unknown');
      if (mutation) return value;
      if (value.status === 'rejected') {
        const errorCode = path === '/stead/api/code' ? /^[a-z_-]{1,64}$/u : /^[a-z_]{1,64}$/u;
        if (typeof value.error !== 'string' || !errorCode.test(value.error)) throw new HomeError('invalid_response');
        throw new HomeError(value.error);
      }
      if (!response.ok) throw new HomeError('outcome_unknown');
      return value;
    } catch (error) {
      if (error instanceof HomeError) throw error;
      throw new HomeError('outcome_unknown');
    } finally { clearTimeout(timer); this.inflight.delete(controller); signal?.removeEventListener('abort', cancel); }
  }
  async capabilities(): Promise<Fields> {
    const owner = Object.freeze({}), generation = this.generation;
    this.capabilityRead = owner;
    const current = () => this.capabilityRead === owner && this.generation === generation;
    try {
      const value = fields(await this.post('/stead/api/capabilities', { protocol: 'stead.capabilities/3' }, false));
      if (!current()) throw new HomeError('session_changed');
      if (value.protocol !== 'stead.capabilities/3' || value.profile !== 'configured-team') throw new HomeError('unsupported_version');
      this.productCarrier = productCarrierMode(value);
      return value;
    } catch (error) {
      // Resume may abort an older check after a newer check has been admitted.
      // Neither a late failure nor a late success can change that newer profile.
      if (!current()) throw new HomeError('session_changed');
      this.productCarrier = Object.freeze({kind: 'unsupported'});
      throw error;
    }
  }
  async start(input: string): Promise<Fields> {
    // Explicit logout is required before switching identities. The browser does
    // not silently cancel an existing member session using an actor name.
    const ship = input.trim();
    if (!/^~?[A-Za-z]+(?:-{1,2}[A-Za-z]+)*$/u.test(ship) || ship.length > (ship.startsWith('~') ? 64 : 63)) {
      throw new HomeError('invalid_ship_name');
    }
    const identity_ship = (ship.startsWith('~') ? ship : '~' + ship).toLowerCase();
    const value = fields(await this.post('/stead/auth/start', { protocol: 'stead.auth/1', identity_ship }, false));
    if (value.status !== 'pending' || !TOKEN.test(value.challenge_id ?? '')) throw new HomeError('invalid_response');
    return value;
  }
  async status(challenge_id: string): Promise<Fields> {
    const value = fields(await this.post('/stead/auth/status', { protocol: 'stead.auth/1', challenge_id }, false));
    if (!['pending', 'approved'].includes(value.status ?? '') || value.challenge_id !== challenge_id) throw new HomeError('invalid_response');
    return value;
  }
  private async adopt(value: Record<string, unknown>, ticket: number): Promise<Fields> {
    if (ticket !== this.generation) throw new HomeError('session_changed');
    const row = fields(value);
    if (row.status !== 'authenticated' || !TOKEN.test(row.csrf ?? '')) throw new HomeError('invalid_response');
    this.csrf = row.csrf!;
    const view = await this.readQuery({kind: 'identity', project_id: '', container_id: '', resource_id: '', search: '', cursor: ''}, true);
    if (ticket !== this.generation) throw new HomeError('session_changed');
    const person = Object.values(view.rows)[0];
    if (!person || !['principal_id', 'binding_id', 'binding_revision', 'identity_ship', 'session_audit_id'].every(key => !!person[key])) {
      throw new HomeError('invalid_response');
    }
    const changed = !this.identity || ['principal_id', 'binding_id', 'binding_revision', 'identity_ship', 'session_audit_id'].some(key => this.identity![key] !== person[key]);
    if (changed) { this.partition = Object.freeze({}); this.clearCodeMerges(); this.onInvalidated(); }
    this.identity = person;
    this.retired.clear(); // Confirmed resume/consumption retires prior server read handles.
    this.suspended = false;
    return person;
  }
  private async authenticate(path: string, body: Fields) {
    const previous = this.identity;
    this.fence(); const ticket = this.generation; this.adopting = ticket; this.suspended = true;
    try { return await this.adopt(await this.post(path, body, false), ticket); }
    catch (error) {
      // An unconfirmed resume may have rotated CSRF at home. Fence further
      // authenticated calls, retaining the prior identity partition and its
      // drafts/request IDs until explicit resume or confirmed invalidation.
      // post() already clears an authoritative 401; adopt() clears a changed
      // identity. A stale completion cannot alter the newer generation.
      if (ticket === this.generation && !previous) this.clear();
      throw error;
    }
    finally { if (ticket === this.generation) this.adopting = 0; }
  }
  async consume(challenge_id: string) {
    return this.authenticate('/stead/auth/consume', {protocol: 'stead.auth/1', challenge_id});
  }
  async resume() { return this.authenticate('/stead/auth/resume', {protocol: 'stead.auth/1'}); }
  async logout() {
    // Keep the credential available if the server did not confirm invalidation.
    try {
      const result = fields(await this.post('/stead/auth/logout', { protocol: 'stead.auth/1' }, true));
      if (result.status !== 'logged_out') throw new HomeError('outcome_unknown');
      this.clear();
    } catch (error) { if (error instanceof HomeError && error.code === 'session_required') return; throw new HomeError('logout_unconfirmed'); }
  }
  async query(query: Query): Promise<View> { return this.readQuery(query); }
  async browseCode(project_id: string, snapshot: string, ref: string, path: string[],
    view: GitBrowseView, signal?: AbortSignal): Promise<GitBrowseResult> {
    const protocol = 'stead.git-browse/1';
    if (!UUID.test(project_id) || !TOKEN.test(snapshot) || ref.length > 2048 || !GIT_REF_HEX.test(ref)
      || path.length > 12 || path.some(name => !GIT_NAME.test(name))
      || path.reduce((size, name) => size + name.length, 0) > 2048 || (view === 'file' && !path.length)) {
      throw new HomeError('invalid_request');
    }
    const value = await this.post(BROWSE_PATH, { protocol, project_id, snapshot, ref, path, view }, true, false, false, '', signal);
    if (value.protocol !== protocol || value.project_id !== project_id || value.snapshot !== snapshot || value.ref !== ref
      || !Array.isArray(value.path) || value.path.length !== path.length || value.path.some((name, index) => name !== path[index])
      || value.status !== view || typeof value.commit !== 'string' || !GIT_OID.test(value.commit)) throw new HomeError('invalid_response');
    const commit = value.commit;
    if (view === 'tree') {
      if (!Array.isArray(value.entries) || value.entries.length > 128 || typeof value.truncated !== 'boolean') {
        throw new HomeError('invalid_response');
      }
      const seen = new Set<string>();
      const entries: Extract<GitBrowseResult, { status: 'tree' }>['entries'] = value.entries.map(item => {
        const { name, kind, oid } = object(item);
        if (typeof name !== 'string' || !GIT_NAME.test(name) || seen.has(name)
          || (kind !== 'tree' && kind !== 'file' && kind !== 'symlink' && kind !== 'submodule')
          || typeof oid !== 'string' || !GIT_OID.test(oid)) throw new HomeError('invalid_response');
        seen.add(name);
        return { name, kind, oid };
      });
      return { status: 'tree', commit, entries, truncated: value.truncated };
    }
    const { preview, bytes, text } = value;
    if ((preview !== 'text' && preview !== 'binary' && preview !== 'too-large')
      || typeof bytes !== 'number' || !Number.isSafeInteger(bytes) || bytes < 0 || bytes > 99_999_999
      || (preview === 'text' ? typeof text !== 'string' || bytes > 32768 || new TextEncoder().encode(text).byteLength !== bytes
        : text !== undefined)) throw new HomeError('invalid_response');
    return { status: 'file', commit, preview, bytes, ...(typeof text === 'string' ? {text} : {}) };
  }
  async code(project_id: string, input: CodeInput): Promise<Fields> {
    const value = fields(await this.post('/stead/api/code', { protocol: 'stead.code/1', project_id, ...input }, true,
      false, false, EXTERNAL_ACTIONS.has(input.action) ? input.action : ''));
    if (value.protocol !== 'stead.code/1') throw new HomeError('invalid_response');
    if (input.action === 'pack-view' || input.action === 'pack-accept') {
      if (!['external', 'external-staged'].includes(value.status ?? '') || !TOKEN.test(value.snapshot ?? '')
        || !DECIMAL.test(value.authority_epoch ?? '') || value.authority_epoch === '0'
        || !DECIMAL.test(value.object_count ?? '') || Number(value.object_count) < 1
        || Number(value.object_count) > 16384 || (value.generation !== undefined && !CODE_GENERATION.test(value.generation)) || (value.status === 'external'
          && (!value.request_id || !DECIMAL.test(value.accepted_at_ms ?? '')))) throw new HomeError('invalid_response');
      if (value.generation_limit !== undefined && (!/^[1-9][0-9]{0,19}$/u.test(value.generation_limit)
        || BigInt(value.generation_limit) > 2n ** 64n - 1n || value.generation === undefined
        || BigInt(value.generation) > BigInt(value.generation_limit))) throw new HomeError('invalid_response');
      packRefs(value);
      if (input.action === 'pack-accept' && (value.status !== 'external' || value.snapshot !== input.snapshot
        || value.authority_epoch !== input.authority_epoch || value.request_id !== input.request_id)) {
        throw new HomeError('invalid_response');
      }
    }
    if (input.action === 'issue' && (value.status !== 'issued' || !TOKEN.test(value.handle ?? '')
      || !TOKEN.test(value.bearer ?? '') || !DECIMAL.test(value.expires_at_ms ?? ''))) throw new HomeError('invalid_response');
    if (input.action === 'proposal' && (value.status !== 'proposal' || value.proposal_id !== input.proposal_id
      || value.revision !== input.revision || !GIT_OID.test(value.base_oid ?? '') || !GIT_OID.test(value.head_oid ?? '')
      || !value.ref?.startsWith('refs/heads/') || !value.work_id || !value.author || value.reviewer === undefined
      || value.merged_revision === undefined || (value.merged_revision !== '' && !DECIMAL.test(value.merged_revision)))) {
      throw new HomeError('invalid_response');
    }
    if (['approve', 'submit', 'merge', 'delegate', 'revoke-delegation'].includes(input.action)
      && value.status !== 'accepted' && value.status !== 'replayed') throw new HomeError('invalid_response');
    if ((input.action === 'delegate' || input.action === 'revoke-delegation') && value.delegation_id !== input.delegation_id) {
      throw new HomeError('invalid_response');
    }
    if (input.action === 'merge' && (value.request_id !== input.request_id || value.proposal_id !== input.proposal_id
      || value.revision !== input.revision || !DECIMAL.test(value.repository_revision ?? '') || value.repository_revision === '0')) {
      throw new HomeError('invalid_response');
    }
    if (input.action === 'external-proposal') externalProposal(value, input.proposal_id);
    if ((input.action === 'external-submit' || input.action === 'external-approve')
      && (value.status !== 'accepted' || value.request_id !== input.request_id || value.proposal_id !== input.proposal_id
        || value.revision !== input.revision)) throw new HomeError('invalid_response');
    if (input.action === 'external-merge') {
      let proof: Record<string, unknown>;
      try { proof = object(JSON.parse(input.proof)); }
      catch { throw new HomeError('invalid_response'); }
      if (Object.keys(value).length !== 6 || value.status !== 'merged'
        || value.request_id !== input.request_id || value.proposal_id !== input.proposal_id
        || proof.request_id !== input.request_id || proof.proposal_id !== input.proposal_id || proof.revision !== input.revision
        || !TOKEN.test(value.snapshot ?? '') || value.snapshot !== proof.candidate_snapshot || !DECIMAL.test(value.generation ?? '')
        || typeof proof.generation !== 'string' || !DECIMAL.test(proof.generation)
        || BigInt(value.generation!) !== BigInt(proof.generation) + 1n) throw new HomeError('invalid_response');
    }
    return value;
  }
  async externalReviews(project: string, workId?: string): Promise<Fields[]> {
    const value = await this.code(project, { action: 'external-list', ...(workId ? { work_id: workId } : {}) });
    try {
      if (value.status !== 'proposals' || Object.keys(value).length !== 3) throw new HomeError('invalid_response');
      const rows: unknown = JSON.parse(value.rows!);
      if (!Array.isArray(rows) || rows.length > 64) throw new HomeError('invalid_response');
      const proposals = rows.map(row => externalProposal(fields(row)));
      if (new Set(proposals.map(row => row.proposal_id)).size !== proposals.length
        || (workId && proposals.some(row => row.work_id !== workId))) throw new HomeError('invalid_response');
      return proposals;
    } catch { throw new HomeError('invalid_response'); }
  }
  async workDelegations(project: string, work: string): Promise<WorkDelegation[]> {
    const value = await this.code(project, {action: 'work-delegations', work_id: work});
    try {
      if (value.status !== 'work-delegations' || value.work_id !== work) throw new HomeError('invalid_response');
      const rows = Object.entries(object(JSON.parse(value.rows!)));
      if (rows.length > 32) throw new HomeError('invalid_response');
      return rows.map(([id, record]) => {
        const row = fields(record);
        const {worker_ship: worker, ref, expires_at_ms: expires, status, can_revoke} = row;
        if (row.delegation_id !== id || !UUID.test(id) || !worker || worker.length > 64 || !SHIP.test(worker)
          || !ref?.startsWith('refs/heads/') || new TextEncoder().encode(ref).length > 128
          || !expires || !DECIMAL.test(expires) || !Number.isSafeInteger(Number(expires))
          || (status !== 'active' && status !== 'expired' && status !== 'revoked' && status !== 'unavailable')
          || (can_revoke !== 'yes' && can_revoke !== 'no')) throw new HomeError('invalid_response');
        const links = Object.entries(object(JSON.parse(row.proposals!)));
        if (links.length > 64) throw new HomeError('invalid_response');
        const proposals = links.map(([proposal_id, revision]) => {
          if (!UUID.test(proposal_id) || typeof revision !== 'string' || !REVIEW_REVISION.test(revision)) throw new HomeError('invalid_response');
          return {proposal_id, revision};
        });
        return {id, worker, ref, expires, status, proposals, revocable: can_revoke === 'yes'};
      });
    } catch { throw new HomeError('invalid_response'); }
  }
  async reviewChanges(project_id: string, snapshot: string, proposal_id: string, revision: string,
    view: GitChangesView, path: string, signal?: AbortSignal): Promise<GitChangesResult> {
    const protocol = 'stead.git-changes/1';
    if (!UUID.test(project_id) || !TOKEN.test(snapshot) || !UUID.test(proposal_id)
      || !REVIEW_REVISION.test(revision) || (view === 'files' ? path !== '' : !GIT_CHANGE_PATH.test(path))) {
      throw new HomeError('invalid_request');
    }
    const value = await this.post(CHANGES_PATH, {protocol, project_id, snapshot, proposal_id, revision, view, path}, true,
      false, false, '', signal);
    const {base, head} = value;
    if (value.protocol !== protocol || value.project_id !== project_id || value.snapshot !== snapshot
      || value.proposal_id !== proposal_id || value.revision !== revision || value.status !== view
      || typeof base !== 'string' || !GIT_OID.test(base) || typeof head !== 'string' || !GIT_OID.test(head)) throw new HomeError('invalid_response');
    if (view === 'files') {
      if (!Array.isArray(value.entries) || value.entries.length > 256 || typeof value.truncated !== 'boolean') throw new HomeError('invalid_response');
      const seen = new Set<string>();
      const entries: Extract<GitChangesResult, {status: 'files'}>['entries'] = value.entries.map(record => {
        const {path, status, old_mode, new_mode} = fields(record);
        if (!path || !GIT_CHANGE_PATH.test(path) || seen.has(path)
          || (status !== 'A' && status !== 'M' && status !== 'D' && status !== 'T')
          || !old_mode || !GIT_MODE.test(old_mode) || !new_mode || !GIT_MODE.test(new_mode)) throw new HomeError('invalid_response');
        seen.add(path);
        return {path, status, old_mode, new_mode};
      });
      return {status: 'files', base, head, entries, truncated: value.truncated};
    }
    const {preview, text, sanitized} = value;
    if (value.path !== path || (preview !== 'text' && preview !== 'binary' && preview !== 'too-large' && preview !== 'unsupported-type')
      || (preview === 'text' ? typeof text !== 'string' || new TextEncoder().encode(text).byteLength > 196608 || typeof sanitized !== 'boolean'
        : text !== undefined || sanitized !== undefined)) throw new HomeError('invalid_response');
    return {status: 'patch', base, head, path, preview, ...(typeof text === 'string' && typeof sanitized === 'boolean' ? {text, sanitized} : {})};
  }
  clearCodeMerges() { this.pendingMerges.clear(); this.pendingExternalMerges.clear(); }
  pendingCodeMerge(project: string): Readonly<CodeMerge> | undefined {
    return this.pendingMerges.get(project);
  }
  async mergeCode(project: string, key?: CodeReviewKey): Promise<Fields> {
    const prior = this.pendingMerges.get(project);
    if (prior && key && (key.proposal_id !== prior.proposal_id || key.revision !== prior.revision)) {
      throw new HomeError('code_merge_pending');
    }
    const request: CodeMerge | undefined = prior ?? (key && { ...key, action: 'merge', request_id: newId() });
    if (!request) throw new HomeError('no_pending_merge');
    this.pendingMerges.set(project, request);
    try {
      const receipt = await this.code(project, request);
      if (this.pendingMerges.get(project) === request) this.pendingMerges.delete(project);
      return receipt;
    } catch (error) {
      // A first confirmed rejection needs no retry. Once an outcome is
      // uncertain, a later denial cannot tell us whether the first applied.
      const uncertain = !(error instanceof HomeError)
        || ['outcome_unknown', 'invalid_response', 'session_changed'].includes(error.code);
      if (!prior && !uncertain && this.pendingMerges.get(project) === request) this.pendingMerges.delete(project);
      throw error;
    }
  }
  pendingExternalMerge(project: string): Readonly<CodeReviewKey> | undefined {
    const row = this.pendingExternalMerges.get(project);
    return row && { proposal_id: row.proposal_id, revision: row.revision };
  }
  stopExternalMergeRetry(project: string, key: CodeReviewKey): boolean {
    const row = this.pendingExternalMerges.get(project);
    if (!row || row.proposal_id !== key.proposal_id || row.revision !== key.revision) return false;
    return this.pendingExternalMerges.delete(project);
  }
  async recoverExternalMerge(project: string): Promise<Fields | null> {
    const pending = this.pendingExternalMerges.get(project);
    if (!pending) return null;
    const row = await this.code(project, { action: 'external-proposal', proposal_id: pending.proposal_id });
    const expected = object(JSON.parse(pending.proof)).candidate_snapshot;
    if (this.pendingExternalMerges.get(project) !== pending || row.merged_request_id !== pending.request_id
      || row.merged_revision !== pending.revision || row.merged_snapshot !== expected) return null;
    this.pendingExternalMerges.delete(project);
    return row;
  }
  async mergeExternalCode(project: string, input?: ExternalMerge): Promise<Fields> {
    const prior = this.pendingExternalMerges.get(project);
    if (prior && input) throw new HomeError('code_merge_pending');
    const request = prior ?? (input && { ...input });
    if (!request) throw new HomeError('no_pending_merge');
    this.pendingExternalMerges.set(project, request);
    try {
      const receipt = await this.code(project, request);
      if (this.pendingExternalMerges.get(project) === request) this.pendingExternalMerges.delete(project);
      return { ...receipt, revision: request.revision };
    } catch (error) {
      const uncertain = !(error instanceof HomeError)
        || ['outcome_unknown', 'invalid_response', 'session_changed'].includes(error.code);
      if (!prior && !uncertain && this.pendingExternalMerges.get(project) === request) this.pendingExternalMerges.delete(project);
      throw error;
    }
  }
  private async readQuery(query: Query, adoption = false): Promise<View> {
    const request_id = newId();
    const value = await this.post('/stead/api/query', { protocol: 'stead.query/3', request_id, ...query }, true, false, adoption);
    if (value.protocol !== 'stead.query-result/3' || value.request_id !== request_id || value.status !== 'read' || value.kind !== query.kind
      || value.project_id !== query.project_id || value.container_id !== query.container_id
      || value.resource_id !== query.resource_id || typeof value.generation !== 'string' || !TOKEN.test(value.generation)
      || typeof value.authority_epoch !== 'string' || !DECIMAL.test(value.authority_epoch)
      || typeof value.cursor !== 'string' || (value.cursor !== '' && !TOKEN.test(value.cursor))) throw new HomeError('invalid_response');
    const rows = object(value.rows);
    if (Object.keys(rows).length > 20) throw new HomeError('invalid_response');
    for (const row of Object.values(rows)) fields(row);
    return value as unknown as View;
  }
  async updates(input: UpdateInput): Promise<UpdateResult> {
    const request_id = newId();
    const value = await this.post('/stead/api/updates', {protocol: 'stead.updates/3', request_id, ...input}, true);
    const names = ['protocol', 'request_id', 'status', 'watch_id', 'cursor', 'generation', 'rows'];
    if (Object.keys(value).length !== names.length || names.some(name => !Object.hasOwn(value, name))
      || value.protocol !== 'stead.update-result/3' || value.request_id !== request_id) throw new HomeError('invalid_response');
    const expected = {open: 'watching', poll: 'updated', cancel: 'cancelled', resume: 'resumed'}[input.action];
    if (value.status !== expected && value.status !== 'refresh_required') throw new HomeError('invalid_response');
    const terminal = value.status === 'cancelled' || value.status === 'refresh_required';
    if (typeof value.watch_id !== 'string' || typeof value.cursor !== 'string' || typeof value.generation !== 'string'
      || (terminal ? value.cursor !== '' || value.generation !== '' : !TOKEN.test(value.watch_id) || !TOKEN.test(value.cursor) || !TOKEN.test(value.generation))
      || (input.action === 'poll' || input.action === 'cancel' ? value.watch_id !== input.watch_id : terminal && value.watch_id !== '')) throw new HomeError('invalid_response');
    const rows = object(value.rows); const keys = Object.keys(rows);
    if (keys.length > 16 || (value.status !== 'updated' && keys.length !== 0)
      || keys.some((key, index) => key !== String(index))) throw new HomeError('invalid_response');
    let previous: bigint | undefined;
    for (const item of Object.values(rows)) {
      const row = fields(item);
      if (Object.keys(row).length !== 2 || !TOKEN.test(row.generation ?? '') || !DECIMAL.test(row.sequence ?? '')) throw new HomeError('invalid_response');
      const sequence = BigInt(row.sequence!);
      if (sequence === 0n || sequence > 2n ** 64n - 1n || (previous !== undefined && sequence !== previous + 1n)) throw new HomeError('invalid_response');
      previous = sequence;
    }
    if (keys.length && (rows[keys.at(-1)!] as Fields).generation !== value.generation) throw new HomeError('invalid_response');
    return value as unknown as UpdateResult;
  }
  async watch(scope: UpdateScope, resumeCursor = ''): Promise<HomeWatch | null> {
    const partition = this.generation;
    for (const watch of [...this.retired]) await this.retire(watch);
    if (partition !== this.generation) throw new HomeError('session_changed');
    const result = await this.updates({...scope, action: resumeCursor ? 'resume' : 'open', watch_id: '', cursor: resumeCursor});
    if (partition !== this.generation) throw new HomeError('session_changed');
    if (result.status === 'refresh_required') return null;
    return new HomeWatch(this, scope, result, () => { if (partition !== this.generation) throw new HomeError('session_changed'); });
  }
  async retire(watch: HomeWatch): Promise<void> {
    if (!this.retired.has(watch) && this.retired.size >= 4) throw new HomeError('updates_cleanup_pending');
    this.retired.add(watch);
    try { await watch.cancel(); this.retired.delete(watch); }
    catch (error) {
      // React cleanup can retire an old handle after confirmed adoption has
      // already cleared this queue. It cannot cancel in the new partition or
      // prevent the new partition from opening its own watch.
      if (error instanceof HomeError && error.code === 'session_changed') { this.retired.delete(watch); return; }
      throw error;
    }
  }
  private async receipt(value: unknown, command: Command): Promise<Receipt> {
    const row = fields(value);
    const digest = await commandDigest(command);
    const person = this.identity;
    const expectedFields = ['protocol','status','request_id','canonical_sha256','project_id','resource_id','resource_kind','container_id','resource_revision','authority_epoch','operation','principal_id','binding_id','binding_revision','identity_ship','authentication','authentication_strength','session_audit_id','runtime','accepted_at_ms','git_commit_oid'];
    const resourceKind = command.operation.split('.')[0] === 'container' ? 'container' : command.operation.split('.')[0];
    if (Object.keys(row).length !== expectedFields.length || expectedFields.some(key => !Object.hasOwn(row, key))) throw new HomeError('invalid_response');
    if (row.resource_kind !== resourceKind || !['isolated-fake', 'live-synthetic'].includes(row.runtime!)
      || !DECIMAL.test(row.accepted_at_ms!) || BigInt(row.accepted_at_ms!) === 0n || BigInt(row.accepted_at_ms!) > (2n ** 64n - 1n)
      || (resourceKind === 'document' ? !/^[0-9a-f]{40}$/u.test(row.git_commit_oid!) : row.git_commit_oid !== '')) throw new HomeError('invalid_response');
    if (!person || row.protocol !== 'stead.receipt/3' || row.status !== 'accepted'
      || row.request_id !== command.request_id || row.project_id !== command.project_id
      || row.resource_id !== command.resource_id || row.operation !== command.operation
      || row.canonical_sha256 !== digest || row.authority_epoch !== command.authority_epoch
      || row.container_id !== (command.operation === 'container.create' ? command.resource_id : command.payload.container_id ?? '')
      || row.resource_revision !== String(BigInt(command.expected_revision) + 1n)
      || row.authentication !== 'native-approved-browser/1' || row.authentication_strength !== 'native-approved-browser'
      || ['principal_id', 'binding_id', 'binding_revision', 'identity_ship', 'session_audit_id'].some(key => row[key] !== person[key])) throw new HomeError('invalid_response');
    return row as Receipt;
  }
  async command(command: Command): Promise<Receipt> {
    if (!this.identity) throw new HomeError('session_required');
    const row = fields(await this.post('/stead/api/command', command, true, true));
    if (row.status === 'rejected') {
      if (row.protocol !== 'stead.result/3' || row.request_id !== command.request_id
        || row.canonical_sha256 !== await commandDigest(command)
        || !/^[a-z_]{1,64}$/u.test(row.error ?? '')) throw new HomeError('outcome_unknown');
      throw new HomeError(row.error!);
    }
    return this.receipt(row, command);
  }
  async recover(command: Command): Promise<Receipt> {
    let view: View;
    try {
      view = await this.query({kind: 'receipt', project_id: command.project_id,
        container_id: command.operation === 'container.create' ? command.resource_id : command.payload.container_id ?? '',
        resource_id: command.request_id, search: '', cursor: ''});
    } catch (error) {
      // A proposed collection may not exist because its first request
      // never arrived. Keep it unconfirmed only while fresh authority still
      // permits creation; never turn an inaccessible scope into a saved result.
      if (error instanceof HomeError && error.code === 'denied_or_not_found') {
        if (command.operation === 'container.create') {
          const current = await this.query({kind:'project',project_id:command.project_id,container_id:'',resource_id:'',search:'',cursor:''});
          const projects = Object.values(current.rows);
          const project = projects[0];
          if (projects.length === 1 && project?.project_id === command.project_id
              && project.authority_epoch === command.authority_epoch
              && (project.role === 'maintainer' || (project.role === 'contributor' && command.payload.visibility === 'private'))) {
            throw new HomeError('outcome_unknown');
          }
        }
      }
      throw error;
    }
    const row = Object.values(view.rows)[0];
    if (!row) throw new HomeError('outcome_unknown');
    return this.receipt(row, command);
  }

}
export class HomeWatch {
  private cursor: string;
  private generation: string;
  private lastSequence: bigint | undefined;
  private inflight = false;
  private closed = false;
  private cancelled = false;
  private cancelling: Promise<void> | null = null;
  readonly id: string;
  constructor(private client: HomeClient, readonly scope: UpdateScope, result: UpdateResult, private current: () => void) {
    this.id = result.watch_id; this.cursor = result.cursor; this.generation = result.generation;
  }
  get resumeCursor() { return this.cursor; }
  async poll(): Promise<UpdateResult> {
    this.current();
    if (this.closed) throw new HomeError('refresh_required');
    if (this.inflight) throw new HomeError('update_in_progress');
    this.inflight = true;
    try {
      const result = await this.client.updates({kind: '', project_id: '', container_id: '', resource_id: '', search: '', action: 'poll', watch_id: this.id, cursor: this.cursor});
      this.current();
      if (this.closed) throw new HomeError('refresh_required');
      if (result.status === 'refresh_required') { this.closed = true; return result; }
      if (result.cursor === this.cursor) throw new HomeError('invalid_response');
      const rows = Object.values(result.rows);
      if (rows.length && this.lastSequence !== undefined && BigInt(rows[0]!.sequence) !== this.lastSequence + 1n) throw new HomeError('invalid_response');
      if (!rows.length && result.generation !== this.generation) throw new HomeError('invalid_response');
      if (rows.length) this.lastSequence = BigInt(rows.at(-1)!.sequence);
      this.cursor = result.cursor; this.generation = result.generation;
      return result;
    } finally { this.inflight = false; }
  }
  async cancel(): Promise<void> {
    if (this.cancelled) return;
    if (this.cancelling) return this.cancelling;
    this.closed = true; this.current();
    this.cancelling = (async () => {
      await this.client.updates({kind: '', project_id: '', container_id: '', resource_id: '', search: '', action: 'cancel', watch_id: this.id, cursor: ''});
      this.current(); this.cancelled = true;
    })();
    try { await this.cancelling; } finally { this.cancelling = null; }
  }
}
export function command(project_id: string, resource_id: string, expected_revision: string,
  authority_epoch: string, operation: string, payload: Fields): Command {
  return { protocol: 'stead.command/3', request_id: newId(), project_id,
    resource_id, expected_revision, authority_epoch, operation, payload };
}

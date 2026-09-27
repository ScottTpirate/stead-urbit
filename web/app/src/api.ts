import { newId, commandDigest } from './protocol';
// Public HTTPS client. No owner cookies, channels, scries or administrative APIs.
export type Fields = Record<string, string>;
export type Row = Fields;
export type ViewKind = 'identity' | 'projects' | 'project' | 'work' | 'documents' | 'containers' | 'document' | 'relations' | 'search' | 'activity' | 'inbox' | 'receipt';
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
const DECIMAL = /^(0|[1-9][0-9]{0,19})$/u;
const MAX_RESPONSE = 262144;
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new HomeError('invalid_response');
  return value as Record<string, unknown>;
}
function fields(value: unknown): Fields {
  const result = object(value);
  if (Object.keys(result).length > 32 || Object.values(result).some(x => typeof x !== 'string')) throw new HomeError('invalid_response');
  return result as Fields;
}
async function boundedJSON(response: Response): Promise<unknown> {
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
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(data)); }
  catch { throw new HomeError('invalid_response'); }
}
export class HomeClient {
  // Lives only in memory. A fresh page uses the same-origin resume endpoint.
  private csrf = '';
  private generation = 0;
  private identity: Fields | null = null;
  private adopting = 0;
  private suspended = false;
  private inflight = new Set<AbortController>();
  onInvalidated: () => void = () => {};
  private fence() {
    this.generation++;
    for (const controller of this.inflight) controller.abort();
    this.inflight.clear();
  }
  clear() {
    this.fence(); this.csrf = ''; this.identity = null; this.adopting = 0; this.suspended = false; this.onInvalidated();
  }
  private async post(path: string, body: unknown, authenticated: boolean, mutation = false, adoption = false): Promise<Record<string, unknown>> {
    if (authenticated && this.adopting && !adoption) throw new HomeError('session_changed');
    if (authenticated && this.suspended && !adoption) throw new HomeError('resume_required');
    if (authenticated && !TOKEN.test(this.csrf)) throw new HomeError('session_required');
    const raw = JSON.stringify(body);
    if (new TextEncoder().encode(raw).byteLength > 65536) throw new HomeError('request_too_large');
    const generation = this.generation;
    const controller = new AbortController();
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
      const value = object(await boundedJSON(response));
      if (generation !== this.generation) throw new HomeError('session_changed');
      if (!response.ok && !(response.status === 403 && value.protocol === 'stead.result/3' && value.error === 'invalid_csrf')) throw new HomeError('outcome_unknown');
      if (mutation) return value;
      if (value.status === 'rejected') {
        if (typeof value.error !== 'string' || !/^[a-z_]{1,64}$/u.test(value.error)) throw new HomeError('invalid_response');
        throw new HomeError(value.error);
      }
      if (!response.ok) throw new HomeError('outcome_unknown');
      return value;
    } catch (error) {
      if (error instanceof HomeError) throw error;
      throw new HomeError('outcome_unknown');
    } finally { clearTimeout(timer); this.inflight.delete(controller); }
  }
  async capabilities(): Promise<Fields> {
    const value = fields(await this.post('/stead/api/capabilities', { protocol: 'stead.capabilities/3' }, false));
    if (value.protocol !== 'stead.capabilities/3' || value.profile !== 'configured-team') throw new HomeError('unsupported_version');
    return value;
  }
  async start(identity_ship: string): Promise<Fields> {
    // Explicit logout is required before switching identities. The browser does
    // not silently cancel an existing member session using an actor name.
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
    if (changed) this.onInvalidated();
    this.identity = person;
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
  private async receipt(value: unknown, command: Command): Promise<Receipt> {
    const row = fields(value);
    const digest = await commandDigest(command);
    const person = this.identity;
    const expectedFields = ['protocol','status','request_id','canonical_sha256','project_id','resource_id','resource_kind','container_id','resource_revision','authority_epoch','operation','principal_id','binding_id','binding_revision','identity_ship','authentication','authentication_strength','session_audit_id','runtime','accepted_at_ms','git_commit_oid'];
    const resourceKind = command.operation.split('.')[0] === 'container' ? 'container' : command.operation.split('.')[0];
    if (Object.keys(row).length !== expectedFields.length || expectedFields.some(key => !Object.hasOwn(row, key))) throw new HomeError('invalid_response');
    if (row.resource_kind !== resourceKind || row.runtime !== 'isolated-fake'
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
    const view = await this.query({kind: 'receipt', project_id: command.project_id,
      container_id: command.operation === 'container.create' ? command.resource_id : command.payload.container_id ?? '',
      resource_id: command.request_id, search: '', cursor: ''});
    const row = Object.values(view.rows)[0];
    if (!row) throw new HomeError('outcome_unknown');
    return this.receipt(row, command);
  }

}
export function command(project_id: string, resource_id: string, expected_revision: string,
  authority_epoch: string, operation: string, payload: Fields): Command {
  return { protocol: 'stead.command/3', request_id: newId(), project_id,
    resource_id, expected_revision, authority_epoch, operation, payload };
}

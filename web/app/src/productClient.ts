// Reserved adapter: callers must supply the eventual reviewed authenticated
// carrier. No route, cookie, CSRF, capability or authority is implemented here.
import {encodeProductCommand, encodeProductQuery, parseProductCommand, parseProductQuery, parseProductReceipt, parseProductView, productCommandDigest,
  type Completion, type ProductCommand, type ProductContract, type ProductProperties, type ProductQuery, type ProductScope,
  type UnfinishedStatus, type WorkContractRevisions} from './productProtocol';
export type ProductSessionToken = string | object;
export interface ProductTransport {
  currentSession(): ProductSessionToken | null;
  command(canonicalBytes: string): Promise<string>;
  query(canonicalBytes: string): Promise<string>;
}
export type PreparedProductCommand = Readonly<{command: ProductCommand; bytes: string; digest: string}>;
export class ProductClientError extends Error {
  constructor(readonly code: 'session_required' | 'session_changed' | 'outcome_unknown' | 'unrecognized_prepared_command') { super(code); }
}
export class ProductWorkClient {
  private readonly prepared = new WeakMap<PreparedProductCommand, ProductSessionToken>();
  constructor(private readonly transport: ProductTransport) {}
  private session() {
    const token = this.transport.currentSession();
    if (token === null || token === '') throw new ProductClientError('session_required');
    return token;
  }
  private check(token: ProductSessionToken) {
    if (this.transport.currentSession() !== token) throw new ProductClientError('session_changed');
  }
  async prepare(value: ProductCommand): Promise<PreparedProductCommand> {
    const token = this.session(), bytes = encodeProductCommand(value), command = parseProductCommand(bytes);
    const digest = await productCommandDigest(command); this.check(token);
    const prepared = Object.freeze({command, bytes, digest}); this.prepared.set(prepared, token); return prepared;
  }
  prepareCreate(scope: ProductScope, properties: ProductProperties, contract: ProductContract) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.create',
      expected: {work_revision: '0', execution_contract_revision: '0'}, payload: {...properties, ...contract}});
  }
  prepareProperties(scope: ProductScope, work_revision: string, payload: ProductProperties) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.update-properties', expected: {work_revision}, payload});
  }
  prepareContract(scope: ProductScope, execution_contract_revision: string, payload: ProductContract) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.update-contract', expected: {execution_contract_revision}, payload});
  }
  prepareLegacyBlocked(scope: ProductScope, work_revision: string, status: UnfinishedStatus, blocked_reason: string) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.resolve-legacy-blocked', expected: {work_revision}, payload: {status, blocked_reason}});
  }
  prepareLegacyAssignee(scope: ProductScope, work_revision: string, owner_principal_id: string, worker_principal_id: string) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.resolve-legacy-assignee', expected: {work_revision}, payload: {owner_principal_id, worker_principal_id}});
  }
  prepareComment(scope: ProductScope, discussion_sequence: string, body: string) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.comment', expected: {discussion_sequence}, payload: {body}});
  }
  prepareCompletion(scope: ProductScope, expected: WorkContractRevisions, payload: Completion) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.complete', expected, payload});
  }
  prepareDelete(scope: ProductScope, expected: WorkContractRevisions & {discussion_sequence: string}) {
    return this.prepare({...scope, protocol: 'stead.command/4', operation: 'work.delete', expected, payload: {}});
  }
  async submit(prepared: PreparedProductCommand) {
    const token = this.prepared.get(prepared);
    if (token === undefined) throw new ProductClientError('unrecognized_prepared_command');
    this.check(token);
    let raw: string;
    try { raw = await this.transport.command(prepared.bytes); }
    catch { this.check(token); throw new ProductClientError('outcome_unknown'); }
    this.check(token);
    try { return parseProductReceipt(raw, prepared.command, prepared.digest); }
    catch { this.check(token); throw new ProductClientError('outcome_unknown'); }
  }
  // Explicit retries reuse the same frozen object/bytes/request and session.
  retry(prepared: PreparedProductCommand) { return this.submit(prepared); }
  async read(query: ProductQuery) {
    const token = this.session(), bytes = encodeProductQuery(query), request = parseProductQuery(bytes);
    let raw: string;
    try { raw = await this.transport.query(bytes); }
    catch { this.check(token); throw new ProductClientError('outcome_unknown'); }
    this.check(token);
    return parseProductView(raw, request);
  }
  readWork(request: {request_id: string; project_id: string; resource_id?: string; cursor?: string}) {
    return this.read({...request, protocol: 'stead.query/4', kind: 'work', container_id: '', search: '', resource_id: request.resource_id ?? '', cursor: request.cursor ?? ''});
  }
  readComments(request: {request_id: string; project_id: string; resource_id: string; cursor?: string}) {
    return this.read({...request, protocol: 'stead.query/4', kind: 'comments', container_id: '', search: '', cursor: request.cursor ?? ''});
  }
}

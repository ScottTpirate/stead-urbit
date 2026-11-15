// Reserved callable adapter. Capability values must come from an eventual
// reviewed carrier; none are advertised or fetched by this module.
import {docChangeCommandDigest, encodeDocChangeCommand, parseDocChangeCommand, type DocChangeCommand} from './docChangeProtocol';
import {encodeDocChangeQuery, parseDocChangeQuery, parseDocChangeReceipt, parseDocChangeView, snapshotDocChangeOutput, verifyDocChangeBody,
  type DocChangePreview, type DocChangeQuery} from './docChangeReadProtocol';
import {productJSON} from './productWire';
export type DocChangeSessionToken = string | object;
export type DocChangeCapabilities = {queries: 'stead.doc-change-query/1' | null; commands: 'stead.doc-change/1' | null};
export type PreparedDocChangeCommand = Readonly<{command: DocChangeCommand; bytes: string; digest: string}>;
export interface DocChangeTransport {
  currentSession(): DocChangeSessionToken | null;
  capabilities?(): DocChangeCapabilities;
  query(bytes: string): Promise<string>;
  command(bytes: string): Promise<string>;
}
export class DocChangeClientError extends Error {
  constructor(readonly code: 'session_required' | 'session_changed' | 'unsupported_operation' | 'outcome_unknown' | 'unrecognized_prepared_command' | 'stale_cursor' | 'body_pin_required') { super(code); }
}
type Cursor = {session: DocChangeSessionToken; filter: string; generation: string; epoch: string};
export class DocChangeClient {
  private readonly prepared = new WeakMap<PreparedDocChangeCommand, DocChangeSessionToken>();
  private readonly cursors = new Map<string, Cursor>();
  constructor(private readonly transport: DocChangeTransport) {}
  currentSessionToken() { return this.transport.currentSession(); }
  private session() { const token = this.transport.currentSession(); if (token === null || token === '') throw new DocChangeClientError('session_required');
    for (const [cursor,record] of this.cursors) if (record.session !== token) this.cursors.delete(cursor); return token; }
  private check(token: DocChangeSessionToken) { if (this.transport.currentSession() !== token) throw new DocChangeClientError('session_changed'); }
  private capability(kind: 'queries' | 'commands') {
    const value = this.transport.capabilities?.();
    if (value?.[kind] !== (kind === 'queries' ? 'stead.doc-change-query/1' : 'stead.doc-change/1')) throw new DocChangeClientError('unsupported_operation');
  }
  async prepare(value: DocChangeCommand): Promise<PreparedDocChangeCommand> {
    this.capability('commands'); const token = this.session(), bytes = encodeDocChangeCommand(value), command = parseDocChangeCommand(bytes);
    const digest = await docChangeCommandDigest(command); this.check(token); this.capability('commands');
    const prepared = Object.freeze({command,bytes,digest}); this.prepared.set(prepared,token); return prepared;
  }
  async submit(prepared: PreparedDocChangeCommand) {
    const token = this.prepared.get(prepared); if (token === undefined) throw new DocChangeClientError('unrecognized_prepared_command');
    this.check(token); this.capability('commands'); let raw: string;
    try { raw = await this.transport.command(prepared.bytes); }
    catch { this.check(token); throw new DocChangeClientError('outcome_unknown'); }
    this.check(token);
    // A malformed or mismatched receipt does not prove that the command failed.
    try { return parseDocChangeReceipt(raw,prepared.command,prepared.digest); }
    catch { this.check(token); throw new DocChangeClientError('outcome_unknown'); }
  }
  retry(prepared: PreparedDocChangeCommand) { return this.submit(prepared); }
  async read(value: DocChangeQuery, expectedBody?: DocChangePreview): Promise<ReturnType<typeof parseDocChangeView>> {
    this.capability('queries'); const token = this.session(), bytes = encodeDocChangeQuery(value), query = parseDocChangeQuery(bytes);
    if (query.kind === 'body' && !expectedBody) throw new DocChangeClientError('body_pin_required');
    const bodyPin = query.kind === 'body' ? snapshotDocChangeOutput(expectedBody!,query) : undefined;
    const filter = productJSON({...query,request_id:'',cursor:''});
    const continuation = query.cursor ? this.cursors.get(query.cursor) : undefined;
    if (query.cursor && (!continuation || continuation.session !== token || continuation.filter !== filter)) throw new DocChangeClientError('stale_cursor');
    // Native continuations are one-use. Unknown read outcomes require a fresh first page.
    if (query.cursor) this.cursors.delete(query.cursor);
    let raw: string;
    try { raw = await this.transport.query(bytes); }
    catch { this.check(token); throw new DocChangeClientError('outcome_unknown'); }
    this.check(token); this.capability('queries');
    const view = parseDocChangeView(raw,query);
    if (view.status === 'read') {
      if (continuation && (view.generation !== continuation.generation || view.authority_epoch !== continuation.epoch)) throw new DocChangeClientError('stale_cursor');
      if (view.kind === 'body') { await verifyDocChangeBody(view.rows[0]!,bodyPin!); this.check(token); this.capability('queries'); }
      if (view.cursor) {
        if (!query.cursor) this.cursors.clear();
        if (view.cursor === query.cursor || this.cursors.has(view.cursor) || this.cursors.size >= 4) throw new DocChangeClientError('stale_cursor');
        this.cursors.set(view.cursor,{session:token,filter,generation:view.generation,epoch:view.authority_epoch});
      }
    }
    return view;
  }
  readChanges(request: {request_id: string; project_id: string; work_id: string; cursor?: string}) {
    return this.read({...request,protocol:'stead.doc-change-query/1',kind:'changes',change_id:'',result_revision:'0',result_digest:'',side:'',cursor:request.cursor ?? ''});
  }
  readDetail(request: {request_id: string; project_id: string; work_id: string; change_id: string; result_revision?: string; result_digest?: string}) {
    return this.read({...request,protocol:'stead.doc-change-query/1',kind:'change',result_revision:request.result_revision ?? '0',result_digest:request.result_digest ?? '',side:'',cursor:''});
  }
  readResults(request: {request_id: string; project_id: string; work_id: string; change_id: string; cursor?: string}) {
    return this.read({...request,protocol:'stead.doc-change-query/1',kind:'results',result_revision:'0',result_digest:'',side:'',cursor:request.cursor ?? ''});
  }
  readBody(requestId: string, output: DocChangePreview, side: 'before' | 'after') {
    return this.read({protocol:'stead.doc-change-query/1',request_id:requestId,kind:'body',project_id:output.project_id,work_id:output.work_id,change_id:output.change_id,
      result_revision:output.result_revision,result_digest:output.result_digest,side,cursor:''},output);
  }
}

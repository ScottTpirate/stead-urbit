// Reserved human answer/cancel boundary only. No endpoint, capability, worker
// dispatch or authority is supplied here. An answer does not resume a worker;
// accepted cancellation does not prove process exit or undo accepted changes.
import {byteLength, freeze, keys, parseProductJSON, productJSON, ProductProtocolError, protocolText} from './productWire';
import type {RunPhase, RunSessionToken} from './runReadProtocol';

export type RunControlScope = {request_id: string; project_id: string; run_id: string; expected_revision: string; expected_attempt: string};
export type RunControlCommand = RunControlScope & {protocol: 'stead.run-command/1'; operation: 'answer' | 'cancel'; payload: string};
export type RunAnswerPayload = {question: string; text: string};
export type RunControlError = 'invalid_request' | 'invalid_capacity' | 'denied_or_not_found' | 'request_id_reuse' | 'capacity_exceeded'
  | 'invalid_time' | 'revision_conflict' | 'terminal_run' | 'invalid_reason' | 'stale_contract_or_authority' | 'expired_authority'
  | 'invalid_answer' | 'unknown_question' | 'already_answered';
type ReceiptBase = {protocol: 'stead.run-result/1'; request_id: string; canonical_sha256: string};
type ReceiptHead = {run_id: string; run_revision: string; attempt: string; phase: RunPhase};
export type RunControlReceipt = (ReceiptBase & {status: 'rejected'; error: RunControlError} & Partial<ReceiptHead>)
  | (ReceiptBase & ReceiptHead & {status: 'accepted'; error: ''});
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u;
const HASH = /^[a-f0-9]{64}$/u;
const commandKeys = ['protocol','request_id','project_id','run_id','expected_revision','expected_attempt','operation','payload'];
const receiptKeys = ['protocol','status','request_id','canonical_sha256','error'];
const errors: readonly string[] = ['invalid_request','invalid_capacity','denied_or_not_found','request_id_reuse','capacity_exceeded','invalid_time',
  'revision_conflict','terminal_run','invalid_reason','stale_contract_or_authority','expired_authority','invalid_answer','unknown_question','already_answered'];
function requireValue(condition: unknown): asserts condition { if (!condition) throw new ProductProtocolError(); }
function uint(value: unknown, positive = false): asserts value is string {
  protocolText(value); requireValue(/^(?:0|[1-9][0-9]{0,19})$/u.test(value) && BigInt(value) <= 18446744073709551615n && (!positive || value !== '0'));
}
function prose(value: unknown, limit: number): asserts value is string {
  protocolText(value); requireValue(byteLength(value) > 0 && byteLength(value) <= limit && !value.includes('\r'));
}
export function parseRunAnswer(raw: string): Readonly<RunAnswerPayload> {
  const row = parseProductJSON(raw, {bytes: 16384, depth: 1, keys: 2}); keys(row, ['question','text']);
  uint(row.question, true); prose(row.text, 2048); requireValue(productJSON(row) === raw);
  return freeze(row as unknown as RunAnswerPayload);
}
export function parseRunControlCommand(raw: string): Readonly<RunControlCommand> {
  const row = parseProductJSON(raw, {bytes: 65536, depth: 1, keys: 8}); keys(row, commandKeys);
  for (const value of Object.values(row)) protocolText(value);
  requireValue(row.protocol === 'stead.run-command/1');
  for (const key of ['request_id','project_id','run_id']) requireValue(UUID.test(row[key] as string));
  uint(row.expected_revision, true); uint(row.expected_attempt); requireValue(BigInt(row.expected_attempt) <= 3n);
  if (row.operation === 'answer') parseRunAnswer(row.payload as string);
  else { requireValue(row.operation === 'cancel'); prose(row.payload, 256); }
  return freeze(row as unknown as RunControlCommand);
}
export function encodeRunControlCommand(value: unknown): string { return productJSON(parseRunControlCommand(productJSON(value))); }
export async function runControlDigest(command: RunControlCommand): Promise<string> {
  const bytes = new TextEncoder().encode('stead.run-command/1\0' + encodeRunControlCommand(command));
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(value => value.toString(16).padStart(2,'0')).join('');
}
export function parseRunControlReceipt(raw: string, request: RunControlCommand, commandDigest: string): Readonly<RunControlReceipt> {
  try {
    const command = parseRunControlCommand(encodeRunControlCommand(request));
    const row = parseProductJSON(raw, {bytes: 8192, depth: 1, keys: 9});
    for (const value of Object.values(row)) protocolText(value);
    requireValue(HASH.test(commandDigest) && row.protocol === 'stead.run-result/1' && row.request_id === command.request_id
      && row.canonical_sha256 === commandDigest && (row.status === 'accepted' || row.status === 'rejected'));
    requireValue(row.status === 'accepted' ? row.error === '' : errors.includes(row.error as string));
    if (row.status === 'rejected' && Object.keys(row).length === 5) keys(row, receiptKeys);
    else {
      keys(row, [...receiptKeys,'run_id','run_revision','attempt','phase']); requireValue(row.run_id === command.run_id);
      uint(row.run_revision, true); uint(row.attempt); requireValue(BigInt(row.attempt) <= 3n);
      requireValue(['queued','running','waiting','submitted','failed','canceled'].includes(row.phase as string));
      if (row.status === 'accepted') requireValue(BigInt(row.run_revision) === BigInt(command.expected_revision) + 1n
        && row.attempt === command.expected_attempt && row.phase === (command.operation === 'answer' ? 'waiting' : 'canceled'));
    }
    return freeze(row as unknown as RunControlReceipt);
  } catch { throw new ProductProtocolError('invalid_response'); }
}

export type PreparedRunControl = Readonly<{command: Readonly<RunControlCommand>; bytes: string; digest: string}>;
export interface RunControlTransport {
  currentSession(): RunSessionToken | null;
  capability?(): 'stead.run-command/1' | null;
  command(bytes: string): Promise<string>;
}
export class RunControlClientError extends Error {
  constructor(readonly code: 'session_required' | 'session_changed' | 'unsupported_operation' | 'outcome_unknown'
    | 'unrecognized_prepared_command' | 'command_pending') { super(code); }
}
type Preparation = {session: RunSessionToken; generation: number; pending: boolean};
export class RunControlClient {
  private readonly prepared = new WeakMap<PreparedRunControl, Preparation>();
  private generation = 0;
  constructor(private readonly transport: RunControlTransport) {}
  currentSessionToken() { return this.transport.currentSession(); }
  invalidate() { this.generation++; }
  private capability() { if (this.transport.capability?.() !== 'stead.run-command/1') throw new RunControlClientError('unsupported_operation'); }
  private check(record: Preparation) {
    if (record.generation !== this.generation || this.transport.currentSession() !== record.session) throw new RunControlClientError('session_changed');
  }
  async prepare(value: RunControlCommand): Promise<PreparedRunControl> {
    this.capability(); const session = this.transport.currentSession();
    if (session === null || session === '') throw new RunControlClientError('session_required');
    const record: Preparation = {session, generation: this.generation, pending: false};
    const bytes = encodeRunControlCommand(value), command = parseRunControlCommand(bytes), digest = await runControlDigest(command);
    this.check(record); this.capability(); const prepared = Object.freeze({command,bytes,digest}); this.prepared.set(prepared,record); return prepared;
  }
  prepareAnswer(scope: RunControlScope, answer: RunAnswerPayload) {
    return this.prepare({...scope,protocol:'stead.run-command/1',operation:'answer',payload:productJSON(answer)});
  }
  prepareCancel(scope: RunControlScope, reason: string) {
    return this.prepare({...scope,protocol:'stead.run-command/1',operation:'cancel',payload:reason});
  }
  async submit(prepared: PreparedRunControl): Promise<Readonly<RunControlReceipt>> {
    const record = this.prepared.get(prepared);
    if (!record) throw new RunControlClientError('unrecognized_prepared_command');
    this.check(record); this.capability(); if (record.pending) throw new RunControlClientError('command_pending');
    record.pending = true;
    try {
      let raw: string;
      try { raw = await this.transport.command(prepared.bytes); }
      catch { this.check(record); throw new RunControlClientError('outcome_unknown'); }
      this.check(record);
      // Capability withdrawal blocks future sends. A verified in-flight receipt
      // still reconciles this exact request; a malformed reply proves no outcome.
      try { return parseRunControlReceipt(raw,prepared.command,prepared.digest); }
      catch { throw new RunControlClientError('outcome_unknown'); }
    } finally { record.pending = false; }
  }
  retry(prepared: PreparedRunControl) { return this.submit(prepared); }
}

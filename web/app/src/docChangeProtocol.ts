// Reserved stead.doc-change/1 syntax only. No route, capability, producer,
// review authority, acceptance context or run lease is supplied by this codec.
import {byteLength, freeze, keys, object, parseProductJSON, productJSON, ProductProtocolError, protocolText} from './productWire';
import type {DocumentOutcome} from './productProtocol';
export {ProductProtocolError as DocChangeProtocolError} from './productWire';

export type DocChangeSubmitPayload = {
  outcome_id: string; target: DocumentOutcome; markdown: string; summary: string;
  execution_contract_revision: string; execution_contract_digest: string;
  run_id: string; attempt: string;
};
export type DocChangeDecisionOperation = 'change.request-changes' | 'change.approve' | 'change.adopt'
  | 'change.accept' | 'change.reject' | 'change.quarantine';
export type DocChangeDecisionPayload = {result_revision: string; result_digest: string; note: string};
export type DocChangeScope = {request_id: string; project_id: string; work_id: string; change_id: string;
  authority_epoch: string; expected_revision: string};
export type DocChangeCommand = DocChangeScope & {protocol: 'stead.doc-change/1'} & (
  | {operation: 'change.submit'; payload: DocChangeSubmitPayload}
  | {operation: DocChangeDecisionOperation; payload: DocChangeDecisionPayload}
);

const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u;
const HASH = /^[a-f0-9]{64}$/u;
const envelope = ['protocol', 'request_id', 'project_id', 'work_id', 'change_id', 'authority_epoch', 'expected_revision', 'operation', 'payload'];
const decisions: readonly string[] = ['change.request-changes', 'change.approve', 'change.adopt', 'change.accept', 'change.reject', 'change.quarantine'];
function requireValue(condition: unknown): asserts condition { if (!condition) throw new ProductProtocolError(); }
function uint(value: unknown, positive = false): asserts value is string {
  protocolText(value);
  requireValue(/^(?:0|[1-9][0-9]{0,19})$/u.test(value) && BigInt(value) <= 18446744073709551615n && (!positive || value !== '0'));
}
function uuid(value: unknown): asserts value is string { protocolText(value); requireValue(UUID.test(value)); }
function digest(value: unknown): asserts value is string { protocolText(value); requireValue(HASH.test(value)); }
function explanation(value: unknown): asserts value is string {
  protocolText(value); const bytes = new TextEncoder().encode(value);
  requireValue(bytes.length <= 2048 && bytes.every(byte => byte === 9 || byte === 10 || byte >= 32) && bytes.some(byte => byte > 32));
}
function commandValue(row: Record<string, unknown>): DocChangeCommand {
  keys(row, envelope); requireValue(row.protocol === 'stead.doc-change/1');
  for (const name of ['request_id', 'project_id', 'work_id', 'change_id']) uuid(row[name]);
  uint(row.authority_epoch, true); uint(row.expected_revision);
  const payload = object(row.payload);
  if (row.operation === 'change.submit') {
    keys(payload, ['outcome_id', 'target', 'markdown', 'summary', 'execution_contract_revision', 'execution_contract_digest', 'run_id', 'attempt']);
    uuid(payload.outcome_id);
    const target = object(payload.target);
    keys(target, ['kind', 'project_id', 'collection_id', 'document_id', 'expected_revision', 'base_markdown_sha256']);
    requireValue(target.kind === 'document' && target.project_id === row.project_id);
    uuid(target.collection_id); uuid(target.document_id); uint(target.expected_revision);
    if (target.expected_revision === '0') requireValue(target.base_markdown_sha256 === ''); else digest(target.base_markdown_sha256);
    protocolText(payload.markdown); requireValue(byteLength(payload.markdown) <= 32768 && !payload.markdown.includes('\r'));
    explanation(payload.summary); uint(payload.execution_contract_revision, true); digest(payload.execution_contract_digest);
    protocolText(payload.run_id); uint(payload.attempt);
    if (payload.run_id === '') requireValue(payload.attempt === '0'); else { uuid(payload.run_id); uint(payload.attempt, true); }
  } else {
    requireValue(typeof row.operation === 'string' && decisions.includes(row.operation)); uint(row.expected_revision, true);
    keys(payload, ['result_revision', 'result_digest', 'note']); uint(payload.result_revision, true); digest(payload.result_digest);
    // The note key remains mandatory; only approve/accept admit its empty string.
    if (!(['change.approve', 'change.accept'].includes(row.operation) && payload.note === '')) explanation(payload.note);
  }
  return freeze(row as unknown as DocChangeCommand);
}
export function parseDocChangeCommand(raw: string): DocChangeCommand {
  return commandValue(parseProductJSON(raw));
}
export function encodeDocChangeCommand(value: unknown): string {
  return productJSON(parseDocChangeCommand(productJSON(value)));
}
export async function docChangeCommandDigest(value: DocChangeCommand): Promise<string> {
  const bytes = new TextEncoder().encode('stead.doc-change/1\0' + encodeDocChangeCommand(value));
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

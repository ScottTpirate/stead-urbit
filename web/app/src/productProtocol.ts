// Reserved command/query/receipt4. This module advertises no capability and
// does not change the frozen command3 client or activate any network route.
import {byteLength, freeze, keys, object, parseProductJSON, productJSON, ProductProtocolError, protocolText} from './productWire';
export {ProductProtocolError} from './productWire';
export type ProductWorkType = 'deliverable' | 'task' | 'problem';
export type ProductPriority = 'none' | 'low' | 'medium' | 'high' | 'urgent';
export type ProductStatus = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'canceled';
export type UnfinishedStatus = Exclude<ProductStatus, 'done' | 'canceled'>;
export type ProductProperties = {type: ProductWorkType; status: ProductStatus; priority: ProductPriority;
  owner_principal_id: string; worker_principal_id: string; blocked_reason: string};
export type DocumentOutcome = {kind: 'document'; project_id: string; collection_id: string; document_id: string; expected_revision: string; base_markdown_sha256: string};
export type CodeOutcome = {kind: 'code'; project_id: string; repository_id: string; target_ref: string; base_oid: string};
export type NoteOutcome = {kind: 'completion-note'; project_id: string; work_id: string; expected_revision: string};
export type ProductOutcome = DocumentOutcome | CodeOutcome | NoteOutcome;
export type ProductOutcomes = Readonly<Record<string, ProductOutcome>>;
export type ProductContract = {title: string; description: string; acceptance_criteria: string; required_outcomes: ProductOutcomes};
export type ProductScope = {request_id: string; project_id: string; resource_id: string; authority_epoch: string};
export type Completion = {basis: 'accepted-outcomes'; note: ''} | {basis: 'human-note'; note: string};
export type WorkContractRevisions = {work_revision: string; execution_contract_revision: string};
export type ProductCommand = ProductScope & {protocol: 'stead.command/4'} & (
  | {operation: 'work.create'; expected: {work_revision: '0'; execution_contract_revision: '0'}; payload: ProductProperties & ProductContract}
  | {operation: 'work.update-properties'; expected: {work_revision: string}; payload: ProductProperties}
  | {operation: 'work.update-contract'; expected: {execution_contract_revision: string}; payload: ProductContract}
  | {operation: 'work.resolve-legacy-blocked'; expected: {work_revision: string}; payload: {status: UnfinishedStatus; blocked_reason: string}}
  | {operation: 'work.resolve-legacy-assignee'; expected: {work_revision: string}; payload: {owner_principal_id: string; worker_principal_id: string}}
  | {operation: 'work.comment'; expected: {discussion_sequence: string}; payload: {body: string}}
  | {operation: 'work.complete'; expected: WorkContractRevisions; payload: Completion}
  | {operation: 'work.delete'; expected: WorkContractRevisions & {discussion_sequence: string}; payload: Record<string, never>}
);
export type ProductQuery = {protocol: 'stead.query/4'; request_id: string; kind: 'work' | 'comments' | 'principals' | 'completion'; project_id: string;
  container_id: ''; resource_id: string; search: ''; cursor: string};
export type ProductWorkBase = {kind: 'work'; project_id: string; resource_id: string; container_id: ''; resource_revision: string;
  work_revision: string; execution_contract_protocol: 'stead.work-contract/2'; execution_contract_revision: string;
  execution_contract_digest: string; discussion_sequence: string; title: string; type: ProductWorkType;
  status: ProductStatus | 'legacy-blocked'; priority: ProductPriority; owner_principal_id: string; worker_principal_id: string;
  owner_display_name: string; worker_display_name: string};
export type ProductWorkPreview = ProductWorkBase & {snippet: string};
export type ProductWorkDetail = ProductWorkBase & {description: string; acceptance_criteria: string; required_outcomes: string;
  blocked_reason: string; completion_basis: '' | 'legacy' | 'human-note' | 'accepted-outcomes'; completion_principal_id: string;
  completion_request_id: string; completion_note: string; legacy_assignment_pending: 'yes' | 'no'; legacy_assignee_principal_id: string;
  legacy_assignee_display_name: string; legacy_blocked_pending: 'yes' | 'no'; legacy_blocked_status: '' | 'blocked'; legacy_prior_status: string};
export type ProductComment = {kind: 'comment'; project_id: string; work_id: string; sequence: string; body: string;
  principal_id: string; display_name: string; identity_ship: string; request_id: string; accepted_at_ms: string; legacy_comment_revision: string};
export type ProductPrincipal = {kind: 'principal'; principal_id: string; display_name: string;
  principal_kind: 'person' | 'agent' | 'service' | 'unresolved'; active: 'yes' | 'no'; project_role: 'reader' | 'contributor' | 'maintainer'};
export type ProductCompletion = {kind: 'completion'; project_id: string; work_id: string; execution_contract_revision: string;
  execution_contract_digest: string; ready: 'yes' | 'no'; reason: '' | 'human-note-required' | 'required-outcomes-unconfirmed'};
type QueryResult = {protocol: 'stead.query-result/4'; status: 'read'; request_id: string; project_id: string; container_id: '';
  resource_id: string; authority_epoch: string; generation: string; cursor: string};
export type ProductView = QueryResult & ({kind: 'work'; rows: readonly (ProductWorkPreview | ProductWorkDetail)[]}
  | {kind: 'comments'; rows: readonly ProductComment[]}
  | {kind: 'principals'; rows: readonly ProductPrincipal[]} | {kind: 'completion'; rows: readonly ProductCompletion[]});
export type ProductQueryRejection = {protocol: 'stead.query-result/4'; status: 'rejected'; request_id: string; error: string};
export type ProductResulting = WorkContractRevisions & {discussion_sequence: string; execution_contract_digest: string};
type ReceiptBase = {protocol: 'stead.receipt/4'; request_id: string; canonical_sha256: string; error: string};
export type ProductReceipt = (ReceiptBase & {status: 'rejected'}) | (ReceiptBase & ProductScope & {
  status: 'accepted' | 'rejected'; operation: ProductCommand['operation']; principal_id: string; recorded_at_ms: string;
  expected: ProductCommand['expected']; resulting: ProductResulting});

const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u;
const HASH = /^[a-f0-9]{64}$/u;
const statuses = ['backlog', 'todo', 'in_progress', 'in_review', 'done', 'canceled'];
const propertyKeys = ['type', 'status', 'priority', 'owner_principal_id', 'worker_principal_id', 'blocked_reason'];
const contractKeys = ['title', 'description', 'acceptance_criteria', 'required_outcomes'];
const commandKeys = ['protocol', 'request_id', 'project_id', 'resource_id', 'authority_epoch', 'operation', 'expected', 'payload'];
const queryKeys = ['protocol', 'request_id', 'kind', 'project_id', 'container_id', 'resource_id', 'search', 'cursor'];
const baseRowKeys = ['kind', 'project_id', 'resource_id', 'container_id', 'resource_revision', 'work_revision', 'execution_contract_protocol',
  'execution_contract_revision', 'execution_contract_digest', 'discussion_sequence', 'title', 'type', 'status', 'priority',
  'owner_principal_id', 'worker_principal_id', 'owner_display_name', 'worker_display_name'];
const detailKeys = ['description', 'acceptance_criteria', 'required_outcomes', 'blocked_reason', 'completion_basis', 'completion_principal_id',
  'completion_request_id', 'completion_note', 'legacy_assignment_pending', 'legacy_assignee_principal_id', 'legacy_assignee_display_name',
  'legacy_blocked_pending', 'legacy_blocked_status', 'legacy_prior_status'];
function requireValue(condition: unknown): asserts condition { if (!condition) throw new ProductProtocolError(); }
function text(row: Record<string, unknown>, name: string): string { const value = row[name]; protocolText(value); return value; }
function decimal(value: unknown, positive = false): asserts value is string {
  protocolText(value); requireValue(/^(?:0|[1-9][0-9]{0,19})$/u.test(value) && BigInt(value) <= 18446744073709551615n && (!positive || value !== '0'));
}
function uuid(value: unknown, empty = false) { protocolText(value); requireValue((empty && value === '') || UUID.test(value)); }
function hash(value: unknown, empty = false) { protocolText(value); requireValue((empty && value === '') || HASH.test(value)); }
function title(value: unknown) { protocolText(value); requireValue(byteLength(value) >= 1 && byteLength(value) <= 800 && [...value].length <= 200 && !/[\u0000-\u001f]/u.test(value)); }
function prose(value: unknown, bound = 8192) { protocolText(value); requireValue(byteLength(value) <= bound && !value.includes('\r')); }
function body(value: unknown) {
  protocolText(value); const bytes = new TextEncoder().encode(value);
  requireValue(bytes.length <= 2048 && bytes.every(byte => byte === 9 || byte === 10 || byte >= 32) && bytes.some(byte => byte > 32));
}
function branch(value: string) {
  requireValue(byteLength(value) <= 128 && value.startsWith('refs/heads/') && !/[\u0000-\u0020\u007f~^:?*\[\\]/u.test(value)
    && !value.includes('..') && !value.includes('@{') && !value.endsWith('.')
    && value.split('/').every(part => !!part && !part.startsWith('.') && !part.endsWith('.lock')));
}
function outcomes(value: unknown, project: string, work: string, profile = false): asserts value is ProductOutcomes {
  const entries = object(value); requireValue(Object.keys(entries).length <= 16);
  const identities = new Set<string>();
  for (const [id, target] of Object.entries(entries)) {
    uuid(id); const row = object(target); const kind = text(row, 'kind'); requireValue(row.project_id === project);
    if (kind === 'document') {
      keys(row, ['kind', 'project_id', 'collection_id', 'document_id', 'expected_revision', 'base_markdown_sha256']);
      uuid(row.collection_id); uuid(row.document_id); decimal(row.expected_revision);
      if (row.expected_revision === '0') requireValue(row.base_markdown_sha256 === ''); else hash(row.base_markdown_sha256);
    } else if (kind === 'code') {
      keys(row, ['kind', 'project_id', 'repository_id', 'target_ref', 'base_oid']); uuid(row.repository_id);
      branch(text(row, 'target_ref')); requireValue(/^[a-f0-9]{40}$/u.test(text(row, 'base_oid')));
    } else if (kind === 'completion-note') {
      keys(row, ['kind', 'project_id', 'work_id', 'expected_revision']); requireValue(row.work_id === work); decimal(row.expected_revision);
    } else throw new ProductProtocolError();
    const identity = JSON.stringify(kind === 'document' ? [kind, project, row.collection_id, row.document_id]
      : kind === 'code' ? [kind, project, row.repository_id, row.target_ref] : [kind, project, row.work_id]);
    requireValue(!identities.has(identity)); identities.add(identity);
    if (profile && kind !== 'document') throw new ProductProtocolError('unsupported_profile');
  }
}
function contract(row: Record<string, unknown>, project: string, work: string) {
  title(row.title); prose(row.description); prose(row.acceptance_criteria); outcomes(row.required_outcomes, project, work);
}
function properties(row: Record<string, unknown>, allowDone: boolean) {
  requireValue(['deliverable', 'task', 'problem'].includes(text(row, 'type')));
  requireValue(statuses.includes(text(row, 'status')) && (allowDone || row.status !== 'done'));
  requireValue(['none', 'low', 'medium', 'high', 'urgent'].includes(text(row, 'priority')));
  uuid(row.owner_principal_id, true); uuid(row.worker_principal_id, true);
  if (row.blocked_reason !== '') { requireValue(row.status !== 'done' && row.status !== 'canceled'); body(row.blocked_reason); }
}
function expected(row: Record<string, unknown>, names: string[], creation = false) {
  keys(row, names);
  for (const name of names) { decimal(row[name], !creation && name !== 'discussion_sequence'); if (creation) requireValue(row[name] === '0'); }
}
function commandValue(row: Record<string, unknown>): ProductCommand {
  keys(row, commandKeys); requireValue(row.protocol === 'stead.command/4');
  uuid(row.request_id); uuid(row.project_id); uuid(row.resource_id); decimal(row.authority_epoch, true);
  const project = text(row, 'project_id'), work = text(row, 'resource_id'), operation = text(row, 'operation');
  const exp = object(row.expected), payload = object(row.payload);
  switch (operation) {
    case 'work.create': expected(exp, ['work_revision', 'execution_contract_revision'], true); keys(payload, [...propertyKeys, ...contractKeys]); properties(payload, false); contract(payload, project, work); break;
    case 'work.update-properties': expected(exp, ['work_revision']); keys(payload, propertyKeys); properties(payload, true); break;
    case 'work.update-contract': expected(exp, ['execution_contract_revision']); keys(payload, contractKeys); contract(payload, project, work); break;
    case 'work.resolve-legacy-blocked':
      expected(exp, ['work_revision']); keys(payload, ['status', 'blocked_reason']); requireValue(statuses.slice(0, 4).includes(text(payload, 'status')));
      if (payload.blocked_reason !== '') body(payload.blocked_reason); break;
    case 'work.resolve-legacy-assignee': expected(exp, ['work_revision']); keys(payload, ['owner_principal_id', 'worker_principal_id']); uuid(payload.owner_principal_id, true); uuid(payload.worker_principal_id, true); break;
    case 'work.comment': expected(exp, ['discussion_sequence']); keys(payload, ['body']); body(payload.body); break;
    case 'work.complete':
      expected(exp, ['work_revision', 'execution_contract_revision']); keys(payload, ['basis', 'note']);
      if (payload.basis === 'human-note') body(payload.note); else requireValue(payload.basis === 'accepted-outcomes' && payload.note === ''); break;
    case 'work.delete': expected(exp, ['work_revision', 'execution_contract_revision', 'discussion_sequence']); keys(payload, []); break;
    default: throw new ProductProtocolError();
  }
  return freeze(row as unknown as ProductCommand);
}
export function parseProductCommand(raw: string): ProductCommand { return commandValue(parseProductJSON(raw)); }
export function encodeProductCommand(value: unknown): string { const raw = productJSON(value); return productJSON(parseProductCommand(raw)); }
export async function productCommandDigest(command: ProductCommand): Promise<string> {
  const bytes = new TextEncoder().encode('stead.command/4\0' + encodeProductCommand(command));
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(byte => byte.toString(16).padStart(2, '0')).join('');
}
export function parseProductQuery(raw: string): ProductQuery {
  const row = parseProductJSON(raw, {bytes: 65536, depth: 2, keys: 16}); keys(row, queryKeys);
  requireValue(row.protocol === 'stead.query/4' && row.container_id === '' && row.search === '');
  uuid(row.request_id); uuid(row.project_id); hash(row.cursor, true);
  requireValue(['work', 'comments', 'principals', 'completion'].includes(text(row, 'kind')));
  if (row.kind === 'principals') requireValue(row.resource_id === '');
  else uuid(row.resource_id, row.kind === 'work');
  if (row.kind === 'completion') requireValue(row.cursor === '');
  return freeze(row as unknown as ProductQuery);
}
export function encodeProductQuery(value: unknown): string { return productJSON(parseProductQuery(productJSON(value))); }
export function productDetailOutcomes(row: ProductWorkDetail): ProductOutcomes {
  const parsed = parseProductJSON(row.required_outcomes, {bytes: 65536, depth: 2, keys: 16});
  requireValue(productJSON(parsed) === row.required_outcomes); outcomes(parsed, row.project_id, row.resource_id, true);
  return freeze(parsed);
}
function workRow(value: unknown, query: ProductQuery): ProductWorkPreview | ProductWorkDetail {
  const row = object(value), full = query.resource_id !== ''; keys(row, [...baseRowKeys, ...(full ? detailKeys : ['snippet'])]);
  for (const value of Object.values(row)) protocolText(value);
  requireValue(row.kind === 'work' && row.project_id === query.project_id && row.container_id === ''); uuid(row.resource_id);
  if (full) requireValue(row.resource_id === query.resource_id);
  for (const name of ['resource_revision', 'work_revision', 'execution_contract_revision']) decimal(row[name], true);
  decimal(row.discussion_sequence); requireValue(BigInt(row.discussion_sequence as string) <= 32n);
  requireValue(row.execution_contract_protocol === 'stead.work-contract/2'); hash(row.execution_contract_digest);
  title(row.title); requireValue(['deliverable', 'task', 'problem'].includes(text(row, 'type')));
  requireValue([...statuses, 'legacy-blocked'].includes(text(row, 'status')));
  requireValue(['none', 'low', 'medium', 'high', 'urgent'].includes(text(row, 'priority')));
  uuid(row.owner_principal_id, true); uuid(row.worker_principal_id, true);
  if (row.owner_principal_id === '') requireValue(row.owner_display_name === '');
  if (row.worker_principal_id === '') requireValue(row.worker_display_name === '');
  if (!full) { prose(row.snippet, 640); requireValue([...(row.snippet as string)].length <= 160); }
  else {
    prose(row.description); prose(row.acceptance_criteria);
    if (row.blocked_reason !== '') body(row.blocked_reason);
    requireValue(['', 'legacy', 'human-note', 'accepted-outcomes'].includes(text(row, 'completion_basis')));
    const completed = row.completion_basis === 'human-note' || row.completion_basis === 'accepted-outcomes';
    uuid(row.completion_principal_id, !completed); uuid(row.completion_request_id, !completed);
    if (!completed) requireValue(row.completion_principal_id === '' && row.completion_request_id === '');
    if (row.completion_basis === 'human-note') body(row.completion_note); else requireValue(row.completion_note === '');
    requireValue(['yes', 'no'].includes(text(row, 'legacy_assignment_pending')) && ['yes', 'no'].includes(text(row, 'legacy_blocked_pending')));
    uuid(row.legacy_assignee_principal_id, row.legacy_assignment_pending === 'no');
    if (row.legacy_assignee_principal_id === '') requireValue(row.legacy_assignee_display_name === '');
    requireValue(['', 'blocked'].includes(text(row, 'legacy_blocked_status')));
    if (row.legacy_blocked_pending === 'yes') requireValue(row.legacy_blocked_status === 'blocked');
    requireValue(['', 'backlog', 'todo', 'in_progress'].includes(text(row, 'legacy_prior_status')));
    if (row.status === 'legacy-blocked') requireValue(row.legacy_blocked_pending === 'yes');
    productDetailOutcomes(row as unknown as ProductWorkDetail);
  }
  return row as unknown as ProductWorkPreview | ProductWorkDetail;
}
function commentRow(value: unknown, query: ProductQuery): ProductComment {
  const row = object(value); keys(row, ['kind', 'project_id', 'work_id', 'sequence', 'body', 'principal_id', 'display_name', 'identity_ship', 'request_id', 'accepted_at_ms', 'legacy_comment_revision']);
  for (const value of Object.values(row)) protocolText(value);
  requireValue(row.kind === 'comment' && row.project_id === query.project_id && row.work_id === query.resource_id);
  decimal(row.sequence, true); requireValue(BigInt(row.sequence as string) <= 32n); body(row.body);
  uuid(row.principal_id); uuid(row.request_id); decimal(row.accepted_at_ms);
  if (row.legacy_comment_revision !== '') decimal(row.legacy_comment_revision, true);
  requireValue(/^~[a-z]+(?:-{1,2}[a-z]+)*$/u.test(text(row, 'identity_ship')) && byteLength(row.identity_ship as string) <= 65);
  return row as unknown as ProductComment;
}
function principalRow(value: unknown): ProductPrincipal {
  const row = object(value); keys(row, ['kind', 'principal_id', 'display_name', 'principal_kind', 'active', 'project_role']);
  for (const value of Object.values(row)) protocolText(value);
  requireValue(row.kind === 'principal'); uuid(row.principal_id);
  if (row.display_name !== '') title(row.display_name);
  requireValue(['person', 'agent', 'service', 'unresolved'].includes(text(row, 'principal_kind'))
    && ['yes', 'no'].includes(text(row, 'active')) && ['reader', 'contributor', 'maintainer'].includes(text(row, 'project_role')));
  return row as unknown as ProductPrincipal;
}
function completionRow(value: unknown, query: ProductQuery): ProductCompletion {
  const row = object(value); keys(row, ['kind', 'project_id', 'work_id', 'execution_contract_revision', 'execution_contract_digest', 'ready', 'reason']);
  for (const value of Object.values(row)) protocolText(value);
  requireValue(row.kind === 'completion' && row.project_id === query.project_id && row.work_id === query.resource_id);
  decimal(row.execution_contract_revision, true); hash(row.execution_contract_digest);
  requireValue(row.ready === 'yes' ? row.reason === '' : row.ready === 'no'
    && ['human-note-required', 'required-outcomes-unconfirmed'].includes(text(row, 'reason')));
  return row as unknown as ProductCompletion;
}
function response<T>(operation: () => T): T {
  try { return operation(); }
  catch (failure) { if (failure instanceof ProductProtocolError && failure.code === 'unsupported_profile') throw failure; throw new ProductProtocolError('invalid_response'); }
}
export function parseProductView(raw: string, request: ProductQuery): ProductView | ProductQueryRejection {
  return response(() => {
    const query = parseProductQuery(encodeProductQuery(request));
    const row = parseProductJSON(raw, {bytes: 262144, depth: 3, keys: 32});
    requireValue(row.protocol === 'stead.query-result/4' && row.request_id === query.request_id);
    if (row.status === 'rejected') { keys(row, ['protocol', 'status', 'request_id', 'error']); requireValue(/^[a-z_]{1,64}$/u.test(text(row, 'error'))); return freeze(row as unknown as ProductQueryRejection); }
    keys(row, ['protocol', 'status', 'request_id', 'kind', 'project_id', 'container_id', 'resource_id', 'authority_epoch', 'generation', 'cursor', 'rows']);
    requireValue(row.status === 'read' && row.kind === query.kind && row.project_id === query.project_id && row.container_id === '' && row.resource_id === query.resource_id);
    decimal(row.authority_epoch, true); hash(row.generation); hash(row.cursor, true);
    const indexed = object(row.rows), count = Object.keys(indexed).length; requireValue(count <= 20);
    requireValue(Object.keys(indexed).every(key => /^(?:0|[1-9][0-9]?)$/u.test(key) && Number(key) < count));
    const rows = Array.from({length: count}, (_, index) => query.kind === 'work' ? workRow(indexed[String(index)], query)
      : query.kind === 'comments' ? commentRow(indexed[String(index)], query)
      : query.kind === 'principals' ? principalRow(indexed[String(index)]) : completionRow(indexed[String(index)], query));
    if (query.kind === 'work') {
      const ids = rows.map(value => (value as ProductWorkBase).resource_id); requireValue(new Set(ids).size === ids.length);
      if (query.resource_id) requireValue(count === 1 && row.cursor === '');
    } else if (query.kind === 'comments') {
      const comments = rows as ProductComment[];
      for (let index = 1; index < comments.length; index++) requireValue(BigInt(comments[index]!.sequence) === BigInt(comments[index - 1]!.sequence) + 1n);
      if (!query.cursor && comments.length) requireValue(comments[0]!.sequence === '1');
    } else if (query.kind === 'principals') {
      const ids = rows.map(value => (value as ProductPrincipal).principal_id); requireValue(new Set(ids).size === ids.length);
    } else {
      requireValue(count === 1 && row.cursor === '');
    }
    if (row.cursor !== '') requireValue(count === 20);
    return freeze({...row, rows} as unknown as ProductView);
  });
}
export function parseProductReceipt(raw: string, request: ProductCommand, digest: string): ProductReceipt {
  return response(() => {
    const command = parseProductCommand(encodeProductCommand(request)); hash(digest);
    const row = parseProductJSON(raw, {bytes: 8192, depth: 2, keys: 16});
    requireValue(row.protocol === 'stead.receipt/4' && row.request_id === command.request_id && row.canonical_sha256 === digest);
    requireValue(row.status === 'accepted' || row.status === 'rejected');
    if (row.status === 'rejected' && Object.keys(row).length === 5) {
      keys(row, ['protocol', 'status', 'request_id', 'canonical_sha256', 'error']); requireValue(/^[a-z_]{1,64}$/u.test(text(row, 'error')));
      return freeze(row as unknown as ProductReceipt);
    }
    keys(row, ['protocol', 'status', 'request_id', 'canonical_sha256', 'project_id', 'resource_id', 'authority_epoch', 'operation', 'principal_id', 'recorded_at_ms', 'error', 'expected', 'resulting']);
    for (const key of ['project_id', 'resource_id', 'authority_epoch', 'operation'] as const) requireValue(row[key] === command[key]);
    uuid(row.principal_id); decimal(row.recorded_at_ms);
    requireValue(productJSON(row.expected) === productJSON(command.expected));
    requireValue(row.status === 'accepted' ? row.error === '' : /^[a-z_]{1,64}$/u.test(text(row, 'error')));
    const resulting = object(row.resulting); keys(resulting, ['work_revision', 'execution_contract_revision', 'discussion_sequence', 'execution_contract_digest']);
    decimal(resulting.work_revision, row.status === 'accepted'); decimal(resulting.execution_contract_revision, row.status === 'accepted'); decimal(resulting.discussion_sequence);
    requireValue(BigInt(resulting.discussion_sequence as string) <= 32n);
    hash(resulting.execution_contract_digest, resulting.execution_contract_revision === '0');
    if (resulting.execution_contract_revision === '0') requireValue(resulting.execution_contract_digest === '' && resulting.work_revision === '0' && resulting.discussion_sequence === '0');
    return freeze(row as unknown as ProductReceipt);
  });
}

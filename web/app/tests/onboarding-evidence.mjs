// Passive evidence validation for a human journey. Never submits app requests.
import {createHash} from 'node:crypto';
const keys = ['protocol','status','request_id','canonical_sha256','project_id','resource_id','resource_kind',
  'container_id','resource_revision','authority_epoch','operation','principal_id','binding_id','binding_revision',
  'identity_ship','authentication','authentication_strength','session_audit_id','runtime','accepted_at_ms','git_commit_oid'];
const uuid = /^019939ba-4000-7000-8000-[0-9a-f]{12}$/u;
const uint = /^(0|[1-9][0-9]{0,19})$/u;
export function sha(bytes) { return createHash('sha256').update(bytes).digest('hex'); }
export function scope(project, kind, container, resource) {
  return canonical({project, kind, container, resource});
}
export function workBody(value) {
  const names = ['title','description','type','status','priority'];
  if (names.some(name => typeof value[name] !== 'string')) throw new Error('work_body_shape');
  return sha(canonical(Object.fromEntries(names.map(name => [name, value[name]]))));
}
export function canonical(value, depth = 0) {
  if (depth > 5) throw new Error('evidence_depth');
  if (typeof value === 'string') return JSON.stringify(value);
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length > 32) throw new Error('evidence_shape');
  return '{' + Object.keys(value).sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)))
    .map(key => JSON.stringify(key) + ':' + canonical(value[key], depth + 1)).join(',') + '}';
}
export function acceptedReceipt(command, row, person) {
  if (!person || !row || typeof row !== 'object' || Array.isArray(row)
      || Object.keys(row).length !== keys.length || keys.some(key => typeof row[key] !== 'string')) throw new Error('receipt_shape');
  const resourceKind = command.operation.split('.')[0];
  const digest = sha(Buffer.concat([Buffer.from('stead.command/3\0'), Buffer.from(canonical(command))]));
  if (command.protocol !== 'stead.command/3' || row.protocol !== 'stead.receipt/3' || row.status !== 'accepted'
      || row.canonical_sha256 !== digest || row.resource_kind !== resourceKind || row.runtime !== 'isolated-fake'
      || ['request_id','project_id','resource_id','operation','authority_epoch'].some(key => row[key] !== command[key])
      || !uint.test(command.expected_revision) || BigInt(command.expected_revision) >= 2n ** 64n - 1n
      || row.resource_revision !== String(BigInt(command.expected_revision) + 1n)
      || row.container_id !== (command.operation === 'container.create' ? command.resource_id : command.payload.container_id ?? '')
      || ['principal_id','binding_id','binding_revision','identity_ship','session_audit_id'].some(key => row[key] !== person[key])
      || row.authentication !== 'native-approved-browser/1' || row.authentication_strength !== 'native-approved-browser'
      || !uint.test(row.accepted_at_ms) || BigInt(row.accepted_at_ms) === 0n || BigInt(row.accepted_at_ms) > 2n ** 64n - 1n
      || (resourceKind === 'document' ? !/^[0-9a-f]{40}$/u.test(row.git_commit_oid) : row.git_commit_oid !== '')) throw new Error('receipt_correlation');
  return Object.fromEntries(['request_id','project_id','resource_id','container_id','operation',
    'resource_revision','canonical_sha256','git_commit_oid','accepted_at_ms'].map(key => [key, row[key]]));
}
export function personalIdentity(query, value) {
  if (query.protocol !== 'stead.query/3' || query.kind !== 'identity' || value.protocol !== 'stead.query-result/3'
      || value.status !== 'read' || value.request_id !== query.request_id || value.kind !== 'identity'
      || !value.rows || Object.keys(value.rows).length !== 1) throw new Error('identity_correlation');
  const person = Object.values(value.rows)[0];
  if (person.identity_ship !== '~bus' || person.principal_id !== '019939ba-4000-7000-8000-000000000066'
      || person.binding_id !== '019939ba-4000-7000-8000-0000000000ca' || person.binding_revision !== '1'
      || !uuid.test(person.principal_id) || !/^[0-9a-f]{64}$/u.test(person.session_audit_id)) throw new Error('identity_actor');
  return person;
}

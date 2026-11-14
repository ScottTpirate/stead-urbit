import { HomeError, MAX_EXTERNAL_CODE, UUID, type ExternalMerge, type Fields } from './api';
import { canonical } from './protocol';

export const MAX_ARTIFACT_BYTES = MAX_EXTERNAL_CODE;
const PROOF = 'stead.git-pack-reviewed-proof/1';
const SIGNATURE = /^[a-f0-9]{128}$/u;
const DIGEST = /^[a-f0-9]{64}$/u;
const UINT = /^[1-9][0-9]{0,19}$/u;
const MAX_UINT = 2n ** 64n - 1n;
const BRANCH = '726566732f68656164732f';

export function refLabel(hex: string) {
  return refText(hex) ?? `Raw ref bytes ${hex}`;
}

function refText(hex: string): string | null {
  const bytes = Uint8Array.from(hex.match(/../gu) ?? [], pair => Number.parseInt(pair, 16));
  try { return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { return null; }
}

function refHex(ref: string): string {
  return Array.from(new TextEncoder().encode(ref), byte => byte.toString(16).padStart(2, '0')).join('');
}

export function reviewBranches(refs: Fields, target: string) {
  return Object.entries(refs).flatMap(([key, oid]) => {
    if (!key.startsWith(BRANCH) || key === target || oid === refs[target]) return [];
    const name = refText(key);
    return name === null ? [] : [{ key, name, oid }];
  });
}

export function reviewRequest(review: Fields, request_id: string): Fields {
  return { protocol: 'stead.git-pack-review-request/1', request_id, proposal_id: review.proposal_id!,
    revision: review.revision!, work_id: review.work_id!, source_ref: review.source_ref!, ref: review.ref!,
    base_oid: review.base_oid!, head_oid: review.head_oid!, base_snapshot: review.base_snapshot!, generation: review.generation! };
}

function object(input: unknown, keys: string[]): Record<string, unknown> {
  if (!input || typeof input !== 'object' || Array.isArray(input)
    || Object.keys(input).length !== keys.length || keys.some(key => !Object.hasOwn(input, key))) {
    throw new HomeError('invalid_review_artifact');
  }
  return input as Record<string, unknown>;
}

export function parseReviewArtifact(raw: string, project: string, snapshot: Fields, review: Fields): ExternalMerge {
  try {
    const bytes = new TextEncoder();
    if (bytes.encode(raw).byteLength > MAX_ARTIFACT_BYTES) throw new HomeError('invalid_review_artifact');
    const { proof, worker_generation, worker_signature } = object(JSON.parse(raw), ['proof', 'worker_generation', 'worker_signature']);
    if (typeof proof !== 'string' || !proof.endsWith('\n') || typeof worker_signature !== 'string' || !SIGNATURE.test(worker_signature)
      || typeof worker_generation !== 'string' || !UINT.test(worker_generation) || BigInt(worker_generation) > MAX_UINT) {
      throw new HomeError('invalid_review_artifact');
    }
    const row = object(JSON.parse(proof), ['protocol', 'scope', 'base_snapshot', 'generation', 'proposal_id', 'revision',
      'work_id', 'source', 'target', 'base_oid', 'head_oid', 'request_id', 'candidate_snapshot']);
    if (canonical(row) + '\n' !== proof) throw new HomeError('invalid_review_artifact');
    const scope = object(row.scope, ['home', 'authority_epoch', 'project_id', 'repository_id']);
    const value = typeof scope.home === 'string' && /^~[a-z][a-z-]{2,62}$/u.test(scope.home)
      && scope.authority_epoch === snapshot.authority_epoch && scope.project_id === project && scope.repository_id === project
      && row.protocol === PROOF && row.base_snapshot === review.base_snapshot && row.base_snapshot === snapshot.snapshot
      && row.generation === review.generation && row.generation === snapshot.generation
      && row.proposal_id === review.proposal_id && row.revision === review.revision
      && row.work_id === review.work_id && row.source === refHex(review.source_ref ?? '') && row.target === snapshot.head
      && row.target === refHex(review.ref ?? '') && row.base_oid === review.base_oid && row.head_oid === review.head_oid
      && typeof row.request_id === 'string' && UUID.test(row.request_id) && typeof row.candidate_snapshot === 'string'
      && DIGEST.test(row.candidate_snapshot) && row.candidate_snapshot !== row.base_snapshot;
    if (!value) throw new HomeError('invalid_review_artifact');
    const request: ExternalMerge = { action: 'external-merge', proposal_id: review.proposal_id!, revision: review.revision!,
      request_id: row.request_id as string, worker_generation, worker_signature, proof };
    if (bytes.encode(JSON.stringify({ protocol: 'stead.code/1', project_id: project, ...request })).byteLength > MAX_ARTIFACT_BYTES) {
      throw new HomeError('invalid_review_artifact');
    }
    return request;
  } catch { throw new HomeError('invalid_review_artifact'); }
}

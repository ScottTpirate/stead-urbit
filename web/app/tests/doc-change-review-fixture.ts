// Deliberately synthetic adapter data. No native authority or acceptance proof.
import {docChangeCommandDigest, encodeDocChangeCommand, parseDocChangeCommand, type DocChangeCommand} from '../src/docChangeProtocol';
import {docDecisionActions, docReviewPin, type DocActionEligibility, type DocDecisionSubmitter, type DocReviewBody, type DocReviewEnvironment, type DocReviewSnapshot} from '../src/docChangeReviewState';
export const id = (n: number) => '019939ba-4000-7000-8000-' + String(n).padStart(12, '0');
export const beforeText = '# Guide\n\nOriginal text.\n';
export const afterText = '# Guide\n\nClearer text.  \n';
export async function hash(text: string) { return [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))].map(n => n.toString(16).padStart(2, '0')).join(''); }
export async function fixture() {
  const scope = {projectId: id(100), workId: id(101), changeId: id(400)}, sessionKey = 'synthetic-session-one';
  const snapshot: DocReviewSnapshot = {scope, sessionKey, authorityEpoch: '1', generation: 'a'.repeat(64),
    head: {revision: '3', status: 'submitted', resultRevision: '2', resultDigest: 'b'.repeat(64)},
    output: {revision: '2', digest: 'b'.repeat(64), outcomeId: id(401), targetLabel: 'Shared guide',
      target: {kind: 'document', project_id: id(100), collection_id: id(200), document_id: id(201), expected_revision: '1', base_markdown_sha256: await hash(beforeText)},
      executionContractRevision: '4', executionContractDigest: 'c'.repeat(64), markdownSha256: await hash(afterText), summary: 'Clarify the guide.',
      producer: {principalId: id(103), displayName: 'Writer agent'}, runId: id(500), attempt: '1', submittedAtMs: '1794770000000'}};
  const body = (side: 'before' | 'after', markdown: string, sha256: string): DocReviewBody => ({scope, sessionKey,
    resultRevision: '2', resultDigest: snapshot.output.digest, side, state: 'ready', markdown, sha256});
  return {snapshot, before: body('before', beforeText, snapshot.output.target.base_markdown_sha256), after: body('after', afterText, snapshot.output.markdownSha256)};
}
export function eligibility(snapshot: DocReviewSnapshot): DocActionEligibility {
  return {scope: snapshot.scope, sessionKey: snapshot.sessionKey, pin: docReviewPin(snapshot), actions: Object.fromEntries(docDecisionActions.map(operation => [operation, {state: 'eligible', reason: 'none'}])) as DocActionEligibility['actions']};
}
export async function prepare(command: DocChangeCommand) {
  const bytes = encodeDocChangeCommand(command), parsed = parseDocChangeCommand(bytes);
  Object.freeze(parsed.payload); Object.freeze(parsed);
  return Object.freeze({command: parsed, bytes, digest: await docChangeCommandDigest(parsed)});
}
export function environment(snapshot: DocReviewSnapshot): DocReviewEnvironment {
  const submitter: DocDecisionSubmitter = {currentSessionToken: () => 'synthetic-token', prepare, submit: async () => { throw new Error('No fixture transport supplied'); }};
  return {scope: snapshot.scope, sessionKey: snapshot.sessionKey, supported: true, access: 'writable', online: true, authorizedReadToken: {},
    submitter, eligibility: eligibility(snapshot), onDraftState: () => {}, onRefresh: () => {}, onAccessChanged: () => {}, onAccepted: () => {}};
}

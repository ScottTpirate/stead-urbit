// Host state/body tests only. Injected eligibility is not native authorization.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {encodeDocChangeCommand} from '../src/docChangeProtocol';
import {adoptDocDecision, advanceDocReviewGeneration, boundedDocDiff, chooseDocDecision, currentDocOutput, docActionEligible, docDecisionActions,
  docDecisionCommand, docReviewHasDraft, docReviewPin, makeDocReviewDraft, reconcileDocReviewDraft, restoreDocReviewDraft, sameDocReviewPin, verifyDocReviewBody} from '../src/docChangeReviewState';
import {afterText, beforeText, environment, fixture, hash, id, prepare} from './doc-change-review-fixture';

test('decision eligibility requires every current scope session output epoch and generation binding', async () => {
  const {snapshot} = await fixture(), env = environment(snapshot);
  for (const operation of docDecisionActions) assert.equal(docActionEligible(env, snapshot, operation), true);
  for (const altered of [{...env, eligibility: undefined}, {...env, supported: false}, {...env, online: false}, {...env, refreshing: true},
    {...env, access: 'read-only' as const}, {...env, access: 'revoked' as const}, {...env, sessionKey: 'other'}, {...env, scope: {...env.scope, workId: id(999)}}]) {
    assert.equal(docActionEligible(altered, snapshot, 'change.accept'), false);
  }
  for (const pin of [{...docReviewPin(snapshot), authorityEpoch: '2'}, {...docReviewPin(snapshot), generation: 'd'.repeat(64)}, {...docReviewPin(snapshot), headRevision: '4'},
    {...docReviewPin(snapshot), resultRevision: '1'}, {...docReviewPin(snapshot), resultDigest: 'f'.repeat(64)}]) {
    assert.equal(docActionEligible({...env, eligibility: {...env.eligibility!, pin}}, snapshot, 'change.approve'), false);
  }
  assert.equal(docActionEligible({...env, eligibility: {...env.eligibility!, scope: {...snapshot.scope, projectId: id(999)}}}, snapshot, 'change.accept'), false);
  assert.equal(docActionEligible({...env, eligibility: {...env.eligibility!, sessionKey: 'other'}}, snapshot, 'change.accept'), false);
  for (const state of ['blocked', 'unsupported'] as const) assert.equal(docActionEligible({...env, eligibility: {...env.eligibility!, actions: {...env.eligibility!.actions,
    'change.accept': {state, reason: 'independent_review_required'}}}}, snapshot, 'change.accept'), false);
  const prior = {...snapshot, output: {...snapshot.output, revision: '1'}}; assert.equal(currentDocOutput(prior), false);
  assert.equal(docActionEligible(env, prior, 'change.accept'), false);
});
test('decision notes retain independent exact pins until explicit current-output adoption', async () => {
  const {snapshot} = await fixture(); let draft = chooseDocDecision(makeDocReviewDraft(snapshot.scope, snapshot.sessionKey), 'change.request-changes', snapshot);
  draft.decisions['change.request-changes']!.note = 'Keep this exact note  \n';
  draft = chooseDocDecision(draft, 'change.approve', snapshot); draft.decisions['change.approve']!.note = 'Independent note';
  const newer = {...snapshot, authorityEpoch: '2', generation: 'd'.repeat(64), head: {...snapshot.head, revision: '4'}};
  draft = chooseDocDecision(draft, 'change.request-changes', newer);
  assert.equal(draft.decisions['change.request-changes']!.base.authorityEpoch, '1');
  const adopted = adoptDocDecision(draft, 'change.request-changes', newer);
  assert.equal(adopted.decisions['change.request-changes']!.note, 'Keep this exact note  \n');
  assert.deepEqual(adopted.decisions['change.request-changes']!.base, docReviewPin(newer));
  assert.equal(adopted.decisions['change.approve'], draft.decisions['change.approve']);
  assert.equal(adoptDocDecision(draft, 'change.request-changes', {...newer, output: {...newer.output, revision: '1'}}), draft);
  assert.equal(adoptDocDecision(draft, 'change.request-changes', {...newer, sessionKey: 'other'}), draft);
});
test('unresolved requests survive remount exactly and cannot be adopted or restored into another session', async () => {
  const {snapshot} = await fixture(); let draft = chooseDocDecision(makeDocReviewDraft(snapshot.scope, snapshot.sessionKey), 'change.approve', snapshot);
  const prepared = await prepare(docDecisionCommand(draft, 'change.approve', id(600))), token = {};
  draft = {...draft, attempt: {operation: 'change.approve', phase: 'saving', token, prepared, bytes: prepared.bytes, digest: prepared.digest, message: ''}};
  const restored = restoreDocReviewDraft(snapshot.scope, snapshot.sessionKey, draft);
  assert.equal(restored.attempt!.phase, 'unknown'); assert.equal(restored.attempt!.prepared, prepared); assert.equal(restored.attempt!.token, token);
  assert.equal(restored.attempt!.bytes, prepared.bytes); assert.equal(docReviewHasDraft(restored), true);
  assert.equal(adoptDocDecision(restored, 'change.approve', {...snapshot, authorityEpoch: '2'}), restored);
  assert.equal(restoreDocReviewDraft(snapshot.scope, 'other', draft).attempt, undefined);
  assert.equal(restoreDocReviewDraft({...snapshot.scope, changeId: id(999)}, snapshot.sessionKey, draft).attempt, undefined);
  assert.equal(restoreDocReviewDraft(snapshot.scope, snapshot.sessionKey, {...draft, attempt: {...draft.attempt!, phase: 'preparing'}}).attempt, undefined);
});
test('accepted readback clears only the submitted note after matching current lifecycle advances', async () => {
  const {snapshot} = await fixture(); let draft = chooseDocDecision(makeDocReviewDraft(snapshot.scope, snapshot.sessionKey), 'change.request-changes', snapshot);
  draft.decisions['change.request-changes']!.note = 'Revise this'; draft = chooseDocDecision(draft, 'change.approve', snapshot);
  draft.decisions['change.approve']!.note = 'Retain independently';
  draft.attempt = {operation: 'change.request-changes', phase: 'accepted', token: 'token', message: '', awaitingReadback: true, outcome: {status: 'accepted', resultingRevision: '4'}};
  assert.equal(reconcileDocReviewDraft(draft, snapshot), draft);
  assert.equal(reconcileDocReviewDraft(draft, {...snapshot, sessionKey: 'other', head: {...snapshot.head, revision: '4'}}), draft);
  const reconciled = reconcileDocReviewDraft(draft, {...snapshot, head: {...snapshot.head, revision: '4', status: 'changes-requested'}});
  assert.equal(reconciled.decisions['change.request-changes'], undefined); assert.equal(reconciled.decisions['change.approve'], draft.decisions['change.approve']);
  assert.equal(reconciled.selected, 'change.approve'); assert.equal(reconciled.attempt!.awaitingReadback, false);
});
test('exact body verification checks independent SHA256 and rejects wrong content metadata or scope', async () => {
  const {snapshot, before, after} = await fixture();
  assert.equal(snapshot.output.markdownSha256, createHash('sha256').update(afterText).digest('hex'));
  assert.deepEqual(await verifyDocReviewBody(before, snapshot, 'before'), {state: 'ready', markdown: beforeText});
  assert.deepEqual(await verifyDocReviewBody(after, snapshot, 'after'), {state: 'ready', markdown: afterText});
  assert.deepEqual(await verifyDocReviewBody({...after, state: 'ready', markdown: 'Changed', sha256: snapshot.output.markdownSha256}, snapshot, 'after'), {state: 'unavailable'});
  assert.deepEqual(await verifyDocReviewBody({...after, state: 'ready', markdown: afterText, sha256: '0'.repeat(64)}, snapshot, 'after'), {state: 'unavailable'});
  for (const altered of [{...after, sessionKey: 'other'}, {...after, resultRevision: '1'}, {...after, resultDigest: '0'.repeat(64)}, {...after, scope: {...snapshot.scope, changeId: id(999)}}]) {
    assert.deepEqual(await verifyDocReviewBody(altered, snapshot, 'after'), {state: 'loading'});
  }
  assert.deepEqual(await verifyDocReviewBody(before, snapshot, 'after'), {state: 'loading'});
});
test('body byte bounds and exact text rules reject unsafe inputs without substituting latest content', async () => {
  const {snapshot, after, before} = await fixture();
  for (const markdown of ['é'.repeat(16385), 'bad\r\ntext', 'bad\0text', '\ud800']) {
    const sha256 = await hash(markdown), next = {...snapshot, output: {...snapshot.output, markdownSha256: sha256}};
    assert.deepEqual(await verifyDocReviewBody({...after, state: 'ready', markdown, sha256}, next, 'after'), {state: 'unavailable'});
  }
  const markdown = 'é'.repeat(16384), sha256 = await hash(markdown);
  assert.equal((await verifyDocReviewBody({...after, state: 'ready', markdown, sha256}, {...snapshot, output: {...snapshot.output, markdownSha256: sha256}}, 'after')).state, 'ready');
  assert.deepEqual(await verifyDocReviewBody({...before, state: 'unavailable', markdown: undefined, sha256: undefined}, snapshot, 'before'), {state: 'unavailable'});
  const newDoc = {...snapshot, output: {...snapshot.output, target: {...snapshot.output.target, expected_revision: '0', base_markdown_sha256: ''}}};
  assert.deepEqual(await verifyDocReviewBody({...before, state: 'new-document', markdown: undefined, sha256: undefined}, newDoc, 'before'), {state: 'new-document'});
  assert.deepEqual(await verifyDocReviewBody({...before, state: 'new-document', markdown: undefined, sha256: undefined}, snapshot, 'before'), {state: 'unavailable'});
});
test('bounded line comparison retains every source byte and explicitly refuses larger comparisons', () => {
  for (const [before, after] of [[beforeText, afterText], ['', 'New\n'], ['  λ\ntrailing  ', ' λ\ntrailing\n'], ['same\n', 'same\n']]) {
    const result = boundedDocDiff(before!, after!); assert.equal(result.state, 'ready'); if (result.state !== 'ready') throw new Error('Expected ready');
    assert.equal(result.lines.filter(line => line.kind !== 'added').map(line => line.text).join('\n'), before);
    assert.equal(result.lines.filter(line => line.kind !== 'removed').map(line => line.text).join('\n'), after);
    assert.equal(result.beforeFinalNewline, before!.endsWith('\n')); assert.equal(result.afterFinalNewline, after!.endsWith('\n'));
  }
  for (const [before, after] of [['x\n'.repeat(401), ''], ['x\n'.repeat(200), 'y\n'.repeat(200)], ['x'.repeat(32769), ''], ['\ud800', '']]) assert.equal(boundedDocDiff(before!, after!).state, 'unavailable');
});
test('view generation never reuses an earlier request generation across scope client session or read changes', async () => {
  const {snapshot} = await fixture(), env = environment(snapshot), read = {}, token = {};
  const a = advanceDocReviewGeneration(undefined, 'A', env.submitter, token, read);
  assert.equal(advanceDocReviewGeneration(a, 'A', env.submitter, token, read), a);
  const b = advanceDocReviewGeneration(a, 'B', env.submitter, token, read), returned = advanceDocReviewGeneration(b, 'A', env.submitter, token, read);
  assert.equal(returned.generation, 3); assert.notEqual(a.generation, returned.generation);
  const newClient = advanceDocReviewGeneration(returned, 'A', {...env.submitter}, token, read);
  const newSession = advanceDocReviewGeneration(newClient, 'A', newClient.submitter, {}, read);
  const freshRead = advanceDocReviewGeneration(newSession, 'A', newClient.submitter, newSession.token, {});
  assert.equal(freshRead.generation, 6);
});
test('decision commands retain original pins and exact notes with no caller-supplied authority claims', async () => {
  const {snapshot} = await fixture(); let draft = chooseDocDecision(makeDocReviewDraft(snapshot.scope, snapshot.sessionKey), 'change.request-changes', snapshot);
  draft.decisions['change.request-changes']!.note = 'Clarify λ  \n';
  const command = docDecisionCommand(draft, 'change.request-changes', id(601)); assert.equal(Object.keys(command).length, 9);
  assert.deepEqual(command.payload, {result_revision: '2', result_digest: snapshot.output.digest, note: 'Clarify λ  \n'});
  assert.equal(command.expected_revision, '3'); assert.equal(command.authority_epoch, '1');
  assert.equal((await prepare(command)).bytes, encodeDocChangeCommand(command));
  draft = chooseDocDecision(draft, 'change.request-changes', {...snapshot, head: {...snapshot.head, revision: '9'}});
  assert.equal(docDecisionCommand(draft, 'change.request-changes', id(602)).expected_revision, '3');
  draft.decisions['change.request-changes']!.note = ''; assert.throws(() => encodeDocChangeCommand(docDecisionCommand(draft, 'change.request-changes', id(603))));
  draft = chooseDocDecision(draft, 'change.approve', snapshot); assert.doesNotThrow(() => encodeDocChangeCommand(docDecisionCommand(draft, 'change.approve', id(604))));
});
test('access-denial fence persists across same-session remount and conflict adoption retains the previous request', async () => {
  const {snapshot} = await fixture(); let draft = chooseDocDecision(makeDocReviewDraft(snapshot.scope, snapshot.sessionKey), 'change.reject', snapshot);
  draft.decisions['change.reject']!.note = 'Keep rejected note'; const token = {};
  draft = {...draft, accessDeniedReadToken: token};
  assert.equal(restoreDocReviewDraft(snapshot.scope, snapshot.sessionKey, draft).accessDeniedReadToken, token);
  assert.equal(restoreDocReviewDraft(snapshot.scope, 'other', draft).accessDeniedReadToken, undefined);
  draft.attempt = {operation: 'change.reject', phase: 'conflict', token: 'session', message: 'Producer access changed', outcome: {status: 'rejected', reason: 'producer_quarantined'}};
  draft.decisions['change.reject']!.conflicted = true;
  const current = {...snapshot, generation: 'd'.repeat(64), head: {...snapshot.head, revision: '4', status: 'quarantined' as const}};
  const adopted = adoptDocDecision(draft, 'change.reject', current);
  assert.equal(adopted.previousAttempt, draft.attempt); assert.equal(adopted.decisions['change.reject']!.note, 'Keep rejected note');
  assert.equal(adopted.decisions['change.reject']!.conflicted, false); assert.equal(sameDocReviewPin(adopted.decisions['change.reject']!.base, docReviewPin(current)), true);
});

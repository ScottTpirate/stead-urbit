import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {parseUnifiedPatch, PATCH_DISPLAY_BYTES, PATCH_DISPLAY_LINES, PATCH_DISPLAY_HUNKS} from '../src/unifiedPatchParser';
import {UnifiedPatch} from '../src/UnifiedPatch';
import {ReviewChanges, ReviewReadFence, ReviewScopeFence} from '../src/ReviewChanges';
import type {HomeClient} from '../src/api';

const headers = 'diff --git a/guide.md b/guide.md\nindex 1111111..2222222 100644\n--- a/guide.md\n+++ b/guide.md\n';
const escaped = (s: string) => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;');
const parsed = (text: string) => {const value = parseUnifiedPatch(text); assert.equal(value.kind, 'parsed'); if (value.kind !== 'parsed') throw Error('Expected complete parsed patch'); return value;};
const client = {} as HomeClient;
const identity = () => ({client, project: 'project', snapshot: 'snapshot', proposal: 'proposal', revision: '1', base: 'base', head: 'head', token: {}, mode: 'legacy'});

test('Complete unified hunks use independent exact counters and retain original text and EOF markers', () => {
  const text = headers + '@@ -1,3 +1,4 @@ section\n first\n-old\n+new\n+extra\n last\n@@ -10 +11 @@\n-tail\n\\ No newline at end of file\n+new tail\n\\ No newline at end of file\n';
  const value = parsed(text); assert.equal(value.hunks.length, 2); assert.deepEqual(value.headers, headers.trimEnd().split('\n'));
  assert.deepEqual(value.hunks[0]!.lines.map(row => [row.kind, row.oldLine, row.newLine, row.text]), [
    ['context', 1, 1, 'first'], ['removed', 2, undefined, 'old'], ['added', undefined, 2, 'new'],
    ['added', undefined, 3, 'extra'], ['context', 3, 4, 'last']]);
  assert.deepEqual(value.hunks[1]!.lines.map(row => [row.kind, row.oldLine, row.newLine]), [
    ['removed', 10, undefined], ['note', undefined, undefined], ['added', undefined, 11], ['note', undefined, undefined]]);
  assert.equal(text, headers + value.hunks.map(hunk => hunk.header + '\n' + hunk.lines.map(row =>
    row.kind === 'note' ? row.text : (row.kind === 'context' ? ' ' : row.kind === 'added' ? '+' : '-') + row.text).join('\n') + '\n').join(''));
});
test('Added deleted and metadata-only files do not invent opposite-side lines or text hunks', () => {
  assert.deepEqual(parsed(headers + '@@ -0,0 +1 @@\n+new\n').hunks[0]!.lines, [{kind: 'added', text: 'new', newLine: 1}]);
  assert.deepEqual(parsed(headers + '@@ -1 +0,0 @@\n-old\n').hunks[0]!.lines, [{kind: 'removed', text: 'old', oldLine: 1}]);
  assert.deepEqual(parsed('diff --git a/guide.md b/guide.md\nold mode 100644\nnew mode 100755\n').hunks, []);
  for (const meta of ['new file mode 100644\nindex 0000000..e69de29\n', 'deleted file mode 100644\nindex e69de29..0000000\n',
    'new file mode 100644\nindex 0000000..1234567\n', 'deleted file mode 100644\nindex 1234567..0000000\n']) {
    const raw = 'diff --git a/guide.md b/guide.md\n' + meta;
    assert.deepEqual(parseUnifiedPatch(raw), {kind: 'fallback', reason: 'syntax'});
    assert.ok(renderToStaticMarkup(<UnifiedPatch text={raw} sanitized={false}/>).includes('>' + escaped(raw) + '</pre>'));
  }
  assert.deepEqual(parsed(''), {kind: 'parsed', headers: [], hunks: []});
});
test('Incomplete counts unknown records second files and incomplete termination use whole-text fallback', () => {
  for (const tail of ['@@ -1 +1 @@\n-old\n', '@@ -1 +1 @@\n-old\n+new\n+extra\n',
    '@@ -1 +1 @@\nold\n+new\n', '@@@ -1 +1 @@@\n-old\n+new\n', '@@ -1 +1 @@\n-old\n+new',
    '@@ -1 +1 @@\n-old\n+new\ndiff --git a/other b/other\n', '@@ -1 +1 @@\r\n-old\n+new\n']) {
    assert.deepEqual(parseUnifiedPatch(headers + tail), {kind: 'fallback', reason: 'syntax'});
  }
  for (const prefix of ['diff --git a/a b/a\nsimilarity index 100%\n', 'diff --git a/a b/a\nindex abc..def\n',
    'diff --git a/a b/a\nnew mode 100755\n', 'diff --git a/a b/a\n--- a/a\n']) {
    assert.equal(parseUnifiedPatch(prefix).kind, 'fallback');
  }
});
test('Unsafe coordinates overlap and invalid no-newline placement never produce line counters', () => {
  for (const body of ['@@ -9007199254740991 +1 @@\n-old\n+new\n', '@@ -0 +1 @@\n-old\n+new\n',
    '@@ -0,0 +0,0 @@\n', '@@ -01 +1 @@\n-old\n+new\n', '@@ -1 +1 @@\n same\n@@ -1 +1 @@\n same\n',
    '@@ -1 +4 @@\n-old\n+new\n', '@@ -1 +1 @@\n same\n@@ -4 +5 @@\n later\n',
    '@@ -1 +1 @@\n\\ No newline at end of file\n-old\n+new\n',
    '@@ -1,2 +1 @@\n-old\n\\ No newline at end of file\n-tail\n+new\n',
    '@@ -1 +1 @@\n-old\n+new\n\\ No newline at end of file\n\\ No newline at end of file\n',
    '@@ -1 +1 @@\n same\n\\ No newline at end of file\n@@ -3 +3 @@\n more\n']) {
    assert.equal(parseUnifiedPatch(headers + body).kind, 'fallback', body);
  }
});
test('UTF8 bytes records and hunks have independent display bounds without truncating supplied text', () => {
  assert.deepEqual(parseUnifiedPatch('🪴'.repeat(Math.floor(PATCH_DISPLAY_BYTES / 4) + 1)), {kind: 'fallback', reason: 'display-limit'});
  const rows = headers + `@@ -1,${PATCH_DISPLAY_LINES} +1,${PATCH_DISPLAY_LINES} @@\n` + ' x\n'.repeat(PATCH_DISPLAY_LINES);
  assert.deepEqual(parseUnifiedPatch(rows), {kind: 'fallback', reason: 'display-limit'});
  const many = headers + Array.from({length: PATCH_DISPLAY_HUNKS + 1}, (_, i) => `@@ -${i * 3 + 1} +${i * 3 + 1} @@\n x\n`).join('');
  assert.deepEqual(parseUnifiedPatch(many), {kind: 'fallback', reason: 'display-limit'});
  const maximum = headers + Array.from({length: PATCH_DISPLAY_HUNKS}, (_, i) => `@@ -${i * 3 + 1} +${i * 3 + 1} @@\n x\n`).join('');
  assert.equal(parsed(maximum).hunks.length, PATCH_DISPLAY_HUNKS);
});
test('Unsupported Raw preserves every supplied Unicode space escape and line ending as inert text', () => {
  const text = '<img src="https://bad.test">\r\n雪🪴\t  \\u{202e}\n\nunfinished';
  const html = renderToStaticMarkup(<UnifiedPatch text={text} sanitized/>);
  assert.ok(html.includes('>' + escaped(text) + '</pre>')); assert.match(html, /Raw supplied patch/u);
  assert.match(html, /cannot be numbered reliably/u); assert.match(html, /including those escapes/u);
  assert.doesNotMatch(html, /<(?:img|script|iframe)\b|<table\b|role="tab"/u);
});
test('Rendered counters and explicit change labels are readable without color and never execute patch text', () => {
  const text = headers + '@@ -1 +1 @@\n-<script>old()</script>\n+<img src="https://bad.test">雪🪴\n';
  const html = renderToStaticMarkup(<UnifiedPatch text={text} sanitized={false}/>);
  assert.match(html, /role="tab"[^>]*aria-selected="true"[^>]*data-patch-mode="diff"/u);
  for (const label of ['Old', 'New', 'Change', 'Content', 'Added line', 'Removed line', 'Read-only', 'Hunk 1']) assert.ok(html.includes(label));
  assert.match(html, /&lt;script&gt;old\(\)&lt;\/script&gt;/u); assert.match(html, /&lt;img src=&quot;https:\/\/bad.test&quot;&gt;/u);
  assert.doesNotMatch(html, /<(?:img|script|iframe|textarea|input)\b|>Approve<|>Merge</u);
});
test('Scope A to B to A session and capability replacement permanently retire previous read lifetimes', () => {
  const fence = new ReviewScopeFence(), a = identity(); const first = fence.update(a);
  assert.equal(fence.current(first), true); assert.equal(fence.update({...a}), first);
  const other = fence.update({...a, project: 'other'}); assert.equal(fence.current(first), false);
  const again = fence.update(a); assert.equal(fence.current(first), false); assert.equal(fence.current(other), false); assert.equal(fence.current(again), true);
  for (const change of [{token: {}}, {token: null}, {mode: 'unsupported'}, {client: {} as HomeClient}, {revision: '2'}, {head: 'new-head'}]) {
    const before = fence.update(a), changed = fence.update({...a, ...change}); assert.equal(fence.current(before), false);
    const restored = fence.update(a); assert.equal(fence.current(changed), false); assert.equal(fence.current(restored), true);
  }
});
test('New selection retry and retirement cannot revive earlier in-flight publication', async () => {
  const fence = new ReviewReadFence(), accepted: string[] = [];
  let resolveA!: () => void; const pendingA = new Promise<void>(resolve => {resolveA = resolve;});
  const a = fence.begin(); const old = pendingA.then(() => {if (fence.current(a)) accepted.push('old A');});
  const b = fence.begin(); assert.equal(fence.current(a), false);
  const again = fence.begin(); assert.equal(fence.current(b), false); accepted.push('fresh A'); resolveA(); await old;
  assert.deepEqual(accepted, ['fresh A']); fence.retire(); assert.equal(fence.current(again), false);
  assert.equal(fence.current(fence.begin()), true);
});
test('Missing actual session and unsupported current carrier reveal no review metadata or read controls', () => {
  for (const [token, mode] of [[null, 'legacy'], [{}, 'unsupported'], [{}, 'native-human-doc']] as const) {
    const stub = {currentSessionToken: () => token, productMode: () => ({kind: mode}),
      reviewChanges: () => {throw Error('No read permitted');}} as unknown as HomeClient;
    const html = renderToStaticMarkup(<ReviewChanges client={stub} project="private-project" snapshot="private-snapshot"
      proposal="private-proposal" revision="private-revision" base="private-base" head="private-head"/>);
    assert.match(html, /unavailable/u); assert.doesNotMatch(html, /private-|<button|Patch|Comparison/u);
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {ProductWorkList, groupProductWorkPage} from '../src/productWorkList';
import type {ProductWorkPreview} from '../src/productProtocol';
import {id, project, row} from './product-work-list-rows';
const render = (rows: readonly ProductWorkPreview[], locked = false) => renderToStaticMarkup(<ProductWorkList projectId={project} pageToken={{}} rows={rows}
  locked={locked} onOpen={() => { throw Error('Static markup cannot navigate'); }} onRefresh={() => { throw Error('Static markup cannot refresh'); }}/>);

test('One authorized page groups every row once without sorting within a status or mutating source', () => {
  const rows = Object.freeze([row(201, {status: 'done'}), row(202, {status: 'in_review'}), row(203), row(204, {status: 'backlog'}),
    row(205, {status: 'canceled'}), row(206, {status: 'legacy-blocked'}), row(207, {status: 'in_progress'}), row(208)]
    .map(value => Object.freeze(value)));
  const before = JSON.stringify(rows), groups = groupProductWorkPage(project, rows)!;
  assert.deepEqual(groups.map(group => group.status), ['backlog', 'todo', 'in_progress', 'in_review', 'legacy-blocked', 'done', 'canceled']);
  assert.deepEqual(groups.find(group => group.status === 'todo')!.rows, [rows[2], rows[7]]);
  assert.equal(new Set(groups.flatMap(group => group.rows)).size, rows.length); assert.equal(JSON.stringify(rows), before);
});
test('Malformed scope duplicate unknown enums and overfull pages fail as one page without partial content', () => {
  const bad = [row(201, {project_id: id(101)}), row(201, {status: 'running' as ProductWorkPreview['status']}),
    row(201, {priority: 'critical' as ProductWorkPreview['priority']}), row(201, {priority: '__proto__' as ProductWorkPreview['priority']})];
  for (const value of bad) { assert.equal(groupProductWorkPage(project, [row(200), value]), undefined); assert.doesNotMatch(render([row(200), value]), /Work 200/u); }
  assert.equal(groupProductWorkPage(project, [row(200), row(200)]), undefined);
  assert.equal(groupProductWorkPage(project, Array.from({length: 21}, (_, i) => row(200 + i))), undefined);
  assert.equal(groupProductWorkPage(project, Array.from({length: 20}, (_, i) => row(200 + i)))![0].rows.length, 20);
});
test('Group counts explicitly describe only this page and terminal groups start as named disclosures', () => {
  const html = render([row(201), row(202), row(203, {status: 'done'}), row(204, {status: 'canceled'})]);
  assert.match(html, /Grouped by status on this page\./u); assert.match(html, /2 on this page/u);
  assert.equal((html.match(/<details\b/gu) ?? []).length, 2); assert.doesNotMatch(html, /<details[^>]*\bopen(?:[=>\s])/u);
  assert.match(html, /<summary[^>]*>Done/u); assert.match(html, /<summary[^>]*>Canceled/u);
  assert.equal((html.match(/<button\b/gu) ?? []).length, 4); assert.doesNotMatch(html, /all work|project total|completed today/iu);
  const second = render([row(220, {status: 'done'})]); assert.doesNotMatch(second, /Work 20[1-4]/u); assert.match(second, /1 on this page/u);
});
test('Owner and worker stay separate with honest blank names and Normal priority without exposed identities', () => {
  const html = render([row(201, {priority: 'medium', owner_principal_id: id(300), worker_principal_id: id(301), worker_display_name: 'Mira'}),
    row(202, {status: 'legacy-blocked'})]);
  assert.match(html, /Owner: <\/span>Project member/u); assert.match(html, /Working on it: <\/span>Mira/u);
  assert.match(html, /Priority: <\/span>Normal/u); assert.match(html, /No priority/u); assert.match(html, /Blocked \(legacy\)/u);
  assert.match(html, /Owner: <\/span>Unassigned/u); assert.doesNotMatch(html, /Medium|Agent|Human|019939ba|a{64}/u);
});
test('Read navigation remains available to readers and locks disable every row without adding mutation controls', () => {
  const rows = [row(201), row(202, {status: 'done'})], ready = render(rows), locked = render(rows, true);
  assert.doesNotMatch(ready, /<button[^>]*disabled/u); assert.equal((locked.match(/<button[^>]*disabled=""/gu) ?? []).length, 2);
  assert.match(locked, /Work 201/u); assert.doesNotMatch(locked, /<input|<textarea|<form|>Save<|>Assign<|>Complete</u);
});
test('Untrusted display labels remain text and empty pages do not claim that all Work is complete', () => {
  const html = render([row(201, {title: '<script>private()</script>', owner_display_name: '<img src="https://bad.test">', worker_display_name: '雪🪴'})]);
  assert.match(html, /&lt;script&gt;private\(\)&lt;\/script&gt;/u); assert.match(html, /&lt;img src=&quot;https:\/\/bad\.test&quot;&gt;/u);
  assert.doesNotMatch(html, /<(?:script|img)\b|<[a-z][^>]*\s(?:href|src)=/u);
  assert.match(html, /雪🪴/u); assert.equal(render([]), '');
});

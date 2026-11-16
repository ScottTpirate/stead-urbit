import test from 'node:test';
import assert from 'node:assert/strict';
import {decodeProductRoute, encodeProductRoute, NavigationMemory, type ProductRoute} from '../src/productRoutes';
import {newWorkDefaults, priorityLabel, relationshipLabel, workStateLabel} from '../src/productModel';
const project = '019939ba-4000-7000-8000-000000000001';
const item = '019939ba-4000-7000-8000-000000000002';
const collection = '019939ba-4000-7000-8000-000000000003';
test('resource routes round-trip independent scope and exact revision without titles', () => {
  const routes: ProductRoute[] = [
    {kind:'workspace',view:'my-work'}, {kind:'project',project,view:'overview'},
    {kind:'work',project}, {kind:'work',project,item},
    {kind:'doc',project,collection,document:item}, {kind:'doc',project,collection,document:item,revision:'12'},
    {kind:'collection',project,collection},
    {kind:'repository',project,repository:item,view:'history'},
    {kind:'change',project,change:item,revision:'2'}, {kind:'run',project,run:item},
    {kind:'review',project,change:item,revision:'18446744073709551615'},
    {kind:'doc-change',project,work:item,change:collection},
    {kind:'doc-change',project,work:item,change:collection,result:{revision:'18446744073709551615',digest:'f'.repeat(64)}},
    {kind:'file',project,repository:item,commit:'a'.repeat(40),path:'docs/東京 guide.md'},
  ];
  for (const route of routes) assert.deepEqual(decodeProductRoute(encodeProductRoute(route)),route);
  assert.equal(encodeProductRoute({kind:'work',project,item}), `#work/${project}/${item}`);
});
test('addresses reject ambiguous scope, query payloads, encodings and unsupported revisions', () => {
  for (const hash of ['', '#unknown', '#work/foo', `#work/${project}/`, `#work/${project}/${item}/extra`,
    `#work/${project}?title=secret`, `#work/${project}%2F${item}`, `#doc/${project}/${collection}/${item}/0`,
    `#doc/${project}/${collection}/${item}/01`, `#project/${project}/agents`, `#run/${project}/${item}\n`,
    `#doc/${project}/${collection}/${item}/18446744073709551616`,
    `#review/${project}/${item}/18446744073709551616`,
    `#doc-change/${project}/${item}/${collection}/1`,
    `#doc-change/${project}/${item}/${collection}/0/${'f'.repeat(64)}`,
    `#doc-change/${project}/${item}/${collection}/18446744073709551616/${'f'.repeat(64)}`,
    `#doc-change/${project}/${item}/${collection}/1/${'f'.repeat(40)}`,
    `#doc-change/${project}/${item}/${collection}/1/${'F'.repeat(64)}`,
    `#doc-change/${project}/${item}/${collection}/1/${'f'.repeat(64)}/extra`,
    `#file/${project}/${item}/${'a'.repeat(40)}/..%2Fprivate`,
    `#file/${project}/${item}/main/README.md`,
    `#file/${project}/${item}/${'a'.repeat(40)}/docs%2fguide.md`]) {
    assert.equal(decodeProductRoute(hash), null, hash);
  }
});
test('navigation retains view state without allowing cross-principal leakage or mutation', () => {
  const memory = new NavigationMemory(); const route: ProductRoute={kind:'work',project};
  const view={filters:{title:'private words',status:'todo',assignee:''},scroll:120};
  memory.set(route,view); assert.equal(memory.get(route),undefined);
  memory.bind('member-one');memory.set(route,view);view.filters.title='changed';
  assert.equal(memory.get(route)?.filters.title,'private words');
  memory.get(route)!.filters.title='caller mutation';assert.equal(memory.get(route)?.filters.title,'private words');
  memory.bind('member-two');assert.equal(memory.get(route),undefined);
  memory.set(route,view);memory.clear();assert.equal(memory.get(route),undefined);
});
test('legacy labels keep blocked and supporting document meanings while defaults stay unassigned', () => {
  assert.equal(workStateLabel('blocked'),'Blocked');assert.equal(workStateLabel('in_review'),'In review');
  assert.equal(priorityLabel('medium'),'Normal');assert.equal(relationshipLabel('documents'),'Supports');
  assert.equal(newWorkDefaults.assignee_principal_id,'');assert.equal(newWorkDefaults.type,'task');
  assert.equal(newWorkDefaults.priority,'none');assert.equal(newWorkDefaults.status,'todo');
});

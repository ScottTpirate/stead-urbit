// Source-level navigation boundary tests; no Home/browser/native acceptance.
import test from 'node:test';
import assert from 'node:assert/strict';
import {NavigationMemory,encodeProductRoute} from '../src/productRoutes';
import {workspaceRestore,workspaceRestoreDecision,WORKSPACE_RESTORE_MAX_PAGES,WORKSPACE_RESTORE_BUDGET_MS,WorkspaceCursorSequence,WorkspaceRestoreCapture} from '../src/workspaceNavigation';
const project='019939ba-4000-7000-8000-000000000100',work='019939ba-4000-7000-8000-000000000101';
const route=encodeProductRoute({kind:'work',project,item:work});
const memory=(page=3,selection=route)=>({filters:{title:'guide',status:'',assignee:''},workspacePage:page,selection,scroll:321});
test('Workspace page metadata uses the existing session-cleared memory without protected rows or cursors',()=>{
 const store=new NavigationMemory(),address={kind:'workspace',view:'search'} as const;store.bind('session-a');store.set(address,memory());
 const read=store.get(address)!;assert.deepEqual(read,memory());read.workspacePage=9;read.filters.title='changed';assert.deepEqual(store.get(address),memory());
 store.bind('session-b');assert.equal(store.get(address),undefined);
});
test('Submitted search and view scope must match before restoring a later page',()=>{
 assert.equal(workspaceRestore('workspace-search','other',memory()),undefined);
 assert.equal(workspaceRestore('my-work','guide',memory()),undefined);
 assert.equal(workspaceRestore('workspace-search','guide',memory())?.page,3);
 assert.equal(workspaceRestore('my-work','unused',{...memory(),filters:{title:'',status:'',assignee:''}})?.page,3);
});
test('Restoration is bounded to admitted capacity and invalid page metadata cannot start traversal',()=>{
 assert.equal(WORKSPACE_RESTORE_MAX_PAGES,205);assert.equal(WORKSPACE_RESTORE_BUDGET_MS,20000);
 for(const page of [0,-1,1.5,NaN,Infinity,206,Number.MAX_SAFE_INTEGER])assert.equal(workspaceRestore('workspace-search','guide',memory(page)),undefined);
 assert.equal(workspaceRestore('workspace-search','guide',memory(205))?.page,205);
 const legacy={...memory()};delete (legacy as Partial<typeof legacy>).workspacePage;assert.equal(workspaceRestore('workspace-search','guide',legacy)?.page,1);
});
test('A selected item on an earlier fresh page stops traversal before the remembered page',()=>{
 const target=workspaceRestore('workspace-search','guide',memory())!;
 assert.equal(workspaceRestoreDecision({page:1,cursor:'one',target,routes:[]}), 'continue');
 assert.equal(workspaceRestoreDecision({page:2,cursor:'two',target,routes:[route]}),'found');
});
test('Missing selection does not scan beyond its remembered page and absence copy distinguishes end',()=>{
 const target=workspaceRestore('workspace-search','guide',memory())!;
 assert.equal(workspaceRestoreDecision({page:3,cursor:'untouched-next',target,routes:[]}),'page');
 assert.equal(workspaceRestoreDecision({page:2,cursor:'',target,routes:[]}),'end');
 assert.equal(workspaceRestoreDecision({page:205,cursor:'untouched-next',target:{...target,page:205},routes:[]}),'page');
});
test('Only exact Work/Doc selections and finite scroll positions are restored',()=>{
 for(const selection of ['#work/'+project,'#project/'+project+'/overview','#search','javascript:alert(1)'])assert.equal(workspaceRestore('workspace-search','guide',memory(2,selection))?.selection,undefined);
 const doc=encodeProductRoute({kind:'doc',project,collection:work,document:'019939ba-4000-7000-8000-000000000102'});
 assert.equal(workspaceRestore('workspace-search','guide',memory(2,doc))?.selection,doc);
 assert.equal(workspaceRestore('workspace-search','guide',{...memory(),scroll:Infinity})?.scroll,0);
 assert.equal(workspaceRestore('workspace-search','guide',{...memory(),scroll:-1})?.scroll,0);
});

test('A restore sequence rejects a repeated returned token even when subsequent rows differ',()=>{
 const sequence=new WorkspaceCursorSequence();sequence.use('');sequence.receive('a');sequence.use('a');sequence.receive('b');sequence.use('b');
 assert.throws(()=>sequence.receive('a'),/invalid_response/u);
});
test('A cursor can be consumed once and a returned current input cannot authorize another read',()=>{
 const sequence=new WorkspaceCursorSequence();sequence.receive('one');sequence.use('one');
 assert.throws(()=>sequence.use('one'),/invalid_response/u);assert.throws(()=>sequence.receive('one'),/invalid_response/u);
 const fresh=new WorkspaceCursorSequence();fresh.receive('one');fresh.use('one');fresh.receive('');
});

test('Parent page-memory rerender cannot replace the original scroll and selection before focus commits',()=>{
 const capture=new WorkspaceRestoreCapture(),original={page:3,selection:route,scroll:777};
 const accepted=capture.capture('scope-a',0,original)!;original.scroll=0;original.page=1;
 const rerender=capture.capture('scope-a',0,{page:3,selection:route,scroll:12});
 assert.equal(rerender,accepted);assert.deepEqual(rerender,{page:3,selection:route,scroll:777});assert.equal(Object.isFrozen(rerender),true);
 const refreshed=capture.capture('scope-a',1,{page:1,scroll:0});assert.notEqual(refreshed,accepted);assert.equal(refreshed?.page,1);
 capture.capture('scope-b',0,{page:2,scroll:40});assert.equal(capture.capture('scope-a-new-generation',0,{page:4,scroll:99})?.scroll,99);
});

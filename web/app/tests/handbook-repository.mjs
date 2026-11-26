import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';

// Check the same release Markdown and adapter that esbuild serves to the real Code screen.
const adapter = await build({entryPoints: [fileURLToPath(new URL('../src/handbookRepository.ts', import.meta.url))],
  bundle: true, platform: 'browser', target: 'es2022', format: 'esm', write: false});
const {handbookRepositoryResponse: respond} = await import('data:text/javascript;base64,' + Buffer.from(adapter.outputFiles[0].contents).toString('base64'));
const project = '019a0000-0000-7000-8000-000000000001';
const code = '/stead/api/code', browse = code + '/browse';
const request = {protocol: 'stead.code/1', project_id: project};
const status = await respond(code, {...request, action: 'status'}).json();
assert.deepEqual(status, {protocol: request.protocol, status: 'external', write: 'no', manage: 'no'});
const pack = await respond(code, {...request, action: 'pack-view'}).json();
const ref = Buffer.from('refs/heads/main').toString('hex');
const selection = {protocol: 'stead.git-browse/1', project_id: project, snapshot: pack.snapshot, ref};
const tree = await respond(browse, {...selection, path: [], view: 'tree'}).json();
const name = Buffer.from('README.md').toString('hex');
const file = await respond(browse, {...selection, path: [name], view: 'file'}).json();
const markdown = await readFile(new URL('../src/handbook/README.md', import.meta.url));
function objectId(kind, bytes) {
  return createHash('sha1').update(kind + ' ' + bytes.length + '\0').update(bytes).digest('hex');
}
const blobId = objectId('blob', markdown);
const treeId = objectId('tree', Buffer.concat([Buffer.from('100644 README.md\0'), Buffer.from(blobId, 'hex')]));
const author = 'Stead Handbook <handbook@stead.invalid> 1795651200 +0000';
const commitId = objectId('commit', Buffer.from(`tree ${treeId}\nauthor ${author}\ncommitter ${author}\n\nRead the Stead Handbook\n`));
assert.deepEqual(tree.entries, [{name, kind: 'file', oid: blobId}]);
assert.deepEqual(JSON.parse(pack.refs), {[ref]: commitId});
assert.equal(pack.head, ref);
assert.equal(tree.commit, commitId);
assert.equal(file.commit, commitId);
assert.equal(file.bytes, markdown.length);
assert.equal(file.text, markdown.toString('utf8'));
assert.equal(pack.object_count, '3');
assert.match(pack.snapshot, /^[0-9a-f]{64}$/u);

assert.equal(respond('/stead/api/query', {}), undefined);
for (const input of [
  {...request, action: 'issue'}, {...request, action: 'pack-accept'}, {...request, action: 'external-submit'},
  {...request, action: 'status', extra: 'field'}, {...request, action: 'external-list', work_id: project},
  {...request, action: 'status', project_id: '019a0000-0000-7000-8000-000000000002'}
]) assert.equal(respond(code, input).status, 403);
for (const overrides of [
  {snapshot: '0'.repeat(64)}, {ref: '00'}, {path: [name, name]}, {view: 'file'}, {project_id: ''}, {extra: true},
]) assert.equal(respond(browse, {...selection, path: [], view: 'tree', ...overrides}).status, 403);
for (const scope of [{}, {work_id: '019a0000-0000-7000-8000-000000000003'}]) {
  assert.deepEqual(await respond(code, {...request, action: 'external-list', ...scope}).json(),
    {protocol: request.protocol, status: 'proposals', rows: '[]'});
}

import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rename, rm, readdir } from 'node:fs/promises';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { publishDirectory } from '../publish.mjs';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const runtime = path.resolve(root, '../../.runtime/web-app-tests');
await mkdir(runtime, {recursive: true});
async function fixture(t) {
  const base = await mkdtemp(path.join(runtime, 'publication-'));
  t.after(() => rm(base, {recursive: true, force: true}));
  const staging = path.join(base, '.build-owned'); const destination = path.join(base, 'dist');
  for (const [dir, value] of [[staging, 'new'], [destination, 'old']]) { await mkdir(dir); await writeFile(path.join(dir, 'version'), value); }
  return {base, staging, destination};
}
test('publication restores existing output after an actual missing-staging filesystem failure', async t => {
  const {staging, destination} = await fixture(t);
  let moves = 0;
  await assert.rejects(publishDirectory(staging, destination, {rm, rename: async (from, to) => {
    if (++moves === 2) await rm(staging, {recursive: true});
    return rename(from, to); // Actual ENOENT, after moving the old output aside.
  }}), {code: 'ENOENT'});
  assert.equal(await readFile(path.join(destination, 'version'), 'utf8'), 'old');
  assert.equal(moves, 3);
});
test('successful publication preserves an unrelated interrupted-build backup', async t => {
  const {base, staging, destination} = await fixture(t);
  const orphan = path.join(base, '.build-interrupted-previous'); await mkdir(orphan);
  await writeFile(path.join(orphan, 'version'), 'earlier');
  await publishDirectory(staging, destination);
  assert.equal(await readFile(path.join(destination, 'version'), 'utf8'), 'new');
  assert.equal(await readFile(path.join(orphan, 'version'), 'utf8'), 'earlier');
  assert.deepEqual((await readdir(base)).sort(), ['.build-interrupted-previous', 'dist']);
});
test('failed rollback retains the previous output for explicit recovery', async t => {
  const {staging, destination} = await fixture(t);
  let moves = 0;
  await assert.rejects(publishDirectory(staging, destination, {rm, rename: async (from, to) => {
    if (++moves === 2) { await mkdir(destination); await writeFile(path.join(destination, 'concurrent'), 'unexpected'); }
    return rename(from, to); // Both moves fail against the nonempty destination.
  }}), AggregateError);
  assert.equal(await readFile(path.join(staging + '-previous', 'version'), 'utf8'), 'old');
  assert.equal(await readFile(path.join(staging, 'version'), 'utf8'), 'new');
  assert.equal(await readFile(path.join(destination, 'concurrent'), 'utf8'), 'unexpected');
});
test('actual build rejects concurrent lock ownership before compiling', {timeout: 5000}, async t => {
  const holder = spawn('flock', ['-n', path.join(root, '.build.lock'), 'cat'], {stdio: ['pipe', 'pipe', 'pipe']});
  t.after(() => holder.stdin.end());
  const acquired = once(holder.stdout, 'data'); holder.stdin.write('held\n');
  assert.equal(String((await acquired)[0]), 'held\n');
  const second = spawnSync(process.execPath, [path.join(root, 'build.mjs')], {encoding: 'utf8', timeout: 2000});
  assert.equal(second.status, 75); assert.match(second.stderr, /already running/u);
  const finished = once(holder, 'exit'); holder.stdin.end(); assert.equal((await finished)[0], 0);
});

// Bounded host boundary tests only. No browser, native ship or live carrier.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir, mkdtemp, readFile, writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0');
const files = ['src/docChangeProtocol.ts','src/productWire.ts','src/productProtocol.ts','src/protocol.ts','tests/doc-change-protocol.test.ts','tests/doc-change-protocol.mjs','tests/doc-change-vectors.json','package-lock.json','../../native/core/desk/lib/stead-doc-change-codec.hoon','../../native/core/desk/lib/stead-codec.hoon','../../native/core/desk/lib/stead-team-codec.hoon','../../native/core/desk/lib/stead-product-codec.hoon','../../native/core/desk/tests/stead-doc-change-codec.hoon'];
async function inputs() { return Object.fromEntries(await Promise.all(files.map(async name => {
  const raw = await readFile(path.join(root, name)); assert.ok(raw.length <= 1024 * 1024); return [name, createHash('sha256').update(raw).digest('hex')];
}))); }
await mkdir(path.resolve(root, '../../.runtime'), {recursive: true});
const output = await mkdtemp(path.resolve(root, '../../.runtime/doc-change-protocol-'));
const names = [...(await readFile(path.join(root, 'tests/doc-change-protocol.test.ts'), 'utf8')).matchAll(/^test\('([^']+)'/gmu)].map(match => match[1]);
assert.equal(names.length, 10); assert.equal(new Set(names).size, 10);
const report = {classification: 'host-doc-change-codec-source-derived-vectors', qualifies_phase: false, node: process.version,
  expected_tests: names, status: 'running', inputs_before: await inputs()};
try {
  const bundle = path.join(output, 'doc-change-protocol.test.mjs');
  await build({absWorkingDir: root, entryPoints: ['tests/doc-change-protocol.test.ts'], outfile: bundle, bundle: true, platform: 'node', format: 'esm', target: 'node24'});
  const run = spawnSync(process.execPath, ['--test', '--test-reporter=tap', '--test-concurrency=1', bundle], {encoding: 'utf8', timeout: 60000, maxBuffer: 1024 * 1024});
  const log = (run.stdout ?? '') + (run.stderr ?? ''); await writeFile(path.join(output, 'tests.log'), log);
  assert.equal(run.error, undefined); assert.equal(run.status, 0, log);
  assert.match(log, /# tests 10\n/u); assert.match(log, /# pass 10\n/u); assert.match(log, /# fail 0\n/u);
  const executed = [...log.matchAll(/^ok [0-9]+ - (.+)$/gmu)].map(match => match[1]);
  assert.deepEqual(executed, names);
  report.status = 'pass';
} catch (error) { report.status = 'fail'; report.error = error.stack ?? String(error); process.exitCode = 1; }
finally {
  report.inputs_after = await inputs();
  if (JSON.stringify(report.inputs_before) !== JSON.stringify(report.inputs_after)) { report.status = 'fail'; report.error = 'Protocol inputs changed'; process.exitCode = 1; }
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({status: report.status, report: path.join(output, 'report.json'), error: report.error}));
}

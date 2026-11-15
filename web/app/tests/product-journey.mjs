// Bounded host tests for injected journey state/read boundaries, not live acceptance.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir, mkdtemp, readFile, writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0');
await mkdir(path.resolve(root, '../../.runtime'), {recursive: true});
const output = await mkdtemp(path.resolve(root, '../../.runtime/product-journey-'));
const names = [...(await readFile(path.join(root, 'tests/product-journey.test.ts'), 'utf8')).matchAll(/^test\('([^']+)'/gmu)].map(match => match[1]);
assert.equal(names.length, 17); assert.equal(new Set(names).size, 17);
const sha = raw => createHash('sha256').update(raw).digest('hex');
const inputs = Object.create(null);
for (const file of ['package-lock.json', 'tests/product-journey.mjs']) inputs[file] = sha(await readFile(path.join(root, file)));
const report = {classification: 'host-product-journey-state-and-injected-read-tests', qualifies_phase: false, node: process.version,
  expected_tests: names, status: 'running', inputs_before: inputs};
try {
  const bundle = path.join(output, 'product-journey.test.mjs');
  await build({absWorkingDir: root, entryPoints: ['tests/product-journey.test.ts'], outfile: bundle, bundle: true, platform: 'node', format: 'esm', target: 'node24',
    plugins: [{name: 'hash-exact-owned-build-inputs', setup(builder) { builder.onLoad({filter: /\.(?:tsx?|jsx?|css)$/}, async args => {
      if (args.path.includes('/node_modules/')) return;
      const file = path.relative(root, args.path); assert.ok(!file.startsWith('..') && !path.isAbsolute(file));
      assert.match(file, /^(?:src|tests)\//u); assert.ok(Object.keys(inputs).length < 64 || file in inputs);
      const raw = await readFile(args.path); assert.ok(raw.length <= 1024 * 1024); inputs[file] = sha(raw);
      // CSS has no host behavior. It remains hash-bound, while browser layout is a separate gate.
      return {contents: args.path.endsWith('.css') ? '' : raw, loader: args.path.endsWith('.tsx') ? 'tsx' : args.path.endsWith('.ts') ? 'ts' : 'js'};
    }); }}]});
  const run = spawnSync(process.execPath, ['--test', '--test-reporter=tap', '--test-concurrency=1', bundle], {encoding: 'utf8', timeout: 60000, maxBuffer: 1024 * 1024});
  const log = (run.stdout ?? '') + (run.stderr ?? ''); await writeFile(path.join(output, 'tests.log'), log);
  assert.equal(run.error, undefined); assert.equal(run.status, 0, log);
  assert.match(log, /# tests 17\n/u); assert.match(log, /# pass 17\n/u); assert.match(log, /# fail 0\n/u);
  assert.deepEqual([...log.matchAll(/^ok [0-9]+ - (.+)$/gmu)].map(match => match[1]), names);
  report.status = 'pass';
} catch (error) { report.status = 'fail'; report.error = error.stack ?? String(error); process.exitCode = 1; }
finally {
  report.inputs_after = Object.fromEntries(await Promise.all(Object.keys(inputs).map(async file => [file, sha(await readFile(path.join(root, file)))])));
  if (JSON.stringify(report.inputs_before) !== JSON.stringify(report.inputs_after)) { report.status = 'fail'; report.error = 'Journey source changed'; process.exitCode = 1; }
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({status: report.status, report: path.join(output, 'report.json'), error: report.error}));
}

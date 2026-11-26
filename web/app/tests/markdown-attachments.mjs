// Host rendering and strict-client fixtures; browser/native checks are separate.
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, readFile, writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build, stop} from 'esbuild';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0');
assert.ok(process.argv.length <= 3);
const parent = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(root, '../../.runtime');
await mkdir(parent, {recursive: true});
const output = await mkdtemp(path.join(parent, 'markdown-attachments-'));
const names = [];
for (const file of ['markdown.test.tsx', 'markdown-attachments.test.tsx', 'product-contract.test.ts']) {
  names.push(...[...(await readFile(path.join(root, 'tests', file), 'utf8')).matchAll(/^test\('([^']+)'/gmu)].map(match => match[1]));
}
assert.equal(names.length, 15); assert.equal(new Set(names).size, 15);
try {
  const bundle = path.join(output, 'host.test.mjs');
  await build({absWorkingDir: root, entryPoints: ['tests/markdown-attachments-host.ts'], outfile: bundle,
    bundle: true, platform: 'node', format: 'esm', target: 'node24',
    banner: {js: "import {createRequire} from 'node:module';const require=createRequire(import.meta.url);"},
    plugins: [{name: 'host-css', setup(builder) {
      builder.onLoad({filter: /\.css$/}, () => ({contents: '', loader: 'js'}));
    }}]});
  const run = spawnSync(process.execPath, ['--test', '--test-reporter=tap', '--test-concurrency=1', bundle],
    {cwd: root, encoding: 'utf8', timeout: 30000, maxBuffer: 1024 * 1024});
  const log = (run.stdout ?? '') + (run.stderr ?? '');
  await writeFile(path.join(output, 'tests.log'), log);
  assert.equal(run.error, undefined); assert.equal(run.status, 0, log);
  assert.deepEqual([...log.matchAll(/^ok [0-9]+ - (.+)$/gmu)].map(match => match[1]), names);
  for (const line of ['# tests 15', '# pass 15', '# fail 0', '# skipped 0', '# cancelled 0', '# todo 0']) {
    assert.ok(log.includes(line + '\n'), log);
  }
  console.log(JSON.stringify({classification: 'host-only-markdown-attachments-and-product-routes', status: 'pass', tests: 15, output}));
} finally { stop(); }

import { build } from 'esbuild';
import { mkdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.resolve(root, '../../.runtime/web-app-tests/client.test.mjs');
await mkdir(path.dirname(output), { recursive: true });
await build({absWorkingDir: root, entryPoints: ['tests/client.test.ts'], outfile: output,
  bundle: true, platform: 'node', format: 'esm', target: 'node24'});
const result = spawnSync(process.execPath, ['--test', '--test-concurrency=1', output,
  path.join(root, 'tests/build.test.mjs'), path.join(root, 'tests/onboarding-evidence.test.mjs'),
  path.join(root, 'tests/response-capture.test.mjs')], {stdio: 'inherit'});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;

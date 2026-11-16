// Host boundary tests only. No browser, native ship, transport endpoint or effect.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir, mkdtemp, readFile, writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');assert.equal(process.version,'v24.21.0');
const files=['src/runReadProtocol.ts','src/productWire.ts','src/protocol.ts','tests/run-read.test.ts','tests/run-read.mjs','tests/run-read-vectors.json','package-lock.json',
  '../../native/core/desk/lib/stead-run-query.hoon','../../native/core/desk/lib/stead-run-views.hoon','../../native/core/desk/lib/stead-run-state.hoon','../../native/core/desk/lib/stead-run.hoon','../../native/core/desk/lib/stead-codec.hoon'];
async function inputs(){return Object.fromEntries(await Promise.all(files.map(async file=>{const raw=await readFile(path.join(root,file));assert.ok(raw.length<=1024*1024);return[file,createHash('sha256').update(raw).digest('hex')];})));}
await mkdir(path.resolve(root,'../../.runtime'),{recursive:true});const output=await mkdtemp(path.resolve(root,'../../.runtime/run-read-'));
const names=[...(await readFile(path.join(root,'tests/run-read.test.ts'),'utf8')).matchAll(/^test\('([^']+)'/gmu)].map(match=>match[1]);assert.equal(names.length,14);assert.equal(new Set(names).size,14);
const report={classification:'host-run-read-protocol-and-injected-client-tests',qualifies_phase:false,browser_executed:false,native_executed:false,node:process.version,
  expected_tests:names,status:'running',inputs_before:await inputs()};
try{
  const bundle=path.join(output,'run-read.test.mjs');await build({absWorkingDir:root,entryPoints:['tests/run-read.test.ts'],outfile:bundle,bundle:true,platform:'node',format:'esm',target:'node24'});
  const run=spawnSync(process.execPath,['--test','--test-reporter=tap','--test-concurrency=1',bundle],{encoding:'utf8',timeout:60000,maxBuffer:1024*1024});
  const log=(run.stdout??'')+(run.stderr??'');await writeFile(path.join(output,'tests.log'),log);assert.equal(run.error,undefined);assert.equal(run.status,0,log);
  assert.match(log,/# tests 14\n/u);assert.match(log,/# pass 14\n/u);assert.match(log,/# fail 0\n/u);
  assert.deepEqual([...log.matchAll(/^ok [0-9]+ - (.+)$/gmu)].map(match=>match[1]),names);report.status='pass';
}catch(error){report.status='fail';report.error=error.stack??String(error);process.exitCode=1;}
finally{report.inputs_after=await inputs();if(JSON.stringify(report.inputs_before)!==JSON.stringify(report.inputs_after)){report.status='fail';report.error='Run read inputs changed';process.exitCode=1;}
  await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,report:path.join(output,'report.json'),error:report.error}));}

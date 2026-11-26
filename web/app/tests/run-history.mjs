// Host async-state and static-markup checks. No browser or native authority.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir,mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');assert.equal(process.version,'v24.21.0');
const files=['src/RunHistory.tsx','src/run-history.css','src/runReadProtocol.ts','src/productWire.ts','src/protocol.ts','src/productRoutes.ts','src/primitives.tsx','src/Icon.tsx','src/controls.css','src/style.css',
  'tests/run-history-fixture.ts','tests/run-history.test.ts','tests/run-history.mjs','package-lock.json'];
async function inputs(){return Object.fromEntries(await Promise.all(files.map(async file=>{const raw=await readFile(path.join(root,file));assert.ok(raw.length<=1024*1024);return[file,createHash('sha256').update(raw).digest('hex')];})));}
await mkdir(path.resolve(root,'../../.runtime'),{recursive:true});const output=await mkdtemp(path.resolve(root,'../../.runtime/run-history-'));
const names=[...(await readFile(path.join(root,'tests/run-history.test.ts'),'utf8')).matchAll(/^test\('([^']+)'/gmu)].map(match=>match[1]);assert.equal(names.length,12);assert.equal(new Set(names).size,12);
const report={classification:'host-run-history-controller-and-static-markup',qualifies_phase:false,browser_executed:false,native_executed:false,node:process.version,status:'running',expected_tests:names,inputs_before:await inputs()};
try{
  const bundle=path.join(output,'run-history.test.mjs');await build({absWorkingDir:root,entryPoints:['tests/run-history.test.ts'],outfile:bundle,bundle:true,platform:'node',format:'esm',target:'node24',
    loader:{'.css':'empty'},banner:{js:"import {createRequire as hostRequire} from 'node:module';const require=hostRequire(import.meta.url);"}});
  const result=spawnSync(process.execPath,['--test','--test-reporter=tap','--test-concurrency=1',bundle],{cwd:root,encoding:'utf8',timeout:30000,maxBuffer:1024*1024});
  const log=(result.stdout??'')+(result.stderr??'');await writeFile(path.join(output,'tests.log'),log);assert.equal(result.error,undefined);assert.equal(result.status,0,log);
  assert.match(log,/# tests 12\n/u);assert.match(log,/# pass 12\n/u);assert.match(log,/# fail 0\n/u);assert.deepEqual([...log.matchAll(/^ok [0-9]+ - (.+)$/gmu)].map(match=>match[1]),names);report.status='pass';
}catch(error){report.status='fail';report.error=error.stack??String(error);process.exitCode=1;}
finally{report.inputs_after=await inputs();if(JSON.stringify(report.inputs_before)!==JSON.stringify(report.inputs_after)){report.status='fail';report.error='Run History source changed';process.exitCode=1;}
  await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,report:path.join(output,'report.json'),error:report.error}));}

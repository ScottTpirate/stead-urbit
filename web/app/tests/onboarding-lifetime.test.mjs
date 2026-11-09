import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdir, mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {setTimeout as sleep} from 'node:timers/promises';
import {test} from 'node:test';
import {fileURLToPath, pathToFileURL} from 'node:url';

// Substitute only Firefox's control interface. The actual recorder and
// evidence files run in the subprocess, without a desktop or native fixture.
const browser = `
import {EventEmitter} from 'node:events';
import {existsSync} from 'node:fs';
import {writeFile} from 'node:fs/promises';
const output = process.argv[4], scenario = process.argv[5];
export const firefox = {async launchPersistentContext() {
  const context = new EventEmitter();
  context.browser = () => ({version: () => 'synthetic'});
  context.route = async () => {};
  context.close = async () => { throw new Error('Recorder closed the user browser'); };
  context.newPage = async () => {
    const page = new EventEmitter();
    page.mainFrame = () => page;
    page.exposeBinding = async (_name, handler) => { page.finish = handler; };
    page.setContent = async () => {};
    page.goto = async () => {};
    page.evaluate = async () => writeFile(output + '/review-open', '');
    page.bringToFront = async () => {
      if (scenario !== 'submitted-for-review') return;
      const submit = setInterval(() => {
        if (!existsSync(output + '/ready.json')) return;
        clearInterval(submit);
        void page.finish({frame: page}, {tasks: [], notes: '', help: 'no'});
      }, 10);
    };
    return page;
  };
  const keepOpen = setInterval(() => {
    if (!existsSync(output + '/user-close')) return;
    clearInterval(keepOpen);
    context.emit('close');
  }, 10);
  return context;
}};
`;
const recorder = fileURLToPath(new URL('./onboarding.mjs', import.meta.url));
for (const scenario of ['submitted-for-review', 'deadline-incomplete', 'evidence-incomplete']) {
  test(`onboarding ${scenario} ends evidence capture and leaves the review window open`, {timeout: 6000}, async () => {
    const output = await mkdtemp(join(tmpdir(), 'stead-recorder-'));
    const input = join(output, 'personal-fixture.json');
    const mock = pathToFileURL(join(output, 'firefox.mjs')).href;
    const hooks = join(output, 'hooks.mjs');
    const env = {...process.env};
    delete env.SSLKEYLOGFILE;
    if (scenario === 'evidence-incomplete') await mkdir(join(output, 'onboarding-partial.tmp'));
    await writeFile(input, JSON.stringify({execution_id: 'synthetic', code: 'fake-code',
      origin: 'https://home.localhost:8443', identity_origin: 'https://bus.localhost:8444', identity_ship: '~bus'}));
    await writeFile(fileURLToPath(mock), browser);
    await writeFile(hooks, `
      import {registerHooks} from 'node:module';
      registerHooks({resolve(specifier, context, next) {
        return specifier === 'playwright' ? {url: ${JSON.stringify(mock)}, shortCircuit: true} : next(specifier, context);
      }});
      const timeout = globalThis.setTimeout;
      globalThis.setTimeout = (callback, delay, ...args) => timeout(callback, delay === 540000 ? 50 : delay, ...args);
    `);
    const processHandle = spawn(process.execPath, ['--import', hooks, recorder, output, input, output, scenario], {env});
    const exited = new Promise(resolve => processHandle.once('exit', resolve));
    try {
      const open = join(output, 'review-open');
      for (let count = 0; count < 150; count++) {
        try { await readFile(open); break; }
        catch (error) { if (error.code !== 'ENOENT') throw error; }
        assert.equal(processHandle.exitCode, null);
        await sleep(20);
      }
      await readFile(open);
      const report = JSON.parse(await readFile(join(output, 'onboarding-report.json'), 'utf8'));
      assert.equal(report.status, scenario);
      assert.equal(report.qualifies_phase, false);
      assert.equal(processHandle.exitCode, null);
      await writeFile(join(output, 'user-close'), '');
      assert.equal(await exited, 0);
    } finally {
      if (processHandle.exitCode === null) processHandle.kill();
      await exited;
      await rm(output, {recursive: true, force: true});
    }
  });
}

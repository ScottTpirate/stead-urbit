// Real Firefox interactions on an explicitly synthetic, API-free reference.
// This is not native authorization, dispatch, usability or release evidence.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { firefox } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
assert.equal(process.version, 'v24.21.0', 'Use the pinned frontend Node runtime');
const requestedCases = process.argv.slice(2);
assert.ok(requestedCases.length <= 8 && new Set(requestedCases).size === requestedCases.length
  && requestedCases.every(name => /^[a-z0-9-]{1,100}$/u.test(name)), 'At most eight unique bounded reference case names');
const runtime = path.resolve(root, '../../.runtime');
await mkdir(runtime, {recursive: true});
const output = await mkdtemp(path.join(runtime, 'product-work-reference-'));
const files = ['src/productWorkState.tsx','src/productWorkFields.tsx','src/productWorkComposer.tsx','src/productWorkDetail.tsx','src/productWork.css','src/productClient.ts','src/productProtocol.ts','src/productWire.ts','src/protocol.ts','src/primitives.tsx','src/Icon.tsx','src/controls.css','src/style.css','src/Markdown.tsx','src/markdown.css','tests/product-work-reference.tsx','tests/product-work-reference.css','tests/product-work-reference.mjs','package-lock.json'];
async function inputs() {
  return Object.fromEntries(await Promise.all(files.map(async file => {
    const raw = await readFile(path.join(root, file));
    assert.ok(raw.length <= 1024 * 1024, 'Bounded reference input');
    return [file, createHash('sha256').update(raw).digest('hex')];
  })));
}
const report = {classification: 'real-browser-synthetic-product-work-reference', qualifies_phase: false,
  node: process.version, status: 'running', checks: [], requested_cases: requestedCases,
  execution_scope: requestedCases.length ? 'selected-cases' : 'all-declared-cases', inputs_before: await inputs()};
let browser;
let server;
try {
  await build({absWorkingDir: root, entryPoints: ['tests/product-work-reference.tsx'], outfile: path.join(output, 'reference.js'),
    bundle: true, format: 'esm', target: 'es2022', define: {'process.env.NODE_ENV': '"development"'}});
  server = createServer(async (request, response) => {
    const asset = {'/reference.js': ['reference.js', 'text/javascript'], '/reference.css': ['reference.css', 'text/css']}[request.url];
    if (request.method !== 'GET') { response.writeHead(405); response.end(); }
    else if (asset) { response.writeHead(200, {'content-type': asset[1]}); response.end(await readFile(path.join(output, asset[0]))); }
    else if (request.url === '/') {
      response.writeHead(200, {'content-type': 'text/html'});
      response.end('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Stead synthetic interaction reference</title><link rel="stylesheet" href="/reference.css"></head><body><div id="root"></div><script type="module" src="/reference.js"></script></body></html>');
    } else { response.writeHead(404); response.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  browser = await firefox.launch({headless: true, timeout: 15000});
  report.browser = browser.version();
  async function check(name, operation) {
    if (requestedCases.length && !requestedCases.includes(name)) return;
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    const errors = [];
    const external = [];
    page.on('pageerror', error => errors.push(String(error)));
    await context.route('**/*', route => {
      const request = route.request();
      if (!request.url().startsWith(origin + '/') || request.method() !== 'GET') {
        external.push({url: request.url(), method: request.method()}); return route.abort();
      }
      return route.continue();
    });
    const item = {name, status: 'running'};
    report.checks.push(item);
    try {
      await page.goto(origin);
      await page.getByRole('heading', {name: 'Reserved Work interaction reference', exact: true}).waitFor();
      await operation(page);
      assert.deepEqual(errors, [], 'No browser runtime errors');
      assert.deepEqual(external, [], 'Reference never invokes Home, workers or external resources');
      item.status = 'pass';
    } catch (error) { item.status = 'fail'; item.error = error.stack ?? String(error); throw error; }
    finally { await context.close(); }
  }
  async function focused(locator) {
    const focus = await locator.evaluate(element => ({matches: element === document.activeElement,
      expected: element.getAttribute('aria-label') ?? element.textContent ?? element.tagName,
      actual: document.activeElement?.getAttribute('aria-label') ?? document.activeElement?.textContent?.slice(0, 120) ?? document.activeElement?.tagName}));
    assert.equal(focus.matches, true, `Expected keyboard focus: ${focus.expected}; found: ${focus.actual}`);
  }
  const panel = page => page.locator('.product-work-detail');
  const control = (page, name) => page.getByRole('region', {name: 'Reference controls', exact: true}).getByRole('button', {name, exact: true});
  const sent = page => page.evaluate(() => window.productWorkReference.sent.map(raw => JSON.parse(raw)));
  async function accepted(page, count) { await page.waitForFunction(count => window.productWorkReference.acceptedCallbacks === count, count); }
  async function choose(page, label, current, value) {
    await page.getByRole('button', {name: label + ': ' + current, exact: true}).click();
    const search = page.getByRole('combobox', {name: 'Search ' + label.toLowerCase(), exact: true});
    if (await search.count()) { await search.fill(value); await search.press('Enter'); }
    else await page.getByRole('menuitemradio', {name: value, exact: true}).click();
  }
  async function layout(page, name) {
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    await page.screenshot({path: path.join(output, name + '.png'), fullPage: true});
  }
  await check('composer-keeps-title-defaults-and-owner-worker-eligibility-at-narrow-width', async page => {
    await control(page, 'New work').click(); const dialog = page.getByRole('dialog', {name: 'Create work item', exact: true});
    const title = dialog.getByLabel('Title', {exact: true}); await title.waitFor(); await focused(title); await title.fill('New task');
    await dialog.getByRole('button', {name: 'Owner: Unassigned', exact: true}).click();
    const search = page.getByRole('combobox', {name: 'Search owner', exact: true}); await search.fill('Writer');
    assert.equal(await page.getByRole('option').count(), 0); await search.press('Escape');
    await choose(page, 'Working on it', 'Unassigned', 'Writer agent');
    await page.setViewportSize({width: 320, height: 900}); await layout(page, 'composer-320');
    await dialog.getByRole('button', {name: 'Create work item', exact: true}).click(); await accepted(page, 1);
    const [command] = await sent(page); assert.equal(command.operation, 'work.create');
    assert.deepEqual(command.expected, {work_revision: '0', execution_contract_revision: '0'});
    assert.equal(command.payload.title, 'New task'); assert.equal(command.payload.type, 'task'); assert.equal(command.payload.status, 'todo');
    assert.equal(command.payload.priority, 'none'); assert.equal(command.payload.owner_principal_id, ''); assert.ok(command.payload.worker_principal_id);
    assert.deepEqual(command.payload.required_outcomes, {});
  });
  await check('independent-comment-property-and-purpose-saves-retain-other-section-drafts', async page => {
    const work = panel(page); await work.getByRole('button', {name: 'Edit purpose', exact: true}).click();
    await work.getByLabel('Purpose', {exact: true}).fill('Local purpose  \n');
    await work.getByLabel('Comment', {exact: true}).fill('Independent comment'); await work.getByRole('button', {name: 'Post comment', exact: true}).click(); await accepted(page, 1);
    assert.equal(await work.getByLabel('Purpose', {exact: true}).inputValue(), 'Local purpose  \n');
    await work.getByRole('button', {name: 'Save purpose', exact: true}).click(); await accepted(page, 2);
    await choose(page, 'Priority', 'No priority', 'High'); await work.getByRole('button', {name: 'Save properties', exact: true}).click(); await accepted(page, 3);
    const commands = await sent(page); assert.deepEqual(commands.map(command => command.operation), ['work.comment', 'work.update-contract', 'work.update-properties']);
    assert.deepEqual(commands.map(command => command.expected), [{discussion_sequence: '1'}, {execution_contract_revision: '1'}, {work_revision: '1'}]);
  });
  await check('unknown-save-retries-identical-bytes-and-keeps-draft-until-readback', async page => {
    const work = panel(page); await control(page, 'Lose next response').click(); await work.getByLabel('Comment', {exact: true}).fill('Question  \n');
    await work.getByRole('button', {name: 'Post comment', exact: true}).click(); const retry = work.getByRole('button', {name: 'Check same request', exact: true}); await retry.waitFor();
    assert.equal(await work.getByLabel('Comment', {exact: true}).inputValue(), 'Question  \n'); assert.equal(await work.getByLabel('Comment', {exact: true}).isDisabled(), true);
    await retry.click(); await accepted(page, 1); assert.equal(await work.getByLabel('Comment', {exact: true}).inputValue(), '');
    const raw = await page.evaluate(() => window.productWorkReference.sent); assert.equal(raw.length, 2); assert.equal(raw[0], raw[1]);
    assert.equal(await work.locator('.product-work-conversation article').count(), 2);
  });
  await check('authority-conflict-needs-refreshed-explicit-adoption-with-unchanged-work-revision', async page => {
    const work = panel(page); await choose(page, 'Priority', 'No priority', 'High'); await control(page, 'Change access before response').click();
    await work.getByRole('button', {name: 'Save properties', exact: true}).click(); const refresh = work.getByRole('button', {name: 'Refresh current work', exact: true}); await refresh.waitFor();
    assert.equal(await work.getByRole('button', {name: 'Save properties', exact: true}).isDisabled(), true);
    assert.equal(await work.getByRole('button', {name: 'Keep draft using current version', exact: true}).isDisabled(), true);
    await refresh.click(); const adopt = work.getByRole('button', {name: 'Keep draft using current version', exact: true}); await adopt.waitFor();
    await work.getByText('Current saved properties', {exact: true}).click(); await adopt.click();
    await work.getByRole('button', {name: 'Save properties', exact: true}).click(); await accepted(page, 1);
    const commands = await sent(page); assert.equal(commands.length, 2); assert.equal(commands[0].authority_epoch, '1'); assert.equal(commands[1].authority_epoch, '2');
    assert.equal(commands[0].expected.work_revision, commands[1].expected.work_revision); assert.notEqual(commands[0].request_id, commands[1].request_id);
  });
  await check('late-a-to-b-to-a-response-cannot-publish-or-reconcile-a-new-view', async page => {
    await control(page, 'Hold next response').click(); await panel(page).getByLabel('Comment', {exact: true}).fill('Held original comment');
    await panel(page).getByRole('button', {name: 'Post comment', exact: true}).click(); await page.waitForFunction(() => window.productWorkReference.holding);
    await control(page, 'Switch to other work').click(); await panel(page).getByRole('heading', {name: 'Other work', exact: true}).waitFor();
    await control(page, 'Return to original work').click(); await panel(page).getByRole('heading', {name: 'Guide', exact: true}).waitFor();
    await panel(page).getByRole('button', {name: 'Check same request', exact: true}).waitFor();
    await control(page, 'Release held response').click(); await page.waitForFunction(() => !window.productWorkReference.holding);
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(await page.evaluate(() => window.productWorkReference.acceptedCallbacks), 0);
    assert.equal(await panel(page).getByLabel('Comment', {exact: true}).inputValue(), 'Held original comment');
    await panel(page).getByRole('button', {name: 'Check same request', exact: true}).click(); await accepted(page, 1);
    const bytes = await page.evaluate(() => window.productWorkReference.sent); assert.equal(bytes.length, 2); assert.equal(bytes[0], bytes[1]);
  });
  await check('required-doc-pins-advance-explicitly-and-duplicate-targets-are-not-offered', async page => {
    const work = panel(page); await work.getByRole('button', {name: 'Edit purpose', exact: true}).click();
    await choose(page, 'Shared Doc', 'Choose…', 'Shared guide'); await control(page, 'Advance Doc choice').click();
    assert.equal(await work.getByRole('button', {name: 'Add required Doc', exact: true}).isDisabled(), true);
    await work.getByRole('button', {name: /^Shared Doc:/u}).click(); const search = page.getByRole('combobox', {name: 'Search shared doc', exact: true}); await search.fill('Shared guide'); await search.press('Enter');
    await work.getByRole('button', {name: 'Add required Doc', exact: true}).click();
    await work.getByRole('button', {name: /^Shared Doc:/u}).click(); assert.equal(await page.getByRole('option').count(), 0); await page.keyboard.press('Escape');
    await work.getByRole('button', {name: 'Save purpose', exact: true}).click(); await accepted(page, 1);
    const [command] = await sent(page), outcomes = Object.values(command.payload.required_outcomes); assert.equal(outcomes.length, 1); assert.equal(outcomes[0].expected_revision, '2'); assert.equal(outcomes[0].base_markdown_sha256, 'd'.repeat(64));
    assert.equal(await work.getByLabel('Completion note', {exact: true}).count(), 0);
    await control(page, 'Outputs accepted').click(); await work.getByRole('button', {name: 'Complete with accepted outputs', exact: true}).click(); await accepted(page, 2);
    assert.deepEqual((await sent(page))[1].payload, {basis: 'accepted-outcomes', note: ''});
    await work.getByText('Reopen this work with an unfinished status before changing its purpose or required outputs.', {exact: true}).waitFor();
    assert.equal(await work.getByRole('button', {name: 'Edit purpose', exact: true}).isDisabled(), true);
  });
  await check('legacy-blocked-and-assignment-need-separate-explicit-resolution', async page => {
    await control(page, 'Load legacy work').click(); const work = panel(page);
    await choose(page, 'Resolved status', 'Choose a status', 'In progress'); await work.getByLabel('Blocking reason', {exact: true}).fill('Waiting for review');
    await work.getByRole('button', {name: 'Resolve blocked status', exact: true}).click(); await accepted(page, 1);
    const section = work.locator('section').filter({has: work.getByRole('heading', {name: 'Resolve older assignment', exact: true})});
    await section.getByRole('button', {name: 'Owner: Unassigned', exact: true}).click(); await page.getByRole('combobox', {name: 'Search owner', exact: true}).fill('Alice'); await page.keyboard.press('Enter');
    await section.getByRole('button', {name: 'Working on it: Unassigned', exact: true}).click(); await page.getByRole('combobox', {name: 'Search working on it', exact: true}).fill('Writer agent'); await page.keyboard.press('Enter');
    await section.getByRole('button', {name: 'Resolve assignment', exact: true}).click(); await accepted(page, 2);
    assert.deepEqual((await sent(page)).map(command => command.operation), ['work.resolve-legacy-blocked', 'work.resolve-legacy-assignee']);
    await page.setViewportSize({width: 320, height: 900}); await layout(page, 'detail-320');
  });
  await check('human-note-completion-and-revoked-remount-preserve-only-current-session', async page => {
    const work = panel(page); await work.getByLabel('Comment', {exact: true}).fill('Retained on temporary access loss');
    await control(page, 'Revoke access').click(); assert.equal(await panel(page).count(), 0); await control(page, 'Restore access').click();
    assert.equal(await panel(page).getByLabel('Comment', {exact: true}).inputValue(), 'Retained on temporary access loss');
    await work.getByLabel('Completion note', {exact: true}).fill('Outcome reviewed by a person'); await work.getByRole('button', {name: 'Complete with note', exact: true}).click(); await accepted(page, 1);
    assert.deepEqual((await sent(page))[0].payload, {basis: 'human-note', note: 'Outcome reviewed by a person'});
    assert.equal(await work.getByLabel('Comment', {exact: true}).inputValue(), 'Retained on temporary access loss');
    await control(page, 'Change session').click(); assert.equal(await panel(page).count(), 0);
    await control(page, 'Unsupported Home').click(); assert.equal(await sent(page).then(rows => rows.length), 1);
  });
  assert.equal(report.checks.length, requestedCases.length || 8, 'Every requested reference journey executed');
  if (requestedCases.length) assert.deepEqual(report.checks.map(check => check.name).sort(), [...requestedCases].sort(), 'Exact requested reference case set');
  report.status = 'pass';
} catch (error) {
  report.status = 'fail'; report.error = String(error); process.exitCode = 1;
} finally {
  report.inputs_after = await inputs();
  if (JSON.stringify(report.inputs_before) !== JSON.stringify(report.inputs_after)) {
    report.status = 'fail'; report.error = 'Reference inputs changed during execution'; process.exitCode = 1;
  }
  if (browser) await browser.close();
  if (server?.listening) await new Promise(resolve => server.close(resolve));
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({status: report.status, checks: report.checks.length, report: path.join(output, 'report.json'), error: report.error}));
}

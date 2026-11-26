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
const output = await mkdtemp(path.join(runtime, 'doc-change-review-reference-'));
const files = ['src/docChangeReviewState.tsx','src/docChangeReview.tsx','src/docChangeReview.css','src/docChangeProtocol.ts','src/productProtocol.ts','src/productWire.ts','src/protocol.ts','src/primitives.tsx','src/Icon.tsx','src/controls.css','src/style.css','src/Markdown.tsx','src/markdown.css','src/AcceptedTime.tsx','tests/doc-change-review-fixture.ts','tests/doc-change-review-reference.tsx','tests/doc-change-review-reference.css','tests/doc-change-review-reference.mjs','package-lock.json'];
async function inputs() {
  return Object.fromEntries(await Promise.all(files.map(async file => {
    const raw = await readFile(path.join(root, file));
    assert.ok(raw.length <= 1024 * 1024, 'Bounded reference input');
    return [file, createHash('sha256').update(raw).digest('hex')];
  })));
}
const report = {classification: 'real-browser-synthetic-doc-change-review-reference', qualifies_phase: false,
  node: process.version, status: 'running', checks: [], requested_cases: requestedCases,
  execution_scope: requestedCases.length ? 'selected-cases' : 'all-declared-cases', inputs_before: await inputs()};
let browser;
let server;
try {
  await build({absWorkingDir: root, entryPoints: ['tests/doc-change-review-reference.tsx'], outfile: path.join(output, 'reference.js'),
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
      await page.getByRole('heading', {name: 'Reserved Doc review interaction reference', exact: true}).waitFor();
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
  const panel = page => page.locator('.doc-change-review');
  const control = (page, name) => page.getByRole('region', {name: 'Reference controls', exact: true}).getByRole('button', {name, exact: true});
  async function ready(page) { await panel(page).getByRole('button', {name: 'Approve output', exact: true}).waitFor(); await page.waitForFunction(() => [...document.querySelectorAll('.doc-change-review button')].some(button => button.textContent === 'Approve output' && !button.disabled)); }
  async function choose(page, action, note = '') { await ready(page); await panel(page).getByRole('button', {name: action, exact: true}).click(); await panel(page).getByLabel('Decision note', {exact: true}).fill(note); }
  async function accepted(page, count) { await page.waitForFunction(count => window.docChangeReference.acceptedCallbacks === count, count); }
  async function layout(page, name) { assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true); await page.screenshot({path: path.join(output, name + '.png'), fullPage: true}); }
  await check('after-is-default-exact-source-diff-and-toolbar-focus-survive-narrow-layout', async page => {
    await ready(page); const review = panel(page), after = review.getByRole('button', {name: 'After', exact: true});
    assert.equal(await after.getAttribute('aria-pressed'), 'true');
    await review.getByRole('button', {name: 'Source', exact: true}).click(); assert.equal(await review.getByLabel('Proposed Markdown source', {exact: true}).textContent(), '# Guide\n\nClearer text.  \n');
    await focused(review.getByRole('button', {name: 'Source', exact: true}));
    await review.getByRole('button', {name: 'Changes', exact: true}).click(); await review.getByRole('region', {name: 'Exact Markdown changes', exact: true}).waitFor();
    assert.ok(await review.locator('[data-kind="removed"]').count() > 0); assert.ok(await review.locator('[data-kind="added"]').count() > 0);
    await layout(page, 'review-1440'); await page.setViewportSize({width: 320, height: 900}); await layout(page, 'review-320');
    await focused(review.getByRole('button', {name: 'Changes', exact: true}));
  });
  await check('unavailable-original-never-becomes-empty-diff-or-invented-decision-restriction', async page => {
    await ready(page); await control(page, 'Before unavailable').click();
    await panel(page).getByRole('button', {name: 'Changes', exact: true}).click(); await panel(page).getByText('Original version unavailable. Read the proposed Doc in After or Source; no comparison is shown.', {exact: true}).waitFor();
    assert.equal(await panel(page).getByRole('region', {name: 'Exact Markdown changes', exact: true}).count(), 0);
    assert.equal(await panel(page).getByRole('button', {name: 'Approve output', exact: true}).isDisabled(), false);
    await control(page, 'Large comparison').click(); await panel(page).getByText('Line comparison is unavailable for this size. Read the exact Before and After versions or proposed Source.', {exact: true}).waitFor();
    await panel(page).getByRole('button', {name: 'Source', exact: true}).click(); assert.equal(await panel(page).getByLabel('Proposed Markdown source', {exact: true}).textContent(), 'Proposed line\n'.repeat(210));
  });
  await check('eligibility-and-exact-body-are-required-and-prior-output-stays-read-only', async page => {
    await ready(page); await control(page, 'Remove eligibility').click();
    assert.equal(await panel(page).getByRole('button', {name: 'Approve output', exact: true}).isDisabled(), true);
    await control(page, 'Restore eligibility').click(); await ready(page); await control(page, 'Corrupt proposed content').click();
    await panel(page).getByText('The exact proposed Doc is unavailable. Refresh before making a decision.', {exact: true}).waitFor();
    assert.equal(await panel(page).getByRole('button', {name: 'Approve output', exact: true}).isDisabled(), true);
    await control(page, 'View prior output').click(); await panel(page).getByText('This is an older immutable output. Open the current output to make a decision.', {exact: true}).waitFor();
    assert.equal(await panel(page).getByRole('button', {name: 'Accept into Doc', exact: true}).count(), 0); assert.equal(await page.evaluate(() => window.docChangeReference.sent.length), 0);
  });
  await check('unknown-decision-retries-original-bytes-and-keeps-independent-notes', async page => {
    await choose(page, 'Request changes', 'Independent revision question'); await choose(page, 'Approve output', 'Exact review note  \n');
    await control(page, 'Lose next response').click(); await panel(page).getByRole('button', {name: 'Confirm approve output', exact: true}).click();
    const retry = panel(page).getByRole('button', {name: 'Check same request', exact: true}); await retry.waitFor();
    assert.equal(await panel(page).getByLabel('Decision note', {exact: true}).inputValue(), 'Exact review note  \n'); assert.equal(await panel(page).getByLabel('Decision note', {exact: true}).isDisabled(), true);
    await retry.click(); await accepted(page, 1); await ready(page); await panel(page).getByRole('button', {name: 'Request changes', exact: true}).click();
    assert.equal(await panel(page).getByLabel('Decision note', {exact: true}).inputValue(), 'Independent revision question');
    const sent = await page.evaluate(() => window.docChangeReference.sent); assert.equal(sent.length, 2); assert.equal(sent[0], sent[1]);
  });
  await check('epoch-conflict-requires-fresh-comparison-and-explicit-note-adoption', async page => {
    await choose(page, 'Request changes', 'Keep original pinned request'); await control(page, 'Change access before response').click();
    await panel(page).getByRole('button', {name: 'Confirm request changes', exact: true}).click();
    const refresh = panel(page).getByRole('button', {name: 'Refresh current output', exact: true}); await refresh.waitFor();
    const adopt = panel(page).getByRole('button', {name: 'Use current output for this decision', exact: true}); assert.equal(await adopt.isDisabled(), true);
    assert.equal(await panel(page).getByRole('button', {name: 'Confirm request changes', exact: true}).isDisabled(), true);
    await refresh.click(); await page.waitForFunction(() => [...document.querySelectorAll('.doc-change-review button')].some(button => button.textContent === 'Use current output for this decision' && !button.disabled));
    await adopt.click(); assert.equal(await panel(page).getByLabel('Decision note', {exact: true}).inputValue(), 'Keep original pinned request');
    await panel(page).getByRole('button', {name: 'Confirm request changes', exact: true}).click(); await accepted(page, 1);
    const sent = await page.evaluate(() => window.docChangeReference.sent.map(raw => JSON.parse(raw))); assert.equal(sent.length, 2); assert.equal(sent[0].authority_epoch, '1'); assert.equal(sent[1].authority_epoch, '2');
    assert.equal(sent[0].expected_revision, sent[1].expected_revision); assert.notEqual(sent[0].request_id, sent[1].request_id);
  });
  await check('late-a-to-b-to-a-decision-cannot-publish-into-returned-view', async page => {
    await choose(page, 'Approve output', 'Held note'); await control(page, 'Hold next response').click(); await panel(page).getByRole('button', {name: 'Confirm approve output', exact: true}).click();
    await page.waitForFunction(() => window.docChangeReference.holding); await control(page, 'Switch change').click(); await panel(page).getByRole('heading', {name: 'Other proposed Doc', exact: true}).waitFor();
    await control(page, 'Return original change').click(); await panel(page).getByRole('button', {name: 'Check same request', exact: true}).waitFor();
    await control(page, 'Release held response').click(); await page.waitForFunction(() => !window.docChangeReference.holding);
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))); assert.equal(await page.evaluate(() => window.docChangeReference.acceptedCallbacks), 0);
    assert.equal(await panel(page).getByLabel('Decision note', {exact: true}).inputValue(), 'Held note');
    await panel(page).getByRole('button', {name: 'Check same request', exact: true}).click(); await accepted(page, 1);
    const sent = await page.evaluate(() => window.docChangeReference.sent); assert.equal(sent.length, 2); assert.equal(sent[0], sent[1]);
  });
  await check('denied-decision-clears-content-through-remount-until-fresh-authorized-read', async page => {
    await choose(page, 'Request changes', 'Keep confidential decision note'); await control(page, 'Deny next decision').click();
    await panel(page).getByRole('button', {name: 'Confirm request changes', exact: true}).click(); await page.waitForFunction(() => window.docChangeReference.deniedCallbacks === 1);
    assert.equal(await panel(page).count(), 0); await control(page, 'Close fixture').click(); await control(page, 'Reopen fixture').click(); assert.equal(await panel(page).count(), 0);
    await page.getByRole('button', {name: 'Refresh access', exact: true}).click(); await ready(page);
    assert.equal(await panel(page).getByLabel('Decision note', {exact: true}).inputValue(), 'Keep confidential decision note');
    await control(page, 'Change session').click(); assert.equal(await panel(page).count(), 0); assert.equal(await page.evaluate(() => window.docChangeReference.acceptedCallbacks), 0);
  });
  await check('quarantine-rejection-keeps-note-and-offline-and-list-keyboard-states-remain-explicit', async page => {
    await choose(page, 'Reject output', 'Explain the concern'); await control(page, 'Quarantine next decision').click();
    await panel(page).getByRole('button', {name: 'Confirm reject output', exact: true}).click(); await panel(page).getByText('Original producer access changed. This output cannot be accepted.', {exact: true}).waitFor();
    assert.equal(await panel(page).getByLabel('Decision note', {exact: true}).inputValue(), 'Explain the concern'); assert.equal(await page.evaluate(() => window.docChangeReference.acceptedCallbacks), 0);
    await panel(page).getByRole('button', {name: 'Refresh current output', exact: true}).click(); await panel(page).getByText('Current Change: Quarantined', {exact: true}).waitFor();
    await control(page, 'Offline').click(); assert.equal(await panel(page).getByRole('button', {name: 'Confirm reject output', exact: true}).isDisabled(), true);
    assert.equal(await page.getByRole('region', {name: 'Proposed Doc changes', exact: true}).locator('li button').isDisabled(), true);
    await page.reload(); await ready(page); const row = page.getByRole('region', {name: 'Proposed Doc changes', exact: true}).locator('li button'); await row.focus(); await row.press('Enter');
    await page.waitForFunction(() => window.docChangeReference.opened.length === 1); await control(page, 'Read only').click(); assert.equal(await panel(page).getByRole('button', {name: 'Approve output', exact: true}).isDisabled(), true);
    await control(page, 'Unsupported Home').click(); assert.equal(await panel(page).count(), 0);
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

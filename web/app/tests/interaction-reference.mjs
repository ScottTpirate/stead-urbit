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
const output = await mkdtemp(path.join(runtime, 'interaction-reference-'));
const files = ['src/primitives.tsx', 'src/Icon.tsx', 'src/controls.css', 'src/style.css', 'src/work.css', 'src/DocumentBody.tsx', 'src/Markdown.tsx',
  'src/markdown.css', 'src/ResourceLink.tsx', 'src/documentFormatting.ts', 'tests/interaction-reference.tsx',
  'tests/interaction-reference.css', 'tests/interaction-reference.mjs', 'package-lock.json'];
async function inputs() {
  return Object.fromEntries(await Promise.all(files.map(async file => {
    const raw = await readFile(path.join(root, file));
    assert.ok(raw.length <= 1024 * 1024, 'Bounded reference input');
    return [file, createHash('sha256').update(raw).digest('hex')];
  })));
}
const report = {classification: 'real-browser-synthetic-interaction-reference', qualifies_phase: false,
  node: process.version, status: 'running', checks: [], requested_cases: requestedCases,
  execution_scope: requestedCases.length ? 'selected-cases' : 'all-declared-cases', inputs_before: await inputs()};
let browser;
let server;
try {
  await build({absWorkingDir: root, entryPoints: ['tests/interaction-reference.tsx'], outfile: path.join(output, 'reference.js'),
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
      await page.getByRole('heading', {name: 'Work, Docs and review', exact: true}).waitFor();
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
  await check('menu-navigation-skips-disabled-items-and-restores-focus', async page => {
    const trigger = page.getByRole('button', {name: 'Work actions', exact: true});
    await trigger.focus(); await trigger.press('ArrowDown');
    const menu = page.getByRole('menu', {name: 'Work actions', exact: true});
    await menu.waitFor(); await focused(menu.getByRole('menuitem', {name: 'Copy link', exact: true}));
    await page.keyboard.press('ArrowDown'); await focused(menu.getByRole('menuitem', {name: 'Open details', exact: true}));
    await page.keyboard.press('End'); await focused(menu.getByRole('menuitem', {name: 'Delete…', exact: true}));
    await page.keyboard.press('Home'); await focused(menu.getByRole('menuitem', {name: 'Copy link', exact: true}));
    await page.keyboard.press('o'); await focused(menu.getByRole('menuitem', {name: 'Open details', exact: true}));
    await page.keyboard.press('Enter'); await page.getByText('Open details selected', {exact: true}).waitFor();
    await menu.waitFor({state: 'hidden'}); await focused(trigger);
    await trigger.press('ArrowUp'); await menu.waitFor(); await focused(menu.getByRole('menuitem', {name: 'Delete…', exact: true}));
    await page.keyboard.press('Escape'); await menu.waitFor({state: 'hidden'}); await focused(trigger);
    await trigger.click(); await menu.waitFor(); await page.keyboard.press('Tab'); await menu.waitFor({state: 'hidden'});
    assert.equal(await trigger.evaluate(element => element === document.activeElement), false, 'Tab leaves the menu in document order');
  });
  await check('searchable-people-picker-selects-on-enter-and-keeps-eligibility-distinct', async page => {
    const owner = page.getByRole('button', {name: 'Owner: Unassigned', exact: true});
    await owner.click();
    const search = page.getByRole('combobox', {name: 'Search owner', exact: true});
    await search.waitFor(); await focused(search);
    await search.fill('maya');
    const option = page.getByRole('option', {name: /Maya Chen/u}); await option.waitFor();
    assert.equal(await search.getAttribute('aria-activedescendant'), await option.getAttribute('id'));
    await search.press('Enter');
    const selected = page.getByRole('button', {name: 'Owner: Maya Chen', exact: true}); await selected.waitFor(); await focused(selected);
    await selected.click(); await search.fill('Docs editor');
    await page.getByText('No matching options', {exact: true}).waitFor();
    assert.equal(await page.getByRole('option').count(), 0, 'Agent is not offered as accountable human owner');
    await search.press('Escape'); await focused(selected);
    await page.getByRole('button', {name: 'Working on it: Docs editor', exact: true}).click();
    const worker = page.getByRole('combobox', {name: 'Search working on it', exact: true});
    await worker.fill('Sam'); await worker.press('Enter');
    await page.getByRole('button', {name: 'Working on it: Sam Rivera', exact: true}).waitFor();
    await selected.click(); await search.fill('unavailable');
    assert.equal(await page.getByRole('option', {name: 'Unavailable member', exact: true}).getAttribute('aria-disabled'), 'true');
    await search.press('Enter'); assert.equal(await search.isVisible(), true, 'Disabled option cannot be chosen');
    await search.press('Escape'); await focused(selected);
  });
  await check('dialog-traps-focus-preserves-draft-and-supports-nested-picker', async page => {
    const trigger = page.getByRole('button', {name: 'Edit reference work', exact: true});
    await trigger.click();
    const dialog = page.getByRole('dialog', {name: 'Edit reference work', exact: true});
    await dialog.waitFor(); const title = dialog.getByRole('textbox', {name: 'Title', exact: true}); await focused(title);
    await title.fill('Draft retained after Escape');
    await dialog.getByRole('button', {name: 'Dialog status: To do', exact: true}).click();
    const menu = page.getByRole('menu', {name: 'Dialog status: To do', exact: true}); await menu.waitFor();
    assert.equal(await menu.evaluate(element => !!element.closest('dialog[open]')), true, 'Nested menu remains in modal top layer');
    await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
    await dialog.getByRole('button', {name: 'Dialog status: In progress', exact: true}).waitFor();
    const update = dialog.getByRole('button', {name: 'Update preview', exact: true});
    await update.focus(); await page.keyboard.press('Tab');
    await focused(dialog.getByRole('button', {name: 'Close Edit reference work', exact: true}));
    await page.keyboard.press('Shift+Tab'); await focused(update);
    await page.keyboard.press('Escape'); await dialog.waitFor({state: 'hidden'}); await focused(trigger);
    await trigger.click(); await dialog.waitFor(); assert.equal(await title.inputValue(), 'Draft retained after Escape');
    await update.click(); await dialog.waitFor({state: 'hidden'}); await focused(trigger);
    await page.locator('.reference-work-detail').getByRole('heading', {name: 'Draft retained after Escape', exact: true}).waitFor();
  });
  await check('loading-empty-error-and-read-only-states-remain-explicit', async page => {
    for (const [label, expected] of [['Loading members', 'Loading options…'], ['Empty members', 'No eligible options'], ['Unavailable members', 'Project members could not be loaded.']]) {
      const trigger = page.getByRole('button', {name: `${label}: Choose…`, exact: true});
      await trigger.click(); await page.getByText(expected, {exact: true}).waitFor();
      await page.keyboard.press('Escape'); await focused(trigger);
    }
    await page.getByRole('checkbox', {name: 'Read-only reference', exact: true}).check();
    assert.equal(await page.getByRole('button', {name: 'Edit reference work', exact: true}).isDisabled(), true);
    assert.equal(await page.getByRole('button', {name: 'Owner: Unassigned', exact: true}).isDisabled(), true);
    assert.equal(await page.getByRole('button', {name: 'Status: To do', exact: true}).isDisabled(), true);
    await page.getByRole('button', {name: 'Work actions', exact: true}).click();
    assert.equal(await page.getByRole('menuitem', {name: 'Delete…', exact: true}).isDisabled(), true);
    await page.keyboard.press('Escape');
  });
  await check('desktop-narrow-crowded-and-empty-reference-layouts', async page => {
    for (const variant of ['Normal', 'Crowded', 'Empty']) {
      const trigger = page.getByRole('button', {name: /^Reference data:/u});
      await trigger.click(); await page.getByRole('menuitemradio', {name: variant, exact: true}).click();
      for (const width of [1440, 390, 320]) {
        await page.setViewportSize({width, height: 1000});
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${variant} at ${width}px has no horizontal page overflow`);
        await page.screenshot({path: path.join(output, `${variant.toLowerCase()}-${width}.png`), fullPage: true});
      }
    }
    await page.getByRole('button', {name: 'Create reference work', exact: true}).click();
    const dialog = page.getByRole('dialog', {name: 'Edit reference work', exact: true}); await dialog.waitFor();
    assert.equal(await dialog.evaluate(element => element.getBoundingClientRect().width <= innerWidth), true);
    await page.screenshot({path: path.join(output, 'dialog-320.png'), fullPage: true});
  });
  await check('production-work-widths-dense-rows-and-two-times-zoom-reflow', async page => {
    const view = page.locator('.work-view');
    const detail = view.locator('.work-detail');
    assert.equal(Math.round(await detail.evaluate(element => element.getBoundingClientRect().width)), 560, 'Ample-width preview is 560px');
    async function layout(name) {
      await page.getByRole('button', {name: /^Work layout:/u}).click();
      await page.getByRole('menuitemradio', {name, exact: true}).click();
    }
    await layout('List');
    for (const height of await page.locator('.work-row').evaluateAll(rows => rows.map(row => row.getBoundingClientRect().height))) {
      assert.ok(height >= 44 && height <= 48, `Desktop work row is ${height}px`);
    }
    await layout('Create');
    assert.equal(Math.round(await detail.evaluate(element => element.getBoundingClientRect().width)), 680, 'Create surface is 680px');
    await layout('Full detail');
    assert.equal(Math.round(await detail.evaluate(element => element.getBoundingClientRect().width)), 800, 'Full detail readable surface is 800px');
    await layout('Preview');
    await page.setViewportSize({width: 1000, height: 1000});
    assert.equal(await view.locator('.view-list').isVisible(), false, 'Narrow detail uses a single primary surface');
    await page.setViewportSize({width: 1440, height: 1000});
    await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
    assert.equal(await view.locator('.view-list').isVisible(), false, 'Two-times CSS zoom reflows using available container width');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Zoom causes no horizontal page overflow');
    await page.screenshot({path: path.join(output, 'zoom-200-percent.png'), fullPage: true});
  });
  await check('document-read-edit-preview-preserves-local-draft', async page => {
    const doc = page.getByRole('region', {name: 'Welcome to the project', exact: true});
    const modes = doc.getByRole('group', {name: 'Document view', exact: true});
    await doc.getByRole('heading', {name: 'Your first day', exact: true}).waitFor();
    assert.equal(await doc.getByRole('checkbox').count(), 2, 'Markdown retains both task states');
    assert.equal(await doc.getByRole('checkbox', {name: 'Completed task', exact: true}).isChecked(), true);
    assert.equal(await doc.getByRole('checkbox', {name: 'Incomplete task', exact: true}).isChecked(), false);
    for (const box of await doc.getByRole('checkbox').all()) {
      assert.equal(await box.isDisabled(), true, 'Reading a task list cannot mutate the source');
      const width = await box.evaluate(element => element.getBoundingClientRect().width);
      assert.ok(width >= 12 && width <= 20, `Task checkbox remains inline at ${width}px`);
    }
    assert.equal(await doc.getByRole('textbox').count(), 0, 'Existing document starts in reading mode');
    await modes.getByRole('button', {name: 'Edit', exact: true}).click();
    const source = doc.getByRole('textbox', {name: 'Markdown source', exact: true});
    const paragraph = 'Intro paragraph.\nSecond paragraph.\nThird paragraph.\n\nKeep trailing  \n';
    await source.fill(paragraph);
    await source.evaluate(element => element.setSelectionRange(5, 5));
    await doc.getByRole('button', {name: 'Heading', exact: true}).click();
    assert.equal(await source.inputValue(), '# ' + paragraph, 'Heading prefixes the complete current line from a midline caret');
    await source.evaluate(element => {
      element.setSelectionRange(element.value.indexOf('Second') + 3, element.value.indexOf('Third') + 4);
    });
    await doc.getByRole('button', {name: 'List', exact: true}).click();
    const formatted = '# Intro paragraph.\n- Second paragraph.\n- Third paragraph.\n\nKeep trailing  \n';
    assert.equal(await source.inputValue(), formatted, 'List prefixes each selected line and preserves outside bytes');
    await modes.getByRole('button', {name: 'Preview', exact: true}).click();
    await doc.getByRole('heading', {name: 'Intro paragraph.', exact: true}).waitFor();
    assert.equal(await doc.getByRole('listitem').count(), 2, 'Multiline formatting creates two readable list items');
    await modes.getByRole('button', {name: 'Source', exact: true}).click();
    assert.equal(await source.inputValue(), formatted);
    await source.fill('## Local draft\n\nThis preview stays in this reference.');
    await modes.getByRole('button', {name: 'Preview', exact: true}).click();
    await doc.getByRole('heading', {name: 'Local draft', exact: true}).waitFor();
    await modes.getByRole('button', {name: 'Source', exact: true}).click();
    assert.equal(await source.inputValue(), '## Local draft\n\nThis preview stays in this reference.');
    await page.getByRole('checkbox', {name: 'Read-only reference', exact: true}).check();
    assert.equal(await source.getAttribute('readonly'), '', 'Read-only source cannot be edited');
    assert.equal(await modes.getByRole('button', {name: 'Edit', exact: true}).count(), 0);
  });
  await check('light-dark-system-theme-text-and-focus-contrast', async page => {
    for (const theme of ['light', 'dark', 'system']) {
      await page.emulateMedia({colorScheme: theme === 'light' ? 'light' : 'dark', reducedMotion: 'reduce'});
      await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
      const ratios = await page.evaluate(() => {
        const style = getComputedStyle(document.documentElement);
        const luminance = name => {
          const hex = style.getPropertyValue(name).trim().slice(1);
          const linear = [0, 2, 4].map(offset => parseInt(hex.slice(offset, offset + 2), 16) / 255)
            .map(channel => channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4);
          return linear[0] * .2126 + linear[1] * .7152 + linear[2] * .0722;
        };
        return Object.fromEntries(['--ink', '--muted', '--focus', '--danger', '--success'].map(name => {
          const first = luminance(name), second = luminance('--paper');
          return [name, (Math.max(first, second) + .05) / (Math.min(first, second) + .05)];
        }));
      });
      for (const [name, ratio] of Object.entries(ratios)) assert.ok(ratio >= (name === '--focus' ? 3 : 4.5), `${theme} ${name} contrast ${ratio}`);
      report.theme_contrast ??= {}; report.theme_contrast[theme] = ratios;
      await page.screenshot({path: path.join(output, `theme-${theme}.png`), fullPage: true});
    }
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

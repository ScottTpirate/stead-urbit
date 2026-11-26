// The shipped React app talks only to this synthetic Home inside the browser test.
import assert from 'node:assert/strict';
import {mkdir, readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {chromium} from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const [fixture] = (await build({absWorkingDir: root, entryPoints: ['tests/contextual-search-home.mjs'],
  bundle: true, write: false, platform: 'node', format: 'esm'})).outputFiles;
const {createHome, project, collection, item, id} =
  await import('data:text/javascript;base64,' + Buffer.from(fixture.contents).toString('base64'));
const base = 'https://stead.test';
const manifest = JSON.parse(await readFile(new URL('../dist/manifest.json', import.meta.url), 'utf8'));
const output = process.argv[2];
if (output) await mkdir(output, {recursive: true});
const browser = await chromium.launch({headless: true});
try {
  for (const width of [1440, 320]) {
    const context = await browser.newContext({viewport: {width, height: 900}, hasTouch: width === 320,
      serviceWorkers: 'block'});
    try {
      const home = createHome();
      home.state.role = 'reader';
      const event = (operation, resource_id, container_id, request_id) => ({kind: 'activity', operation, resource_id,
        container_id, request_id, principal_id: id(900), accepted_at_ms: '1790519400123', title: operation});
      home.state.activity = [event('work.comment', item, '', id(701)),
        event('document.publish', id(301), collection, id(702)), event('work.delete', id(109), '', id(703)),
        event('future.event', id(110), '', id(704))];
      const unexpected = [];
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin === base && route.request().method() === 'POST') return home.route(route);
        if (url.origin === base && route.request().method() === 'GET') {
          const name = url.pathname === '/stead/' ? 'index.html' : url.pathname.replace(/^\/stead\/assets\//u, '');
          if (Object.hasOwn(manifest.files, name) && /\.(?:html|js|css)$/u.test(name)) {
            const type = name.endsWith('.html') ? 'text/html' : name.endsWith('.css') ? 'text/css' : 'text/javascript';
            return route.fulfill({contentType: type, body: await readFile(new URL('../dist/' + name, import.meta.url))});
          }
          if (url.pathname === '/favicon.ico') return route.fulfill({status: 204});
        }
        unexpected.push(url.pathname);
        await route.abort();
      });
      const page = await context.newPage();
      page.setDefaultTimeout(8000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const activity = '#project/' + project + '/activity';
      await page.goto(base + '/stead/' + activity);
      const work = page.getByRole('link', {name: 'Open work item', exact: true});
      const doc = page.getByRole('link', {name: 'Open document', exact: true});
      await work.waitFor();
      assert.equal(await work.count(), 1);
      assert.equal(await doc.count(), 1);
      assert.equal(await page.locator('[data-activity-target]').count(), 2);
      const box = await work.boundingBox();
      assert.ok(box && box.width >= 44 && box.height >= (width === 320 ? 44 : 32));
      if (output) await page.screenshot({path: join(output, 'activity-' + width + '.png')});
      await work.focus();
      await work.press('Enter');
      await page.waitForURL('**/#work/' + project + '/' + item);
      await page.locator('#work-detail-title').waitFor();
      assert.ok(home.state.queries.some(q => q.kind === 'work' && q.project_id === project && q.resource_id === item));
      await page.goBack();
      await work.waitFor();
      await page.waitForFunction(() => document.activeElement?.getAttribute('data-activity-target')?.endsWith('701'));
      await doc.focus();
      await doc.press('Enter');
      await page.waitForURL('**/#doc/' + project + '/' + collection + '/' + id(301));
      await page.getByText('Exact saved context.', {exact: false}).first().waitFor();
      assert.ok(home.state.queries.some(q => q.kind === 'document' && q.container_id === collection && q.resource_id === id(301)));
      await page.goBack();
      await doc.waitFor();
      await page.waitForFunction(() => document.activeElement?.getAttribute('data-activity-target')?.endsWith('702'));
      home.state.documents = [];
      await doc.click();
      await page.getByText('This page is unavailable or you do not have access.', {exact: true}).waitFor();
      assert.equal(await page.getByText('Exact saved context.', {exact: false}).count(), 0);
      await page.goBack();
      await work.waitFor();
      await page.reload();
      await doc.waitFor();
      assert.equal(new URL(page.url()).hash, activity);
      assert.deepEqual(unexpected, []);
      assert.deepEqual(home.state.errors, []);
      assert.deepEqual(errors, []);
      assert.deepEqual(home.state.commands, []);
      console.log('PASS Activity at ' + width + 'px: scoped reads, keyboard return, unavailable target, refresh and zero mutations.');
    } finally { await context.close(); }
  }
} finally { await browser.close(); }

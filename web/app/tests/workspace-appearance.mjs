// Browser captures of the packaged Stead client with deterministic synthetic Home responses.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {chromium} from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = process.argv[2];
assert.ok(output, 'Supply a screenshot directory');
await mkdir(output, {recursive: true});
const [fixture] = (await build({absWorkingDir: root, entryPoints: ['tests/contextual-search-home.mjs'],
  bundle: true, write: false, platform: 'node', format: 'esm'})).outputFiles;
const {createHome, project, collection, id, work, doc} =
  await import('data:text/javascript;base64,' + Buffer.from(fixture.contents).toString('base64'));
const manifest = JSON.parse(await readFile(new URL('../dist/manifest.json', import.meta.url), 'utf8'));
const base = 'https://stead.test';
const projectRows = [
  ['Field station', 'FIELD', project, 'Make the field station ready for the first weekend of the season.'],
  ['Library', 'LIB', id(77), 'Publish the spring reading list.'],
  ['Wayfinding', 'WAY', id(78), 'Help visitors find their way around the grounds.'],
].map(([title, project_key, project_id, summary]) => ({kind: 'project', project_id, resource_id: project_id,
  title, project_key, summary, preset: 'general', resource_revision: '3', policy_revision: '1',
  authority_epoch: '1', role: 'maintainer'}));
const people = ['Mae Winters', 'Eli Park', 'Sam Reed'].map((display_name, n) => ({
  display_name, identity_ship: ['~bus', '~nec', '~sev'][n], principal_id: id(900 + n)}));
const tasks = [
  ['Confirm the opening crew', 'todo', 'high', 0],
  ['Print the field maps', 'todo', 'medium', 1],
  ['Write the visitor welcome note', 'todo', 'low', 2],
  ['Check trail markers', 'in_progress', 'high', 1],
  ['Set up the tool library', 'in_progress', 'medium', 2],
  ['Approve the rain plan', 'blocked', 'high', 0],
  ['Collect the gate keys', 'done', 'none', 2],
].map(([title, status, priority, who], n) => ({...work(101 + n), title, status, priority,
  description: 'Review the opening checklist and confirm the handoff with the team.',
  assignee_principal_id: people[who].principal_id, assignee_display_name: people[who].display_name}));
const guideTitle = 'Opening the field station';
const documents = [guideTitle, 'Trail map and meeting points', 'Wet weather plan'].map((title, n) => ({
  ...doc(301 + n), title, markdown: [
    '---', 'id: ' + id(301 + n), 'type: page', 'state: published', '---', '# ' + title, '',
    'Meet at the north gate at 8:30 on Saturday. The opening crew has an hour before the first visitors arrive.', '',
    '## Before visitors arrive', '',
    '- Unlock the tool shed and check the first-aid kit.', '- Place a field map at each entrance.',
    '- Walk the west trail and report any damaged markers.', '',
    '## Handoff', '', 'Leave the gate keys with the afternoon lead and record any follow-up in Work.', ''].join('\n')}));
const browser = await chromium.launch();
const source = (...args) => execFileSync('git', args, {cwd: root, encoding: 'utf8'}).trim();
const report = {classification: 'Packaged app in Chromium with synthetic project, people and documents',
  commit: source('rev-parse', 'HEAD'), appSourceTree: source('rev-parse', 'HEAD:web/app/src'), browser: browser.version(),
  screenshots: [], keyboardActivated: [], appearance: [], noWrites: true};
try {
  for (const [width, height] of [[1440, 960], [390, 844], [320, 800]]) {
    const context = await browser.newContext({viewport: {width, height}, colorScheme: 'light',
      hasTouch: width < 600, serviceWorkers: 'block', reducedMotion: 'reduce'});
    const home = createHome(), errors = [];
    home.state.documents = documents;
    await context.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin === base && request.method() === 'GET') {
        const name = url.pathname === '/stead/' ? 'index.html' : url.pathname.replace(/^\/stead\/assets\//u, '');
        if (Object.hasOwn(manifest.files, name) && /\.(?:html|js|css)$/u.test(name)) {
          const type = name.endsWith('.html') ? 'text/html' : name.endsWith('.css') ? 'text/css' : 'text/javascript';
          return route.fulfill({contentType: type, body: await readFile(new URL('../dist/' + name, import.meta.url))});
        }
        if (url.pathname === '/favicon.ico') return route.fulfill({status: 204});
      }
      if (url.origin === base && request.method() === 'POST') {
        const q = request.postDataJSON();
        if (url.pathname.endsWith('/command')) {
          errors.push('Unexpected write: ' + q.operation);
          return route.abort();
        }
        if (url.pathname === '/stead/api/capabilities') return route.fulfill({json: {
          protocol: 'stead.capabilities/3', profile: 'configured-team', commands: 'stead.command/3',
          queries: 'stead.query/3', updates: 'stead.updates/3', work_contract: 'stead.work-contract/1',
          workspace_queries: 'stead.workspace-queries/1'}});
        if (url.pathname === '/stead/api/query') {
          let rows;
          switch (q.kind) {
            case 'identity': rows = [{...people[0], binding_id: id(801), binding_revision: '1',
              session_audit_id: home.state.audit, can_create: 'yes'}]; break;
            case 'projects': rows = projectRows; break;
            case 'project': rows = projectRows.filter(r => r.project_id === q.project_id); break;
            case 'work': rows = tasks.filter(r => !q.resource_id || r.resource_id === q.resource_id); break;
            case 'assignees': rows = people; break;
            case 'containers': rows = [{kind: 'container', project_id: project, container_id: collection,
              resource_id: collection, title: 'Field guide', visibility: 'shared', resource_revision: '1'}]; break;
          }
          if (rows) return route.fulfill({json: {...q, protocol: 'stead.query-result/3', status: 'read',
            cursor: '', authority_epoch: '1', generation: home.state.generation,
            rows: Object.fromEntries(rows.map((r, i) => [String(i), r]))}});
        }
        return home.route(route);
      }
      errors.push('Unexpected request: ' + url.pathname);
      return route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(9000);
    page.on('pageerror', error => errors.push(error.message));
    const button = name => page.getByRole('button', {name, exact: true});
    async function activate(target, name) {
      await target.focus();
      assert.ok(await target.evaluate(el => el === document.activeElement));
      await page.keyboard.press('Enter');
      report.keyboardActivated.push({width, name});
    }
    async function capture(name) {
      // Keyboard navigation and the appearance selector can scroll the document.
      // A fresh navigation starts at the top, which is what these comparisons show.
      await page.evaluate(async () => { await document.fonts.ready; window.scrollTo(0, 0); });
      const extent = await page.evaluate(() => ({viewport: innerWidth, page: document.documentElement.scrollWidth}));
      assert.ok(extent.page <= extent.viewport + 1, JSON.stringify({width, name, ...extent}));
      const record = {view: name, width, height, documentWidth: extent.page};
      if (width !== 320) {
        record.file = name + '-' + width + '.png';
        await page.screenshot({path: join(output, record.file), animations: 'disabled'});
      }
      report.screenshots.push(record);
    }
    try {
      await page.goto(base + '/stead/#project/' + project + '/overview');
      await page.getByRole('heading', {name: projectRows[0].title, exact: true}).first().waitFor();
      await button('Open work').waitFor();
      const cover = page.locator('.project-cover');
      if (await cover.count()) {
        const paint = await cover.evaluate(el => {
          const style = getComputedStyle(el);
          return {image: style.backgroundImage, color: style.backgroundColor};
        });
        assert.match(paint.image, /gradient/u);
        assert.notEqual(paint.color, 'rgba(0, 0, 0, 0)');
      }
      await capture('overview');
      const nav = page.getByRole('navigation', {name: 'Project views'});
      await activate(nav.getByRole('button', {name: 'Work', exact: true}), 'Work');
      await button(tasks[0].title).waitFor();
      await capture('work');
      const appearance = page.getByRole('combobox', {name: 'Appearance', exact: true});
      if (width === 1440 && await appearance.count()) {
        assert.equal(await appearance.inputValue(), 'system');
        const surface = () => page.locator('body').evaluate(el => getComputedStyle(el).backgroundColor);
        const light = await surface();
        await appearance.selectOption('dark');
        await page.locator('html[data-theme="dark"]').waitFor();
        const dark = await surface();
        assert.notEqual(dark, light);
        await page.reload();
        await button(tasks[0].title).waitFor();
        assert.equal(await appearance.inputValue(), 'dark');
        assert.equal(await surface(), dark);
        await capture('work-dark');
        await appearance.selectOption('light');
        await page.locator('html[data-theme="light"]').waitFor();
        assert.equal(await surface(), light);
        await appearance.selectOption('system');
        await page.emulateMedia({colorScheme: 'dark'});
        assert.equal(await surface(), dark);
        await page.emulateMedia({colorScheme: 'light'});
        assert.equal(await surface(), light);
        report.appearance.push('System', 'Dark', 'Dark after reload', 'Light', 'System respects device changes');
      }
      await activate(nav.getByRole('button', {name: 'Docs', exact: true}), 'Docs');
      await page.getByRole('combobox', {name: 'Collection', exact: true}).selectOption(collection);
      await button(guideTitle).waitFor();
      await capture('docs');
      await activate(button(guideTitle), 'Open guide');
      await page.getByRole('heading', {name: 'Before visitors arrive', exact: true}).waitFor();
      await capture('guide');
      assert.deepEqual(errors.concat(home.state.errors), []);
      assert.equal(home.state.commands.length, 0);
    } catch (error) {
      await page.screenshot({path: join(output, 'failure-' + width + '.png')});
      console.error((await page.locator('body').innerText()).slice(0, 2800), errors, home.state.errors);
      throw error;
    } finally { await context.close(); }
  }
} finally {
  await writeFile(join(output, 'browser-report.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}

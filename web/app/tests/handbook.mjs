import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {chromium} from 'playwright';

const dist = new URL('../dist/', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('manifest.json', dist)));
const base = 'https://stead.test/stead/';
const account = n => '019939ba-4000-7000-8000-' + String(n).padStart(12, '0');
let member = 1;
const unexpected = [];
const browser = await chromium.launch();
const context = await browser.newContext({serviceWorkers:'block'});
try {
  await context.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url());
    if (url.origin !== new URL(base).origin) return route.abort();
    if (req.method() === 'GET') {
      const name = url.pathname === '/stead/' ? 'index.html' : url.pathname.slice('/stead/assets/'.length);
      if (url.pathname === '/favicon.ico') return route.fulfill({status:204});
      if (Object.hasOwn(manifest.files,name)) return route.fulfill({
        contentType: name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'text/javascript',
        body: await readFile(new URL(name, dist))});
    } else if (req.method() === 'POST') {
      const q = req.postDataJSON();
      if (url.pathname === '/stead/api/capabilities') return route.fulfill({json:{
        protocol:'stead.capabilities/3',profile:'configured-team',commands:'stead.command/3',queries:'stead.query/3',
        updates:'stead.updates/3',work_contract:'stead.work-contract/1',workspace_queries:'stead.workspace-queries/1'}});
      if (url.pathname === '/stead/auth/resume') return route.fulfill({json:{status:'authenticated',csrf:'c'.repeat(64)}});
      if (url.pathname === '/stead/api/query' && ['projects','identity'].includes(q.kind)) {
        const rows = q.kind==='projects'?{}:{'0':{principal_id:account(member),identity_ship:'~bus',display_name:'Member '+member,
          binding_id:account(50+member),binding_revision:'1',session_audit_id:String(member).repeat(64),can_create:'no'}};
        return route.fulfill({json:{protocol:'stead.query-result/3',status:'read',request_id:q.request_id,kind:q.kind,
          project_id:q.project_id,container_id:q.container_id,resource_id:q.resource_id,search:q.search,
          cursor:'',generation:'a'.repeat(64),authority_epoch:'1',rows}});
      }
    }
    unexpected.push(url.pathname);return route.abort();
  });
  const page=await context.newPage();
  page.setDefaultTimeout(8000);
  const rail=page.getByRole('navigation',{name:'Projects',exact:true}).getByRole('link',{name:'Stead Handbook'});
  const preferences=page.getByRole('navigation',{name:'Preferences'}).getByRole('link',{name:'Settings'});
  const visibility=page.getByLabel('Show Stead Handbook in Projects');
  await page.goto(base);await rail.click();
  await page.getByRole('heading',{name:'Start here'}).waitFor();
  await page.getByRole('link',{name:'Work',exact:true}).click();
  await page.getByText('Update the visitor guide',{exact:true}).click();
  await page.getByRole('heading',{name:'Completion criteria'}).waitFor();
  await page.getByRole('link',{name:'See how to brief an agent'}).click();
  await page.getByRole('heading',{name:'Does each agent need a moon?',exact:true}).waitFor();
  await page.getByRole('link',{name:'Code',exact:true}).click();
  await page.getByRole('heading',{name:'Working with Git in Stead'}).waitFor();
  await page.getByRole('button',{name:'Raw',exact:true}).click();
  const readme=await readFile(new URL('../src/handbook/README.md',import.meta.url),'utf8');
  assert.equal(await page.getByLabel('README source').textContent(),readme);
  await preferences.click();await visibility.uncheck();assert.equal(await rail.count(),0);
  await page.reload();await visibility.waitFor();assert.equal(await visibility.isChecked(),false);
  await page.getByRole('link',{name:'Open Stead Handbook'}).click();
  await page.getByRole('heading',{name:'Start here'}).waitFor();
  await page.goBack();await visibility.waitFor();
  member=2;await page.reload();await visibility.waitFor();assert.equal(await visibility.isChecked(),true);
  await rail.waitFor();member=1;await page.reload();await visibility.waitFor();assert.equal(await visibility.isChecked(),false);
  await visibility.check();await rail.waitFor();
  await page.setViewportSize({width:320,height:800});await page.goto(base+'#handbook/questions');
  await page.getByRole('heading',{name:'Common questions',exact:true}).waitFor();
  const switcher=page.getByRole('button',{name:'Browse workspace'});
  await switcher.click();await rail.waitFor();await rail.click();
  await page.getByRole('heading',{name:'Start here'}).waitFor();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
  assert.deepEqual(unexpected,[]);
  console.log('Handbook verified for two members with zero shared projects. README matches Markdown exactly. No business API requests.');
} finally {await browser.close();}

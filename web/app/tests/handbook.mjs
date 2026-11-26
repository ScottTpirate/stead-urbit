import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {chromium} from 'playwright';

const dist = new URL('../dist/', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('manifest.json', dist)));
const base = 'https://stead.test/stead/';
const account = n => '019939ba-4000-7000-8000-' + String(n).padStart(12, '0');
let member = 1;
const unexpected = [];
const nativePosts = [];
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
      nativePosts.push({path:url.pathname,kind:q.kind});
      if (q.project_id === '019a0000-0000-7000-8000-000000000001') {
        unexpected.push([url.pathname,q.kind??q.action]);return route.abort();
      }
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
  const heading=(name)=>page.getByRole('heading',{name,exact:true});
  const button=(name)=>page.getByRole('button',{name,exact:true});
  const views=page.getByRole('navigation',{name:'Project views'});
  const tab=name=>views.getByRole('button',{name,exact:true});
  const steps=['Overview','Work','Docs','Code'];

  await page.goto(base);await rail.waitFor();
  assert.equal(await button('Show me around').count(),0);
  const nativeBeforeGuide=nativePosts.length;
  await rail.click();await heading('Stead Handbook').waitFor();
  await page.getByRole('region',{name:'Project shortcuts'}).waitFor();
  await button('Show me around').focus();await page.keyboard.press('Enter');
  for (const [index,view] of steps.entries()) {
    const tour=page.getByRole('region',{name:view,exact:true});
    await tour.getByText(`Step ${index+1} of 4`,{exact:true}).waitFor();
    await tab(view).waitFor();
    if (view==='Work') {
      await heading('Work items').waitFor();
      await tour.getByRole('button',{name:'Back'}).click();
      await page.getByText('Step 1 of 4',{exact:true}).waitFor();await button('Next').click();
    }
    if (view==='Docs') await page.getByRole('combobox',{name:'Collection'}).waitFor();
    if (view==='Code') await page.getByRole('list',{name:'Folder contents'}).waitFor();
    await button(view==='Code'?'Done':'Next').click();
  }
  await button('Replay tour').waitFor();
  const files=page.getByRole('list',{name:'Folder contents'});
  const rootReadme=page.getByRole('region',{name:'Repository README'});
  await rootReadme.getByRole('heading',{name:'Working with Git in Stead',exact:true}).waitFor();
  assert.equal(await files.isVisible(),true);
  const readmeFollowsDirectory=await files.evaluate(list =>
    Boolean(list.compareDocumentPosition(document.querySelector('.repo-root-readme')) & Node.DOCUMENT_POSITION_FOLLOWING));
  assert.equal(readmeFollowsDirectory,true);
  await files.getByRole('button',{name:'README.md',exact:true}).click();
  await heading('Working with Git in Stead').waitFor();
  await page.getByRole('tab',{name:'Raw',exact:true}).click();
  const readme=await readFile(new URL('../src/handbook/README.md',import.meta.url),'utf8');
  assert.equal(await page.getByLabel('File contents').textContent(),readme);
  assert.equal(await button('Create read credential').count(),0);

  await tab('Work').click();
  await button('Update the visitor guide').click();
  await page.locator('#work-detail-panel').getByRole('heading',{name:'Update the visitor guide'}).waitFor();
  await page.getByText(/Only the meeting day changes from Monday to Wednesday/).waitFor();
  await page.getByText('I’ll check that the time and meeting point still match the original.',{exact:true}).waitFor();
  assert.equal(await button('Edit work item').count(),0);
  await button('Show links').click();
  await button('Give an agent a task').click();
  await heading('Does each agent need a moon?').waitFor();
  const docModes=page.getByRole('group',{name:'Document view'});
  assert.equal(await docModes.getByRole('button',{name:'Edit'}).count(),0);
  await docModes.getByRole('button',{name:'Source'}).click();
  const source=page.getByLabel('Markdown source');
  assert.equal(await source.getAttribute('readonly'),'');
  const full=await source.inputValue();
  const agentGuide=await readFile(new URL('../src/handbook/agents.md', import.meta.url),'utf8');
  assert.match(full,/^---\nid: [0-9a-f-]{36}\ntype: page\nstate: published\n---\n/u);
  assert.equal(full.slice(full.indexOf('---\n',4)+4),agentGuide);

  assert.deepEqual(nativePosts.slice(nativeBeforeGuide),[]);
  const articles=[
    ['why-stead','Why Stead?'],
    ['architecture','How Stead works'],
    ['settings','Settings and access'],
  ];
  for (const [slug,title] of articles) {
    await tab('Docs').click();
    await button(title).click();
    await page.waitForURL(base+'#handbook/'+slug);
    await page.reload();
    const reader=page.locator('.document-reader');
    await reader.getByRole('heading',{name:title,exact:true}).waitFor();
    if (slug==='architecture') {
      await reader.getByRole('heading',{name:'What lives in Git, and what lives in Home',exact:true}).waitFor();
      await reader.getByRole('table').waitFor();
    }
    if (slug==='settings') {
      await reader.getByRole('heading',{name:'Sign in on the private pilot',exact:true}).waitFor();
      await reader.getByText('Approve sign-in',{exact:true}).waitFor();
      await reader.getByText('Check approval',{exact:true}).waitFor();
    }
    await docModes.getByRole('button',{name:'Source'}).click();
    const saved=await source.inputValue();
    assert.equal(saved.slice(saved.indexOf('---\n',4)+4),
      await readFile(new URL('../src/handbook/'+slug+'.md',import.meta.url),'utf8'));
  }

  await preferences.click();await visibility.uncheck();assert.equal(await rail.count(),0);
  await page.reload();await visibility.waitFor();assert.equal(await visibility.isChecked(),false);
  await page.getByRole('link',{name:'Open Stead Handbook'}).click();
  await heading('Stead Handbook').waitFor();await button('Replay tour').waitFor();
  await page.goBack();await visibility.waitFor();
  member=2;await page.reload();await visibility.waitFor();assert.equal(await visibility.isChecked(),true);
  await rail.click();await button('Show me around').click();
  await page.getByText('Step 1 of 4',{exact:true}).waitFor();
  await button('Skip').click();await page.reload();await button('Replay tour').waitFor();
  await button('Replay tour').click();await page.getByText('Step 1 of 4',{exact:true}).waitFor();await button('Skip').click();

  await preferences.click();member=1;await page.reload();await visibility.waitFor();assert.equal(await visibility.isChecked(),false);
  await visibility.check();await rail.waitFor();await page.setViewportSize({width:320,height:800});
  await page.goto(base+'#handbook/questions');await heading('Common questions').first().waitFor();
  await page.getByRole('button',{name:'Browse workspace'}).click();await rail.click();
  await heading('Stead Handbook').waitFor();await button('Replay tour').click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
  await button('Skip').click();
  // Leave a deep link for Settings immediately. Late reads must stay scoped to their old route.
  await page.evaluate(()=>{location.hash='handbook/agents';location.hash='settings';});
  await visibility.waitFor();assert.equal(await heading('Stead Handbook').count(),0);
  assert.deepEqual(unexpected,[]);
  console.log('Handbook verified in the shared project screens, with read-only tasks and linked Docs, exact Git and document sources, a four-stop optional tour, account-scoped settings and 320px navigation.');
} finally {await browser.close();}

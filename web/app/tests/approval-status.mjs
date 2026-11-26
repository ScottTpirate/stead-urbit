// Render the real sign-in client against a synthetic native challenge, with no live credentials.
import assert from 'node:assert/strict';
import {mkdir, readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {chromium} from 'playwright';

const origin = 'https://stead.test';
const files = JSON.parse(await readFile(new URL('../dist/manifest.json', import.meta.url), 'utf8')).files;
const images = process.argv[2];
if (images) await mkdir(images, {recursive:true});
const browser = await chromium.launch({headless:true});
try {
  for (const width of [1440, 320]) {
    const context = await browser.newContext({viewport:{width, height:900}, serviceWorkers:'block'});
    try {
      const page = await context.newPage();
      const start = Date.UTC(2026, 10, 25, 18, 0, 0);
      await page.clock.install({time:new Date(start)});
      let starts = 0, polls = 0, consumes = 0, status = 'approved';
      const errors = [], unexpected = [];
      page.on('pageerror', error => errors.push(error.message));
      await context.route('**/*', async route => {
        const req = route.request(), url = new URL(req.url());
        if (url.origin !== origin) {unexpected.push(url.origin); return route.abort();}
        if (req.method() === 'GET') {
          const name = url.pathname === '/stead/' ? 'index.html' : url.pathname.replace(/^\/stead\/assets\//u, '');
          if (Object.hasOwn(files, name) && /\.(?:html|css|js)$/u.test(name)) {
            return route.fulfill({contentType:name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'text/javascript',
              body:await readFile(new URL('../dist/'+name, import.meta.url))});
          }
          return route.fulfill({status:404,body:''});
        }
        const send = (data, code=200) => route.fulfill({status:code,contentType:'application/json',body:JSON.stringify(data)});
        if (url.pathname === '/stead/api/capabilities') return send({protocol:'stead.capabilities/3',profile:'configured-team'});
        if (url.pathname === '/stead/auth/resume') return send({},401);
        if (url.pathname === '/stead/auth/start') {
          if (++starts === 1) return send({protocol:'stead.result/3',status:'rejected',error:'denied_or_not_found'});
          const id = String(starts).padStart(64, 'a');
          return send({protocol:'stead.auth/1',status:'pending',challenge_id:id,comparison_code:id.slice(0,12),
            expires_at_ms:String(start + (starts-1)*120_000),origin,home:'~zod'});
        }
        if (url.pathname === '/stead/auth/status') {
          polls++;
          if (status === 'unavailable') return send({}, 503);
          if (status === 'ended') return send({}, 401);
          return send({protocol:'stead.auth/1',status,challenge_id:req.postDataJSON().challenge_id});
        }
        if (url.pathname === '/stead/auth/consume') {consumes++; return send({},401);}
        unexpected.push(url.pathname); return send({},403);
      });
      await page.goto(origin+'/stead/');
      await page.getByRole('textbox',{name:'Urbit ID'}).fill('~bus');
      const request = page.getByRole('button',{name:'Continue',exact:true});
      await request.click();
      await page.getByText(/ask your operator to check your member access/).waitFor();
      await request.click();
      await page.getByRole('heading',{name:'Approve on your identity ship'}).waitFor();
      await page.clock.fastForward(4001);
      await page.getByRole('button',{name:'Open Stead'}).waitFor();
      await page.getByRole('heading',{name:'Sign-in approved'}).waitFor();
      assert.equal(consumes,0);
      const n = polls;
      await page.clock.fastForward(10_000);
      assert.equal(polls,n);
      if (images) await page.screenshot({path:join(images,'sign-in-'+width+'.png')});
      await page.clock.fastForward(120_000);
      const renew = page.getByRole('button',{name:'Request a new code'});
      await renew.waitFor(); await renew.focus(); status='ended'; await renew.press('Enter');
      await page.getByRole('button',{name:'Check approval'}).waitFor();
      await page.clock.fastForward(4001); await renew.waitFor();
      status='unavailable'; await renew.click();
      await page.getByRole('button',{name:'Check approval'}).waitFor();
      await page.clock.fastForward(4001);
      await page.getByText(/could not check automatically/).waitFor();
      await page.getByRole('button',{name:'Use a different ID'}).click();
      await page.waitForFunction(()=>document.activeElement?.getAttribute('autocomplete')==='username');
      const last=polls;
      await page.clock.fastForward(120_001);
      assert.equal(polls,last); assert.equal(consumes,0);
      assert.deepEqual(errors,[]); assert.deepEqual(unexpected,[]);
      console.log('PASS sign-in at '+width+'px: denial recovery, read-only approval, expiry, retry, transport failure and keyboard return.');
    } finally {await context.close();}
  }
} finally {await browser.close();}

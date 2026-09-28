import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';

async function channel(page, path) {
  const name = 'stead-boundary-' + randomBytes(12).toString('hex');
  const result = await page.evaluate(async ({name, path}) => {
    const url = '/~/channel/' + name;
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 20000);
    const events = [];
    let reader;
    try {
      const sent = await fetch(url, {method: 'PUT', credentials: 'same-origin', signal: abort.signal,
        headers: {'Content-Type':'application/json'}, body: JSON.stringify([
          {id:1, action:'subscribe', ship:'zod', app:'stead-http-boundary-probe', path:'/public-control'},
          {id:2, action:'subscribe', ship:'zod', app:'stead-home', path},
          {id:3, action:'poke', ship:'zod', app:'stead-http-boundary-probe', mark:'json', json:{public_control:'yes'}},
        ])});
      if (sent.status !== 204) throw new Error('Channel send failed');
      const response = await fetch(url, {credentials:'same-origin', signal:abort.signal, headers:{Accept:'text/event-stream'}});
      if (response.status !== 200 || !response.headers.get('content-type')?.startsWith('text/event-stream') || !response.body) throw new Error('Channel stream failed');
      reader = response.body.getReader();
      let text = '', bytes = 0;
      const decoder = new TextDecoder('utf-8', {fatal:true});
      while (!(events.some(row => row.id === 1 && row.response === 'diff')
          && events.some(row => row.id === 2 && row.response === 'subscribe')
          && events.some(row => row.id === 3 && row.response === 'poke'))) {
        const part = await reader.read();
        if (part.done) throw new Error('Channel ended early');
        bytes += part.value.byteLength;
        if (bytes > 65536 || events.length > 16) throw new Error('Channel bound');
        text += decoder.decode(part.value, {stream:true});
        let split;
        while ((split = text.indexOf('\n\n')) !== -1) {
          const event = text.slice(0,split); text = text.slice(split+2);
          for (const line of event.split('\n')) if (line.startsWith('data: ')) events.push(JSON.parse(line.slice(6)));
        }
      }
      return {events, bytes};
    } finally {
      clearTimeout(timer); abort.abort();
      if (reader) await reader.cancel().catch(() => {});
      const cleanup = await fetch(url, {method:'POST', credentials:'same-origin', signal:AbortSignal.timeout(5000),
        headers:{'Content-Type':'application/json'}, body:JSON.stringify([{action:'delete'}])});
      if (cleanup.status !== 204) throw new Error('Owned channel cleanup failed');
    }
  }, {name, path});
  assert.ok(result.events.some(row => row.id === 1 && row.response === 'subscribe' && row.ok === 'ok'));
  assert.ok(result.events.some(row => row.id === 1 && row.response === 'diff' && row.json?.public_control === 'yes'));
  assert.ok(result.events.some(row => row.id === 3 && row.response === 'poke' && row.ok === 'ok'));
  const denied = result.events.find(row => row.id === 2 && row.response === 'subscribe');
  assert.ok(denied && Object.hasOwn(denied,'err') && !Object.hasOwn(denied,'ok'));
  assert.ok(JSON.stringify(denied.err).includes('stead-current-member-required'));
  assert.ok(!result.events.some(row => row.id === 2 && row.response === 'diff'));
  return {bytes:result.bytes, public_watch:true, public_poke:true, protected_watch_denied:true, channel_deleted:true};
}

export async function endpointBoundaries({browser, alice, material, pageIn, restrict, passed}) {
  const origin = material.origin;
  const path = '/v3/result/~bus/019939ba-4000-7000-8000-0000000000ca/1/019939ba-4000-7000-8000-00000000a001/' + 'a'.repeat(64);
  const member = await channel(alice.home, path);
  const scry = await alice.home.evaluate(async () => (await fetch('/~/scry/stead-http-boundary-probe/public-control.json',
    {credentials:'same-origin', signal:AbortSignal.timeout(5000)})).status);
  assert.equal(scry,403);
  passed('member-session-cannot-promote-raw-eyre-channel-or-scry-to-home-authority', member);
  const outsider = await browser.newContext({ignoreHTTPSErrors:false,serviceWorkers:'block'});
  await restrict(outsider);
  try {
    const home = await pageIn(outsider);
    await home.goto(origin + '/stead/');
    await home.getByRole('textbox',{name:'Your identity ship',exact:true}).fill('~bud');
    const response = home.waitForResponse(row => row.url() === origin + '/stead/auth/start');
    await home.getByRole('button',{name:'Request sign-in',exact:true}).click();
    const denied = await (await response).json();
    assert.equal(denied.error,'denied_or_not_found');
    assert.equal(await home.getByRole('heading',{name:'Approve on your identity ship',exact:true}).count(),0);
    assert.equal((await outsider.cookies(origin)).some(row => row.name === '__Host-stead-session'),false);
    passed('unbound-individual-browser-cannot-start-a-member-session');
  } finally { await outsider.close(); }
  const owner = await browser.newContext({ignoreHTTPSErrors:false,serviceWorkers:'block'});
  await restrict(owner);
  try {
    const page = await pageIn(owner);
    await page.goto(origin + '/~/login');
    assert.equal(new URL(page.url()).origin,origin);
    assert.equal(new URL(page.url()).pathname,'/~/login');
    await page.locator('input#pass').fill(material.identities.zod.code);
    await page.locator('#local button[type=submit]').click();
    await page.goto(origin + '/stead/');
    const probe = await page.evaluate(async () => (await fetch('/stead-boundary-probe/',{credentials:'same-origin'})).json());
    assert.equal(probe.owner_authenticated,'yes');
    const observed = await page.evaluate(async () => {
      const query = {protocol:'stead.query/3',request_id:'019939ba-4000-7000-8000-00000000a002',kind:'identity',
        project_id:'',container_id:'',resource_id:'',search:'',cursor:''};
      const member = await fetch('/stead/api/query',{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json'},body:JSON.stringify(query)});
      const control = await fetch('/~/scry/stead-http-boundary-probe/public-control.json',{credentials:'same-origin'});
      const protectedScry = await fetch('/~/scry/stead-home/state.json',{credentials:'same-origin'});
      return {member_status:member.status, member_body:await member.json(), public_status:control.status,
        public_body:await control.json(), protected_status:protectedScry.status};
    });
    assert.equal(observed.member_status,401); assert.equal(observed.member_body.error,'session_required');
    assert.equal(observed.public_status,200); assert.deepEqual(observed.public_body,{public_control:'yes'});
    assert.equal(observed.protected_status,500); // Pinned default-agent explicitly bails on every home peek.
    const raw = await channel(page,path);
    assert.equal((await owner.cookies(origin)).some(row => row.name === '__Host-stead-session'),false);
    passed('organization-owner-cookie-does-not-create-member-session-or-raw-home-read',raw);
  } finally { await owner.close(); }
}

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

export async function endpointBoundaries({browser, alice, material, pageIn, restrict, passed, recordBoundary}) {
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
      async function capture(operation, url, options = {}) {
        const row = {operation, status: null, content_type: 'absent', body_bytes: 0,
          body_sha256: null, capture: 'failed', parse: 'not-json'};
        let reader;
        try {
          const response = await fetch(url, {...options, credentials: 'same-origin', signal: AbortSignal.timeout(5000)});
          row.status = response.status;
          const type = response.headers.get('content-type')?.split(';')[0].trim().toLowerCase();
          row.content_type = type && /^[a-z0-9.+/-]{1,80}$/u.test(type) ? type : 'other';
          reader = response.body?.getReader();
          if (!reader) return row;
          const chunks = [];
          for (;;) {
            const part = await reader.read();
            if (part.done) break;
            row.body_bytes += part.value.byteLength;
            if (row.body_bytes > 65536) { row.capture = 'oversized'; return row; }
            chunks.push(part.value);
          }
          const bytes = new Uint8Array(row.body_bytes);
          let offset = 0;
          for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
          row.body_sha256 = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
            value => value.toString(16).padStart(2, '0')).join('');
          row.capture = 'complete';
          if (row.content_type === 'application/json') {
            try {
              row.value = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes));
              row.parse = 'json';
            } catch { row.parse = 'invalid-json'; }
          }
          return row;
        } catch { return row; }
        finally { if (reader) await reader.cancel().catch(() => {}); }
      }
      const query = {protocol:'stead.query/3',request_id:'019939ba-4000-7000-8000-00000000a002',kind:'identity',
        project_id:'',container_id:'',resource_id:'',search:'',cursor:''};
      return [
        await capture('owner-member-query', '/stead/api/query', {method:'POST',
          headers:{'Content-Type':'application/json'},body:JSON.stringify(query)}),
        await capture('owner-public-scry', '/~/scry/stead-http-boundary-probe/public-control.json'),
        await capture('owner-protected-scry', '/~/scry/stead-home/state.json'),
      ];
    });
    for (const row of observed) {
      const {value, ...metadata} = row;
      recordBoundary(metadata);
    }
    for (const row of observed) assert.equal(row.capture, 'complete', row.operation + ' complete response');
    const [memberQuery, publicScry, protectedScry] = observed;
    assert.equal(memberQuery.status,401); assert.equal(memberQuery.parse,'json');
    assert.ok(memberQuery.value !== null && typeof memberQuery.value === 'object'
      && !Array.isArray(memberQuery.value) && memberQuery.value.error === 'session_required',
      'Owner-only query must return the exact session-required denial');
    assert.equal(publicScry.status,200); assert.equal(publicScry.parse,'json');
    assert.ok(publicScry.value !== null && typeof publicScry.value === 'object'
      && !Array.isArray(publicScry.value) && Object.keys(publicScry.value).length === 1
      && publicScry.value.public_control === 'yes', 'Public scry control payload differs');
    // Pinned Gall converts the default-agent peek bail to [~ ~]; Eyre returns 404.
    assert.equal(protectedScry.status,404);
    const raw = await channel(page,path);
    assert.equal((await owner.cookies(origin)).some(row => row.name === '__Host-stead-session'),false);
    passed('organization-owner-cookie-does-not-create-member-session-or-raw-home-read',raw);
  } finally { await owner.close(); }
}

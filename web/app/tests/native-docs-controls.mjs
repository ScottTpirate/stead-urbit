// Actual browser HTTPS observations; no synthetic views, cursors or authority.
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';

export async function privateProjectionControl(page, origin, project, sharedCollection) {
  const observed = page.waitForResponse(response => response.url() === origin + '/stead/api/query'
    && response.request().postDataJSON()?.kind === 'project'
    && response.request().postDataJSON()?.project_id === project);
  await page.getByRole('button', {name:'Refresh', exact:true}).click();
  const response = await observed;
  assert.equal(response.status(), 200);
  const csrf = (await response.request().allHeaders())['x-stead-csrf'];
  assert.match(csrf, /^[0-9a-f]{64}$/u);
  const metadata = await response.json();
  assert.equal(metadata.status, 'read');
  assert.equal(Object.values(metadata.rows)[0].role, 'reader');
  await page.locator('#project-content[data-live-updates="connected"]').waitFor();

  async function post(endpoint, protocol, body) {
    const request = {protocol, request_id:'019939ba-4000-7000-8000-' + randomBytes(6).toString('hex'), ...body};
    const result = await page.evaluate(async ({endpoint, csrf, request}) => {
      const response = await fetch('/stead/api/' + endpoint, {method:'POST', credentials:'same-origin',
        signal:AbortSignal.timeout(15000), cache:'no-store', redirect:'error',
        headers:{'Content-Type':'application/json', 'X-Stead-CSRF':csrf}, body:JSON.stringify(request)});
      if (response.status !== 200 || !response.headers.get('content-type')?.startsWith('application/json') || !response.body)
        throw new Error('Native projection transport failed');
      const reader = response.body.getReader(), chunks = [];
      let size = 0;
      try {
        while (true) {
          const part = await reader.read();
          if (part.done) break;
          size += part.value.byteLength;
          if (size > 262144) throw new Error('Native projection byte bound');
          chunks.push(part.value);
        }
      } finally { await reader.cancel(); reader.releaseLock(); }
      const bytes = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
      return JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes));
    }, {endpoint, csrf, request});
    assert.equal(result.request_id, request.request_id);
    assert.equal(result.protocol, endpoint === 'query' ? 'stead.query-result/3' : 'stead.update-result/3');
    return result;
  }
  function scope(kind) {
    return {kind, project_id:kind ? project : '', container_id:kind === 'documents' ? sharedCollection : '', resource_id:'', search:''};
  }
  const kinds = ['project', 'containers', 'documents', 'search', 'activity', 'inbox', 'relations'];
  async function query(kind) {
    const result = await post('query', 'stead.query/3', {...scope(kind), cursor:''});
    assert.equal(result.status, 'read');
    for (const key of ['kind','project_id','container_id','resource_id']) assert.equal(result[key], scope(kind)[key]);
    assert.match(result.generation, /^[0-9a-f]{64}$/u);
    assert.equal(result.cursor, '', 'Inspect the complete small authorized projection');
    assert.ok(result.rows && !Array.isArray(result.rows) && Object.keys(result.rows).length <= 20);
    return {generation:result.generation, authority_epoch:result.authority_epoch, cursor:result.cursor, rows:result.rows};
  }
  const watches = new Map(), before = new Map();
  async function close() {
    const errors = [];
    for (const [kind, handle] of watches) {
      try {
        const result = await post('updates', 'stead.updates/3', {...scope(''), action:'cancel', watch_id:handle.watch_id, cursor:''});
        assert.equal(result.status, 'cancelled'); assert.equal(result.watch_id, handle.watch_id);
        assert.equal(result.cursor, ''); assert.equal(result.generation, ''); assert.deepEqual(result.rows, {});
      } catch (error) { errors.push(error); }
      finally { watches.delete(kind); }
    }
    if (errors.length) throw new AggregateError(errors, 'Owned projection watches did not close');
  }
  async function poll(kind) {
    const previous = watches.get(kind);
    const result = await post('updates', 'stead.updates/3', {...scope(''), action:'poll', watch_id:previous.watch_id, cursor:previous.cursor});
    assert.equal(result.status, 'updated'); assert.equal(result.watch_id, previous.watch_id);
    assert.match(result.cursor, /^[0-9a-f]{64}$/u); assert.notEqual(result.cursor, previous.cursor);
    assert.match(result.generation, /^[0-9a-f]{64}$/u);
    watches.set(kind, result);
    return {previous, result};
  }
  try {
    // Three owned watches plus the product's existing UI watch fit the cap.
    for (const kind of ['search', 'activity', 'inbox']) {
      const result = await post('updates', 'stead.updates/3', {...scope(kind), action:'open', watch_id:'', cursor:''});
      assert.equal(result.status, 'watching');
      assert.match(result.watch_id, /^[0-9a-f]{64}$/u); assert.match(result.cursor, /^[0-9a-f]{64}$/u);
      assert.deepEqual(result.rows, {});
      watches.set(kind, result);
    }
    for (const kind of kinds) before.set(kind, await query(kind));
    for (const kind of watches.keys()) {
      const {result} = await poll(kind);
      assert.deepEqual(result.rows, {}); assert.equal(result.generation, before.get(kind).generation);
    }
  } catch (error) { await close(); throw error; }
  return {
    close,
    async unchanged() {
      const observations = [];
      for (const kind of kinds) {
        const after = await query(kind);
        assert.deepEqual(after, before.get(kind), 'Private mutation changed reader projection: ' + kind);
        observations.push({kind, row_count:Object.keys(after.rows).length, generation:after.generation});
      }
      for (const kind of watches.keys()) {
        const {previous, result} = await poll(kind);
        assert.deepEqual(result.rows, {}); assert.equal(result.generation, previous.generation);
      }
      return observations;
    },
    async sharedChange() {
      const observations = [];
      for (const kind of watches.keys()) {
        const {previous, result} = await poll(kind);
        assert.notEqual(result.generation, previous.generation, 'Visible edit must exercise the same watch');
        const rows = Object.values(result.rows);
        assert.equal(rows.length, 1, 'One visible publication must produce exactly one invalidation');
        rows.forEach(row => {
          assert.deepEqual(Object.keys(row).sort(), ['generation','sequence']);
          // These scopes have no other active watch: cancellation drops their
          // former streams. Private edits must not consume a sequence number.
          assert.equal(row.sequence, '1');
          assert.match(row.generation, /^[0-9a-f]{64}$/u);
        });
        assert.equal(rows.at(-1).generation, result.generation);
        assert.equal((await query(kind)).generation, result.generation);
        observations.push({kind, invalidations:rows.length});
      }
      return observations;
    },
  };
}

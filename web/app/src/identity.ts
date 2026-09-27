import './identity.css';
// This page belongs to the person's own ship. It never receives a Stead bearer.
type Fields = Record<string, string>;
const root = document.getElementById('root')!;
const heading = document.createElement('h1'); heading.textContent = 'Approve a Stead sign-in';
const introduction = document.createElement('p'); introduction.textContent = 'Compare the code and home address with the Stead window you opened. Approve only a sign-in you requested.';
const status = document.createElement('p'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
const refresh = document.createElement('button'); refresh.textContent = 'Refresh requests';
const list = document.createElement('div'); list.setAttribute('aria-label', 'Sign-in requests');
root.append(heading, introduction, refresh, status, list);
let busy = false;
function fields(value: unknown): Fields {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length > 16 || Object.values(value).some(v => typeof v !== 'string')) throw new Error('Invalid response');
  return value as Fields;
}
function requestFields(value: unknown): Fields {
  const row = fields(value);
  const required = ['comparison_code', 'origin', 'identity_ship', 'home', 'principal_id', 'binding_id', 'binding_revision', 'expires_at_ms', 'status', 'csrf'];
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u;
  if (Object.keys(row).length !== required.length || required.some(key => !(key in row)) ||
      !uuid.test(row.principal_id!) || !uuid.test(row.binding_id!) || !/^[1-9][0-9]{0,19}$/u.test(row.binding_revision!) || BigInt(row.binding_revision!) > 18446744073709551615n ||
      !/^[1-9][0-9]{0,15}$/u.test(row.expires_at_ms!) || !Number.isSafeInteger(Number(row.expires_at_ms)) ||
      !Number.isFinite(new Date(Number(row.expires_at_ms)).getTime()) ||
      !/^~[a-z-]{3,80}$/u.test(row.home!) || !/^~[a-z-]{3,80}$/u.test(row.identity_ship!)) throw new Error('Invalid response');
  const origin = new URL(row.origin!);
  if (origin.protocol !== 'https:' || origin.origin !== row.origin || row.origin!.length > 256) throw new Error('Invalid response');
  return row;
}
async function post(operation: 'list' | 'approve', body: Fields): Promise<Record<string, unknown>> {
  const response = await fetch('/stead-identity/api/' + operation, {method: 'POST', credentials: 'same-origin', cache: 'no-store', redirect: 'error',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: AbortSignal.timeout(15000)});
  if (response.status === 401) throw new Error('owner_required');
  if (!response.ok || response.headers.get('content-type')?.split(';')[0] !== 'application/json' || !response.body) throw new Error('The request was not confirmed.');
  const reader = response.body.getReader(); const parts: Uint8Array[] = []; let size = 0;
  try {
    while (true) { const part = await reader.read(); if (part.done) break; size += part.value.length; if (size > 32768) throw new Error('Response too large'); parts.push(part.value); }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0; for (const part of parts) { bytes.set(part, offset); offset += part.length; }
  const value: unknown = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid response');
  return value as Record<string, unknown>;
}
function error(error: unknown) {
  list.replaceChildren();
  if (error instanceof Error && error.message === 'owner_required') {
    status.textContent = 'Sign in to this identity ship to review requests.';
    const login = document.createElement('a'); login.href = '/~/login?redirect=/stead-identity/'; login.textContent = 'Sign in to my ship'; list.append(login);
  } else status.textContent = error instanceof Error && error.name !== 'TimeoutError' ? error.message : 'The outcome is unconfirmed. Refresh requests before trying again.';
}
async function load() {
  if (busy) return; busy = true; refresh.disabled = true;
  try {
    const value = await post('list', {protocol: 'stead.identity/1'});
    if (value.protocol !== 'stead.identity/1' || value.status !== 'read' || !value.requests || typeof value.requests !== 'object' || Array.isArray(value.requests)) throw new Error('Invalid response');
    const rows = Object.entries(value.requests); if (rows.length > 4) throw new Error('Invalid response');
    list.replaceChildren(); status.textContent = rows.length ? 'Review each request before approving.' : 'No pending sign-ins. Start in your Stead window, then refresh here.';
    for (const [id, raw] of rows) {
      const row = requestFields(raw);
      if (!/^[0-9a-f]{64}$/u.test(id) || row.comparison_code !== id.slice(0,12) || !/^(pending|sent|approved|failed)$/u.test(row.status ?? '')) throw new Error('Invalid response');
      const article = document.createElement('article'); const code = document.createElement('h2'); code.textContent = row.comparison_code;
      const address = document.createElement('p'); address.textContent = 'Stead home: ' + row.home + ' at ' + row.origin;
      const identity = document.createElement('p'); identity.textContent = 'Identity: ' + row.identity_ship;
      const principal = document.createElement('p'); principal.textContent = 'Principal: ' + row.principal_id;
      const binding = document.createElement('p'); binding.textContent = 'Binding: ' + row.binding_id + ', revision ' + row.binding_revision;
      const expiry = document.createElement('p'); expiry.textContent = 'Expires: ' + new Date(Number(row.expires_at_ms)).toLocaleString() + ' (the home enforces this deadline).';
      const result = document.createElement('p'); result.setAttribute('role', 'status'); result.textContent = ({pending: 'Waiting for your approval.', sent: 'Approval sent; refresh to check acknowledgement.', approved: 'Home acknowledged your approval. Return to Stead to finish signing in.', failed: 'Approval was not accepted. Start a new sign-in in Stead.'} as Fields)[row.status!]!;
      article.append(code, address, identity, principal, binding, expiry, result);
      if (row.status === 'pending') {
        if (!/^[0-9a-f]{64}$/u.test(row.csrf ?? '')) throw new Error('Invalid response');
        const approve = document.createElement('button'); approve.textContent = 'The code and home match — approve';
        approve.addEventListener('click', async () => {
          if (busy) return; busy = true; refresh.disabled = true; for (const button of list.querySelectorAll('button')) button.disabled = true;
          try {
            const reply = await post('approve', {protocol: 'stead.identity/1', challenge_id: id, csrf: row.csrf!, comparison_code: row.comparison_code!, origin: row.origin!});
            if (reply.protocol !== 'stead.identity/1' || reply.status !== 'sent' || reply.challenge_id !== id) throw new Error('Approval was not confirmed. Refresh before trying again.');
            result.textContent = 'Approval sent. Refresh to check acknowledgement, or return to Stead to finish signing in.';
          } catch (failure) {
            error(failure instanceof Error && failure.message === 'owner_required' ? failure : new Error('The approval outcome is unconfirmed. Refresh requests before trying again.'));
          }
          finally { busy = false; refresh.disabled = false; }
        });
        article.append(approve);
      }
      list.append(article);
    }
  } catch (failure) { error(failure); }
  finally { busy = false; refresh.disabled = false; }
}
refresh.addEventListener('click', () => { void load(); });
void load();

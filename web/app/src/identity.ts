import './identity.css';
// This page belongs to the person's own ship. It never receives a Stead bearer.
type Fields = Record<string, string>;
function element<Tag extends keyof HTMLElementTagNameMap>(tag: Tag, className: string, content?: string) {
  const node = document.createElement(tag);
  node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}
const root = document.getElementById('root')!;
const header = element('header', 'identity-header');
const mark = element('span', 'identity-mark', '~'); mark.setAttribute('aria-hidden', 'true');
const heading = element('h1', '', 'Approve a Stead sign-in');
header.append(mark, heading);
const status = element('p', 'identity-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); status.tabIndex = -1;
const refresh = element('button', 'identity-action identity-action--quiet', 'Refresh requests'); refresh.type = 'button';
const toolbar = element('div', 'identity-toolbar'); toolbar.append(status, refresh);
const list = element('div', 'identity-requests'); list.setAttribute('aria-label', 'Sign-in requests');
root.append(header, toolbar, list);
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
    refresh.hidden = true;
    status.textContent = 'Sign in to your Urbit to review the request.';
    const login = element('a', 'identity-action identity-action--primary', 'Sign in to my ship');
    login.href = '/~/login?redirect=/stead-identity/';
    list.append(login);
  } else {
    status.textContent = 'The request was not confirmed. Refresh requests before trying again.';
  }
}
async function load() {
  if (busy) return; busy = true; refresh.disabled = true;
  status.textContent = 'Checking for sign-in requests…';
  try {
    const value = await post('list', {protocol: 'stead.identity/1'});
    if (value.protocol !== 'stead.identity/1' || value.status !== 'read' || !value.requests || typeof value.requests !== 'object' || Array.isArray(value.requests)) throw new Error('Invalid response');
    const rows = Object.entries(value.requests); if (rows.length > 4) throw new Error('Invalid response');
    list.replaceChildren();
    status.textContent = rows.length ? 'Match the Home address and code with your Stead tab before approving.'
      : 'No pending sign-ins. Start in your Stead tab, then refresh here.';
    for (const [id, raw] of rows) {
      const row = requestFields(raw);
      if (!/^[0-9a-f]{64}$/u.test(id) || row.comparison_code !== id.slice(0,12) || !/^(pending|sent|approved|failed)$/u.test(row.status ?? '')) throw new Error('Invalid response');
      const article = element('article', 'identity-request');
      const label = element('p', 'identity-caption', 'Comparison code');
      const code = element('h2', 'identity-code', row.comparison_code);
      const address = element('p', 'identity-address', 'Stead home: ' + row.home + ' at ' + row.origin);
      const identity = element('p', 'identity-caption', 'Approving as ' + row.identity_ship);
      const expiry = element('p', 'identity-caption');
      const date = new Date(Number(row.expires_at_ms));
      const deadline = element('time', '', date.toLocaleTimeString(undefined, {hour: 'numeric', minute: '2-digit'}));
      deadline.dateTime = date.toISOString();
      expiry.append('Expires ', deadline);
      const result = element('p', 'identity-result', ({pending: 'Waiting for your approval.', sent: 'Approval sent. Return to your Stead tab and check approval.', approved: 'Approval confirmed. Return to your Stead tab to finish signing in.', failed: 'Approval was not accepted. Start a new sign-in in Stead.'} as Fields)[row.status!]!);
      result.setAttribute('role', 'status');
      result.tabIndex = -1;
      const details = element('details', 'identity-details');
      details.append(element('summary', '', 'Request details'),
        element('p', '', 'Principal ' + row.principal_id),
        element('p', '', 'Binding ' + row.binding_id + ', revision ' + row.binding_revision));
      article.append(label, code, address, identity, expiry, result);
      if (row.status === 'pending') {
        if (!/^[0-9a-f]{64}$/u.test(row.csrf ?? '')) throw new Error('Invalid response');
        const approve = element('button', 'identity-action identity-action--primary', 'Approve sign-in');
        approve.type = 'button';
        approve.addEventListener('click', async () => {
          if (busy) return; busy = true; refresh.disabled = true; for (const button of list.querySelectorAll('button')) button.disabled = true;
          try {
            const reply = await post('approve', {protocol: 'stead.identity/1', challenge_id: id, csrf: row.csrf!, comparison_code: row.comparison_code!, origin: row.origin!});
            if (reply.protocol !== 'stead.identity/1' || reply.status !== 'sent' || reply.challenge_id !== id) throw new Error('Approval was not confirmed. Refresh before trying again.');
            result.textContent = 'Approval sent. Return to your Stead tab and check approval.';
            approve.remove();
            result.focus();
          } catch (failure) {
            error(failure);
            status.focus();
          }
          finally { busy = false; refresh.disabled = false; for (const button of list.querySelectorAll('button')) button.disabled = false; }
        });
        article.append(approve);
      }
      article.append(details);
      list.append(article);
    }
  } catch (failure) { error(failure); }
  finally { busy = false; refresh.disabled = false; }
}
refresh.addEventListener('click', () => { void load(); });
void load();

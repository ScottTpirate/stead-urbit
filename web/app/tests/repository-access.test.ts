import assert from 'node:assert/strict';
import test from 'node:test';
import {HomeClient, repositoryAccess, type Fields} from '../src/api';

const status = (mode: string, write = 'yes', manage = 'yes') => ({
  protocol: 'stead.code/1', status: mode, write, manage,
});
const pack = (mode = 'external', limits: Fields = {}) => ({status: mode, ...limits});

function clientWith(current: Fields, snapshot: Fields) {
  const client = new HomeClient();
  Object.defineProperty(client, 'code', {value: async (project: string, input: {action: string}) => {
    assert.equal(project, 'project');
    if (input.action === 'status') return current;
    assert.equal(input.action, 'pack-view');
    return snapshot;
  }});
  return client;
}

test('only an existing inline or accepted external repository can issue a write credential', () => {
  for (const mode of ['disabled', 'external-staged', 'ready', 'external']) {
    assert.equal(repositoryAccess(status(mode)).writable, ['ready', 'external'].includes(mode));
    assert.equal(repositoryAccess(status(mode, 'no', 'yes')).writable, false);
    assert.equal(repositoryAccess(status(mode, 'yes', 'no')).manage, false);
  }
});

test('unknown status and malformed authority flags fail closed', () => {
  for (const value of [status('unknown'), status('ready', 'unknown'), status('external', 'yes', ''),
    {...status('ready'), protocol: 'other'}]) assert.throws(() => repositoryAccess(value), /invalid_response/);
});

test('status and the snapshot must agree before presenting external operations', async () => {
  for (const mode of ['disabled', 'ready', 'external-staged']) {
    await assert.rejects(clientWith(status(mode), pack()).externalRepository('project'), /repository_changed/);
  }
  await assert.rejects(clientWith(status('external'), pack('external-staged')).externalRepository('project'), /repository_changed/);
  const staged = await clientWith(status('external-staged'), pack('external-staged')).externalRepository('project');
  assert.equal(staged.access.manage, true);
  assert.equal(staged.access.writable, false);
});

test('accepted snapshots remain readable at capacity and preserve older replies without limits', async () => {
  for (const [fields, full] of [[{}, false], [{generation: '2', generation_limit: '3'}, false],
    [{generation: '3', generation_limit: '3'}, true]] as [Fields, boolean][]) {
    const snapshot = pack('external', fields);
    const current = await clientWith(status('external', 'no'), snapshot).externalRepository('project');
    assert.deepEqual(current.snapshot, snapshot);
    assert.equal(current.atCapacity, full);
    assert.equal(current.access.writable, false);
  }
});

test('the client reports revocation only after the Home confirms it', async () => {
  const client = new HomeClient();
  let reply = 'issued';
  Object.defineProperty(client, 'post', {value: async () => ({protocol: 'stead.code/1', status: reply})});
  const input = {action: 'revoke', handle: 'a'.repeat(64)} as const;
  await assert.rejects(client.code('project', input), /invalid_response/);
  reply = 'revoked';
  assert.equal((await client.code('project', input)).status, 'revoked');
});

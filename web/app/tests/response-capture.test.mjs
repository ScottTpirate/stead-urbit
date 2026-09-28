// Actual promise scheduling controls. No browser or native execution.
import assert from 'node:assert/strict';
import test from 'node:test';
import {ResponseCapture} from './response-capture.mjs';

test('closeout waits for and records a rejection arriving during final drain', async () => {
  const capture = new ResponseCapture();
  let reject;
  const response = new Promise((_, fail) => { reject = fail; });
  capture.track(() => response);
  let finished = false;
  const closing = capture.close().then(value => { finished = true; return value; });
  await Promise.resolve();
  assert.equal(finished, false);
  reject(new SyntaxError('synthetic invalid response JSON'));
  assert.deepEqual(await closing, {complete:true,failures:1});
  assert.equal(capture.pending, 0);
});

test('explicit capture boundary refuses later events without invoking them', async () => {
  const capture = new ResponseCapture();
  let count = 0;
  assert.equal(capture.track(async () => { count++; }), true);
  const closing = capture.close();
  assert.equal(capture.track(() => { throw new Error('must not run'); }), false);
  assert.deepEqual(await closing, {complete:true,failures:0});
  assert.equal(count, 1);
});

test('synchronous and asynchronous capture failures remain counted after retirement', async () => {
  const capture = new ResponseCapture();
  capture.track(() => { throw new Error('synchronous'); });
  capture.track(async () => { throw new Error('asynchronous'); });
  await capture.drain();
  assert.equal(capture.pending, 0);
  assert.equal(capture.failures, 2);
  assert.deepEqual(await capture.close(), {complete:true,failures:2});
});

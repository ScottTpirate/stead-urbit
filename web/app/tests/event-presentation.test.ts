import test from 'node:test';
import assert from 'node:assert/strict';
import {eventPresentation} from '../src/eventPresentation';

const principal = '019939ba-4000-7000-8000-000000000101';
const other = '019939ba-4000-7000-8000-000000000102';
const request = '019939ba-4000-7000-8000-000000000301';
const resource = '019939ba-4000-7000-8000-000000000201';
const accepted = '1790519400123';
const row = {kind: 'activity', operation: 'work.comment', principal_id: principal,
  request_id: request, resource_id: resource, container_id: '', accepted_at_ms: accepted};

test('accepted events use readable actions and preserve exact audit values only in Details', () => {
  const presented = eventPresentation(row, other);
  assert.equal(presented.summary, 'Project member commented on work');
  assert.equal(presented.acceptedAt, accepted);
  assert.equal(presented.summary.includes(principal), false);
  assert.deepEqual(presented.details, [
    {label: 'Operation', value: 'work.comment'}, {label: 'Request ID', value: request},
    {label: 'Member ID', value: principal}, {label: 'Resource ID', value: resource},
    {label: 'Accepted time (milliseconds)', value: accepted},
  ]);
  assert.equal(eventPresentation(row, principal).summary, 'You commented on work');
});

test('actor names require an explicit authorized same-principal projection', () => {
  assert.equal(eventPresentation({...row, display_name: 'Unqualified row field'}, other).actor, 'Project member');
  assert.equal(eventPresentation(row, other, {principal_id: principal, display_name: 'Maya 東京'}).actor, 'Maya 東京');
  for (const resolved of [
    {principal_id: other, display_name: 'Wrong person'},
    {principal_id: principal, display_name: principal},
    {principal_id: principal, display_name: '  '},
    {principal_id: principal, display_name: 'Name\nForged event'},
    {principal_id: principal, display_name: '名'.repeat(100)},
  ]) assert.equal(eventPresentation(row, other, resolved).actor, 'Project member');
  assert.equal(eventPresentation({}, undefined).actor, 'Project member');
});

test('operation projection never invents completion approval or a resource title', () => {
  assert.equal(eventPresentation({...row, operation: 'work.update', status: 'done'}).action, 'Updated work');
  for (const operation of ['work.future-success', '__proto__', 'constructor', '']) {
    const presented = eventPresentation({...row, operation, title: '<script>invented title</script>'});
    assert.equal(presented.action, 'Recorded a project update');
    assert.equal(presented.summary, 'Project member recorded a project update');
    if (operation) assert.equal(presented.details[0]?.value, operation);
  }
  assert.equal(eventPresentation({...row, operation: 'document.save'}).action, 'Saved a document');
  assert.equal(eventPresentation({...row, operation: 'document.publish'}).action, 'Published a document');
});

test('missing or unusual accepted timestamps are not replaced or rounded by presentation', () => {
  assert.equal(eventPresentation({}).acceptedAt, '');
  const exact = '18446744073709551615';
  const presented = eventPresentation({...row, accepted_at_ms: exact});
  assert.equal(presented.acceptedAt, exact);
  assert.equal(presented.details.at(-1)?.value, exact);
  assert.equal(eventPresentation({...row, accepted_at_ms: 'invalid'}).acceptedAt, 'invalid');
});

// Synthetic verifier controls; these do not execute the human onboarding gate.
import test from 'node:test';
import assert from 'node:assert/strict';
import {acceptedReceipt, canonical, personalIdentity, sha, scope, workBody} from './onboarding-evidence.mjs';
const id = suffix => '019939ba-4000-7000-8000-' + suffix.padStart(12,'0');
const person = {principal_id:id('66'),binding_id:id('ca'),binding_revision:'1',identity_ship:'~bus',session_audit_id:'a'.repeat(64)};
const command = {protocol:'stead.command/3',request_id:id('301'),project_id:id('302'),resource_id:id('303'),
  expected_revision:'1',authority_epoch:'1',operation:'work.update',
  payload:{title:'Synthetic task',description:'Changed description',type:'task',status:'todo',priority:'none'}};
const receipt = {protocol:'stead.receipt/3',status:'accepted',request_id:command.request_id,
  canonical_sha256:sha(Buffer.concat([Buffer.from('stead.command/3\0'),Buffer.from(canonical(command))])),
  project_id:command.project_id,resource_id:command.resource_id,resource_kind:'work',container_id:'',
  resource_revision:'2',authority_epoch:'1',operation:'work.update',...person,
  authentication:'native-approved-browser/1',authentication_strength:'native-approved-browser',
  runtime:'isolated-fake',accepted_at_ms:'1790550000000',git_commit_oid:''};
test('synthetic receipt needs current identity and exact original request/body/scope/revision',() => {
  assert.equal(acceptedReceipt(command,receipt,person).request_id,command.request_id);
  for (const [key,value] of Object.entries({status:'proposed',request_id:id('304'),canonical_sha256:'b'.repeat(64),
    project_id:id('305'),resource_id:id('306'),resource_kind:'document',container_id:id('307'),resource_revision:'1',
    authority_epoch:'2',principal_id:id('65'),binding_id:id('cb'),binding_revision:'2',identity_ship:'~nec',
    session_audit_id:'b'.repeat(64),authentication:'native-ship/1',authentication_strength:'native-ship',
    runtime:'production',accepted_at_ms:'0',git_commit_oid:'f'.repeat(40)})) {
    assert.throws(() => acceptedReceipt(command,{...receipt,[key]:value},person),key);
  }
  assert.throws(() => acceptedReceipt(command,receipt,null));
  assert.throws(() => acceptedReceipt({...command,payload:{...command.payload,description:'Different'}},receipt,person));
  assert.throws(() => acceptedReceipt(command,{...receipt,extra:'unexpected'},person));
  const missing = {...receipt}; delete missing.canonical_sha256;
  assert.throws(() => acceptedReceipt(command,missing,person));
});
test('private document receipt requires its Git identity and original container',() => {
  const page = {...command,operation:'document.save',payload:{container_id:id('400'),markdown:'---\nSynthetic\n'}};
  const row = {...receipt,operation:page.operation,resource_kind:'document',container_id:page.payload.container_id,
    canonical_sha256:sha(Buffer.concat([Buffer.from('stead.command/3\0'),Buffer.from(canonical(page))])),git_commit_oid:'1'.repeat(40)};
  assert.equal(acceptedReceipt(page,row,person).git_commit_oid,row.git_commit_oid);
  assert.throws(() => acceptedReceipt(page,{...row,git_commit_oid:''},person));
  assert.throws(() => acceptedReceipt(page,{...row,container_id:id('401')},person));
});
test('identity evidence cannot switch participant or accept a mismatched query',() => {
  const query = {protocol:'stead.query/3',kind:'identity',request_id:id('500')};
  const result = {protocol:'stead.query-result/3',status:'read',kind:'identity',request_id:query.request_id,rows:{one:person}};
  assert.deepEqual(personalIdentity(query,result),person);
  assert.throws(() => personalIdentity(query,{...result,request_id:id('501')}));
  assert.throws(() => personalIdentity(query,{...result,rows:{}}));
  for (const [key,value] of Object.entries({identity_ship:'~nec',principal_id:id('67'),binding_id:id('cb'),
    binding_revision:'2',session_audit_id:'bad'})) {
    assert.throws(() => personalIdentity(query,{...result,rows:{one:{...person,[key]:value}}}),key);
  }
});
test('readback scope and full Work body prevent cross-scope or list-preview matches',() => {
  const original = scope(id('1'),'document',id('2'),id('3'));
  for (const values of [[id('4'),'document',id('2'),id('3')],[id('1'),'work',id('2'),id('3')],
    [id('1'),'document',id('4'),id('3')],[id('1'),'document',id('2'),id('4')]]) {
    assert.notEqual(scope(...values),original);
  }
  assert.equal(workBody(command.payload),workBody({...command.payload,irrelevant:'metadata'}));
  for (const key of ['title','description','type','status','priority']) {
    assert.notEqual(workBody(command.payload),workBody({...command.payload,[key]:'changed'}));
    const missing = {...command.payload}; delete missing[key]; assert.throws(() => workBody(missing));
  }
});

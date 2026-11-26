import test from 'node:test';
import assert from 'node:assert/strict';
import {permittedCommand, permittedCodeRead, exactApproval} from './namedObserverBoundary.mjs';
import {acceptedReceipt, personalIdentity, canonical, sha, scope, workBody, collectionReadback} from './namedObserverEvidence.mjs';
const HOME='https://home.example.invalid';
const id=n=>'019939ba-4000-7000-8000-'+n.padStart(12,'0');
const person={principal_id:id('66'),binding_id:id('ca'),binding_revision:'1',identity_ship:'~sampel-palnet',session_audit_id:'a'.repeat(64),runtime:'named-test'};
const command={protocol:'stead.command/3',request_id:id('301'),project_id:id('302'),resource_id:id('303'),expected_revision:'1',authority_epoch:'1',operation:'work.update',payload:{title:'Synthetic task',description:'Changed description',type:'task',status:'todo',priority:'none'}};
const row={protocol:'stead.receipt/3',status:'accepted',request_id:command.request_id,canonical_sha256:sha(Buffer.concat([Buffer.from('stead.command/3\0'),Buffer.from(canonical(command))])),project_id:command.project_id,resource_id:command.resource_id,resource_kind:'work',container_id:'',resource_revision:'2',authority_epoch:'1',operation:'work.update',...person,authentication:'native-approved-browser/1',authentication_strength:'native-approved-browser',accepted_at_ms:'1790550000000',git_commit_oid:''};
test('named receipt binds exact current actor runtime request body and revision',()=>{
  assert.equal(acceptedReceipt(command,row,person).request_id,command.request_id);
  for(const [key,value]of Object.entries({runtime:'isolated-fake',binding_revision:'2',session_audit_id:'b'.repeat(64),canonical_sha256:'c'.repeat(64),resource_revision:'1',project_id:id('999'),status:'proposed'}))assert.throws(()=>acceptedReceipt(command,{...row,[key]:value},person));
  assert.throws(()=>acceptedReceipt({...command,payload:{...command.payload,title:'Changed'}},row,person));
  assert.throws(()=>acceptedReceipt(command,row,null));
});
test('named identity must equal separately admitted member and fresh query',()=>{
  const q={protocol:'stead.query/3',kind:'identity',request_id:id('400')};
  const v={protocol:'stead.query-result/3',kind:'identity',request_id:q.request_id,status:'read',rows:{one:person}};
  assert.deepEqual(personalIdentity(q,v,person,'named-test'),person);
  for(const key of ['principal_id','binding_id','binding_revision','identity_ship'])assert.throws(()=>personalIdentity(q,{...v,rows:{one:{...person,[key]:'other'}}},person,'named-test'));
  assert.throws(()=>personalIdentity(q,{...v,request_id:id('401')},person,'named-test'));
  assert.throws(()=>personalIdentity(q,v,person,''));
});
test('mutation fence blocks before Start after stop and cross project effects',()=>{
  const made={work:new Set([command.resource_id]),container:new Set(),document:new Set()};
  assert.equal(permittedCommand(command,command.project_id,made,true,person),true);
  for(const [start,who,project]of [[false,person,command.project_id],[true,null,command.project_id],[true,person,id('999')]])assert.equal(permittedCommand(command,project,made,start,who),false);
  for(const operation of ['project.create','grant.set','work.delete','document.publish','identity.configure'])assert.equal(permittedCommand({...command,operation},command.project_id,made,true,person),false);
  const read={protocol:'stead.code/1',action:'work-delegations',project_id:command.project_id,work_id:id('777')};
  // A real read may precede passive receipt capture for this new Work.
  assert.equal(made.work.has(read.work_id),false);
  assert.equal(permittedCodeRead(read,command.project_id),true);
  for(const change of [{action:'delegate'},{project_id:id('999')},{work_id:'not-a-uuid'},{extra:'field'},{protocol:'other'}])
    assert.equal(permittedCodeRead({...read,...change},command.project_id),false);
  assert.equal(permittedCodeRead(null,command.project_id),false);
});
test('only session-created objects can be edited and new collections stay private',()=>{
  const made={work:new Set(),container:new Set(),document:new Set()};
  assert.equal(permittedCommand(command,command.project_id,made,true,person),false);
  assert.equal(permittedCommand({...command,operation:'work.create',expected_revision:'0'},command.project_id,made,true,person),true);
  const create={...command,operation:'container.create',expected_revision:'0',payload:{visibility:'private'}};
  assert.equal(permittedCommand(create,command.project_id,made,true,person),true);
  assert.equal(permittedCommand({...create,payload:{visibility:'shared'}},command.project_id,made,true,person),false);
  const doc={...command,operation:'document.save',expected_revision:'0',payload:{container_id:id('500'),markdown:'Synthetic'}};
  assert.equal(permittedCommand(doc,command.project_id,made,true,person),false);made.container.add(id('500'));
  assert.equal(permittedCommand(doc,command.project_id,made,true,person),true);
  assert.equal(permittedCommand({...doc,expected_revision:'1'},command.project_id,made,true,person),false);made.document.add(command.resource_id);
  assert.equal(permittedCommand({...doc,expected_revision:'1'},command.project_id,made,true,person),true);
});
test('approval never accepts similar origins other members or malformed comparison',()=>{
  const text='Home\n'+HOME+'\nIdentity\n~sampel-palnet';
  assert.equal(exactApproval(text,'a'.repeat(12),'~sampel-palnet',HOME),true);
  for(const other of [text.replace(HOME,HOME+'.evil'),text.replace('~sampel-palnet','~sampel-palnet-other'),text.replace(HOME,'http://home.example.invalid')])assert.equal(exactApproval(other,'a'.repeat(12),'~sampel-palnet',HOME),false);
  assert.equal(exactApproval(text,'a'.repeat(11),'~sampel-palnet',HOME),false);
});
test('readback uses full Work body and exact project collection resource scope',()=>{
  assert.equal(workBody(command.payload),workBody({...command.payload,other:'ignored'}));
  for(const key of ['title','description','type','status','priority'])assert.notEqual(workBody(command.payload),workBody({...command.payload,[key]:'different'}));
  assert.notEqual(scope(id('1'),'document',id('2'),id('3')),scope(id('1'),'document',id('4'),id('3')));
});
test('document receipt requires exact original container and Git content identity',()=>{
  const c={...command,operation:'document.save',payload:{container_id:id('500'),markdown:'Synthetic\n'}};
  const r={...row,operation:c.operation,resource_kind:'document',container_id:id('500'),git_commit_oid:'1'.repeat(40),canonical_sha256:sha(Buffer.concat([Buffer.from('stead.command/3\0'),Buffer.from(canonical(c))]))};
  assert.equal(acceptedReceipt(c,r,person).git_commit_oid,r.git_commit_oid);
  assert.throws(()=>acceptedReceipt(c,{...r,container_id:id('501')},person));assert.throws(()=>acceptedReceipt(c,{...r,git_commit_oid:''},person));
});
test('private collection readback binds receipt and rejects changed visibility',()=>{
  const accepted={operation:'container.create',visibility:'private',project_id:id('1'),container_id:id('2'),resource_id:id('2'),resource_revision:'1',request_id:id('3')};
  const q={protocol:'stead.query/3',kind:'containers',project_id:id('1'),container_id:'',resource_id:'',request_id:id('4')};
  const container={kind:'container',container_id:id('2'),resource_id:id('2'),resource_revision:'1',visibility:'private'};
  const v={...q,protocol:'stead.query-result/3',status:'read',rows:{one:container}};
  assert.equal(collectionReadback(q,v,accepted).visibility,'private');
  assert.throws(()=>collectionReadback(q,{...v,rows:{one:{...container,visibility:'shared'}}},accepted));
  assert.throws(()=>collectionReadback(q,{...v,request_id:id('5')},accepted));
});

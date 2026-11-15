import test from 'node:test';
import assert from 'node:assert/strict';
import {agentBrief} from '../src/agentBrief';
import {type Row, type WorkDelegation} from '../src/api';
const project='019939ba-4000-7000-8000-000000000001';
const item='019939ba-4000-7000-8000-000000000002';
const grant:WorkDelegation={id:'019939ba-4000-7000-8000-000000000003',worker:'~bus',expires:'10000',ref:'refs/heads/main',status:'active',revocable:true,proposals:[]};
const work:Row={resource_id:item,resource_revision:'4',title:'Exact title ',description:'Keep bytes\n'};
test('brief uses canonical Work link independent of the current view and preserves legacy pin',()=>{
  const brief=JSON.parse(agentBrief(project,work,grant,'https://home.test'));
  assert.equal(brief.work_url,`https://home.test/stead/#work/${project}/${item}`);
  assert.equal(brief.protocol,'stead.agent-brief/1');assert.equal(brief.work_revision,'4');
  assert.equal(brief.title,work.title);assert.equal(brief.description,work.description);
});
test('complete execution pin survives comment revisions without silently downgrading malformed pins',()=>{
  const pinned={...work,execution_contract_protocol:'stead.work-contract/1',execution_contract_revision:'2',execution_contract_digest:'a'.repeat(64)};
  const brief=JSON.parse(agentBrief(project,pinned,grant,'https://home.test'));
  assert.equal(brief.protocol,'stead.agent-brief/2');assert.equal(brief.execution_contract_revision,'2');
  assert.equal(brief.work_revision,undefined);assert.equal(brief.execution_contract_protocol,undefined);
  assert.equal(agentBrief(project,pinned,grant,'https://home.test'),agentBrief(project,{...pinned,resource_revision:'5'},grant,'https://home.test'));
  for(const invalid of [{...work,execution_contract_revision:'2'},{...pinned,execution_contract_digest:'bad'},
    {...pinned,execution_contract_protocol:'future'},{...pinned,execution_contract_revision:'18446744073709551616'}])
    assert.throws(()=>agentBrief(project,invalid,grant,'https://home.test'));
  assert.throws(()=>agentBrief(project,pinned,{...grant,status:'revoked'},'https://home.test'));
});

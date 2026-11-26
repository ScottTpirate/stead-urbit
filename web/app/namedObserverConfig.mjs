// Admission data is supplied by the operator; this validator creates no grant.
import assert from 'node:assert/strict';
const fields=(value,names)=>{
  assert.ok(value&&typeof value==='object'&&!Array.isArray(value));
  assert.deepEqual(Object.keys(value).sort(),[...names].sort());
};
export function validateConfig(value) {
  fields(value,['protocol','source','origins','forward_ports','pins','person','project',
    'synthetic_project_confirmed','admission_observed_at_unix']);
  assert.equal(value.protocol,'stead.named-human-observer/1');
  assert.match(value.source,/^[0-9a-f]{40}$/u);
  for(const name of ['origins','forward_ports','pins'])fields(value[name],['home','identity']);
  for(const name of ['home','identity']){
    assert.equal(typeof value.origins[name],'string');
    const url=new URL(value.origins[name]);
    assert.equal(url.protocol,'https:');assert.equal(url.origin,value.origins[name]);
    assert.match(url.hostname,/^[a-z0-9.-]+$/u);
    assert.ok(Number.isInteger(value.forward_ports[name])&&value.forward_ports[name]>=1024&&value.forward_ports[name]<=65535);
    assert.match(value.pins[name],/^[A-Za-z0-9+/]{43}=$/u);
  }
  assert.notEqual(value.origins.home,value.origins.identity);
  fields(value.person,['principal_id','binding_id','binding_revision','identity_ship','authentication','authentication_strength']);
  const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u;
  for(const name of ['principal_id','binding_id'])assert.match(value.person[name],uuid);
  assert.match(value.person.binding_revision,/^[1-9][0-9]{0,19}$/u);
  assert.ok(BigInt(value.person.binding_revision)<2n**64n);
  assert.match(value.person.identity_ship,/^~[a-z-]{3,80}$/u);
  assert.equal(value.person.authentication,'native-approved-browser/1');
  assert.equal(value.person.authentication_strength,'native-approved-browser');
  fields(value.project,['id','title']);assert.match(value.project.id,uuid);
  assert.equal(typeof value.project.title,'string');assert.ok(value.project.title.length>0&&value.project.title.length<=128);
  assert.equal(value.synthetic_project_confirmed,true);
  assert.ok(Number.isSafeInteger(value.admission_observed_at_unix)&&value.admission_observed_at_unix>0);
  return value;
}

import test from 'node:test';
import assert from 'node:assert/strict';
import {validateConfig} from './namedObserverConfig.mjs';
const id=n=>'019939ba-4000-7000-8000-'+n.padStart(12,'0');
const sample=()=>({protocol:'stead.named-human-observer/1',source:'a'.repeat(40),
  origins:{home:'https://home.example.invalid',identity:'https://identity.example.invalid'},
  forward_ports:{home:14043,identity:14044},pins:{home:'A'.repeat(43)+'=',identity:'B'.repeat(43)+'='},
  person:{principal_id:id('1'),binding_id:id('2'),binding_revision:'1',identity_ship:'~sampel-palnet',
    authentication:'native-approved-browser/1',authentication_strength:'native-approved-browser'},
  project:{id:id('3'),title:'Synthetic garden'},synthetic_project_confirmed:true,admission_observed_at_unix:1});
test('operator config is closed and admits only explicit synthetic profile metadata',()=>{
  const value=sample();assert.equal(validateConfig(value),value);
  for(const change of [{synthetic_project_confirmed:false},{source:'branch'},{secret:'not-allowed'},
    {admission_observed_at_unix:'1'},{person:{...value.person,code:'not-allowed'}}])
    assert.throws(()=>validateConfig({...value,...change}));
});
test('origin forwarding and member pins reject ambiguous or weakened configuration',()=>{
  for(const mutate of [v=>v.origins.home='http://home.example.invalid',
    v=>v.origins.home='https://user:password@home.example.invalid',v=>v.origins.home+='/',
    v=>v.origins.identity=v.origins.home,v=>v.forward_ports.home=0,v=>v.forward_ports.home='14043',
    v=>v.forward_ports.extra=18445,v=>v.pins.home='disabled',v=>v.person.binding_revision='0',
    v=>v.person.binding_revision='18446744073709551616',v=>v.person.authentication='owner',
    v=>v.project.id='../other',v=>v.project.title='']){
    const value=sample();mutate(value);assert.throws(()=>validateConfig(value));
  }
});

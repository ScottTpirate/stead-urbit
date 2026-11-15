import test from 'node:test';
import assert from 'node:assert/strict';
import {formatLines} from '../src/documentFormatting';
test('block formatting operates on complete selected lines while preserving surrounding source',()=>{
  assert.deepEqual(formatLines('Before\nA long line\nAfter',10,10,'heading'),{text:'Before\n# A long line\nAfter',start:12,end:12});
  assert.deepEqual(formatLines('One\nTwo\nThree',0,8,'list'),{text:'- One\n- Two\nThree',start:2,end:12});
  assert.equal(formatLines('One\nTwo\nThree',5,6,'list').text,'One\n- Two\nThree');
  assert.equal(formatLines('One\n\nThree',4,4,'heading').text,'One\n# \nThree');
});
test('existing markers are replaced without nesting and empty text remains editable',()=>{
  assert.equal(formatLines('### Existing',8,8,'heading').text,'# Existing');
  assert.equal(formatLines('1. One\n* Two',0,12,'list').text,'- One\n- Two');
  assert.deepEqual(formatLines('',0,0,'list'),{text:'- ',start:2,end:2});
  assert.deepEqual(formatLines('😀 Notes',3,3,'heading'),{text:'# 😀 Notes',start:5,end:5});
});

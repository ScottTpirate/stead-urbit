import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import test from 'node:test';
import {renderToStaticMarkup} from 'react-dom/server';
import {ShipSigil} from '../src/ShipSigil';
import {shipGlyphs} from '../src/shipSigilGlyphs';

const render = (ship?: string) => renderToStaticMarkup(<ShipSigil ship={ship}/>);

test('all small sigil shapes, phonemes and positions match the pinned Urbit sources', () => {
  // Digest of sorted position|syllable|element|stroke|path rows taken independently
  // from sigil-js e86b674 / urbit-ob 3808c27. Circles and rectangles have fixed size.
  const rows: string[] = [];
  const unique = new Set<string>();
  for (const glyph of shipGlyphs) {
    for (const position of ['prefix', 'suffix'] as const) {
      const syllables = position === 'prefix' ? glyph.prefixes : glyph.suffixes;
      for (const syllable of syllables.match(/[a-z]{3}/g) ?? []) {
        assert.ok(!unique.has(syllable));
        unique.add(syllable);
        rows.push([position, syllable, glyph.kind, glyph.border ? '@BG' : '-', glyph.d ?? '-'].join('|'));
      }
    }
  }
  assert.equal(unique.size, 512);
  assert.equal(createHash('sha256').update(rows.sort().join('\n') + '\n').digest('hex'),
    '52699c03b9f7015bf3621d439ffbba60154607cc76b0021824675971fc5fa034');
});

test('a real profile renders the supported ship class with the canonical cell order and thematic ink', () => {
  assert.match(render('~zod'), /scale\(2\)/);
  assert.match(render('~marzod'), /translate\(0 64\)/);
  const planet = render('~tagdep-salled');
  assert.equal((planet.match(/<g transform="translate\(/g) ?? []).length, 4);
  assert.match(planet, /translate\(0 0\).*translate\(128 0\).*translate\(0 128\).*translate\(128 128\)/);
  assert.match(planet, /aria-hidden="true"/);
  assert.match(planet, /fill="var\(--ink\)"/);
  assert.doesNotMatch(planet, /href=|src=|tagdep/);
});

test('unsupported, missing and invalid ship identifiers leave the account text alone', () => {
  for (const ship of [undefined, '', 'bus', '~doz', '~zodzod', '~zzzzzz-zzzzzz', '~tagdep-salled-sampel-palnet']) {
    assert.equal(render(ship), '');
  }
});

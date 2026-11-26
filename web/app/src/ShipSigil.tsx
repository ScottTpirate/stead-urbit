import {shipGlyphs, type ShipGlyph} from './shipSigilGlyphs';

const prefix = new Map<string, ShipGlyph>();
const suffix = new Map<string, ShipGlyph>();
for (const glyph of shipGlyphs) {
  for (const syllable of glyph.prefixes.match(/[a-z]{3}/g) ?? []) prefix.set(syllable, glyph);
  for (const syllable of glyph.suffixes.match(/[a-z]{3}/g) ?? []) suffix.set(syllable, glyph);
}

function symbolsFor(ship: string | undefined) {
  if (!ship || !/^~(?:[a-z]{3}|[a-z]{6}(?:-[a-z]{6})?)$/u.test(ship)) return [];
  const syllables = ship.slice(1).replace('-', '').match(/.{3}/g)!;
  const symbols: ShipGlyph[] = [];
  for (const [index, syllable] of syllables.entries()) {
    const lookup = syllables.length > 1 && index % 2 === 0 ? prefix : suffix;
    const glyph = lookup.get(syllable);
    if (!glyph) return [];
    symbols.push(glyph);
  }
  return symbols;
}

/** The adjacent name and @p supply the accessible identity, including unsupported ship classes. */
export function ShipSigil({ship}: {ship?: string}) {
  const symbols = symbolsFor(ship);
  if (!symbols.length) return null;
  // sigil-js detail:none, space:none. Center a star's two-cell row inside the square slot.
  const group = symbols.length === 1 ? 'scale(2)' : symbols.length === 2 ? 'translate(0 64)' : undefined;
  return <svg width="28" height="28" viewBox="0 0 256 256" className="ship-sigil"
    focusable="false" aria-hidden="true" fill="var(--ink)">
    <rect width="256" height="256" fill="var(--paper)"/>
    <g transform={group} strokeWidth={256 / 28}>
      {symbols.map((glyph, index) => <g key={index} transform={`translate(${(index % 2) * 128} ${Math.floor(index / 2) * 128})`}
        stroke={glyph.border ? 'var(--paper)' : 'none'}>
        {glyph.kind === 'circle' ? <circle cx="64" cy="64" r="64"/> :
          glyph.kind === 'rect' ? <rect width="128" height="128"/> : <path d={glyph.d}/>}
      </g>)}
    </g>
  </svg>;
}

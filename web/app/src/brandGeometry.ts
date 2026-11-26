// The four closed paths of the original Stead design. Coordinates use a unit square.
export const steadPaths = [
  'M .4828 0 V .4164 H .3992 V .5172 H 0 V .4828 A .4828 .4828 0 0 1 .4828 0 Z',
  'M .5172 0 H 1 V .5517 A .4828 .2984 0 0 0 .5172 .2533 Z',
  'M 0 .5517 A .3647 .2295 0 0 0 .3647 .7812 V 1 H 0 Z',
  'M .6008 .4164 H .7082 A .2918 .2918 0 0 1 .7082 1 H .3992 V .6353 H .6008 Z',
] as const;

// The compact master is drawn on a 16-unit grid. Its top and bottom vertical
// seams are each 1.5 units wide, so they survive favicon rasterization.
export const compactSteadPaths = [
  'M7 0V6H5.75V7.5H0V7A7 7 0 0 1 7 0Z',
  'M8.5 0H16V8.5A7.5 5 0 0 0 8.5 3.5Z',
  'M0 9A5.5 3.5 0 0 0 5.5 12.5V16H0Z',
  'M9.5 6.5H11.25A4.75 4.75 0 0 1 11.25 16H7V10.5H9.5Z',
] as const;

export const sectionPaths = {
  project: compactSteadPaths,
  work: [
    'M0 6V4A4 4 0 0 1 4 0H6V4H4V6Z',
    'M8 1H14A2 2 0 0 1 14 5H8Z',
    'M0 15V13A4 4 0 0 1 4 9H6V13H4V15Z',
    'M8 10H14A2 2 0 0 1 14 14H8Z',
  ],
  documents: [
    'M0 2H3A4 4 0 0 1 7 6V15A5 5 0 0 0 2 12H0Z',
    'M9 6A4 4 0 0 1 13 2H16V12H14A5 5 0 0 0 9 15Z',
  ],
  code: [
    'M6 1V4H4V6H3V12H6V15H0V7A6 6 0 0 1 6 1Z',
    'M10 15V12H12V10H13V4H10V1H16V9A6 6 0 0 1 10 15Z',
  ],
} as const;

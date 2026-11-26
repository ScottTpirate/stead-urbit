# Frontend source and dependency provenance

This is a new client for the native home. The archived backend, routes and
deployment stack are not application dependencies.

`src/primitives.tsx` is copied from original Stead commit
`3d47f0172a41beebb31f5c3a7df133cc1d4b1ead`, path
`packages/design-system/src/primitives.tsx`, retained locally as
`reference/stead/packages/design-system/src/primitives.tsx`.
Original file SHA-256:
`f900568a7229e1a7dadbd0ae00496a7dec7757379c70ba577a814418ee639336`.
Its Apache-2.0 license remains in `reference/stead/LICENSE` and the root LICENSE.
The reusable behavior is labelled inputs, pending buttons, empty/error states
and exclusion of resource-loading/raw-HTML DOM properties. No old feature or
authorization acceptance transfers. Native browser tests must exercise the new
usage and hostile Markdown independently.

The Node 24.21.0/npm 11.19.0 executable remains the pinned repository toolchain.
Direct dependencies were resolved from the official npm registry on 2026-09-27:
React/React DOM 19.3.0 (MIT), React type packages 19.3.0 (MIT), esbuild 0.28.2
(MIT), TypeScript 7.0.2 (Apache-2.0), and Playwright 1.63.0 (Apache-2.0).
`package-lock.json` pins all transitive artifacts by registry integrity.
Only React, React DOM and scheduler are browser runtime dependencies; compiler,
bundler, types and Playwright are development/test tools.

Installation uses the repository-local npm cache and `npm ci --ignore-scripts`.
No package lifecycle script is permitted. Esbuild and TypeScript use their
lockfile-pinned platform packages. The installed Linux package license/notice
files must be preserved in the dependency notice artifact. Esbuild's native
platform package is covered by the accompanying esbuild MIT license. Playwright
and TypeScript include third-party notices; retain these unchanged. Browser
archives and their licenses require separate pinning before browser tests.

The initial registry vulnerability audit reported zero known findings across
56 locked dependencies. This is a time-specific registry observation, not proof
of safety or native/browser test acceptance. Any lockfile update requires a new
audit, notices and independent review. No browser test has yet been executed for
this package.

## Product Docs parser, November 15, 2026

The Docs slice adds exact `markdown-it` 15.0.3 from the official npm registry
(MIT, SHA-512 integrity pinned in package-lock.json). Its token parser supplies
CommonMark and the documented tables/strikethrough subset. Stead renders only
explicit React elements, with HTML/linkify/typographer disabled and maximum
nesting20. Images become deliberate attachment links; rendering never loads
remote images. ResourceLink rejects executable, credential-bearing and
protocol-relative URLs and sets no-referrer/noopener/noreferrer.

The locked additions are mdurl2.1.0 (MIT), entities8.1.0 (BSD-2-Clause),
uc.micro3.0.0 (MIT), linkify-it6.1.0 (MIT), punycode.js2.3.1 (MIT), and
argparse3.0.4 (PSF-2.0, CLI dependency). Actual installed license texts were
inspected; all are included by the release notice builder, including the CLI
license as a conservative package-distribution record. No lifecycle scripts ran.
The registry audit at installation reported zero known vulnerabilities across
20 installed packages; this is time-specific metadata, not a security proof.
Source tests cover structured Markdown, literal hostile HTML, suppressed image
loads, unsafe URL schemes and bounded dense/oversized content. Runtime/browser
qualification remains separate and must name the exact candidate.

Upstream references: [parser and license](https://github.com/markdown-it/markdown-it),
[safety model](https://github.com/markdown-it/markdown-it/blob/master/docs/safety.md),
[version15 changes](https://github.com/markdown-it/markdown-it/blob/master/CHANGELOG.md).

## Handbook example repository

The Handbook Code tab reads a three-object Git repository built from
`web/app/src/handbook/README.md`. After changing that file run
`python3 web/app/handbook-repository.py --update` from the repository root.
The command rebuilds the Git blob, tree, commit and snapshot in a temporary
directory and updates the release identifiers in the browser adapter. Run
`python3 web/app/handbook-repository.py` to check them. The Handbook CI job
also opens the root tree and file through the same read-only adapter used by
the project’s Code tab.

## Profile ship sigils

A member's galaxy, star or planet uses Urbit's official 28 px icon vocabulary
(`detail: none`, `space: none`). The account name and ship address remain the
identity labels. The renderer centers a star's rectangular sigil in its square
avatar slot. For ship classes outside the official generator, the account
uses its text label. The browser matches phonemes in memory.

The 512 syllables in the official small-size index resolve to 14 distinct SVG
element records. The local table deduplicates identical records and retains the
exact paths, circle/rectangle dimensions, stroke choices and syllable assignments.
Some different ships therefore share the same small-size silhouette. The profile
uses ordinary React SVG elements in the active theme. The distribution includes
Tlon's MIT license for both upstream sources in `NOTICE.txt`.

[Official icon index and revision](https://github.com/urbit/sigil-js/blob/e86b674a4a3539ddc634351f335ac31d63bf64bd/src/symbols/icon.ts) ·
[Official layout](https://github.com/urbit/sigil-js/blob/e86b674a4a3539ddc634351f335ac31d63bf64bd/src/core.ts) ·
[Prefix and suffix positions](https://github.com/urbit/urbit-ob/blob/3808c277fba9444a30946fc38c84c4751eae8d5f/src/internal/co.js)

## Stead mark comparison

The [offline comparison](tests/ship-sigil-audit.py) renders the application’s
five distinct marks and the pinned official generator’s geometry at 256 px.
It checks the galaxy, star and planet layouts, both detail settings, all three
spacing settings and both monochrome polarities. For each possible first
syllable it counts solid pixels that disagree with Stead and that no later
syllable can cover. The lower bounds were 962 pixels for the original master,
2,747 for compact/Overview, 4,657 for Work, 2,534 for Docs and 3,407 for Code.
These bounds establish a difference for those stock renderings. They measure
neither perceived similarity at avatar size nor third-party marks.

To reproduce, use Node 24 and Python with Cairo and GI/librsvg. Run the
following from the repository root, pointing it at the official revision above.

```sh
python3 web/app/tests/ship-sigil-audit.py /path/to/sigil-js
python3 web/app/tests/ship-sigil-audit.py /path/to/sigil-js --display-sizes
```

The second command tests the same 18 generator layouts with the official
small-size stroke widths. It renders black on white and white on black in
librsvg. Within each cell it counts only pixels that no other glyph can
cover. Each number below is a lower bound on pixels that differ by at least
96 grayscale levels out of 255, across every syllable combination and both
color arrangements. For example, at 12 px even the compact mark differs in at
least 10 of the 144 pixels. This describes the tested rasterizer at one device
pixel per image pixel. Human recognition also depends on the screen and size.

| Size | Original | Compact / Overview | Work | Docs | Code |
| --- | ---: | ---: | ---: | ---: | ---: |
| 12 px | 11 | 10 | 11 | 13 | 13 |
| 14 px | 18 | 18 | 17 | 18 | 22 |
| 16 px | 29 | 30 | 38 | 31 | 38 |
| 28 px | 143 | 173 | 179 | 128 | 171 |
| 34 px | 215 | 261 | 282 | 211 | 276 |

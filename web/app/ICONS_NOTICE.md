# Local icon source and review

`src/Icon.tsx` contains eight Lucide shapes from
[Lucide commit 55782beff3a0133df79c417eb68f96e8f19e2404](https://github.com/lucide-icons/lucide/tree/55782beff3a0133df79c417eb68f96e8f19e2404).
The exact upstream SVGs, full ISC/MIT copyright and license notices, Git blob
identities and SHA-256 digests are retained in `vendor/lucide/`. Each downloaded
file was checked against its Git blob identity before inclusion. No package or
browser network dependency is added. Release dependency notices must include
`vendor/lucide/LICENSE` unchanged.

The reviewed subset is chevron-down, check, circle, circle-exclamation-point,
ellipsis, plus, x and search. Only fixed `path`, `circle` and `line` geometry is
rendered inside a fixed 16 px SVG. The shapes retain Lucide's 24-unit view box,
two-unit stroke, rounded joins and current text color. `Icon` accepts only a
closed icon name; it does not forward attributes, children, URLs, styles,
raw markup, event handlers or resource-loading SVG elements. An unknown runtime
name renders nothing. The original files are provenance material and are not
loaded by the browser.

Icons are decorative and hidden from accessibility APIs. Controls must retain a
visible label or an accessible name; status keeps readable text alongside its
shape. Button hit areas are at least 32 px and become 44 px for coarse pointers.
Theme text/focus contrast and keyboard behavior are exercised by the synthetic
interaction reference. This source review does not claim native authorization
or attended usability qualification.

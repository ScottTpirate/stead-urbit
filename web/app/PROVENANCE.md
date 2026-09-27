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

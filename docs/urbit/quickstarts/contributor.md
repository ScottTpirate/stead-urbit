# Linux contributor quickstart

Work in a checkout of `ScottTpirate/stead-urbit`. Check `git remote -v`; the
original `ScottTpirate/stead` repository is read-only. Read `AGENTS.md` and
[`AGENT_HANDOFF.md`](../AGENT_HANDOFF.md) before implementation.

```sh
make setup
make doctor
make check
```

Setup downloads only the pinned artifacts and verifies their hashes. Doctor
checks this Linux host's namespace and toolchain prerequisites. Check runs host
tests and metadata checks; it does not compile Hoon. A refused prerequisite
needs fixing before continuing. Do not substitute an arbitrary runtime or boot
image to make the command start.

Prepare the browser dependencies before starting the native fixture. From the
repository root, use the pinned Node and npm installed by `make setup`:

```sh
.runtime/node-v24.21.0-linux-x64/bin/node .runtime/node-v24.21.0-linux-x64/lib/node_modules/npm/bin/npm-cli.js ci --prefix web/app --cache "$PWD/.runtime/npm-cache" --ignore-scripts --include=optional
PLAYWRIGHT_BROWSERS_PATH="$PWD/.runtime/playwright" .runtime/node-v24.21.0-linux-x64/bin/node web/app/node_modules/playwright/cli.js install --no-remove firefox
```

The host also needs `/usr/bin/certutil` (the `nss` package on Arch), Firefox's
shared-library dependencies, user namespaces and user systemd/cgroups. Browser
files stay under `.runtime/playwright`, with trust confined to each disposable
test profile. See [browser preparation](../DEV_FLOW.md#frontend-build-and-browser-feedback)
for the boundary between repository installation and host prerequisites.

For a configured native development fixture:

```sh
make preflight
make team-dev
```

The first configured run needs verified stopped seeds from the ordinary
`make dev` fixture. On a fresh checkout, run `make dev` once, wait for its native
checks, and run `make stop` before `make team-dev`. Team-dev compiles the native
code, exercises four synthetic identities and cold restarts, then leaves the
guarded fixture running. It has no purchased identities or public network home.
Use public or synthetic content only.

In another terminal, execute the actual browser journey:

```sh
python3 web/app/browser-check.py
```

It uses a private Firefox trust profile and the fixture's owned native TLS
listeners. Evidence is printed under `.runtime/browser-native-*`. This command
is automated; it does not open a persistent personal workspace. When finished:

```sh
make stop
```

For frontend edits, use the pinned Node executable installed by setup:

```sh
.runtime/node-v24.21.0-linux-x64/bin/node web/app/node_modules/typescript/bin/tsc --noEmit --project web/app/tsconfig.json
.runtime/node-v24.21.0-linux-x64/bin/node web/app/tests/run.mjs
.runtime/node-v24.21.0-linux-x64/bin/node web/app/build.mjs
.runtime/node-v24.21.0-linux-x64/bin/node web/app/package-desk.mjs
```

Use the locked frontend dependencies installed above. The build bundles and
splits the frontend; packaging writes the content-addressed native desk assets.
Stop the fixture before packaging or changing native/harness inputs. Preserve
the previous stopped state and evidence before another disposable run. Keep the
verified `.piers/fakes/seed` directory in place.

Run host and native suites sequentially on a busy workstation. Thermal refusal
and interruption are failed admission/execution outcomes, not passing tests.
The regular edit loop uses focused checks; full qualification is reserved for
the behaviors affected by the change. Commit the exact tested source, retain
failures, and request independent review before integration.

# Local development and testing

Use this Linux workstation for development. The existing harness runs four
disposable fake Urbit ships in one private network namespace: home, contributor,
reader and outsider. They execute the real pinned runtime and Hoon, with separate
state directories. They need no purchased identities, public server, GPU or cloud
account. Fake ships do not join the live Urbit network.

Use public/synthetic content. The complete native Phase 1 gate now passes;
[acceptance and scope](PHASE1_ACCEPTANCE_20260926.md) are recorded separately.
The first browser slice now runs against actual native TLS and individually
approved member sessions; its [executed scope](evidence/2026-09-27/browser-first/README.md)
is recorded separately. Phase 2 remains open, and these local tests do not
authorize company data.

## Runtime pin

The current development pin is Vere 4.6 with the single upstream newt repair
recorded in `specs/urbit/toolchain.lock.json`. `make setup` downloads its roughly
9.7 MB verified binary archive once. Ordinary Hoon or frontend edits do not
rebuild Vere. The complete source/compiler/dependency inputs, patch, notices,
recipe and build observations accompany the development prerelease.

The unchanged runtime regression passed with same-process recovery and clean
exit. Full application, SDK, browser and hosted CI results must bind to this new
binary; old-runtime results do not transfer. Existing fixtures with the old
lock remain rejected. Preserve them and create fresh disposable seeds for this
pin; do not edit their manifests or copy a production pier.

## Commands

`make` prints help without downloading or starting anything.

For GitHub CLI operations, explicitly pass `--repo ScottTpirate/stead-urbit`
(or use the exact derivative repository API path). This fork's CLI can resolve
an unqualified command to the original upstream repository even when `origin`
points here. Verify origin's fetch and push URLs before writing; upstream remains
read-only.

| Command | Purpose | What it establishes |
| --- | --- | --- |
| `make setup` | Fetch and verify the exact pinned runtime, boot and Node artifacts | Reproducible local inputs |
| `make doctor` | Check pins, prerequisites and real namespace isolation | Whether this Linux host supports the harness |
| `make preflight` | Read current temperature admission without launching ships | A current sample, not a promise that a later launch will pass |
| `make check` | Run planning, both contract freezes and host tests | Host/static/mocked results only |
| `make frontend-check` | Run pinned TypeScript and client tests with bounded CPU | Host frontend results; starts no ships or browser |
| `make frontend-build` | Bundle the frontend and record asset hashes | Build output only; does not install into a running ship |
| `make dev` | Start the guarded supervisor, wait for readiness, compile the core and run pure probes | Native compile/probe evidence when it actually passes |
| `make status` | Report stopped, booting, compiling or ready state | Current lifecycle state; an unresponsive owner is not reported as stopped |
| `make core-check` | Reinstall edited Hoon into a fresh fake fixture and rerun compilation/probes | Shorter native feedback, separate from acceptance |
| `make team-dev` | Restore verified seeds, compile configured homes and personal helpers, then exercise four ships and cold restarts | Configured native development evidence; a successful run leaves the guarded fixture available |
| `make team-check` | Repeat the configured four-ship development checks in the running matching supervisor | Replaces disposable test data; preserve any prior evidence first |
| `make sdk-dev SDK_ARCHIVE=<archive>` | Compile and exercise a public-only consumer using three fresh fake identities across two isolated namespaces | Independent SDK candidate; retain actual run status and cleanup |
| `make migration-dev` | Run the exact trusted CI migration generator on one guarded fake ship, then stop | Focused diagnostic with private compiler evidence; not full CI acceptance |
| `make ci-controls-dev` | Reproduce the trusted CI compiler, missing-arm, timeout and frame controls on one guarded fake ship, then stop | Focused diagnostic; not hosted CI or full team acceptance |
| `python3 web/app/browser-check.py` | Run Firefox against the live configured fixture, using its own disposable certificate profile | Real browser/native TLS evidence for the cases actually executed |
| `make test` | Run the original four-identity counter smoke | Native allow/deny, failure propagation and restart |
| `make core-test` | Run the full current Work/Docs qualification corpus | Business, access, delivery, migration and export evidence; missing requirements still fail |
| `make delivery-check` | Run two bounded offline-home timeout/recovery cycles on a fresh fake fixture | Focused lifecycle regression only; never full Phase 1 acceptance |
| `make capacity-check` | Run the eight capacity and predecessor recipes on a fresh fake fixture | Focused diagnostic; never full Phase 1 acceptance |
| `make gall-schedule` | Run actual pinned Gall/app gates with a controlled queue and clock | The delayed old-leave case; no Ames/network identity claim |
| `make skill-prequalify` | Run frozen workflow reference, oracle and mutant controls | Prerequisite for the separate skill evaluation; no participant result |
| `make stop` | Stop the owned ships and release their lifecycle lock | Clean local shutdown |
| `make reset` | Restore verified, stopped disposable fake seeds | Fresh synthetic state after preserving a failed run; never a Git reset |

Run each native command sequentially. Start once, then use `make core-check`
after Hoon edits. After changing any Python harness/runner module, use
`make stop` followed by `make dev`: the supervisor pins its loaded code and
rejects changed files. Do not run a test against a stale supervisor.

The first cold initialization boots four identities sequentially, creates clean
stopped seeds and restarts them. `make dev` waits within the existing two-hour
guarded lifetime for that complete initialization; the former 20-minute caller
wait could expire before four individually bounded boots finished. Each ship
still has its 20-minute readiness deadline, and the outer execution deadline,
thermal limits, CPU limit and native test deadlines are unchanged. Later runs
reuse only the verified clean seeds for the same toolchain.

The native checks restore only marked, stopped, hash-verified fake seeds. Test
data is disposable and is replaced by the next check. They never reset Git or
replace working source. A future interactive team-development fixture will need
its own explicit preservation/reset behavior before users enter lasting data.

## What happens after an edit

Hoon source lives in `native/core/desk/`. The runner copies it into the disposable
mounted development desk and asks Hood to commit the changes to Clay, Urbit's
versioned filesystem. It reads the imported bytes back through Clay and compares
their hashes. The native build probe imports the home agent, client, observer
and marks; further probes exercise the codec and pure reducers. A compiler error,
wrong probe result or missing source fails the command.
The save/load probe also calls the actual home agent's saved-state arms and
compares the resulting serialized noun. It passed with 53 native checks on
September 25; the full behavioral/migration qualification remains separate.

No general Hoon hot-reload claim is made: committing a desk and preserving a
running app's state across an update are different operations. Application
saved-state changes need explicit versioned migrations and their own tests.
`core-check` uses clean fake state; `core-test` additionally exercises the declared
state and behavioral scenarios.

The qualification flow also records exact runtime, source, loaded Python and
test-input identities. Native output is under `.piers/fakes/logs/`; execution
guard reports are under `.runtime/execution-runs/`. Keep failures. Independent
review reconciles the full native results against the required evidence manifest.
Full qualification requires committed source. At startup the supervisor records
the commit, verifies each relevant Git blob and input tree, and checks those
bytes again during qualification. Ordinary `core-check` still supports edits
before committing.

A full corpus can finish with `execution_complete` while its three explicitly
deferred evidence dispositions remain open. The original skipped checks stay in
the raw report. The independent gate reads the completed guard, exact native
transport, scheduled-Gall evidence, and separately reviewed source/N/A proofs.
Only that complete gate can support Phase 1 closure.

Core07 completed that native schedule in 5,473.523 seconds (about 91 minutes)
under the 50% CPU limit; capacity and predecessor work took 3,896.109 seconds
within it. Filling 4,096 real historical events and the eight frozen boundary
recipes makes full qualification much longer than the ordinary developer loop.
Use `make check` for host changes and `make dev` / `make core-check` for native
feedback. Reserve full `core-test`, scheduled Gall and evidence reconciliation
for changes that affect the qualified native behavior or its execution inputs.
Documentation-only changes do not need another full native run.

The private fixture controls `migrate-legacy` and `load-bad-legacy` have a
600-second native and 620-second host diagnostic ceiling so full-state
validation can be measured. All other requests retain their existing 55/75-second
bounds. A native timeout is never a malformed-state rejection. These ceilings
are not latency targets or measured performance results. The full test caller
waits within the unchanged outer guardian's 7,200-second execution budget.
The [first focused diagnostic](evidence/2026-09-26/native-attempts/capacity01/independent-diagnosis.json)
measured 117–119 seconds for full 4,096-event validation at the 50% CPU quota.
It then failed a separate missing-binding test expectation. Those timings explain
the earlier 75-second host timeout; they do not establish overall qualification
or acceptable production latency.

## Host conditions

The Phase 2 unit inventory keeps ordinary suites at a 60-second host deadline.
The separate global-update capacity suite has a fixed 180-second diagnostic
deadline: it actually fills 64 watches/cursors/streams across current principals,
then tests refusal and slot reclamation. A combined-suite attempt timed out at
60 seconds and required forced cleanup; its failure is retained. The larger
deadline is not a performance target or a passing result. It does not change
the outer lifetime, CPU quota, thermal startup/stop limits, or response bounds.

The reviewed guard admits startup at at most 75 C and stops native execution at
90 C. It also requires fresh sensor evidence, one CPU of affinity and a transient
50 percent CPU quota. These controls do not change persistent workstation settings.
The shared lock serializes this repository's native jobs. Other workstation
workloads continue independently. If a start is refused, inspect `make preflight`
and the retained report; resume after cooling without changing the limits.

`make start` and `make dev` also put preparation in a transient user scope with
the same 50 percent/10 ms CPU limit and one allowed CPU. This covers seed and
toolchain hashing before the native guardian takes over. The integrated
`make dev` passed all 53 native checks at `b9765bf` in 58 seconds, with
committed, unchanged source inputs; see the [execution record](evidence/2026-09-25/dev-flow-and-gall-attempts/index.json).
The successful independent Git audit used the same preparation limit. These
commands do not change fan or persistent power settings. The host must remain
below the guard's limit throughout qualification. The September 26
[host observations](evidence/2026-09-26/host-load-observations/index.json)
show CPU spikes coinciding with the desktop agent-usage collector, including
while Stead was stopped. This is correlation, not proof of a sole thermal cause.
Host settings outside this repository require separate owner authorization.
During the September 26 qualification window, the owner authorized temporarily
pausing the agent-usage widget and restoring it after the native jobs. The
[recorded window](evidence/2026-09-26/host-load-observations/restoration-and-window02/index.json)
ended with the exact desktop configuration and all 34 fan values restored and
verified; Chromium was paused by the owner, with no automated browser changes.

`make dev` cleans up a failed/interrupted operation. A successful developer check
leaves the supervised fake environment running for the next check; use `make stop`
when finished. If a hard interruption leaves an unclean marker, preserve the
failure record and use the documented seed verification/reset procedure. A saved
process snapshot is not automatically a clean seed.

A timed-out Dojo/Lens request can also leave pending work in the disposable
pier even after the processes stop. If the next boot cannot become ready,
retain both attempts, run `make stop`, then `make reset` before `make dev`.
The reset command verifies that the owned fixture is stopped and that its seed
hashes match. The [September 26 recovery record](evidence/2026-09-26/native-timeout-recovery/index.json)
retains an observed readiness failure and the subsequent verified reset. Do not
delete a pier or treat a process snapshot as a replacement seed.

## Phase 2 SDK package

The current v3 SDK exports four public libraries, four marks, a sample consumer,
API documentation and notices. Build and bind it to its declared Git source
without starting ships. From the repository root:

```sh
mkdir -p .runtime/sdk
python3 scripts/package_sdk_v3.py build --archive .runtime/sdk/stead-sdk-v3.tar
python3 scripts/package_sdk_v3.py verify --archive .runtime/sdk/stead-sdk-v3.tar
python3 scripts/check_sdk_source.py --archive .runtime/sdk/stead-sdk-v3.tar
```

Choose a new output name for a later build; existing files are preserved.
The checked-in export lock fixes the public file list, hashes, notices and
toolchain. A changed public file needs a reviewed pin update. The package command
copies no private fixture client or home state, and verification never extracts
an input archive. The source checker additionally reads the exact commit's Git
blobs with replacement objects and lazy fetching disabled. Run it only against
a reviewed checkout; repository Git configuration is not sandboxed. The v2
package and lock remain available separately. See [the v3 package scope](../../sdk/v3/README.md).

This is host package verification. Compiling a separate native client from the
published fragment, version negotiation and complete independent API conformance
remain unfinished URB-180 work. No additional hosting or identity is needed
to build or test this package locally.

## Frontend build and browser feedback

The frontend has its own pinned Node runtime and lockfile. From the repository
root, run `make setup`, then install the exact locked dependencies and the
Firefox revision selected by that locked Playwright package:

```sh
.runtime/node-v24.21.0-linux-x64/bin/node .runtime/node-v24.21.0-linux-x64/lib/node_modules/npm/bin/npm-cli.js ci --prefix web/app --cache "$PWD/.runtime/npm-cache" --ignore-scripts --include=optional
PLAYWRIGHT_BROWSERS_PATH="$PWD/.runtime/playwright" .runtime/node-v24.21.0-linux-x64/bin/node web/app/node_modules/playwright/cli.js install --no-remove firefox
```

The optional packages include esbuild's platform binary; lifecycle scripts are
disabled. These commands write only repository dependencies and browser files.
They do not install system packages or modify the system certificate store.
The Linux host must already provide `/usr/bin/certutil`, Firefox's shared-library
dependencies, user namespaces, and usable user systemd/cgroups. On Arch,
`certutil` is supplied by `nss`; other distributions use different packages.
Do not use Playwright's `install-deps` as a portable Linux setup command: it
invokes distribution package management. Resolve missing host prerequisites
before starting a native fixture. A headed human trial also needs the current
user's local display socket.

After dependency installation:

```sh
make frontend-check
make frontend-build
```

These commands use the pinned Node binary and the existing 50% CPU preparation
limit. They start no native fixture or browser. After preserving and stopping
any running fixture, package the verified build into the development desk:

```sh
.runtime/node-v24.21.0-linux-x64/bin/node web/app/package-desk.mjs
```

TypeScript and client tests provide host feedback. The build emits a byte/hash
manifest and split assets; packaging verifies that manifest and generates the
native desk's exact route inventory. Stop the native fixture before packaging
new assets. Content-addressed filenames change when their contents change;
uncommitted replacements are permitted for development and cannot claim exact
committed-source qualification.

For native browser feedback, preserve the last run, stop, package the frontend,
then run `make team-dev` and `python3 web/app/browser-check.py`. The configured
lane needs the stopped clean seeds created by an initial `make dev`. Preserve
those seeds when archiving failed live piers; `make reset` verifies their hashes
before restoring them. Never use a partially executed live pier as a seed.

The browser runner verifies native listener ownership, TLS CA/hostname/leaf,
fixture and thermal health, and whole-browser process cleanup. Certificate
trust is confined to its disposable Firefox profile; it does not change system
trust. Its current tests use synthetic member approvals and are development
checks, not a production deployment. Do not infer a full milestone pass from
the first successful browser journey or from mocked rendered tests.

## Hosted native CI while the workstation is busy

The reviewed workflow is manual. It runs on a disposable GitHub-hosted Ubuntu
worker with synthetic fake ships; it does not start local Urbit processes.
After pushing a candidate commit to the derivative repository:

```sh
gh workflow run native-hosted.yml --repo ScottTpirate/stead-urbit --ref main --field candidate="$(git rev-parse HEAD)"
gh run list --repo ScottTpirate/stead-urbit --workflow native-hosted.yml --limit 5
```

Main's immutable manifest selects the reviewed controller. The candidate supplies
only allowed product blobs; changing a runner, test or SDK consumer needs its
own reviewed controller update. Omitting `candidate` tests the pinned controller.
The job first proves admission and failure cleanup, then runs native compilation,
units, multi-ship behavior and negative controls. A dispatch or a green admission
step is not a passing native result. Download and independently review its bounded
evidence before treating a completed run as acceptance.

Hosted tests do not satisfy the local rendered browser, natural session-expiry
or independent human onboarding gates. Keep the local native/browser lanes
paused when the workstation cannot meet their existing thermal admission; the
hosted profile does not change those limits.

## Phase 2 and later testing

The configured home, synthetic teams/containers, individual sessions and first
local two-member browser journey are implemented. The full Phase 2 inventory
adds private/shared Docs, conflicts and recovery, authorized updates, an
independently built public-API client, native CI and onboarding acceptance.
The user's identity ship approves a session; page bodies travel directly from
the browser to the home. Owner administration credentials must not become the
team login. See the executed evidence and remaining
[acceptance inventory](PHASE2_ACCEPTANCE.md) before choosing a test scope.

For initial local browser testing the user needs only a supported browser and a
short period to try the shared Work/Docs flow with synthetic content. Any local
HTTPS certificate trust step must be explained before changing the browser's
trust configuration. The automated runner's loopback origins exist only while
its owned relay and guarded fixture are healthy; they are not public deployments
or persistent user-facing servers.

Public hosting and real identities belong to a later live-network canary. They
will require an owner-chosen host/budget, separate organization and tester
identities, HTTPS administration boundaries, and qualified backup/recovery. A
VPS is one option; an approved Linux machine reachable by the test cohort can
also host a server. Cross-host tests are required before claiming network or
independent-custody behavior. Local fake tests cannot establish those properties.

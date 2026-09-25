# Local development and testing

Use this Linux workstation for development. The existing harness runs four
disposable fake Urbit ships in one private network namespace: home, contributor,
reader and outsider. They execute the real pinned runtime and Hoon, with separate
state directories. They need no purchased identities, public server, GPU or cloud
account. Fake ships do not join the live Urbit network.

Use public/synthetic content. The application and its tests are still undergoing
Phase 1 qualification. A passing compile check is not permission to use company
data, and the browser application is not implemented yet.

## Commands

`make` prints help without downloading or starting anything.

| Command | Purpose | What it establishes |
| --- | --- | --- |
| `make setup` | Fetch and verify the exact pinned runtime, boot and Node artifacts | Reproducible local inputs |
| `make doctor` | Check pins, prerequisites and real namespace isolation | Whether this Linux host supports the harness |
| `make preflight` | Read current temperature admission without launching ships | A current sample, not a promise that a later launch will pass |
| `make check` | Run planning, both contract freezes and host tests | Host/static/mocked results only |
| `make dev` | Start the guarded supervisor, wait for readiness, compile the core and run pure probes | Native compile/probe evidence when it actually passes |
| `make status` | Report stopped, booting, compiling or ready state | Current lifecycle state; an unresponsive owner is not reported as stopped |
| `make core-check` | Reinstall edited Hoon into a fresh fake fixture and rerun compilation/probes | Shorter native feedback, separate from acceptance |
| `make test` | Run the original four-identity counter smoke | Native allow/deny, failure propagation and restart |
| `make core-test` | Run the full current Work/Docs qualification corpus | Business, access, delivery, migration and export evidence; missing requirements still fail |
| `make gall-schedule` | Run actual pinned Gall/app gates with a controlled queue and clock | The delayed old-leave case; no Ames/network identity claim |
| `make skill-prequalify` | Run frozen workflow reference, oracle and mutant controls | Prerequisite for the separate skill evaluation; no participant result |
| `make stop` | Stop the owned ships and release their lifecycle lock | Clean local shutdown |

Run each native command sequentially. Start once, then use `make core-check`
after Hoon edits. After changing any Python harness/runner module, use
`make stop` followed by `make dev`: the supervisor pins its loaded code and
rejects changed files. Do not run a test against a stale supervisor.

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

## Host conditions

The reviewed guard admits startup at at most 75 C and stops native execution at
90 C. It also requires fresh sensor evidence, one CPU of affinity and a transient
50 percent CPU quota. These controls do not change persistent workstation settings.
The shared lock serializes this repository's native jobs. Other workstation
workloads continue independently. If a start is refused, inspect `make preflight`
and the retained report; resume after cooling without changing the limits.

`make dev` cleans up a failed/interrupted operation. A successful developer check
leaves the supervised fake environment running for the next check; use `make stop`
when finished. If a hard interruption leaves an unclean marker, preserve the
failure record and use the documented seed verification/reset procedure. A saved
process snapshot is not automatically a clean seed.

## Phase 2 and later testing

First qualify the native core, then add configurable synthetic teams/containers
and an independently built public-API client. Next add individual sessions and a
local browser journey with separate contributor, reader and outsider contexts.
The user's identity ship approves a session; page bodies travel directly from
the browser to the home. Owner administration credentials must not become the
team login. A future frontend build/dev-server command will be documented only
after it exists and has been exercised against that authorized API.

For initial local browser testing the user needs only a supported browser and a
short period to try the shared Work/Docs flow with synthetic content. Any local
HTTPS certificate trust step must be explained before changing the browser's
trust configuration. There is no browser URL to test at this checkpoint.

Public hosting and real identities belong to a later live-network canary. They
will require an owner-chosen host/budget, separate organization and tester
identities, HTTPS administration boundaries, and qualified backup/recovery. A
VPS is one option; an approved Linux machine reachable by the test cohort can
also host a server. Cross-host tests are required before claiming network or
independent-custody behavior. Local fake tests cannot establish those properties.

# Phase 2 preparation checkpoint

Recorded 2026-09-28 UTC; updated 2026-09-29 UTC. Phase 2 is incomplete. Its six milestone issues
(#9, #10, #14, #21, #22 and #29) remain open. The Phase 0/1 acceptance record
remains tied to its recorded source; it does not qualify the newer candidate.

## Ready for the next qualification window

The candidate contains configured individual sessions, Work/Docs, private
search/activity/inbox and update handling. The frontend edit loop has
`make frontend-check` and `make frontend-build`; packaging and native fixture
restart are separate explicit steps in [DEV_FLOW](DEV_FLOW.md).

The disposable human launcher requires a passed automated native/browser run
on the same running source, the live supervisor's native-report digest, and
matching packaged frontend bytes. It refuses stale or failed prerequisites.
The participant receives only the [task](quickstarts/onboarding-task.md) and
[member quickstart](quickstarts/member.md). Private collection creation and
readback are correlated in the bounded trial evidence. A checked task box is
not acceptance.

These changes are reviewed and pushed in [PR #50](https://github.com/ScottTpirate/stead-urbit/pull/50).
Commit `a027d424e15dd5be1cf2024c1710b21e83d00251` passed 14 Python
admission/input/process controls, 31 frontend/evidence controls and 34 supervisor
controls. Supervisor native calls were mocked. Earlier edit-loop validation
also ran TypeScript checking, 30 frontend tests and a real frontend build.
Small local preparation checks used 25% of one CPU. None is native qualification.

Commit `6ea465a4e6f33b9b64ccea027e38647a422f05d0` preserves an uncertain save through
another tab's CSRF rotation and a lost resume response. Browser admission now
requires the exact case inventory and fully drained response capture; late
capture failures cannot be published as a passing journey. Eighteen Python
admission/input/process controls and 35 frontend/evidence controls passed,
along with TypeScript, frontend build and exact 12-asset packaging/readback.
Independent source review cleared both the product fix and evidence changes.

Commit `3e49081` extends the prepared journey to 34 required observations:
private document edits preserve the reader's complete views, counts, generations
and usable watch cursors; a selected publication must produce exactly one public
invalidation. Shared edits reload exact Markdown, revision and a new Git OID.
Keyboard sign-in covers denial/recovery, approval against the same home/code
card, live status and heading focus. These additions passed source review,
JavaScript syntax and host admission controls; they have not run in a browser.

The v3 archive's 13 public exports and toolchain lock were checked against exact
Git source `16651c89b2d63f4bebc43580b170b75e4252160e`. Eleven real local Git/package
controls passed. The new SDK input preparer also passed 12 host controls. Actual
preparation produced 15 verified input files plus its receipt, with no private
client or authority source. An earlier attempt was refused before receipt on
the repository's Btrfs directory-enumeration behavior; both failed directories
are retained, and the corrected readback passed on that filesystem. This is
package/input preparation. Commit `f259863` also prepares bounded readback for
the sample and four named compiled mark artifacts, requiring external retained
pins and returning exact verified bytes. Ten filesystem controls with synthetic
bytes passed; independent review cleared that helper. It does not authenticate
its pins, prove builder cleanup, decode jam or qualify a consumer. The independent
isolated builder lifecycle, artifact transfer integration and runtime consumer
still need implementation and native execution. A fixed native build-thread
source is now prepared and independently reviewed: one absolute Clay case,
complete sample/mark vases, bounded binary exports and staged-only metadata.
It is not installed by an executing runner and has not compiled or executed.
Commit `32df210` adds its exact bytes from the reviewed controller checkout to
input receipt v2; package-selected roots cannot substitute their own hook.
Thirteen host controls passed, and actual CLI preparation produced 16 verified
files plus receipt SHA-256
`75da2f6c8269802e4c5ea3558a0b3d0072e4fd0770feb14db9d403a6b973cd4e`.
Commit `df3962f` adds a bounded staged-response parser with strict inventory,
decimal, digest and size checks and immutable metadata. Six synthetic controls
passed; it does not authenticate the response or authorize artifact transfer.
All 58 SDK host controls passed together in 5.314 seconds. The source changes
received independent review; see the
[reviewed qualification boundary](SDK_CONSUMER_QUALIFICATION.md).

## Actual hosted observations

The repository is public and the manual workflow runs on disposable GitHub
workers. The workstation's thermal limits are unchanged.

[Run 36365662794](https://github.com/ScottTpirate/stead-urbit/actions/runs/36365662794)
used controller/candidate `144153132a4a583c5265e7b340fb7f5e7cf6f873` and workflow
`cdf591e17197f7d909d666f6af592e672676327a`. All six admission/lifetime controls
passed. The native worker then failed after 1,324.208 seconds. Collector EOF,
child termination and empty owned cgroup were verified. The public artifact
contained only a generic worker error, so the precise failing native stage was
not established. This is failed evidence, not a partial native pass.

Reviewed controller `7cc474ecdeded5f534e8c88603b2ea10c79177cc` adds a failed-only
diagnostic projection with closed stage/error categories and bounded counters.
It excludes native text, requests, credentials and log tails, preserves the
initiating boot error through cleanup, and cannot promote failure to acceptance.
Thirty-nine host CI controls passed in 1.329 seconds; these include synthetic
diagnostic rejection controls. [PR #64](https://github.com/ScottTpirate/stead-urbit/pull/64)
pinned this controller without changing the reviewed workflow or resource policy.
[Retry 36368007924](https://github.com/ScottTpirate/stead-urbit/actions/runs/36368007924)
passed all six admission/lifetime controls, then failed at filesystem controls
after 1,066.449 seconds. All four fresh ships had reached readiness and exited
cleanly; application checks had not begun. Collector EOF and empty owned cgroup
were verified. Its exact error remained outside the diagnostic vocabulary.

A small actual host namespace reproduction found that mode 0550 returns EACCES
on both read-only and writable mounts. Reviewed controller
`3b683c5d44fe5302a3755ca9ebed86b7f85d32d2` requires both a read-only mount observation
and a refused write-open; permissions alone cannot pass. Forty-five host CI
controls passed in 1.892 seconds, including four real mount/permission controls.
This fixes the reproduced incompatibility without claiming the exact original
hosted error was observed. [PR #65](https://github.com/ScottTpirate/stead-urbit/pull/65)
changes only the reviewed controller pin.
[Run 36369882994](https://github.com/ScottTpirate/stead-urbit/actions/runs/36369882994)
uses workflow `856c3c357df4a168cf91742f078a580e99aef24e`, that controller and candidate
`6ea465a4e6f33b9b64ccea027e38647a422f05d0`. All six admission/lifetime controls
passed. The native worker reached application checks, with 80 installed files
on each of four ships and six recorded unit/control suites, then failed after
1,223.686 seconds with 679 passed checks and one failed assertion. Input identity,
collector EOF, child termination and empty owned cgroup were verified. The
failed check name was not retained by the closed diagnostic projection.

Source review found that the capabilities assertion required a literal row key,
although the public API declares opaque keys and the native serializer uses
numbered keys. Its position matches the failed check count; this is a source
inference, not an observed assertion name. The correction checks the correlated
query envelope and exactly one complete capability payload without interpreting
the row key. Four synthetic host admission controls and 46 CI host controls
passed. Independent review cleared the source and pin-only
[PR #66](https://github.com/ScottTpirate/stead-urbit/pull/66). The failed hosted
run remains failed evidence.

[Retry 36371977543](https://github.com/ScottTpirate/stead-urbit/actions/runs/36371977543)
uses workflow `699b99176b4903bcfe4f312e7fc2370993fc6ab8`, reviewed controller
`87d14e5f779dbc84a49208b7192201432cd841c3` and candidate
`1c8ef7b19b7e4a433ba76c018595634e7ff311dc`. All six admission/lifetime controls
and all 755 team checks passed. The worker then failed at the supported-predecessor
migration gate after 1,381.953 seconds. Input identity, collector EOF, child
termination and empty owned cgroup were verified. The diagnostic establishes
the stage and failed output assertion, but does not expose the exact compiler
or Hoon assertion cause. Later native controls did not run. This remains an
overall failed run; the capabilities correction has cleared its earlier check.

## Combined preparation and next retry

[Draft #67](https://github.com/ScottTpirate/stead-urbit/pull/67) combines the
reviewed SDK/onboarding and hosted-controller branches without replacing main's
reviewed workflow. Its initial host suite found six setup errors from Linux's
Unix-socket path limit in the nested checkout. Reviewed commit `4b73991` binds
the same endpoint through an owned private directory descriptor. Eight focused
socket controls passed; the corrected full host suite ran 584 tests in 119.077
seconds with one explicit skip and no failures. The skip is for an optional
retained historical failure artifact absent from this new worktree, not a native
qualification case. Twenty-two contract checks and
frozen source checks also passed. These are host/static/mocked checks, not native
TLS or browser evidence. The original failed suite is retained.

Source review of the migration probe established a wrong count: project creation
reserves a creator grant, and revoking the separate member grant retains it.
Reviewed controller `2e491771575a13da0d34c28a1cba5ec98e68e1cc` requires both grants
and their exact migrated values, preserving the other assertions. It adds bounded
failed-only byte/hash/closed marker observations from the exact migration
response; raw text stays private. Forty-eight host CI controls passed in 1.691
seconds. This source defect is not the observed original failure's proven cause.
[PR #68](https://github.com/ScottTpirate/stead-urbit/pull/68) pins the correction.
[Retry 36374379219](https://github.com/ScottTpirate/stead-urbit/actions/runs/36374379219)
uses workflow `f38cffe728752631614f4abff54e9db961b28fff`, that controller, and candidate
`4b73991fa245e4cf413a218c34fae55e1834a366`; its native product bytes match the prior
candidate. The run failed after 755 passing team checks and the admission/cleanup
controls. A focused local reproduction observed the same 57-byte response and
SHA-256 `48df5b0bbd1d0e0772e0fb7c2ac35b554110c6ac2553644b144a96a82bd9506b`:
`%generator-build-fail`. Actual compiler output identified incorrect import
ordering, then an ambiguous `q.on-save` access. The corrected generator imports
libraries before the agent and names the saved vases explicitly. All 22
assertions remain. Source `e59d72fea049642c6626a556582b9b79ea0e790e` passed
`make migration-dev`: 160 checks, the exact supported-migration marker,
59.372 seconds inside the diagnostic and clean owned cleanup. The migration
file SHA-256 is `bf7f09814c6a61469ac34bb9bfa017f8a8991dbd067b3d7c70ebba66ad366c23`.
That historical source context retained `committed_bytes_verified=false` because
two untracked Python cache files existed in the web helper mount. All committed
source and installed native files matched; this focused result is not a complete
committed-tree or CI qualification. The cache files were preserved and the entry
points now disable cache writes before loading those helpers.

[PR #69](https://github.com/ScottTpirate/stead-urbit/pull/69) pins reviewed controller
`99879c516b0481d1013051672658bf85fe030428`. The fresh
[run 36412165213](https://github.com/ScottTpirate/stead-urbit/actions/runs/36412165213)
uses main `9a6fec9a6030d381f1fa846bd9bb4ec8779cd382` and candidate
`2a525948b5b369a05bcf1c2a783a9dbc5c361390`. It failed after 1,644.320 seconds:
673 passing checks, zero failed checks and 681 recorded commands. All four ships
had 80 installed files; migration was not reached. Input identity, collector EOF,
clean owned child exits and empty cgroup were verified. The counters match the
third ship's bootstrap acknowledgment followed by admission; that location is a
source-derived inference because the exact failing operation was not retained.
There is no evidence establishing a thermal or frontend cause. Reviewed controller
`a27c6218eb7a97294b6d8c7192f3e1aa656244d4` adds closed admission location/error
categories and preserves the initiating exception through both rollback attempts.
Fifty host CI controls and 11 lifecycle controls passed; none is native acceptance.

The updated browser client eliminates duplicate identity reads and scope
snapshots, submits search explicitly and serializes unfinished watch opens.
Pinned TypeScript and 35 host client/build controls passed; all 16 real Firefox
checks against a mocked Home passed with unchanged input digests. Native timing
instrumentation is prepared but has not run against this new client. Generated
assets were verified and packaged in `cf19d00`; this is build evidence, not
native browser acceptance.

## Executable independent SDK candidate

The current lane supersedes the earlier unexecuted artifact-transfer proposal:
it compiles and invokes the public package in the same fresh isolated consumer,
with a separate synthetic Home created only after compilation and isolation
checks. The private authority implementation is unavailable in the consumer.
Commits `a9b9156` through `ad8d305` implement and independently review this lane.
Twelve real bounded socket-relay controls, nine synthetic result validators and
38 development-flow controls passed. A lightweight actual Linux control verified
separate namespaces, zero capability sets, no-new-privileges, mapped host file
ownership and owned-evaluator SIGKILL/reaping after creator loss. A separate mocked
control confirms the configured fixture's UID restriction cannot be bypassed.

Three retained attempts failed before native startup: a missing explicit user
namespace option, a rejected nested UID mapping, then a redundant capability-drop
operation after all capabilities were already absent. The reviewed correction
retains the nonroot caller outside, maps the consumer inside and never adds
capabilities. The fourth attempt booted and imported the public files, then failed
because the naked import-control gates needed a noun argument. Commit `2ea590a`
adds that required argument after pinned Dojo source review. The fifth attempt
was stopped at 92°C by the unchanged 90°C thermal ceiling after 437.748 seconds;
it did not qualify public compilation. Both failures and their private evidence
are retained. Native SDK compilation and complete conformance remain unqualified
until actual results and cleanup are independently reviewed. See
[SDK consumer qualification](SDK_CONSUMER_QUALIFICATION.md).

## Remaining execution

The user has paused K4 and requested completion of Stead. Guarded local work has
resumed. No K4, fan or desktop settings were changed by this continuation.
Local admission still requires 75°C or lower and stops at 90°C.

The remaining gates are the expanded hosted native inventory, the independent
SDK consumer, fresh local native/browser journeys including
natural session expiry, and the uncoached human trial. Review their exact-source
results against [PHASE2_ACCEPTANCE](PHASE2_ACCEPTANCE.md), then integrate the
reviewed PRs and reconcile the six issues. Linux fake ships suffice for this
phase; no purchased identity or separate public Urbit server is required.

## Configured history and recovery acceptance preparation

Independent review identified missing configured-v3 stock Git and interrupted
projection save/load checks. A private fixed fixture observation now reads the
actual stored object bytes, preserving lengths, then uses ordinary Git hash-object,
fsck, rev-list, ls-tree and cat-file. Browser receipts bind source/publication/edit
heads and Markdown; complete destination ancestry excludes private canaries and
source history. This is synthetic owner observation, not a public export API.
The actual Home probe now saves and reloads during an incomplete 16-event batch,
checks quarantine, retired wakes, discarded forged views, exact final pages and
revoked access. These new Hoon/browser checks remain unexecuted.

Eight host controls passed in 0.126 seconds (synthetic observations with real Git,
mocked-native RPC persistence/late-guard failure and source-binding controls),
and 12 browser-evidence controls passed in 0.008 seconds. Two independent source
reviews cleared the corrections for native execution; neither is acceptance.

Hosted run `36416743910` completed with failure after 1,707.854 seconds. All 755
team checks passed and the supported migration passed; failure occurred next in
the native-controls stage. Its bounded artifact `10968932347` records unchanged
inputs and verified empty host cleanup. This run does not qualify CI.

## Native failure controls and runtime repair candidate

The new focused `make ci-controls-dev` lane uses one stopped-seed fake to run
the same trusted native failure controls locally. Its results are diagnostics,
not complete team or hosted qualification. The first actual run at source
`c85cb4579babdaae793172893d433b1978330215` passed all 166 setup checks and 162
commands, then rejected the observed compiler diagnostic. The native compiler
correctly rejected the deliberately undefined name; the checker expected a
different diagnostic. Reviewed commit `f7452c444f0ff1fe9f28edd25679775cb0370b06`
matches both exact pinned diagnostic lines, retains the false native verdict
requirement and adds closed control failure categories. Fifty-two host CI
controls passed, including the retained actual compiler-output fixture.

The second real run at `f7452c4` passed missing-arm, compiler-failure and finite
timer controls. The 50 ms deadline produced the expected response-header timeout
with zero received bytes. The next recovery call reached EOF: the owned Vere
process exited `-11` without forced termination, and cleanup correctly failed.
The failed diagnostic took 44.457 seconds. The runtime log and system crash
metadata confirm SIGSEGV; no core image was retained, so the precise memory
fault is not proven. Both failed runs, the crashed disposable state and the
original stopped seeds are preserved. The
[bounded observations](evidence/2026-09-28/runtime-disconnect/observation.json)
retain exact input/report hashes and failure boundaries.

Upstream's official [newt fix](https://github.com/urbit/vere/commit/c0a35c6f6302baf536a13522afd1ac89ea8c7776)
describes a closely matching early-disconnect failure. Independent source review
verified that its parent file matches released 4.6 byte-for-byte. An isolated
candidate applies only that hunk to 4.6, preserves the MIT notice, and uses pinned
Zig 0.15.2 with the original package hashes. Full extracted source/compiler bytes
are checked against the downloaded archives; compilation has no network, home
or credentials, uses a read-only dependency cache, and retains the existing
single-owner 50% CPU and 75/90°C guard. The project runtime pin is unchanged.
Compilation, a real unchanged disconnect replay, subsequent runtime adoption,
hosted CI and Phase 2 acceptance are separate gates. None is established merely
by this candidate preparation or source review.

The local source build was stopped at 92°C after 158.420 seconds by the unchanged
90°C ceiling. Source/compiler inputs remained unchanged; no completed binary
was produced. [PR #71](https://github.com/ScottTpirate/stead-urbit/pull/71) adds a
separate manually dispatched build on a standard disposable public GitHub runner.
Only the pinned public runtime/compiler/dependency sources enter the offline,
unprivileged, capability-free containers. Their CPU, memory, tasks, writable
storage, logs and deadlines are bounded and checked. This workflow does not run
application code or replace the existing native CI gates.

Independent source review cleared that build lane; eight host controls passed
in 0.012 seconds. Actual run `36485432542` stopped before the first compiler
invocation: Docker's local logging driver rejects its default compression with
a single retained file. Its artifact `10999355695` retained the exact error,
verified container removal and tmpfs cleanup. The reviewed one-line correction
in [PR #72](https://github.com/ScottTpirate/stead-urbit/pull/72) explicitly disables
compression while retaining the same single 4 MiB log bound. Eight host controls
passed in 0.011 seconds.

[Build run 36485873646](https://github.com/ScottTpirate/stead-urbit/actions/runs/36485873646)
completed successfully at workflow `825aebf719d1fd99bfc51457cc023ce36edda089`.
The downloaded artifact matches GitHub's SHA-256. All 27 input archives, exact
workflow recipe bytes, binary correspondence, 26 completed containers and their
cleanup were verified locally and independently reviewed. The
[bounded build record](evidence/2026-09-28/runtime-disconnect/build.json)
retains the actual hashes. The experimental binary is
`f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833`.
The project toolchain is unchanged. Native recovery, runtime adoption and complete
native CI remain pending; this successful build does not qualify Phase 2.
Additional runtime fault investigation is paused following the owner's request
to avoid repeated platform safety interruptions. Ordinary application checks
continue; required acceptance checks are not removed or reported as passed.

The configured recovery probe's first native compilation found a missing
nonempty-journal refinement. Reviewed commit `af87ec3` adds it; its actual retry
passed 168 setup/unit checks but failed compilation on the test bowl's entropy
literal (`@ud` where Gall requires `@uvJ`). The next retry at `39b5799` again
passed 168 setup/unit checks, then identified an inferred fixed tuple where the
four-query loop required a list. All failed reports and compiler logs are
retained. The reviewed corrections preserve the same entropy values and four
query kinds, adding their explicit types without removing assertions. Successful
recompilation and the actual interrupted-projection assertions are still pending.

## Development runtime adopted; fresh qualification pending

At `79aebc1`, all 731 configured native checks passed in 833.013 seconds,
including the corrected recovery probe, all 70 expected unit arms and the
native deliberate-failure control. Committed source and inputs matched.
The supervisor later reached the thermal ceiling at 1,793.62 seconds while
left ready. The [observation](evidence/2026-09-28/team-recovery/observation.json)
retains both outcomes; the overall lifetime remains unqualified.

The existing reviewed regression passed all 13 checks in 15.819 seconds on the
repaired runtime. The same process recovered and exited zero without force;
its guard completed and inputs were unchanged. Independent review cleared
development pin adoption. The
[regression observation](evidence/2026-09-28/runtime-disconnect/native-regression.json)
is separate from the historical build-stage snapshot.

The [development prerelease](https://github.com/ScottTpirate/stead-urbit/releases/tag/runtime-v4.6-newt-c0a35c6)
retains the binary, complete source/compiler/dependency inputs, notices, recipe
and observations. GitHub asset digests matched, and actual `make setup` fetched
and verified the published archive. Forty-four host harness checks passed in
3.699 seconds; planning validators passed. Old fixtures remain preserved;
fresh seeds, current SDK/native/browser/Git/performance/expiry checks, human
onboarding and a complete hosted native CI run are still required.

The v2/v3 package locks now bind unchanged public exports to source
`d3b2b97ee7a4c343f3e4472dc05c479e2de11cfb` and the new runtime lock.
The rebuilt v3 archive is 81,920 bytes, SHA-256
`de41150e113c1df26804ffa7466f6018f2bfbf3b509715f2d971f6001f6ef6ac`.
Package verification and exact Git-source checks passed. All 81 SDK host
controls passed in 11.600 seconds, including existing actual Linux namespace
controls. Independent review cleared both metadata updates; public Hoon exports
are unchanged, and native consumer execution remains pending.

## Acceptance review and clean browser setup, 2026-09-29

Independent review found three gaps in the prepared Phase 2 coverage: deletion
while subscribed, the 64-row retained-history boundary, and fresh contributor
browser prerequisites. Reviewed commit `d89330ec0da287eae5b1c86e7e2389d33152f9ac`
adds Work/document/relation deletion with active native watches, surviving-object
and dangling-link readback, old-cursor rejection and private-delete invisibility.
A pure native arm drives 65 accepted updates while polling, checks ordered
delivery and exact retained sequences 1–64 then 2–65. The strict inventory now
requires 71 positive arms, including 26 update arms, and the unchanged deliberate
failure control. Seventeen host inventory controls and 52 host CI controls passed.
The added Hoon and configured deletion checks still need actual native execution.

The contributor guide now gives the locked npm installation, a repository-local
cache, pinned Playwright Firefox provisioning, and separate Linux host requirements.
A fresh isolated dependency directory, empty npm cache and empty browser directory
passed installation, TypeScript, all 35 client/build checks and a production build.
The 12 resulting assets (296,911 bytes total) exactly match the current packaged
build. Firefox 155.0 ran one existing rendered case against a mocked Home with
unchanged inputs and verified empty browser cgroup. The host certificate tool
created an empty private test database. The first build attempt retained a missing
LICENSE error caused by the operator's partial fixture copy; copying the original
repository LICENSE unchanged resolved it. This is verified browser setup and
mocked-Home readiness, not native/browser acceptance. See the
[bounded setup observation](evidence/2026-09-29/phase2-preparation/clean-browser-setup.json).

The first fresh local four-ship startup on the repaired runtime stopped at the
unchanged 90°C ceiling after 843.490 seconds while booting the second ship. No
application checks ran and no clean seed was created. The entire stopped fixture
and failure evidence were preserved without modifying their contents. See the
[failed startup observation](evidence/2026-09-29/phase2-preparation/cold-start.json).
This remains failed execution evidence; successful dependency setup does not
qualify it. The next independent SDK attempt and hosted runs must retain their
actual results before any milestone closure.

## First complete hosted native run and local startup correction

[Run 36512081282](https://github.com/ScottTpirate/stead-urbit/actions/runs/36512081282)
passed on workflow `8a1df2fd2273aad397082259100234b2e32713ef`, controller
`d3b2b97ee7a4c343f3e4472dc05c479e2de11cfb` and candidate
`4be1ebf5940cbe0fb18554c40aebdf28baec0bd8`, using the repaired development runtime.
Independent review reconciled 763 passing check observations, including 70
positive native arms and the expected failing control, plus six admission/lifetime
controls. These counts overlap and must not be added. The supported migration
and additional negative controls passed the pinned controller's verification.
The 1,819.103-second guard exited zero, the collector reached complete EOF, and
all seven owned cgroups were empty with no cleanup errors. The
[retained public artifacts and bounded index](evidence/2026-09-29/ci-36512081282/index.json)
bind the exact source and inputs. Private worker bytes are represented by a
digest; they are not included in these public artifacts. This run does not cover
the later 71st arm or deletion checks. The expanded run `36513481746` then failed;
its retained outcome is described below. Phase 2 remains open.

The next local SDK attempt at `d89330e` stopped at the unchanged 90°C limit after
281.056 seconds during fresh consumer boot. Four initial admission checks passed;
public compilation did not qualify. Sources stayed unchanged, the controller was
reaped, and the failed consumer startup and reports remain retained. See the
[bounded failure record](evidence/2026-09-29/phase2-preparation/sdk-thermal.json).

The combined host suite at `220b96a` ran 637 tests in 174.448 seconds: 636 passed
and one optional retained-artifact check was explicitly skipped. There were no
failures. Planning and frozen-contract validators also passed. These are host,
static and mocked checks, including actual Linux host controls, not Hoon evidence.
Reviewed commit `347ee04` then corrects only `make dev`'s caller wait: it may await
four sequential cold boots within the existing 7,200-second guard lifetime.
Per-ship 1,200-second readiness limits, native-suite deadlines and resource and
thermal limits remain unchanged. Forty focused host development-flow tests passed.
Hosted CI does not invoke this CLI caller; the change still alters the captured
controller inventory, so earlier CI is not execution at this newer commit.

## Expanded inventory timeout and bounded correction

[Run 36513481746](https://github.com/ScottTpirate/stead-urbit/actions/runs/36513481746)
failed on controller/candidate `d89330ec0da287eae5b1c86e7e2389d33152f9ac` after
1,179.878 seconds. All six resource controls passed. The native diagnostic
retained 172 passed checks, zero recorded failed checks, three completed unit suites
and four captured transcripts, with a response-header timeout during team-check.
The counters place it in the ordinary updates suite; the public projection cannot
identify a particular arm or distinguish compilation from execution. Worker
cleanup failed; the collector reached EOF and final host cleanup verified an
empty cgroup. The [public artifacts](evidence/2026-09-29/ci-36513481746/index.json)
remain failed evidence. Later configured deletion and migration did not qualify.

Independent source review found avoidable test work: the new history arm rebuilt
the entire growing projection on every one of 65 updates. The prepared correction
carries the projection through the actual append path, asserts readiness after
every accepted update, and compares the final result with one complete rebuild.
All update/poll and exact 64/65-history assertions remain. The arm moves to the
existing capacity suite: 25 ordinary update arms and two capacity arms preserve
71 positive arms overall. Ordinary 60-second and capacity 180-second deadlines
remain unchanged. Eighteen host inventory controls passed; actual native
execution of this correction is still required.

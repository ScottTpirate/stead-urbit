# Phase 2 preparation checkpoint

Recorded 2026-09-28 UTC; updated 2026-09-29 UTC. Phase 2 is incomplete. Its six
milestone issues (#9, #10, #14, #21, #22 and #29) remain open. The reviewed Git
observation corrections are pushed at `e7c81fdc833f9966d65c58e0d18024acab66592c`.
The earlier Phase 0/1 record remains tied to its own source.

The configured team at `874a773` passed all 757 native checks in 1,011.104
seconds, including 71 positive unit arms, the deliberately failing control and
all four cold restarts. Independent review verified its installed source and
native transcripts. The whole guard then closed after 1,679.486 seconds with
exit zero, no cleanup errors and no remaining owned cgroup.
[Native evidence](evidence/2026-09-29/team-native-874a773/index.json) records that
pass separately from the subsequent failed browser closeout.

The real Firefox journey at the same source passed all 34 recorded observations,
including Work/Docs, private publication, conflicts, offline saves and the
corrected probe. Its browser process was reaped cleanly. The subsequent ordinary
Git verification failed: its first generated command contained an ungrouped Hoon
hexadecimal atom, which produced a recorded syntax error and then timed out.
[The failed closeout](evidence/2026-09-29/browser-git-failure-874a773/index.json)
remains failed. The small formatter correction preserves exact Git OIDs and
object bytes; nine focused host tests and independent source review passed.
The next configured run at `04262a2` passed 757 checks in 1,018.569 seconds,
including the positive unit inventory, deliberate failure and four cold
restarts. Its whole guard closed after 1,592.213 seconds with exit zero, no
cleanup errors and no remaining owned cgroup. Independent review verified the
[native evidence](evidence/2026-09-29/team-native-04262a2/index.json).
Firefox again passed all 34 journey observations, but the subsequent Git
observation exposed a generator return-aura mismatch (`@t` versus `@ux`).
The [failed closeout](evidence/2026-09-29/browser-git-aura-failure-04262a2/index.json)
remains failed; no Git objects were materialized.

The two-line correction at `e7c81fd` explicitly casts the existing bytes through
the base atom type and imports this helper into the early build probe. It
preserves exact Git object bytes and makes this compiler error detectable
before the later browser journey. Independent source review passed. The
configured run at `e7c81fd` then passed all 757 checks in 1,008.301 seconds,
including the early build probe and four cold restarts. Its browser attempt
stopped at the unchanged thermal ceiling after 14 progress observations, without
a final journey report. The native guard closed cleanly after 1,445.583 seconds;
stopped piers, logs, ingress and browser evidence were preserved.
[This failed browser attempt](evidence/2026-09-29/browser-thermal-e7c81fd/index.json)
does not qualify browser, Git or expiry. A new configured run is restoring the
same verified clean seeds for a fresh browser attempt. Full acceptance remains
pending.

The independent SDK at `7f113a1` passed 64 assertions and 41 public API calls,
with exact package/source binding and clean shutdown. The shared reader change
at `874a773` is qualified by its real atomic-replacement host controls and the
closed native lifetime above. This is explicitly composed evidence, not another
SDK execution or unchanged-input equivalence. See
[SDK qualification](SDK_CONSUMER_QUALIFICATION.md).

Hosted run [36540906136](https://github.com/ScottTpirate/stead-urbit/actions/runs/36540906136)
passed at controller/candidate `874a773`: 789 observations, 71 positive native
arms, the deliberately failing control, migration and negative controls. The
1,901.526-second guard exited zero with complete collector EOF and clean owned
cleanup. Independent review reconciled the exact inputs and all six resource
controls. [Hosted evidence](evidence/2026-09-29/ci-36540906136/index.json) remains
bound to that source; the subsequent browser Git formatter is outside its
executed path. The later `e7c81fd` build-probe change does execute in CI, so a
fresh [run 36548243535](https://github.com/ScottTpirate/stead-urbit/actions/runs/36548243535)
is qualifying controller/candidate `e7c81fd` under workflow
`96102116a7b5b42db53999618e70479e08ef5a79`. Reviewed pin-only PR #80 is merged;
the new run is not yet a pass. The earlier run's predecessor
[36535031127](https://github.com/ScottTpirate/stead-urbit/actions/runs/36535031127)
failed after 677 passing checks at ingress admission; the initiating retirement
cause was not recorded. Its [failed evidence](evidence/2026-09-29/ci-36535031127/index.json)
remains retained. The reproduced atomic-reader race is a possible cause, not
an established diagnosis of that failure.

Current host regression passed 679 tests with one optional artifact skip and
54 CI host controls. Browser/Git closeout, natural session expiry, the uncoached
human Work/Docs trial and final integration still remain. The sections below
retain earlier checkpoints and failures; their then-pending statements are
historical rather than current acceptance claims.

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

## Frontend repeated-work and preview correction

Reviewed commit `815550b29b21765d4029f1982d6fda05a2f7e240` retains the displayed
snapshot's exact session/scope generation. Authenticated update polls still run,
rotate their cursors and process expiry/revocation; only an invalidation already
represented by that snapshot avoids another metadata/view read. Later remote
generations still refresh. The Markdown preview is memoized and deferred within
a component keyed to its identity/document scope. Dense structure switches to
a keyboard-scrollable, inert complete-body text view before creating thousands
of React elements. The editor retains the exact canonical text.

TypeScript and 35 host frontend/build controls passed. All 18 real Firefox cases
against a mocked Home passed with matching source digests and verified empty
browser cgroups. The save regression was then strengthened to count from before
Save, requiring exactly two additional reads through subsequent own-invalidation
polls; its focused rerun passed. The same case still loads a later member change
and clears the view on revocation. A near-limit newline-dense page preserved
its complete inert body and editor text with bounded DOM; changing documents
did not retain its previous deferred preview. The
[retained frontend evidence](evidence/2026-09-29/frontend-performance/index.json)
separates these mocked-Home results from native acceptance.

The actual production build packages 12 verified assets totaling 297,673 bytes,
including the 258,065-byte app. Independent review matched every packaged byte
and all 17 asset routes against the generated manifest. Native useful-content,
save, preview and transfer timings remain unexecuted for this source; these
structural improvements are not a measured native latency or p95 claim.

A cross-checkout rebuild found that the operator's temporary shared dependency
symlink gave esbuild different chunk names. That first build manifest is retained
as history. Installing the same locked packages normally in the integration
checkout produced a manifest byte-identical to the root build:
`cf46ab5c9fc334b8642c90b1b10c38e659847cbd1eb754865692be3f6e15ccd0`.
The generated package was corrected to those normal-install bytes; frontend
source and the observed browser behaviors did not change.

## SDK import-control observation

The fresh SDK run at `cd75365364d8cb9a25d36d175c2c2b3840fb6806` failed after
655.696 seconds without a thermal stop. The public-import generator compiled;
the private generator failed, and Clay reported `no files match` for the exact
private library. The runner expected `file-not-found`, so its assertion failed
before public sample/mark compilation, Home boot or any SDK call. Four initial
checks were recorded; inputs were unchanged and the controller was reaped, but
consumer cleanup reported a failed bridge. The
[bounded observation](evidence/2026-09-29/phase2-preparation/sdk-import-diagnostic.json)
retains those facts and private evidence hashes without promoting the attempt.

The correction checks the exact generator response and complete observed Clay
missing-library line within the same bounded log segment. The existing absent
private-library check and successful public-import control remain mandatory.
Four host replay/regression tests passed; generic failure, timeout, the wrong
generator/dependency, an incidental mention and oversized output are rejected.
The complete 85-test SDK host suite then passed in 13.118 seconds, including
the existing Linux namespace/process controls. A new native run is still required.

## Expanded hosted inventory passed

[Run 36517682428](https://github.com/ScottTpirate/stead-urbit/actions/runs/36517682428)
passed on workflow `20e0a4b3efc65b5aa441bd28141ad3434ac0bd66`, controller and candidate
`cd75365364d8cb9a25d36d175c2c2b3840fb6806`. Independent review reconciled all 217
controller inputs and 49 product inputs with Git, the composed desk and six
native transcripts. There are 789 passing check observations (776 distinct names),
including all 71 expected positive native arms and the deliberate failure control.
These counts overlap. Work/document/relation deletion, survivor and dangling-link
readback, and private-deletion invisibility checks passed. The history-boundary
arm completed in 12.911842 seconds within the unchanged 180-second capacity limit;
this is a native test duration, not an application latency claim.

Supported migration and additional negative controls passed the pinned controller's
verification. All six admission/lifetime controls passed. The guard completed in
1,858.213 seconds with exit zero, complete collector EOF, no cleanup errors and
all seven owned cgroups empty. Fourteen exact compressed public artifacts and
their hashes are retained in the [evidence index](evidence/2026-09-29/ci-36517682428/index.json).

Against SDK-only correction `8a2702a577b355acbbc621a38be51348b59e02a5`, all 49 product
files and 216 controller files remain identical; only the captured controller-pin
manifest differs. The SDK runner/test correction is outside CI's execution graph.
The index records those comparisons. Hosted execution remains tied to `cd75365`;
the later SDK lane needs its own native evidence.

## SDK public compilation and rejected member fixture

The next SDK run at `8a2702a` completed its fresh public consumer boot in 648.003
seconds. The subsequent public sample/four-mark compilation step took 1.771 seconds.
The private-import negative control passed. A separate fresh Home booted, but
configuration failed at the predicate that forbids Home from being a member
identity. The SDK controller had supplied its Home as the control member.

The [failed observation](evidence/2026-09-29/phase2-preparation/sdk-member-fixture.json)
records ten checks (nine passed, one failed), zero SDK business calls and unchanged
inputs. Both native children exited cleanly and were reaped, and the consumer
controller exited zero. The overall run remains failed. Correct the test fixture
to use a distinct individual control member; do not relax the product's separation
between the organization Home and individual principals.

## Distinct SDK control-member fixture prepared

The corrected runner gives the control member a fresh `~nec` identity alongside
Home in the trusted namespace. The independent public consumer remains `~bus`
in its separate namespace. Owner-local configuration binds only those two
individuals; business control requests use `~nec`'s actual native socket and
validate its receipt identity. Only seven exact adapter dependencies are installed
on the control member. Product Hoon and the public package are unchanged.

The runner preserves the invocation sample used by the pinned Khan `%fyrd`
path, requires a correlated bootstrap acknowledgement before admission, preserves
bounded readiness failures and attempts shutdown of both trusted children
independently. A read-only isolation check between trusted cold boots avoids
spanning the consumer's request-wait limit. The cancellation case opens a fresh
live watch before cancelling, checks that it cannot deliver data, then repeats
cancellation.

All 100 SDK host tests passed in 11.589 seconds with 25% of one pinned CPU. They
include actual Linux namespace/process checks and mocked fixture/dispatch,
readiness and cleanup controls. The full `make check` then passed planning and
contract checks and 658 of 659 discovered tests in 118.111 seconds, with one
optional retained-local-artifact test skipped. These suites overlap. Independent
source review cleared the corrected fixture for a fresh guarded native attempt.
The [host evidence](evidence/2026-09-29/sdk-fixture-host/index.json) records exact
reviewed source hashes and logs. Native conformance remains unexecuted; previous
failed runs remain failed, and Phase 2 remains open.

## Bounded accepted-journal replay prepared

The issue-closure audit found that URB-190's bounded-work criterion needed more
than the existing whole-projection comparison. The retained-history test now
also uses its 68 real accepted events to check actual Home reconstruction. Each
projection wake must consume exactly the smaller of 16 and the remaining count;
the transition from authoritative restoration must expose all 68 pending events
before projection work starts. Intermediate views remain closed.

The test saves the actual Home after two full batches, reloads it with a new job
identity, rejects an old wake and checks the restarted reconstruction through
completion. Final state and all Work/search/activity/inbox pages for both granted
members must equal the incremental reference. Duplicated accepted events remain
idempotent; gapped or corrupt events cannot promote a visible index. The prior
64/65 history assertions, 71-arm inventory and 180-second capacity deadline remain.

Eighteen host inventory tests passed in 0.078 seconds. The new Hoon assertions are
not yet compiled or executed. They test bounded replay across five batches; they
do not establish the 6,144-event maximum, large Git import latency or percentile
performance. A new reviewed controller and actual native execution are required.

## Fresh local fixture and core run passed

The first four-ship initialization at `8a2702a` created clean stopped seeds for
the pinned toolchain. Its subsequent core check passed 175 observations,
including all 71 native unit arms and the deliberate failure control. These
counts overlap. The core check took 364.377 seconds; its bound inputs were
unchanged. The complete guarded lifetime took 2,992.228 seconds, ended with exit
zero and no cleanup errors, and its owned cgroup was absent after clean shutdown.
Exact reports, seed hashes and the stop result are retained in the
[local evidence index](evidence/2026-09-29/local-core-8a2702a/index.json).

This qualifies the recorded local compile/probe scope only. It does not cover
the later 68-event recovery assertions, configured four-ship acceptance,
SDK business calls or browser/human testing. The root checkout advanced only
after shutdown; the new SDK attempt uses `6e5d194` and fresh independent piers.

Reviewed [PR #76](https://github.com/ScottTpirate/stead-urbit/pull/76) merged only
the controller-pin update into main at `0ecdbec`. Its new hosted run is bound to
controller/candidate `8077dff20c2aa7c784810ce861171068e89ba7fc`. The native inventory
remains 71 arms. Its actual result is required before the added assertions
qualify; the previous hosted pass remains bound to its earlier recorded inputs.

## Expanded replay CI failed; local reproduction pending

[Run 36524215404](https://github.com/ScottTpirate/stead-urbit/actions/runs/36524215404)
failed on workflow `0ecdbec7995e9d69564ecbe48f59011cebf7173f` and
controller/candidate `8077dff20c2aa7c784810ce861171068e89ba7fc`. It recorded
173 passing observations, four completed suites and five native transcripts
while running or validating `/tests/stead-update-capacity`, which contains the added
replay assertions. Zero named failed checks were recorded; the run still failed
and those partial counts do not qualify it.

The public native diagnostic reports `ValueError` with an unrecognized reason;
it does not retain the precise native or output-validation failure. The bound inputs
were unchanged, the guard ended after 1,341.414 seconds with exit one, the
collector completed through EOF without overflow, and worker and host cleanup
were verified. Fourteen exact public artifacts and hashes are retained in the
[failed-run index](evidence/2026-09-29/ci-36524215404/index.json).

Finish the independent SDK run, then reproduce this native suite locally using
the verified stopped seeds and inspect its private transcript. Preserve the
failed attempt and obtain an observed diagnosis before changing the test or
dispatching another hosted run. The earlier hosted pass remains valid only for
its earlier recorded inputs.

## Three-identity SDK configuration passed; first call encoding failed

The fresh SDK attempt at `6e5d194` booted all three disposable identities and
passed fourteen checks, including public sample/four-mark compilation, private
import refusal, namespace separation, exact control-member installation, Home
configuration and correlated bootstrap readiness. It then failed at the first
public capabilities request, before sending its encoded request to the native
socket. No SDK business call completed.

The private encoder trace records `eval: bail: %exit` and 52 stdout bytes that
do not form the required Newt frame. It retains the exact request and Clay
case for diagnosis; this observation alone does not establish the cause. The
[failed observation](evidence/2026-09-29/phase2-preparation/sdk-request-encoding.json)
records exact input/evidence hashes and unchanged source.

The worker ended after 2,013.210 seconds. Consumer failure triggered its lifetime
watchdog; Home was stopped prematurely, so worker cleanup was not clean. The
control member exited cleanly. The outer guard ended after 2,014.075 seconds with
exit one and no guard cleanup errors; its owned cgroup was absent afterward.
This remains a failed run. Correct the observed request construction issue and
execute the full public conformance cases in a fresh guarded attempt.

## Local replay failure reproduced with warm seeds

`make dev` at unchanged `6e5d194` reproduced the fifth-suite failure in 92.353
seconds. The private native transcript identifies a syntax error at line 148,
column 61 of `stead-update-capacity.hoon`: the newly added wide `levy` expression
was split across lines. The source bytes match the failed hosted candidate.
The corrected expression stays on one line and preserves every assertion.

The local run recorded 164 passing observations and four completed suites before
the compiler failure. Bound inputs were unchanged; the guarded fixture shut
down cleanly after 105.648 seconds, exited zero and left no owned cgroup. The
compile result remains failed. Exact reports are retained in the
[local reproduction index](evidence/2026-09-29/local-replay-6e5d194/index.json).
The correction still needs actual native execution and a new hosted run.

## Replay helper naming and SDK case representation corrected

The next local replay compile at `2d4b68a` got past the syntax error and reported
`nest-fail` at line 56: an existing serializer named `wire` shadowed the global
wire mold used by the new recovery helper. Renaming that serializer and its sole
call to `update-wire` leaves its payload and all assertions unchanged. The
failed run took 94.068 seconds, with 164 passing observations and four completed
suites. Its guard closed cleanly after 104.586 seconds with exit zero and no
cleanup errors. [Exact reports](evidence/2026-09-29/local-replay-2d4b68a/index.json)
retain the compiler failure separately from clean shutdown.

Independent source review also diagnosed the SDK encoder's column 56 syntax
error at the padded month `09`. The kernel's display date and the
[pinned ivory parser](https://github.com/urbit/urbit/blob/ac87d8bbb3915d5e7c880b97c102ffe22112335f/pkg/arvo/sys/hoon.hoon#L5426)
use different date spelling rules. The qualifier now emits `clay_case_atom`
using `%ux` from the same captured `p.case` as the existing display field. The
invocation uses that exact atom after canonical positive hex validation bounded
to 128 bits. Display-based Clay readback, the Khan unit wrapper, framing checks
and all execution limits remain unchanged.

Both corrections were independently reviewed and pushed at `4452750`. Eight
focused host regressions passed, and the overlapping full SDK host suite passed
all 102 tests in 13.222 seconds under 25% of one pinned CPU. The
[host evidence](evidence/2026-09-29/sdk-case-atom-host/index.json) records exact
source and logs. Native recompilation and a fresh full SDK run remain required.

## Corrected replay passed local native execution

`make dev` at `445275019a7f84e1e586520a90729295f3e0171d` passed 175
observations in 401.954 seconds, including all 71 positive native test arms,
the deliberately failing control and actual Home authority probes. Counts
overlap. The expanded replay assertion passed actual save/load and all five
bounded projection batches, stale-job rejection, incomplete-view refusal and
authorized page equality. The history/capacity suite remained inside its
existing 180-second deadline.

Inputs were unchanged. `make stop` completed successfully; the whole guard
lifetime closed after 439.916 seconds with exit zero and no cleanup errors.
Its owned cgroup was absent afterward. Three exact artifacts are retained in
the [local evidence index](evidence/2026-09-29/local-core-4452750/index.json).
This remains local compile/probe evidence, separate from the upcoming hosted
run, configured fixture, independent SDK and browser/human acceptance.

The corrected SDK fixture is now running fresh at `7f113a1`. Its public package
bytes remain unchanged; the source change encodes the same captured Clay case
without depending on display-date spelling. [PR #77](https://github.com/ScottTpirate/stead-urbit/pull/77)
merged the reviewed hosted-controller pin into main at
`bbcaa3ed64c59c30b08fe45e31130436878b88fd`.
[Run 36529027820](https://github.com/ScottTpirate/stead-urbit/actions/runs/36529027820)
is executing controller/candidate `7f113a1573e78de3d6c839508cfd8abd286be17b`.
Independent evidence review cleared the local pass and closed guard; actual
hosted and SDK outcomes remain pending.

## Final host check passed; lower-CPU attempt retained

The final `make check` at `cf63289` passed planning/contract checks and 660 of 661
discovered tests in 172.791 seconds at 25% of CPU 19. One optional retained local
artifact check was skipped; the authored reader checks still executed. These
are host/static/mocked and actual Linux namespace/process controls, separate
from Hoon and browser qualification.

An earlier attempt on unchanged source at 10% of the same CPU failed one host
network-control test after its peer barrier closed; 659 passed and one was
skipped in 439.450 seconds. The initiating monitor error was not captured, so
CPU pressure remains an inference. The five focused controls then passed
unchanged at 25% in 17.022 seconds before the complete successful rerun. No
source, native deadline, thermal ceiling or native CPU quota was relaxed.
All three exact logs are retained in the
[host evidence index](evidence/2026-09-29/host-final-cf63289/index.json).

## Configured restart readiness reproduced

Local `make team-dev` at `4ddb822` failed `zod-restart-fresh-bootstrap` after
744 passing observations in 958.935 seconds. All six native suites completed.
The native terminal was an explicit `poke-fail` at `stead-team-owner.hoon`
line 69: restoration must be absent and the projection must be ready. Gall
activation did not establish that combined readiness condition. The trace does
not distinguish which term remained incomplete. This identifies the local
failure; the corresponding hosted location remains a source-order inference.

Inputs were unchanged. Automatic shutdown completed; the guard ended after
966.780 seconds with exit zero, no cleanup errors and its owned cgroup absent.
The full report remains private because it contains transient handles. The
[selected failure record](evidence/2026-09-29/team-bootstrap-4ddb822/index.json)
publishes its hash, bounded source locations and exact guard evidence.

The fixture correction requires an exact owner acknowledgment and preserves
each completed refusal. It retries only explicit native poke refusals, using the
same owned process and ingress-bound nonce, at most three times. The admission
window is 180 seconds; a new exchange needs the full existing 30/75/30-second
encode/transport/decode budget. Late acknowledgments, transport errors, wrong
responses and ownership changes fail. Existing admission remains responsible
for releasing access. No native, thermal or whole-lifetime limit is relaxed.
The public CI diagnostic now uses fixed codes for these bootstrap failures.
Actual corrected native execution is still required.

The correction was independently reviewed and pushed at
`f5e79f4682cf7a78fb2a7e5b9729c76e175aff41`. The full host suite passed 671
of 672 tests with one optional artifact skip in 121.892 seconds; all 53 CI host
controls passed in 1.813 seconds. Exact tested files and both logs are retained
in the [host evidence](evidence/2026-09-29/bootstrap-host-f5e79f4/index.json).

[PR #78](https://github.com/ScottTpirate/stead-urbit/pull/78) merged only the reviewed
controller pin into main `199414291da7cbeebbb8915bfc1187e990d77348`.
[Run 36535031127](https://github.com/ScottTpirate/stead-urbit/actions/runs/36535031127)
uses controller/candidate `f5e79f4682cf7a78fb2a7e5b9729c76e175aff41`.
The hosted run remains pending. The first matching local attempt ended in the
thermal interruption described below; it is not passing evidence.

The first local retry on `f5e79f4` was thermally interrupted before the corrected
bootstrap path. Five suites and 166 checks had completed. At 238.112 seconds,
the guard observed TCPU at 93C and stopped execution under the unchanged 90C
ceiling. Its final failed record closed at 249.160 seconds, with supervised
SIGTERM cleanup and no remaining owned cgroup. The interrupted fixture's marker
and stopped state were preserved, then `make reset` restored verified clean
seeds. The [thermal record](evidence/2026-09-29/team-thermal-f5e79f4/index.json)
remains failed/unqualified. A later preflight at 77C refused startup; no other
workload was stopped. Hosted CI continues independently.

Independent read-only review confirms that the SDK result at `7f113a1` retains
its recorded scope for the unchanged SDK execution path at `f5e79f4`. All actual
SDK runner/consumer, authority Hoon, public package and pinned runtime inputs
match. The broad inventory does contain one changed but unused team-runner file;
this is execution-input equivalence, not a claim of a new SDK run.

After the reset, a later preflight observed 61C and admitted another local
`make team-dev` attempt on unchanged `f5e79f4`. This second attempt is running;
no startup limit, thermal ceiling or workload setting was changed.

## Atomic control reads and browser probe correction

An actual atomic replacement between opening and inspecting a heartbeat file
can leave the open inode with zero links. The previous reader rejected that
snapshot. The corrected reader discards it and reopens the same anchored,
no-follow pathname at most three times. Hard links, nonregular or oversized
files, parse failures and every lease identity, freshness and policy check
remain refusals. The ingress diagnostic retains the first closed retirement
code through later monitor observations and rollback; no credential or raw
exception text enters the public diagnostic.

The first full host run found two historical test fixtures deriving an old guard
from the current implementation. The fixtures now retain exact Git source blobs
from `54734c8` and `209bd33`, independently of current source. Historical
acceptance rules and original evidence remain unchanged. The focused 21-test
historical suite passes. The complete rerun passed 679 of 680 tests, with one
optional artifact skip, in 173.899 seconds. All 54 CI host controls passed in
2.409 seconds. The [exact host logs and tested source hashes](evidence/2026-09-29/atomic-reader-host/index.json)
retain the initial failures as well. These are host checks, separate from
native/browser qualification.

Pinned Gall removes the trailing conversion mark before an app peek; the public
synthetic probe must match `/x/public-control`. Gall turns a default-agent peek
bail into `[~ ~]`, which pinned Eyre maps to HTTP 404. The corrected browser
control keeps exact response requirements and records fixed operation labels,
status, bounded content type, byte count and complete-body hashes before asserting.
The partial fake-ship state was preserved after clean shutdown. Fresh installed
source and a new browser journey are required; these edits are not passing
native/browser evidence.

The reviewed changes are pushed as `a07911c` (reader/diagnostics) and
`874a77334533c36d7f7cb4974eb601e76cb77751` (synthetic probe/browser controls).
After preserved-state reset, a 70C preflight admitted a fresh local configured
run on `874a773`; it is in progress. [PR #79](https://github.com/ScottTpirate/stead-urbit/pull/79)
merged only the reviewed controller pin into workflow main
`ee137f1fcb10117e8b08652104eb4923d1fdc6d3`.
[Hosted run 36540906136](https://github.com/ScottTpirate/stead-urbit/actions/runs/36540906136)
uses controller/candidate `874a773` and is also pending. Repository visibility
was rechecked as public before dispatch. The unchanged workflow and all 217
controller, 49 product and 85 composed inputs were independently reconciled;
the selected product files are byte-identical to the prior controller.

## Native browser passed; ordinary Git fixture command corrected

The `874a773` Firefox journey completed all 34 required observations with exact
input/case binding and drained response capture. It remains an incomplete
browser gate because the separate Git check failed before materializing any
objects. The first manifest command's 40-digit `@ux` head began at column 113;
Lens recorded a syntax error at column 119, its fifth hexadecimal digit. The
pinned parser requires dotted groups. The existing 120-second observation wait
then expired; this was not evidence of a slow Git import.

The correction at `04262a2` uses the existing canonical atom encoder only at
the Hoon call boundary. Leading/trailing-zero regression vectors preserve the
numeric OIDs; stored object bytes and exact 40-digit Git identities remain
unchanged. All nine focused host tests passed, including real stock-Git object
checks and separately mocked native/supervisor controls. Independent source
review cleared both the correction and its unchanged export generator for a
fresh native run. No timeout or thermal limit changed.

The failed fixture's four children exited zero without forced termination.
After the outer guard closed and its owned cgroup disappeared, the stopped
state was preserved before restoring hash-verified clean synthetic seeds.
The prepared expiry cookie belongs to this failed, stopped fixture and will
not be used to claim natural-expiry acceptance. Human onboarding remains
unexecuted.

## Current hosted native CI passed independent review

Run `36540906136/1` passed at workflow
`ee137f1fcb10117e8b08652104eb4923d1fdc6d3` and controller/candidate
`874a77334533c36d7f7cb4974eb601e76cb77751`. It recorded 789 passing observations
with 776 distinct names, including all 71 positive native arms, the deliberately
failing control, configured four-ship behavior, migration and negative controls.
Counts overlap. The guard closed after 1,901.526 seconds with exit zero,
complete collector EOF, no overflow or cleanup errors, and verified empty
owned process groups.

Independent review checked all 217 controller, 49 product and 85 composed input
files; all 81 installed files per ship; six native log/terminal transcripts;
the six admission/lifetime controls and all seven final empty cgroups. The
114,610-byte GitHub artifact matches its recorded digest and all 14 retained
members. The public report binds the trusted verifier's private worker-output
digest; the private migration/control transcripts are not reconstructed or
claimed to be published. The [exact public evidence](evidence/2026-09-29/ci-36540906136/index.json)
records this boundary.

The later `04262a2` formatter changes an imported, captured but uncalled browser
Git observation helper. The hosted worker invokes team, migration and negative
checks, not `team-git-check`. Its executed paths and product files are unchanged;
independent review found no need for another CI run solely for this helper edit.
The complete captured inventory is not unchanged, and this remains CI execution
at `874a773`. Actual local browser/Git execution qualifies the helper separately.

URB-110's hosted CI criteria are evidenced by this publication. Whole Phase 2
still requires a fully passing browser/Git closeout, natural expiry, the unaided
human trial and reviewed integration. The earlier CI and browser failures remain
failed evidence.

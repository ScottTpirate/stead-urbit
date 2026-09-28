# Phase 2 preparation checkpoint

Recorded 2026-09-28 UTC. Phase 2 is incomplete. Its six milestone issues
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
It is not installed by any runner and has not compiled or executed; see the
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
candidate. The result is pending. It does not qualify the combined supervisor
or new ingress code, which the separately pinned controller does not execute.

## Remaining execution

The user needs K4 running. Local native/browser qualification and the human
trial remain paused. Stead is stopped; no K4, fan or desktop settings were changed
for this preparation. Local admission still requires 75°C or lower and stops at 90°C.

The remaining gates are a complete hosted native compile/unit/multi-ship/migration
run, the independent SDK consumer, fresh local native/browser journeys including
natural session expiry, and the uncoached human trial. Review their exact-source
results against [PHASE2_ACCEPTANCE](PHASE2_ACCEPTANCE.md), then integrate the
reviewed PRs and reconcile the six issues. Linux fake ships suffice for this
phase; no purchased identity or separate public Urbit server is required.

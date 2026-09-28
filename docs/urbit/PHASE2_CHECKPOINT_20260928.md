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

The v3 archive's 13 public exports and toolchain lock were checked against exact
Git source `16651c89b2d63f4bebc43580b170b75e4252160e`. Eleven real local Git/package
controls passed. The independent builder, compiled artifact transfer and runtime
consumer still need implementation and native execution; see the
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
is pending qualification at this checkpoint; its actual result must be inspected.

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

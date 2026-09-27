# Phase 0/1 checkpoint — September 26, 2026

**Phases 0 and 1 are complete. The full Phase 1 gate passes all 73 requirements
and independent review finds no blockers. Phase 2 begins with URB-180 / #21.**

The [acceptance record](PHASE1_ACCEPTANCE_20260926.md) supersedes the pending
native work described below. Core07 at `dd0e8c0` completed 496 direct native
checks and all eight capacity/predecessor recipes, with clean shutdown. The
separate 58-check Gall schedule and 476 host tests retain their distinct roles.
The exact native, guard and source bytes are retained with the passing
[final reconciliation](evidence/2026-09-26/phase1-final-dd0e8c0/derived-v7/qualification.json).
The widget was restored at 00:32:50 UTC; fans were already restored and no
browser setting was changed.

## Historical checkpoint before core07

The following account preserves the earlier blockers, attempts and planned
integration sequence. Its pending statuses describe that earlier checkpoint.

**Phase 0/M0 is closed with all five issues complete; Phase 1 remains open. Phase 2 has not started.**
The aggregate branch `increment/phase01-closeout-20260925` is pushed through
`dd0e8c0ce8d1d00f15de6b07e2e26d368c5c3774` in draft
[PR #42](https://github.com/ScottTpirate/stead-urbit/pull/42). The latest native
logs and closeout notes are retained locally pending a complete full rerun. Core06
at `dd0e8c0` was thermally interrupted after 313 passing direct checks and 145 QA
passes plus three frozen deferrals. Its exact failed result is retained; no
partial-prefix combination qualifies. The preceding core05 at
`5208f3273426e8fe76dc8622ffe93ace93982e17`, completed 145 main cases plus three
frozen deferrals and seven delivery cases plus the scheduled-Gall deferral,
then timed out validating a corrupted predecessor with 4,096 journal events.
That timeout is a failure, not an expected rejection. The stopped failed state
and exact evidence are preserved. The [focused capacity diagnostic](evidence/2026-09-26/native-attempts/capacity01/index.json)
at `3f0f377` compiled the revised client and verified all five malformed-load
rejections and valid 4,096-event migration. Full-state validations took
117–119 seconds under the CPU50% quota. The diagnostic then failed an incorrect
expectation of a JSON denial after the contributor's binding was removed;
its result subscription was rejected before the client sent a poke.

The [independently reviewed correction](evidence/2026-09-26/missing-binding-fix/index.json)
at `dd0e8c0` requires that exact watch rejection, an actual contributor poke with
unchanged protected state, and an explicit denial at the native final transition.
It changes no Hoon, authorization rules or guard limits. All **476 host tests**
pass, and a fresh **58-check native Gall schedule** passes at the same source.
The full core rerun and final 73-row reconciliation remain pending. Prior
records retain their original source bindings.
No implementation PR has
been merged and no GitHub CI or human approval is claimed.

## Accepted bounded work

Issues #2–#6 and #24 are closed for repository preservation, pinned toolchain,
four-fake harness, Git dependency evaluation, frozen contracts and threat-map
**design** acceptance. The smoke at `4236ed5` executed all 12 frozen calls and
actual home restart under a completed guard. The independent 14-vector Git audit
records explicit non-adoption of the candidate backend. No original Stead
approval transfers to this derivative. Browser and future route security remain
with the owning later issues.

The workflow-v2 source committed as `0d877cff` passed planning and both contract
freezes, then **464 host/static/mocked tests**. The CPU50%/10ms CPU19 wrapper
took 68.666 seconds; [exact logs](evidence/2026-09-26/workflow-v2-source/index.json)
are retained. The subsequent socket-path fix passed **465 host tests**, including
an actual Unix-socket round trip in a deeply nested checkout, in 68.707 seconds;
see the [source-bound host record](evidence/2026-09-26/socket-path-fix/result.json).
The independently audited 142-test capture at `5208f32` overlaps the full suite
and must not be added to it. It supports [seven nonnative dispositions](evidence/2026-09-26/phase1-nonnative-v4/dispositions.json);
the separate readiness record still has 66 missing native obligations. Earlier
138-test and other captures retain their original bindings.
The later [timeout-lifecycle fix](evidence/2026-09-26/delivery-lifecycle-fix/index.json)
passed all **470 host tests** at `5208f32` in 68.669 seconds (67.979 seconds for
the unittest suite). These host results are not Hoon execution.

The native compile/save-load probes previously passed all 53 checks, and
`make dev` passed in about 58 seconds at its recorded source. Full populated
behavioral/migration qualification remains separate. [DEV_FLOW.md](DEV_FLOW.md)
documents the Linux edit/build/test loop and stopped-seed recovery.

## Current native evidence and remaining gates

| Gate | Actual result | Remaining execution |
| --- | --- | --- |
| Workflow reference admission | [prequal12](evidence/2026-09-26/native-attempts/prequal12/index.json): all six references, 134 checks, 96 native commands and the complete weak-mutation continuation control passed at `0d877cff`; completed outer guard. | Completed prerequisite for the recorded v2 pair. |
| URB-170, issue #20 | [Fresh paired v2 run](evidence/2026-09-26/workflow-evaluation-v2/README.md): complete one-shot private scoring, **5/6 per condition**. Both T05 suites missed the actual `~bud` mutant; all five subjects and every submitted test arm were retained. [Final acceptance review](evidence/2026-09-26/workflow-evaluation-v2/URB170_FINAL_ACCEPTANCE.md) also verifies all separate contributor-tooling criteria. | Published; issue #20 and M0 closed, 5/5 issues complete. The v1 comparison remains separately incomplete; no candidate repair, efficacy or isolation claim. |
| URB-040/050, issues #7/#8 | Core05 reached 145 QA passes + three deferrals and seven delivery passes, then timed out. [Capacity01](evidence/2026-09-26/native-attempts/capacity01/independent-diagnosis.json) subsequently verified full-state validation, then failed the missing-binding test expectation. [Core06](evidence/2026-09-26/native-attempts/core06/index.json) at `dd0e8c0` was thermally interrupted after 313 direct checks and 145 QA passes. All failures are retained. | Complete full core rerun, including the corrected probe and all eight capacity/predecessor recipes. No partial-prefix combination qualifies. |
| Scheduled Gall | [58 native checks passed](evidence/2026-09-26/phase1-final-dd0e8c0/gall/index.json) at `dd0e8c0`, including the delayed old leave and deliberately wrong pending-count control. Closed outer guard and exact logs retained. | [Independent semantic review](evidence/2026-09-26/phase1-final-dd0e8c0/reviews/gall-final04-independent-review.json) complete for this obligation; include it in final reconciliation. Earlier passes remain separately retained. |
| Phase 1 acceptance | [Seven refreshed source/N-A/host dispositions](evidence/2026-09-26/phase1-nonnative-v5/dispositions.json) use the actual 142-test capture at `dd0e8c0`. Their separate readiness still reports 66 missing native obligations. [Independent portable audit](evidence/2026-09-26/phase1-final-dd0e8c0/reviews/nonnative-v5-dd0e8c0-portable-audit.json) verifies all seven; earlier records keep their bindings. | Bind 65 core + one scheduled-Gall native obligations and seven nonnative obligations to exact final inputs, derive the gate and independently review all 73 rows. |

The original failed runs remain unchanged. This includes the earlier populated
round-trip failure, workflow timeouts/size failures, thermal refusals, and the
[Dojo timeout recovery](evidence/2026-09-26/native-timeout-recovery/index.json).
Process shutdown does not guarantee that a timed-out request is absent from a
disposable pier; preserve the failed run and restore verified stopped seeds.

The [independent core04 diagnosis](evidence/2026-09-26/native-attempts/core04/independent-source-diagnosis.json)
confirms a five-second host socket deadline while the native thread allowed 55 seconds.
Home restarted before that native request finished. The contributor subsequently
reported a broken pipe and SIGSEGV; no core image was generated, so that causal
mechanism remains inferred. A local sender connection refusal must never qualify
as expected home unavailability. The corrected test must drain the specific
native timeout, then verify the same contributor process survives recovery.
The crashed disposable state is separately preserved; it is not a clean seed.
[Focused deliverycheck02](evidence/2026-09-26/native-attempts/deliverycheck02/index.json)
then passed both real 55-second native timeout/recovery cycles at `5208f32`,
with the same live contributor, unchanged protected state and successful
follow-up protected reads. The [independent review](evidence/2026-09-26/native-attempts/deliverycheck02/independent-review.json)
verifies exact transport and a completed guard (65 C peak). This verifies the
narrow lifecycle correction; it neither proves the old SIGSEGV mechanism nor
replaces the full acceptance schedule.

## Thermal and review boundaries

Admission remains 75 C, stop 90 C, sensor freshness three seconds and native
CPU50%/10ms with one CPU of affinity. The core03 guard stopped all owned work
cleanly and recorded no cleanup escalation. Its interrupted case is not an
application failure assertion and its partial successes cannot close Phase 1.
The host can also exceed the cutoff while Stead is stopped, as retained earlier
observations demonstrate. The [retained host samples](evidence/2026-09-26/host-load-observations/index.json)
show periodic high CPU use by `omarchy-agent-u` coinciding with temperature
spikes. This does not prove sole causation. The owner approved temporarily
removing the agent-usage widget during native qualification and restoring it
afterward. The change was verified through the running shell's effective layout.
The first focused delivery check thermally stopped at 92 C with the widget
disabled; the widget was not the sole source of heat. The owner-authorized temporary fan boost was reapplied after
local authentication, with original curves saved and a one-hour restoration limit.
After core05, [all 34 original fan values and the desktop configuration](evidence/2026-09-26/host-load-observations/restoration-and-window02/index.json)
were restored and independently read back. The owner paused Chromium; no
automated browser quota was applied. No security gate or thermal threshold changed.

The later [widget pause03](evidence/2026-09-26/host-load-observations/widget-pause03/index.json)
ended after core06's thermal interruption. The exact original configuration and
effective running widget were restored and verified at 22:55 UTC. Fans remained
at their original settings; Chromium remained under the owner's control.

The paired v2 audit reconciled every observed wrapper call, final candidate
hash, model setting and charged interval. Both conditions used the same observed
model alias/settings, with unknown immutable backend revision. Five passes each
show no observed pass-count benefit. The full tool catalog was exposed, so trace review
is not complete tool isolation. All 15 persisted encrypted parent messages match
actual child delivery descriptors. Twelve earlier plaintexts are unavailable;
three are separately attributed integrator observations. Preserved initial
plaintext-equality flags remain false. Complete prompt equality is not established.
Active times include compaction/delivery overhead without retrospective adjustment.
Hidden reasoning and
system/developer content are excluded from portable traces. Independent agent
review is not human approval or a CI result.

## Integration and Phase 2

All prior branch work is contained in the aggregate chain:
`origin/main 4bb28c6 → #33 9697154 → #34 77428f6 → #35 aa93f41 → #36 ce808a2 → #41 87ea9e1 → #42`.
Local branches, main and the old review worktree reference are preserved. Local
`increment/native-core-qualification` points to PR #36 while its remote points
to PR #35; do not bulk-push branches. Qualification and final source review must
precede integration; retain the commits to which native evidence is bound.

After Phase 0/1 acceptance, begin Phase 2 with a narrow published developer
package and independent native Work client, then individual sessions and the
multi-user Work/Docs browser journey. Private search/activity, native CI and
onboarding/accessibility complete that phase. The local Linux fake ships need
no purchased identity, hosted Urbit server or GPU. A browser journey can run
locally once the interface and session boundary exist. Real identities,
external hosting and live-network recovery remain later owner-controlled work.

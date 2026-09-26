# Phase 0/1 checkpoint — September 26, 2026

**Phase 0 acceptance evidence is complete; Phase 1 remains open. Phase 2 has not started.** The local aggregate branch
`increment/phase01-closeout-20260925` is associated with draft
[PR #42](https://github.com/ScottTpirate/stead-urbit/pull/42). The latest local
closeout commits and retained evidence await publication. The latest completed full attempt, core05 at
`5208f3273426e8fe76dc8622ffe93ace93982e17`, completed 145 main cases plus three
frozen deferrals and seven delivery cases plus the scheduled-Gall deferral,
then timed out validating a corrupted predecessor with 4,096 journal events.
That timeout is a failure, not an expected rejection. The stopped failed state
and exact evidence are preserved. The next focused capacity diagnostic requires
specific native rejection context and measures bounded full-load duration;
it has not yet been executed. Final 73-row reconciliation remains pending.
Prior records retain their original source bindings.
The independently reviewed diagnostic source is now
`a1d35b27d8ee482b1854c7352ebc6eecf96a2b08`; [472 host tests pass](evidence/2026-09-26/capacity-fix/index.json).
Its Hoon client change has not yet been compiled or executed.
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
| URB-170, issue #20 | [Fresh paired v2 run](evidence/2026-09-26/workflow-evaluation-v2/README.md): complete one-shot private scoring, **5/6 per condition**. Both T05 suites missed the actual `~bud` mutant; all five subjects and every submitted test arm were retained. [Final acceptance review](evidence/2026-09-26/workflow-evaluation-v2/URB170_FINAL_ACCEPTANCE.md) also verifies all separate contributor-tooling criteria. | Publish reviewed closeout and reconcile issue/milestone metadata. The v1 comparison remains separately incomplete; no candidate repair, efficacy or isolation claim. |
| URB-040/050, issues #7/#8 | [core05](evidence/2026-09-26/native-attempts/core05/index.json): 145 QA passes + three frozen deferrals; 495 direct checks and seven delivery cases passed. After reaching 4,096 predecessor events, the policy-corruption load timed out. The guard did not thermally stop (69 C peak); home shutdown required a forced exit. | Measure and verify full-state loads with specific rejection predicates, complete all eight capacity/predecessor recipes, then rerun/reconcile the full current-source schedule. No partial-prefix combination qualifies. |
| Scheduled Gall | [58 native checks passed](evidence/2026-09-26/phase1-final-5208f32/gall/index.json) at `5208f32`, including the delayed old leave and deliberately wrong pending-count control. Closed outer guard and exact logs retained. | Include the independent semantic review in final reconciliation. Earlier `55475f0` and `0d877cff` passes remain separately retained. |
| Phase 1 acceptance | Seven typed source/N-A/host dispositions are retained at `5208f32`; core05 failed, and the new diagnostic changes require fresh source bindings. | Bind 65 core + one scheduled-Gall native obligations and seven nonnative obligations to exact final inputs, derive the gate and independently review all 73 rows. |

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

# Phase 0/1 checkpoint — September 26, 2026

**Phases 0 and 1 remain open. Phase 2 has not started.** Implementation and
retained evidence are on `increment/phase01-closeout-20260925`, in
[PR #42](https://github.com/ScottTpirate/stead-urbit/pull/42). Latest executed
source: `8334a75cad4c2b063147e7e3352cdf76da0d5893`. No implementation PR has
been merged and no GitHub CI or human approval is claimed.

## Accepted bounded work

Issues #2–#6 and #24 are closed for repository preservation, pinned toolchain,
four-fake harness, Git dependency evaluation, frozen contracts and threat-map
**design** acceptance. The smoke at `4236ed5` executed all 12 frozen calls and
actual home restart under a completed guard. The independent 14-vector Git audit
records explicit non-adoption of the candidate backend. No original Stead
approval transfers to this derivative. Browser and future route security remain
with the owning later issues.

At `8334a75`, `make check` passed planning and both contract freezes, then
**447 host/static/mocked tests**. The CPU50%/10ms CPU19 wrapper took 66.429 seconds;
[exact logs](evidence/2026-09-26/host-check-8334a75/index.json) are retained.
The independently audited 137-test capture overlaps this suite and must not be
added to it. It supports [seven nonnative dispositions](evidence/2026-09-26/phase1-nonnative/dispositions.json);
the separate readiness record still has 66 missing native obligations.
These host results are not Hoon execution.

The native compile/save-load probes previously passed all 53 checks, and
`make dev` passed in about 58 seconds at its recorded source. Full populated
behavioral/migration qualification remains separate. [DEV_FLOW.md](DEV_FLOW.md)
documents the Linux edit/build/test loop and stopped-seed recovery.

## Current native evidence and remaining gates

| Gate | Actual result | Remaining execution |
| --- | --- | --- |
| Workflow reference admission | [prequal11](evidence/2026-09-26/native-attempts/prequal11/index.json): all six tasks, 121 checks and evaluator controls passed at `8334a75`; completed outer guard. | New prequalification after the versioned scorer repair. |
| URB-170, issue #20 | [Actual fresh-context paired v1 run](evidence/2026-09-26/workflow-evaluation/README.md): five verified task passes per condition. Both T05 suites missed the outsider mutant; the scorer bailed before two remaining mutants. T05 qualification is invalid and the overall comparison incomplete. | Retain v1, repair complete mutation collection, freeze v2, then run two fresh contexts once with complete private scoring and independent trace/timing review. No old-candidate retries or efficacy claim. |
| URB-040/050, issues #7/#8 | [core02](evidence/2026-09-26/native-attempts/core02/index.json): thermal stop at 92 C, after 90 passed cases, one typed deferral, one guard-interrupted case and 56 not run. | Full corpus, populated round-trip, migration/capacity, concurrent/delivery/recovery/export lanes under a completed guard. |
| Scheduled Gall | The earlier Gall08 compiled and passed 14 positive assertions. Its actual negative tang was rejected by the old parser; the exact-format correction is reviewed. | Fresh complete positive/negative run at the same source as full core. |
| Phase 1 acceptance | Seven typed source/N-A/host dispositions are retained at `8334a75`; native acceptance remains absent. | Reconcile all 66 native plus seven nonnative obligations against exact current execution and independently review the artifacts. |

The original failed runs remain unchanged. This includes the earlier populated
round-trip failure, workflow timeouts/size failures, thermal refusals, and the
[Dojo timeout recovery](evidence/2026-09-26/native-timeout-recovery/index.json).
Process shutdown does not guarantee that a timed-out request is absent from a
disposable pier; preserve the failed run and restore verified stopped seeds.

## Thermal and review boundaries

Admission remains 75 C, stop 90 C, sensor freshness three seconds and native
CPU50%/10ms with one CPU of affinity. The core02 guard stopped all owned work
cleanly and recorded no cleanup escalation. Its interrupted case is not an
application failure assertion and its partial successes cannot close Phase 1.
The host can also exceed the cutoff while Stead is stopped, as retained earlier
observations demonstrate; temperature alone does not identify the responsible
process or hardware cause. No security or thermal threshold was raised.

The paired v1 audit reconciled every observed wrapper call, final candidate
hash, model setting and charged interval. Both conditions used the same observed
model alias/settings, with unknown immutable backend revision. Five passes each
show no observed benefit. The full tool catalog was exposed, so trace review
is not complete tool isolation. Encrypted incoming delivery metadata is retained
with a separately attributed integrator plaintext ledger. Hidden reasoning and
system/developer content are excluded from portable traces. Independent agent
review is not human approval or a CI result.

## Integration and Phase 2

All prior branch work is contained in the aggregate chain:
`main 4bb28c6 → #33 9697154 → #34 77428f6 → #35 aa93f41 → #36 ce808a2 → #41 87ea9e1 → #42`.
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

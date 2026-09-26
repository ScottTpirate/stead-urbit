# Phase 0/1 checkpoint — September 26, 2026

**Phases 0 and 1 remain open. Phase 2 has not started.** Reviewed implementation
and evidence are pushed on `increment/phase01-closeout-20260925`, in
[PR #42](https://github.com/ScottTpirate/stead-urbit/pull/42). The latest native
helper source is `b2ec89c258c5544a3344c3665a81700b9e7075b4`; subsequent checkpoint
commits change documentation/evidence only. No implementation PR was merged.

## Completed and independently reviewed

Issues #2–#6 and #24 are closed for their bounded repository, toolchain, harness,
Git evaluation, contract-freeze and threat-map design acceptance. The real
four-fake smoke at `4236ed5` covered all 12 frozen calls and actual home restart;
its completed guard and exact source context were independently verified.
Contract review recomputed all 14 frozen file hashes. Threat-map closure is a
design/test-inventory decision; browser isolation and later route qualification
remain required. The 14-vector stock-Git audit records explicit non-adoption of
the candidate backend. No original Stead approval was inherited.

At `b2ec89c`, `make check` passed the plan, ecosystem and both contract checks,
then **445 host/static/mocked tests in 65.579 seconds**. The complete wrapper
took 66.297 seconds with CPU50%/10ms on CPU19. [Exact logs](evidence/2026-09-26/final-host-checkpoint/index.json)
are retained. These tests do not establish Hoon behavior. Independent agent
source reviews are recorded in [the review log](reviews/PHASE01_INDEPENDENT_REVIEW_20260925.md);
they are not human/GitHub approvals or CI passes.

The native code previously passed 53 compile/save-load probes, and the daily
`make dev` flow passed in about 58 seconds at its recorded source. Full current
qualification remains distinct. [DEV_FLOW.md](DEV_FLOW.md) documents the Linux
edit/build/test commands and the conditions they actually prove.

## Native results and remaining work

| Gate | Observed result | Required next execution |
| --- | --- | --- |
| Scheduled Gall | Gall08 compiled and passed 14 positive assertions. Its real negative tang was rejected by the old parser; that attempt stays failed. The reviewed exact-tang parser correction has host regressions. | Fresh complete positive/negative scheduled-Gall run and completed guard. |
| URB-170 workflow, issue #20 | Reference T01/T02 passed in prequal04 and prequal06. T03 timed out; prequal06 correctly left T04–T06 unrun. A typed probe, separate initial-save diagnostic, progress markers and native result-size bound are now reviewed. The cause of the timeout remains unconfirmed. | All six references/controls must pass before fresh baseline/assisted participants, real public feedback, one private score per task and complete independent tool/timing audit. |
| URB-040/050, issues #7/#8 | The earlier full corpus failed a populated save/load roundtrip after 145 native cases. The saved-format repair passed a smaller native probe. | Fresh full core, concurrent calls, delivery, populated migration/capacity/recovery and exact Git results; reconcile all 66 native plus seven separately typed obligations. |

The reviewed [workflow tooling bundle](evidence/2026-09-26/workflow-tooling/index.json)
retains exact workspace/broker/timer sources and synthetic host probes, including
the original incomplete file-inventory evidence. The corrected file-operation
probe has 41 checks; broker tests mock native execution; timer tests use synthetic
time and temporary files. No participant, real public-feedback delivery or
skill-effectiveness result is claimed. Two equal public input directories are
prepared locally, but their actual initial T02 diagnostic remains pending a
completed reference prequalification. Both clocks remain unstarted.

Prequal05 and prequal07 stopped before tasks with the supervisor error
`Stale, future or reversed thermal sample`. The exact supervisor excerpts are
retained in the final environment record; the combined error does not identify
which condition occurred. Prequal08 stopped before tasks at an actual 96 C sample. All reports,
source contexts and closed outer guards are retained as failures. No limit was
raised: admission remains 75 C, stop 90 C, sensor freshness three seconds and
CPU50%/10ms. After interruptions, all owned ships were stopped and their test
state restored from verified stopped synthetic seeds. [Recovery records](evidence/2026-09-26/native-recovery-checkpoints/index.json)
retain the earlier cancellation/resets; [the final environment record](evidence/2026-09-26/environment-closeout/index.json)
retains the later resets and fan restoration.

A separate 30-sample observation reached **96 C while the fixture was stopped
before and after**, with both fans at roughly 6,600–6,700 RPM. Individual sensor
reads took at most 0.002458 seconds in that observation. This proves the host can
exceed the native-test ceiling independently of Stead; it does not attribute the
spikes to a particular other process or diagnose their hardware cause. Repeated
native retries were paused. A quiet workload window or a separately approved
Linux test host is needed for reliable qualification. No other workload was
stopped and no CPU/power profile or thermal ceiling was changed. The temporary
fan boost was restored and all 34 original curve/enable values verified.

## Branches and next phase

Independent ancestry review verified the complete chain:
`main 4bb28c6 → #33 9697154 → #34 77428f6 → #35 aa93f41 → #36 ce808a2 → #41 87ea9e1 → #42`.
All prior local branch work is contained in the aggregate. Local
`increment/native-core-qualification` points to PR #36's commit while its remote
is PR #35's head; do not bulk-push branches. Local main and old review/worktree
refs were preserved. All implementation PRs remain drafts with no GitHub checks
or approval claimed. Final qualification/review must precede integration; merge
commits or one aggregate merge can preserve evidence-bound commit identities.

After Phase 0/1 acceptance, Phase 2 starts with individual sessions, the narrow
public API and a usable two-principal Work/Docs browser journey, followed by
private search/activity, native CI and onboarding/accessibility. The local Linux
fake ships need no hosted Urbit server, purchased identity or GPU. Browser testing
can be local once that interface exists. Real identities, hosting and live
network/recovery acceptance are later, owner-controlled work.

For the next operator: keep the latest helper source unchanged, confirm a quiet
host with `make preflight`, then use a fresh `make start`/`make wait-ready` lifetime
for `make skill-prequalify`; always finish with `make stop`. Inspect the new T03
initial-save and per-case/encoded-size markers before choosing any further code
change. Do not bypass the guard or treat a compile message as six-task success.
The full core and scheduled-Gall runs must bind the final common source closure
before building the 73-obligation evidence and admitting Phase 2.

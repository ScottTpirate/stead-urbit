# Phase 1 acceptance — September 26, 2026

The complete native run has finished at
`dd0e8c0ce8d1d00f15de6b07e2e26d368c5c3774`. The final reconciliation passes all 73 requirements with no errors.
Independent semantic review accepts this bounded phase with no blocking findings.
[Core review](evidence/2026-09-26/phase1-final-dd0e8c0/reviews/core07-independent-review.json)
and [final 73-requirement review](evidence/2026-09-26/phase1-final-dd0e8c0/reviews/phase1-final73-independent-review.json)
are retained exactly. [Source preservation](evidence/2026-09-26/phase1-final-dd0e8c0/source-preservation.json)
verifies all 156 host/native-tested files against the executed commit.
The aggregate [PR #42](https://github.com/ScottTpirate/stead-urbit/pull/42)
preserves the complete reviewed stack and native source ancestry.
The execution ended September 27 at 00:32 UTC, September 26 locally.

| Evidence | Observed result | Exact retained record |
| --- | --- | --- |
| Full native core, four isolated fake ships | 496 direct checks passed; no failed checks. All 148 QA cases reached: 145 passed and three original typed deferrals retained. | [Core07](evidence/2026-09-26/phase1-final-dd0e8c0/core/index.json) |
| Capacity and predecessor qualification within that same run | All eight recipes and 12,897 assertions passed, including legitimate 4,096-event predecessor construction, five malformed-load rejections, valid migration, project-local revocation reserves and each resource boundary. These assertions are part of the core run, not another test run. | [Native result](evidence/2026-09-26/phase1-final-dd0e8c0/core/native.json) |
| Scheduled Gall | 58 native checks passed, including receiver-boundary delayed old leave and deliberately wrong pending-count control. | [Gall run](evidence/2026-09-26/phase1-final-dd0e8c0/gall/index.json), [independent review](evidence/2026-09-26/phase1-final-dd0e8c0/reviews/gall-final04-independent-review.json) |
| Host/static/mocked suite | 476 tests passed. The separate 142-test capture overlaps this suite; do not add the counts. | [Host execution](evidence/2026-09-26/missing-binding-fix/index.json), [typed evidence audit](evidence/2026-09-26/phase1-final-dd0e8c0/reviews/nonnative-v5-dd0e8c0-portable-audit.json) |

The acceptance manifest requires 65 native core obligations, one scheduled-Gall
obligation and seven separately typed source, N/A, host or mocked-sensor
obligations. The raw QA and delivery deferrals remain unchanged. They are resolved
only by the manifest's separate proof types, never by relabeling a skip as native
execution. The evidence derivation replays the retained command bytes; the gate
checks the installed Clay, loaded Python, toolchain, corpus and committed source
identities.

The first reconciliation preserved 66 successful native derivations but failed
because a source-review proof used expanded prose in the exact manifest scope
field. The next failed because its continuity reference still named that earlier
proof. Both failed results are retained under `derived/` and `derived-v6/`.
The v6/v7 records correct only those evidence fields, preserve the expanded
review prose and all historical bytes, and change no source, acceptance rule or
native result. The final output is [derived-v7](evidence/2026-09-26/phase1-final-dd0e8c0/derived-v7/qualification.json).

The full core execution took 5,473.523 seconds under the existing 50% CPU quota;
capacity/predecessor work accounted for 3,896.109 seconds. These are observed
qualification durations, not production performance targets. The guard completed
with exit zero and a 78 C maximum recorded sensor value. All four ships stopped
cleanly. Admission remains 75 C, stop 90 C and sensor freshness three seconds.
The authorized [widget pause04](evidence/2026-09-26/host-load-observations/widget-pause04/index.json)
ended with the original configuration and effective widget restored at 00:32:50
UTC. Earlier fan settings were already restored. No automated Chrome change was
made.

This accepts only the initial authoritative Work/Docs and permission slice:
current authorization at the final transition, bounded synthetic principals,
revision conflicts, retries, scoped reads, revocation, versioned state, populated
save/load, fenced graceful process restart, canonical native document Git objects
and stock-Git export. It does not establish browser authentication, employee
sessions, general Smart HTTP Git, arbitrary installed-app isolation, abrupt-crash
recovery, live networking, production deployment or confidential-data readiness.

Phase 0 remains separately accepted: pinned development inputs, isolated harness,
dependency/license decision and contributor workflow evaluation. The workflow
comparison was a 5/6 tie; both conditions missed the same T05 mutation. That
bounded evaluation is complete without claiming improved effectiveness.

Following this acceptance, Phase 2 begins with the narrow public
SDK under [URB-180 / #21](https://github.com/ScottTpirate/stead-urbit/issues/21),
then an independent consumer, individual sessions and the multi-user browser
journey. SDK packaging alone does not close that issue. See [local development](DEV_FLOW.md)
for the Linux test loop and later user-facing testing requirements.

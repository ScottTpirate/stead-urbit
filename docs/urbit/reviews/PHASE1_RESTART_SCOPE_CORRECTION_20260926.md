# Phase 1 restart requirement — attributed correction

Author: `/root`, integrating the independent finding of
`/root/core_acceptance_review` at source
`0d877cff4319de8d437f0da58d4518535f758c36`. This corrects explanatory prose;
it changes no Hoon, runner, contract, acceptance predicate or frozen manifest.

`NATIVE_CORE.md` previously described controlled abrupt-crash recovery as a
required, nondeferred Phase 1 lane. That was an unsupported additional
requirement. The master directive requires restart/recovery; the ecosystem M1
exit and URB-040 require restart persistence, and
[issue #7](https://github.com/ScottTpirate/stead-urbit/issues/7) names cold restart.
The frozen `warm-home-restart` requirement explicitly
specifies graceful fenced process replacement and excludes abrupt-crash proof.
Current save/load and predecessor migration remain separate required assertions.

The actual implementation stops the old home, requires a nonforced exit 0,
starts a distinct process using the retained pier, and reads protected state
through current authorization. The qualifying lane must also demonstrate exact
retry, denied access and stock-Git export identity after restart. A saved-state
round-trip alone does not satisfy it. No completed full current core run has
established this lane yet.

Controlling and implementation references:

- [Master directive](../MASTER_BUILD_DIRECTIVE.md), Phase 1.
- [Ecosystem plan](../ECOSYSTEM_PLAN.md), M1; [backlog](../../../specs/urbit/backlog.json), URB-040.
- [Frozen gate](../../../specs/urbit/v2/qualification-gate.json), `warm-home-restart`.
- [V2 amendment](../CONTRACT_AMENDMENT_2.md), distinct save/load, migration, restart and recovery assertions.
- `scripts/urbit/core_test.py`, `scripts/urbit/core_cases_v2.py`,
  `scripts/urbit/build_phase1_evidence.py` and
  `specs/urbit/fixtures/native-cases-v2.json`.
- [Independent preflight review](../evidence/2026-09-26/phase1-current/reviews/core-acceptance-preflight-review.json),
  including exact source hashes and the full 73-obligation review checklist.

Earlier hash-bound reviews remain unchanged, including
[September 25 review](PHASE01_INDEPENDENT_REVIEW_20260925.md) and
[September 26 source review](NATIVE_CORE_SOURCE_REVIEW_20260926.md). This correction
supersedes only their characterization of abrupt-crash testing as a current
Phase 1 prerequisite. Abrupt-crash recovery, production backup/restore, OTA and
live migration remain unqualified; this note assigns them no invented milestone
and claims no runtime pass.

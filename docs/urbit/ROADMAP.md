# Phased implementation roadmap

## Current next increment — November 15, 2026

Adopt the [product experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) on the
existing native foundation. The [32-package plan](../../specs/urbit/product-execution-plan.yaml)
adds follow-up scope to existing URB parents; A–F are work groups, not new M0–M6
milestones. The [capability matrix](CAPABILITY_MATRIX.md) is the concise current
status and evidence map. Historical entries below retain their dated scope.

| Work group | Outcome | Packages / acceptance |
| --- | --- | --- |
| A | Shared product, identity, repository, revision and storage contracts | T01–T06; concrete versioned interfaces and migration decisions reviewed before shared mutations. |
| B | Daily human Work/Docs and bounded live-tree repair | T07–T11, T19; G1 with truthful navigation, permissions, conflict and recovery. |
| C | Complete agent Docs outcome | T12–T18; G3 in a no-Code project, including clarification/revision/acceptance. |
| D | Credible software forge | T20–T23; G2/G4 on the declared Git profile with exact review, checks and restore. |
| E | Bounded project automation and sustained capacity | T24/T25/T31; finite queue/budgets, exception handling and measured limits. |
| F | Installable supported beta | T26–T30/T32; independent installation/use/upgrade/recovery and capability-bound release decision. |

T01 product decisions are documented; interface/migration acceptance remains
pending. T02 reference preparation, T06 capacity inventory and T19 live-tree
investigation may proceed independently; shared-contract mutations wait for T01.
T07 consumes T01/T02; T08 additionally needs T05 and T09 needs T06. Follow the YAML
DAG rather than treating every group as a sequential barrier. Docs linking and
Docs autonomy do not wait for complete forge delivery. Code automatic acceptance
stays disabled until T22/T23 pass. T32 remains open for consolidation after shipped
T18/T23/T28, despite this initial documentation alignment.

The live tracker still has 16 open canonical tasks, including #29/URB-260, as
observed November 15. Its state is separate from November 9's bounded local
acceptance and the new independent first-time-user gates. No gate is closed by
writing this roadmap. GitHub source cutover, deployment and release remain
separate decisions tied to exact-profile evidence.

## Historical implementation and qualification timeline

No dates or effort estimates here are promises. Each phase exits on evidence, not elapsed time.

September 26: Phases 0 and 1 are complete. The [Phase 1 native gate](PHASE1_ACCEPTANCE_20260926.md)
passes all 73 requirements with independent semantic acceptance.
September 29: The Phase 2 candidate has passing configured native, real
browser/stock-Git, independent SDK, hosted native CI and natural session-expiry
evidence. Its local native lifetime is closed and the stopped fixture preserved.
The [current qualification record](PHASE2_QUALIFICATION_20260929.md) binds each
result to its source and scope. [PR #67](https://github.com/ScottTpirate/stead-urbit/pull/67)
integrated the reviewed implementation; five of six M2 issues are closed. At that checkpoint,
the uncoached human Work/Docs trial in #29 was still open. The
[preparation checkpoint](PHASE2_CHECKPOINT_20260928.md) retains earlier failed
attempts and their historical limits.

October 2: [fresh native, browser and Git checks passed](PHASE2_ONBOARDING_20261002.md)
at the integrated source, with clean shutdown and restoration. The human trial
expired without qualifying activity or feedback.

November 8: The native Git pack path now reconstructs stock packs and emits
exact objects that stock Git can index. The graph helper proves bounded
reachability and exact-commit file reads over a scoped view. Git still needs
authenticated Smart HTTP and an authoritative repository transaction. The
offline desk and recovery work verifies [packaged Home HTTPS](RELEASE_PACKAGING.md#configured-home-https-verification)
and [current Work and Docs portability](PORTABLE_RECOVERY_PROFILE.md).
Full authority recovery, upgrades and a reviewed canary remain Phase 4 gates.

| Phase | Deliverable | Gate |
|---|---|---|
| 0 | Independent repo, pinned dependencies, four-fake-ship harness, Git feasibility audit, contributor workflow | Actual native smoke tests, recorded reuse decisions and executed baseline/assisted workflow evaluation |
| 1 | One authoritative home, core Work/Docs state, explicit permissions | Restart, negative access, idempotence and revision tests |
| 2 | Individual sessions, useful shared web UI, native CI | Two users collaborate while an outsider cannot read or mutate through alternate paths |
| 3 | Native Git, reviews and limited agent proposals | Stock Git conformance, branch/ref policy, revoked-token and corrupt-pack tests |
| 4 | Portable export, operational recovery, low-cost public/synthetic canary | Independent security/restore/load evidence |
| 5 | Explicit replicas, safe home migration, self-hosted dogfooding | One authoritative source of truth, fenced migration and tested exitability |
| 6 | Supported ecosystem release | Independent adopters, integration, maintainership and qualified security/recovery/distribution process |

November 9: Independent Astra review replaces the earlier human-trial gate for
URB-260 and accepted the real local Work/Docs journey at `0aa32ae`. The
[local evidence](LOCAL_ACCEPTANCE_20261109.md) records the scope and remaining
checks. Freeze Git and storage contracts before wiring them into the authority.
Build the complete work-item-to-build workflow through native Git,
exact-revision review and isolated runners. Keep Code, Reviews and Build
navigation specific to software projects.

The November 9 [local verification](LOCAL_CODE_IMPORT_20261109.md)
covers bounded native stock Git, protected-ref denial, restart of populated
Code state, and loss-aware Work/Docs import. The local proof profile is
intentionally small. Phase 3 still requires durable staged receive and
protected review/build integration. Both exact role archives passed separate
native installs. Phase 4 still requires supported upgrades and interrupted
recovery, complete export, and a measured canary.

The next [local Phase 3/4 workflow](PHASE34_LOCAL_WORKFLOW_20261109.md) adds
durable Git admission, exact protected review and merge, an assigned build
lease, independent release intent, portable Code and delivery records,
controlled upgrade recovery and a measured canary. The local qualification
uses a bounded SHA-1 profile and a fixed verified worker recipe. Larger
repositories, live worker operation and multi-host rollout have separate
gates.

The [Phase 5 local evidence](PHASE5_LOCAL_20261110.md) records the fenced
same-ship move, source-project retirement and exact full-history Git approval
and readback. The November 14 private standalone pilot verified member
sign-in, Work/Docs, binding revocation, clean restarts and full-history Git
restore. Separate guarded fixtures verified stock clone/fetch with native
authorization and rehearsed GitHub issues as Stead Work. The native external
push ledger, worker proof, and Home v8 persistence have scoped passing tests.
Full-history push acceptance, protected review integration, cross-ship
activation, fresh-host admission and GitHub cutover remain open. The
[Phase 6 release verifier](RELEASE_READINESS.md)
passed a synthetic key-recovery drill. Independent adoption, support and
release operations still need evidence from the actual participants.

The standalone Phase 3/4 development checks use synthetic local ships.
A real House is outside their acceptance scope. A future House adapter still
needs a supported installation and launch path, verified individual identity,
and membership expiry and revocation. The adapter gate covers two members,
denial across spaces, and removal.

Workstreams: integration/architecture owns shared contracts; platform owns runtime/harness; native-core owns authoritative transitions; identity/security owns authentication and policy; Git owns protocol/object validation; frontend owns direct-home UX; QA/operations owns independent verification and deployments. One person or agent may fill several roles, but implementation and final approval must remain independent.

Parallelize only after contracts freeze. Do not launch separate agents to invent competing project IDs, schemas, ACLs or storage masters. Platform setup and dependency research may proceed independently. After URB-030, native state and authorization can progress against common tests; frontend and Git follow the relevant gates.

Historical bootstrap order was URB-000, URB-010/020/025, then URB-030. That first-slice work established the native foundation; it is not the current assignment. Use the current next increment above and preserve its acceptance evidence.

The original task definitions remain in `specs/urbit/backlog.json`;
`specs/urbit/ecosystem.json` adds ecosystem tasks, milestones and live issue
numbers. Live issues track execution; the evidence determines acceptance.

## First adversarial acceptance corpus

- Outsider cannot infer private project existence through list/search/counts/notifications.
- Reader cannot mutate via HTTP, native messages, Git, export/replication controls or debug interfaces.
- A native sender cannot impersonate another principal by changing payload author text.
- Repeated command produces one committed result; same request ID/different payload is rejected.
- Stale document revision conflicts; two separate documents need not conflict unnecessarily.
- Concurrent ref updates use expected-old-OID semantics; invalid graphs/packs never advance refs.
- A token revoked while a pack is staged cannot complete the ref update.
- Clone cannot reveal documents hidden only in the UI.
- Personal identity helper logs never receive private page bodies by default.
- Missing security/profile/context inputs fail closed; hierarchy never creates a grant.
- Restored private data remains private and outbound effects are not replayed automatically.
- Home unavailability yields Pending/Unavailable, not a false Saved/Accepted state.
- No dual-live same-identity deployment; controlled migration fences old authority.
- Export reconstructs source, documents, work context and policy history without the original service.

## Defer until evidence justifies scope

Large monorepo claims, all Gitea features, arbitrary Jira workflows, global federation indexes, CRDT-everything, untrusted runtime extensions, replicated execution of every action, native model inference, a blockchain/token economy, and broad compliance certification.

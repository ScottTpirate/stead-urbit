# Original Stead carryover ledger

Review date: 2026-09-12. Original repo is read-only. Keep requirements and useful tests, adapt runtime mechanisms, and do not inherit completion, licensing approval, certification or release acceptance.

The derivative archives main `3d47f0172a41beebb31f5c3a7df133cc1d4b1ead`. The original Phase 1 [PR #45](https://github.com/ScottTpirate/stead/pull/45) remains draft/unmerged at `588331457c30769ea70acb3e61ef6362200d536a`. Its described tested application checkpoint is `da037350c3e319d509207e6220af152c31b35e26`. That later work is not automatically in reference/stead. Selectively inspect exact source/tests before porting; this review did not rerun its reported campaigns. Original TEST-009/010, performance and release acceptance were explicitly not complete.

All source issue numbers below refer to https://github.com/ScottTpirate/stead/issues/NUMBER . Destination URB IDs resolve through specs/urbit/ecosystem.json. A single issue can retain semantics while retiring implementation details.

| Original issue(s) | Disposition and requirement | Destination |
| --- | --- | --- |
| #2 | Retain provenance, original notices, coherent reproducible foundation; replace Go toolchain assumptions. | URB-000/010/170/270 |
| #3 | Retain atomic accepted state, audit and effect intent; replace PostgreSQL transaction/role plumbing. | URB-030/040/050/190 |
| #4 | Retain deterministic release artifacts, scope-specific signing and independent verification. | URB-220/250/270 |
| #5 | Retain universal Org/Team/Project/Work/Docs ontology, fixed workflow, stable IDs and conflicts. | URB-030/040/180 |
| #6 | Retain individual identity, relationship+classification+context, agent scope and no bypass. | URB-050/060/160/210 |
| #7 | Replace stock Gitea/hidden tracker architecture; retain canonical Git, supported boundary and access invariants. | URB-025/080 |
| #8 | Retain attachment manifests, hashes, security partitions, provider-independent storage and backup behavior. | URB-100/200 |
| #9 | Retain Markdown/frontmatter, stable IDs/history/conflicts and parser fidelity tests; no assumed Commonplace integration. | URB-040/070/240 |
| #10 | Retain accepted activity, inbox, audit, dedup and replay; replace NATS implementation. | URB-090/190 |
| #11 | Retain authorized search/relations and no count/snippet/existence leak. | URB-180/190 |
| #12 | Retain job, artifact, provenance and secret-isolation contracts; replace provider-specific runner assumptions. | URB-090/250 |
| #13 | Retain unified nontechnical Work/Docs UI and accessible progressive disclosure. | URB-070/260 |
| #14 | Retain additive Code/PR capability after general-work acceptance. | URB-080/090 |
| #15 | Retain optional delivery UI, scoped jobs and artifact links; do not make every project a software project. | URB-250/260 |
| #16 | Retain simple install/doctor, privacy-safe diagnostics, consistent backup, upgrades and portability. | URB-100/120/220/230 |
| #17 | Retain independent release/negative/restore/performance evidence; no inherited acceptance. | URB-110/130/210/280 |
| #18 | Retire PostgreSQL physical-role/schema design; preserve intended atomicity/isolation. | URB-030/050 |
| #19 | Replace NATS ordering/retention mechanics; preserve bounded replay and explicit ordering. | URB-190 |
| #20 | Replace Gitea reconciliation implementation; retain idempotency, conflict handling and authority. | URB-080/190 |
| #21, #25 | Reuse reviewed frontend pieces and interaction behavior with exact provenance; reject imported ontology/routes. | URB-070/260 |
| #22 | Retain lean measured performance and negative evidence; do not resurrect superseded validator bureaucracy. | URB-110/130/200 |
| #26, #32, #33, #35 | Re-evaluate actual test dependencies/versions/licenses; retain browser sandbox, TLS/CSP, accessibility and test-only isolation. | URB-010/110/170/260 |
| #30 | Keep empty database namespace deferred; implement real portable import jobs when needed. | URB-240 |
| #38 | Retire PostgreSQL/pgx runtime dependency. Approval does not transfer to unrelated native code. | No native dependency carried |
| #41 | Keep dependency-free contract/invariant intent; replace Go implementation. | URB-030 |
| #42 | Keep capacity/preflight/error bounds; replace broker-specific configuration. | URB-120/200 |
| #44 | Keep one-command non-destructive development setup and real smoke testing; replace old service stack. | URB-000/020/120 |

## High-value regression material

Docs findings include malformed/unclosed frontmatter, duplicate keys, unknown types, BOM/CRLF, whitespace and log ordering. Preserve byte identity where promised; define intentional normalization rather than silently changing imported Git. These were bounded upstream observations, not permission to adopt Commonplace or proof of full Docs compatibility.

Original UI/authorization evidence contains both successful and failed attempts, incomplete denial-audit correlations and unknown request-failure causes. Reuse the concrete negative cases and user journeys; do not relabel old incomplete work as passed in the native system.

Product contracts worth retaining explicitly include ordinary Git, Markdown/OKF-compatible data, documented JSON exports, CloudEvents mappings and principal/group portability. Introduce the relevant mappings at real API/export boundaries rather than importing a large standards runtime for appearance.

## Execution rule

Before copying a file from unmerged or archived work, record source commit/path, desired behavior, licensing/notice obligations, native destination and new tests. Do not cherry-pick the seven-service stack, deployment secrets, local installation state or superseded approval manifests. No writes or issue-state changes are made to the original repository by this plan.

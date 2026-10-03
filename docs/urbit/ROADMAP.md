# Phased implementation roadmap

No dates or effort estimates here are promises. Each phase exits on evidence, not elapsed time.

September 26: Phases 0 and 1 are complete. The [Phase 1 native gate](PHASE1_ACCEPTANCE_20260926.md)
passes all 73 requirements with independent semantic acceptance.
September 29: The Phase 2 candidate has passing configured native, real
browser/stock-Git, independent SDK, hosted native CI and natural session-expiry
evidence. Its local native lifetime is closed and the stopped fixture preserved.
The [current qualification record](PHASE2_QUALIFICATION_20260929.md) binds each
result to its source and scope. [PR #67](https://github.com/ScottTpirate/stead-urbit/pull/67)
integrated the reviewed implementation; five of six M2 issues are closed. The
uncoached human Work/Docs trial remains open in #29; Phase 2 is not complete. The
[preparation checkpoint](PHASE2_CHECKPOINT_20260928.md) retains earlier failed
attempts and their historical limits.

October 2: [fresh native, browser and Git checks passed](PHASE2_ONBOARDING_20261002.md)
at the integrated source, with clean shutdown and restoration. The human trial
expired without qualifying activity or feedback; #29 and Phase 2 remain open.

| Phase | Deliverable | Gate |
|---|---|---|
| 0 | Independent repo, pinned dependencies, four-fake-ship harness, Git feasibility audit, contributor workflow | Actual native smoke tests, recorded reuse decisions and executed baseline/assisted workflow evaluation |
| 1 | One authoritative home, core Work/Docs state, explicit permissions | Restart, negative access, idempotence and revision tests |
| 2 | Individual sessions, useful shared web UI, native CI | Two users collaborate while an outsider cannot read or mutate through alternate paths |
| 3 | Native Git, reviews and limited agent proposals | Stock Git conformance, branch/ref policy, revoked-token and corrupt-pack tests |
| 4 | Portable export, operational recovery, low-cost public/synthetic canary | Independent security/restore/load evidence |
| 5 | Explicit replicas, safe home migration, self-hosted dogfooding | One authoritative source of truth, fenced migration and tested exitability |
| 6 | Supported ecosystem release | Independent adopters, integration, maintainership and qualified security/recovery/distribution process |

Workstreams: integration/architecture owns shared contracts; platform owns runtime/harness; native-core owns authoritative transitions; identity/security owns authentication and policy; Git owns protocol/object validation; frontend owns direct-home UX; QA/operations owns independent verification and deployments. One person or agent may fill several roles, but implementation and final approval must remain independent.

Parallelize only after contracts freeze. Do not launch separate agents to invent competing project IDs, schemas, ACLs or storage masters. Platform setup and dependency research may proceed independently. After URB-030, native state and authorization can progress against common tests; frontend and Git follow the relevant gates.

Start: URB-000, then URB-010, URB-020 and URB-025, then URB-030. The first product milestone is one page/work item saved on the home and correctly visible or denied to different principals after a restart. Do not start by translating all upstream engine source.

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

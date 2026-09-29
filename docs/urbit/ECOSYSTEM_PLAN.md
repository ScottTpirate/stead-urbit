# Ecosystem implementation and release plan

Status: proposed implementation gates, not runtime acceptance. Reviewed 2026-09-12 (America/New_York).
Live coordination: [roadmap #1](https://github.com/ScottTpirate/stead-urbit/issues/1).
This supplements the Master Build Directive and existing phases; it does not restart the local agent.

## Immediate sequence

Continue URB-010/020/025: pin the actual toolchain, run a real four-fake-ship positive/negative test, and audit native Git reuse. Then freeze the minimum URB-030 contracts and deliver URB-040/050 together. Skills qualification can follow the first native harness; ecosystem planning must not prevent that first executable result.

Work+Knowledge remains universal. A general project must work without exposing Code/PR/Build navigation. Minimal canonical Git-backed document persistence belongs to the early Docs slice; the later native forge task adds protocol, refs and software collaboration. A temporary non-Git document store is not completion of canonical Docs.

## Milestones

| Gate | Deliverable | Exit evidence |
| --- | --- | --- |
| M0 / Phase 0 | Reproducible native development | Pinned source/boot/toolchain, actual fake-ship allow/deny and cleanup, Git reuse decision; qualified contributor workflows. |
| M1 / Phase 1 | Authoritative Work and Docs | Stable project/principal identities, native versioned state, explicit policy, conflict/idempotency, restart and threat/test contracts. |
| M2 / Phase 2 | Usable team alpha | Real individual sessions and multi-user Work/Docs journey, safe search/activity/inbox, independent API sample, accessibility and native CI. |
| M3 / Phase 3 | Native software collaboration | Stock Git/OID fidelity, scoped reviews/agents, isolated builds, bounded storage/jobs and measured interactive behavior. |
| M4 / Phase 4 | Installable, recoverable beta | Actual desk installation, immutable release manifest, supported upgrades, export/import/restore, operator runbooks and multi-host synthetic/public canary. |
| M5 / Phase 5 | Federation and self-dogfooding | Explicit replicas, fenced home migration, one authoritative native project and controlled GitHub mirror; browser-only identity design truthfully scoped. |
| M6 / Phase 6 | Supported ecosystem release | Independent adopters, third-party integration, supported-version policy, backup maintainer and verified security/recovery/distribution process. |

`specs/urbit/ecosystem.json` maps all 30 task IDs to live issues and milestones. The old catalog remains the source for URB-000 through URB-160; this supplement owns only additional tasks. GitHub issues own execution status. Phase numbers describe acceptance gates, not a prohibition on preparatory work. Missing evidence is not a pass.

Before URB-130 canary admission, applicable URB-200/210/220/230 controls must be independently checked. Closing the early threat-model design task is not verification of future features. A beta observation window and workload are frozen before measurement, not chosen retrospectively to make results pass.

## Make the application reusable without expanding the trusted core

Begin with one authoritative native application and small owned libraries. Publish stable command/update marks and a minimal developer package, not private state structures. The SDK consumer must build independently and pass the same policy tests as the web client. Native messages, authenticated browser calls and later CLI/MCP adapters share the same final authorization path.

Keep four roles separate: contributor developing code; user joining a project; operator hosting data; publisher distributing executable code. Installing a desk does not mean replicating a company or granting company access. An identity or sponsorship relationship is not an organizational role. Optional Landscape, Hark, Tlon Groups, model workers and hosting products are adapters, not hidden authorities.

Publisher separation does not make publisher code harmless: installed updates can execute on the ship. Publisher custody and update acceptance belong inside the threat model. Do not promise cross-application isolation based on a planned UIP; verify the pinned runtime and use trusted applications only until stronger isolation is proven.

## Distribution, compatibility and recovery

Build self-contained desks using a pinned dependency closure. The standard skeleton's desk/desk-dev approach is useful; a library sample is not approval to run floating dependency refreshes in release CI. Ship matching source, desk digest/revision, frontend/glob digest, notices, supported runtime/kernel, API/mark versions and saved-state version in a release manifest.

Provide separate canary/stable publication and a reviewed promotion process. Verify actual operator update/pin behavior; do not assume a Git tag controls native OTA. Native delivery and optional HTTP mirrors must resolve to the same verified artifact. A conventional downloadable/offline bundle preserves exitability and should not require a private service.

Test install from a clean ship, supported predecessor upgrades, interrupted migrations, wrong Kelvin, stale browser bundles, incompatible peers, unavailable publisher and corrupt artifacts. Saved-state downgrade is not equivalent to checking out older source. Backup, portable export and entire-ship recovery are different procedures. Stop/remove/purge must have explicitly different semantics.

## Data and performance boundaries

A document page is not an independent Git confidentiality boundary if its underlying repository is cloneable. Separate repositories or disable raw clone exposure where page-level restrictions cannot be preserved. Reauthorize search snippets/counts, subscriptions, signed URLs and export manifests, not just page navigation.

Routing bodies through a personal ship can persist them in its history; direct browser-to-home delivery remains the default. Define retention, redaction, caches, backup keys and residual disclosure honestly. Revoking access cannot erase a prior recipient's copy. Restoring state must not resurrect revoked sessions or repeat external effects.

Put explicit bounds on payloads, delta chains, object graphs, jobs, queues, query results and storage. Persist job intent/checkpoints; an in-flight Spider thread is not the durable job ledger. A native thread is not automatic CPU isolation. Measure p50/p95/p99 interactive operations during import, not merely empty-project startup. Unknown large-repository capacity remains unknown until measured.

Keep arbitrary build/model execution off the authority host. Bind job and artifact evidence to exact source and limited delegation. Native orchestration does not require pretending every external language toolchain runs in Hoon.

## Independent readiness and community

Before a stable claim, two independent teams must operate the candidate and at least one separate Urbit app must integrate through the published SDK. A nonauthor must install, upgrade, recover and export using the docs. A backup accountable maintainer must reproduce/verify a release and exercise a recovery/security drill. No maintainers, adopters, SLAs or security contacts are invented by this plan.

The owner made the repository public during Phase 2 CI preparation (visibility
verified 2026-09-28 UTC). That visibility change does not complete URB-270:
history/license/secret review, a verified private vulnerability reporting route,
maintainer backup and release-key recovery remain separate release gates. Keep
essential security free and open source; preserve notices and reviewed
dependency scope.

Defer global consensus, blockchain-per-edit, active-active project authority, arbitrary plugin marketplaces and native arbitrary-language build farms. Do not accumulate optional dependencies just because they exist in Urbit.

## Evidence and integration discipline

One current integrator owns shared contracts. Parallel work is safe only behind those boundaries. The supplement changes guidance and planning, not the active runtime, lock, original repository or local unpushed work. Do not close tasks merely because this document or an issue exists. Link exact tested source, inputs, actual command/result, negative controls and independent review disposition.

See [Developer Guide](DEVELOPER_GUIDE.md), [Stead carryover](STEAD_CARRYOVER.md), root CONTRIBUTING/SECURITY/SUPPORT and live task acceptance criteria.

## Primary references

- Urbit environment: https://docs.urbit.org/build-on-urbit/environment
- Distribution model and desk compatibility: https://docs.urbit.org/build-on-urbit/userspace/dist
- Native testing: https://docs.urbit.org/build-on-urbit/userspace/unit-tests
- Thread lifecycle: https://docs.urbit.org/urbit-os/base/threads
- Official desk skeleton: https://github.com/urbit/desk-skeleton
- Original implementation checkpoint: https://github.com/ScottTpirate/stead/pull/45

References describe platform behavior; choices and acceptance gates above are proposed Stead engineering requirements, not claims that the features have been executed.

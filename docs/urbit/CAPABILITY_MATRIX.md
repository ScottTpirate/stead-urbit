# Current product capability matrix

Inspected November 15, 2026 at `539825650c60e606634bf4ab5967b698a6daa6e3`.
This is a source/document and tracker reconciliation, not a fresh runtime test.
“Qualified” below means the linked record's exact source, actors and profile only;
it does not extend old evidence to a new release. The project remains experimental:
no row establishes a supported production release or completion of the redesign.
Current requirements: [experience contract](PRODUCT_EXPERIENCE_CONTRACT.md).
Current work: [execution plan](../../specs/urbit/product-execution-plan.yaml).

| Capability | Implemented at baseline | Qualified evidence and boundary | Supported release / next work |
| --- | --- | --- | --- |
| Native authority, explicit grants, Work/Docs persistence | Implemented native core with scoped identity, revision/idempotency and recovery controls. | [Phase 1](PHASE1_ACCEPTANCE_20260926.md), exact native/host evidence; not a new run here. | Experimental; retain invariants through T01/T03–T06 migrations. |
| Individual sign-in and browser Work/Docs | Implemented configured-team flow and private pilot. | [Phase 2 qualification](PHASE2_QUALIFICATION_20260929.md), [Nov 9 local acceptance](LOCAL_ACCEPTANCE_20261109.md), [Phase 5 pilot](PHASE5_LOCAL_20261110.md). Native, browser and independent local review scopes differ. | Pilot scope only. New first-time-user G1/G3 gates remain; T07–T11/T27. |
| Everyday Work UX and contextual links | Existing lists, detail, comments, supporting Docs/blockers and quick actions; full redesign absent. | Source and earlier local journey; no new 24-screen visual validation here. | T07/T08/T10/T11: readable keys, route continuity, owner/worker, proper attention queues. |
| Docs and portable Markdown | Canonical stored Markdown/private publishing/export; current renderer covers a limited subset and drafts are in memory. | [Portable recovery](PORTABLE_RECOVERY_PROFILE.md) and [local import](LOCAL_CODE_IMPORT_20261109.md). | T09/T12/T26: correct rendering, title/author rules, safe draft recovery, exact Docs review and loss-aware imports. |
| Work contract vs discussion | Combined Work revision; comments can invalidate a pinned task revision. | Current `stead-team.hoon` source, not evidence for the requested revision split. | T05 migration required; no unchanged-contract run stability claim yet. |
| Independent repositories | Current Code scope reuses project ID as repository ID. | `stead-code-home.hoon` baseline; existing profile proofs use that scope. | Zero-repo Work/Docs remains valid; multi-repo identity/credentials/reviews need T04/T20. |
| Agent principals and actual runs | Proposal grants and copied briefs exist; dispatch/supervisor/model-driven Docs journey remain proposed. | [Job profile](AGENT_JOB_PROFILE.md) distinguishes current behavior; [delivery profile](CODE_DELIVERY_PROFILE.md) covers bounded proposals/build recipe. | No supported autonomous worker. T03/T12–T18 deliver real G3 first. |
| Durable proposal review after execution expiry | Current delegation eligibility ties proposal admission/review to current grant conditions. | [Delivery profile](CODE_DELIVERY_PROFILE.md); source `stead-code-delivery.hoon`. | T13 must implement explicit adoption/current-authority checks; docs do not change live eligibility. |
| Native bounded Git and delivery | Bounded object/receive/review/build paths exist. | [Nov 9 Code import](LOCAL_CODE_IMPORT_20261109.md), [Phase 3/4 workflow](PHASE34_LOCAL_WORKFLOW_20261109.md), exact small SHA-1/fixed-worker profile. | No general forge claim. T19 live-tree diagnosis and T20–T23 full workflow/profile parity. |
| Full-history Git | Stock clone/fetch and encrypted restore rehearsed; external push ledger has scoped tests. | [Phase 5](PHASE5_LOCAL_20261110.md), [dogfood rehearsal](PHASE5_DOGFOOD_REHEARSAL.md); full-history push acceptance/protected integration remain open. | GitHub stays canonical. Exact write/review/check/build/restore and explicit cutover decision needed. |
| Capacity and sustained agents | Explicit pilot bounds, not qualified long-running team scale; no real ten-worker queue. | Source limits below; bounded local observations are not representative scale. | T06/T24/T25/T31: measured budgets, paged history, queue fairness, bounded low-risk policy. |
| Install, upgrade and recovery | Release packaging, controlled local recovery and private pilot procedures exist. | [Packaging](RELEASE_PACKAGING.md), [Phase 3/4](PHASE34_LOCAL_WORKFLOW_20261109.md), [Phase 5](PHASE5_LOCAL_20261110.md). | T28/T30 require independent clean install/update/restore, declared support profile and source cutover decision. |
| Browser-only onboarding / House | Browser identity proposal/proof and standalone packaging exist; House interface unqualified. | [Browser identity profile](BROWSER_IDENTITY_PROFILE.md), [deployment scope](PHASE5_DEPLOYMENT.md). | T27 actual supported-auth journey; T29 capped House investigation. No compatibility claim. |
| Supported ecosystem release | Offline verifier and synthetic key-recovery rehearsal exist. | [Release readiness](RELEASE_READINESS.md); synthetic signatures do not establish independent participants. | URB-270/280 and T30 still require independent teams/app, maintainership, security/recovery and owner release decision. |

## Current pilot bounds and new targets

Source-visible configured-team safeguards include 16 projects, 128 Work per
project, 32 comments per Work, 32 Docs and 128 saved commits per collection,
32,768-byte complete Markdown documents, 256 relations per project and 4,096 ordinary
accepted events per Home, and an 8 MiB Docs object-store limit. These are
admission ceilings, not measured production capacity. Preserve reserve operations
and bounded decoding. Do not remove limits to make a target pass.

The T31 corpus of 1,000 Work, 500 Docs, 100,000 business events and 10 simultaneous
runs is a proposed measurement workload only. Record actual source/host/profile,
latency, retention/replay, memory/object growth, fairness and recovery before
publishing supported sizes. Repository capacity adds its own profile after T20.

## Tracker and qualification remain separate

The November 15 live issue search found 16 open canonical URB tasks: #11, #12,
#13, #15, #16, #17, #18, #19, #23, #25, #26, #27, #28, #29, #30 and #31.
In particular, [URB-260 / #29](https://github.com/ScottTpirate/stead-urbit/issues/29)
is open even though the November 9 local Astra review accepted its bounded
Work/Docs workflow. [Roadmap issue #1](https://github.com/ScottTpirate/stead-urbit/issues/1)
still contains older September gate wording. Treat that as a tracker discrepancy,
not a reason to erase either record. Optional #37–#40 remain candidates.

All 32 redesign packages remain implementation-pending. T01 has a documented
product decision table; concrete versioned interfaces and migration acceptance
remain open. T32's final shipped-product guidance still depends on T18/T23/T28.
No issue, milestone or release gate was closed by this alignment.

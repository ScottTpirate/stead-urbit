# Current product capability matrix

Baseline inspected November 15, 2026 at `539825650c60e606634bf4ab5967b698a6daa6e3`.
The baseline table below preserves earlier evidence. The implementation increment
records new observations separately; no new native or release acceptance is implied.
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

All 32 redesign packages remain open. T01–T03/T05–T13/T19 are in progress;
the execution plan records their actual partial outcomes. T01 has a documented
product decision table and reviewed additive Work read interface; successor
interfaces and migration acceptance remain open. T32's final shipped-product guidance still depends on T18/T23/T28.
No issue, milestone or release gate was closed by this alignment.

## Authorized implementation increment — November 15

The user authorized all packages and supervised deployment to the existing
Lightsail pilot at its current URLs. This does not authorize a new paid instance
or cutover of the source repository from GitHub. The live pilot is now
`c2f286154ada3f27dd53a7dda78741a75788b522`. Its [independent readback](evidence/2026-11-15/controller-refresh/lightsail-c2f2861-readback.json)
verifies exact served assets, healthy services and unchanged Work/Docs/Git content.
Authenticated browser acceptance remains pending. The owned local run stopped
at its thermal guard. Subsequent guarded Lightsail browser checks passed sign-in
and approval but stopped at workspace loading; diagnosis is in progress. Both
owned sessions were revoked and the owned browser/fences removed with services
healthy. No content acceptance or human trial is claimed.

| Increment | Implemented | Observed verification | Still required |
| --- | --- | --- | --- |
| T05a execution pins | Commit `f25424464623c8fad7557227444907578933fa0e` derives title/description execution revision and digest from accepted journal history, exposes them only on authorized detail reads, and supports strict brief/2 plus portable export. | 52 targeted host tests passed. [Hosted native evidence](evidence/2026-11-15/controller-refresh/receipt.json): candidate f254244, controller 3e1cabd, workflow 0699d25 passed 167 arms including all six execution-pin cases and 1,647 native checks, with verified cleanup. The first attempt failed before native execution; its exact toolchain mismatch was fixed. | Verify the real browser detail/brief path on the release candidate. No atomic finish fencing until T14. |
| T03/T05 successor native source | A source-only principal catalog and command/4 Work reducer preserve legacy identity and comments, separate property/contract/discussion revisions, expose query/4 reads and validate bounded mixed history. Concrete current native/Doc adapters and a closed Doc Change decoder are also prepared. | Independent hash-bound source reviews: [principal](evidence/2026-11-15/controller-refresh/reserved-principal-review.json), [Work](evidence/2026-11-15/controller-refresh/reserved-product-review.json), [queries](evidence/2026-11-15/controller-refresh/reserved-query-review.json), [restore](evidence/2026-11-15/controller-refresh/reserved-restore-review.json), [adapters](evidence/2026-11-15/controller-refresh/reserved-adapters-review.json). The 230-arm isolated candidate containing these 57 new arms [failed at the migration suite](evidence/2026-11-15/controller-refresh/hosted-43748907122/review.json) before any registered arm in that suite was observed. Nine earlier suites supplied 420 passing checks; all containment controls and empty cleanup passed. A same-source [diagnostic retry](evidence/2026-11-15/controller-refresh/hosted-43753293747/review.json) isolated module build/load failure before registered arms, with the same 420 prior checks and successful containment/cleanup. No successor-native qualification is claimed. | Service authentication, versioned Home integration, real migration/recovery qualification and UI activation. This code has no live routes and is excluded from the current pilot release. |
| T03/T05/T12/T13 ordered administration and Doc Changes | Reserved owner operations, original-authority Doc proposals, independent review, explicit expiry adoption, exact paired acceptance and concrete accepted-outcome proof are implemented as pure source. Compound recovery integrates these with Work in one timeline. | [Owner review](evidence/2026-11-15/controller-refresh/reserved-owner-review.json), [initial history review](evidence/2026-11-15/controller-refresh/reserved-history-review.json), [Doc reducer/proof review](evidence/2026-11-15/controller-refresh/reserved-doc-change-review.json). Thirty-four further native arms are prepared, including the six compound-recovery cases; all remain uncompiled and unexecuted. | Register and execute exact source, finish service/run authority and serving/read/UI paths, qualify versioned Home migration. No active saved format, route or worker capability follows from this source alone. |
| T12 exact Doc Change reads | Reserved per-Work metadata/detail, immutable result pages and exact before/after bodies with current access and bounded cursors. | [Independent source review](evidence/2026-11-15/controller-refresh/reserved-doc-change-views-review.json) binds seven uncompiled native arms. Missing historical bases stay explicitly unavailable; feedback/reviews remain tied to the selected result. | [Browser read/receipt client](evidence/2026-11-15/controller-refresh/reserved-doc-read-client-review.json) has TypeScript and fifteen host tests passing, exact body verification and session/cursor fencing. Native execution, Home read carrier and UI adapter integration remain. No live read capability yet. |
| T12 Doc review interface | Reserved scoped Change list and exact After/Before/Source/comparison views, native-supplied action eligibility, independent per-action notes and exact unknown-request retry. | [Independent source review and host evidence](evidence/2026-11-15/controller-refresh/reserved-doc-review-ui-review.json): TypeScript and ten host tests passed; eight synthetic browser cases prepared, unexecuted. Access denial hides protected content through remount until a fresh authorized read. | Rendered validation, strict read/receipt/transport adapters, Home integration and actual Doc acceptance. Components are not wired into the live app. |
| T14 run transitions | Reserved pure no-Code run/attempt lifecycle, exact contract pins, bounded leases/budgets, pre-effect authorization, explicit unknown-effect reconciliation and cancellation. | [Independent source review](evidence/2026-11-15/controller-refresh/reserved-run-review.json) binds ten uncompiled native arms and a host-calculated portable digest vector. | A closed command decoder adds six [source-reviewed, uncompiled arms](evidence/2026-11-15/controller-refresh/reserved-run-codec-review.json). The [native authority/result adapter](evidence/2026-11-15/controller-refresh/reserved-run-adapters-review.json) adds eight uncompiled arms using actual Work/Doc reducers. Service/effect adapters, read/history/saved-state integration, actual executor and G3 remain. No external dispatch or live run API yet. |
| T02 controls/layout | Shared controls, bounded local icons, modal keyboard focus, 560px preview, 680px composer, 800px full view and responsive modes. | [Eight Firefox reference cases](evidence/2026-11-15/product-interaction-reference.json), including 320/390px, crowded/empty/read-only, zoom and themes; synthetic data, not native or human usability evidence. | Complete app integration and golden journeys. |
| T07–T09 shell/Work/Docs | Commit a72d7b5 adds typed routes, memory-only navigation state, compact project navigation, title-only Work defaults, safe Markdown and explicit reader/editor modes. | [Browser follow-up](evidence/2026-11-15/product-frontend-followup.json): 61 unit tests, 20 selected current-source app cases and targeted formatting reference passed; earlier 21-case partial run is retained separately. | Native release save/readback and remaining package requirements. The subsequent workspace query/UI changes are a separate unqualified slice. |
| T07/T11 workspace reads | Capability-gated Search and My work aggregate authorized previews on this Home, using native pagination and watches. My work retains legacy assignee semantics. | [Ten Firefox workspace cases](evidence/2026-11-15/product-workspace-reference.json) passed. After retained fixture-ID and structural list-guard failures, [hosted run 43745730053](https://github.com/ScottTpirate/stead-urbit/actions/runs/43745730053) passed at `c2f2861`: 173 arms, 27 positive suites, 1,672 checks, migration and containment controls with empty cleanup. [Exact artifact verification](evidence/2026-11-15/controller-refresh/hosted-43745730053/review.json) also passed; supervised rollout and browser verification are separate. | Deployed-browser verification; durable actionable Inbox; Owner/worker split. Back revalidates page one, so a later-page selection is not fully restored. |
| T08 successor Work editor | Reserved composer/detail components separate property, purpose and conversation saves; human Owner and human/agent worker selection, exact shared-Doc outputs, explicit completion and retained scoped drafts are implemented but unwired. | [Independent source review and focused host evidence](evidence/2026-11-15/controller-refresh/reserved-work-ui-review.json): TypeScript, ten draft-state tests and fifteen protocol tests passed. Eight browser cases are prepared and unexecuted. | Real rendered cases, query/command carrier integration, current access/readback and native release qualification. No active screen uses these components yet. |
| T10a Doc backlinks | Saved Docs can show authorized supporting/related Work, resolve current names/status, and open canonical Work routes. Links remain informational and follow the latest authorized content. This source is deployed in `c2f2861`. | [Browser evidence](evidence/2026-11-15/product-document-context-reference.json): eight initial cases passed; the actual Back-focus failure was corrected and both affected layout/integration cases passed with final TypeScript. | Live authenticated browser regression; exact pinned revisions and required-outcome acceptance remain native successors. Private Doc views require explicit Refresh links for unrelated Work changes. |
| T19 live tree investigation | No speculative service change made. | [Authenticated tree/README/stale-selection/sign-out checks](evidence/2026-11-15/product-tree/receipt.json) passed against unchanged pilot source. The in-app browser could not resolve the private route; a separately owned Chromium browser subsequently reached both named sites through the private tunnel. | Actual authenticated browser regression after rollout; the original reported UI tree failure remains unreproduced. |

Committed documentation and source are implementation evidence, not proof of a
supported release. The full G3 Docs agent, subsequent Code journey, migration,
capacity and independent adoption gates remain open.

# Stead implementation handoff

Updated November 25, 2026. The active repository is `ScottTpirate/stead-urbit`. The product increment covers Work and Docs in projects without a repository, optional Code, and collaboration between people and agents. The owner authorized T01–T32 and supervised updates to the existing private Lightsail pilot. Verify the remote before writing. Preserve the historical upstream and other contributors’ work.

## What to build

The UX and native leads accepted the T01 design on November 25. The [native interface decisions](PRODUCT_NATIVE_INTERFACES.md) cover predecessor identities, revisions, saved states and the conditions for activating a successor.

The first agent journey is a document update in a project with no Code. A person assigns Work to a named agent. The agent asks a question, receives an answer and submits exact Markdown. An independent reviewer requests a revision and accepts the resulting Doc change. Work reaches Done when its required outcomes are accepted. A comment, model response or submitted proposal has its own status. [Experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) · [Execution plan](../../specs/urbit/product-execution-plan.yaml)

Home owns permissions, business state, accepted results and custody. Owner is the accountable human. A worker is a person or a stable agent principal. Each run pins its definition, runtime, context, Work contract and allowed effects. Keep contract revisions independent of comments. Recheck current authority at execution, adoption and acceptance. Keep an expired worker’s original evidence available for authorized review. [Master directive](MASTER_BUILD_DIRECTIVE.md) · [Agent and job profile](AGENT_JOB_PROFILE.md)

Use the selected Home for workspace Inbox, My work and Search. Project navigation is Overview, Work, Docs and optional Code. Each resource has one scoped identity. A project may contain zero or several repositories. A repository document shown in Docs keeps its Git origin. Render Markdown safely and preserve the original bytes. [Experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) · [Portable Docs](PORTABLE_DOCS.md)

## Current work

| Area | Verified position | Next action |
| --- | --- | --- |
| Private pilot | Release `a0e90ef` serves both named sites. The November 25 check matched all 21 web routes and found eight active services. Read-only repository browsing meets T19 on this profile. | Use `stead-pilot` on the configured machine to open the sites. Preserve the existing member data, Git snapshot and signing key through any update. |
| Shared interaction reference | Eight Firefox scenarios and five Chromium attachment scenarios exercised desktop and narrow layouts, keyboard focus, target sizes and safe links. T02 is accepted for this reference. | Apply the shared controls to real user journeys and verify each connected flow. |
| Work and Docs client | Candidate `a670d58c` passed the complete-app check with candidate assets. Its Home package preserves 101 backend desk files from the pilot. | Rehearse the native upgrade against a synthetic saved-version-8 predecessor, including cold restart and rollback. [Candidate comparison](https://github.com/ScottTpirate/stead-urbit/pull/130) |
| Upgrade rehearsal | The corrected launcher passed 10 host regressions. Run 45734762563 executed 261 native commands and shut down cleanly. The worker reported a failure before recording the first saved-state capture. | Locate the failing operation, fix the observed defect, then exercise the full rehearsal before staging a live update. [Rehearsal](https://github.com/ScottTpirate/stead-urbit/actions/runs/45734762563) |
| Agent models | Main includes versioned agent/runtime-to-model selection for compatible hosted endpoints and isolated local models. All 39 adapter, catalog and journal checks passed. A separate isolated Qwen2.5 trial returned the exact 47-byte Markdown output. | Wire the current native claim, bounded effects, questions, review and durable acceptance into the no-Code journey. [Model selection](https://github.com/ScottTpirate/stead-urbit/pull/129) · [Actual inference](https://github.com/ScottTpirate/stead-urbit/actions/runs/43843435452) |
| Native workflow | The successor Home built in diagnostic 43863766357. Thirteen suites returned 131 of 329 positive arm verdicts before restore timed out. The separate model-codec evaluation returned two controls and timed out at 86.55 seconds without a model verdict. | Localize the first missing native result. Capture real predecessor state before promoting a shared migration. [Home diagnostic](https://github.com/ScottTpirate/stead-urbit/actions/runs/43863766357) · [Model evaluation](https://github.com/ScottTpirate/stead-urbit/actions/runs/45731575647) |
| Independent repositories | The corrected native repository catalog returned all six expected arm verdicts. | Exercise import, authority and storage together, with a project hosting two repositories and an explicit legacy-ID migration. [Native catalog check](https://github.com/ScottTpirate/stead-urbit/actions/runs/45732106760) |

## Operating the pilot

Keep this computer on lightweight source, Git, hash and data inspection. Run native builds, models and untrusted work on a disposable worker. Reviewed, bounded browser and host checks may use the existing Lightsail arrangements. The authority and identity processes have their own duties. Keep their resources and private data separate from model and repository execution.

A live Home update requires a tested predecessor, a stopped checkpoint, a maintenance fence, preservation of the existing signing key and saved state, and a verified rollback path. Keep Identity at its reviewed release. Check both named URLs, a fresh sign-in, the three projects’ Work/Docs content and the accepted Git snapshot after updating. The real pilot already has Code and is ineligible for the reserved no-Code test profile. [Deployment runbook](PHASE5_DEPLOYMENT.md#prepare-a-pilot-update)

## Evidence and ownership

Preserve M0–M6, URB-000 through URB-280 and their original acceptance records. T01–T32 identify follow-up packages. Record the source, runtime, actors, actual result and remaining gap for each exercised profile. A named pilot acceptance applies to that release and scope. [Capability matrix](CAPABILITY_MATRIX.md) · [Ecosystem issue mapping](../../specs/urbit/ecosystem.json)

Use one integrator for shared native molds, wire marks and migrations. Assign bounded implementation slices to independent lanes and have an independent reviewer check each result. For UI work, inspect rendered desktop and narrow layouts, keyboard access, stale or revoked reads and draft continuity. For native work, use the actual harness for replay, stale inputs and recovery. For agent work, observe the request, effects, answer, revision, exact output and acceptance, including lost-reply reconciliation.

Independent first-time-user trials and the owner's eventual source-cutover decision remain separate gates. Keep GitHub authoritative until the stock Git write, review, check, build and recovery profile qualifies and the owner authorizes the switch. The current authorization covers the existing pilot. New paid hosting, provider accounts, identities and third-party outreach require their own decisions.

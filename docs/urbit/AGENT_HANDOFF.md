# Current implementation-agent handoff

Updated November 15, 2026. Build a coherent Work, Docs, optional Code and human/agent collaboration product on the existing native foundation. This replaces the original bootstrap assignment; that assignment and its results remain in Git history and the acceptance records.

## Scope and baseline

Work only in `ScottTpirate/stead-urbit`; verify the remote and current working tree before writes. Preserve concurrent work, the original `ScottTpirate/stead` repository, `reference/stead/`, licenses/notices and existing evidence. Do not reset another agent's checkout or reactivate the historical Go/provider stack.

The supplied review baseline is `539825650c60e606634bf4ab5967b698a6daa6e3` (November 15, 2026); the supplied screenshots identify UI `dbc8cc0`. The local checkout matched the review baseline during documentation alignment. On each new increment, inspect current branch, changes and live task state; reconcile any later work before applying a packet. See the [alignment record](PRODUCT_ALIGNMENT_20261115.md). The source/screenshot review and documentation alignment do not constitute new native, browser, deployment or capacity evidence.

Phases 0/1 and subsequent bounded workflows already have acceptance records. Do not restart the initial fake-ship/bootstrap assignment, describe the repository as not yet an app, or infer full product support from those records. Consult the [capability matrix](CAPABILITY_MATRIX.md) for the implemented/qualified/supported distinction and the exact linked evidence.

Read before implementation:

1. Root `AGENTS.md` and [master directive](MASTER_BUILD_DIRECTIVE.md).
2. [Product experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) and [capability matrix](CAPABILITY_MATRIX.md).
3. [Dependency-ordered product execution plan](../../specs/urbit/product-execution-plan.yaml), [roadmap](ROADMAP.md), relevant current profiles and canonical task catalogs.
4. The relevant repo-local skill and existing callers/tests for the chosen slice. Historical `reference/stead/` material supplies provenance and selective reuse, not current architecture instructions.

## Product decisions

- A team defines an outcome, gathers context, assigns a person or agent, reviews resulting changes and accepts the work. This works without a repository; software projects extend it with repositories, pull requests, checks, builds and releases.
- Retain native Hoon Home authority, canonical Markdown, ordinary Git identities, existing React/tooling and isolated external runners. No blanket rewrite, general workflow framework or speculative House/Gnat migration.
- Workspace Inbox, My work and Search initially aggregate within the selected Home. Projects show Overview, Work, Docs and optional Code; relationships appear in context. Use named people, clear outcomes and actionable states. Put diagnostic IDs/epochs/proofs in Details.
- Work is one canonical scoped resource. Projects have zero or multiple independently identified repositories; initially each repository has one owning project. External issue mappings do not define internal Work. Preserve legacy identity and refs through explicit migrations.
- Owner means accountable human, Working on it means human or agent worker, and Run means one execution with attempts. Autonomous work requires an explicit owner or visible inheritance from the project's human steward. Stable agent principals, versioned instructions/runtime bindings and attempts are separate objects.
- Separate Work property revisions, execution-contract revisions and discussion/activity sequences. Ordinary comments/progress do not stale an unchanged task contract. Changed acceptance/output requirements require re-planning. Runs pin exact context, while authorization/revocation remains live.
- Use a narrow common Change envelope with typed Doc/code targets and existing Git reducers. Review is bound to exact inputs/output and current target/base. Submitted is not accepted, merged is not deployed, and process exit is not task completion.
- Execution lease/grant expiry stops worker effects but does not erase a proposal or prevent an independently authorized review. Explicit adoption preserves original author/run provenance and exact bytes, checks current scope/target/base/reviews/acceptance authority, and never renews revoked worker credentials silently.
- Review required is the default for deliverables/protected targets, not every comment/progress update. Later low-risk automatic acceptance is explicitly bounded and uses separate required reviewer/acceptance authority. Workers cannot expand their own tools, access, budget or policy.
- Project Pause new work stops new claims. Per-run Stop/Cancel fences effects and late results; it does not undo accepted output or promise arbitrary remote process checkpoint/resume.
- Docs open in readable rendered form, with focused Edit, Preview and Source. One canonical Markdown origin survives save/export/agent access; a repository README viewed in Docs remains that repository file. Collections remain real access boundaries.

These are adopted target requirements. Pending implementation/migration must remain visible in the capability matrix; changing prose does not change existing native behavior.

## Next executable increment

The current user has explicitly authorized implementation of all T01–T32 packages and supervised updates on the existing Lightsail instance at the same named URLs, with heavier work moved off the local computer. This supersedes any earlier assumption that this session is planning-only or lacks deployment authorization. It does not authorize a new paid instance or a GitHub source cutover. Continue independently until the authorized work is finished; retain genuine human acceptance and externally provisioned prerequisites as separate gates.

The current pilot is source `da42d2220c7f85709996b5a7bfd8fa3f236c8625`, deployed after [hosted run 43756199115](evidence/2026-11-15/controller-refresh/hosted-43756199115/review.json) passed 173 arms and 1,672 checks. [Independent rollout readback](evidence/2026-11-15/controller-refresh/lightsail-da42d22-readback.json) verifies all eight services, exact assets, unchanged Work/Docs and the accepted Git snapshot; the paired checkpoint is retained. [Authenticated Lightsail browser checks](evidence/2026-11-15/controller-refresh/pilot-rendered-da42/review.json) passed all ten content/navigation cases and both sign-outs, including the 22-entry repository root and exact README. This is automated read-only evidence, not human acceptance or a mutation/recovery trial. The thermal-stopped local attempt and earlier remote failures remain retained. Keep browser and native execution off the laptop; the reviewed remote browser runs with bounded resources, private routing and verified cleanup.

Three observed visual defects have a separately reviewed correction at `2fc41f7`: mobile Workspace navigation width, bundled plus icons and clean Doc reading controls. That source is not yet deployed or rendered-qualified. Synthetic successor Work and Doc review components passed [eight browser cases each](evidence/2026-11-15/controller-refresh/synthetic-work-doc-browser/review.json), after stable textarea labels and a test locator correction. These fixtures do not establish native authority or a connected acceptance journey.

Continue reserved native qualification separately. The [293-arm diagnostic candidate at `125e4a6`](evidence/2026-11-15/controller-refresh/hosted-43758913444/review.json) collected 44 transcripts and exposed 15 module failures; it did not qualify the successor. Twelve failures report nest-fail, two report syntax errors and one lacks a recognized marker. Narrow syntax corrections are independently reviewed at `1f06b1b` and `ea98691`, but no passing native evidence covers them. A fixed import-only diagnostic is narrowing independent library and fixture failures; do not substitute its small selected suite for full qualification. The prepared `native-human-doc/1` Home version 10 integration is held for compiler diagnosis and real Gall migration/authorization/recovery testing. It admits only an explicitly activated disposable fake, no-Code Home; the real pilot keeps its predecessor envelope and content. Service/run activation, real model dispatch and G3 remain open.

Continue T01 interface decisions through the integrator as each remaining service/run/repository seam becomes concrete. Existing pure source and documentation do not finish its migration acceptance. T02/T07–T11 have implemented partial UI outcomes, T06 has a source-bound storage inventory, and T19 has authenticated API evidence; none is automatically complete. If a pilot path is unavailable, retain that exact limitation and continue other authorized work without inventing a cause.

After interfaces freeze, deliver the shell/Work/Docs slices T07–T09 against their actual dependencies while the native lane implements T05 and principal/run prerequisites. Coordinate T03/T04 identity and repository migration through the integrator. Prefer one complete visible journey to several half-connected screens. Use the YAML dependency graph rather than assuming letter phases run serially or that a later package number is always blocked by every earlier one.

The first user-facing agent acceptance is **G3/T18**: a no-Code project delegates a Doc update, receives a question, requests a revision, accepts exact Markdown and completes Work. The deterministic Code recipe is a parallel internal execution/isolation proof, neither a substitute for this journey nor its product prerequisite. Baseline Docs linking and bounded Docs autonomy must not wait for complete multi-repository Code delivery. Code autonomy additionally waits for its declared forge gates.

Do not treat this handoff as authorization to implement every package, spend money, provision identities/secrets, contact third parties, merge, deploy, or move the source of truth. Execute only the user's authorized increment; prepare independent work within that scope. GitHub remains the source until exact-profile full-history write/review/check/build/recovery evidence and explicit cutover authorization are present.

## Delegation and integration

Use a small team: integrator, two independent implementation lanes and independent reviewer when four slots are available. Rotate specialties. Shared saved-state molds, public marks, wire schemas, policy and migration files have one owner at a time. Agents can consume frozen interfaces; they must not invent competing ones.

Every delegated packet states:

- User outcome and exact product-contract section.
- Existing source anchors and clearly marked proposed boundaries.
- Allowed edits, non-goals and dependencies.
- Layout/control/copy/default decisions and relevant loading, empty, read-only, offline, conflict, revoked and pending states.
- Observable acceptance, required evidence and the reviewer who can establish it.

Do not delegate unbounded “improve UX” or “build agents” work. Routine implementation decisions within the adopted contract belong to implementers. Surface only real incompatible requirements, missing capabilities or consequential tradeoffs, and continue independent authorized work.

## Evidence and completion

For frontend changes, inspect the actual rendered result at desktop and narrow widths with empty/normal/crowded data, long text, keyboard interaction, accessible labels, zoom and read-only access. Preserve governed rendering, watch/poll reconciliation, draft continuity and focus behavior. A synthetic reference screen is not a native user journey.

For native identity/workflow changes, use the real harness and relevant skill for stale revisions, replay, revocation, predecessor migration and recovery. Never call static/Python checks or mocked browser results Hoon proof. Use bounded relevant checks; broaden only for a concrete regression risk or existing gate. Follow current resource/thermal controls, and disclose duration/prerequisites before expensive or interactive work.

For agents, demonstrate dispatch, observed progress, bounded effects, clarification, submission, revision, review and exact acceptance. Include cancellation, revoked/expired authority, next-day review, stale contract and lost replies. Reconcile the same request/output; native replay must not repeat external calls automatically. A grant, copied brief, process exit or synthetic run card is not completion.

For Git, preserve OIDs and stock-client behavior. Bind reviews/checks to exact revisions and current target/base; keep incomplete diffs and failed/unknown checks explicit. Do not reuse acceptance of different bytes after rebase or target movement. Test relevant conflict and recovery cases on the declared profile.

Independent reviewers assess the exercised journey separately from the whole product. Report source/toolchain/profile, input and actors, actual commands/observations, failures and unexecuted cases. Historical acceptance remains bound to its original source and scope. No lost accepted data, permission disclosure or misleading success state is acceptable regardless of other passing checks.

## Tracker and documentation discipline

Preserve M0–M6 and URB-000 through URB-280. `specs/urbit/backlog.json` owns the original definitions; `specs/urbit/ecosystem.json` owns additive tasks, milestone membership and issue mapping. T01–T32 are follow-up package labels, not replacement canonical IDs. Inspect current issues before changing tracker claims. A closed parent does not accept new scope, and writing a plan does not close a gate.

Update the existing authoritative profiles as implementations change, plus the single experience contract and current capability matrix. Keep normal quickstarts short and link detailed historical evidence. Do not create competing contract layers or delete failed evidence. State implemented, qualified on a named profile and supported in the release separately.

Report the outcome delivered, what remains incomplete, observed evidence and next dependency. Distinguish agent-executable work from required human tests, approvals, identity/secret provisioning and deployment decisions. Avoid broad readiness percentages or claims that wording changes reran tests.

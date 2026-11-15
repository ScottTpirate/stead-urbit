# Stead product review and next implementation phases

**Prepared for Scott Kilgore · November 15, 2026**

**Review baseline:** `ScottTpirate/stead-urbit`, main `539825650c60e606634bf4ab5967b698a6daa6e3`; supplied screenshots depict deployed UI `dbc8cc0`. Recommendations below are a proposed product and implementation contract. They do not change the repository, existing release approvals, or the status of an implementation gate.

## 1. The decision

**Keep the native foundation. Redesign the product around completing work. Make agents participants in that product. Do not restart the application or spend another phase adding disconnected capabilities.**

Stead already has several unusually valuable foundations: one authoritative project home, individually attributed actions, revision checks, canonical Git-backed Markdown, ordinary Git identities, explicit relationships, scoped proposals, and review bound to an exact revision. These are worth preserving. The governing architecture already captures much of Scott's desired destination. [R1–R4]

The product has not caught up with those foundations. Its interface frequently presents records and protocol steps instead of helping a person answer: What needs my attention? What is the goal? Who is working on it? What changed? Can I accept it? What happens next? The project overview repeats a title; Inbox is other people's activity; a delegation grants access but does not start a worker; code review sits below the repository browser. That is the central bottleneck. [S04, S12–S13, S20–S24; R5–R8]

The next release should prove this promise:

> A team can plan an outcome, keep its knowledge together, delegate work to people or agents, inspect the resulting changes, and accept them in one coherent workspace. Software projects add repositories, pull requests, builds, and releases to that same workflow.

Urbit supplies ownership and authority. Markdown and Git supply portability. Excellent interactions supply adoption. None substitutes for the others.

### The bold choices

1. **Work is the organizing unit; a repository is optional.** One canonical Work item appears from a project, repository, document, or personal queue. Do not create separate tracker issues and forge issues.
2. **Keep Work, Docs, and Code as the three main content areas.** Make relationships contextual. Put Inbox, My work, and Search at workspace scope. Let Overview describe the project rather than act as an empty landing page.
3. **Agents get identities, memberships, capabilities, and ordinary work.** Their runtime setup is a member-management concern; their work is not a separate application.
4. **Separate the accountable owner, the worker, and the run.** A human can remain accountable while an agent or another human does the work. A run is an execution attempt, not a person and not a ticket status.
5. **Use a common Change model.** A Markdown edit and a code pull request share proposal, exact revision, review, acceptance, and provenance concepts, while retaining appropriate editors and diff viewers.
6. **Make the first polished agent journey update a document in a project without Code.** In parallel, use the already specified deterministic code job as an internal execution proof. Then complete the software delivery journey.
7. **Treat a usable small-team forge as an explicit milestone.** “Replace GitHub” cannot mean only a file tree and clone button; it also cannot require copying every GitHub service before anyone can use Stead.
8. **Design for House integration through narrow adapters.** Do not rewrite the core for an unverified House plugin interface or a speculative `%gnat` migration.
9. **Stop delegating product judgment to implementation agents.** Give them exact screens, default behavior, states, scope, evidence, and failure cases. Product decisions belong in a short approved contract, not in whichever component an agent happens to edit.

## 2. What was reviewed and what the evidence establishes

The supplied archive contains one walkthrough and 24 screenshots. Every screenshot was visually inspected across the review team. The repository was available through the connected GitHub integration; main matched the archive's pinned commit when checked. Review included the active directive, roadmap and release documents, job/delivery profiles, the frontend source, selected native reducers and identity/view code, SDK references, planning catalogs, and open issue titles. Historical `reference/stead` material is not the active architecture. [R1–R4, R16]

This is a screenshot, source, and contract review. No live pilot business writes, native Hoon execution, fresh Git conformance run, deployment, or runtime capacity measurement was performed for this review. Existing execution records are reported as repository evidence, not as tests rerun here.

| Evidence | What it supports | What it does not establish |
| --- | --- | --- |
| Supplied live screenshots | The captured live UI states | A complete write workflow or sustained operation |
| Supplied demo screenshots | Designed interface states using synthetic records | Production data correctness or working live endpoints |
| Pinned frontend/native source | Implemented logic, data coupling, explicit limits | Measured latency, operating capacity, or deployment correctness |
| Existing acceptance/release records | Previously reported tests at their recorded revisions and scope | Automatic acceptance of the current or future candidate |
| Proposed job profile | An intended contract | A working job API, dispatch service, or autonomous agent |

**Preserve the distinctions in every future agent report.** A mock returning a successful response proves a component interaction, not an accepted native change. A compiled reducer does not prove the entire user journey. A successful small synthetic repository does not prove ordinary full-history source hosting.

### What is genuinely worth keeping

- The warm neutral palette, restrained chrome, grouped Work list, inline property actions, visible role distinctions, and Work-to-Doc return behavior.
- Current final authorization, immutable inputs, exact proposal revisions, stale-write rejection, idempotent receipts, and independent review.
- A single transaction-owning native Home with modular libraries, instead of several writable systems trying to reconcile afterward.
- Canonical Markdown and Git objects, portable history, and explicit restrictions on private drafts and cloneable collections.
- Existing worker isolation and build patterns. Extend them for actual task execution instead of replacing them with a new orchestration stack. [R1–R8]

## 3. The findings that should change the plan

Severity here describes the order of product work: **P0** fixes a contract or blocker before building on it; **P1** is required for a credible team product; **P2** follows the completed core journeys.

| ID | Priority | Finding and evidence | Required change |
| --- | --- | --- | --- |
| F01 | P0 | Navigation exposes eight equal project destinations; Overview largely repeats the project name. [S04; `main.tsx`] | Adopt workspace attention/navigation and project Overview, Work, Docs, optional Code. Define Overview content and an actionable empty state. |
| F02 | P0 | The agent control creates a short-lived proposal grant and copies a brief. It does not dispatch or execute the task. The job profile explicitly says unimplemented. [S22–S24; R7–R8] | Keep that grant machinery underneath a real Delegate → Run → Change → Review → Accepted journey. Do not present “access granted” as work started. |
| F03 | P0 | Work comments are embedded in the Work record and increment its resource revision; the proposed job pins that revision. [R8, R10] | Separate execution-contract revision, ordinary work-property revision, and discussion/event sequencing. A comment or progress update must not invalidate an unchanged task. |
| F04 | P0 | Proposal eligibility is checked again for review/merge through the live delegation; UI defaults to 30 minutes. [R7, R9] | Separate worker execution authority from the authority to review durable proposals. Define expiry, revocation, quarantine, and explicit adoption of an exact proposal. |
| F05 | P0 | Code scope currently uses project ID as repository ID. [R11] | Introduce a real Repository identity and project-repository association before expanding agent or multi-repo functionality. |
| F06 | P0 | Principal identity is conceptually separate in the directive, but configured members and actor resolution are currently ship keyed. [R12] | Add versioned principal/authentication bindings and scoped worker credentials; do not require a planet for every logical agent or run. |
| F07 | P1 | The current Markdown renderer handles headings, block quotes, paragraphs, and inline code, not ordinary lists, links, fenced code, or tables. [S10; R6] | Specify a documented CommonMark/GFM profile, safe rendering, editor fidelity, and portable attachments. Keep Markdown canonical. |
| F08 | P1 | Docs list titles derive from the first 80 Unicode characters of body content; editor titles derive from a heading. Commit construction uses `Stead Fixture`. [R10, R13] | One title extraction/metadata contract; truthful new revision attribution; preserve old commit IDs. |
| F09 | P1 | Inbox is an activity projection excluding the current actor, with no distinct actionable notification lifecycle. [S12–S13; R13] | Add recipient/reason/read/action state, meaningful copy, aggregation, deep links, and PM review queues. |
| F10 | P1 | Work detail is cramped, and code review spends its first viewport on repository navigation and repetitive IDs. [S07, S18, S20–S21] | Full task route plus a useful preview; dedicated review route with change summary, diff, checks, discussion, and decision controls. |
| F11 | P1 | Pilot ceilings are incompatible with sustained team/agent activity. [R10] | Build bounded pagination, storage/retention boundaries, archival and measurements before increasing limits. |
| F12 | P1 | UI state is concentrated in an approximately 85 KB `main.tsx`; global busy/form state couples unrelated interactions. [R5] | Extract route-owned views and resource-owned pending/draft state while delivering the new shell. Avoid an unrelated framework rewrite. |
| F13 | P1 | Inline and external repository profiles expose different workflows. Full-history push/cutover is still open in the repository status. [R2, R3] | One product-level repository interface with honest capability reporting; qualify each profile's exact supported operations. |
| F14 | P1 | Live repository tree did not load during the supplied capture; stronger repository screens use demo data. [archive walkthrough] | Reproduce the live failure, give retryable error states, and require a live clone/browse/review/write scenario before calling Code ready. |
| F15 | P1 | The visible sign-in journey requires an identity ship approval loop. The broader product is intended for ordinary teams. [S01–S03; R1] | Preserve native identity for the current cohort; prioritize a separately qualified browser-only identity path before broad nontechnical adoption. |
| F16 | P2 | House installation/membership/plugin compatibility is not established by the pilot. [archive; R15; W5] | A bounded compatibility investigation and adapters, with supported House version and installation evidence before making a compatibility claim. |

### The capacity problem is not cosmetic

The configured-team source has deliberate pilot ceilings: 16 projects, 128 Work items per project, 32 comments per Work item, 32 documents per collection, 128 saved commits per collection, 32,768-byte complete Markdown documents, including metadata, 256 relations per project, and 4,096 ordinary accepted events per project. The Docs object store is also capped at 8 MiB across the state it holds. These limits are source-visible safeguards, not measured production capacity. [R10]

A pilot can pass its tests and still be unsuitable for normal ongoing use. At these limits, autosaving every pause or logging an agent's entire stream into comments would quickly exhaust history. **Do not remove the safeguards.** Move comments and run telemetry into separately paginated records, distinguish the portable accepted journal from transient logs, retain objects outside hot state through the documented storage boundary, and qualify realistic retention and restart behavior. Preserve reserve capacity for revocation and recovery operations.

## 4. The canonical product model

### Correct the GitHub/Linear premise

Linear issues are Linear records that can link to or synchronize with GitHub issues; they are not inherently GitHub issues. Linear's official documentation describes separate records and one-way or two-way synchronization. [W1]

Stead can provide something simpler internally: **one canonical Work item, with repository-specific views of that same item.** An external GitHub integration maps a foreign issue to that Work ID. It is an adapter, not the internal data model. Work must continue to exist when a repository is removed or a project never had one.

Do not put every Work item into a Git file just because Docs use Markdown. A Git-backed document is a good content format. Concurrent workflow state, assignments, notification read state, leases, and permissions are better represented by the native command/state model and portable structured exports. The goal is simple ownership and interoperability, not one storage format for everything.

### Small ontology, explicit responsibilities

| Concept | Meaning | Design rule |
| --- | --- | --- |
| Workspace/organization | Membership, policy defaults, projects, shared identities | Organizational grouping does not automatically grant content access. |
| Home | Authority that accepts project changes | One authoritative home per project; transport location is not project identity. |
| Project | A goal and its working context | Works with zero repositories. Has a steward, summary, milestones, Work, and Docs. |
| Work item | An outcome someone is responsible for delivering | Stable scoped resource reference plus readable project sequence such as `STEAD-142`. Same object in every view. |
| Document | Canonical Markdown content with identity and revisions | Default readable page; ordinary editing; source mode available. |
| Collection | Document organization and compatible access boundary | Do not hide private pages inside a repository exposed through unrestricted clone. |
| Repository | Git objects, refs, access and delivery settings | Independent ID. A project can contain several repositories. |
| Change | Proposed durable changes with exact input/output references | Shared lifecycle; specialized Markdown/code presentations. |
| Principal | Person, agent, or service identity | Has authenticated bindings and permissions; is not a ship or a model name. |
| Membership | A principal's authorized participation | Explicit, revocable, scoped; independent of ship sponsorship. |
| Run | One execution of an assigned task contract | Visible on Work; includes attempts, progress, limits and output references. |
| Relationship | Typed connection between authorized resources | Stores stable identity, direction and optional revision anchors. |

Start with one owning project per repository and explicit project-repository association. Permit the model to support shared repositories later, but do not immediately implement arbitrary many-to-many ownership. This avoids confusing ownership and access while escaping today's one-project/one-repository coupling.

### Work status and execution status are different

Keep a fixed, small workflow. Recommended target: Backlog, To do, In progress, In review, Done, Canceled. Model “blocked” as a reasoned condition on unfinished work: dependencies, waiting for information, unavailable worker, or rejected access. Migration of today's `blocked` status must retain its meaning and history; do not silently relabel every blocked item as ready.

A run has a separate lifecycle: Queued, Running, Waiting for input, Submitted, Failed, Canceled. Pause new work is initially a project-queue control; it does not promise checkpointable pause/resume of arbitrary running processes. A submitted run produced a reviewable result; it has not completed the Work. A merged code change is not necessarily a successful deployment. A document save is not necessarily approval of its content.

Recommended completion rule: Work becomes Done when its declared required outcomes have been accepted and any required checks have passed. Optional informational links cannot prevent completion. Multiple required code changes must all finish; a single merged branch must not prematurely close a multi-repository task. A human can explicitly complete a non-artifact task, with a short completion note.

### Linking that people and agents can understand

Start with a small vocabulary:

| Relation | Source → target | Typical UI |
| --- | --- | --- |
| Parent/child | Work → Work | Subtasks with progress |
| Blocks | Work → Work | “Blocked by STEAD-141” on the dependent item |
| Related | Work/Doc → Work/Doc | Related work/docs |
| Supports | Doc → Work/Project | Supporting documents |
| Implements | Change → Work | Changes required for this work |
| Documents | Doc → code reference | Documentation linked to a file/module/revision |
| Derived from | New artifact → source artifact | Provenance and source history |

Each link references a stable scoped resource identity `(project, kind, collection where applicable, local ID)`, not a bare UUID, title or fragile URL. Preserve the current contract amendment’s scope rules. [R17] A code reference includes repository ID, exact commit, path, and optional line range; a branch bookmark is explicitly a moving reference. A document reference may mean latest authorized revision or an exact accepted revision; the UI must distinguish those two meanings. A run always records the exact revisions it actually read.

Automatic backlinks are derived views of the same relation. Permission to see one endpoint does not grant permission to see the other. A hidden target must not leak its name, snippet, private project, count, or existence beyond the approved disclosure policy. Deleted resources retain a stable tombstone; user-facing links show an unavailable state without exposing protected content.

MVP linking is contextual: “Add supporting document,” “Add dependency,” “Link change.” A generic relation editor may exist under advanced tools. Do not build a graph canvas as the primary way to do work.

### Canonical Markdown without a hostile editor

“Docs are Markdown” should describe storage and interoperability, not require every user to edit raw syntax all day.

- Default view is rendered reading. Enter a focused editor on Edit. Offer Write, Preview and Source; do not force a permanent split pane.
- In the first iteration, use an accessible Markdown-aware source editor with simple formatting tools and accurate preview. A constrained rich editor can follow only if it preserves supported Markdown reliably.
- Use a deliberately small, versioned metadata header: stable ID, type/state, title contract, and schema version as needed. Avoid duplicating the whole project database in frontmatter.
- Prefer explicit title metadata for new documents, with a defined fallback to the first heading for imported older documents. Preserve unsupported metadata during round trips or report it as unsupported; never silently discard it.
- Support headings, paragraphs, emphasis, lists, task lists, code fences, tables, links, block quotes and safe attachments. Reference CommonMark and the documented GFM extensions. Raw HTML/MDX execution is unnecessary. [W3]
- Distinguish editing a working draft from publishing an accepted shared revision. Preserve current private-draft publication semantics until an explicit migration is reviewed. Do not accidentally publish an entire private collection when someone shares one page.
- Save working drafts without making a canonical Git commit per keystroke. In early delivery, explicit Save plus resilient draft recovery is acceptable; later autosave must have bounded commit cadence and an honest “Saving/Saved/Offline draft/Conflict” indicator.
- Treat local browser draft persistence as a product/security decision: scope it to session/principal/resource, purge protected copies on logout/revocation according to policy, and do not promise cross-device drafts until implemented.
- A document container remains distinct from a project's optional software repo. If a project exposes code Markdown inside Docs, choose one canonical origin and edit through it. Do not make two independently writable copies of the same README.

## 5. The agent model to implement

### One work experience, several kinds of participant

The shared Work detail shows **Owner**, **Working on it**, and the current outcome. A human may own and perform their own task. A human owner can delegate to a human collaborator or an agent. An agent can create permitted child tasks, comment, change ordinary statuses, request information, submit changes and respond to review through the same business operations.

Linear's human owner/agent delegate distinction supports this direction, but Stead should not inherit every limitation of Linear's agent platform. For example, the current Linear documentation restricts agents from project membership/lead roles. Stead's own membership and authorization contract should determine what an agent can do. [W2]

Do not build a parallel “AI tasks” database, a separate bot comment thread, or a floating chat panel as the main way to manage agent work. A chat can be an input surface that creates or updates ordinary Work; the durable state belongs on Work, Changes, Docs and the project.

### Three identities to keep separate

| Object | What it represents | Example |
| --- | --- | --- |
| Agent principal | The durable colleague, its permissions and attribution | “Docs editor” |
| Agent definition and runtime binding | The versioned instructions, model/tool capabilities, endpoint and isolation profile | “Docs editor v3 on the team's worker host” |
| Run and attempt | One task execution and a retry or resumed lease | Run R-48, attempt 2 |

A named agent should survive changing the model provider or moving the worker to another host. A run should not create a new ship. An organization can operate several logical agent principals on a worker service, each with separately scoped credentials and attribution. An independently operated cross-organization agent may use its own ship identity. Urbit's Gall “agent” means a persistent application; it must not be confused with each AI worker invocation. [R1, R12; W4]

New agent setup belongs beside people in Members & agents. Initial setup fields: name, icon, owner/steward, project access, runtime connection, capability profile, and a connection test. Provider keys remain in the trusted runtime supervisor/secret boundary, not the task description or repository. Model/provider egress is explicit in the profile; an allowed data read is not permission to send the content to an arbitrary model service.

### Human accountability without a human-click bottleneck

Default the accountable owner to an explicit assignee; allow tasks created by an authorized project agent to inherit the project's human steward until reassigned. Show that inheritance. Do not require the PM to choose a new human name for every generated subtask.

The default project automation policy should require independent review for submitted deliverables and protected targets. Ordinary permitted comments, progress/status updates and direct edits remain direct operations unless that target’s policy specifically requires a proposal. A project steward can authorize bounded automatic acceptance for narrow low-risk classes after the normal review loop works. Such policy can allow an independent reviewer agent and a separately authorized acceptance action. It must not mean the producing agent can approve its own work or rewrite its own limits.

Keep policy small and understandable: allowed operations/resources, required checks/reviewer, concurrency, cost/time budget, and escalation conditions. Start with Review required and a narrowly defined low-risk automatic policy, not a programmable workflow designer. Actual deployment authorization remains a separate governed action.

### What Delegate should do

From the Work item, choose “Delegate…” and pick a named worker. Show the inferred task brief, selected context, and expected output. A user should normally need only choose the worker and start.

Default context is the Work description, acceptance criteria, required dependencies, and explicitly linked documents/repositories the worker can read. The dialog should say what it will access. Access restrictions, runtime model, time limit and cost ceiling are visible in a compact expandable section. Target branch is inferred from the selected repository's default branch when Code is relevant. No branch, commit or runtime fields appear for a document-only task.

After Start, the Work item shows: “Docs editor is updating the onboarding guide,” started time, a concise progress summary, and Stop work/Cancel. “View run” exposes inputs, attempts, activity, budget, tool/effect summary, logs and diagnostics. Do not stream every token into the discussion or promise completion percentages that the worker cannot substantiate.

The job may ask a specific question. That appears in the same Work discussion as an attributable request, with a visible “Waiting for your answer” action in Inbox. Answering can resume the authorized run when its contract still holds. A declined or expired response does not silently broaden authority.

### Correct the revision and expiry traps before dispatch

**Revision split.** Add `work_revision` for mutable properties, `execution_contract_revision` for objective/acceptance/output requirements, and independent discussion/activity sequences. The run stores a contract digest and exact context pins. Editing acceptance criteria invalidates or explicitly supersedes the run's contract; posting a comment, resolving an unrelated notification, or advancing progress does not. Role changes and revocation always remain live authorization checks.

A new version of a linked Doc does not retroactively change what the run read. The default is a pinned snapshot, with a visible “Context has newer revisions” marker. A material change to a required input triggers re-planning or an explicit new run. Do not make every incidental edit anywhere in the project kill all in-flight work.

**Expiry split.** A renewable execution lease and the delegating grant are separate authorities. Lease expiry or grant expiry stops further worker effects/publication under that authority. Neither automatically erases a historical proposal or requires the worker’s execution grant to remain valid merely so an authorized reviewer can inspect it. The next-day review path checks current reviewer permission and exact proposal provenance. Explicit revocation or loss of trust can quarantine pending output. A maintainer may adopt an exact quarantined/expired proposal under a fresh acceptance decision, with a new review where required; that does not revive the old worker's authority. Adoption preserves the original immutable author/run provenance and exact output digest, and checks current scope, target/base, required reviews and checks, and the adopter’s current acceptance authority. It never renews the old worker’s credentials or silently accepts output affected by revocation or compromise. This is an intentional contract change to the current `eligible/current` behavior and requires negative tests. [R7–R9]

**Cancellation.** Stop new claims/effects; mark cancellation durably; fence the attempt; reject late publication from canceled or stale attempts. The supervisor tries to terminate the child, but the UI must not imply a remote process stopped merely because a cancel request was accepted. Outputs already accepted before cancellation remain historical outcomes; cancellation is not rollback.

### Durable execution, without adding a second authority

Keep native Home as the job authority and the external supervisor as an effect executor. Reuse the existing build worker's isolation concepts; do not install Temporal, Kubernetes, or a generic agent framework merely because jobs exist.

A proposed job/run envelope includes:

- Work ID and execution-contract revision; project, Home and authority epoch.
- Requester, worker principal, reviewed agent-definition version and scoped grant.
- Exact authorized context manifest and digest; output kind and target resource(s).
- Repository/base/target only for code outcomes; document IDs/revisions for Doc outcomes.
- Budget, deadline, capability profile, request idempotency key and policy version.
- Attempts with fencing token, lease, heartbeat, claimed worker, checkpoints and immutable result references.

The supervisor should pull or subscribe to eligible jobs, claim one with compare-and-set semantics, execute in isolation, and submit a bounded result manifest. Repeated delivery is expected. Exactly-once external computation is not a realistic universal promise; aim for deduplicated accepted outcomes, reconciled effects, and explicit ambiguous states.

If a result is lost after a model call, inspect the durable local receipt/provider evidence before retrying. Do not claim that replaying native state repeats the same AI response. Tool calls that send messages, buy services, deploy code or otherwise produce external side effects need their own explicit effect policy and reconciliation; task assignment alone is not blanket authority for those actions.

Implement Change as a narrow common metadata envelope and lifecycle with typed document/code targets. Retain existing Git proposal reducers rather than introducing a universal transaction or workflow engine. A Change preserves the submitted result, summary, before/after references, source Work, worker, run, checks and reviews. Code outcomes use the existing exact proposal/review mechanics. Document outcomes use exact Markdown diffs. A research result creates a Doc or evidence-bearing completion note. External-action results use an appropriate receipt. Do not fake a Git repository for non-code work.

### The PM experience at 99 percent agent execution

The PM works from My work and Inbox, with queues for Needs decision, In review, Blocked, and Active. Initially aggregate within the selected Home/workspace. Cross-home aggregation requires a separate permission-filtered protocol and must not create automatic replicas or a global private-content index. Project Overview shows the next milestone and a short exception summary. Agents continue authorized dependent work after acceptance; the PM does not press Resume on every child task.

A project-level planner may propose a task decomposition and assign eligible work within a preapproved boundary. Pause new work stops new claims; already running jobs continue unless separately canceled. Resumable per-run pause is a later capability only for executors with a proven checkpoint contract. Every child is an ordinary Work item with dependencies, an inherited owner, output requirements, and its own scope/budget allocation. Reject dependency cycles. Claim jobs atomically. Enforce finite concurrent runs and per-project budget. Stop repeated failures and escalate with the attempted approaches and the smallest decision needed.

Agents collaborate through Work comments and structured questions linked to the item or artifact being discussed. A discussion must conclude with a result, accepted answer, changed contract or escalation. Do not introduce an unbounded autonomous group chat as a prerequisite for coordinated work.

## 6. Architecture choices that preserve the future

### Keep the native core and make the seams explicit

Retain `stead-home` as the mutation owner with modular Hoon libraries. Keep Git/Markdown bytes and accepted pointers canonical, derived views rebuildable, and final policy checks at the authority boundary. The old Go/PostgreSQL/NATS/Gitea architecture is reference material, not a starting point for this iteration. [R1, R4]

The same command contract should serve the browser, CLI/SDK, approved automation, and future MCP/A2A adapters. “Same API” does not mean exposing every action to every actor. It means the same validation, permission checks, concurrency semantics and receipts apply regardless of client.

Start with a small practical tool surface: search/read Work, read a context bundle, read a Doc at revision, create/update permitted Work, comment/ask, claim/heartbeat/cancel a run, submit a Change, read review outcome. Add broader capabilities only with actual workflows. Structured typed results matter more than a very large tool catalog.

### Frontend refactor as a delivery strategy

Keep React and the established build tooling. Split `main.tsx` along product ownership: application shell/session; workspace Inbox/My work/Search; project Overview/Work/Docs/Code; route-driven Work detail; editor/draft state; typed query/command hooks; resource-level pending outcomes. Centralize status labels, person/agent display, relationship rendering, notifications and capability displays.

Introduce route contracts before new screens. Every Work, Doc, repository, Change, review, and run needs a shareable address that survives refresh. Use readable labels in the UI while retaining immutable IDs in routes/lookup. Back/Forward must restore query, filters, selection and scroll; returning from a Doc must preserve the current comment draft. Do not store sensitive content in a URL.

Do not widen raw DOM forwarding or disable the existing content protections to make rich controls easier. Add explicit vetted link, icon, attachment and editor components. A generic primitive that permits arbitrary resource-loading properties would undermine the controlled rendering boundary.

### One Code product over supported storage profiles

The inline and external Git profiles should implement one typed product capability interface: list repositories/refs/tree, read file at revision, compare, create/read/revise Change, review, accept, check/build, release. Declare unavailable operations explicitly. The product should say “Push is not supported by this repository configuration” rather than exposing storage proofs as ordinary workflow steps.

Keep storage profiles in operations settings. Normal users see repositories, branches, commits, pull requests, checks, releases and clone addresses. Provide “Technical details” for snapshot digests, authority epochs, full OIDs and diagnostic receipts. Preserve the semantics without requiring everyone to understand the implementation.

**Do not cut Stead over from GitHub until the exact chosen profile can complete ordinary full-history pushes, concurrent updates, reviews, independent checks, restore and rollback rehearsal at representative scale.** Retain the current external source during the pilot. A later one-way mirror can support discovery; avoid dual writable masters.

### House compatibility

The current native Urbit distribution model publishes Gall apps/frontends in a desk. That establishes an app packaging path, not House plugin compatibility. Primary House discussion describes a simpler invite/passkey experience and an evolving `%gnat` application model; it is not a stable plugin contract. [W4–W5]

Create only the seams needed now:

- Host shell adapter: launch context, navigation, theme, deep links and optional embedded presentation.
- Identity adapter: verified external identity binding to a Stead principal; individual authorization remains native.
- Notification adapter: privacy-filtered events delivered to a host surface.
- Capability negotiation: supported host/application versions, explicit fallback behavior.
- Packaging manifest and install/upgrade hooks behind a documented interface once a real host contract is available.

Run a capped compatibility investigation against actual House source/docs and license. Its deliverable is a verified capability matrix and a tiny install/sign-in/deep-link proof, or a documented unresolved dependency. Do not let that investigation block standalone Work/Docs/agent completion or authorize a speculative core rewrite.

### Open source and reuse

The repository declares Apache-2.0 and preserves third-party notices. Use familiar interaction conventions and appropriately licensed components; do not assume a “Linear-like” reference supplies Linear source code or licenses. Reuse should be justified by a named component need, pinned source/version, maintenance and accessibility quality, and license compatibility. [R14]

The product's simplicity comes from the ontology and defaults, not from a mandatory absence of dependencies. A well-tested Markdown parser or accessible combobox is preferable to a growing custom approximation, provided the integration preserves the current boundaries.

## 7. The experience contract

These values are proposed implementation defaults, not claims that a standard mandates this particular design. A design agent may challenge them before implementation; an implementation agent should not silently replace them.

### Layout and hierarchy

| Element | Target |
| --- | --- |
| Workspace rail | 224 px desktop, with Search, Inbox, My work, then projects/favorites. Settings and member management at the bottom. |
| Global chrome | 48–56 px high. Compact identity/project context. No permanent implementation footer. |
| Project views | Overview, Work, Docs, and Code when enabled. A compact project title; no repeated oversized heading on detail screens. |
| Main spacing | 24 px desktop gutters; 16 px on smaller screens; a 4/8 px spacing rhythm. |
| Work list | 44–48 px rows, subtle separators, short key and clear title. Status groups, completed/canceled collapsed by default after a just-completed item remains visible briefly. |
| Work preview | About 560 px wide. If the remaining list would be unusable, open a full-page or overlay view instead of squeezing both panes. |
| Full Work detail | Readable main column plus compact properties; approximately 720–800 px content measure when appropriate. |
| Create Work | 600–720 px dialog on desktop; full-screen composer on small devices. Title initially focused. |
| Docs | 720–800 px prose measure; outline when useful. Source/preview side by side only when explicitly selected and enough space exists. |
| Review | Dedicated full-width route; about 240 px changed-file navigator; diff owns the main space. Decision bar remains reachable. |
| Small screens | One primary surface at a time, an accessible navigation drawer, no two narrow columns. |

Use system sans typography: 13–14 px interface labels, 14 px list titles, 16 px prose, 24–28 px page headings and 12–13 px code. These are starting values; zoom and text expansion must work. Do not shrink text to make a bad layout fit.

Retain the warm palette. Proposed light tokens: background `#F7F7F5`, surface `#FFFFFF`, rail `#F0EFEB`, border `#DEDCD5`, text `#20211F`, secondary text `#63665F`, accent `#5B50BD`. Derive an equivalent dark/system theme rather than inverting screenshots. Validate text, control, focus and status contrast in context. Use color plus shape/text, never color alone.

Use a single icon family: an audited local Lucide subset as the target, subject to the repository’s dependency review. Use 16 px icons for ordinary controls, standard file/repository/branch/pull-request metaphors, consistent stroke, and no decorative icon next to every label. People and agents use the same avatar structure; add an explicit Agent badge. Display name first, full Urbit identity in details.

### Choose controls by the job

| Selection/action | Control | Required behavior |
| --- | --- | --- |
| Status | Compact property button → ordered menu | Current selection, status icon/text, arrows/Enter/Escape, focus return. |
| Owner | Searchable member combobox | Authorized humans only; named project-steward inheritance explicit; Unassigned allowed before autonomous admission. |
| Worker | Searchable people-and-agents combobox | Authorized human or agent; name/avatar/type; no raw ID typing. Reuse the picker component with distinct eligibility rules. |
| Priority | Compact menu | None/Low/Normal/High/Urgent. Keep stored `medium` mapped consistently if displayed as Normal. Default None. |
| Branch or tag | Searchable ref popover | Show default/protected context, preserve exact ref, copy on demand. |
| Filters | Add filter → value picker → removable chips | Persist filter state in navigation. Clear visible. No giant permanent filter form. |
| Repeated action group | Visible overflow/context menu | Existing right-click and keyboard parity preserved; destructive actions separated. |
| Infrequent small setting | Native select or radio group | Use native controls when they fit. A custom dropdown is not automatically better. |
| Two or three immediate view modes | Segmented control | Clear selection; no hidden route reset or lost draft. |
| Dangerous irreversible operation | Separate deliberate confirmation | Name the affected object and consequence. Routine reversible edits need no confirmation. |

Apple's guidance supports familiar, predictable menus; it does not support replacing every dropdown for novelty. Accessible custom pickers require keyboard and focus behavior, not just appearance. For pointer controls, meet WCAG 2.2 target-size requirements; prefer 32 px or larger icon-button hit areas and approximately 44 px for touch controls. [W6–W7]

### Keep settings deliberately small

User preferences: System/Light/Dark appearance, notification delivery, timezone, and accessibility preferences where they are not already supplied by the device. Default to system appearance and the user's locale/timezone. Keep one standard density initially. Project settings: steward/members, optional repositories, review rules, allowed worker capabilities and bounded automation budgets. Workspace settings: identity, agent/runtime connections, storage/backup health and integrations. Avoid custom navigation, arbitrary field/workflow builders and per-project theme designers in the core release.

Open-source self-hosting must cover the application, its data, and necessary runtime services. Agent execution is optional; provide a provider-neutral runtime boundary that can use a local model or a configured external service. No mandatory hosted model account or proprietary control-plane service should be required to use Work, Docs and Code. State separately which optional model/runtime adapters are supported.

### Default Work behavior

Create from the current project with just a title. Defaults: Task, To do, No priority, Unassigned. Offer Assign to me. Never silently make the creator accountable. Starting autonomous work requires an explicit owner or visibly applies the configured project steward. Due date, milestone, outcome and context are optional at creation; they become required only where execution policy actually needs them.

The Work row order is status, short key, title, relevant blocking/change indicator, owner/worker, priority, overflow. Description is in preview/detail, not repeated in every row. Default grouping is status; board is a later projection of the same items and filters, not a second workflow implementation.

Work detail order: title and purpose; acceptance criteria; current worker and meaningful progress; proposed outputs; supporting Docs/dependencies; conversation. Keep type/priority/milestone in the compact properties rail. Raw revisions and IDs are under Details. Review feedback belongs to the Change and is summarized back on the Work item.

### Every screen needs these states

Initial loading; incremental refresh; empty; no filter results; read-only; dirty draft; saving; accepted; disconnected/stale; unknown outcome; conflict; revoked access; failed retryable request; unsupported operation. Define the action and visible message for each state before coding the happy path.

Use local skeletons. Preserve existing scoped watch/subscription and stale-response guards; real update infrastructure already exists. Reconcile on reconnect/focus. Keep targeted Retry and a refresh fallback, but do not make “Refresh” the primary way to operate Stead.

A save says Saved only after native acceptance. An optimistic item is visibly pending and can be reconciled. Unknown outcome should say “Checking whether this saved…” and recover the same request, not instruct the user to create a duplicate. Keep diagnostic receipt IDs available through Details. Never convert uncertain acceptance into a success toast.

### The 24 supplied screens and their replacements

| Screenshot | Exact recommendation | Acceptance condition |
| --- | --- | --- |
| 01 Home sign-in | Name the destination workspace/Home; simple Continue; explain approval next. Preserve ID normalization. | An invited first-time member knows who is requesting access and reaches the next step without operator instructions. |
| 02 Awaiting approval | Use verified configured approval destination where available; otherwise copyable address. Observe approval automatically with bounded retries; show expiry, Denied, Restart, manual fallback. | Original tab advances after approval. Expired/wrong-identity/unreachable cases are recoverable. Never guess an identity origin. |
| 03 Identity approval | Pending first; clear Approve/Deny; recognizable Home and matching code; history and protocol details secondary. | Approving one request cannot authorize a different or expired request. |
| 04 Project overview | Purpose, steward, next milestone, attention items, pinned Docs, active Work. Empty state offers New work/New doc; optional Add repository. | A reader can identify the goal, next action and contribution path. |
| 05 Work list | Compact rows and filters; short Work keys; steady metadata columns; no oversized description cards. | A normal laptop shows a useful queue, filters preserve selection, and server pagination remains correct beyond one page. |
| 06 Quick actions | Keep existing right-click, visible ellipsis, inline properties, S/A/P and keyboard-menu behavior. Improve discoverability. | All actions work without a mouse; focus returns to the correct row after filtering. |
| 07 Work detail | Replace 270–350 px inspector with useful preview and full route; content before administration. | Read a complex task comfortably; no lost draft on Doc navigation; loading ends in data, empty or error. |
| 08 Create Work | Wide composer, title/description first, property chips, “Create work item.” | Title-only create works; unavailable roster still permits an unassigned task; Cmd/Ctrl+Enter is intentional. |
| 09 Docs collection | Navigable list/tree with private/shared scope, readable titles, recent/pinned pages, updated time. | Find/open a page without repeated selection dropdowns or an extra Open button. |
| 10 Markdown editor | Read/Edit/Source/Preview; accurate supported Markdown; safe resource handling; clear save/conflict states. | Lists, links, fences and tables work; unsupported content survives; safe render and export agree. |
| 11 Project Links | Contextual source → relation → target with names/status and backlinks. Advanced table only if needed. | Real and synthetic fixtures display endpoints consistently. The supplied demo's bare verbs are not accepted reference UI. |
| 12 Activity | Display actor, verb, object and important before/after value; collapse noisy batches. | “Maya updated the onboarding guide,” not `document.save` and a UUID. |
| 13 Inbox | Cross-project attention queue: review, question, assignment, blocked/failure, decision. Persist unread/handled state. | Ten workers generate actionable decisions, not a heartbeat stream. Handling an item survives reload. |
| 14 Search | Global entry with explicit current-project filter, type chips and keyboard navigation. | Results open an exact object; no inaccessible title, snippet or count leakage. |
| 15 Repository | Name, branch, path, latest accepted commit, Clone; Files/Pull requests/History subnavigation. Details collapsed. | Live tree and stock Git workflow work on the same declared profile; demo data cannot close the gate. |
| 16 Branches/tags | Keep searchable picker; friendly `stead-142-fix-login` convention for new refs only; exact ref accessible. Preserve all existing/imported refs. | Long names truncate safely; branch change preserves path or explains absence. |
| 17 File preview | Render README with Raw option; code line numbers and permalink; binary/large-file states. | Pinned line links remain correct when a branch moves. |
| 18 Work context | Consolidate Development/Code changes into linked outcomes. Docs/dependencies show titles and states; removal in overflow. | A relation removal never reads as deleting the target. Required vs merely related changes are distinct. |
| 19 Linked Doc return | Generalize origin-aware routing and draft preservation to Docs, Work, files and Changes. | Deep link, refresh and Back behave predictably; reading a linked page does not require edit mode. |
| 20 Exact review | Dedicated route; purpose, author, revision, base→head, Files/Checks/Overview, review summary and action. | Reviewer sees what changed and what prevents acceptance before technical metadata. New bytes require the appropriate new review. |
| 21 File patch | Unified diff with file navigator, old/new line numbers, accessible insert/delete markers, threads and viewed state. | Multi-file review works by keyboard; threads persist through the authorized native API with repository/base/head/path/blob/side/line anchors; outdated threads survive revisions. Incomplete diffs are explicitly incomplete. |
| 22 Agent delegation | Worker/run card with queued/running/waiting/submitted state, evidence and relevant controls. | “Access granted” never implies “worker running.” |
| 23 Delegation form | Pick known agent; task/context/output summary; inferred defaults; advanced limits. | Non-code work shows no branch fields. Start dispatches a durable run or truthfully remains a grant-only action. |
| 24 Agent proposal | Same review screen as human-authored changes; Agent/run provenance; protections in repository settings. | Review, checks, conflict and merge rules are identical for comparable human/agent changes. |

The current native relationship projection does construct endpoint titles; screenshot 11's bare labels may be a synthetic-fixture/presentation discrepancy. Fix the demonstrated experience and fixture/native contract together rather than claiming the stored graph lacks endpoints. [R13]

## 8. What replacing the existing tools actually requires

Use a capability ledger with **implemented**, **qualified on a named workload**, and **supported in this release** as separate fields. A closed issue does not by itself establish any of those states.

| Replacement goal | Required core | Later breadth, explicitly separate |
| --- | --- | --- |
| Everyday Jira/Linear work | Reliable Work create/edit/assign, short keys, list and board, dependencies/subtasks, milestones/dates, search, personal queues, comments, notifications, imports/exports, understandable permissions | Arbitrary custom workflows, portfolio analytics, complex planning formulas, service-desk products |
| Confluence/wiki/docs | Readable/editorial Docs, hierarchy/collections, true Markdown, links/backlinks, safe attachments, history/diff, controlled sharing/publishing, search, migration/export | Rich collaborative cursors, large template marketplace, arbitrary executable embeds |
| Small-team GitHub/Bitbucket forge | Independent repos, stock clone/fetch/push, refs/history/files, PRs/diffs/threads, reviewers, checks, protected merge, credentials/revocation, backups/restore, supported limits | Full Actions marketplace, Packages/Pages, advanced code intelligence, global social discovery, every protocol extension |
| Agent collaboration | Named principals, bounded runtime, same Work/Docs/Code commands, durable runs, clarification, proposal/review, automatic continuation, observable failure/cancel | Unbounded autonomous organization, arbitrary self-installed tools, generalized agent marketplace |
| Broad self-hosted adoption | Supported installer, private owner setup, member invitations, browser identity path, backups/update/recovery, capacity/cost visibility | Every hosting provider, active-active authority, effortless automatic migration between all hosts |

This does not shrink the vision. It gives each claim a concrete exit condition. A team should be able to replace its ordinary workflow before Stead reproduces every service in the Atlassian or GitHub ecosystem.

### Migration is part of the product

Implement staged importers, beginning with Git, Markdown and GitHub issues, then Linear/Jira and Confluence exports according to actual adoption needs. Preserve source IDs, URLs, authors/timestamps where supplied, comments, labels, state mappings, attachments and relationships. Do not falsely attribute historical imported text to the importing principal.

Each importer needs dry-run mappings, unsupported-field/loss report, duplicate detection, resume, and idempotent replay. Import into a staged destination and review before activation. Record cross-links that could not be resolved. Identity mapping may require a human decision; do not silently merge two people with similar names. A Git mirror does not migrate work, knowledge, membership or review history.

### Self-hosting is a first-time-user journey

Ship one recommended supported deployment profile, not a menu of every infrastructure option. The operator should install a pinned release, name the Home, create an owner, invite a colleague, create a project, optionally connect a worker, and verify a backup using a concise guided path. Current technical runbooks remain useful underneath that flow.

The release manifest binds runtime/desk/frontend/API/saved-state compatibility. Upgrade preview states what will change and verifies a recoverable backup. Do not equate downgrading a frontend with rolling back migrated state. Recovery proves exactly one active authority, retained accepted history, identity continuity and fenced stale workers. Track backup age, storage growth, queue health and resource limits without requiring users to inspect raw journals.

## 9. Implementation phases and exit gates

These are **next-work packages**, not a renumbering of the repository's existing M0–M6 milestones or URB IDs. Preserve previously accepted evidence, map follow-ups into the current catalogs, and do not let this review become a competing roadmap. The companion YAML holds executable task packets and dependencies.

| Package | Goal and work | Exit gate | Existing alignment |
| --- | --- | --- | --- |
| A — Freeze the product contract | Reconcile terminology, owner/worker/run/Change, Project/Repository separation, revision semantics, route model, supported Git profiles and visual reference states. | One agreed interpretation of the five golden journeys; schema/route owners named; new and old states mapped; no competing contract documents. | URB-030/070/180/260 |
| B — A team can use Work and Docs daily | Shared shell, list/detail/create, real Docs, contextual links, readable activity, actionable Inbox/search, identity display, draft recovery; repair live repository browse separately. | A new member completes ordinary non-code work without operator help. Same journey passes direct-link, refresh, permission, conflict and offline recovery cases. | URB-040/060/070/190/260 |
| C — One complete agent outcome | Principal/runtime/run authority, task-contract revisions, bounded supervisor, common Change and Docs review, one real model adapter, run UX. Internal deterministic Code recipe remains a transport proof. | Non-code project delegates a Doc edit, answers a question, requests a revision, accepts it, and completes Work; restart/cancel/revoke/next-day review work. | URB-090/180/200/210/250 |
| D — A credible software forge | Independent repos, one Code product, stock Git full-history write workflow, dedicated PR review, checks, job-scoped staging, agent Code parity and restore. | Human and agent each complete a real supported repository change from task to accepted exact revision and independent check/build; conflict and recovery cases pass. | URB-080/090/100/200/250; later URB-150 |
| E — A PM can supervise a bounded agent project | Dependency queue, child-task plans, budgets, concurrency, exception Inbox, policy-controlled low-risk acceptance, paged history and retention. | Ten-task plan progresses with one clarification, one retry and one stale-document/result conflict; code queue parity follows the forge gate; no duplicate accepted outputs or budget bypass; PM can pause/reassign. | URB-090/190/200/250/260 |
| F — Installable supported beta | Installer/onboarding, browser identity, imports, supported upgrades/backup/restore, qualified capacity, independent teams, House compatibility spike. | Independent users install, use, update and recover the declared profile. Release claims match tested capabilities. House claim requires separate host proof. | URB-100/120/130/160/220/230/240/270/280 |

The dependency graph, not the letter order alone, controls parallel work. Bounded Docs project automation can begin after C; Code automation additionally waits for D. Storage and capacity design starts in A and ships incrementally across B–E. Do not wait until ten agents are running to redesign comment storage. Identity and repository contract work can proceed beside shell improvements once shared interfaces freeze. Do not make every visible UI improvement depend on completing all platform migrations.

### The first development increment

The first increment should deliver a visible difference and settle the contracts that block useful agent work:

1. Product integrator finalizes the owner/worker/Change and route contract using the five journeys below.
2. UI agent ships the compact shell, useful Work detail, title-only create, readable event presentation and meaningful empty states against existing APIs.
3. Native/domain agent separates Work execution-contract revisions and paged discussion, with predecessor-state migration.
4. Docs agent ships correct Markdown rendering, consistent titles and truthful new commit attribution.
5. Runtime agent proves one isolated deterministic result with crash/retry/cancel behavior; it does not claim model autonomy.
6. Independent reviewer performs the non-code workflow and records exact observed failures. Integrator fixes those before opening new feature lanes.

A suggested two-week planning window can contain the product contract, shell/Work and Docs slices; it is not an estimate for the entire phase or a promise that native identity/runtime work fits the same window. Size from actual repository work after the contract pass.

### Five golden journeys

**G1 — Ordinary team work.** Create “Plan the launch event,” create an event brief and tasks, assign a colleague, link the schedule, discuss a change, complete the deliverable. Code is never enabled. A reader can follow every step they are permitted to view.

**G2 — Human software work.** From a Work item, select the correct repository, use a normal Git client, push a branch, open a pull request, review files, request a revision, run required checks, merge the exact approved candidate and update the Work outcome. The branch moving invalidates stale review/check evidence appropriately.

**G3 — Agent Docs work.** Create Work in a no-Code project; choose a named agent; pin context; get a clarification; receive an exact Markdown diff; request one change; accept a new revision; observe Work completion and downstream readiness. No copied JSON brief or manual commit IDs are required.

**G4 — Agent software work.** Worker starts on an exact base, publishes only a job-scoped proposal, receives a change request, revises, passes separate checks, and is accepted by authorized review/merge actors. Normal comments do not kill the run; changed acceptance criteria cause explicit re-planning.

**G5 — Failure and recovery.** A worker crashes after producing output; the PM revokes access on another run; a Home restarts; a branch moves. Reconciliation yields one accepted result per intended action, rejects stale/unauthorized publication, retains history, and tells the user what needs a decision.

## 10. Agent team structure and handoff rules

Use one product/integration lead and a small number of focused implementers. Parallelize independent slices after interfaces freeze; do not assign “improve UX everywhere” to several agents.

| Role | Owns | Must coordinate |
| --- | --- | --- |
| Product/integration lead | Product decisions, phase scope, task dependencies, integration branch and acceptance | Shared schema/marks, migration order, route model and terminology |
| UX/components agent | Shell, tokens, controls, Work interactions, visual states | Domain/API contract; never invent server acceptance in UI |
| Work/Docs agent | Documents, task content, links, readable activity | Canonical Markdown, revisions, graph and export |
| Native identity/workflow agent | Principals, grants, command semantics, runs and state migrations | Sole state/authorization integrator; scoped workers |
| Runtime agent | Supervisor, isolation, adapter, effect reconciliation | Job contract and native final admission |
| Forge agent | Repository model, Code adapters, diff/review/checks and Git conformance | Native authority, exact refs and independent build |
| Operations/migration agent | Packaging, install/upgrade/recovery/imports | Supported profile and release manifest |
| Independent reviewer | User journeys, negative cases, accessibility and evidence | Cannot author the slice they independently accept |

These are work roles, not a requirement to keep eight agents running. With four concurrent execution slots, use the lead plus two independent implementers and one reviewer; rotate specialties. One agent may own several roles sequentially, but preserve independence where a gate requires it.

### Every task packet must contain

User outcome; exact existing file anchors; proposed new modules clearly labeled; inherited contracts; allowed changes; explicit non-goals; empty/loading/read-only/error/conflict states; default values and interaction details; dependencies; acceptance scenarios; evidence required; definition of done.

No task closes because its planning doc is written, a component renders a synthetic fixture, or an agent says tests passed. Require the relevant observed journey. Avoid boilerplate evidence rituals: a small UI change needs a focused screenshot/interaction check, while new authority or worker semantics need native/recovery negatives. Run broader checks only to address a concrete regression risk or current release gate.

### Integrator rules

- Read current `AGENTS.md`, active handoff/directive and the relevant skill before implementation. Check whether main advanced beyond this review; reconcile, do not reset another agent's work.
- Preserve M0–M6 and URB identifiers. Review-package task IDs are local labels; map them to existing parents and linked follow-ups. Do not overwrite historic acceptance or close issues from prose.
- One owner edits shared saved-state molds, public marks, policy contracts and wire schemas at a time. Parallel branches may consume agreed interfaces, not invent competing ones.
- Use a small coherent vertical slice per integration. Review exact source and inputs. Preserve the current independent review and deployment boundaries.
- Keep `MASTER_BUILD_DIRECTIVE.md` authoritative for architecture; update relevant current profiles when accepting these changes. Add a compact experience contract and current capability matrix. Do not create dozens of overlapping design documents.
- Keep the user-facing supported quickstart short. Historical test narratives and source-binding evidence belong behind links.

## 11. Concrete source ownership map

Paths below are existing unless explicitly marked proposed. File paths are relative to the repository root.

| Change | Existing implementation anchors | Intended extraction/addition |
| --- | --- | --- |
| Shell, route and draft continuity | `web/app/src/main.tsx` — `App`, `openProject`, `selectProjectTab`, `decodeWorkAddress`, `workAddress`, `openWorkDocument`, `backToWorkFromDocument`; `style.css` | Proposed `WorkspaceShell`, project/resource routes, per-resource draft/pending state |
| Work list/detail/create | `main.tsx` — `resourceRow`, `refresh`, `activeRows`, `formPanel`, `submitForm`, `openWork`; `WorkQuickActions.tsx`; `work.css` | Proposed `WorkList`, `WorkDetail`, `WorkComposer`, reusable property/member picker |
| Relationship and discussion UX | `WorkContext.tsx`, `WorkDiscussion.tsx`, `WorkDevelopment.tsx`, `WorkCodeLinks.tsx` | One contextual relation renderer, output/Change list, paged comments |
| UI primitives/states | `primitives.tsx`, `style.css`, `work.css`, `AcceptedTime.tsx`, `SupportDetails.tsx` | Vetted Dialog, Combobox, Menu, StatusBadge, PersonBadge, pending/conflict states |
| Markdown/Docs | `Markdown.tsx` — `inline/content`; editor JSX and `pageTitle` in `main.tsx`; `stead-team.hoon` document paths; `stead-git.hoon ++make-commit`; `stead-views.hoon ++resource-row` | Tested Markdown codec/profile, Doc reader/editor, title metadata, new-author attribution |
| Work revisions/comments | `stead-team.hoon ++revision/evaluate` and Work operations; `stead-team-codec.hoon`; `stead-core.hoon` types; `api.ts` | Contract revision vs Work fields vs append-only discussion sequence; versioned migration |
| Identity | `stead-team-config.hoon`, `stead-session.hoon`, `stead-identity-core.hoon`, `stead-browser.hoon`, current browser identity profile | Principal/auth-binding/service-credential contracts and registry; individual authorization |
| Independent repositories | `stead-code-home.hoon ++target`; scoped credentials, review/build/pack modules and frontend Code components | Repository registry, project associations, migrated IDs, repository-scoped routes/APIs |
| Runs | `stead-home.hoon`; `stead-code-delivery.hoon`; `stead-code-build-home.hoon`; `scripts/urbit/code_build_worker.py`; `scripts/urbit/agent_proposal.py` | Proposed native job reducer, supervisor and typed job protocol; reuse reviewed isolation patterns |
| Worker UI | `WorkDelegations.tsx`, its inline-Code condition in `main.tsx`, `api.ts` | Proposed `WorkerAssignment`, `ExecutionCard`, `RunDetail`, context picker, clarification actions |
| Common Changes and Docs review | Code proposal/review modules; canonical Docs save path; `CodeReview.tsx`, `CodeExternalReview.tsx`, `ReviewChanges.tsx` | Shared review shell, artifact-kind renderers, exact Doc proposal reducer |
| Expiry/adoption | `stead-code-delivery.hoon ++grant-valid/eligible/current/approve/merge-candidate`; review home/export code | Explicit execution vs proposal/adoption semantics; preserved current-authority checks |
| Inbox/global search | `stead-views.hoon ++activity/searchable`; `main.tsx resourceRow/refresh`; `api.ts`; existing updates modules | Durable attention projection and permission-safe aggregate queries |
| Code browser/review | `CodeRepository.tsx`, `CodePack.tsx`, `RepoBrowser.tsx`, `CodeReview.tsx`, `CodeExternalReview.tsx`, `ReviewChanges.tsx`, `externalReview.ts`, repository CSS | Dedicated routes and consistent capability contract; familiar PR/diff controls |
| Capacity and retention | `stead-team.hoon`; code store/pack/delivery modules; current storage/recovery profiles | Paged comments, hot/cold boundaries, retained receipts, bounded telemetry and quotas |
| Adoption and House | Current deployment/package/import/recovery scripts and docs, SDK v3 | Supported operator/member journey; thin host adapters after real compatibility proof |

Before changing a module, inspect current associated tests and all callers on the implementation branch. This map is a set of source anchors, not a claim that a complete change is limited to the listed files.

## 12. Acceptance and measurement

### Product evidence

Use real people who did not build the interface for at least the ordinary Work/Docs and review journeys. A useful initial target is four of five first-time testers completing the core task without coaching; record wrong turns and where they need help. This is a proposed target, not a result or a statistically strong study. Any lost accepted data, incorrect permission disclosure or misleading success state is a release blocker regardless of completion percentage.

For every visible slice, capture empty/normal/crowded data at laptop and small-screen widths, long titles/names, keyboard-only flow, screen-reader labels, reduced motion, zoom and a read-only role. Test the actual task, not only whether elements exist.

### Native/execution evidence

Required scenarios include concurrent writes, lost save replies, duplicate requests, stale task contract, ordinary comments during runs, expired lease, next-day review, revoked worker, canceled late result, stale epoch, moved target branch, incomplete diff, failed/unknown check, private linked input, and restart/export/restore. A new run or rebase cannot silently reuse approval of different bytes.

A job's process exit is not enough to report success. A successful check is not proof that acceptance criteria were met. An approved proposal is not a merged change. A release intent is not a completed deployment. Preserve these distinctions in both state and copy.

### Capacity evidence

Choose and publish a first supported workload before promising “teams” or “many agents.” A reasonable **qualification corpus to attempt**, not a supported capacity claim, is 1,000 Work items, 500 documents across collections, 100,000 retained business events, 10 simultaneous runs, and representative repositories in a declared byte/object/history range. Begin smaller if needed, record why, and adjust the supported target from measurements.

Measure read/save p50/p95, initial rendering, event backlog, live-state memory, object growth, queue fairness, crash recovery, backup/restore duration, and model/runner cost where observable. Set concrete latency/resource budgets after the first baseline. Keep per-command and decompression bounds even when historical scale increases. Do not delete dedup receipts or revocation evidence simply to make a benchmark pass.

### Release evidence

A credible beta requires an independent clean installation, one real no-code team workflow, one real software workflow, one real model-driven task, supported update and recovery, export without Stead, and a readable capability/limitations page. Existing URB-270/280 release governance still applies. House compatibility and native source cutover each need their own completed proof. [R16]

## 13. Explicitly defer

Defer a new core runtime, `%gnat` migration, generic workflow builder, arbitrary agent marketplace, global relationship graph canvas, unconstrained bot chat, active-active Home, a custom CI marketplace, broad portfolio analytics, full GitHub service parity and uncontrolled live rich-document collaboration. Keep future candidate issues #37–#40 as candidates unless a specific pilot justifies one; they are not new prerequisites for the current release.

Do not defer reliable navigation, readable content, correct Markdown, real agent dispatch, ordinary Git operations for the declared forge profile, migration honesty, or recovery. Those are the product.

## 14. Source register

All repository links below use the reviewed commit. `S01`–`S24` refer to the numbered PNGs in the supplied `review.zip`; the original `Stead-Architect-Review.md` identifies which are live and which are demos.

- **R1 — Active architecture:** [MASTER_BUILD_DIRECTIVE.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/MASTER_BUILD_DIRECTIVE.md).
- **R2 — Current repository status:** [README.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/README.md).
- **R3 — Current native delivery scope:** [CODE_DELIVERY_PROFILE.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/CODE_DELIVERY_PROFILE.md), [PHASE5_DOGFOOD_REHEARSAL.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/PHASE5_DOGFOOD_REHEARSAL.md).
- **R4 — Scope and historical architecture:** [AGENTS.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/AGENTS.md), [STEAD_CARRYOVER.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/STEAD_CARRYOVER.md).
- **R17 — Scoped resource identity amendment:** [CONTRACT_AMENDMENT_2.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/CONTRACT_AMENDMENT_2.md).
- **R5 — Application shell/state:** [main.tsx](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/web/app/src/main.tsx), [style.css](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/web/app/src/style.css).
- **R6 — Markdown implementation:** [Markdown.tsx](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/web/app/src/Markdown.tsx).
- **R7 — Current delegation UI:** [WorkDelegations.tsx](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/web/app/src/WorkDelegations.tsx).
- **R8 — Unimplemented job proposal:** [AGENT_JOB_PROFILE.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/AGENT_JOB_PROFILE.md); current handoff helper [agent_proposal.py](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/scripts/urbit/agent_proposal.py).
- **R9 — Delegation/review/merge authority:** [stead-code-delivery.hoon](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/native/core/desk/lib/stead-code-delivery.hoon).
- **R10 — Work, Docs, comments and explicit pilot limits:** [stead-team.hoon](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/native/core/desk/lib/stead-team.hoon).
- **R11 — Repository scoping:** [stead-code-home.hoon](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/native/core/desk/lib/stead-code-home.hoon).
- **R12 — Configured identity and session types:** [stead-team-config.hoon](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/native/core/desk/lib/stead-team-config.hoon), [stead-session.hoon](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/native/core/desk/lib/stead-session.hoon).
- **R13 — Projections and Docs commits:** [stead-views.hoon](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/native/core/desk/lib/stead-views.hoon), [stead-git.hoon](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/native/core/desk/lib/stead-git.hoon).
- **R14 — Licensing and notices:** [LICENSE](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/LICENSE), [THIRD_PARTY_NOTICES.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/THIRD_PARTY_NOTICES.md).
- **R15 — Standalone pilot and House boundary:** [PHASE5_DEPLOYMENT.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/PHASE5_DEPLOYMENT.md).
- **R16 — Existing milestones and release:** [ecosystem.json](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/specs/urbit/ecosystem.json), [RELEASE_READINESS.md](https://github.com/ScottTpirate/stead-urbit/blob/539825650c60e606634bf4ab5967b698a6daa6e3/docs/urbit/RELEASE_READINESS.md).
- **W1 — Linear/GitHub are separate linked or synced records:** [Linear GitHub documentation](https://linear.app/docs/github).
- **W2 — Human ownership, agent delegation and current platform restrictions:** [Linear assigning issues](https://linear.app/docs/assigning-issues), [Linear agent platform](https://linear.app/developers/agents).
- **W3 — Markdown standards:** [CommonMark specification](https://spec.commonmark.org/), [GFM specification](https://github.github.com/gfm/).
- **W4 — Native Urbit app model and distribution:** [Userspace](https://docs.urbit.org/build-on-urbit/userspace), [Software Distribution Guide](https://docs.urbit.org/build-on-urbit/userspace/dist/software-distribution).
- **W5 — House direction and evolving Gnat model:** [Toward the self-driving computer, October 31, 2026](https://graymirror.substack.com/p/toward-the-self-driving-computer). This is creator commentary, not a verified plugin SDK contract.
- **W6 — Control conventions:** [Apple Pop-up buttons](https://developer.apple.com/design/human-interface-guidelines/pop-up-buttons.md).
- **W7 — Accessible target size:** [W3C Understanding WCAG 2.2 Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum).

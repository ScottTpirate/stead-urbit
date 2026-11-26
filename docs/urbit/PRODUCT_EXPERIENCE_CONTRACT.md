# Stead product experience contract

Adopted requirements: November 15, 2026. Baseline:
`539825650c60e606634bf4ab5967b698a6daa6e3`. This contract directs the next
increments; it does not claim that target behavior is implemented or qualified.
The [master directive](MASTER_BUILD_DIRECTIVE.md) governs architecture. This
document owns product semantics and interaction defaults; current profiles own
their declared runtime versions. A future wire/state migration must be reviewed
and qualified before replacing a frozen contract. See the
[capability matrix](CAPABILITY_MATRIX.md), [alignment record](PRODUCT_ALIGNMENT_20261115.md),
and [32 execution packages](../../specs/urbit/product-execution-plan.yaml).
The [source review](reviews/2026-11-15-product-review.md) retains the detailed
screen specifications and source anchors; it is a dated design input, not a
second current directive.

## 1. Product promise and scope

A team defines an outcome, gathers context, assigns a human or agent, reviews
the result, accepts the work, and continues. This must work without a repository.
Software projects add repositories, pull requests, checks, builds and releases.
Keep the native Hoon Home, canonical Markdown, ordinary Git identities and
React frontend. No platform rewrite, generic workflow engine, mandatory hosted
model account or proprietary control plane is part of this increment.

Work is one canonical resource across project, repository, document and personal
views. External GitHub/Linear/Jira records map to Work through integrations; they
do not become competing internal masters. Work state, permissions, leases and
notification state remain native structured records with portable exports.

Workspace Inbox, My work and Search aggregate only within the selected Home
initially. Project navigation is Overview, Work, Docs and optional Code. Links
and Activity become contextual views, with advanced inspection available when
useful. Cross-home aggregation needs a separately authorized protocol.

## 2. Domain and interface contract

| Concept | Required meaning and boundary |
| --- | --- |
| Home | One authority accepts project mutations; transport address is not project identity. |
| Project | Goal, summary, human steward, milestones, Work and Docs; zero or multiple repositories. |
| Work | Stable scoped identity plus readable project sequence; one object in every view. |
| Owner | Accountable human. Unassigned is allowed at creation; autonomous admission requires an explicit human owner or visibly inherited project steward. |
| Working on it | Authorized human or stable agent principal carrying out the work. |
| Agent definition | Versioned instructions, runtime/model binding, tools, egress and isolation profile; distinct from principal identity. |
| Run / attempt | One execution of a task contract, with fenced retry attempts, budgets and exact inputs/outputs. No new ship per run. |
| Doc / collection | Canonical Markdown and revisions, organized within an explicit access boundary. A software repository is optional and separate. |
| Repository | Independent immutable ID, explicit owning project, Git objects/refs and scoped policy. Start with one owning project per repository. |
| Change | Narrow shared proposal metadata/lifecycle with typed Doc/code targets and exact before/after references. Reuse existing code reducers. |
| Relationship | Scoped endpoints, direction/type and optional exact revision. Backlinks derive from the same record. |

Interface sketches below are requirements for versioned implementation, not
existing API field promises:

```text
ResourceRef = (project, kind, collection?, local_id)
CodeRef     = (repository_id, commit_oid, path, optional_line_range)
Work        = (ref, work_revision, execution_contract_revision,
               discussion_sequence, owner, worker, status, blocked_reason,
               acceptance_criteria, required_outcomes)
Run         = (work_ref, execution_contract_revision, contract_digest,
               home, authority_epoch, requester, worker_principal,
               definition_version, grant, context_manifest, policy_version,
               output_targets, budget, deadline, idempotency_key, attempts)
Attempt     = (claim, fencing_token, lease, heartbeat, effect_receipts, results)
Change      = (work_ref, producer, run?, typed_targets, exact_inputs,
               exact_outputs, summary, checks, reviews, acceptance_receipt)
```

Membership/authentication bindings are explicit and revocable. Display names,
ship sponsorship, a model name and organizational grouping confer no permission.
Provider secrets stay in the supervisor's secret boundary. Permission to read
content does not authorize sending it to an arbitrary model service.

### State and completion decisions

Work states: Backlog, To do, In progress, In review, Done, Canceled. Blocked is a
reasoned condition on unfinished Work. Run states: Queued, Running, Waiting for
input, Submitted, Failed, Canceled. Submitted means reviewable output, not Done.
Changes distinguish proposed, changes requested, accepted, rejected and
quarantined outcomes; acceptance does not mean deployment.

Done requires all declared required outcomes accepted and required checks passed.
Informational links do not block completion. Multiple required repositories or
Docs cannot be satisfied by one merge. A human may explicitly complete a
non-artifact task with a completion note. Review required applies to submitted
deliverables and protected targets; permitted comments/progress/direct edits
remain direct operations unless target policy requires a proposal.

### Compatibility and migration dispositions

| Existing state or identity | Required disposition before migration ships | Owner/package |
| --- | --- | --- |
| Native ship members and bindings | Preserve IDs and historical attribution; add explicit service bindings without deriving access from a label; test rotation and revocation. | Native identity / T03 |
| Repository ID equals project ID | Retain that ID for the legacy repository, introduce explicit association and independent IDs for new repositories; preserve refs, credentials, reviews and OIDs. | Native forge / T04 |
| Work `revision` includes comments | Preserve history and old revision checks for old clients; introduce contract revision and separate paginated discussion/activity. Reject unsupported writes rather than ambiguously interpret them. | Native workflow / T05 |
| Legacy `blocked` status | Preserve raw status/history and blocking reason. Restore a known preceding unfinished state only from evidence; otherwise keep an explicit legacy blocked disposition requiring resolution. Never map silently to ready. | Native workflow / T05, T08 |
| Legacy Done items | Retain historical completion; do not invent acceptance receipts. Mark completion basis as legacy where required. New/reopened work follows required-outcome rules. | Native workflow / T05, T12 |
| Legacy priorities and Work IDs | Preserve stored values and IDs; display `medium` as Normal. New readable keys supplement identity and are stable within their project. | Work UI/domain / T08 |
| Existing grants and code proposals | Preserve provenance and exact bytes; keep current enforcement until T13 migration. Lease/grant expiry fences effects; durable inspection/adoption uses fresh current authority. | Native policy / T13 |
| Existing private drafts and published pages | Preserve explicit page publication semantics and distinct identities/provenance. Do not publish a collection implicitly or convert existing copies into synchronized writable mirrors. | Docs / T09, T12 |
| Repo Markdown exposed in Docs | Use one canonical repository file, exact origin and revision; all edits route through that origin. Standalone Docs retain their own container. | Docs/forge / T09, T20 |
| Imported Markdown/title/metadata | Explicit title for new Docs; defined heading fallback for older content. Preserve unsupported metadata or return an explicit loss report. New authorship must be truthful; old commit bytes remain unchanged. | Docs / T09, T26 |
| Existing links, routes and refs | Preserve scoped identities, existing/imported refs, tombstones and revision pins; keep compatibility routing or explicit unavailable/unsupported states. Do not reinterpret private URLs. | Integrator / T07, T10, T20 |
| Legacy `documents` (Doc→Work) and `related_to` relations | Preserve original bytes, meaning and direction. Use versioned decoding to present legacy Doc→Work as supporting context; new `Documents` means Doc→CodeRef and cannot reinterpret old records. | Native workflow / T10 |
| Existing evidence and frozen contracts | Keep original bytes, source/profile bindings and failed cases. Add a versioned successor; never rehash old proof to pretend it qualified new behavior. | Integrator and reviewer / T01 |

Each migration requires explicit save/load versioning, predecessor fixtures,
old-client disposition and restart/export/restore evidence. T01 is not fully
accepted merely because this decision table exists: native and UX leads must
review concrete versioned interfaces and migration designs first.

## 3. Relationships, Docs and navigation

Project Activity is a secondary view with address `#project/PROJECT/activity`. A supported event opens the current, freshly authorized Work item or document and collection. Back returns to the project activity list.

Relationship vocabulary: Parent/child (Work→Work), Blocks (Work→Work), Supports
(Doc→Work/Project), Implements (Change→Work), Documents (Doc→CodeRef), Related
(Work/Doc→Work/Doc), Derived from (artifact→source). Show dependencies, supporting
Docs and required changes on their objects. Removing a link never means deleting
its target. Distinguish latest-authorized Doc/branch bookmarks from exact pinned
revisions. Runs record what they actually read. Hidden endpoints reveal no name,
snippet, count or existence beyond the approved disclosure policy.

Use shareable routes for Work, Docs, repositories, Changes, reviews and runs.
Immutable identity drives lookup; readable labels drive display. Back/Forward,
refresh and linked-object return retain filters, selection, scroll and drafts.
Keep protected content out of URLs. The exact route grammar and compatibility
redirects belong in T01/T07 interface review before mutation.

Docs enter rendered Read mode, with focused Edit, Write/Preview and Source.
Support headings, emphasis, lists/task lists, fences, tables, links, quotes and
safe attachments using a documented CommonMark/GFM subset. No executable raw
HTML/MDX. Accurate preview, export and canonical Markdown must agree. Use explicit
Save and resilient draft recovery first; never commit per keystroke. Local draft
persistence requires principal/session/resource scope and logout/revocation
purging policy. Current memory-only drafts remain truthfully labeled until changed.

## 4. Agent execution and review

Delegate selects a named authorized worker, summarizes goal, allowed context and
expected output, then starts a real durable run. Defaults supply runtime, reviewer,
permissions and limits; advanced details remain inspectable. Doc-only work has no
branch fields. Until dispatch exists, label the current action as grant/brief only.

The Work card shows the named worker, useful progress, waiting question or proposed
output, plus View run and Stop work/Cancel. Inbox offers Answer or Review changes.
Keep tokens, raw logs and diagnostic IDs out of the ordinary conversation. A run
may ask an attributable question and respond to requested revisions in the same
Work/Change flow used by humans.

Normal comments and progress do not invalidate an unchanged execution contract.
Changed objective, acceptance criteria or required output triggers re-planning or
explicit supersession. Inputs stay pinned; a newer Doc is visibly newer, without
retroactively changing what the worker read. Material required-input changes need
an explicit decision. Current authorization is checked at every protected effect
and final admission regardless of pins.

Execution lease and delegating grant are distinct. Expiry stops further worker
effects/publication but does not erase historical proposals. Next-day inspection
uses current read/reviewer permission. Revocation or compromise may quarantine
output. Explicit adoption preserves original author/run/digest and requires fresh
acceptance authority, current scope/base/target, and required exact review/checks;
it never revives old credentials or bypasses revocation.

Home owns job state. An isolated external supervisor claims with compare-and-set,
uses leases/fences, records effect receipts and submits bounded manifests. Native
replay never automatically repeats model calls or external effects. Lost replies
reconcile the same request/output; ambiguous effects stay unknown. Task assignment
does not authorize messaging, purchases or deployment by itself.

Cancel durably stops new claims/effects and rejects late stale publication. Report
the difference between cancellation accepted and remote process termination
observed. Accepted outcomes remain history. Project Pause new work stops new
claims; existing runs need separate cancellation. No arbitrary process pause/resume
promise. Later queue automation has cycle checks, finite concurrency/budgets,
failure escalation and steward inheritance. Low-risk automatic acceptance needs
separate reviewer/acceptance authority; producers cannot approve themselves or
expand their budgets, tools or policy. Code automation waits for Code gates.

## 5. Five observable journeys

| Journey | Next action and durable outcome | Required failure behavior |
| --- | --- | --- |
| G1 Ordinary Work/Docs | No-Code project: create launch work, event brief/tasks, assign colleague, link schedule, discuss and complete deliverable. | Denied links remain private; conflict retains draft; reconnect reconciles the original save. |
| G2 Human Code | Select repository, stock Git push, PR, file review, revision, checks, exact merge and Work outcome. | Moved branch invalidates stale review/checks; unsupported/incomplete operations never appear accepted. |
| G3 Agent Docs | Named agent in no-Code project, pinned context, clarification, exact Markdown diff, requested revision, acceptance and downstream readiness. | Comments do not kill run; changed contract requires re-plan; expired grant permits only authorized durable review/adoption. |
| G4 Agent Code | Exact base, job-scoped proposal, revision request, independent checks and authorized exact merge. | No self-approval, wrong-repository credentials, stale review reuse or unauthorized target write. |
| G5 Failure/recovery | Crash after output, another run revoked, Home restart and moved branch; recover one accepted outcome per intended action. | Reconcile external effects, fence stale/canceled attempts, retain provenance and show the smallest required user decision. |

G3/T18 is the first complete agent product acceptance. Deterministic Code execution
is an internal isolation/transport proof, neither a substitute for G3 nor its
forge prerequisite. Docs linking and bounded Docs autonomy do not wait for T20.

## 6. Qualification, support and exclusions

Keep implemented, qualified on exact source/profile, and supported release as
separate claims. Preserve M0–M6 and URB-000–280; T01–T32 are mapped packages, not
replacement tracker IDs. Historical local acceptance is not new product acceptance.
Use real unfamiliar people for G1 and review usability: initial target four of five
without coaching, with wrong turns retained. This is a target, not an observed
result. Lost accepted data, permission disclosure or false success blocks release.

Native changes require concurrent/stale writes, duplicate requests, lost replies,
contract changes vs comments, expiry/adoption, revocation, late canceled results,
epoch changes, moved branches, incomplete diffs, unknown checks and restart/restore.
Visible slices need desktop/narrow, empty/normal/crowded, long text, keyboard,
labels, zoom, reduced motion and read-only observations. Synthetic screens do not
prove native behavior; model execution must actually dispatch and admit outputs.

Retain bounds and reserve recovery/revocation capacity. Page comments/run telemetry
separately; distinguish accepted business journal from transient logs. T31 attempts
1,000 Work, 500 Docs, 100,000 retained business events and 10 runs, with repository
sizes declared separately. These are qualification targets, not supported limits.
Measure latency, memory/object growth, fairness, backlog, costs and recovery before
setting support budgets. No uncontrolled removal of existing pilot safeguards.

Imports require source identity/provenance, dry-run mappings and loss reports,
staging, resume, deduplication and explicit activation. One supported installation
path must cover owner/member setup, optional worker, backup, update and recovery
with one active authority and fenced workers. GitHub remains source until a full
exact-profile write/review/build/restore proof and explicit cutover authorization.
House gets a bounded source/license/SDK investigation and narrow adapters only;
unsupported interfaces stay disabled and never block standalone delivery.

Defer new core/Gnat migration, arbitrary workflow builders, global graph canvas,
unbounded agent chat/marketplace, active-active Home, CI marketplace, broad
portfolio analytics and full GitHub-service parity. Existing #37–#40 remain
candidates, not release prerequisites. Independent adoption, app integration,
maintainer and release governance still apply under URB-270/280.

## 7. Visual and interaction defaults

| Surface | Default |
| --- | --- |
| Shell | 224 px rail; 48–56 px chrome; 24 px desktop / 16 px small-screen gutters; 4/8 px rhythm. |
| Work list | 44–48 px rows: status, short key, title, blocker/change, owner/worker, priority, overflow; status grouping. Done/Canceled collapse after brief completion visibility. |
| Work detail | About 560 px preview or full route; 720–800 px readable main column with compact properties. One primary surface on narrow screens. |
| Create Work | 600–720 px dialog or mobile full-screen; title focused and only required field. Task, To do, No priority, Unassigned; explicit Assign to me. |
| Detail order | Purpose, acceptance criteria, worker/progress, proposed outputs, supporting Docs/dependencies, conversation. IDs/revisions in Details. |
| Docs | 720–800 px prose; outline when useful; split source/preview only by choice with adequate width. |
| Review | Dedicated full-width route; ~240 px changed-file navigator; Files/Checks/Overview, line numbers, accessible diff markers, threads and reachable decisions. |
| Typography | System sans; 13–14 px controls, 14 px list titles, 16 px prose, 24–28 px headings, 12–13 px code; support zoom/text expansion. |
| Palette | A warm charcoal rail (#181817) with ivory type (#F6F2EB). Light work surfaces use #F8F7F4 and white, text #252420 and secondary #63605B. Dark surfaces use #1B1B1A and #242422. Reserve violet for focus and active state. |
| Icons | One audited local Lucide subset subject to dependency review; 16 px ordinary icons, preferably 32 px hit areas / ~44 px touch. Text/shape plus color for state. |

Use the low-light entrance and restrained typography of [Urbit House](https://urbit.house/front) for sign-in, approval and the project overview. Match the scan density and keyboard navigation of [Linear](https://linear.app/) in Work. Give Docs a quiet reading column and keep project actions in the same place across views. Use only locally served styling and assets. Provide a device-local system, light and dark appearance preference for working surfaces.

Status/priority use compact ordered menus. Human owner and human/agent worker use
the same searchable picker with distinct eligibility rules. Branches/tags use
searchable exact-ref pickers. Filters are removable chips retained in navigation.
Keep right-click, visible overflow, keyboard actions and focus return. Use native
selects/radios for small infrequent settings; no novelty dropdown replacement.

User settings: system/light/dark, notification delivery, locale/timezone and
needed accessibility preferences, one density initially. Project settings:
steward/members, repositories, review rules and bounded worker policy. Workspace
settings: identities, runtime connections, storage/backup health and integrations.

Every surface specifies loading, incremental refresh, empty, no results, read-only,
dirty draft, saving, accepted, stale/disconnected, unknown outcome, conflict,
revoked, retryable failure and unsupported states. Preserve watch/poll guards and
reconcile on focus/reconnect. Saved follows native acceptance only. Unknown says
“Checking whether this saved…” and reconciles the same request. No fake progress
percentage or success toast. Govern resource links/attachments/DOM props explicitly.

Detailed replacements and acceptance conditions for all 24 supplied screens are
retained in [source review §7](reviews/2026-11-15-product-review.md#7-the-experience-contract)
and apply with these decisions. Its 24-screen review is supplied evidence; this
alignment did not re-open the screenshot archive or repeat its visual inspection.

## Stead Handbook

Every signed-in member can open Stead Handbook under Projects, including someone with no shared projects. It opens in the normal project shell with reader access. Use the shared Overview, Work list and detail, Docs collection and reader, and Code repository browser. The bundled project has its own read-only data source. Its example illustrates an actual Work item, discussion and linked guide. Team membership, search and Git credentials stay scoped to team projects.

Offer **Show me around** on the Handbook. Each step opens the corresponding project tab and gives one short hint. Members can browse freely, skip from any step and replay the tour. Save Skip or Done for that account in the current browser. Settings lets each member hide or restore the Handbook in Projects. Bookmarked guides remain accessible.

Open Code at the selected branch or tag’s root file list. When that tree contains a readable README, render it below the list using the same commit and Markdown reader. A member can still open the file to inspect its exact source.

Introduce the product with a short **Why Stead?** and a separate **How Stead works** guide. Explain how portable Git and Markdown content, Urbit identity and Home’s permissions fit together. Maintain the guides and Git README in `web/app/src/handbook/`. Edit the corresponding Markdown in the same change as a user-visible workflow, command, permission or setting. Check the directions using the role and release the guide describes. Describe experimental agent and Git actions accurately until the capability matrix records the completed user journey. The Handbook browser check exercises project navigation, the tour, the canonical Markdown, visibility across reloads and account isolation.

# Product native interfaces and migration proposal

Prepared November 15, 2026 from source `539825650c60e606634bf4ab5967b698a6daa6e3`.
Status: **proposed for integrator and independent native review**. This is the
concrete T01/T06 design supporting the [experience contract](PRODUCT_EXPERIENCE_CONTRACT.md),
not a new active wire or saved-state version. Native compilation and migration
qualification have not run for this change. The root agent's current preflight
reported 96°C and refused startup above the existing 75°C admission limit;
continue source work without changing thermal guards.

## Current seams and immediate implementation slice

- `stead-home.hoon` accepts saved envelopes 1–9; configured Work/Docs uses 3,
  inline Code uses 4/5, handoff uses 6, retirement/external packs use 7,
  external write ledger uses 8, and external reviews use 9.
- `stead-team-owner.saved` contains team state plus rebuildable projections.
  `stead-core.work-state` is `[revision data=object-map]`; command/3 comments
  are embedded in `discussion` and increment the same resource revision.
  `stead-restore` reconstructs accepted command/3 journal history, including
  original actor and target-binding records; old bytes cannot be reinterpreted.
- Configured members and `stead-session.actor` are ship keyed. `stead-team.current`
  resolves that identity again. Code credentials/delivery repeat the same actor
  checks. Non-ship service actors require coordinated resolver replacement.
- `stead-code-home.target` constructs `[home project project epoch]`.
  Repository maps, external pack anchors, credentials and review paths share
  that coupling. A repository picker alone cannot implement T04.

**First slice T05a:** add a pure execution-contract projection over the existing
accepted Work journal, consume it in authorized Work reads and an explicitly
versioned agent brief. This removes the helper's comment/status invalidation
trap without changing command/3 receipt or predecessor bytes. It does not close
T05: independent comment CAS, paged storage, new statuses and required-outcome
acceptance require the later v4/v10 migration.

T05a contract projection processes accepted Work creation/update events in
accepted order, bounded by the Home's existing 4,096 ordinary-event limit.
Start execution revision at 1 on creation; increment only when exact title or
description bytes change. Status, priority, type, assignment and comments do
not change it. Deletion makes the Work unavailable. Do not derive a contract
revision from the latest aggregate resource revision. During restore no read
serves until current journal reconstruction has completed.

Expose `execution_contract_revision` (canonical unsigned decimal string) and
`execution_contract_digest` (64 lowercase hex) on the authorized single-Work
read. These are additive query/3 fields with an explicit capability label
`stead.work-contract/1`; do not widen the closed command/3 parser. Digest input
is existing canonical JSON, domain `stead.work-contract/1`, containing exact
`project_id`, `work_id`, `execution_contract_revision`, `title`, `description`.
Use `hash:stead-codec`, whose domain separation is already established. Including
the contract revision prevents a changed-then-restored goal from reviving an
old task. Never include comments, status, priority, progress or current clock.

Agent brief/2 pins both fields and the existing project/Work/worker/target
scope. Its helper fetches current authorized Work and compares the contract
revision/digest; brief/1 retains its existing strict aggregate revision check.
Do not reinterpret an old brief. Delegation/current-membership/target/base
checks remain live. A positive comment-during-task test and a negative goal
change test must exercise the actual new helper path, not an unused model.
The existing native Code submit does not carry a Work contract pin: this helper
check alone has a read/submit race and cannot prove atomic stale-contract
publication rejection. T14 typed admission must compare the contract inside
Home's final transaction. T05a acceptance must retain that limitation.

## Shared shapes reserved for the reviewed successor

The reserved public successor is `stead.command/4`, `stead.query/4`,
`stead.receipt/4`, with distinct marks and declared capabilities. Saved-state
successor is `%stead-home %10`; do not use version 10 before predecessor fixtures
and fingerprint/export/recovery helpers understand it. Existing shapes 1–9
remain frozen. New modules own product types rather than changing old molds
in place. Exactly one integrator owns these shared additions.

| Shape | Fields and invariants |
| --- | --- |
| Principal | `principal_id`, `kind=person/agent/service`, display fields, active flag. ID is independent of authentication/runtime. |
| Binding | `binding_id`, immutable principal owner, `mechanism=native/oidc/service`, verified external reference, revision, active/expiry. Keep ownership tombstones and revision high-water marks. |
| Verified actor | principal ID, binding ID/revision, mechanism/assurance, expiry and transport-specific verified identity. Clients never supply a trusted actor. |
| Agent definition | stable definition ID + revision, principal ID, instructions digest, runtime connection/profile, model/tool/egress policy and steward; no provider secret. |
| Repository association | independent immutable repository ID, owning project ID, object format/profile and active/tombstone state. Resource scope always carries both IDs. |
| Work metadata | Work ref, property revision, execution-contract revision/digest, discussion sequence, explicit owner or steward inheritance, worker, state, blocked condition, completion basis and required outcomes. |
| Comment | immutable `(project_id, work_id, sequence)` subresource, body, original actor/time, accepted request reference and optional legacy comment revision. Sequence is an internal scoped ordered identity, not a replacement Work UUID. |
| Typed target | Doc: project/collection/document + exact prior revision and Markdown digest. Code: project/repository + exact target/base/head. Completion note: source Work + exact note revision. |
| Change | ID/revision, Work, producer, optional run/attempt, typed target, immutable input/output digests, summary, checks/reviews, state and acceptance receipt. |
| Run | ID, Work, contract revision/digest, requester/owner/worker, definition revision, scoped grant/policy version, authorized exact context manifest, output targets, budget/deadline and lifecycle. |
| Attempt | monotonic attempt number/fencing token, claimed worker binding, lease/heartbeat, durable effect references and immutable result manifest. |

A principal may retain one active mechanism binding initially; there is no
shared agent credential. T03 first imports current ship members without changing
IDs, actor records or grants, then adds individually authenticated service
bindings. Resolver callbacks for Git/review/run code accept verified principal
references rather than `@p` alone. Native sender lookup remains explicit.

## T05 command, concurrency and migration contract

Retain a legacy aggregate revision for old receipt correlation; do not call it
the new property revision. New Work operations use the following independent
preconditions, all in addition to current principal/grants/epoch and request
idempotency. Command/4's closed envelope keeps project/resource/request/epoch,
operation and payload; a typed `expected` object replaces the ambiguous single
`expected_revision`. Unknown expected fields/operation combinations fail.

| Operation | Expected fields | Changes |
| --- | --- | --- |
| `work.create` | `work_revision=0`, `execution_contract_revision=0` | Creates properties and contract at 1, discussion sequence 0; no implicit worker/run. |
| `work.update-properties` | `work_revision` | Status, priority, type, owner, worker and blocking condition; never silently changes goal. |
| `work.update-contract` | `execution_contract_revision` | Title, description, acceptance criteria and typed required outcomes; increments contract only when canonical content changes. |
| `work.comment` | `discussion_sequence` | Appends one immutable comment and increments sequence; does not alter property/contract revision. |
| `work.complete` | `work_revision`, `execution_contract_revision` | Requires accepted required outputs/checks or an explicit authorized human non-artifact note. |
| `work.delete` | `work_revision`, `execution_contract_revision`, `discussion_sequence` | Tombstones the Work and fences active runs without deleting historical comments. |

A concurrent comment and property edit can each accept using their independent
preconditions. Concurrent comments use stream CAS: one wins; two comments cannot
occupy one sequence. An unknown-outcome retry sends the exact original bytes and
request ID. After Home confirms a CAS conflict, the client may construct a new
command with the current sequence and a new request ID, retaining the rejected
attempt. Never mutate expected fields beneath an existing request ID. Closed receipts
identify operation, expected/resulting relevant revisions and immutable comment
sequence where applicable. Request identity stays `(project, principal, request)`;
a changed canonical payload under that ID conflicts. No parser silently
translates command/3 into command/4 or changes its digest.

Migration first validates the actual predecessor with its existing replay
rules, then applies one deterministic versioned conversion. Keep old journal,
receipt, Git and actor bytes. Move embedded comment payloads into separately
keyed comment records in posting order; preserve `comment_revision` as the legacy
alias and retain author/time/accepted request. Remove the live embedded copy
only when the v10 record becomes authoritative. Derive initial property and
contract revisions from actual accepted operations, not current labels.

The v10 product sidecar owns metadata, comments, principal/repository additions,
Changes and runs; the existing core Work map remains the sole current source
for Work content. A versioned v4 reducer receives core plus sidecar and commits
both and its journal/receipt in one Home transition. Existing legacy fields are
retained for history/read projection, not separately writable masters. V10
restore must replay the versioned legacy prefix, apply its recorded migration
boundary, then replay v4 records before comparing the full authoritative state.
A partially rebuilt sidecar serves no business data. Export/fingerprint includes
both core and sidecar; runtime sessions, credentials and leases are not restored
as live authority.

After a project activates v4 Work, command/3 new Work writes return correlated
`unsupported_version` after current auth; exact previously accepted command/3
retries may recover their old receipt under current access. Query/3 can expose
a faithful compatibility read only; new `in_review`/blocked semantics that an
old client cannot represent require upgrade, never silent relabeling. Other
unchanged command/3 resource families may remain enabled until individually
migrated; capabilities declare this per operation. Legacy unconfigured fixtures
remain on their historical formats.

For legacy blocked Work, preserve raw state and cause; reconstruct a prior
unfinished state only if history supports it, otherwise expose an explicit
legacy-blocked disposition requiring resolution. Legacy Done preserves a
`legacy` completion basis without invented acceptance. New/reopened Work uses
required-outcome acceptance. Migration never creates fictitious user events.

## T04/T12/T13/T14 incremental integration

- **T04:** import each legacy repository under its existing ID equal to project
  ID and add an explicit association. New repositories use independent IDs.
  Update map keys/resolvers, Git URL/credentials, pack manifests, delivery
  boards, recovery and UI together. Old Git URLs resolve only that legacy
  association; no fallback chooses an arbitrary repo. Wrong-repo credentials,
  reviews, job outputs and replay attempts must fail. Reissued credentials
  never change existing object IDs or historical scope.
- **T12:** new Docs Changes live in the product sidecar; Code envelopes reference
  existing exact proposal ID/revision/OIDs rather than copy a mutable board.
  Accept Docs through current document authorization and revision CAS; keep
  private collection publication distinct. Change acceptance and the resulting
  Doc revision/receipt commit together. Historical direct saves stay direct.
- **T13:** keep producer/run/grant provenance immutable and separate readable
  retained output from current publication/acceptance authority. Expiry fences
  new effects. Explicit revocation may quarantine. `change.adopt` binds exact
  Change revision/output digest/current target and records current adopter,
  reviews and checks; it never renews a worker credential or accepts its late
  publication. Producer self-approval remains denied.
- **T14:** Home owns issue/read/list/claim/heartbeat/wait/answer/resume/cancel/
  finish. Attempt number is a fencing token within run scope; claim/renew/finish
  compare it plus current authority, contract, epoch and budget. Resume means
  clarification continuation only. Durable effect intents/results are recorded
  separately from telemetry; restart reconciles the same effect before retry.
  A finish commits exact Change reference and Submitted together, not Done.

## Storage and qualification boundary

[Storage inventory](../../specs/urbit/product-storage-profile.json) records actual
source caps, traversal costs and proposed evidence, not measured capacity.
**The ordinary accepted-event limit is 4,096 per Home, not per project.**
`stead-team.event-count` deliberately ignores project for ordinary receipts and
filters by project only for the 128-event security reserve. The dated supplied
review's per-project wording is superseded by this source finding.

Initial sidecar additions must stay within existing total request/response and
Home event bounds. Paged comments and run telemetry cannot grow unbounded nouns.
Use small indexed pages for current metadata; retained immutable Markdown/Git/
artifact bytes belong behind the existing content-addressed storage boundary.
Do not delete accepted receipts, revocation high-water marks, tombstones or
required review/effect provenance to make a benchmark pass. Compaction needs a
versioned checkpoint with verified retained-history/export and exact replay
semantics, then restore testing before activation.

Qualification order: pure T05a native vectors and helper regressions; actual
single-Work read/brief consumption; then v4 reducer positives/negatives; exact
v3–v9 predecessor conversion; browser concurrency and restart/export/restore.
T03/T04/T12/T13/T14 each add their own scope/revocation/late-output negatives.
The full T06 baseline measurement remains pending safe thermal admission, and
T31's 1,000 Work/500 Docs/100,000 events/10 runs remains a target, not support.

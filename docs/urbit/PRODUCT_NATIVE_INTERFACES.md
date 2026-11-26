# Product native interfaces and migration proposal

Prepared November 15, 2026 from source `539825650c60e606634bf4ab5967b698a6daa6e3`.
Status: **successor interfaces, disposable Home carrier and app integration independently source-reviewed; native qualification and activation pending**. This is the
concrete T01/T03/T05/T06 design supporting the [experience contract](PRODUCT_EXPERIENCE_CONTRACT.md),
not a new active wire or saved-state version. T05a's existing-state execution
pin extension passed hosted native qualification at commit `f254244` (167 arms,
1,647 checks); the successor command/4 decoder, migration and reducer below
remain a separate unactivated increment. See the qualification receipt
for exact source and limits. Heavy native work uses the hosted runner; local
thermal admission and cleanup guards remain unchanged.

## T01 native design review — November 25, 2026

**Native design accepted for T01's scoped identity and migration decisions.**
The experience contract and the concrete interfaces below agree on the
dispositions in this section. No further product decision is needed to freeze
this native design. This verdict does not activate a wire or saved format,
qualify a migration, or close the separate UX review. The dated implementation
and test notes below retain their original source scope; current execution
status belongs in the [capability matrix](CAPABILITY_MATRIX.md).

Home is the authority namespace. An ID from another Home is not implicitly
usable here, even when its bytes match. Within that namespace, the exact keys
and revision meanings are:

| Resource | Scoped identity and revision contract |
| --- | --- |
| Principal and binding | Home catalog IDs; a binding has one immutable principal owner. Retain binding-owner tombstones and principal revision high-water marks. Definition/runtime versions use `(id, revision)` and never rewrite a Run's pins. |
| Work and comment | Work is `(project, work)`. A comment is `(project, work, sequence)`. Legacy aggregate Work revision, new property revision, execution-contract revision and discussion sequence are distinct. The readable project sequence does not replace the Work ID. |
| Repository | Catalog identity is the repository ID, with one immutable owning project. Authorization carries Home, project, repository and epoch. Only an explicitly imported legacy association uses `repository = project`; new repositories have independent IDs. |
| Run, attempt and effect | Run is `(project, run)` with an immutable Work reference in its contract; the UI route also carries Work. Attempts are keyed by Run and attempt number; effects add the effect ID. Question sequence is Run-global and is not reset on a new attempt. A bounded per-attempt model question count is a separate value. |
| Doc Change and result | Change is `(project, change)` and retains its Work. Immutable result identity adds result revision. Change lifecycle revision, result revision, Work contract revision and target Doc revision are separate CAS domains. Code Changes retain existing exact proposal/revision/OID identities. |
| Target | A Doc target is `(project, collection, document)` plus exact base revision/hash. Code targets carry project, repository and exact refs/OIDs. A view or imported origin does not create a second writable Doc or repository file. |
| Request | Work, Run and Doc Change request records use `(project, principal, request)` and their integrator checks cross-family reuse. This does not redefine every ledger: owner requests remain in the owner ledger, and repository creation uses its catalog request ID with exact actor/project/repository binding. |

The concrete source anchors are [product state](../../native/core/desk/lib/stead-product-state.hoon),
[principals](../../native/core/desk/lib/stead-principals.hoon),
repository catalog,
Run state and
Doc Change state.

Migration dispositions are fixed, rather than deferred to a future heuristic:

- Import legacy principals without changing IDs, actor bytes, grants or binding
  ownership. Kind remains unresolved until the actual Home owner declares it;
  a native login or historical assignment does not prove accountable human
  ownership. Preserve unresolved assignment and blocked provenance explicitly.
- Validate the old Work journal before conversion. Preserve old receipt and
  aggregate revision meaning; derive the new counters from accepted events.
  Move comments only after exact comparison with the predecessor discussion,
  retaining their old revision aliases, authors, times and requests. Legacy
  Done keeps its legacy basis without fabricated acceptance.
- Import each legacy repository through its explicit project-equal alias and
  preserve the complete old Code, pack, external-write and review state.
  Existing URLs cannot select an arbitrary new repository. New repository
  creation and current authorization remain separate from historical import.
- Do not manufacture Runs or typed Change acceptance from legacy assignments,
  direct Doc saves or Code history. New Run/Change records use their versioned
  reducers and exact adjacent transaction/replay rules. Submitted remains
  distinct from Done; adoption preserves producer and output provenance and
  never renews execution authority.
- Keep envelopes 1–9 and their original payload/type observations intact. The
  current `%10` `native-human-doc/1` format retains its exact product target and
  all outer Code/handoff/retirement/pack/external/review fields; its first
  disposable profile explicitly refuses nonempty Code-related tails. It is
  not an upgrade path for the live Code Home. Reserved later service/Run/model
  state requires an explicitly versioned successor, not an in-place widening
  of frozen `%10`. Actual old-state capture, exact payload/type comparison,
  interrupted recovery and current authority checks remain activation gates;
  synthetic fixtures cannot impersonate that evidence.

These dispositions are implemented or staged at the concrete boundaries in
[Work migration](../../native/core/desk/lib/stead-product-migrate.hoon),
repository import,
product history and
[Home save/load](../../native/core/desk/app/stead-home.hoon). Completing their
carrier integration and native qualification is downstream implementation work,
not an unresolved T01 identity or migration-policy decision.

## Current seams and immediate implementation slice

- The deployed predecessor accepts saved envelopes 1–9; configured Work/Docs uses 3,
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
accepted order, bounded by 6,144 retained journal entries: the existing 4,096
ordinary events plus the configured per-project security reserves.
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

## Prepared disposable human Work/Docs carrier

Commit `34c62a4` adds the explicit `native-human-doc/1` carrier. It is
source-reviewed,
with fourteen new native test arms and ten passing host adapter tests; the Hoon
carrier and new arms have not compiled or run. This is not an eligible upgrade
for the current real Code pilot. Actual owner transport, Jael fake status,
`isolated-fake` runtime, `local-disposable` custody, empty Code state and the exact
configuration/predecessor fingerprint are required before activation.

The full version-10 envelope retains profile, pristine predecessor or product
restore target, Code, handoff, retirement, packs, external writes and reviews.
Migration and validation keep the original target until publication. All old and
new accepted Work/Doc/owner operations enter one ordered product history.
Existing versions 1–9 retain their old routes and saved shapes. Version-10 host
fingerprint helpers
passed 38 host checks; generated Dojo expressions and interrupted restore still
need actual native execution.

The prepared profile advertises exact command/4, query/4 and Doc Change
capabilities with explicit refresh. Typed `principals` and `completion` reads
remain scoped and advisory; final acceptance rechecks current authority and
exact outcomes. Unsupported old Work, aggregate search/activity, watches, Code,
legacy export, service and run routes stay unavailable in this first profile.
The app integration at `0f9aba9` selects this capability explicitly, retains
original requests in the actual current-session draft partition and hides
revoked content without dropping unrelated drafts. It adds exact Doc Change
addresses and a human proposal/review/acceptance journey. TypeScript, 46 client
regressions, 19 typed-read checks and 10 journey boundary checks passed; these
host checks
do not prove the connected browser or native journey.

The exact-`125e4a6` [import diagnostic](https://github.com/ScottTpirate/stead-urbit/actions/runs/43762343777)
passed Product codec/state and Actor/Run-state imports, but failed the migration
library and the old Run/Doc decoder syntax. The original Product codec test
fixture is a separate failure. Reviewed syntax corrections and a bounded
compiler-location diagnostic are successors, not passing qualification. Actual
multi-person native/HTTP, migration, cold restart and browser evidence remain
required before activating this profile.

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

`oidc` in the Binding design is a reserved future verified mechanism. The
current `stead-actor` variants are native and service; this table does not
activate an OIDC resolver or let authored fields construct a verified actor.

A principal may retain one active mechanism binding initially; there is no
shared agent credential. T03 first imports current ship members without changing
IDs, actor records or grants, then adds individually authenticated service
bindings. Resolver callbacks for Git/review/run code accept verified principal
references rather than `@p` alone. Native sender lookup remains explicit.

The source-only `stead-principals` catalog preserves every predecessor principal
ID, binding ownership tombstone and principal revision high-water mark. Imported
kinds are **unresolved**: a native login alone does not prove a person, and past
worker ships must not become accountable human Owners by inference. A declaration
from the actual Home owner, with current catalog revision, selects an immutable
person/agent/service kind. Display and active state have their own catalog CAS;
deactivation cannot permit a later kind transfer. Removed predecessor members
retain IDs without an invented current display name. The native-kind adapter
requires both an active declared catalog entry and a live current native binding;
it does not replace current project grants or Work assignment eligibility.

Agent runtime bindings and definitions have separate stable IDs and immutable
versions. A definition pins an exact runtime version and instructions digest;
a runtime version pins an explicit profile and policy digest. New versions do
not change existing definitions, earlier authorship or run pins. Runtime and
definition ownership cannot transfer to another agent. Only the trusted Home
owner path can append these records; an agent cannot alter its own policy. These
records contain no credential and do not authorize execution. The runner must
resolve the named profile and digests against its reviewed allowlist.

This catalog is included in the prepared disposable version-10 carrier above,
but no deployed route or native qualification covers it. Its six original native
cases remain source-only. Broader activation still requires
recorded configuration/custody changes, saved-state validation and replay,
individually scoped service credentials, verified non-ship actor resolution and
the corresponding current-membership adapters. Catalog declarations alone do
not satisfy T03's live service-agent acceptance.

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
| `work.resolve-legacy-blocked` | `work_revision` | Explicitly chooses the unfinished state and optional blocking reason while retaining legacy provenance. Ordinary property edits cannot clear this disposition. |
| `work.resolve-legacy-assignee` | `work_revision` | Explicitly chooses owner/worker or leaves both unassigned, retaining the legacy assignment and marking it resolved. |
| `work.comment` | `discussion_sequence` | Appends one immutable comment and increments sequence; does not alter property/contract revision. |
| `work.complete` | `work_revision`, `execution_contract_revision` | Requires accepted required outputs/checks or an explicit authorized human non-artifact note. |
| `work.delete` | `work_revision`, `execution_contract_revision`, `discussion_sequence` | Tombstones the Work and fences active runs without deleting historical comments. |

### Reserved T05b decoder shape

The source-only `stead-product-codec` decoder and its native tests implement the
following closed shape for review. They are not yet a registered native test
suite, activated route, supported saved format or qualified release capability.
No command/3 shape changes. The envelope has exactly `protocol`, `request_id`,
`project_id`, `resource_id`, `authority_epoch`, `operation`, `expected`, `payload`.
The protocol is `stead.command/4`; all IDs are canonical UUIDs and all numeric
fields are canonical unsigned 64-bit decimal strings. Epoch and existing Work/
contract revisions must be positive; creation revisions and a first discussion
sequence are zero. Unknown operations, fields and combinations fail closed.

Payloads are full replacements of their named section, not partial patches:

| Operation | Exact payload fields |
| --- | --- |
| `work.create` | All property and contract fields below. |
| `work.update-properties` | `type`, `status`, `priority`, `owner_principal_id`, `worker_principal_id`, `blocked_reason` |
| `work.update-contract` | `title`, `description`, `acceptance_criteria`, `required_outcomes` |
| `work.resolve-legacy-blocked` | `status`, `blocked_reason` (unfinished status only) |
| `work.resolve-legacy-assignee` | `owner_principal_id`, `worker_principal_id` (both may be empty) |
| `work.comment` | `body` |
| `work.complete` | `basis`, `note` |
| `work.delete` | Empty object. |

Type and priority retain their existing enumerations. Authored states are
`backlog`, `todo`, `in_progress`, `in_review`, `done`, `canceled`. Creation cannot
start Done. Property updates may carry Done so an already complete Work item
can change priority or owner without reopening. The final reducer must reject
any transition **into** Done except through `work.complete`, and preserve the
valid completion basis when Done is retained with an unchanged contract.
Blocked is a nonblank reason on unfinished Work, never a status; Done and
Canceled cannot carry a blocking reason. Legacy blocked disposition and legacy
completion basis are migration-owned and cannot be authored through this codec.
Resolution uses `work.resolve-legacy-blocked`; it does not erase the legacy
record, and an unrelated property edit cannot silently resolve it.
Owner/worker are UUIDs or empty; owner kind, current eligibility and any explicit
steward inheritance are final authorization checks, not assertions from a client.
Legacy assignee IDs and available display/provenance stay explicitly identified
as legacy assignments. Migration does not silently make them a new accountable
human owner or worker. Autonomous dispatch requires resolved human accountability
or explicit, visible steward inheritance. A contract edit on Done is rejected
unless it is an exact no-op; changing that goal requires an explicit reopen.
Legacy assignment resolution uses its dedicated operation and the property CAS.
Ordinary property edits do not resolve a blank-to-blank assignment and cannot
change owner/worker while that legacy assignment remains unresolved. Explicit
clearing to unassigned preserves original assignment provenance and changes only
the property revision. New resolution requests after resolution are rejected;
an exact retry of the accepted request remains idempotent under current access.

`required_outcomes` is an object of at most 16 stable outcome UUIDs, each mapping
to one closed desired target. It does not claim that an output already exists:

| Kind | Exact target fields in addition to `kind` |
| --- | --- |
| `document` | `project_id`, `collection_id`, `document_id`, `expected_revision`, `base_markdown_sha256` |
| `code` | `project_id`, `repository_id`, `target_ref`, `base_oid` |
| `completion-note` | `project_id`, `work_id`, `expected_revision` |

Every target project matches the command project; a completion note names the
source Work. Target identities must be distinct across outcome IDs: a Doc's
project/collection/document, a Code branch's project/repository/ref, or the
completion note's project/Work. Different expected revisions do not create
different targets. This prevents one acceptance from making a duplicate required
output permanently stale. Doc revision zero requires an empty prior digest; a positive
revision requires a 64-character lowercase SHA-256. Code targets use a bounded
valid branch ref and exact 40-character base OID. The produced Doc revision/
digest or Code head belongs to the later Change; it is not guessed in the Work
requirement. Existence, collection/repository association and access remain
authoritative reducer checks.
The initial reserved reducer profile admits required output targets only in
shared Doc collections belonging to the Work's project. It checks current
collection write access, nonexistence for revision zero, or the exact existing
revision before invoking the trusted Markdown digest resolver. A private
collection is refused even when the Work author owns it; exact contracts can
then be read by project members without exposing private target references or
counts. Private context and drafts remain separately scoped, with existing
explicit publication unchanged. Code and completion-note targets are reserved
decoder shapes and fail closed in this reducer until their adapters qualify.

Completion basis is `accepted-outcomes` with an empty note, or `human-note` with
a nonblank bounded note. The latter must be rejected by the final reducer when
any required outcomes exist; it neither proves a human actor nor bypasses
required acceptance/checks. An empty required-outcome set needs the explicit
authorized human non-artifact completion path.

The decoder permits at most four object levels, 16 keys per object and 65,536
request bytes; duplicate keys, arrays and non-string scalars are rejected.
Title retains the existing 800-byte/200-character bound; description and
acceptance criteria allow 8,192 bytes each. Comment, completion note and blocking
reason use the existing nonblank 2,048-byte discussion-body rules. Canonical
bytes preserve string content and hash under `stead.command/4`. These are
decoding limits, not measured storage or concurrency support.

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

The current v10 product state owns Work metadata/comments, the principal
catalog, owner ledger and Doc Changes; it does not contain a repository catalog,
service ledger, Run state or model state. Those additions need their separately
versioned integration. The existing core Work map remains the sole current
source for Work content. A versioned v4 reducer receives core plus sidecar and commits
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

The original source-only T05c `stead-product-migrate` prototype first completes the
existing `stead-restore` validation, then processes 16 accepted events or 16
Work rows per step. It exposes a result only after the full conversion. Its
authored native tests alone are not execution evidence. The later prepared
disposable Home carrier above invokes this conversion while withholding
publication until validation completes. Exact predecessor conversion and v10
restore qualification remain separate from this design acceptance.

Conversion starts property/contract revisions at one. Exact changes to type,
status, priority or legacy assignment advance the imported property revision;
exact title/description changes advance the imported contract revision. Accepted
comments independently advance discussion sequence and retain the request,
legacy aggregate revision, actor, time, exact body and original receipt. The
derived comment list must match the embedded predecessor list exactly before
the live embedded copy is removed. Deleted Work and its comments remain tied to
the retained tombstone. Legacy command/3 never allowed reuse of an existing
Work UUID, including one retained after deletion.

The core Work map remains the single current source of authored content;
sidecar metadata holds counters, the `/2` contract digest, migration provenance
and completion basis. `/2` includes acceptance criteria and required outcomes;
`/1` and old agent-brief pin semantics remain frozen. Activation must advertise
the new capability explicitly and reject incompatible writes/briefs. This
prototype does not make old query/3 consumers understand the new Work fields.

The conversion retains the exact original journal, receipts and non-Work state.
A domain-separated migration fingerprint binds the journal count, per-project
heads, current registry digest and a chronological digest chain over every
accepted journal record. That chain also binds cross-project interleaving.
This is a fingerprint of the validated predecessor history; it is not a claim
that the converted current-state hash equals the predecessor hash. Current
registry display labels are marked as such; unavailable historical display
names are not invented. No existing event, Work or comment limit is increased.
The bounded predecessor registry is retained as immutable, hash-bound replay
input, never live authority. Later registry changes must join the same ordered
post-migration timeline as v3/v4 operations or be rejected during activation;
restoration cannot substitute today's registry for that historical boundary.

The separate source-only `stead-product-restore` packet reconstructs the legacy
prefix using the frozen registry and the existing restore's historical actor
checks, reruns conversion and requires its exact migration boundary. It then
replays every later v3/v4 event in the single recorded order, including retained
v4 rejections, and compares the complete core/sidecar pair. Sequence, preceding
digest, canonical event/body bytes, generated receipts and completion evidence
must agree. Its bounded steps expose no partial result. The original
`stead-restore` begin/step/result behavior remains unchanged; a separately tagged
history API exposes reconstructed predecessor state only after historical
validation finishes.

V4 replay requires a Home-internal historical evidence adapter. Missing evidence
rejects reconstruction. A recorded principal-kind string or today's principal
catalog cannot independently authorize a past operation; historical kinds,
target eligibility and accepted output proof must be established from retained
authority evidence. Native test adapters model a fixed synthetic declaration
interval and are not a real catalog/Change chronology. The initial replay
profile rejects any post-migration registry change until configuration events
have a qualified ordered representation. Sessions and cursors are not rebuilt.
These source tests remain unregistered and unexecuted; there is no v10 Home
activation or claim of recovery qualification from this packet alone.

### Reserved paired Work reducer

The source-only `stead-product-work` reducer returns core and sidecar state in
one pure transition. Its native tests remain unregistered/unexecuted until the
next hosted qualification packet. Current identity, project access, epoch and
the operation's independent CAS are checked before mutations; replay visibility
also requires current identity and access. Admitted v4 attempts retain their
command digest and original accepted/rejected receipt, so a confirmed conflict
cannot be retried under changed bytes and the same request ID. Admission denied
for missing current authority or exhausted capacity is not a retained attempt.

Ordinary capacity counts legacy accepted ordinary events plus retained v4
attempts against the existing 4,096 limit. Existing revocation reserves remain
available. Failure while constructing a bounded receipt/event or advancing a
generation rolls back both core and sidecar. Every accepted v3 operation after
migration must pass `apply-legacy`, which fences new legacy Work writes and
records other accepted operations in the same ordered timeline as v4 attempts.
Request identity is checked across both legacy and new receipt maps.

Completion records retain the actual completing principal, request, contract pin
and note or exact accepted-outcome evidence in both current metadata and the
immutable event. A current human owner or maintainer may use the non-artifact
note path; unassigned ordinary Work also allows a current human contributor.
Declared outcomes cannot be bypassed by a note. Unresolved legacy blocking or a
current blocking reason prevents completion. Completing already-Done Work under
a new request is rejected; priority/owner edits may retain valid Done evidence.

The kind, target and accepted-proof resolver gates are trusted Home internals,
never command fields. Unknown kinds/targets/proofs fail closed. The initial
assignment eligibility adapter still requires the current native member roster;
a catalog-only or service principal needs a reviewed current-membership adapter.
Pure native tests supply explicit trusted fixture gates; those gates do not
qualify real Doc/Code access, accepted checks or a live agent workflow.

Activation still requires product-aware reads/projections, mixed timeline replay
and v10 save/load/export/fingerprint validation, owner-configuration timeline
handling, current principal/target/proof adapters and actual Home routing. The
existing projection reads only the legacy journal and cannot discover newly
created v4 Work by itself. None of these serving or restore obligations is
satisfied merely by the pure reducer source.

### Ordered owner and principal administration

The reserved `stead.owner-command/1` envelope contains exactly `protocol`,
`request_id`, `operation`, `expected_revision`, and `payload`. Its four operations
are `home.configure`, `principal.declare`, `runtime.put`, and `definition.put`.
The actual Home sender must match the configured Home before even an exact retry
can recover a receipt. Commands use explicit revisions and immutable request
identity. Configuration reconciliation preserves original binding ownership,
revision high-water marks and previously declared principal kinds; new imported
identities remain unresolved until an explicit declaration.

Owner changes return a proposed core/catalog/ledger state and a typed record.
The new, unactivated `stead-product-history` wrapper appends that record to the
same product timeline as ordinary Work and legacy operations, or discards the
entire transition. There is no separate administrative journal. Rebuilding
starts from the frozen predecessor registry, reruns the actual migration, then
replays configuration and principal changes in their original order. It
regenerates receipts and exact event bytes before comparing the entire final
state; a recorded kind or today's catalog cannot authorize an earlier event.
Bounded reconstruction exposes no partial serving state. This is semantic
reconstruction of retained history, not a new cryptographic custody attestation.

Ordinary owner attempts share the Home's existing 4,096-event capacity. Once
that pool is full, only a successful strict authority reduction may use the
remaining security reserve: removing authority, shortening expiry or disabling
a known principal, without adding bindings, creator rights or new authority.
Owner security attempts are capped at 128 and also share the existing combined
2,048 maximum with project revocations. No extra guaranteed reserve is added.
Catalog deactivation must fence every active carrier, including Code, before
activation; fencing only the new Work reducer is insufficient.

The owner reducer's six arms and the integrated history cases are source-only.
They are outside the immutable 230-arm qualification candidate `f93a42a` and
must pass their own registered native run before Home integration can qualify.

### Reserved service actors and credential bindings

`stead-actor` separates exact existing native authentication from a verified
service context. A service has a stable principal and no invented ship. Its
scope pins Home, project, epoch, Work, optional shared Doc and a closed set of
Work read/comment and Doc read/propose operations. No wire field constructs a
verified actor.

`stead-service-bindings` preserves binding ownership, custody and revision
high-water marks, rejects parallel native/service mechanisms, and pins exact
runtime versions. A current authorized human may issue a credential only within
existing shared core grants. The raw bearer is returned once; persistent
records contain its hash, immutable scope, original issuer and grant evidence.
The carrier must enforce request identity before issuance. Lost issuance replies
require explicit rotation; replay cannot remint or reveal a saved secret.

Every effect rechecks current catalog, binding, native issuer, original grants,
resource scope and epoch. A replacement grant cannot revive old authority.
Credentials last at most fifteen minutes, clipped to all original authority
expiries. They also require the current ephemeral incarnation/book. Loading
retained descriptors never rebuilds a usable old bearer.

At ordinary capacity, strict revocation shares the existing global and owner
security remainder. Already revoked/inactive operations are unchanged and use
no reserve. Temporary catalog disablement does not prevent permanent revocation
of retained capability; expired or absent-incarnation credentials cannot spend
that reserve. Shape bounds do not replace ordered historical validation.

The four actor and eight binding arms are source-only and unexecuted. Their
hash-bound independent review
does not activate a carrier, service grant route, principal-aware roster,
ordered issuance history or saved state. Those integration steps remain required.

## T04/T12/T13/T14 incremental integration

### First exact Doc Change interface

The source-only `stead-doc-change-codec` reserves `stead.doc-change/1` with the
closed fields `protocol`, `request_id`, `project_id`, `work_id`, `change_id`,
`authority_epoch`, `expected_revision`, `operation`, and `payload`. The expected
revision is the Change's lifecycle revision. It is distinct from the immutable
result revision, Work execution revision and target Doc revision. No route or
mark exposes it yet. Six syntax/boundary arms remain uncompiled.

The reserved browser command codec mirrors these exact nine fields and seven
operations, preserving uint64 decimal strings, typed target pins and the
`stead.doc-change/1` command digest. Its ten host tests and source-derived
canonical vectors pass; they are not native execution. No read interface,
transport, session authority or live capability is provided by that codec.

`change.submit` carries an outcome ID, the exact document target already declared
by that Work, canonical Markdown bytes, a summary, execution-contract revision
and digest, and a run/attempt pair. Empty run plus attempt zero denotes a human
submission; the reducer must verify a current person. A nonempty run requires a
positive attempt and final native run/lease/contract authorization. Parsing the
pair grants no execution permission. First-profile submissions target shared
project Docs only; private publication remains a separate explicit operation.

`change.request-changes`, `change.approve`, `change.adopt`, `change.accept`,
`change.reject`, and `change.quarantine` all carry exact `result_revision`,
`result_digest`, and `note`. Requesting changes, adoption, rejection and quarantine
require a nonblank explanation. Approval and acceptance may omit the note. The
producer identity, original authentication, timestamp, checks, approval and lease
are derived by Home, never accepted as authored fields. Approval must be by a
currently authorized person other than the producer. Acceptance must recheck the
current reviewer, current accepting human, Work contract, target scope, exact
base revision/hash and required checks. An adoption records a new authorized
adopter while preserving the original producer, run and output bytes; it does
not issue a credential or allow another worker publication.

The proposed retained state keeps lifecycle and immutable output history
separate. A new result supersedes prior review/adoption eligibility without
deleting their provenance. Exact Markdown bodies use a bounded content-addressed
proposal store; they are not extra mutable copies of the accepted Doc. A result
digest binds project/Work/Change/result, outcome and exact target, Work contract,
producer/run/attempt, and output digest. Read access is checked against current
Work and shared target visibility before exposing either body, metadata or counts.

Doc acceptance must call `apply-legacy:stead-product-work`, returning the actual
canonical Doc write and accepted Change state in one pure transition. Its v3
Doc event and typed Change-accept event are a fixed adjacent pair committed
atomically. The latter binds the exact preceding write digest and receipt.
Recovery recognizes that pair before stepping, reruns acceptance once against
the preceding state and compares both generated records. Orphaned or forged
acceptance records fail closed. Ordinary historical direct saves remain direct
and do not gain fabricated Change provenance. No general transaction dispatcher
or Code board replacement is introduced.

The new `stead-doc-change` and `stead-doc-change-state` pure source implements
proposal bodies, immutable outputs, current review/adoption eligibility and the
paired acceptance preparation described above. Fourteen reducer/proof test arms and independent source review
are prepared; it is not registered, compiled or activated. Previous
review/adoption provenance remains in the single timeline when a newer output
clears current eligibility. Accepted Changes are immutable; quarantine fences
unaccepted output and does not retroactively undo a committed Doc.

Original producer authority retains the exact native binding/session and one
deterministically selected contributor or maintainer grant. Expiry of that
unchanged authority requires explicit adoption; revoked, replaced, disabled or
unknown authority quarantines unaccepted output. A later session or grant does
not silently extend an old result. A nonempty run requires a Home-internal
verified run/attempt resolver, which currently denies all such submissions.

The companion `stead-doc-change-proof` implements pure resolution of Work
completion from exact accepted outputs, current Doc revision/Markdown digest,
the actual native receipt and the retained save event. Authored proof strings
and an accepted status flag alone cannot complete Work. This resolver and the
compound-pair replay integration remain unqualified. No live Doc Change, run,
service credential, new saved envelope or UI capability is advertised yet.

### Reserved Doc Change reads

`stead-doc-change-query` and `stead-doc-change-views` implement source-only
`stead.doc-change-query/1` and `stead.doc-change-query-result/1`. The closed
request has ten fields: protocol, request_id, kind, project_id, work_id,
change_id, result_revision, result_digest, side and cursor. Kinds are `changes`
(per-Work metadata), `change` (current or exact result detail), `results`
(immutable result metadata), and `body` (one exact result's `before` or `after`).
An explicit result requires both its positive revision and exact digest.

Current native identity, active principal catalog, project/Work access and both
current and selected shared target visibility precede metadata, body and cursor
access. Metadata excludes Markdown, credentials and raw receipts. Detail exposes
current eligibility and the actual latest decision/feedback for the selected
result; historical results never inherit a newer result's approval or adoption.
Action advice is explanatory only: the reducer performs final authorization.

After-body bytes must match the immutable result's Markdown hash. Before-body
bytes come only from the exact scoped Doc save revision and hash in accepted
history. Revision zero is explicitly a new document; missing retained history
is explicitly unavailable. Neither current Doc text nor an unrelated blob can
substitute for that base. Pages contain at most twenty metadata rows or one
32 KiB body, within the existing 256 KiB response bound. Cursors share the
existing global/principal budget and bind actor, exact filter, epoch, generation
and expiry. The historical lookup is bounded by the existing 6,144-event limit.

Independent source review
binds seven prepared arms covering scope, exact bodies, revoked access,
feedback attribution, review authority and pagination. They have not been
compiled or executed; no route or capability advertises these reads yet. The
prepared browser client
checks the exact query/result/receipt shapes, body hashes and current session;
unknown command outcomes retain the original frozen request. TypeScript and
fifteen host cases pass, with no native or live-carrier claim. Its callable
transport defaults to absent capabilities and invents no endpoint.

### Reserved native run transitions

The source-only `stead-run-state` and `stead-run` packet implements typed,
bounded no-Code run transitions with immutable Work/context/Doc target pins,
current verified actors, finite budgets and at most three attempts. Claim and
clarification continuation return distinct candidate execution intents; durable
replay and restart return none. Unknown effects fence replacement until explicit
trusted reconciliation. Every proposed effect passes a payload-aware Home gate
before budget reservation; an eventual carrier must commit the actual ordinary
Work/Inbox/Doc effect and run transition together or discard both.

The contract hashes portable canonical grant and keyed Doc-target JSON; internal
target ordering is normalized for future decoding. Result references use
`result_revision` and `result_digest`, matching Doc Changes. Leases live in a
separate incarnation book, never exceed current actor/member/original-grant/run
expiry, and cannot survive restart or credential replacement silently. Strict
cancellation shares the existing security reserve rather than allocating a new
capacity pool. Finish verifies a declared outcome and trusted exact result; it
marks the run Submitted, never the Work Done.

Independent source review
binds ten prepared native arms. The expected portable digest was calculated on
the host; the Hoon assertion remains unexecuted. Trusted fixture callbacks are
not production adapters. The reserved run decoder
now admits eight closed command fields and thirteen typed operations, with
canonical nested contract/target/grant/budget/effect strings and six prepared,
uncompiled native arms. Its local 23-field contract parser keeps the 64 KiB
request bound without widening the shared parser. Decoding proves no authority.
The native run adapter
now derives authorization from current actual registry/catalog/Work/Doc state.
It requires an explicit current human Owner and the exact assigned native agent;
it does not infer a project steward. Context contains only the exact one to four
shared Doc target bases, Work purpose/criteria and immutable instructions/policy
pins, within 64 KiB and the issued input budget. Changed purpose, assignment or
Doc base blocks execution while current authorized history remains readable.
Finish requires the actual matching Doc submit command, closed accepted receipt,
Markdown hash and run attempt audit. Submitted results remain reviewable after
finish clears their lease; original expiry still needs explicit adoption.
Eight prepared native arms use the real pure reducers and remain uncompiled.
Service actors, provider effects, settlement and replacement reconciliation are
explicitly denied by this initial adapter. Shared history, saved-state migration,
Home routes, real executor and G3 remain required.

The reserved run reader
adds closed `stead.run-query/1` queries for a Work's runs or one exact run.
Current catalog, native membership, Work and shared-target visibility precede
metadata and cursor use. Nineteen preview fields and twenty-five detail fields
separate durable phase from observed lease state and advisory execution freshness;
neither observation authorizes execution. Details include the recorded question,
answer and exact submitted result, without grants, context bodies, provider data
or live lease secrets. Blank retained names remain blank rather than inventing
identity. Pages share the existing twenty-row, four-per-principal and sixty-four
global cursor limits; tokens bind current actor, scope, epoch and visible generation.
Eight additional source-reviewed native arms remain uncompiled and unregistered.
These reads require admitted, reconstructed state and expose no live route yet.

The reserved browser `RunReadClient` now checks that exact closed query/result
grammar, including canonical nested attempt/question/result records. It requires
an explicit read capability and an opaque current-session identity. A new list
refresh fences older successful and failed responses before they can replace
its one-use cursor; exact-detail reads remain independent. Source review,
TypeScript and fourteen host checks
passed. The native wire is unchanged; no Home endpoint, Run control, connected
screen or actual dispatch is activated by this reader.

The reserved `RunHistory` component now uses that reader for a Work-scoped list
and detail view, clarification history and the exact submitted Change route.
Its additive `supportsReads()` query lets it hide cached content immediately
on capability withdrawal. Session/scope/view generations fence late reads;
offline retention is explicitly stale, navigation is disabled, and Back focus
is scoped to the same Work. Issued time is Run requested; a terminal lease
does not assert process exit. Independent source review, scoped TypeScript and
twelve host checks
passed. Eight isolated real-browser synthetic cases
also passed, with desktop/320px visual inspection, keyboard and access-state
checks and complete cleanup. The component is not connected to Home or enabled
in the app.

The reserved human `RunControlClient` admits only `answer` and `cancel` from
`stead.run-command/1`. It checks canonical nested question/text, exact request
and digest, the short five-field rejection and full nine-field receipt. An
accepted answer remains Waiting; accepted cancellation records Canceled but
does not prove process exit or undo output. Prepared objects retain exact bytes
across an explicit retry, while changed sessions and invalidation fence replies.
Lost or malformed replies remain outcome unknown; no automatic retry occurs.
Independent source review, TypeScript and fourteen host checks
passed. No endpoint, capability advertisement, UI action or worker is activated.

### Remaining integrations

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

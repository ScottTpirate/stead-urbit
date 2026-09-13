# First-slice contracts — version 1

This is the integration-owned contract for the next increment, URB-040/050.
The freeze record binds exact files after independent review. It is not an
implementation, an owner merge approval, or a live authentication profile.
The URB-020 counter uses a separate synthetic probe protocol and does not
implement these contracts.

## Identity and authority

The canonical ontology in the retained [domain contract](../../reference/stead/docs/architecture/canonical-domain-model.md)
and [OWGP 0.1](../../reference/stead/specs/work-graph-profile/owgp-v0.1.md) remains the product vocabulary.
This first-slice subset uses Project, Work Item, Document and explicit principal
bindings; it does not delete the remaining entity types. Principal is the shared
identity interface for User, Agent and Service Principal, not a competing person
master. Organization and Team ownership cardinalities remain requirements for
product initialization. A repository/document container is
an access boundary, not a second project or document master. This slice starts
with project-scoped commands. Organization/Team knowledge containers remain a
preserved later scope, not documents silently moved into an unrelated project.
Organization/Team hierarchy is descriptive and supplies no grants. Readers,
contributors, maintainers and organization administrators are permission bundles,
never policy bypasses. No ship rank appears in the authorization contract.

Resource and principal IDs preserve the existing lowercase UUIDv7 format and
`urn:uuid:<id>` identity profile. The UUID is independent of ship, URL, sponsor,
username and organization hierarchy; resource kind is explicit context, never
inferred from a hostname. Generate IDs with an RFC 9562-conforming allocator using
cryptographic randomness, reject collisions, and preserve them through an
authorized migration of the same project. Request IDs use the same lexical UUIDv7
profile. Fixed test UUIDs are synthetic. An ID is not a secret or capability;
private project existence still requires authorization. Forks and transfers into
new governance/custody receive new IDs with authorized ancestry records rather
than silently assuming the source's access grants.

Exactly one home accepts project mutations. A directory record binds project ID,
home principal and native identity/origin, monotonically increasing authority
epoch, previous record digest, authorized change evidence and record version.
The initial epoch is `1`. Current epoch and home must agree at acceptance.
Directory lookup itself is authorized. No public enumeration is introduced.
Directory signatures, migration authority and disconnected-writer fencing are
deferred; an epoch field does not implement fencing.

Networking ship bindings are versioned records, separate from application
principal identity. Record authentication mechanism, strength, native life/rift
and delegation evidence when available. Recovery or ship control changes suspend
the old employment binding pending explicit rebinding. An unavailable historical
binding is not reconstructed from the current key. Fake fixtures map four native
senders to distinct synthetic principals by explicit harness configuration only.

## Requests and trusted context

`specs/urbit/command.schema.json` defines the external request. Every field is
required; unknown fields, duplicate JSON keys, invalid UTF-8/surrogates, non-string
numbers, unsupported versions and operations fail closed. Credentials travel in
the authenticated transport, never clone URLs or author fields. External requests
cannot supply an authenticated principal, policy decision or accepted timestamp.

The authoritative adapter constructs an internal context containing principal ID,
binding ID/revision, session or delegation ID, authentication mechanism/strength,
trusted receipt time, and independently resolved policy/context evidence. Native
sender identity comes from Gall's trusted bowl, not the request noun. Browser
context will come from a reviewed individual Stead session. Dojo, Lens, ship-owner
cookies and `+code` remain administration; none is the future employee API.

`request_id` identifies one principal's command in one project, independent of
sessions. Its durable lookup key is `(project_id, principal_id, request_id)`.
Reauthenticate and reevaluate current read/action authority before consulting or
returning an old result. Revocation yields the same opaque denial as an unknown
project; it must not reveal the stored receipt. The same ID and request digest
returns the original accepted receipt without appending another mutation, even
when its expected revision is now old. The same ID with a different digest is an
ID-reuse conflict only after authorization permits that disclosure. Distinct IDs
are distinct commands. Do not evict acceptance deduplication records silently;
their tombstones must survive supported retry windows, export and recovery.

Requests bind protocol version, project, target resource, operation, expected
resource revision, current authority epoch and payload. Revisions and epochs are
canonical unsigned decimal strings bounded by `2^64-1` (safe across JS/Hoon).
Zero revision means the named resource must not yet exist. Creation accepts zero;
edit requires the exact current positive revision. Each resource has its own
revision, so edits to different documents do not conflict merely because they
share a project. `project.create` initializes project content revision and policy
revision to `1` in one event. It records an explicit initial-owner maintainer
grant to the authenticated creator authorized by the parent organization's
create-project permission. The owning Team must exist in that organization;
guessed future project membership cannot authorize creation.
`policy.grant` and `policy.revoke` address `resource_id = project_id`, with the
operation selecting that project's **separate policy revision counter**. They
compare/increment policy revision, not project content revision. A
multi-resource command must specify every precondition in a later schema version;
version 1 supports a single target and cannot imply a transaction across targets.

## Limits and serialization

Protocol `stead.command/1` uses the bounded JSON profile below. This is a
documented Stead serialization, not a claim of RFC 8785 conformance or native
signature implementation. The host reference validator and checked-in vectors
are an executable specification; Hoon encoding parity is a gate for URB-040.

Parse at most 65,536 UTF-8 bytes; reject duplicate object keys before constructing
objects. A request has the closed schema's fixed ASCII keys. Values are strings,
objects, or the exact booleans permitted by a future version (none in version 1);
floats and numeric JSON values are not permitted. String values are Unicode scalar
sequences. Do not apply Unicode normalization: different scalar sequences are
different bytes. Reject NUL and CR in source Markdown; accepted source text uses
LF. Frontmatter is part of the source text, not an independent writable object.
Unsupported frontmatter syntax is rejected by the later document validator.

Canonical bytes use sorted object keys by their ASCII code points, no whitespace
outside strings, and UTF-8 without BOM. Escape quotation marks and backslashes,
use `\b`, `\f`, `\n`, `\r`, `\t` for those controls and lowercase `\u00xx` for
other U+0000–U+001F controls; do not escape `/` or other Unicode scalars. All keys
are ASCII and no JSON numbers are present, avoiding number/UTF-16 ordering
ambiguities. The digest is SHA-256 of ASCII `stead.command/1`, a zero byte, then
these canonical bytes. It is a content binding, not a signature or proof of a
person's intent. Credential bytes and transport wrappers are excluded; principal
scope is part of the lookup key and the eventual receipt's authenticated record.

Titles are 1–200 scalars, at most 800 UTF-8 bytes. Work descriptions are at most
8,192 UTF-8 bytes; a document save is at most 32,768 UTF-8 bytes of Markdown plus
frontmatter. No attachments, binary Git packs, execution commands or arbitrary
extension fields fit this envelope. Later import/blob profiles must define their
own quarantines, expansion/graph limits, retention and replaceable storage.

The final document acceptance validator resolves `container_id` and requires that
it belongs to this project, home and compatible handling boundary. Canonical
frontmatter `id` must equal `resource_id`; its type/state must use the retained
document enums and project/container references must agree. A save cannot move
an existing document to another container, lower handling restrictions or publish
a private draft by editing frontmatter. New documents begin as private drafts in
a container explicitly restricted to that principal. A later separately authorized
publication operation must validate recipient/custody policy and selected content;
that operation is not in v1. If a draft object would be reachable through a broader
clone, reject the save or use a separate compatible container. These are required
final native checks, not claims that the envelope parser validates Markdown or
provides draft storage today.

## Policy decisions

Only `stead-home` accepts a mutation and appends its journal record. Pure Hoon
libraries may compute transitions/policy; they have no independent writable state
or effect authority. All protected routes use the same final decision boundary:
HTTP, native messages, Git, exports, subscriptions and future replicas.

The decision is the intersection of five independently evidenced dimensions:

1. Current membership/explicit relationship grants.
2. Information-flow/handling policy for sender, recipient and custody boundary.
3. Session/delegation scope, expiry, revocation and current delegator authority.
4. The exact action and resource/container scope.
5. Runtime/context requirements, including supported profile and authentication.

Each dimension is `allow`, `deny`, `missing`, `expired`, `contradictory` or
`unsupported`. Every dimension must be present and `allow`. Explicit denies win;
every other incomplete state denies. Unknown dimensions or values deny. A role,
home ship, common sponsor or team parent never fills a missing dimension. An
organization administrator still needs handling and context evidence. Agents
receive the intersection of current delegator permissions and explicit task,
project, operation and expiry restrictions. Clarification, proposing a change,
merging and release approval are separate operations; no implicit escalation.

The version-1 bundles below contribute only to the membership/action dimensions;
all five dimensions still must allow. Listed reads remain permission-checked even
though v1's mutation schema does not specify the future read transport.

| Role and scope | Allowed operations before other policy gates | Grant/revoke ceiling |
|---|---|---|
| Reader, project | project/work/document read | None |
| Contributor, project | Reader operations; work.create, work.update, document.save | None |
| Maintainer, project | Contributor operations; policy.grant, policy.revoke | Reader or contributor grants within this project |
| Organization administrator, organization | Reader/contributor operations in explicitly granted projects; project.create in this organization; project policy.grant/revoke | Reader, contributor or maintainer within this organization |

`policy.grant` is project-scoped and cannot grant organization administrator.
Grant IDs are create-only and globally collision-checked against retained IDs.
A grant operation cannot overwrite, downgrade or refresh an existing grant.
Revoked grant IDs remain non-reusable tombstones. A role change requires an
authorized revoke of the old grant followed by a fresh grant ID; both operations
recheck the current actor ceiling and policy revision.
Organization administrators come from a separately authorized organization binding
(only explicit fixture configuration in the initial native profile). Revoke checks
the existing grant's role and project at final acceptance; a lower role cannot
revoke an administrator's higher grant by guessing its ID. Grant expiry must be
future at acceptance, cannot exceed delegator/session expiry, and never refreshes
revoked authority. No grant may widen a delegation's allowed operations, resource
scope or handling/custody policy. Organization administrators receive no implied
membership in every project and no handling override. Grant/revoke capability
does not authorize reading the protected resource's contents. Role changes take
effect on every acceptance and retry; expired/missing grants are not role evidence.

The policy result binds decision version, policy revision, project, resource,
operation, principal/binding, evaluated epoch/time and the evidence references.
Private denial reasons stay in authorized audit views. An outsider receives an
opaque `denied_or_not_found` response with no project titles, counts, relations,
revision, epoch, redirect or notification. Request parsing errors may reveal the
public protocol only. Authorize searches and notifications before producing
counts/snippets; filtered rows followed by unfiltered totals are prohibited.

## Acceptance and journal

`queued` and local draft are client states; `received` is transport receipt;
`accepted` is a durable home decision; `replicated` is a separate selected-replica
observation; `rejected` is an authoritative refusal. A transport ACK never becomes
Saved. There is no automatically replicated status in the first slice.

At the final event, validate bounded input, derive trusted principal, check current
policy/epoch and retry authority, handle idempotence, check resource preconditions,
validate staged canonical content, then atomically advance state and append the
application journal plus durable receipt. Save the principal's original request
digest and the resulting revision. For document saves, required Git objects and
the commit must already be admitted in the same durable outcome before the
document pointer and receipt can advance. Failure leaves the old pointer/ref;
no independent Markdown master is introduced. If native Git admission is not yet
available, a later Work/Docs increment must label document saves unimplemented,
not substitute a second authoritative text store.

The journal record includes schema/version, monotonically increasing project
sequence, prior event digest, request digest/ID, principal and authentication
evidence references, policy revision/decision, epoch, resource old/new revision,
accepted content/Git OIDs, and trusted acceptance time. This portable journal is
separate from Vere's event log. Its format/signature and retention implementation
are later gates; no runtime-log hash is advertised as a portable human signature.

Git commits remain exact Git bytes with original SHA-1 OIDs. Pusher identity is a
separate accepted record. Git ref acceptance compares old OID and current branch
policy and rechecks credentials after staging, including revocation during upload.
No independently writable engine route may bypass that decision. A cloneable
container must have a compatible access/handling scope for every reachable object.

Derived indexes and notification views are rebuildable. Notification failure does
not roll back accepted work. External effects receive a durable, authorized effect
ID after the decision and an idempotent executor. Replaying history only reconstructs
state from recorded inputs/results; it does not run builds, call an LLM, send a
message, buy anything or deploy. A restored command still rechecks current access.

## Implementation and approval gates

The JSON validator/corpus tests syntax, canonical digests and a reference policy
decision table. It cannot establish native authorization, transaction atomicity,
UI behavior, Git admission, journal durability or cryptographic identity continuity.
The next increment must implement independent Hoon conformance against these
vectors, four-principal denials, duplicate/revoked retry cases, per-resource stale
revisions and restart tests. Browser sessions and Git integration retain their
later gates. Final PR acceptance and any deployment remain the owner's decision.

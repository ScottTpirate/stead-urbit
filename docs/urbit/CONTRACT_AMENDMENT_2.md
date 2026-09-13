# Minimum native privacy and exhaustion amendment — version 2

Integration decision, September 13, 2026. This amends the version-1 freeze for
issues #6–#8 and #24. The original `contract-freeze.json`, its nine files, old
native corpus, accepted records and execution reports remain unchanged. This is
a development interface freeze, not native qualification or permission to merge.
Independent design review: `/root/hoon_review`; adversarial owner: `/root/qa_review`.

## Identity is a complete scoped reference

UUIDv7 remains the lexical local identifier. A work reference is
`(project_id, work, local_id)`, a document reference is
`(project_id, document, container_id, local_id)`, and a grant reference is
`(project_id, grant, local_id)`. These tuples, including their kind and parent
scope, are the stable identity; a bare local UUID is no longer a globally unique
resource identity. They contain no host, URL, rank or sponsor. There is no global
availability check or fallback search for work, document or grant creation.
The same local UUID in another kind/project/container cannot block creation.
Within the authorized scope, existing IDs still obey CAS and retained tombstones.
Document filenames/frontmatter retain the local UUID; the container manifest
supplies its complete scope. Moving content to another container creates a new
scoped identity through a future explicit publication/transfer operation.

This first profile still has one explicitly configured organization. Its
organization policy-administration capability explicitly includes project
existence and allocation metadata within that organization, after the same
handling/authentication/context checks. It confers no project content access.
Other principals and unsupported organization inputs fail before project
allocation lookup. Project IDs themselves remain stable UUIDs in this profile.
Enabling a second organization requires separately scoped project allocation;
this amendment does not authorize a second organization over a global caller
chosen project namespace. This is a Phase 2A prerequisite, not a reason to delay
the current scoped Work/Docs fix.

## Versioned wire and receipt projection

`stead.command/2` retains the eight closed command fields and bounds of v1.
Canonical serialization is unchanged; the SHA-256 domain is the command's
literal protocol plus a zero byte. `stead-command-2` is the new mutation mark.
Result/read paths use `/v2`. Document reads include container before local ID.
Receipt recovery includes container (project ID for non-document operations),
resource, operation and request ID. Every consumer must carry full typed scope;
v1 read paths have no ambiguous fallback. The single-shot transport and limits
otherwise remain unchanged, with lazy expiry on the next relevant event.
The closed receipt field names, resource-kind vocabulary and mark/version matrix
are in `specs/urbit/v2/native-api.json`. Mark 2 accepts command 2 and replay-only
command 1; legacy mark 1 accepts replay-only command 1. Every response uses mark
2 and a v2 path. An authorized unaccepted legacy command returns
`unsupported_version` after current authority/epoch checks, without a mutation.

Public `stead.receipt/2` includes protocol, status, request ID, command digest,
project ID, resource kind, container ID (empty for non-documents), local resource
ID, resulting resource revision, authority epoch, principal/binding,
authentication mechanism/strength, acceptance time and Git commit OID.
It includes **no journal sequence, journal digest or project policy counter**.
The resource revision and request ID suffice to identify this accepted result.
Policy commands use their policy resource revision; only an authorized policy
actor receives it. Ordinary project reads do not expose a policy counter.
Exports expose only the selected authorized container's history and objects.

The full application journal stays internal to trusted administration, including
its original per-project sequence, previous digest, decision policy revision and
`stead.journal/1` codec. Existing stored receipt bytes and journal bytes are not
rewritten. Public responses, retries and receipt recovery all use the same v2
projection after current authorization. A projected v1 receipt retains its
original command digest, timestamp and Git OID. V1 commands may only recover an
already accepted identical command, after current scope/epoch/authority checks;
they cannot create new v1 accepted work. Old clients require an explicit upgrade.
Reusing a v1 request ID with new v2 bytes is a different payload, not migration.

## Bounded security capacity

At most 4,096 ordinary accepted commands are retained. Each of at most 16
projects additionally reserves 128 accepted `policy.revoke` records and receipts.
Maximum total journal/receipts is therefore 6,144. Ordinary work and grant
creation cannot consume that reserve. Revocation uses all the ordinary current
authentication, profile, grant ceiling, epoch, duplicate and CAS checks. It has
no generic administrator bypass. Every grant remains a retained create-only
tombstone, at most 128 per project, and may be revoked once. Consequently a
project's reserve is sufficient to revoke every retained grant, independently of
activity in other projects. Duplicates/rejections consume no capacity.

When a project's 128-record security reserve is exhausted, or its policy counter
cannot advance, that project is closed to protected reads, mutations and receipt
recovery. The condition is derived from persisted accepted history/counters;
it does not erase audit history or pretend a rejected revoke committed. The last
valid revoke's receipt is authorized at its pre-decision linearization point;
all later requests observe closure. Recovery requires a separately reviewed
bounded format/retention migration, not an unaudited reopening command.
Current ordinary exhaustion does not disable another project's revocations.

Other existing resource bounds remain unchanged: 16 projects, 128 works/project,
128 retained grants/project, 32 documents/container, 128 commits/container,
8,388,608 Git object bytes, 65,536 request bytes and 262,144 response bytes.
Boundary refusal admits no objects, refs, resource pointers, receipt or journal.
Resource-limit and timing side channels of a shared physical runtime are not a
constant-time or independent-custody guarantee.

## Stored format and evidence

`[%stead-home %2 state]` has explicit conversion from the actual product v1 mold:
document keys gain their stored container; grant keys gain their stored project.
Bindings, projects, canonical Git bytes/OIDs, reachability, accepted receipt bytes
and journal history are preserved exactly. No inferred grants or new accepted
events are introduced. Validate the predecessor and bounded counters before
admitting it. Counter/future/unsupported states fail; current save/load, actual
predecessor migration, graceful process restart and abrupt-crash recovery remain
separate assertions. V1 administrative test snapshots are not employee APIs.

Independent QA must reproduce both old disclosure cases and the old revocation
exhaustion against provenance-bound predecessor transitions, then verify the
amended behavior. Capacity fixtures use bounded batches of real transitions,
not hand-set counters. Actual native observer events must support duct isolation,
leave/cancel, lazy expiry, quotas, missing/late responses and unavailable home.
An ended duct stays ended; a fresh authorized registration may retry/recover an
old receipt. ACK, NACK, timeout, partial or absent output never becomes Saved.

The 25 old skipped assertions remain in their historical reports. A new current
gate maps each to actual native evidence, exact-source review, or a narrow
no-effect/not-applicable disposition where that subsystem is absent. Missing
required current-phase evidence fails the gate. Source review is not a native
test; an absent effect subsystem is not proof of a future replay executor.

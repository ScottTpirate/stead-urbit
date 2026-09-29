# Public native protocol 3

This contract accompanies the exported codecs and `stead-sdk-call` sample.
The configured home is `%stead-home`. Gall's actual sender and the current
operator binding establish the actor. No payload actor, role or ship-owner
cookie confers project permissions. This alpha supports the declared pinned
kernel/runtime and local fake profile; it does not certify live identity custody.

## Carrier and correlation

Use marks `%stead-command-3`, `%stead-query-3` and `%stead-updates-3`, carrying
UTF-8 JSON as a cord. The sample handles the watch and poke. A manual consumer
must first watch:

```text
/v3/result/~SENDER/BINDING_UUID/BINDING_REVISION/REQUEST_UUID/DIGEST
```

`DIGEST` is lowercase SHA-256 of the corresponding protocol name, one NUL byte,
then canonical JSON. Use the exported `canonical` and `hash` functions;
canonicalization preserves string bytes, object keys sort by UTF-8 bytes and
insignificant JSON whitespace disappears. The domain comes from the versioned
carrier, including when testing an unsupported envelope version. The sender
must match the actual ship, and binding ID/revision must be current. Watches
are reserved for one actor and one request/digest, bounded per principal and
globally, and expire after 60 seconds.

The result uses `%stead-result-3`; one ACK, one fact and one kick may arrive in
any order. Collect all three once, using `stead-delivery`. A duplicate,
unexpected mark, failed ACK, missing result or timeout is unconfirmed. ACK or
kick alone never means saved. The sample has a 55-second timeout and returns
the JSON in `%stead-sdk-result`, or a bounded `stead.sdk-error/1` outcome.
See the README for platform errors outside its callback boundary.

JSON must have exactly the declared fields. Numbers below are canonical
unsigned decimal **strings**, at most uint64, with no leading zero except `0`.
IDs are lowercase UUIDv7 with the RFC variant. Empty scope fields are `""`.
No NUL or CR is accepted in prose. Commands and queries are at most 65,536 UTF-8 bytes;
updates at most 2,048 bytes; results at most 262,144 bytes. Decode failure does
not authorize a mutation. Unknown/legacy carriers are outside this API.
Authenticated callers can query `capabilities` for supported versions. An
unsupported envelope version on a v3 carrier returns a request/digest-bound
`unsupported_version`; legacy carrier rejection is a transport failure, not
evidence from which to guess a remote protocol version.

## Commands

```json
{
  "protocol": "stead.command/3",
  "request_id": "019939ba-4000-7000-8000-000000000111",
  "project_id": "019939ba-4000-7000-8000-000000000001",
  "resource_id": "019939ba-4000-7000-8000-000000000112",
  "expected_revision": "0",
  "authority_epoch": "1",
  "operation": "work.create",
  "payload": {
    "title": "Independent client task",
    "description": "Public synthetic content",
    "type": "task",
    "status": "todo",
    "priority": "medium"
  }
}
```

Generate your own request/resource IDs; the example IDs grant nothing. Obtain
project scope, current epoch and revision through authorized queries.
`expected_revision` is zero for creation and the actual resource revision for
edits. The epoch must be positive and current. Preserve the original canonical
command and request ID across an uncertain result. A different body under the
same request is rejected; retrying an accepted original is idempotent.

| Operation | Exact payload fields | Scope and expected revision |
| --- | --- | --- |
| `project.create` | `organization_id`, `owning_team_id`, `title`, `project_key`, `preset` | Explicit project creator; project = resource; revision 0; preset `general` |
| `work.create`, `work.update` | `title`, `description`, `type`, `status`, `priority` | Contributor or maintainer; 0 for create, positive for update |
| `work.delete` | none | Contributor or maintainer; positive revision |
| `container.create` | `title`, `visibility` | Contributor or maintainer for private; maintainer for shared; revision 0 |
| `document.save` | `container_id`, `markdown` | Current container write scope; 0 for new, current revision for edit |
| `document.delete` | `container_id`, `expected_head` | Current write scope and exact 40-hex Git head; positive revision |
| `document.publish` | `source_project_id`, `source_container_id`, `source_document_id`, `source_revision`, `source_head`, `container_id`, `expected_head` | Same project; caller's own private source into writable shared destination; source revision/head exact; destination resource new, revision 0 |
| `relation.create` | `type`, `source_project_id`, `source_kind`, `source_container_id`, `source_id`, `target_project_id`, `target_kind`, `target_container_id`, `target_id` | Both authorized endpoints in this project; revision 0 |
| `relation.delete` | none | Current authority over relation and endpoints; positive revision |
| `policy.grant` | `grant_id`, `principal_id`, `role`, `expires_at_ms` | Project maintainer; project = resource; current positive policy revision |
| `policy.revoke` | `grant_id` | Project maintainer; project = resource; current positive policy revision |

Titles have 1–200 Unicode code points, at most 800 UTF-8 bytes and no control
bytes below space. Work description is at most 8,192 bytes; Markdown at most
32,768 bytes. Project keys are 2–10 uppercase letters/digits starting with a
letter. Work types are `deliverable`, `task`, `problem`; states `backlog`,
`todo`, `in_progress`, `blocked`, `done`, `canceled`; priorities `none`, `low`,
`medium`, `high`, `urgent`. Visibility is `private` or `shared`. Grant roles are
`reader`, `contributor`, `maintainer`, with a positive absolute expiry.
Relation types are `related_to`, `blocks` (Work to Work), or `documents`
(document to Work); document endpoints require their collection ID.

Canonical Markdown begins with this exact LF-delimited header, followed by the
body. Substitute the resource UUID and use `draft` for private collections or
`published` for shared collections; the final header line has a trailing LF:

```text
---
id: <resource UUID>
type: page
state: draft
---
```

Saving preserves ordinary Git blob/tree/commit identities; it
does not normalize source or identity bytes to manufacture an OID. Publishing
does not move the private collection or copy other pages. It preserves the
body while replacing the header's destination UUID and state. For a new empty
destination collection, `expected_head` is empty; otherwise it is the exact
current destination head. Deletion and publication head fields use full
lowercase SHA-1 Git OIDs.

## Queries

```json
{"protocol":"stead.query/3","request_id":"019939ba-4000-7000-8000-000000000113","kind":"work","project_id":"019939ba-4000-7000-8000-000000000001","container_id":"","resource_id":"","search":"","cursor":""}
```

All eight fields are required. `identity`, `capabilities` and `projects` use empty scope fields.
Project kinds are `project`, `work`, `containers`, `documents`, `document`,
`relations`, `search`, `activity`, `inbox`, `receipt`. `work` optionally selects
one resource. `documents` requires a collection; `document` also requires a
resource. `search` accepts at most 128 bytes. Other unused fields remain empty.
For `receipt`, `resource_id` is your original request ID and `container_id` is
the original command's container, when applicable. Recovery requires current
authorized scope and the original principal; an empty result is unconfirmed.

Successful replies are `stead.query-result/3`, status `read`, with request ID,
kind, project/container/resource IDs, `authority_epoch`, `generation`, `cursor`
and a `rows` object. Rows contain string fields and opaque row keys. Do not
infer identity or ordering from row keys. Page size is 20. Follow only a
returned cursor with the same query scope. Cursors are actor/purpose-bound,
expire, and reject replay or stale generation; restart from a fresh read on
rejection. Never merge unrelated private scopes or invent missing rows.

One pagination walk may be active for an exact actor at a time. A successful
fresh read with more than 20 rows supersedes that actor's earlier query cursors.
Metadata and single-page reads do not supersede them, and update cursors are
unaffected. Query and update cursors share a budget of four per principal and
64 globally.

List and search projections are previews. Before editing Work, read `work`
with its `resource_id`: list/search descriptions are truncated to 160 Unicode
code points, while this single-resource read supplies the full description.
Before editing Docs, read `document` with its collection and resource IDs;
`documents` and search rows omit Markdown. Never save a preview as the full body.

All row fields below are strings. Resource rows use `kind`, `resource_id`,
`container_id` and `resource_revision` unless stated otherwise. IDs and revisions
come from the row, never from parsing the opaque row key.

| Row | Additional fields or exact metadata shape |
| --- | --- |
| Identity | `principal_id`, `identity_ship`, `binding_id`, `binding_revision`, `session_audit_id`, `display_name`, `organization_id`, `team_id`, `home`, `can_create` (`yes` or `no`); no resource fields |
| Capabilities | `protocol`, `profile`, `commands`, `queries`, `updates`, `authentication`, `max_request_bytes`, `max_response_bytes`, `page_size`, `runtime`; no resource fields |
| Project | `project_id`, `title`, `project_key`, `preset`, `authority_epoch`, `role`; maintainer only: `policy_revision`; no `container_id` |
| Work | `title`, `description`, `type`, `status`, `priority`, `snippet`; empty `container_id`; full description only on single-resource read |
| Collection | `title`, `visibility`, `container_head`; `kind=container`, collection ID in both ID fields |
| Document | `container_head`, `title`, `snippet`, `visibility`; exact `markdown` only on `document` read |
| Relation | `title` plus every `relation.create` payload field; empty `container_id` |
| Activity / Inbox | Exactly `kind` (`activity`), `resource_id`, `container_id`, `operation`, `title` (the operation), `request_id`, `principal_id`, `accepted_at_ms`; authorized projections, not command receipts; no resource revision |
| Receipt | Exact `stead.receipt/3` fields listed under Validate outcomes; validate against the original command |

## Updates

Every envelope has `protocol`, `request_id`, `action`, `watch_id`, `cursor`,
`kind`, `project_id`, `resource_id`, `container_id`, `search`.
Use `stead.updates/3`. `open` uses query scope with empty watch/cursor; `resume`
uses query scope, an empty `watch_id` and a returned cursor. Identity, capabilities and receipt scopes cannot be
watched. `poll` sends only the watch/cursor, with scope fields empty. `cancel`
sends only the watch, with cursor/scope empty. Every call has a fresh request ID.

Open before reading the initial snapshot, then poll. Success protocol is
`stead.update-result/3`; status is `watching`, `updated`, `resumed`, `cancelled`
or `refresh_required`. The exact fields are `protocol`, `status`, `request_id`,
`watch_id`, `cursor`, `generation` and `rows`. All except `rows` are strings.
Bind request ID, watch, cursor and generation. Rows have consecutive decimal
keys `0` through `n-1`, and each contains exactly `sequence` (a positive uint64
decimal string) and `generation` (64 lowercase hexadecimal characters).
Sequences are contiguous; the final row's generation equals the response's
generation. Empty polls keep the generation. Every successful poll rotates its
one-use cursor. `open` and `resume` return no rows; a resumed suffix arrives on
the next poll. Terminal `cancelled` and `refresh_required` replies have empty
cursor, generation and rows.

Invalidations carry no business content or receipts. Read current authorized
state after invalidation. Never reorder or apply one scope's updates to another.
Replayed cursors fail. Cancel is idempotent; cancellation does not submit mutations.

The service limits four handles per principal, 64 globally, a 16-row watch
queue and a 64-row retained scope window. A successful poll renews the handle
lease to the earlier of actor expiry or five minutes after that poll.
Overflow retires the handle with a content-free `refresh_required`. Revocation,
expiry, bootstrap or restart invalidates access and queued data. Unrelated
private activity must not be inferred from visible counters or cursor changes.

## Validate outcomes

An accepted command is a `stead.receipt/3` object with exactly these string
fields: `protocol`, `status`, `request_id`, `canonical_sha256`, `project_id`,
`resource_id`, `resource_kind`, `container_id`, `resource_revision`,
`authority_epoch`, `operation`, `principal_id`, `binding_id`,
`binding_revision`, `identity_ship`, `authentication`,
`authentication_strength`, `session_audit_id`, `runtime`, `accepted_at_ms`,
`git_commit_oid`.

Require status `accepted`; exact request/digest/scope/operation/epoch; resource
revision = expected revision + 1; and the operator-confirmed principal/binding
and actual sender. Native authentication is `native-sender/1`, strength
`native-sender`, with empty session audit ID. This local profile records
`isolated-fake`. Accepted time is a positive uint64 string. Document receipts
have a full Git OID; other kinds use an empty OID. Receipt/2 helpers do not
validate this shape.

A correlated command rejection uses `stead.result/3`, status `rejected`,
request ID, canonical digest and a bounded error code. Other failures use
bounded error results or a native transport NACK. Keep stale revision, denied
scope, malformed input, capacity, unavailable session and unconfirmed transport
distinct. Neither a structurally valid response nor a historical accepted
receipt establishes new authority or authorizes another mutation.

# Minimum native implementation profile

This is the URB-030 supplement needed by URB-040/050, under CONTRACTS.md. It does not
activate the broader ecosystem roadmap. The original counter remains a separate
smoke fixture. Product tests install one `stead-home` from `native/core/desk` into
fresh stopped fake seeds; only one version owns a home at a time.

## Fixture identity and context

`specs/urbit/native-fixture.json` defines the explicit Organization, Team, principal,
ship binding, private-container and supported-profile inputs. No application
principal ID is computed from rank, sponsorship or payload author text. The
organization administration binding belongs to the fixture's home administration
service; it is not an independently signed human action. The other three named
fake senders are distinct synthetic principals with no implicit project grant.
Project creation requires the explicit organization capability and records a
creator maintainer grant. The normal command still creates the project.

The fixture is installed only through a home-local, versioned initialization
command on disposable `~zod`, with no current project state. Reserved containers
become usable only when their named project exists and their owner has current
project access. Their owner/custody cannot be changed by document.save. This
fixture supplies container initialization pending a reviewed general container
management API; no implicit container creation or grant is inferred from a UUID.

At every protected event, derive `src.bowl` and resolve the current binding;
require unexpired supported authentication/context, explicit applicable grant and
resource scope, and the project's compatible handling/custody profile. All four
profile dimensions must be present and exact. Unknown, absent, stale, unsupported
or contradictory profile evidence denies; the caller cannot supply `allow` flags.
These four fixture fields provide authentication/runtime/handling evidence to the
five policy dimensions; they never substitute for membership, action or scope.
Service/person fixture bindings are explicit. Agent delegation, live identities,
rotated keys, browser credentials and other unsupported mechanisms deny rather
than inheriting a person's rights. An owner-local fixture control can invalidate
bindings/context for negative tests; it is not a business bypass or employee API.

## Commands, reads and receipts

The native mutation mark carries **raw bounded UTF-8 JSON bytes**, then the home
validates the frozen command schema. It must preserve duplicate decoded keys until
rejection and match the six canonical byte/digest vectors. The native JSON parser's
ordinary map conversion is insufficient: duplicate keys disappear there. Use a
closed strings-and-objects parser with maximum nesting two, matching v1, and the
specified ASCII-key sorting/escapes. Do not use native map iteration as canonical
serialization. JSON content has no caller-authenticated identity fields.

Native fixture reads use one-shot, authenticated Gall watches with explicit
project/resource identifiers. The home sends at most one bounded result and ends
the subscription. There are no ongoing content subscriptions, search, counts or
notifications in this increment. A read reevaluates all current permissions and
returns the same `denied_or_not_found` for unknown and forbidden resources. A
callerless scry is not a member API; app peeks and unrelated pokes/watches fail.
Native delivery is public/synthetic fixture transport only. Production private
content still requires the later direct-browser-to-home profile.

Before the poke, the fixture thread watches the exact result path in
`specs/urbit/native-api.json`. The path includes trusted sender/binding, project,
request ID and canonical digest. The home verifies the current sender binding
and reserves an empty channel; registration grants no project permission. Pending
channels are capped at 16 per sender and 64 total, expire after 60 seconds, and
are removed on leave/completion. A payload cannot name another principal's route.

After the final decision, derive the eligible path again from trusted current
context. Emit one result fact plus kick for that exact path, from the same event
as acceptance. An authorized conflict or opaque denial needs no durable denial
cache and changes no protected business state. The thread handles fact, poke ACK,
poke NACK and kick in either order; a generic ACK never means Saved. Do not drop
early facts while waiting for an ACK. Test these delivery orders independently.

An ordinary read or receipt-recovery watch returns fact/kick to the requesting
duct only, not all subscribers of a public path. Recovery receipt lookup supplies
project, resource, operation and request ID; it checks current authority and the
recorded fields before revealing the old outcome. Revocation can hide a previously
accepted receipt without rolling back that accepted work. Missing/expired response
channels leave the accepted state durable and the client outcome unknown.

Accepted receipts contain version `stead.receipt/1`, status `accepted`, request ID
and canonical SHA-256, project/resource IDs, resulting resource revision, current
authority epoch, decision policy revision, journal sequence/digest, principal and
binding IDs, authentication mechanism/strength, and trusted acceptance time.
Document receipts also contain the exact commit OID. A duplicate returns the
original receipt and does not append a journal event. Authorized different-body
ID reuse and revision conflicts are explicit errors. Opaque denial contains no
resource revision, project existence, title, policy state or historical receipt.

The journal is a bounded append-only application structure in the same saved
state. It records the original canonical command plus trusted acceptance context,
resulting pointers/receipt and previous event digest. Its deterministic codec and
hash domain must be tested natively; no independent-human-signature claim is made. The record
codec uses the command profile's sorted-key UTF-8 JSON rules, with all counters and
timestamps as decimal strings. Hash ASCII `stead.journal/1`, zero byte, then the
record excluding its own digest; include previous digest, canonical command,
principal/binding/authentication, acceptance time, policy/epoch, old/new revision
and resulting Git OID (empty string when inapplicable). The first previous digest
is 64 zeroes. The accepted receipt includes the resulting journal digest and is
not recursively included in its own hash. This slice
has no external jobs, messages, builds, ongoing content subscriptions or effect replay. Capacity
limits reject new mutations without silently dropping deduplication/history.

## Canonical document and Git subset

Document frontmatter starts with exact `---\n`, ends with `\n---\n`, and has exactly
one each of `id`, `type`, `state` in that order, written `key: value`. No duplicate
keys, unknown keys, BOM, CR/CRLF, YAML anchors, nested values or missing delimiter
are accepted by this initial subset. `id` matches resource_id; `type` is `page`;
`state` is `draft`. Other preserved ontology values require later explicit support
and fail clearly here. The body after the closing delimiter is unchanged Markdown.
This deliberately small frontmatter grammar is not a general YAML implementation.

A private container holds compatible documents belonging to its owner; project
reader/administrator status does not override that boundary. Publication and
container sharing are later commands. Within the container, exact Markdown and
frontmatter bytes live in canonical Git blobs. Parsed document metadata stores
only IDs, revisions and object/commit pointers, never another writable body.

The home creates exact Git SHA-1 blob/tree/commit bytes itself. Represent every
binary object as `[byte_length atom]`, preserving trailing zeroes. Flat filenames
are lowercase `<document UUID>.md`, mode `100644`, sorted by Git byte order. Each
save uses the current accepted container tree and ref, changes only its target
entry, and creates one commit with the prior container commit as its sole parent
(except the first). Compare the target document revision, not a container-wide
client revision, so accepted saves to distinct documents preserve each other.

Commit author/committer identify the Stead fixture service and the authenticated
principal in a recorded deterministic format; they are host-recorded attribution,
not proof of a human signature. The exact commit bytes and OIDs, document pointer,
container ref, journal and receipt advance in one home event. Object/history/state
limits are in native-fixture.json; failure admits none of those changes.

An authorized fixture export returns a bounded manifest of the accepted container
ref and reachable object IDs, then serves one object per separately authorized
watch. Each object request binds the container, retained snapshot commit and object
ID, and proves reachability within that snapshot after current authorization.
Responses are at most 262,144 UTF-8 bytes; no entire 8 MiB store enters one response. The Linux test helper materializes those bytes with stock Git and
checks exact OIDs, `git fsck --full --strict` and recovered Markdown byte equality.
It cannot write the authoritative home or manufacture its commits. This is a
minimal native object model and portable container export, not Smart HTTP, push,
pack ingestion, a forge, general backup or complete OWGP export. Symlinks,
submodules, arbitrary filenames, clone routes and unimplemented Git features fail.

## Native acceptance corpus

Test actual project creation/grants, Work create/edit/read, deny known/unknown
resources, reader/outsider mutation denial, caller-author forgery, stale revision
and epoch, same-ID retries/payload mismatch, revoked and expired authority, absent
handling/context, independent resources, private drafts, and malformed document
inputs. Assert state/journal/object counts are unchanged after rejection.

Test cold restart separately from on-save/on-load migration. The first product
state has its own version; the counter's state is not silently interpreted as
product data. Round-trip current saved state, test every declared predecessor and
reject future/unsupported versions. Recover exported Git bytes after restart.
Independent QA owns adversarial cases and the Hoon reviewer inspects exact source
and observed evidence. Unsupported profiles remain explicitly unimplemented even
when their denial controls pass. Browser, live-network and production endpoint
isolation are separate gates.

Primary format references: [UUIDv7](https://www.rfc-editor.org/rfc/rfc9562.html#name-uuid-version-7),
[Git objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects).
These define existing formats; this document defines Stead's bounded subset.

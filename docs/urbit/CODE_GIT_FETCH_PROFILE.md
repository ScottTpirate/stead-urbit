# Bounded stateless fetch selection

`stead-code-fetch` composes the upload-pack request parser, object graph walker,
response packet writer and native pack emitter. It adds no product endpoint,
listener, saved state or credential issuer.

## Contract

`respond(input: request, advertised: (list edge), load: reader)` returns
`(each [terminal=(%round|%done) body=octets object-count=@ud] @tas)`.
`request` is `stead-code-fetch-wire.request`; `edge` and `reader` are the graph
library's OID/kind pair and scoped object loader. `from-wire(body, offered-offset-deltas,
advertised, load)` first invokes the existing bounded parser.

The home must authenticate and authorize the principal and repository afresh
for each POST, then supply the **current** authorized advertised OIDs and kinds.
The earlier discovery response is not a lasting grant. If a ref moved or access
was revoked, a formerly advertised want is denied unless its OID remains in the
current authorized advertisement. There is no reflog or arbitrary reachable-OID
exception. When creating the list, include only actual advertised tips/peeled
values and derive their kinds from verified objects. A scoped loader must never
fall back to a global OID store or another repository.

Every want is checked against that list before the first object load. Repeated
wants are deduplicated. The exact closure of the selected wants is then walked
with the graph library, which checks required object kinds, original hashes,
missing objects and its graph budgets. Missing/corrupt closure data returns
`unavailable`; no partial body is returned.

The first `have` already in that verified wanted closure selects a basic ACK.
Otherwise the response uses NAK. Unknown, private and unrelated haves cause no
object lookup and never widen the closure. On `%round`, only that packet is
returned and the object count is zero. On `%done`, the packet precedes a complete
native pack of the wanted closure. The pack deliberately includes objects the
client may already have. Haves do not remove required objects or authorize thin
pack bases. Other advertised-but-unwanted objects are excluded.

This is the basic stateless v0 behavior: one ACK for the first common have in
the POST, or NAK if none, with pack data after `done`. See the
[Git pack protocol](https://git-scm.com/docs/pack-protocol#_packfile_negotiation)
and the `get_common_commits` implementation in
[Git 2.55.0 upload-pack](https://github.com/git/git/blob/v2.55.0/upload-pack.c).
There is no multi-ACK state retained between POSTs. No side-band, shallow,
filter, thin-pack or protocol-v1/v2 path is implemented here. Negotiated
`ofs-delta` is accepted by the byte entry point only when offered; emitted packs
use ordinary stored entries regardless of that flag.

## Bounds and integration limits

Admission inspects at most 512 advertisement entries, 256 wants and 1,024 haves.
OIDs must be nonzero SHA-1 values; duplicate advertised OIDs must agree on kind.
The byte entry point retains the parser's 64 KiB request limit. Graph work is
bounded to 65,537 calls around the existing 32,768-visit/queue, 64 MiB aggregate
body budget. Final packs contain at most 4,096 objects and 8 MiB, plus at most
49 bytes of negotiation framing. The count bounds are tested; maximum aggregate
capacity is not a performance qualification.

The helper is synchronous pure computation over immutable inputs. Integration
must budget execution, preserve a current policy snapshot and reauthorize
before releasing output if work is staged across events. It must also enforce
HTTP version/content-type/cache behavior and prevent raw bypass routes. This
library does not prove the supplied policy or loader is authoritative.

The graph library's conservative object profile still applies, including its
unsupported symlink/submodule modes and incomplete `fsck --strict` metadata
validation. The successful synthetic stock fsck checks below do not remove
those general limits or qualify arbitrary repositories.

## Verification

[Retained proof](evidence/2026-11-09/code-fetch/README.md) passed 43 native arms,
two failure controls and fourteen stock/response assertions. Both ACK and NAK
bodies match stock negotiation prefixes, and their native packs pass pinned
Git index-pack, strict fsck and exact five-object body/OID readback. Trap loaders
exercise unknown/private/unwanted-have exclusion. No Stead HTTP endpoint or
real user credential was exercised.

The durable verifier is `scripts/urbit/code_fetch_check.py`. It uses the existing
serialized thermal/CPU guard, isolated namespace, pinned runtime and stock Git.
Run it only when the shared native slot is available; its 120-second deadline
and 40-second native-call deadlines remain fixed. Host-only corpus-integrity
checks do not replace native execution.

## Isolated stock-client follow-on

A separate loopback fixture subsequently passed thirteen checks using actual
stock Git 2.55.0 `clone --no-tags` and `fetch --no-tags`, forced to protocol v0.
The fixture served native discovery and evaluated each captured POST through
`from-wire`; it did not substitute a stock-generated pack. Clone reached
`7b0d20a5669435d817020be49c29f66e0411fa6e` with exactly three objects. After the
synthetic advertised ref advanced, fetch reached
`adb053935e98aa1282b44c571ea3e0bcce994c0f` with exactly four objects. Both passed
strict fsck and complete original object-byte/OID readback.

The clone POST was 123 bytes and received a 259-byte body: eight-byte NAK framing
plus a 251-byte native pack. Fetch's 123-byte POST received a 504-byte body:
49-byte ACK framing plus a 455-byte native pack. A separate 73-byte POST asking
for the former tip, now only an unadvertised ancestor, returned the native
`unadvertised-want` error. The synthetic HTTP wrapper mapped it to status 400
and exactly `Fetch rejected\n` (15 bytes), without pack data. Successful bodies
used HTTP 200. These are fixture mappings, not product HTTP status contracts.

The listener existed only in a fresh namespace with loopback up and no external
route; it was closed and its process scope stopped. The run proves this small
client exchange, not deployment, credentials, policy enforcement, protocol v2,
tag fetching or arbitrary repository support. Exact source/report identity,
negative request and local reproduction are retained in the
[follow-on evidence](evidence/2026-11-09/code-fetch/README.md#isolated-clone-and-fetch-follow-on).

# Smart HTTP v0 response body profile

`stead-code-git-response.hoon` encodes two bounded pure response bodies:

- `discovery(kind, refs, capabilities) -> (each octets @tas)` accepts
  `%git-upload-pack` or `%git-receive-pack`, a sorted list of
  `[name=@t oid=@ux peeled=(unit @ux)]`, and explicit capability strings.
- `report(unpack, outcomes) -> (each octets @tas)` accepts unpacked/failed state
  and `[name=@t result=outcome]` rows. An outcome is `%committed` or `%rejected`.
  There is no pending-success variant.

Discovery adds the service pkt-line, initial flush, reference records and final
flush. Capabilities follow a NUL on the first reference; an empty set of refs
uses the zero-OID sentinel. HEAD, when supplied, must be first. Peeled tags
follow their parent row. This follows Git's [HTTP discovery format](https://git-scm.com/docs/http-protocol#_discovering_references)
and [reference advertisement rules](https://git-scm.com/docs/pack-protocol#_reference_discovery).
The report emits unpack status followed by one final status per input ref and a
flush, following the [report-status format](https://git-scm.com/docs/pack-protocol#_report_status).

## Caller contract

The authoritative home must supply only refs currently visible to the principal,
including a valid authorized HEAD when applicable. It must derive each annotated
tag's peeled OID from verified objects and include it; the encoder cannot infer
object kinds or validate reachability from the supplied numbers. Names and OIDs
are preserved, and the input order is validated rather than repaired.

Capabilities are explicit commitments of the integrated service. The encoder
allows `ofs-delta` for upload; receive additionally allows `report-status`,
`delete-refs` and `atomic`. Allowlisting these strings does not enable their
implementation. The caller must advertise only operations it actually supports.
No side-band, report-status-v2, symref, shallow, push-options, protocol v1/v2,
fetch negotiation or pack data is emitted by this library.

Call `report` only when report-status was negotiated. A `%committed` row must
come from the authoritative durable final transition, including a successful
deletion. Quarantine success, candidate refs and proposal receipts are not
committed outcomes. The caller must provide exactly one row for every attempted
command and preserve the operation's result. The encoder cannot verify durable
commit provenance or detect omitted commands. If atomic was negotiated, the
home must enforce all-or-none outcomes; mixed reports remain representable for
non-atomic protocol use. Failed unpack with any committed row is rejected.

This library returns body bytes only. HTTP routing, authentication, status and
Content-Type/cache headers, requested protocol version, policy rechecks,
transport termination and final receipts remain integration responsibilities.
Internal formatting helpers assume their public gate's admission checks.

## Bounds and denial cases

At most 256 advertised rows (HEAD included), 32 result rows, 1,024 bytes per
full ref name, and eight supplied capabilities are inspected. The capability
allowlist and duplicate rejection make the accepted list smaller. Existing
refs require nonzero SHA-1-width OIDs; only the empty-list sentinel uses zero.
Peeling is accepted only for `refs/tags/` rows and requires a nonzero valid-width
OID. Duplicate/unsorted refs, invalid names, misplaced/peeled HEAD, unknown or
duplicate capabilities and an empty capability list fail without returning a
partial body. Packet and aggregate sizes are bounded by those input limits.

Error text must contain 1–128 printable ASCII bytes and must differ from `ok`.
This prevents newline/NUL injection. Ref results must be nonempty and unique.
The caller should choose safe failure labels rather than exposing private
backend diagnostics.

[Native evidence](evidence/2026-11-08/code-git-response/README.md) records 35
passing test arms and two failure controls. End-to-end stock-client requests,
a listener, authentication, authorization, final commit and restart behavior
are unexecuted for this slice.

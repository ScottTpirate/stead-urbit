# Native pack entry and delta primitives

These original pure helpers implement two bounded layers of the primary
[Git pack format](https://git-scm.com/docs/gitformat-pack). They do not inflate
zlib streams, resolve a whole delta graph, validate object semantics or accept
repository state. No Urgit source or separate writable engine is involved.

## Entry header

`stead-code-git-entry.hoon` exports `decode [pack offset]`, returning an `each`
of `[kind inflated source zlib-offset]` or a reason. `source` is `%none`,
`[%offset at]`, or `[%oid value]`.

The complete explicit-width buffer must be 32 bytes through 8 MiB. The caller
first verifies the outer envelope and supplies an actual entry boundary.
The decoder excludes the 20-byte SHA-1 trailer, requires an entry position at
or after byte 12, and requires at least one byte at the returned zlib offset.
It does not repeat the envelope checksum or prove that byte is valid zlib.

Types 1–4 are ordinary objects; 6 and 7 carry an OFS or REF delta base. Other
types fail. Type/size decoding permits at most five bytes, with declared
inflation capped at 8 MiB. That is the size of the delta program for a delta
entry, not its reconstructed object size. REF bases preserve all 20 bytes in
network order. OFS distances use Git's biased encoding, consume at most four
bytes, and must point strictly backward to a position at or after byte 12.
The resolver must still prove that this position identifies an earlier entry.
These are engineering admission bounds, not measured repository capacity.

## Delta application

`stead-code-git-delta.hoon` exports `apply [base patch remaining]`, returning an
`each` of exact output octets or a reason. Base, patch and declared result are
each capped at 8 MiB; `remaining` is the caller's aggregate expansion budget,
capped at 32 MiB. The caller subtracts each accepted expansion from that budget.

The two leading sizes must fit four encoded bytes. The base size must equal
the explicit input length and the output must consume the entire patch and
match its declared size exactly. Up to 4,096 copy/literal instructions are
allowed. Copy optional bytes keep their bit positions; a zero encoded copy
length means 65,536. A zero instruction is rejected. Copies must stay within
the base; copies and literals must stay within the declared result and budget.
Truncation and out-of-width input atoms fail explicitly.

Pieces are accumulated as bounded explicit-width chunks and assembled once
with the pinned standard `can` primitive. No repeated growing-buffer append is
required. This preserves binary and trailing zero bytes without normalization.
The remaining core arms are implementation helpers; these two gates are the
supported external interfaces.

## Verification boundary and next integration

The fixed native runner includes separate expected entry/delta arm inventories.
Its stock REF/OFS fixtures are independently expanded with the host-only
`git_pack_oracle.py`; the original object bytes/OIDs are compared with native
delta output. Native header offsets are compared with those same actual pack
entries. Real deltas must be present for a fixture to pass. Host zlib expansion
in this comparison is not native zlib evidence.

The [2026-11-08 checked receipt](evidence/2026-11-08/code-git-deltas/README.md)
records 211 combined checks passing, including all 32 entry and 32 delta unit
arms. Two real stock packs supplied five REF and five OFS deltas; native output
matched every original body and SHA-1 OID. Exact source bindings and the earlier
generated-fixture failure are retained. This is pure evaluator evidence, not
installed pack service or authoritative state evidence.

The next required interface is bounded native inflation that returns exact
consumed compressed bytes and exact decompressed width. A pack resolver must
then enumerate exactly the declared entries through the trailer boundary,
resolve only authorized bases, enforce aggregate expansion and chain-depth
limits, validate objects/graphs and preserve quarantine. Final current-policy
authorization, compare-and-swap refs and authoritative receipts remain separate.

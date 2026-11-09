# Outbound SHA-1 packs

`stead-code-git-emit` is an original pure encoder for an already selected list
of ordinary Git objects. `encode` returns `[%& length data]` exact octets or
`[%| reason]`. It adds no upload-pack route, negotiation, object selection,
repository read permission or accepted business effect.

The output follows the [Git pack format](https://git-scm.com/docs/pack-format):
version 2, a network-order object count, ordinary commit/tree/blob/tag entries,
and a network-order SHA-1 trailer over all preceding pack bytes. Entry headers
use the shortest type/size encoding. Input order is retained deterministically.
Every input object is rehashed from its unchanged kind and explicit-width body;
its declared SHA-1 must match before successful output. Pack entries do not
contain their OIDs directly: consumers recover the same IDs from those exact
object bytes. A matching hash alone does not validate commit/tree/tag semantics.

Each entry uses a [zlib wrapper](https://www.rfc-editor.org/info/rfc1950/) with
header bytes `78 01`, no dictionary and the Adler-32 of its exact uncompressed
body. [Stored DEFLATE blocks](https://www.rfc-editor.org/info/rfc1951/) carry at
most 65,535 bytes each, byte-aligned with little-endian length/complement fields.
Only the last block has the final bit. An empty body has one final empty block.
The Adler-32 trailer is network-order. Trailing zero bytes remain significant.
No compression heuristic, delta, thin pack, external base or SHA-256 is emitted.

| Bound | Limit |
| --- | ---: |
| Input objects | 4,096, rejecting duplicate OIDs |
| Explicit body length | 8 MiB; atom must fit its declared width |
| Complete emitted pack | 8 MiB, including all headers and trailers |
| Stored block | 65,535 bytes |
| Declared OID | At most 160 bits; independently rehashed |

The pack limit is applied to the exact encoded size before any body hashing or
emission. It includes per-object zlib and entry-header overhead, so a single
8 MiB body does not fit. For the one-blob profile the largest admitted body is
8,387,926 bytes. Unsupported kinds, duplicate IDs, invalid widths, count/byte
overflow or mismatched hashes return explicit errors and no partial output.

`admit` performs metadata-only count/width/size admission. It does not verify
object hashes and is not an encoded-pack result. `header`, `zlib-size`, `adler`
and `stored` expose bounded format helpers for focused testing. `encode` is the
complete checked pack constructor.

The caller must supply objects selected through the current repository's read
authorization and validated graph. This library cannot prove reachability,
custody, principal identity, ref visibility or current permissions. No transport
may infer permission from a successful encoding. Protocol response framing,
negotiation, backpressure and reauthorization remain outside this slice.

The implementation is bounded but synchronous. Its maximum-size native cost
and transport scheduling are not yet qualified. Do not turn the byte limit
into a performance claim or run it on an authority event path without the
surrounding admission/scheduling checks.

## Verification scope

The accompanying suite defines 28 positive arms plus a deliberately failing
control. Independent literal vectors cover an empty pack, a complete one-blob
pack, zlib/Adler bytes, binary/trailing zeros, entry-size boundaries and the
65,535/65,536-byte stored-block transition. Count and maximum pack-size tests
exercise metadata admission, not maximum-size hashing/emission. The
`interoperability` fixture arm returns a pack containing a blob, empty tree,
commit and annotated tag for separate stock-Git checks.

The [retained guarded run](evidence/2026-11-08/code-git-emit/README.md) passes
all 39 expected checks: 28 native arms, failing tang/compiler controls, and nine
pack/stock-Git assertions. Stock `index-pack --strict` and `fsck --full --strict`
consume the actual native-emitted bytes; all four original object IDs and bodies
match, including a blob with trailing zero bytes. Corrupt-trailer rejection is
also observed. The fixed driver is `scripts/urbit/code_git_emit_check.py` and
uses the existing shared execution/thermal guard. Earlier wrapper and fixture
compiler failures are retained with the successful result.

No clone/fetch service, maximum-size runtime qualification or phase acceptance
is implied by this bounded interoperability evidence.

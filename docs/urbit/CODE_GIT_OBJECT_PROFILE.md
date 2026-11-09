# Code Git objects, ref syntax and pack envelopes

These original pure helpers extend the existing document Git byte primitives.
They use no Urgit source and create no independently writable Git engine. The
home remains the only future transaction owner. No Smart HTTP, clone/push,
private-object isolation or production acceptance is claimed by these helpers.

## Exact bytes and names

`stead-code-git-objects.hoon` imports the existing `stead-git.hoon` without
modifying it. Its `octets` and `object` molds retain the original representation.

| Pure interface | Contract |
| --- | --- |
| `hash-object [kind body]` | Optional object containing the original kind/body and canonical SHA-1 OID. Supports blob, tree, commit and tag, up to the existing 8 MiB body bound. Invalid kind/width/size returns absent. |
| `parse-oid text` | Optional 160-bit OID from exactly 40 lower-case hex bytes. Zero parses as zero; the caller must interpret create/delete sentinels and must not treat zero as an existing object. |
| `valid-ref name` | Boolean for a full `refs/` name of 6–1,024 explicit bytes. Applies Git component/character rules without case, slash or Unicode normalization. `HEAD` is outside this interface. |

Hashing is not semantic validation: a malformed tree, commit or tag still has a
hash. Object kind, graph connectivity, reachability, duplicate OID collisions,
parent relationships and access require separate checks. Imported author and
committer bytes remain unchanged; the authenticated pusher is separate evidence.

Ref validation follows the primary
[Git ref-name rules](https://git-scm.com/docs/git-check-ref-format), with the
additional stated byte bound and full-name prefix. Byte syntax alone grants no
branch permission. The later receive policy may support fewer namespaces.

## Outer pack integrity

`stead-code-git-pack.hoon` exports `inspect pack`. For complete SHA-1 pack bytes
it returns either `%envelope` with version, **declared** object count, entry-byte
length and checksum, or `%invalid` with a bounded reason. It verifies the PACK
signature, big-endian version/count, versions 2 or 3 and trailing SHA-1 over the
preceding bytes. Bounds are 8 MiB and 4,096 declared objects. Empty packs must
contain only header/trailer; nonzero counts must have some entry bytes.
These are engineering admission limits, not measured repository capacity.

This follows the primary [Git pack format](https://git-scm.com/docs/gitformat-pack).
The result deliberately says **envelope**: it does not enumerate entries, prove
the declared count, inflate streams, resolve REF/OFS deltas, reject every form
of internal trailing garbage, establish connectivity or admit objects. A native
unit explicitly checks that a checksum-valid garbage entry can pass this outer
layer. No caller may interpret that result as a valid or accepted pack.

## Reconstructing a quarantined pack

`stead-code-git-resolve` starts from the verified outer envelope. Its tagged
`%scan` stage consumes one complete entry per step. It checks exact declared
object count and alignment before the SHA-1 trailer. The bounded
[native inflater](CODE_GIT_INFLATE_PROFILE.md) verifies stream integrity and
returns the first byte after the Adler-32 trailer. The resolver checks the
inflated width against the entry header before retaining data.

The `%resolve` stage completes one delta attempt per step. OFS bases must point
to an earlier entry boundary. REF bases can resolve from objects already built
in the pack, including on a later pass, or through the home's authorized reader
for the same repository. An external base is rehashed and stays outside the
new object inventory. The decoder limits both depth and passes to 32 and charges
inflated input plus expanded delta results against a 32 MiB budget. A collision
with different staged bytes rejects the pack.

Only `%complete` returns reconstructed candidate objects. The authority owns
its saved-state version, quarantine lifetime, cancellation, byte and work
admission, existing-object collision checks, reachable graph, final policy and
ref transaction. `%rejected` drops the partial inventory.

## Integration order and evidence

1. Authenticate the individual request and establish a bounded upload/quarantine
   context without making new objects readable.
2. Parse framing and receive commands; validate exact refs/OIDs and declared
   limits. Inspect the complete outer pack envelope.
3. Reconstruct candidate objects with the bounded resolver. Validate object
   structure and graph closure inside the permitted repository. Persist and
   reconcile durable job intent across interruption.
4. At final acceptance, re-read current policy, scope, credential expiry,
   authority epoch and refs. The home must atomically accept validated objects,
   compare-and-swap refs and record the result. A candidate map or checksum is
   not a committed receipt.

The shared pure runner executes each module's exact unit inventory separately.
It round-trips native blob/tree/commit/tag bytes and OIDs through stock Git,
runs stock `fsck`, compares a bounded ref corpus with `git check-ref-format`,
and inspects stock-generated and corrupted packs. Stock `index-pack --strict`
checks the positive/negative pack fixtures independently. These checks qualify
only the exercised pure helpers. URB-080, URB-200, local UI acceptance and live
deployment each have separate qualification requirements.

The [2026-11-08 retained result](evidence/2026-11-08/code-git-foundation/README.md)
contains all 128 expected foundation checks passing, including 18 object/ref
unit arms, 12 envelope unit arms and the actual stock-Git comparisons described
above. It preserves the source hashes and earlier compiler/fixture failures.
These results qualify these pure inputs and interfaces, not a native Git server.

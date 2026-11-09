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

## Integration order and evidence

1. Authenticate the individual request and establish a bounded upload/quarantine
   context without making new objects readable.
2. Parse framing and receive commands; validate exact refs/OIDs and declared
   limits. Inspect the complete outer pack envelope.
3. Compose the [entry/delta helpers](CODE_GIT_PACK_ENTRY_PROFILE.md) with bounded
   native zlib expansion, delta resolution, object validation and
   graph/reachability checks. Verify declared count and exact
   end-of-entry offset. Interrupted work must retain durable resumable intent.
4. At final acceptance, re-read current policy, scope, credential expiry,
   authority epoch and refs. The home must atomically accept validated objects,
   compare-and-swap refs and record the result. A candidate map or checksum is
   not a committed receipt.

The shared pure runner executes each module's exact unit inventory separately.
It round-trips native blob/tree/commit/tag bytes and OIDs through stock Git,
runs stock `fsck`, compares a bounded ref corpus with `git check-ref-format`,
and inspects stock-generated and corrupted packs. Stock `index-pack --strict`
checks the positive/negative pack fixtures independently. These checks qualify
only the exercised pure helpers; they do not close URB-080, URB-200, the human
trial, or any live deployment gate.

The [2026-11-08 retained result](evidence/2026-11-08/code-git-foundation/README.md)
contains all 128 expected foundation checks passing, including 18 object/ref
unit arms, 12 envelope unit arms and the actual stock-Git comparisons described
above. It preserves the source hashes and earlier compiler/fixture failures.
These results qualify these pure inputs and interfaces, not a native Git server.

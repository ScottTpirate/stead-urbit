# Independent SDK consumer qualification

This is a reviewed implementation boundary for URB-180 / #21, not a compiled or
executed consumer. The public [SDK v3](../../sdk/v3/README.md) and package/source
checker exist. The isolated builder, artifact transfer and runtime loader remain
to be implemented and tested.

## Source and execution boundary

A fresh isolated fake builder receives only the verified public SDK archive,
pinned kernel/runtime/pill and fixed reviewed build runner. No Home state, private
client, broad native-source mount, existing pier or seed enters it. Package
admission must call `scripts/check_sdk_source.py` and bind every export to the
declared Git commit; archive integrity alone does not establish that source.

Compile the sample and four named marks at one absolute Clay case captured by
`get-beak:strandio`. Retain the complete sample vase, including captured payload,
jammed directly. The mark builder returns `dais:clay`; retain its typed vase
separately and preserve each logical mark name even when source bytes match.

Wait boundedly for the exported regular files to materialize with exact sizes
and digests. Stop and reap the builder, verify owned cleanup, then re-read and
verify the bytes before releasing them. Bind package/source, installed Clay
bytes, runner, toolchain, artifact inventory, lengths and hashes to the observed
run. Artifact sizes are unmeasured; choose explicit reviewed bounds before
execution and fail closed on excess.

A separate runtime caller receives only compiled artifacts and the fixed loader,
with neither sample nor private-client source. Validate length and digest before
cue, canonical re-jam equality, and the sample's `thread:spider` type. Expected
digests come from the retained builder manifest, never an accompanying untrusted
request. Invoke the
retained gate directly with its input vase. Calling the named sample through
Spider would compile source again and would not prove this boundary. The actual
receipt must identify the runtime caller, not the builder.

Compiled mark validation does not install marks into Gall. Bind the Home's
installed mark bytes to the same public exports and test the actual carrier.

## Pinned interfaces reviewed

The references below are from kernel commit
`5a187fededc4582a34fcd6055c67bb63e0917b94`:

- [strandio](https://github.com/urbit/urbit/blob/5a187fededc4582a34fcd6055c67bb63e0917b94/pkg/arvo/lib/strandio.hoon)
  provides `build-file-hard`, `build-mark`, `get-beak` and `read-file`.
- [jam-all-desks](https://github.com/urbit/urbit/blob/5a187fededc4582a34fcd6055c67bb63e0917b94/pkg/arvo/ted/jam-all-desks.hoon)
  demonstrates binary export through Clay `%info`. This path has no `%mere`
  merge acknowledgment; verify actual file bytes instead.
- The pinned `jam` and `mime` marks carry binary data. A `%mime` import with
  explicit `[length atom]` preserves the byte boundary, including trailing zeros.
  The proposed loader composition still requires native compilation.
- [Spider's slam-thread](https://github.com/urbit/urbit/blob/5a187fededc4582a34fcd6055c67bb63e0917b94/pkg/arvo/app/spider.hoon)
  applies a `vase -> shed` gate directly. Name only the fixed loader in `%fyrd`,
  account for Khan's unit wrapper, and retain the runtime strand bowl.

Existing helpers need narrow alternatives: `core_conn.exchange` pretty-prints
and expects `%stead-core-result`; `native_install.install` assumes raw `@t` bodies;
the ordinary team installer includes private client source on every ship. Keep
the current one-megabyte conn/evaluator limits unchanged. Clay's existing binary
export path avoids rendering the full compiled type through those text helpers.

## Required native observations

First resolve the remote-fact compatibility concern with one harmless public
query from a distinct ship. Capture the actual fact's mark/wire, the comparison
of its vase type with `%noun`, bounded type/payload sizes and digests, and the
`mule` outcome around the sample's exact `!<(@t ...)` expression before its failure
normalizer. A timeout or absent fact proves nothing. The concern is from source
review; do not change either client on the claim that a runtime failure occurred.

Then require public-only compilation and direct retained-vase execution with
authorized Work creation/readback and denied scope, actual caller identity and
correlated business receipts. Native controls must reject an altered payload
with its original digest, a valid jam with the wrong type and correctly bound
control digest, truncated/trailing/noncanonical/oversized bytes, missing or
misnamed marks, and changed loader bindings. A deliberate private import must
fail inside the SDK-only builder alongside the successful public build.

Complete the issue's malformed input, unsupported version, replay, watch
cancellation, revocation, stale cursor and reordered-update cases through this
consumer. Existing private-client tests and package verification are separate
evidence and cannot substitute for these calls.

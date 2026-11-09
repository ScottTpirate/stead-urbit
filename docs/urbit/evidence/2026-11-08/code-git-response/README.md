# Native response encoder evidence

Fixed diagnostic `.runtime/response-dev-2zhj9hia` passed **37 expected checks**:
35 exact named test arms returned empty tangs, the deliberate failure returned
three tang lines, and malformed Hoon was rejected. The compiler-negative
process returned zero; its actual syntax/bail diagnostic established failure.

Nine independent literal streams cover empty/upload/receive discovery, HEAD,
peeled tags, capability placement and committed/rejected/mixed/unpack-failed
reports. Those literal fixtures were also host-checked for complete packet
framing. Other native arms cover sorting, duplicates, invalid/zero/wide OIDs,
capabilities, limits, invalid ref names, contradictory final results and error
text injection. No stock-client/server exchange was run for this slice.

The guarded run took **5.016 seconds**, CPU 19 at 50% quota, with maximum sampled
temperature **46°C**. Existing 75°C admission, 90°C stop, shared lock, 45-second
overall deadline and 30-second per-call deadline remained unchanged. Its own
scope was observed inactive/dead. No ship was booted; the evaluator ran without
network access in an isolated namespace.

[receipt.json](receipt.json) binds all five native input files before/after,
generated Hoon, diagnostic scripts, helper/runtime identity, actual outputs,
raw reports and resource proof. Current source hashes matched at receipt
creation. New source was uncommitted, and the recorded receipt-time checkout
commit is not a claim about run-time commit membership.

The initial diagnostic `.runtime/response-dev-zb83jvff` failed compilation with
`-find.$.+2`. Two tests were corrected to bind computed results before reading
their tag; native library bytes were unchanged. The failed source, diagnostics
and hashes remain retained. It contributes no passing tests. The shared vector
runner was not edited; the one-use diagnostic is separate.

Observed command, with verified Git 2.55.0 first on PATH:

```sh
PATH=/tmp/stead-local-preview.umQhNO/tools/usr/bin:/usr/bin:/bin python3 .runtime/response-dev-2zhj9hia/run.py
```

This qualifies only pure response body encoding. The [public profile](../../../CODE_GIT_RESPONSE_PROFILE.md)
states caller duties for authorized refs, verified peeled objects, capabilities,
negotiation and durable final outcomes. No phase, listener, authentication or
committed-write acceptance is implied. Raw outputs remain in the ignored paths
recorded in the receipt; successful output and the prior compiler diagnostic
are preserved in the checked receipt.

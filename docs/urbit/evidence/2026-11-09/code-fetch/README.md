# Native fetch selection evidence

Staged run `20261109T113029Z-swyf6dp6` passed **59 expected checks**:
43 native arms, two failure controls and fourteen native-response/stock-Git
assertions. The first native attempt passed.

Both native response bodies match pinned Git 2.55.0 negotiation prefixes:
NAK without a common have, or ACK for the first common have. Their five-object
packs each passed stock index-pack with strict validation, full strict fsck,
exact object inventory and every original body/OID readback. Both corrupt
trailers were rejected. Unit cases also cover current-advertisement denial,
private/unknown/unwanted-have exclusion with a trap loader, duplicate wants,
missing/corrupt data, complete wanted closure, parser composition and bounds.
No Stead HTTP endpoint or real credential was exercised.

The guarded run took **10.031 seconds**, CPU 19 at 50% quota, maximum sampled
31°C. The existing 75°C admission, 90°C stop, shared lock, 120-second total and
40-second native-call deadlines were retained. Its scope was observed
inactive/dead. No ship was booted; the namespace had no network access.

[receipt.json](receipt.json) binds exact before/after inputs, canonical native
sources, runtime/stock Git identity, named checks and raw paths with digests.
[report.json](report.json) preserves actual native and stock output. New Hoon
ran from private staging and was promoted byte for byte. It was uncommitted;
the execution commit is context. Every tested native source still matched at
receipt creation. The common host vector helper changed after execution during
parallel integration; its exact executed copy and both hashes are recorded.
This does not retest or qualify that subsequent helper revision.

The executed driver was `.runtime/fetch-core-7zeslohn/fetch_check.py`. Its portable
canonical-path version is `scripts/urbit/code_fetch_check.py`; path/binding setup
changed on promotion, and that entry point has not received a second native run.
Three new host proof-integrity tests and twelve existing host vector/parser
checks passed separately.

```sh
PATH=/tmp/stead-local-preview.umQhNO/tools/usr/bin:/usr/bin:/bin python3 scripts/urbit/code_fetch_check.py
```

The [integration profile](../../../CODE_GIT_FETCH_PROFILE.md) documents stateless
semantics, current-ref races, scoped loading and resource limits. This does not
qualify a phase, product endpoint, policy/authentication boundary or saved state.
Maximum aggregate capacity is not a performance qualification.

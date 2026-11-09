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

## Isolated clone-and-fetch follow-on

Run `20261109T115028Z-3tc1_823` passed **13 separate checks** on source commit
`c6e10865ac1d7c5c016cb44c63b3ccf41dbee0aa`. Input hashes matched before/after,
including the pinned Git HTTP helper. This was actual stock Git 2.55.0 clone and
fetch over private loopback, with protocol v0 and `--no-tags`. Native discovery
and actual `from-wire` results supplied the response bytes.

| Exchange | Request | HTTP / response bytes | Exact resulting commit |
| --- | --- | --- | --- |
| Clone | 123 bytes, duplicate want | 200 / 259: NAK 8 + pack 251 | `7b0d20a5669435d817020be49c29f66e0411fa6e` |
| Fetch after ref advance | 123 bytes, one have | 200 / 504: ACK 49 + pack 455 | `adb053935e98aa1282b44c571ea3e0bcce994c0f` |
| Stale discovery want | 73 bytes | 400 / 15, no pack | Native `unadvertised-want` |

Clone contained exactly three objects; fetch contained exactly four. Both
passed full strict fsck and every expected original object body/OID check.
Fetch acknowledged the original commit. The negative POST requested that same
commit after it ceased being advertised, despite remaining reachable; the
wrapper returned exactly `Fetch rejected\n`. HTTP status mapping belongs to
this synthetic wrapper. The negative native result does not establish a real
credential-revocation or product authorization boundary.

The run took **20.054 seconds**, CPU 19 at 50%, maximum sampled **49°C**, within
the unchanged 120-second guard and stricter 30-second native-call timeout.
The listener was only `127.0.0.1` in fresh `net:[4026533518]`, with UP loopback
as its only interface and no external route. It closed successfully, and owned
scope `stead-native-78d3ecd5c560e8d5d7024d4c87cfcf85.scope` was then observed
inactive/dead. No host-exposed listener or ship was started.

Raw diagnostic material remains private under:
`.runtime/fetch-client-1_ouv6de/runs/20261109T115028Z-3tc1_823/`.
Its `output/report.json` SHA-256 is
`0321585e3225c97affb147ea836a95334b85da362ddb552812a7b64f344f7611`.
The guard report is `.runtime/execution-runs/fetch-client-nq3zv8fm/report.json`.
The staged script `.runtime/fetch-client-1_ouv6de/fetch_client.py` has SHA-256
`bcc7015ed4b9415a69547a8ba7f882780d1b3cb69e426e177d8ec2ca6771747e`.
Only when the shared native slot is available, local reproduction uses:

```sh
PATH=/tmp/stead-local-preview.umQhNO/tools/usr/bin:/usr/bin:/bin python3 .runtime/fetch-client-1_ouv6de/fetch_client.py
```

This follow-on is independent of the earlier 59-check pure proof. It does not
qualify a product endpoint, real credentials/policy, tags, v2 or maximum capacity.

# November 9 Phase 3 and 4 local workflow evidence

This follow-up starts from the earlier [local Code and import
verification](LOCAL_CODE_IMPORT_20261109.md). The product path here uses
configured disposable Urbit ships, pinned Vere, stock Git 2.55.0 and native
Eyre TLS. It leaves the existing manual review pier and original stopped
fixtures alone.

## Native workflow at 5505f22

Commit `5505f22ce65a8067ebebf7039b8840ccb027923d` saves accepted review,
build and staged upload state in the Home v5 envelope. V3 Work/Docs and v4
Code-only states remain readable and keep their respective envelopes. The
queued upload and its original wire bytes can survive a Home restart.
The HTTP reply lease and credential ledger are transient. Resumption requires
a fresh authorized request carrying the same bytes.

The exact desk compiled. The official pinned Khan test command passed 15
protected-review and eight upload cases. Its deliberately failing control
failed as expected and the isolated fake shut down cleanly. Native report
`.runtime/phase3-review-clay-j0Knqpu1/state/report.json` SHA-256
`842644b7d9c18fd84c7f51f7e8d8e2a89cf9789d5a30446da9ca4d075fb36056`.
The host suite ran 845 tests with one skip and the frontend suite passed 39.

The fresh four-ship workflow passed 14 Git and authenticated Home checks.
It tested ordinary clone, fetch, push and strict fsck, native Work-linked
proposal and review, protected compare-and-swap, exact merge replay, and
revoked reviewer denial. A separate member claimed the build lease and
produced the static manifest in the isolated worker. Home verified the
artifact bytes against the exact commit and accepted one finished job.
The worker's artifact SHA-256 was
`9e1a99df1c4968ad2f47c9e12d4d6e45e2163ab7a4f7c0f099415d9702df382c`.

The 320, 390 and 1440 pixel native screenshots were independently inspected
by Astra ultra. Review actions were exercised through the authenticated
HTTP boundary in this run. The screenshots show the Code and initial review
form. A separate mock-response Firefox test covered the form and explicit
retry of the same merge request through navigation.

## Measured local canary

The same configured fixture ran three stock pushes, three fetches and three
clones. Each Work and Docs group has 18 baseline reads and 18 loaded reads.
All loaded reads overlapped an observed transfer. The canary verified a
separate reader, denied private Docs and anonymous Git access, revoked
credentials, and verified an offline Code archive and restore from the final
authenticated clone.

| Read | Baseline p50 | Baseline p95 | Loaded p50 | Loaded p95 |
| --- | ---: | ---: | ---: | ---: |
| Work | 458 ms | 650 ms | 678 ms | 1,620 ms |
| Docs | 454 ms | 594 ms | 700 ms | 1,517 ms |

With 18 samples, p95 and p99 both use the largest sample. The timings are
request observations under the local one-core guard. This establishes a
small local workload baseline. The native runtime completed in 393.078
seconds with clean ship and browser retirement.

| Evidence | SHA-256 |
| --- | --- |
| `.runtime/phase34-focused-ox9TN7sA/browser-ukir97h7/result.json` | `28288f8327b1cc02151f56e6ec1e14d32aab20d805c295eed3f5a15a49e74e13` |
| `.runtime/execution-runs/four-fakes-9rdy167a/report.json` | `d3682e42dbf6188aa98346437d9649a87b05cea35dce9eaba384be81c3848fad` |

## Interrupted upgrade and populated recovery

Both exact role archives from `5505f22` reproduced byte for byte and passed
offline verification. The Home v5-capable archive SHA-256 is
`ffb5625d1d1f819ad4b2f54ca30f04abee337cc04ca63718c7d123d47a27cbcd`.
Identity v1 is
`289654ffb181dc5b68100113ba03ed595e3ca6fdcc0c8b0f98eccf9b0fd4a143`.

The Home upgrade applied that exact target desk to the verified historical
v3 copy. All 18 native checks passed. The first child stopped after the Clay
commit with the old Home suspended. The next child resumed the sealed
checkpoint, kept HTTPS fenced until fresh owner bootstrap, and preserved
the exact v3 database. This controlled interruption uses a clean stop and
restart. A Code-free Home still emits v3 after the upgrade. [Upgrade profile](HOME_UPGRADE_PROFILE.md)

The separate populated v5 recovery cold-booted a stopped clone of the
successful workflow. All ten checks passed, including exact v5 lane
fingerprints, all ten reachable Git object bytes, protected ref and review
receipt, and assigned finished build with its exact artifact digest.
The restored Home served the exact shell after fresh bootstrap. Both
clones and guards stopped, with the source checkpoints unchanged.

| Evidence | SHA-256 |
| --- | --- |
| `.runtime/release-home-upgrade-uu4lbibt/upgrade-report.json` | `3175d50ccc5ce7044d326ffe7d07cd3a09ca2db6388091b473b836115e999035` |
| `.runtime/team-v5-recovery-stage-hmPBz1yM/work/proof-report.json` | `92c7fa7d01e6ef71fb850988084a6ab910f20561d30f5afd9ba0aaff029ecb65` |

## Independent release and portable delivery at aebff68

The final configured workflow at
`aebff68f37ca8efa455009517b01f44a85f2a81b` passed 16 Git and Home checks and
six browser checks. A third individually authenticated maintainer accepted
one release intent for the exact reviewed commit and finished artifact.
The Home returned the original result on exact replay and denied a second
intent and replay after the signer's grant was revoked. A forged canonical
artifact with a recomputed matching outer digest was denied before the valid
manifest was accepted.

An authorized maintainer captured a paged audit with 17 records, including
the review and ref receipt, exact build artifact bytes and release intent.
The offline verifier checked its snapshot and ref/receipt relationships.
The separately measured stock Git workload again passed. Loaded p95 was
930 ms for Work and 2,286 ms for Docs, with 18 overlapping samples per view.
Both role archives from the same source were byte-reproducible and passed
offline verification. The exact Home and Identity archive SHA-256 values are
`f8d6afd48449b274d11ee8cc5b6f466c09055c1723dab80300bf44618760f906` and
`13956acab0e19e6a54be4f5a268f2522a78537fd0d6c63574659de6bd2d4b21d`,
respectively. Both archives and their target profiles are in
`.runtime/phase34-final-release-dyLJ0z0Y`.

Astra ultra independently checked the exact Git, review, build, release
and audit bindings and inspected the populated proposal UI at all three
widths. The guard completed cleanly in 422.833 seconds, peaking at 64°C. The
browser and four ships stopped and the temporary member-session files were
removed. The final host suite ran 853 tests with one skip.

| Evidence | SHA-256 |
| --- | --- |
| `.runtime/phase34-final-focused-GY5QzebY/browser-beiqq59l/result.json` | `34d07418b23d14016905f63c2c90a9255c6755f84e5722b66b817ebf043b88a3` |
| `.runtime/phase34-final-focused-GY5QzebY/browser-beiqq59l/delivery-audit.json` | `d6287130d29dbd0b09dd524b637637337dcd6bdab5dcfab77a6000fb670f3950` |
| `.runtime/execution-runs/four-fakes-2m8x6eg1/report.json` | `605a4f28960f527682b70b038273773d8240cb21d674313e2a8db83949d968e1` |
| `.runtime/code-delivery-audit-native-sRaoqSxE/state/report.json` | `621df75d8d3c0aa097ec051d4a34900943b5eeca36ed0356670288f40bc95828` |

The final v5 cold recovery independently checked the exact three-person
release against the same 17-record audit. All seven saved state lane digests
matched across suspension, reload and fresh bootstrap. The exact protected
merge, stock Git objects, worker artifact bytes and independent release
record remained intact. The audit snapshot verified again afterward. The
original stopped fixture rehashed unchanged and the isolated Home stopped
cleanly in 25.430 seconds.

| Recovery evidence | SHA-256 |
| --- | --- |
| `.runtime/team-v5-recovery-stage-h7JgLWDI/work/proof-report.json` | `de12059615763842801adca20e67c3f2b8da70229f725019f79d62f7ef4375b3` |
| `.runtime/execution-runs/team-v5-recovery-e3tqtmqx/report.json` | `3a44e5cd538a591f74b63db057273ca189b3b732aecbc8e46e051592cba72d02` |

The exact final Home archive repeated the controlled v3 upgrade and passed
all 18 native checks in 80.040 seconds. The sealed replacement process
required fresh owner bootstrap, served nine exact HTTPS assets and preserved
the v3 authority fingerprint. The final child stopped cleanly and the source
copies rehashed unchanged. The aggregate report is
`.runtime/release-home-upgrade-g8p0cmfp/upgrade-report.json` with SHA-256
`bcc51d06d4fa42ad56bf1568724d08e64ef91f081d46515d25107660b90fc7c2`.

The local scope is SHA-1 repositories within the current 64-object limit,
one exact manifest recipe, separately portable Git and delivery audit files,
and a measured single-host canary. The audit preserves readable evidence
while restoration of authority uses the verified native recovery procedure.
Reattachment of an interrupted pending upload has native transition coverage.
The cold-copy proof observed the completed workflow. The release operation
records intent. Actual host admission and multi-host behavior are part of
the [Phase 5 deployment runbook](PHASE5_DEPLOYMENT.md).

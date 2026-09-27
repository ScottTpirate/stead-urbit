# Native core review — bounded source disposition

Reviewed September 13, 2026 UTC by the independent `/root/hoon_review` agent.
Implementation owner: `/root`; adversarial test owner: `/root/qa_review`;
original Git-object helper owner: `/root/urgit_audit`.

**Current disposition: bounded source review complete; execution evidence
supports the first native slice. The native driver passes, while 25 broader QA
assertions remain incomplete.** The final addendum assesses the completed run
without closing the broader qualification gates.
This is independent agent review, not a human Hoon specialist audit, owner
approval, permission to merge, or deployment/security qualification. The reviewer
did not edit implementation code or operate the running fake ships during this
review. The only authored repository artifact is this note.

The review base is commit `96971540cf70c557f01a5ef10db832ddee2e0130` on
`increment/urb-040-050`. The implementation is uncommitted at this checkpoint;
the base commit alone does not identify it. Origin was verified as
`https://github.com/ScottTpirate/stead-urbit.git`; the original Stead upstream
remained read-only.

## Reviewed source snapshot

Paths are relative to `native/core/desk/`. SHA-256 identifies exact reviewed bytes;
subsequent changes need a review addendum.

| File | SHA-256 |
|---|---|
| `app/stead-home.hoon` | `7dafb0d9af5667eb8ea9648476e3ba2a8119c4dc15d03724d5d98b268be9b6f4` |
| `ted/stead-client.hoon` | `4211ca0d32afc125e114973aa6bc666cd714217bfea96751a6ab0b940cbd61ea` |
| `lib/stead-core.hoon` | `6c886d37d17b2ef6c732e72c92934d586c2dd36aa1c13691456cc46757184d24` |
| `lib/stead-codec.hoon` | `ce4c7a69b03ee1761590c37e71ff49b9f63a1a2edd2aaa6dfbf75bc3c960584a` |
| `lib/stead-delivery.hoon` | `178cac634471554dae9928f8c38248751329314391061976a436a22a7075548d` |
| `lib/stead-git.hoon` | `826b83485429c02f577c9b462ee6cddd3ab8ea1a099d33b66893f863d54c54d7` |
| `gen/stead-reducers-probe.hoon` | `a5c3b59ef426a2e1d44bb3b0084b222a26120ed999dd0744885bbe2a78c14471` |
| `mar/stead-control-1.hoon` | `643d9d5221b5b43230f864f11b1d6830ad2b32ffd64644c77ea70c0fa1ea8c5e` |
| `mar/stead-command-1.hoon`, `mar/stead-fixture-1.hoon`, `mar/stead-result-1.hoon` (each) | `fcd87c92acc16c2883b1dd4900af5064d1da910af317e93c327455cd56d9553b` |

The frozen contract manifest is
`specs/urbit/contract-freeze.json`, SHA-256
`61d9a18f16b8b01629bd35177d5b801cc05cd8ddaf7f68c3cc1678faf642cf90`.
The toolchain lock is `specs/urbit/toolchain.lock.json`, SHA-256
`4a209c10cf1756eb0f7357cc3eca8250bf66c239b4cd0ca31a8c0886d4d304ee`:
Vere 4.6, commit `8ddc4b786979574dbfcb655e3db1b634f658d0de`, and kernel
408k-2, commit `5a187fededc4582a34fcd6055c67bb63e0917b94`.

## Source findings and corrections

- **Authority before retry disclosure.** `stead-core` checks current binding,
  exact supported profile, action/read scope and authority epoch before consulting
  accepted receipts. Duplicate content returns its original receipt before the
  current revision comparison; revoked authority cannot recover it through that
  path. Receipt-recovery reads check current read/action scope before lookup and
  the stored operation/resource and full current action authorization afterward.
- **Scoped policy and history.** Grants are project-scoped, expire at the final
  decision, obey the maintainer/administrator grant ceiling, and cannot overwrite
  retained or revoked grant IDs. Content access still requires explicit membership;
  organization administration is not a document-container bypass. Journal sequence
  and previous digest are selected per project. The decision policy revision is
  recorded separately from the resulting policy-resource revision.
- **One authoritative save.** Work, document pointer, container head, native Git
  objects, reachability, journal and receipt are returned as one home state
  transition. The document's canonical text is its exact Git blob. Existing OIDs
  must retain the exact object tuple; collisions against historical objects or
  within the staged blob/tree/commit are rejected. Object exports recheck current
  container access and snapshot reachability for each object.
- **Native delivery.** The home derives the sender from Gall, binds pending paths
  to sender/binding/project/request/digest, bounds reservations, and emits one fact
  and kick. Ordinary reads address only the current request duct. The client
  retains ACK/fact/kick independently, rejects duplicate events and wrong marks,
  bounds JSON, and checks command and read correlation. An ACK-only fixture/poke
  result is `{}`; it is not a business acceptance. The local `%codec` test mode's
  `accepted` means codec validation only, not a home mutation.
- **Parser and state boundaries.** Raw command JSON remains bounded and closed;
  decoded duplicate keys and NUL are rejected before map/string conversion loses
  them. The broader response parser has separate limits. Product saved state is
  `%stead-home %1`; unsupported counter/future shapes fail instead of resetting
  product state. Pending replies are cleared on app load. Process restart and
  `on-save`/`on-load` are separate tests.
- **Fixed native construction errors.** The implementation owner fixed the
  control mark's `+grab +noun` to be an actual validating gate rather than a tuple
  of mold cores. Independent evaluation found the reducer probe used the list
  `~['x']` where the answer unit required `[~ 'x']`; the owner applied that fix.

These are source-level conclusions, not a claim that every branch has executed.

## Independently executed check

The reviewer ran two standalone processes of the pinned binary:
`.runtime/bin/vere-v4.6-linux-x86_64 eval --loom 29`. No pier, network, native
identity, browser, GitHub action or fixture state was involved. The evaluator
reported a 512 MB loom mapping; this is not a benchmark or a measured ship RSS.

The input injects the unchanged `stead-delivery` library, takes the delivery-only
section of `stead-reducers-probe` (before `=/  blob`), and returns a unique marker.
This executes all six ACK/fact/kick permutations, asserts incompleteness after
the first two events, and checks NACK plus duplicate ACK/kick/fact rejection.
It does not execute the later object-collision assertions or simulate Spider's
event dispatcher, timer, routing, or network.

| Evaluation | Input SHA-256 | Exact result |
|---|---|---|
| Six orders and four rejection cases | `929280333b696ae6a3bd3cc10bf5190739da2c199230c853c517d9bdccabe70e` | stdout `%stead-delivery-independent-pass`, exit 0 |
| Intentionally inverted first assertion | `1fec318152a38912ff8591987790c53c61cc919289c857d0a42a6d782498f7c7` | empty stdout, stderr `eval: bail: %exit`, exit 0 |

The failure control demonstrates why Vere's process exit code alone is not a
passing test. Reconstruct the two evaluator inputs from this snapshot with:

```python
from pathlib import Path
lib = Path('native/core/desk/lib/stead-delivery.hoon').read_text()
probe = Path('native/core/desk/gen/stead-reducers-probe.hoon').read_text()
body = probe[probe.index('=/  progress'):probe.index('=/  blob')]
positive = '=/  stead-delivery\n' + lib + body + '%stead-delivery-independent-pass\n'
negative = positive.replace(
    '?>  =(| (complete:stead-delivery progress))',
    '?>  =(& (complete:stead-delivery progress))', 1)
```

## Inspected execution evidence and its limits

The reviewer read the implementation owner's local real-native report
`.piers/fakes/logs/core-20260913T025145Z.json`, SHA-256
`b73f0232cc8082ac3ad0b9d4df22756e775cfafc02dc0aaab9ccb5129873ef44`.
It contains 12 command records, build probes on all four fake ships, and exactly
two passing business checks: a home project-creation receipt and `~bud` receiving
the exact opaque project-read denial. Reported elapsed time is 25.798 seconds.

That report names earlier native tree
`c39a2f96767a53a71fcf2c22397e01babbaba72ccfff2cd42fa9be1425bacfeb`.
It does not validate all source bytes in this note. Its runner measured the tree
only after execution, so it also lacks the later required start/end and
loaded-runner source binding. The full driver must fail on source drift rather
than attach a passing result to uninstalled bytes. These local logs are ignored
artifacts; retain the final portable evidence separately before claiming a
reproducible PR result.

Separately, the reviewer previously inspected and rehashed the original Git
helper's 51-check pure-evaluator/stock-Git evidence, including 14 exact object
byte/OID comparisons, round trips and `fsck`. The reviewer did not rerun that
whole corpus. It demonstrates object construction, not home saves, Smart HTTP,
quarantine, credentials, or pack ingestion. See [the object profile](GIT_OBJECT_PROFILE.md)
and its accompanying evidence.

## Gates still open

1. **Full native acceptance and source binding.** The current implementation
   still needs the complete independently owned corpus against an unchanged
   installed snapshot: four-principal policy denials, stale/duplicate/revoked
   retries, document and object privacy, actual export recovery, schema negatives,
   current/future/counter state checks and a stopped-process product restart.
   The pure reducer result does not prove channel quotas, expiration, cleanup,
   unavailable-home behavior, or real delivery order under Spider.
2. **Private-existence collision oracle.** Global `id-used` checks combined with
   caller-selected creation IDs expose whether an ID is retained elsewhere:
   someone authorized to create a work item in project B can submit a known or
   guessed ID from inaccessible project A and distinguish acceptance from a
   collision rejection. This is source-derived, not a native exploit reproduced
   in this review. Changing only the error text cannot remove the distinction.
   Keep comprehensive private-existence protection open pending a reviewed
   allocation/reservation or equivalent design; do not change frozen contracts
   silently or generalize the synthetic outsider-read test into that claim.
3. **Administrative and real-data isolation.** Fixture initialization, context
   controls (including synthetic binding drop/restore), migration controls and
   the state/revision snapshot are owner-local test
   administration, not employee APIs or audited policy-management mutations.
   Rejecting Stead app peeks does not prove owner-local Gall scries, `%dbug`, Eyre,
   or other installed applications cannot expose administrative state. Browser
   sessions, live identity continuity, endpoint isolation, confidential data,
   backup/crash-window recovery and deployment remain separately gated.

No public live Urbit, cloud, browser, performance, real-GitHub test, migration of
project authority, native Smart HTTP, pack-ingestion, or release claim is made by
this review. Record later evidence as a dated addendum with its exact source
identity; do not rewrite these limited checks as broader successes.

## Addendum — September 13, 2026, 03:28 UTC

The updated owner-only snapshot now accumulates explicitly typed `[@t @t]`
revision pairs before creating its JSON object. Policy revisions use the project
ID as key; project/work/document resource revisions use `project/resource` keys.
This remains an administrative derived view, with no writable master added. The
app hash in the table supersedes the initially reviewed
`778e9e4e4461d192676301e35a48e76b829a1608d8744c48eb08c538f5c44832`.
Core, client, codec, delivery and reducer-probe hashes remain unchanged. Current
native tree SHA-256 is
`6f1bc326d0d0388ee8ea4c3e12e01c345e2f309e69e5664b3de3b96be8611669`.
The reviewer reread the app additions and confirmed the unchanged core
authorization/epoch-before-deduplication order and client correlation checks.

The reviewer inspected two further implementation-owner reports without running
or changing any fake ship:

| Report | Recorded outcome | SHA-256 |
|---|---|---|
| `.piers/fakes/logs/core-20260913T031350Z.json` | Failed at the zod build probe on an earlier tree; 18 driver checks passed and one failed | `eab2e8e6e5067ee2db5a187c903294342cfc6ad84721727fec005e1c0b6a6870` |
| `.piers/fakes/logs/core-20260913T031535Z.json` | Failed in the host encoder after the business corpus and part of the codec corpus; 204 driver checks had passed | `f38e0d060aef9710535b1489ee743acecd13a521344ef82c667a29d6ac953383` |

The second report's independent QA section contains **129 executed cases: 115
passed and 14 incomplete**, with **2,542 passed assertions and 25 explicitly
skipped assertions**. It preserves QA status `incomplete`, while the outer runner
preserves status `fail` and `ValueError: Invalid runtime-encoded core request`.
The skipped assertions comprise 22 request-duct/delivery observations, one wider
metadata-confidentiality assertion, one external-effect observation and one
internal lookup-order assertion owned by source review. No skipped assertion is
converted to a pass in this note. The reviewer inspected these records and their
counts, not independently replayed every business operation. Reported elapsed
time was 335.382 seconds for the failed attempt, not a product benchmark.

Before/after input dictionaries in that failed attempt are equal, and its native
tree matches the current tree above. This improves on the original two-check
report's source attribution. That completed attempt checked copied mount files;
it did not yet contain the new Clay `%cx` checks.

The current driver additionally reads **actual Clay source bytes** through `%cx`
and compares their SHA-256 before compiling each of the four ships. Source
inspection confirms this check occurs after commit and before the build probe.
It checks loaded supervisor/core-runner hashes, records native/runner/harness/
fixture/corpus/vector/lock/freeze inputs before and after execution, and forces
failure on drift. Reviewed driver SHA-256:
`a668aa0971741279d17a13185748d882ebd3413637fb23d79b5c1b465823ce2c`.
These new checks belong to the active rerun; no completed result for that rerun
was available at this addendum.

The owner retained a separate
[Vere evaluator boundary regression](evidence/2026-09-12/native-core/vere-eval-boundary.json),
SHA-256 `d50bf7f511f58b1a566124cd35a5567ccc66376ed6835953ae0e2e29aa333478`.
For the 65,537-byte malformed corpus input, it records a pipe returning 65,536
bytes of a declared 65,590-byte Newt frame despite exit 0. The regular-file output
returns all 65,590 bytes, with frame SHA-256
`ee1efd978907f7f493003036401822f952da673c61953b9ab37448f95e4fb5fe`.
The reviewer independently reconstructed the corpus input and verified its
recorded length/digest, and checked the referenced binary and adapter hashes;
the reviewer did not rerun this evaluator regression. The incomplete frame was
rejected before sending it to the home, so this failure was not a native
acceptance or rejection of the oversized command.

Reviewed `scripts/urbit/core_conn.py` SHA-256 is
`460ecd9c37979d0974c2fdef74579d346b9af2bd7592e037ee7f82e868d90090`.
It now captures encoder and decoder output using an anonymous temporary regular
file, bounds the read, retains the evaluator timeout, and still validates exact
frame length and the complete terminal response wrapper. This is a host transport
fix; it does not relax the native command limit or establish native rejection
until the corresponding home test executes.

The source-review disposition remains suitable for continuing the synthetic run.
Full acceptance, the explicitly skipped observations, metadata confidentiality,
and the administrative/real-data isolation gates above remain open. The active
rerun must produce its own final evidence and independent QA disposition.

## Completed-run assessment — September 13, 2026, 03:37 UTC

The reviewer independently inspected
`.piers/fakes/logs/core-20260913T032554Z.json`, SHA-256
`e22f4606a53c42b2beee75ae2bed5dca26ae8260346513398f328cbc95d5ca6e`
(8,242,058 bytes). It records outer-driver status **pass**, 413 passing driver
assertion records, no failed driver assertion, and 390.266 seconds elapsed. It
contains 871 command records and 15 lifecycle records. Counts of assertions are
not counts of independent scenarios or performance measurements.

QA still records **115 passed and 14 incomplete cases**, with **2,542 passed and
25 skipped assertions**, across all 129 expected business cases. There are no
failed or unrun business cases. QA status remains `incomplete`; the skip reasons
listed in the preceding addendum are retained. The driver's pass does not turn
those assertions into passes.

The recorded native tree is still
`6f1bc326d0d0388ee8ea4c3e12e01c345e2f309e69e5664b3de3b96be8611669`.
The reviewer recomputed and compared every entry in `inputs_before` and
`inputs_after` against current native files, four runner modules, the supervisor
dependency closure, fixture, case corpus, canonical vectors, contract manifest
and toolchain lock. All match. The pinned binary independently rehashes to
`47ad302e8934271dfc00dcdab1d553c6d6460b105e3099ff47e0e4e4231bb26d`.
No Hoon file hash in the reviewed table changed for this completed run.

All **60 recorded Clay `%cx` comparisons** return `%.y`: exactly the 15 current
Hoon files on each of `~zod`, `~bus`, `~nec` and `~bud`. The reviewer independently
parsed each expression and matched its path and expected digest against the
current source, then checked complete per-ship coverage. Together with loaded
source and before/after checks, these records address the earlier attribution
gap: a Hood ACK is no longer the only evidence of source installation.

The completed driver records these additional executed checks:

- All 49 codec vectors, including the six frozen vectors; 35 malformed vectors
  also reach the home and receive the specific `stead-invalid-command` NACK.
  The 65,537-byte vector now reaches that native boundary after the encoder fix.
- All 14 trusted-context fault scenarios, with denied operations and unchanged
  protected state; these remain synthetic owner-controlled fault injections.
- Current state `on-save`/`on-load` round trip, specific unsupported future and
  counter-state rejection, and denial of an outsider's fixture-control poke.
- Two concurrently submitted, different-principal CAS mutations from revision 4:
  `~zod` receives the accepted revision-5 receipt and `~bus` receives
  `revision_conflict`. The reader sees the winning payload, with one additional
  journal event/receipt. This one executed race is not a general concurrency proof.
- Concurrent owner/outsider reads of the same document return owner content and
  exact opaque outsider denial. A sender reserving another sender's result path
  receives a specific watch NACK. Wider subscription races remain separate.

The reviewer also performed independent, read-only computation over the report:

- Reconciled all 747 successful terminal wrappers with their exact decoded UTF-8
  JSON and canonical serialization; checked all 53 failure wrappers. Successful
  wrappers include codec checks and administrative ACKs, not just accepted work.
- Rechecked 42 accepted receipt observations, including retries/recovery, against
  their trusted sender and correlated path where applicable. Their journal fields
  and command-domain digests agree with the captured records.
- Recomputed 34 distinct application-journal digests and both contiguous chains:
  33 events in the main project and one in the second project. Previous-digest,
  sequence, canonical command, decision context and receipt links agree.
- Recomputed exact Git SHA-1 OIDs for all 15 unique exported objects and checked
  byte lengths and immutable repeated observations. Eight exports contain recorded
  successful `git fsck --full --strict` results. The pre/post stopped-process
  restart export has identical head, object bodies and files.

These computations inspect captured real execution; the reviewer did not run
new native commands, restart ships, rerun stock Git, or operate the current
counter-regression/QA fixtures. A separately owned native QA replay is distinct
from this evidence assessment.

The bounded native project/work/document, deny-by-default policy, accepted
receipt/journal, restart and exact-object export results are now supported by this
recorded run. The 25 incomplete assertions, global-ID/metadata confidentiality,
broader channel timing/quotas, abrupt crash-window recovery, live/browser/admin
isolation, native Smart HTTP, and human qualification remain open. Supported
predecessor state versions are explicitly empty; rejecting the counter and future
shapes does not claim an implemented historical data migration. Prior failed runs
and their causes remain part of this note.

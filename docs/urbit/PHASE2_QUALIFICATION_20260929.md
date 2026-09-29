# Phase 2 team alpha qualification

Status on September 29, 2026: **incomplete**. The configured native, browser,
stock-Git, SDK and current hosted CI components have passing evidence. Natural
session expiry, a completed independent human trial, final local guard cleanup
and integration remain required. The six M2 issues remain open.

The current local and hosted application candidate is
`d9115056a04fd86cf55a07fd0d8a0bf0be84caaf`. It uses the pinned Vere 4.6 development
binary `f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833`
and kernel 408 commit `5a187fededc4582a34fcd6055c67bb63e0917b94`.
The reviewed integration additions are evidence, documentation and the CI
controller pin; executable native/browser/SDK inputs and packaged assets match.

## Current results

| Component | Observed result | Evidence and boundary |
| --- | --- | --- |
| Configured native | 760/760 checks; 71 positive unit arms plus deliberate failure; four cold restarts; 1,002.739 seconds | [Local record](evidence/2026-09-29/local-native-browser-d911505/index.json); all 77 installed files on four ships match. The whole guard is still live. |
| Real Firefox and native TLS | All 34 expected journey observations passed; complete response capture and empty browser cgroup | Same local record; two principals, Work/Docs, publication/privacy, conflicts/recovery, layouts, account change and logout. Five request failures remain scoped below. |
| Stock Git | Three native document histories; 43 successful commands | Exact receipt OIDs, Markdown/trees, destination-only ancestry and private-history exclusion; stock `fsck --full --strict` on each retained repository. |
| Independent SDK | 64 assertions and 41 public calls at `7f113a1`; clean shutdown | [SDK qualification](SDK_CONSUMER_QUALIFICATION.md) explains the reviewed `874a773` shared-guard composition and unaffected d911 invoked paths. This is not a new SDK execution. |
| Hosted CI | 792 passing observations, 779 distinct names; 71 positive arms plus deliberate failure; six resource controls and seven empty cgroups | [Run 36555130587](https://github.com/ScottTpirate/stead-urbit/actions/runs/36555130587), [exact artifact evidence](evidence/2026-09-29/ci-36555130587/index.json). Guardian completed in 1,889.794 seconds with complete EOF and exit zero. |
| Natural expiry | Pending | The unchanged session has a 30-minute native lifetime. An actual timed follow-up remains required. |
| Independent human trial | Incomplete | [First attempt](evidence/2026-09-29/onboarding-incomplete-20260929T104307Z/index.json): nine-minute deadline, zero captured qualifying operations/readbacks, no feedback or coaching attestation. Cause is unknown; launch/capture success is not task completion. |

The native and browser inventories overlap with individual assertions; do not add
these counts as independent tests. Before the final Git-helper correction, the
full host regression recorded 679 passing tests and one optional artifact skip;
the focused Git observation tests then passed 11 cases
using synthetic native replies, and 54 CI host controls passed. These host results
are distinct from actual native execution.

Independent review reconciled source bindings, all local unit transcripts and
110 native exchanges, the three actual receipt-bound Git probes, all four cold
restarts, browser capture and the stock-Git histories. Hosted review independently
reparsed its retained unit transcripts. Hosted migration and additional native
negative controls remain the pinned verifier's attestations because their private
output bytes are absent from the public artifact. No missing bytes were recreated.

## Performance and development foundation

The frontend uses scope-aware suppression of duplicate reads, deferred Markdown
loading/rendering, memoized previews and a bounded rendering path for dense text.
Native updates use bounded pages, queues and 16-event projection batches, with
actual interruption/recovery across the 68-event replay fixture. The SDK and
browser reach the same final business authorization.

The matching frontend contains 12 assets totaling 297,673 bytes, including the
258,065-byte app bundle. In this finite synthetic browser journey, useful-content
navigation took 2.630–4.232 seconds across three observations.
Eleven saves took 1.080–2.698 seconds to an accepted response and
2.751–7.359 seconds to visible confirmation. First and repeated
preview observations were 6.872 seconds and 170 ms. The local record retains all
samples, request counts, cumulative asset snapshots and the machine definition.

These timings include the measured user flow under a 25% browser CPU quota and
50% native quota on the same allowed CPU. They are not production percentiles,
import benchmarks or an unconstrained performance baseline. Cumulative asset
snapshots overlap. Of five request failures, two channel cancellations and one
offline command have test context; the query and updates aborts have no firm
initiating-stage attribution.

The [development flow](DEV_FLOW.md) keeps frontend type/tests/build separate from
native feedback and full qualification. Ordinary edits do not rebuild Vere.
Native source changes require the affected native lane; changes only to documents
and retained evidence do not require another full execution. Local tests need
Linux and disposable fake identities, without purchased identities or an external
server. Public hosting, real identities and network/custody qualification remain
later canary work.

## Milestone reconciliation

| Issue | Remaining acceptance work |
| --- | --- |
| [URB-060 / #9](https://github.com/ScottTpirate/stead-urbit/issues/9) | Natural expiry and final local lifetime closure. |
| [URB-070 / #10](https://github.com/ScottTpirate/stead-urbit/issues/10) | Final local lifetime closure and reviewed integration. |
| [URB-110 / #14](https://github.com/ScottTpirate/stead-urbit/issues/14) | Publication and reviewed integration of the current passing CI record. |
| [URB-180 / #21](https://github.com/ScottTpirate/stead-urbit/issues/21) | Integrate the qualified SDK composition and browser adapter. |
| [URB-190 / #22](https://github.com/ScottTpirate/stead-urbit/issues/22) | Integrate the executed replay/privacy/update and browser cases. |
| [URB-260 / #29](https://github.com/ScottTpirate/stead-urbit/issues/29) | Completed uncoached human Work/Docs trial with accepted saves, readbacks and participant feedback. |

Final acceptance must also close the owned native lifetime, retain failed attempts,
merge the reviewed integration and reconcile the constituent PRs without deleting
unintegrated work. [Earlier checkpoints](PHASE2_CHECKPOINT_20260928.md) preserve
the failed compiler, Git-helper, thermal and CI attempts as failures. Local team
alpha acceptance does not authorize a production deployment.

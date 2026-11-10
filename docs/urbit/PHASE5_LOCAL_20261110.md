# Phase 5 local candidate evidence

This record starts with candidate `02c1cefe8852bd95227cda9a4864fe4be55dc20a`
and records the follow-up native checks below. Pilot and cutover status
appear with the latest evidence.

| Check | Observed result |
| --- | --- |
| Host checks | 864 tests, one skip, plus the contract and plan checks. The browser client passed 39 host tests. |
| Replica custody | Synthetic positive and negative tests checked exact grants, expiry, changed generation, and private content. The verifier also refused a real synthetic native HTTPS archive containing private Docs. |
| Handoff rules | Pinned Vere evaluated the exact pure handoff library and all five test arms. The separate Gall install, sealed reload, and source-to-destination run are open. |
| Packages | Both role archives at this candidate passed offline archive, dependency, and target verification. |
| Dogfood history | Stock Git 2.55.0 preserved all 7,782 source OIDs and the pinned branch and tag, refused a divergent mirror, and independently recovered all 7,784 expected OIDs after deleting both rehearsal repositories. |
| Browser identity | The design was independently reviewed. A host signature vector passed and rejected changed inputs. Native login with the new binding profile remains separate. |

The Home archive SHA-256 is
`20902976e5ba297d0e198b35c20d5cfc8a3d0b39fa90606869e3d46d539a3e9e`.
The Identity archive SHA-256 is
`9919c1d5edb88b6c407299ec7dda382bfc750b8cf39ac2fc9ed47c0606b1f577`.
Both are in `.runtime/phase5-release-KZcD4uBl`. The final stock Git rehearsal
report is `.runtime/phase5-dogfood-main-sP5dnlWx/git/report.json`, SHA-256
`8f402533716335b480d2aab0e201195896e6094bdf37a35a5f1eacbb707954b8`.
The exact pure Hoon evidence used Vere SHA-256
`f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833`.

Seeded native attempts could not read the new source back from Clay.
The independent evaluator exposed a handoff variant type error before a full
install. After it was fixed, the stopped-checkpoint package attempt reached
desk staging before the existing thermal guard stopped it. The guard report
is `.runtime/execution-runs/phase5-warm-install-2de5f3kh/report.json`. No
Phase 5 native guard scope remained running. This run did not observe a
successful Gall install, owner bootstrap, or handoff reload.

## Native follow-up

The saved Home checkpoint pinned the older test adapter. Restoring those
exact bytes and moving the Phase 5 checks to their own adapter allowed the
guarded upgrade to run. It also exposed a type error in the packaged operator
thread when Khan invoked that thread. After the fix, candidate
`afaefd692121734c41db56ab63bcf979d2b43412` passed the 18-check native Home
upgrade. The Home preserved its authoritative database, served its packaged
routes after fresh bootstrap, and stopped cleanly.

The sealed handoff then passed 26 native checks using an isolated checkpoint
copy. Khan ran both packaged owner and TLS threads. The Home denied HTTPS
and bootstrap after sealing, saved a v6 vase, and preserved that exact vase
on a stopped copy. The destination remained sealed after reload, refused
the wrong ticket and an old generation, accepted activation once, and served
HTTPS after a fresh bootstrap. The old sealed copy remained unchanged. The
exact Identity archive installed on a new desk in the isolated fixture and
served HTTPS after owner configuration and bootstrap. This tested both roles
on the isolated fake. Member traffic between separate live ships still needs
verification in the pilot.

A separate new-desk Home install on an isolated fake passed seven checks.
The fake refused the live Home configuration. The packaged owner command
then configured the fake profile, observed its startup status, and completed
bootstrap. The exact Home served HTTPS and shut down cleanly.

| Evidence | SHA-256 |
| --- | --- |
| `.runtime/phase5-release-HKtZ3ain/home.tar` | `47c1a7bbf7911382a08f691b158b81d16b16b909a21b07ec2e6c6b4b2df0809c` |
| `.runtime/phase5-release-HKtZ3ain/identity.tar` | `7a2778a3349d8f427777c683916fc57065e9073052196832a6c4dfb649804b0c` |
| `.runtime/release-home-upgrade-7kir13b4/upgrade-report.json` | `316cccc466cb2eb922b1073d58d0f3c4b83053020fbfe3150b940d3a1a3f8196` |
| `.runtime/phase5-sealed-native-4nyh0QoA/state/report.json` | `af85258ce1cf4d11fc6a7035405922fae9b02a2f4022905e3c4d9b7210a2968d` |
| `.runtime/execution-runs/phase5-sealed-native-na8ht5ff/report.json` | `f202b2b6ded8b3c58b18afcf3355f6f529f59aecf00acdaa465c114c01dc3b21` |
| `.runtime/phase5-fresh-desk-3Cvdmu2Q/state/report.json` | `d370496a9bf01784bbb308b1f9bf123e2006e1a5edc8ba2eea36cfcd449d1cb7` |

The configured four-ship suite then passed all 1,212 checks at commit
`a40ee91f6e5baff5db8a82c8e25e9ba2fd0744f1`, including 17 handoff checks.
The Home denied a fresh member write while sealed, reloaded the exact saved
vase after the old process stopped, and required the correct ticket and
generation. The original receipt and member Work readback matched after
fresh bootstrap. The suite also verified independent native member grants,
private document visibility, and revocation. The run took 1,132.488 seconds.
The guard stopped all four test ships, and the previous disposable fixture
was restored to its original path.

| Evidence | SHA-256 |
| --- | --- |
| `.piers/fakes/logs/team-check-20261110T223833Z.json` | `b67cfa9990912bc91820c003beba27d68d048684f55843ce13a0fb40b775c247` |
| `.runtime/execution-runs/four-fakes-1j6zx6gp/report.json` | `541016eeac91e6760134e7a023d73d780a1d253d00ec7937d63f258604cf292a` |

The continued host suite ran 878 tests with one skip. The separate bounded
pack store recovered 7,803 objects and the exact two refs. Home still needs
to authorize and commit the immutable pack digest with the accepted refs
before full-history native Git serving. The signed cross-ship verifier
checks the transfer and journal evidence and issues a candidate directory
record. The source retirement and destination activation transitions are
still needed for a cross-ship authority move.

The synthetic pilot needs a qualified live runtime and startup fence on the
chosen host. Dogfooding also needs the native full-history Git path and the
approved change of write authority.
[Pilot checklist](PHASE5_DEPLOYMENT.md) · [Git rehearsal](PHASE5_DOGFOOD_REHEARSAL.md)
· [Custody and handoff](PHASE5_CUSTODY.md) · [Cross-ship verification](CROSS_SHIP_PROJECT_MIGRATION.md)

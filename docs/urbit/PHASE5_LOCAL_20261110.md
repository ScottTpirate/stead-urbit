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

## Home v7 and full-history readback

The Home and Identity archives built from
`7d0d025df091abe0dcaf013c048e9b490f7b763f` passed offline verification.
The packaged v3-to-v7 Home upgrade passed all 18 native checks. A separate
21-check native run exercised the packaged owner handoff commands and the
project retirement fence. Home refused pack staging on the retired project
and preserved the exact retirement record after a cold restart.

A two-ship HTTPS run passed 24 checks. A member logged in through the
separate Identity ship, created a project, reviewed and accepted the
owner-staged pack, and received the same receipt on a repeated request.
Home denied anonymous review, the wrong snapshot and epoch, and inline
repository creation after acceptance. Stock Git 2.55.0 restored all 7,803
objects and both refs through the authorized private readback helper. Home
returned the same receipt after a cold restart and a fresh member login.
The five native pack tests ran in the same test with the fixture correction
from `ac40202`. The test applied the changed Hoon to a stopped synthetic
checkpoint. The separate upgrade run installed the exact archive.

The independent UI review found a late repository response could update the
wrong project and that Overview Refresh missed an operator-staged snapshot.
The browser changes fence those responses to the current project and session
and refresh repository status on request. Type checking and 40 host browser
client tests passed. Headless Firefox passed 30 rendered cases with synthetic
Home responses, including discovery of a staged snapshot without a reload.

| Evidence | SHA-256 |
| --- | --- |
| `.runtime/current-v7-release-sHVJU892/home.tar` | `c75b5ab16844211b22c2f85b33b67a8bd2c5ae48389ba533053d332d74327a66` |
| `.runtime/current-v7-release-sHVJU892/identity.tar` | `5d5712b0c85430b9e997b6384bc5247c35956a502b5f7ec6ac8f4acacb0bdd59` |
| `.runtime/release-home-upgrade-xasp5rf2/upgrade-report.json` | `728667558d2a36646908c6b577b5036f9f423615ecdadd7363374729794b6a63` |
| `.runtime/current-v7-native-oSGcvOt0/state/report.json` | `fe6f846cf53a8004db6bb017b05486992a7ec0c931eb75e8a53d52d1256bf74d` |
| `.runtime/current-pack-team-GBZGf4jN/state/report.json` | `4fab3337054ba2edd1fd84a8975adc46e7d60ef30d9202257b003cebe4b52492` |
| `.runtime/execution-runs/current-pack-team-ci37jerg/report.json` | `fdc7d517c1ffbd29ea74df8f008f9183ae76be9e7db7cea497a539f02f4ded7b` |
| `.runtime/web-render-tests/report.json` | `dc0cace06f2e089713d513dcbc670aff5381e75f2f3a764ddadea0de487e2c96` |

## Candidate follow-up

The initial run confirmed that renewing the identity binding alone leaves
an expired project grant in place. Candidate
`8055b62a86f5b10378ce14b97a5b6bce7b5f7eaf` passed a 47-check paired native run.
The original creator explicitly renewed the grant with a fresh binding.
Home rejected a stale policy revision and preserved the exact renewal receipt
and restored write access across a cold restart. Four focused native cases
also covered grant ownership, replay, revocation and project retirement.
The SDK v3 export lock binds the updated command contract to its source.
[Grant renewal](PHASE2_CONTRACT.md)

After five more accepted writes, the owner retired the project at its exact
journal head. The private owner command retrieved nine original records
across two pages, verified the complete 59,069-byte journal and published it
atomically. Home refused active-project export, mismatched migration intent,
and a later write to the retired project. The separate full-history approval
and stock Git restore passed again in the same run. Both disposable ships
stopped cleanly, and the original checkpoints were unchanged.
[Frozen journal export](CROSS_SHIP_PROJECT_MIGRATION.md)

The exact Home archive passed all 18 v3-to-v7 upgrade checks. The exact
Identity archive passed 13 clean-install checks, including native HTTPS
after fresh bootstrap and after restart. Both native processes stopped and
the recovery sources stayed unchanged.

| Evidence | SHA-256 |
| --- | --- |
| `.runtime/current-v7-candidate-U1tmyUht/home.tar` | `27513dbbcbea68de7bfca0c8ebdac92e941173a33ebd03833df714a3effce198` |
| `.runtime/current-v7-candidate-U1tmyUht/identity.tar` | `64203e9ea21615a372c9b545a7f83c1190bdd95c72e9d281e556bdc582a80cff` |
| `.runtime/current-phase5-native-ciw0ifv4/state/report.json` | `6a12abf1a569d96c45f3ef2060884af0f529aee387f4f64116bb0a3a005a9b95` |
| `.runtime/execution-runs/current-phase5-native-_n71uk30/report.json` | `292d54c97d292e050acb6e226627a7be8ab4fe68c3b62be78531b94bbac3a1b2` |
| `.runtime/phase5-creator-renewal-native-InTMDQYE/state/report.json` | `efb9e4fad1ae56bdea3b622a25a77309d6a2494cbe2729293bf50f960905d14b` |
| `.runtime/release-home-upgrade-qxixy45b/upgrade-report.json` | `af62d65fccd89b9175b80001ba153517d5954f4e3dc970d5a5cc6062864ab979` |
| `.runtime/release-install-mm640nyn/work/report.json` | `6b5d7cca15bc058b17e184cc88e0ecdf98aef807e43299ae186242e039ae39c9` |

## Retirement limits and latest archives

The final native change checks the project journal's record count, record
size and total export size before the first retirement. Six native tests
passed, including the exact 64 MiB boundary, an oversized journal that leaves
the writer active, and a retry that preserves the original retirement record.
Both the retirement and pack-approval tests are now in the normal guarded
team test inventory.

Both role archives from `f18f6417f5170fb0c8c15747f9488792fc614d13` passed
offline verification. Its exact Home archive passed all 18 v3-to-v7 upgrade
checks. A new desk on a copied disposable pier installed the exact Identity
archive and passed eight checks, including packaged owner bootstrap, HTTPS
routes, fail-closed reload and exact Clay readback. The source pier stayed
unchanged. The host suite ran 898 tests with one skip, and the follow-up
inventory verification passed all 18 cases after registering the additional
native arms.

| Evidence | SHA-256 |
| --- | --- |
| `.runtime/phase5-final-candidate-M29muuSS/home.tar` | `524d958b010053814cbc2046e1f6fe621782aaf7de67e73584cbae30a2c64815` |
| `.runtime/phase5-final-candidate-M29muuSS/identity.tar` | `c9392345ebc4ccec3e526642bb5d853cffcf26ef7da259455273cb2a7a04751a` |
| `.runtime/phase5-retirement-export-admission-native-2nh3r1uy/state/report.json` | `1a188d0c6668deac17b2e1dfe4d2f7275cadd9a83440de9e897376dd4d6c4edd` |
| `.runtime/release-home-upgrade-6sw5b4ld/upgrade-report.json` | `b85eff8003ee08bede6a0e72a33c7515598d442b41020346fa375def78685282` |
| `.runtime/phase5-final-identity-fCweWGv6/state/report.json` | `bc91808a9b5a483985d60f845477118af807d435e3627dc9610fac9c29f0e7e8` |

The live pilot needs a qualified runtime and startup fence on the chosen
host. Dogfooding needs stock-client access and pushes for the full-history
profile and an approved change of write authority. The cross-ship migration
still needs complete project snapshot export and native destination replay
and activation. The separate same-ship handoff passed the earlier native
qualification above.
[Pilot checklist](PHASE5_DEPLOYMENT.md) · [Git rehearsal](PHASE5_DOGFOOD_REHEARSAL.md)
· [Custody and handoff](PHASE5_CUSTODY.md) · [Cross-ship verification](CROSS_SHIP_PROJECT_MIGRATION.md)

## External pack qualification

On a guarded pair of disposable ships, the new native decision endpoint
passed anonymous, wrong-project, and revoked Git credential denials. The
native Home issued the member an individual read credential, refused write
credentials for the external snapshot, and returned the exact manifest over
Eyre before revocation. All four newly inventoried native arms passed; the
deliberate failure control also reported its expected failure.

The subsequent 29-check guarded run combined native Home authentication,
private HTTPS Git serving, and stock Git. The mirror clone and fetch returned
the exact refs and all 7,803 reachable objects of the pinned rehearsal pack;
strict `fsck` passed. After native revocation, the Git HTTPS adapter returned
401 with no body and stock `ls-remote` returned no refs. The adapter used a
loopback transport shim for the older fixture’s native port. It and both fake
ships stopped at the end of the run. Private evidence:

| Artifact | SHA-256 |
| --- | --- |
| `.runtime/pack-read-compile-IaOPe9vz/state/report.json` | `06f359570a6e8b0283176c8efb8b9be92fe7ff0ce05256073426b5e1c681e207` |
| `.runtime/pack-read-smart-http-x5csBSmY/probe.py` | `607de7e37c8c8df5e51f5bb7687e55b8c9b077019e6d856864db926fb5850ed3` |
| `.runtime/pack-read-smart-http-x5csBSmY/state/report.json` | `d112b3c5094fbd98c2e2f827b3e993de27eee8e69b3e80635d10bb6fc1432551` |
| `.runtime/execution-runs/pack-read-stock-mxga75vl/report.json` | `28fa5740ed9870f5c621b3cc234ffa99164268b84143fd91a65614f943a25fc3` |

The packaged candidate at `e2f9a2ec1a1ac7367f35c336506e6704b6529f98` includes
the new read-credential controls. Both desk archives passed offline verification
against their exact declared targets (Home `727ea58b8c61602812fc998d1b0c9e0b1e88ab6842196cb03fe22560ddaa6e19`,
Identity `091777f92f1f76bb3dc142bdd9a5c7d486650aeff890873f842e0a45e5bbf7a7`).
The focused Firefox journey approved the snapshot, issued a read credential,
showed no write action and removed the credential after revoke using synthetic
HTTP responses. Offline package verification does not replace native upgrade admission.

### External write ledger persistence

Five route-free native tests called the actual Home's load and save arms on the
pinned runtime. A valid v7 state stayed v7. An accepted v8 ledger survived two
load/save calls with its exact manifest and receipt. A pending v8 job stayed
pending; its old incarnation could not commit. Home rejected empty, corrupt,
wrong-scope and unsupported future envelopes. The review fingerprint included
the authoritative ledger and excluded the rebuildable projection. The
disposable test ship stopped cleanly. This qualifies the saved-state handling;
no external push route, production upgrade, or full-history ref write is open.
The private report `.runtime/home-v8-load-ur37o42e/state/report.json` has
SHA-256 `dc34966cbb7234306f40b7b096eb78ceedf3795593fafcd429f4fd03e87db1c4`.
The Home v8 and Identity v1 packages built from `4d91be1` passed offline
verification. Archive SHA-256 values are
`e6493f1bb0d277002cf533fc7472260f6ccf28d1adda6ccf28a389ebedd258a4` (Home)
and `05c9271630d9fcf8360fac208108486000c3ad6320ef1efbcea068456c52c082`
(Identity).

The native read selectors passed five checks with the same accepted v8
snapshot selected for the browser and the Git worker. A separate native
selector check confirmed that an accepted ledger uses the latest exact
receipt and that genesis and pending-only ledgers retain the initial anchor.
The focused report `.runtime/selected-read-retry-83tziogd/state/report.json`
has SHA-256 `27266137cc2d835c5e3c385a99d38f87d84e3cecde948c668defaee3473ef0b4`.

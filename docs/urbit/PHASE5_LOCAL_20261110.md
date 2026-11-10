# Phase 5 local candidate evidence

Candidate `02c1cefe8852bd95227cda9a4864fe4be55dc20a` is a local checkpoint.
The live synthetic pilot and the native dogfooding cutover are still gated.

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

Before opening a synthetic pilot, finish exact Home and Identity native
installation, restart, and protected workflow verification. Qualify the
live runtime and startup fence for the chosen host. Before dogfooding,
qualify the full repository under a larger native storage profile and complete
the owner-approved move of write authority. Cross-identity project migration
with epoch advancement still requires its own transfer and fencing proof.
[Pilot checklist](PHASE5_DEPLOYMENT.md) · [Git rehearsal](PHASE5_DOGFOOD_REHEARSAL.md)
· [Custody and handoff](PHASE5_CUSTODY.md)

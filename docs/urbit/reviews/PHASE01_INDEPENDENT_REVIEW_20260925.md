# Bounded Phase 0/1 independent review, 2026-09-25

Reviewer and independent test owner: agent `/root/independent_review`.
This is agent review and observed execution evidence, not human approval or
Phase 0/1 completion. Origin fetch/push was verified as
`https://github.com/ScottTpirate/stead-urbit.git` before this write; the original
Stead upstream remains read-only with `DISABLED_UPSTREAM_PUSH`.

## Reviewed source scope

The source review covers
`87ea9e199a748a86daf1a9d95d4946e65b45c3ba` through
`072c401c072210ee62660b411289a3d799114a4a`, including the compiler corrections
through `c299f19acf0f7afb368d22c85f91c60f3af8515b`. Later commits on PR 42
are outside this source disposition unless separately reviewed.

| File at `072c401` | SHA-256 |
| --- | --- |
| `native/core/desk/app/stead-home.hoon` | `a740af8c1d09311d76dfde521b2db6fcd59b3eca56bd64fd2f934b4d5a0c4eea` |
| `native/core/desk/app/stead-observer.hoon` | `16589b4f9f51782d0907a7c186e3fcff6625c713bb64006f37330d6056645e45` |
| `native/core/desk/lib/stead-core.hoon` | `4c183ef6283030437af5e1433e3fbf80f414757bcede4cab1282fc71ff5f34de` |
| `scripts/urbit/urgit_audit.py` | `dceae3d2c44a4be9fbdb4a776f40c428914872ad818ce1cbc1486d3c839f4e98` |
| `tests/urbit/test_urgit_audit_safety.py` | `82095e98e5ea38595b644dff70fee927f36bd665905ec703ba8d52b5e5f360e1` |

No source blocker was identified in the bounded Hoon corrections: the
predecessor container map receives its intended recursive mold; the three
fixture route comparisons retain the same branches and fail closed otherwise;
helper placement restores the ten-arm Gall shape; and the observer's explicit
list narrowing, nullable tail rebinding, tall syntax and path mold remove
compiler errors without removing authorization, outcome correlation or event
recording. Native compilation is separate evidence below.

Independent review found that the Urgit host importer could accept a `passed`
report with empty, partial or false check rows. Commit `072c401` requires exactly
the fourteen frozen unique names, all true for a pass, retains failed partial
reports and copies the original untrusted report bytes separately before
assigning a host disposition. Source re-review found no remaining blocker in
that correction. The integrator reported 24 host/mock boundary tests; this
reviewer did not execute that suite during this audit.

## Native evidence inspected, with execution ownership kept separate

The integrator executed the current compile/probe and smoke runs. This reviewer
read `.piers/fakes/logs/core-check-20260925T095919Z.json`: 50/50 checks, status
`pass`, classification `local-real-native-compile-probes`, and explicitly
`qualifies_phase:false`. Its SHA-256 is
`a05fc950fb74dfb92b89314b2e8f9998da7d84527aed39be5608afaf43cb8c90`.
The corresponding native input digest is
`3d4eeb5b1e6e897e5659a9f48df6e18f410e23fb40c00b99e3395b6e7d3d0090`.
The inspected smoke report `.piers/fakes/logs/smoke-20260925T100137Z.json`
records `pass`, SHA-256
`6d15137f3e771a5e3ecb4a331b175c5124faf90e9d6f1692d5d66c77c8132cd2`.
Both carry guard run `b71358a9b420beb4232ebfaa747cd730`. These are inspected
integrator results, not independent executions or a full current qualification
gate review. The full core gate and final source/guard binding remain separate.

This reviewer independently invoked `python3 scripts/urbit/urgit_audit.py` at
10:28:35 UTC after the integrator stopped the four-ship environment and released
the native slot. The invocation began at Git HEAD
`1c7104697efc1c66cbcbe20a40af9aa77f74d798`; its immutable runner/helper/pins
were verified unchanged afterward. The result is **failed, zero of fourteen
checks executed**: the common guard stopped the fresh ship during boot at a
maximum observed 92 C. It is not a failed Git vector and not a conformance pass.

Local retained directory:
`.runtime/urgit-evaluations/20260925T102835Z-2mgo4s0g/evidence/`.

| Artifact or binding | Exact value |
| --- | --- |
| Guard run | `cb324363de6f78b82f1d10ac3b16f137` |
| Guard result | Failed; `GuardError: Thermal ceiling reached`; 372.978 seconds |
| Runtime / sandbox / runner exit | `1 / 1 / 1` |
| Thermal / CPU policy | Start 75 C, stop 90 C; one CPU, quota `5000/10000` |
| `report.json` SHA-256 | `66b064b9650660757057cd69fa1b5fffeaea249a76c6ba3e019dace2833880a3` |
| `evaluator-report.json` SHA-256 | `a4d83e9b295d6e0880019b9f48641b23fa21e126f90211df54c06f98be525789` |
| `execution-guard.json` SHA-256 | `f8aedb6a165d52ba18d42a1b889a1ae01de89d08029620771e41b9843215a479` |
| `SHA256SUMS.json` SHA-256 | `96794899e17a97a2bf60ff5aa6b3363605a56e0853201b609b22f6b55e606132` |
| Evaluator helper SHA-256 | `bd14bb9088a62420d65350a85c98553c48f4743adf05d7d61a3e8022a56d8f91` |
| Guard source SHA-256 | `7166d197a6e3879f21c22637f2bd3074ff90975c33a2149f6e07763e2eeaa04e` |
| Candidate lock SHA-256 | `50a90b296fa40e5a9178999cb2709682884812a98e2b133f6261eb5ec3934561` |
| Toolchain lock SHA-256 | `4a209c10cf1756eb0f7357cc3eca8250bf66c239b4cd0ca31a8c0886d4d304ee` |

All ten retained manifest file hashes matched. The evaluator recorded the stop
request and the guard recorded no additional cleanup escalation. After exit,
no `vere`/`urbit` processes were present and the repository native lifetime lock
was successfully acquired nonblocking and immediately released. No retry or
threshold change was performed. Temperature samples are host-wide and do not
identify the cause of the abrupt rise. Original local provenance includes host
metadata; any portable publication must document its transformations rather
than exposing the original machine identity or calling transformed bytes exact.

## Remaining acceptance and integration work

The live acceptance bodies of [URB-025](https://github.com/ScottTpirate/stead-urbit/issues/5)
and [URB-170](https://github.com/ScottTpirate/stead-urbit/issues/20) were re-read
with an explicit derivative repository argument on this date. They remain open.

1. **Git decision and execution:** recommend documented non-adoption of pinned
   Urgit as Stead's authority backend. Its ship-owner/repository-token routes
   and unfinished final-policy boundaries do not establish Stead principal
   authorization. Non-adoption can close the reuse decision without claiming
   redistribution approval or resolving notices for code never copied. It does
   not silently waive the live issue's stock-Git clone/fetch/push/fsck/OID vector
   criterion. The historical fourteen-check pass remains pre-fix evidence;
   this independently executed repaired-runner attempt adds a preserved thermal
   failure, not a repaired native pass. Full first-party notices/provenance remain
   prerequisites if adoption is reconsidered. Existing source concerns were
   reviewed, not dynamically exploited.
2. **Current native core:** finish the exact-source full corpus, capacity and
   migration lanes, all required negative controls and explicit typed
   dispositions. The integrator's reported 145 passed plus three incomplete
   rows must not be presented as a complete 148-case qualification. A subsequent
   saved-state correction needs its own review and native rerun.
3. **Actual delayed old leave:** retain the existing narrow local `leave-ended`
   result. Pinned Gall may drop that request before transmission, so it cannot
   substitute for an old inbound duct. The separately authored schedule fixture
   captures a real sender-Gall leave before kick, installs a fresh same-path
   reservation and delivers the unchanged original task to real receiving Gall.
   Its proposed classification, `native-scheduled-gall`, explicitly uses a
   synthetic queue/clock and claims no Ames/UDP timing. Actual positive execution,
   the specifically identified negative assertion, input/source/guard binding
   and a narrowly scoped qualification rule are still required.
4. **Six-task workflow evaluation:** the frozen 39-file package has identity
   `d78697102021b4b4837efd2d560668310fad5ab69fcbf98c7592a9cd0fff3e00`.
   It is prepared, not native prequalified. Reference, type-error and behavioral
   mutant controls must run before fresh baseline/assisted contexts. The two
   conditions require equal model/tool/budget metadata and actual private
   scoring. No efficacy or qualification claim follows from skill metadata.
5. **Records and approvals:** preserve current evidence, review exact final
   source, reconcile task dispositions and then integrate the reviewed stack
   in order: **33 -> 34 -> 35 -> 36 -> 41 -> 42**. PR 42 was an open draft on
   `increment/phase01-closeout-20260925` over
   `increment/local-dev-flow-20260924` when checked. Its current head
   `da15ea8ab50dcdbb2472440edb68c2b2f32b5d7c` is later than this bounded source
   review. Neither merging nor issue closure establishes phase acceptance.

The preserved original baseline/provenance and bounded Phase 1 threat/test
inventory have no newly identified source blocker in this review. The threat
map's future browser identity, installed-app trust, custody, recovery and release
obligations remain assigned to their owning later features. They are not
represented as runtime security results or silently added to this core pass.

## Test-owner work and independent review boundary

This reviewer authored the frozen task package and evaluation adapter, so this
record is not independent approval of that code. Reviewer
`/root/editor_tool_review` identified five admission/diagnostic/bound issues:
unenforced declared molds, lost evaluator failure output, incomplete prior
prequalification admission, late file inventory limits, and Python's decimal
digit limit. Bounded corrections and host-only negative regressions were added.
After the native candidate stopped, this reviewer executed:

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/urbit -p 'test_skill_evaluation_support.py' -v`

**20 host tests passed in 0.013 seconds.** Subprocess/native activity is mocked;
the positive admission specimen is explicitly authored data, never native
evidence. Tested adapter SHA-256:
`22bde729118039f075d00e205bd9fddafe3cdcb7452da72df7c2d85520807728`;
test file SHA-256:
`dd76288270c7243d454f8dc25e1ab24a15c6390c26c0e9bf70f8a6757f022492`.
The frozen 39 payload hashes were rechecked unchanged. Native prequalification,
participant runs and final independent adapter review remain unexecuted/pending.

The separate supplied-payload Gall checker was read at SHA-256
`77a138ff10ea96daf33694e6d82201a4c6d16a3740ec0a6d05f3f37b4076af55`
and its authored tests at
`7a59721ae96a0299bde484814f519a2facb5d0a05166cfa0a8e61a079000a242`.
No additional source blocker was found in its bounded canonical jam decoding,
exact leave/duct checks, receipt/observer/history consistency and current-leave
control. Its `native_execution_verified:false` admission boundary is appropriate.
This reviewer did not execute those tests or the native schedule.

## Follow-up: saved-state correction and missing native recovery controls

The bounded source scope now additionally covers the three implementation files
changed by `da15ea8ab50dcdbb2472440edb68c2b2f32b5d7c` and the integrator's
uncommitted `qualification_cases.py` recovery controls at the hashes below.
It does not approve other newly integrated runner/guard work or the whole PR
head. No native runtime was launched for this follow-up.

| Reviewed or tested file | SHA-256 |
| --- | --- |
| `native/core/desk/app/stead-home.hoon` | `3bfc0e45062ef0bc8572d5034a60b5b35f6502350f821129b5ba7a7cca0b2b9c` |
| `native/core/desk/gen/stead-save-probe.hoon` | `46f8b456fa79df03d979c119da97553a5e5a7b3c16d013402cfaf61a54866c93` |
| `scripts/urbit/core_check.py` | `b732d7854142bbd4bed1644baaec65a42a9a832a01ba076bb817d1de57db22aa` |
| `scripts/urbit/qualification_cases.py` | `1d06a75fea124e2a17b27167c8402090532d8f30425d69ecde8441094b088c71` |
| `tests/urbit/test_dev_flow.py` | `f200a9590255bb46589a65acc10b5e7eb84b304789b64382e775f1bcee4d5dfa` |
| `tests/urbit/test_qualification_cases.py` | `830bf21624fed55522b633df8c19d9924217e291a585fdc8c4849ab2ab99ef4a` |

No implementation source blocker was identified in this delta. Moving the
common `%stead-home` tag outside the `%1`/`%2` union preserves the serialized
noun shape while making the immediate version tags distinct. `on-save` remains
version 2; `on-load` retains predecessor validation/migration, unsupported-state
rejection and pending-subscription cleanup. The new probe calls the actual agent
save/load arms with a synthetic bowl, checks the version-2 envelope, requires
empty returned cards and compares the saved nouns. It targets fresh version-2
roundtrip behavior; populated-state roundtrip, predecessor migration and cold
restart still require their full native lanes.

The recovery additions use the native receipt read route and actual transport
sender. The migrated document result must match the currently authorized retry
and exact canonical bytes. The new legacy command has a valid version-1 body,
the current revision and a fresh request absent from predecessor acceptance;
it must receive `unsupported_version`. Closed-project recovery is checked for
both creator and member transports. Existing complete state/hash comparisons
cover the new reads and denials, and the input recipe includes the new command's
hash. These are proposed actual execution checks, not supplied state mutations.

Review found and corrected two host test gaps at the integrator's request:
the mocked compile success path lacked the new required save-probe token, and
the complete generated-command inventory omitted the newly executed legacy
input. The inventory now validates **5,065** distinct inputs. Added regressions
reject empty/wrong save-probe results while retaining their output, check the
unaccepted request's freshness/current revision, and check document-container
versus project recovery scope and explicit sender override.

Executed separately after native ownership was released:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/urbit -p 'test_qualification_cases.py' -v`: **28 passed**, 2.884 seconds.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/urbit -p 'test_dev_flow.py' -v`: **21 passed**, 0.141 seconds.

These **49 host-only results** validate input and adapter/lifecycle boundaries;
native process calls are mocked. They do not show that the new Hoon mold/probe
compiled or that migration/recovery passed. The retained first full native run
remains failed at `owner-control:roundtrip`; its three QA dispositions and later
unexecuted lanes remain nonpassing until actual qualification and review.

## Follow-up: complete skill test-arm discovery

Reviewer `/root/editor_tool_review` confirmed the five earlier adapter fixes,
then found that an exactly-two-space `++` matcher could omit a legal three-space
test arm. A shared matcher now recognizes two or more spaces consistently for
arm names, bodies and skeletons. Other top-level `++` spellings unsupported by
this bounded adapter are explicitly rejected, never silently skipped. A host
regression covers discovery/execution-inventory inclusion of an extra
`++   test-extra` arm and rejection of an unsupported multiline gap.

The same adapter suite then passed **21 host-only tests in 0.015 seconds**.
Final handed-off adapter bytes, moved by the integrator from `tests/urbit` to
`scripts/urbit/skill_evaluation_support.py`, have SHA-256
`dccf7e5919cf59b1633504b93ee3be65f29e26f786bf2f9ac0d7a97a6e2bd0ce`;
the test file has
`9c0ef4eb8bf40e35073dfead70e6851b9919c60bfc502aad47bf9bafeb6ef686`.
This supersedes the earlier 20-test adapter handoff without changing the frozen
39-file package. It does not supply native prequalification or participant
results.

## Guarded integration checkpoint: host results, final admission review pending

The next bounded review covered the new harness/RPC operations, read-only
package/workflow mounts, eager imports and lifecycle handling. The integrator
was still adding exact source/install evidence and separating execution from
qualification; those unfinished fields were explicitly excluded from final
approval. No native runtime was launched.

The selected suites `test_harness_safety.py`, `test_dev_flow.py`,
`test_gall_schedule_runner.py`, `test_gall_schedule_proof.py`,
`test_skill_evaluation_support.py` and `test_execution_policy.py` passed
**99 host tests in 1.680 seconds**. The in-development
`test_phase1_reconciliation.py` was excluded. These seven source hashes were
captured unchanged before and after that execution:

| File | Tested SHA-256 |
| --- | --- |
| `Makefile` | `0b85befd7bcec566d1531ffdf5ccb48e0fc7d983d9d7e9cbc1bac220559584df` |
| `scripts/urbit/harness.py` | `6a3ca36100d80884f592023f97320e60100ad786473e77875699ae2898431b8a` |
| `scripts/urbit/supervisor.py` | `0f528606e3c51f3e20f02f0155d3e5ac8d4b63038abb3b0fb588b3faba25c1dd` |
| `scripts/urbit/digests.py` | `8a976c8861b3d65fed22d8d4cd4a62f704e25c9f0e3f0105a3228df48549a845` |
| `scripts/urbit/gall_schedule.py` | `032810466f65d1dba7219f05b01307bedb0b174afada11d7cec0b31c36222c90` |
| `scripts/urbit/skill_evaluation_support.py` | `dccf7e5919cf59b1633504b93ee3be65f29e26f786bf2f9ac0d7a97a6e2bd0ce` |
| `scripts/urbit/execution_policy.py` | `da16e2e0fd32eb5b90706b546a7ea8332a65807fc8279f3bd765dcc18aaad9b5` |

The first inspected RPC draft left readiness set after a Gall failure and could
leave the skill lifetime alive after an unexpected exception. The integrator
corrected both before the test snapshot above. Two additional mocked RPC
experiments observed a failed Gall result clearing readiness, marking failure
and calling `all_stop` once; and an unexpected skill exception clearing
readiness, calling `all_stop` once and latching lifetime stop. These experiments
invoke the actual dispatcher with mocked native runners, not fake-ship tests.

A separate actual copied-Python import/cache experiment loaded all four runners
eagerly, edited the copied `core_conn.py`, and confirmed that cached function
objects remained old while every runner closure and the supervisor digest
changed. No source mutation occurred in the repository and no native runtime
executed. This extends the prior two-runner cache check to the new Gall and
skill lanes.

Two admission concerns remain for the next source review: confine prior proof
references to the read-only `/workflow` mount instead of permitting writable
`/state` artifacts; and bind all qualification-relevant bytes, including overlay
and spec inputs, to their claimed committed Git source rather than relying on
one earlier `git status` observation plus later hashes. The new Make targets
also need `.PHONY` declarations. These are requested corrections, not waived
requirements or a final integration approval.

## Final bounded source, proof and cleanup admission review

Reviewer: `/root/independent_review`. This follow-up reviewed the uncommitted
integration over `209bd33f047ef3dbc686557c1c70b8137080d337`, using exact file
hashes below. Remotes were verified before the authorized test and review
writes. No native runtime, live identity or external write was performed by
this reviewer for this follow-up.

The earlier proof-path and `.PHONY` findings are resolved. Workflow proof
references must be absolute paths inside the read-only `/workflow` mount,
cannot contain `..`, and the adapter rejects redirected path components. The
new RPCs accept only their fixed operation/condition inventory. Failed Gall
work clears readiness and stops owned children; skill work always ends its
owned lifetime, including admission exceptions. Final outer-guard completion
is still required separately from an inner report's status.

The source capture now checks actual bytes against every committed Git blob,
then compares the full mounted input inventories with that committed file set.
Bounded no-follow reads reject special files, hardlinks and redirected parents.
The supervisor checks the same inventories, tree identities and bytes again.
Only helper `__pycache__` directories are omitted from the script inventory;
the supervisor uses a fresh cache prefix inside its private `/tmp`, so omitted
host bytecode cannot supply the loaded helpers. Native/spec/overlay/package
inventories omit no cache directory.

That last distinction was required by an actual temporary Git experiment:
with an ignored extra native `.hoon` file, the earlier capture reported clean
Git status and `committed_bytes_verified=true`, and admitted its commit even
though the file was absent from `committed_files`. This was observed at harness
SHA-256 `dc7af0bed2660efab74c203f0594c0ec8ca07d85c74edebe09fdd7950badddc6`.
The integrator corrected the full inventory comparison. The permanent
regression now rejects ignored extra files in all four non-script roots and
an ignored native `__pycache__/hidden.hoon` file. Other new controls verify that
a clean Git status with `assume-unchanged` cannot conceal changed blob bytes,
post-capture source additions/changes reject, and FIFO reads refuse without
waiting for a writer. A real temporary Python-cache control loads deliberately
stale bytecode normally, then executes the changed source under the fresh
cache prefix. All these fixtures and Git repositories are synthetic and local.

The guard disk-error regression was corrected to inject its fault only after
the mocked owned child was actually launched. It retains the required cleanup
signal and stopped-child assertions. A separate fault after preparation but
before launch asserts that neither a child nor a cleanup signal is created.
This corrects the test's stage assumption after the added prelaunch lease
publication; it does not relax production cleanup.

Final execution: **113 host-only tests passed in 1.447 seconds**, covering
`test_harness_safety.py`, `test_runtime_guard_adversarial.py`,
`test_dev_flow.py`, `test_gall_schedule_runner.py` and
`test_skill_evaluation_support.py`. This is a fresh combined run; earlier
80-test and 68-test intermediate runs overlap it and are not additive evidence.
The ten file hashes below and the complete 20-module harness closure remained
unchanged throughout this final run. The latter was
`9732d93bc513e040eb11c9101af93a9330be469f6b241a51269b2ce9b4e32616`.

| File | Final host-tested SHA-256 |
| --- | --- |
| `Makefile` | `30e8db3ab2570c0bd05fa1677fecd49c2c7aaf7af3e262eff6b5f8873a9b5427` |
| `scripts/urbit/harness.py` | `6816cb078b781feb614f186f15526ebc183f6567a368d49e95e948a4b7d790ed` |
| `scripts/urbit/supervisor.py` | `b49275055befca8a39745a4c0a64c3de829213d1cdbf3c2ad83622997e19992d` |
| `scripts/urbit/digests.py` | `88e6333bd6c764f48fb8939bafa77c9eb236c5b3586a19fe1a1f6e48e27dc08c` |
| `scripts/urbit/core_test.py` | `457c41ee8df177d228c48cc92c58cd318903ac93d04b9df8d2285e5524c367b3` |
| `scripts/urbit/gall_schedule.py` | `3b6793a00deb41b8ad8e4d4a0a8e250943811708b3dc0210b9b9ebc7fa9ce491` |
| `scripts/urbit/skill_evaluation_support.py` | `dccf7e5919cf59b1633504b93ee3be65f29e26f786bf2f9ac0d7a97a6e2bd0ce` |
| `scripts/urbit/execution_policy.py` | `da16e2e0fd32eb5b90706b546a7ea8332a65807fc8279f3bd765dcc18aaad9b5` |
| `tests/urbit/test_harness_safety.py` | `16aee0f67ce3fa95fa5248677753df005edaa6c3cc96716361cb5cd44a51054e` |
| `tests/urbit/test_runtime_guard_adversarial.py` | `1d95245c8cd91c10952f2adc3b4b7e1983c155ef555e3d3d03697554dad57fe6` |

No remaining blocker was found within this bounded source/proof/lifecycle
review. The core and scheduled-Gall records now retain source commits and
installed/Clay-verified file hashes. Core `execution_complete` explicitly
awaits independent qualification; it is not phase acceptance. The final QA
producer opt-in and reconciliation semantics are separately assigned to
`/root/gall_schedule_review`; their native proof must still be reviewed from
actual completed artifacts. This record does not approve unexecuted native
code, the six-task skill evaluation, Git conformance, Phase 0/1 completion or
Phase 2 activation.

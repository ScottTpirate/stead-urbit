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


## Evaluator facts, narrow historical continuity and current nonnative evidence

Reviewer and host-test executor: `/root/independent_review`. This follow-up
retains actual current host results and source findings. It is not a native
execution, human approval or Phase 0/1 completion record. Remotes were checked
before each authorized evidence/review write; original historical files were
read only.

The evaluator record importer now requires exactly the three actual exchanges
for malformed input, encoding the large result and decoding that same frame.
It checks the pinned binary/arguments, exact raw input/output/diagnostics,
nonzero large-frame inventory, actual size over 65,536 bytes, linked frame and
result hashes, and exact expected decoded JSON bytes. A pure evaluator record
cannot also masquerade as a ship/Dojo record or satisfy another requirement.
The `evaluator-error-boundaries` proof is labeled `real-native-evaluator`, and
must reference all three actual commands in order. The host validator does not
independently execute jam/cue; authored validator fixtures are not native
results. Root reviewed the importer after this reviewer implemented these
bounded admission corrections.

The executed `test_core_conn.py` and `test_phase1_reconciliation.py` suites
passed **32 host tests in 14.008 seconds** at these unchanged source hashes:

| File | SHA-256 at that execution |
| --- | --- |
| `scripts/urbit/core_conn.py` | `e178a5c0ce619031b8da64376b99b429ac0f90dded293ac60fa1137447d53614` |
| `scripts/urbit/core_test.py` | `fc46acabdedce6b597015624dc9ad333f9179fd98c1578cba2c88ad4c7dde27d` |
| `scripts/urbit/qualification_gate.py` | `404e81ddc940ddf9030a266c2e835226eeef6944d581145be115d662461dfda7` |
| `tests/urbit/test_core_conn.py` | `fdca369149ed4eea7e8af94491b0835dfe4828faa38ffa9f571a30fb22a81d37` |
| `tests/urbit/test_phase1_reconciliation.py` | `1e894b70d1aed40b4e9f2a86ef11accebf17a52b303d9c0ae71c106ccae1536c` |

The subsequent historical-continuity change is limited to the two original
nonnative guard requirements and four fixed September 13 artifact hashes.
It retains the original guard hash
`7166d197a6e3879f21c22637f2bd3074ff90975c33a2149f6e07763e2eeaa04e`.
Admission requires actual historical/current source bytes to differ only by
the exact nine-line prelaunch resample, cancellation check and lease publication.
It also requires a current independent guard-source review and retained current
host-test artifacts. It grants no general stale-source exception and changes
no frozen requirement or assertion. Two targeted host test methods, including
adversarial subcases, passed **2.085 seconds** with unchanged gate hash
`ce0d8d0d87e9556940143943d7107099bfeb5c36eec6744342e555bfd292a6ab`
and test hash
`850dff88548529ef74555733c0b23616a4fb823d1cc57896e048f8adbc5b815b`.
Root independently reviewed and accepted that bounded implementation. This
reviewer does not describe review of their own gate changes as independent.

The exact current common guard is
`da16e2e0fd32eb5b90706b546a7ea8332a65807fc8279f3bd765dcc18aaad9b5`.
Whole-source comparison confirms the nine-line conservative addition, leaving
initial refusal, limits, scope, lock, lease and cleanup source unchanged.
The historical reports still show real 93/81 C refusals with no child launch.
The historical positive shim remains explicitly a real platform check using
mocked 45 C readings, with actual quota/namespace/read-only-lease output.
Historical lock release is supported by the completed guarded lifetime and
unchanged lock context; no additional historical lock readback was recreated.
No old observation is rebound to the current guard hash and no heat was
manufactured.

A fresh combined run passed **127 unique host tests in 1.628 seconds** across
`test_execution_policy`, `test_runtime_guard_adversarial`,
`test_harness_safety`, `test_dev_flow`, `test_delivery_cases`,
`test_delivery_evidence_regressions` and `test_delivery_suite`. Actual stdout,
stderr, command, timing, every observed test ID and unchanged before/after
source hashes are retained in
`docs/urbit/evidence/2026-09-25/phase1-nonnative/host-current.json`
(SHA-256 `5cfe4d692e6898113a8e1ff1dba3c78ebc4832a1fc2eb621d63f50c967fe4772`).
The execution correctly retains base HEAD
`8ed872e576e0ee0317ddf4f5824f38d4e7cf3c3d` and its then-uncommitted gate.
These are host regressions with synthetic sensor/transport records, plus real
lightweight Python-child, file, flock and cache controls. They neither start
ships nor demonstrate live event reordering. Their counts overlap earlier
runs and must not be added as distinct coverage.

The pending seven-item disposition index is
`docs/urbit/evidence/2026-09-25/phase1-nonnative/dispositions-pending.json`.
Its current source proofs bind exact reviewed home/core/guard bytes; assertion
rows link the actually observed host test IDs. The source review confirms
current typed authorization before receipt lookup/decode. The only N/A is the
absent external executor; native response facts/kicks keep their independent
mandatory delivery tests. Two historical items directly reference their
unchanged original proof JSON. Common commit/tree/runner bindings remain null
while native fixture compiler corrections continue. The integrator may fill
them only after comparing reviewed/tested bytes with the final committed
source and refreshing all artifact references. Null bindings cannot qualify.
The actual host-run identity must remain unchanged during that final binding.

Separately, source inspection of the saved-state probe's one-line `=+`
destructuring correction found that it preserves the same `on-load`, empty
card-list assertion and exact subsequent `on-save` noun comparison. This
reviewer inspected root's resulting
`.piers/fakes/logs/core-check-20260925T113418Z.json`
(SHA-256 `dcd4cf132b36d84454f79da728c5b9a81d4d7ab6b1ad3b60b6c00858b7e656ce`):
53/53 checks, stage completed, 48.395 seconds, unchanged input hashes and
`qualifies_phase=false`. This is root-executed compile/probe evidence inspected
by this reviewer, not an independently launched native run or full business,
delivery, predecessor or capacity acceptance.


## Initial builder semantics review: simultaneous-write evidence still open

This is read-only source review by `/root/independent_review`, with no builder
or native execution in this follow-up. The inspected source hashes were:

- `scripts/urbit/build_phase1_evidence.py`: `de7492a0c2d2a124cf87062f4e26131ab9c25c9dde3194b1a2b7556e7efe2387`
- `scripts/urbit/core_test.py`: `fc46acabdedce6b597015624dc9ad333f9179fd98c1578cba2c88ad4c7dde27d`
- `scripts/urbit/qualification_gate.py`: `ce0d8d0d87e9556940143943d7107099bfeb5c36eec6744342e555bfd292a6ab`

The builder reconstructs exact command sources, actors and routes, re-parses
retained terminal results, verifies restart launch/clean-stop rows, reconstructs
Git object identities and the recorded materialization/fsck command context,
and maps the frozen 66 native requirements across their proper lanes. It
retains failed stages and typed deferrals. Source inspection does not qualify
its delivery/capacity/scheduled-Gall replay paths without actual completed
artifacts and a final assertion review.

One concrete acceptance gap was sent to the integrator and builder author.
The frozen `v2-concurrent-cas` scope requires two simultaneous writes. Current
`core_test.py` submits two ThreadPool calls but retains only their final
sender/command/response records; it retains no start/end overlap evidence.
`CoreStages.concurrency` recomputes one winner, one conflict and one durable
acceptance, while reconciliation only checks the submission list length.
Sequential matching exchanges can satisfy those predicates. Before closing
that requirement, retain a bounded two-worker release and actual monotonic
call intervals linked to their exact transcript references, then verify both
calls started before either finished and that both exact submitted identities
match the recomputed requests/responses. This is a requested correction, not
an executed regression or a weakened requirement.


## Bounded concurrency correction and host validation

The integrator assigned the above concurrency correction to this reviewer.
Accordingly, this subsection records implementation and actual host execution
by `/root/independent_review`; independent source review of this correction
belongs to `/root/editor_tool_review`.

Two actual native client calls now wait at a bounded common barrier. The
producer retains readiness, shared release, start and finish times from
`time.monotonic_ns`, preserves failed-worker records, and requires strict
overlap before proceeding. Each successful call appends a separate interval
record to the same raw transport sidecar under its existing lock. That record
contains the shared release, exact times, sender/route/input digest and the
exact completed response transcript reference. The reader requires distinct
interval records after their own responses and exact equality between raw
interval bytes, summary metadata and the recomputed requested commands and
outcomes. Client-call overlap includes encoding/transport; it does not claim
simultaneous state mutation inside the authoritative ship.

The independent reviewer caught the initial summary-only timing field gap.
It was corrected before this final host run. Negative fixtures now reject
plausible summary-only time/release edits, invented overlap over unchanged
sequential raw records, missing/swapped interval and response references,
wrong request identities, nonfinite/reversed/unbounded clocks, and distinct
raw intervals that are sequential or merely touch. Actual lightweight Python
callbacks exercise barrier overlap and a retained worker failure. No native
process, ship or production identity is involved.

Final focused execution passed **26 host tests in 0.328 seconds**. These are
not additional native tests and overlap the earlier intermediate 25-test run.
Before/after source hashes were unchanged:

| File | SHA-256 |
| --- | --- |
| `scripts/urbit/core_test.py` | `dcf5ead9d3969322dfe880427090b108e0729e40d4a29aaadd4bc1dcf77c0916` |
| `scripts/urbit/build_phase1_evidence.py` | `1eb8f8dad1199ce9f3cf6667ef3f26e20774ab3eb50d54590e5b0b30e4b8fb63` |
| `tests/urbit/test_phase1_evidence_builder.py` | `73ec54971d7d50ed96cf858109078f6e270d8a4b9fa587ea6dad080705f70900` |

Actual command, source identities, count, timing and stdout/stderr are retained
in `docs/urbit/evidence/2026-09-25/phase1-nonnative/concurrency-host.json`
(SHA-256 `6a7b4c2e04eee0cacf0fd9b7af8b37b6dd3454ffb506348f9fefd4af572484c8`).
The correction is uncommitted at that execution and no rerun at a later commit
is implied. Source/test edits were then explicitly frozen for the integrator.
Native simultaneous-write acceptance still awaits the actual current-source
corpus, raw interval records and final independent artifact review.


## Public workflow feedback and observed pretty-output correction (September 26)

The integrator assigned this bounded implementation to
`/root/independent_review`; this subsection is the implementer's execution
record, not independent approval of its own changes. Independent source
review belongs to `/root/editor_tool_review`. Remotes were verified before
each write; no native process or participant was started by this agent.

The retained failed prequalification report
`.piers/fakes/logs/skill-evaluation-20260925T122058Z-prequalification.json`
has SHA-256
`931cae7989ce99cad377edd734aa8a7b267bac2fc2fec2f7819bcdcfcc2a093c`.
Its actual deliberate-failure-control output placed whitespace after `[` and
before `]`, including CRLF around the grouped decimal atom. The parser now
accepts that observed formatting while retaining whole-frame matching,
canonical decimal validation and text/noun bounds. A regression contains the
exact stripped stdout. Parsing that retained output in a host test does not
turn the failed native attempt into a pass.

The separate `skill-feedback` operation accepts only a candidate condition,
one of T01–T06, and integer attempt 1–3. It resolves a fixed read-only snapshot
at `/workflow/feedback/{condition}/{task}/{attempt}`, requires completed
reference prequalification, and ends the owned supervisor lifetime. T01–T03
run only their two frozen public examples; T04 runs only the public pinned-Gall
scenario; T05 executes all submitted test arms against the correct subject
without mutants or the private minimum-added-arm gate; T06 checks the supplied
assembly bytes and native generator. The six-task private scoring path and
frozen package are unchanged.

Participant feedback is a distinct `*-feedback.json` projection. It excludes
admission/reference proofs, infrastructure-control commands and private case
results. Late guard, final source or cleanup failure invalidates both public
and internal records. The independent reviewer caught an initial status bug:
an ordinary compiler failure would have been described as infrastructure
failure. Explicit guard/source/cleanup invalidation now preserves the
distinction, including a healthy-guard failed-compiler regression.

Actual focused host execution on the dirty tree based on
`4236ed5ad408ee8fc6e4cb2b9f699a16be7e4f84`:

- `python3 -m unittest discover -s tests/urbit -p 'test_skill_evaluation_support.py' -v`:
  **30 tests passed in 0.110 seconds**.
- `python3 -m unittest discover -s tests/urbit -p 'test_dev_flow.py' -v`:
  **29 tests passed in 0.167 seconds**.
- Scoped `git diff --check` passed. There is no diff under the frozen
  `tests/urbit/skill_evaluation` package.

These **59 unique host tests** include actual Python adapter/control dispatch
with mocked native responses; they are not native Hoon execution. The counts
and durations above are transcribed from the actual tool output; a new raw
stdout/stderr artifact was not written for these two commands. Exact final
source/test hashes, frozen before the integrator's next native run:

| File | SHA-256 |
| --- | --- |
| `scripts/urbit/skill_evaluation_support.py` | `50ea71b69bd240e01bbffcb04eefc2a5364a14f78ff633477586c97584247289` |
| `scripts/urbit/harness.py` | `aa798c754b3fc62da384ac14fdf43fba04205f88ffc3fd106ca4ff692855c5df` |
| `scripts/urbit/supervisor.py` | `d157a974075d2e1cbfb1ae07609182a3232c5a3f16b75c3e9287652434d774d2` |
| `tests/urbit/test_skill_evaluation_support.py` | `82a3391048f2201557f415dacd2fd9cc42ea1f6e3e79b20d2e33457b43ac2209` |
| `tests/urbit/test_dev_flow.py` | `f5d32daee698ab452be51df2c522d1dbeb39829a133e375b9bc4052798ea4364` |

The broker still must count and freeze each participant request, enforce the
equal maximum of three public requests per task, exclude native queue/guard
wait from active work time, and release public feedback only after the final
outer guard completes cleanly. The attempt field alone is not a durable
request ledger. Both participants must receive the same actual T02 starter
compiler diagnostic from completed prequalification before beginning. Native
prequalification and subsequent participant execution/private scoring remain
unexecuted for this new slice. Phase 0/1 and Phase 2 admission remain open.


## Independent smoke02 artifact and execution review (September 26)

`/root/editor_tool_review` independently reviewed the retained smoke02 evidence;
this reviewer did not execute the native run. The [portable bundle index](../evidence/2026-09-25/native-followup-attempts/index.json)
has SHA-256 `431dd989e13eaa37b82d4d089f6a562ad36cdaf69a84139366df1bfc172690e0`.
All **38 artifacts** match their compressed hashes, decompressed hashes and
original local bytes. Gzip is the only declared transformation. All **126
source-context file hashes** were independently checked against committed Git
blobs at `4236ed5ad408ee8fc6e4cb2b9f699a16be7e4f84`.

The smoke report does not contain its own commit field; its wrapper and retained
source context supply the commit binding. Recomputing that commit's source
closure yields harness SHA-256
`764ea8e1729fcd59dbb96413edb14041ec8e8b5f529663e3f0dace4a4b8966c6`
and smoke desk SHA-256
`dff85b9af5429c096e38789f81f1e6097368c244e84d2d1b5b49a66a1f6fcf89`,
both equal to the executed report. Toolchain and frozen smoke-corpus hashes
also match. Both workflow common examples are byte-identical to the executed
smoke library and agent; this does not prequalify the six workflow tasks.

Command-level review confirms all **12 frozen native calls: seven positive
ACKs and five expected runtime rejections**, including spoofed sender claims,
stale revision and the deliberately incorrect counter assertion. The recorded
request nouns, terminal frames and specific runtime rejection diagnostics
match the corpus. A graceful zod stop, distinct replacement process and
post-restart assertion confirm retained count 1. Smoke duration was **54.981
seconds**. The separate reset15 record reports successful restoration of four
stopped, hash-verified synthetic seeds.

Guard `efeca8d16129cc8e8d4bc9a903647841` matches the smoke report's run ID,
policy and guard-source digest. It completed with exit zero in **99.472
seconds**, actual `cpu.max` readback `5000 10000`, CPU affinity `[19]`, 102
retained thermal samples peaking at **71 degrees C**, and no cleanup escalation.
This same guarded lifetime later contains failed prequal01; its clean outer
completion does not turn that failed task into a pass.

Disposition: the exact smoke02 source, native positive/negative behavior,
restart and guard closure are accepted as scoped URB-020 evidence. Full issue
closure also relies on the separately retained safe-path host negatives.
Gall04/Gall05 and prequal01 remain failures. No current edited helper bytes,
Phase 1 qualification, workflow comparison, live-network behavior or deployment
are certified by this historical smoke run. The existing draft above is
preserved unchanged; the author confirmed this file was free for this append,
and derivative remotes were verified immediately before writing.


## Observed compiler stream and stop-socket race corrections (September 26)

The integrator assigned these two implementation corrections to
`/root/independent_review`; `/root/editor_tool_review` independently inspected
the final source and regressions without rerunning tests. The failed prequal03
report `.piers/fakes/logs/skill-evaluation-20260926T134510Z-prequalification.json`
has SHA-256 `42c9d00aade97d90121f790cee94abafd408a38726b88b36a135081f9d7bf28e`.
Its actual T02 starter compiler diagnostic is on stdout (`-need.u(@ud)`,
`-have.@ud`, `nest-fail`); stderr contains ordinary runtime diagnostics and
`eval: bail: %exit`, with exit code zero. The retained native attempt remains
failed. The shared execution/receipt predicate now recognizes the existing
compiler-error token classes in either bounded stream, while rejecting a
generic bail, process signal, result frame and oversized diagnostic.

The other observed failure was a stop request racing the supervisor's own
clean shutdown. Only missing/refused control-socket connections now fall
through to the existing lifetime-lock wait. A held lock still fails; timeout,
permission and reported control errors still propagate. The host regression
uses real temporary-file flocks to exercise both released and held cases.

Actual focused host execution: **32 adapter tests passed in 0.113 seconds**
and **31 developer-flow tests passed in 0.160 seconds**, using the same two
`python3 -m unittest discover` commands recorded above. These 63 tests include
the previous 59 and are not additive native evidence. Scoped diff checking
passed. Final reviewed hashes:

| File | SHA-256 |
| --- | --- |
| `scripts/urbit/skill_evaluation_support.py` | `d4f5404816ad1adae3309afd9cabeb425e87543b61a61c6cd885185948f147ca` |
| `scripts/urbit/harness.py` | `a63615cabf3c01698cec27bc6ae3f1381cc22be08d0c33859c992d96b8035c04` |
| `tests/urbit/test_skill_evaluation_support.py` | `dd084b0c58c4ef4fcb4835fd594200fd61cdfc2d60043e944984aaad39879da3` |
| `tests/urbit/test_dev_flow.py` | `4ca41c49a993bdc12032ec1b0e3df3a9bcd46923627603ee169e88e28dbdb66e` |

No frozen package changed and this agent launched no native process. The
integrator committed the reviewed slice as `97e8628`; subsequent native
results must be retained separately before qualification or participant launch.


## T03 probe type bounds and timeout abort (September 26)

The integrator's actual prequal04 report at source `97e8628` has SHA-256
`861e4f594850945dbc19a97553c9fa62facc8ccb2f32acdf2d383f7611f0bd80`.
T01 and T02 passed their reference checks. T03 timed out after 120 seconds;
the old adapter then queued T04's commit, which also timed out. The recorded
cleanup failed with zod exit `-9`. This attempt remains failed and does not
qualify the six-task workflow.

At the integrator's request, `/root/independent_review` implemented the bounded
adapter correction. `TimeoutError` and `subprocess.TimeoutExpired` now retain
the failed task, exit the task loop immediately and enter existing cleanup.
Later tasks remain `not_run`. Public feedback marks this uncertain native
execution as infrastructure failure even if cleanup later completes cleanly.
No timeout was increased.

The generated T03 probe now calls one fixed-sample gate for the same 12 frozen
cases in their original order, with explicit `agent:gall` and `vase` types.
It retains actual load calls, empty-card checks, expected saved state, the
initialized nonempty state before rejection, native rejection tags, unchanged
before/after vases, and repeated full-vase save/load comparison. Rejection-only
checks use pinned `mute:vi`. In pinned Arvo commit
`5a187fededc4582a34fcd6055c67bb63e0917b94`, `sys/hoon.hoon` lines 6292–6328 show
polymorphic `mule` reconstructing the success type while typed `mute` returns
`(each * (list tank))`; `mute` belongs to `vi` and has no top-level alias. This
supports the intended type-work reduction, but does not establish the cause
of the native timeout without another actual native run. The two-case public
probe still excludes all private cases and rejection setup.

Actual focused host execution was
`python3 -m unittest discover -s tests/urbit -p test_skill_evaluation_support.py -v`:
**36 tests passed in 0.156 seconds**, including the prior 32. Authored native
mocks prove that a T03 timeout queues no T04 command, an evaluator timeout
queues no T02 evaluation, cleanup is entered, and timed-out public execution
cannot be published as an ordinary task failure. Generated-source checks
preserve the exact frozen case inventory. These are host-only observations,
not Hoon execution. Scoped diff checking passed.

| File | SHA-256 |
| --- | --- |
| `scripts/urbit/skill_evaluation_support.py` | `6c32d46b4022085ea04d9e0a4a22d4069d1342d16ae8b96615ccfadb63c6c45d` |
| `tests/urbit/test_skill_evaluation_support.py` | `0a48ee6112e08f35b0fea703b00097a5dbb5aaa936773bc69dbec653ec7d1689` |

The source was handed to `/root/editor_tool_review` for independent review.
This implementing agent launched no native process. The frozen package is
unchanged; native prequalification, participant execution and phase closure
remain pending. Derivative remotes were verified before each write.

Independent source disposition: `/root/editor_tool_review` reviewed the exact
`6c32d46b` adapter and `0a48ee61` test bytes above and found no remaining blocker.
The reviewer confirmed all 12 ordered oracle cases, full-vase roundtrip, six
rejections after nonempty-state initialization, unchanged rejection state,
public-only filtering and immediate timeout cleanup. The reviewer performed
no native execution and did not rerun the author's host tests.


## T03 timeout localization, not a confirmed cause (September 26)

The integrator's subsequent prequal06 report at `decfe35`,
`.piers/fakes/logs/skill-evaluation-20260926T141133Z-prequalification.json`, has
SHA-256 `d09b8d700d11bd4e3838b7850df1751655257d23b3b75917d6acf9c6e05b13a6`.
T01 and T02 passed, but T03 again timed out at 120 seconds. T04–T06 remained
`not_run`, demonstrating the new abort path in this actual run. Cleanup still
failed with zod exit `-9`; the attempt remains failed. The preceding prequal05
was a guard freshness failure before any task, not a T03 result.

The timeout's cause is not established. Successful Clay byte scries do not
prove the imported agent or generator compiled. The full T03 report also jams
saved vases and rejection tangs before decimal rendering; the earlier successful
Stead save probe instead returns a small constant after checking saved nouns.
These observations motivate separating import/initial-save, case execution,
encoding and rendering rather than claiming either type expansion or printing
as the confirmed cause.

At the integrator's request, `/root/independent_review` added a small
prequalification-only import/initial-save generator. Its actual result will be
retained separately as `T03-initial-save-probe` and must be the exact initial
saved noun `[1 0 0]`. Receipt admission requires the diagnostic's native
observation, generator command, generated source digest and explicit check;
it cannot substitute for the original 12-case result. Public feedback and
final private scoring do not run this prequalification diagnostic.

The full probe keeps all 12 case assertions and full native vase comparisons.
Bounded `~&` markers distinguish entry, each load or virtual rejection,
completion and final encoded byte count. Pinned `sys/hoon.hoon` lines 8559–8564
lower `~&` to the native slog hint; the existing Gall fixture uses the same
size-marker form. The probe jams its unchanged evidence once and applies the
existing host `MAX_JAM` limit of 262,144 bytes natively before decimal rendering,
with `stead-skill-t03-result-jam-oversize` and measured size on failure. It
raises no limit, changes no frozen case and claims no completed execution.

Actual focused host execution of `test_skill_evaluation_support.py` passed
**39 tests in 0.185 seconds**, including the preceding 36. Additional authored
controls reject absent, incomplete, wrongly valued or relabeled diagnostic
evidence and its use instead of the full task. Mocked Python execution retains
the initial probe before a full-probe timeout and queues no following task.
Generated-source controls check retained assertions, the single encoding and
the bound before rendering. These are host-only tests; Hoon remains uncompiled
at handoff. Scoped diff checking passed.

| File | SHA-256 |
| --- | --- |
| `scripts/urbit/skill_evaluation_support.py` | `289295fd2650fe8a22f6e69a7657440ef8a43dd65791a78b7da9f4d509d20ded` |
| `tests/urbit/test_skill_evaluation_support.py` | `c3fe67b2b066dddcd730b1cfba12eea4cac210dd77304e46d40d2ea4de56dc30` |

The implementation was frozen and handed to `/root/editor_tool_review` for
independent review before the integrator's next guarded run. No participant
has been launched by this agent and no phase acceptance follows from this
instrumentation. Derivative remotes were verified before writing.

Independent source review by `/root/editor_tool_review` cleared adapter
`289295fd` and tests `c3fe67b2` above. It verified the unchanged 12 case paths,
separate initial-save evidence and admission inventory, one-line pinned hint
syntax, single jam and the existing byte limit before decimal rendering. The
reviewer did not rerun host tests or execute Hoon. Native results remain pending.

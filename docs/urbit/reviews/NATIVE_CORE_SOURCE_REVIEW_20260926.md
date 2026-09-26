# Current native application source review — September 26, 2026

Reviewer: agent `/root/gall_schedule_review`, independent test owner. This is
source and retained-record review, not new test execution, human approval,
implementation-merge approval or Phase 0/1 acceptance. No native process, test
suite or participant was launched or contacted for this review. Origin fetch
and push were verified as `https://github.com/ScottTpirate/stead-urbit.git` before
writing this new file; upstream push remains `DISABLED_UPSTREAM_PUSH`.

**Disposition: no application-source blocker identified within the frozen
public/synthetic four-fake profile. Issues #7 and #8 remain open pending current
complete native execution and independent evidence reconciliation.** One stale
linked scope document is identified below; it does not change the application
source disposition.

The application bytes inspected match commit
`8334a75cad4c2b063147e7e3352cdf76da0d5893`, including every one of the 22 Hoon
files under `native/core/desk`. The checkout advanced to evidence/documentation
commit `b7c2a10da7037476bc2e2d1c928a8e483e7101ff` during this review without
changing those application bytes. The reviewed semantics are the current
result of the initial `f52293f` implementation, the `54734c8` privacy/capacity
amendment, subsequent compiler corrections, the saved-mold correction in
`da15ea8`, and the save-probe binding correction in `c1e437f`.

This supplements, without editing or transferring acceptance from,
[the earlier bounded review](PHASE01_INDEPENDENT_REVIEW_20260925.md) and
[the design/trust-boundary review](URB030_210_DESIGN_REVIEW_20260926.md).
The live acceptance criteria were read with explicitly scoped read-only calls
to [URB-040 / issue #7](https://github.com/ScottTpirate/stead-urbit/issues/7) and
[URB-050 / issue #8](https://github.com/ScottTpirate/stead-urbit/issues/8).

The following source paths were traced for the requested application review:

| Boundary | Observed source semantics |
| --- | --- |
| Command parsing | `stead-codec` admits the closed eight-field command, known operations, UUID/scoped inputs, canonical decimal strings, bounded UTF-8 and payloads. It rejects duplicate keys and unknown fields. The digest includes the literal command protocol and zero separator. Raw cord marks do not authorize or validate business operations themselves. |
| Final authority | `stead-home:246–266` supplies `src.bowl` and home time to the pure transition. `stead-core:56–131,200–219` requires the current active, unexpired binding and exact four-field synthetic profile, then current action/resource/container authorization and authority epoch before duplicate receipt lookup. No caller actor field, sponsor or team ancestry grants access. Unsupported principal/profile modes deny. |
| Administrative authority | The fixed home service has explicit single-organization allocation/policy capability. Project creation records an explicit initial maintainer grant. Administrative status does not supply document-container ownership or ordinary content grants. Maintainers cannot grant/revoke the maintainer role, and delegated grant expiry cannot exceed the applicable current authority. This is the frozen synthetic policy, not implemented general delegation or browser authentication. |
| Atomic transitions and conflicts | `stead-core:151–278` returns a new business state and its accepted journal/receipt together. Current authorization and epoch precede idempotency; identical accepted bytes return the stored projected receipt without another mutation, different bytes produce request-ID conflict, and fresh commands compare the appropriate resource or policy revision. Rejection returns the original business state. No external build/message/model/deployment executor exists in this slice. |
| Private resource identity | Work is keyed by project/local ID; document keys include project/container/local ID; grant keys include project/local ID. No global cross-kind availability lookup remains. The single configured organization's explicit allocation administrator can inspect its project allocation metadata; adding another organization requires its separately scoped allocation design. |
| Reads and receipt recovery | `stead-core:322–460` checks current context, project closure, grants and typed scope before protected lookups/projection. Receipt lookup uses project/principal/request and rechecks stored resource/operation/container plus current authorization. The public receipt is a closed sixteen-field projection; project policy counters and journal sequence/digests stay internal. Known and unknown unauthorized resources produce the same opaque denial. |
| Document and Git boundary | `save-document` accepts only the frozen exact draft/page header and preserves the accepted Markdown bytes as a Git blob. Container ownership and project authority precede admission. Blob/tree/commit construction, collision checks, capacity and pointer/history updates precede the single accepted transition. Every export manifest/object read reauthorizes the selected container; individual objects must be reachable from a retained snapshot in that container. This is not Smart HTTP, pack ingestion, publication or a general forge. |
| Capacity and revocation | Ordinary accepted events are capped at 4,096. At most 128 retained grants and revocations per project reserve security capacity independently of ordinary activity. Exhausted revocation reserve or policy counter closes that project's protected reads, writes and recovery. The last admitted revoke can return its receipt at its pre-decision authorization point; later requests see closure. No receipt/history eviction or reopening bypass was found. |
| Saved state and migration | `stead-home` saves `[%stead-home %2 db]` and loads a common `%stead-home` envelope containing distinct `%1`/`%2` branches. The v1 path verifies bounded journal/receipt consistency and reconstructs content/policy/Git projections before rekeying documents and grants; it does not execute historical commands or reauthorize past decisions. Current and predecessor paths clear pending result reservations and kick prior subscriptions. Unknown envelope/version shapes fail. This is not validation of an arbitrary untrusted production backup. |
| Request delivery | Result reservations bind sender, current binding, project, request and command digest, with 16-per-sender/64-total limits. A later result registration or command prunes expired reservations; expiry is lazy. Commands reauthorize at actual execution. Read facts use the current request duct, while command results use the exact reserved path and then kick. The client requires correlated result content and ACK/fact/kick completion; ACK alone is not acceptance. Delayed old-leave correctness still requires the separate real-Gall schedule, not app-level source inference. |
| Observer and privileged routes | The bounded observer records metadata/digests and requires owner-local controls/queries. Fixture initialization, predecessor building, batch controls, binding mutations and administrative snapshots require owner-local `~zod`; they remain privileged test operations. Application `on-peek` provides no employee read API, but pinned Gall owner-local saved-state access and other trusted installed code remain part of the authority-host trust boundary. |

The saved predecessor codec is byte-identical to the initial `f52293f` codec.
The predecessor core differs from the original core only in its codec import
and name binding. It therefore retains the actual previous implementation for
migration and regression work, including historical weaknesses; it is not the
active public transition path. Owner-local predecessor controls are not proof
of adversarial cross-ship isolation.

The inspected limits remain material: this is one configured organization with
fixed fake bindings and owner-private containers; no live identity, HTTP/browser
session, general policy language, employee administration boundary, production
recovery or installed-app confinement is demonstrated. Shared runtime timing
and capacity are not constant-time/noninterference guarantees. These exclusions
match the frozen amendment and are not permission to weaken later gates.

Exact application hashes for the primary reviewed files are:

| File under `native/core/desk/` | SHA-256 |
| --- | --- |
| `app/stead-home.hoon` | `3bfc0e45062ef0bc8572d5034a60b5b35f6502350f821129b5ba7a7cca0b2b9c` |
| `app/stead-observer.hoon` | `16589b4f9f51782d0907a7c186e3fcff6625c713bb64006f37330d6056645e45` |
| `lib/stead-core.hoon` | `4c183ef6283030437af5e1433e3fbf80f414757bcede4cab1282fc71ff5f34de` |
| `lib/stead-core-v1.hoon` | `879615a5547d06a09d382c2bac4c5cb20cdf03236ddfdab79c9f1da15bd33cb5` |
| `lib/stead-codec.hoon` | `56e3d574381bbf8cdf29ca192c70eff256009f89d782e3ffe859b19c1321cbd7` |
| `lib/stead-codec-v1.hoon` | `ce4c7a69b03ee1761590c37e71ff49b9f63a1a2edd2aaa6dfbf75bc3c960584a` |
| `lib/stead-git.hoon` | `826b83485429c02f577c9b462ee6cddd3ab8ea1a099d33b66893f863d54c54d7` |
| `lib/stead-delivery.hoon` | `178cac634471554dae9928f8c38248751329314391061976a436a22a7075548d` |
| `ted/stead-client.hoon` | `e039355539b2aef4db0ac8137dae71984d9284abeaffd20a1d9fb110adb35c5f` |
| `gen/stead-save-probe.hoon` | `84899440be705a00f1bd9a7da38c3f8499ca13562e110aef53c9fac40f8e2ffd` |
| `mar/stead-command-1.hoon`, `mar/stead-command-2.hoon`, `mar/stead-result-1.hoon`, `mar/stead-result-2.hoon`, `mar/stead-fixture-1.hoon` | `fcd87c92acc16c2883b1dd4900af5064d1da910af317e93c327455cd56d9553b` |
| `mar/stead-control-1.hoon` | `643d9d5221b5b43230f864f11b1d6830ad2b32ffd64644c77ea70c0fa1ea8c5e` |
| `mar/stead-observer-1.hoon` | `e30d449181f121ea403b8d38e12d3b925362591ee516092f254852af0631a684` |

The complete native tree identity retained before/after core02 is
`7b0257ba03b0de93de319d55c5523fa481c302772471645987818da543ac4621`.
Current qualification still uses the v2 freeze
`a2336e5060c71c7c16849b3151cc024a598d6cdf867561452eff1338e3232670`
and the exact 73-row manifest
`f374349cc3ccd64993e3dade9a44e306854479c228b7f93d6559647006aee94c`.

The retained [core02 index](../evidence/2026-09-26/native-attempts/core02/index.json)
and raw report support the current interrupted-run wording. The raw report is
`fail`, with 90 passed cases, one typed incomplete case, one case interrupted by
`GuardError: Fixture stop is latched`, and 56 not run. No failed business-check
row is present in that partial corpus. The separately retained outer guard is
failed with exit 1 and thermal-ceiling reason, recorded 92 C against the unchanged
90 C cutoff, and has an empty cleanup-error list. The raw report's null inner
execution-guard field is preserved; the separate outer report does not turn it
into a passing run. Populated round-trip, migration/capacity, concurrent writes,
delivery/recovery, export and full independent reconciliation remain required.

| Retained artifact | SHA-256 of inspected uncompressed bytes |
| --- | --- |
| `native-attempts/core02/core-20260926T172751Z.json.gz` | `ff9a6db614b65368220f925a662fe844b22ad5f976713ad704916d0a03ab0bbd` |
| `native-attempts/core02/outer-guard.json.gz` | `44e281b4a59a6bf22fd320999ee8ed0d22384a20f0da8331bd658832c63307c9` |
| `workflow-evaluation/raw/private/baseline/native-inner.json` | `3bc3107217b91ebb0039bc9e773687b8bdc8b34532a02f149eeba56da921379f` |
| `workflow-evaluation/raw/private/local_skill_assisted/native-inner.json` | `74978a1039f0667c06accf04204861086327742b864717569d29f379131281ba` |
| `workflow-evaluation/result.json` | `b97f8c0a2c264eb66946464e55b11217d242b7231e00ffeb3bcd6db6a9ca5ab2` |
| `workflow-evaluation/independent-review-disposition.json` | `157123b875ed5fa55e9fe5941266a79ecfe6dd95cfef5464dc60abb950e050db` |

The preserved v1 workflow README/result correctly retain five verified passes
per condition and invalid T05 qualification. Both actual private reports contain
T05 correct/claimed-author evaluation and the outsider-granted runtime failure;
the remaining two mutant subjects were not executed. Complete invocations and
outer guards do not make the six-task mutation inventory complete. The current
record retains this distinction, requires a versioned scorer and fresh pair,
and does not assert skill efficacy, human approval or phase closure. I read the
published results and received independent-review disposition; I did not repeat
the other reviewer's full trace/timing/archive-member audit.

The four requested current status/runbook documents are consistent with those
boundaries at the following bytes:

| Document | SHA-256 |
| --- | --- |
| `README.md` | `ee75869439257b40c0e243d264ba7caaa78473cbfc3294a579c2fd06ad4660b1` |
| `docs/urbit/PHASE01_CHECKPOINT_20260926.md` | `10daec7e0b0c388bd104b2b30ebeac3106bdbfbf8fe9a217f7aee82daa3673e8` |
| `docs/urbit/TEST_RESULTS.md` | `6b28e12d64b170267d86f635bd2b6e7f1db12c816b56f4d17a255ca922e9ba1f` |
| `docs/urbit/DEV_FLOW.md` | `6a0f0bc45e44f524a94112b4f0e5f95bb3e00b74e3008f6e91da4b553daac65d` |

One linked document needs an update: `docs/urbit/NATIVE_CORE.md` at
`4b796067be3a5415b823e258c73f3b907c1e182bebbb3c89c4f6ce9f3d240eae`
still describes current v2 as uncompiled/unexecuted and assigns abrupt-crash
injection to later work. Current source has actual compilation/save-load probe
evidence and an interrupted corpus; the Phase 1 recovery lane remains required
but unqualified. Correct that scope wording without relabeling the interrupted
run or moving its required recovery checks out of the current gate. This finding
was sent to the integrator; no application or existing document was edited by
this reviewer.

The old hash-bound review remains unchanged at
`ae0edda0a91d5b89b1cd070c8685de8d73dbc190093563c8cd2d4dba1d51b717`.
This new source review cannot replace a completed guarded native run, the
specific delayed-old-leave positive/negative execution, the fresh workflow
evaluation, or independent acceptance of the exact final 73-obligation bundle.

Follow-up resolution, September 26: the integrator corrected `NATIVE_CORE.md`
at SHA-256
`25af0f2f5d17b2d82e912ee576f0a02f30338566bd35d5c25ded9447396ae5a6`.
The opening now distinguishes actual compile/save-load probes and the interrupted
90-case partial run from pending full qualification. Migration and controlled
abrupt-crash recovery remain explicitly required in Phase 1; production backup,
rollback and live identity migration remain separate. **The documentation
finding above is resolved by these integrator edits.** No application acceptance
or new native execution follows from the correction.

The integrator also corrected `DEVELOPER_GUIDE.md` at SHA-256
`b6976a495d75033f3e771a057f19a939fc1b38659bac78910592c22145df7918`.
Its pinned-toolchain/guarded-command wording matches the real checked-in lock
(Vere 4.6, kernel 408k-2 / Kelvin 408 at
`5a187fededc4582a34fcd6055c67bb63e0917b94`). A fresh read-only
`gh issue list --repo ScottTpirate/stead-urbit --state all --limit 100 --json number,milestone`
confirmed the seven live M0–M6 milestone identities and the thirty catalog task
assignments. The guide keeps that observed GitHub state separate from mocked
CLI tests and runtime acceptance. I changed only this new review's resolution
note; the older hash-bound review stayed unchanged. No tests/native were run.

# Phase 1 evidence mapping — 2026-09-25

Reviewer/test owner: `/root/gall_schedule_review`. This is a source and artifact
mapping, not native execution or phase acceptance. No runtime was started for
this review. The derivative origin was verified before writing this file;
upstream remains read-only. The integrator owns subsequent fixes and execution.

## Inspected baseline and observed failure

The manifest contains **73 requirements: 66 native and 7 other typed
dispositions**. This maps the runner closure recorded in
`.piers/fakes/logs/core-20260925T100137Z.json`; changes after that execution need
their own exact bindings. In particular, the integrator is extending
`qualification_cases.py` and fixing the saved-state mold during this review.
The gaps below describe the recorded baseline, not an assertion that those
subsequent fixes have executed.

| Inspected input/artifact | SHA-256 |
| --- | --- |
| `specs/urbit/v2/qualification-gate.json` | `f374349cc3ccd64993e3dade9a44e306854479c228b7f93d6559647006aee94c` |
| `scripts/urbit/core_test.py` | `054160ae4b779ca74dab99382f0c612476eeb746fbbe4726e9b66760f9de06f8` |
| `scripts/urbit/core_cases_v2.py` | `eaaf9035eed9ca7e99823c8698cfc9c1a9fbf6c9503dec75f82bcfdd593d0e6a` |
| `scripts/urbit/delivery_suite.py` | `35980a0e9dd2be0eda54cc0d1ac5582012e75359e0faf39a05005bd8eb08b180` |
| `scripts/urbit/qualification_cases.py` recorded by the run | `d8b3eddd5497b131166c3096b437c317dc825a4459b5fe024943ec124bd545fc` |
| `scripts/urbit/qualification_gate.py` | `4d11a0de57f24875634f3e6c276952cb76b8703df75be04b8adeffe2b1c80bd7` |
| Core report | `84a539f820b1f825b63b888a9c3414c291ea7a287134cb006b7ba32eabbc48f2` |
| Core transport `.jsonl.gz` | `a1309afeef68ff10b37b3f15031cb610372c99639b859408564d672793c8afc2` |
| Core transport uncompressed bytes | `6b3d62ef80342613c1d2f193182df37f178e0b955357840d1603a029f3c16006` |

The report records native tree
`3d4eeb5b1e6e897e5659a9f48df6e18f410e23fb40c00b99e3395b6e7d3d0090`,
**145 passed cases, 3 incomplete cases, 3,952 passed QA checks and 3 skipped QA
checks**. Its overall result is **fail**, with
`AssertionError: owner-control:roundtrip`. Concurrency, the dedicated delivery
suite and predecessor/capacity qualification were not reached. The 22 retained
one-shot observations are present, but they do not qualify changed source or
the unfinished aggregate.

The saved-mold diagnosis is supported by source: the old union repeated
`%stead-home` as both outer discriminators. Factoring it to
`[%stead-home $%([%1 db=state:stead-core-v1] [%2 db=state:stead-core])]`
preserves the serialized noun shape while selecting on version. The observed
failure enters the `%1` mold for a `%2` save. This is source reasoning, not a
passed repair: require a populated current `%2` save/load, an actual provenance
`%1` migration, and atomic future/counter/malformed rejection after the fix.

## Concrete missing mechanisms in the recorded baseline

1. `delivery-late-old-leave`: `delivery_suite` case `ended-leave-attempt` sends
   leave after the old subscription is already completed. Sender Gall may
   drop it locally. Its explicit missing assertion correctly keeps the case
   incomplete. It cannot establish the receiving boundary. The separately
   scheduled Gall lane below is the proposed replacement evidence.
2. `migration-legacy-receipt-projection`: `Driver.exhaustion()` checks the
   original migrated document command's retry, but does not recover that
   receipt and does not submit a never-accepted legacy command to current
   home. Add actual current-authorized recovery preserving digest/time/OID,
   the exact unsupported-version rejection, and unchanged native state for
   both. A planned recipe/hash without a call is insufficient.
3. `v2-security-reserve-exhaustion`: the same driver checks closed-project
   reads, retry and a revoked member's mutation, but not receipt recovery
   after closure. Add recovery against a previously accepted receipt in each
   closed project and require exact opaque denial plus unchanged state.
4. Three typed QA dispositions have no integration path in `core_test.run()`.
   They are not three failed business cases; neither are they green skips.
   The following section supplies a non-circular completion design.

Other native requirements have identified mechanisms in the table. Some are
composites: a resource capacity check alone does not establish all scoped
authorization, receipt, tombstone or revision behavior. The current recipes do
not specifically test updating an existing work item at a full 128-item
capacity, or allocating a new grant after a tombstone at full capacity. Do not
claim those stronger scenarios from the lower-count revision/tombstone checks;
the table identifies the actual combined coverage of the present scope.

## Independent completion without rerunning solely for review metadata

`core_cases_v2.Runner.__init__` accepts `review_evidence`; `Runner.review()`
requires an item with `verified_by: stead.qualification-gate/2`, exact typed
kind/status, artifact and bindings. `core_test.run()` does **not** pass that
argument. The unresolved records are:

| Requirement | Original immutable QA pointer | Required final disposition |
| --- | --- | --- |
| `scoped-private-metadata` | `/qa/cases/74`, check `projection-timing-and-all-metadata-nondisclosure` | Native composite: predecessor reproduction plus current scoped allocation, normal/retry/recovery receipts and authorized export evidence. Physical timing remains outside scope. |
| `no-effect-subsystem` | `/qa/cases/95`, check `no-external-effects-replayed` | Independent `not_applicable` with exact reviewed source and reason that this bounded profile has no external-effect subsystem. A lifecycle prose string is not the proof. |
| `receipt-lookup-order` | `/qa/cases/121`, check `source-ordering-property` | Independent `source_review`, with exact mutation/recovery paths, current authorization and receipt lookup ordering described. |

The first check runs before the later privacy and predecessor lanes. Feeding
its own final gate result back into that run would be circular. Recommended
implementation, owned by the integrator:

1. Make the execution runner retain the original QA checks and statuses. Once
   every runtime stage completes, record `execution_status: completed` and
   `phase_qualification_status: awaiting_independent_review`, with the exact
   deferred requirement IDs. Do not convert the three skips to passes or
   require `qa.status == passed` as a prerequisite to reviewing their later
   evidence. Keep any native exception, incomplete stage, unrecognized skip,
   failed check, source drift or guard failure fatal. Explicitly retain the
   old-leave case's limitation pending the separate schedule proof.
2. A separate read-only post-run reconciler validates the completed immutable
   core report, exact transport sidecar, guard record, scheduled Gall result,
   and independent source/N/A artifacts. It derives assertions from the
   concrete selectors below; it does not merely copy labels or trust a
   truthy `native` field. It writes a **new** evidence index and typed proof
   artifact, preserving every raw report hash and skipped record.
3. The reconciler records resolution of each deferred QA check in that new
   artifact. The native composite uses later recorded native facts; the
   source and N/A items use separately authored independent dispositions.
   It never marks the original QA case green and never calls `Runner.review`
   with a result whose only support is that same unresolved check.
4. Run the final qualification gate over exactly all 73 IDs. Success requires
   66 supported native items and all 7 correctly typed other items. A complete
   execution is not a phase pass. Missing, failed or stale review evidence
   leaves qualification incomplete/failed without requiring a 25-minute
   corpus rerun merely to inject review metadata.

The current report's real `owner-control:roundtrip` failure cannot use this
deferred-review path. A corrected native run is required. A future report
that reaches all runtime stages but records only the old final
`required-current-qa-assertions-complete` administrative failure could be
reconciled without editing it only if an explicitly reviewed adapter validates
the complete stage inventory and exactly the three known missing typed
dispositions. A generic “ignore failed aggregate status” rule is forbidden;
prefer the explicit execution/qualification split before the next run.

Recommended new reconciliation artifact fields:

- `protocol`, exact manifest artifact/hash, `status`, reconciler source/closure
  hashes, actual independent reviewer identity and reviewed scope.
- Immutable `inputs`: repository-relative path, SHA-256, size, encoding,
  uncompressed size/hash/count where applicable; exact JSON pointers and
  transport references for each cited execution fact. Retain original
  classification, status, failures, source-before/source-after and guard result.
- `execution_bindings` per lane: observed native/core tree, overlay and pinned
  Gall hashes where applicable, runtime lock, corpus, fixture, both freezes,
  actual installed/Clay byte map, loaded runner closure and observer hash.
  Shared source bindings must agree; lane-specific closures remain distinct.
- `deferred_qa_dispositions`: requirement, original report/hash/check pointer,
  original `skipped` status, supporting native requirement IDs or independent
  disposition pointer, resolved typed status and bounded scope.
- One proof per manifest requirement: `id`, `kind`, typed `status`, `bindings`,
  nonempty unique named `assertions`, each assertion's fact references and
  semantic predicate. Native proof carries actual command/result references
  and completed guard evidence. Source/N/A proof carries actual reviewer,
  exact `reviewed_source_files`, and an N/A reason where required.
- `historical_reports_unchanged` backed by input hashes checked again after
  reconciliation; exact 73-item inventory and 66-native count. Host validation
  must describe itself as validation of retained native evidence, never a new
  native execution.

Required negative checks for the new adapter/gate: missing/duplicate/unknown
IDs; zero/missing/duplicate assertions; wrong typed status; wrong scope or
classification; any source/toolchain/corpus/manifest/closure/observer drift;
missing, modified, unresolved or truncated transport bytes; an artifact
outside the admitted root; malformed/duplicate-key or oversized JSON; reused
one-shot occurrence or wrong ship/path; missing stage or native failure hidden
behind `awaiting_review`; extra skipped check; review before later dependent
facts; self-approved or stale source/N/A proof; a false completed guard; a
mock presented as native; and the existing failed roundtrip report presented
as a completed execution. Deleting either newly required recovery control or
the unaccepted-legacy control must leave its requirement nonpassing. The
scheduled-Gall proof additionally rejects an edited old move/duct, equal
nonces, changed pending/history/observer, absent fresh fact/kick, failed live
leave, and a negative control that merely failed compilation or timed out.

Two current gate integration hazards need explicit source review:

- `qualification_gate.evaluate()` accepts source/N/A reviewers only as
  `/root/qa_review` or `/root/hoon_review`. A disposition authored by the
  currently delegated `/root/independent_review` must retain that real
  identity; any role allowlist extension needs explicit ownership, not
  impersonation of a historical reviewer.
- Its single `expected_bindings` map currently requires identical runner,
  loaded-closure and installed-Clay hashes across all native proofs. The
  scheduled lane has a distinct runner and additional overlay. Validate each
  lane against its exact recorded execution closure, or use an explicitly
  defined verified composite binding with separate constituent records.
  Never stamp core execution hashes onto schedule evidence to satisfy equality.

## Native evidence selectors and conditions

`C` = core report `/checks`, `/commands`, `/evaluator_controls`, lifecycle and
exact transport references, from `core_test.py`. `Q[n]` = `/qa/cases/n`, checked
against the named corpus case, with `/qa/calls`, snapshots and captures from
`core_cases_v2.py`. `D[name]` = `/delivery/cases` selected by exact case name,
with assertions and recorded native calls from `delivery_suite.py`.
`P[name]` = `/qualification/recipes/name`, joined to `/qualification/checks`,
`calls` and `batches` from `qualification_cases.py`. A recipe marked `executed`
alone is not evidence; verify its actual assertions and command/result bytes.
`G` = separate actual scheduled-Gall run described below.

For each `delivery:<case>:<occurrence>` row, select its distinct
`Q[n]/delivery_observations[k]`. Re-run `delivery_cases.verify_one_shot` against
the exact associated response bytes, ship and route. Require the actual
known-mark request fact/ACK/kick, payload length/hash, no observer fault or
post-terminal fact, an acknowledged active foreign sentinel unchanged by the
read, and four actual runtime log segments free of admitted errors. The
assertion name is `one-shot-request-duct-only` for each of these 22 IDs; its
generic spelling cannot justify reusing one observation for multiple IDs.
Array indices below are for the inspected corpus; a consumer must also verify
case names and occurrence counts, not trust historical numeric pointers.

| # | Native requirement | Required source/report evidence and scope |
| --- | --- | --- |
| 1 | `delivery:empty-project-known-unknown:1` | Q[0]/delivery_observations/0; `empty-project-known-unknown`, bud known project, one-shot rule above. |
| 2 | `delivery:empty-project-known-unknown:2` | Q[0]/delivery_observations/1; same case, bud unknown project. |
| 3 | `delivery:outsider-private-project-existence:1` | Q[5]/delivery_observations/0; `outsider-private-project-existence`, bud known project. |
| 4 | `delivery:outsider-private-project-existence:2` | Q[5]/delivery_observations/1; same case, bud unknown project. |
| 5 | `delivery:reader-can-read-work:1` | Q[12]/delivery_observations/0; `reader-can-read-work`, nec exact authorized work. |
| 6 | `delivery:outsider-work-known-unknown:1` | Q[13]/delivery_observations/0; `outsider-work-known-unknown`, bud known work. |
| 7 | `delivery:outsider-work-known-unknown:2` | Q[13]/delivery_observations/1; same case, bud unknown work. |
| 8 | `delivery:explicit-grant-allows-former-outsider:1` | Q[41]/delivery_observations/0; exact explicit-grant case, bud authorized work. |
| 9 | `delivery:owner-reads-private-document:1` | Q[63]/delivery_observations/0; bus own document/container. |
| 10 | `delivery:reader-private-document-known-unknown:1` | Q[64]/delivery_observations/0; nec known private document, exact denial. |
| 11 | `delivery:reader-private-document-known-unknown:2` | Q[64]/delivery_observations/1; nec unknown private document, same denial. |
| 12 | `delivery:outsider-private-document-known-unknown:1` | Q[65]/delivery_observations/0; bud known private document, exact denial. |
| 13 | `delivery:outsider-private-document-known-unknown:2` | Q[65]/delivery_observations/1; bud unknown private document, same denial. |
| 14 | `scoped-private-metadata` | Composite P[v1-private-identity-and-sequence-reproduction] plus Q[129–147], normal accepted receipt checks and authorized export checks. Derive `projection-timing-and-all-metadata-nondisclosure` only within manifest scope; Q[74]'s skipped placeholder is not support. |
| 15 | `delivery:reader-private-manifest-known-unknown:1` | Q[90]/delivery_observations/0; nec known private manifest. |
| 16 | `delivery:reader-private-manifest-known-unknown:2` | Q[90]/delivery_observations/1; nec unknown private manifest. |
| 17 | `delivery:object-read-binds-retained-snapshot-and-container:1` | Q[93]/delivery_observations/0; authorized bus snapshot/blob in bus container. |
| 18 | `delivery:object-read-binds-retained-snapshot-and-container:2` | Q[93]/delivery_observations/1; zod snapshot/blob in zod container queried by bus, denied. |
| 19 | `delivery:object-read-binds-retained-snapshot-and-container:3` | Q[93]/delivery_observations/2; zod snapshot/blob with bus container substitution, denied. |
| 20 | `delivery:object-read-binds-retained-snapshot-and-container:4` | Q[93]/delivery_observations/3; bus snapshot/blob with zod container substitution, denied. |
| 21 | `delivery:object-read-binds-retained-snapshot-and-container:5` | Q[93]/delivery_observations/4; unknown snapshot, denied. Bind OIDs to actual run captures. |
| 22 | `delivery:object-read-binds-retained-snapshot-and-container:6` | Q[93]/delivery_observations/5; unknown object, denied. |
| 23 | `delivery:downgraded-reader-retains-work-read:1` | Q[119]/delivery_observations/0; bus retains exactly permitted work read after downgrade. |
| 24 | `v2-native-compile` | C exact installed byte/Clay checks for every Hoon file on four ships; actual `+stead-build-probe` result on all four, codec/core/reducer probes, home and real observer start. Exact loaded closure and diagnostics required. |
| 25 | `v2-ordered-journey` | Q exact 129 retained named cases (99 ordered + 10 expiry + 17 continuation + 3 second-project), nine explicit v2 acceptance amendments, all applicable receipt/journal/atomicity checks. Current run also requires all 19 scoped-privacy cases (148 total). Resolve three typed placeholders separately; do not weaken case inventory. |
| 26 | `v2-codec-and-home-rejection` | C `codec-v*-six-frozen-vectors`, per-input `codec:*`, frozen digest, `home-rejects-malformed:*` and `codec-no-business-change:*`. Includes six current vectors and 43 raw controls, plus retained six v1 vectors; exact canonical bytes and actual home NACK reason. |
| 27 | `v2-context-controls` | C all 14 context controls: invalid watch NACK, transport-only poke, exact read denial, unchanged business state and exact baseline restoration for missing/expired/revoked/profile/sender evidence. |
| 28 | `v2-concurrent-cas` | C `/concurrent_submissions`, two actual simultaneous bus/zod writes at expected revision 4: `two-principal-concurrent-cas-one-winner`, trusted sender receipts, visible winning revision 5, one journal/receipt, no Git-object change. |
| 29 | `legacy-private-project-probe-reproduced` | P[v1-private-identity-and-sequence-reproduction]: actual provenance-built v1 hidden second project/work; bus hidden reads opaque; cross-project local-ID collision gets `invalid_command`, fresh control accepts; refusal leaves state exact. |
| 30 | `legacy-private-container-probe-reproduced` | Same P recipe: actual private owner document, same local ID attempted by bus yields old same-project denial; fresh authorized save accepts, hidden read denied; exact native calls and unchanged rejection state. |
| 31 | `v2-cross-project-local-id` | Q[126–128,142–147] plus earlier outsider main-project reads: independent work/grant ID allocation in two projects, exact authorized views, second-project known/unknown denial and primary journal isolation. |
| 32 | `v2-cross-container-local-id` | Q[132,137–141] and private owner denial cases: identical document local ID saves independently; original other-owner document remains exact; cross-container read denied. |
| 33 | `v2-public-receipt-normal` | New Work/Docs acceptances Q[11,51,139,144] and all receipt validators: closed v2 envelope, exact typed resource/container/context, canonical bytes, original accepted time and Git OID, absent private journal sequence/hash/policy counters. Internal journal remains separately validated. |
| 34 | `v2-public-receipt-retry` | Q equal retries including [75,96,130,134]; `original-receipt-bytes-and-fields` exact raw equality despite private activity; no new authoritative event. Revoked/expired/downgraded retry denial remains required. |
| 35 | `v2-public-receipt-recovery` | Q[19,33,68,105,113,114,121,123,135] and D[missing-channel-and-wrong-digest]; exact original public receipt where currently authorized, exact opaque denial for wrong principal/container/current authority. |
| 36 | `v2-public-export-projection` | Q[92–94,98,131,136], export captures and `core_export`: exact authorized Markdown/files, stock Git object OIDs, selected-container reachable history only, no unrelated objects, actual `git fsck --full --strict`, identical export after restart/private activity. |
| 37 | `legacy-revocation-exhaustion-reproduced` | P[v1-exhaustion-migration-security-reserve]: native transition history at 4095 then 4096, two projects/256 retained grants, both v1 revoke refusals atomic. No counter injection or recipe inventory substitution. |
| 38 | `v2-security-revoke-reserve` | Same P recipe after migration: authorized first revoke at ordinary 4096 accepts; retry consumes no reserve; unauthorized/missing-binding probes deny before capacity; ordinary overflow atomic. |
| 39 | `v2-cross-project-security-admin` | Same P recipe: explicit organization-policy administrator revokes in each project with ordinary capacity exhausted; current binding/profile checks preserved; after first project closes, other reserve remains zero and bus content read still works. |
| 40 | `v2-security-reserve-exhaustion` | Same P recipe: 128 actual retained-grant revokes per project, security/ordinary/journal counts, closed reads/retries/mutations and other-project independence. **Gap:** closed receipt recovery absent in recorded baseline. |
| 41 | `v2-security-counter-u64-edge` | C actual `+stead-core-probe` `%stead-core-basic-and-counter-edge-pass`; inspect bounded pure probe's U64−1/U64 closure/refusal checks. Label synthetic state explicitly; not the real 4096-history lane. |
| 42 | `boundary-projects` | P[projects]: 16 actual projects, unauthorized overflow opaque, authorized 17th allocation capacity refusal, all authoritative hashes/counts unchanged. |
| 43 | `boundary-grants` | P[grants]: creator + 127 explicit grants, 129th refusal atomic and unauthorized probe opaque; Q[29,35,44] tombstone/non-overwrite checks plus P exhaustion's retained-grant state after real revokes. |
| 44 | `boundary-work` | P[work_items]: 128 accepted items and atomic 129th rejection; Q independent scoped IDs and revision/CAS cases supply separate collision/revision coverage. No inference of a full-capacity existing-item update. |
| 45 | `boundary-documents-tree` | P[documents]: 32 accepted documents/tree entries, unauthorized next save denied, authorized 33rd refused; before/after state, objects, ref/pointer, journal and receipts equal. |
| 46 | `boundary-container-history` | P[history]: 128 actual document saves in one container (129 journal events including project creation), 129th save refused with no admitted object/ref/receipt. |
| 47 | `boundary-object-bytes` | P[object_bytes]: legitimate distinct max-size document saves across two containers; first budget crossing refused with bytes ≤ 8,388,608 and next 32,768-byte body beyond budget, other limits not reached, no partial admission. Do not claim exactly 8,388,608 allocated bytes. |
| 48 | `boundary-ordinary-journal-receipts` | P exhaustion: exact 4095→4096 accepted transition and receipt count, next ordinary mutation capacity refusal, unchanged state; retain bounded batch command/result hashes and full transport. |
| 49 | `boundary-pending` | D[pending-quotas]: four real senders, 16 each/64 total actual reservations; 17th per sender NACK with no fact/subscription, all leaves clean up to zero, no business change. |
| 50 | `delivery-positive-known-mark-control` | D[known-mark-and-held-outsider]: actual `stead-result-2` fact with exact payload hash/size and kick; observer fault/runtime error absence, foreign acknowledged sentinel unchanged. A zero-event observer without positive control fails. |
| 51 | `delivery-ended-duct-no-late-fact` | D[leave-and-fresh-retry] and D[lazy-expiry-and-same-path-retirement], plus completed-duct observations: no later private facts on old probes while distinct fresh retry receives one fact/kick; actual business state unchanged. |
| 52 | `delivery-expired-same-path-reregistration` | D[lazy-expiry-and-same-path-retirement]: trusted real time crosses old 60-second deadline; first same-path registration ACK+kick/zero facts retires only; a later fresh registration receives exact retry receipt. |
| 53 | `delivery-late-old-leave` | **G only after actual execution and independent review:** captured active old Gall leave delivered unchanged to home at its old duct after fresh registration; pending/incoming/observer unchanged, fresh completion and live-leave/negative controls. D[ended-leave-attempt] is insufficient. |
| 54 | `delivery-expiration-lazy` | D[lazy-expiry-and-same-path-retirement]: retained deadline, trusted current time and real elapsed wait; expired pending remains before triggering watch and retires upon event. No autonomous timer claim. |
| 55 | `delivery-leave-cancels` | D[leave-and-fresh-retry]: current watch's actual leave changes pending 1→0; duplicate command gives no old fact, old observer ends, business history unchanged. G live-leave is an additional positive control. |
| 56 | `delivery-same-path-private-readers` | D[known-mark-and-held-outsider]: bud held same-path ACK/no content; authorized owner receives exact content while bud unchanged; fresh outsider read returns exact opaque denial. |
| 57 | `delivery-wrong-sender-digest` | D[wrong-sender-and-binding] plus D[missing-channel-and-wrong-digest]: wrong source/binding watch NACK without reservation; live wrong-digest watch receives no result from actual accepted command and is cleaned up. |
| 58 | `delivery-missing-channel` | D[missing-channel-and-wrong-digest]: actual command without route durably accepts exactly once; poke ACK carries no acceptance; authorized recovery obtains exact receipt and leaves state unchanged. |
| 59 | `delivery-home-unavailable` | D[home-unavailable]: actual stopped home, bounded supported transport timeout/error, no Saved outcome, old process exits zero, distinct replacement PID and identical business state. An arbitrary exception is insufficient. |
| 60 | `delivery-late-response` | D[leave-and-fresh-retry] and D[lazy-expiry-and-same-path-retirement]: actual poke after cancelled/retired route yields no old private fact; ACK/kick alone is not Saved; later fresh receipt cannot reopen old probe. Scope is tested application routing, not arbitrary Ames packet reorder. |
| 61 | `migration-current-roundtrip` | C `owner-control:roundtrip` and `native-on-save-on-load-roundtrip`, exact populated business snapshot equality. **Observed failure in inspected run; subsequent fix needs native proof.** |
| 62 | `migration-actual-v1-vase` | P exhaustion: provenance-built actual `%1` vase, `migration-preserves-exact-history-content-and-bindings`, exact counts/journal/receipts/objects/bindings/containers/reachable hashes and document OID/bytes, no invented security event. Not OTA proof. |
| 63 | `migration-legacy-receipt-projection` | P exhaustion `v1-replay-projects-original-acceptance`: current projected original digest/time/OID and no new event. **Gaps:** retained receipt recovery and never-accepted legacy command rejection absent in recorded baseline. |
| 64 | `migration-invalid-predecessors` | C actual `load-future`/`load-counter` NACK `stead-unsupported-state` with unchanged populated state; P malformed predecessor variants receipts/policy/grant/reachable/initialized reject without changing current or retained predecessor state. |
| 65 | `warm-home-restart` | Q[95–98], captured restart old exit 0/distinct PID, exact accepted revisions/policy/document OIDs and exported Git bytes after replacement, authorized retry and denial. External effects have independent N/A disposition; no abrupt-crash claim. |
| 66 | `evaluator-error-boundaries` | C `/evaluator_controls` and `native-evaluator-failure-and-large-frame-controls`: actual pinned evaluator rejects invalid Hoon with incomplete/nonpassing frame and diagnostics; >64 KiB valid frame round-trips exactly. Process exit alone is insufficient. |

## Scheduled Gall lane's limited use

Draft sources are under `tests/urbit/native_gall_schedule/`. The runner is
`scripts/urbit/gall_schedule.py`; supplied-payload validation is
`scripts/urbit/gall_schedule_proof.py` (reviewed SHA-256
`77a138ff10ea96daf33694e6d82201a4c6d16a3740ec0a6d05f3f37b4076af55`).
Its host tests and `native_execution_verified: false` result are not native
execution evidence. No successful native schedule artifact was reviewed here.

Require actual pinned `/sys/vane/gall` plus actual home and observer gates,
only mocked delivery queue and clock, exact installed core/overlay/Clay and
loaded-source closure, original emitted leave while old watch is active,
byte-identical later delivery at the old duct, old/new nonce and duct
inequality, actual retired old incoming duct absent, fresh pending/incoming
present, unchanged fresh pending/history/observer after release, one exact
fresh receipt fact and kick, and live-leave pending 1→0. The old sender
already emitted leave locally, so zero old facts is valid and must not be
invented as old receipt observation. Every delivered move must trace to real
Gall output. No direct app `on-leave`, fabricated task, edited pending/bitt,
locally dropped task treated as home delivery, or synthetic observer qualifies.

Require a separate actual negative generator result with the specific runtime
assertion showing expected pending 2 versus actual 1. Compile failure, timeout
or a general crash cannot substitute. The new `native-scheduled-gall`
classification may be accepted only for `delivery-late-old-leave`, with this
narrow scope and exact bindings. All other native classifications and gates
remain unchanged. Neither Ames/UDP nor live identity authentication is tested.

## Final artifact review cautions

- The seven other items remain: `no-effect-subsystem` (N/A),
  `receipt-lookup-order` and `guard-independent-source-review` (source review),
  `guard-negative-host-tests` and `delivery-host-order-permutations` (host
  mocked), `guard-real-hot-preflight-refusal` (real host), and
  `guard-real-platform-mocked-sensors` (real platform/mocked sensors).
  Preserve each exact named assertion and evidence kind; none is native.
- `qualification_gate` validates hashes, pointers, typed dispositions and
  assertion names, but does not itself derive all predicates in this map.
  A handcrafted envelope with a truthy `native` list is not sufficient review.
- Raw core reports use `local-real-native-fake-ships` and `pass`/`fail`, while
  typed gate proofs use `real-native-fake-ships` and `passed`. Preserve the raw
  records and document the validated wrapper's exact source; do not globally
  rewrite status/classification strings.
- Aggregate native proof must bind all exact inputs, original and current
  freezes, installed Clay bytes, source before/after, loaded closure,
  observer, guard, transport hashes and actual assertions. Native assertion
  names that recur across projects need project/call selection, not “first
  check with this name.” Never infer complete coverage from a count alone.
- The legacy assertion spelling `projection-timing-and-all-metadata-nondisclosure`
  exceeds the deliberately bounded scope in the manifest. It does not certify
  physical timing secrecy or every possible metadata channel.
- This mapping does not close Phase 1, approve deployment, or change the
  manifest. Independent review of the final exact artifacts remains required.

## Addendum: reconciliation admission review and host validation

The integrator implemented the non-circular admission API in
`qualification_gate.reconcile`. Reviewed gate SHA-256:
`38a49870a8a6daf0f6715ba926cbdea0e4eab30cfdd6809df035c55a0b01dd14`.
Independent authored test SHA-256:
`e2ef9b18f0feb0ec2553f2b395ba1b40b8b1cb463365cd38192461366a34af58`
(`tests/urbit/test_phase1_reconciliation.py`). These fixtures explicitly model
report formats on the host; they are not native evidence.

The reviewed contract retains exactly the three typed QA deferrals and the
single known old-leave delivery limitation, while rejecting other failed,
missing, empty or incomplete runtime controls. It checks the authoritative
73-item manifest, whole retained execution and guard artifacts, current source
before/after, complete expected input maps, lane-specific loaded and installed
source identities, and actual `/commands/N` references. It preserves typed
independent source/N/A dispositions and limits scheduled Gall evidence to the
old-leave requirement. The final CLI uses reconciliation rather than falling
back to the weaker format-only evaluator.

Host command executed:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests/urbit python3 -m unittest test_phase1_reconciliation
```

Result: **17 tests passed in 4.474 seconds**, including negative subcases for
metadata substituted for native commands, detached guard hashes, changed
manifest scope/count, pinned Gall/helper/fixture/predecessor input drift,
missing final source identity, rewritten skips, actual runtime failures,
unresolved transport records, and missing/incorrect schedule controls.

A separate read-only call to `validate_transport` passed in 0.057 seconds for
the actual `core-20260925T100137Z.json` and its 1,752-record compressed sidecar.
This verifies retained transport integrity and the exact long-stdout
abbreviation rule. The report SHA-256 remains
`84a539f820b1f825b63b888a9c3414c291ea7a287134cb006b7ba32eabbc48f2`;
the sidecar remains
`a1309afeef68ff10b37b3f15031cb610372c99639b859408564d672793c8afc2`.
Its native result remains **fail / owner-control:roundtrip**. No native workload
or qualification attempt was performed by this addendum. Independent semantic
review of the final per-requirement proof derivations and new native execution
artifacts remains outstanding.

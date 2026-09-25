# Executed development evidence

September 25 continuation: the [native build and smoke](evidence/2026-09-25/native-build/index.json)
passed at `c299f19`. The [first full core run](evidence/2026-09-25/native-core-first-run/index.json)
failed a real saved-state round-trip after 145 passed cases and three incomplete
typed dispositions. The failed result remains unchanged. Follow-up save/load,
recovery and qualification-runner changes remain subject to new native evidence;
Phases 0/1 are still open and Phase 2 has not started.

Latest September 24 continuation: [cooling and native build checkpoint](COOLING_CHECKPOINT_20260924.md).
290 host tests passed; real native framing and cleanup passed, while the Hoon
build failed. The subsequent type correction remains unexecuted after thermal
admission refused. Phases 0/1 remain open and Phase 2 has not started. The
[earlier local development checkpoint](DEVELOPMENT_CHECKPOINT_20260924.md) and
historical native records below remain separate evidence.

Historical September13 checkpoint: [Phase1 closeout](PHASE1_CLOSEOUT.md) and
[exact lightweight execution](evidence/2026-09-13/qualification/root-lightweight-final.json).
The v2 source is uncompiled/unexecuted after real thermal preflight refusals.
The September12 record below, including its failures and25 skips, is historical
and remains unchanged. Do not apply its native success to the new source.

September 12, 2026 US/Eastern; raw timestamps are UTC. This report separates
planning, mocked/host, real local native, stock-Git candidate and GitHub actions.
The source commit/evidence binding is recorded with the implementation PR. Every
native run also records exact file-tree and toolchain hashes, including runs made
while source was uncommitted. No original approval transfers to this derivative.

## Repository and preservation — real Git/GitHub

Created private `ScottTpirate/stead-urbit` from the supplied verified bootstrap.
Original history through `3d47f0172a41beebb31f5c3a7df133cc1d4b1ead` is an ancestor;
its tracked source is archived under `reference/stead/`, with notices retained.
The original repository is read-only and its push URL is disabled. Inherited
workflows remain archived; no upstream secret/webhook was copied. No new CI
workflow is enabled yet.

The active implementation was preserved in checkpoint `d3d370b` before reviewing
PR #32. Its whole-checkout test-copy bug was fixed as `b52eeef`; 17 planning/mocked
API tests passed. The user-authorized planning PR merged as
`4bb28c645ed155f842f5b9479a0919e743a89378`, then merged into the active increment
without resetting it. Exact runtime lock bytes remained unchanged.

GitHub's branch-protection query returned HTTP 403 requiring a paid private-repo
plan or public visibility. Neither was purchased/changed. Do not claim enforced
branch protection or protected deployment approval from this repository state.
The implementation PR remains for owner review, separate from planning PR #32.

## Toolchain and host checks

[TOOLCHAIN.md](TOOLCHAIN.md) and the executable lock record exact source commits,
URLs, archive/binary/source hashes and verification authorities. Real downloaded
Vere reports 4.6; all four real fake ships report kernel `%408`. Node reports
24.21.0, Git 2.55.0. The frontend lock is toolchain-only, with no browser UI/build.

Executed `make setup`, `make doctor`, `make start`, `make stop`, `make reset` and
`make test`. Setup/archive verification and real namespace doctor passed. Start
and stop were exercised across initial sequential boots, stopped-seed creation,
reset, test startup and clean restart. Reset is limited to marked disposable fake
state; no Git reset or production recovery was performed.

`python3 -m unittest discover -s tests/urbit -p 'test_*.py' -v`: **88 passed** in
the recorded run. This comprises 18 contract/reference checks, 27 harness safety
checks, 4 conn regressions, 22 Urgit runner safety checks and 17 planning/mocked
API checks. Filesystem locks, redirects, outside-file sentinels and socket framing
are real host operations; native process/network behaviors are mocked where each
test explicitly says so. These tests alone do not establish native correctness.

Both planning validators pass (18 original tasks; 30 combined tasks/7 milestones/
4 skills). Milestone synchronization was a dry run only. These metadata checks
are not Hoon execution. Six canonical command fixtures also passed an independent
pinned-Node implementation of ordering/encoding/SHA-256; native codec parity is a
separate URB-040 check.

## Native smoke — real local four-fake-ship execution

The first run compiled the agent and passed a local state assertion but timed out
on a remote thread. It is retained in
[first failure](evidence/2026-09-12/native-smoke-first-failure.json).
Pinned Lens leaves its Dojo subscription on a prompt effect before asynchronous
thread completion; pinned Dojo subsequently reports a missing session. The harness
now uses the runtime's supported conn/Khan interface for asynchronous probes.

A subsequent actual remote rejection exposed a test-parser mismatch: Khan renders
term hints without `%`. [That failed run](evidence/2026-09-12/native-smoke-rejection-parser-failure.json)
is preserved and used by a real-output parser regression. Generic failure, a
wrong semantic hint or a network ACK cannot satisfy a negative test.

After these fixes, `make test` passed all **12 commands**, plus home restart:
7 expected application ACKs and 5 specific failures (3 reader/outsider denials,
1 stale counter revision and 1 intentionally wrong state assertion). Payload
claimed-author text did not override native `src.bowl`. Denials left the tested
counter unchanged. Counter `1` survived clean home stop/relaunch and then advanced
to `2`. A deliberately wrong final assertion was caught, proving the failure path
is observed rather than ignored.

Root run: [31.378 seconds](evidence/2026-09-12/native-smoke-pass.json).
Independent QA run: [20.953 seconds](evidence/2026-09-12/native-smoke-independent-pass.json),
exit 0. Hoon reviewer independently verified source, semantic traces, exact corpus
order/count, seed provenance and source hashes. See REVIEW_OWNERSHIP.md.

Both runs bind these exact bytes:

```text
lock     4a209c10cf1756eb0f7357cc3eca8250bf66c239b4cd0ca31a8c0886d4d304ee
native   dff85b9af5429c096e38789f81f1e6097368c244e84d2d1b5b49a66a1f6fcf89
harness  36e141574825b284e6877d6947a58cb4710d65abebb91ac19d518bfd5506e93e
corpus   3a05090f8ff4aceddcd228145346564ce9ecf28af7016fd256eb911430dbbd9c
```

This is a synthetic counter and trusted-native-sender test. It is not yet Work,
Docs, shared browser authentication, a Git forge, a portable application journal,
a live-network test or proof of cross-app endpoint isolation. Process restart is
also distinct from Gall application upgrade/on-save/on-load migration.

## Urgit — separate real local candidate evaluation

[URGIT_AUDIT.md](URGIT_AUDIT.md) records source/license inspection and 14 passing
native/stock-Git checks on the initial runner, including exact OIDs, clone/fetch/
push, tags, fsck, malformed pack and bounded revocation checks. An explicit MIT
app declaration permits the recorded isolated evaluation; redistribution notices
and integration approval remain open. No candidate source is vendored.

Independent QA found and fixed host artifact redirection and false persisted-pass
hazards in that runner; 22 regressions pass. Subsequent runs of the hardened
runner aborted before readiness at host thermal limits, including a verified
50%/10ms CPU quota attempt. Those runs completed **zero** native checks and remain
failed, alongside the valid but explicitly pre-fix 14-check result. A complete
hardened-run replay remains open. No temperature ceiling was increased to pass.

This bounds URB-025 feasibility evidence; it does not approve Urgit as Stead's
backend. The first native Work/Docs slice can implement its small Git object model
inside `stead-home` without adopting the candidate's independent mutation routes.

## Environment, measurements and unresolved gates

[Environment](evidence/2026-09-12/environment.json): Arch/Omarchy Linux x86-64,
Intel i9-12900H, 64 GB physical RAM, roughly 40 GB available initially. Each of the
four fake processes reserves a 2 GiB loom; no resource allocation follows rank.
Observed timings above are test wall times, not save/read latency benchmarks.
There are no representative Work/Docs/import p50/p95, capacity, RPO/RTO, browser,
live-Urbit, VPS or production measurements. Synthetic data only; no purchases,
real identities, credentials or confidential datasets were introduced.

URB-010 pins and URB-020 smoke have execution evidence. URB-025 records bounded
candidate feasibility plus an open hardened replay/integration limitation.
URB-030 freezes only the minimum first-slice contracts after independent review.
URB-040/050 native product behavior, browser/session isolation, full native Git,
CI, export/recovery qualification, canary and deployment require their own evidence.
Evidence attached to an issue is coordination, not owner merge or release approval.

## Work/Docs and authorization — executed native first slice

The subsequent URB-040/050 increment implements native state and authorization
under the minimum URB-030 contracts, without changing that freeze or the active
runtime lock. [NATIVE_CORE.md](NATIVE_CORE.md) describes the implemented API and
limits. This section supersedes earlier future-tense references to that slice;
it does not broaden the earlier counter or candidate-Git evidence.

Root executed `make core-test` on the four isolated fake ships. The final root
run passed its bounded execution gate in **390.266 seconds**, including a real
120-second grant-expiry interval. It recorded **413 direct checks**, **129 native
business cases**, and **2,542 independent-corpus assertions** with no failed or
unrun business cases. The QA coverage subreport deliberately remains incomplete:
115 cases have all their declared checks, 14 have broader checks still open, and
**25 assertions are explicitly skipped**. These include subscriber instrumentation,
metadata confidentiality, external-effect observation and source-order inspection;
none are relabeled as native passes.

The executed behavior includes:

- Home-owned project and work creation/update, explicit contributor/reader grants,
  maintainer grant ceilings, retained revocation IDs, and organization capability
  without implicit content access.
- Exact original receipts on authorized duplicate requests; changed-payload reuse,
  stale resource revisions and epoch mismatches reject. Current revoked, expired
  or downgraded authority cannot recover an old mutation receipt.
- Five native Git-backed document saves in two owner-private containers, including
  independent document revisions, exact Markdown/frontmatter, parent commits,
  historical snapshots and current authorization on every object fetch.
- A clean home process restart with preserved content, policy, receipts, journal
  and objects; real `on-save`/`on-load` roundtrip; unsupported counter/future state
  rejection without data loss. There are zero declared predecessor product versions.
- Two actually simultaneous work mutations from `~bus` and `~zod`: one accepted,
  one revision conflict. Concurrent same-path document reads return the owner's
  exact body and the outsider's opaque denial. Another sender cannot reserve the
  owner's result path.
- **49 native codec vectors** (six frozen plus 43 adversarial), including all 35
  malformed inputs rejected again at the home. **14 invalid-context scenarios**
  reject result registration, prevent direct-poke business changes, and deny reads.
  Native ACK/fact/kick reducer permutations and its negative controls also execute.

Every one of the 15 Hoon files is checked byte-for-byte through actual Clay `%cx`
scries on all four ships before the app/client compile probes. Before/after source,
fixture, corpus and lock hashes match, and loaded Python closures match disk.
The root report contains 871 exact administrative/native command records. The
independent Hoon reviewer also verified its wrappers, all 34 accepted journal
records in two project chains, receipt fields, and all 15 unique exported Git
object IDs. See [review](NATIVE_CORE_REVIEW.md) and the
[readable report](evidence/2026-09-12/native-core/root-pass.summary.json).
The full JSON is retained as a standard gzip artifact with hashes in that index.

Eight native document exports were reconstructed and checked with stock Git.
A selected synthetic document container was also exported as a standard
[Git bundle](evidence/2026-09-12/native-core/synthetic-documents.bundle), then
independently cloned without Urbit, checked with `git fsck --full --strict`, and
both current Markdown files recovered exactly. See
[bundle recovery](evidence/2026-09-12/native-core/bundle-recovery.json).
This is document-container exitability, not a complete organization backup.

The original `make test` counter suite still passes on the final harness:
12 commands, five specific expected failures, and restart in **23.628 seconds**;
its native source hash is unchanged. All **131 host tests** pass, including
17 scripted-native/real-temporary-Git export checks. The original pure native
Git constructors separately passed **51/51** vector checks, with compiler and
failed-assertion controls: [object evidence](evidence/2026-09-12/git-objects/index.json).
Planning/contract validators also pass and retain their explicitly non-native labels.

Actual failures are preserved alongside the passes. They exposed invalid native
path encoding, a missing/wrong mark conversion, a typed snapshot-helper build
error, and a 64 KiB pipe-output truncation in the pinned Vere evaluator. The last
failure occurred after all 129 business outcomes, so that run remained overall
failed. A direct reproduction showed 65,536 output bytes against a 65,590-byte
frame despite exit 0. File-backed output returns the full frame, and the final
native run rejects the 65,537-byte input at the home as expected. Host export
regressions additionally caught wrong response identities, object-kind mismatches
and 33-entry trees. See the [evidence index](evidence/2026-09-12/native-core/README.md).

The benchmark environment remains the recorded local Arch/Linux x86-64 machine,
i9-12900H and 64 GB physical RAM; four separately fenced fake processes share one
loopback-only namespace, with 2 GiB configured loom per ship. The times above are
suite wall times with compilation, native transport, exports and real expiry waits.
No product p50/p95, representative load, RPO/RTO or enterprise capacity is claimed.
The lock remains Vere 4.6 / kernel 408k-2, pinned brass pill, Node 24.21.0 and Git
2.55.0, with all exact URLs and hashes in [the lock](../../specs/urbit/toolchain.lock.json).

Browser sessions/direct-home HTTPS, live identity verification, Smart HTTP packs
and refs, general shared/public document containers, full portable Work/policy
export, native CI, production backup/recovery and endpoint isolation are not
implemented by this increment. Global caller-chosen UUID collision disclosure and
private-container activity inference through project counters remain explicit
confidentiality gates. The Urgit hardened full replay/integration gate also remains
open; the new native document constructor does not copy or depend on Urgit source.
Real company data, canary, implementation merges and deployment remain owner-gated.

Independent QA then executed the same `make core-test` from unchanged source:
**PASS**, exit 0, **390.834 seconds** native suite time (**391.002 seconds** including
its wrapper), again 413 direct checks, 129 business cases, 2,542 passed assertions
and 25 explicit skips. [Independent report](evidence/2026-09-12/native-core/independent-pass.summary.json)
and [QA execution metadata](evidence/2026-09-12/native-core/qa-execution.json) retain
source bindings, command output and five-second temperature samples. The source
was uncommitted during execution; the final source-binding record maps those
exact bytes to the committed increment rather than mislabeling the base commit.

The independent run sampled a **96°C** CPU package/core peak at
`2026-09-13T03:35:53.696675Z`. Sampling does not establish an unsampled maximum or
attribute the cause. The main harness has no thermal stop; this is a functional
pass, **not a thermally bounded or sustained-load qualification**. No further
native runs were made after that observation. Operator thermal controls and
measurement remain open before repeated heavy runs or representative benchmarks;
Urgit's separate hardened thermal aborts remain failures, not replaced by this pass.

Tested native source commit: `f52293f7cd6970ded20e73b097beffb7418e4bbd`; the records-only
[source binding](evidence/2026-09-12/native-core/source-binding.json) verifies that
its Git blobs exactly match both completed run manifests.

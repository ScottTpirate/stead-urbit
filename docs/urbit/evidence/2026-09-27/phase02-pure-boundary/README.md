# Phase 2 pure session and HTTP boundary qualification

This increment does not close Phase 2. These are pure native libraries, not an
implemented identity exchange, member endpoint, TLS deployment or browser journey.
The live `stead-home` mutation owner and Phase 1 business libraries are unchanged.

## Actual execution

`make dev` ran the pinned four-fake supervisor with the existing thermal/resource
guard, then `core_check` restored clean synthetic seeds and installed/read back
all 29 native Hoon source files. The report binds the exact source tree, loaded
runner and harness, unit inventory and toolchain before and after execution.
It also compares the actual Clay `/ted/test/hoon` and `/mar/path/hoon` with the
pinned kernel files (resolving only inside the verified kernel tree).

Report: `native-report.json`, SHA-256
`7a293bf1aca0a58712100ecf53c892d260c9b10720f1d364103a854ab4fde817`. `source-sha256.json` records exact
changed source files without depending on mutable branch names.

Observed on 2026-09-27: **74/74 runner checks, 54.645 seconds**, including:

- 19 named native session arms and 12 named HTTP arms, with exact inventories.
- One deliberately failing native arm outside `/tests`, its exact tang marker,
  and Khan's successful thread result containing `false`.
- Seven compiled probes: existing build, codec, core, reducers and save/load
  probes, plus the 57-assertion session and 49-assertion HTTP development probes.
- Actual pinned evaluator framing and parse-failure controls.

Named units use the unchanged official `/ted/test` via Khan with its typed
`%path` input mark. Dojo resolves the immutable beam separately. The Lens/Dojo
`-test` invocation executed the session arms but then raised a real Dojo `%kick`
diagnostic; that earlier run was failed, not filtered into a pass. A `%noun`
input was also rejected by the official runner's type assertion; `%path` fixes
the transport type rather than editing upstream tests. All earlier failed
reports remain in local harness logs.

The native verifier rejects absent/duplicate/extra arms, empty suites, unknown
records, compiler/runtime diagnostics, mismatched verdicts and missing negative
markers. Partial frames, timeout/exit diagnostics and exact input requests are
retained on runner failures. These code paths are not a claim that every planned
CI corruption/timeout control has executed.

The guard run was `4221c0dcd91b5279cf1db25d97597bd1`, CPU quota 5000/10000,
affinity CPU 19, startup 75 C and stop 90 C. It closed completed, exit zero,
without a cleanup failure. No sensor threshold was weakened.

## Independent review

A separate nonauthor review agent checked the final source and retained evidence,
including all six runner dependency hashes, all 29 native files, exact expected
and observed arms, the deliberate failure, raw frame lengths/digests, and all
three transcript slices against the actual ship log. It found no blocking issue
for this bounded pure-library increment. This is agent source/evidence review,
not a human security audit or production authorization.

The reviewer confirmed that CSRF resumption changes only the selected session's
CSRF and the monotonic counter, preserves bearer/browser binding/audit/expiry,
and leaves state unchanged on failed admission. Its HTTP preconditions still
have to be enforced by the future endpoint.

A separate runtime-source review established that Gall keeps full running cores
across process restart. `on-save` omission alone does not invalidate sessions.
Pinned Vere's `/zen/ver.non` comes from a 31-bit time hash and can repeat. The
Phase 2 contract therefore requires an external fail-closed ingress fence and
an acknowledged owner-local reset before reopening browser TLS; this mechanism
has not been implemented or qualified by this increment.

## Host checks and remaining acceptance

The host unittest suite passed 508 tests in 23.040 seconds (`host-tests.log`).
It is separately classified: synthetic/mocked runner tests
do not execute Hoon. Its fixture was updated for the added unit inventory,
pinned dependencies and mocked unit transcripts while retaining late-guard,
changed-source, empty-source and wrong-result negatives. Planning validators
check catalogs only.

Remaining Phase 2 includes configured authoritative team state, actual native
identity approval and HTTPS/session handlers, startup fencing, the integrated
browser Work/Docs journey, authorized projections/cursors/updates, v3 SDK
consumer conformance, isolated native CI and onboarding/accessibility evidence.
No Phase 2 issue is closed by this report.

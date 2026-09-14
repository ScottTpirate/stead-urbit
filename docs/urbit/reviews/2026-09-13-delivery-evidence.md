# Delivery evidence review and focused host fixes

Baseline: PR #35 at `aa93f41a3f15116878035941414125c163908b85`.
Review date: September 13, 2026 US/Eastern.
Scope: host observer-evidence verification, not Hoon implementation or native qualification.

## Reproduced defects

The baseline `scripts/urbit/delivery_cases.py` accepts some incomplete or contradictory authored records as a successful one-shot observation:

- Omitting/nulling the probe ID disables its correlation check; a null route likewise bypasses route comparison when no external expected route is supplied.
- A mere `/v2/result/~bud/` prefix passes as a foreign reserved route without its binding, project, request or digest fields.
- Equal sentinel events can conceal local leave/cancel or changed closed/watch state because those fields are not checked in both snapshots.
- A read-only proof can include poke work, and a late event can contradict a previously observed terminal event.

Malformed request envelopes also raise incidental AttributeError/KeyError rather than the intended ObservationError. Those exceptions were already nonpassing; they are not false-positive acceptance.

These are defects in validation of captured/authored evidence. They are not a reproduced native data disclosure or evidence that the agent's historical product outcomes were false. This helper does not authenticate a transcript merely because a caller supplies a `native` label; actual native source/trace provenance remains the responsibility of the execution harness and independent reviewer.

## Changes

Require explicit typed probe/path correlation and complete reserved sentinel paths. Require the sentinel to be active and not leaving in both retained snapshots. Keep read-only observations free of poke work. Check that a probe's terminal marker cannot reverse after a kick, watch NACK or latched leave.

Preserve valid late ACKs. Preserve sparse per-probe serials because the native observer numbers events across all probes. Do not compare timestamps from separate ships as a global clock. No protocol or saved-state format is changed.

## Actual local verification

Retrieved source and existing test fixture were reconstructed into an isolated selected-file workspace and matched to these Git blob IDs before running:

- Baseline checker: `ccf789cd012de643116717ab6177be2a456e7552`.
- Unchanged existing tests: `77db293eee28a2d3cd1a04fcb6bd408a4d153097`.

Python 3.13.5; standard library only; authored synthetic records. This is not the agent's pinned native/host environment.

| Run | Observed result |
| --- | --- |
| Existing 10 tests against baseline | PASS, 10 tests. |
| New 11 test methods against baseline | Expected FAIL: 13 failing subtests/assertions and 4 errors across the adversarial cases; 3 positive compatibility methods pass. |
| Existing tests against changed checker | PASS, 10 tests. |
| New regression tests against changed checker | PASS, 11 tests. |

Exact targeted commands:

```sh
python3 -m unittest discover -s tests/urbit -p test_delivery_cases.py -v
python3 -m unittest discover -s tests/urbit -p test_delivery_evidence_regressions.py -v
```

Changed checker blob: `196e62a32c5619abc0297c84d35e6bffaf2236c2`;
SHA-256 `171edf429fc1677e3250bcebff4cd2fb55e762d767204afdae846f86deccc131`.
New test blob: `522495149d479dc3fb0e2d391fd6c3ed4b1bec72`;
SHA-256 `f33f843b0cd54a8881eda7821905374e88af6b91afc75e095154f5ab5a515532`.

Not run here: the complete 253-test host suite, planning/contracts/doctor, Hoon compilation, native observer/delivery execution, delayed inbound-leave injection, Git recovery, GitHub CI, browser/live-network or deployment. No phase gate is closed. The 25 historical skips and 0/66 current native evidence result are not edited or replaced.

## Continuation

Incorporate the reviewed fix without resetting the qualification branch, then run the full host suite. Capture new source/runner bindings for new native runs; do not copy historical bindings to this changed verifier.

The owner reports competing workloads have stopped. Recheck the actual 75 C admission/90 C stop policy on the local machine; do not retain old hot readings as a permanent blocker or assume cooling without measurement. Keep the common guard throughout compile, test and cleanup.

Finish the delayed inbound old-leave mechanism in `delivery_suite.py` before claiming that case complete. Its current `ended_leave` explicitly sets missing evidence: issuing a stale local leave may be discarded before reaching home. Use a bounded fake-only receiving-boundary schedule with exact old/new subscription identity and a negative control. If the pinned kernel makes the proposed schedule unreachable, demonstrate the actual invariant and obtain an explicit reviewed requirement correction; do not silently substitute a local ACK or fabricated on-leave call.

Then compile/debug the changed Hoon, run the current 148-case corpus and delivery/capacity/migration lanes, retain framing/evaluator negative controls, and independently reconcile all 66 native obligations. Required missing evidence remains nonpassing. The optional Urgit replay must not block original Work/Docs constructors.

After qualification, implement configurable synthetic team/container setup and shared pages, then individual browser sessions and the two-user/outsider Work/Docs journey. Preserve the existing staged scope. Owner approval for implementation merges, live identities and deployment is unchanged.

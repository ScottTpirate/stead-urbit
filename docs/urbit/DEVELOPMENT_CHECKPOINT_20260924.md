# Local development continuation — September 24, 2026

Phase 0 and Phase 1 remain open. Phase 2 implementation has not started. This
checkpoint improves the local edit/build/test flow and retains real guarded
native failures. It does not replace the outstanding acceptance evidence.

The working base now includes PR #36 (`ce808a2cf9b87d44506e983f7dcebc94f0d2ed4b`),
fast-forwarded locally after a clean-checkout and remote check. No implementation
PR was merged into main. The original Stead repository remains untouched.

## Changes

- `make` shows help without downloading or launching anything. `make check`
  gathers host/static/mocked checks. `make status`, `make preflight` and
  `make wait-ready` make lifecycle and admission explicit.
- `make dev` starts the guarded fake environment, waits for readiness and invokes
  `core-check`. Failure, Ctrl-C and SIGTERM request owned cleanup.
- `core-check` verifies installed Clay bytes and invokes four native build/codec/
  reducer probes, separately from `core-test`. Its reports explicitly set
  `qualifies_phase: false`. Atomic initially-failed checkpoints preserve current
  inputs/stage if the guard terminates a later attempt.
- Both native runners load with the supervisor. Their shared Python modules are
  included in the loaded source identity, closing a stale cached-import gap.
- Compile failure clears readiness and stops fake children. A missing control
  socket with an occupied lifecycle lock is reported as an unresponsive owner.

See [the developer guide](DEV_FLOW.md) for the exact daily workflow and how local
Linux testing differs from browser testing and a later live-network canary.

## Executed results

| Evidence class | Observed result |
| --- | --- |
| Root host/static/mocked baseline | 264 tests passed after incorporating PR #36; planning/ecosystem/contracts passed. |
| Root new host regressions | 19 developer-flow tests passed, including interrupted report retention and actual temporary-source cached-import checks. Native callbacks are mocked. |
| Independent final host/static/mocked | `make check` passed, including the full 283-test suite and both contract freezes. [Exact review and hashes](reviews/2026-09-24-dev-flow.md). |
| Actual Linux platform | Current `make doctor` passed the private loopback namespace/no home/no Docker socket check and verified the existing pins. [Commands/output](evidence/2026-09-24/dev-flow/host-platform.json). |
| Actual guarded native attempts | All four fake ships booted and reported kernel `%408` in each admitted attempt. The subsequent evaluator stage hit 93 C and then 91 C host sensor readings; the guardian terminated its owned scope each time. No current compile/probe pass resulted. [Failure index](evidence/2026-09-24/dev-flow/native-attempts.json). |
| Final checkpoint enhancement | Host interruption regression passed. The second actual native interruption retained a failed checkpoint with exact inputs and stage `evaluator-controls`; no compiler/probe command completed. |
| Browser/live network/GitHub CI/deployment | Not executed. No browser URL or deployed product is claimed. |

The final isolated retry executed source commit
`b425cc2576ad8767b6ac9a5696879f9df80535aa`, with the host-test and review work idle.
Its [source binding](evidence/2026-09-24/dev-flow/interrupted-source-binding.json)
matches 48 source/pin files to that commit and binds the retained failed
checkpoint. This establishes interruption evidence only, not installed Clay
bytes or successful Hoon compilation.

Both actual admitted invocations restricted the launcher to CPU 19 with `taskset`;
the existing guardian independently enforced one CPU and the unchanged 50 percent
quota/10 ms period, 75 C admission and 90 C stop. No persistent machine setting,
toolchain pin or thermal ceiling changed. Host temperature samples cannot
attribute heat to a particular process.

The interruption created the expected unclean-state marker. After preserving the
guard and native startup logs, `make stop` proved the lifetime lock released and
`make reset` restored only stopped, hash-verified, marked disposable seeds. Final
`make status` reports stopped. The [final lifecycle record](evidence/2026-09-24/dev-flow/final-lifecycle.json)
retains these outcomes. The stopped fixture is ready for a future guarded
attempt; no hot boot or test is left running.

## Outstanding work, in dependency order

1. Obtain a stable local thermal window or explicitly qualify an approved other
   Linux development host. Do not treat a server purchase or live identity as a
   prerequisite for fake-ship testing.
2. Compile/debug the current Hoon, then execute the original smoke and current
   148-case business corpus, delivery and eight migration/capacity lanes. Reconcile
   all 66 current native requirements with independent exact-source evidence.
3. Implement the delayed inbound old-leave regression. A valid pinned upstream
   Gall/Ames regression demonstrates the schedule is reachable. Source reasoning
   or an old local leave ACK must not be substituted for actual receiving-boundary
   evidence. A kernel-simulation test needs its own truthful evidence class and
   independent requirement review; no requirement was weakened here.
4. Finish Phase 0's hardened Urgit replay/reuse disposition and the frozen
   contributor-skill baseline/assisted evaluation. Structural skill checks do not
   complete that evaluation. Urgit adoption is not needed by the original native
   document constructors.
5. Complete independent Phase 0/1 review and owner acceptance; integrate the stack
   in dependency order and validate the resulting candidate.
6. Begin Phase 2 with configurable synthetic organizations, members, projects and
   shared containers plus an independent public-API client. Then add individual
   sessions, local HTTPS and the two-user/outsider browser Work/Docs journey.

For this local work the user needs a machine that can sustain the existing guard
and eventually a browser test session with synthetic data. No credentials, cloud
account, real ship identity or private dataset is needed now. If the current
workstation cannot sustain it, choosing an approved alternate development host
is a separate decision; there is no prequalified alternate runner in this repo.

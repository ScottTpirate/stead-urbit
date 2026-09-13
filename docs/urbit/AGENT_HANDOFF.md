# First assignment for the local implementation agent

Work only in `ScottTpirate/stead-urbit`; verify the remote. Bootstrap this independent derivative if it does not exist. The original Stead main-line baseline is `3d47f0172a41beebb31f5c3a7df133cc1d4b1ead`. Preserve its history and notices. Do not push to the original repository or reactivate its archived workflows.

Read the new master directive and deployment plan. The repository is not a working Urbit app yet. Existing copied source is reference material.

## Deliver the first independently runnable development increment

Complete URB-010, URB-020 and URB-025 in dependency order, then URB-030. This means:

- Resolve current runtime/kernel/pill dependencies; record exact versions, URLs, hashes and compatibility evidence. Do not fill example pins from guesses.
- Inspect candidate Urgit source/license and record whether reuse is actually permitted. Run its stock-client vectors separately if legally/technically feasible. A successful install is not approval.
- Implement a local isolated four-fake-ship harness with doctor/start/stop/reset/test commands. No live network identity or cloud purchase. Keep fixtures disposable and ensure reset cannot delete arbitrary paths.
- Prove a minimal native Hoon message handler/state transition compiles on the pinned toolchain and survives restart; run an actual negative native test as well as a positive one. Record commands and output.
- Define stable project/principal IDs, request/revision/epoch semantics, policy decisions and bounded envelopes. Freeze these contracts before parallel feature agents touch them.
- Establish independent test ownership and a Hoon reviewer. Start with one mutation-owning home agent and pure libraries, not a microservice rewrite.

Stop this increment at reproducible environment and frozen first-slice contracts. Produce a PR with real evidence and a clear list of unimplemented features. Do not claim a page, Git forge, authentication system or deployment works until separately executed.

## Subsequent increment

Implement URB-040 and URB-050: home-owned project/work/document transitions and deny-by-default permissions tested across the four identities, including restart, stale revisions, revoked access and duplicate commands. Use public/synthetic content only. Browser/session and native Git integration are later reviewed increments.

## Reporting contract

Report source commit, toolchain pins, exact checks executed, failures, expected failures, benchmark environment, and unresolved gates. Label local/mocked/real-GitHub/live-Urbit tests separately. Never turn a green planning validator into evidence of runtime correctness. Spending, live keys, confidential datasets, merging an implementation PR and deployment all need the relevant owner approval.

# Executed development evidence

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

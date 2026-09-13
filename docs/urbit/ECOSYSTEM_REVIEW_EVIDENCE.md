# Ecosystem review evidence

Review date: 2026-09-12 America/New_York. Baseline: dd0f2c642eb07f60285ea93e984f60777d6a3205.

Executed locally on the proposed supplement and the unchanged bootstrap overlay:

- `python3 scripts/urbit/validate_plan.py`: PASS, 18 original planning tasks.
- `python3 scripts/urbit/check_ecosystem.py`: PASS, 30 total tasks, 7 milestone definitions, 4 skill files.
- `python3 -m unittest discover -s tests/urbit -p 'test_*.py' -v`: PASS, 16 tests.
- `python3 scripts/urbit/sync_milestones.py`: successful dry run; no network or writes.

Tests reject task/dependency cycles (including canary admission), unknown dependencies, duplicate or missing issue mappings, wrong repository, milestone phase mismatch, missing/invalid skills and missing guidance. Mocked GitHub tests exercise create/assign, idempotent rerun and preflight refusal for unrelated issues, PRs and conflicting milestones.

Not executed: Hoon compilation, native skill evaluation, real Git operations, browser or live-ship tests, cloud deployment, GitHub CLI milestone apply, and independent security review. This evidence does not close an implementation task or qualify a release. The issue creation and review PR are repository administration, separate from these static/mocked checks.

No third-party skill code was copied or installed. The external skill source is recorded as a reference-only candidate. No original-repository write, active native source edit, toolchain pin replacement, visibility change, secret provisioning or deployment was performed by this supplement.

## Local integration review

On 2026-09-12 America/New_York the local integrator reviewed PR #32 at
`f454a846daa73b83fdf5477dcd8a4983a479ea41` against the active development checkout.
The original whole-tree test copy would traverse ignored runtimes and piers,
including live Unix sockets. Tests now copy only the validator's named inputs.
A regression fixture includes an actual Unix socket and a synthetic private-file
sentinel; neither enters the copied fixture.

Executed in an isolated review worktree: both planning validators PASS, the
17-test planning/mocked-API suite PASS, and milestone dry-run PASS with no network
or mutation. These are separate from all native execution results. The active
implementation was first checkpointed as `d3d370b`; no checkout reset, toolchain
replacement or runtime-state copy was part of this PR integration.

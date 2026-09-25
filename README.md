# Stead Urbit — experimental native implementation

Status: **Phase 1 qualification remains open. The current core compiles and passes its save/load probe; full behavioral qualification is still pending. Browser login, a full Git forge and production access remain separate gates.**

Latest [executed results](docs/urbit/TEST_RESULTS.md): 53 native compilation and
save/load checks pass, and the independent Git evaluation passes all 14 checks.
Repository preservation and the Git reuse decision are complete. Full core,
delivery and contributor-workflow qualification still keep Phases 0/1 open.

An independent derivative of `ScottTpirate/stead`, preserving that repository's main-line history through `3d47f0172a41beebb31f5c3a7df133cc1d4b1ead` (inspected September 12, 2026). The original repository is not modified.

The working architecture is **federated project homes**: one authoritative home for each project, explicit organizational custody, ordinary Git compatibility, individual authorization, and selective reads/replication. No automatic company-wide replicas on personal ships. No blockchain transaction per edit or commit.

## Start here

- [Master directive](docs/urbit/MASTER_BUILD_DIRECTIVE.md)
- [Development and deployment](docs/urbit/DEPLOYMENT.md)
- [Phases and acceptance gates](docs/urbit/ROADMAP.md)
- [First implementation-agent assignment](docs/urbit/AGENT_HANDOFF.md)
- [Research sources and verification limits](docs/urbit/SOURCES.md)
- [Machine-readable backlog](specs/urbit/backlog.json)

Use the [local runbook](docs/urbit/RUNBOOK.md) for `make setup`, `make doctor`, `make start`, `make test`, `make core-test` and `make stop`. Read [actual results and limitations](docs/urbit/TEST_RESULTS.md) and the [native slice scope](docs/urbit/NATIVE_CORE.md).

For the daily edit/build loop and what you need for local testing, read
[Local development and testing](docs/urbit/DEV_FLOW.md). Run `make` for command help.

Run `python3 scripts/urbit/validate_plan.py` to validate the planning metadata. This is not a Hoon build, security audit, or interoperability test.

The old source tree is retained under `reference/stead/` for specification traceability and selective reuse. Its build/deployment instructions and architecture locks are not this experiment's live instructions. Inherited workflows are archived there rather than activated. Original license and third-party notices remain at the root.

Native application logic and Git semantics are the target. Browser JavaScript, Linux hosting, independent CI execution, and a documented replaceable bulk-storage boundary are allowed in the staged implementation. This is not a claim that every infrastructure dependency has been rewritten in Hoon.

No candidate dependency is approved by being named here. In particular, Urgit reuse requires a recorded license decision and independent compatibility/security results.

## Ecosystem roadmap and contributor guidance

[Roadmap issue #1](https://github.com/ScottTpirate/stead-urbit/issues/1) links the 30 tracked tasks. The [ecosystem plan](docs/urbit/ECOSYSTEM_PLAN.md) preserves phases 0–5 and adds a supported ecosystem release gate. Read the [developer guide](docs/urbit/DEVELOPER_GUIDE.md) for repo-local Hoon skills and checks, and the [carryover ledger](docs/urbit/STEAD_CARRYOVER.md) before reusing original Stead work.

These are implementation requirements and tested planning tools, not evidence that the native product is complete. Existing agent work remains the priority. CONTRIBUTING.md, SECURITY.md and SUPPORT.md describe the current experimental scope.

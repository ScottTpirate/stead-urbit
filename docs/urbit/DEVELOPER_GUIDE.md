# Developer and agent enablement

## Start with the working increment

Read root AGENTS.md and AGENT_HANDOFF.md. Preserve the implementation agent's branch and uncommitted work. Use the pinned toolchain and guarded native commands established by URB-010/020; see [the local edit/build loop](DEV_FLOW.md). A successful static validator does not prove a Hoon desk compiles.

Static checks shipped by this supplement:

```sh
python3 scripts/urbit/validate_plan.py
python3 scripts/urbit/check_ecosystem.py
python3 -m unittest discover -s tests/urbit -p 'test_*.py'
```

The legacy validator currently expects planned statuses; changing execution tracking must be an explicit schema change, not a claim that all work remains unfinished or finished. Live issue status and linked evidence describe actual progress.

## Four local skills, loaded only when relevant

| Skill | Use |
| --- | --- |
| stead-hoon | Typed Hoon edits, source layout, pinned examples and compile/debug loop. |
| stead-gall-security | Native state, save/load, identity/policy, events, watchers and effects. |
| stead-native-tests | Unit/integration/Git tests, negative controls and honest evidence. |
| stead-urbit-release | Desks, frontend artifacts, publisher trust, migrations and recovery. |

They live in `.agents/skills/<name>/SKILL.md`. Current Codex documentation supports this repository-scoped location. Other agent tools may need a reviewed adapter to their discovery path; do not duplicate divergent instructions or globally install the pack by default. AGENTS.md describes the repository rules, while skills provide task-specific workflows. Neither is an enforced security boundary.

These skills are original project guidance with references, not vendored third-party implementation and not validated Hoon source. The [completed frozen comparison](evidence/2026-09-26/workflow-evaluation-v2/README.md) recorded five of six tasks passing in both conditions. Both missed the same authorization mutant. This one pair establishes no observed pass-rate benefit, general effectiveness or complete tool isolation; the report retains its input and timing limitations.

## Community material worth evaluating

`thelifeandtimes/running-urbit` at `90912c1425573de37110a65627c6ab4bf125586c` is an MIT community skill collection related to `ryanthomas-org/urbit-skills`. README, LICENSE and the Gall skill were inspected. Its `safe` annotation means the reviewer did not see obvious malicious instructions; `works` means manual execution. They are not interchangeable.

The sampled Gall skill's minimal example serializes untagged state but attempts to load a tagged version union, while a later example recommends a version tag. This is a concrete reason not to copy it as a proven template. It was not compiled in this audit. Upstream material remains a reference-only candidate; it has not been installed or copied into the project.

Intake process: exact commit and license; inspect all instructions/scripts; validate every copied code example against our pinned compiler; run denied/failure cases; retain required notices; compare against a held-out task corpus; approve only the useful subset. Disable automatic execution from comments, docs, retrieved pages or unknown SKILL.md files. conn.sock/dojo interaction tools get disposable fake ships only, no production identity material.

The six-task evaluation covers typed function compilation, type-error repair, save/load migration, denied poke/watch, missing-test detection and clean desk assembly. Its report records the observed model/settings, pinned toolchain, attempts, baseline and assisted outcomes, and failures. Structural skill validity remains separate from functional execution.

## Editor and build ergonomics

The [optional Hoon language-server review](reviews/URB170_EDITOR_TOOL_REVIEW_20260925.md) rejected the pinned candidate for adoption: its bridge source failed the pinned Node parser check before any ship connection. No editor package or agent was installed, and native compatibility is unqualified. Any future editor evaluation must use disposable fake ships and pin its inputs. Compiler and actual unit/integration tests remain authoritative.

Hoon uses LF source files; scope editor/Git settings to new source, not historical or byte-fidelity fixtures. Do not mass-normalize Markdown frontmatter, imported Git, symlinks or golden binary data. Keep dependencies reproducible; use the desk skeleton's source/developer-package separation without floating `peru reup` in CI.

The native `-test` thread discovers `test-` arms. Tests returning empty tang indicate success, but a run with zero expected tests is not success for our harness. Verify expected arms, structured result, timeout and failure propagation rather than merely grepping for 'built'. Keep snapshots/logs short, redacted and linked to source/toolchain identities.

## Primary references

- https://learn.chatgpt.com/docs/build-skills
- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://docs.urbit.org/build-on-urbit/environment
- https://docs.urbit.org/build-on-urbit/userspace/unit-tests
- https://github.com/urbit/desk-skeleton
- https://github.com/urbit/hoon-language-server
- https://github.com/thelifeandtimes/running-urbit/tree/90912c1425573de37110a65627c6ab4bf125586c

## GitHub milestone fields

The seven milestone definitions and all issue numbers are checked in. The live derivative repository now has all seven milestone objects and task assignments, verified September 26, 2026. The integrator can inspect or reconcile them using the authenticated GitHub CLI:

```sh
python3 scripts/urbit/sync_milestones.py
python3 scripts/urbit/sync_milestones.py --apply
```

Default mode makes no network calls or writes. Apply mode targets only ScottTpirate/stead-urbit, checks every issue identity and existing assignment before mutations, creates missing titles, and preserves existing statuses/visibility/protection. It refuses conflicting assignments and is resumable after inspecting partial failures. Run with one coordinator: GitHub does not provide an atomic transaction over these objects, and another operator must not edit milestones concurrently. The CLI tests use a mocked API; the observed live milestone state is separate evidence. The CLI is an operator convenience, not a runtime dependency.

Schema references: https://docs.github.com/en/rest/issues/milestones ; https://cli.github.com/manual/gh_api .

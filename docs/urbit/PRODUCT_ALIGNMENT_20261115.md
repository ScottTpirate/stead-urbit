# Product alignment record — November 15, 2026

This is the historical record of the initial documentation-only alignment.
The user subsequently authorized all T01–T32 implementation and supervised updates
on the existing Lightsail pilot. Follow the [current handoff](AGENT_HANDOFF.md),
[capability matrix](CAPABILITY_MATRIX.md) and
[execution plan](../../specs/urbit/product-execution-plan.yaml) for that ongoing
work. Statements below about no implementation, commits or deployment apply to
the initial alignment only.

## Scope and baseline

The user requested review of the supplied assessment/instructions and alignment
of project documents/directives. The documents' embedded request to execute
implementation packages is source material, not a separate instruction to build
all 32 packages, deploy, or close gates. This change adopts the product direction
and prepares a consistent implementation handoff; runtime behavior is unchanged.

The active repository is `ScottTpirate/stead-urbit`, inspected on `main` at
`539825650c60e606634bf4ab5967b698a6daa6e3`, exactly the review baseline. Its working
tree was clean before this change. Origin is
`https://github.com/ScottTpirate/stead-urbit.git`; upstream points to the original
Stead repository with push disabled. The chat's initial `/home/skilgore/stead`
checkout is the older `phase1` project, not the handoff target; it was inspected
and left unchanged. No worktrees were created or other active checkouts reset.

The supplied screenshot reference is UI `dbc8cc0`. This alignment read the
review, plan, kickoff and pasted assessment, inspected current source/profiles,
and read live GitHub issue state. It did not receive or re-inspect the original
24-image archive, exercise the pilot, rerun native qualification or measure
capacity. Existing results remain their original source/profile's evidence.

## Decisions incorporated

The [master directive](MASTER_BUILD_DIRECTIVE.md) remains the architecture
authority. The [experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) owns the
current product vocabulary, defaults, state distinctions, migration dispositions
and G1–G5 outcomes. The [capability matrix](CAPABILITY_MATRIX.md) records baseline
implementation, named qualification and support limits. The
[execution plan](../../specs/urbit/product-execution-plan.yaml) retains all 32
packages, dependencies, acceptance criteria and evidence requirements, adds
canonical parent issue mappings, and labels implementation as pending.

| Requirement | Aligned current guidance |
| --- | --- |
| Preserve native authority; redesign around completing work | Master directive, AGENTS, README, current handoff and experience contract. |
| One Work; optional independent repositories; scoped contextual relationships | Experience contract, Phase 2 compatibility note and Code Home profile. Legacy IDs and relation meanings retained for migration. |
| Accountable human / worker / run; stable principal vs runtime | Experience contract, job profile, browser identity profile and master directive. |
| Separate execution-contract revisions from discussion | Experience contract and job/Phase 2 profiles; current combined revision explicitly remains baseline. |
| Typed Changes; expiry vs durable review and explicit adoption | Job, delivery and protected-review profiles; current native eligibility unchanged until versioned implementation. |
| No-Code agent Docs journey first; bounded effects and later automation | Job profile, handoff, roadmap and package dependencies. Deterministic Code proof is parallel, not a product prerequisite. |
| Canonical Markdown, safe readable Docs and one repository-file origin | Experience contract, portable Docs and Phase 2 profiles. Existing private publication boundaries retained. |
| Precise UX defaults, all states, all 24 screen recommendations | Experience contract and immutable source review; no synthetic/live acceptance conflation. |
| Git profile honesty, source cutover and House boundaries | Master directive, Code profiles, deployment and capability matrix. |
| Capacity, imports, operations and independent beta gates | Roadmap, ecosystem/release guidance and complete package plan. |
| Remove stale bootstrap orders; preserve actual user instructions | Handoff, AGENTS, roadmap, ecosystem and developer guide. Existing quickstarts retain actual controls and label target redesign separately. |

The dated [full review](reviews/2026-11-15-product-review.md) is retained verbatim
as the detailed source input. Its recommendations are interpreted through the
adopted experience contract; it is not a competing live directive. The kickoff's
useful instructions are integrated into the current handoff rather than creating
another agent instruction file. The attached Library originals are unchanged.

## Preserved boundaries and outstanding work

- M0–M6, all canonical URB task definitions, dependencies, acceptance criteria
  and issue mappings remain intact. Catalogs link the new package plan rather
  than replace their tasks. The legacy backlog's top-level status now explains
  that execution is tracked in live issues; per-task legacy planned fields are
  not a current completion ledger.
- November 15 live search found 16 open canonical URB tasks, including #29.
  Its older human-trial wording differs from the November 9 local review record.
  The capability matrix records this discrepancy. No tracker issues were edited,
  created or closed; optional #37–#40 remain outside required delivery.
- Frozen contracts, source hashes, prior acceptance, failed runs, license notices,
  `reference/stead/`, and runtime/source code remain unchanged. In particular,
  `CONTRACT_AMENDMENT_2.md` keeps its frozen SHA-256
  `f9793a947b4ba69e9099ec0cd68ed004602cb0ffe6fbbf79f9f464cb256315c6`.
- T01 has adopted product decisions and interface sketches. Concrete wire/routes,
  state-version designs, migration fixtures and native/UX acceptance remain open.
  T32 is not complete: final shipped-product guidance depends on T18/T23/T28.
- Next: finish T01 interface/migration review; prepare T02 controls, T06 capacity
  inventory and T19 bounded live-tree investigation. Shared mutations wait for
  T01; subsequent packages follow their exact dependency graph.
- New runtime/model tests, external effects, deployment, procurement and source
  cutover were not performed. Existing owner/release decisions remain separate.

## Input provenance

| Supplied file | SHA-256 |
| --- | --- |
| Stead-Product-and-Architecture-Review.md | `59b43ffff05176000e0f9823244e417a4c7a4d7f8258f79821666619a5825973` |
| Stead-Agent-Execution-Plan.yaml | `d5f4bf3fa0882cb0926ac747cbc768e5fe5162cc94f4e9e8a61dd1ebf65d0fb5` |
| Stead-Agent-Kickoff.md | `8d802da63a11c5974554e32087418405f843066757f360fd143e4fd875779de3` |
| Pasted text.txt | `786fdfa613fb1c7e5e57991cbf373725a5fa891e0d60b0bfcb8831ad3cb03072` |

## Verification

The planning validators pass: 18 baseline task definitions, 30 combined URB
tasks, seven milestones and four skill files. These checks validate planning
structure only. The product-plan audit passed: 32 unique packages, acyclic dependencies, 151
existing source-anchor references, unchanged original packet fields and valid
canonical parent mappings. All 170 local Markdown references resolve; whitespace
checks pass. Both freeze manifests still match all 14 recorded paths. All 29
changed/added files are documents or planning metadata; runtime/source and the
original Stead checkout remain unchanged. Independent documentation review
passed with no blocking findings. This is not native or product-journey
qualification. Changes remain local and uncommitted; no remote publish occurred.

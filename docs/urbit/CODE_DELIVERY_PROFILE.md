# Native review and build transitions

## Product target and baseline boundary

The [product experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) and
[execution plan](../../specs/urbit/product-execution-plan.yaml) govern new
work. The reducer and manual workflow below describe the implemented baseline
at `539825650c60e606634bf4ab5967b698a6daa6e3`; they are not the target Delegate
experience. A proposal grant/copyable brief does not start a worker.

T12 adds a narrow shared Change envelope with typed Doc/code targets, exact
before/after references, source Work, original author/run, checks and reviews.
Reuse these Git reducers. Generic Work runs and document review require no
Code repository; G3/T18 no-Code Docs acceptance precedes the complete forge
journey. [Run contract](AGENT_JOB_PROFILE.md)

T13 intentionally changes the baseline coupling between delegation eligibility
and durable review. An execution lease/grant expiry stops new worker effects
and publication, but preserves output already submitted and its provenance.
Current authorized readers/reviewers may inspect that exact proposal without
reviving the worker grant. Revocation/compromise can quarantine output. An
explicit adoption decision requires current adopter acceptance authority,
current scope and target/base, exact output digest, required checks and fresh
review where required. Adoption preserves the original author/run and never
renews old credentials or silently accepts compromised output. Keep existing
eligibility checks until versioned migration and time-shift, revocation, replay
and changed-target tests qualify the replacement; documentation alone does
not enable adoption.

Review required remains the default for deliverables and protected targets.
Ordinary permitted comments and progress are direct operations. A producer
cannot approve its own output. T25 may add steward-authorized narrow low-risk
automatic acceptance using separate reviewer/acceptance authority, after its
dependencies pass. Submission, acceptance, Work completion, build and deployment
remain distinct. All declared required outcomes and checks must pass before
Work becomes Done; a single merged branch cannot complete unrelated required
outputs.

## Baseline reducer behavior

The delivery reducer owns one bounded version-1 board for one exact Home,
project, repository and authority epoch. It takes already authenticated
actors, re-resolves their current binding and checks the Work, branch and
action through the current Home policy. The board retains proposal revisions,
review evidence, build attempts, release intents and revoked delegations.
An applied result contains the replacement board. An exact authorized replay
returns the current board unchanged. Rejection leaves the caller's board
intact.

## Proposal and review

The Home resolves the proposal's exact immutable source through an authorized
object view. The proposal binds an author, Work item, repository, target
branch, expected prior commit, head OID, authority epoch and revision. Only
the original principal binding can revise a proposal. A revision increments
by one and leaves prior review evidence in the board for history.

A delegation binds its sponsor and worker to one Work item and target branch
for at most 24 hours, further limited by both current memberships. The sponsor
must hold delegation authority, and the worker must hold proposal-only agent
authority. Revocation or a changed membership invalidates later use, even
when a prior proposal was approved. The delegation cannot confer review,
merge, build-runner or release permission.

A review records the entire exact revision and a separate current reviewer.
The reducer returns an exact candidate branch update only after current
authorization for a separate merger and the stored reviewer, verification of
the latest proposal, and comparison with the current target ref. Home must
admit that candidate through its existing graph, ancestry and atomic ref
transaction. Candidate evaluation performs no write on the repository.

## Build and release

A queued build binds the exact proposal, the Home-resolved source digest and
an allowlisted recipe digest. An independently authorized worker obtains a
two-minute lease for a numbered attempt. An expired claim may be replaced
using its expected attempt number, with at most three attempts. A live claim
has one worker. Completion checks the current requester and worker bindings,
current recipe, exact revision, exact claim, and matching source and recipe.
The authority must verify the output evidence for that exact job, attempt,
worker and outcome through its trusted artifact readback or authenticated
attestation policy. It cannot accept a caller-supplied verification boolean.
An exact completion retry can recover its stored result after a later
proposal revision or lease expiration. It still requires the original
worker binding, current historical proposal and build permissions, and
verified artifact evidence.

A finished build records a passed or failed result. Cancellation ends an
uncompleted job. A release intent requires a currently allowed release actor
separate from the author, requester and runner. It also requires a passed
artifact verification, an exact stored review with current reviewer authority,
the accepted ref receipt for that proposal, and the current target head.
At most one release intent may be recorded per build. A release intent does
not launch a deployment. External execution needs its own admitted worker
and idempotent effect reconciliation.

An exact release retry returns its stored result after the target head
advances or a later proposal revision is submitted. Current permissions for
the original release, proposal, build and review still apply, including
delegation and membership checks. The release actor and artifact must still
match the stored result. Creating a release intent requires fresh source,
proposal, target-head and acceptance checks.

The proof profile holds at most 32 delegations, builds and releases and 64
proposal revisions and reviews per board. Capacity fails closed. Production
service wiring, bounded durable artifact transport, a v1 saved-state
predecessor matrix, and external worker operation require their own evidence.

## Try a Work delegation

This is the baseline manual proposal workflow, not automatic delegation or
the planned no-Code run experience.

In a project with inline Code, open a Work item as a maintainer. Choose
**Delegate to an agent** (renamed **Grant agent proposal access** in the
implementation candidate), enter the agent's own Urbit ID, choose the target
branch, and set an expiration. The member must already have project access.
The human assignee stays responsible for the ticket. Home shows proposal access
and the proposals submitted using it.

Use **Copy agent brief** to pass the current task to the worker. A worker with
its own approved session can verify a private copy of the brief with
`python3 scripts/urbit/agent_proposal.py --brief BRIEF --session-file SESSION`.
Both files must be owned by the worker and have mode 0600. The session uses the
same format as the member export tool and stays with the worker's Home client.
Keep it out of the model prompt, repository, and logs. The brief contains
project content.

Give the worker a disposable checkout of the authorized repository. For a
first task, ask it to add a README example and run the project's checks. Have
an authorized Git writer stage the resulting commit on a feature branch, then
give the agent the exact original target and staged commit IDs. Run the same
command with `--base BASE --head HEAD`. It rechecks current delegation and the exact Work pin, submits under the worker's identity, and confirms the exact proposal
through Home. A retry with the same inputs can recover the proposal. The ticket
links the submitted revision for independent review.

This workflow hands off one task at a time to an external worker. Automatic
worker dispatch, execution progress, and the external Git profile's delegation,
build and release steps are separate unfinished paths.

### Versioned brief compatibility in the implementation candidate

The single-Work read can advertise `execution_contract_protocol` equal to
`stead.work-contract/1` with a complete execution revision/digest pair. The
candidate browser then emits `stead.agent-brief/2`; a partial, malformed or
unknown pin is rejected rather than silently downgraded. An older Home without
these fields continues to produce brief/1, retaining its strict aggregate
`work_revision` comparison. The brief link always names the canonical scoped
Work resource, independent of the current browser view. Copying it does not
start a worker.

The helper accepts both exact shapes. A brief/2 goal is unchanged by ordinary
comments, status, priority, type or assignment edits, while exact title or
description edits (including editing and reverting) advance the pin. Current
membership/delegation/target checks still apply. This preflight comparison is
not atomic with native Code submission; T14 must close that race before claiming
stale-contract publication is fenced at final authority. Qualification status
is recorded in the [capability matrix](CAPABILITY_MATRIX.md).

[Diagnostic run 43846986399](https://github.com/ScottTpirate/stead-urbit/actions/runs/43846986399)
records source-bound positive results for `stead-work-contract` (6 registered
arms) and `stead-work-delegations` (3) in its exact candidate/controller
composition. Counts follow the trusted all-pass sequence; original positive-arm
transcripts were not exported. The delegation suite's native HTTP-handler cases
do not establish a new network/browser round trip or start an external worker.
The `stead-run` suite failed to compile, so this result does not close the
generic Run lifecycle, atomic publication or no-Code agent journey gates.

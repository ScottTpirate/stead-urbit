# Native review and build transitions

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

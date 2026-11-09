# Revision-addressed source control for Stead

Stead supports portable Git objects, stock clients and offline clones. A home
owns acceptance, access policy and ref advancement. In this design, source
objects are immutable and ref changes compare an expected prior OID at the
authority. Proposal creation, code review, build execution, ref acceptance and
release are separate transitions, each with its own authorization.

[Anthropic's Scion writeup](https://www.anthropic.com/research/redesigning-source-control)
describes exposing source history and file queries as first-class operations,
cheap access to selected objects, and rebuildable derived data. Stead adopts
those interfaces with Git identities and its single native home authority. The
article's workload and performance observations belong to Anthropic's system.

## Agent and tool contract

- Address every read by repository and exact revision. A branch name first
  resolves to an OID. A caller can request a bounded path listing, file,
  ancestry check or diff without a working copy. Cursors bind the query,
  authorization and snapshot. Large replies use bounded continuation.
- Treat the repository as the access boundary. Verify current access and
  reachability from allowed refs or an explicitly granted proposal on each
  request. Knowing an OID grants no access. Cache content only inside the
  authorized custody domain. Revalidate grants before each response or
  continuation and keep private objects and metadata out of shared caches.
- An agent or person proposes a change with a work item, repository, base,
  head, revision, scope, epoch and durable operation ID. Specifying a commit
  does not grant merge rights. An independently authorized principal accepts an
  exact reviewed revision against the current ref and policy. Reusing an
  operation ID with the same input returns the prior receipt. Different input
  conflicts.
- A build job reads its exact authorized source revision. It records the recipe
  and isolated runner identity, result, artifact hashes and source provenance.
  Untrusted code runs off the home. Release acceptance independently verifies
  the required checks and authority.
- Derive ancestry, path history, change summaries and search from validated
  immutable objects and accepted records. Key derived data by repository,
  object format, OID and index schema. Rebuild it on import or upgrade without
  mutating object bytes. Use SHA-1 for the initial Git wire profile and keep the
  object format explicit in contracts. A stronger digest can attest bytes
  without rewriting original IDs.

## Explicit transitions

The pack decoder uses tagged `%scan`, `%resolve`, `%complete` and
`%rejected` values. Only completion produces reconstructed candidate objects.
Admission still requires validation of object structure and graph, closure of
the proposed refs, policy, quotas, current authority epoch and ref compare and
swap. Rejection drops candidate state. A caller persisting the decoder must
version the record and bind it to the upload digest and authorization scope.

Use named transitions for durable work as well. A job claim has a bounded lease
and recorded attempt. Completion binds the attempt and exact inputs. Revocation,
cancellation, expiry and failures have distinct terminal outcomes. A review
proof is tied to one proposal revision, so edits create a new review target.
An accepted state transition commits the outcome and its receipt together.
External runners reconcile effect intents with results by operation ID after
interruption. A socket, a worker's memory or a successful HTTP upload alone
cannot represent a durable outcome.

The [native graph profile](CODE_GIT_GRAPH_PROFILE.md) implements bounded
closure traversal and an exact-commit file read from an authorized object
view. These are building blocks for the revision-addressed API. The home still
has to select and reauthorize the view for each request, persist transitions,
and qualify the complete transport before exposing them.

## Repository acceptance contract

Use the existing project Home as the sole authority. A staged upload belongs
to one Home, repository, principal binding and authority epoch. Its immutable
input includes the canonical ordered ref updates and SHA-256 of the exact
uploaded bytes. Native validation produces a sealed candidate containing the
object inventory, repository view used for graph and ancestry checks, and
exact target OIDs. Client input never supplies trusted graph facts or review
results. An unrelated ref or object cannot extend the scoped view.

The final transition rechecks current credentials, binding, grants, authority
epoch, applicable reviews, protection rules, quotas and expected prior OIDs.
Fast-forward evidence follows verified commit parents from the proposed tip to
the prior tip. Incomplete traversal rejects the update. If a change invalidates
the view used for validation, revalidate under the new view before acceptance.
Promote validated objects, update every requested ref, append the journal record
and store the receipt in a single versioned saved-state transition. A failed
transition retains the previous objects, refs and accepted journal.

The accepted receipt binds the operation ID, authenticated principal,
repository, epoch, exact input digest and resulting OIDs. A retry with the
same ID and digest returns that receipt after current authorization. A changed
digest conflicts. Capacity exhaustion fails closed until bounded retention or
export is qualified. Home restart invalidates in-flight bearer admissions and
requires fresh authorization for any staged job; a completed receipt remains
durable. Report ref success to Git only after the authoritative transition.

The [native Home profile](CODE_HOME_PROFILE.md) integrates the repository
reducer into the Home with bounded synchronous Smart HTTP. The current
prototype holds decoded objects only during the accepting event. The durable
job and replay contracts above apply to a later staged receive path.
The [delivery reducer](CODE_DELIVERY_PROFILE.md) implements explicit proposal,
review, build and release transitions. Home persistence and protected-ref
application must bind those transitions to a single authoritative commit.

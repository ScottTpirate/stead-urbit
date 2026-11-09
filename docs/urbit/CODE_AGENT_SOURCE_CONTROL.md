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

This profile guides the future revision-addressed API, durable jobs and native
repository integration. Each interface requires its own policy, persistence,
retry, boundedness and native conformance tests before exposure.

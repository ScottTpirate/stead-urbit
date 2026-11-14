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

The [native Home profile](CODE_HOME_PROFILE.md) saves the complete bounded
Smart HTTP upload before a separate event decodes and accepts it. It binds a
pending upload to its exact wire bytes and the current actor. A fresh
authorized retry can reattach to that pending job. The final ref transition
remains atomic and does bounded validation within one event.
The [delivery reducer](CODE_DELIVERY_PROFILE.md) supplies explicit transitions
for the Home-owned review and build board. The protected ref and exact merge
receipt commit together. Release intent requires separate authority and
verified artifact bytes. [Local workflow verification](PHASE34_LOCAL_WORKFLOW_20261109.md)

## External write integration boundary

The first external profile stores one immutable accepted manifest. Keep the
v7 saved representation readable. A future writable profile needs its own
version, with a current manifest and generation, bounded pending intents, and
receipts indexed by operation ID. Preserve the original snapshot approval
when initializing the first generation.

For each upload, record the project, epoch, actor binding, base snapshot and
generation, ordered expected ref updates, original wire digest, and a narrow
worker lease. A verified worker can stage a complete immutable candidate in the
pack store and report object kind and ancestry facts for that exact candidate.
Authenticate the worker and bind its evidence to the admitted job, attempt,
upload digest, base, and candidate. Wire clients cannot submit trusted facts.

The Home computes the resulting refs from the current ones, compares the
candidate’s complete ref map, and rechecks current uploader permissions. It
must atomically advance the manifest/generation, resolve the pending intent,
and save the receipt. Exact same-actor retries can return that receipt even
after the ref advances again, subject to current authorization. A successful
worker response or staged manifest cannot cause `receive-pack` to report
success. Restart requires fresh worker and uploader admission for an unfinished
job and must preserve an already accepted receipt.

Use one review and build board with storage-specific lookups for committed
refs, exact source, and accepted receipts. Pin proposal revisions and builds to
an exact source manifest. A protected merge needs the current board’s exact
independent approval and must bind the accepted pointer, receipt and merge
record in the same event. A build needs independently verified tree bytes for
its pinned Git OID. Retain the accepted, proposal, build and recovery snapshots
before reclaiming other packs. Missing retained bytes suspend recovery and
publication until the exact digest is recovered.

The pure `stead-code-pack-ledger` module implements admission, verification,
commit and exact receipt replay over one project. It caps accepted advances at
seven beyond genesis, rejects a previous Home incarnation for pending work,
and validates saved lineage against the original accepted anchor. Four pinned
native arms and the deliberate failure control ran successfully. This module
has no credential or worker protocol of its own; the authenticated adapter,
selected manifest reads, and actual `receive-pack` transition are separate.

Keep the large upload in the adapter's bounded private spool. The worker
gets only the admitted digest, selected pack, exact ref commands and a narrow
attempt identifier. It never receives the individual's Git secret. The adapter
forwards the client's Basic credential only to the configured Home TLS origin.
Use an independently authenticated local control or dedicated off-host worker
identity for evidence, not a general Git credential or browser cookie.
Record worker evidence only after the exact pack and manifest are durable.

The worker serializer binds the independently pinned `stead.git-pack-admission/1`
bytes, including the actor binding, incarnation, attempt, admitted upload hash
and ordered commands. It emits `stead.git-pack-worker-proof/1` with indexed
commands and verified ancestry facts, the candidate manifest digest, and the
pack and object inventory hashes. Both documents are bounded canonical JSON.
The Home must reconstruct the candidate refs and recompute the manifest digest.
An expired worker returns no proof. Its previously staged immutable bytes may
remain for retention to reconcile. The proof format itself gives no authority.

The native decoder runs against the exact Python canonical bytes and the
Home-selected base. Four pinned native tests verified the resulting manifest,
raw ref bytes, and refusals for changed scope, command order, HEAD, inventory
and framing. This verifies parsing and reconstruction; the caller must still
authenticate both the worker and the Git principal before using the proof.

The typed control gate rejects sealed, retired and unavailable Home contexts,
the wrong epoch, nonwriters, expired credentials, and direct changes to the
default or protected branches. It checks a worker's exact admission and proof
before verifying or committing a new attempt. Receipt lookup is separate:
the same binding may read the exact result with a fresh write credential;
that path cannot make a new acceptance. Three native tests passed. The
transport still needs to establish the worker's identity and invoke this gate
from the authoritative Gall event.

The private message wrapper now binds the canonically encoded admission to
the same writer and event clock, then decodes and checks the worker proof
against the Home-selected base. Three native tests exercised two successive
changes and retrieval of exact earlier receipts from their original bases.
The wrapper has no effect on persistent Home state by itself; no Gall event
or Smart HTTP write route invokes it yet.

Default and otherwise protected branches stay closed to direct external
updates until the exact review commit is implemented. For an ambiguous stock
client response, reconcile the exact digest and ordered commands under the
same current binding and scope. Reconfirm the expected result before reporting
a historical receipt. Restart closes outstanding worker admissions; sealed or
retired homes and missing policy deny new work.

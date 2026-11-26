# Native Home Git development profile

## Repository model alignment

The paragraphs below describe the bounded baseline at
`539825650c60e606634bf4ab5967b698a6daa6e3`. Its one-repository-per-project
scope construction is not the target product model. T04 in the
[execution plan](../../specs/urbit/product-execution-plan.yaml) introduces an
independent Repository ID and explicit association to one owning project. A
project has zero or multiple repositories; Work and Docs remain complete
without Code. Preserve existing repository IDs, refs, OIDs, receipts and
permissions during versioned migration, including legacy IDs equal to a
project ID. No alias may broaden authorization or silently move ownership.

T20 provides one product-level repository capability interface across inline
and external profiles. Expose exact supported tree/file/ref/compare/proposal/
check/write operations, size limits and exclusions. Do not claim full-history
push, equivalent external delivery, LFS or SHA-256 support from this bounded
profile. [Current capability matrix](CAPABILITY_MATRIX.md)

T19 must reproduce the reported live tree failure with actual profile, source,
authorization and response evidence before claiming its cause or repair.
Distinguish empty, unavailable, stale and unsupported results; demo tree data
cannot establish live readiness. New Code work follows the
[experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) while the safeguards and
baseline behavior below remain in force until their reviewed migrations pass.

The implementation candidate adds a read-only Markdown reader to the existing
accepted-snapshot file browser: Read is the default for supported Markdown
filenames, with exact Raw/Copy contents and commit/size Details. It uses the
existing authorized file response and preserves its origin. Empty, binary,
oversized, stale and denied states remain explicit. Eight remote host and eight
synthetic browser cases
passed with full TypeScript and verified cleanup. This is frontend evidence;
the current pilot has not received this change, and it establishes no additional
Git write or multi-repository capability.

## Current candidate native evidence

[Diagnostic run 43846986399](https://github.com/ScottTpirate/stead-urbit/actions/runs/43846986399)
built Home and records source-bound positive results for 39 suites containing
254 registered arms. Nine suites containing the other 75 arms failed to
compile. This applies to candidate `6e6c21a` composed with controller
`e316934`, not to every later checkout change. Positive results are derived
from the exact trusted test sequence and closed observed counts; original
positive-arm transcripts were not exported.

The positive suites include the external pack anchor, read, push, ledger,
proof, control, carrier, relay-wire, worker-signature, admission, review and
review-board helpers, plus the v8/v9 saved-envelope rehearsals. This is native
helper evidence. It does not rerun stock-client HTTP conformance, qualify
independent repository IDs, establish a new browser journey or deploy the
current source. The ordinary journey and saved-state capture were not reached;
full qualification remains open. The historical baseline below retains its
original evidence scope.

## Baseline development behavior

A project maintainer can enable one SHA-1 repository through the project
overview. The Code view appears after explicit enablement. A reader can issue
a read credential. A contributor or maintainer can issue a write credential.
The Home authorizes current role, member binding, repository and authority
epoch on each Git request. Grant removal takes effect on the next request,
including a push that had started sending bytes before removal.

Use the clone URL shown in Code. When a stock client prompts, use the username
`stead` and the individually issued credential as the password. Keep the URL
credential-free. The credential expires at the earliest of 15 minutes,
the issuing session expiry and the member expiry. The credential ledger stores only a digest. The active HTTP reply lease
holds the submitted bearer until it completes or disconnects. The Code view exposes its revocation handle separately.
Startup/bootstrap and team reconfiguration retire all device credentials.

The Git path has a separate binary request boundary and uses the same native
Eyre ownership and secure-origin checks as the Home. It rejects browser
cookies, proxy overrides and cross-origin authorization. The configured Home
owns objects, refs and accepted receipts in a single Gall transition.
The first receive event puts the exact wire bytes in a durable bounded queue.
It schedules a separate native event with a transient reply lease. The second
event rechecks the live reply route, credential, actor, project and authority
epoch before decoding or applying the pack. It removes the queue entry and
commits refs and the receipt together. A reply reports success only after the
accepted event.
Receive checks current reachability, pack structure, exact SHA-1 object IDs,
graph and branch ancestry, policy, quota and prior OIDs. A protected branch
rejects direct writes. The [protected review path](CODE_PROTECTED_REVIEW_PROFILE.md)
checks the exact approved proposal before applying a single ref change.
An [assigned external worker](CODE_BUILD_WORKER.md) can claim a bounded lease
and return the artifact and its digest.

The development bounds are four repositories per Home, 64 objects and
256 KiB of accepted object bodies per repository, 16 refs, 32 accepted push
receipts, eight ref commands, and 64 KiB per incoming request. The queue holds
four complete uploads per Home and two per current actor binding. Staged
uploads expire within five minutes. A disconnected or restarted client can
present the same complete upload with a current authorized credential before
expiry. The Home never starts a saved upload on its own. Expired entries are
pruned on the next admission. The development profile still needs larger
repository measurements and receipt/object retention management.
This profile handles SHA-1 Smart HTTP v0, full clone/fetch, fast-forward
updates, branch creation/deletion and tags. SHA-256, LFS, shallow and partial
clone, arbitrary ref namespaces and unqualified Git object shapes are outside
the initial profile. [Git HTTP protocol](https://git-scm.com/docs/gitprotocol-http)

## State and verification

Work/Docs-only Home state stays on v3. Enabling Code saves an outer v4 envelope
with the existing team state plus its repository map. Queued uploads, review
boards and build evidence use v5. V4 remains readable and remains the emitted
format for repositories with no queued or delivery state. Load validates
each supported envelope, including queue scope and wire hashes. It starts
with an empty reply-lease map and credential ledger. It checks capacity,
object hashes and graph closure, then reconstructs current refs from
the ordered accepted receipt history before serving a new incarnation.
The Work/Docs journal and views keep their existing independent restore
checks. The [local populated recovery](LOCAL_CODE_IMPORT_20261109.md#saved-home-state)
checked both state fingerprints and original Git objects, refs, and protection
after reload and bootstrap of a stopped v4 copy.

The native browser lane invokes a separate stock-client diagnostic after
the team workflow. It uses the same disposable member, verified native TLS
and pinned Git executable and HTTP helper. The diagnostic reports native
branch/tag push, clone/fetch and denial observations independently of the
Work/Docs acceptance count. See the [release packaging profile](RELEASE_PACKAGING.md)
for the declared saved-state versions.

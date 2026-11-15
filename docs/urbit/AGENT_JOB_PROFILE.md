# Work agent jobs and durable runs

**Status: adopted target contract, not an implemented job API.** The November
15, 2026 alignment replaces the former Code-first job proposal. At baseline
`539825650c60e606634bf4ab5967b698a6daa6e3`, delegation grants proposal access
and copies a brief; it does not dispatch a worker. No run, model adapter or
autonomous product gate is closed by this document.

Follow the [product experience contract](PRODUCT_EXPERIENCE_CONTRACT.md),
[capability matrix](CAPABILITY_MATRIX.md), and T03/T05/T12–T18 in the
[execution plan](../../specs/urbit/product-execution-plan.yaml). The first
user-facing acceptance is G3/T18: a document update in a project with no Code.
A deterministic inline-Code recipe remains a separate parallel proof of
execution and isolation. It neither substitutes for nor blocks Docs delivery.

The reserved pure `stead-run-state` and `stead-run` source now implements
bounded no-Code lifecycle transitions, leases, effect reservation and explicit
reconciliation. [Independent review](evidence/2026-11-15/controller-refresh/reserved-run-review.json)
binds ten prepared native arms; none has run. Current authorization and
payload-aware effect gates are mandatory trusted Home adapters, still absent
from live routes. A transition returns candidate ordinary Work/Inbox/Doc intents;
it does not dispatch a process. Restart clears live leases and emits no external
intent. Canonical contracts preserve original grant, exact Doc targets and
normalized target order; result references match the Doc Change vocabulary.
The reserved closed command decoder has six additional independently reviewed,
uncompiled native arms; it validates intent shape and never substitutes for
current Home authority. Versioned history/carrier integration, actual execution
and G3 remain open.

## Reuse and separation

- `stead-code-delivery.hoon` checks current delegation, membership, proposal and
  review authority. Its build transitions supply lease, expected-attempt,
  cancellation and exact-replay patterns. The expiry/adoption contract below
  needs explicit migration and negative tests; retain existing eligibility
  checks until that replacement is implemented and qualified.
- `stead-code-build-home.hoon` exposes authenticated build operations and
  verifies artifact bytes. Those post-proposal jobs remain distinct from
  pre-proposal runs; do not repurpose them as generic task jobs.
- `code_build_worker.py` supplies pinned inputs, isolation, bounded resources
  and receipt-last publication. Its existing recipe inventories a commit;
  it neither edits source nor calls a model. Reuse the isolation boundary
  with a separate typed job/result protocol.
- `agent_proposal.py` verifies a private worker session, current Work and
  delegation, then submits already-staged OIDs. Preserve exact readback while
  replacing manual staging in the normal product interaction.
- `stead-code-store.hoon` supplies bounded graph/object validation, ref policy,
  comparison before update and original Git identities. Proposal-only runs
  must not receive general repository write credentials.

## Owner, worker and run

**Owner** is the accountable human, explicitly assigned or visibly inherited
from the project's human steward. **Working on it** identifies the current
human or agent worker. A **run** is one execution of a task contract with
separate attempts. Submission is reviewable output, not Work completion.

Separate the stable agent principal from its versioned instructions, model/tool
profile and runtime connection. Runtime replacement preserves historical
attribution; a new run does not require another ship. Service credentials are
individually scoped, versioned and revocable. Authentication and final
authorization use the same principal resolver as ordinary members. Display
names and user-supplied actor fields confer no power.

Work, Docs, comments, questions, relationships and Changes are shared business
objects for people and agents. Do not add a parallel AI-task database.
Ordinary permitted comments/progress remain direct actions; default
**Review required** applies to deliverables and protected targets.

## Immutable run contract

Home owns a new versioned job map. Preserve predecessor saved-state shapes
through explicit migration, validation and portable export. The initial
bounded proof profile retains at most 32 jobs per project, three attempts per
job and one live lease per job; these are proposed test limits, not measured
capacity. Initial deterministic leases are at most two minutes and never exceed
membership, grant or job expiry. Model execution needs separately qualified
renewal and a finite maximum duration. T06/T31 must specify retention and
qualify supported limits.

An issued run binds:

- Run/request ID, Home, project, authority epoch and source Work identity.
- Work `execution_contract_revision` and digest of goal, acceptance criteria
  and required outcomes; ordinary `work_revision` is not the execution pin.
- Requester, accountable owner, worker principal/binding, agent-definition
  version, runtime profile, scoped grant and policy version.
- Exact authorized context manifest and digest, output kind and targets.
- Deadline, finite time/cost/tool/network budgets, attempts, fencing token,
  lease, heartbeat and immutable result references.

Targets are typed. Docs bind complete project/collection/document identity,
exact prior revision and expected Markdown outcome. Code additionally binds
an independent repository identity, target ref, exact base OID, source/recipe
digests and fixed staging ref `refs/heads/agent/<run_id>`. Completion evidence
binds an authorized Doc or explicit completion note. Generic runs require no
repository, branch or commit; never invent a Git repo for non-code Work.

Home resolves every context item under current worker access. Linked Docs are
not implicitly readable. Pin exact revisions; show newer context without
silently substituting it. Material required-input changes need explicit
re-planning or a new run. Input/output byte and object bounds cannot be widened
by caller-supplied paths or commands.

T05 separates execution-contract revisions from mutable Work properties and
discussion/activity sequences. Comments, progress and unrelated notifications
must not invalidate an unchanged contract. Changed acceptance criteria do.
T05a now implements an additive read-only execution pin derived from accepted
legacy title/description edits, plus strict agent brief/2 consumption. This is
qualified on the hosted native profile at commit `f254244` (167 arms and 1,647
checks), not a durable-run API. Commands
and comments still use the legacy aggregate revision. The helper checks the pin
before Code submission, leaving a read/submit race; atomic contract fencing,
acceptance criteria, output requirements and independent discussion CAS still
require the versioned migration and T14 final native admission. See
[the exact interface boundary](PRODUCT_NATIVE_INTERFACES.md).

## Lifecycle and effects

The proposed authenticated protocol covers issue/read/list/claim/heartbeat,
wait/answer/resume, cancel and finish. Final route/mark names need a versioned
wire freeze; these are not existing endpoints. Listings and telemetry are
bounded, paginated and permission filtered.

| Transition | Required behavior |
| --- | --- |
| Issue → Queued | Current requester authorizes the exact task under policy/grant/budget. Identical ID and inputs replay; differing inputs conflict. Preserve accountable owner. |
| Claim → Running | Assigned worker compares expected attempt and gets a fencing token. Home commits before execution. Competing claims yield one live attempt. |
| Heartbeat / renewal | Compare exact attempt/token; recheck current authority, contract, grant, budget and maximum deadline. Never revive revoked or expired authority. |
| Running → Waiting for input | Persist a bounded attributable question on Work and an actionable Inbox item. Retain context and attempted effects. |
| Answer → continuation | Continue a clarification wait only while contract, scope and current authority hold. An answer cannot broaden tools or rewrite the issued contract. |
| Expired attempt → replacement | Reconcile receipts/effects first; require current authority and expected expired attempt. Fence old attempts and retain history. Never blindly repeat an external call. |
| Finish → Submitted | Verify exact attempt/token, immutable result, live publication authority, contract/context and target preconditions. Commit result reference, Change and submitted state coherently. |
| Finish → Failed | Retain bounded failure evidence without target acceptance. Different inputs require a new authorized run. |
| Cancel → Canceled | Persist cancellation, stop new claims/effects and fence late publication. Exact retries replay. Previously accepted outcomes remain historical. |

Stop work/Cancel is per run. **Pause new work** stops new project claims;
running work continues unless separately canceled. Clarification continuation
does not promise arbitrary process checkpoint/resume. The supervisor attempts
child termination; the UI distinguishes accepted cancellation from observed
process stop.

An external unprivileged supervisor holds scoped private credentials. The
isolated child receives sealed context/source and bounded tools, not Home
sessions, provider keys, deployment credentials or inherited network access.
Model/provider egress is explicit: a Doc read does not authorize sending it to
an arbitrary service. Retrieved content cannot change policy. Task assignment
alone never authorizes messages, purchases or deployment; these need explicit
effect authority and reconciliation. Deterministic recipes are allowlisted and
do not execute arbitrary repository hooks or commands. Keep the executor
contract provider-neutral and compatible with local models; an external model
provider is optional and never a dependency of ordinary Work/Docs/Code.

Journal run, attempt and input digests before effects; publish output and a
receipt last. On restart reconcile Home and durable local/provider evidence
before another claim or call. Home replay never dispatches a worker. Lost
finish replies retry the same immutable result. Uncertain model/effect outcomes
remain explicit rather than silently repeated. Exact completion retries read
the stored result under current access without reapplying effects; a different
result for the same terminal attempt conflicts. Promise deduplicated accepted
outcomes, not universal exactly-once external computation.

## Change admission, review and durable proposals

A narrow common **Change** envelope retains source Work, original author/worker,
run/attempt, summary, exact before/after references, output digest, checks and
reviews. Keep typed Doc/code targets and existing Git proposal reducers; do not
introduce a universal workflow or transaction engine. Exact Markdown diffs
serve Docs; original OIDs and exact branch comparisons serve Code.

At admission Home rechecks worker binding, grant, lease/token, epoch, contract,
required context and target base. Code uses bounded quarantine/graph checks,
descends from the pinned base and stages only the assigned ref with its exact
expected prior value. It cannot advance a protected target. Docs admission
submits an exact reviewable revision without publishing private collection
contents. Retain staged/uncertain intermediate states durably; partial staging
is neither Submitted nor Accepted.

Execution lease and delegating grant are distinct from durable review. Expiry
stops further worker effects/publication but does not erase an earlier proposal
or require a live worker grant merely to inspect it. Current reader/reviewer
access still applies. Revocation or compromise may quarantine pending output.

T13 implements explicit adoption of an exact expired or quarantined proposal.
Preserve original author/run provenance and digest; require the adopter's
current acceptance authority, current scope/target/base, required checks and
fresh review where required. Adoption never renews credentials, authorizes a
new worker effect or silently accepts compromised output. Baseline delivery
eligibility remains enforced until migration, time-shift and revocation tests
qualify this intentional contract change.

Acceptance is separate from submission and build/release authority. Work is
Done only when declared required outcomes are accepted and required checks
pass; optional links do not block it. An authorized human may explicitly
complete a non-artifact task with a short note. Later T25 low-risk automatic
acceptance requires separate reviewer/acceptance authority and steward-owned
policy. Producers cannot approve themselves or raise budgets, tools, data
access or acceptance scope.

## Incremental acceptance

| Gate | Required executed evidence | Does not establish |
| --- | --- | --- |
| T14 native runs | Competing claims, stale contract/epoch, comment during run, denied context, cancellation, late attempt, migration, export, exact replay and restart. | External execution or model success. |
| T15 deterministic Docs | Real isolated Doc edit submitted through Home; kill before/after output/publication reply; one accepted result, no child credentials, honest cancellation/readback. | Model reasoning, Code readiness or autonomy. |
| T15 parallel Code proof | Original Git commit, scoped staging and exact proposal in a synthetic inline repo; base conflict, denied broad write, separate builder and recovery. | A prerequisite for Docs, full-history Git or arbitrary repository execution. |
| T17 model adapter | Actual synthetic Doc edit with pinned configuration/context, explicit egress, finite tools/cost/time; lease renewal, cancellation and ambiguous-call reconciliation. | General task success or a required cloud dependency. |
| G3/T18 no-Code journey | Create Work, delegate to a named agent, answer a question, request revision, accept exact Markdown and complete Work without a repository. Include comments during execution, changed criteria, next-day review, revoked attempts and restart. | Completion from mocked APIs, copied briefs or operator staging. |
| T24/T25 bounded autonomy | Ordinary child Work, acyclic dependencies, finite concurrency/budget, Pause new work, partial failure/reassignment and separate low-risk review/acceptance authority. | Unbounded scheduling, self-approval or deployment permission. |

Record exact source, profile, actors, inputs, observed outcomes, failures and
unexecuted cases. Independent real-browser/native/model evidence closes the
product journey; a process exit, grant receipt or run card does not. External
Git jobs, full-history Code acceptance, sustained capacity and supported release
retain their separate gates.

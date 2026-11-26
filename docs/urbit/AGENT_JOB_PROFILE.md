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
reconciliation. Independent review
binds ten registered native arms; the lifecycle suite still fails compilation in actual 43846986399. Current authorization and
payload-aware effect gates are mandatory trusted Home adapters, still absent
from live routes. A transition returns candidate ordinary Work/Inbox/Doc intents;
it does not dispatch a process. Restart clears live leases and emits no external
intent. Canonical contracts preserve original grant, exact Doc targets and
normalized target order; result references match the Doc Change vocabulary.
The reserved closed command decoder has six additional independently reviewed,
native arms, now verified by the source-bound sequence/count evidence in actual 43846986399; it validates intent shape and never substitutes for
current Home authority. The native adapter
adds current human-owner/assigned-agent checks, exact shared Doc context and real
Doc submit receipt verification, with eight further native arms verified in that same diagnostic.
This first profile requires an explicit Owner; service actors, provider effects,
settlement and replacement reconciliation stay denied. Versioned history/carrier
integration, actual execution and G3 remain open.

The reserved per-Work run reader
adds eight source-reviewed native arms, also verified in that diagnostic. Current authorized metadata
distinguishes durable phase, observed lease and execution freshness, and exposes
recorded clarification and exact submitted result without credentials or context
bodies. Shared bounded pagination rechecks current access; no public carrier or
supported run API follows from this source alone.

[Actual diagnostic 43846986399](https://github.com/ScottTpirate/stead-urbit/actions/runs/43846986399) builds Home and verifies 39 positive suites/254 registered arms, including Run codec6/adapters8/views8. Nine suites containing 75 arms still fail. Counts rely on exact trusted sequence and closed observations; raw positive-arm transcripts were not exported. Six controls, eleven Doc-child checks and cleanup pass. The fixed diagnostic stops before actual capture or journey; no service dispatch, migration or G3 acceptance follows.

The reserved browser answer/cancel client has independent source review and
fourteen passing host checks.
It preserves exact requests after unknown replies and fences changed sessions.
An accepted answer does not resume execution; accepted cancellation does not
prove process exit. The client supplies no endpoint, authority or dispatch.

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

## Deterministic Doc worker

`scripts/urbit/doc_run_worker.py` consumes exact existing `stead.run-context/1`
bytes and one declared Doc target under a closed local worker envelope. Its
allowlisted append-paragraph recipe preserves the original Markdown bytes,
checks the current input digest and output budget, and produces a private
`proposal.md` plus an `output-ready` receipt written last. The child receives
only sealed inputs and private scratch, without Home/provider/deployment
credentials or inherited networking. An existing output, including a partial
interrupted output, cannot be overwritten by a retry.

Independent source review and eleven host tests
cover input/scope/Unicode bounds, target and byte mismatches, output comparison,
timeout and partial publication. Child calls in those tests are mocked. The
subsequent actual hosted child result is recorded below; native dispatch remains
unimplemented. This local envelope does
not grant authority or constitute a new Home API. Before launch, the admitted
supervisor must verify the current Run claim, lease, source and context, own the
bounded remote process and reconcile retained output on restart. Publication
must atomically bind the exact Doc proposal to the current Run attempt through
Home. The supervisor, Run carrier, native publication and G3 remain required. Keep execution off the laptop and off the authority host.

The prepared hosted proof
uses the existing admitted CI owner and a further unprivileged, sealed namespace.
Its exact-output and publication-boundary kill cases are source-reviewed; ten
host adversarial verifier/custody checks passed with process launches prohibited.
[Hosted run 43783836691](https://github.com/ScottTpirate/stead-urbit/actions/runs/43783836691)
passes all eleven actual isolation/output/publication-fault checks under the
corrected pinned controller. The later native application build probe failed
before any unit arms; that does not erase the separately observed child result.
This proof excludes native publication, an active-child kill and power-loss
durability. Cleanup and all six containment controls passed. No model execution
or G3 acceptance follows from this deterministic proof.

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

The [later native inspection](https://github.com/ScottTpirate/stead-urbit/actions/runs/43791768317) repeats all eleven actual Doc-child checks successfully, then fails the native application build at the recorded Work set traversal. The [corrected-candidate run 43795000844](https://github.com/ScottTpirate/stead-urbit/actions/runs/43795000844) again passes the eleven child checks but stops at the zod build probe after 502 passing checks and one failure. Its closed log records a syntax-error marker and an owner-library mention, without an exact source span or raw trace. Zero of the 329 unit arms ran; saved-state capture and the product/browser journey were not reached. All six containment controls and cleanup passed. Neither result advances model execution, native proposal publication or G3.

## Model and tool connections

The November 15 owner decision requires interchangeable providers and local
models, with several named agents able to use different connections. Keep a
stable agent principal separate from immutable instruction, runtime and model
connection revisions. The target Run contract pins the chosen revisions and exact model;
changing a connection never changes old provenance, grants or budgets.
The current reserved wire stores runtime ID/revision and context digest; an
immutable supervisor allowlist must bind those pins to the selected connection
and model. The operator catalog below resolves those pins during request preparation. Live dispatch remains disabled.

Start with one small compatible HTTP chat/tool adapter and an explicit extension
interface for other provider protocols. A connection declares its endpoint,
model, capabilities, secret reference, permitted egress and finite resource
limits. Unsupported capabilities are visible; there is no silent provider or
model fallback. Native network, token and cost reservation units remain explicit
and bounded for local endpoints too; they are distinct from provider currency
charges. Credentials remain in the trusted supervisor, outside prompts,
ordinary product state, tools and child output. MCP tool connections and model
inference connections are separate boundaries. A model's proposed tool call
still passes the same current native authorization and effect reconciliation as
other agent actions.

A planet can own and select a local model connection without running inference
inside its authority process or on the shared authority host. An isolated worker
or separately admitted local service supplies that endpoint. Reuse governed,
versioned tools and preserve deterministic results that users can also operate
through the UI. This applies the product ideas in
[Toward the self-driving computer](https://graymirror.substack.com/p/toward-the-self-driving-computer);
it does not adopt the article's proposed platform migration or treat its
security claims as qualification evidence.

Connections are disabled until their endpoint, resource limits and secret
reference, when needed, are configured. The pure adapter boundary now exists in `scripts/urbit/model_connections.py`: versioned connection parsing, exact request preparation and bounded untrusted reply/tool proposals. Twelve remote host cases pass; the promotion record preserves exact tested module bytes. The separately versioned `llamacpp.chat-completions/1` extension now also passes its six local-response boundary cases alongside the original twelve in the 18-case host profile. It accepts only declared bounded timing metadata and empty non-thinking metadata, preserves the original raw response digest and retains all proposal/authority checks. No model account, inference service or paid call is active. The fixed loopback transport now has one actual response below; general provider transport, secret resolution, aggregate budget settlement and native dispatch remain pending.
The model-call journal is retained in `scripts/urbit/model_effect_journal.py` with twelve actual remote filesystem cases. It binds exact requests and structurally checked native-intent bytes, preserves original responses, and leaves interrupted or uncertain calls unable to dispatch automatically. Publication-fault tests exercise write/link/unlink/fsync failures; they are not process-kill or power-loss tests. Stored receipts never grant current authority or settle native charges.

The first selected transport trial uses Qwen3-0.6B Q8_0 with llama.cpp b12359 on
the existing disposable hosted worker: one CPU core, 2 GiB memory, no swap,
128 processes and at most ten minutes of execution. Model and runtime downloads
are pinned by revision, size and SHA-256. It uses one public synthetic document,
one loopback request and no paid API calls. The authority host and local laptop
do not run inference. The third and fourth standalone trials each observe one model call, both with failed exact-content checks; see the retained result below. Failed trials must retain bounded original responses when available,
explicit absence when unavailable, and verified cleanup without accepting a
failed proposal.

The failed-response collector now passes 29 remote host cases, including strict original-byte custody, empty versus absent output, caller/worker cleanup and suppression of failed proposals. These use constructed process/service boundaries. The original fixture permission failure is retained with its test-only correction. The [first standalone trial](https://github.com/ScottTpirate/stead-urbit/actions/runs/43815447620) stopped during artifact preparation before the model service started, with verified cleanup and no inference result. The refusal needs a precise diagnostic; native G3 acceptance remains separate.

The model worker failure-preservation and diagnostic boundaries pass 29 and 33 constructed remote host cases. The first two standalone attempts stopped before service start; the second records a download redirect refusal. The exact one-host CDN correction passes eight constructed host cases. The [third actual trial, 43823695825](https://github.com/ScottTpirate/stead-urbit/actions/runs/43823695825), starts the fixed local model and receives one original tool response (234 input and 35 output tokens). It chooses the correct tool but omits the requested final Markdown newline, so the unchanged exact-content gate fails. Original bytes and verified cleanup are retained; no failed proposal is exported, tool executed or document changed. This proves a bounded real inference path, not a successful document proposal, native Run authority or G3. The [fourth trial 43832899126](https://github.com/ScottTpirate/stead-urbit/actions/runs/43832899126) clarifies the exact JSON string and again returns one normalized tool proposal, using 260 input and 35 output tokens, but still omits the terminal LF. The original response and complete cleanup are verified. The strict check, model and limits were unchanged; no further retry is admitted. Never append the missing newline or relabel this failed trial as passed.

The selected source-reviewed profile uses official Qwen2.5-1.5B-Instruct Q4_K_M, revision `91cad51170dc346986eccefdc2dd33a9da36ead9`, with the same llama.cpp runtime and all resource/cost limits. The synthetic connection advances to revision 2. It removes the Qwen3-specific template option and sets temperature 0/seed 42; the exact prompt, free-string tool, original-response handling and 47-byte check are unchanged. Three response-fidelity host cases now pass in the actual 23-case remote batch, distinguishing both original failed replies from constructed byte-preservation examples. The other twenty cases cover worker, collector and outer-adapter boundaries with inert process/namespace/network doubles; all 75 inputs remained unchanged and cleanup passed. The exact controller `cff48cb64e725830ac8f82717303b7567d564722` was published through PR #117, and one trial [43843435452](https://github.com/ScottTpirate/stead-urbit/actions/runs/43843435452) was dispatched from workflow `3b2582855dd98e9cb3d14095041e30d884ecc449`. The [actual original-evidence review](https://github.com/ScottTpirate/stead-urbit/actions/runs/43843435452) passes one response with the exact 47-byte Markdown, including its final LF, and the same normalized untrusted proposal. Observed usage is 258 input plus 31 output tokens; client time is 5,924 ms and outer time 25,067 ms. Source/workflow pins, all five original ZIP members and client/server/whole-unit cleanup are verified. This one case ran within the unchanged limits; peak memory and a reliability rate were not measured. No tool ran, Doc changed or native authority was supplied. Native multi-turn dispatch, clarification, requested revision and acceptance remain required for G3.

The separate fixed native-helper evaluator attempt [43841636361](https://github.com/ScottTpirate/stead-urbit/actions/runs/43841636361) failed with a post-admission collector `ValueError`. The cause and completed evaluation count remain unobserved; no evaluator report was exported, and worker and whole-unit cleanup are verified. The passing host23 evidence does not supply a native result or authorize a retry, and no model or G3 success follows from this attempt. A separate 18-case diagnostic host check passes six closed failure-position/redaction cases and twelve existing collector/outer cases, with exact source custody and cleanup. These constructed checks support the next diagnostic attempt; they do not identify the original cause.

The private model-to-Doc proof source is independently reviewed with five authored native arms, still uncompiled. For `model-doc/1`, it independently normalizes retained response bytes, requires a settled native effect and one approved tool, and compares literal Markdown with the Doc command. The existing atomic Doc/Run pair adds a bounded immutable result link; full chronological replay reconstructs it before serving state is admitted. Original retry returns the prior proposal under current visibility without renewing execution. The turn-command codec now has two source reviews and six authored, uncompiled arms: four exact operation shapes and deterministic child identities, with no authority grant or state mutation. Retained continuation state and the actual clarification/revision journey remain pending; neither slice closes G3.

The first native model path uses an explicit `model-doc/1` runtime profile with a
`single-shared-doc/1` request policy. A profile name grants no authority: current
actor, original grant, lease, Work contract, context, owner connection allowlist
and budget must all agree. The initial single-call profile is not sufficient for
G3 clarification and revision. Normal continuation must get a separately
reviewed bounded multi-turn profile; replacing an attempt to bypass its call
limit is not an acceptable continuation mechanism.

The first real G3 trial still needs actual model output, current Run authority,
clarification, review and exact accepted Markdown. A provider adapter alone
cannot close that gate.

### Choose a model for an agent runtime

The supervisor reads a bounded JSON catalog with two lists. Each connection names a model, its protocol, its endpoint, a credential reference when needed, and its limits. Each binding selects a connection revision for one Home, project, agent definition revision and runtime policy. Several agents can share a connection. A planet-owned agent can point to a model on an isolated local worker. Hosted providers that implement the supported chat-completions protocol use the same interface.

Start with the [two-agent example](../../specs/urbit/fixtures/model-catalog.json). Its addresses, identities and policy digests are examples. To inspect the selected models and their pins, run the following command from the repository root.

```sh
python3 scripts/urbit/model_catalog.py specs/urbit/fixtures/model-catalog.json
```

Keep the operator catalog outside worker-writable storage. Save the selected connection digest with the run. When changing a model, create a new connection revision and runtime binding, and retain the previous revisions for review. The supervisor entry point `EffectJournal.for_run` matches the Home, project, definition, runtime, policy and connection digest before preparing or reopening the exact request. A missing or changed pin fails the request. An empty catalog disables all selections.

This path prepares a request. Before sending it, the supervisor still needs the current native grant, lease, budget and egress decision. A proposed tool call also requires its own authorization. The catalog contains credential references only. Installing an example does not start a model, send data to a provider or enable the pilot's Run controls.

A connection using `stead.model-connection/2` declares
`capabilities.required_tool_choice` as `single-function/1` or `unsupported`.
Give the connection a new revision and select its new digest in the Run scope.
The supervisor can pass `required_tool="propose_doc_replacement"` to
`catalog.prepare` or `EffectJournal.for_run`. The provider then receives
one registered function and `tool_choice: "required"`. This also works with
servers that support required tool use but lack a named-function wire format.

A completed reply must contain exactly one call to the selected function.
Refusal, incomplete output and text-only responses supply no Doc change.
The default remains automatic selection. Existing version-one requests and
journals retain their exact bytes and continue to replay.

### Recover a model proposal for review

The supervisor retains the terminal `result_sha256` for the exact request. After
a restart, reopen the same journal with its original Run scope and pinned model
connection. Call `journal.read_proposal(result_sha256)` to recover the verified
text or proposed tool arguments. A document tool's `markdown` argument retains
its exact UTF-8 content, including the final newline. Check the pinned tool ID,
revision, target document and base revision before submitting it for review.

A refusal, a truncated or filtered reply, a changed receipt, or an interrupted
publication supplies no actionable proposal. Reading the journal performs no
provider call, tool execution or Home mutation. Native submission and
independent acceptance still need current authorization.

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

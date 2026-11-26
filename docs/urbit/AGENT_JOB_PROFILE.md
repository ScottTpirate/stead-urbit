# Proposed Work agent jobs

**Status: unimplemented proposal.** This document specifies the next bounded
increment; it is not a supported API, executed test report, or claim of agent
autonomy. Start with synthetic data and inline Code. External Git, model-driven
execution and batch control require their own acceptance below.

The [master directive](MASTER_BUILD_DIRECTIVE.md#10-agent-and-ci-boundaries)
requires durable Work, source, proposal, checks and review links, recoverable
effects, and separate acceptance/release authority. A proposal grant alone
does not dispatch or execute a task.

## Reuse and separation

- `stead-code-delivery.hoon` already checks current delegation, membership,
  proposal and review authority. Its build transitions provide lease,
  expected-attempt, cancellation and exact-replay patterns.
- `stead-code-build-home.hoon` already exposes authenticated build
  queue/read/claim/finish/cancel/release operations and verifies artifact
  bytes. These follow an existing proposal and require an independent
  builder. Do not repurpose them as pre-proposal agent jobs.
- `code_build_worker.py` provides pinned inputs/Git, isolated namespaces,
  bounded resources/output and receipt-last publication. Its only current
  recipe inventories an existing commit; it does not edit source or call a
  model. Reuse the isolation design with a separate job/result protocol.
- `agent_proposal.py` verifies a private worker session, current Work and
  delegation, then submits already-staged OIDs. Reuse those checks and exact
  proposal readback; replace the manual staging handoff with job admission.
- `stead-code-store.hoon` supplies bounded object/graph validation, ref policy,
  comparison before update and original Git identities. Existing Git
  credentials are repository read/write, not job/ref scoped. A proposal-only
  worker must not receive a general write credential.

## Proposed single-job contract

Home owns a new versioned job map. Preserve predecessor saved-state shapes;
add migration, validation and portable export instead of silently extending
an existing saved mold. Initial limits: 32 jobs per project, three retained
attempts per job, one live lease per job. Capacity fails explicitly.

An immutable issued job binds `job_id`, Home/project/repository/authority epoch,
requester and worker principal bindings, `delegation_id`, Work ID and revision,
context digest, target ref and exact base OID, source digest, recipe digest,
expiry, and staging ref `refs/heads/agent/<job_id>`. Home resolves source and
context through current authorization. Linked Docs are pinned to exact
revisions and included only when the worker can read them. Input context and
results have explicit byte/object limits; caller-provided paths or commands
cannot widen the recipe.

Proposed authenticated operations are `agent-job-issue`, `agent-job-get`,
`agent-job-claim`, `agent-job-cancel`, and `agent-job-finish`. These names are
not implemented routes. Listing is bounded and reveals only authorized jobs.

| Transition | Required behavior |
| --- | --- |
| Issue → `queued` | Maintainer authorizes the exact task under a live delegation; identical job ID and inputs replay, differing inputs conflict. Human assignment stays unchanged. |
| Claim → `running` | Only the assigned worker may claim with `expected_attempt`; compare at Home, increment once and persist before execution. Initial synthetic lease is at most two minutes and never exceeds membership/delegation/job expiry. |
| Expired claim → new attempt | Current authority and pinned inputs must still hold; only the expected expired attempt can be replaced, up to three attempts. Preserve prior attempts. |
| Finish → `submitted` | Verify exact attempt, result, live authority and source/context preconditions; admit the staging branch and exact proposal, then retain their IDs, OIDs, checks and receipt. |
| Finish → `failed` | Store bounded failure evidence without a proposal or target-ref change. Failure is terminal; a new authorized job is required to try different inputs. |
| Cancel → `cancelled` | Authorized requester cancels an unfinished job; repeated cancellation replays. A completed proposal remains historical and does not become merged or released. |

Expired/revoked authority or changed Work/context/base prevents publication.
Readback must explain the blocked condition without presenting a live run as
accepted. A fresh scope needs a new job, not an in-place rewrite. An exact
completion retry reads the stored outcome under current access without
reapplying effects. A different result for the same terminal attempt conflicts.

## Execution and result admission

An external unprivileged supervisor polls Home and holds the worker's own
private session. The isolated child receives only sealed job/context/source;
no Home session, general Git write credential, authority files, deployment
keys or inherited network access. The initial allowlisted recipe makes a
deterministic README edit in a synthetic repository and records bounded
checks. It never executes arbitrary repository hooks or commands.

The supervisor journals job, attempt and input digests before execution and
publishes output plus a receipt last. On restart it reconciles Home and any
complete local result before considering another claim. Home replay never
starts a worker. A lost reply retries the same immutable result; it does not
automatically repeat a model call or other external effect.

Add job-scoped result admission, not a broad write token. At final admission
Home rechecks worker binding, current delegation, lease/attempt, epoch, Work
context and target base. Reuse bounded Git quarantine/graph checks; require
the generated commit to descend from the pinned base and allow only the
job's fixed staging ref with its exact expected prior value. Preserve original
Git OIDs. The protected target cannot advance through this operation.

The staging-ref receipt, exact proposal under the worker's identity, and
`submitted` job outcome must commit together. If transport requires staging,
retain a durable intermediate record and reconcile it; never expose a partial
result as completed. Revocation/cancellation prevents final publication.
Supervisor polling should stop local work, but does not promise instantaneous
remote process termination. Recipe checks remain worker evidence, not an
independent accepted build.

Existing exact review and separately authorized build/release transitions
follow the proposal. Show queued/running/blocked/failed/cancelled/submitted
outcomes, attempt history, exact proposal and checks on Work. Only Home
readback may establish a shared outcome.

## Incremental acceptance

| Gate | Required executed evidence | Does not establish |
| --- | --- | --- |
| Deterministic synthetic task | One Work job produces a real isolated edit and original Git commit, staged through job-scoped admission, then an exact reviewable proposal. Verify separate builder admission; competing claims; stale Work/base; cancellation/revocation; attempt expiry; lost completion reply; restart before/after publication; export/readback; and absence of credentials in the child. Include native authorization and real browser-to-Home execution, not only mocked browser responses. | Model reasoning, arbitrary repository execution, external Git readiness or batch scheduling. |
| Model-driven task | A separately reviewed, pinned executor adapter performs an actual model-driven task on synthetic source. Record model/configuration, authorized context, input/output and checks; bound cost, duration, retries and tool/network effects. Keep provider credentials outside repository execution. Prove cancellation, restart and ambiguous external-effect recovery without silently repeating calls. Use separately specified finite lease renewal/maximum duration; the two-minute synthetic profile is not sufficient evidence. | General task success, safe execution of arbitrary code, external Git or batch operation. |
| Bounded batch control | Explicit batch membership, per-job scope and finite concurrency/cost/time budgets; durable enqueue and pause/cancel controls; per-job outcomes; predictable partial failure. Prove restart without duplicate dispatch, starvation bounds and cancellation while jobs are queued/running. Every child still passes single-job authorization and exact proposal admission. | Unbounded autonomous scheduling, production capacity or deployment authorization. |

External Git additionally needs this job authority connected to accepted
snapshots, scoped result ingestion, build acceptance and release authority.
Any retained local passing evidence must name exact source/payload hashes,
executed scope and exclusions. No gate closes merely because its UI exists.

### Choose a model for an agent runtime

The supervisor reads a bounded JSON catalog with two lists. Each connection names a model, its protocol, its endpoint, a credential reference when needed, and its limits. Each binding selects a connection revision for one Home, project, agent definition revision and runtime policy. Several agents can share a connection. A planet-owned agent can point to a model on an isolated local worker. Hosted providers that implement the supported chat-completions protocol use the same interface.

Start with the [two-agent example](../../specs/urbit/fixtures/model-catalog.json). Its addresses, identities and policy digests are examples. To inspect the selected models and their pins, run the following command from the repository root.

```sh
python3 scripts/urbit/model_catalog.py specs/urbit/fixtures/model-catalog.json
```

Keep the operator catalog outside worker-writable storage. Save the selected connection digest with the run. When changing a model, create a new connection revision and runtime binding, and retain the previous revisions for review. The supervisor entry point `EffectJournal.for_run` matches the Home, project, definition, runtime, policy and connection digest before preparing or reopening the exact request. A missing or changed pin fails the request. An empty catalog disables all selections.

This path prepares a request. Before sending it, the supervisor still needs the current native grant, lease, budget and egress decision. A proposed tool call also requires its own authorization. The catalog contains credential references only. Installing an example does not start a model, send data to a provider or enable the pilot's Run controls.

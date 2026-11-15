# Stead Urbit — master implementation directive

Version 0.2 • November 15, 2026 • Current architecture and adopted product requirements. Implementation, qualification and release support remain separate claims.

This directive governs architecture. The [experience contract](PRODUCT_EXPERIENCE_CONTRACT.md) fixes the product interactions; the [execution plan](../../specs/urbit/product-execution-plan.yaml) maps follow-up packages to existing URB parents. The [capability matrix](CAPABILITY_MATRIX.md) records what is implemented, qualified on a named profile and supported. The [alignment record](PRODUCT_ALIGNMENT_20261115.md) reconciles the review baseline and document changes. Adoption does not close a functional gate, replace M0–M6, or reinterpret historical evidence as a new test run.

## 1. Mission and preserved requirements

Stead is where a team defines an outcome, gathers context, assigns a worker, reviews the result and accepts the work. Build that coherent Work + Docs experience on the existing Urbit-native foundation, with optional software delivery. Preserve the small canonical ontology, one coherent UI, open exports, domain-neutral security profiles, explicit authorization, narrow agent delegation, and the separation of organizational hierarchy from access grants. Improve the product; do not restart the core or add disconnected capabilities in place of complete journeys.

This derivative deliberately replaces the original deployment/engine locks. It does not waive security, data integrity, or portability requirements. The source baseline and all original implementation material are retained in `reference/stead/` and Git history. No old Phase 0 approval constitutes approval of this new design.

The initial product is native-authoritative: Hoon application state/logic and native Git semantics, with a conventional browser and Linux runtime host. External build execution and documented bulk storage are permitted infrastructure boundaries. Running Gitea behind a Hoon proxy is not completion of native Git; invoking an LLM externally is not native model inference. Do not conflate those claims.

### Product and domain decisions

- A project works with zero repositories and can own multiple repositories. Repository identity is independent of project identity; start with one owning project per repository and an explicit association. Preserve existing IDs, refs and historical links in a versioned migration.
- One canonical Work item appears from project, repository, supporting document and personal queues. External issue integrations map foreign IDs to that resource; they do not create an internal tracker/forge split. Native workflow state and structured exports remain appropriate for Work, permissions, discussion and runs; not every record belongs in a Git file.
- Resource references include project, kind, collection where applicable and local ID. Exact Doc revisions and repository/commit/path references differ from moving latest/branch references. Backlinks derive from the same relation, and each endpoint is independently authorized. Protected names, snippets, counts and existence must not leak through relations or aggregate views.
- Owner is the accountable human, Working on it is the human or agent worker, and Run is one execution with attempts. Authorized autonomous work may visibly inherit its project's human steward. Agent principal, versioned instructions/runtime binding and run attempt are distinct; a run needs no new planet.
- Work target statuses are Backlog, To do, In progress, In review, Done and Canceled. Blocking is a reasoned condition on unfinished work. Preserve legacy blocked state and history through explicit migration; do not relabel it ready. Work is Done only when declared required outcomes are accepted and required checks pass, or an authorized human explicitly completes a non-artifact task with a note. Optional informational links do not block completion; one merged change cannot complete a task requiring several changes.
- Separate mutable `work_revision`, `execution_contract_revision`, and discussion/activity sequences. A run pins its objective, acceptance/output contract and exact authorized input revisions. Comments/progress do not invalidate an unchanged contract; material contract/input changes require explicit re-planning. Newly available context does not rewrite what a run read. Revocation and role changes remain live checks.
- Change is a narrow common metadata/lifecycle envelope with typed Doc/code targets, exact before/after references, Work, producer/run provenance, checks and review. Reuse Git reducers and specialized editors/diffs. Do not introduce a universal transaction engine or parallel AI task database.

These decisions define the implementation target. Current wire formats and saved-state behavior remain those of the implemented profile until a versioned migration is reviewed and executed; prose alone cannot safely change native semantics.

### Product surface

Workspace navigation is Inbox, My work and Search, initially aggregated within the selected Home. Project navigation is Overview, Work, Docs and optional Code. Overview explains the goal, next milestone and exceptions; relationships are contextual, not a primary Links destination. Each Work, Doc, repository, Change, review and run has a shareable address, with navigation preserving filters, selection and drafts. Sensitive content does not belong in URLs.

Create Work requires only a title, defaulting to current project, Task, To do, No priority and Unassigned. Never silently assign the creator. Autonomous admission requires an explicit owner or visible steward inheritance. Work detail presents purpose, acceptance, worker/progress, outputs, supporting context and discussion. Use named people/agents, meaningful outcomes and actionable states; raw IDs, epochs and receipts belong in Details.

Preserve the established React/tooling and governed rendering boundary while extracting coherent product surfaces. Real screens must cover loading, empty, no results, read-only, dirty draft, saving, accepted, disconnected/stale, outcome unknown, conflict, revoked, retryable error and unsupported operation. Retain subscriptions, stale-response guards, focus reconciliation and draft continuity. Only native acceptance permits Saved; unknown outcomes reconcile the same request. The experience contract supplies the layout, control and copy defaults.

## 2. Hosting model: federated project homes

Each project has exactly one authoritative home in the first implementation. A company can place many projects on one organization-controlled ship. Separate sensitive domains or materially different trust boundaries require separate deployments; do not create a ship per page, repository, employee, or team merely to imitate an organizational chart.

A project ID is independent of the serving ship and URL. A versioned, authorized directory record identifies the current home and authority epoch. Initial discovery uses explicit invitations/bookmarks; there is no mandatory global Stead directory or public project index. Private project existence and relations are protected information.

Distinguish:

- Principal: person, organization, agent or service, with stable application identity and authentication bindings.
- Home: the authority that accepts mutations for a project under current policy.
- Host machine: the VPS/on-prem computer running one or more isolated ship processes.
- Replica: an explicitly authorized copy of a selected project's accepted state, initially read-only.
- Backup: a recovery artifact, not an independently active ship or necessarily a queryable replica.
- Client cache: bounded authorized views; never presumed complete or authoritative.

Urbit ranks are not organizational roles, storage tiers, CPU allocations, or ACL inheritance. A planet is sufficient as an organization service identity. Members can authenticate using ships with unrelated sponsors. A moon is controlled by its parent and is appropriate for a service/distribution/testing identity, not an independent employee identity by default. No star or galaxy purchase is needed.

One physical VPS can run several ships. Each needs separate state, identity and process/service controls. Sharing a physical administrator is still a shared trust boundary; separate containers do not protect data from that administrator.

## 3. Where data resides

The home holds authoritative work items, document history, membership/policy state, Git objects and refs, and accepted activity. Clients receive only requested authorized resources and bounded authorized subscriptions. A new page does not copy a project to everyone. A push does not automatically clone code onto every member's laptop or ship.

A developer's ordinary Git checkout intentionally contains the repositories they clone, subject to shallow/partial-clone choices. That is separate from replicating the whole Stead organization. An optional organizational backup/replica is a deliberate additional copy, not a default personal cache.

Large attachments/build artifacts/LFS must not be silently jammed into the home agent's live state. Define content-addressed manifests, digest verification, limits, retention and a replaceable storage boundary. Begin with small synthetic text repositories and no mandatory object store. An external storage profile must be labeled as such; it is not a fully self-contained Hoon storage implementation.

## 4. Separate identity verification from content delivery

The organization host's +code and Dojo access are administrative credentials, never employee login mechanisms. Urbit's default ship-owner web authentication is not our multi-user application authorization model.

Early native testing uses distinct fake-ship principals. For a live native cohort, design and audit an identity handshake: home issues an unpredictable, expiring, one-use challenge bound to the browser session, home identity/origin, requested principal and protocol version; the user's identity ship explicitly approves through an authenticated native exchange; the home binds that approval to a Stead-only session. Entering a ship name alone proves nothing.

Requests and page bodies then travel directly from the browser to the project home over HTTPS. The personal ship acts as an identity endpoint, not a content proxy. This avoids writing private page bodies into a personal ship's persistent input/event history. It does not stop a recipient copying anything they are allowed to see, nor eliminate local browser exposure. Notification titles, challenge messages and relations must also avoid unnecessary disclosure.

Use separate origins and host-scoped secure cookies; validate Origin/CSRF, nonce/session binding, replays, expiration, logout and revocation. Validate that raw Eyre channels, scries, debug routes and other installed apps cannot bypass Stead. Do not assume proposed Eyre isolation work is deployed. Only audited/trusted applications on authority ships until independently proven isolation supports broader use.

Later add a browser-only organizational identity binding (for example a reviewed OIDC/passkey integration) so ordinary employees need not operate a ship. The integration cannot be faked by letting all users act as the organization ship. Preserve individual application principals and record how they authenticated. This is a later access profile, not a day-one dependency or a claim of implemented native WebAuthn/OIDC support.

## 5. Authorization and identity continuity

Every protected read/mutation, search result, notification, attachment operation, native message, Git operation, export, and replication request is checked at the authoritative boundary. Transport authentication determines a sender; it does not grant a business permission.

Authorization is the intersection of membership/relationship grants, information-flow policy, session/delegation scope, action/resource scope and current runtime/context requirements. Explicit denies win. Missing, contradictory, expired or unsupported evidence fails closed. Team parenthood and ship sponsorship confer no grants.

Starter roles are reader, contributor, maintainer and organization administrator, expressed as tested permissions rather than a global bypass. No role automatically overrides handling restrictions. Agent authority is narrower than the delegator's and may be limited by project, task, allowed operations and expiry. Distinguish proposing a patch from merging it and approving a release.

Bindings record historical networking-key life/rift and application-key delegation information where relevant. Ship control changes or identity recovery must not silently transfer employment access. Current key lookup alone is not historical verification. Record authentication strength; do not misrepresent a host-recorded author as an independently signed human action.

For asynchronous Git ingestion, membership and protection are re-evaluated when accepting the ref update, not only when upload begins. Reject expired/revoked credentials at that decision point. Native/direct Git routes may not bypass this check.

## 6. One transaction owner and explicit mutation semantics

Initially use one mutation-owning Gall agent (`stead-home`) with modular Hoon libraries. It owns policy and the small authoritative pointers/state transitions for Work, Docs and Git refs. This is a modular monolith, not one agent per field or table. Heavy tasks can be staged across bounded events; staging confers no acceptance.

For each command preserve a unique request ID, protocol version, principal/session or delegation, project ID, expected resource revision, authority epoch and bounded payload. Derive authenticated principals from trusted transport/session context, never from a caller-supplied author field. Use a documented serialization and digest/signature profile before relying on cryptographic portability.

Separate statuses: queued/local draft, received, accepted at home, replicated to selected replica, rejected. A network ACK is not a successful merge/save. Durable acceptance returns the resulting revision/ref and receipt. Requests can be retried idempotently; duplicate content under the same request ID cannot create new mutations. Reuse of an ID with a different payload is rejected. Rechecking access on a retry must not disclose a formerly authorized response after revocation.

All accepted changes append to a purpose-built application journal; the runtime log is not the permanent portable audit format. Search, notification views and indexes are derived and rebuildable. Bounded jobs resume after crashes. Stale inputs cause explicit conflicts, not silent overwrite. Notification failure does not uncommit accepted work.

## 7. Creating and editing a document

Reading rendered Markdown is the normal entry point. Edit opens a focused, accessible Markdown-aware editor with formatting controls, accurate Preview and Source; no mandatory raw textarea or permanent split pane. Support the documented CommonMark/GFM subset without raw HTML/MDX execution. Keep title metadata/fallback and unsupported metadata round trips explicit. Draft recovery is scoped to principal/session/resource and follows logout/revocation policy; it does not imply cross-device drafts.

A document belongs to an explicit project/container. Private drafts remain private until publication. Saving carries an expected document revision. The home verifies edit rights and policy, normalizes/validates portable Markdown and frontmatter, creates the Git-backed revision, advances the authoritative document pointer and records the accepted event. Only then does the UI say Saved.

Markdown/frontmatter bytes and their Git commit are canonical content; any parsed native view/index is derived. Do not maintain two independent writable document masters. Keep ordinary Git exports recoverable. Stage Git changes and document metadata so no crash yields a saved receipt for an absent revision.

A document container is distinct from a project's optional software repositories. A repository README may appear in Docs only as a view of that canonical repository file, with writes through its origin. Explicit publication controls private drafts; sharing a page must not publish its entire collection. New commits must accurately attribute the accepted author/actor under the declared identity profile without rewriting historical commits.

Two people editing the same revision either use a tested merge algorithm or receive a clear conflict. Start with revision checks, not a homegrown CRDT. Do not create a Git commit for every keystroke; save meaningful accepted revisions. Realtime typing/co-editing can be added behind the same canonical-save model later.

A cloneable repository/document container is an access boundary. Per-page UI restrictions cannot protect files exposed through an unrestricted clone. Separate containers by compatible access/handling, or disallow whole-container cloning where it would expose unauthorized content.

Other members receive a minimal authorized update notice and fetch content as needed. Direct-message content enters shared knowledge only by explicit permission-checked publication of a selected fragment or summary; no automatic bulk copying by AI.

## 8. Pushing code

Normal Git clients use Smart HTTP to the organization home. Each principal/device/agent obtains its own scoped read/write credential, with revocation and no credentials in clone URLs/logs. Preserve original commit objects and IDs; Git author text is not proof of the pusher's identity.

Ingest into bounded quarantine; verify pkt-lines, pack checksum, expansion limits, objects/deltas, graph reachability, ref preconditions, credentials and branch policy. At the authority decision, compare expected old ref, check the current policy/epoch, and atomically admit objects plus refs and an acceptance record. Return success only after that outcome is durable. Failed/malformed uploads do not advance refs or expose quarantined/unreachable objects.

Existing Urgit is the native Git feasibility/dependency candidate, not a preapproved production backend. Resolve its reuse license first. Independently test ordinary Git interoperability and current limitations. Reuse licensed libraries or collaborate upstream on an authoritative-policy integration. A UI proxy over independently writable Urgit routes is unacceptable. If the engine must remain a separate agent, an ADR and failure tests must define the inter-agent transaction/fencing protocol before production integration.

Start with versioned, explicit Git support: canonical SHA-1 repositories, clone/fetch/push, tags, concurrent-ref protection and branch policy. Evaluate SHA-256, LFS, partial/shallow clone, symlinks/submodules and ecosystem integrations as separate conformance items. Unsupported features fail clearly. An independent SHA-256 attestation can bind the exact content without rewriting legacy Git IDs. A Git-to-Clay projection is optional and more restrictive than storing arbitrary Git objects.

Expose one Code product over declared inline/external storage capabilities: repositories, branches, files at revision, comparisons, pull requests, checks, builds and releases. Storage proofs belong in operations/Details; unavailable operations receive an explicit product explanation. GitHub remains Stead's source until the exact chosen profile passes full-history writes, concurrent updates, review, independent checks/builds and representative restore/rollback rehearsal, followed by explicit owner cutover authorization. Do not create dual writable masters.

## 9. Federation, availability and recovery

Decentralize operation between project homes, not the ordering of every shared edit. Any organization can run a home; native peers can interact through reviewed explicit protocols. A project can move home while retaining its ID and history. A member can participate in projects on different homes without those homes receiving each other's private data.

The first version is a single writer with backups. If the home is down, no shared mutation is final; local drafts/commits remain possible and authorized cached data is explicitly stale. An unsaved or queued action cannot be shown as accepted. RPO/RTO are measured goals, not implications of persistence.

Do not run duplicate live copies of a ship identity. Development uses fake/disposable identities, not a production pier copied online. Backups are encrypted and restored first with networking disabled. Validate log/revision consistency and lost-write windows. An older pier rollback may require runtime-specific network-continuity handling; a cold copy is not automatically a safe live rollback.

For same-identity host migration, quiesce writes, stop/fence the old process, transfer a consistent pier, verify, and start exactly one replacement. For later cross-identity project migration, transfer an authorized snapshot plus journal, verify content, fence the old home, advance a signed authority-epoch record and reject stale writes. Abrupt failover requires a separately designed fencing/recovery authority: a signed directory entry alone cannot stop a disconnected old host accepting work.

Replicas are selected by project and permitted custody boundary. A clone of source code is not a complete organizational backup. No active-active acceptance or automatic election until a justified, tested consensus/finality design is approved. No Ethereum transaction is necessary for ordinary work. Optional public checkpoint anchoring is deferred and requires privacy review.

## 10. Agent and CI boundaries

Model calls, compilers and test runners are external effects with recorded inputs/results where useful. Never execute arbitrary repository code on the authority ship/host. Build results are attestations under an explicit trust model, not proof of correctness.

Give separate workers project/task-limited authority. Untrusted PR jobs have no live keys, organization sessions or deployment credentials. Replaying state must not repeat builds, messages, purchases, LLM requests or deployments. Stage an explicit authorized effect after recorded state decisions and handle retries idempotently.

Design complete, repeatable workflows with visible outcomes and recovery. The first product agent journey is a document update in a project without Code: named worker, real dispatch, pinned context, clarification in Work discussion, exact Markdown proposal, requested revision, independent acceptance and Work completion. A permission grant/copied brief, synthetic card, successful process exit or internal deterministic Code recipe does not establish this journey. Extend it into software work linking Work, Docs, branch, exact reviewed change, independent checks and accepted build. An agent uses the same authorized business operations as a person. Preserve all proposal, review, Work, Docs and Git history through supported updates and exports.

Native Home owns jobs; an isolated external supervisor executes authorized effects. Run states are Queued, Running, Waiting for input, Submitted, Failed and Canceled, separate from Work status. Pin Work contract/context, agent definition, project/Home epoch, grant, output targets, policy version, budget and deadline. Claims use compare-and-set, leased attempts and fencing tokens. Reconcile lost replies/results before retrying; native replay cannot repeat model/tool effects automatically. Deduplicate accepted outcomes without promising universally exactly-once external computation. Per-run cancellation fences new effects and late publication, does not roll back accepted outcomes, and is not confirmation that a remote process has terminated. Project Pause new work stops new claims; arbitrary process pause/resume is not promised.

Separate execution lease/grant expiry from durable proposal review. Expiry stops worker effects/publication under that authority but does not erase proposals or require a worker grant for an independently authorized reviewer to inspect them. Revoked or compromised output can be quarantined. Explicit adoption of an exact expired/quarantined proposal preserves its original immutable producer/run provenance and digest, rechecks current scope/target/base, required reviews/checks and acceptance authority, and obtains new review where required. It neither renews worker authority nor silently accepts compromised output. This target intentionally changes current eligibility behavior and requires a versioned contract and negative tests.

Review required is the default for submitted deliverables and protected targets, not every authorized comment/progress update or ordinary direct edit. Acceptance and release authority remain separate from proposal creation. After the review loop works, a steward may authorize narrowly bounded low-risk automatic acceptance with separate required reviewer/acceptance actors. The producer cannot approve its own output or expand tools, access, budgets or policy. Enforce project concurrency, time/cost limits, acyclic dependencies and escalation of repeated failures. Sending messages, purchases, deployments and other external effects require their own explicit authority; a task assignment does not confer it.

Agent configuration belongs beside people in Members & agents: stable principal, steward, explicit access, versioned runtime/capability binding and connection test. Keep provider keys in the supervisor's secret boundary. Read permission is not permission for arbitrary model-provider egress. Agent execution is optional, with a provider-neutral boundary for local/configured external models; ordinary Work, Docs and Code must not require a hosted model account or proprietary control plane.

Design agent and CI access around exact revisions and bounded object, path and history queries that do not require a full working copy. Keep Git identities and portable clones. Use explicit, versioned transitions for uploads, proposals, reviews, builds and releases, with distinct authorization and recoverable outcomes. The [revision-addressed source control profile](CODE_AGENT_SOURCE_CONTROL.md) records the design and its relationship to Anthropic’s Scion work.

No native-inference or native-every-compiler requirement blocks the work/document/Git milestone. Such research remains a separately budgeted track.

House work is limited to a capped investigation and narrow shell, identity, notification and capability/version adapters against verified source/license/API/install contracts. Preserve explicit native grants. Record unresolved interfaces and keep unsupported integration disabled; desk packaging alone is not House compatibility. This work must not block standalone delivery or authorize a speculative `%gnat` rewrite.

## 11. Acceptance boundaries

The following initial slices remain historical gate definitions, not instructions to restart completed foundation work. Consult the capability matrix and exact acceptance records for current evidence. T01–T32 add follow-up scope without replacing URB-000 through URB-280 or M0–M6. A documented requirement, closed parent or synthetic demo does not accept that new scope.

Development: four fake ships (home, contributor, reader, outsider), public/synthetic data only, deterministic fixtures and independent browser contexts.

First native slice: create project; explicitly grant access; save/edit a page and work item; deny unauthorized reads/writes; prove duplicate handling and stale revision behavior; restart and recover; export the result without the app.

Git slice: stock-client round trip with fsck; preserve OIDs; final authorization after concurrent revocation; reject malformed packs; one of two conflicting CAS ref updates wins; prove no alternate endpoint bypass.

Live canary: limited identified test cohort; isolated administrative access; pinned release/runtime; tested rollback/recovery; public/synthetic data only. Real company data remains blocked until auth/session/endpoint isolation and backup threat models pass independent review.

Performance targets are goals, not measured claims: after receipts are implemented, select representative small/medium repositories and work corpora, record p50/p95 save/read latency during imports, memory/loom growth, event backlog, recovery time and storage growth. Freeze actual thresholds from an initial baseline rather than inventing enterprise capacity.

The five current product gates are G1 ordinary no-Code team work, G2 human software work, G3 agent Docs work, G4 agent software work and G5 failure/recovery; their observable steps are in the experience contract. The first real agent product acceptance is G3/T18. Bounded Docs automation may follow that gate independently; Code automation waits for the forge gates. Qualify storage growth early, retaining deduplication, audit and revocation history. The proposed 1,000 Work/500 Docs/100,000 events/10-run corpus is an experiment target, not supported capacity.

For visible slices, inspect real desktop/narrow, empty/normal/crowded, long-text, keyboard, accessible-label, zoom and read-only behavior. Native authority changes need relevant stale/replay/revoked/migration/recovery cases on the actual harness. Real agent acceptance includes dispatch, clarification, cancel/revoke, next-day review and no duplicate accepted result. Preserve failed/unexecuted cases and exact source/profile bindings. Independent unfamiliar-user completion (initial target four of five without coaching) is measured separately from technical tests.

Beta support additionally requires independent clean install, browser/member onboarding, real Work/Docs/software/model-driven journeys, loss-aware import/export, upgrade and restore, and URB-270/280 governance. Imports stage before activation, retain source IDs/author/time provenance and loss reports, and resume idempotently. The release manifest binds runtime, desk, frontend, API and saved-state compatibility. Recovery must retain one active authority and fence stale workers. House compatibility and source cutover remain separate decisions.

## 12. What is deferred

Full Gitea/Jira/Confluence parity, an arbitrary workflow engine, global discovery, per-user full replicas, active-active project homes, token economics, blockchain writes per action, native LLM inference, arbitrary native language toolchains, untrusted on-ship extensions, and classified/regulated deployment claims. Air-gapped and domain-neutral policy remain design requirements but need dedicated qualification before being advertised as supported.

# Phase 1 trust boundaries and test obligations

September 13, 2026. Minimum design/test inventory for [#24](https://github.com/ScottTpirate/stead-urbit/issues/24),
using the original directive and [contract amendment 2](CONTRACT_AMENDMENT_2.md).
This does not qualify any unexecuted route or security profile. Existing issues
remain the execution/status authority; the qualification manifest is a required
test inventory, not another backlog.

| Boundary | Authority and disclosure rule | Required evidence / owning issue |
|---|---|---|
| Native commands and watches | Gall sender maps to a current application binding; context, grant, action, container and epoch precede receipt lookup. Explicit denial wins. | Four-fake sender/context/revocation/retry/CAS corpus; #7/#8. V2 unexecuted. |
| Result subscriptions | Request path binds sender, binding, project, request and digest. Result facts use that bound reservation path; protected reads use the current duct. Pending16/sender,64/total,60s lazy expiry; an expired same-path registration is retired with ACK/kick and no business fact. | Actual observer facts/kicks, wrong sender, quotas, leave, expired same-path registration, late/missing/unavailable outcome; #8/#9. |
| Private resource allocation | Work IDs are project-scoped; document IDs include the container; grant IDs include the project. Project allocation currently belongs to explicit single-org administration metadata scope. | Old native oracle reproduction and v2 scoped creation; a second organization needs scoped project allocation before activation; #6/#7/#8. |
| Receipts, journal and derived views | Closed public receipt2 exposes no cross-container journal sequence/digest/policy counter. Full internal audit remains privileged. Revalidation also precedes recovery/export. | Before/after private activity, retry/recovery/manifest vectors; #7/#8. |
| Exhaustion | Ordinary work cannot consume project-local revoke reserve. At exhausted reserve/policy counter, that project's protected access closes. No erased history or general admin bypass. |4096 legitimate v1 transitions, two project reserves, full-boundary atomic refusal, corrupted predecessor rejection; #7/#8. |
| Git document bytes and Clay | Container is the access boundary. Manifest authorization is rechecked for each exact retained object. Clay/Dojo/conn are privileged administration, not member APIs. | Stock Git fsck/OID/file recovery, cross-container snapshot/object denial; #7/#8. Native Smart HTTP/pack quarantine later #11/#23. |
| Fixture administration | Fixed fake bindings, legacy builder and context corruption controls are isolated test helpers. Snapshots contain protected synthetic state. | Owner-only negative controls; no deployment/provisioning claim; #4/#7. Remove or isolate helpers before #21 deployable API. |
| HTTP/Eyre and individual sessions | A request reaching the home does not become the home administrator. Server authentication must establish principal/session context. Distinct origins, secure host cookies, CSRF/Origin, one-use session-bound challenge and authenticated native approval are required. | #9/#10/#21. No HTTP/session implementation or pinned-runtime browser isolation proof yet. Deny activation until raw Eyre/native/admin/debug bypass tests pass. |
| Personal identity ship and browser | In the later direct-browser profile, the identity helper receives necessary challenge material, never page bodies by default. Current synthetic native document/export clients do receive bodies through fake ships and their runtime history. Later browsers get directly authorized home content and bounded caches. | Fake-native approval protocol and separate-browser A/B/outsider journey, logout/revocation/cache checks and privacy canaries; #9/#10/#29. No live identity qualification. |
| Host, backup and support access | Physical administrator and reviewed installed apps remain in plaintext custody. Diagnostic/admin snapshots are private; no untrusted authority-ship apps. Backup keys live outside host/Git. | Endpoint allowlist, redacted support bundle, encrypted off-host recovery, restored revocation and fenced single identity; #13/#15/#16/#24. Warm restart is not crash restore. |
| Distribution and publisher | Publisher and employment policy are separate logical roles, but malicious approved code can change authorization or exfiltrate on-ship plaintext. Publisher compromise is inside the data trust boundary. Pin and deliberately review/promote source/desk/UI/runtime. | Reproducible artifact, rollback/forward-fix/upgrade and mixed-version tests; #25/#26. No release or OTA qualification here. |
| Objects, links, webhooks and workers | Imports/expansion/graph/object quotas fail atomically. No repository code, external URL fetch, model call or untrusted job on authority host. No worker credentials inherited from PR content. | Malicious pack/Markdown, SSRF/webhook destinations, retention/GC and isolated worker tests; #11/#23/#28. Current Git constructors do not depend on Urgit. |
| External bulk/object storage | No external object store exists in this slice. A later adapter must have explicit custody, authenticated authorization for every operation, content manifests/digest verification, size/retention/deletion limits and consistent backup. Its operator is an additional trust boundary. | Replaceable storage and export/restore tests; #13/#23/#24. Pending/object bounds are not a per-principal request-rate or bandwidth limiter; those controls remain unimplemented. |
| Effects and replay | No external-effect subsystem exists in the current core. Later effects need authorized durable intent, captured inputs/results and idempotent dispatch outside replay. | Current narrow source/N-A disposition; later interrupted/replayed build/message/model/release tests under #12/#13/#28. |

## Identity continuity and incident handling

The pinned kernel's `pkg/arvo/sys/vane/gall.hoon` lines 3025–3042 expose the
owner-local `%v`/`on-save` path independently of an application's `on-peek`.
Therefore an absent member scry is not installed-app or administrator isolation.
Reviewed trusted applications and the ship/host administrator remain plaintext
custodians. The browser/Eyre isolation profile still requires its own execution
evidence before activation.

Application principal, organization principal, ship control, publisher and project
authority are separate identities/capabilities. Sponsorship and team position
create no grant. Current fake bindings record synthetic authentication strength;
they establish neither a human signature nor historical network-key ownership.
Live enrollment must record relevant key life/rift and delegation evidence.
Selling/recovering/rotating a ship must suspend or explicitly rebind employment
access, not inherit it from a new key lookup. #9/#19/#24 own native and later
browser-only binding scenarios. The current implementation does not advertise
those lifecycle flows.

Offboarding must revoke membership, sessions, device/agent credentials and pending
delegations at the accepting boundary. Revocation cannot retract data already
received, exported, backed up or copied. A restored snapshot cannot silently revive
an old grant, session or authority epoch. Authority fencing and lost-write windows
belong to actual recovery tests, not a signed directory entry alone.

Agent permissions to ask, propose and authorize stay separate and narrower than
the delegator's. An Urbit Gall component is not an AI principal. No current fixture
flag authorizes arbitrary delegated agents. Context/profile failures remain closed;
future profiles must add tested evidence requirements rather than privileged names.

On a suspected disclosure or compromised publisher/host: stop new authorization,
fence the affected authority, preserve bounded private evidence, revoke/rebind
credentials, and review affected accepted history and recipients. Do not publish
confidential logs or exploit details into public channels. Verify an actual private
reporting route under #30 before advertising one. Recovery must use a reviewed
forward fix or verified restoration; never start two live copies of an identity.

The executable v2 manifest retains all 25 historical skipped assertions and maps
them to current typed evidence obligations. Required missing native evidence fails
the current gate. Constant-time execution, hostile co-resident apps, complete
disaster recovery and live/browser identity are not inferred from local source
review, host checks or a fake-ship demonstration.

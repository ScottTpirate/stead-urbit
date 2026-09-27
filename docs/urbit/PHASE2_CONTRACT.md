# Phase 2 implementation contract

This defines the supported single-organization Work/Docs alpha. It is a design
under review until the corresponding native, HTTP, browser and CI evidence is
executed. It does not close M2 or authorize production identities/data.

## Authority and compatibility

`stead-home` remains the only mutation owner. Existing Git objects, Work/Docs
records, grants, accepted journal and receipts stay in its authoritative state.
New libraries add session, configured-team and projection behavior; neither a
web process nor an identity helper owns business data. The existing synthetic
v2 profile and its corpus remain available for regression. Configuring a team
disables the private fixture/control routes and their fixed principal profile.
Public native and browser commands use the same team authorization function.

The organization operator configures one home/origin, organization/team IDs,
explicit person bindings and narrowly assigned project-creation authority.
Initial configuration is an owner-local operation accepted only on an empty,
uninitialized home. It rejects nonempty v1/v2 fixtures; converting historical
fixture IDs or reassigning their data is unsupported. At most 32 bindings (one
per principal and ship) and eight explicit project creators are permitted.
The local profile bounds ship identifiers to 128 bits, keeping retained actor
metadata within its separate decoding limits.
Binding/origin updates require the expected configuration revision. Binding
revisions increase monotonically; at most 128 distinct principals may enter the
non-resetting binding-revision history (32 may be configured concurrently).
At most 256 binding IDs are retained with their immutable principal owner; an ID
cannot be recycled to another person after removal.
Removing a binding retains its high-water revision, and capacity rejects an
update atomically; rebinding invalidates that principal's
sessions, challenges, cursors and watches. Origin changes invalidate all
ephemeral credentials. Accepted records retain their original attribution.
Member routes cannot update configuration.
Names are display fields; immutable IDs and verified native senders establish
identity. Sponsorship grants nothing. Organization administration is not a
content-read permission. Project creation records an explicit creator grant.

The configured-team saved envelope is version 3. Load versions 1 and 2 through
their existing converters into an unconfigured legacy profile, preserving their
exact content, Git identities, history and revocations. Team configuration and
canonical metadata persist; the upgrade envelope omits browser sessions and
pending login approvals. A cold Vere restart retains full Gall cores and
therefore requires an external ingress fence: no browser/TLS traffic is forwarded
until an owner-local bootstrap atomically clears all sessions, pending approvals,
cursors and watches, creates a fresh incarnation, and returns a correlated
acknowledgement. The fence owns the child lifetime, closes existing streams before
restart and on unexpected exit, and cannot reopen from a reused PID or stale ACK.
The public ports stay in the private namespace; Lens/Khan are never bridged.
Actual upgrade `on-load` separately clears ephemeral state. `/zen/ver.non` alone
is insufficient: pinned Vere derives it from a 31-bit time hash that may repeat.
Unknown or malformed state fails closed. Old fixture execution continues to save its version-2 shape.

Configured-state validation is consistency reconstruction, not independent proof
of historical identity approval. Each internal journal entry retains the exact
nonsecret authentication context, binding and credential expirations, and the
live target binding for a grant. These details never appear in employee activity
or public receipts. A private validator checks retained binding ownership and
revision history, reconstructs each unique accepted command with the unchanged
business authorization/revision/object checks, and compares the complete state.
Historical membership, project-creation admission and browser approval remain
assertions of that retained journal. Current membership may legitimately differ;
equal binding revisions must still describe identical identities. Validation
advances at most 16 accepted events per step. Aggregate noun admission is bounded
before semantic traversals; individual maps, record sizes, object bytes and
nested histories retain their business limits. No reconstructed registry serves
requests. Failed or unfinished validation exposes no restored business state.
An upgrade restarts validation from its target and never trusts a saved
validation status. Continuations must bind to the current job and all business
and configuration mutations remain quarantined until the final atomic commit.

| Profile | Commands | Reads and results | Saved state |
| --- | --- | --- | --- |
| Legacy fixture | command/2; command/1 only for authorized existing receipt recovery | existing v2 scoped routes, receipt/2 and owner-local fixture controls | save 2, load 1 or 2 |
| Configured team | command/3; /1 and /2 return unsupported_version | query/3, updates/3, receipt/3 and capabilities; all fixture/v1/v2 routes denied | save/load 3 |
| Empty installation | owner-local configure only | no business reads | 2 until configured |

SDK v2 continues to support legacy homes; it must report unsupported_version
against a configured home. No silent translation of authority/container
semantics. A v3 SDK is a new package with independent vectors. Historical
receipts are read projections, never reexecuted commands.

The final home authorization context contains principal ID, binding ID/revision,
verified ship, authentication method/strength, nonsecret session audit ID (empty
for native calls), home, organization/team scope and expiration. Native calls
resolve it from Gall's sender and the current binding; browser calls resolve it
from a validated session and the same binding. No request supplies an actor or
administrator flag. Configured records use actual `native-sender/1` or
`native-approved-browser/1` attribution and explicitly record `isolated-fake`
for local tests. Never create fake-native receipts and rewrite them afterward.
All reads, mutations and receipt recovery also resolve current grants, epoch,
scope and expected revisions at the home.

## Individual authentication

The home creates an unpredictable 256-bit challenge and a separate browser
binding from Gall entropy, domain-separated by purpose and a monotonic counter.
The pending browser receives a Secure/HttpOnly/SameSite=Strict host-only cookie.
The native challenge contains only challenge ID, home, exact allowed HTTPS
origin, requested identity/principal binding, protocol, purpose and expiration.
No page/work content or browser bearer credential enters the identity ship.

The person's `stead-identity` helper displays the home/origin and comparison
code. It requires an explicit approval by that identity ship's authenticated
owner, then sends the approval to the home through Gall. The home verifies the
actual native sender and every challenge field, current binding and expiration.
The helper cannot choose an employee identity for the home. The organization
ship's owner cookie or `+code` never establishes a member session.

Only the browser holding the matching pending cookie can consume the approved
challenge, once. Consumption rotates to a separate random Stead session cookie
and CSRF value and invalidates previous credentials for that browser binding.
Neither actor text nor an approved challenge ID alone is a credential. Challenges
expire after two minutes; sessions expire after thirty minutes. Bound pending
challenges and sessions globally and per principal; expiration is checked on
every use. Logout removes the session. Binding revision, active/expiry evidence,
current grants, authority epoch and resource scope are checked again for every
command, read, receipt recovery and update delivery. Key/recovery changes require
explicit binding revision/revocation; fake-network evidence is not a live key
continuity or independent-custody claim.

Expiration uses the home's native event clock in milliseconds, never a client
clock. Approval binds the binding ID/revision and exact protocol, purpose, home,
origin, principal and expiry shown by the helper. Consumption verifies and
removes the challenge and creates the session atomically. Failed consumption
cannot rotate a valid session. Starting a new login with a live session cookie requires an explicit, confirmed
logout first. The unauthenticated start endpoint cannot invalidate a current
session. The pure replacement transition remains reserved for a future
authenticated switch flow. Logout removes the session and
challenges tied to its browser binding, cancels queued deliveries and kicks its
watches. Expiration, rebinding, origin changes and restart also cancel delivery.

Hard maxima: 32 challenges/four per principal; 64 sessions/four per principal;
64 watches/four per session or native binding; 32 headers/8 KiB total;
64 KiB request body; 256-byte origin; 64-byte lowercase-hex challenge, bearer,
CSRF and cursor tokens; 512-byte URL. Reject excess before decoding. Reject
duplicate Host, Origin, Content-Type, CSRF or Cookie headers, duplicate recognized
cookie names, malformed cookies and all Forwarded or X-Forwarded-* headers.
Unknown cookies confer nothing; never select among conflicting credentials.
Cookies are `__Host-stead-pending` and `__Host-stead-session`, Secure, HttpOnly,
SameSite=Strict, Path=/, no Domain. Clear both with matching attributes at logout.
The CSRF token is returned no-store and kept only in memory. Pending status
requires the pending cookie and exact Origin; challenge ID alone grants nothing.

## HTTP and browser boundary

The supported transport terminates TLS in pinned Vere/Eyre at the home and
separate identity ships. Configure an actual certificate/key through Eyre's
owner-local cert task. The app requires the secure inbound flag and exact
configured Host/Origin and rejects all forwarding headers before trusting the
flag: pinned Eyre otherwise interprets Forwarded from loopback. No reverse proxy
may assert transport security. A local harness bridge may forward raw TCP/TLS
bytes only to enumerated public secure ports inside its private namespace.
Never bridge the separate loopback Lens port, Khan socket or arbitrary ports.
Use distinct home/identity hostnames: ports alone do not isolate cookies.
Trust local certificates only in a disposable browser profile, with TLS checks
and the browser sandbox enabled.

Home HTTP allowlist: GET /stead/ and named immutable assets; POST
/stead/auth/start, /stead/auth/status, /stead/auth/consume, /stead/auth/logout,
/stead/auth/resume,
/stead/api/capabilities, /stead/api/command, /stead/api/query and
/stead/api/updates. Unknown method/path combinations are denied. Only
start/status/consume use pending authentication; only start and capabilities
are unauthenticated and neither discloses business metadata. No raw path becomes
a native watch/scry. Identity approval has its own owner-authenticated UI and
bounded POST. Stead cookies must fail on actual public TLS Eyre channel, scry,
login/admin and Lens routes. Callerless home scries, unknown native marks/watches
and configured fixture/control routes fail closed. Trusted owner-installed
applications remain part of the authority-host trust boundary; member cookies
never become owner cookies.

`POST /stead/auth/resume` is the explicit exception for a reloaded browser that
has its HttpOnly session cookie but has lost the in-memory CSRF value. It requires
the same native TLS, exact Host/Origin, no-forwarding and bounded JSON checks.
Resolve the current binding and existing session; rotate only CSRF using fresh
Gall entropy and counter separation. Preserve bearer, audit ID, browser binding
and original expiration. Return the new CSRF token only, no-store and without
CORS. Failure changes nothing. Other tabs must refresh their CSRF after rotation;
a stale CSRF never causes automatic mutation replay. The authenticated identity
view is a separate protected query after resumption.

Protected API calls use same-origin JSON POSTs with the session cookie and CSRF
header. Validate exact configured HTTPS origin; no wildcard CORS, credentialed
cross-origin access or bearer tokens in URLs/local storage. Serve application
responses with no-store, restrictive CSP, frame denial and nosniff. Personal
identity approval uses its own separately authenticated origin. Test actual
pinned Eyre channels, scries, Lens/admin paths and direct native requests;
trusted installed applications remain part of the authority-host trust boundary.

UI state is partitioned by home and session, cleared on logout/identity changes
and authorization failure. Keep unsaved text in memory and preserve it on
conflict or failed saves. A transport ACK or timeout is never Saved. Display
pending/unavailable distinctly and reconcile retries using the original request
ID. Do not automatically replay mutations after reconnect. Render Markdown as
safe React elements without HTML execution or remote resources.

## Commands, views and publication

Public version 2 retains its declared legacy-profile compatibility. Version 3
adds configured project/container creation, document publication/deletion, typed
relations and bounded queries/updates. Capabilities declare supported versions,
operations and limits; unknown versions fail explicitly. Request/receipt IDs,
expected revisions and authority epochs remain mandatory for mutation.

A newly created draft container is private to its owner. A maintainer can
explicitly create a shared project container; current project grants then govern
that container. Publication names the full source project/container/document,
expected source revision/head, full destination project/container/new document
identity, expected destination revision zero and expected destination head.
It requires source ownership and current contributor permission, plus current
contributor permission in the explicitly shared destination. Both must have the
same project, home and custody domain. Administration bypasses neither gate.
Both CAS checks, authorization, Git objects, state, journal and receipt commit
atomically; failure changes none. The commit's only parent is the destination's
previous head. Its tree includes current destination entries and the selected
page, never source trees/parents, other drafts or private source provenance.
Canonical front matter changes only the source ID to the explicitly supplied
destination ID and `state: draft` to `state: published`; body bytes are preserved.
Public receipts/activity contain only destination identity/commit. The original
remains private and unchanged. Test an unselected private page canary in all
destination reads, history and stock Git exports. Creating a shared container
never publishes existing drafts.
Editing shared content still requires contributor permission. Container-wide
Git reads use exactly the same confidentiality boundary.

Typed relations name full scoped endpoints (kind/project/container/resource).
`blocks` connects work to work; `documents` connects a page to work;
`related_to` permits either resource kind. Both endpoints must be visible at
acceptance and query time. Resource deletion
is an accepted tombstone, invalidating reads, projections and subscriptions;
retained historical Git objects remain accessible only through authorized
container-history exports. Deletion removes current views, not historical bytes:
an authorized collaborator may already have cloned them. The new current tree
omits the page; older commits preserve their OIDs. Physical erasure/retention
policy is outside this alpha, and the UI must say so.

Search, relations, activity and inbox are bounded projections of accepted
records, with ordered checkpoints and idempotent replay. Rebuild work advances
in bounded batches and stores progress. Duplicate events are no-ops; a gap or
invalid event stops projection advancement with a content-free diagnostic.
Authorize every result before disclosing titles, snippets, counts or edges.
Never expose the internal security journal as employee activity.

Query cursors bind version, principal/binding, scope, filter, policy and a scoped
view generation (a domain-separated SHA-256 fingerprint of relevant membership
and scope counters). Reject stale or altered cursors; private mutations in unrelated
scopes do not change a member-visible cursor/count. Updates contain minimal
authorized invalidation metadata, never private bodies. Recheck current access
before each emission. Cancelled/revoked/expired watches cease delivery. Resume
is bounded and either replays the allowed retained window or requires a refresh.

Limits: 16 projects, 128 work items/project, 32 containers/project,
32 documents/container, 128 revisions/container, 256 relations/project,
4,096 total ordinary accepted events plus 128 security events/project and 8 MiB Git
objects. Existing stricter envelope/text limits remain. A projection batch
processes at most 16 events; persisted checkpoints record predecessor digest
and replay position. Duplicates cannot advance counters. Gap/poison stops before
publishing partial views with a content-free diagnostic. Recovery rebuilds a
separate view from the accepted journal and swaps only after full validation;
never skip an invalid event. While rebuilding, queries report unavailable.

Work list/search rows contain bounded previews; a work query with a resource ID
returns exactly that authorized item for editing. Project policy CAS revisions
appear only for current maintainers, with corresponding view invalidation.

Queries return at most 20 rows in stable scoped resource-ID order; activity and
inbox use scope-local accepted order, never a global sequence. Search is literal
Unicode matching, at most 128 query bytes, not executable regular expressions.
Reauthorize before titles, counts, snippets, edges or cursor disclosure; never
return cross-project totals. Opaque random cursors are server-held records
(64 global/four per actor, five-minute lifetime) binding principal/binding
revision, session audit ID or native sender, scope, filter, last position, view
generation and epoch. No unsigned cursor state is trusted. Only changes visible
in that scope advance its generation; unrelated private mutations do not affect
shared cursors/counts. Access generations are principal/project/container scoped.
Altered, stale, expired or rebound cursors require refresh.

Each scope retains 64 minimal invalidations; each watch queues at most 16.
Overflow emits refresh_required and closes the watch. Reauthorize at dequeue,
including session expiry, binding, grants and scope. Revocation/expiry discards
queued rows before delivery. Resume uses the same bound opaque cursor store.
Cancellation is idempotent and removes queue/watch. Restart invalidates all
cursors/watches; clients explicitly refresh without replaying mutations.

## Verification and release boundary

The independent SDK consumer compiles only from the package and declared pinned
runtime dependencies, with private fixtures unavailable. Execute golden vectors,
malformed/oversized/unknown-version inputs, allow/deny, replay/idempotency,
conflicts, cancellation, revocation, stale cursor and reordered-update controls.

Freeze the detailed native/browser expected-case inventory before qualification.
Run the actual two-user/outsider browser journey, keyboard/focus/accessibility,
Unicode/time-zone, responsive/empty/error/offline, XSS and cache-separation cases.
Measure useful-content timing and eager/lazy bytes on the real native path.
An independent nonauthor participant receives only the quickstart/task, without
maintainer coaching; record participant type, failures and time. An automated
participant is not described as a human usability study.

Native CI runs on disposable isolated workers with synthetic fixtures, explicit
resource admission, pinned actions/tools and no production secrets or persistent
writable cache shared with PR code. Its positive job and deliberate failure,
missing-arm, compiler/timeout/corrupt-output/cache-poisoning and cleanup controls
must actually execute. The workstation thermal guardian is unchanged. A hosted
worker profile needs its own reviewed admission evidence; absent host facilities
are not replaced by fake sensors or an environment-variable bypass.

Separate contributor, user, operator and integrator quickstarts. Support exports
require consent and contain only bounded diagnostic codes/versions/correlation
IDs by default, excluding cookies, keys, messages and content. Local fake ships
qualify the local protocol/browser profile; live network custody, public hosting,
production TLS deployment and confidential data remain separate later gates.

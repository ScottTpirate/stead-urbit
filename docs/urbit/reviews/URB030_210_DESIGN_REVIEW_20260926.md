# Phase 1 contract and threat-map design review

Reviewed 2026-09-26 by `/root/gall_schedule_review`, independently of the
implementation owner `/root`. Review checkout:
`29d1be87fc3e9ef3857a76c2190a20a85babc7c5`; exact reviewed bytes are bound below.
Read the live acceptance bodies using `gh issue view 6` and `gh issue view 24`,
both with explicit `--repo ScottTpirate/stead-urbit`. Both issues were open.

**Disposition: no remaining blocker for the bounded URB-030 contract-freeze or
URB-210 Phase 1 design/test-inventory acceptance.** This supports design closure
of [#6](https://github.com/ScottTpirate/stead-urbit/issues/6) and
[#24](https://github.com/ScottTpirate/stead-urbit/issues/24) as their acceptance
bodies define it. It does not qualify Phase 1 native implementation, browser
isolation, live identity, Git transport, release or deployment. No issue, PR,
runtime, script or frozen specification was changed by this review.

## Contract coverage and retained tests

The original contract preserves Organization/Team/Project/Work/Document and
typed relation requirements through its explicit canonical-domain/OWGP
references. Acting User/Agent/Service Principal is distinct from ship control;
Work and Docs are universal and software capabilities optional. Stable IDs do
not include a serving host, sponsor or URL. The explicit v2 amendment makes
work/document/grant identity a complete typed scoped tuple; consumers must not
silently apply the historical bare-UUID global-identity rule to those resources.
A second organization remains blocked on scoped project allocation. Future
interchange/relations consumers must preserve those full scopes.

The closed command envelope binds version, request/resource/project identity,
expected revision, epoch, operation and payload. Trusted transport supplies the
principal/delegation context separately; caller-authored actor/decision fields
are forbidden. Current authorization precedes duplicate-result disclosure.
One home owns the atomic state, receipt and journal decision; external effects
need durable authorized intent and a later separate executor. Transport ACK,
proposal/local draft and committed acceptance remain distinct. Five evidenced
policy dimensions, explicit grants and opaque denials exclude sponsorship,
hierarchy or generic administrator bypasses.

I independently recomputed all nine original and five amendment file hashes:
zero mismatches. The retained September 13 `contracts-check-final.log` records
18 original host-reference tests and four amendment tests passing, including
closed schema/versions, duplicate keys, canonical bytes, ID/revision/epoch
bounds, policy evidence, escalation/role limits and unchanged freezes. Their
frozen source/test files remain byte-identical today. These are historical
codec/reference results, not new native execution. This audit reran no tests;
current native stale-state, retry, scoped privacy, migration and delivery
acceptance remains with #7/#8 and the exact qualification manifest.

## Pinned userspace and browser authority

The inspected kernel is the lock's `408k-2`, commit
`5a187fededc4582a34fcd6055c67bb63e0917b94`. I hashed the cached archive against
the lock and compared both inspected local files byte-for-byte to its members.
This is local source provenance, not a signed upstream build attestation or a
browser experiment.

| Pinned source observation | Design consequence |
|---|---|
| Eyre lines 761–776 give local Lens requests `%ours`. Lines 834 and 1584–1602 define owner-authenticated requests from a current `%ours` session. Lines 1619–1627 distinguish local `%ours`, eauth `%real`, and guest `%fake` identities. | Owner administration, a remote ship identity and an individual Stead employee session are different authorities. A boolean `authenticated` cannot supply the missing employee policy context. |
| Eyre `request-to-app`, lines 1284–1309, forwards HTTP requests into Gall. `deal-as`, lines 3382–3387, maps `%ours` to `our` and uses `/eyre` provenance. Channel handling also derives `from=our` for `%ours` at lines 2602–2603. | Reaching Gall as the home ship does not establish a narrower employee identity. Later APIs must establish and check their own principal/session/scope at final acceptance, including raw Eyre/channel/native bypass cases. |
| Eyre's cookie constructor, lines 1723–1732, uses a ship session cookie with `Path=/`; CORS state is handled at lines 881–910 and response handling. | Neither that owner-cookie path nor a CORS decision demonstrates per-application browser-origin or employee isolation. Final serving/proxy/browser behavior was not tested here. |
| Gall lines 3025–3042 allow the current owner-local `%v` scry (`our` ship, `[~ ~]` permissions) to export the live agent's saved state through `on-save`, independently of its member `on-peek`. | An absent member scry is not installed-app or administrator confinement. Ship/host operators and reviewed installed applications remain plaintext custodians. |

These observations reinforce the existing threat map's trusted-app restriction:
no untrusted authority-ship application marketplace or extension execution.
The direct-browser profile still requires distinct origins, individual bounded
sessions, CSRF/Origin checks, session-bound one-use challenges, authenticated
approval and final policy checks. No source inference above is a demonstrated
browser attack or an isolation/security qualification.

## Owning tests and remaining activation boundaries

The threat map covers native commands/watches/scries; HTTP/Eyre and browser
caches; Git/Clay and fixture/admin surfaces; publisher-controlled updates;
host/backup/support custody; objects, external storage and model/build workers.
It separates organization/project authority, human/application principals,
ship control and publisher power. Key life/rift/ownership changes, offboarding,
delegation expiry, stale caches, restored revocation and single-live-identity
fencing remain explicit obligations. Disclosure cannot be revoked from prior
recipient copies, event logs, exports or backups. Publisher code and physical
operators are inside the plaintext trust boundary.

The map assigns browser/origin/session tests to #9/#10/#21/#29; hostile Git and
storage/import boundaries to #11/#23; effect/model/build isolation to #12/#28;
backup/restoration and custody to #13/#15/#16; update/mixed-version/release tests
to #25/#26; and a verified private incident-reporting route to #30. Request-rate
controls, live identity continuity, browser isolation and complete recovery are
explicitly unimplemented or unqualified. Closing the design issues does not
waive those tests, authorize confidential data or activate those routes.

## Exact source and evidence bindings

| Input | SHA-256 |
|---|---|
| `specs/urbit/contract-freeze.json` — 9 files checked | `61d9a18f16b8b01629bd35177d5b801cc05cd8ddaf7f68c3cc1678faf642cf90` |
| `specs/urbit/v2/contract-freeze.json` — 5 files checked | `a2336e5060c71c7c16849b3151cc024a598d6cdf867561452eff1338e3232670` |
| `docs/urbit/CONTRACTS.md` | `f43c64e71c4356a62be0e7f9e4f42de569d9916311f883aa44196388a0a5cb2e` |
| `docs/urbit/CONTRACT_AMENDMENT_2.md` | `f9793a947b4ba69e9099ec0cd68ed004602cb0ffe6fbbf79f9f464cb256315c6` |
| `docs/urbit/PHASE1_THREAT_TEST_MAP.md` | `dd955052c968b18dc594d274ea43a365ba00c3b450d5f6dff90fbd3c8b982654` |
| `docs/urbit/NATIVE_CORE_REVIEW_V2.md` | `44a5cf4ced42140c10192fe9c3125bbcd2f849f703a446c2487675318719b8fa` |
| `specs/urbit/toolchain.lock.json` | `4a209c10cf1756eb0f7357cc3eca8250bf66c239b4cd0ca31a8c0886d4d304ee` |
| `.runtime/downloads/urbit-408k-2.tar.gz` | `7f6f41388f456d1e94850a51b60b15e3148ede103ebb03b8acad470ed27beb31` |
| Pinned `pkg/arvo/sys/vane/eyre.hoon` | `34353e2ddfd226a2603f49904ea159053757df0de2099edd459c0ebd3d54e906` |
| Pinned `pkg/arvo/sys/vane/gall.hoon` | `31c4d615cbc32544a2b954de83e6c381346ec45f48b210fce7a1fab7a939ec4c` |
| `docs/urbit/evidence/2026-09-13/qualification/contracts-check-final.log` | `cc2ade95d08f045d46c59a12c6f8ba08f2fc9dbf3dc0c25876ca68269bb1530f` |
| `specs/urbit/v2/qualification-gate.json` — unchanged runtime obligations | `f374349cc3ccd64993e3dade9a44e306854479c228b7f93d6559647006aee94c` |

Origin was checked as the experimental `ScottTpirate/stead-urbit` repository
before writing this review; original Stead upstream's push URL was disabled.

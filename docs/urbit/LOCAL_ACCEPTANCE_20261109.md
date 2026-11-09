# November 9 local acceptance and recovery

This record distinguishes independently reviewed rendered UI, the actual
configured native team fixture, Git protocol tests, and release recovery.
The [Phase 2 acceptance inventory](PHASE2_ACCEPTANCE.md) now uses independent
Astra review of the local native journey. The October human trial is retained
as historical evidence.

## Rendered UI review

An independent GPT-6 Astra reviewer exercised 27 cases in guarded headless
Firefox against mocked Home responses. It inspected desktop and narrow
screenshots, keyboard focus, read-only Work details, document editor actions,
conflict and recovery, and the warm monochrome layout. Astra found that the
signed-in ship disappeared on narrow screens. The fix at
`15b74a3e639fcb9ff8b8cf5452b4d645507fdee6` keeps the ship alongside signout.
The independently repeated 320, 390 and 1440 pixel checks passed. Both browser
scopes were reaped. These results establish rendered behavior with the tested
inputs. The real browser acceptance has its own native evidence requirement.

The private reviewed reports are
`.runtime/astra-review-20261109T112014Z/fresh-rendered/report.json`
(SHA-256 `6028549b5cc54af0a18dcdd3a5434105248311227afedce99a5d7485dc0595ba`)
and `.runtime/astra-mobile-20261109T112500Z/rendered/report.json`
(SHA-256 `d52929fe2aac12ced252b320df799afc97be3c74c368cf8974cf8d7ad33e0f4a`).

## Interrupted native attempts

| Attempt | Result | Preserved evidence |
| --- | --- | --- |
| `15b74a3` | 220 passed observations; all 71 positive pure unit arms. Launcher received SIGTERM and the supervisor latched a normal stop before the deliberate failure control. | `.piers/fakes/logs/team-check-20261109T112544Z.json` SHA-256 `bf6b3b443b50a3724e3df6a73b875bb224c0576591a1efda71a831a5710988cc` |
| `2e0d86a` | 926 distinct passed observations; 108 exact installed files per ship, the 71 unit arms and failure control, owner setup, access denials, accepted Work readback, duplicate idempotency and stale revision. The guard stopped on sample freshness at 786.288 s. Highest observed CPU temperature was 81°C. | `.piers/fakes/logs/team-check-20261109T113519Z.json` SHA-256 `849e760a8712aff2a7a2c54dcf3623a2afa93a0d3678606b054d10ddf6fb61ce` |

Astra independently reviewed both attempts. Cold restarts, the current
real-browser journey and the receipt-bound Docs Git histories were unreached
in these attempts. The first wrapper's misleading exit file is retained with
its failing native and Make logs. The second wrapper exited nonzero and
verified cleanup. The final retry used an independent supervised process
whose monitor may run off the native core, with the same 50% native quota,
75°C admission, 90°C stop, and 3-second freshness limit.

## Configured native pass

The retry at `bf1c09aeef7f79e36429eb8189c200b8c8a15b78` passed all 1,024
observations in 1,022.392 seconds, with 110 exact installed files per ship and
equal before/after inputs. It exercised individual and outsider access, update
and replay controls, and all four cold restarts with accepted-state readback.
The passing native report is `.piers/fakes/logs/team-check-20261109T115316Z.json`
with SHA-256 `a19b61d1fd78d2e42d488bf87d1948ea9709dbad9c16596c2bfc6afc72cfc696`.

Astra independently decoded 110 native JSON responses. Twenty-five accepted
receipt observations represented 22 unique receipts, with exact equality on
retries and restart and matching document OIDs in native export probes.

## Interrupted native browser journey

The first real Firefox run passed 21 cases, including both individual
sign-ins, keyboard approval, reader details, accepted Work and Docs saves,
two-member live readback, private Search and projection boundaries, exact
shared Markdown reopen, and a two-principal stale save with explicit rebase.
Astra inspected the actual Work and Docs screens. In the deliberate
response-loss case the save was accepted, the retry after another tab's CSRF
rotation was denied, and the next resume response was authenticated and then
discarded. The screenshot preserved the draft and pending receipt controls.
The runner failed on an obsolete literal message expectation for that stage.
The updated test checks the recovery alert and pending draft, then retains the
original no-replay and exact receipt checks. The failed browser was reaped and
the fixture stopped cleanly. The private report is
`.runtime/browser-native-20261109T121019Z/browser-report.json` SHA-256
`ecc37bfcdeb34180b38656f901c19bb9ed60b4fb70babdd0f46750cf5317fb18`.

## Corrected real browser journey

The clean retry at `0aa32ae` repeated all 1,024 configured native checks and
the four cold restarts in 1,034.325 seconds. The actual native TLS Firefox
journey passed all 34 cases. It exercised bare and tilde-prefixed ship sign-in,
keyboard controls, Work and Docs saves and readbacks, Search and Activity,
individual grants, read-only Work details, loss and conflict recovery, offline
drafts, revocation, account change and signout. It captured Work, Docs and
320/390/1440-pixel layouts. Stock Git checked the receipt-bound source,
published and edited histories independently, with 43 successful commands.

Independent GPT-6 Astra disposition: **accept the local Work/Docs workflow**.
Astra checked the exact case inventory, native prerequisite, source hashes,
accepted and reopened records, the native TLS and Git evidence, and the five
actual screenshots. The signed-in ship remained visible at every width. The
review found clear saved, private, shared and reader states and no blocking UX
finding. The public URB-260 tracker and full release gates are separate.

| Bound evidence | SHA-256 |
| --- | --- |
| `.piers/fakes/logs/team-check-20261109T121757Z.json` | `8571bb1be9a4685a61951112a227fe9ac8931da59daf0d48fabe6444ae01c9f4` |
| `.runtime/browser-native-20261109T123512Z/browser-report.json` | `7b66e5c8f55f4114672254752a9767562895afc87b1b09151bdadecf1da63771` |
| `.runtime/browser-native-20261109T123512Z/transport-report.json` | `004acb910e1c29b0fd2b420091c53b52a56be341ad7a0d557e0b71716a0c36a6` |
| `.piers/fakes/logs/team-git-20261109T123512Z.json` | `5484f8980d09133c6778339b4d1e12904512960a554449e2ce108e8821189a09` |
| `.runtime/execution-runs/four-fakes-fd6w5jxd/report.json` | `c51d68e5f633c2770523df4c2c3632e6fb336a0539c31494db7159a534f14a2e` |

The source pins matched before and after. The browser was reaped, its private
profile removed, and the native lifetime finished in 1,501.981 seconds with
no ships left running. The 502 captured responses retain five request failure
observations. Two channel cancellations and one offline command have explicit
test context. Query and update aborts lack firm initiating-stage attribution.
Eleven save confirmations ranged from 2.569 to 6.098 seconds, and the first
Markdown preview took 6.043 seconds in this constrained fixture. These are
observations under the local guard and do not qualify production latency.
The natural session-expiry follow-up was prepared and remains unexecuted at
this source. Prior expiry evidence retains its historical scope.

The separate portable recovery observation used a current individual member
session, verified native HTTPS, and the existing capture/verify/extract CLI.
It recovered two Work items and three documents, including the exact saved
Unicode Work title and description and canonical private/shared Markdown from
the browser fixture. The local archive SHA-256 is
`12bb079ec1fcf440ebc1a0f7dc92f8c591aa315d1c37be4ae515d176369ece9b`.
The test removed its temporary portable-export credential file. This verifies
currently readable export and file extraction. Authority, history and access
grants have separate recovery requirements.

## Git and release evidence

- The pinned pure Git runner passed **290** checks, including 20 repository
  credential cases and their deliberate failing control. All 30 bound inputs
  matched before and after. Local report
  `.runtime/code-git-vectors/20261109T113314Z-ik0euo89/output/report.json`
  SHA-256 `e0a83ffc8a5358a925c2112920553f2065575d753f6af51c7e4662345e9de1dc`.
- The [fetch profile](CODE_GIT_FETCH_PROFILE.md) records 59 pure native and
  stock readback checks and a separate 13-check stock clone/fetch proof in
  isolated loopback. The listener is a synthetic fixture. Native authority
  integration and stock push remain open.
- Exact commit ancestry uses tagged walking, ancestor, diverged and invalid
  results, following commit parents through a scoped object reader one turn at
  a time. The pinned evaluator passed 16 arms and both failure controls.
  Local report `.runtime/code-ancestry-pKlbKM2c/output/report.json` SHA-256
  `bbccc5cf6f5e18f0fec0c8e364f0a4f7c067a5176a28c051a17549a032c0fbad`.
  The future receive transition must separately verify complete graph closure,
  current authorization and ref compare-and-swap.
- The [versioned repository reducer prototype](CODE_REPOSITORY_STORE_PROFILE.md)
  passed 41 native cases and two failure controls. Under its small proof
  quotas it combines admitted objects, refs and receipt in one candidate state
  or returns the original state. It checks current credentials before receipt
  replay and denies protected ref changes pending stored review integration.
  The reducer and its tests were qualified separately from the installed team
  workflow. The Home still needs durable staging and native service routes.
- Both role archives from `219b5bd9e134331981ec7b42627be6f02d798244`
  were rebuilt byte for byte and verified against their declared target.
  Local directory `.runtime/releases/astra-candidate-8yCV5UMh`.
  Home SHA-256 `18b73461298eef7f0697dd90ff4a82960e23ac4bd59dd8ab440060d7029ba5ab`.
  Identity SHA-256 `4bc7d986a50a398247335a0d64530237e46c07f7949b4c96c09ca51b7cef53ce`.
  Each has 53 of 56 desk files equal to the previously tested role payload.
  The generated inventory and two Home CSS/JS assets changed. The earlier
  install results retain their own archive scope.
- The [stopped Home recovery](RELEASE_PACKAGING.md#isolated-boot-of-a-restored-home-clone)
  verified 611 files and cold-booted a fresh restored clone of the historical
  Home payload, passing 12 native checks with clean shutdown. It tested
  configured startup and HTTP boundaries.
- The [same-schema asset upgrade](RELEASE_PACKAGING.md#same-schema-home-asset-upgrade-rehearsal)
  passed all 15 native checks on a fresh copy of the historical Home. It
  removed superseded assets in Clay, verified the exact target desk, kept
  HTTPS fenced until a fresh bootstrap, and preserved the authoritative v3
  database fingerprint. This is scoped to the tested asset change and saved
  configuration. Cross-schema upgrades, accepted business data recovery and
  live continuity have separate gates.

The final host suite ran 810 cases with one skip. The local review, Git and
recovery evidence do not qualify a live canary or close the Phase 3/4 release
gates.

[Phase 5 deployment runbook](PHASE5_DEPLOYMENT.md)

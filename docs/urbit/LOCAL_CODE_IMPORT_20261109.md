# November 9 local Code and import verification

The standalone development fixture used four disposable Urbit ships, the
pinned Vere and Git runtimes, and a private local TLS CA. The previous manual
review workspace was separate. The proofs used synthetic records and local
authority. They carry separate statuses for Work/Docs, Code, import, recovery,
and packaging.

## Configured Home and portable import

The configured native run passed 1,064 observations, including four cold
restarts and exact readback of 115 installed files per ship. Native source
inputs matched before and after. Firefox then passed 34 Work/Docs checks,
including individual approval, shared and private document boundaries, stale
revision, lost response, local draft recovery, and revocation. A separate
stock Git check passed for the three Docs histories captured by that journey.
The guard completed in 1,606.076 seconds and all four ships stopped.

The portable import probe captured two Work records, three collections, three
pages, and one relation through a current member session. It applied two
commands, resumed in a fresh client process, and verified all ten accepted
records through authorized HTTPS readback. The import created a separate
project and new receipts. Original authority, complete history and Git
ancestry are outside this create-only format. [Portable recovery and import](PORTABLE_RECOVERY_PROFILE.md)

The original Code diagnostic created a repository, then failed before its first
Git request because it tried to use a Python HTTPS connection as a context
manager. The Work/Docs pass and the import pass have independent evidence. The
corrected Git retry uses an explicitly closed connection.

| Evidence | SHA-256 |
| --- | --- |
| Configured native `.piers/fakes/logs/team-check-20261109T161652Z.json` | `a943c66cd710f51fbaed6f15ada457feaa3dc84e8a27a353eb21a2a3e56772fc` |
| Firefox `.runtime/browser-native-20261109T163431Z/browser-report.json` | `115158d4375006605fad41bf2f62d61ef2fbeb4b0bc55ea74a84316b050f13ce` |
| Transport `.runtime/browser-native-20261109T163431Z/transport-report.json` | `73c0669a45a68dc7f15f8baa93fdf6cb4838b7ec91a0f0a352bf7050a7d971cc` |
| Docs Git `.piers/fakes/logs/team-git-20261109T163431Z.json` | `d053cd1764ae1503d63ec3f8824a8a03d3b625221e2bc0f00d384d9f3db4302a` |
| Guard `.runtime/execution-runs/four-fakes-yefijnur/report.json` | `79532e9f789fd5b60c5a4d7c74d66f2ea1416173eb1e8491ffc60aca7b0133d4` |

## Native stock Git and Code

A focused retry started copied test ships from the sealed fixture and used
fresh individually approved browser sessions. The first retry passed empty
clone and Code layout checks, then stock Git's first push returned HTTP 400.
The pinned send-pack emits a single space before the capabilities following
the command NUL. The decoder now accepts that delimiter and still rejects
duplicate and malformed tokens. [Pinned send-pack source](https://raw.githubusercontent.com/git/git/v2.55.0/send-pack.c)

The corrected run at `242ee45d12f43dbbefe9227b000bf3d1531b2059` passed ten stock
Git observations and four browser checks. It verified an empty clone, atomic
branch and annotated tag creation, exact commit and binary blob readback,
strict Git fsck, fast-forward and fetch, stale compare-and-swap, malformed
pack denial, protection, and revocation before an upload finished. A
read-only credential could fetch and could not push. A separate reader
principal was denied a write credential. The Code view survived selecting
the project again and was captured at 320, 390, and 1440 pixels. An
independent Astra ultra review inspected all three native screenshots and
found no blocking visual issue. Credential issue and revoke were exercised
through the API. The browser proof checked the Code controls and reader
write denial.

The final branch head was `35ff7e047e65d0efaca2effccc246a4b1303c647` and the
annotated tag object was `1db85568b0e8d403d28bb0dbbf40bff3f6ce4fdf`. The guarded
run completed in 294.819 seconds, retired the browser, and stopped all four
copied ships. The original stopped four-fake fixture rehashed unchanged.

| Focused evidence | SHA-256 |
| --- | --- |
| Source ledger `.runtime/native-code-retry-Dh9rv6q4/source.json` | `0586eb81829e73cf9b0b931de47821f842fe1536181bd1a55bdd2a9c27004014` |
| Browser and stock Git `.runtime/native-code-retry-Dh9rv6q4/browser-xs120jmg/result.json` | `cb59ced42fb57cf3d8090932ec89110ecf25b2da4b99c0ef7128a3af3509b090` |
| Guard `.runtime/execution-runs/four-fakes-9hr4dqgk/report.json` | `7d22f7b901dfa2d0db92723e75121950f969556c2884d8a99caca9202cfb7a9f` |

## Saved Home state

The isolated recovery copied the stopped synthetic Home and independently
rehashed the original checkpoint. It verified the v4 Work/Docs database and
enabled empty repository fingerprints before suspension, while suspended, after native
reload, and after a fresh owner bootstrap. The restored Home returned 503
until bootstrap, served the exact packaged shell over TLS 1.3, and denied the
still-unexpired prior browser session. The copy stopped cleanly. The
`review_prepare.py` fingerprint used in this proof retains the v4 repository
map while excluding the rebuildable Work/Docs projection.

Private report `.runtime/team-home-recovery-stage-Kg5hSgVg/work/proof-report.json`
SHA-256 `a7d77a2bf5795a25bc80da5e48ca332c87a004cc213030447e6d34b05a572998`.
The proof covers an enabled, empty repository and its accompanying Work/Docs
state.

The populated recovery used the stopped clone from the successful stock Git
run. Native checks matched the saved main branch, annotated tag, protection
and all seven reachable objects against an independently verified stock Git
clone. They matched each object's kind, original OID, byte length, and
SHA-256 before suspension and after fresh bootstrap. The native Home retained
its exact Work/Docs and Code fingerprints and served the packaged shell after
bootstrap. The guard stopped cleanly after 27.020 seconds and the copied
checkpoint's source remained unchanged. Private report
`.runtime/team-git-recovery-stage-i79NPqRt/work/proof-report.json` SHA-256
`376e4d110a55676896836834c8d205f80ca78206972c236c42e246034088b146`.

## Agent proposals and build transitions

The [delivery reducer](CODE_DELIVERY_PROFILE.md) passed 44 native cases and four
verification controls. The independent review found that a later revision
or ref change could hide an earlier accepted build or release outcome from
an exact retry. The repaired reducer checks stored outcomes separately from
fresh mutation rules, with current membership and permissions still required. A separate loopback-only worker built a fixed synthetic
source with pinned Git and retained exact source, recipe and artifact hashes.
The reducer and worker proofs have separate inputs. Home board persistence,
protected-ref acceptance, and product integration of external workers remain
open.

Reducer report
`.runtime/code-delivery-replay-9KkOuuRV/runs/20261109T170156Z-5fzq5v5u/output/report.json`
SHA-256 `ebee5f35941ec9aea099b86b50befd83bd8695039f17db03d8e349c56db373cb`.
Worker report
`.runtime/code-delivery-BHfYWMKu/build-proof-99roqz6f/output/report.json`
SHA-256 `cf3fc89453a14a35d40df7567c9b8563f702878d9e5a6ca3217ee99015622c5b`.

## Offline desk packages

Both role archives from `011fef82717dca9a1e6a7506e247106a6b09ce8e` rebuilt
byte for byte and passed exact offline verification against their reviewed
target JSON. The Home declares maximum saved state v4 and Identity declares v1.
Historical Home v3 archives remain verifiable against their own pinned targets.
These packages were verified offline. Clean installs of these exact role
archives and a supported cross-schema upgrade have separate evidence requirements.

| Archive under `.runtime/releases/code-review-aAmAlM7B` | SHA-256 |
| --- | --- |
| Home | `e4bcc7e777b2567ee9fad667537cb500558bde6ecb88d1eb6392df7e384a5ae0` |
| Identity | `c11730f68976c2f049aac32c5ad519e995cc834f9cd30f7635c73ee0d49354f4` |

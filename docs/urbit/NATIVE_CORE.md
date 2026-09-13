# Native Work/Docs and permissions slice

This increment implements one home-owned synthetic project/work/document state
machine and authorization together. The minimum contracts remain byte-for-byte
frozen under `specs/urbit/contract-freeze.json`. Its executable desk is
`native/core/desk`; the URB-020 counter remains separately available in
`native/desk`. They are installed into separate fresh test runs, never as two
simultaneous owners of the same state.

From a ready four-fake-ship harness, run `make core-test`. It restores only the
marked disposable fixture from stopped, verified seeds, installs/compiles the
Hoon sources on all four fake ships, and drives the home through real native
messages. Python controls test inputs and inspects outcomes; it does not decide
permissions or manufacture the home's document commits. `make test` still runs
the original counter suite. Stop/start the supervisor after Python runner edits.
Neither command resets the Git checkout. See [RUNBOOK.md](RUNBOOK.md).

`stead-home` owns projects, work revisions, document pointers, grants and retained
revocations, immutable Git objects/refs, receipts and the application journal.
Pure `stead-core` transitions intersect the fixed context with current explicit
grants and action/container scope. The home takes the principal from Gall's
sender, checks current authority/epoch before retry lookup, and applies resource
revision checks at acceptance. An accepted event changes its resource, journal
and receipt in one native transition. Policy revision is separate from document
and work revisions. Rejected commands preserve that business state.

The four principals are fixed public/synthetic fixture bindings, not a login
system. Owner-local fixture controls deliberately invalidate context and exercise
save/load rejection. They are restricted to the fake home administration context;
the snapshot contains private-test state and must never become an employee API.
There is no HTTP handler, browser UI, credential issuer, real identity handshake
or installed-app isolation claim. Gall's owner/local administration surface is
still privileged even though the application provides no member scry.
These development clients exchange synthetic bodies through fake ships. The
future identity-only personal-ship handshake and direct HTTPS browser content
path have not been implemented or qualified by this test harness.

A document save accepts the frozen minimal Markdown/frontmatter subset into an
explicit owner-private container. Exact bytes are the Git blob; native Hoon also
creates the tree and commit and advances the container ref and document pointer.
Parsed metadata is not a second writable document master. Work items can be read
by explicitly granted project readers; a private document still requires its
container owner's access. Publication and broader container sharing are later
work. No full forge, Smart HTTP upload, pack parser or asynchronous push is implied.

The host export adapter fetches a currently authorized manifest and each object
separately, checks identities and byte digests, materializes those exact bytes
with stock Git, and runs fsck and file recovery. A prior manifest is not authority
for a later object fetch. The export is a bounded document-container test artifact,
not a complete portable organization backup. A failed export may leave a private
partial disposable directory; it does not change any home ref.

The QA corpus has independent expected receipts, revisions, policy decisions,
negative outcomes and object bytes. The root runner preserves the QA report's
skipped/source-only assertions as incomplete rather than marking them executed.
Pure reducer permutations, real message outcomes, mocked adapter checks, actual
stock Git operations and static Hoon review have separate evidence labels.
Source/toolchain/corpus hashes are captured before and after every native run;
loaded Python mismatches or source drift fail that run.

The initial saved-state format is `[%stead-home %1 state]`. There are zero declared
predecessor product formats. Owner-only tests invoke the real `on-save`/`on-load`
arms, and reject the counter and future versions without changing accepted data.
Warm process restart is tested separately. Neither check establishes abrupt-crash
windows, production backups, a safe runtime rollback or same-identity live migration.

Open confidentiality decisions include caller-selected globally unique IDs
(create success versus collision can reveal allocation) and project journal
sequence counters (aggregate activity can leak across private containers). Opaque
known/unknown read outcomes do not resolve those design limits. Real company data
remains blocked pending the independent authentication, endpoint-isolation and
backup reviews in the master directive. Capacity-edge fill schedules, concurrent
subscription races, abrupt crash injection and production effect replay monitoring
are also separate gates; no representative latency or capacity claim is made.

Executed counts, failures, exact source binding and review links belong in
[TEST_RESULTS.md](TEST_RESULTS.md) and the attached issue evidence, not this usage
and scope description. No implementation merge or release approval is implied.

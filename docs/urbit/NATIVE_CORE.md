# Native Work/Docs and permissions slice

The original increment executed one home-owned synthetic project/work/document
state machine and authorization together at `f52293f`. The v2 code now compiles
and has passed 53 native compile/save-load probes. **Full v2 qualification remains
open:** core05 at `5208f32` reached all 148 main cases (145 passes and
three frozen deferrals), completed the seven delivery cases, and filled the
4,096-event predecessor. A malformed-policy load then timed out without a native
terminal response; seven capacity/predecessor recipes remain unexecuted. The
preceding timeout-lifecycle correction passed 470 host tests and both focused
native timeout/recovery cycles. Full-state validation and final reconciliation
remain required. The new focused capacity diagnostic has not yet run.
See the [current checkpoint](PHASE01_CHECKPOINT_20260926.md).
The original minimum contracts remain byte-for-byte frozen under
`specs/urbit/contract-freeze.json`; the narrow [v2 amendment](CONTRACT_AMENDMENT_2.md)
has its own `specs/urbit/v2/contract-freeze.json`. The native desk is
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

The current source saves `[%stead-home %2 state]` and explicitly converts the
original `%1` format. The test-only predecessor builder calls the archived v1
transition, in batches of at most 32 commands, to produce an actual old-state
vase; it does not assign a fabricated journal count. Migration reconstructs and
checks content/policy projections while preserving original journal, receipt and
Git bytes. These migration and corruption tests still need a completed qualifying
run. Current save/load, predecessor migration and fenced process restart are
separate required checks. The frozen Phase 1 restart gate requires a cleanly
stopped process and a distinct replacement retaining the same pier. Abrupt-crash
recovery has not been qualified and is not that gate. None establishes production backup recovery,
a safe runtime rollback or same-identity live migration.

V2 scopes local work IDs by project, documents by project/container, and grants by
project. It removes the global resource-availability lookup. Public receipts use
a closed sixteen-field projection without internal sequence/digest/policy counters;
normal replies, retries and recovery use the same scope. Original internal bytes
and the v1 freeze/evidence remain unchanged. New writes require command2; retained
command1 retries are replay-only and undergo current authorization first.

Ordinary accepted activity is bounded at 4,096 records. Each of at most sixteen
projects has a separate reserve of 128 revocations for its retained grants. A
fully consumed reserve, or an exhausted policy counter, closes that project's
protected reads, retries and mutations. No ordinary workload consumes another
project's security reserve. No history is erased and no administrator bypass is
introduced. The derived bound is 6,144 retained acceptance records.

These privacy/capacity changes require their actual native regressions; source
review is not reproduction of either old vulnerability or proof of the fix. Real company data
remains blocked pending the independent authentication, endpoint-isolation and
backup reviews in the master directive. The current gate requires capacity-edge
fill schedules, actual subscription evidence and the specified fenced restart.
See the [attributed restart-scope correction](reviews/PHASE1_RESTART_SCOPE_CORRECTION_20260926.md)
for the controlling requirements and the preserved earlier wording. Production effects remain later work.
There is no implemented external-effect
subsystem to replay; this is a bounded source/N-A disposition, not effect-engine
qualification. No representative latency or capacity claim is made.

Executed counts, failures, exact source binding and review links belong in
[TEST_RESULTS.md](TEST_RESULTS.md) and the attached issue evidence, not this usage
and scope description. No implementation merge or release approval is implied.

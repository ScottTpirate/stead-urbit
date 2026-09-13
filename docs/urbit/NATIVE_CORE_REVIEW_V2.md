# Native privacy and exhaustion amendment — independent source review

Reviewed September 13, 2026 by `/root/hoon_review`. Implementation owner:
`/root`; adversarial test and observer owner: `/root/qa_review`.

**Current disposition: bounded design and static source review complete for the
closing hashes below; v2 native qualification has not run. Phase 1 qualification
remains incomplete.**
The implementation owner reported that the execution guard refused startup at
unsafe host temperatures. This reviewer did not run Vere, start or stop fake
ships, bypass the guard, or execute the new migration/observer corpus. Historical
v1 successes do not qualify changed v2 source. The old review and its 25 skipped
assertions remain unchanged in `NATIVE_CORE_REVIEW.md`.

This is independent agent source review, not a human Hoon specialist audit,
owner approval, permission to merge, live authentication qualification, or release
approval. The reviewer edits only this note. Repository origin was verified as
`https://github.com/ScottTpirate/stead-urbit.git`; original Stead upstream has a
disabled push URL.

## Source and contract binding

Review base: `77428f6c35eb0fe7b7e497b64c5a1eab92e943cd`. The v2 implementation
is uncommitted at this checkpoint, so that commit alone does not identify it.
Initial inspected source hashes, relative to `native/core/desk/`:

| File | SHA-256 |
|---|---|
| `app/stead-home.hoon` | `63fc32d610a05a1e16c8c461fb2c11cd556422d21fe8bf9b4a4606ca6277916f` |
| `lib/stead-core.hoon` | `74a14ee693e54ad119b286e081ef1e7aa74e8f15094dde28850133441a187f73` |
| `lib/stead-codec.hoon` | `56e3d574381bbf8cdf29ca192c70eff256009f89d782e3ffe859b19c1321cbd7` |
| `ted/stead-client.hoon` | `a3359a607819c13045bfe006b981a807de59c1adfb72ef12310b200bb697e465` |
| `lib/stead-delivery.hoon` | `178cac634471554dae9928f8c38248751329314391061976a436a22a7075548d` |
| `lib/stead-git.hoon` | `826b83485429c02f577c9b462ee6cddd3ab8ea1a099d33b66893f863d54c54d7` |

Both contract manifests were independently checked with Python `hashlib` against
all listed files: nine original files and five amendment files, no mismatches.
The v2 manifest hash is
`a2336e5060c71c7c16849b3151cc024a598d6cdf867561452eff1338e3232670`;
the amendment hash is
`f9793a947b4ba69e9099ec0cd68ed004602cb0ffe6fbbf79f9f464cb256315c6`.
This establishes immutable planning bytes, not runtime behavior.

Toolchain lock remains
`4a209c10cf1756eb0f7357cc3eca8250bf66c239b4cd0ca31a8c0886d4d304ee`:
Vere 4.6 at `8ddc4b786979574dbfcb655e3db1b634f658d0de`, kernel 408k-2
at `5a187fededc4582a34fcd6055c67bb63e0917b94`. These are intended compilation
inputs; this review did not compile the amendment.

## Bounded design disposition

The amendment addresses the identified oracles by making identity a complete
typed reference: project/work/local ID, project/document/container/local ID, and
project/grant/local ID. Validated UUIDs cannot contain the `/` separator used by
the implementation. There is no legitimate cross-kind or cross-container
availability lookup for these resources. Project allocation remains restricted
to the explicit single-organization administration metadata capability; this
does not grant content access. A second organization remains gated on its own
scoped allocation design.

Public receipt2 omits journal sequence, journal digest and policy counter.
The internal journal and historical receipt bytes retain their original format.
Current binding, handling profile, scope and epoch must precede accepted-receipt
lookup; current authorization also governs recovery and object export.

The reserve math is bounded: 4,096 ordinary accepted records plus 128 revocations
per project, with at most 16 projects, yields at most 6,144 accepted records.
Each retained grant can be revoked once, including the creator grant. Ordinary
work cannot consume another project's reserve. The last authorized revoke may
return its receipt at the pre-decision linearization point; reserve exhaustion
then closes that project. Duplicates and rejections must consume no capacity.
This is a shared-runtime availability policy, not a constant-time guarantee.

## Findings from the initial source pass

These are source-derived findings, not native reproductions. The closing
addendum records source corrections; their native regressions remain pending.

1. **Incomplete scope correlation in the client.** Initial client lines 63–101
   checked project/resource/request/digest but omitted receipt `resource_kind`
   and `container_id`, and did not match a document read's container payload to
   the requested path. Reused local IDs make these fields part of identity.
   Enforce the closed receipt2 field set and complete scope correlation.
2. **Public projection used a blacklist.** Initial `public-receipt` copied the
   stored object after deleting three fields. It must construct the frozen
   sixteen public fields explicitly, so unexpected predecessor fields cannot
   become public merely because their names differ from the blacklist.
3. **Predecessor validation was incomplete.** The initial validator checked
   journal/receipt counts, canonical journal hashes and chain links, receipt
   correlation, object-body hashes and revoke flags. It did not reconcile final
   policy/resource counters with the journal, nor validate all document,
   container and reachable-object references. An altered policy counter,
   dangling document pointer, or extraneous private object in a reachable set
   could survive conversion. Validate those structural invariants and the closed,
   canonical accepted v1 receipt shape. A same-count corrupt fixture is necessary;
   deleting every receipt only exercises the simplest count mismatch.

## Predecessor provenance and migration limits

The archived v1 codec is byte-identical to the codec at the review base:
`ce4c7a69b03ee1761590c37e71ff49b9f63a1a2edd2aaa6dfbf75bc3c960584a`.
The archived core is byte-identical after exactly two codec import-name changes
in `/+` and `=,`. Its hash is
`879615a5547d06a09d382c2bac4c5cb20cdf03236ddfdab79c9f1da15bd33cb5`;
the original core hash is
`6c886d37d17b2ef6c732e72c92934d586c2dd36aa1c13691456cc46757184d24`.
These comparisons were executed locally using `git show`, byte comparison and
SHA-256; no v1 transition was executed during this review.

The owner-only predecessor builder calls the archived v1 transition function
with at most 32 commands per event. The planned test passes its actual version-1
state vase into the version-2 `on-load` converter. If executed with source-bound
inputs and outputs, this is legitimate generated-native predecessor evidence for
format conversion. It is not an installed old-Gall-app upgrade, an operational
OTA test, or a production recovery rehearsal. The builder is test state and is
not a second authoritative home. No hand-assigned journal counter can substitute
for the required 4,096 accepted predecessor transitions.

The converter must preserve raw receipt/journal bytes, canonical Git objects and
OIDs, content pointers, explicit grants, revocations and bindings. It must not
reauthorize historical commands using present permissions or create acceptance
records for its own conversion. Current save/load, predecessor conversion,
graceful restart and abrupt-crash recovery remain distinct tests.

## Delivery observer and remaining execution gates

The test-only observer is owner-controlled on the four disposable fake ships and
targets only `~zod`/`%stead-home`. It retains bounded event metadata and hashes,
not content bodies. Review requested persistent failure metadata for malformed or
oversized facts, a correct path-depth bound, saved-count consistency, explicit
labelling of the inferred peer-agent field, and sign/lane correlation. The closing
addendum binds the corrected observer source.

The following remain unexecuted for v2: native compilation; scoped-ID collision
and metadata-oracle regressions; real predecessor and full-capacity reserve
tests; actual facts/kicks, wrong-duct, leave/cancel, lazy expiry and quota tests;
missing/late/unavailable outcomes; malformed migration rejection; current and
predecessor save/load; graceful restart; abrupt-crash recovery; authorized native
export and independent Git object verification. Required current-phase cases
cannot be waived by the previous 25 skips or a green host planning validator.
Later phases remain blocked until the current gate has the required evidence.

## Closing static-source addendum

The following exact sources were re-read after the findings were corrected.
This is an uncompiled source disposition. Later source changes require another
review; none of these hashes is bound to a passing v2 native run.

| File under `native/core/desk/` | SHA-256 |
|---|---|
| `app/stead-home.hoon` | `586f595bd465f692c545fc08421b985810573857ac5f42446b6f3b6f6e9e1ce8` |
| `lib/stead-core.hoon` | `9ad77eba9c2bb5e916af74c62250761513278bdbfbb729ec3919edb04d2b5da4` |
| `lib/stead-codec.hoon` | `56e3d574381bbf8cdf29ca192c70eff256009f89d782e3ffe859b19c1321cbd7` |
| `ted/stead-client.hoon` | `fb30805f20d8c9ef02b5287d3366d570af39b005c5a5c51607c6aa2fd45ba9ce` |
| `app/stead-observer.hoon` | `678109ed478d2cbdcc0ed0b3c3976635f6555352485625c81d38fb3f2a1291a3` |
| `mar/stead-observer-1.hoon` | `e30d449181f121ea403b8d38e12d3b925362591ee516092f254852af0631a684` |
| `mar/stead-command-2.hoon`, `mar/stead-result-2.hoon` (each) | `fcd87c92acc16c2883b1dd4900af5064d1da910af317e93c327455cd56d9553b` |

The public projection now constructs exactly the sixteen specified fields. The
client checks the closed receipt shape and correlates resource kind and container
on mutation/recovery responses, and container on document reads. Administrative
snapshot revision keys now include kind, preventing project/work local-ID
collisions from hiding a diagnostic revision.

Migration now verifies the canonical closed accepted-v1 receipt shape and walks
the preserved journal to reconstruct policy counters, work revisions/data,
document revisions, container trees/commit history, exact Git objects and
reachable sets. It compares those projections with the stored predecessor. It
also reconstructs the complete retained grant map, including each explicit
grant's principal/role/expiry and project-matching, one-time revocation. The
creator grant's implicit historical expiry was never recorded in the v1 journal;
the converter preserves its existing bounded value and does not claim to verify
it independently or derive it from today's binding. Current bindings are
preserved, not historically authenticated by this projection.

An uninitialized predecessor must equal the exact pristine state with
`initialized=false`; initialized predecessors must contain both fixed fixture
containers, including an empty one. Corruption controls now include same-count
policy, grant and reachability changes and flipping the initialized flag, as
well as deleting receipts. These controls exist in source; none has run on v2.

A further delivery finding was corrected: lazy expiry of a result path could
kick a freshly registered duct at that same path while retaining its new pending
row. The corrected event retires the expired route and stores no replacement;
a subsequent registration may reserve it. The retire event's ACK/kick is not a
business receipt. A client that sent its command without receiving an outcome
must remain uncertain and use an authorized retry/recovery.

This reasoning depends on the exact pinned `sys/vane/gall.hoon`:
`+ap-subscribe` lines 1844–1850 inserts the new incoming duct before `on-watch`;
`+ap-ducts-from-paths` lines 1685–1713 resolves a named path to every matching
duct; `+ap-handle-kicks` lines 2300–2315 removes kicked ducts immediately.
`+ap-load-delete` lines 2078–2087 calls `on-leave` only for a still-registered
duct. Supported outgoing watches receive distinct subscription nonces at lines
2366–2380. Consequently, a delayed leave for the retired old duct cannot invoke
`on-leave` to delete the later registration. Native same-path expiry/retry and
late-leave tests are still required.

The observer includes all requested source corrections and faults while retaining
metadata for invalid facts or unexpected sign/lane pairings. Its peer-agent field
is explicitly labelled as inferred from the fixed issued Gall wire. It records
events delivered to `on-agent`; Gall can reject mark conversion or routing before
that callback. Zero observer facts therefore is not proof that a peer's runtime
never received bytes. Privacy tests need a valid-mark positive control and
retained runtime errors. A passing observation must have an empty fault field;
aggregate ACK counts from multiple pokes do not independently correlate each
command.

The owner-only held-outsider-read hook creates a real overlapping Gall
subscription for a selected test path without storing a body or changing
business state. Both predecessor and current-capacity batch controls call real
pure transitions in bounded batches but use an administrative selected sender;
they cannot substitute for separately executed four-ship sender-authentication
tests. These hooks remain confined to the disposable synthetic profile.

Executed checks for this review were file reads, `git diff --check`, exact source
byte/import-alias comparisons against `git show`, SHA-256 checks, and both frozen
manifest checks. The historical review remained byte-identical at
`724e357bd740fa3ac23a55d2df52f105928f5b1027d32ad1ccd5604cb1ca91a2`.
No new native test, runtime benchmark, migration, export, network observation or
GitHub action was executed by this reviewer. No remaining source blocker was
identified within this bounded pass; compilation, runtime correctness, migration
cost and all required qualification evidence remain open.

## Follow-up: predecessor read and pending-duct diagnostics

The following narrow test additions were independently re-read after the closing
snapshot. Earlier hashes remain recorded above; these replace only the listed
source hashes for the current static disposition.

| File under `native/core/desk/` | SHA-256 |
|---|---|
| `app/stead-home.hoon` | `122bb4d8b7b27f25eddb8652e5552a7f46298e156cdc3e73023044b6ce78ed6b` |
| `ted/stead-client.hoon` | `e039355539b2aef4db0ac8137dae71984d9284abeaffd20a1d9fb110adb35c5f` |
| `gen/stead-build-probe.hoon` | `5b95dc5675894897cdf1bda25cbb9bf27100dd6bd305dfd836aad4ec06725d96` |

The `legacy-read` control remains behind owner-local administration and an
initialized predecessor. It accepts at most 512 input bytes, exactly two UUID
fields, and only the three literal project/work/document route kinds. It calls
the exact archived v1 read function with an administrative selected sender and
stores the result in the existing owner-readable fixture response. This is a
predecessor behavior fixture, not a native sender-authentication test or an
employee legacy-read endpoint.

The owner-only `/v1/pending-snapshot` evaluates the existing pending map without
pruning it. It caps its entries at 64 and reports each pending path's current
incoming-duct count from `sup.bowl`, using the pinned Gall `bitt` map shape.
The snapshot's own request path does not equal a pending result path and is not
included in those counts. These are actual Gall counts for listed pending paths,
not a complete inventory of orphan or held subscriptions; observer events and
outgoing-subscription evidence must accompany them. Result serialization fits
the existing three-object-level parser and response cap.

The client recognizes this exact fixture protocol on its fixed diagnostic route.
The build probe now explicitly imports the observer app and mark, so later native
execution must compile them too. The changed expiry condition is the same
short-circuit unit guard in wide syntax. No pseudo-helper or dynamic Hoon source
construction remains in the additions. Core, codec and observer source hashes
are unchanged from the prior addendum. `git diff --check` passed. No new source
blocker was identified; all native compilation and execution gates remain open
following the reported thermal refusals.

## Follow-up: ended observer subscription and Phase 1 threat inventory

The observer's added `leave-ended` control was independently re-read at SHA-256
`f0eafde4ed667db2ee304181e9397c01b7113eee13a10de2b7a88f437a3f7539`.
It retains the owner-only control boundary, requires an existing closed or
leaving watch and empty route/body fields, and emits `%leave` on the original
wire without fabricating an incoming sign or changing business state. No new
source blocker was identified in this delta. Native compilation and execution
remain unperformed.

This control can exercise a stale local leave request. The pinned Gall source
at `sys/vane/gall.hoon` lines 2333–2336 drops an outgoing leave when its
subscription is already absent. An ACK to the control poke therefore does not
prove delivery of a reordered leave to the home. Observer events and unchanged
fresh pending/receipt state can support the narrower local-control claim;
receiver-side handling of an actually delayed old duct remains source reasoning
until exercised separately.

The [Phase 1 threat/test map](PHASE1_THREAT_TEST_MAP.md) was reviewed at SHA-256
`dd955052c968b18dc594d274ea43a365ba00c3b450d5f6dff90fbd3c8b982654`
against the current acceptance body of
[#24](https://github.com/ScottTpirate/stead-urbit/issues/24), selected retained
threat/bypass entries, and the current source boundaries. No remaining blocker
was identified for that issue's bounded Phase 1 design/test-inventory gate.
This disposition does not close its later implementation or release obligations.

The reviewed map explicitly distinguishes current fake-peer body delivery from
the later direct-browser identity profile, result reservation paths from current
read ducts, bounded pending/object state from unimplemented rate limiting, and
external bulk-storage custody from the current native object implementation.
It records publisher-controlled code and reviewed installed apps as plaintext
trust boundaries. The pinned owner-local `%v`/`on-save` route at Gall lines
3025–3042 bypasses application `on-peek`; absent member scries cannot establish
installed-app or administrator isolation.

The map assigns identity lifecycle, browser origin isolation, restored revocation,
effect replay, malicious content and custody evidence to the existing owning
issues. Those obligations remain unexecuted where stated. Neither this design
review nor the observer delta changes the failing/unexecuted v2 qualification
disposition, waives any of the historical 25 skips, or constitutes human approval.

## Follow-up: pure policy-counter boundary probe

The added checks in `gen/stead-core-probe.hoon` were independently re-read at
SHA-256 `ce41ca465d959dabde9c9dbfb0f39db4294ec5117b5b7d65c7b2f8a2a21f718c`.
The core and codec retain their previously reviewed hashes. The existing positive
project, identical-retry and outsider checks now use command2. The added local
values set the policy counter to u64 maximum minus one and maximum, assert the
`closed` predicate's boundary, and require opaque denial for a project read and
accepted-command retry at maximum. The denied transition also compares the
entire unchanged input state. Current read scope reaches the closed check before
stored-receipt lookup, including the project-create retry used here.

No static syntax or semantic blocker was identified within this narrow addition.
It deliberately alters a local generator value; it does not install saved state
or construct the provenance-bound capacity fixture. It does not test an accepted
policy transition from maximum minus one to maximum, migration, persistence, or
4096-event exhaustion. The fixed success tag is reachable only after the source
assertions, but the generator has not been compiled or executed on v2. Native
qualification remains open under the common execution guard.

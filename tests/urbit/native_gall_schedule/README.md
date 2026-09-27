# Delayed old leave: bounded native Gall schedule

Status: the prior draft compiled and reached its scheduling assertions in the
retained Gall04/Gall05 runs, then failed report serialization. The protocol-2
projection revision below has not yet been natively compiled or executed. This
directory alone is not acceptance evidence and does not amend a frozen contract
or qualification mapping.

The proposed classification is `native-scheduled-gall`: compile and execute the
actual pinned `/sys/vane/gall`, `/app/stead-home`, and `/app/stead-observer` gates
inside a disposable fake's native Hoon generator. Only the delivery queue and
clock are simulated. The two Gall states represent `~zod` and `~bus`; they are
ordinary immutable nouns inside that generator, not duplicate live ship piers.
This does not exercise Ames encryption, packet routing, UDP, wall-clock expiry,
separate processes, or actual network authentication.

The receiving Gall, not the test, decides whether `on-leave` runs. No test calls
`stead-home.on-leave` directly, changes `bitt` or pending state, or fabricates a
leave task. The test takes the real sender-Gall-emitted `%pass %g %deal %leave`
while its old subscription is active, retains that exact immutable noun and
nonce-bearing duct, and later calls receiving Gall with those exact values.
Directly routing an emitted Gall deal is the explicit mocked transport boundary;
return gifts are dispatched through the real sender Gall `take` arm.

The schedule is:

1. Install the actual agents using the pinned upstream `make-gall` / `load-agent`
   pattern. Initialize the frozen public fixture, then submit canonical project
   creation and contributor-grant commands through home Gall.
2. Have the actual bus observer watch the exact work-command result path. Route
   its emitted watch and the real home watch ACK. Query pending and observer.
3. Ask the actual observer to leave while its watch is active. Capture the one
   emitted Gall leave without delivering it. Sender Gall has now removed its
   old outgoing subscription; retaining a leave after this point is the tested
   scheduling gap, not an edited runtime data structure.
4. Submit the real work command through the observer and home Gall. Preserve and
   deliver every emitted poke ACK, result fact and kick to sender Gall. Its old
   observer sees no private fact because its local watch has already ended.
5. Register a distinct observer probe at the identical result path. Require a
   different sender nonce/duct and exactly one actual incoming home duct.
6. Deliver the captured old leave unchanged at the captured old home duct.
   Require no emitted moves, identical pending query, identical incoming duct
   map, identical fresh and old observer queries, and identical business history.
7. Retry the same work command via the fresh observer. Require one correlated
   native fact, one kick, watch/poke ACKs, identical receipt bytes, pending zero,
   no old-probe delivery, and unchanged business history.
8. Positive live-leave control: another real watch at the same path, followed by
   its actual emitted leave, must remove the reservation and incoming duct.
9. The negative generator uses the same schedule but expects pending two when
   the actual fresh pending count is one. It must fail at the labeled assertion;
   a compiler error, timeout, missing output or generic process failure is not
   evidence of this control passing.

`build_inputs.py --check` checks exact generated input bytes and the input
manifest only. It neither compiles Hoon nor exercises Gall. To regenerate, use
`build_inputs.py --write` from this repository; it verifies derivative remotes
before writing and only writes inside this directory. The selected canonical
commands come from the existing v2 corpus, without changing it.

Root integration must copy this directory's `desk/` overlay into the same
disposable desk as the current native core. Run the positive and negative
generators through the guarded native harness, retaining command, raw output,
compiler log, current pins, native-core/overlay/input source hashes before and
after execution, and both results. The positive wrapper returns a single
`%stead-core-result` hex-encoded JSON object, using the existing bounded parser.
The runner must check the explicit `passed` result and named controls; the
negative generator must be recognized as the intended runtime assertion, not
an arbitrary failed build. Root and the independent test owner must approve
any mapping of this evidence to `delivery-late-old-leave` before phase closure.

## Bounded reporting and explicitly omitted poke types

`stead.native-scheduled-gall/2` changes only the representation of
`old_poke_moves` and `fresh_poke_moves`. Gall05 measured the actual old poke
output list at 1,376,721 jam bytes for a 389-byte command. Its inferred vase
type therefore cannot be emitted through the existing 16 KiB noun-record bound.
The dispatch schedule still sends every original poke, leave and gift unchanged.

Only during final report serialization, `poke-record` creates a
`stead.gall-poke-projection/1` record. Its bounded `projected_moves` jam retains
the original output order, owner ACK, parent duct, outgoing wire, sender, target,
provenance, agent, mark and exact command body. Only the poke vase type is
replaced with `[ %stead-opaque-vase-type type-sha256 type-jam-bytes ]`. This marker
is deliberately not a valid vase type and is never dispatched to Gall.

The wrapper also retains native-measured jam SHA-256 and byte count for the
original complete move list, selected poke move and omitted vase type. Each
measurement has a separate 2 MiB native-only input cap, based on the observed
Gall05 size. The omitted bytes are never passed to the host decoder. These are
opaque native measurements: the host verifies their scalar bounds, explicit
scope, marker consistency and old/fresh type equality, but cannot independently
reconstruct or check the omitted original bytes against their reported hashes.
The guarded native command, exact output and reviewed source bindings remain
necessary. The host result states `independently_reconstructed: false` and
`native_execution_verified: false`.

Captured and delivered leave records, watch records, incoming duct maps and
result gift records remain complete canonical jams. Their 16 KiB jam limit,
existing host traversal bounds and 128 KiB total report bound are unchanged.
A native scalar diagnostic prints the jam byte counts of both original poke
lists and both result gift lists before serialization. Gift limits remain
unchanged; a gift-size failure is retained for measurement and review rather
than automatically widened or projected.

## Source and license provenance

The native initialization/load helpers are adapted from Urbit commit
`5a187fededc4582a34fcd6055c67bb63e0917b94`,
`pkg/arvo/lib/test/ames-gall.hoon` (`make-gall`, `load-agent`, `gall-call`,
`gall-take`). The actual Gall implementation is imported, never rewritten.
The upstream `tests/sys/grq-out-of-order-pleas.hoon` independently demonstrates
that a leave can be queued while active and remain in flight across a kick;
its Ames simulation is not claimed to have run here.

Pinned sources are available under `.runtime/urbit-5a187fededc4582a34fcd6055c67bb63e0917b94/`.
The retained MIT notice is in `UPSTREAM_LICENSE.txt`. This adaptation changes
the fixed test date to 2026-09-25 so the fixture's explicit expiry is meaningful.

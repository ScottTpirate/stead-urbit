# Stead configured-team SDK v3

This package is a developer desk fragment for the pinned Kelvin 408 kernel.
It exports protocol codecs, raw versioned marks, a bounded delivery reducer,
and a native thread sample. It contains no home state, policy engine, browser
credentials, owner controls, fixture administrator or deployment identity.

The protocol is version 3. Keep the v2 SDK for the legacy fixture profile;
do not translate v2 commands into team commands. The export manifest pins every
file, kernel, runtime and source revision. Package verification checks bytes;
native consumer conformance is separate evidence.

[`API.md`](API.md) specifies the carrier, exact JSON fields, limits, receipt
validation and query/update lifecycle for independent consumers.

Copy `desk-dev` into a development desk with the pinned kernel's `spider` and
`strandio` dependencies. Call the `stead-sdk-call` thread with:

```hoon
[~ home=@p binding-id=@t binding-revision=@ud mode=@tas json=@t]
```

Modes are `%command`, `%query`, `%updates`. The sample derives the sender from
the actual strand bowl, watches the correlated public result path, and waits
for one ACK, one result fact and one kick, in any order. It times out after
55 seconds. Its `%stead-sdk-result` contains the JSON result; transport or
correlation failure returns `stead.sdk-error/1` with `request_unconfirmed`.
Spider compilation and mark-admission failures happen outside the sample.
An invoking adapter must suppress platform diagnostic tangs and report them as
unconfirmed transport failures, never expose them to end users.
That outcome is never an accepted mutation. Keep the original request ID and
exact command for explicit receipt recovery or retry.

The operator supplies your own current binding ID/revision and home. The home
resolves the native Gall sender, verifies the current binding and final project
permissions, and rejects stale identities. The input binding is correlation
information and grants no authority. A client's declaration is never an actor.

Commands require explicit request IDs, expected resource revisions and
authority epochs. Query and update cursors belong to the issuing principal,
session and exact query. Use a fresh request ID for each poll. Open the stream
before reading its snapshot, consume invalidations, and query authorized state
again; notifications are not business receipts. Cancel unused streams. Refresh
on overflow or stale handles. Limits are four streams per principal and 64
global handles, with bounded queues and five-minute handle lifetimes.

The shared `stead-codec.receipt-fields` helper is for receipt/2; it is not a
receipt/3 validator. This thread returns bounded JSON transport outcomes. A
consumer must validate the response protocol, request/digest, native identity,
resource scope and expected revision before treating an outcome as accepted.

Public JSON codecs are optional client-side admission helpers. They do not
replace final home validation. The sample intentionally permits a bounded
envelope to reach the home so independent clients can test negative inputs and
version negotiation. Unknown marks, guessed result paths, private scries and
owner operations are outside this API and confer no access.

The package is not an application installation or a production release channel.

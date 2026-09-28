# Independent SDK consumer qualification

The executable candidate is `make sdk-dev SDK_ARCHIVE=<verified archive>`.
It is implemented for guarded local qualification; native compilation and the
complete conformance run are still unexecuted. This document is not acceptance.

## Current source and execution boundary

The runner verifies the public v3 package against its declared Git source and
prepares private, immutable input copies. It creates a fresh `~bus` consumer from
the pinned pill, runtime and kernel. Only the public desk, explicit fixed test
runners and three generic native framing/process helpers enter its filesystem.
No Home source, state, pier, seed, private client or host credentials enter it.
Package and runner inventories are checked against their expected hashes before
launch, inside the consumer, and at closure.

The public sample and all four carrier marks must compile. An otherwise matching
public-import generator must succeed while importing private `stead-core` must
fail for the actual missing dependency. The runner captures an absolute Clay
case, checks the installed bytes, and keeps that same fresh consumer alive.
Runtime calls compile the public sample at that immutable case, cast its full
vase to the pinned `thread:spider` type and invoke that gate with the public
arguments. This preserves the sample's captured subject. The current invocation
wrapper is checked before every call; current and captured installed files are
read back at closure.

Only after compilation and isolation controls does the trusted controller boot a
separate fresh synthetic `~zod` Home. It installs the actual bound product desk,
including assets, and executes the unchanged owner-local configuration and
bootstrap exchange. It never restores Home state or restarts either identity.
This native-only profile does not substitute for configured browser/TLS or
cold-restart qualification.

The consumer has separate user, mount, PID and network namespaces. Both sides
have loopback only. A private controller socket carries bounded framed results
and fixed-peer UDP datagrams. The relay exposes exactly the fake Ames pair
31337/31519 and accepts packets only from its expected owned local native port;
it cannot forward TCP, arbitrary addresses, HTTP, Lens or filesystem sockets.
Live TCP and abstract-socket controls, absent filesystem paths and namespace
identities are recorded. A numeric port occupied by the consumer's own Lens is
not evidence that Home's different network namespace is reachable.

One existing foreground thermal/cgroup guardian owns both namespaces and all
children. The independent lease watchdog remains active during blocking calls.
It closes admission and signals owned children after guard loss or unexpected
exit. Vere and evaluator children have parent-death binding, no capabilities and
no-new-privileges. Shutdown attempts are independent; failed cleanup remains a
failure. The host retains the final owned-cgroup evidence. A run never qualifies
from exit status or a compiler message alone.

## Running the candidate

Build the public package as described in [DEV_FLOW](DEV_FLOW.md#phase-2-sdk-package),
then use a stopped workstation fixture:

```sh
make sdk-dev SDK_ARCHIVE=.runtime/sdk/stead-sdk-v3.tar
```

Every attempt gets new `.runtime/sdk-builder-native-*` inputs and
`.runtime/sdk-consumer-*` private evidence; partial runs are preserved, never
reused as seeds. The 75°C startup and 90°C stop limits, one-heavy-run lock, 50%
CPU quota and pinned CPU remain unchanged. The profile requires no purchased
identity, remote server or host configuration changes.

The finite cases cover real capabilities/version negotiation, allowed Work
creation/readback, denied existing scope, exact duplicate receipt, altered
request reuse, revision conflict, malformed/oversized client input, native
malformed envelope, watch cancellation/resume, delayed/replayed cursors and
revocation before queued delivery. Closed validators require exact public
response shapes and receipt correlation. A normalized unconfirmed SDK outcome
is never counted as an authoritative business denial; subsequent reads verify
that negative inputs did not mutate accepted state.

Report package/source/toolchain hashes, installed and invoked source, actual
consumer identity, correlation, observations, negative controls and cleanup.
Separate real native execution from the host socket and synthetic corrupted-reply
controls. Source review is not compiler or runtime evidence.

## Earlier transfer preparation

The earlier five-jammed-artifact builder/loader proposal was never executed.
Its prepared `build.hoon`, artifact reader, staged metadata parser and host tests
remain in the repository with their original unexecuted status. They are not
called by this qualification lane and are not needed by the governing Phase 2
public-package consumer gate. The current same-consumer lifecycle avoids that
additional transfer boundary while preserving independent compilation and exact
public-source custody. Historical preparation receipts do not prove this lane.

Pinned interfaces are in kernel commit
`5a187fededc4582a34fcd6055c67bb63e0917b94`: `lib/strandio.hoon` supplies
`get-beak`, `build-file-hard` and `build-mark`; `app/spider.hoon` supplies the
full-vase thread cast/slam example; `sys/vane/khan.hoon` supplies the `%fyrd`
unit-input convention. Actual native compilation is still required.

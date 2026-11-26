# Native app integrator quickstart

Before adding product interfaces, read the
[experience contract](../PRODUCT_EXPERIENCE_CONTRACT.md) and
[current handoff](../AGENT_HANDOFF.md). Existing SDK exports below retain their
versioned meaning; owner/worker/run, independent repositories and separate Work
contract revisions require reviewed successors rather than silent API changes.

Use the separately versioned [SDK v3](../../../sdk/v3/README.md) for configured
team homes. SDK v2 remains the legacy fixture interface. The package is a
developer fragment, not an application installation or deployment credential.

For SDK v3 0.2.0-alpha with the Work discussion exports, use a clean checkout of
package commit `12c92797b8cf60ed663b2edc2b71a3d1c46b3732`. Its export lock
identifies native source `4ef41f5bb6a94976c46e1bff5220f256c828ef30`.
From the package checkout, build and verify the archive.

```sh
mkdir -p .runtime
python3 scripts/package_sdk_v3.py build --archive .runtime/stead-sdk-v3.tar
python3 scripts/package_sdk_v3.py verify --archive .runtime/stead-sdk-v3.tar
python3 scripts/check_sdk_source.py --archive .runtime/stead-sdk-v3.tar
```

The parent directory must already exist and build refuses to overwrite an
archive. Verification checks package bytes, not a publisher signature or native
compatibility. The source check also requires the declared commit in the local
Git object store and matches each public export and the toolchain lock to its
exact regular Git blob; it does not fetch missing history. Use the native consumer
evidence associated with that exact source, archive and Kelvin/runtime pair.
Git must support `--no-lazy-fetch`;
older Git versions fail closed instead of attempting to retrieve missing objects.
Use a reviewed local repository: this check suppresses default global/system Git
configuration, but repository/worktree configuration and explicit includes still
apply. It is not a sandbox for arbitrary Git metadata.

Install only the exported fragment and its declared pinned kernel dependencies
in the client development desk. The operator supplies your own home, binding ID
and binding revision. The sample derives the actual native sender; it does not
accept an actor or administrator flag. Obtain explicit project permission from
the home. A transport subscription or successful ACK is not a business grant.

Start with an authorized query. For a mutation, retain the exact command,
request ID, canonical digest, project/resource scope, expected revision and
authority epoch until its outcome is confirmed. Validate a returned receipt's
protocol, request, digest, scope, identity and revision before reporting Saved.
On an uncertain result, recover the original receipt or explicitly retry that
same command. Do not invent a new request ID to conceal a timeout or replay a
mutation automatically after reconnect.

Open an update stream before reading its snapshot. Poll with fresh request IDs,
consume opaque cursors once, and reread authorized state after invalidation.
Cancel unused streams. Refresh on a stale handle or overflow; a cursor is not
permission and cannot move between actors, scopes or purposes. Revocation,
binding changes and restart require new authorization and handles.

Exercise a denied scope and malformed/unsupported input alongside successful
calls. Never import home implementation libraries to make a client compile,
invoke owner controls from an employee app, expose raw diagnostic tangs, or
normalize Git identities. Keep the full source and observed result with your
integration evidence.

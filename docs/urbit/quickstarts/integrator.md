# Native app integrator quickstart

Use the separately versioned [SDK v3](../../../sdk/v3/README.md) for configured
team homes. SDK v2 remains the legacy fixture interface. The package is a
developer fragment, not an application installation or deployment credential.

Obtain a reviewed source checkout and its matching export lock. Build and verify
the exact archive using the pinned package command:

```sh
python3 scripts/package_sdk_v3.py build --archive .runtime/stead-sdk-v3.tar
python3 scripts/package_sdk_v3.py verify --archive .runtime/stead-sdk-v3.tar
```

The parent directory must already exist and build refuses to overwrite an
archive. Verification checks package bytes, not a publisher signature or native
compatibility. Use the native consumer evidence associated with that exact
source, archive and Kelvin/runtime pair.

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

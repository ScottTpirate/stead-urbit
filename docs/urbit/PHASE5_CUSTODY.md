# Phase 5 custody and Home handoff

The local profile has two distinct tools. A project replica is a read-only
copy of current shared Work and Docs. A Home handoff moves a stopped pier
with its existing ship identity. It preserves project IDs, history and
authority epochs, and advances the separate Home handoff generation.

## Grant and check a shared project replica

Use a dedicated member with an explicit reader grant on one project and no
private containers. Decide who may retain the copy and for how long before
transferring the archive. Store it in the approved custody boundary, with
private filesystem permissions and encryption at rest. The owner can capture
one version using the [portable export](PORTABLE_RECOVERY_PROFILE.md).

The custody approver prepares a private JSON grant for those exact bytes and
sends its SHA-256 through the approved authenticated channel. Use these fields:

```json
{
  "protocol": "stead.replica-grant/1",
  "scope": "shared-work-docs",
  "custodian": "approved-replica-name",
  "home": "~zod",
  "origin": "https://stead.example",
  "project_id": "<capture.json project_id>",
  "principal_id": "<capture.json identity.principal_id>",
  "authority_epoch": "<capture.json authority_epoch>",
  "generation": "<capture.json generation>",
  "artifact_sha256": "<whole archive SHA-256>",
  "expires_at": "<UTC ISO 8601, within seven days of capture>"
}
```

Run from this checkout:

```sh
python3 scripts/urbit/project_replica.py shared.zip \
  --grant grant.json --grant-sha256 "$APPROVED_GRANT_SHA256" \
  --custodian approved-replica-name
```

Add `--read index.json` or select a listed Work or Docs path. An online
freshness check takes `--session-file` for the original reader at the exact
source origin. It rechecks the authenticated project view and denies reads
when that view has changed or access is gone. With no connection the status
is `offline-unchecked` until expiry. Issue a new grant for a refreshed copy.
Expiry limits reads through the replica tool. The custodian must still delete
the raw archive and derivatives on revocation or expiry under its retention
policy. The archive contains no credentials, authority state, Code, or full
project history. Keep a separate verified backup for recovery.

## Same-identity handoff protocol

The owner-local Gall status path is `/home-handoff/status`. Its
`stead.home-handoff/1` response reports `home`, `phase` and `generation`.
The `%stead-home-handoff-1` mark accepts `[%seal CURRENT CHALLENGE]` and
`[%activate SEALED_GENERATION TICKET]`. Challenge and ticket are lower-case
64-digit hex strings. Generate the ticket in a private operator process using
32 bytes of cryptographic randomness and deliver it only to the target.
For seal, compute SHA-256 over these exact UTF-8 bytes:

```text
stead.home-handoff/1<NUL>~ship-name/NEXT_GENERATION/LOWERCASE_HEX_TICKET
```

Sealing advances the generation once, invalidates the current browser and
Git access and blocks all product commands, including configuration and
bootstrap. Existing upload evidence stays on disk, but deferred finalization
cannot proceed. Observe the sealed status before stopping the source.

1. Close the public routes, seal the Home and confirm its next generation.
2. Stop and disable the source service. Independently verify retirement and
   make an encrypted, digest-verified copy of the sealed stopped pier. Retain
   one protected copy for recovery. Keep the old host unable to start or
   publish this identity.
3. Start only the verified destination copy behind closed public routes.
   Confirm the same ship and sealed generation after saved-state replay.
   Deliver the ticket privately to the destination owner process. Avoid Dojo
   command history, process arguments, and logs for the plaintext ticket.
4. Verify open status at that generation, then complete fresh owner bootstrap
   and authorized readbacks. Open the reviewed routes only after the complete
   runtime and source-fence checks pass. If either host's writer status is
   uncertain, keep traffic closed and preserve both records for review.

The Home validates the ticket and generation. The operator and the host's
service/network controls enforce exclusive custody of the pier and ticket.
Both copies of the same ship would accept the ticket if it were delivered to
both. Older backups lack the new fence. This is a planned handoff, with no
automatic failover or election. Moving a single project to a different ship
requires a separately qualified project snapshot and journal protocol that
preserves attribution, permanently retires the old authority and advances
the project epoch. The [cross-ship evidence verifier](CROSS_SHIP_PROJECT_MIGRATION.md)
checks the signed candidate for that move. Native transfer and activation
are separate qualification steps.

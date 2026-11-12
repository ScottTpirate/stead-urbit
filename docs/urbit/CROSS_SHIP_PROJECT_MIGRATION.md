# First cross-ship project handoff

The offline verifier checks the evidence for moving a project from its original
Home at authority epoch 1 to a different ship and origin at epoch 2 within the
same custody boundary. It returns a candidate directory entry with a distinct
protocol, `stead.project-directory-candidate/1`. Home provides the native
source fence and frozen journal export. Project snapshot export, destination replay, and activation still
need implementation and qualification.

## Retire the source project

Use the existing owner-local Khan connection to read the source project status
with `project-retirement-status --project PROJECT_ID`. Select the move ID and
the destination ship after reviewing the current epoch and journal head.
Submit `project-retire --intent-file INTENT_JSON` with those exact values. The
Gall event compares the
epoch and the current Work/Docs journal head before it records the permanent
project fence. A retry of the same intent preserves the first retirement record.
A competing move fails.

Read back `writer_state=retired` through the same owner-local connection. The
native status contains the source, project, migration, destination, epoch,
journal head and retirement timestamp. Save the compact, sorted CLI JSON
without its final newline as the source observation. Keep it private. Prepare
the Work/Docs and Code snapshot after observing retirement so it includes any
Code commits accepted before the fence. Pending upload jobs confer no write
authority and their finalization is denied after retirement.

Export the frozen Work/Docs journal through the same owner-local connection
with `project-journal-export --intent-file INTENT_JSON --output PRIVATE_DIR/journal.ndjson`.
Use the retirement intent from the preceding step and an owner-only directory.
The command verifies the full original journal and reads the same retirement
record again before publishing a new mode-0600 file. Its JSON result supplies
the exact journal digest, record count and head for the signed transfer. The
Work/Docs and Code snapshots remain separate inputs.

Current membership and project authorization still govern reads on the source.
The source can revoke an identity binding, and authorized readers can obtain
read-only Git credentials. Project grants, Work, Docs and accepted Code state are frozen.
Keep older backups isolated, and stop serving the old Home's project after the
destination takes over so it cannot become a stale access path.

## Evidence and signatures

Use the active directory record and trust pins acquired independently of the
transfer. The trust file pins the exact current directory SHA-256, the two
distinct operator public keys, and the approved destination ship and origin.
Keep all evidence private to the approved custody boundary. Pass owned regular
files with mode `0600` to the verifier.

| File | Required format |
| --- | --- |
| Current directory | `stead.project-directory/1` with `protocol`, `project_id`, `custody_id`, `home`, `origin`, and `authority_epoch`. |
| Trust pins | `stead.project-handoff-trust/1` with `protocol`, `current_directory_sha256`, `source_ed25519`, `destination_ed25519`, `destination_home`, and `destination_origin`. Public keys are the lowercase hex encoding of the 32-byte Ed25519 public keys. |
| Signed transfer | `transfer`, `source_signature`, and `destination_signature`. The `transfer` object contains `protocol` (`stead.project-handoff/1`), `migration_id`, `project_id`, `custody_id`, `prior_directory_sha256`, `destination_home`, `destination_origin`, `destination_epoch`, `snapshot_sha256`, `journal_sha256`, `journal_count`, `journal_head`, `source_fence_sha256`, and `destination_readback_sha256`. |
| Journal | One exact native `stead.journal/3` record per line, ordered from sequence 1 with a trailing LF. Hash each row without the LF for the chain and hash the whole file including the LFs for `journal_sha256`. |
| Snapshot | Exact opaque bytes of the proposed project snapshot. The verifier checks the byte hash. The native importer must verify its format and contents before any activation. |
| Source fence and destination readback | Canonical records containing `protocol`, `migration_id`, `project_id`, `home`, `authority_epoch`, `journal_head`, `snapshot_sha256`, `observation_sha256`, and `writer_state`. Use `stead.project-source-fence/1` with state `retired` and `stead.project-destination-readback/1` with state `write-disabled`. |
| Observations | The source is the exact native `stead.project-retirement-status/1` response. The destination is the exact private report of isolated, write-disabled readback and matching project evidence. |

The JSON files use [Stead canonical JSON](CONTRACTS.md#limits-and-serialization)
without a trailing LF. Use lowercase SHA-256 hex and UUIDv7 values for project,
custody, and migration IDs. Each operator signs the same `transfer` object in
their own role, with this exact Ed25519 message:

```text
stead.project-handoff/1<NUL>source<NUL><canonical transfer bytes>
stead.project-handoff/1<NUL>destination<NUL><canonical transfer bytes>
```

Write each 64-byte signature as lowercase hex in the envelope. Operators must
check their own evidence before signing. The verifier authenticates the
operators' statements and binds the original reports. Proof that the hosts
actually enforced those states comes from the native and operational checks.

```sh
python3 scripts/urbit/project_migration.py \
  --directory directory.json --trust trust.json --signed handoff.json \
  --journal journal.ndjson --snapshot snapshot.bin \
  --source-fence source-fence.json --source-observation source-report.json \
  --destination-readback destination-readback.json --destination-observation target-report.json
```

The verifier uses OpenSSL Ed25519 verification and bounds the journal to
6,144 rows and 64 MiB, the snapshot to 256 MiB, the source observation to
4 KiB and the destination observation to 1 MiB.
It checks the native journal link, command and acceptance-receipt hashes, stable
binding ownership, actor revision continuity, attribution, time ordering, and
duplicate request scope. The journal stays in the original authority epoch and
original Home context. This is an
integrity check of the supplied history. Native replay still has to check each
business transition, every receipt, and the final application state.

## Native activation boundary

1. Retire the selected project, capture its frozen snapshot and verify the
   signed evidence. Verify that normal reload preserves the fence and protect
   older backups behind the operational startup fence.
2. Rebuild the old project in isolation using its historical Home, policy,
   binding, and epoch context. Verify Work, Docs revisions and Git objects, Code
   refs and accepted receipts, grants, and any state outside the Work/Docs
   journal. Keep its accepted records and stable principal IDs intact. The
   destination needs its own current bindings and fresh sessions. The existing
   saved-state replayer expects historical actors to match the configured Home,
   so using it unchanged on the destination would fail this transfer.
3. Verify the signed candidate against the current directory digest and both
   reports. Commit exactly one destination authority for the new epoch under a
   compare-and-swap against the old directory. The destination must stay
   write-disabled until it has durably recorded the exact move. Treat repeated
   submissions for the same move idempotently and reject competing moves.
4. Confirm that old-epoch commands, Git credentials and sessions fail on the
   destination before receipt lookup or effect execution. Verify the old Home
   stays retired on restart and that the destination returns unchanged original
   receipts and OIDs through authorized readback. Keep this directory private
   to the project's approved audience.

The same-identity move continues to use the separate Home handoff protocol.
[Same-identity handoff](PHASE5_CUSTODY.md)

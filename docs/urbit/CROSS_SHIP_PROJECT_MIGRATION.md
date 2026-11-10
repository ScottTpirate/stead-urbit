# First cross-ship project handoff

The offline verifier checks the evidence for moving a project from its original
Home at authority epoch 1 to a different ship and origin at epoch 2 within the
same custody boundary. It returns a candidate directory entry with a distinct
protocol, `stead.project-directory-candidate/1`. The native source fence,
project snapshot export, destination replay, and activation are separate steps
that still need implementation and qualification.

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
| Observations | Exact private reports reviewed by the signing operators. The source report describes how the old authority was fenced. The destination report describes the isolated, write-disabled readback and the matching project evidence. |

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
6,144 rows and 64 MiB, the snapshot to 256 MiB, and each observation to 1 MiB.
It checks the native journal link, command and acceptance-receipt hashes, stable
binding ownership, actor revision continuity, attribution, time ordering, and
duplicate request scope. The journal stays in the original authority epoch and
original Home context. This is an
integrity check of the supplied history. Native replay still has to check each
business transition, every receipt, and the final application state.

## Native activation boundary

1. Add a durable source retirement transition for the selected project. The
   source must close every write route for the project, drain in-flight writes,
   and retain the final journal tip and state checkpoint. Verify that normal
   reload and recovery cannot reopen the retired writer. Protect older backups
   behind an operational startup fence.
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

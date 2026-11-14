# Paired Home and Git pack recovery binding

`scripts/urbit/paired_recovery.py` verifies that a retained Home checkpoint
artifact and one original Git pack match a separately trusted operator capture.
It is an offline integrity check. It does not start a ship, decrypt a backup,
copy a pier, run Git, acquire authority, or activate a destination.

The existing [Home handoff](PHASE5_CUSTODY.md) and immutable pack restore tools
cover different artifacts. A pack alone omits the Home's Work, Docs, grants,
reviews, accepted ledger and handoff fence. A Home checkpoint alone does not
retain the external worker's immutable pack. This binding records their exact
relationship without changing either restore procedure.

## Trusted capture prerequisite

An authorized operator must establish the capture before using this tool:

1. Close mutation routes and drain accepted writes. Observe the final selected
   pack through the existing authenticated `pack-view` response. Keep its
   complete response, including acceptance request and time.
2. Seal the Home and observe `stead.home-handoff/1` with phase `sealed` and the
   next handoff generation. Reconcile any uncertain command result. Confirm
   through owner-controlled inspection that the saved selection is the one
   recorded above; a read taken before an intervening write is insufficient.
3. Record the exact Home source commit, saved-state version, and authoritative
   durable-state fingerprint for this sealed state. The fingerprint definition
   is the versioned extraction in `review_prepare.durable_fingerprint`; it
   includes the handoff, external ledger and review boards where present and
   excludes the rebuildable projection. Do not use a whole-vase or file digest
   in its place.
4. Stop the source and independently establish exclusive custody as required
   by the handoff procedure. Produce the protected checkpoint artifact and
   record its exact SHA-256 and length. If encrypted, these are the ciphertext
   bytes; no key or handoff ticket belongs in capture or binding JSON.
5. Retain the selected canonical `snapshot.json` and original `objects.pack`.
   Prepare the capture below and retain its SHA-256 through a trusted channel
   independent of these files.

The tool cannot infer these observations from opaque checkpoint bytes. The
trusted capture is an operator evidence assertion, not a native signature.
Someone able to replace both evidence and its independently trusted digest
can assert a different history. Building a binding does not independently
authenticate that history or prove the recorded source is currently retired.

## Capture shape

Use the following exact fields. `handoff` is the unchanged JSON object from
the existing owner-local status operation. `selection` is the unchanged JSON
object from the existing native `pack-view` operation; `refs` remains its JSON
string of hex-encoded ref names and original SHA-1 OIDs. The tool accepts the
capture's original whitespace and retains its complete UTF-8 bytes verbatim.
The values below are placeholders, not evidence.

```json
{
  "protocol": "stead.home-pack-capture/1",
  "capture_id": "<UUIDv7>",
  "source_commit": "<40 lowercase hex digits>",
  "saved_state": {
    "version": 9,
    "durable_sha256": "<64 lowercase hex digits>"
  },
  "checkpoint": {
    "sha256": "<64 lowercase hex digits>",
    "bytes": 12345
  },
  "handoff": {
    "protocol": "stead.home-handoff/1",
    "home": "~zod",
    "phase": "sealed",
    "generation": "2"
  },
  "scope": {
    "home": "~zod",
    "project_id": "<project UUIDv7>",
    "repository_id": "<same project UUIDv7>",
    "authority_epoch": "1"
  },
  "selection": {
    "protocol": "stead.code/1",
    "status": "external",
    "snapshot": "<SHA-256 of exact canonical snapshot.json>",
    "authority_epoch": "1",
    "object_count": "3",
    "head": "726566732f68656164732f6d61696e",
    "refs": "{\"726566732f68656164732f6d61696e\":\"<40 lowercase hex digits>\"}",
    "request_id": "<accepted request UUIDv7>",
    "accepted_at_ms": "<positive decimal milliseconds>"
  }
}
```

Versions 7, 8 and 9 are accepted: they retain accepted pack state. The Home
handoff generation is distinct from the project authority epoch and Git
ledger generation. Updated native responses may also include `generation` in
`selection`; preserve it as the original unsigned decimal string. The optional
`generation_limit` requires that generation and must be positive and at least
as large. Both are validated and bound when present. A capture does not invent them for
older responses, including the qualified `caaa85e` fixture.

## Build and verify

All input files and their immediate directories must be private and owned by
the verifier's user. Ancestor symlinks, leaf symlinks, hard links and special
files are rejected. The builder requires the independently trusted capture
digest and creates an absent output; it never overwrites a previous binding.
It syncs a private temporary file before publishing the final name. A directory
sync failure after publication retains the complete file for inspection and
does not emit a success report.

```sh
python3 -B scripts/urbit/paired_recovery.py build \
  --evidence /private/capture.json --evidence-sha256 "$CAPTURE_SHA256" \
  --checkpoint /private/sealed-home.enc \
  --snapshot /private/snapshot.json --pack /private/objects.pack \
  --output /private/paired-binding.json

python3 -B scripts/urbit/paired_recovery.py verify \
  --binding /private/paired-binding.json --sha256 "$BINDING_SHA256" \
  --checkpoint /private/sealed-home.enc \
  --snapshot /private/snapshot.json --pack /private/objects.pack
```

Retain `BINDING_SHA256` independently before relying on a restored copy. The
binding contains the original capture bytes and complete canonical snapshot
manifest. Verification compares the Home, project, epoch, selected snapshot,
refs, HEAD and object count, then streams both artifact hashes. It also checks
the pack header and declared object count. This is not an `index-pack` or
`fsck` check. Inputs remain open until final inode, path, size and change-time
checks complete. A failure preserves the inputs and emits no successful report.

Limits are one project, one checkpoint of at most 1 GiB, one pack of at most
64 MiB, a 384 KiB capture, a 1 MiB binding, the existing pack/ref/object limits,
and a 60-second verification deadline. Hashing reads at most 64 KiB at a time;
no checkpoint or pack is buffered in memory. A large checkpoint still costs
disk I/O and hashing time, so schedule it outside an active guarded native
run. A successful report explicitly leaves native replay, decryption, source
retirement, Git object verification and fresh-host qualification false.

## Remaining fresh-host qualification

The 16 focused host tests use tiny synthetic files and mock no native restore.
They do not establish that a retained real checkpoint is sealed or bootable.
To qualify a paired restore on an independently prepared fresh host:

- Preserve the originals and independently fence the original identity and
  service. Keep destination public routes closed throughout verification.
- Transfer the encrypted checkpoint and pack through the approved custody
  boundary, verify the independently retained binding digest, and decrypt with
  separately controlled keys. Boot only the permitted destination copy.
- Replay the exact supported Home source and pinned runtime. Observe the same
  sealed handoff generation, authoritative durable fingerprint, selected pack,
  acceptance receipt, project epoch, Work/Docs state and review/ledger history.
- Use the pinned stock Git restore verifier against the paired manifest and
  pack. Verify original refs/OIDs, reachable object inventory, strict `fsck`,
  and a fresh clone with the source store unavailable.
- Activate using the existing private ticket protocol only after retirement
  and sealed replay are proven. Obtain fresh owner bootstrap and sessions;
  prove old access is rejected and duplicate requests do not repeat effects.
- Record recovery duration, loss window, exact input/source/toolchain hashes,
  negative mismatch cases, and cleanup. Have an independent reviewer check the
  observed result before changing the recovery gate.

No such fresh-host qualification is implied by a binding or by the separate
accepted-pack encrypted restore rehearsal.

## Bounded local checkpoint helpers

`scripts/urbit/checkpoint_archive.py` supplies the local rehearsal's exact-tree
archive and encryption operations. `archive_tree` includes every regular file
and retained Clay mount; `extract_tree` rejects traversal, duplicate names,
links, devices, sparse/PAX entries and nonzero trailing payloads. Extraction
uses fixed 512-byte USTAR headers and rejects extensions before any
extension-sized read or library-parser allocation. The destination
tree must match the independently retained checkpoint fingerprint before its
new name is published. Existing destinations are never replaced. Failed
extraction leaves an unpublished private scratch tree for inspection.

The checkpoint helper now accepts an explicit `maximum_files` profile up to
32,768. Its default remains 8,192. The larger profile keeps the existing 4,096
directory, 512-MiB individual-file and 1-GiB tree-byte limits; no mount or alias
is silently omitted. The archive profile reserves header space and limits tar
bytes to 960 MiB and ciphertext to 1 GiB.

`crypt_file` streams through a separately pinned installed GnuPG executable,
with AES256-OCB selected explicitly. Its caller supplies a fresh random 32-byte
synthetic key encoded as 64 lowercase hex digits plus newline in a private file.
The passphrase is passed only on an inherited descriptor. GnuPG uses a temporary
private home, no agent autostart, no external key lookup and no compression.
The wrapper accepts decrypt output only after GnuPG reports the exact AEAD
profile and successful authentication; legacy MDC ciphertext is refused.
Plaintext remains private and unpublished until that check finishes. No Python
cryptographic primitive is implemented. The wrapper caps process address space
at 512 MiB, CPU at 90 seconds, output size at 1 GiB, status output at 64 KiB and
wall time at 120 seconds. Large runs still require the ordinary execution guard.

Eight focused tests executed against installed GnuPG 2.4.9 cover a tiny AEAD
roundtrip and exact restore, corrupt ciphertext, wrong key, wrong executable
pin, legacy-profile rejection, archive attacks and create-only publication.
Five additional checkpoint-profile tests cover explicit bounds, exact alias
copies and hostile filesystem entries; the ten existing checkpoint tests still
pass. These are host tests, not evidence of an executed paired native restore.

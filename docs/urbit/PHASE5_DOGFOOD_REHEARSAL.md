# Stead Git dogfooding rehearsal

GitHub is the writable source of truth during local qualification and the live
synthetic pilot. The local rehearsal copies explicitly pinned branch and tag
refs into private bare Git repositories. It publishes a test fast-forward from
the local authority to the local mirror, stops on an independent mirror write,
then removes both temporary repositories and restores the accepted refs from a
Git bundle. Stock Git verifies both the refs and object graph.

## Run against a pinned checkout

From the Stead Urbit checkout, use a new directory under `.runtime`. Choose the
branch and tag refs that belong to the pilot and pin their reviewed OIDs. The
script accepts local filesystem paths and enables only Git's file transport.

```sh
run_dir=$(mktemp -d .runtime/dogfood-XXXXXXXX)
python3 -B scripts/urbit/dogfood_rehearsal.py . "$run_dir/git" \
  --git .runtime/tooling/git-2.55.0/bin/git \
  --ref refs/heads/main=2a833c29199aa863ea2d7d751ec26355623cbab2 \
  --ref refs/tags/runtime-v4.6-newt-c0a35c6=825aebf719d1fd99bfc51457cc023ce36edda089
```

`source.bundle` holds the exact pinned source refs. `rehearsal.bundle` holds the
same history plus the two local test commits. `report.json` binds each bundle's
digest to the observed refs and reachable object inventory. Keep the digest
with the approved backup record. To recover with stock Git, verify the bundle
digest, initialize an empty bare SHA-1 repository, run `git bundle verify`, and
fetch the listed branch and tag refs from the bundle. Set `HEAD` to the reported
default branch. Run `git fsck --full --strict` and compare the recovered refs
with the report. Use `source.bundle` to recover the pinned source before the
rehearsal commits. Git bundles carry reachable Git history. Back up Stead's
application records and authority separately using its recovery procedure.

## Observed local evidence

Git 2.55.0 rehearsed `2a833c29199aa863ea2d7d751ec26355623cbab2` and the pinned
runtime tag. The source bundle held 7,701 reachable objects with 148,825,267
uncompressed bytes and a largest object of 10,631,081 bytes. The simulated
mirror advanced from `2a833c2` to `b9d4e85` and preserved the unexpected
`875733d` when the authority tried to publish `9c23a9a`. Recovery retained the
tag, restored `9c23a9a`, and matched all 7,703 reachable object IDs from the
temporary authority. The private report at
`.runtime/dogfood-20261110-74yr63ry/git/report.json` had SHA-256
`3ce4a33628b375c04daeb3bb9aef417fa6c1b082ed8000524a5f278e5a2a3e38`.

The current native profile supports 64 objects and 262,144 total object bytes
per Code repository. Its portable Code archive supports 512 objects and 8 MiB
of combined body bytes. This rehearsal exercises local Git recovery and an
atomic leased mirror push. Full history hosted by the native Home, GitHub
rules, and live mirroring require separate qualification. [Native store](../../native/core/desk/lib/stead-code-store.hoon)
· [Portable Code](PORTABLE_CODE.md)

## External pack storage

The private pack store stages a complete SHA-1 pack for the exact pinned branch
and tag refs. It uses stock Git to validate the pack in a fresh bare repository,
compares the complete reachable object set, and runs strict `fsck` before
publishing the pack and manifest together. The manifest binds the Home ship,
project, repository, epoch, object format, default branch, refs, pack SHA-256 and
object inventory. Snapshot IDs are SHA-256 hashes of canonical manifests.

Use a private directory on Linux and a complete authorized checkout. Pin the
desired OIDs before generating the pack. The commands below stage only `main`.
To include tags, add each exact tag OID to `roots` and pass another `--ref-hex`.

```sh
umask 077
run_dir=$(mktemp -d .runtime/pack-store-XXXXXXXX)
mkdir "$run_dir/store"
git_bin=.runtime/tooling/git-2.55.0/bin/git
main_oid=$("$git_bin" rev-parse --verify refs/heads/main)
main_hex=726566732f68656164732f6d61696e
printf '%s\n' "$main_oid" > "$run_dir/roots"
"$git_bin" pack-objects --threads=1 --stdout --revs --delta-base-offset \
  < "$run_dir/roots" > "$run_dir/source.pack"
read -r pack_digest unused_path < <(sha256sum "$run_dir/source.pack")
scope=(--home '~zod' --project "$PROJECT_ID" --repository "$REPOSITORY_ID" --epoch 1)
python3 -B scripts/urbit/git_pack_store.py stage "$run_dir/store" "$run_dir/source.pack" \
  --git "$git_bin" --sha256 "$pack_digest" --head-hex "$main_hex" \
  --ref-hex "$main_hex=$main_oid" "${scope[@]}" > "$run_dir/stage.json"
```

The custodian retains the approved snapshot digest separately. Restore into a
new private directory using that digest and the exact scope.

```sh
python3 -B scripts/urbit/git_pack_store.py restore "$run_dir/store" "$run_dir/restored.git" \
  --git "$git_bin" --snapshot "$APPROVED_SNAPSHOT_SHA256" "${scope[@]}"
```

The profile bounds each pack to 64 MiB, 16,384 objects, 16 MiB per object,
256 MiB of object bodies, and 64 branch or tag refs. Git subprocesses use
address space, file size, CPU time and wall-clock limits. Each Home and
repository scope holds up to eight snapshots. Custodians also need a filesystem
quota for the storage root and an approved retention policy.

An interrupted command can leave a `.code-restore-*` directory under the
repository store or restore destination's parent. Before clearing it, stop pack
jobs and verify that no stage or restore command is in flight. Hold the same
exclusive lock on the repository directory used by the pack store while
inspecting its entries. Confirm the scratch directory is owned by the operator
and inside the intended private parent, then move confirmed abandoned scratch
to private quarantine. Retain every snapshot named in an accepted Home receipt
or approved backup record.

The local run with pinned Git 2.55.0 staged exact `main`
`dd1f57f755484c0ed881ab3a5c53738a5bc8ca99` and the runtime tag. It restored
both refs and all 7,803 OIDs in an independent stock clone, which passed strict
`fsck`. Pack size was 24,842,161 bytes and decoded object bodies totaled
149,616,724 bytes. Snapshot SHA-256 was
`a031f96958f0bff2883087759d156e5e639146eff3602caff03d68b1597d09ef`.
The private evidence is in `.runtime/phase5-pack-store-BaJKt7aN`.

### Home acceptance boundary

The local tool produces a custody candidate. The native integration must bind
the durable manifest digest to a Home-owned proposal that also records the
current accepted snapshot, exact old and proposed ref OIDs, actor binding,
request ID and wire digest. The Home must authenticate validation results and
check current grants, epoch, old OIDs, branch protection, verified ancestry
and quota when accepting. It must commit the accepted digest, refs, journal
and receipt together. An interrupted attempt may leave a candidate for later
reconciliation. Git success follows the durable Home receipt.

Reads must resolve an exact accepted digest through current Home authorization
and expose only the permitted ref closure. Recovery selects the digest from an
independently trusted accepted checkpoint. Removal of accepted snapshots needs
Home-owned retention evidence. Native manifest anchoring, authenticated Git
transport, staged incremental push, and restore of the Home's application state
remain separate checks. [Source control contract](CODE_AGENT_SOURCE_CONTROL.md)

## After the synthetic pilot

1. Qualify the full current repository through the native Home. Compare exact
   refs and run stock clone, fetch, push, strict `fsck` and recovery, including
   a fresh host and the planned workload. A larger storage profile must keep
   ref acceptance and current authorization in the Home. A pack store may hold
   verified immutable objects under explicit custody and quotas.
2. With owner approval, stop GitHub source writes and capture the final refs.
   Import and verify those refs and the recovery copy before opening Stead for
   writes. Record the authority epoch and last mirrored OID of every ref.
3. Allow only the mirror identity to publish to GitHub after the transfer. Use
   explicit refs and expected previous OIDs. If any mirrored ref differs from
   the recorded snapshot, stop publication and review the difference as a
   proposal. Recover the Stead authority and verified backup before resuming
   writes after an outage. [Deployment procedure](PHASE5_DEPLOYMENT.md)

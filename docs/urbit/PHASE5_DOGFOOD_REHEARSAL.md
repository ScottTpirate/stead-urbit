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

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

The Home can anchor the first full-history snapshot of a project that has no
inline repository. The project and repository IDs are the same in this
profile. The pack custodian first verifies the exact retained object pack
and immutable manifest. The Home operator stages the verified attestation
through the owner-local Khan command from the [pilot runbook](PHASE5_DEPLOYMENT.md).
Keep the attestation and command output inside the project's private custody.

```sh
umask 077
python3 -B scripts/urbit/git_pack_store.py attest "$run_dir/store" \
  --git "$git_bin" --snapshot "$REVIEWED_SNAPSHOT_SHA256" "${scope[@]}" \
  > "$run_dir/attestation.json"
"${owner[@]}" pack-stage --attestation-file "$run_dir/attestation.json"
```

The Home recomputes the stock manifest digest from the canonical refs and
scope and records the candidate for 15 minutes. An authenticated project
maintainer opens **Code**, reviews the exact snapshot and refs, and selects
**Accept this snapshot**. The Home checks the current actor binding and grant,
authority epoch, candidate digest, and absence of an inline or accepted
repository. It saves the exact refs, manifest and receipt in one transition.
The same request ID replays the receipt only for the same current authorized
binding. The current external snapshot is immutable.

An authorized operator can read the accepted snapshot through the Home and
restore the matching private pack locally. Use the existing private session
file format from the [portable Code instructions](PORTABLE_CODE.md).

```sh
python3 -B scripts/urbit/git_pack_readback.py STORE PRIVATE_DEST \
  --project "$PROJECT_ID" --session-file "$SESSION_FILE" --git "$git_bin"
```

The helper compares the exact Home refs, default branch and object count with
the verified store. It rechecks the accepted snapshot and current authorization
after stock Git verification and before publishing the private clone. Use
`--ca-file` when the pilot Home uses an explicitly trusted private CA. Retain
accepted snapshots according to the Home receipt and backup records.

An external snapshot has a private restore workflow and a Git read worker.
The worker verifies the exact accepted object closure in a fresh private
repository, prepares a bounded stock `upload-pack` reply, and checks the same
Home decision again before disclosing any bytes. It never sends a receive-pack
result or edits accepted refs.

The read adapter accepts only the exact Smart HTTP discovery and fetch routes.
Its control call delegates authentication to the Home's Git credential check
on `/stead/git/<project>.git/stead-snapshot`. A separate ingress must enforce
TLS, request framing, timeouts and canonical routing before this adapter is
deployed. Each request currently verifies
the full pack; multi-client workload and fresh-host recovery require
qualification. Incremental push, protected refs, and live authority transfer
remain separate work. [Source control contract](CODE_AGENT_SOURCE_CONTROL.md)

### External push preparation

The offline preparation worker in `git_pack_push.py` takes an independently
selected Home snapshot, the SHA-256 of the original upload, and the client’s
ordered expected and proposed OIDs. It derives the entire proposed ref map,
then checks it against a verified complete pack. Stock Git confirms the
branch updates are fast-forwards. The worker refuses stale or repeated refs,
branch rewrites, tag replacement, deletion, and objects outside the proposed
ref closure. It stages a separate immutable candidate and never edits the
base. The result is not a push receipt or permission to publish.

A synthetic fast-forward against the 8,049-object `3ba8e43` history and the
unchanged runtime tag produced an 8,050-object staged candidate in 2.911
seconds on the test machine. An independent restore passed strict `fsck`.
This measurement covers preparation on one local host. Wire admission,
protected-branch review, concurrent Home acceptance, durable receipt and
full-history push recovery still require separate proof.

## Prepare GitHub issues for Work

Use `scripts/urbit/github_work_plan.py` to preview moving issues from
`ScottTpirate/stead-urbit` into Work. It reads a private local file and writes
one new private plan. Point it at a JSON array from GitHub's repository Issues
API or the array of paginated arrays emitted by `gh api --paginate --slurp`.
[GitHub Issues API](https://docs.github.com/en/rest/issues/issues#list-repository-issues)
· [GitHub CLI](https://cli.github.com/manual/gh_api)

If you need to make the export, run the first command with the appropriate
GitHub read access. The Python script runs entirely offline.

```sh
umask 077
run_dir=$(mktemp -d .runtime/github-work-XXXXXXXX)
gh api --hostname github.com --paginate --slurp \
  'repos/ScottTpirate/stead-urbit/issues?state=all&per_page=100' > "$run_dir/issues.json" &&
python3 -B scripts/urbit/github_work_plan.py "$run_dir/issues.json" \
  --output "$run_dir/work-plan.json"
```

The output reports the SHA-256 of the exact source and plan. It gives each
draft a source issue number and permalink and uses the existing `work.create`
payload fields. Open issues map to **To do**. Completed issues map to **Done**.
Issues closed as duplicates or not planned map to **Canceled**. Review the
suggested **Done** status for issues closed without a reason. Drafts default to
**Task** and no priority. Pull request numbers are listed separately. Original
issue descriptions keep their text and links, with carriage returns normalized
to line feeds. Issues beyond the Work title or description limits need manual
review using the source file. The plan lists the omitted metadata and history.

The tool checks the pinned repository and exact GitHub issue URLs and fails on
malformed rows or repeated issue numbers. The input is limited to 2,048 rows
and 16 MiB of JSON. A native project currently has room for 128 Work items total.
Review the intended destination and its remaining capacity before copying any
drafts into Work. This is a preview of the supplied GitHub rows. It creates no
Stead records and makes no changes to GitHub. Keep both files within the same
private custody as the issues.

The November 14 preview of the pinned GitHub repository produced 35 Work
drafts (20 To do), excluded 48 pull requests and reported no title or body
size exceptions. The data stayed in a private local rehearsal directory.

### Rehearse selected drafts on a disposable Home

Use a synthetic issue export and the existing [disposable Home session
format](PORTABLE_RECOVERY_PROFILE.md#local-create-only-import). The importer
connects only to numeric loopback and requires verified TLS for
`home.localhost`, the native `isolated-fake` runtime, and a current individual
project creator session. The session file and CA path below are for the
disposable Home.

```sh
common=(--source "$run_dir/issues.json" --preview "$run_dir/work-plan.json"
  --preview-sha256 "$REVIEWED_PREVIEW_SHA256" --target-home '~zod'
  --session-file "$LOCAL_SESSION_FILE" --ca-file "$LOCAL_CA_FILE")
python3 -B scripts/urbit/github_work_import.py plan "${common[@]}" \
  --project-key GHIMPORT --title 'GitHub import rehearsal' \
  --issue 2 --issue 9 --output "$run_dir/import-plan.json"
```

Replace the example issue numbers with the complete drafts you reviewed. The
new plan binds your selection and target to the exact preview and source
bytes. Review the project and selection in that plan, then use the project ID
and plan SHA-256 from the planning receipt. Create the progress directory once.

```sh
mkdir -m 700 "$run_dir/progress"
bound=(--plan "$run_dir/import-plan.json" --plan-sha256 "$REVIEWED_IMPORT_SHA256"
  --confirm-project "$REVIEWED_PROJECT_ID" --progress "$run_dir/progress")
python3 -B scripts/urbit/github_work_import.py apply "${common[@]}" "${bound[@]}"
python3 -B scripts/urbit/github_work_import.py verify "${common[@]}" "${bound[@]}"
```

Apply creates a new project and its selected Work items in batches of at most
16 commands. A `ready` result needs another batch. If a response is uncertain,
keep the same plan and progress, investigate and rerun `apply` explicitly to
retry the exact pending command. The importer matches native receipts to the
project, actor and inputs before proceeding. After `complete`, `verify` reads
back every Work item and refuses missing, changed or unexpected records. Fresh
sessions for the same binding can resume a plan. A changed binding or Home
requires a new rehearsal. Keep the disposable project under sole control until
verification completes.

A guarded run on two disposable fake ships passed 19 checks with actual native
member approval and HTTPS. It applied two invented issues in separate CLI
processes, verified exact Work readback, and replayed the completed plan without
creating a duplicate. The fixture also rejected the wrong target confirmation,
changed source bytes and overwrite of the prior preview. It removed the member
session and reaped both fakes. No GitHub issue was written to the pilot.
The private report `.runtime/github-import-native-hwhq451u/state/report.json`
has SHA-256 `5031fc201ea79eb46ec35ad092a9d110c20560faab0e9bcb3dc97e468a7eb571`.

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

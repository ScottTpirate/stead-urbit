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

The November 14 local rehearsal at `f82358e` preserved all 8,186 reachable
objects and both pinned refs through bundle restore, passed strict `fsck`, and
refused to overwrite a divergent mirror. Neither test switched GitHub authority.

The latest external pack rehearsal pinned `8c05529ad619f0f845111dcf3047374b0c650e8e`
and the same runtime tag. It staged a 25,142,488-byte pack with 8,931 reachable
objects, validated a stock-client update in a private candidate, and retained
all original objects through strict `fsck`. The source refs remained unchanged.
The five-check result is `.runtime/latest-native-pack-RmgHjU6b/pack/report.json`,
SHA-256 `bcb82067538e7b7865dba955702b8d5a9ff58aba84c9eece9a43dbee8b63d7ce`.
This host-side test ran separately from native Home acceptance.

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
repository scope holds up to 80 immutable snapshots. The Home allows up to
64 accepted pushes and protected-branch promotions together. Exact snapshot
retry still works at storage capacity. The extra storage slots allow staged
candidates. Custodians also need a filesystem quota for the storage root
and a retention policy. At the per-pack maximum, 80 copies can use 5 GiB
in each store before scratch or backup.

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
binding. Each pack snapshot is immutable.

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
deployed. Each request currently
verifies the full pack. Multi-client workload, the combined live service
path and separate-host recovery still need qualification. The local signed
push and protected-review rehearsals below cover native acceptance.
[Source control contract](CODE_AGENT_SOURCE_CONTROL.md)

### External push preparation

The offline preparation worker in `git_pack_push.py` takes an independently
selected Home snapshot, the SHA-256 of the original upload, and the client’s
ordered expected and proposed OIDs. It derives the entire proposed ref map,
then checks it against a verified complete pack. Stock Git confirms the
branch updates are fast-forwards. The worker refuses stale or repeated refs,
branch rewrites, tag replacement, deletion, and objects outside the proposed
ref closure. It stages a separate immutable candidate and never edits the
base. The result is not a push receipt or permission to publish.

`git_pack_receive.py` rehearses the preceding wire step. It takes the admitted
SHA-256 of an exact private stock `receive-pack` request, verifies the ordered
command block, and reconstructs the candidate with the selected immutable
base in a temporary Git repository. It supports bounded SHA-1 thin packs
whose missing bases belong to that snapshot. It rejects added objects outside
the proposed ref closure, then prepares the complete immutable candidate.
The preparation rehearsal captures ordinary stock push bytes and reports a
refusal. The private fake-ship push test below exercises Home acceptance.

Run `git_pack_rehearsal.py` with the same exact branch and tag pins as the
bundle rehearsal to capture a stock push and test the complete preparation
on a real-sized repository. It uses a new private directory under `.runtime`.
The test makes one synthetic commit and tag, verifies the worker proof,
restores the proposed pack and checks every original OID. Its loopback peer
explicitly refuses the push and leaves the source checkout unchanged.

At `c274604`, this rehearsal preserved all 8,233 original Git objects and
added only the intended commit and annotated tag. The stock client sent a
635-byte request for this small change. The pack restored with strict `fsck`.
The report `.runtime/full-wire-history-pxqxtegS/rehearsal/report.json` has
SHA-256 `d8838ce468fb32e573889e581bf9b28a45b9b9fe2daedbf278dbb494f15aaa6d`.

A synthetic fast-forward against the 8,049-object `3ba8e43` history and the
unchanged runtime tag produced an 8,050-object staged candidate in 2.911
seconds on the test machine. An independent restore passed strict `fsck`.
This measurement covers preparation on one local host. Wire admission,
protected-branch review, concurrent Home acceptance, durable receipt and
full-history push recovery still require separate proof.

The pure native ref reducer passed five tests under pinned Vere. It recomputes
the candidate ref map from the current accepted manifest, compares the scope,
generation and prior OIDs, and consults verified object facts and project
policy. The tests include a byte-exact non-UTF-8 ref, hidden ref changes and
direct protected updates. A candidate and an accepted receipt have separate
types. The reducer is not connected to a saved Home ledger or external push
route in that reducer-only run. Report `.runtime/pack-push-native-ELIcQOlt/state/report.json`, SHA-256
`cb6b464064f490d9061f78b49bfc284d2efeb2dbd363fe29fe77621a9a67b65b`.

### Private push adapter

The host adapter prepares a candidate with its private pack worker and gives
the Home the individual write credential for each transition. A positive Git
report requires a canonical Home receipt matching the admission, actor, exact
ordered ref changes and accepted snapshot. If the commit response is lost, the
adapter performs one read-only lookup with the original admission and proof.
The host transport test uses a simulated Home. The native admission builder
separately passed three pinned Vere tests, including a byte-for-byte
comparison with the worker's canonical format.

The guarded two-ship test connected stock Git over private loopback HTTPS to
a disposable Urbit Home. It passed 24 checks. A member pushed a branch and
annotated tag, and Git received a success report after recovering the exact
receipt from a deliberately lost commit reply. The Home refused a direct
default-branch push and then refused the revoked uploader's credential.
After restarting Home, a fresh member approval and mirror clone reproduced
the exact refs and 7,805 reachable IDs and passed strict `fsck`. Both ships
stopped cleanly. The Home enables this transport only on the isolated fake
profile. The live pilot still needs an authenticated worker deployment,
the protected-branch workflow exercised through its live ingress, and a
paired Home and pack restore on a fresh host.

| Evidence | SHA-256 |
|---|---|
| `.runtime/pack-push-stock-4x_848lf/state/report.json` | `f21e1b2f967ecf6c31e7c0b0fb94d9f2be524f8b41815a073b615d830d56bbd6` |
| `.runtime/execution-runs/pack-push-stock-po2qs3z8/report.json` | `234c21ed59d7b441d55d57f9643ef9bfd215e4d444691114f1429e7ed7d7fc3d` |

A fresh network-isolated process on the same machine restored a copied,
AES-256-GCM-encrypted backup of that accepted pack with the original store
unavailable. It rejected a modified ciphertext. The restore took 5.055
seconds and the independent bare clone took 1.628 seconds. Both matched all
four refs and 7,805 reachable IDs. Across the 13 checks, the workload took
8.953 seconds. The test covers Git pack recovery. Paired Home data, service
authority and second-host recovery have separate gates.

The private report `.runtime/accepted-pack-offline-4bd2ndop/state/report.json`
has SHA-256 `5fe563abbc6f6878b55abfa3cca17a6d113e85e3acd5b4598427ac8546466a16`.

### Protected default branch review

The native review preflight binds the Work item, author, exact proposal
revision, source branch tip, target OID and selected snapshot. It checks the
current author, reviewer and merger grants, requires the worker's exact
fast-forward evidence, and permits one ref change with the existing object
inventory. The seven pinned Vere tests cover exact selection, stale review,
changed grants and worker evidence.

In **Code**, a contributor links a Work item and proposes a source branch
already pushed to the repository. A different maintainer approves that exact
revision. The merge advances the default branch to the proposed commit, with
the same pack and other refs. Each role must still have access to the Work item
at merge time. A stale snapshot, a changed ref or a removed grant requires a
fresh review. Home saves the accepted proposal and Git snapshot in one
transition and returns the same receipt for an exact authorized retry.

Download the reviewed request from **Code**. Run the following on the Git
worker account, using its approved profile and owner-only directories. Copy
the request as a mode-0600 file. Import the resulting proof in **Code** and
select **Merge reviewed change**. Keep the worker key with the worker.

```sh
python3 -B scripts/urbit/git_pack_worker_service.py --profile "$WORKER_PROFILE" \
  --review-request "$PRIVATE_REQUEST" --review-output "$PRIVATE_PROOF" \
  --home "$HOME_SHIP" --project "$PROJECT_ID" --authority-epoch "$AUTHORITY_EPOCH"
```

The browser review picker supports UTF-8 branch names. Git storage also
preserves ref names with arbitrary valid Git bytes.

The private report `.runtime/pack-review-native-3l9marb8/state/report.json`
has SHA-256 `0d53445edac8022fa44b92f28d709df5e4bebda1e4715aa19ab7a146faf3b164`.

A separate 53-check journey used pinned Vere, stock Git, one disposable
Home and two distinct member ships. It exercised native browser-session
approval on both members, ordinary branch and annotated tag push with
recovered receipt, exact Work-linked proposal and approval, protected
default-branch promotion using real signed evidence, and exact review
receipt replay. The Home refused direct default-branch push, contributor
approval and modified proof bytes. After restart, the accepted Code view
and review receipt were present, and a fresh stock mirror clone matched all
7,805 reachable IDs and passed strict `fsck`. All three ships stopped
cleanly. This journey used a loopback fixture with the relay and worker in
one process. Distinct service accounts are qualified separately by the
projection tests.

The private report `.runtime/pack-reviewed-stock-woha7b4f/state/report.json`
has SHA-256 `2776f55b5d9e1d62400bbe77b0627b3b0cc4de61011a4463a9a0638f628bf5e1`.

### Worker result authentication

The worker signer and native verifier use Ed25519 for a fixed message that
names `stead.git-pack-worker-attestation/1`, the active key generation and
SHA-256 of the exact proof bytes. The proof also binds the Home admission,
including project, repository, authority epoch, Home incarnation and upload.
The native tests verified the cross-language signature and rejected key
generation drift, changed proof bytes, a weak public key and a noncanonical
scalar. The host tests exercised an independently verified OpenSSL signature.
The relay uses a scoped current key and a separate per-incarnation capability.
A guarded loopback test passed 31 checks using the real Home TLS carrier.
It covered default-closed startup, owner installation of a current relay pin,
read-only and wrong-capability denials, a signed stock-client push, exact
receipt recovery and revocation. Both ships stopped cleanly. A fresh clone
after restart matched all 7,805 reachable objects. The test invokes the real
signer in the relay process. The separate Unix worker service still needs
combined qualification with the native Home and the pilot ingress. The
three-account projection fixture independently exercised worker and relay
store isolation. Stock Git also cloned through nginx and the actual Gunicorn
relay against a synthetic TLS Home.
[Ed25519 specification](https://www.rfc-editor.org/rfc/rfc8032.html)

The private report `.runtime/pack-worker-signature-native-8fux4jc2/state/report.json`
has SHA-256 `c8c3adb7ac6eab9c5fdff21b9b6bf5449caeaf34a8cce03c508444906384661c`.
The relay report `.runtime/pack-relay-stock-xpy8xhqp/state/report.json` has
SHA-256 `84ef3c10bb54aead82d0ea950e530a3a61b9c8956bb1073910b19b765650c6c1`.

## Prepare GitHub issues for Work

Use `scripts/urbit/github_work_plan.py` to preview a GitHub repository’s issues as Work.
Pass `--repository owner/name` to select the source. The default is
`ScottTpirate/stead-urbit`. It reads a private local file and writes
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

The current preview preserves the source issue ID, number and permalink, reported
GitHub author, and creation, update and closure times when the export supplies
them. The Work description carries the source author and dates. Stead records
the member performing the import as its creator. Each private preview lists
the source assignees for manual mapping and the count of omitted comments when
available. A missing author or timestamp appears as `null` in the preview.
Keep a reviewed version 1 preview with its original source and progress when
resuming an earlier import. Rebuilding the preview would change its digest.

The tool checks the selected repository and exact GitHub issue URLs and fails on
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

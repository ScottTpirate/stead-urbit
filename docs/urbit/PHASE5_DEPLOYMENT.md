# Phase 5 deployment runbook

Use this sequence when the candidate passes local qualification and the owner
approves a synthetic live pilot. The present configured Home accepts only the
`local-disposable` custody and `isolated-fake` runtime profile. Live setup must
wait for a reviewed live profile and startup fence. A real ship must never
be labeled as a disposable fake to get through admission. [Home configuration
decoder](../../native/core/desk/lib/stead-team-config.hoon)

## Candidate admission

Keep a reviewed record of the exact Git commit and both role archives. For each
archive record its independently trusted SHA-256, its target JSON, its API and
saved-state versions, and the passing evidence for that payload. The target
includes the exact Kelvin, kernel commit, Vere binary SHA-256 and frontend
SHA-256. Use the pinned toolchain in the [packaging guide](RELEASE_PACKAGING.md).

On the verification machine, put the reviewed archive and target in a private
directory within the checkout. Use checkout-relative paths.

```sh
python3 -B scripts/package_release.py verify \
  --archive "$HOME_ARCHIVE" --sha256 "$HOME_SHA256" --target "$HOME_TARGET"
python3 -B scripts/package_release.py verify \
  --archive "$IDENTITY_ARCHIVE" --sha256 "$IDENTITY_SHA256" --target "$IDENTITY_TARGET"
```

Run the native verifier from the reviewed commit with its pinned prerequisites,
one role at a time, and retain the exact install and guard reports. Each role
starts a fresh isolated fake under the local runtime guard.

```sh
PATH="$PWD/.runtime/tooling/git-2.55.0/bin:$PATH" \
python3 -B scripts/release_install.py \
  --archive "$HOME_ARCHIVE" --sha256 "$HOME_SHA256" --target "$HOME_TARGET"
```

Use the Identity variables for the second invocation. A single-role result
establishes that role's install and reload. The reviewed candidate also needs
paired native identity approval, separate sessions, revoke and replay denials,
stock-client access with durable Git ref outcomes, supported upgrades and
application recovery from a backup. Review the local UI evidence independently
under the current [acceptance criteria](PHASE2_ACCEPTANCE.md). Record unexecuted
cases as open.

## Prepare the pilot

1. Obtain the owner's approval for the exact candidate, host, budget, domain,
   dedicated Home ship and separate member identities. Use only synthetic data.
   Keep live ship keys and certificate credentials in the operator's custody.
2. On the reviewed host, create an unprivileged service account and private
   state directories. Install the exact pinned runtime and verify its binary
   digest. Keep the Vere control socket, Lens, Khan and admin access private.
   Review the public TLS and Ames routes, port ownership, firewall rules and
   process supervision. An HTTPS-only frontend does not establish native peer
   connectivity.
3. Stage verified archives separately for the Home and member Identity roles.
   Match each ship's actual `our` and `zuse` to the approved identity and
   target. For a first install use empty, distinct desks. Existing desks or
   saved application state go through the qualified upgrade procedure.

## Install and bootstrap

The following is the offline desk staging procedure to use behind the closed
ingress fence. For each role, use its freshly verified archive from a private
directory. Extract only its desk payload.

```sh
umask 077
stage=$(mktemp -d)
tar --extract --file="$archive" --directory="$stage" \
  --no-same-owner --no-same-permissions --strip-components=2 \
  --wildcards 'stead-release/desk/*'
```

On the corresponding ship run these Dojo commands with an unused desk. For
the Identity role use a separate member ship and substitute the approved
Identity desk name, such as `%stead-identity-candidate`.

```text
|new-desk %stead-home-candidate
|mount %stead-home-candidate
```

Verify the mounted desk belongs to the intended pier. Review its existing
files and stop if any fall outside the candidate inventory. From the verified
staging directory, copy the Hoon files first. Commit the desk from Dojo so Clay
has the mark definitions before loading assets.

```sh
mount="$pier/stead-home-candidate"
cd "$stage"
find . -type f -name '*.hoon' -exec cp --parents -- {} "$mount/" \;
```

```text
|commit %stead-home-candidate
```

Then copy the remaining candidate files and verify the full mounted inventory.

```sh
find . -type f ! -name '*.hoon' -exec cp --parents -- {} "$mount/" \;
diff -qr -- "$stage" "$mount"
```

Commit again. Check Clay's raw byte digests and the typed Kelvin and bill against
the candidate before installing. Verify the role is live on the correct desk
after installation.

```text
|commit %stead-home-candidate
|install our %stead-home-candidate
.^(desk %gd /=stead-home=/$)
.^(? %gu /=stead-home=/$)
```

Substitute `stead-identity` in the role check for the member ship. The official
software-distribution guide and the pinned verifier document the Clay sequence.
[Urbit distribution](https://docs.urbit.org/build-on-urbit/userspace/dist/software-distribution)
· [Verifier](../../scripts/release_install.py)

Once the live profile is qualified, configure the empty Home via the reviewed
owner-local operation with the approved HTTPS origin, organization and team
IDs, explicit individual ship/principal/binding IDs and revisions, expirations
and project-creator grants. Configure each member's Identity role with the
matching Home and exact HTTPS origins. The existing fixture driver and its fake
configuration are local test inputs.

For each start or restart, keep ingress and external peer writes fenced. The
operator's controller must prove the new process owns the expected pier,
native identity and private TLS listener. Before stopping an admitted process,
capture its expected saved-state schema and fingerprint with writes fenced and
drained. Retain a reviewed copy of those values and the last accepted Work,
Docs and Git receipts. For a recovery use the corresponding backup record.
Before a supported reload, start with the app suspended and verify its saved
schema and fingerprint against the reviewed record. For a planned migration
check the source schema and fingerprint before conversion, then verify the
expected target schema and application readback before release. Stop on any
mismatch. The synthetic team's controller demonstrates the saved-state check.
[Local startup proof](../../scripts/urbit/team_lifecycle.py)

After those checks, use that process's owner-local connection. Generate a
fresh 32-byte nonce encoded as lowercase hex, open the Gall watch
`/bootstrap/<nonce>` and send `%stead-bootstrap-1` to the corresponding role
with this JSON payload.

```json
{"protocol":"stead.bootstrap/1","nonce":"<nonce>"}
```

Require an acknowledgement on that watch with protocol `stead.bootstrap/1`,
status `ready`, the expected ship in `home`, the exact nonce and a fresh
64-character hexadecimal `incarnation`. Successful bootstrap retires prior
sessions, approvals, cursors and watches. The acknowledgement proves the new
incarnation. While the fence is closed, verify the recovered acceptance
receipts and application readback against the reviewed checkpoint. Open traffic
only after this readback and the acknowledgement and listener checks pass for
the same process. Close ingress and existing streams when that process exits
or loses ownership.
[Configured-team contract](PHASE2_CONTRACT.md)

## Back up, restore and fence

1. Before upgrades or cutover, block new mutations, drain in-flight writes and
   record the authority epoch, final accepted command and receipt IDs, ref
   OIDs, and the loss window since the previous backup. Export Work, Docs and
   Git for exitability.
2. Close ingress and disable automatic restart. Stop Vere gracefully, confirm
   its child processes and listeners have exited, and keep the old host fenced.
   Capture the complete stopped pier and any approved external stores at that
   same boundary. Encrypt the backup off-host. Keep its keys separate and
   retain a manifest, runtime/candidate digests and file verification.
3. Verify the restored files in an isolated network with ingress and egress
   blocked. Check the restored saved state and exact acceptance receipts, Work
   and Docs records, Git OIDs, grant revocations and absence of repeated effects.
   Record measured recovery time and observed data loss. Source rollback alone
   cannot downgrade saved state.
4. For a same-identity migration, transfer the final stopped state and verify
   continuity before enabling precisely one replacement. Keep all old copies
   fenced. If the latest intact state cannot be recovered, stop before joining
   Ames until the operator reviews the runtime's continuity procedure. A later
   cross-identity migration also needs a verified project transfer and an
   authority-epoch advance. [Urbit cloud migration](https://docs.urbit.org/user-manual/running/cloud-hosting)
   · [Life and rift](https://docs.urbit.org/urbit-id/life-and-rift)

The [offline copy rehearsal](RELEASE_PACKAGING.md#stopped-home-file-round-trip)
checks byte preservation of a stopped synthetic pier. [Portable Work and
Docs recovery](PORTABLE_RECOVERY_PROFILE.md) has a separate data scope.

## Canary and dogfooding

Start with an approved, access-limited synthetic pilot. Verify onboarding and
individual sessions, stale/denied operations, binding revocation, restart
invalidation, support redaction, and ordinary Git clone/fetch/push with
`git fsck --full --strict`. Compare accepted receipts and original OIDs after
restart and recovery. Monitor write and read latency, failed authorization,
event backlog, memory/loom, disk and backup age with the declared workload.
Stop on unauthorized access, lost or duplicated accepted work, or uncertain
single-writer authority. Keep the last consistent state and failure evidence.

GitHub remains the writable source of truth during this pilot. Start Phase 5
dogfooding with a read-only import and verify its exact refs and export. Move
writes only after migration and fencing pass and the owner approves the
cutover. Then Stead owns accepted writes and GitHub is a one-way outward
mirror. Record the authority epoch and last mirrored OID. Resolve any
unexpected upstream writes as explicit proposals.

Admission of real team data requires a separate owner decision following
independent access, backup and operational review. [Deployment plan](DEPLOYMENT.md)
· [Master directive](MASTER_BUILD_DIRECTIVE.md)

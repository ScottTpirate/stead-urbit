# Phase 5 deployment runbook

Use this sequence for a reviewed synthetic pilot. Home recognizes the
`operator-pilot` custody and `live-synthetic` runtime profile only when Jael
reports a real ship. The repository's current Vere pin has fake-ship qualification.
Review that exact runtime for live operation and qualify the actual host's
closed startup fence before enabling pilot traffic. [Home startup checks](../../native/core/desk/lib/stead-team-owner.hoon)
The [local qualification record](PHASE5_LOCAL_20261110.md#retirement-limits-and-latest-archives)
identifies the tested v7 role archives and links the earlier four-ship results.

## Pilot checklist

1. Choose a pilot Linux host, a dedicated Home ship and a separate member ship.
   This is enough to test live sign-in and member work. Use multiple disposable
   member ships for local isolation and revocation checks. A testing moon can
   supply another distinct live identity under the same operator for a synthetic
   check. Choose an HTTPS hostname for each serving ship and keep its keys on
   the corresponding host.
2. Verify the approved Home and Identity archives and stage their desks with
   pilot traffic blocked. Install and configure them over private operator access.
3. Bootstrap each ship using the owner command below. Open traffic only for pilot
   participants after the app, process, certificate and restart checks pass.
4. Try separate logins, Work and Docs writes, a small stock Git round trip,
   revocation and backup recovery using synthetic data. Record the results before
   considering the repository cutover.

The [custody and handoff guide](PHASE5_CUSTODY.md) covers scoped replicas and
planned same-ship moves. The [Git rehearsal](PHASE5_DOGFOOD_REHEARSAL.md) covers
the full-history offline proof and the native storage gate for cutover. The
[browser identity profile](BROWSER_IDENTITY_PROFILE.md) is a separate design
track. Use individual native member ships for this pilot.

## Prepare a pilot update

Prepare both role archives and the Git relay tools from a single reviewed
commit. Use a fresh private output directory for each attempt.

```sh
python3 -B scripts/prepare_pilot_release.py \
  --source "$REVIEWED_COMMIT" --output .runtime/pilot-release-candidate
```

The receipt pins the archives to that commit. Check it before transfer and
again on the host before staging. Record the running predecessor, fence
ingress, and verify a stopped checkpoint before installing the candidate.
Reopen the existing origins after matching saved state, the accepted Git
snapshot, and the served assets. Check a fresh member sign-in and the project
readback through the same routes pilot members use. Keep certificate and
origin changes out of routine product updates.

## Before switching Stead's own project

Keep GitHub authoritative while the private pilot takes synthetic changes.
Use the [issue preview and import rehearsal](PHASE5_DOGFOOD_REHEARSAL.md#prepare-github-issues-for-work)
to choose the issue records for the cutover. The current import writes only to
a disposable Home; no live issue migration or authority transfer is implied
by the preview.

Keep private Git uploads fenced during candidate qualification. The worker
runs under its own account and exchanges only bounded upload and signature
frames with the relay over a Unix socket. The relay uses a pinned TLS
connection to Home and forwards an individual Git credential on each
decision. Give the service accounts access only to their designated private
paths. The ingress must dispatch Git and browser routes explicitly, strip
the relay capability header from participant requests, and reject the private
Home carrier path. The HTTPS pass-through used by the earlier pilot needs a
route-aware ingress for this profile. [Git rehearsal](PHASE5_DOGFOOD_REHEARSAL.md#worker-result-authentication)

Render the proposed Home edge configuration into a private review file. The
inputs are the approved Home HTTPS hostname, its pinned desk and native TLS
trust, and the relay's private Git socket. Use a dedicated nginx listener in
its `http` context and check the complete configuration with `nginx -t`.

```sh
umask 077
python3 -B scripts/urbit/git_pack_edge.py --hostname "$HOME_HOSTNAME" \
  --listen-ipv4 "$APPROVED_ADDRESS" --public-port 443 --home-port "$NATIVE_TLS_PORT" \
  --git-socket "$GIT_EDGE_SOCKET" --project "$PROJECT_ID" --desk "$VERIFIED_DESK" \
  --certificate "$PUBLIC_CERT_CHAIN" --key "$PUBLIC_CERT_KEY" --home-ca "$NATIVE_TLS_CA" \
  > "$PRIVATE_REVIEW_DIR/stead-home-nginx.conf"
```

Keep the native TLS listener on `127.0.0.1` with no separate public
pass-through. The Git relay listens only on its Unix socket, with group
write access for the dedicated nginx worker account and no other client
accounts. Reconnect the ingress fence to the admitted Vere process before
opening traffic. The generated include serves only the Home hostname, its
exact browser routes, and the selected project's Git Smart HTTP routes.
The Code file browser uses `POST /stead/api/code/browse` on the same origin.
Exact proposal comparisons use `POST /stead/api/code/changes`. The relay
obtains the base and head from Home's authorized proposal revision, verifies
that both commits remain in the accepted pack, and rechecks the proposal and
snapshot before returning changed files or a bounded patch. Historical
comparisons depend on the retention of both exact commits.
The relay checks the member's session, project access, and accepted snapshot
with Home before reading the pack and again before returning names or plain
text. Refresh the nginx include and restart the relay when installing support
for this route. Existing edges continue to offer branches, tags, and Git clone.
Use the separate, approved Identity HTTPS route for member ship sign-in.
Local nginx tests exercise the Home/Git dispatch and certificate validation
with synthetic backends. Validate the actual host's fence, upstream ownership,
client interoperability and service deadlines before pilot activation.
The edge accepts Git uploads with an explicit content length. For a push
whose request exceeds Git's default 1 MiB buffer, use
`git -c http.postBuffer=8454144 push stead YOUR_BRANCH` for that invocation.
The receive request limit is 8,454,144 bytes, including protocol framing.
[Git HTTP buffer configuration](https://git-scm.com/docs/git-config#Documentation/git-config.txt-httppostBuffer)

Load the relay using a private mode-0600 JSON profile owned by its
unprivileged service account. Use the existing private Home origin, with
its native listener port and exact certificate SHA-256. The capability
belongs only to this process. Install the reviewed Git executable under
root-owned, non-writable-by-service directories and supply its digest.

The profile protocol is `stead.git-pack-relay-service/1`. Its exact fields
are `protocol`, `project`, `home`, `origin`, `home_port`,
`certificate_sha256`, `ca`, `capability`, `relay_uid`, `worker_uid`,
`worker_socket`, `spool`, `read_store`, `git`, and `git_sha256`.
Use separate private spool and read-store directories. With the relay
account and its dedicated edge group, an example foreground service is

```sh
gunicorn --chdir "$STEAD_CHECKOUT/scripts/urbit" \
  --bind "unix:$GIT_EDGE_SOCKET" --umask 0007 --workers 1 --timeout 90 \
  "git_pack_relay_service:create_application('$RELAY_PROFILE')"
```

The native socket and reviewed Git digest are checked during use. Git runs
in an isolated namespace that can read only the selected temporary bare
repository and its executable and runtime libraries. The relay account's
socket directory admits the nginx worker group only. Configure a service
supervisor so nginx stops forwarding when either upstream loses its fence.
[Gunicorn Unix sockets](https://gunicorn.org/deploy/)

The Vere account is the sole writer for the projection mailbox. Provision
its directory mode 0750 with the mailbox group shared by the worker and read
relay. Give each service a separate mode-0700 store and provision a second
socket directory for pack projection. Run the projection socket command as
the worker and the reconciliation command as the read relay.

```sh
common=(--home "$HOME_SHIP" --project "$PROJECT_ID" --authority-epoch "$AUTHORITY_EPOCH"
        --mailbox "$MAILBOX" --controller-uid "$VERE_UID" --mailbox-gid "$MAILBOX_GID"
        --artifact-socket "$PROJECTION_SOCKET" --worker-uid "$WORKER_UID" --relay-uid "$RELAY_UID")

# Worker account
python3 -B scripts/urbit/git_pack_projection_reconcile.py "${common[@]}" \
  serve --worker-store "$WORKER_STORE" --socket-gid "$SOCKET_GID"

# Vere account, repeat before the 15-second lease expires
"${owner[@]}" pack-projection-refresh --project "$PROJECT_ID" --authority-epoch "$AUTHORITY_EPOCH" \
  --mailbox "$MAILBOX" --mailbox-gid "$MAILBOX_GID"

# Read relay account
python3 -B scripts/urbit/git_pack_projection_reconcile.py "${common[@]}" \
  once --read-store "$RELAY_STORE" --git "$PINNED_GIT"
```

Keep ingress closed until the retained worker data and read relay agree with
the current Home snapshot. A missing, expired or changed lease prevents
publication. Each Git read still requires a current individual credential
and the exact Home decision. Before a writer change, fence ingress and
in-flight requests, close the native relay policy, and refresh the closed
mailbox while Home is reachable.

Before proposing the switch, demonstrate all of the following with one pinned
candidate:

1. A member can sign in, reopen Work and Docs, and revoke one credential
   without losing another member's access. Use distinct authenticated member
   identities on the same Home to check the second member's grant and removal.
   Operator control of both synthetic identities is sufficient for this test.
2. Stock Git pushes a change against the full pinned repository. A second
   push from the same prior ref loses the comparison, protected refs advance
   only through exact review, and a lost reply reconciles to the durable
   receipt. Reopen the accepted refs, Work item and review after restart.
3. Restore the matching Home checkpoint and accepted Git data on a fresh
   isolated host, verify the exact refs and protected records, and prove
   that only one writer can be admitted. Record restore duration and data loss.
   The local rehearsal already exercises sealed replay, decrypted recovery,
   strict clone verification and fresh session admission.
   [Paired recovery evidence](PAIRED_RECOVERY_PROFILE.md#executed-local-paired-restore)
4. Rehearse mirror divergence and backout. Only then ask the owner to approve
   freezing GitHub writes and transferring authority to the verified Home.

After the transfer, the first dogfood task should take one real issue through
Work, an individual collaborator or agent proposal, review, accepted source,
and the isolated build. Keep the branch, work item, review and build receipts
connected so failures can be fixed inside Stead. A supported release also
needs the independent teams, integration and maintainer checks in the
[ecosystem plan](ECOSYSTEM_PLAN.md).

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

### Candidate and host admission

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

Configure the empty Home with the approved HTTPS origin, organization and team
UUIDv7s, and explicit ship/principal/binding mappings. In the initial Home JSON
use `protocol` = `stead.team-config/1`, `expected_revision` = `0`, `custody` =
`operator-pilot`, and `runtime` = `live-synthetic`. Set `home`, `origin`,
`organization_id`, and `team_id`. Key `bindings` by canonical member ship name.
For each member supply `principal_id`, `binding_id`, `binding_revision` = `1`,
`active` = `yes`, future `expires_at_ms`, and `display_name`. Key
`project_creators` by the explicitly authorized principal IDs with value `yes`.
Use JSON strings for these values. Identity JSON has `protocol` =
`stead.identity-config/1`, `expected_revision` = `0`, `home`, `home_origin`, and
the member's distinct `origin`. [Configuration decoder](../../native/core/desk/lib/stead-team-config.hoon)

The candidate includes an owner-local Khan thread on each installed desk. Run
the helper from the reviewed checkout as the dedicated Vere account, with the
Vere PID and the actual absolute pier path used at launch. Repeat for each
member with the Identity desk, role, ship and configuration. Keep the pier and
`.urb` directories private and the Khan socket unexposed.

```sh
owner=(python3 -B scripts/urbit/pilot_owner.py --pid "$vere_pid" \
  --binary "$vere_binary" --pier "$pier" --ship "$ship" \
  --desk "$desk" --role "$role" --approved-runtime-sha256 "$approved_runtime_sha256")
"${owner[@]}" configure "$config_json"
"${owner[@]}" cert --key "$private_key_pem" --chain "$full_chain_pem"
```

For each start or restart, keep ingress and external peer writes fenced. The
host supervisor must keep the fence closed across Vere exits and supervisor
restarts. Use the launcher with an existing dedicated pier and the reviewed
runtime. It injects a sealed Gall suspension at startup and binds HTTP to
loopback. Configure the host's HTTPS pass-through and Ames network fence
separately. Use the launched Vere PID for the owner commands.

For a systemd service, set `KillMode=mixed` so SIGTERM goes to the Vere
parent first and it can shut down its worker. Verify successful service exit,
removed pier lock and control socket, and closed listeners before taking a
stopped-pier backup or starting another process against that pier.

```sh
python3 -B scripts/urbit/pilot_start.py --binary "$vere_binary" --pier "$pier" \
  --role "$role" --approved-runtime-sha256 "$approved_runtime_sha256" \
  --ames-port "$ames_port" --http-port "$native_http_port" --https-port "$native_https_port"
```

Before stopping an admitted process,
capture its expected saved-state schema and fingerprint with writes fenced and
drained. Retain a reviewed copy of those values and the last accepted Work,
Docs and Git receipts. For a recovery use the corresponding backup record.
Before a supported reload, start with the app suspended and verify its saved
schema and fingerprint against the reviewed record. For a planned migration
check the source schema and fingerprint before conversion, then verify the
expected target schema and application readback before release. Stop on any
mismatch. The synthetic team's controller demonstrates the saved-state check.
[Local startup proof](../../scripts/urbit/team_lifecycle.py)

For a restart, confirm the expected `our`, `zuse`, desk and suspended app
through private Dojo before using `|rein` on the approved desk. The following
shows Home; substitute the Identity desk and agent on each member ship.

```text
our
zuse
.^(desk %gd /=stead-home=/$)
.^(? %gu /=stead-home=/$)
|rein %stead-home-candidate [%.y %stead-home]
```

After those checks and the native Eyre certificate request, run the following for
Home. A first configuration has revision `1`. Use the exact approved HTTPS
origin, native TLS listener port, and SHA-256 of the leaf certificate in DER
form. The installed certificate chain must validate with the host trust store.
The private key file must be mode `0600` and owned by the service account.

```sh
"${owner[@]}" status --revision "$config_revision"
"${owner[@]}" bootstrap --revision "$config_revision" --origin "$origin" \
  --listener-port "$native_https_port" --certificate-sha256 "$certificate_sha256"
```

For Identity run `bootstrap` with its own origin, port and certificate digest,
omitting `--revision`. On restart include `--previous-incarnation` using the
retained value. The helper binds the private Khan connection and TLS listener to
the reviewed process. Home bootstrap requires a closed app with a ready
projection, correlates a fresh native acknowledgement to the exact config
revision and checks availability again. Bootstrap invalidates prior sessions,
approvals, cursors and watches.

While the host fence is closed, verify the recovered acceptance receipts and
readback against the reviewed checkpoint. The host's fence must close ingress,
existing streams and peer writes when the admitted process exits or loses
ownership, including across supervisor restart. Open traffic only after the
readback, bootstrap and listener checks all pass for that same process.
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

## House test-space option

The steps above deploy the standalone Stead Home and Identity desks. A House
space pilot also needs a supported desk installation and app entry contract,
a verifiable member identity assertion tied to the exact space, and a source of
membership changes and revocations. Map each verified member to a Stead
principal and scoped grants. Test two members, denial across spaces, removal
and a stale membership assertion before granting access to real records. The
space connection token is insufficient evidence of owner control or member
authorization. Keep the standalone pilot and House integration evidence
separate. [Roadmap](ROADMAP.md)

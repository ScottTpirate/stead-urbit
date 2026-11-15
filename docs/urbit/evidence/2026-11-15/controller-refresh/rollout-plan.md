# Reviewed procedure for the next existing-pilot update

Status: preparation only. No host mutation or deployment has occurred. The user
authorized the existing Lightsail rollout; the integrator will select the exact
qualified commit before execution. This procedure does not activate command/4,
new Work saved-state molds, or autonomous agent execution.

## Observed predecessor

Read-only inspection on 2026-11-15 found the active release at
`dbc8cc01adb32b14912e3e74c8efa324ba0eb5c9`, under
`/var/lib/stead-pilot/candidate-v9-dbc8cc0`. Both native role services and all six
Git services were active. The external Ames input/output fence remains closed.
The two piers occupy about 1,147 MiB; the worker, read relay and native pack
stores occupy about 118 MiB together. The backup volume has over 146,000 MiB
free. There is no need to provision another host.

| Role | Ship | Desk | Native HTTPS | Existing member origin |
| --- | --- | --- | --- | --- |
| Home | `~hapnev-sabweb` | `stead-home-candidate` | loopback 18443 | `https://stead.kilgore.science` |
| Identity | `~tagdep-salled` | `stead-identity-candidate` | loopback 18444 | `https://stead-id.kilgore.science` |

The Home edge listens on loopback 19443. The private tunnel remains the member
entry point. Keep the existing certificates, CA, configured origins, ports,
native identity, custody and runtime unchanged. Never print or commit private
keys, cookies, relay capabilities, identity codes or private configuration.

The actual current Home save is format 8; the package contract supports up to
format 9. Home chooses its saved envelope according to populated state. The
current candidate's Home and Identity app files match the deployed predecessor,
so this slice requires no saved-state migration. Recheck that equality at the
final candidate. Do not infer actual saved schema from the release maximum.

Existing verified stopped checkpoints are retained at
`/var/backups/stead-pilot-release-dbc8cc0.u8RU9Cs2` and
`/var/backups/stead-pilot-origins.Fd3NaTB2`. Take a new checkpoint for this update;
neither old checkpoint is the current rollback boundary.

## Candidate and preparation gates

1. Freeze a commit containing the reviewed UI, T05a and workspace-query slice.
   Reserved `stead-product-*` libraries/tests must be absent from that commit.
   Register the six workspace native arms and qualify this exact commit with
   the reviewed hosted controller. Retain the hosted source inventory, native
   transcript results, supported migration and empty-process cleanup evidence.
2. Complete the bounded frontend build and interaction checks; commit the exact
   generated role assets and manifests. If this changes native package inputs,
   use that final immutable commit for native qualification. Do not substitute
   a later mutable working tree after the run.
3. Run `scripts/prepare_pilot_release.py` from the reviewed checkout with the
   full commit ID and a new private `.runtime/NAME` directory. This packages
   already built assets and checks both archives without executing native code.
   It emits the two role archives, targets, verification records, relay tools
   and receipt. Independently verify archive hashes and the exact source commit.
4. Compare the candidate's native app files, role manifests and toolchain pins
   against the predecessor. Read-only projection/query changes must not alter
   authoritative saved state. If the actual app or saved-state contract changes,
   stop using this procedure and review a migration-specific procedure.
5. Stage a new root-owned candidate directory on the existing host. Verify all
   transferred hashes before extracting into private staging directories.
   Carry reviewed helpers from the exact candidate; do not compile arbitrary
   source or run a model on the authority host. Preserve the predecessor.
6. Prepare the operator helper against the existing named origins and CA.
   Historical `app.py` hardcodes old localhost origins and cannot be reused
   unchanged. Its exact Clay inventory, process binding and save checks remain
   required. Bootstrap the existing configuration revision and certificate;
   never call the historical origin-changing `domain-roles.py install` action.

## Fence and checkpoint

1. Acquire both existing nonblocking locks:
   `/run/lock/stead-private-v9-rollout.lock` and
   `/run/lock/stead-private-v9-git.lock`. Verify runtime SHA-256
   `f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833`,
   exact running process ownership, both installed desk inventories, named TLS
   routes, active predecessor metadata and absence of another maintenance fence.
2. Create a fresh root-private checkpoint directory and durable phase marker.
   Add the existing maintenance output fence for loopback ports
   18080, 18081, 18443, 18444 and 19443, initially permitting only root and the
   dedicated Vere account. Verify the rule. Keep the external Ames fence.
3. Capture a fresh authenticated read-only baseline through the named origins:
   all accessible projects, Work, collections, full Docs, relations and the
   accepted Code snapshot/ref/tree. Log out the probe session. Use bounded
   canonical row fingerprints, not titles or secrets in public evidence.
4. Stop and verify the edge, reconciliation, lease, relay, worker and projection
   services. Preserve the final mailbox selection and exact accepted snapshot.
   Suspend each native app through its process-bound owner connection; this
   drains accepted app work and closes authority before the save capture.
5. Capture each role's exact saved-vase hash and authoritative-state hash.
   Retain configuration revision, prior incarnation and public target pins.
   Stop both Vere services gracefully; require successful exit, no remaining
   process/cgroup members, no role listeners, no `.vere.lock` and no Khan socket.
6. Copy both complete stopped piers and all paired worker/read-relay/native pack
   stores. Include current edge configuration, private service profiles, signing
   material, public pins and bootstrap records in the private checkpoint only.
   Require ordinary files/directories, preserve ownership/modes, hash the full
   checkpoint, verify every hash, and compare each stopped source pier to its
   copy. Mark `checkpoint-verified` only after all checks pass.

## Install and verify while fenced

1. Restart each existing pier through the reviewed suspended-start launcher,
   using the existing service identity and limits. Verify exact ship, Kelvin,
   desk and pre-update saved-vase hash before loading the candidate.
2. Stage only the verified role archive. Require the mounted inventory and Clay
   bytes to match the exact predecessor before changing any file. Commit Hoon
   before new non-Hoon assets where mark admission requires it, then verify the
   candidate Clay bytes and remove only obsolete files in the exact predecessor
   inventory. Require the complete final inventory to match the archive.
3. Stop and restart suspended once more. Verify the expected saved-vase hash,
   activate the candidate role, and require the authoritative-state hash to
   equal the checkpoint. Require actual save schema to remain unchanged.
4. Wait for the rebuilt projection, then bootstrap each role with its unchanged
   named origin, native TLS pin, current configuration revision and retained
   previous incarnation. Verify fresh incarnation and exact native served shell.
   Recheck the authoritative-state hash before any new member authentication.
5. Re-establish the existing Git services with a new scoped worker generation
   after proving Home's relay policy is closed. Use the existing reviewed key
   rotation and relay admission path; require the published mailbox selection
   to equal the checkpoint's accepted snapshot and fresh Home incarnation.
   Update only reviewed relay tools if their exact candidate diff requires it.
   Keep current named routing and certificates; validate the complete nginx
   configuration before starting the edge.
6. Permit only the existing ingress/relay service accounts through maintenance
   to Home's native TLS port. Start projection, worker and relay; verify sockets
   and ownership. Admit the unchanged snapshot, then start lease,
   reconciliation and edge. The general maintenance fence stays in place.
7. Fetch every packaged role asset through the exact named HTTPS routes and
   compare byte length and SHA-256 to the archive. Confirm anonymous query/Git
   denial and private-carrier rejection. Perform a new approval/sign-in and
   compare the full Work/Docs/relations/Code baseline. Exercise the new Work
   contract and workspace capability/read surfaces with that member. Confirm
   no cross-project/private canary disclosure, then log out and prove denial.

## Reopen and hand back

Only after all preceding checks pass, atomically write the new active release
metadata with source/archive hashes and the new checkpoint path. Remove the
maintenance table, leaving the established external Ames fence and private
tunnel policy unchanged. Recheck served assets and live service ownership after
reopening. Perform the actual rendered browser path through `stead-pilot`:
fresh sign-in and approval, My work/Search, Work detail, Docs preview/source,
Code tree/file and back navigation. Record failures honestly; an API readback
does not establish rendered product acceptance. Retain the previous artifacts
and stopped checkpoint after handoff.

On any mismatch, keep maintenance closed and preserve the phase marker and
evidence. Do not automatically open traffic or restore an old pier. A failure
before candidate activation may safely leave the predecessor suspended. After
activation, first inspect whether authority changed; same-source rollback may
be sufficient for this no-migration slice, but copying an older pier over a
newer live identity is not an automatic recovery action. Any recovery must keep
exactly one writer and use the verified paired boundary.

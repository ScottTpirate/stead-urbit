# Reviewed procedure for the next existing-pilot update

Status: the supervised rollout completed successfully on 2026-11-15. The
active pilot source is `c2f286154ada3f27dd53a7dda78741a75788b522`; hosted run
`43745730053` passed all 173 positive arms, 1,672 checks and six containment
controls with reviewed controller `8c7fbe1550542d187508f6b4fbd6a62448d02925`.
The stopped paired checkpoint is
`/var/backups/stead-pilot-product-c2f2861.orKUJW4h`. All eight services are active,
maintenance is removed, and exact Work/Docs/relations across three projects plus
the accepted Git snapshot match the baseline. Home's 11 and Identity's 10
packaged HTTPS asset routes matched their exact bytes and hashes. See
`lightsail-c2f2861-readback.json` and `hosted-43745730053/review.json`.
The first isolated local browser check stopped at the reviewed 80°C limit
after 95.4 seconds during Identity approval, before any content checks. Its
process group is empty; Home was not authenticated, and Identity logout could
not be confirmed after the ephemeral context closed. No unrelated owner
session was revoked. `pilot-browser-thermal-stop/` retains that incomplete
result. Rendered acceptance remains pending and will move to an isolated
remote browser if its separate runtime review succeeds. No human trial is claimed.

The first operator attempt stopped before any fence or service change because
installed support tools were older than their active source metadata implied.
The independently reviewed correction pins the exact eight-path before/after
tool hash map; four unrelated modules remain untouched. The successful retry
used that correction, retained in `release-operator-amendment-c2f2861.json`.

The earlier `01aa9e9` and `c27268f` candidates failed in the workspace test
fixture and are not deployable; both failure records are retained separately.
The current candidate adds only an explicit list-cell guard to that fixture;
its native applications, libraries and generated assets match `c27268f`.
The current operator packet is `.runtime/pilot-release-product-c2f2861/operator`; it requires the
matching successful native receipt before execution. This procedure does not activate command/4,
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

Earlier verified stopped checkpoints are retained at
`/var/backups/stead-pilot-release-dbc8cc0.u8RU9Cs2` and
`/var/backups/stead-pilot-origins.Fd3NaTB2`. The successful rollout added the new `stead-pilot-product-c2f2861.orKUJW4h`
checkpoint listed above; neither older checkpoint is this rollout boundary.

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
7. Regenerate the Home edge's exact asset-route allowlist from the candidate
   desk. New shared chunk names require a new include even when relay code is
   unchanged. Stage it with the reviewed `edge-update.py` checks: bind the
   predecessor include hash, candidate tools archive hash and nginx binary hash;
   verify identical hostname, TLS, upstream, socket and project bindings;
   validate the shadow complete configuration with `nginx -t`; verify that
   active files remained unchanged during staging. Keep its exact staged receipt.

## Fence and checkpoint

1. Acquire both existing nonblocking locks:
   `/run/lock/stead-private-v9-rollout.lock` and
   `/run/lock/stead-private-v9-git.lock`. Verify runtime SHA-256
   `f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833`,
   exact running process ownership, both installed desk inventories, named TLS
   routes, active predecessor metadata and absence of another maintenance fence.
2. Create a fresh root-private checkpoint directory and durable phase marker.
   Add the existing maintenance output fence for loopback ports
   18080, 18081, 18443, 18444 and 19443, permitting root and the dedicated Vere
   account. Permit the existing ingress and relay accounts only to native Home
   port 18443 so the supervised baseline can traverse the unchanged edge while
   member ingress remains fenced. Verify the rules. Keep the external Ames fence.
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
   Install the staged asset-route include with predecessor-hash compare-and-set.
   Keep current named origins and certificates; validate the complete nginx
   configuration before starting the edge.
6. Permit only the existing ingress/relay service accounts through maintenance
   to Home's native TLS port. Start projection, worker and relay; verify sockets
   and ownership. Admit the unchanged snapshot, then start lease,
   reconciliation and edge. The general maintenance fence stays in place.
7. Fetch every packaged role asset through the exact named HTTPS routes and
   compare byte length and SHA-256 to the archive. Confirm anonymous query/Git
   denial and private-carrier rejection. Perform a new approval/sign-in and
   compare the full Work/Docs/relations/Code baseline. Exercise the new Work
   contract and workspace capability/read surfaces with that member. Require
   workspace results to equal the independently read authorized project union;
   retain the hosted cross-project/private-canary denial proofs separately.
   Log out both probe sessions and prove Home denial after signout.

## Reopen and hand back

Only after all preceding checks pass, atomically write the new active release
metadata with source/archive hashes and the new checkpoint path. Remove the
maintenance table, leaving the established external Ames fence and private
tunnel policy unchanged. Recheck served assets and live service ownership after
reopening. Perform the actual rendered browser path through a verified private
SSH tunnel and isolated Chromium profile with the existing exact certificate pins:
fresh sign-in and approval, My work/Search, Work detail, Docs preview/source,
Code tree/file and back navigation. Record failures honestly; an API readback
does not establish rendered product acceptance. Retain the previous artifacts
and stopped checkpoint after handoff. Repair the existing `stead-pilot` helper's
stale socket only after verifying it has no live owner or listening ports; use
the helper's normal checked tunnel startup without changing global trust or the
user's browser profile.

On any mismatch, keep maintenance closed and preserve the phase marker and
evidence. Do not automatically open traffic or restore an old pier. A failure
before candidate activation may safely leave the predecessor suspended. After
activation, first inspect whether authority changed; same-source rollback may
be sufficient for this no-migration slice, but copying an older pier over a
newer live identity is not an automatic recovery action. Any recovery must keep
exactly one writer and use the verified paired boundary.

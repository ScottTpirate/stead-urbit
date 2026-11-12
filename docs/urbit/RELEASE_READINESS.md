# Phase 6 release evidence and publisher key recovery

Run the verifier after assembling the evidence for an exact candidate.
It checks both role archives against their signed digests and compatibility
targets, binds each review to the candidate and its observations, and checks
owner approval against those exact signed reviews. The operator checks
independence, the substance of the observations, and suitability for public
release. Keep a private copy of this bundle and publish only reviewed,
redacted compatibility and release evidence.

## Verify a candidate

```sh
python3 scripts/release_readiness.py \
  --trust /path/to/reviewed-trust.json \
  --trust-sha256 "$REVIEWED_TRUST_SHA256" verify /path/to/evidence-bundle
```

The trust digest must come from the separately reviewed current policy. Set
`profile` to `independent` only after the owner confirms the signers and their
independent roles. Use `synthetic` for rehearsals. Supply canonical JSON with
protocol `stead.release-trust/1`, the `profile`, integer `generation`, `keys`,
and `retired_publishers`. Start at generation `1` with an empty retired list.
The keys are distinct raw Ed25519 public keys encoded as 64 lowercase hex
characters. The roles are `publisher`, `recovery`, `owner`, `backup-maintainer`,
`team-a`, `team-b`, and `app-integrator`. Keep private keys with their signers.

| Bundle file | Required contents |
| --- | --- |
| `home.tar` and `identity.tar` | Exact archives from `scripts/package_release.py` for a single commit. |
| `candidate.json` | Publisher signature and `stead.release-candidate/1` statement with `profile`, `release` (such as `v1.0.0`), `source_commit`, `trust_sha256`, and `archives`. The `archives` object contains `home` and `identity`, each with `sha256` and its exact package `target`. |
| `<role>.json` and `<role>.evidence` for `backup-maintainer`, `team-a`, `team-b`, and `app-integrator` | Each role signs a `stead.release-review/1` statement with `candidate_sha256`, `observation_sha256`, and `checks`. Its distinct evidence file contains the observations the signer reviewed. |
| `owner.json` and `owner.evidence` | The owner signs a `stead.release-owner-approval/1` statement with `candidate_sha256`, `reviews` (reviewer role to signed JSON file SHA-256), `checks`, and `observation_sha256` for the distinct owner review. |

Use the sorted check names from `REVIEW_CHECKS` and `OWNER_CHECKS` in the
verifier. The backup maintainer reproduces the archives and exercises private
reporting and key recovery. Each independent team documents installation,
upgrade, restoration, export and the tested support profile. The separate
app verifies its integration through the published SDK. The owner reviews
release-blocking defects, the support matrix, repository history, licenses,
secret handling, and the independence of those observations before signing
the exact candidate for public release. Keep reporting tests within the
approved private intake channel.

An envelope has `statement` and `signature` fields. The signature is 128
lowercase hex characters. Serialize records with the verifier's `encoded`
function, which uses sorted keys, two-space indentation and a trailing LF.
`candidate_sha256` hashes the canonical candidate statement bytes.
`observation_sha256` hashes the exact evidence file. Use `signing_bytes` from
the verifier to produce the message for your signer. It is the statement's
protocol, a NUL byte, the signing role, a NUL byte, and the canonical
statement bytes. The report identifies synthetic and independent claims
explicitly. The owner retains control over the release operation.

## Recover a lost publisher key

Obtain the current policy from the trusted source. Generate a fresh publisher
key with the backup maintainer. The `stead.release-key-recovery/1` statement
binds `prior_trust_sha256`, `retired_publisher`, `next_publisher`, and
`next_generation`. Use the immediate next integer generation. The owner,
offline recovery signer, and replacement publisher each sign the same
statement with roles `owner`, `recovery`, and `next-publisher`, respectively.
Put the three signatures in a `signatures` object in the recovery envelope.

```sh
python3 scripts/release_readiness.py \
  --trust /path/to/reviewed-trust.json \
  --trust-sha256 "$REVIEWED_TRUST_SHA256" verify-recovery /path/to/recovery.json
```

The report contains the proposed `next_trust` policy and its canonical SHA-256.
The owner distributes that exact policy and digest to verifiers after review.
Verifiers advance from the current generation, retain the retired publisher
history, and use the new policy for further candidates. Save the old and new
policy digests, the signed rotation and the result as drill evidence. Keep
the approved recovery key available through the chosen independent custody
procedure.

## Local rehearsal

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/urbit \
  -p 'test_release_readiness.py' -v
```

The seven tests ran real Ed25519 signatures and offline package verification.
The CLI also verified the Home and Identity archive pair built at `afaefd6`
with synthetic roles, advanced to generation 2, accepted a candidate from the
replacement publisher, and refused both the retired publisher and a replay of
the rotation. The temporary keys were discarded. The local report is
`.runtime/phase6-readiness-6v37z93o/result.json` with SHA-256
`3c74b644cf93f02f8cfe577d6bb5a181521d550ba780b7393a77fcfcdea0d19a`.

The same CLI rehearsal passed against the v7 role archives built from
`7d0d025df091abe0dcaf013c048e9b490f7b763f`. It verified the initial synthetic
candidate, accepted the replacement publisher after rotation, and refused
the retired publisher and replayed rotation. The local report is
`.runtime/current-v7-readiness-1mFi4PaL/report.json` with SHA-256
`73d3aeb5f3593a1b486d002adcf2de828843099ed243d063f7ea3971766534a2`.

URB-270 still needs a real backup maintainer, verified private reporting,
actual custody and recovery of release keys, and owner approval after the
history, license and secret review. URB-280 still needs evidence from two
independent teams and a separate SDK app, plus reviewed support and upgrade
evidence for the release candidate.

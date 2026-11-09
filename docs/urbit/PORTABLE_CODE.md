# Portable Code history

The Code archive captures a private bare SHA-1 clone made through the ordinary
authorized Git route. It preserves every branch and tag ref, the local clone's
HEAD, and the exact bytes of every object reachable from those refs. The restored
repository opens with ordinary Git without a Home or Urbit runtime.

## Capture and verify

Use a fresh full bare clone from Code's credential-free URL. Supply the individual
read credential to Git's password prompt with username `stead`. Keep the URL and
command history free of credentials. For a local fixture, use its verified
certificate authority and keep TLS verification enabled.

```sh
umask 077
scratch=$(mktemp -d)
git -c credential.helper= -c http.followRedirects=false clone --bare --template= \
  "$STEAD_CLONE_URL" "$scratch/source.git"
python3 -B scripts/urbit/portable_code.py create \
  "$scratch/source.git" "$scratch/code.json" --project "$STEAD_PROJECT_ID"
```

Record the returned SHA-256 independently. A quiescent private clone is the
snapshot boundary. The tool checks that observed refs, HEAD and config remain
unchanged while it reads the objects. Capture requires an owned private clone
using the ordinary files backend, with no alternates, shallow history, redirected
files, or extended local configuration. For a local Git source, use
`--no-local` to avoid hardlinked object files.

The canonical archive carries exact ref-name bytes in hex, including names Git
can represent without UTF-8. It supports 64 refs, 512 objects, an 8 MiB combined
object body limit, a 1 MiB per-object limit and an 18 MiB archive limit. Capture
and offline verification each reconstruct a private bare repository and require
stock `git fsck --full --strict --no-reflogs` plus an exact object closure.

```sh
python3 -B scripts/urbit/portable_code.py verify \
  "$scratch/code.json" --sha256 "$RECORDED_SHA256"
python3 -B scripts/urbit/portable_code.py restore \
  "$scratch/code.json" "$scratch/restored.git" --sha256 "$RECORDED_SHA256"
git --git-dir="$scratch/restored.git" for-each-ref
```

Restore publishes a verified, synced bare repository at a new path using
no-replace rename on Linux. It never writes to an existing repository. A failed
verification leaves the destination absent. The archive is readable content.
Keep it in private storage and protect independently recorded digests.

## Publishing to a new Home

The offline restore carries Git content. It omits branch protection, membership,
Home receipts, proposals, reviews, builds and credentials. Unreachable objects,
separate repositories, and external Git LFS or submodule content are also outside
the archive. The project ID is an operator label. The digest checks exact bytes
and Git consistency, independent of current membership or Home provenance.

Create a new empty target repository in an access-restricted project. Confirm its
URL and empty refs using a fresh target credential. Publish only the restored
branch and tag refspecs with ordinary Git, use `--atomic`, and give each ref an
empty expected old value with `--force-with-lease=<ref>:` to prevent overwriting a
concurrently created ref. Compare the target's full branch and tag inventory
against the restored repository after the push. Recreate approved branch
protection and access rules through the target's own authority before opening it
to other writers. A Home may choose a different default HEAD.

The target independently applies its push size, object and ref limits. An archive
that verifies offline can exceed a single native push. The archive tool performs
no network write or policy migration. [Native Git limits](CODE_HOME_PROFILE.md)

## Verification boundary

The host regression uses stock Git against synthetic data to check deterministic
capture, exact commit ancestry and refs, annotated tags, binary blobs,
unborn/detached HEAD, offline recovery and atomic publication into an empty Git
repository. Negative cases cover unreachable and missing objects, resealed
corruption, alternate or redirected storage, unexpected refs, symlinks and a
racing destination. The stock Git host test is separate from the existing
authorized native Smart HTTP checks.

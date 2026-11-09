# Offline desk packaging foundation

This implements a bounded **URB-220 packaging candidate**, alongside the M4
requirements in `ECOSYSTEM_PLAN.md`. It does not close URB-220 or qualify an
install, upgrade, backup restore, canary, distribution channel or production use.
No command here starts a ship, imports private state, changes an installed desk,
publishes a release or contacts a service.

## What the artifact contains

`scripts/package_release.py` builds a deterministic, uncompressed USTAR archive
from one exact Git commit. A role is mandatory: `home` selects `%stead-home`;
`identity` selects `%stead-identity`. Each archive has one role in `desk.bill`.
It includes the selected app's recursively resolved Ford imports, the selected
v3 and owner/bootstrap marks, pinned standard marks, `sys.kelvin`, exact native
frontend assets and their route inventory, licenses and operator guidance.

`specs/urbit/release-package.json` pins the standard dependency bytes to the
already pinned Urbit kernel and runtime. The initial dependency pins were checked
against the SHA-256-verified kernel archive, without extracting it. Each pin also
names its reviewed regular source path: the standard libraries and marks come
from `pkg/base-dev/`, and the license comes from `pkg/arvo/LICENSE.txt`. The
`pkg/arvo/` library/mark aliases are not build inputs. The packager rejects
symlinks at any component of a selected source path and does not resolve or trust
cache aliases. Build requires those files in the existing verified local kernel
cache; it never refreshes a branch or downloads a missing dependency. Missing, changed or unsupported Ford
imports fail. The original SDK remains a separate stable public developer package.

The manifest records the source commit, packager digests, dependency contract,
toolchain, frontend digest, every file, each desk source, API version and saved
state version. Timestamps, ownership, modes and archive order are fixed. Build
reads committed source; uncommitted edits and unrelated files are excluded.
It refuses a packager that differs from the selected committed version.

The candidate includes no pier, key, cookie, account binding, project export,
test fixture, operator credential or host-specific path. It does not include a
Grid docket or external glob: the current frontend is served through native
Eyre routes. The package has a statically resolved import closure, but compilation
and actual installation on a separate desk remain unexecuted release gates.

## Build and inspect

Commit the reviewed packaging/source changes first. The existing verified kernel
cache must match the toolchain lock. Create an output directory under `.runtime`
and run, for example:

```sh
mkdir -p .runtime/releases
python3 scripts/package_release.py build --role home --output .runtime/releases/home-candidate.tar
python3 scripts/package_release.py build --role identity --output .runtime/releases/identity-candidate.tar
```

Build refuses to overwrite an existing output. It reports the archive SHA-256,
source commit and a `target_profile` declaration. Preserve the hash in a separately
reviewed release record. A hash obtained from the same untrusted download is not
publisher authentication; this foundation implements no signature or promotion.

## Verify offline

Supply the expected archive digest from that trusted record and a JSON file
declaring the intended target. The target has protocol `stead.release-target/1`
and the exact fields printed in `target_profile`: role, kernel Kelvin and commit,
runtime version and binary digest, API version, saved-state version and frontend
digest. Those declarations must be checked against the intended runtime and
release record; the build report is not a measurement of a running server.

```sh
python3 scripts/package_release.py verify \
  --archive .runtime/releases/home-candidate.tar \
  --sha256 "$TRUSTED_RELEASE_SHA256" \
  --target .runtime/releases/intended-home-target.json
```

Verification reads archive members in memory. It never unpacks or executes them.
It rejects mismatched target versions/frontend, corrupt content, missing or extra
files, altered standard dependencies, broken frontend pins, symlinks, traversal,
duplicate members, oversized inputs, noncanonical metadata and trailing data.
It also refuses a manifest that claims native qualification. A successful result
means **package integrity and declared compatibility only**. It is not approval
to install on a ship with existing state.

## Optional guarded clean-fake check

`scripts/release_install.py` is a separate native verifier. It first performs
the same archive/target verification, then stages regular candidate files in a
new private directory. It starts one fresh fake in a private network/filesystem,
with no preserved pier, current native source tree or credentials mounted. It
creates `%release-test`, imports only the candidate, checks raw Hoon/asset bytes
and typed Kelvin/bill values through Clay, locally installs the desk, checks the
selected agent's desk/liveness, and observes explicit stop/reload. It reaps the
fake and records actual checks and cleanup. It does not configure a company or
validate configured Home state, migrations, authentication or user workflows.

The commands follow the [official distribution guide](https://docs.urbit.org/build-on-urbit/userspace/dist/software-distribution)
and the exact pinned `new-desk`, `install` and `rein` generator sources. The
[distribution architecture](https://docs.urbit.org/build-on-urbit/userspace/dist)
requires local marks, including the packaged `%kelvin` and `%bill` marks.

Prerequisites are the committed verifier/helpers, a verified package and target,
the existing pinned runtime/kernel/pill and Git toolchain, a nonroot Linux caller
and an available shared native execution lock. This cold boot may take tens of
minutes. The verifier is bounded to one hour, one CPU affinity and the existing
50% CPU quota,75°C start and90°C stop policy. Its single fake uses the existing
2GiB loom address-space setting. It refuses a competing native run; it does not
stop the user's review session or change cooling settings.

```sh
PATH="$PWD/.runtime/tooling/git-2.55.0/bin:$PATH" \
python3 scripts/release_install.py \
  --archive .runtime/releases/home-candidate.tar \
  --sha256 "$TRUSTED_RELEASE_SHA256" \
  --target .runtime/releases/intended-home-target.json
```

Run each role separately and retain its exact artifact, verifier commit, native
check report and guard report. A host unit-test pass does not mean this native
command has run. Even a successful native report has `qualifies_phase: false`:
the remaining M4 install/upgrade/recovery/canary gates below are broader.

## Remaining installation and recovery gates

Before an installable beta claim, demonstrate clean installation of each role on
the pinned runtime, native route/mark behavior, bootstrap and access isolation,
and operator-controlled update/pin behavior. Test unavailable publishers, wrong
Kelvin/frontend/API versions, interrupted updates, every supported predecessor
and a nonauthor following the runbook. Define and verify canary/stable promotion
and any Grid launch metadata before advertising those paths.

This code artifact cannot restore project data. URB-100 must provide consistent
Git/Markdown/JSON exports plus authority evidence and reconstructed derived
indexes. URB-230 must prove supported state migration, mixed-version behavior,
interrupted recovery, invalidation of stale access and no repeated effects.
Before any recovery operation, preserve the checkpoint and loss-window evidence,
fence the old authority, and ensure no duplicate live ship identity. Do not equate
rolling back source with downgrading saved state. Stop, uninstall, data purge and
project restore remain distinct operations. Hosting, identity provisioning and
real release/canary promotion retain their existing owner and independent-review
gates. No such operational action is implemented or authorized by this package.

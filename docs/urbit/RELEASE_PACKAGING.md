# Offline desk packaging foundation

This implements a bounded **URB-220 packaging candidate**, alongside the M4
requirements in `ECOSYSTEM_PLAN.md`. Package build and verification are offline.
The optional native verifier starts a disposable test ship in an isolated
environment. See [local install evidence](#local-install-evidence) for its scope.

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
Grid docket or external glob. The current frontend is served through native
Eyre routes. The package has a statically resolved import closure.

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
fake and records actual checks and cleanup. The configured single-role HTTPS
extension below adds synthetic owner setup; paired authentication, business
workflows and migrations remain separate acceptance gates.

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

## Configured single-role HTTPS checks

The verifier now also stages four committed test-driver files separately from
the release package: the existing owner-local configuration/bootstrap and TLS
threads, plus their codec and delivery libraries. After verifying the candidate
installed on `%release-test`, it installs those test-only adapters on `%base`.
Their bytes and the Python TLS/transport helpers are bound to the verifier commit;
the application desk remains exactly the artifact. No current source-tree mount,
old certificate, credential history, application change or public network is used.

One synthetic role is owner-configured through the existing versioned marks.
Bootstrap must complete its existing watch/poke/fact/kick exchange with the exact
nonce and current incarnation. A fresh private CA and certificate are installed
in native Eyre. The verifier checks the owned TLS listener, CA and hostname, then
fetches every role asset over private loopback HTTPS and checks its exact length,
digest, MIME type and security headers. It never follows redirects or disables
certificate verification.

Independent denials cover wrong Host/Origin, unknown paths, query strings, wrong
methods, POST-to-asset, GET-with-body, Forwarded overrides and anonymous protected
API calls. Ordinary cleartext HTTP must redirect to the exact native HTTPS origin;
a spoofed cleartext Forwarded header must still be rejected. Home also returns its
public capabilities through the installed route. On app reload, requests must
remain unavailable until a new owner bootstrap; the incarnation must change and
all asset/boundary checks repeat. Partial HTTP failure evidence retains only the
bounded response metadata/digest, not response bodies or any certificate key.

This is a configured **single-role fixture**. Its report keeps
`paired_home_identity: false`, `browser_authentication: false` and
`qualifies_phase: false`. The extension needs its own native execution receipt;
the older eight-check install reports below do not prove these additional checks.
The next paired slice would run two distinct fresh fakes, install each verified
role, configure matching Home/member bindings and separate TLS hostnames, then
exercise real member approval, session/CSRF enforcement and revocation. It must
retain the native peer/startup fencing and cannot substitute an owner cookie or
synthetic authenticated HTTP request for that exchange.

## Narrow retry after a clean pre-install failure

The optional `--retry-clean .runtime/release-install-<prior-run>` argument, with
`--retry-clean-sha256` naming its explicitly reviewed stopped tree digest, can reuse a stopped fresh fake only for the audited descriptor-enumeration race
before installation. It requires the exact reviewed controller/helper provenance,
same package and toolchain, the precise three-command boot transcript, successful
clean exit/reaping, a stopped lease and a retired empty guard scope. Any desk
creation/install attempt, different failure, altered input, runtime lock, symlink,
hard link or special file rejects reuse. Other failures require a fresh run or
separate review; there is no automatic fallback or reuse of `.piers` state.

While holding the shared native execution lock, the verifier copies the original
into a newly owned disposable run and compares bounded hashes before/after copy.
The original stays stopped and unchanged. The child verifies the copied digest
again before boot and repeats native identity, Kelvin, namespace, capability,
socket ownership and package checks before any installation. The report records
`boot_mode: resumed-clean-checkpoint`, its prior evidence and digest, and
`fresh_boot_acceptance: false`. This can check installation from the resumed clean
baseline; it does not count as a new cold boot, an upgrade or recovery acceptance.

Use the same artifact, SHA-256 and explicit target as the prior attempt, adding
`--retry-clean` and `--retry-clean-sha256` to the existing verifier command. The shared lock and normal
thermal/deadline limits still apply. Partial copy failures remain private evidence
in their new run directory and never replace the original checkpoint.

## Local install evidence

On November 8, 2026, both role archives were built twice with identical bytes
from source `1ac28f7e5d1ef1cecd1b5699dc7dd47a2200e25a`. The native verifier
was `a293368ea0dd7e307194be98272b4e0f5ed5eebc`. It matched 56 installed desk
files per role, passed all eight native checks per role, observed explicit
stop and reload, and reaped both fakes cleanly. Home used a verified stopped
checkpoint after a descriptor-enumeration race on the first cold boot, before
desk creation. Identity started fresh. Both runs report `qualifies_phase: false`.

| Role | Archive SHA-256 | Native report SHA-256 | Boot |
| --- | --- | --- | --- |
| Home | `0ed0a28696a8446ab3c767a8023634074959d5b5a522a9e57c168503b6adbec2` | `36fdbce0bcd56224ef3d9dfe3324d4ae1974fc0562430d1c35d9db8bf4bb516c` | Stopped checkpoint |
| Identity | `7acfe6daf51db6c0f87b0fa8c90b19b261ae994e77ad222a50e6836c0bc39ce4` | `70a8fac555b4180e3e1176d4d68a0ba457dd60a7d18bda16f37ba9f9a8ce0a6f` | Fresh fake |

The archives and build checks are in local directory
`.runtime/releases/alias-verified-1ac28f7e5d1e/`. The exact native reports are
`.runtime/release-install-onuyfkoj/work/report.json` for Home and
`.runtime/release-install-pwffjn_5/work/report.json` for Identity. The initial
Home failure remains in `.runtime/release-install-bu8_udck/work/report.json`.
These runs cover isolated desk installation. A configured Home/Identity pair,
upgrades, state recovery and a canary remain separate gates.

## Remaining installation and recovery gates

Before an installable beta claim, demonstrate fresh-boot Home installation,
native route/mark behavior, bootstrap and access isolation, and operator-controlled
update/pin behavior. Test unavailable publishers, wrong Kelvin/frontend/API
versions, interrupted updates, every supported predecessor and a nonauthor
following the runbook. Define and verify canary/stable promotion and any Grid
launch metadata before advertising those paths.

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

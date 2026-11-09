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
Pinned Eyre adds an anonymous guest cookie to application responses. The verifier
recognizes only `urbauth-~zod` with a canonical, at-most-128-bit `@uv` value and
exact `Path=/; Max-Age=604800` attributes, as defined by that pinned kernel's
`+session-cookie-string`. Cookie values are redacted before recording headers;
other cookie shapes or attributes fail the check. The observed guest-cookie flag
is never authentication evidence. No cookie is stored or replayed, and outgoing
Cookie or Authorization headers are prohibited. Authenticated kernel cookies and
application session cookies remain outside this anonymous fixture.

This is a configured **single-role fixture**. Its report keeps
`paired_home_identity: false`, `browser_authentication: false` and
`qualifies_phase: false`. The configured Home checks have their own receipts
below, separate from the older eight-check install reports.
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

### Configured Home HTTPS verification

The Home artifact above also passed the extended single-role verifier from the
reviewed stopped checkpoint. The exact report is
`.runtime/release-install-2vpttgtk/work/report.json`, SHA-256
`a61793b7522ed1f5d02ee21b7b48df33810f2e9e9945527d3748b6ff24adf26c`.
The verifier source was `5651caa0a94babbd318a900d84a56bf84bf52dc4`.
It passed 13 checkpoints, matched nine HTTPS assets to their packaged bytes,
and verified 11 HTTP boundary outcomes both before and after reload. Reload
required a fresh owner bootstrap and changed incarnation before serving.
The run reaped the fake and reports `qualifies_phase: false`.

An earlier HTTPS probe reached the first correct asset and then rejected Eyre's
guest cookie. That verifier failure is retained locally under
`.runtime/release-install-473r_aoe/`. The corrected verifier identifies the
pinned guest cookie, redacts its value and keeps the test request anonymous.

The same Home archive passed all 13 checks from a fresh fake using verifier
`716a96b559ba9ed551f67c216be6607b03b0355c`. The native report is
`.runtime/release-install-o8t9xohg/work/report.json`, SHA-256
`884ba734df79ea04602a27f0ea3bea83ed0cfc5a3a32b30a8c2813782f2e968c`.
It matched 56 installed desk files and repeated the nine asset and 11
boundary checks across reload. It shut down and reaped the fake cleanly.
The guarded run took 669.720 seconds and peaked at 58°C. A preceding fresh
attempt stopped before boot because the HTTPS flag split the pier creation
argument. The corrected launcher preserves the create flag and path together.

## Remaining installation and recovery gates

Before an installable beta claim, qualify configured Identity and paired
Home/Identity authentication, access isolation and revocation. Verify
operator-controlled update/pin behavior, unavailable publishers, wrong
Kelvin/frontend/API versions, interrupted updates, every supported predecessor
and an independent agent or operator following the runbook. Define and verify canary/stable promotion
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

## Stopped Home file round trip

`scripts/release_recovery.py` rehearses an offline backup and restore from
the exact verified fresh Home installation above. Supply the archive and its
trusted digest, the target, the retained native report digest and the retained
guard report digest. It checks the installed desk inventory against the
archive, the guard's isolated workspace and stopped lease, retirement of the
owned scope and absence of a runtime lock. It refuses concurrent guarded
native execution.

```sh
python3 -B scripts/release_recovery.py \
  --prior .runtime/release-install-o8t9xohg \
  --archive .runtime/releases/alias-verified-1ac28f7e5d1e/home.tar \
  --sha256 0ed0a28696a8446ab3c767a8023634074959d5b5a522a9e57c168503b6adbec2 \
  --target .runtime/releases/alias-verified-1ac28f7e5d1e/home-target.json \
  --install-report-sha256 884ba734df79ea04602a27f0ea3bea83ed0cfc5a3a32b30a8c2813782f2e968c \
  --guard-report-sha256 e5e14cd8ab0269311180fcd2a9e6e42ba408f67f4546d4f7597f42dc9256ad40
```

The script creates a new private directory under `.runtime` containing
`backup`, `restored`, and a receipt. The bounded copier admits only owned
regular files and directories and verifies all three tree fingerprints.
The command above passed locally on November 9, 2026. The original, backup
and restored trees each had 611 files and 253,077,260 bytes, with fingerprint
`d66931183e5672721cfa8fa1ceeaa579b36bbb11c10860d2c5eb9efec518f5a0`.
The local receipt is `.runtime/release-recovery-7gvmskob/report.json` with
SHA-256 `4e73d8e08032ae736beafa984e54ff6b67e5b532703d3cb6fcd4cadf48117d8f`.

Keep both copies offline and private. An interrupted copy retains its failure
receipt and partial data. These copies prove file transfer only. They do not
establish native startup, application state recovery, historical pier
integrity since shutdown, network continuity or production backup encryption.
The [Phase 5 runbook](PHASE5_DEPLOYMENT.md) keeps those gates separate.

## Isolated boot of a restored Home clone

With the reviewed verifier committed, add the copy receipt inputs to the same
command and use the pinned Git toolchain. This starts one fake Home under the
existing runtime guard, with a 15-minute deadline. It copies a new pier under
`.runtime/release-restore-boot-*`. The original, backup and restored files
remain stopped and are checked against the reviewed fingerprint before and
after the native run.

```sh
PATH="$PWD/.runtime/tooling/git-2.55.0/bin:$PATH" \
python3 -B scripts/release_recovery.py \
  --prior .runtime/release-install-o8t9xohg \
  --archive .runtime/releases/alias-verified-1ac28f7e5d1e/home.tar \
  --sha256 0ed0a28696a8446ab3c767a8023634074959d5b5a522a9e57c168503b6adbec2 \
  --target .runtime/releases/alias-verified-1ac28f7e5d1e/home-target.json \
  --install-report-sha256 884ba734df79ea04602a27f0ea3bea83ed0cfc5a3a32b30a8c2813782f2e968c \
  --guard-report-sha256 e5e14cd8ab0269311180fcd2a9e6e42ba408f67f4546d4f7597f42dc9256ad40 \
  --boot-copy .runtime/release-recovery-7gvmskob \
  --copy-report-sha256 4e73d8e08032ae736beafa984e54ff6b67e5b532703d3cb6fcd4cadf48117d8f
```

The native controller checks the app and the configured v3 saved vase in the
loopback-only namespace, obtains a fresh owner acknowledgement and repeats
the package and native TLS route checks. The packaged assets and capabilities
must be available, and protected queries must require a session. The verifier
also checks the saved-vase fingerprint around bootstrap and checks the clone
again after it is stopped and reaped. `recovery-report.json` is written only
after the native proof and the retained-tree checks both pass.

The fixture contains Home configuration and a member binding. Member sign-in,
accepted business record readback, supported upgrades and live continuity
require separate evidence. A saved-vase fingerprint captured inside the clone
does not substitute for a reviewed pre-stop application fingerprint.

On November 9, 2026, the command passed all 12 native checks for the historical
`1ac28f7e5d1ef1cecd1b5699dc7dd47a2200e25a` Home payload. The verifier ran from
`c6e10865ac1d7c5c016cb44c63b3ccf41dbee0aa`. The guard completed in 25.784 seconds
and peaked at 46°C. The new incarnation preserved the v3 saved-vase digest
`e69fcb11ddc4cb0df4023a1747413bdf9df7390adfdfb33f2af8c662c64949c7`.
Nine native TLS assets matched and 11 HTTP boundary checks passed. The clone
stopped and was reaped, and host and sandbox agreed on its stopped fingerprint
`ac59a7623a8857de83c5fce3f4671826751758c407b50c9fc74e8b2e56892bac`.
All three retained trees still matched the original reviewed fingerprint.

| Local evidence | SHA-256 |
| --- | --- |
| `.runtime/release-restore-boot-1nq6z31n/recovery-report.json` | `3c8726018f3ded725a8f9b1bdd08b1e92a948c94c47a79a792eceaf7cd2d6307` |
| `.runtime/release-restore-boot-1nq6z31n/work/report.json` | `46b75b74248d6659da0d2f92a89ab7513b6984a614a95ab158a8a53fd5ae9cb2` |
| `.runtime/execution-runs/release-restore-boot-9kjjs8hx/report.json` | `886e519159acab8dce87e074429f89776f3477e052fba796b4fc97e63ee3d396` |

## Same-schema Home asset upgrade rehearsal

The clone command also accepts a distinct target archive for a narrow
asset-only upgrade. Both Home archives must pass package verification and
agree on native code, toolchain, release contract, API and saved schema. The
rehearsal suspends the isolated clone at the independently reviewed v3
fingerprint, replaces only generated inventory and content-addressed assets,
and compares the full mounted and Clay target contents. It removes exact
obsolete paths with `|rm` and checks their absence at the current Clay
revision. [Urbit filesystem](https://docs.urbit.org/user-manual/os/filesystem)

After reload it requires a 503 before fresh bootstrap and then verifies the
exact target assets and HTTP boundaries. It records the full v3 saved-vase
digests and compares the authoritative database noun before suspension, after
reload and after bootstrap. The versioned save envelope also contains a
projection that Home rebuilds on load. The stopped clone and retained copies
must match their verified checkpoints before `upgrade-report.json` is written.

```sh
PATH="$PWD/.runtime/tooling/git-2.55.0/bin:$PATH" \
python3 -B scripts/release_recovery.py \
  --prior .runtime/release-install-o8t9xohg \
  --archive .runtime/releases/alias-verified-1ac28f7e5d1e/home.tar \
  --sha256 0ed0a28696a8446ab3c767a8023634074959d5b5a522a9e57c168503b6adbec2 \
  --target .runtime/releases/alias-verified-1ac28f7e5d1e/home-target.json \
  --install-report-sha256 884ba734df79ea04602a27f0ea3bea83ed0cfc5a3a32b30a8c2813782f2e968c \
  --guard-report-sha256 e5e14cd8ab0269311180fcd2a9e6e42ba408f67f4546d4f7597f42dc9256ad40 \
  --boot-copy .runtime/release-recovery-7gvmskob \
  --copy-report-sha256 4e73d8e08032ae736beafa984e54ff6b67e5b532703d3cb6fcd4cadf48117d8f \
  --upgrade-archive .runtime/releases/astra-candidate-8yCV5UMh/home.tar \
  --upgrade-sha256 18b73461298eef7f0697dd90ff4a82960e23ac4bd59dd8ab440060d7029ba5ab \
  --upgrade-target .runtime/releases/astra-candidate-8yCV5UMh/home.target.json \
  --saved-home-sha256 e69fcb11ddc4cb0df4023a1747413bdf9df7390adfdfb33f2af8c662c64949c7
```

This pair changes the Home CSS and JS and their generated inventory. The
reviewed v3 digest comes from the preceding isolated recovery. A stopped or
failed attempt retains its disposable workspace and reports. Start a new
clone after reviewing the failure. Cross-schema migration, interrupted upgrade
recovery, installed Identity, accepted business record readback and live
continuity each require separate evidence.

The first attempt on November 9 reached exact target Clay bytes but left an
obsolete asset in Clay after a Unix-only removal. The explicit Clay removal
retry verified both obsolete paths were gone and observed the expected 503
after reload. It stopped when the full saved-vase digest changed from the
reviewed `e69fcb11ddc4cb0df4023a1747413bdf9df7390adfdfb33f2af8c662c64949c7`
to `7bc5d9ab0d0c504064eb1645d61925a851078a8940de8ab62972cb8e1d1fe0bd`.
Both clones stopped cleanly. The retained trees still matched the file-copy
receipt. The full-vase difference did not identify which saved component changed.

| Local failure evidence | SHA-256 |
| --- | --- |
| `.runtime/release-asset-upgrade-e4cghu9_/work/report.json` | `0ca22c2c92800a0e87cb9f0af918fb9f15152a354a3f9ebae0ee9420988444c3` |
| `.runtime/execution-runs/release-asset-upgrade-jyqvsezo/report.json` | `8e7bd13a59c17057a063ef024f64d3661d808bc7bfa4e15d503d016e0c9905dd` |
| `.runtime/release-asset-upgrade-w9fbrb7o/work/report.json` | `b9449782a7abb40d0c015a1256a08fa854ad271fcc2c8228ffe0c1af5139256d` |
| `.runtime/execution-runs/release-asset-upgrade-t130bm0_/report.json` | `02fba8bd19c710214e0a6ad4771c7297f6c57a8ab093e386fcc3918a3b59ece5` |

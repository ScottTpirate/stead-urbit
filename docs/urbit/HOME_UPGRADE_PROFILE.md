# Local Home v3 upgrade rehearsal

The offline verifier upgrades a fresh copy of a configured synthetic Home
from a reviewed v3 desk to a Code-capable Home archive declaring a maximum
saved-state version of v4 or v5. The selected archives must share the exact
kernel, Vere and API profile. The verifier checks the target's native agent,
its dependency closure and its frontend bytes. In this transition, a Home
with existing v3 state and no Code repositories continues to save v3. The
package maximum does not force a state rewrite.

## Controlled interruption

The runner verifies the previous native install report, its retired guard,
the retained file-copy receipt and the reviewed v3 saved-vase digest. It
boots a new copy under a loopback-only guard, suspends Home, and compares the
complete v3 vase with the reviewed fingerprint. It commits the target desk
in Clay while Home stays suspended and checks every target file and removal.

The interruption occurs after the target desk commit and before activation.
The runner stops and reaps the first Vere process, seals the stopped pier,
and checks that fingerprint before starting a second Vere process in the
same private namespace. The restarted clone must still have Home suspended
and retain the previous v3 vase. The runner then enables Home, requires HTTP
503 until fresh owner bootstrap, verifies the new Code endpoint's anonymous
denial, and checks the exact packaged routes. The authoritative database
fingerprint must agree before staging, after reload and after bootstrap.
Rebuilt projection bytes may change.

The run reports the controlled stop and restart separately from the final
clean shutdown. A failure leaves its private workspace for inspection.
For a fresh attempt, start again from the reviewed stopped source and
verified copies. An arbitrary partial staging directory is outside the
supported resume profile.

## Reproduce the local rehearsal

Use the [original install and copy receipts](RELEASE_PACKAGING.md#same-schema-home-asset-upgrade-rehearsal).
The current checkout must have committed verifier and helper bytes. Supply a
verified target Home archive and its target profile. Use a trusted SHA-256
for each artifact and receipt. This runs one disposable Home at a time under
the existing native guard.

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
  --upgrade-mode home-v3 \
  --upgrade-archive "$TARGET_HOME_ARCHIVE" \
  --upgrade-sha256 "$TARGET_HOME_SHA256" \
  --upgrade-target "$TARGET_HOME_PROFILE" \
  --saved-home-sha256 e69fcb11ddc4cb0df4023a1747413bdf9df7390adfdfb33f2af8c662c64949c7
```

On success, retain the emitted `upgrade-report.json`, the referenced native
and guard reports, and the exact target archive and profile. The verifier
checks that the original, backup and restored source trees remain unchanged.

The historical checkpoint covers a configured local Home. Populated
business-record replay, migration of existing Code repositories, interruption
inside a Clay or Gall event, arbitrary power loss, kernel changes, and a
live multi-ship upgrade require their own evidence.

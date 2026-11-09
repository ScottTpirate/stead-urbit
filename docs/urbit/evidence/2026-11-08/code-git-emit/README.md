# Native outbound Git pack evidence

Observed on 2026-11-08 local / 2026-11-09 UTC. Run
`20261109T025922Z-d8tf_cjn` passed all **39 expected checks**:

- 28 exact native unit arms, each returning an empty tang.
- The deliberate failing tang and malformed compiler controls were detected.
- Nine checks cover the native SHA-1 pack envelope, stock `index-pack --strict`,
  `fsck --full --strict`, exact four-object inventory, exact blob/tree/commit/tag
  bytes and original OIDs, and rejection of a corrupted trailer.

The blob includes two trailing zero bytes. The fixture contains a valid empty
tree, commit and annotated tag; its extra blob is intentionally unreferenced.
Stock Git consumes the actual native-emitted `native.pack`, not a Python pack.
This proves bounded encoding/readback, not an authorized graph selection,
installed service, clone/fetch route, accepted Stead write or completed phase.

The unchanged-source run completed in **7.027 seconds** with 50% CPU quota on
CPU 19, 75°C admission and 90°C stop. Highest sampled temperature was **40°C**.
Its owned scope was then observed inactive/dead and unloaded. The ordinary
shared execution lock and 120-second deadline remained in force. No ship was
booted. The stock fixture was isolated from the network, user home and live
authority state.

`inputs.json` binds exact source/helper/toolchain/Git hashes before and after.
The source files were uncommitted; the checkout commit alone does not bind them.
`report.json` contains native outputs and stock commands/results. `guard.json`
and `scope.json` retain observed control and cleanup state. Generated evaluator
inputs, the executed driver, module/tests and exact output pack are retained.
`history.json` and `history/` preserve the preceding wrapper and fixture compiler
failures instead of counting them as passes.

Observed fixed command from the canonical checkout:

```sh
PATH=/tmp/stead-local-preview.umQhNO/tools/usr/bin:/usr/bin:/bin python3 scripts/urbit/code_git_emit_check.py
```

The temporary Git path is machine-specific. Reproduction requires the pinned
Git 2.55.0/toolchain cache, user systemd, thermal sensors and bubblewrap. The
driver accepts no caller-selected inputs or external commands. Maximum-size
metadata admission was tested; maximum-size native hashing/emission timing was
not measured. See the [emitter profile](../../../CODE_GIT_EMIT_PROFILE.md).

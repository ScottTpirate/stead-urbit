# Pure native Git foundation evidence

Observed on 2026-11-08 local / 2026-11-09 UTC. Final run
`20261109T015607Z-taztv6wj` passed all **128 expected checks**. This is pure
Vere evaluation and synthetic stock-Git subprocess interoperability. It boots
no ship, installs no service, accepts no repository write and closes no phase.

| Observed checks | Count |
| --- | ---: |
| Packet framing native unit arms | 23 |
| Object hashing/OID/ref syntax native unit arms | 18 |
| Outer pack envelope native unit arms | 12 |
| Candidate ref acceptance native unit arms | 15 |
| Receive command header native unit arms | 45 |
| Deliberately failing tang/compiler controls | 3 |
| Stock-Git interoperability assertions | 12 |
| Total | 128 |

Every positive native arm returned an empty tang. The two intentionally failing
tangs returned nonempty results, and malformed Hoon was rejected. The 12 stock
checks cover native `ls-refs` request framing and decoding of the stock response,
exact blob/tree/commit/annotated-tag bytes and OIDs, stock `fsck --full --strict`,
28 ref-name comparisons, a stock-created pack envelope, corrupt trailer rejection
and independent stock `index-pack --strict` checks. The stock pack is not a
native decompression, delta, reachability or acceptance test.

The guard completed in **30.091 seconds** with a 50% CPU quota on CPU 19,
`cpu.max = 5000 10000`, 75°C admission and 90°C stop. Highest sampled temperature
was 36°C. The owned scope was subsequently observed inactive/dead and unloaded.
The guard retained its ordinary shared lock and a three-minute deadline.
No other runtime was started by this runner.

`inputs.json` records exact before/after source hashes, toolchain/helper/Git
identities and the checkout commit. The foundation files were uncommitted at
execution; their matching source hashes are the source binding, not an assertion
that the checkout commit already contains them. `report.json` contains actual
native output and stock commands/results. Module JSON files preserve separate
unit results. `guard.json` and `scope.json` contain observed execution controls.
`history.json` retains the earlier wrapper, compiler and fixture failures instead
of treating them as passes. `host-tests.txt` records 10 passing host-only checks.

Observed command from the canonical checkout, with the verified Git 2.55.0
binary first on PATH:

```sh
PATH=/tmp/stead-local-preview.umQhNO/tools/usr/bin:/usr/bin:/bin python3 scripts/urbit/code_git_vectors.py
```

The temporary Git location is specific to this machine. Reproduction requires
the checked toolchain versions, prepared cache, host thermal sensors, user
systemd and bubblewrap; the runner verifies its origin and pinned prerequisites.
It accepts no arbitrary input paths or external commands. Inputs are staged
read-only inside a private network namespace with only synthetic output writable.

Outstanding boundaries include object expansion/deltas, object graph and
reachable-object isolation, authenticated transport, quarantine/storage/jobs,
final current-policy authorization and atomic authoritative receipt, native
restart/recovery, actual clone/fetch/push and independent deployment qualification.
The receive policy returns a candidate map only. Pack `%envelope` proves only
its outer header/trailer; a checksum-valid garbage entry is deliberately present
in the unit corpus to demonstrate that limitation. See the
[packet profile](../../../CODE_GIT_PACKET_PROFILE.md) and
[object/pack profile](../../../CODE_GIT_OBJECT_PROFILE.md).

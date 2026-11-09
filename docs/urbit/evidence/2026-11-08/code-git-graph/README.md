# Native derived graph evidence

The fixed diagnostic `.runtime/graph-dev-b_7a5oe_` passed **31 expected checks**:
29 named native arms returned empty tangs, the deliberately failing control
returned three tang lines, and malformed Hoon was rejected. Compiler rejection
was identified from its actual diagnostic; Vere returned process status zero
for that negative control.

The cases cover object/tree/commit/tag derivation, bounded closure, exact
commit/path blob reads, missing/wrong-kind/corrupt/forbidden/unreachable objects,
unsafe or duplicate tree names, tree ordering, unsupported symlinks and selected
root/path/queue/visit/byte bounds. Some budget cases construct a bounded work
state directly. Maximum capacities and exhaustive malformed Git metadata were
not benchmarked or qualified.

The guarded native evaluator completed in **5.019 seconds** on CPU 19 with
50% quota. Maximum sampled temperature was 50°C. Admission remained 75°C and
stop remained 90°C; the shared lock, 45-second overall deadline and 30-second
per-evaluation timeout were unchanged. Its own scope was subsequently observed
inactive/dead. No ship was booted and no network was available inside the run.

[receipt.json](receipt.json) binds the four exact native source inputs before
and after execution, all observed results, helper/runtime identity, generated
Hoon and diagnostic scripts, raw reports and guard proof. Current source hashes
matched at receipt creation. New graph files were uncommitted; the commit
recorded at receipt creation is context, not execution or inclusion proof.
The one-use diagnostic was separate from the official vector runner.

Three earlier native compilation failures remain preserved with raw paths,
source/input digests and diagnostics: a narrowed nonempty queue becoming empty,
a mixed queue tail inferred as leave-only, and a character aura mismatch.
They were resolved with explicit result/list molds, explicit queue state
construction and the pinned standard ASCII-casefold helper. No failed attempt
was counted as a passing test.

Observed command, with verified Git 2.55.0 first on PATH:

```sh
PATH=/tmp/stead-local-preview.umQhNO/tools/usr/bin:/usr/bin:/bin python3 .runtime/graph-dev-b_7a5oe_/run.py
```

This is pure graph/helper evidence and does not qualify a phase, a running Git
server, `git fsck --strict` equivalence, final authorization or committed writes.
See the [integration profile](../../../CODE_GIT_GRAPH_PROFILE.md) for callback
scope, fresh authorization requirements and exact limits. Raw output remains
under the ignored runtime paths recorded in the receipt; the checked receipt
preserves the successful native output and prior failure diagnostics.

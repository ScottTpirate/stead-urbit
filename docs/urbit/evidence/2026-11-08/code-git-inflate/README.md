# Native zlib inflater evidence

Fixed-target run `20261109T024001Z-0ye3oq6a` passed **49 expected checks**:
47 native test arms returned empty tangs, a deliberately failing tang remained
nonempty, and malformed Hoon was rejected. No unexpected native failure occurred
in this inflater run. The source binding is independent of other module results.

Twelve exact positive fixture pairs were independently rechecked with stock
Python zlib. Native cases cover stored, fixed and dynamic streams; binary and
trailing-zero bytes; absolute offsets, trailing bytes and concatenated streams;
overlapping and cross-block matches; and the 256-block boundary. Negative cases
cover headers/dictionaries, checksum/truncation, output limits, reserved codes,
malformed trees/repeats and work guards. Maximum repository-size capacities
were not benchmarked; work guards are partly exercised through internal helpers.

The guarded run completed in **5.019 seconds**, using CPU 19 at 50% quota.
Maximum sampled temperature was 35°C. The existing 75°C admission, 90°C stop,
shared native lock and three-minute deadline were unchanged. Its own scope was
subsequently observed inactive/dead. No ship was booted.

[receipt.json](receipt.json) records exact before/after source hashes, all named
checks, pinned toolchain/helper identity and raw report paths with digests.
Current hashes matched at receipt creation. New source was uncommitted at run
time; the recorded checkout commit provides context, not inclusion proof. The
focused target neither stages nor compiles the concurrently developed resolver.
Twelve host-only parser/inventory tests pass separately.

Observed command, with verified Git 2.55.0 first on PATH:

```sh
PATH=/tmp/stead-local-preview.umQhNO/tools/usr/bin:/usr/bin:/bin python3 scripts/urbit/code_git_vectors.py inflate
```

This is pure inflater evidence. Complete pack reconstruction, authorized base
selection, object graphs, quarantine, final acceptance, native restart/recovery
and server operation require separate evidence. The
[public contract](../../../CODE_GIT_INFLATE_PROFILE.md) states exact consumed
byte semantics and admission limits.

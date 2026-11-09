# Native pack entry and delta evidence

Final run `20261109T021554Z-s2qto4im` passed **211 expected checks**:
192 positive native unit arms, three deliberately failing controls and
16 stock-Git assertions. The new native modules contribute 32 entry-header,
32 delta-application and 15 review-proof arms. All returned empty tangs.

Stock Git produced six-entry REF and OFS packs, each containing five real
deltas. Native headers matched their types, declared sizes, base references
and compressed-data offsets. Native application of all ten delta programs
reproduced the exact original 34,816-byte bodies and SHA-1 OIDs. The independent
host oracle and stock `index-pack --strict` checked the fixtures separately.
The native comparison receives host-inflated delta programs: **native zlib
inflation and complete pack reconstruction remain unimplemented**.

The guarded run completed in 101.267 seconds on CPU 19 at 50% quota; maximum
sampled temperature was 58°C. Existing 75°C admission, 90°C stop and three-minute
deadline were unchanged. Its owned scope was then observed inactive/dead.
Eleven host parser controls pass separately.

[receipt.json](receipt.json) binds exact before/after source hashes, the pinned
toolchain and all raw report paths/digests. Current source hashes matched at
receipt creation. New helpers were uncommitted when evaluated, so the recorded
checkout commit is context rather than source inclusion proof. Raw outputs
remain in the ignored local `.runtime/code-git-vectors/` directories.

The previous attempt `20261109T021403Z-9kbeqg9g` passed 207 checks, then rejected
a generated Hoon fixture because decimal offset `2440` required `2.440`.
The receipt retains that failed assertion, compiler diagnostic, input/report
hashes and corrected generator binding. It is not counted as a passing run.

This evidence proves exercised pure interfaces only. Header parsing does not
prove entry-boundary membership; delta application does not resolve or authorize
bases; review proof emits a candidate only. Native inflation, full pack/graph
validation, quarantine and budgets across jobs, final authoritative acceptance,
network transport, restart/recovery and deployment qualification remain separate.
See the [entry/delta contract](../../../CODE_GIT_PACK_ENTRY_PROFILE.md) and
[earlier foundation evidence](../code-git-foundation/README.md).

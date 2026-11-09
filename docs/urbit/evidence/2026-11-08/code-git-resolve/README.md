# Native pack reconstruction evidence

Run `20261109T025937Z-ppw29_ni` passed all 221 checks. The corpus retains the
packet, object, ref, wire and review checks. It also reconstructs both stock Git
REF and OFS packs through native inflation and staged delta resolution.
Each object matches its original SHA-1, kind and bytes. Stock Git and the host
oracle check the fixture packs independently.

Eight additional native fixtures cover the empty pack, a wrong declared count,
a corrupt zlib trailer within a checksum-valid pack, a wrong inflated size,
an OFS pointer inside an entry, and thin-pack reads with a missing, incorrect
or verified base. The verified external base stays outside the candidate
inventory. The fixture reader stands in for the repository-scoped reader.

The shared execution guard completed in 90.238 seconds with a maximum sampled
CPU temperature of 46°C. It used the existing one-CPU, 50% quota and thermal
limits. The 22 source file hashes matched before and after. The earlier test
module wrapper timed out. Its source and transcript are retained in
`.runtime/code-git-vectors/20261109T025511Z-2a1r5acs/`. The passing run uses
direct native composition and evaluates each expected result explicitly.

| Local receipt | SHA-256 |
| --- | --- |
| `.runtime/code-git-vectors/20261109T025937Z-ppw29_ni/inputs.json` | `52cd7bc231140ff0a82a22b22e3a6de08582de4f3abc0d1edce80da4859b75d9` |
| `.runtime/code-git-vectors/20261109T025937Z-ppw29_ni/output/report.json` | `cf3f5f2652b88c19c945a22de3bd477c0dbfa5d829d9ba8b7c55a0f6fe928d84` |

Reproduce with the pinned Git executable first on PATH and
`python3 -B scripts/urbit/code_git_vectors.py`. The run exercises pure native
code and synthetic stock Git processes. Its `qualifies_phase` field remains
false. Git transport, final authorization, persistence and application-level
ref transactions still require native service evidence.

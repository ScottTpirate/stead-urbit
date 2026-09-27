# Pinned development inputs

The executable lock is [toolchain.lock.json](../../specs/urbit/toolchain.lock.json),
resolved September 12, 2026. The original `.example.json` remains unresolved planning
metadata and is never executed. Downloads and extracted binaries/source are checked
before the harness executes them; no floating desk update runs in the fixture.

| Input | Pin | Checksum source |
|---|---|---|
| Vere | `vere-v4.6`, commit `8ddc4b786979574dbfcb655e3db1b634f658d0de` | GitHub asset SHA-256; extracted binary independently hashed |
| Arvo/base source | `408k-2`, commit `5a187fededc4582a34fcd6055c67bb63e0917b94` | Immutable source archive locally hashed, full extracted tree hashed |
| Brass boot pill | Same kernel commit, 23,389,629 bytes | Exact SHA-256 from pinned Git LFS pointer |
| Node / npm | `24.21.0` / `11.19.0` | Official Node SHASUMS256.txt; extracted Node binary hash |
| Frontend lock | `web/toolchain/package-lock.json` | SHA-256; deliberately contains no UI or dependencies |
| Stock Git | `2.55.0` | Actual host version; executable identity in test evidence |
| Smoke corpus | `stead.synthetic-counter/0` | Exact checked-in corpus SHA-256 |

Exact URLs and all archive/extracted hashes are in the lock. The kernel download's
hash is a local integrity measurement, not a signed upstream build attestation.
Node's checksum-file signature was not verified. This is reproducible input
selection and tested compatibility, not a supply-chain or runtime security audit.

Vere 4.6 and kernel 408k-2 were the current published releases found during this
inspection. The pinned brass pill is supplied with `-B`, and the pinned kernel/base
source with `-A /kernel/pkg/arvo`; the pill alone is not claimed to contain the
final source. Every fake boot must answer `zuse` with `%408`. The native smoke
compiles our agent and thread against that actual state. Development uses the
mounted disposable `%base` desk, with default-agent, Spider and strandio from this
kernel source. This is not yet a self-contained distribution desk.

The kernel tree includes intentional relative aliases into base-dev. Source
verification hashes each symlink's target text and every target file in the full
extracted tree; absolute/out-of-tree/broken aliases fail. Stopped pier seeds permit
no symlinks or special files. Archive hashes alone do not authorize a modified
extracted executable.

The administrative control profile is documented by the pinned
[Vere conn source](https://github.com/urbit/vere/blob/8ddc4b786979574dbfcb655e3db1b634f658d0de/pkg/vere/io/conn.c).
Khan `%fyrd` runs asynchronous probes over private Unix sockets. The same pinned
binary's pure `eval --loom 29 -jn` / `-ckn` handles jam/cue, with bounded Newt frames
and exact terminal application outcomes checked by the harness. Lens is used only
for local synchronous desk administration and readiness. See TEST_RESULTS.md for
its observed asynchronous failure and the retained reproducer.

Primary release records: [Vere 4.6](https://github.com/urbit/vere/releases/tag/vere-v4.6),
[408k-2](https://github.com/urbit/urbit/releases/tag/408k-2),
[Node 24.21.0](https://nodejs.org/dist/v24.21.0/SHASUMS256.txt).
The Urgit evaluation has its own candidate/import lock and is not a dependency of
`stead-home`.

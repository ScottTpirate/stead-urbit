# Git source for external build workers

The Home accepts a reviewed revision on its protected default ref. A trusted
source custodian passes the exact merge receipt, proposal revision, selected
manifest digest, ref and commit OID to
[`git_pack_build_source.export`](../../scripts/urbit/git_pack_build_source.py).
The authorization callback checks that exact source before reading the pack
and again before publishing. The exporter verifies the retained pack and its
Git closure using stock Git with isolated configuration. It reads the exact
tree without a checkout and uses private no-replace publication.

| File | Contents |
| --- | --- |
| `source.json` | `stead.git-build-source/1`, project scope and epoch, snapshot and exact Git commit and tree OIDs, receipt and its SHA-256, proposal revision, archive length and SHA-256, and ordered directory and blob records. Each blob carries its original Git OID, mode, size and SHA-256. |
| `source.tar` | Uncompressed deterministic PAX archive of the same tree. File mode is preserved. Archive timestamps and numeric owners are zero. |

The export bounds each file to 16 MiB, total file bytes to 128 MiB, and the
tree to 8,192 entries. It accepts UTF-8 paths, regular files and directories.
Symlinks, submodules, path collisions and unsafe path spellings cause refusal.

Supply the worker a read-only copy of both files and the trusted `source.json`
SHA-256 through a separate authenticated channel. The verification command
needs no Git binary, networking, Home identity, or checkout directory.

```sh
python3 -B scripts/urbit/git_pack_build_verify.py "$PRIVATE_SOURCE_DIR" \
  --sha256 "$TRUSTED_SOURCE_MANIFEST_SHA256"
```

The verifier checks the exact canonical manifest, receipt scope and digest,
each archive header and size, every blob's Git OID and SHA-256, and the
reconstructed Git directory tree OIDs. It emits the bounded
`stead.build.verify-source-archive/1` result on stdout. The commit OID comes
from the pinned source record. The pack custodian resolves and verifies the
original commit before export. Source verification reads bytes without
extracting files or executing project code. The Home still needs an assigned
build job, an independently authorized attempt and explicit acceptance of its
result before it can record a build outcome.

## Isolated automation command

Use [`git_pack_build_integrity.py`](../../scripts/urbit/git_pack_build_integrity.py)
on an unprivileged Linux worker with Bubblewrap. Give it a private canonical
JSON job, its independently trusted SHA-256, and the source directory. The
job has these four fields, with a final LF after canonical JSON serialization.

| Field | Required value |
| --- | --- |
| `protocol` | `stead.build.source-integrity-job/1` |
| `job_id` | A valid UUIDv7 |
| `recipe` | `stead.build.verify-source-archive/1` |
| `source_manifest_sha256` | The trusted digest of `source.json` |

```sh
python3 -B scripts/urbit/git_pack_build_integrity.py \
  --job "$PRIVATE_JOB" --job-sha256 "$TRUSTED_JOB_SHA256" \
  --source "$PRIVATE_SOURCE_DIR"
```

The launcher binds the open job, source files, and reviewed verifier modules
read-only by descriptor. The worker checks distinct namespaces, read-only
mounts, loopback-only networking, and the absence of capabilities. The launcher
rechecks the original paths and inodes before emitting bounded canonical
`stead.build.source-integrity-result/1` evidence. The result includes the exact
job digest and the digest of the verifier result. It contains no credentials
and performs no job admission, repository changes, or release actions.

## Local evidence

The retained synthetic reviewed snapshot `2652605332d2fb5b32f67b40c855518e41d1289a5a9b4f17438aecbeba74e6c1`
contained 7,805 objects. Pinned Git 2.55.0 exported its exact tree of 3,332
entries and 2,786 files in 2.189 seconds on one low-priority local CPU. The
export contained 105,656,221 file bytes in a 108,308,480-byte archive. The
source manifest SHA-256 was `f45d14639dd4325d66933c5d4d6aea2687fc98c0666bc22607766b53907f772a`.
The native fixture confirmed the protected-branch promotion but retained no
receipt identifiers in its report. This export used explicitly synthetic
request and proposal IDs. Its private report,
`.runtime/accepted-source-export-Tk25S3vb/report.json`, has SHA-256
`301800586de64bcb7f1e2dfe35f7b42a39e7c9dee31c53bf9c36e6da8023fb45`.

A separate verifier process read the same archive in distinct user, mount,
PID and network namespaces with read-only input, no capabilities and only
loopback. It matched all 2,786 file OIDs and 546 directory OIDs in 0.302 seconds.
The verification result SHA-256 was
`667cca509390035a8c489f13b80d65e3495377c2b19fc2041a074f4a933fd5a6`.
The private receipt `.runtime/accepted-source-export-Tk25S3vb/offline-verification.json`
has SHA-256 `e90d384eb458a2eaf36d756d8ef337825786c9a901ef83ac3655d251a69df2dc`.

# Minimum native Git object profile

`native/core/desk/lib/stead-git.hoon` is an original pure implementation for
URB-040/050's document-container subset. It uses the pinned Hoon SHA-1 primitive
and the [Git object format](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects).
No Urgit source is used. This module constructs bytes; the home owns current
authorization, object reachability, aggregate storage limits and atomic acceptance.
It is not a Smart HTTP server, pack parser, forge or general object validator.

## Interface and bytes

```hoon
+$  octets  [length=@ud data=@]
+$  object  [kind=@tas body=octets oid=@ux]
```

`data` is a little-endian atom containing exactly `length` bytes. Zero bytes at
the end of the byte sequence remain significant even when the atom's measured
size is shorter. `[2 97]` means bytes `61 00`, and `[2 0]` means `00 00`.
Data with bits beyond the declared width is rejected. Bodies are bounded to
8,388,608 bytes; the home applies its separate aggregate object-store limit.

| Arm | Input | Result/preconditions |
| --- | --- | --- |
| `make-object` | `[kind=@tas body=octets]` | Accepts only `blob`, `tree`, `commit`; validates width and hashes the exact bytes. It does not parse arbitrary tree/commit bodies. |
| `make-blob` | `octets` | Exact body bytes; no UTF-8, Markdown, frontmatter, line-ending or trailing-zero normalization. The document validator is separate. |
| `make-tree` | `(list [name=@t oid=@ux])` | At most 32 unique flat lowercase `<UUIDv7>.md` names; mode `100644`; sorts by Git byte order. |
| `make-commit` | `[tree=@ux parent=(unit @ux) principal=@t timestamp=@ud document-id=@t revision=@ud]` | Zero or one parent; canonical lowercase UUIDv7 IDs; unsigned 64-bit numeric fields and positive revision. |

An object's digest input is ASCII `kind`, one space, ungrouped decimal body
length, a zero byte, then the exact body. The returned `body` omits this digest
header. `sha-1l:sha` takes big-endian input, so the module reverses the complete
little-endian byte sequence with its **explicit width** before calling it.
The resulting OID is the conventional SHA-1 number. Hex references always have
40 lowercase digits; leading zeroes are retained.

Each tree record is ASCII `100644`, one space, the 39-byte filename, a zero byte,
then **20 binary OID bytes in network order**. Records concatenate without an
additional delimiter. OIDs are width-checked, but the pure library cannot prove
their existence or kind. The home must prove the referenced accepted blobs.
Fixed flat filenames mean ordinary unsigned byte comparison gives Git ordering;
the implementation uses the pinned bytewise `aor` ordering. Duplicate adjacent
names after sorting reject the whole construction.

Commit bytes are exactly the following, with LF after every displayed line,
including the final message line. Omit the parent line when `parent` is absent.

```text
tree {tree_oid}
parent {parent_oid}
author Stead Fixture <{principal_uuid}@stead.invalid> {unix_seconds} +0000
committer Stead Fixture <{principal_uuid}@stead.invalid> {unix_seconds} +0000

Save {document_uuid} revision {revision}
```

Braces mark placeholders; OIDs are 40 lowercase hex digits and numbers are
ungrouped decimals. For example, the literal author line is:

```text
author Stead Fixture <019939ba-4000-7000-8000-000000000102@stead.invalid> 1789171200 +0000
```

The caller supplies trusted Unix **seconds**, not request-provided attribution
or milliseconds. Both identity lines use the same fields. UUID validation
prevents extra header lines; decimals contain no Hoon grouping dots. This is
host-recorded fixture attribution, not an independently signed human action.
Checking date-policy suitability remains the home caller's responsibility.

## Executed evidence

On September 12, 2026 US/Eastern (September 13 UTC), the command
`python3 scripts/urbit/git_vectors.py` passed **51/51** checks. It used pinned
Vere 4.6 `eval --loom 29` with CPU affinity 19, without booting or modifying any
ship, plus stock Git 2.55.0 in a fresh synthetic bare repository with empty home,
disabled credential helpers/hooks and no host Git configuration.

The 51 checks comprise:

- 20 standard `test-*` arms executed through pinned `/lib/test.hoon` in the
  pure evaluator, with exact expected arm names and empty-tang success.
- A deliberately nonempty failure tang and an invalid-source compiler control.
  The latter exits Vere with code 0; the runner rejects its diagnostics rather
  than treating the process status as a passing test.
- 14 exact native object byte/OID comparisons against stock Git, followed by
  14 writes of the **native-returned** bytes and exact `git cat-file` recovery.
- Stock `git fsck --full --strict` on the native-built object graph, exit 0.
  Additional independent vectors can appear as expected dangling objects.

The vectors cover empty/all-zero/trailing-zero/binary/UTF-8 blobs; blob OIDs
with a leading or trailing zero byte; reversed and sorted tree input, the
32-entry boundary; initial and parent commits, Unix zero and revision 1000.
Negative arms cover duplicate/path/uppercase/wrong-version names, 33 entries,
oversized OIDs, width mismatch, unsupported kind, invalid principal, zero
revision and numeric overflow. The script reconstructs each explicit-width
native body before giving it to stock Git; it does not substitute a host-created
document body for the native result.

Examples: empty blob `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`;
`61 00` blob `90802fedc2462f10bf2114d086cacb9e3af99ffb`;
`00 00` blob `09f370e38f498a462e1ca0faa724559b6630c04f`.
The 285-byte first-commit vector has OID
`7819726cdf00caeb75221b527f7d5d18eefa5a6d`.

[The evidence index](evidence/2026-09-12/git-objects/index.json) binds copied and
original digests. [Objects](evidence/2026-09-12/git-objects/objects.json) include
all exact body bytes as hex; [commands](evidence/2026-09-12/git-objects/commands.jsonl)
record 36 evaluator and 45 Git invocations. [The report](evidence/2026-09-12/git-objects/report.json)
records every assertion and source/toolchain/helper hash. The raw unique run is
`.runtime/git-object-vectors/20260913T022039Z-dq41to78`.

Compiler refinements before the passing run were preserved in the work record:
wide-form multiline syntax, nested increment shorthand, a leading-zero Hoon hex
literal, and one test helper's explicit `@ud` to `@ux` conversion. Those attempts
produced syntax/type diagnostics despite process exit 0 and were not counted as
passes. The passing corpus compiles every test arm and includes the diagnostic
control as a regression against reporting compiler errors as passes.

Independent Hoon review inspected source, all evidence/source hashes, 51 unique
checks, failure controls, fsck and all 14 object SHA-1s. It found no source blocker;
this was an agent source/evidence review, not a second evaluator run or human
approval. Reviewed library SHA-256:
`826b83485429c02f577c9b462ee6cddd3ab8ea1a099d33b66893f863d54c54d7`;
tests SHA-256:
`51518a1239373467864412e64ab92cfbc8258bd37783988b2ae6c17c6eac2d98`.

This qualifies only the pure byte constructors. Mounted-desk compilation,
home acceptance/restart, private export authorization and the complete
URB-040/050 state scenarios are integrator-owned tests. No browser, live Urbit,
Smart HTTP, tags, pack ingestion, SHA-256 repository, LFS, symlink/submodule,
partial/shallow clone or production deployment capability is claimed.

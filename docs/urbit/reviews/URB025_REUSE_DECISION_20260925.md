# URB-025 reuse decision, September 25, 2026

**Decision: do not adopt the pinned Urgit application as Stead's runtime Git
backend.** Its bounded isolated interoperability evaluation is complete:
the repaired guarded runner passed **14/14 native/stock-Git checks**. This result
supports a completed evaluation and explicit non-adoption disposition for
URB-025; it does not satisfy later Stead Git integration gates.

Execution and this review were performed by independent agent
`/root/editor_tool_review`, separate from implementation integrator `/root`.
The earlier cold attempt in this bundle was inspected from another independent
owner's preserved records. No additional agent approval of the successful
transcript, human approval, production deployment or phase-wide closure is
claimed.

## Exact result and source

Passing run: `20260925T112813Z-p7thco40`. Read the
[portable result](../evidence/2026-09-25/urgit-audit/runs/20260925T112813Z-p7thco40/report.json),
[commands and observed output](../evidence/2026-09-25/urgit-audit/runs/20260925T112813Z-p7thco40/commands.jsonl),
[guard](../evidence/2026-09-25/urgit-audit/runs/20260925T112813Z-p7thco40/execution-guard.json),
and [all-attempt index](../evidence/2026-09-25/urgit-audit/index.json).

The tested audit files match committed
`7f4cf118e0bb18bb34f05e4633de16175894fded`; the containing checkout at this
attempt was `a0f5fe218ecc9b909e7a2d5b54bc87198cb8bd08`. Exact identities of the
driver, both bootstrap helpers, guard, toolchain verifier and digest dependency
were recorded before and after execution and were unchanged. The complete
[driver record](../evidence/2026-09-25/urgit-audit/driver-records/urgit-independent-attempt-20260925T112812Z-bb8d11b4.json)
preserves those hashes and the actual wrapper argv.

| Executed file | SHA-256 |
| --- | --- |
| `scripts/urbit/urgit_audit.py` | `c16b32b67c450ccd1fab8efc739e7d272ef4dc96c82dff8f119107f30b3c28d5` |
| `scripts/urbit/urgit_eval/evaluate.py` | `cb26fca7fcc45bcc60da1d12b54a2ed92f6a3eda1c7b08c1665ea787e876e6e4` |
| `scripts/urbit/urgit_eval/bootstrap.py` | `49e9fe5665490c7eab60e4e07dd5c72769fbf3c95a771bbb4e1093a6e73d4b56` |
| `scripts/urbit/urgit_seed.py` | `1df796d497290da0cf05faa919324fe318079fe910912e658adc88e599fd73b6` |
| `scripts/urbit/execution_policy.py` | `da16e2e0fd32eb5b90706b546a7ea8332a65807fc8279f3bd765dcc18aaad9b5` |

The candidate is
[`yapishu/urgit@9cec0371b02269efcdbd8580c42e883e69b82000`](https://github.com/yapishu/urgit/tree/9cec0371b02269efcdbd8580c42e883e69b82000),
archive SHA-256 `facf578b6edccbdb5b748ff16eabcbeaf10c4ca0dbc8c6073bedb0cbee7e5ee3`.
The source archive contained 132 regular files totaling 1,258,242 bytes. The
candidate desk was installed without source changes, with its pinned external
skeleton helper. No Zig/npm/frontend build was run.

The [toolchain lock](../evidence/2026-09-25/urgit-audit/inputs/toolchain.lock.json)
binds Vere 4.6, kernel `408k-2` at
`5a187fededc4582a34fcd6055c67bb63e0917b94`, the brass boot artifact, and stock
Git 2.55.0. Toolchain-lock SHA-256 is
`4a209c10cf1756eb0f7357cc3eca8250bf66c239b4cd0ca31a8c0886d4d304ee`;
[candidate-lock](../evidence/2026-09-25/urgit-audit/inputs/candidate.lock.json)
SHA-256 is `50a90b296fa40e5a9178999cb2709682884812a98e2b133f6261eb5ec3934561`.

## Observed checks

The transcript contains 36 actual stock-Git commands, the native request/reply
pairs and exactly 14 passing check records. The independent reviewer checked
the observed Git output as well as the evaluator's summary. The three nonzero
Git exits are the expected unauthenticated, stale-client and revoked-token
denials; other Git commands exited 0.

| Check | Observed result and boundary |
| --- | --- |
| Pinned readiness | `zuse` returned `%408`; separate native baseline returned `our = ~zod` and clean Urgit state `%.y`. |
| Native codec | Blob OID equals stock `git hash-object --stdin` for `hello world` plus LF. |
| Native pack | Stock `index-pack --strict --stdin` accepted a 56-byte pack, exact blob bytes recovered, `fsck --full --strict` exited 0 with expected dangling/no-default-reference notices. |
| Stock pack vector | Native inflate/decode fields true. |
| REF_DELTA vector | Native parse/resolve/decode true; six objects reconstructed. |
| OFS_DELTA vector | Native decode true; six objects reconstructed. |
| Unauthenticated push | Exit 128, prompts disabled; no missing-route 404 accepted as a denial. |
| Authenticated push | Original first commit OID preserved by remote ref. |
| Clone and fsck | Exact first OID/file bytes and stock strict fsck succeeded. |
| Annotated tag | Exact tag OID preserved through push/fetch. |
| Incremental fetch | Exact second commit OID and strict fsck succeeded. |
| Stale client lease | Exit 1 with `stale info`; remote ref remained the second commit. This tests client lease behavior, not simultaneous server CAS. |
| Corrupt pack | Corrupted checksum rejected with unpack/ref failure; remote ref remained unchanged. This is one corruption case, not general hostile-pack qualification. |
| Revoked-before-request token | Exit 128 after revocation; remote ref unchanged. This does not test revocation while ingestion is staged. |

Preserved IDs: blob `3b18e512dba79e4c8300dd08aeb37f8e728b8dad`; first commit
`4c6822411f79230c1d8ae6e1d42d89bbd533b68e`; second commit
`a57608b70cda4efa686ed3d92e71a728f4448f77`; annotated tag
`4b2e0711ffe898baaaaf4f5f9569022980c7cd6a`. The native pack SHA-256 is
`d3a13f2f0179dbe263951b6dd16910310fe1117a27899bc9906caaa5b085e245`.
The fixture's Git author/committer bytes and OIDs were not normalized.

## Resource and evidence boundary

The complete driver ran in an additional transient user scope with observed
`cpu.max = 5000 10000` and CPU 19 affinity. The existing inner native scope
independently reported those same limits. Admission remained 75 C, thermal stop
90 C, total native timeout 2,100 seconds, and loom exponent 31. No persistent
system setting, fan setting or ceiling was changed.

The guard completed in 38.469 seconds; peak sampled host temperature was 63 C.
Runtime, sandbox and wrapper exited 0. This is one bounded execution using
preexisting stopped synthetic seed state, not a cold-start or capacity benchmark.
The seed manifest binds all four known fake ships, only a private stopped `~zod`
copy entered the audit, and source/input digests were unchanged afterward.

Both scope inventories were empty and both lifetime locks were free before the
native slot was released. The namespace excluded host homes and external
networking; this was a single disposable fake, not live Urbit network testing.
All failed/refused attempts remain separate in the
[bundle history](../evidence/2026-09-25/urgit-audit/README.md).
An earlier serialization failure has zero checks in its host report but one
readiness check in its command transcript; the bundle explicitly preserves
that distinction. The final native pass closes the repaired-run rerun gap
described in the historical [September 12 audit](../URGIT_AUDIT.md).

Portable copies normalize declared host paths, uname node name and cgroup UID;
original and portable SHA-256 values are separately recorded. Original raw
native logs remain local with hash references. No candidate source or pier is
vendored, and no generated credential appears in published evidence.

## Why backend adoption remains closed

The pinned [application docket](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/desk.docket-0#L7)
declares `license+'MIT'`; the candidate is not being described as unlicensed.
Inspection of this exact archive found no LICENSE/COPYING/NOTICE file or
first-party copyright/full permission text outside dependency lockfiles. The
declaration is retained as evidence, but a complete first-party notice and
provenance package is still required before tracked reuse or redistribution.
The external skeleton's verified MIT notice is separately preserved. No missing
attribution is invented. These findings are bound in
[source-review.json](../evidence/2026-09-25/urgit-audit/source-review.json).

The [master directive](../MASTER_BUILD_DIRECTIVE.md) requires one authoritative
home and final policy/revision/epoch checks at every Git acceptance boundary.
The pinned candidate's
[`write-authorized`](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/app/urgit.hoon#L7800)
accepts ship-owner Eyre authentication or a repository token; it does not bind
the Stead principal/grant/epoch protocol. A separate independently writable
`%urgit` authority cannot be admitted merely by placing a Stead UI in front of
it. Prior source concerns around delayed native/Clay completion remain review
items, not dynamically demonstrated exploits in this corpus.

No execution here qualifies final authorization after concurrent revocation,
server CAS under competing writers, alternate-endpoint fencing, private-project
non-disclosure, crash-during-push durability/recovery, bounded hostile expansion
or graph admission, large repositories, SHA-256 repositories, LFS, shallow or
partial clone, Git-to-Clay projection, frontend behavior or live deployment.
The tested repository was intentionally public and synthetic.

Keep Urgit as an evaluated feasibility reference, not a runtime dependency.
Future reuse must either place reviewed library functions under Stead's single
mutation owner or supply an approved separate-agent transaction/fencing design,
complete notices and a new failure/conformance corpus. This non-adoption
decision does not block work on Stead's own canonical Git-backed Docs design,
and it grants no release, hosting, identity or production authority.

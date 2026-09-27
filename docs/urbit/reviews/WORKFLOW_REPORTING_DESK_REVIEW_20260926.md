# Workflow reporting and clean desk correction — September 26

The actual prequal10 at `a68a5a7b12c2f87396ca666807e22a170d82a3f1` passed
T01, T02, T04 and T05. T03 and T06 failed; this is not a six-task pass. The
[unchanged run and closed completed outer guard](../evidence/2026-09-26/native-attempts/prequal10/index.json)
are retained. The raw inner report SHA-256 is
`1d5044b3e73205060b0a680de48112b26f50cdc85a3b379a6364b88e435af9e7`;
it ran for 217.164 seconds and ended with a T06 timeout. All ships then stopped
cleanly; the guard completed with exit zero. Prequal09 is retained separately as
a zero-task admission refusal.

## Observed T03 behavior and bounded transport

The new initial-save diagnostic passed. The full probe emitted all 12 case
completion markers, then measured a 1,325,984-byte evidence jam. The existing
262,144-byte pre-render limit rejected it. This localizes the current failure
to evidence serialization; the earlier timeout remains an unchanged failed run.

The correction retains all 12 cases, full native vase comparisons before/after
rejection and repeated save/load, actual rejection tags, empty-card checks,
expected saved nouns and public-only case selection. Only the returned evidence
changes: saved noun values remain literal; compiler types and rejection tangs
are represented by their native jam byte lengths and SHA-256 digests. Pinned
`pkg/arvo/sys/hoon.hoon` lines 3320–3324 define the used `shax` primitive. No
case, assertion, timer or byte limit is relaxed.

## T06 platform scaffold and typed metadata

The pinned `gen/hood/clay/new-desk.hoon` copies four standard marks and
`sys.kelvin`; it does not include the bill mark by default. The failed mount
contained those five files plus the candidate overlay, with no `mar/bill.hoon`.
The subsequent library scry timed out. Missing mark support is the
source-supported diagnosis, pending verification of the fix.

The adapter now requires the exact five-file pinned platform baseline, then
installs only the pinned `mar/bill.hoon` before the four candidate files. The
final mount must equal the exact nine-file union. Platform hashes are separate
from the unchanged candidate assembly and dependency manifest. The bill mark
SHA-256 is `a0196da4970b8dfdee321a638040a564f95e8000f3b49eccc274ee8de2fae0ff`.

Hoon files retain native text/hash readback. `desk.bill` and `sys.kelvin` are
parsed Clay nouns, so they use their pinned typed predicates: an empty
`(list dude:gall)` and `[%zuse 408]` as `waft:clay`. Exact original text bytes
remain checked in the assembled and mounted files. Prior-run admission requires
both actual successful metadata commands. The native generator must still
return 42. No additional candidate dependency or third-party library is added.

## Host validation and review boundary

The [focused host execution](../evidence/2026-09-26/workflow-projection-host/index.json)
passed 41 tests in 0.991 seconds under CPU50%/10ms on CPU19. Native calls are
mocked in this suite. Controls reject extra platform files, wrong metadata,
missing native readbacks and incomplete receipts, while preserving public
feedback isolation and timeout cleanup. The frozen evaluation package is
unchanged at `d78697102021b4b4837efd2d560668310fad5ab69fcbf98c7592a9cd0fff3e00`.

| Reviewed file | SHA-256 |
| --- | --- |
| `scripts/urbit/skill_evaluation_support.py` | `1d93cb91441ff80384c1072d81cca2f6d47e143d6377da740f6ac5ad8a20bfba` |
| `tests/urbit/test_skill_evaluation_support.py` | `991b62a0d71cd798f4a445805fa018cfdda9ed58534381699e3e9d8836fe3df8` |

Independent source review by `/root/editor_tool_review` cleared the exact two
file hashes above, checked the pinned primitives and metadata semantics, and
verified the unchanged frozen package. The reviewer inspected the retained host
results but ran no tests or native process and edited no files. Omitted types
and tangs are native hash/size observations, not host-reconstructed full evidence.

Native compilation and execution of the correction remain required. No
participant, phase closure, human approval or GitHub CI success is claimed.

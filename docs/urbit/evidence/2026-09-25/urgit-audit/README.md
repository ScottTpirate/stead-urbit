# September 25 Urgit audit evidence

The repaired, guarded evaluator completed its bounded native/stock-Git corpus:
**14 of 14 checks passed** in run `20260925T112813Z-p7thco40`. The independent
execution owner was `/root/editor_tool_review`, separate from the implementation
integrator. This is agent execution/review evidence, not human approval or
adoption of Urgit as a Stead backend.

Start with the [formal reuse decision](../../../reviews/URB025_REUSE_DECISION_20260925.md),
[passing report](runs/20260925T112813Z-p7thco40/report.json),
[actual command transcript](runs/20260925T112813Z-p7thco40/commands.jsonl),
and [completed guard](runs/20260925T112813Z-p7thco40/execution-guard.json).
The [index](index.json) binds portable files to their original local bytes.

## Execution boundary

The executed driver was `python3 scripts/urbit/urgit_audit.py`. The passing
attempt placed that whole driver, including seed hashing/copy preparation,
inside an additional transient user scope. Its actual `cpu.max` was
`5000 10000` and affinity was CPU 19. The unchanged inner guard independently
verified the same quota/period and affinity. The outer scope reduces preparation
load; it does not relax the inner 75 C start and 90 C stop ceilings.

The [independent driver record](driver-records/urgit-independent-attempt-20260925T112812Z-bb8d11b4.json)
retains the exact outer wrapper argv, before/after file hashes, admission sample,
exit code and scope readback. The [outer proof](driver-records/urgit-outer-scope-proof-20260925T112812Z-bb8d11b4.json)
was written from inside the active scope before invoking the audit. Normalized
argv contains placeholders and is evidence, not a command to execute unchanged.

The baseline was observed natively as `~zod`, `%408`, and `%.y` for the absence
of a previous `%urgit` desk/agent. A verified stopped fake seed was copied to a
unique read-only input and then the sandbox work directory. Source seeds and
input copy were unchanged afterward. No live identity was imported or exposed.
The outer/inner scopes exited, the native runtime exited 0, and both lifecycle
and native locks were free at the independent [cleanup observation](cleanup-observation.json).

## All attempts in this bundle

These are all seven September 25 audit directories present at packaging time,
plus a preliminary admission refusal that never invoked the audit driver.
Earlier September 12/13 attempts remain separately preserved in
[their existing index](../../2026-09-12/urgit/index.json).

| Attempt, UTC | Recorded outcome |
| --- | --- |
| `20260925T102835Z-2mgo4s0g` | Cold boot thermal stop; 0/14 checks, 372.978 s; peak sampled 92 C. Executed by another independent owner; inspected from its preserved records here. |
| Preliminary refusal recorded `20260925T110018Z` | Start admission refused; no audit invocation. Original rejected temperatures were not captured; the later diagnostic sample is explicitly separate. |
| `20260925T110142Z-d542j3zm` | Seed admission refused before native launch because the new helper used incompatible file ordering. All four original seed hashes still matched the established convention. |
| `20260925T110551Z-h7434vf0` | Warm boot returned `~zod` and `%408`; clean-state query failed. Redactor shadowing prevented evaluator report serialization. Host report has 0 checks; transcript retains one readiness check. |
| `20260925T111141Z-ukilsapn` | Warm boot and report serialization worked; the clean-state expression still failed with `-find.$`. Failed report retains 1/14 checks. |
| `20260925T111845Z-kf_u2q3b` | Final launch admission refused at 78 C before any native process; 0/14. |
| `20260925T112445Z-_1wiivjr` | Final launch admission refused at 81 C before any native process; 0/14. |
| `20260925T112813Z-p7thco40` | Additional outer preparation quota; actual baseline and all 14 checks passed; guard completed in 38.469 s; peak sampled 63 C. |

No failed attempt is relabeled as passing. Warm-boot timing includes preexisting
synthetic seed state and is not a cold-start or capacity benchmark. Host-wide
temperatures alone do not identify which process caused an earlier spike.

## Portability and integrity

Each `index.json` artifact row records original repository-relative location,
original SHA-256/size, portable location and portable SHA-256/size. Original
per-run manifests are retained as `SHA256SUMS.original.json`; their hashes refer
to local originals, not normalized copies. Every original manifest was checked
before copying.

Normalization is explicit: the repository absolute path becomes `<REPO>`, the
host home becomes `<HOST_HOME>`, the uname node name becomes `<HOST>`, and the
local cgroup UID becomes `<UID>`. JSON/JSONL is reserialized as declared in the
index. Git OIDs, source/pin hashes, outcomes, error text other than local paths,
command options, timings and temperatures retain their values. The evaluator
had already redacted its generated synthetic token and Basic encoding before
writing local evidence; those markers are preserved here.

Raw native logs, piers, candidate source and binaries stay local. The index
retains original hashes/sizes for each omitted native log; commands, console
errors, partial results and guard records remain portable. The candidate source
inventory and inspected file hashes are in [source-review.json](source-review.json).
The pinned skeleton dependency's full license notice is retained in
[inputs/skeleton-LICENSE.txt](inputs/skeleton-LICENSE.txt).

Verify the portable artifacts from this directory with this host-only check:

```sh
python3 - <<'PY'
import hashlib, json
from pathlib import Path
base = Path('.')
index = json.loads((base / 'index.json').read_bytes())
for row in index['artifacts'] + index['supplemental_artifacts']:
    raw = (base / row['portable_path']).read_bytes()
    assert len(raw) == row['portable_bytes']
    assert hashlib.sha256(raw).hexdigest() == row['portable_sha256']
print('portable artifact hashes match')
PY
```

This verifies file integrity only; it does not execute native tests or establish
production readiness. The full first-party notice package, final Stead policy
authority, concurrent server CAS and staged-revocation checks remain open for
any future backend integration.

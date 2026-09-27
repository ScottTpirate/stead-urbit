# Cooling retry: independent host and retained-evidence review

Reviewer: Codex agent `/root/independent_review`, separate from the implementing
integrator. This is agent review, not human specialist approval or phase
acceptance. Work used the repository's native-test and Gall-security review
instructions. The only reviewer write for this follow-up is this record.

Before writing, remotes were verified: `origin` fetch/push is
`https://github.com/ScottTpirate/stead-urbit.git`; the historical `upstream` has
push URL `DISABLED_UPSTREAM_PUSH`. No upstream write occurred. No credentials,
live identities or confidential fixtures were used.

## Independently executed host checks

Reviewed implementation and test source:
`53f17253f5ae1f4204d7292e75ac1ec0fb534f17`, compared with
`7ec8acf6f255c8162f64b268c4d5a0bfb0902fc9`. The reviewer independently executed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/urbit -p test_harness_safety.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/urbit -p test_core_conn.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/urbit -p test_dev_flow.py -v
```

All exited 0: **36 + 13 + 20 = 69 host tests passed**. Native ship/evaluator
operations in these tests are mocked; filesystem, socket/thread and temporary
Python-source checks remain host evidence. The reviewer did not rerun the full
suite, launch ships, run a native evaluator or change machine cooling controls.
No additional tests were executed while preparing this record.

The five reviewed files were rehashed and matched their Git blob bytes at the
source commit above:

| File | SHA-256 |
| --- | --- |
| `scripts/urbit/supervisor.py` | `e748a997e8e1826317184c2dfdce4b3be9f80bb8050352637d911ae1a9a81ae0` |
| `scripts/urbit/core_conn.py` | `76754774de052f8e1f9f49ea4fbd951171aa8a0b158fe9a6b5bfd7902da67071` |
| `tests/urbit/test_harness_safety.py` | `4da7f03276d40e5c9c1ce01d7bc3564000f67713b30330aad93727feddf7ce19` |
| `tests/urbit/test_core_conn.py` | `45d416e8ce939295549dfc6c17e2c40868f1b153e6f95445ab30017492faf1b2` |
| `tests/urbit/test_dev_flow.py` | `9f11f844b0e46d90c6cc415c6d63b80db4b67f23fb7e217eb017a7091f7b213a` |

## Code findings

The previous `all_stop` and `shutdown` paths could signal the same live process
twice; the watchdog could also signal before acquiring the test mutex. The fix
routes those requests through a separate lock and a weak set keyed by the
actual Popen instance, so a replacement process receives its own TERM even if
its ship name or PID is reused. Cleanup still interrupts before waiting for a
busy test mutex and attempts the remaining children after individual failures.

Previously, a nonzero child exit raised without latching failure, allowing a
later `NORMAL_STOP` to produce supervisor exit 0. `SHUTDOWN_FAILED` now survives
normal stop and prevents successful supervisor completion after signal, wait,
kill, nonzero-exit, log-close or collected cleanup errors. Host coverage includes
the actual helper chain, repeated requests, same-PID replacement, nonzero exits,
escalation/errors, swallowed watchdog failure and a retained marker that blocks
restart. No remaining blocking cleanup finding was identified in this bounded
review. The two-thread test does not force simultaneous lock contention; its
repeated-path and process-incarnation assertions still exercise the original
defect.

Reducing the framing control to 34,000 synthetic text bytes does not reduce its
required encoded boundary: the actual native frame must exceed 65,536 bytes,
have the complete declared length and recover the exact JSON bytes. Frame and
result digests are retained. This is a framing control, not a 70,000-byte
application-capacity qualification. Truncation, boundary-sized frames, missing
terminal results, parser failures and crashes remain failure cases.

## Retained failure before the fix

The reviewer read the integrator's retained full-speed-fan attempt under
`.runtime/cooling-20260924/evidence/`. Its limitation record identifies source
`7ec8acf6f255c8162f64b268c4d5a0bfb0902fc9`. All four fake ships reported `%408`.
The guard observed a maximum sample of 64 C and reported `completed`, exit 0,
after 46.187 seconds. The core check nevertheless failed after its 30-second
large-noun encoding timeout, with no compiler/probe commands completed.

The supervisor log records `bud` exiting `-15`, repeated cleanup checks and a
swallowed cleanup error; the limitation record reports no unclean marker.
Therefore that guard completion is not evidence of clean fixture shutdown or
native compilation. Repeated TERM was reachable in the reviewed source; these
logs do not independently establish that it caused the `-15` exit.

| Retained local artifact | SHA-256 |
| --- | --- |
| `full-speed-attempt-guard.json` | `37947a741842e5436e54d0dde5f9bf7c293bf58baa416fc56af394e7ef1a9b6d` |
| `full-speed-attempt-core-check.json` | `36b32d7141fa3cec5009fa3aee502b3aa44fe816c90779af81b3076b0178388e` |
| `full-speed-attempt-scope.json` | `74f1c03a5d1fedb97083e19ebadc3a563c8b46bedeb61d42d7edca55b3cd69db` |
| `full-speed-attempt-supervisor.log` | `d9e8fd8ad9d3764122cea10bae18891efbe3211c97e8601ad984460ea312e89d` |
| `full-speed-attempt-limitation.json` | `aa0f46344792680b9bb6be384fdb2cc8e9467b63cc1bb59b1b65225c2ae83f50` |

These are ignored local evidence paths, not portable PR artifacts by themselves.
The reviewer inspected recorded thermal/control evidence; no independent fan-RPM
measurement, causal cooling benchmark or sustained-load qualification is claimed.

## Completed retry at the reviewed source

The integrator subsequently supplied the final retry artifacts. The reviewer
read them after completion; the earlier in-progress checkpoint was not called a
pass. Guard report
`.runtime/execution-runs/four-fakes-l8c2r_ho/report.json`, SHA-256
`f7972e465c18b2210bbbf405c2816b4206dabee00e11db9e20ac48d2a6dc75a3`,
records `completed`, exit 0, 69.342 seconds and maximum sampled temperature 72 C.
Scope evidence retains one CPU and `cpu.max` of `5000 10000`; 75 C admission,
90 C stop and freshness limits are unchanged.

Core report `.piers/fakes/logs/core-check-20260924T235914Z.json`, SHA-256
`f47d0a7b0746b0654124459b250a9727b6b54062a0a478c347e8a0b196aa71c7`,
retains equal before/after inputs, including the reviewed core connection module,
native digest `a16e6ca6125797fce156aa9e36721432f9152cae5514708d2632464d42f77b7d`
and supervisor digest
`2d99a59506915bc8bc76ab9fec48d8ffa6336fc40411b0d7634ac4f96a53963d`.
The actual native evaluator controls passed: a **68,159-byte frame** recovered the
exact expected JSON. Its frame SHA-256 is
`316032501c4bf7f7955125fe4f2c6d076902455df20087e51d1769de16dc5d39`;
recovered result SHA-256 is
`e55d68cad45178ad7ba65eed8ff4a10b2e1dbd469e0464790298474eca792e3d`.

The report contains 23 commands: the Clay commit, 21 imported-source hash checks
and the failed `+stead-build-probe`. It records 46 of 47 checks true, overall
`status: fail`, `stage: failed`, `qualifies_phase: false`. The inspected native
log reports `mull-grow` / `nest-fail` at `stead-core.hoon` line 571. No successful
home compilation or remaining probe execution follows from the import checks.

The inspected supervisor log snapshot, SHA-256
`6b09874f7851f87ba4d273f25b69e42f62f7f4ace9d7b50713dad716aa79103e`,
records exit 0 without escalation for all four ships during fixture replacement
and failed-build cleanup. This provides actual clean-shutdown evidence for this
run, in addition to the host regressions; it does not count native TERM signals
or prove all shutdown races impossible.

The bounded outcome is successful native framing and clean cleanup, with a
**failed Hoon build**. Phase 0/1 acceptance, full native business/security/
migration/delivery qualification, browser behavior and deployment remain open.
Any subsequent Hoon edit requires separately bound review and execution evidence.

## Source-only addendum: predecessor field-list type

The same reviewer inspected commit
`ed1bd89da8eb3473d89c720fba1446714a47c216` against its parent. Only
`native/core/desk/lib/stead-core.hoon` changed: the existing eight field names
are bound as `shared-fields=(list @t)` before the existing `levy` assertion.
Their values and order are identical; the equality predicate and surrounding
predecessor validation remain intact. No authorization, receipt comparison,
saved-state version or accepted-record check was removed.

The explicit recursive list mold addresses the literal-list type inference at
the previously observed line-571 `mull-grow` / `nest-fail` boundary. No blocking
source finding was identified in this narrow correction. The predecessor file
SHA-256 is `9ad77eba9c2bb5e916af74c62250761513278bdbfbb729ec3919edb04d2b5da4`;
the corrected Git blob SHA-256 is
`4988f9707357bf5423548fe230fc482158bb96e42269664e0df178791e29b620`.

This addendum is **source-only**: no tests or native commands were executed by
the reviewer. The integrator reported that the initial corrected-source attempt
was refused before launch; no successful native compilation of this change is
recorded here. The earlier framing and shutdown results do not qualify the new
Hoon bytes. Remotes were reverified before this review-only append; all phase
acceptance exclusions remain unchanged.

## Final records addendum: portability and restoration

The reviewer read `COOLING_CHECKPOINT_20260924.md`, the README and TEST_RESULTS
introductions, the proposed local PR body and the
[portable evidence index](../evidence/2026-09-24/cooling-retry/index.json).
No host tests, native commands or live cooling operations were performed in this
follow-up. Remotes were reverified before this review-only append.

All **21 indexed artifact hashes match**. For each executed source commit,
`7ec8acf6f255c8162f64b268c4d5a0bfb0902fc9` and
`53f17253f5ae1f4204d7292e75ac1ec0fb534f17`, the reviewer independently compared
all **39 bound Git blobs**: the complete 21-file native desk, 17-module supervisor
source closure and toolchain lock. Recomputed aggregate hashes match the index
and both reports' equal before/after inputs. Both compile reports remain failed.
The inspected index SHA-256 is
`1b0fadd3bdc7463fbde996df9a5f94b7b051f15c6894fe1271114ad97f167b19`.

The final portable `fixed-harness-supervisor.log` has SHA-256
`ed5ee55fab409af30941ae4fa1763fec80d1947965c72fc94bb2de0a74bd3d98`.
The earlier `6b09874...` value above identifies the snapshot read at that time;
it is not the final portable log's digest. The final log retains the failed
build and clean child shutdowns without changing their qualification scope.

The separate restoration readback at `2026-09-25T00:12:43.292514+00:00` records
all **34 values exactly equal** to `original-fan-curves.json`, both mode values
restored to 2, and the original `performance` profile unchanged. The reviewer
compared the recorded maps and profiles, rather than relying only on the
record's success flag. `fan-restoration.json` has SHA-256
`e1b7594e9e7da9e760815869f6ce63849ae087a53fd5a146080a8e58d1eda54e`.
This is independent inspection of the integrator's retained readback, not an
independent execution of sysfs restoration or a cooling benchmark.

The portable record distinguishes successful native framing/cleanup from the
failed build, and records the corrected source's refusal before launch. No
build or phase pass is overstated. Phase 0/1 remain open and Phase 2 has not begun.

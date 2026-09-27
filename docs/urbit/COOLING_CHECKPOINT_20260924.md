# Cooling and native build continuation

Phase 0 and Phase 1 remain open. Phase 2 implementation has not started.
The September 24 evening continuation verified local fan control, fixed two
harness defects, and reached a real Hoon compiler error. Thermal admission and
successful process shutdown are separate from a successful build or phase gate.

## Local compute and cooling

The four real fake ships represent the home, contributor, reader and outsider.
They exercise identity-dependent behavior without live identities or a server.
Their common runtime scope retains one CPU of affinity and a 50 percent quota
with a 10 ms period. Host source verification and host tests are separate work;
the runtime quota is not a cap on the workstation's other processes.

The ASUS ROG Strix G733ZS exposes `asus_custom_fan_curve` through its installed
kernel. Its original Performance curves request full fan duty at 97 C. A
temporary curve reaching full duty at 80 C raised measured fan speeds but still
allowed a 91 C startup interruption. Holding both fans at full duty before the
next run produced measured speeds around 6,600–6,700 RPM. Two admitted runs then
stayed within the existing guard, with recorded maxima of 64 C and 72 C.

These are observed sessions, not an isolated causal cooling benchmark or a
promise that concurrent workloads will fit. A later 20-second sample window,
with Stead stopped, reached 83 C. The next native launch was refused at 77 C.
The integrator also directly observed a 95 C stopped-fixture sample and other
CPU work. No unrelated workload, power profile, CPU turbo setting or persistent
fan service was changed. The original fan settings were saved before mutation.
After testing, the temporary helper restored all 34 original curve/mode values;
separate [sysfs readback](evidence/2026-09-24/cooling-retry/fan-restoration.json)
confirmed the exact values and unchanged Performance profile. Automatic firmware
fan control is restored. The [evidence index](evidence/2026-09-24/cooling-retry/index.json)
records the sessions and restoration outcome.

## Bounded fixes and execution

| Source | Actual result |
| --- | --- |
| `7ec8acf6f255c8162f64b268c4d5a0bfb0902fc9` | Full-speed cooling allowed all four boots. The 70,000-byte synthetic framing input timed out during native encoding. Cleanup exposed repeated TERM requests and an unclean child exit that did not latch supervisor failure. |
| `53f17253f5ae1f4204d7292e75ac1ec0fb534f17` | TERM is deduplicated per Popen instance across the watchdog and control paths. Shutdown failures remain latched through normal stop. The framing control uses 34,000 source bytes while still requiring an actual frame above 65,536 bytes and exact roundtrip recovery. |
| Native retry of `53f1725` | Actual evaluator controls passed with a 68,159-byte frame. All 21 imported Hoon files matched their hashes. `+stead-build-probe` failed with `mull-grow` / `nest-fail` at predecessor validation's field-name list. Fixture replacement and final shutdown recorded exit 0 for every ship. The overall compile report remains failed. |
| `ed1bd89` | The same eight predecessor receipt field names are explicitly typed as `(list @t)` before iteration. Native admission refused before launch; this correction is not compiler-qualified yet. |

The earlier thermal interruption also recorded a native `SIGSEGV` during
startup/shutdown in `_lord_plea_ripe`. No core dump was stored. The timeline and
symbolized runtime log are retained; the exact crash cause is unproven. Removing
duplicate graceful signals does not establish that every upstream shutdown race
is fixed.

Root `make check` passed **290 host tests**, planning/ecosystem checks and both
contract freezes at `53f1725`. After the Hoon edit, the [final host rerun](evidence/2026-09-24/cooling-retry/latest-source-host-check.json)
at `ed1bd89` also passed all 290 tests in 4.568 seconds including the wrapper;
this did not compile Hoon. Independent review executed **69 affected host tests**
at `53f1725`, all passing. Native callbacks in those host tests are mocked. The
native results in the table were separately executed against the real pinned
Vere 4.6/kernel 408 environment. No browser, live-network or deployment test was
executed. See the [independent review](reviews/2026-09-24-cooling-retry.md).

Portable copies of the exact failed native reports, scope proofs, compiler and
shutdown logs, fan settings and hashes are under
[`evidence/2026-09-24/cooling-retry/`](evidence/2026-09-24/cooling-retry/index.json).
The old failed artifacts remain unchanged, including the raw crash log's final
blank line. Whitespace checking reports that preserved evidence byte; the
remaining staged changes pass. The full source and toolchain binding must be
reconciled again after any further implementation edit.

## Remaining gates

The latest Hoon correction needs real compilation and all probes. The current
business, permission, delivery, migration/capacity and export corpus still needs
native qualification and independent review. The actual delayed inbound
old-leave test mechanism remains missing; an unchanged full rerun cannot close
that obligation.

Phase 0 also needs the contributor workflow's six-task baseline/assisted
evaluation and a final Git reuse/acceptance disposition. Rejecting Urgit adoption
does not require proving that candidate works, but it does require an explicit
criterion mapping and does not convert its pre-fix vectors into a hardened pass.
Phase acceptance and integration records remain open. The planned Phase 2 entry
is the configurable synthetic team/project/container model and independent API
client, followed by individual sessions and the browser Work/Docs journey.

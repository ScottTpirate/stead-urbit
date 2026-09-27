# Local fake-ship development

See [the edit/build/test flow](DEV_FLOW.md) for the local command reference and
the distinction between compile checks, acceptance, browser testing and hosting.
`make` prints help; `make status` and `make preflight` do not start ships.

This profile is Linux x86-64, public/synthetic inputs only. It uses the existing
machine, four fake identities, and no live identity or cloud resource. The tested
host is recorded in TEST_RESULTS.md. Prerequisites: Python 3.12+, bubblewrap,
iproute2, GNU make and the exact Git version from the lock. The host must permit
unprivileged user/network/mount/PID namespaces. No sudo or Docker socket is used.

From the repository root:

```sh
make setup
make doctor
make preflight
make start
make wait-ready
make core-check
make test
make core-test
make stop
make reset
```

`setup` downloads and verifies pinned artifacts in ignored `.runtime/`.
`doctor` verifies archives, extracted files, corpus, frontend lock, Git/Node versions
and real namespace isolation. `start` returns the current stage: **booting is not
ready**. Wait until status reports `ready: true` before testing. First boot creates
four separate piers sequentially, mounts the disposable base desks, gracefully
stops all processes, makes hash-verified clean seeds, then starts them again.
This can take several minutes. Later restarts use those seeds.

`start` now requires the common host-owned execution guardian used by the Urgit
candidate runner. Preflight refuses any thermal reading above 75°C; monitoring
stops execution at 90°C. Missing, malformed, changed or older-than-three-second
sensor evidence fails closed. The host reads sensors every second; the isolated
supervisor checks a read-only lease every quarter second and before operations.
The guardian also verifies a transient 50% CPU quota with a 10 ms period and one
CPU of affinity. A shared kernel-held lock permits only one heavy native run.
None of these settings changes persistent host configuration.

If preflight refuses, preserve its `.runtime/execution-runs/*/report.json` and
do not retry hot boots. Finish source/lightweight work and record pending native
commands. An alternative runner requires existing, explicit authorization and
the same compatibility/isolation policy. No alternative is currently qualified.

`test` deliberately replaces only the marked synthetic **live fixture** from its
stopped clean seed. It recompiles native source, tests actual native ACK/NACK
outcomes across four senders and restarts the home. It never resets Git or edits
the working source. Logs/results remain under `.piers/fakes/logs/`; preserve failed
results. A timeout is an unknown result, not a permission denial or successful
save. The test command exits nonzero on missing, unexpected or failed outcomes.
After changing harness Python source, stop/start the supervisor before testing;
loaded-source hashing rejects stale process code.

`make dev` combines start, readiness wait and `core-check`, and attempts owned
cleanup on failure, Ctrl-C or SIGTERM. The compile check installs the home desk,
verifies its actual Clay bytes and runs five named native probes. It records
`qualifies_phase: false`; successful compilation alone cannot close Phase 1.
It uses a fresh disposable fixture, so it is not a state-preserving UI hot-reload
command. Failed compilation clears readiness and stops the fake processes.

`core-test` installs the separate `native/core/desk` into freshly restored fake
fixtures and executes the Work/Docs/permissions journey, native codec and state
version checks, and stock-Git materialization of home-created document objects.
It includes a real two-minute grant-expiry wait. `test` retains the original
counter smoke. Both commands own only disposable test state. The v2 core runner
adds scoped-identity/privacy, predecessor migration, capacity and actual Gall
observer schedules. The September 25 build and smoke passed at `c299f19`; the
following full run passed 145 business cases and left three typed dispositions
incomplete before failing a real saved-state round-trip. That failed report is
preserved under `evidence/2026-09-25/native-core-first-run/`. Subsequent source
fixes require their own recorded execution. The current qualification gate fails
when required evidence is missing; historical 25 skipped assertions remain unchanged. Read
[NATIVE_CORE.md](NATIVE_CORE.md) and the exact evidence before inferring scope.

`stop` uses Vere's supported SIGTERM path, checks clean exits and waits for the
lifetime filesystem lock. The guardian bounds cooperative/TERM/KILL cleanup at
10/10/5 seconds, using only its owned scope and processes. Forced or interrupted
execution is nonpassing, preserves logs, and records `unclean-live.json`; it must
never create a clean seed. `reset` requires stopped processes and the
kernel-held lock, an exact ownership marker, private permissions, matching
versions and every seed hash. It accepts no custom deletion path. It replaces only
`.piers/fakes/live`; it refuses an unmarked path, redirected path, active owner or
changed seed. If a guard fails, inspect/preserve the fixture rather than deleting
around the guard. This is a disposable fake reset, not production recovery.

All four processes share **one** private network namespace with loopback only.
They have separate pier directories. The sandbox gets read-only runtime/source
inputs and writable marked fixture state; no home directory, credentials, host
network or Docker control socket. Administrative HTTP ports 18080–18083 and each
runtime's loopback Lens port are inside that namespace only. Fake galaxy UDP ports
are derived by the pinned runtime as 31337 plus the ship's numeric identity:
`~zod` 31337, `~bus` 31519, `~nec` 31338, `~bud` 31339. Rank has no permission meaning.
Do not turn these administrative sockets into employee APIs.

Each Vere process reserves a 2 GiB virtual loom (`--loom 31`); actual RSS is smaller
and workload-dependent. First boots are sequential. The harness is for small
synthetic data, not arbitrary repository execution or capacity qualification.
Same-user/physical administrators remain in the trust boundary. User namespaces
are not a claim that mutually hostile installed Gall apps are isolated.

Host checks are separate from native execution:

```sh
make plan-check
python3 scripts/urbit/check_ecosystem.py
make contracts-check
python3 -m unittest discover -s tests/urbit -p 'test_*.py' -v
```

The planning tests copy only named metadata inputs, never piers/runtimes. Some
safety tests use mocked processes/network and actual temporary filesystem locks;
read their scope labels. These checks do not compile Hoon. The independent Urgit
candidate command and its limitations are recorded in URGIT_AUDIT.md.

The previous independent native-core replay sampled a 96°C CPU peak before the
common guardian existed. That historical result remains unchanged. Host guard
tests and a short actual systemd/bubblewrap check with explicitly mocked sensors
do not qualify a guarded native run or sustained load. See TEST_RESULTS.md for
separate evidence layers. Restart the supervisor after any harness change; do
not reuse a process that loaded different source.

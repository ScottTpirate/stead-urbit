# Local fake-ship development

This profile is Linux x86-64, public/synthetic inputs only. It uses the existing
machine, four fake identities, and no live identity or cloud resource. The tested
host is recorded in TEST_RESULTS.md. Prerequisites: Python 3.12+, bubblewrap,
iproute2, GNU make and the exact Git version from the lock. The host must permit
unprivileged user/network/mount/PID namespaces. No sudo or Docker socket is used.

From the repository root:

```sh
make setup
make doctor
make start
python3 scripts/urbit/harness.py status
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

`test` deliberately replaces only the marked synthetic **live fixture** from its
stopped clean seed. It recompiles native source, tests actual native ACK/NACK
outcomes across four senders and restarts the home. It never resets Git or edits
the working source. Logs/results remain under `.piers/fakes/logs/`; preserve failed
results. A timeout is an unknown result, not a permission denial or successful
save. The test command exits nonzero on missing, unexpected or failed outcomes.
After changing harness Python source, stop/start the supervisor before testing;
loaded-source hashing rejects stale process code.

`core-test` installs the separate `native/core/desk` into freshly restored fake
fixtures and executes the Work/Docs/permissions journey, native codec and state
version checks, and stock-Git materialization of home-created document objects.
It includes a real two-minute grant-expiry wait. `test` retains the original
counter smoke. Both commands own only disposable test state. The native core
report preserves independently tracked incomplete coverage (such as adversarial
subscription races) separately from executed business outcomes. Read
[NATIVE_CORE.md](NATIVE_CORE.md) and the exact evidence before inferring scope.

`stop` uses Vere's supported SIGTERM path, checks clean exits and waits for the
lifetime filesystem lock. A failed shutdown is reported, without force-killing and
pretending the seed is consistent. `reset` requires stopped processes and the
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

The independent native-core replay sampled a 96°C CPU peak. The main harness
currently has no thermal stop (Urgit's separate runner does). Monitor this local
machine and use `make stop` when necessary; functional test success does not
qualify repeated heavy runs or sustained load. The exact observation and open
operator/measurement gate are retained in TEST_RESULTS.md.

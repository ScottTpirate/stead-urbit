# Disposable local native CI

This Linux profile uses a reviewed controller commit and a separate immutable
candidate commit. Invoke the controller from this repository's designated
primary checkout, never from a candidate branch's executable scripts:

```sh
python3 -I -B scripts/ci/local.py --controller FULL_REVIEWED_SHA --candidate FULL_CANDIDATE_SHA
```

The controller's checked-in CI and harness Python files must exactly match the
working controller before imports. `.runtime` must be owned by this user and
private (mode 0700); run `make setup` to obtain the verified toolchain. The
profile shares the existing native execution lock with `make team-dev`. Run
host checks and browser qualification sequentially with native jobs.

The host reads bounded regular Git blobs, verifies their object identities,
and snapshots the reviewed inputs. Candidate Python, shell scripts, workflows,
Makefiles and tests never execute. Candidate apps, public libraries, marks and
frontend desk assets are composed with controller-owned test inputs. The v1
core/codec and their Git dependency must be present and byte-identical to the
controller. Changes to that predecessor closure require a newly reviewed CI
profile. Unknown or colliding paths fail admission.

Each job creates four distinct fake ships from the pinned boot image inside a
fresh bubblewrap user/PID/network/mount namespace. It never imports host piers,
stopped seeds, identity keys, SSH/Git credentials or user session sockets.
Network access is loopback only. Controller and candidate inputs are read-only;
state and temporary files live in size-bounded tmpfs mounts. Fake runtimes and
native helper children have no capabilities and no-new-privileges enabled.
Only the owned namespace packet controller retains its reviewed capability.

The same thermal guard enforces 75°C admission, 90°C stop, one CPU affinity,
50% CPU per 10 ms and a two-hour deadline. Additional cgroup limits are 12 GiB
memory, no swap and 256 processes; state/tmp limits are 8 GiB/512 MiB. The job
cannot start native execution until both systemd properties and kernel cgroup
files match the controller's admission proof. Every failure remains a failure.

The worker runs the fixed native suite, including its deliberate failure
control, real four-ship allow/deny/replay/update tests and cold restarts. A
separate compiled probe builds populated v1 state using the frozen predecessor,
calls the actual candidate agent's `on-load` under a synthetic bowl, checks
preserved Git/receipt/history/revocation state, round-trips v2, and rejects
corrupt/future envelopes. That probe is not a network upgrade or Phase 4 matrix.

Host verification requires exact source/mount/install identities, all expected
native arms, complete Newt frames, decoded verdicts, raw transcript/command
correspondence, the guard identity and verified owned-scope cleanup. An exit
code or candidate-written green file cannot qualify a job. Bounded evidence is
retained under `.runtime/local-ci/job-*`; ephemeral piers disappear at exit.
The separate `tests/ci` host controls exercise overlay and evidence rejection;
their synthetic records do not count as native execution.

The worker also executes a renamed native arm (the original required arm must
be refused), an intentional undefined Hoon symbol, and a finite two-second
native timer against a 50 ms client deadline with successful calls before and
after. Seed corruption is confined to the stopped disposable seed and restored
before use. A truncated owned copy is rejected by the real runtime pin checker;
an attempted write-open of the shared runtime must fail with EROFS. Corrupt and
truncated output checks inject faults into the retained actual native frame and
are labeled parser fault injection, not runtime-emitted corruption.

This is local disposable CI, not hosted GitHub Actions or a production build
service. It adds no billing commitment or deployment identity. Bubblewrap and
Vere share the host kernel; this profile does not claim VM isolation or immunity
to kernel/runtime vulnerabilities. Production build isolation is a separate
Phase 3 delivery gate.

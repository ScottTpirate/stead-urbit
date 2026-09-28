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
the shared runtime mount must be read-only and its write-open must fail with
EROFS or EACCES. File permissions can reject the open before the mount check;
EACCES on a writable mount is explicitly refused. Corrupt and
truncated output checks inject faults into the retained actual native frame and
are labeled parser fault injection, not runtime-emitted corruption.

This is local disposable CI, not hosted GitHub Actions or a production build
service. It adds no billing commitment or deployment identity. Bubblewrap and
Vere share the host kernel; this profile does not claim VM isolation or immunity
to kernel/runtime vulnerabilities. Production build isolation is a separate
Phase 3 delivery gate.

## Manual hosted profile (implementation under qualification)

`native-hosted.yml` is a separate manual workflow on the standard public
`ubuntu-24.04` runner. The exact `main` workflow commit contains a fixed-path
`specs/urbit/hosted-ci-controller.json` manifest pinning the separately reviewed
controller commit in this repository. The controller cannot be supplied as a
workflow input. The optional candidate is a full Git commit; only the same
bounded product blobs enter the worker. No candidate checkout, scripts,
workflow, Makefile, persistent cache, deployment credentials or live pier
executes or enters the worker.

Before any native execution, the root controller verifies GitHub's RS256 OIDC
signature and fresh random audience, numeric owner/repository IDs, public
visibility, exact workflow/ref/commit, manual event, run/attempt and signed
`github-hosted` claim. This authenticates the workflow job, not the physical
machine. Trusted workflow custody and GitHub's VM isolation remain assumptions.
The request credential and token are never saved or passed into the worker.
The signed workflow SHA binds the manifest at that exact Git commit; its
immutable controller SHA must match the captured and executed controller.
Evidence retains both SHAs, original manifest bytes, blob identity and hashes.
This lets candidate features be qualified before merging them into `main`.

The guardian is the root MainPID of a transient system service. A dedicated
unprivileged UID runs the bubblewrap worker. Kernel readbacks enforce two CPUs,
200%/10ms quota, 12 GiB memory, no swap, 256 tasks and a two-hour ceiling.
Read-only lease observations expire after three seconds; changed limits,
affinity, OOM/process-limit events and cancellation fail. A unique lifetime
pipe couples the workflow caller to the guardian; MainPID exit and whole-unit
OOM handling terminate all owned descendants. Final success also requires
observed inactive and empty cgroup cleanup and native evidence verification.
Hosted thermal management is provider-managed and unmeasured. The workstation
profile retains its 75/90 C guard unchanged; there is no environment-variable
thermal bypass.

The Ubuntu hosted profile also provisions one named AppArmor `userns`
allowance, selected by the privileged systemd service before its worker UID
drop and no-new-privileges setting. This is not an AppArmor confinement
sandbox: the namespace, read-only mounts, native capability drops and cgroup
controls remain essential. The VM keeps `apparmor_restrict_unprivileged_userns`
at 1 and hardens `apparmor_restrict_unprivileged_unconfined` only from 0 to 1
(or retains 1). No setting is lowered. Both settings, exact policy bytes and
guardian/launcher/worker labels are checked before and during execution.

The fixed pre-native controls must prove missing/wrong service-profile
refusal, unrelated unprivileged profile-transition and namespace-capability
denial, successful owned namespace setup, and all four lifetime/resource
failures. Setup records original/final settings, policy hash and parser/kernel
versions. This configuration applies only to the new disposable hosted VM;
the workstation is unchanged. Actual execution is still required.

Unrelated-control revision 2 attempts a direct `CLONE_NEWNS` call after entering
a new user/network namespace, with SYS_ADMIN present and no intervening exec,
mapping, socket or mount operation. Its accepted outcome is an actual namespace
creation or SYS_ADMIN-use refusal, not a NET_ADMIN/ioctl result. Exact PID,
times, namespace identities, labels and capabilities are retained; attributing
the refusal to AppArmor specifically also requires matching kernel audit data.

Primary platform references: [Ubuntu namespace restrictions](https://discourse.ubuntu.com/t/understanding-apparmor-user-namespace-restriction/58007),
[AppArmor parser](https://manpages.ubuntu.com/manpages/noble/man8/apparmor_parser.8.html),
[profile transitions](https://manpages.ubuntu.com/manpages/noble/man2/aa_change_profile.2.html),
and [systemd service profiles](https://github.com/systemd/systemd/blob/v255/man/systemd.exec.xml).

Only bounded input identities and verified result summaries are uploaded for
seven days. Private raw console tails, disposable credentials, piers and tokens
are excluded. Bounded credential-free launcher/service tracebacks are included
on setup failure. Fixed pre-native control consoles have a separate 8 KiB
diagnostic bound; native candidate consoles remain private. This profile is **not yet qualified**: passing host identity and
lease controls does not establish real hosted isolation, failure cleanup or
native acceptance. Record those actual runs separately before closing URB-110.

The workflow pins `actions/upload-artifact` v7.0.1 at
`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`; this standard action runs outside the
native namespace after cleanup. Bubblewrap comes from the signed Ubuntu Noble
package repository and its observed package version is recorded in the job;
the pinned Vere/kernel/pill and native test inventory remain unchanged.
The action's upstream MIT license was inspected at that exact commit. It is a
CI tool fetched by GitHub, with no action source vendored into the Stead desk or
SDK. Its job-scoped OIDC permission belongs to the trusted workflow environment;
it is not a claim that GitHub's request credential exists only in root memory.

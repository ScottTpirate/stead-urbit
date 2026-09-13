# URB-025: native Git candidate audit

Inspected/executed September 12, 2026 US/Eastern (September 13 UTC). Owner:
implementation agent `/root/urgit_audit`; independent runner review/test owner
`/root/qa_review`. These are agent reviews, not independent human approval or
production admission.

Urgit remains a dependency candidate. A bounded native/stock-Git corpus passed
14 checks on the initial runner. Independent review then found and reproduced
a host evidence-path symlink vulnerability in that runner. The repaired runner
passes 22 independent safety regressions; three subsequent native attempts
stopped at the tightened thermal ceiling before readiness, including one under
a verified 50% transient CPU quota. The initial pass is
retained as **pre-fix evidence**, and is not a completed native rerun of the
repaired runner.

No Stead Git integration, employee authentication, private-project isolation,
live network, frontend build, cloud deployment or production approval is
represented. The candidate used one separate disposable fake `~zod`; Stead's
four-identity harness is a different test surface.

## Source and license decision

The immutable candidate is
[`yapishu/urgit@9cec0371b02269efcdbd8580c42e883e69b82000`](https://github.com/yapishu/urgit/tree/9cec0371b02269efcdbd8580c42e883e69b82000),
committed September 11, 2026 at 04:19:58 UTC. Its archive SHA-256 is
`facf578b6edccbdb5b748ff16eabcbeaf10c4ca0dbc8c6073bedb0cbee7e5ee3`.
Exact URLs, hashes, assembly dependency and limits are in
[the candidate lock](../../specs/urbit/urgit-candidate.lock.json).

GitHub reported `license: null` and its license endpoint returned HTTP 404.
However, [the pinned application docket](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/desk.docket-0#L7)
explicitly declares `license+'MIT'`.
[Official Docket documentation](https://docs.urbit.org/build-on-urbit/userspace/dist/docket)
defines this field as the app license. The maintainer introduced the declaration
in [ca0d1396bdb17559a9fda2a959f4059a79945de6](https://github.com/yapishu/urgit/commit/ca0d1396bdb17559a9fda2a959f4059a79945de6)
on August 16. Thus the detector result alone does not establish an absent license.

All 132 regular source files were inspected in memory before writing the
candidate into the ignored evaluation area. No top-level LICENSE/COPYING/NOTICE,
full first-party permission text or first-party copyright notice was found.
Frontend lockfile license fields concern dependencies. The explicit MIT app
declaration supports this isolated local evaluation. Redistribution/import into
tracked source remains gated on a complete notice/provenance package; do not
invent copyright attribution. No candidate source was vendored into this repo.

The candidate [build file](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/build.zig#L17)
imports `pkg/base-dev/lib/skeleton.hoon` from `urbit/urbit` commit
`0f94550b941dfe046d9dff4a541330bd084e8cd1`. That exact file was used, SHA-256
`c7c654a91c5dc1a535d4a76b019ec175955e52961b1ddff70ad49121208d20f5`.
Its [upstream MIT notice](https://github.com/urbit/urbit/blob/0f94550b941dfe046d9dff4a541330bd084e8cd1/LICENSE.txt)
was separately verified and retained in the ignored input directory. Urgit's
own Zig and npm scripts were not executed. A future frontend/artifact build
must resolve its `npm install` path and `latest` requirements independently.

## Native assembly and environment

The runner verifies [the root toolchain lock](../../specs/urbit/toolchain.lock.json)
before each invocation: Vere 4.6, commit
`8ddc4b786979574dbfcb655e3db1b634f658d0de`; binary SHA-256
`47ad302e8934271dfc00dcdab1d553c6d6460b105e3099ff47e0e4e4231bb26d`;
kernel `408k-2`, commit `5a187fededc4582a34fcd6055c67bb63e0917b94`;
brass pill SHA-256
`b4babd14e9f1acbdb421b3c31c215ee637ad6691b7e382b99c6fd8991e623708`.
The passing native run returned `%408` from `zuse`; the candidate
[declares Kelvin 409 and 408](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/sys.kelvin).

Only the pinned desk and skeleton import were copied into a mounted `%urgit`
desk, without candidate source changes. All three candidate Gall agents
installed. This is a native candidate execution, with stock Git acting as an
external client inside the same isolated namespace.

Host: Linux `7.1.9-arch1-2`, x86-64 Intel Core i9-12900H, 64 GB physical RAM;
approximately 40 GB available at initial inspection. Git `2.55.0`, Python
`3.14.7`, bwrap `0.12.0`. One fake ship, loom exponent 31 (2 GiB), affinity
CPU 19. These are execution environment observations, not a capacity benchmark.
The old 99 C stop ceiling permitted a 96 C sample. It was lowered to 90 C;
the runner also refuses to start above 75 C or without thermal readings.
Samples are host-wide and cannot attribute heat to one process.

## Bounded corpus

The initial pre-fix run passed all rows below. Exact native request bodies,
Git argv, outputs and exit codes are preserved in
[the command transcript](evidence/2026-09-12/urgit/pre-fix-pass/commands.jsonl)
and [the result](evidence/2026-09-12/urgit/pre-fix-pass/report.json).

| Check | Observed result and limit |
| --- | --- |
| Pinned kernel readiness | `zuse` returned `%408`. |
| Native Git codec | Native blob OID equals stock `git hash-object --stdin` for `hello world` plus LF. |
| Native pack | Stock `git index-pack --strict --stdin` accepted the 56-byte native pack; exact blob bytes recovered. |
| Stock-pack native vector | All reported inflate/decode checks true. |
| REF_DELTA vector | Parse/resolve/decode true; six objects reconstructed. |
| OFS_DELTA vector | Decode true; six objects reconstructed. |
| Unauthenticated push | Git exit 128; prompts disabled; assertion excludes a missing-route 404. |
| Authenticated push | Original first commit OID preserved. |
| Clone | Exact file bytes/OID; stock `fsck --full --strict` passed. |
| Annotated tag | Exact tag OID preserved after push/fetch. |
| Incremental fetch | Exact second commit OID; stock fsck passed. |
| Stale client lease | Git exit 1, `stale info`, ref unchanged. Client lease check, not concurrent server CAS. |
| Corrupt pack | Flipped checksum byte rejected with unpack failure; ref unchanged. No general expansion/graph qualification. |
| Revoked token | Revoked before the next request; Git exit 128 and ref unchanged. No staged-revocation test. |

Blob OID: `3b18e512dba79e4c8300dd08aeb37f8e728b8dad`. Native pack SHA-256:
`d3a13f2f0179dbe263951b6dd16910310fe1117a27899bc9906caaa5b085e245`.
The single-blob bare vector's fsck exit was 0, with expected dangling-blob/no
default-reference notices. First commit:
`4c6822411f79230c1d8ae6e1d42d89bbd533b68e`; second:
`a57608b70cda4efa686ed3d92e71a728f4448f77`; annotated tag:
`4b2e0711ffe898baaaaf4f5f9569022980c7cd6a`.

Earlier scratch-driver failures remain in ignored `.runtime/urgit-audit/`:
`-t` disables terminal stdin; full `|commands` fail in Lens `source.dojo`;
app nouns need the `%git-action` mark. The wrong-mark attempt yielded two 404
Git failures and is excluded, including its overly broad preliminary denial
assertion. No candidate source fix was hidden in these driver refinements.

## Runner repair and reproducibility

Run `python3 scripts/urbit/toolchain.py fetch` when the pinned root toolchain is
absent, then `python3 scripts/urbit/urgit_audit.py`. No reset or caller-selected
deletion/destination exists. Each invocation leaves a unique marked, ignored
directory, source/pin hashes, outputs and a manifest.

The repaired `bwrap --unshare-all` environment has no external network, host
home/config, Git credential helper, or credentials. Only `/work` and `/output`
are writable persistent mounts. Host evidence is not mounted. `/input`, `/code`
and `/control` are read-only and have no writable aliases. Runtime/pill/kernel
and `/usr` are read-only; `/tmp`, `/proc`, `/dev` and the empty home are private.

Independent QA reproduced an outside sentinel overwritten through an
evaluator-created `evidence/report.json` symlink. Status reads, hash enumeration
and STOP touches had the same trust-boundary problem. Host output imports now
use a pre-opened directory descriptor, fixed names, O_NOFOLLOW/O_NONBLOCK,
regular-file/single-link checks and byte limits. Host writes anchor parent
directory components and atomically replace the final entry. A nonzero sandbox
exit forces a failed report. Early boot without a native control endpoint uses
immediate SIGTERM on stop; a ready runtime receives `+hood/exit` first.

Independent command:
`python3 -m unittest discover -s tests/urbit -p test_urgit_audit_safety.py -v`.
22 passed, covering outside final/parent-link writes, symlinks, FIFOs, hardlinks,
oversized files, parent rename, failed-process status, archive boundaries and
credential redaction across every stream split. These are local filesystem
tests; download/stream/process fixtures are explicitly mocked. They are not
native interoperability tests. A local rerun after the no-PORT shutdown change
also passed 22 tests; independent read-only review accepted that delta.

| Preserved run | Result |
| --- | --- |
| `20260913T011320Z-vw0a4w3q` | **Pre-fix**: 14/14; runtime/sandbox exit 0; last sample 330.2 s; max 96 C. |
| First post-fix start attempt | Refused above 75 C, exit 1, no fixture/runtime created. |
| `20260913T013127Z-q5ts_8zz` | Thermal stop at 93 C/20 s; max 95 C during shutdown; 0 checks, exits 1. |
| `20260913T013620Z-fmsmnyvc` | Thermal stop at 305.1 s/93 C before readiness; 0 checks, exits 1; immediate no-PORT shutdown. |
| `20260913T014440Z-doze539t` | Verified 50% CPU quota; thermal stop at 110.1 s/92 C before readiness; 0 checks, exits 1. |

Pre-fix pass and all failed runs remain separate. The aborted boots' `%term`/boot
failure is the deliberate termination result, not evidence of a candidate
source defect. [The evidence index](evidence/2026-09-12/urgit/index.json) records
original/copy digests and runner/helper hashes through the per-run provenance.
Copies omit piers, candidate source and raw native logs. Synthetic token and
Basic encoding were redacted before output; host paths/nodename are normalized
as stated in the index. The original manifests remain available.

For this heat-sensitive workstation, a further attempt used a transient user
scope without changing persistent system settings:

```sh
systemd-run --user --scope --quiet \
  --unit=stead-urgit-audit-20260913T014430Z \
  --property=CPUQuota=50% --property=CPUQuotaPeriodSec=10ms \
  /usr/bin/python3 scripts/urbit/urgit_audit.py
```

Use a fresh unit name on later runs. Observed systemd `261.2-1-arch` reported
an active scope, `CPUQuotaPerSecUSec=500ms`, `CPUQuotaPeriodUSec=10ms`, and
cgroup `cpu.max` exactly `5000 10000`. The runner/helper sources and 75/90 C
thermal guards are unchanged; affinity still restricts the sandbox to CPU 19.
The [resource-control snapshot](evidence/2026-09-12/urgit/thermal-stop-quota/resource-control.json)
records the exact outer command, active cgroup, throttling counters and tool
digest. This attempt also stopped before readiness at 92 C/110.1 s. Quota was
active; it did not prevent the host-wide thermal event. The guard was not
raised, and no further boots were launched. Completing the repaired runner's
native corpus in an adequate execution window remains open.

Final runner SHA-256:
`13ee74670b4b42fcb738fcff062db2bb61340bd63cb7f16c1a903796d7b84022`;
evaluator SHA-256:
`bd14bb9088a62420d65350a85c98553c48f4743adf05d7d61a3e8022a56d8f91`.
These match the final scoped attempt's provenance. Source commit for the
candidate is pinned above; worktree implementation files are identified by
these exact hashes and the containing PR's commit, rather than pretending an
uncommitted implementation had a published source commit during execution.

## Integration gates

The [architecture](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/specs/architecture.md)
describes native objects/refs and Git policy in `%urgit`, directly exposed
through Eyre Smart HTTP, with a delayed Clay bridge. Broader protocol and
feature claims remain maintainer descriptions except for the corpus above.
Documentation lags source: architecture says state `%1`, while current agent
state is `%4`; roadmap transport descriptions also differ from current code.

Source-review concerns below were **not dynamically exploited**:

- [write-authorized](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/app/urgit.hoon#L7800)
  accepts ship-owner Eyre authentication or one repository token and ignores
  Basic username. This does not provide individual Stead principal authorization.
- [peer-finish](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/app/urgit.hoon#L2596)
  admits staged native pushes without a current `repository-writable` recheck;
  permission is checked earlier in peer-offer.
- [clay-report](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/app/urgit.hoon#L9592)
  installs stored `applied.pending` after delayed work without re-reading current
  credentials/policy.
- [HTTP request pokes](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/app/urgit.hoon#L2233)
  and [peer activity watches](https://github.com/yapishu/urgit/blob/9cec0371b02269efcdbd8580c42e883e69b82000/desk/app/urgit.hoon#L9040)
  lack explicit local-sender guards; alternate-path security remains unproved.

No qualification is claimed for server concurrent CAS, staged revocation,
branch policy, private-project nondisclosure, cross-ship permissions, endpoint
isolation, crash-during-push atomicity, recovery RPO/RTO, hostile expansion/graph
limits, large repositories, SHA-256 repositories, LFS, shallow/partial clone or
Git-to-Clay behavior. Clay's symlink/submodule/path restrictions are distinct
from ordinary Git object storage.

Reuse reviewed libraries under Stead's single mutation owner, or require a
separate-agent transaction/fencing ADR and failure corpus before integration.
A Stead UI in front of independently writable Urgit routes does not satisfy
the authoritative-policy requirement. Licensing notices, integration security,
independent human review and the completed repaired-run native evidence remain
explicit gates; no approval is inherited from this audit.

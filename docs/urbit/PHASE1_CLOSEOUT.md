# Native qualification handoff — September 13, 2026

**Phase 1 remains unqualified; Phase 2 team/browser implementation has not begun.**
The common guardian refused real preflight samples of 93°C and 81°C before launching
native work. The approved fallback was source changes, lightweight verification,
preserved evidence and exact pending native commands. No thermal threshold was
raised and no cloud/identity/alternate runner was provisioned.

The current branch is `increment/native-core-qualification`, stacked on PR #34.
PR #32 is merged at `4bb28c645ed155f842f5b9479a0919e743a89378`.
PR #33 remains draft at `96971540cf70c557f01a5ef10db832ddee2e0130`;
PR #34 remains draft at `77428f6c35eb0fe7b7e497b64c5a1eab92e943cd`.
The last actually tested native product source remains
`f52293f7cd6970ded20e73b097beffb7418e4bbd`;77428f6 is its records-only binding.
The new source/evidence binding and current PR link are recorded in the adjacent
qualification evidence. No implementation PR was merged or force-pushed.

## What changed and what ran

The new source removes global resource-ID availability probes, scopes document
identity by container, projects a closed public receipt without private activity
counters, and reserves bounded project-local capacity for revocation. It adds an
explicit checked v1→v2 saved-format conversion while retaining exact historical
journal/receipt/Git bytes. The original freeze, corpus and evidence are unchanged;
the narrow v2 contract amendment has its own freeze.

Independent QA added a 148-case current corpus preserving the 129 original case
names, native observer metadata, delivery schedules, eight predecessor/capacity
recipes and a 73-requirement evidence gate. Bounded raw transport sidecars retain
successful and failed exchanges, including partial frames. These are new **source
capabilities, not observed native behavior**. Fixed fake bindings/containers and
privileged fixture controls remain test setup, not team provisioning or employee
APIs.

| Evidence layer | Current result |
|---|---|
| Local host/static/mocked |253 unit tests passed; plan, ecosystem and both freezes passed. Exact commands/output/source hashes in `qualification/root-lightweight-final.json`. |
| Real local platform | Doctor proved private loopback namespace/no home or Docker socket. Real93°C and 81°C guard refusals launched no child. A short actual systemd/bubblewrap exercise used explicitly mocked sensors; it ran no Vere. |
| New native Hoon | Not compiled or executed. Installed Clay and loaded native closure for this source are absent, never copied from old evidence. |
| Historical native | Original four-fake smoke and f522 core results remain valid only for their exact source. Historical96°C observation and 25 skipped assertions are preserved. |
| Git | Existing canonical document constructors and historical stock-Git exports remain separate from Smart HTTP and Urgit. No fresh native export run here. |
| Real GitHub | Seven reviewed milestones created; all 30 existing work issues assigned. PR/issue updates are coordination, not GitHub CI. No workflow enabled and no GitHub CI result claimed. |
| Browser/live/network/deployment | Not implemented/executed or approved. No public service, confidential data or live key was used. |

The toolchain lock is unchanged at
`4a209c10cf1756eb0f7357cc3eca8250bf66c239b4cd0ca31a8c0886d4d304ee`:
Vere 4.6 commit`8ddc4b786979574dbfcb655e3db1b634f658d0de`, binary
`47ad302e8934271dfc00dcdab1d553c6d6460b105e3099ff47e0e4e4231bb26d`;
kernel 408k-2 commit`5a187fededc4582a34fcd6055c67bb63e0917b94`; brass pill
`b4babd14e9f1acbdb421b3c31c215ee637ad6691b7e382b99c6fd8991e623708`.
Node 24.21.0/npm 11.19.0 and Git 2.55.0 remain pinned. URLs and compatibility evidence
remain in TOOLCHAIN.md and the executable lock.

This is not a benchmark. Host: Linux 7.1.9-arch1-2 x86-64, glibc 2.44,
Python 3.14.7, Intel i9-12900H, 64 GB RAM. No new native latency/loom/load claim exists.
The guardian retains 75°C admission/90°C stop, 1 s sampling/3s freshness,
one CPU and transient 50%/10ms quota. Raw log retention has explicit bounds;
evaluator temporary-file writes are time-bounded, not a hard disk quota.

## Existing issue dispositions

| Issue | Completed evidence | Current blocker / disposition | Later obligation or owner decision |
|---|---|---|---|
| #2 URB-000 | Private derivative/history/notices and correct remotes preserved. | Baseline evidence available; no new implementation approval implied. | Owner accepts closure. |
| #3 URB-010 | Exact runtime/kernel/pill/Node/Git pins and current doctor verification. | New source needs guarded compile/runtime evidence. | Future release compatibility is #25/#26. |
| #4 URB-020 | Historical four-fake smoke/restart; common safeguards, independent host tests and real platform/refusal evidence. | No four-ship run under the common guardian yet. | Sustained measurements remain #15/#16. |
| #5 URB-025 | Preserved Urgit candidate/license research and historical stock-client vectors. | Hardened replay and redistribution/integration authority remain open. | Optional candidate; does not block original Work/Docs constructors or UI. |
| #6 URB-030 | Original freeze preserved; independently reviewed narrow v2 amendment and vectors. | Changed native consumers uncompiled. | Explicit owner acceptance; second-org allocation/API/session amendments before activation. |
| #7 URB-040 | f522 historical Work/Docs plus reviewed v2 privacy/capacity/migration source. | Native repros, boundaries, exact-content export and compatibility evidence required. | Complete exports/recovery belong to #13/#26/#27. |
| #8 URB-050 | Historical sender/permission tests; reviewed v2 current-auth ordering and protected audit design. | Actual scoped privacy, capacity/revocation and delivery regressions missing. | Sessions/bypass/browser are #9/#10/#21. |
| #20 URB-170 | Four local skills retained; Hoon/security/testing used selectively; structural checks passed. | No skill-effectiveness or LSP benchmark claimed. | Optional tooling evaluation cannot delay native Work/Docs. |
| #24 URB-210 | Independently reviewed [Phase 1 threat/test map](PHASE1_THREAT_TEST_MAP.md) and pinned owner-local Gall exposure inventory. | Phase 1 design/test inventory has no remaining bounded source-review blocker. | Runtime browser, key-continuity, storage, recovery and release tests remain with owning issues; owner accepts design closure. |

## Required evidence and pending command

All 25 historical skips remain unchanged. The new manifest tracks 22 delivery
observations, the wider scoped-confidentiality claim, one narrow absent-effect
disposition and one source-ordering obligation. Source/N-A evidence stays labelled
separately. No required native skip has become a pass. The new current gate fails
with missing native evidence, including the actual delayed inbound old-leave
schedule. An owner-controlled stale local `%leave` request may be discarded by
Gall before transport; it does not prove injection at the home. That remaining
test mechanism must be implemented/reviewed, not renamed away.

The counter-u64 probe is a local pure representation-edge test, not a fabricated
near-capacity history. The4096-event fixture instead uses real archived
transitions. Predecessor conversion, current-format roundtrip, graceful restart,
installed-app upgrade and abrupt-crash recovery are separate claims.

After the workstation meets the unchanged execution policy, use one owner and a
fresh supervisor. Do not retry hot starts. The exact pending native sequence is:

```sh
make doctor
make start
python3 scripts/urbit/harness.py status
# Continue only once status reports ready:true and the current guard lease.
make test
make core-test
make stop
```

If any step fails, retain its output and run `make stop`; never label forcibly
stopped state a clean seed. `test`/`core-test` may restore only verified, stopped,
marked disposable fixtures. They must not reset Git/source. Bind native results
to source, installed Clay, loaded closures, locks, corpus and runtime, retain
evaluator-failure/>64KiB controls, then have independent QA verify the artifacts
with `scripts/urbit/qualification_gate.py`. Missing source/N-A bindings or native
obligations keep the current gate nonpassing. Do not substitute the 253 host tests.

## Stack and next capability

Retain #33/#34 as drafts while the current gate is open. This amendment is another
stacked draft, not permission to merge. After explicit owner approval, integrate
the base first, reconcile dependent PRs without discarding commits, and validate
the exact integrated candidate. Local evidence is not GitHub CI.

After Phase 1 blockers close, the next increment is configurable synthetic
organization/member/project/container setup, explicit shared pages and a separate
public-API client (#21). Then implement the reviewed authentication-to-core
adapter, individual native-approved browser sessions, safe local HTTPS and the
two-user/outsider Work/Docs journey (#9/#10), with #14/#29 tests. These have not
been implemented in this checkpoint. Full search/activity/inbox remains #22.

Smart HTTP/reviews/agents/storage/build workers (#11/#12/#23/#28), actual recovery,
reproducible releases/upgrades/multi-host canary (#13/#15/#16/#25/#26/#27), replicas,
fencing/self-dogfooding/browser-only identity (#17/#18/#19), and independent
adopters/maintainers/private reporting (#30/#31) retain their later gates. No
ecosystem parity requirement has been added to the first native slice.

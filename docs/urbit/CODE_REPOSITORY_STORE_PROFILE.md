# Repository acceptance prototype — version 1

Status: the pinned native evaluator passed all 41 test arms plus the deliberately failing tang and compiler-error controls (43 checks total). This is pure prototype qualification only.

`accept(db, current-scope, credential-ledger, bearer, request-id, payload-digest, now, current-membership, current-repository-policy, current-ref-policy, protected-refs)` returns applied, replayed, or rejected, each with the full resulting state. Rejection returns the input state exactly. A successful application returns one new version-1 state containing objects, refs, incremented revision, accepted receipt, and journal entry, and removes the staged request.

The configured Home is the sole future state owner. All state and resolver/policy closures are Home-owned inputs, not user claims. The reducer reads the requested staged record from that state; it does not ingest raw wire bodies. Current individual credential, exact home/project/repository/epoch, and current principal binding are checked before any receipt lookup. Replay additionally checks current per-ref policy before comparing the digest. Protected ref create, advance, and delete all fail until stored review integration exists.

The fingerprint binds the exact post-parser payload, including request ID, scope, owner, ordered ref commands, and exact object bytes. It does not bind a raw pack transfer. Future staged admission must separately bind raw-pack digest and expiry. Candidates are rehashed and structurally checked, refs pass the existing atomic receive reducer, and fast-forward checks use the verified parent-only ancestry module. Candidate objects outside the resulting ref closure cannot persist. Previously accepted objects may outlive refs; every future read still requires current scoped reachability.

Proof limits: 16 incoming objects and 64 KiB of incoming bodies; 64 stored objects and 256 KiB of total bodies; 8 commands with 128-byte ref names; 16 refs; 4 pending requests; 32 receipts/journal entries. Closure has 512 visits and 1,025 turns. Parent ancestry has 128 steps, 256 queued edges, 256 KiB, and 129 turns. These are small synchronous prototype budgets, not a production event budget. Durable staged validation must precede production adoption.

41 native test arms cover atomic create/advance/delete, replay after subsequent writes, revoked credential/member/repository/ref policy, digest and scope tampering, protected actions, unreachable/missing/corrupt objects, ref races, whole-state rejection, quotas, synthetic inconsistent-store collision, and version-1 noun roundtrip. A separate nonempty failing tang and compiler error are mandatory controls. Noun roundtrip is not Gall persistence, restart, upgrade or migration proof. The store assumes valid Home-owned existing state; it is not an arbitrary corrupted-snapshot repair API.

The private fixed verifier is `.runtime/code-store-2_6824bq/store_check.py`. It accepts no caller-selected source or command, verifies runtime pins, retains all input hashes before/after, runs the explicit inventory in the existing serialized thermal/CPU guard with a 120-second cap, and records both failure controls. Successful run: `.runtime/code-store-2_6824bq/runs/20261109T124437Z-x07pgrd3`, report SHA-256 `3d111bf082c88a5220717703d66b3e07ce49648520cbfdf18e01f23739ad6da9`. Exact input hashes matched before/after; the 10.028-second guarded scope is inactive/dead. `.runtime/code-store-2_6824bq/receipt.json` binds the evidence and retains the earlier failed test-only noun cast attempt. No listener, Gall save/load, accepted Git HTTP write, protected review integration, production deployment, or phase completion is claimed.

## Exact proof inputs

The successful pinned evaluator run used source commit `b98419049e611064af058d7b5aced0e6b02a1cdd` plus the private candidate files below. Promotion copied those library and test bytes unchanged. Current imported ancestry and credential sources were rechecked against the successful input receipt before promotion. The full selected input hashes matched before/after; this evidence does not qualify later edits.

| Input | SHA-256 |
| --- | --- |
| `native/core/desk/lib/stead-code-store.hoon` | `8cf56b11d1a1b7e26b85b089eb17871f0dac43080e1a239b06505988c521bed9` |
| `native/core/desk/tests/stead-code-store.hoon` | `0da14d665e30eeb8ed581a0b1bf0f074e3dc4e47f255a01e4b54f665086afb43` |
| `native/core/desk/lib/stead-code-ancestry.hoon` | `d46a3af25bb6a1ce0cdb36497717a160c96247fd1bcf831cff7035c7e4db91b9` |
| `native/core/desk/lib/stead-code-credentials.hoon` | `6e7eb121e5aa7bb36f80170eeb58bd87db52348a40189ef4f7682952647de2d5` |
| `.runtime/code-store-2_6824bq/store_check.py` | `593dfe4362681ca8b6ead9fdb51349d36dd777113f704f74c4b4e0e769beb35e` |
| `.runtime/code-store-2_6824bq/receipt.json` | `4f851f9966e16b55627e6b9b351c6b8c4fb9c7d4b174acda10476eabb6351a6e` |

Runtime: pinned Vere 4.6, 512-MiB loom, existing serialized thermal admission and CPU 19 at 50%, 120-second outer cap. Successful duration 10.028 seconds; observed maximum CPU temperature 51°C. Both compiler error and nonempty failing tang controls were recognized. Scope `stead-native-a9453cc232cab74267db822755c9a6a8.scope` was observed inactive/dead. Guard report: `.runtime/execution-runs/code-store-prototype-vq2qebx1/report.json`.

The retained first attempt at `.runtime/code-store-2_6824bq/runs/20261109T124403Z-b985a90t` failed native type nesting in the test-only jam/cue vase cast. The test was corrected to compare exact nouns; the library remained byte-identical. No failed attempt was reclassified as passing. The fixed verifier and raw outputs remain private local diagnostics, not a new production runner or endpoint.

Next integration is durable, expiring, repository-scoped staged admission owned by the existing Home, followed by a persisted atomic state/event transition and real authenticated receive endpoint tests. This pure reducer is not wired into saved Gall state. The new store version does not change any existing production state schema, and no migration is claimed.

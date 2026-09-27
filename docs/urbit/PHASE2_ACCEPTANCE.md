# Phase 2 acceptance inventory

Status: candidate inventory. This document is not a passing test report.
Phase 2 remains open until exact-source execution and independent review cover
the applicable cases below. Development runs remain separately labeled.

## Native authority and transport

1. Compile every expected pure unit and Gall app on the pinned runtime. Reject
   missing/zero arms, compiler failure, bad or truncated output and timeout;
   execute a deliberately failing native control.
2. Four fresh disposable identities: owner-local configuration succeeds;
   remote configuration and an unbound sender receive the specific native NACK.
3. Final grants: creator/contributor/reader/outsider, stale revisions, duplicate
   commands, revocation before commitment, and recovery of the exact receipt.
4. TLS: native listener ownership, CA, hostname and exact certificate; wrong
   CA/hostname/leaf, unrelated listener, dead child and guard loss fail closed.
   Anonymous Eyre provenance does not gain ship-owner authentication.
5. Startup and restart: sealed suspension input, saved-version/fingerprint
   verification before reload, fresh bootstrap incarnation, ingress and peers
   blocked until verification, all four old children reaped, committed state
   and receipts preserved. Test unsuccessful startup/reload/cleanup as well.
6. Session/endpoint boundary: origin and CSRF checks; challenge/browser/home/
   principal/binding binding, one-use approval, replay/fixation/expiry/logout,
   key/binding revocation and restart invalidation. Raw native marks, scries,
   Eyre channels and installed trusted-app paths cannot bypass Stead grants.

## Real browser with native home

Each case uses actual TLS and native responses. Mocked rendered controls are
useful regression evidence but cannot satisfy this section.

1. Two distinct principals, separate browser contexts and personal approvals;
   compare the home and challenge code. The organization owner's credential is
   never an employee sign-in. A third unbound identity is denied.
2. Create a general project and Work item, edit and reload, receive an attributed
   accepted receipt, and observe that work from the authorized second member.
   Code/PR/Build navigation stays absent for the general profile.
3. Create private and shared document collections, save/edit canonical Markdown,
   link Work and Docs, explicitly publish one selected page, and verify the other
   private page remains absent from the second member's lists/search/activity/
   inbox/counts/cursors. Confirm ordinary Git-backed persistence separately.
4. Two-user stale save leaves local edits intact; explicit comparison/rebase and
   retry use the current revision. A lost response uses receipt recovery or the
   original request ID. An unsuccessful resume cannot erase the pending request.
5. Session expiry, logout, revocation and account change clear rendered private
   state. Secure/HttpOnly/Strict/host-only cookies stay on their own origin;
   drafts, bodies and bearer values do not enter URLs or browser storage.
6. Keyboard-only principal journey, labels/focus/error/live regions, small and
   large layouts, empty states, Unicode/long text and distinct time zones.
   HTML/script/event-handler/unsafe-URL content remains inert.
7. Network loss preserves local drafts, reports an uncertain save accurately,
   and never invents an accepted outcome or automatically replays mutations.
8. Record actual useful-content/save timing and eager/lazy asset transfer bytes
   on a declared machine/runtime/workload. Do not convert a target into a result.
9. Runner controls: verification remains enabled, clean private trust profile,
   fixed fixture destinations, no debug/key logging, whole browser cgroup cleanup
   after success, timeout and controller death, and source digests before/after.

## Updates and independent integration

1. Same final authorization for native and browser commands/queries/updates;
   unknown versions, malformed/oversized envelopes, bounded errors/correlation.
2. Open/poll/cancel/resume subscriptions; cancellation is idempotent. Reject
   cross-actor/scope/purpose cursors, stale/replayed cursors and reordered updates.
3. Revoke or expire a subscriber before dequeue: queued data is discarded.
   Unrelated private edits produce no visible counter/cursor change.
4. Enforce global/per-actor watch and cursor caps, 16-row watch queue and 64-row
   retained scope window. Overflow closes the watch with refresh_required.
   Restart/configuration/bootstrap require fresh views and watches.
5. Build a native consumer solely from the exported developer package and pinned
   declared dependencies, with private implementation fixtures unavailable.
   Execute allowed Work creation/read and denied scope through that package.

## CI and onboarding

1. Disposable native CI executes a positive compile/unit/multi-ship/migration
   run, the native failing control, missing arm, compiler failure, timeout,
   corrupt/truncated output, cache/seed poisoning, admission refusal and cleanup.
2. Immutable reviewed controller and pinned inputs; untrusted candidate source
   is read-only in an isolated job without deployment credentials, live piers,
   privileged host sockets or shared writable caches. Hosted resource admission
   is reviewed independently; workstation thermal limits remain unchanged.
3. Contributor, member, operator and third-party integrator quickstarts describe
   only supported commands and scopes. A nonauthor receives just the quickstart
   and task; record participant type, errors and completion time. Automated
   participation is not presented as a human usability study.
4. Consent-aware support export contains bounded versions/diagnostic codes and
   correlation IDs, excluding keys, cookies, private messages and document bodies.

## Closing the milestone

Bind execution to the exact source/tree, toolchain and expected-case inventory;
retain failures and negative controls; obtain independent review of behavior and
evidence; push and integrate the reviewed PRs; reconcile URB-060, URB-070, URB-110,
URB-180, URB-190 and URB-260 with their acceptance evidence. Local fake-ship
acceptance does not authorize production deployment or prove live key custody.

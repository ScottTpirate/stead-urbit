---
name: stead-gall-security
description: Review or implement Gall state, migrations, authorization and events in stead-urbit. Do not use for unrestricted ship administration.
---

# stead-gall-security

Read root AGENTS.md and the frozen command/policy contract. Identify the principal, project, authority epoch, expected revision, request ID, trust boundary and final mutation owner before editing.

Keep on-save and on-load version envelopes exactly consistent; test a saved state from each supported predecessor, not only a fresh install. A pure runtime does not imply authorization or safe migrations. Stage validation and current policy checks before one accepted state/audit/effect-intent transition. Receipt is not acceptance. Retried commands must not duplicate accepted work or repeat external effects.

Audit HTTP, native poke/watch/fact, peek/scry, Git/Clay, export and admin paths. A callerless scry is not an authenticated user API. Derive identity from verified transport/session/delegation, never an actor field. No sponsor, parent team or generic administrator content grant. Recheck before commit and future subscription delivery; reject stale authority.

Bound parsing, object traversal and work per event. Durable jobs require persisted intent/checkpoints; Spider threads may fail across upgrades. Separate application effects from external execution; never replay a deployment blindly. Do not route private bodies to personal ships by default. Restoring a pier must not resurrect keys/sessions or start a second live identity.

Add positive/negative/concurrency/restart/migration tests and request independent review. Report platform-isolation assumptions explicitly. References: https://docs.urbit.org/urbit-os/base/threads ; https://docs.urbit.org/build-on-urbit/userspace/dist ; docs/urbit/ECOSYSTEM_PLAN.md.

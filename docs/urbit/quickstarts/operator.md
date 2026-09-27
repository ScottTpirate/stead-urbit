# Operator quickstart: local team alpha

The qualified target for this phase is a disposable Linux fixture. No rented
server, purchased Urbit identity, production ship copy or public DNS is needed
for that target. Production desk distribution and recovery belong to later
phases; this guide does not authorize a production installation.

Follow the [contributor guide](contributor.md) to prepare the pinned toolchain,
verified clean seeds and `make team-dev`. The harness creates a home at `~zod`
and separate synthetic identities. Alice (`~bus`) can create projects; Zoë
(`~nec`) receives only the explicit grants made by the fixture. An organization
ship's owner credential does not sign in as either person.

The operator's configuration names one home, its exact HTTPS origin,
organization/team IDs, each person's immutable principal and native binding,
binding revision/expiry, and the small explicit project-creator list. Display
names do not establish identity. Sponsorship, ship ownership and organization
administration do not implicitly grant project content access.

Initial configuration requires an empty home. Later configuration changes use
the expected configuration revision. Removing or replacing a binding advances
its revision history and invalidates old sessions and handles. Never recycle a
binding ID for a different person, create a second live authority, or copy a
production pier into this development fixture.

Owner configuration and test credentials stay in the private operator harness.
Do not publish `.runtime`, `.piers`, TLS keys, fake `+code` values or browser
profiles. The browser test uses native Eyre TLS through fixed loopback byte
bridges and trusts its local CA only inside a disposable profile. Lens and Khan
remain private. A proxy's forwarding headers cannot establish secure transport
or identity.

Stop with `make stop` and wait for the stopped confirmation before preserving
or resetting the fixture. Keep the verified stopped seed directory. Preserve
failed runs and their evidence before another run; an interrupted state is not
a clean seed. A cold restart must pass suspension, fresh bootstrap and ingress
checks before browsers or peer messages are admitted.

Support reports are opt-in downloads with a visible preview. Ask for that report
and a description of the action, not cookies, identity codes or private page
bodies. Reconcile an uncertain save using its original request ID. A rollback
of application source is not automatically a safe saved-state downgrade.

# Scope and authority

Work only in the new `stead-urbit` repository. Never modify or push to `ScottTpirate/stead`. Verify remote URLs before every write. Treat `upstream` as read-only.

For this experimental derivative, `docs/urbit/MASTER_BUILD_DIRECTIVE.md` governs architecture. `reference/stead/` is historical source material, including the former directive and gates. Preserve its provenance, licenses, notices, requirements and useful tests; do not reactivate the old stack accidentally.

The user authorized a separate experimental rewrite and implementation/deployment plan. This does NOT authorize purchasing hosting or identities, exposing confidential data, changing existing infrastructure, weakening security gates, or claiming unexecuted tests passed.

Read `docs/urbit/AGENT_HANDOFF.md` before implementation. Begin with an executable fake-ship harness and the dependency/license audit; do not run parallel feature rewrites against unfrozen contracts.

Core invariants: one authoritative project home initially; explicit grants; no sponsorship-derived permissions; no shared organization +code; no production ship copied into development; no simultaneous live copies of a ship; ordinary Git identities preserved; no private data broadcast; all mutation paths reach final authoritative authorization; deny-by-default for missing or stale policy evidence; no automatic cross-domain transfer.

Separate proposal receipts from committed business outcomes. Separate real test execution, mocked tests, and planned checks in every report. No fabricated Hoon source/build success, hashes, benchmark numbers, or deployment URLs.

Keep code changes small, version state migrations, and assign independent review. Deployment approval and secret/identity provisioning remain human-controlled. Untrusted build runners and extension code never execute on the authority host.

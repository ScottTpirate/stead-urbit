# Native implementation boundary

The counter in `native/desk` compiles and passes the real four-fake-ship smoke/restart corpus. It is deliberately limited to URB-020 and does not implement Work/Docs or application sessions. See `docs/urbit/TEST_RESULTS.md` and `RUNBOOK.md`.

The first product state/authorization increment will use `native/core/desk` under the minimum frozen contracts, keeping the original counter fixture reproducible. Only one `stead-home` version runs on a given disposable home at a time.

Proposed layout, to be created as implemented:

- `native/desk/app/stead-home.hoon`: the initial mutation-owning Gall agent.
- `native/desk/lib/stead/`: pure domain, policy, Git, and validation libraries.
- `native/desk/sur/stead/`: shared native types.
- `native/desk/mar/`: versioned wire formats.
- `native/desk/tests/`: native conformance and migration tests.
- `web/`: selectively reused React/TypeScript UI, not an unnecessary Hoon rewrite.
- `deploy/urbit/`: reproducible host/service setup, introduced only with tested runtime pins.

An identity-only helper agent may live on member ships. It must not become an accidental storage proxy for private organizational content.

One home agent initially owns the transaction boundary; multiple library modules do not require multiple authoritative agents. Heavy decoding may be staged, but the final policy/ref/revision decision belongs to that authority. Do not assume separate Gall agents share an atomic business transaction.

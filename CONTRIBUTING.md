# Contributing

New product work follows the [experience contract](docs/urbit/PRODUCT_EXPERIENCE_CONTRACT.md)
and [mapped execution packages](specs/urbit/product-execution-plan.yaml).
T01–T32 supplement existing URB parents; a closed historical issue does not accept
new scope. Shared contracts/migrations have one integrator, and independent review
must distinguish implementation from qualification and supported release claims.

Stead Urbit is an experimental native implementation, not a supported production release yet. Start with AGENTS.md, docs/urbit/DEVELOPER_GUIDE.md and roadmap issue #1. Use an existing URB issue rather than duplicate the current agent's increment.

Discuss shared state, protocol, policy and storage boundaries with the current integrator before parallel edits. Preserve the original repository and archived reference tree. Keep one cohesive, reviewable change with native positive/negative tests, documentation and upgrade impact; do not create a separate governance packet for every helper.

Use synthetic fixtures, pinned dependencies and disposable fake ships. Never commit piers, keys, +code, private messages, cookies or customer content. New dependencies and copied examples require actual license/provenance review; archived approvals do not automatically apply. Retain notices; do not silently relicense third-party code. A DCO/CLA policy must be expressly adopted before claiming contributors agreed to one.

PRs report exact source/toolchain, actual commands, outcomes and skipped tests. Static or mocked results are not native execution. Independent review is required for security, state migration and releases; self-review is not independent approval.

Be respectful in technical discussion, provide reproducible reports and review behavior rather than personalities. Maintainer/release succession and public contribution operations are tracked by URB-270. Read SECURITY.md before reporting vulnerabilities.

# Proposed upstream skill correction

Status: prepared locally, not sent upstream. Author: `/root`. This is the separate
fix proposal for URB-170; it changes no imported code or frozen evaluation input.

Target: `thelifeandtimes/running-urbit` at
`90912c1425573de37110a65627c6ab4bf125586c`, `skills/gall-agents/SKILL.md`.
The [recorded intake review](../DEVELOPER_GUIDE.md#community-material-worth-evaluating)
found a minimal example that saves an untagged state but loads a tagged version
union. A later example recommends version tags. The sampled upstream example
was not compiled by this project and remains reference-only, with its MIT
license decision recorded in `specs/urbit/ecosystem.json`.

Proposed change: make the minimal example's saved payload and accepted load mold
agree on one explicit version tag. Show each supported old version in a separate
conversion branch, reject malformed/future versions, and distinguish an initial
empty state from a supported persisted version. Do not silently discard fields
or reinterpret an old payload as the new mold. Label illustrative code as
unexecuted until its exact source is compiled against a named pinned kernel.

Proposed upstream verification: run the actual agent's on-save and on-load arms
for a nonempty state, compare the complete round-trip noun, convert a declared
older version, and require malformed/future input rejection. Include a deliberate
wrong expectation to demonstrate failure propagation. A parser check or a
`validated: safe` annotation does not establish these behaviors.

The project's [frozen T03 task and actual outcomes](../evidence/2026-09-26/workflow-evaluation-v2/README.md)
exercise matching versioned save/load and rejection cases on Vere 4.6 / kernel
408k-2. That separate local execution is not a test of this upstream example
or a compiler guarantee for the proposed prose change. No upstream issue, PR,
message or package installation has been made as part of this proposal.

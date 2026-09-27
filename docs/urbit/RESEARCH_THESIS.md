# Research directions, not shipped capabilities

The product hypothesis is a portable organization work graph with explicit
governance, controlled knowledge publication and scoped human/AI-agent evidence.
This increment establishes the experiment's environment and contracts only.

| Direction | Proposed record and boundary | Evidence before implementation claims |
|---|---|---|
| Fork working context | Authorized snapshot at a journal position, ancestor project ID/digest, and explicitly new governance. Export only resources the successor may receive; do not expose restricted links by listing omitted records. | URB-100 export/restore plus custody/disclosure tests; URB-140 lineage/migration review. No automatic copying of private discussions or grants. |
| Work carries evidence | Link requirement, decision, exact Git revision, test attestation, reviewer authority and release. Keep builder identity/trust policy and revoked/historical approval evidence inspectable. | URB-090/100 implement interoperable attestations, offline verification and rejection of missing/untrusted evidence. Test results are observations, not proof of correctness. |
| Scoped durable agent interactions | Persist who requested what, on whose behalf, approved disclosure, resulting proposal and authority. Separate clarification, proposal, merge and release powers. | URB-050/090 test delegation intersection, expiry, revocation and non-escalation. A Gall application component is distinct from an AI agent principal. |
| Explicit knowledge publication | A newly authorized fragment/summary record with source and approver references; source references themselves may need redaction. | URB-070/090 require deliberate publication and recipient handling checks. No bulk private-chat ingestion or silent AI redistribution. |
| Replay and policy simulation | Versioned transitions consume recorded external results; hypothetical policy runs produce separate scenario output, never alter accepted history. | State migrations, determinism and effect-idempotence tests before URB-100 claims. Replay cannot reproduce an unrecorded response or establish its truth. |

Use [SLSA build provenance](https://slsa.dev/spec/v1.2/build-provenance) for build
definition/execution evidence, rather than introducing an incompatible substitute.
Connecting that evidence to requirements and delegated approval is the proposed
Stead extension. The builder's trust and possible compromise remain part of
verification; hashes alone cannot make a dishonest builder trustworthy.

[Radicle's protocol](https://radicle.dev/guides/protocol) already supplies repository
identity, signed collaboration and Git replication. Decentralized Git collaboration
is prior art, not Stead's novelty claim. The combined organization semantics are a
research thesis, not a demonstrated breakthrough or something mathematically
exclusive to Urbit. A conventional implementation could explore the same ideas.

These directions constrain future designs without widening this increment into
federation, agent messaging, public anchoring or a new ontology. No message to an
external person or agent service, build effect or deployment was authorized by
describing these proposals.

# Development and deployment plan

September 12, 2026. This is a plan; no cloud resources or Urbit identities have been purchased/provisioned.

## Local development first

Use a Linux x86-64 development machine or VM. Begin with the existing hardware, not a hosted production node. Target 16 GB available RAM for a four-ship test harness as a planning allowance, not a verified requirement; measure actual RSS/loom and reduce concurrency when needed. No GPU is required for the application.

Pin the Vere release/commit and checksum, boot pill/kernel compatibility, desk dependencies, Node version, frontend lockfile, Git version and protocol corpus. `specs/urbit/toolchain.lock.example.json` deliberately contains unresolved pins; it must not be treated as an executable supply-chain lock. Review the actual current release, not an old article's version.

Use four fake identities: `~zod` home, `~bus` contributor, `~nec` reader, `~bud` outsider. The initial owner is the home harness administration context. These are synthetic roles, not rank privileges. Fake ships on the same machine can communicate but cannot join the live network. Run them in one private development VM/container network namespace with separate processes and pier directories; do not assume separate Docker loopbacks support the documented same-machine fake networking automatically.

Create a clean seeded fake fixture, stop it before copying, and reset only explicitly marked disposable paths. Keep piers, credentials and logs with private input out of Git. Start/stop/reset/doctor targets must be implemented and tested before advertised. The currently supplied validator validates only planning metadata.

Daily loop: small branch -> edit native libraries/agent or UI -> copy/sync into mounted development desk -> compile/test on pinned fake ship -> multi-ship and browser tests -> export round trip -> PR -> independent review. Keep a real failing test for every bug.

## Continuous integration

Keep GitHub as the source of truth initially. Each PR runs static checks, native compile/tests, four-identity permission scenarios, browser tests, ordinary-Git interoperability, migrations, export/import and malicious-input limits appropriate to its phase. CI jobs use disposable fake ships and synthetic repositories.

Run untrusted work on disposable hosted or tightly isolated runners. Never attach an unattended public-PR runner to the authority VPS, a production pier, the developer's unrestricted home machine, or a Docker socket controlling live services. Live deployments use a separate protected environment with explicit human approval. Pin action dependencies and keep tokens read-only unless a narrowly reviewed job requires otherwise.

Inherited Stead workflows are archived by bootstrap, not enabled. Implement the new CI only after native commands exist. Do not copy existing repository secrets or activate upstream webhooks.

## Shared test host

After the first local acceptance slice passes, rent one ordinary VPS. Initial target: x86-64 Linux, 2-4 vCPUs, 8 GB RAM, at least 80 GB SSD, public IPv4 and permitted UDP. Prefer 16 GB if several live ships or build imports share the box. These are experiment-sizing hypotheses; this is not an enterprise performance promise.

The main authority ship gets its own Linux service/user and private pier. A small identity/test ship may share the machine for a synthetic pilot, with separate services, state and ports. For meaningful cross-host tests run the other peer on local equipment or a second disposable VM. Do not host all participants on one VM and call that evidence of network resilience or independent custody.

Keep builds on CI, not on this VPS. Use a small reverse proxy for HTTPS, an allowlisted application surface, a restricted administration route/VPN, and native UDP routing for the ship runtime. Allocate distinct required ports per ship and verify against the pinned runtime; an HTTPS-only reverse proxy is not the native transport. Block public debug/admin/native-local endpoints.

Do not install unrelated third-party apps on the authority ship. Use the runtime's supported shutdown and consistent-backup procedures. Store ownership/recovery secrets outside the VPS and outside Git; use independently managed encrypted off-host backups. Host operators remain in the plaintext trust boundary unless a separate client-encryption architecture proves otherwise.

No Kubernetes, RDS, NATS, OpenSearch, NAT Gateway, global load balancer, Ethereum node, star, or galaxy is required for the first prototype. A later need can justify an adapter; do not provision unused stack components.

## Hosting options checked

Source links and dates are in SOURCES.md. Values below exclude items not explicitly listed and are not purchase quotes.

| Option | Listed compute | Published base price | Caveat |
|---|---|---|---|
| Existing Linux hardware | Use available capacity | No additional server subscription | Keep development synthetic; hardware/power still have costs. |
| Hetzner CX33, Germany/Finland | 4 vCPU, 8 GB, 80 GB | USD 9.99/month, excluding IPv4 and VAT | Cost-optimized stock is limited; confirm location and checkout availability. |
| AWS Lightsail Linux with public IPv4 | 2 vCPU, 8 GB, 160 GB | USD 44/month | Backups, extra storage/transfer, identities and taxes not included in this figure. |

The Hetzner figure is the new USD price in the provider's June 15, 2026 adjustment table, updated July 8, not older promotional pricing. It is an EU cost-optimized SKU, not a claim about an Ashburn SKU. Lightsail's table lists USD 24 for 4 GB, USD 44 for 8 GB and USD 84 for 16 GB general-purpose IPv4 bundles.

Recommendation: develop locally; try an available CX33 for inexpensive public/synthetic staging if European location is acceptable. Use Lightsail 8 GB when US hosting/AWS familiarity matters more than the saving. If the inexpensive SKU is unavailable, do not silently substitute a much more expensive Hetzner plan. Reserve an estimated USD 20-30/month for the inexpensive staging setup including modest backup/storage allowances, or USD 50-65/month for Lightsail staging. These are planning budgets, not verified all-in bills. Identity acquisition, CI overages and inference are separate.

No server purchase is justified before the local native slice exists.

## Live identities

Use a dedicated organization-owned planet for the project home when ready for live-network canary testing. Keep it separate from a personal daily-use ship. A separately controlled developer planet can test external membership; service/distribution moons are optional and inherit their parent's key-control dependency. Comets can be useful for disposable experiments but are not the permanent organization authority choice.

Do not buy identities for local fake-ship work. Do not require a planet per employee as a permanent product constraint. Later organizational browser-only authentication avoids that operational burden, while native Urbit identities remain useful for cross-home collaboration.

Keep app distribution authority separate from organizational data/administration when broad distribution begins. A test deployment from a pinned GitHub artifact is acceptable before a live release publisher exists. Never combine test/staging and production by copying an active real pier.

## Releases and operations

One source commit produces a versioned source desk/UI artifact, checksums, protocol/schema versions, state-migration tests and a provenance record. Promote the same artifact from fake tests to live canary rather than rebuilding uncontrolled variants. Install approved versions deliberately; record tested kernel/app compatibility. Do not assume arbitrary OTA changes are safe for the organization service.

Before canary, implement health checks, disk/loom/RSS monitoring, event backlog, request/rejection rate, import duration, backup age and restore alerts. Redact private data and credentials from logs. Back up both the pier and any external blob store consistently; a Git mirror omits private work metadata, policy and attachments.

Target for an early canary: a documented recovery point no worse than one day of accepted work and a demonstrated restore in a few hours. These are operator-selected initial goals, not guarantees; improve before real teams rely on the service. After every destructive migration test restore from the actual backup format.

Never power two live copies of one ship. For an old snapshot, use the supported runtime/network continuity procedure and fence the original host. When state is incompatible, prefer a tested forward fix or a controlled full recovery; do not claim downgrading the app binary rolls back its data safely.

## Dogfooding cutover

1. GitHub remains canonical while Stead canary imports read-only copies.
2. Controlled test repositories accept native pushes; compare IDs, permissions and exports with stock Git.
3. Stead Urbit becomes authoritative for its own repository only after backup/recovery, normal Git compatibility and access tests pass.
4. GitHub remains a one-way outward mirror and fallback distribution/read channel. Disable competing upstream writes or accept them only as explicit imported proposals.

Do not create bidirectional synchronization with two independently writable main branches. Do not treat a replica as a backup without deletion/retention protection.

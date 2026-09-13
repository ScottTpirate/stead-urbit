# Sources and verification limits

Research inspected September 12, 2026. These support facts about existing projects; the Stead topology and protocol are proposed designs, not vendor promises.

- Stead baseline: https://github.com/ScottTpirate/stead/commit/3d47f0172a41beebb31f5c3a7df133cc1d4b1ead
- Original directive: https://github.com/ScottTpirate/stead/blob/3d47f0172a41beebb31f5c3a7df133cc1d4b1ead/docs/architecture/MASTER_BUILD_DIRECTIVE.md
- Identity ranks/sponsorship: https://docs.urbit.org/urbit-id/what-is-urbit-id
- Moon identity independence: https://docs.urbit.org/user-manual/id/get-id
- Networking vs ownership keys: https://docs.urbit.org/urbit-os/kernel/arvo/cryptography
- Fake ships and same-machine local networking: https://docs.urbit.org/build-on-urbit/environment
- Piers, moving ships, no simultaneous copies: https://docs.urbit.org/user-manual/os/basics
- Arvo persistence and atomic event processing: https://docs.urbit.org/urbit-os/kernel/arvo
- Eyre HTTP server: https://docs.urbit.org/urbit-os/kernel/eyre
- Userspace/browser isolation work: https://urbit.org/blog/gall-2026
- Native Git candidate: https://github.com/yapishu/urgit
- Native Git architecture: https://github.com/yapishu/urgit/blob/master/specs/architecture.md
- Native Git conformance claims and limits: https://github.com/yapishu/urgit/blob/master/specs/roadmap.md
- GitHub CLI creation command: https://cli.github.com/manual/gh_repo_create
- AWS prices: https://aws.amazon.com/lightsail/pricing/
- Hetzner cost-optimized specifications/availability: https://www.hetzner.com/cloud/cost-optimized/
- Hetzner current-price adjustment (June 15; updated July 8, 2026): https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/

The GitHub connection available during preparation exposed read operations, not repository creation/push. No remote repository or cloud host was created. Native runtime binaries were not executed. The bootstrap is supplied for execution on a networked, authenticated local machine. Inspect TEST_RESULTS.md for the exact local tests performed.

Some Urbit documentation contains historical notes; pin and exercise the runtime rather than assuming every described capability is current. Do not treat Urgit's maintainer-reported tests as independent validation. Urgit licensing was unresolved in the prior inspection; do not copy source before resolving it. Prices exclude stated extras and depend on current stock/region/checkout.

# Security status and reporting

No stable release or sensitive-data deployment approval is claimed. Until the relevant gates pass, use public/synthetic data and disposable development identities. This document is not a certification or an assurance that upstream application isolation is complete.

Do not post live vulnerabilities, credentials, private piers, +code, cookies, customer content or exploit-ready production details in public issues. If GitHub's private vulnerability reporting is enabled and verified for this repository, use it. Otherwise request a private reporting channel from the repository owner without including sensitive details. No monitored security email or response SLA has yet been verified here.

URB-270 must enable and test a private intake route and identify accountable maintainers before public ecosystem release. URB-210 owns the threat model; owning feature tasks execute the relevant negative tests. A reported vulnerability requires reproduction on a disposable environment, impact assessment, coordinated remediation and a scoped advisory when appropriate.

Authority ships run only reviewed trusted applications until isolation is demonstrated. Restrict admin sockets, separate untrusted runners, scope delegated keys and reauthorize all data routes. Upgrades and restore require state/version checks and single-writer fencing. Never start two live copies of one ship to test recovery.

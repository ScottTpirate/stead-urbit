# Attended named-release observation

This tool observes a human using a separately admitted configured-team Home and
Identity. It never starts a native backend, creates an identity, renews access or
installs a tunnel. It does not qualify the historical four-fake M2 profile or
browser-only onboarding. Its report names the configured source and separates
manual Home signout from automatic cleanup.

The operator must first verify the named release, current member binding and
write access to a synthetic project. The participant must be distinct from the
operator and use invented information. A member's Home session retains all its
actual native grants: the browser's selected-project/new-object fence is **not**
a smaller native grant. Use this tool only where the owner authorized that member
session. A client fence cannot make an otherwise inappropriate account safe.

Prepare a private mode-0600 configuration accepted by `namedObserverConfig.mjs`:

- `protocol`: `stead.named-human-observer/1`; `source`: the verified 40-character
  source commit; `admission_observed_at_unix`: the successful readback time.
- `origins.home` and `origins.identity`: distinct exact HTTPS origins;
  `forward_ports.home` and `forward_ports.identity`: already admitted local
  loopback forwards. This tool does not create connectivity.
- `pins.home` and `pins.identity`: verified base64 SHA-256 certificate public-key
  pins. Do not substitute disabled certificate checking.
- `person`: current `principal_id`, `binding_id`, `binding_revision`,
  `identity_ship`, `authentication` and `authentication_strength` from admission.
- `project`: its exact `id` and `title`; `synthetic_project_confirmed`: `true`.

A separate private mode-0600 JSON array names the reviewed code-provider
executable and arguments. It must emit only the authorized Identity code to
stdout, keep secrets out of stderr, and have no unrelated effects. Never put the
code itself in that JSON, command arguments, a file, chat or a log. The launcher
connects its stdout directly to the hidden Identity browser through a private
pipe. The public source supplies no account, code provider or private controls.

Run `named_observer.py` with `--config`, `--code-command`, the independently
verified public `--ca` certificate and a fresh `--output` directory. Before any
code is requested, the two loopback TLS peers must match that CA, their hostnames
and their exact public-key pins. It needs the repository's pinned Node and Playwright dependencies,
system Chromium and the configured user's existing Wayland display. This is a
lightweight local browser with a remote backend. It uses the existing browser
owner's whole-cgroup cleanup, parent-death pipe, 25% CPU limit and temperature
checks. The dedicated owner changes only the original 600-second default/maximum
to 900 seconds, covering preparation, ten minutes of observation and cleanup.

The participant sees an explicit Start button; readiness expires after three
minutes without Start. They sign in, request the exact operator-prepared approval,
create/edit/reopen Work and a Doc in a new private collection, use Search and
Activity, sign out and give feedback. The tool never completes those tasks. The
hidden Identity session approves only the exact comparison and Home origin upon
the human's explicit action, then logs out. The participant never receives its
owner cookie. Both private profiles are removed only after the owner confirms
that the browser cgroup is empty.

Private evidence contains receipt/readback identifiers, request and content hashes,
bounded feedback, timestamps and cleanup results. It does not record document
contents, keystrokes or screenshots. Feedback checkboxes alone never prove a
successful task. Review privacy and actual receipt correlations before publishing
any output. The focused CI validates synthetic boundaries/configuration and source
syntax only; it does not claim a human trial, real credentials or native acceptance.

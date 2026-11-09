"""Print the supported local commands; no environment mutation or native start."""

print('''Stead Urbit local development (Linux, synthetic fake ships)

  make setup       Fetch and verify the pinned toolchain (first use)
  make doctor      Verify toolchain and actual sandbox isolation
  make preflight   Read current temperature admission; start no processes
  make check       Run host/static/mocked checks; no native runtime
  make frontend-check  Check TypeScript and client tests with bounded CPU
  make frontend-build  Bundle frontend assets without starting ships
  make dev         Start, wait for readiness, compile native core and run probes
  make status      Show stopped, booting, ready or unavailable owner state
  make core-check  Recompile core and run pure probes on a fresh fake fixture
  make team-dev    Compile and check the configured four-ship Work/Docs fixture
  make team-check  Repeat configured checks in the matching guarded fixture
  make migration-dev  Run only the trusted CI migration probe, then stop
  make ci-controls-dev  Reproduce trusted CI negative controls on one fake, then stop
  make sdk-dev SDK_ARCHIVE=<archive>  Check a separately packaged native consumer
  make test        Run the original four-ship native smoke suite
  make core-test   Execute the full native corpus; independent qualification follows
  make delivery-check  Check native offline-home timeouts and sender recovery
  make capacity-check  Diagnose all native capacity/migration recipes (not phase acceptance)
  make gall-schedule  Run the pinned Gall reordered-leave qualification lane
  make skill-prequalify  Validate frozen workflow references before evaluation
  make stop        Gracefully stop the owned fake ships and guard
  make review      Create or resume the separate manual review; never reseed it
  make review-status  Read manual review readiness and the last pause reason
  make review-open    Open a persistent private review window after readiness
  make review-login   Write private local sign-in instructions (no code in logs)
  make review-stop    Stop review ships and relay; leave its browser open
  REVIEW_SESSION=<id> make review-reset  Archive a stopped review, preserving data

After Hoon edits: make core-check. After harness Python edits: make stop; make dev.
Native checks replace disposable fake data, never Git/source. Build is not phase
acceptance. The guard requires at most 75 C to start and stops at 90 C.
The browser alpha uses a disposable local Firefox profile and native TLS.
Run python3 web/app/browser-check.py after team-dev for automated browser checks.
The human trial and Phase 2 qualification remain separate acceptance gates.
Manual review uses .piers/review; its browser stays open after tests or native
shutdown. Native thermal limits and the two-hour runtime bound still apply.
Use make review-resume after cooling; saved state is retained. Network loss may
retain in-tab edits, but expired/revoked/changed sessions clear private content.
Review never renews adopted grants. Its credentials and sample data are local.
See docs/urbit/DEV_FLOW.md for frontend packaging, SDK and hosted CI instructions.
''')

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
  make test        Run the original four-ship native smoke suite
  make core-test   Execute the full native corpus; independent qualification follows
  make delivery-check  Check native offline-home timeouts and sender recovery
  make capacity-check  Diagnose all native capacity/migration recipes (not phase acceptance)
  make gall-schedule  Run the pinned Gall reordered-leave qualification lane
  make skill-prequalify  Validate frozen workflow references before evaluation
  make stop        Gracefully stop the owned fake ships and guard

After Hoon edits: make core-check. After harness Python edits: make stop; make dev.
Native checks replace disposable fake data, never Git/source. Build is not phase
acceptance. The guard requires at most 75 C to start and stops at 90 C.
The browser alpha uses a disposable local Firefox profile and native TLS.
Run python3 web/app/browser-check.py after team-dev for automated browser checks.
The human trial and Phase 2 qualification remain separate acceptance gates.
See docs/urbit/DEV_FLOW.md for frontend packaging, SDK and hosted CI instructions.
''')

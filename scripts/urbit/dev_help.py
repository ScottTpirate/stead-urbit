"""Print the supported local commands; no environment mutation or native start."""

print('''Stead Urbit local development (Linux, synthetic fake ships)

  make setup       Fetch and verify the pinned toolchain (first use)
  make doctor      Verify toolchain and actual sandbox isolation
  make preflight   Read current temperature admission; start no processes
  make check       Run host/static/mocked checks; no native runtime
  make dev         Start, wait for readiness, compile native core and run probes
  make status      Show stopped, booting, ready or unavailable owner state
  make core-check  Recompile core and run pure probes on a fresh fake fixture
  make test        Run the original four-ship native smoke suite
  make core-test   Execute the full native corpus; independent qualification follows
  make gall-schedule  Run the pinned Gall reordered-leave qualification lane
  make skill-prequalify  Validate frozen workflow references before evaluation
  make stop        Gracefully stop the owned fake ships and guard

After Hoon edits: make core-check. After harness Python edits: make stop; make dev.
Native checks replace disposable fake data, never Git/source. Build is not phase
acceptance. The guard requires at most 75 C to start and stops at 90 C.
Browser UI is not available yet. See docs/urbit/RUNBOOK.md for evidence and scope.
''')

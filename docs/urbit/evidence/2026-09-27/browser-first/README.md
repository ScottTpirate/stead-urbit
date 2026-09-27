# First configured native browser journey

This is real local development evidence, not Phase 2 closure. The exact input
hashes remain in the original reports. These executions preceded the integration
commit; they are labeled as worktree development runs.

`make team-dev` passed 618 assertions in 337.109 seconds, including all 44 named
pure native unit arms and the deliberately failing control, configured Gall
allow/deny cases, four native TLS listeners, and four cold restarts.
`PYTHONDONTWRITEBYTECODE=1 python3 web/app/browser-check.py` then passed seven
checks through actual Firefox and native HTTPS: two individually approved
sessions, reader restrictions, attributed accepted mutation, second-person read,
cookie/owner separation, and logout. TLS CA/hostname verification stayed enabled;
wrong-CA and wrong-hostname controls failed. The process report proves the browser
cgroup emptied before deletion of the disposable trust profile. The native guard
subsequently completed with exit zero. No private browser profile, fake owner
credential, TLS key or live pier is included here.

The host suite initially found an observation race in the authored worker-start
failure control: frontend EOF occurred before the same locked handler removed
the backend socket. The test now acquires the existing bridge lock to observe
completed cleanup. The implementation and its resource limits did not change.
A second run found `/proc` returning ESRCH while the authored nft child vanished; the test-only death predicate now treats that as disappearance, matching the existing launcher control. Both failed runs are retained. The final repeated host run passed all 531 tests in 27.315 seconds. Separately, TypeScript checking and 16 host frontend/build controls passed, as did four real systemd browser-child cleanup controls (normal completion, timeout, parent death, clean environment).

All still-open acceptance items are in `docs/urbit/PHASE2_ACCEPTANCE.md`. In
particular this first browser journey does not qualify document publication,
subscriptions, SDK3, CI, onboarding, or a production deployment.

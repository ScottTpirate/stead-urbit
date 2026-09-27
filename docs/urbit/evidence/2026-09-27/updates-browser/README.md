# Scoped updates and browser recovery

Source `61b275186a22cd17984d5b1cbd86d9678b8c0c93` passed the configured
native lane: 707 assertions in 555.482 seconds, including 70 pure native arms,
the deliberately failing arm, all four native TLS listeners and cold restarts.
The exact source/input identities are retained in the reports. The guard
completed with exit zero after the real-browser run and explicit fixture stop.

Firefox 155 with Node 24.21.0 passed 23 browser checks against that native home.
They cover personal approvals, attributed Work changes and live updates,
private/shared Markdown and Git identities, selected-page publication,
private canary exclusion, Work/Docs relations, stale-save comparison/rebase,
lost-response receipt recovery, offline uncertainty with explicit retry,
content-free support export, keyboard project/Work creation, small/large
layouts, grant revocation, logout and account change. The keyboard suite uses
physical Tab/Shift+Tab and requires actual focus before typing or Enter.

The browser retained TLS verification, rejected wrong CA/hostname, and used an
owned private trust profile. The browser scope was observed empty before that
profile was deleted. Native and browser processes used CPU 19, respectively
50% and 25% per 10 ms. Thermal admission remained 75°C and termination 90°C.
Observed confirmed mutations took 2.862–3.926 seconds on this throttled local
workstation. The Markdown preview fetched its separate 1,032-byte module.
These are observed local results, not service-level promises.

Separately, the host suite ran 534 tests with one skip and passed. The rendered
mock-Home suite passed 12 cases. Its two-page keyboard case did not prove
recovery from a confirmed loss of document focus. The earlier failed native
browser attempt remains included: its driver incorrectly assumed forward Tab
would wrap through page controls. The corrected driver chooses Tab or Shift+Tab
from the target's relative position. Product code did not change for that fix.
Expected offline request failure and lifecycle cancellation remain visible in
the successful browser report.

This is an implemented, reviewed increment, not Phase 2 closure. Configuring
distinct time zones is not proof of actual localized date rendering. Browser
session expiry and further raw-endpoint denial controls, SDK3 independent
consumer execution, disposable native CI and independent onboarding remain
separate obligations.

`index.json` binds artifacts to the retained originals and describes their
transformations. The portable native report omits owner configuration,
bootstrap and Dojo control transcripts; the full original remains private for
independent review. It is not a complete execution replay. No private trust
profile, TLS key, fake owner credential or live pier is distributed here.

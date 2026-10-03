# Phase 2 onboarding follow-up

Status on October 2, 2026 (US Eastern): **incomplete**. Fresh native,
automated Firefox and stock-Git checks passed at integrated source
`66f051e3600ac6685d0017cb524fdd0becb7a8bf`. The independent human trial
expired without qualifying task observations or participant feedback.
[URB-260 / #29](https://github.com/ScottTpirate/stead-urbit/issues/29) and
M2 remain open. The [evidence index](evidence/2026-10-02/onboarding-66f051e/index.json)
binds the private reports to exact byte counts and hashes.

## Fresh execution and independent review

| Component | Observed result | Scope |
| --- | --- | --- |
| Configured native | 760 passing observations, 747 distinct names; 1,095.685 seconds | Exactly 71 positive unit arms plus one deliberate failure; six transcripts, 110 decoded exchanges and 25 accepted receipts independently reviewed. All 77 installed files on each of four ships match; four cold restarts passed. |
| Automated Firefox | All 34 expected cases passed; 492 captured responses | Complete capture, matching source/prerequisites, wrong-CA and wrong-hostname controls, and clean browser shutdown. |
| Stock Git | All 43 recorded commands exited zero | Three native histories, 18 independently rehashed loose-object copies, exact receipt OIDs and Markdown, destination-only publication ancestry, private-history exclusion and strict fsck. |
| Human trial | Deadline incomplete after 540,044 ms | Zero accepted saves, reads, Work/Docs or collection readbacks; no feedback or coaching attestation; no signout. The cause of absent activity is unknown. |
| Whole native lifetime | Completed with exit zero in 2,372.963 seconds | No cleanup errors; native and both browser cgroups are absent. The stopped fixture and evidence are preserved under the exclusive lifetime lock. |

The browser retained five request failures. Two boundary-channel cancellations
and the deliberate offline command have test context; the query and updates
aborts lack firm initiating-stage attribution. The automated pass retains that
limitation. Counts overlap across evidence classes and are not summed.

The human trial opened at 23:53:27.422 UTC on October 2 and had a nine-minute
window, ending shortly after 00:02:27 UTC on October 3 (8:02 PM Eastern on
October 2). A desktop notification was sent, and read-only window inspection
confirmed the owned trial window was mapped and focused. Its launcher captured
evidence and cleaned up successfully. Neither that outcome nor window visibility
establishes human task completion. The disposable profile and personal fixture
were removed after verified process cleanup.

## Earlier failed attempt

The first native attempt stopped at the thermal-sample freshness check. Its
recorded maximum was 79°C, and one sample-completion interval was 3.133866 seconds.
The freshness limit remained three seconds. The original event was
`Stale, future or reversed thermal sample`. The retained timing does not
distinguish scheduling delay from publication or file-I/O delay, and a successful
retry does not establish that the intermittent cause is fixed.

That attempt remains failed. Its owned ship eventually exited cleanly, about
125 seconds after the original stop event; this is not a 25-second shutdown-bound
pass. Its stopped state and guard were preserved before restoring verified clean
seeds for the successful retry. An intervening startup refusal on the unclean
marker launched no native run. No guard limit or application source was changed.

## Retained qualification and next trial

Executable native/browser/SDK inputs and packaged assets remain equivalent to
the reviewed `d9115056` candidate. The existing SDK, hosted CI and natural-expiry
results retain their [September 29 qualification boundaries](PHASE2_QUALIFICATION_20260929.md);
they were checked for applicability and were not executed again. This follow-up
adds no production, live-network, import-load or unconstrained performance claim.

The temporary widget change was restored to its exact original bytes and checked
independently. No fan settings were changed during this follow-up. The disposable
test fixture is stopped.

The next gate is an attended, uncoached Work/Docs trial with accepted saves,
correlated readbacks, Search/Activity, signout and participant feedback. Agree
on a test window before preparing a fresh fixture, then confirm the participant
is present at the Linux desktop immediately before launching the nine-minute
trial. Availability stated earlier in preparation is insufficient evidence of
current readiness. Preserve the actual outcome and obtain independent review
before closing #29, M2 or Phase 2.

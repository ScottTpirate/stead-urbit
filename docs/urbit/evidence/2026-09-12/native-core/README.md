# Native core evidence

Public/synthetic data only. Raw timestamps use UTC; these runs began September
12 US/Eastern. The runtime lock and minimum contract freeze are unchanged from
source `96971540cf70c557f01a5ef10db832ddee2e0130`. Final source/evidence binding is
recorded separately after the source commit exists.

`root-pass.summary.json` is the readable index for the root's actual
`make core-test` run. `root-pass.json.gz` contains its complete, unabridged JSON
report (decompress with ordinary gzip). Raw and compressed SHA-256 values are in
the summary. Commands, exact native results, lifecycle events, current-authority
snapshots, QA assertions, export objects and source hashes are retained. Large
malformed request bytes are reconstructed from the hashed corpus recipe; their
input hashes and sizes are recorded rather than duplicating giant Hoon literals.

The root report's bounded execution status is pass: 413 direct checks, 129
expected business outcomes, 49 native codec vectors, 14 context-invalidity cases,
state-version rejection/roundtrip, concurrency and 8 document exports. The
independent QA subreport remains **incomplete**, with 115 fully covered cases and
14 partially covered cases: 2,542 assertions passed and 25 are explicitly skipped.
Those skips cover broader subscription/subscriber instrumentation, metadata
confidentiality, external-effect observation and an internal-order property that
source review addresses. They are not converted to native passes. See the exact
skip list in the summary and NATIVE_CORE_REVIEW.md.

The following earlier reports are preserved as gzip plus readable summaries:

- Initial build/import, native path-carrier and remote result-mark failures.
- A two-outcome project/outsider smoke pass; this has weaker source attribution
  than the final before/after/loaded-code and actual Clay-byte checks.
- A real snapshot-helper compile failure from the first expanded runner.
- A full business-journey run that failed at the large-frame host encoder boundary.

`vere-eval-boundary.json` independently reproduces Vere 4.6's truncated pipe output
for the exact 65,537-byte malformed corpus input. The old pipe returned 65,536 of
65,590 declared frame bytes despite exit 0; file-backed stdout returned the full
frame. The native suite separately proves the home rejects that oversized input.

`counter-regression.json` is the preserved URB-020 suite on the final harness:
12 native commands (7 expected ACKs, 5 specific failures) plus home restart in
23.628 seconds. `host-checks.json` records 131 host/mocked/temporary-Git tests and
three validator command groups; these are not Hoon compilation evidence.

`synthetic-documents.bundle` is an actual portable, selected document-container
export. `bundle-recovery.json` records its independent bare clone, full strict
fsck, history and exact recovery of the two current synthetic Markdown files.
It is not an organization-wide backup or an export of work/policy history.

The adjacent `git-objects/` evidence records the original pure Hoon constructors'
51 native/stock-Git vector checks. That source contains no copied Urgit code.
Urgit's separate candidate audit and open hardened replay gate remain in
URGIT_AUDIT.md.

No browser, live Urbit identity, cloud, CI workflow, production security,
representative performance or backup qualification was executed by this corpus.
Warm restart timings include test control overhead and real expiry waits; they
are not product latency benchmarks. Owner-local snapshots and fixture controls
are development administration only.

Independent QA's complete replay is `independent-pass.json.gz`, indexed by
`independent-pass.summary.json`: the same source/inputs, same 413 direct checks,
129 outcomes and explicit 25 skips, in 390.834 seconds. `qa-execution.json` and
`qa-output.txt` record independent invocation and observations. Five-second CPU
samples include 96°C at 03:35:53.696675Z. The main harness has no thermal stop:
this passing functional replay does not qualify thermal bounds or sustained load.
No further native runs were made after observing that result.

Exact tested implementation source: `f52293f7cd6970ded20e73b097beffb7418e4bbd`.
[source-binding.json](source-binding.json) verifies Git blobs against both complete
run manifests. It is a records-only descendant, not a new runtime execution or approval.

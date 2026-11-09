# Guarded local Code canary

This harness measures the configured, disposable four-ship fixture while stock
Git uses its native HTTPS route. The fixtures, browser sessions and TLS bridge
are inputs from the owned local controller. The harness requires an active
guard and checks the admitted native source, Python helpers, Git executable,
HTTPS helper, CA and workload against their recorded digests. It creates one
separate synthetic Code repository in the disposable copy.

## Frozen workload

- Three rounds of stock atomic push, fetch and fresh bare clone. Each push adds
  one fast-forward commit and lightweight tag. Every fetch and clone must see the
  exact expected OID, and each clone must pass strict Git verification.
- Eighteen Work reads and eighteen shared Docs reads in each condition. The
  baseline is collected before Git traffic. Each loaded transfer starts two
  pairs of reads, with alternating first query type. Every transfer must overlap
  at least one query, and each query type must overlap a transfer at least once.
- Measure client time from before the TLS query until after correlated response
  and content verification. The transfer interval covers the stock Git network
  command, excluding local fixture preparation and post-command verification.
  Percentiles use nearest rank, so p95 and p99 are the maximum with 18 samples.
- Confirm the same Work and shared Docs content through a separate reader before
  and after the workload. Confirm that the maintainer can read a selected
  private document and that the reader receives the exact denial both times.
  Anonymous Git must be denied. Both temporary Git credentials are retired.
- Restore an offline Code archive from the final authenticated bare clone. This
  check is outside the latency samples.
- The client work deadline is 105 seconds. This workload establishes a
  baseline for the selected fixture and has no prequalified latency target.

The CLI accepts two private existing member-session files, the active guard's
control directory and run ID, its local CA, and the source project plus
shared/private Work and Docs scope. See `python3 -B
scripts/urbit/code_local_canary.py --help` for argument names. The success report
records counts, exact Git outcome OIDs, observed overlap, latency percentiles
and input hashes. The failure report uses a fixed reason code. The CLI does not
start or stop native processes and never publishes to a remote host.

Host tests exercise the counting, nearest-rank and overlapping/nonoverlapping
controls. They do not produce native latency evidence. A successful CLI run
would measure this small local profile. Multi-host identity and routing,
resource growth under sustained load, and operational rollback have separate
evidence requirements. [Code portability](PORTABLE_CODE.md)

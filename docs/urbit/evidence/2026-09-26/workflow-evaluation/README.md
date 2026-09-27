This is the preserved **incomplete v1 URB-170 evaluation**, executed at
`8334a75cad4c2b063147e7e3352cdf76da0d5893`. Both one-shot private invocations
completed cleanly and their raw adapters reported 5/6 tasks passed. Independent
review found T05 invalid for incomplete required mutation coverage. URB-170
remains open; this is not a qualified six-task evaluation or Phase0/1 acceptance.

| Condition | T01 | T02 | T03 | T04 | T05 qualification | T06 |
|---|---|---|---|---|---|---|
| baseline | pass | pass | pass | pass | invalid; mutation failure observed | pass |
| local_skill_assisted | pass | pass | pass | pass | invalid; mutation failure observed | pass |

Both submitted T05 suites compiled and passed against the correct implementation
(11 arms baseline, 13 assisted), and killed the claimed-author mutant. The
outsider-granted mutant survived, triggering the evaluator's runtime assertion.
The adapter stopped that task before everyone-granted and claim-must-match.
Those two subjects are explicitly **not run**. Raw reports are unchanged; the
derived qualification status does not relabel the mutation failure as a pass.
The frozen README requires every mutant and invalidates missing-case tasks.
The repair requires a versioned evaluator and fresh contexts, not retries or
repairs of these candidates.

Both contexts used the observed model alias `gpt-6-astra`, effort `max`, and fresh
history. The immutable backend revision is unknown. The same 22 initial files
were supplied to each, with four frozen skill files additionally supplied to
the assisted condition. The initial T02 compiler diagnostic was byte-identical.
First work proceeded T01–T06; baseline later revisited T01/T02 for public
feedback. Baseline had eight public reservations: one infrastructure refusal,
one failed T03 build with limited diagnostics, and six passes. Assisted had six
reservations and six passes. No private feedback or repairs followed submission.

Charged active time was 717.089037753 seconds baseline and 651.180362496 seconds
assisted, below the equal 1800 second budget. Baseline includes 23.683894211 seconds
for an agent-capacity delivery failure which never reached the participant.
The charge was conservatively preserved. These timings include parent
observation/delivery overhead and do not measure cognitive speed or establish
a skill effect. The observed task-pass difference is zero in one local pair.

The independent reviewer reconciled 53 baseline and 58 assisted wrapper calls,
19 deliveries, 16 exposed model-setting records, timing and candidate bytes.
The full tool catalog remained exposed; observed permitted-wrapper use is not
complete tool isolation. Incoming message bodies are encrypted. The plaintext
ledger records what the integrator actually sent/received; delivery metadata
is verifiable, but plaintext-to-ciphertext equivalence was not decrypted.
The corrected filtered traces and the superseded export missing visible
messages are both retained. Raw rollouts, hidden reasoning and system/developer
content are excluded.

[result.json](result.json) follows the frozen result schema with explicit nulls
and incomplete/invalid qualification. [index.json](index.json) lists exact
output hashes and all public/private runs. [members.json](members.json) maps
every exact original path to a hash-bound member of [evidence.tar.gz](evidence.tar.gz).
Private reports and outer guards are directly accessible under `raw/private/`;
public native reports use lossless `.json.gz` copies under `raw/public/`, with
both compressed and decoded hashes. Prequalification receipts are under
`raw/prequalification/`; the earlier full prequal11 portable index is linked.
The [received review disposition](independent-review-disposition.json) explicitly
identifies the reviewer and the separate recorder.

The archive includes complete selected inputs, final candidates, immutable
public snapshots, wrapper call logs, timing, public attempts (including the
no-launch refusal), one-shot score records, generated native probes, completed
outer guard events/source contexts, exact scored source/package bytes, support
helpers and preserved versions. It includes no live or seed pier. Extract only
into a separate empty directory; never overwrite a live workspace. Archive
headers are deterministic and carry no source-owner metadata. Every member was
rehashed after packing, and every selected original was rechecked unchanged.
This packaging performed no native or host-test rerun.

Native evidence is Hoon unit evaluation and pinned Gall with explicit synthetic
clock/routing. It does not prove live Ames routing, browser behavior, production
authorization or deployment. T03's omitted type/tang bodies are native size/hash
measurements. Installed Clay evidence is a file projection and typed readbacks;
no complete Clay tree hash is invented. Independent review clears the recorded
trace/timing facts within these limits and requires URB-170 to remain open.

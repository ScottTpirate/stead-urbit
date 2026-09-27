# Independent implementation review

Integration/architecture owner: the root implementation agent, acting within the
user's requested increment. Shared identities, schemas, native state and policy
interfaces are frozen together before feature work. Repository owner retains
implementation merge, release, spending, live-key and deployment approval.

Independent Hoon reviewer: `/root/hoon_review`. Reviewed the counter's typed state,
trusted `src.bowl`, ACK/NACK handling, save/load consistency, source/pin identities
and 12-command native evidence. It identified the Lens asynchronous subscription
failure and verified the replacement pinned conn/Khan codec/terminal format. It
also independently checked all six canonical JSON fixtures using pinned Node,
without the host reference encoder. Current scope: no blocking counter finding;
the minimum Work/Docs contract supplement also passed separate Hoon and QA review before the versioned freeze. QA identified and resolved grant-ID overwrite ambiguity: IDs are create-only, including retained revoked tombstones.

Independent QA owner: `/root/qa_review`. Authored adversarial host fixture safety
regressions, reviewed the independent Urgit runner and performed its own actual
`make test` native run. On September 12 local time / September 13 UTC, that run
passed 12 commands (7 successes and 5 specific failures), plus clean home restart
and state persistence, in 20.953 seconds. See
[evidence](evidence/2026-09-12/native-smoke-independent-pass.json), SHA-256
`a711f2ff234ed78bc0b16ca90f7724537aaf88d91d3fab2e586daf3719826227`.
Pre/post temperature samples were 61/73 C; no in-run peak is claimed.

Git candidate implementer/evaluator: `/root/urgit_audit`. Its source/license and
ordinary-Git results are separately reviewed by QA; its own reports are not final
approval of its implementation. See URGIT_AUDIT.md for source and runner findings.

These are independent agent reviews, not independent human production approval.
The initial smoke establishes a synthetic counter, not Work/Docs authorization,
per-person sessions, a Git forge, saved-state upgrade or endpoint isolation. The
next native increment must have new source-bound execution evidence and review.

## Joint native state and authorization increment

For the subsequent slice, `/root` owns the home/core/codec/client and lifecycle
adapter. `/root/urgit_audit` authored the original pure Hoon Git constructors and
bounded export adapter; its 51 native/Git vectors and 17 host/Git export tests were
separately inspected/rerun as labeled. No Urgit source was copied.

`/root/qa_review` owns the independent 129-case acceptance corpus and assertion
executor. It found retry, grant-lifetime and metadata-scope concerns during design
and reviewed source/evidence without implementing the authority. It independently
reran all 17 export tests and the complete `make core-test`: 390.834 seconds,
exit 0, 413 direct checks, 2,542 passed assertions and 25 explicitly skipped wider
assertions. Source/lock/corpus bytes match the root's passing run. Its measured
96°C sample and absence of a main-harness thermal stop are retained in TEST_RESULTS;
functional execution is not load/thermal qualification.

`/root/hoon_review` independently reviewed exact Hoon bytes, corrected failure
controls, native result routing, final authorization order, journal chains and
object evidence. Its disposition and remaining gates are in
[NATIVE_CORE_REVIEW.md](NATIVE_CORE_REVIEW.md). The original counter also passed
again on the final harness. These distinct agent roles do not replace independent
human Hoon/security review or owner implementation merge/deployment approval.

# URB-170 six-task evaluation package — version 2

This version freezes unchanged participant inputs and repaired independent scoring rules.
It contains **no executed v2 evaluation and no skill-effectiveness claim**.
Version 1 remains preserved as an incomplete comparison: its scorer stopped at
a surviving T05 mutant and omitted two required subjects. Both version 2
conditions require fresh contexts and new answers; never retry the old candidates. New starters,
reference solutions, mutants and oracles require native prequalification before
participant launch. Historical compiled examples are identified separately in
`provenance.json`; their success does not qualify these new fixtures.

The independent test owner is `/root/independent_review`. The integrator owns
native execution, runtime integration and review of this package. This directory
adds no production agent, contract, toolchain choice or runtime command.

## Design

| Task | Candidate output | Required observed behavior |
|---|---|---|
| T01 typed gate | `lib/eval-add.hoon` | Optional bounded sum, including rejection boundaries. |
| T02 type repair | `lib/eval-maybe.hoon` | Repair a real compiler rejection while preserving the optional-result interface. |
| T03 save/load | `app/eval-counter.hoon` | Exact v1 save envelope, v0 conversion, v1 roundtrip, malformed/future rejection. |
| T04 authorization | `app/eval-access.hoon` | Native sender authorization for poke/watch, no claimed-author or owner bypass. |
| T05 missing tests | `tests/eval-coverage.hoon`, `coverage.json` | Identify missing identity coverage; native tests pass correct code and kill identity mutants. |
| T06 desk assembly | `desk/`, `assembly.json` | Exact pinned development desk bytes and actual clean native generator build/result. |

Use two new contexts, one per condition, with no fork of this conversation and no
access to each other's outputs. Use the same exact model/version, reasoning and
tool settings. Both receive the common brief, public task prompts, matching
starters and the two common historically compiled examples. Only the assisted
context receives the frozen local skills. Both have the same task order, active
work budget and maximum feedback submissions. Six tasks in one condition may
share that condition's context; they may not share the other condition's answers.

This is one paired six-task local qualification, not a statistically powered
benchmark or evidence that a skill improves other models/tasks. Equal outcomes,
regressions and unsuccessful attempts must be reported. Completion of the
comparison is separate from claiming a better pass rate.

The integrator copies only `public/`, `common/` and the selected condition's skill
texts into a fresh participant input directory. Do not hand participants this
README, `reviewer/`, result schema, full repository or retained answers. A path
convention is not access isolation: enforce the allowed-input boundary where
possible and record all exposed files/tools. If a baseline receives skill text,
an oracle or another condition's answer, label it contaminated and rerun in a
fresh context. Never hide mandatory safety rules to manufacture a baseline.

Participants do not start ships or contact conn.sock. They submit candidate
files and, at most three times per task, request the integrator's compile/public
example feedback. The same broker and public checks serve both conditions.
Private cases and mutation outcomes are scored only once after final submission;
they are not sent back for repair. Native wait/thermal refusal time is excluded
from active work but retained as infrastructure time. An infrastructure refusal
is incomplete, never an application or skill pass/fail.

## Before launching either context

1. Review and verify all `freeze.json` hashes, pinned inputs and provenance.
2. Through the existing guarded disposable harness, compile the common examples,
   all reference solutions, T05 correct implementation, every mutant and the
   unchanged T06 supplied source. Run each oracle against reference solutions.
   T02's starter must actually fail compilation before it is called a repair
   task. Its repaired reference must pass. A mutant compile error is not a
   killed behavioral mutant. Record the actual commands and results.
3. Verify T03 through actual native on-load/on-save execution; verify T04 through
   pinned native Gall dispatch with recorded sender, cards and final save state.
   A Python permission model or direct fabricated observer output cannot pass.
4. Run the deliberately false expectation in `reviewer/oracles.json` and require
   a semantic assertion failure. Verify empty/missing arms, compile failure,
   timeout and malformed evaluator output are nonpassing. Do not call a build
   message a successful test run.
5. Execute the frozen weak T05 continuation control against the correct subject
   and all four mutants. It must pass the correct subject, kill claimed-author,
   survive outsider-granted, and still execute and kill everyone-granted and
   claim-must-match. Retain every test-arm tang and all five native commands.
   This expected failed test suite is a control, separate from the six passing
   reference tasks. Its missing/incorrect result blocks both participant launches.
6. If a fixture/oracle needs repair, update the package and hash manifest before
   either participant starts. Once started, do not silently repair or reweight
   the corpus; invalidate/restart both conditions under a new package version.

These are required future actions, not an invented executable command. The
integrator must bind a real native adapter to the existing supervised harness.
No new raw-engine bypass, production identity, global skill installation,
network download or unguarded native process is authorized by this package.

## Native adapter contract

`reviewer/oracles.json` defines exact inputs and expected nouns/events. Each pure
case calls the compiled candidate arm at the specified input; compare actual
nouns, not formatted substrings. T03 invokes the actual candidate's Gall arms
with a typed native vase and compares the state returned by on-save after
loading. T04 dispatches through real pinned Gall and records actual ACK/NACK,
fact/kick cards and on-save state before/after. The adapter may use a bounded
native Gall scheduler with explicitly simulated routing/clock; label that
classification honestly rather than four-process network evidence.

T05 runs all discovered `test-` arms, preserves the two original arms, and
requires nonempty expected arm inventory. Run the identical submitted tests
against each separately compiled mutant. At least one assertion must fail for
each mutant while the correct implementation passes all arms. No extra test
arm may be skipped merely because it fails. Independently review that the added
tests exercise sender/claimed-author behavior rather than inspect source text.

Version 2 evaluates the correct subject and the four mutants in that frozen
order. A native typed envelope retains the complete ordered `[arm tang]` list,
subject label, role and derived pass predicate. A failed correct assertion or a
surviving mutant does not bail out or skip subsequent subjects; aggregate the
task outcome only after all five results exist. Missing, duplicated or reordered
subjects/arms, compiler bails, malformed output, source mismatch or an interrupted
run invalidate the task. A timeout or failed guard ends the run and starts
cleanup immediately. These are not killed mutants. Public feedback executes
only the correct subject and discloses no mutation or private-control results.

The transported jam retains the existing 262,144-byte cap, enforced natively
before decimal rendering. Its canonical host decoder additionally bounds noun
depth to 512, encoded nodes to 65,536 and expanded nodes to 1,048,576. Exceeding
a bound is invalid evidence, never a behavioral kill. Full tangs remain in the
retained native jam; pretty noun text is diagnostic and does not drive scoring.

T06 has no applications or frontend. It is a minimal development desk with a
pure library and generator, not an OTA/release qualification. Assemble from an
empty directory twice, reject symlinks/unlisted files, compare byte hashes and
then compile/invoke the actual generator from the assembled files on a verified
clean fixture. The existing general-purpose environment still provides the
pinned kernel; there are no extra library dependencies for T06.

Source and scoring authority are separate. The adapter checks expected file and
arm inventories, candidate hashes, loaded Clay bytes, loaded closure, toolchain,
oracle and evaluator hashes before/after scoring. A stale loaded candidate, a
hash mismatch, missing case or missing failure control invalidates that task.
Do not rewrite an oracle to accept a candidate's behavior.

## Reporting

Use `result.schema.json` for record shape. Preserve all attempts, candidate byte
hashes, native input/output, expected outcome, observer/save-state evidence,
elapsed active/infrastructure time and failure category. Record actual context
IDs and actual model/version/settings; unknown values stay unknown and limit
comparability. Record the skill contents and all other files each context saw.

Report each task and condition, counts out of six, compilation and runtime
outcomes separately, and actual difference without attributing causation from
one sample. Retain source-only review and host metadata validation as separate
evidence. The independent reviewer must inspect final artifacts before URB-170
closure. This package alone closes no issue or phase.

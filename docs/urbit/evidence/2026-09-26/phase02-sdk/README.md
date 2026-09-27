# First Phase 2 SDK package increment

The bounded offline package is accepted at source
`fcac1c081c0dd021eebe8b3cabe754a906ebe8c4`. It exports four pinned public Hoon
helpers/marks, the complete license/notices and SDK instructions. It is a
developer library fragment; URB-180 / issue #21 remains open.

`make check` passed its planning/ecosystem validators, both contract freezes and
**494 host/static/mocked tests**, including the 18 SDK tests. The full command
took 177.659 seconds under a transient 20% CPU quota, 10 ms period and CPU 19
affinity. The unittest suite took 175.890 seconds. Exact committed inputs and
HEAD remained unchanged before and after the run and subsequent CLI commands.
The separately invoked contract tests are not added to the suite count.

The real CLI build and verification both passed. The retained
[archive](final/stead-sdk-v2.tar) is 51,200 bytes, SHA-256
`cb8097fc2036b7720d8ba9ade3fbc219073f828dbe7835756080f58269216d45`.
The [artifact record](final/artifact.json) retains exact commands, output,
durations and digest. Verify the retained archive from the repository root:

```sh
python3 scripts/package_sdk.py verify --archive docs/urbit/evidence/2026-09-26/phase02-sdk/final/stead-sdk-v2.tar
```

The [independent review](reviews/final-fcac1c0.json) accepted this increment with
no remaining blockers. Its 23 actual host checks comprise the same 18 SDK tests
plus five independently authored controls; those overlapping tests are not
additional native evidence. The reviewer independently reproduced the same
archive bytes and checked the complete public surface, source pins and notices.

Review found and then verified corrections for two real defects: a parent path
swap could redirect file I/O, and a directory input could leak a descriptor on
rejection. The unchanged [first](reviews/initial-92e8ee6.json) and
[second](reviews/followup-ef17dbc.json) reviews and their associated passing but
superseded 490/493-test host runs are retained. Passing those earlier suites did
not resolve the independently demonstrated failures. The failed capture setup
record also remains: an absent optional cgroup file stopped that recorder before
`make check` started; its successor records absence and explicitly pins affinity.

The [index](index.json) maps 22 exact retained files and their hashes to their
original capture paths. The [host record](final/host.json), [raw log](final/host.log)
and [capture script](final/capture.py) preserve execution identities. Publication
adds documentation/evidence to that tested source; it does not relabel tests as
executed on a later documentation commit.

No Urbit ships or native consumer were executed for this increment. All native
source and qualification mounts remain identical to the accepted Phase 1 native
baseline `dd0e8c0`. The SDK archive does not qualify an independent consumer, full
API/session/version negotiation, an installable desk, a publisher signature or a
release channel. A failed write can leave a new file in the originally opened
directory, deliberately without deleting through a potentially replaced name.
The command reports failure; there is no atomic publication guarantee.

Next, build the independent native client from this published fragment, exercise
authorized creation/read and denied scope, then implement the remaining public
API conformance and individual sessions before the shared browser journey.

# Bounded scheduled-Gall reporting review

Independent reviewer: `/root/editor_tool_review`; author:
`/root/gall_schedule_review`; integrator: `/root`. Reviewed September 26, 2026.

Actual Gall05 output measured 1,376,721 bytes for the old poke motion list.
The retained failure is in
[native follow-up evidence](../evidence/2026-09-25/native-followup-attempts/index.json).
The revision changes only the final report of the two poke motion lists. The
opaque compiler-generated vase type becomes an explicitly invalid report marker,
with native hashes and sizes of the full list, poke and omitted type. Those
omitted bytes are not independently reconstructed by the host. The command
body, route, duct, order and ACK remain decoded evidence. Actual dispatched
tasks, captured/delivered leave nouns and result gifts are unchanged.

The reviewer found no source blocker. The host retains its 16 KiB jam,
4,096-node, depth-96 and 128 KiB report limits. Native-only opaque measurement
has a separate 2 MiB limit; it does not enlarge the host decoder. Closed fields,
marker references, body/receipt checks and old/fresh type consistency are tested.
Native Hoon compilation and execution of this revision remain pending.

Reviewed SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `tests/urbit/native_gall_schedule/desk/lib/stead-gall-schedule.hoon` | `dde770803e72bb586d137df2f865d3ef142ea85bb9b0b5f54ffabf1a26bce474` |
| `scripts/urbit/gall_schedule_proof.py` | `fe6564900c0b3b6ae5c0a75ea18788807024053f433d0f5fcb0b17f04566904b` |
| `tests/urbit/test_gall_schedule_proof.py` | `e5f49ab05707209098d1127e6343c4027c29de6d7706cd05d6b3eadf14aeeb3a` |
| `tests/urbit/native_gall_schedule/README.md` | `7a946cc14252cf5fb8108a4f80525274f5a63419644e2e0689837953840a9b95` |

The reviewer independently executed
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests/urbit python3 -m unittest -v test_gall_schedule_proof`:
19 host tests passed in 0.805 seconds, exit 0. Scoped `git diff --check` passed.
This is source/host review, not native qualification or owner merge approval.

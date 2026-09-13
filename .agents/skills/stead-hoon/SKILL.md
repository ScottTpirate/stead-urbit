---
name: stead-hoon
description: Develop and debug Hoon in stead-urbit with pinned native compilation. Use for Hoon code or type errors, not cloud administration.
---

# stead-hoon

Read root AGENTS.md and the current URB issue. Confirm the active branch, owned files and pinned toolchain; preserve uncommitted work. Read only the relevant source/types and official documentation, not the whole archived repository.

Choose a small pure typed function first where possible. Use project naming and the standard app/lib/sur/mar/gen/ted/tests desk layout. Keep LF Hoon source; do not normalize Git/Markdown fixtures. Prefer explicit molds and bounded collections. Reuse only compiler-verified examples at the pinned source version; unfamiliar runes require a primary reference rather than plausible syntax.

Compile on the disposable fake ship using the commands established by URB-010/020. Reduce a type failure to a minimal reproducer, inspect the subject/type and fix one assumption at a time. Add actual unit tests before integrating stateful behavior. Do not invent an executable command or claim compilation when the runtime is absent.

For state/security use stead-gall-security; for verification use stead-native-tests. Output changed behavior, source/toolchain identity, actual test results, failure cases and unexecuted checks. Optional language-server diagnostics help editing but never replace native compilation. No live +code, production pier or privileged socket.

References: https://docs.urbit.org/hoon/why-hoon ; https://docs.urbit.org/build-on-urbit/environment ; https://docs.urbit.org/build-on-urbit/userspace/unit-tests .

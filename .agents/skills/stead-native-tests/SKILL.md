---
name: stead-native-tests
description: Test native Hoon, multi-ship behavior and ordinary Git conformance in stead-urbit. Use for evidence and regression work, not to certify unexecuted features.
---

# stead-native-tests

Read AGENTS.md, the issue acceptance criteria and the pinned runtime/corpus manifest. Separate static metadata, pure model tests, native compiler/runtime, browser, live-network and independent review results.

Run expected Hoon test arms through the verified native harness. Official -test discovers test- arms and interprets an empty tang as success. Confirm expected test count/names; zero or missing tests, compiler errors, bad output and timeouts fail. Include a deliberately failing control to demonstrate failure propagation. A build message or process exit alone is insufficient.

For each protected operation test contributor, reader and outsider with final state assertions; add stale revision, duplicate request, revoked credential, interrupted effect, restart and supported migration. Four fake ships test local application behavior, not live-network routing.

For Git, use stock clients, exact original OIDs, fsck, advertised reachability, refs, corrupt/delta/oversized packs and concurrent/revoked writes. Separate general Git support from Clay projection limits. Measure UI behavior under import, not just startup.

Never execute arbitrary PR code with live keys or on the authority host. Publish bounded redacted evidence: exact source/toolchain/input identity, command, expected assertions, actual outputs/status, failures and remaining checks. A reviewer must verify semantics. Metadata validation is not Hoon qualification.

References: https://docs.urbit.org/build-on-urbit/userspace/unit-tests ; https://docs.urbit.org/build-on-urbit/environment ; docs/urbit/STEAD_CARRYOVER.md.

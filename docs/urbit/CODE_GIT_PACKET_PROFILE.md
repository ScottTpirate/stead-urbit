# Code Git packet framing

This is an original, pure Phase 3 foundation for URB-080. It installs no route,
opens no repository and grants no access. It does not complete the native Git
milestone or the outstanding human Work/Docs acceptance gate.

`native/core/desk/lib/stead-code-git-pkt.hoon` preserves binary bytes using
`octets = [length=@ud data=@]`, the same explicit little-endian representation
as the existing document Git library. Trailing zero bytes remain significant.
Bits outside the declared width are invalid. No payload newline, encoding or
author text is normalized.

| Pure interface | Result |
| --- | --- |
| `encode [kind body]` | Optional encoded octets; absent for an invalid width, oversized payload or payload attached to a control packet. |
| `decode [buffer offset]` | One `%ready` packet with kind, exact payload and next offset; `%need` with total bytes needed **from that offset**; or `%invalid` with a bounded reason. |

Kinds are `%data`, `%flush`, `%delim` and `%response-end`. Empty data (`0004`)
remains different from flush (`0000`). The encoder emits lower-case length
digits. The decoder also accepts upper-case hex digits for compatibility.
It preserves the optional trailing LF; a later command-text parser decides
how to interpret that LF. Data frames allow 65,516 payload bytes, and the whole
caller-owned decode buffer is capped at 1 MiB. A caller must compact consumed
prefixes before appending more input. Parsing one header takes four bounded
iterations and returns at most one bounded payload.

The framing rules and protocol-v2 control markers follow the primary
[common Git protocol](https://git-scm.com/docs/gitprotocol-common) and
[protocol-v2 framing](https://git-scm.com/docs/gitprotocol-v2) descriptions.
Recognizing their markers does not implement protocol-v2 commands or advertise
protocol-v2 service support.

## Verification and next boundary

`python3 scripts/urbit/code_git_vectors.py` uses the pinned pure Vere evaluator,
the standard Hoon test helper and stock Git. It never boots a ship. The existing
execution guardian enforces the shared native lock, one CPU, 50% CPU quota,
75°C admission, 90°C stop, a three-minute deadline and owned cleanup. A private
network namespace exposes only staged read-only inputs and synthetic outputs.

The framing corpus includes exact arm inventory, failing tang/compiler controls,
binary/trailing-zero vectors, incomplete headers/bodies, controls, offsets,
reserved lengths and size limits. Native-encoded `ls-refs` requests are passed
to a stock Git subprocess; its advertisement and response are decoded natively
and checked against an independent host framing parser. This is subprocess
interoperability, not Stead HTTP authentication or Git hosting.

The retained [2026-11-08 evidence](evidence/2026-11-08/code-git-foundation/README.md)
records all 128 expected checks passing across the pure foundation, including
the 23 framing arms. Actual source hashes, module results, execution controls
and earlier failed attempts are preserved separately. Ten host parser/oracle
tests also pass; they do not stand in for native evaluation.

The next transport layer must first authenticate an individual scoped credential,
enforce request/transfer quotas and feed only bounded bytes into this codec.
Framing success cannot authorize reading objects or accepting refs. Unknown
commands/capabilities must fail explicitly. Pack entry validation and current
policy/ref acceptance remain separate required layers. The
[object/pack profile](CODE_GIT_OBJECT_PROFILE.md) defines their current boundary.

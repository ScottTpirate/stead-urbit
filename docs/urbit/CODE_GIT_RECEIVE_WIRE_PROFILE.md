# Code Git receive command framing

`stead-code-receive-wire` is an original pure parser for the command block of
a SHA-1 receive-pack request. It adds no route, authentication, pack decoder,
quarantine, persistence, response encoder or accepted ref transaction.

`decode [buffer offered]` returns either `[%& changes pack-offset capabilities]`
or `[%| reason]`. Changes retain wire order and use the existing
`stead-code-receive.update` shape `[name prior target]`. The caller retains the
original `[length data]` octets; `pack-offset` points into those exact bytes.
The parser never interprets, copies into a trusted store, or validates the tail.
Even an empty or malformed pack tail needs separate quarantine validation.
Deletion-only pack-presence rules also belong to that next boundary.

The grammar follows the official [Git pack protocol](https://git-scm.com/docs/pack-protocol):
two lowercase 40-digit OIDs, one space between fields, and an exact ref name.
The first command requires a NUL followed by its capability list, which may be
empty. The list may start with the single space emitted by stock send-pack.
Later commands cannot contain NUL. One terminal LF is accepted on each command. The list ends at flush; other control markers, shallow declarations,
signed-push commands and invalid/truncated frames are rejected.

| Bound | Limit |
| --- | --- |
| Command header including flush | 65,536 bytes |
| Commands | 32; duplicate refs rejected |
| Ref name | 1,024 bytes; `refs/heads/` or `refs/tags/` only |
| Command payload including optional LF | 2,132 bytes |
| Capability block | 1,024 bytes |
| Capability tokens | At most 8; each 1–128 printable ASCII bytes |
| Opaque pack tail | 8 MiB |
| Entire caller buffer | 8 MiB plus 65,536 bytes |

Only the bounded header prefix goes to the existing pkt-line decoder, whose
own whole-buffer limit remains 1 MiB. Trailing zero bytes in the original tail
remain significant through its explicit length.

The caller supplies the exact enabled advertisement profile. Recognized names
are `report-status`, `delete-refs`, `atomic`, `ofs-delta`, and
`object-format=sha1`; the internal `agent` key permits a nonempty informational
`agent=<client-value>` token. The result retains the complete client token.
That value never authenticates a principal. Unknown, duplicate, malformed, or
unadvertised capability keys fail. Deletion requires `delete-refs` in the
offered profile; clients need not echo it. The profile is capped at these six
keys. This follows the [official capability negotiation rules](https://git-scm.com/docs/protocol-capabilities).

Recognizing a capability is not permission to advertise it on a real endpoint.
Only advertise behaviors after their complete transport and acceptance paths
are implemented and tested. In particular, delta handling, atomic wire results,
and report-status output are not implemented by this parser. SHA-256,
push-options, report-status-v2, side-band responses and signed pushes remain
unsupported here.

The next integration stage must validate the exact pack/object graph in bounded
quarantine, resolve objects only within the authorized repository, and call
`stead-code-receive.decide` with current policy and ref state at acceptance.
No successful parse is an authorization decision.

The [retained native evidence](evidence/2026-11-08/code-git-foundation/README.md)
records all 45 receive command parser arms passing and its deliberately failing
control returning a nonempty tang. This verifies the bounded pure parser only;
it adds no installed service, accepted write, or completed phase.

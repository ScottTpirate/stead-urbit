# Bounded Git upload-pack requests

`stead-code-fetch-wire` decodes one complete Smart HTTP v0 upload-pack
request. The [Git pack protocol](https://git-scm.com/docs/gitprotocol-pack)
defines the want list, its flush, and the later have list. A final flush asks
for another negotiation round. A final `done` ends negotiation.

The initial profile accepts 64 KiB per request, 256 wants and 1,024 haves.
OIDs are 40 hexadecimal SHA-1 digits and zero is invalid. The optional
`ofs-delta` token is accepted only on the first want and only when the
discovery response offered it. The parser returns wants and haves in wire
order, including duplicates. Stock Git may repeat a want when `HEAD` and a
branch name point to the same commit. Shallow and filtered requests, other
capabilities, other protocol controls, and trailing bytes are rejected.

The result distinguishes another round from a completed negotiation.
The home must select and authorize the repository and its advertised refs,
check wanted OIDs against that view, and treat haves as client claims. An OID
or a successful decode does not grant read access. The parser does not open a
route, choose a pack, emit ACK/NAK, or retain a negotiation session.

The guarded native vector runner covers the parser alongside the existing Git
checks. The corpus includes an exact request captured from stock Git 2.55.0
cloning a synthetic repository through a loopback fixture. Stock Git verified
that fixture's resulting commit and passed strict fsck. The fixture served
its own stock-generated pack, so that clone does not qualify a Stead endpoint.

On November 9, 2026 the pinned native runner passed all 269 checks, including
19 upload-pack request checks. Source hashes matched before and after. The
local report is `.runtime/code-git-vectors/20261109T105717Z-ri034014/output/report.json` with SHA-256
`6448190aaa131f1cb450b5240dfad1677f825c61c32237704d31a15db275c479`.

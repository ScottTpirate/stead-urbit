# Bounded native zlib inflation

`stead-code-git-inflate.hoon` is an original pure implementation of the
[zlib framing](https://www.rfc-editor.org/rfc/rfc1950.html) and
[DEFLATE coding](https://www.rfc-editor.org/rfc/rfc1951.html) needed by the Git
pack decoder. It uses pinned standard Hoon primitives, with no imported Urgit
or other inflater source, and performs no repository or transport operation.

## Public interface

`inflate [input=octets offset=@ud limit=@ud]` returns an `each` containing
`[body=octets next=@ud]` or a reason. Octets retain explicit little-endian width.
`next` is an absolute byte position immediately after the Adler-32 trailer.
Bytes after it are untouched. The caller may supply a prefix ending immediately
before a pack's SHA-1 trailer and then compare `body.length` with the entry's
declared inflated size. `limit` is a maximum, not an equality requirement.

The decoder checks method/window/header flags, rejects preset dictionaries,
handles stored, fixed and dynamic Huffman blocks, and checks Adler-32 before
returning output. Matches may overlap and cross blocks, but must stay within
the already-produced suffix and advertised window. Code construction rejects
oversubscribed or invalid incomplete trees; the one-symbol and empty-distance
exceptions are explicit. Reserved block/length/distance codes and malformed
code-length repeats fail.

## Admission and work bounds

- Input and caller output limit: at most 8 MiB each.
- Blocks: at most 256; literal/length and distance symbols: at most 131,072.
- Charged input-bit/output-byte work: at most 16,777,216 units.
- Trees: at most 288 symbols and 15 bits; dynamic code-length sequences: at
  most 318 entries. These fixed table bounds also limit uncharged setup work.
- Match history: at most 32 KiB; each match emits at most 258 bytes.

Stored blocks check LEN/NLEN and boundaries before copying. Each emission
checks output/work budgets before updating checksum or retaining bytes.
Output is held in bounded chunks and assembled once after checksum verification;
the sliding suffix is separate. Empty blocks consume the block budget. All
other library arms are implementation helpers, not additional public interfaces.
These are conservative engineering limits, not measured repository capacity or
a claim of unrestricted RFC decompressor conformance.

## Evidence and integration

The fixed `python3 scripts/urbit/code_git_vectors.py inflate` target stages only
the inflater, its exact test inventory, the runner/guard and pinned test helper.
It does not compile or read the pack resolver. It retains the same native lock,
thermal admission, CPU limit and timeout as the foundation runner.

The [checked native receipt](evidence/2026-11-08/code-git-inflate/README.md)
records 47 expected unit arms and both deliberate failure controls passing.
Fixtures include stock zlib output, exact binary/offset/tail boundaries,
overlapping and cross-block references, block-limit edges and malformed inputs.
Work guards are also exercised directly; maximum input/output capacities have
not been benchmarked. Host-only parser tests remain separate.

The pack resolver must enforce exact declared width, forward compressed offset,
entry count/trailer alignment, cumulative expansion and delta depth. It must
resolve only authorized bases, validate the resulting object graph, retain
quarantine and reach final current-policy acceptance. Inflation alone is not
proof that an object is valid, reachable, readable or accepted.

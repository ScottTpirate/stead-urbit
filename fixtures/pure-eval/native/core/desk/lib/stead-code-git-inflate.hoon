::  Original bounded RFC 1950/1951 decoder. No repository or transport effects.
|%
+$  octets  [length=@ud data=@]
+$  cursor  [bit=@ud fuel=@ud]
+$  table  (map [@ud @ud] @ud)
+$  output
  $:  length=@ud  window=octets  chunks=(list octets)
      sum-one=@ud  sum-two=@ud
  ==
+$  segment  [out=output at=cursor symbols=@ud]
+$  tables  [literal=table distance=table at=cursor]
+$  result  (each [body=octets next=@ud] @tas)
::  Fixed-width elements are little-endian within the bit stream.
++  bits
  |=  [wire=octets at=cursor width=@ud]
  ^-  (each [value=@ud at=cursor] @tas)
  ?:  (gth width 16)  [%| %bit-width]
  ?:  (gth (add bit.at width) (mul length.wire 8))  [%| %truncated]
  ?:  (gth width fuel.at)  [%| %work-bound]
  [%& (cut 0 [bit.at width] data.wire) [(add bit.at width) (sub fuel.at width)]]
::  Canonical prefix trees, never more than 288 symbols or 15 bits.
::  Empty distance trees and the RFC one-symbol tree are explicit exceptions.
++  tree
  |=  [lengths=(list @ud) mode=@tas]
  ^-  (each table @tas)
  ?:  (gth (lent lengths) 288)  [%| %tree-bound]
  =/  stats=(each [counts=(map @ud @ud) used=@ud maximum=@ud] @tas)
    =/  left  lengths
    =/  counts=(map @ud @ud)  ~
    =/  used=@ud  0
    =/  maximum=@ud  0
    |-  ^-  (each [counts=(map @ud @ud) used=@ud maximum=@ud] @tas)
    ?~  left  [%& counts used maximum]
    ?:  (gth i.left ?:(=(%codes mode) 7 15))  [%| %tree-width]
    ?:  =(0 i.left)  $(left t.left)
    $(left t.left, counts (~(put by counts) i.left +((fall (~(get by counts) i.left) 0))), used +(used), maximum (max maximum i.left))
  ?:  ?=(%| -.stats)  [%| p.stats]
  =/  first=(each (map @ud @ud) @tas)
    =/  width=@ud  1
    =/  slots=@ud  1
    =/  previous=@ud  0
    =/  code=@ud  0
    =/  starts=(map @ud @ud)  ~
    |-  ^-  (each (map @ud @ud) @tas)
    ?:  =(16 width)
      ?:  =(0 slots)  [%& starts]
      ?:  &(=(%distance mode) =(0 used.p.stats))  [%& starts]
      ?:  &(!=(%codes mode) =(1 used.p.stats) =(1 maximum.p.stats))  [%& starts]
      [%| %incomplete-tree]
    =/  count=@ud  (fall (~(get by counts.p.stats) width) 0)
    =/  available=@ud  (mul slots 2)
    ?:  (gth count available)  [%| %oversubscribed-tree]
    =/  next=@ud  (mul (add code previous) 2)
    $(width +(width), slots (sub available count), previous count, code next, starts (~(put by starts) width next))
  ?:  ?=(%| -.first)  [%| p.first]
  =/  starts  p.first
  =/  symbol=@ud  0
  =/  codes=table  ~
  |-  ^-  (each table @tas)
  ?~  lengths  [%& codes]
  ?:  =(0 i.lengths)  $(lengths t.lengths, symbol +(symbol))
  =/  code=@ud  (fall (~(get by starts) i.lengths) 0)
  $(lengths t.lengths, symbol +(symbol), starts (~(put by starts) i.lengths +(code)), codes (~(put by codes) [i.lengths code] symbol))
::  Huffman symbols are read MSB-first, unlike fixed-width elements.
++  symbol
  |=  [wire=octets at=cursor codes=table]
  ^-  (each [value=@ud at=cursor] @tas)
  =/  width=@ud  0
  =/  code=@ud  0
  |-  ^-  (each [value=@ud at=cursor] @tas)
  ?:  =(15 width)  [%| %invalid-code]
  =/  read  (bits wire at 1)
  ?:  ?=(%| -.read)  [%| p.read]
  =/  next=@ud  (add (mul code 2) value.p.read)
  =/  found  (~(get by codes) [+(width) next])
  ?^  found  [%& u.found at.p.read]
  $(at at.p.read, width +(width), code next)
::  Every emitted byte is charged to work and Adler-32 before publication.
::  Only a 32 KiB suffix is retained for backwards references; output chunks
::  are assembled once after the checksum succeeds.
++  emit
  |=  [out=output bytes=octets limit=@ud fuel=@ud]
  ^-  (each [out=output fuel=@ud] @tas)
  ?:  (gth (add length.out length.bytes) limit)  [%| %output-bound]
  ?:  (gth length.bytes fuel)  [%| %work-bound]
  =/  sums=[one=@ud two=@ud]
    =/  index=@ud  0
    =/  one=@ud  sum-one.out
    =/  two=@ud  sum-two.out
    |-  ^-  [one=@ud two=@ud]
    ?:  =(index length.bytes)  [one two]
    =/  next=@ud  (mod (add one (cut 3 [index 1] data.bytes)) 65.521)
    $(index +(index), one next, two (mod (add two next) 65.521))
  =/  tail=octets
    ?:  (gte length.bytes 32.768)
      [32.768 (cut 3 [(sub length.bytes 32.768) 32.768] data.bytes)]
    =/  keep=@ud  (min length.window.out (sub 32.768 length.bytes))
    [(add keep length.bytes) (mix (cut 3 [(sub length.window.out keep) keep] data.window.out) (lsh [3 keep] data.bytes))]
  [%& [(add length.out length.bytes) tail [bytes chunks.out] one.sums two.sums] (sub fuel length.bytes)]
::  Expand an overlapping distance reference by doubling its prefix, at most
::  nine small iterations for a DEFLATE match of at most 258 bytes.
++  repeat
  |=  [window=octets distance=@ud size=@ud]
  ^-  octets
  =/  width=@ud  (min distance size)
  =/  data=@  (cut 3 [(sub length.window distance) width] data.window)
  |-  ^-  octets
  ?:  (gte width size)  [size (cut 3 [0 size] data)]
  $(width (mul width 2), data (mix data (lsh [3 width] data)))
++  fixed
  ^-  (each [literal=table distance=table] @tas)
  =/  lengths=(list @ud)
    =/  index=@ud  288
    =/  out=(list @ud)  ~
    |-  ^-  (list @ud)
    ?:  =(0 index)  out
    =/  n=@ud  (dec index)
    =/  width=@ud  ?:((lth n 144) 8 ?:((lth n 256) 9 ?:((lth n 280) 7 8)))
    $(index n, out [width out])
  =/  literal  (tree lengths %literal)
  ?:  ?=(%| -.literal)  [%| p.literal]
  =/  distance  (tree (reap 32 5) %distance)
  ?:  ?=(%| -.distance)  [%| p.distance]
  [%& p.literal p.distance]
::  Dynamic code-length trees and their bounded repeat instructions.
++  dynamic
  |=  [wire=octets at=cursor]
  ^-  (each tables @tas)
  =/  header  (bits wire at 14)
  ?:  ?=(%| -.header)  [%| p.header]
  =/  literals=@ud  (add 257 (cut 0 [0 5] value.p.header))
  ?:  (gth literals 286)  [%| %literal-count]
  =/  distances=@ud  (add 1 (cut 0 [5 5] value.p.header))
  =/  ncode=@ud  (add 4 (cut 0 [10 4] value.p.header))
  =/  raw=(each [lengths=(list @ud) at=cursor] @tas)
    =/  index=@ud  0
    =/  at=cursor  at.p.header
    =/  values=(map @ud @ud)  ~
    =/  order=(list @ud)  ~[16 17 18 0 8 7 9 6 10 5 11 4 12 3 13 2 14 1 15]
    |-  ^-  (each [lengths=(list @ud) at=cursor] @tas)
    ?:  =(index ncode)
      [%& (turn (gulf 0 18) |=(n=@ud (fall (~(get by values) n) 0))) at]
    =/  read  (bits wire at 3)
    ?:  ?=(%| -.read)  [%| p.read]
    $(index +(index), at at.p.read, values (~(put by values) (snag index order) value.p.read))
  ?:  ?=(%| -.raw)  [%| p.raw]
  =/  codes  (tree lengths.p.raw %codes)
  ?:  ?=(%| -.codes)  [%| p.codes]
  =/  expanded=(each [lengths=(list @ud) at=cursor] @tas)
    =/  at=cursor  at.p.raw
    =/  count=@ud  0
    =/  previous=@ud  0
    =/  out=(list @ud)  ~
    =/  total=@ud  (add literals distances)
    |-  ^-  (each [lengths=(list @ud) at=cursor] @tas)
    ?:  =(count total)  [%& (flop out) at]
    =/  read  (symbol wire at p.codes)
    ?:  ?=(%| -.read)  [%| p.read]
    ?:  (lth value.p.read 16)
      $(at at.p.read, count +(count), previous value.p.read, out [value.p.read out])
    ?:  &(=(16 value.p.read) =(0 count))  [%| %repeat-without-previous]
    =/  width=@ud  ?:(=(16 value.p.read) 2 ?:(=(17 value.p.read) 3 7))
    =/  extra  (bits wire at.p.read width)
    ?:  ?=(%| -.extra)  [%| p.extra]
    =/  amount=@ud  (add value.p.extra ?:(=(18 value.p.read) 11 3))
    ?:  (gth (add count amount) total)  [%| %repeat-bound]
    =/  value=@ud  ?:(=(16 value.p.read) previous 0)
    $(at at.p.extra, count (add count amount), previous value, out (weld (reap amount value) out))
  ?:  ?=(%| -.expanded)  [%| p.expanded]
  ?:  =(0 (snag 256 lengths.p.expanded))  [%| %missing-end-code]
  =/  literal  (tree (scag literals lengths.p.expanded) %literal)
  ?:  ?=(%| -.literal)  [%| p.literal]
  =/  distance  (tree (slag literals lengths.p.expanded) %distance)
  ?:  ?=(%| -.distance)  [%| p.distance]
  [%& p.literal p.distance at.p.expanded]
::  Decode one compressed block; at most 131,072 literal/length and distance
::  symbols across the stream. Each code consumes at most 15 input bits.
++  compressed
  |=  [wire=octets at=cursor literal=table distance=table out=output limit=@ud window=@ud symbols=@ud]
  ^-  (each segment @tas)
  |-  ^-  (each segment @tas)
  ?:  (gte symbols 131.072)  [%| %symbol-bound]
  =/  read  (symbol wire at literal)
  ?:  ?=(%| -.read)  [%| p.read]
  ?:  =(256 value.p.read)  [%& out at.p.read +(symbols)]
  ?:  (lth value.p.read 256)
    =/  added  (emit out [1 value.p.read] limit fuel.at.p.read)
    ?:  ?=(%| -.added)  [%| p.added]
    $(at [bit.at.p.read fuel.p.added], out out.p.added, symbols +(symbols))
  ?:  (gth value.p.read 285)  [%| %reserved-length]
  =/  index=@ud  (sub value.p.read 257)
  =/  extra=@ud
    ?:  |((lth index 8) =(28 index))  0
    +((div (sub index 8) 4))
  =/  base=@ud
    ?:  =(28 index)  258
    ?:  (lth index 8)  (add 3 index)
    (add (add (bex (add extra 2)) 3) (mul (mod (sub index 8) 4) (bex extra)))
  =/  length-bits  (bits wire at.p.read extra)
  ?:  ?=(%| -.length-bits)  [%| p.length-bits]
  =/  size=@ud  (add base value.p.length-bits)
  ?:  (gte +(symbols) 131.072)  [%| %symbol-bound]
  =/  distance-code  (symbol wire at.p.length-bits distance)
  ?:  ?=(%| -.distance-code)  [%| p.distance-code]
  ?:  (gth value.p.distance-code 29)  [%| %reserved-distance]
  =/  dextra=@ud
    ?:  (lth value.p.distance-code 4)  0
    (dec (div value.p.distance-code 2))
  =/  dbase=@ud
    ?:  (lth value.p.distance-code 4)  +(value.p.distance-code)
    +((lsh [0 dextra] (add 2 (mod value.p.distance-code 2))))
  =/  distance-bits  (bits wire at.p.distance-code dextra)
  ?:  ?=(%| -.distance-bits)  [%| p.distance-bits]
  =/  back=@ud  (add dbase value.p.distance-bits)
  ?:  |((gth back length.window.out) (gth back window))  [%| %distance-bound]
  =/  added  (emit out (repeat window.out back size) limit fuel.at.p.distance-bits)
  ?:  ?=(%| -.added)  [%| p.added]
  $(at [bit.at.p.distance-bits fuel.p.added], out out.p.added, symbols (add symbols 2))
++  stored
  |=  [wire=octets at=cursor out=output limit=@ud symbols=@ud]
  ^-  (each segment @tas)
  =/  skip=@ud  (mod (sub 8 (mod bit.at 8)) 8)
  =/  align  (bits wire at skip)
  ?:  ?=(%| -.align)  [%| p.align]
  =/  len  (bits wire at.p.align 16)
  ?:  ?=(%| -.len)  [%| p.len]
  =/  inverse  (bits wire at.p.len 16)
  ?:  ?=(%| -.inverse)  [%| p.inverse]
  ?.  =(65.535 (mix value.p.len value.p.inverse))  [%| %stored-complement]
  =/  begin=@ud  (div bit.at.p.inverse 8)
  =/  end=@ud  (add begin value.p.len)
  ?:  (gth end length.wire)  [%| %truncated]
  =/  added  (emit out [value.p.len (cut 3 [begin value.p.len] data.wire)] limit fuel.at.p.inverse)
  ?:  ?=(%| -.added)  [%| p.added]
  [%& out.p.added [(mul end 8) fuel.p.added] symbols]
::  Supported public gate. `next` is absolute, immediately after Adler-32.
::  8 MiB input/output, 256 blocks, 131,072 symbols and 16,777,216 charged
::  input-bit/output-byte work units. No preset dictionary is accepted.
++  inflate
  |=  [input=octets offset=@ud limit=@ud]
  ^-  result
  ?.  &((lte length.input 8.388.608) (lte (met 3 data.input) length.input))
    [%| %input-bound]
  ?:  (gth limit 8.388.608)  [%| %output-limit]
  ?:  (gth (add offset 2) length.input)  [%| %truncated]
  =/  cmf=@ud  (cut 3 [offset 1] data.input)
  =/  flags=@ud  (cut 3 [+(offset) 1] data.input)
  ?.  &(=(8 (cut 0 [0 4] cmf)) (lte (rsh [0 4] cmf) 7))
    [%| %zlib-method]
  ?.  =(0 (mod (add (mul cmf 256) flags) 31))  [%| %zlib-header]
  ?:  =(1 (cut 0 [5 1] flags))  [%| %dictionary-unsupported]
  =/  window=@ud  (bex (add 8 (rsh [0 4] cmf)))
  =/  at=cursor  [(mul (add offset 2) 8) 16.777.216]
  =/  out=output  [0 [0 0] ~ 1 0]
  =/  blocks=@ud  0
  =/  symbols=@ud  0
  |-  ^-  result
  ?:  =(256 blocks)  [%| %block-bound]
  =/  header  (bits input at 3)
  ?:  ?=(%| -.header)  [%| p.header]
  =/  final=?  =(1 (cut 0 [0 1] value.p.header))
  =/  kind=@ud  (cut 0 [1 2] value.p.header)
  ?:  =(3 kind)  [%| %reserved-block]
  =/  decoded=(each segment @tas)
    ?:  =(0 kind)  (stored input at.p.header out limit symbols)
    =/  trees=(each tables @tas)
      ?:  =(2 kind)  (dynamic input at.p.header)
      =/  value  fixed
      ?:  ?=(%| -.value)  [%| p.value]
      [%& literal.p.value distance.p.value at.p.header]
    ?:  ?=(%| -.trees)  [%| p.trees]
    (compressed input at.p.trees literal.p.trees distance.p.trees out limit window symbols)
  ?:  ?=(%| -.decoded)  [%| p.decoded]
  ?.  final
    $(at at.p.decoded, out out.p.decoded, symbols symbols.p.decoded, blocks +(blocks))
  =/  trailer=@ud  (div (add bit.at.p.decoded 7) 8)
  ?:  (gth (add trailer 4) length.input)  [%| %truncated]
  =/  expected=@ud  (rev 3 4 (cut 3 [trailer 4] data.input))
  =/  observed=@ud  (add (mul sum-two.out.p.decoded 65.536) sum-one.out.p.decoded)
  ?.  =(expected observed)  [%| %adler]
  [%& [length.out.p.decoded (can 3 (flop chunks.out.p.decoded))] (add trailer 4)]
--

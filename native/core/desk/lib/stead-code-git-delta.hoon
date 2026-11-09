::  Original bounded Git delta program application; no graph or ownership.
|%
+$  octets  [length=@ud data=@]
+$  result  (each octets @tas)
++  valid-octets
  |=  value=octets
  ^-  ?
  &((lte length.value 8.388.608) (lte (met 3 data.value) length.value))
::  Little-endian seven-bit sizes, at most four bytes and 8 MiB.
++  read-size
  |=  [wire=octets cursor=@ud]
  ^-  (each [value=@ud next=@ud] @tas)
  =/  value=@ud  0
  =/  shift=@ud  0
  |-  ^-  (each [value=@ud next=@ud] @tas)
  ?:  (gte cursor length.wire)  [%| %truncated-size]
  ?:  (gte shift 28)  [%| %size-encoding]
  =/  byte=@ud  (cut 3 [cursor 1] data.wire)
  =/  size=@ud  (add value (lsh [0 shift] (cut 0 [0 7] byte)))
  ?:  (gth size 8.388.608)  [%| %size-bound]
  ?:  (lth byte 128)  [%& size +(cursor)]
  $(cursor +(cursor), value size, shift (add shift 7))
::  Optional copy bytes retain their bit position when intervening bytes
::  are absent. An encoded zero copy size means 65,536 bytes.
++  copy-fields
  |=  [wire=octets cursor=@ud opcode=@ud]
  ^-  (each [at=@ud size=@ud next=@ud] @tas)
  =/  index=@ud  0
  =/  offset=@ud  0
  =/  size=@ud  0
  |-  ^-  (each [at=@ud size=@ud next=@ud] @tas)
  ?:  =(7 index)  [%& offset ?:(=(0 size) 65.536 size) cursor]
  ?:  =(0 (cut 0 [index 1] opcode))  $(index +(index))
  ?:  (gte cursor length.wire)  [%| %truncated-copy]
  =/  byte=@ud  (cut 3 [cursor 1] data.wire)
  ?:  (lth index 4)
    $(index +(index), cursor +(cursor), offset (add offset (lsh [3 index] byte)))
  $(index +(index), cursor +(cursor), size (add size (lsh [3 (sub index 4)] byte)))
::  Caller supplies the remaining aggregate expansion budget (<=32 MiB).
::  At most 4,096 instructions; chunks are assembled once, preserving zeroes.
++  apply
  |=  [base=octets patch=octets remaining=@ud]
  ^-  result
  ?.  &((valid-octets base) (valid-octets patch))  [%| %byte-bound]
  ?:  (gth remaining 33.554.432)  [%| %budget-bound]
  =/  before  (read-size patch 0)
  ?:  ?=(%| -.before)  [%| p.before]
  ?.  =(length.base value.p.before)  [%| %base-size]
  =/  after  (read-size patch next.p.before)
  ?:  ?=(%| -.after)  [%| p.after]
  ?:  (gth value.p.after remaining)  [%| %budget-bound]
  =/  target=@ud  value.p.after
  =/  cursor=@ud  next.p.after
  =/  written=@ud  0
  =/  count=@ud  0
  =/  chunks=(list octets)  ~
  |-  ^-  result
  ?:  =(cursor length.patch)
    ?.  =(written target)  [%| %result-size]
    [%& written (can 3 (flop chunks))]
  ?:  =(4.096 count)  [%| %instruction-bound]
  =/  opcode=@ud  (cut 3 [cursor 1] data.patch)
  ?:  =(0 opcode)  [%| %reserved-instruction]
  ?:  (lth opcode 128)
    ?:  (gth (add +(cursor) opcode) length.patch)  [%| %truncated-literal]
    ?:  (gth (add written opcode) target)  [%| %result-bound]
    =/  piece=octets  [opcode (cut 3 [+(cursor) opcode] data.patch)]
    $(cursor (add +(cursor) opcode), written (add written opcode), count +(count), chunks [piece chunks])
  =/  copy  (copy-fields patch +(cursor) opcode)
  ?:  ?=(%| -.copy)  [%| p.copy]
  ?:  (gth (add at.p.copy size.p.copy) length.base)  [%| %copy-bound]
  ?:  (gth (add written size.p.copy) target)  [%| %result-bound]
  =/  piece=octets  [size.p.copy (cut 3 [at.p.copy size.p.copy] data.base)]
  $(cursor next.p.copy, written (add written size.p.copy), count +(count), chunks [piece chunks])
--

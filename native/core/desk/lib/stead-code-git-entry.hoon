::  Original bounded pack-entry header decoder. No inflate or acceptance.
::  The caller verifies the envelope and supplies an actual entry boundary.
|%
+$  octets  [length=@ud data=@]
+$  base  ?(%none [%offset at=@ud] [%oid value=@ux])
+$  header  [kind=@ud inflated=@ud source=base zlib-offset=@ud]
+$  result  (each header @tas)
::  OFS distances use Git's biased big-endian offset encoding. A returned
::  position is only a candidate: the resolver must find an earlier entry.
++  offset-base
  |=  [pack=octets cursor=@ud end=@ud origin=@ud]
  ^-  (each [at=@ud next=@ud] @tas)
  =/  distance=@ud  0
  =/  count=@ud  0
  |-  ^-  (each [at=@ud next=@ud] @tas)
  ?:  (gte cursor end)  [%| %truncated-offset]
  ?:  =(4 count)  [%| %offset-bound]
  =/  byte=@ud  (cut 3 [cursor 1] data.pack)
  =/  value=@ud
    ?:  =(0 count)  (cut 0 [0 7] byte)
    (add (mul +(distance) 128) (cut 0 [0 7] byte))
  ?:  (gth value 8.388.608)  [%| %offset-bound]
  ?:  (gte byte 128)
    $(cursor +(cursor), distance value, count +(count))
  ?:  |(=(0 value) (gth value (sub origin 12)))
    [%| %invalid-offset]
  [%& (sub origin value) +(cursor)]
::  Complete buffer <=8 MiB, first entry >=12, SHA-1 trailer excluded.
::  Size is the inflated object or delta-program length, not the delta result.
++  decode
  |=  [pack=octets offset=@ud]
  ^-  result
  ?.  ?&  (gte length.pack 32)
          (lte length.pack 8.388.608)
          (lte (met 3 data.pack) length.pack)
      ==
    [%| %buffer-bound]
  =/  end=@ud  (sub length.pack 20)
  ?.  &((gte offset 12) (lth offset end))  [%| %entry-offset]
  =/  first=@ud  (cut 3 [offset 1] data.pack)
  =/  kind=@ud  (cut 0 [4 3] first)
  ?.  ?|(=(1 kind) =(2 kind) =(3 kind) =(4 kind) =(6 kind) =(7 kind))
    [%| %reserved-type]
  =/  cursor=@ud  +(offset)
  =/  size=@ud  (cut 0 [0 4] first)
  =/  shift=@ud  4
  =/  more=?  (gte first 128)
  |-  ^-  result
  ?:  more
    ?:  (gte cursor end)  [%| %truncated-size]
    ?:  (gte shift 32)  [%| %size-encoding]
    =/  byte=@ud  (cut 3 [cursor 1] data.pack)
    =/  value=@ud  (add size (lsh [0 shift] (cut 0 [0 7] byte)))
    ?:  (gth value 8.388.608)  [%| %size-bound]
    $(cursor +(cursor), size value, shift (add shift 7), more (gte byte 128))
  ?:  =(6 kind)
    =/  resolved  (offset-base pack cursor end offset)
    ?:  ?=(%| -.resolved)  [%| p.resolved]
    ?:  (gte next.p.resolved end)  [%| %missing-zlib]
    [%& kind size [%offset at.p.resolved] next.p.resolved]
  ?:  =(7 kind)
    ?:  (gth (add cursor 20) end)  [%| %truncated-reference]
    ?:  =(end (add cursor 20))  [%| %missing-zlib]
    [%& kind size [%oid (rev 3 20 (cut 3 [cursor 20] data.pack))] (add cursor 20)]
  ?:  (gte cursor end)  [%| %missing-zlib]
  [%& kind size %none cursor]
--

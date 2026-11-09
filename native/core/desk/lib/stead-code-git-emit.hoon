::  Original bounded SHA-1 pack writer. Stored DEFLATE only; exact bytes.
::  The caller chooses an authorized graph. Encoding grants no read access.
/+  stead-git, stead-code-git-objects
|%
+$  octets  octets:stead-code-git-objects
+$  object  object:stead-code-git-objects
+$  result  (each octets @tas)
::  Ordinary pack entry type and minimally encoded inflated body length.
++  header
  |=  [kind=@tas size=@ud]
  ^-  result
  ?:  (gth size 8.388.608)  [%| %object-bound]
  =/  code=@ud
    ?+  kind  0
      %commit  1
      %tree  2
      %blob  3
      %tag  4
    ==
  ?:  =(0 code)  [%| %unsupported-kind]
  =/  remaining=@ud  (rsh [0 4] size)
  =/  first=@ud  (add (mul code 16) (add (cut 0 [0 4] size) ?:(=(0 remaining) 0 128)))
  =/  out=octets  [1 first]
  |-  ^-  result
  ?:  =(0 remaining)  [%& out]
  =/  next=@ud  (rsh [0 7] remaining)
  =/  byte=@ud  (add (cut 0 [0 7] remaining) ?:(=(0 next) 0 128))
  $(remaining next, out (append:stead-git out [1 byte]))
::  All ordinary entries use the same deterministic stored-block profile.
::  A zero-byte body still has one final empty block.
++  zlib-size
  |=  size=@ud
  ^-  (each @ud @tas)
  ?:  (gth size 8.388.608)  [%| %object-bound]
  =/  blocks=@ud  (max 1 (div (add size 65.534) 65.535))
  =/  total=@ud  (add size (add 6 (mul 5 blocks)))
  ?:  (gth total 8.388.608)  [%| %zlib-bound]
  [%& total]
++  adler
  |=  body=octets
  ^-  (each @ud @tas)
  ?.  (valid-octets:stead-git body)  [%| %object-bound]
  =/  index=@ud  0
  =/  one=@ud  1
  =/  two=@ud  0
  |-  ^-  (each @ud @tas)
  ?:  =(index length.body)  [%& (add (mul two 65.536) one)]
  =/  next=@ud  (mod (add one (cut 3 [index 1] data.body)) 65.521)
  $(index +(index), one next, two (mod (add two next) 65.521))
++  stored
  |=  body=octets
  ^-  result
  ?.  (valid-octets:stead-git body)  [%| %object-bound]
  =/  size  (zlib-size length.body)
  ?:  ?=(%| -.size)  [%| p.size]
  =/  checksum  (adler body)
  ?:  ?=(%| -.checksum)  [%| p.checksum]
  =/  chunks=(list octets)  ~[[2 0x178]]
  =/  offset=@ud  0
  |-  ^-  result
  =/  width=@ud  (min 65.535 (sub length.body offset))
  =/  next=@ud  (add offset width)
  =/  final=?  =(next length.body)
  =/  prefix=octets
    [5 (add ?:(final 1 0) (add (lsh [3 1] width) (lsh [3 3] (sub 65.535 width))))]
  =/  piece=octets  [width (cut 3 [offset width] data.body)]
  =.  chunks  [piece prefix chunks]
  ?.  final  $(offset next)
  =/  trailer=octets  [4 (rev 3 4 p.checksum)]
  [%& p.size (can 3 (flop [trailer chunks]))]
::  Metadata-only resource admission, before hashing bodies or making output.
::  A successful estimate is not a verified object or an encoded pack.
++  admit
  |=  items=(list object)
  ^-  (each [count=@ud bytes=@ud] @tas)
  =/  count=@ud  0
  =/  bytes=@ud  32
  =/  seen=(set @ux)  ~
  |-  ^-  (each [count=@ud bytes=@ud] @tas)
  ?~  items  [%& count bytes]
  ?:  =(4.096 count)  [%| %object-count]
  =/  item  i.items
  ?.  (valid-octets:stead-git body.item)  [%| %object-bound]
  ?:  (gth (met 3 oid.item) 20)  [%| %oid-bound]
  ?:  (~(has in seen) oid.item)  [%| %duplicate-object]
  =/  prefix  (header kind.item length.body.item)
  ?:  ?=(%| -.prefix)  [%| p.prefix]
  =/  stream  (zlib-size length.body.item)
  ?:  ?=(%| -.stream)  [%| p.stream]
  =/  total=@ud  (add bytes (add length.p.prefix p.stream))
  ?:  (gth total 8.388.608)  [%| %pack-bound]
  $(items t.items, count +(count), bytes total, seen (~(put in seen) oid.item))
::  Rehash every caller-supplied object. OIDs, bytes, order and object types
::  are retained. No delta, external base, normalization, refs or graph walk.
++  encode
  |=  items=(list object)
  ^-  result
  =/  admission  (admit items)
  ?:  ?=(%| -.admission)  [%| p.admission]
  =/  prefix=octets
    [12 (can 3 ~[[4 'PACK'] [4 0x200.0000] [4 (rev 3 4 count.p.admission)]])]
  =/  chunks=(list octets)  ~[prefix]
  |-  ^-  result
  ?~  items
    =/  length=@ud  (sub bytes.p.admission 20)
    =/  data=@  (can 3 (flop chunks))
    =/  checksum=@ux  (sha-1l:sha [length (rev 3 length data)])
    [%& bytes.p.admission (mix data (lsh [3 length] (rev 3 20 checksum)))]
  =/  item  i.items
  =/  checked  (hash-object:stead-code-git-objects kind.item body.item)
  ?~  checked  [%| %invalid-object]
  ?.  =(item u.checked)  [%| %oid-mismatch]
  =/  head  (header kind.item length.body.item)
  ?:  ?=(%| -.head)  [%| p.head]
  =/  body  (stored body.item)
  ?:  ?=(%| -.body)  [%| p.body]
  $(items t.items, chunks [p.body p.head chunks])
--

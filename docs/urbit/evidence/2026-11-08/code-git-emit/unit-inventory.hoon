=/  test
::  testing utilities meant to be directly used from files in %/tests
::
|%
::  +expect-eq: compares :expected and :actual and pretty-prints the result
::
++  expect-eq
  |=  [expected=vase actual=vase]
  ^-  tang
  ::
  =|  result=tang
  ::
  =?  result  !=(q.expected q.actual)
    %+  weld  result
    ^-  tang
    :~  [%palm [": " ~ ~ ~] [leaf+"expected" (sell expected) ~]]
        [%palm [": " ~ ~ ~] [leaf+"actual  " (sell actual) ~]]
    ==
  ::
  =?  result  !(~(nest ut p.actual) | p.expected)
    %+  weld  result
    ^-  tang
    :~  :+  %palm  [": " ~ ~ ~]
        :~  [%leaf "failed to nest"]
            (~(dunk ut p.actual) %actual)
            (~(dunk ut p.expected) %expected)
    ==  ==
  result
::  +expect: compares :actual to %.y and pretty-prints anything else
::
++  expect
  |=  actual=vase
  (expect-eq !>(%.y) actual)
::  +expect-fail: kicks a trap, expecting crash. pretty-prints if succeeds
::
++  expect-fail
  |=  a=(trap)
  ^-  tang
  =/  b  (mule a)
  ?-  -.b
    %|  ~
    %&  ['expected failure - succeeded' ~]
  ==
::  +expect-success: kicks a trap, expecting success; returns trace on failure
::
++  expect-success
  |=  a=(trap)
  ^-  tang
  =/  b  (mule a)
  ?-  -.b
    %&  ~
    %|  ['expected success - failed' p.b]
  ==
::
::  +expect-fail-message: kicks a trap, expecting crash, compares the resulting error message
++  expect-fail-message
  |=  [msg=@t a=(trap)]
  ^-  tang
  =/  b  (mule a)
  ?-  -.b
    %|  |^
        =/  =tang  (flatten +.b)
        ?:  ?=(^ (find (trip msg) tang))
          ~
        ['expected error message - not found' ~]
        ++  flatten
          |=  tang=(list tank)
          =|  res=tape
          |-  ^-  tape
          ?~  tang  res
          $(tang t.tang, res (weld ~(ram re i.tang) res))
        --
    %&  ['expected failure - succeeded' ~]
  ==
::  $a-test-chain: a sequence of tests to be run
::
::  NB: arms shouldn't start with `test-` so that `-test % ~` runs
::
+$  a-test-chain
  $_
  |?
  ?:  =(0 0)
    [%& p=*tang]
  [%| p=[tang=*tang next=^?(..$)]]
::  +run-chain: run a sequence of tests, stopping at first failure
::
++  run-chain
  |=  seq=a-test-chain
  ^-  tang
  =/  res  $:seq
  ?-  -.res
    %&  p.res
    %|  ?.  =(~ tang.p.res)
          tang.p.res
        $(seq next.p.res)
  ==
::  +category: prepends a name to an error result; passes successes unchanged
::
++  category
  |=  [a=tape b=tang]  ^-  tang
  ?:  =(~ b)  ~  :: test OK
  :-  leaf+"in: '{a}'"
  (turn b |=(c=tank rose+[~ "  " ~]^~[c]))
--

=/  stead-git
::  Original bounded Git object builders for the minimum Stead document slice.
::  No Urgit code. Git byte formats + pinned Hoon SHA-1 primitive only.
::  Pure construction: callers own authorization, reachability and acceptance.
|%
+$  octets  [length=@ud data=@]
+$  object  [kind=@tas body=octets oid=@ux]
+$  entry  [name=@t oid=@ux]
::
++  valid-octets
  |=  value=octets
  ^-  ?
  ?&  (lte length.value 8.388.608)
      (lte (met 3 data.value) length.value)
  ==
::
++  append
  |=  [left=octets right=octets]
  ^-  octets
  ~|  %stead-git-octets
  ?>  (lte (met 3 data.left) length.left)
  ?>  (lte (met 3 data.right) length.right)
  ?>  (lte (add length.left length.right) 8.388.864)
  [(add length.left length.right) (mix data.left (lsh [3 length.left] data.right))]
::
++  decimal
  |=  value=@ud
  ^-  @t
  ~|  %stead-git-number
  ?>  (lte value 18.446.744.073.709.551.615)
  ?:  =(0 value)  '0'
  =/  digits=tape  ~
  |-  ^-  @t
  ?:  =(0 value)  (crip digits)
  $(value (div value 10), digits [(add 48 (mod value 10)) digits])
::
++  oid-text
  |=  value=@ux
  ^-  @t
  ~|  %stead-git-oid
  ?>  (lte (met 0 value) 160)
  =/  remaining=@ud  40
  =/  digits=tape  ~
  |-  ^-  @t
  ?:  =(0 remaining)  (crip digits)
  $(remaining (dec remaining), value (rsh [2 1] value), digits [(snag (end [2 1] value) "0123456789abcdef") digits])
::
++  valid-uuid
  |=  value=@t
  ^-  ?
  ?.  =(36 (met 3 value))  %.n
  =/  index=@ud  0
  |-  ^-  ?
  ?:  =(36 index)  %.y
  =/  byte=@ud  (cut 3 [index 1] value)
  =/  valid=?
    ?:  ?|(=(index 8) =(index 13) =(index 18) =(index 23))
      =(byte 45)
    ?:  =(index 14)  =(byte 55)
    ?:  =(index 19)  ?|(=(byte 56) =(byte 57) =(byte 97) =(byte 98))
    ?|  ?&((gte byte 48) (lte byte 57))
        ?&((gte byte 97) (lte byte 102))
    ==
  ?.  valid  %.n
  $(index +(index))
::
++  valid-name
  |=  value=@t
  ^-  ?
  ?&  =(39 (met 3 value))
      =('.md' (cut 3 [36 3] value))
      (valid-uuid (cut 3 [0 36] value))
  ==
::
++  make-object
  |=  [kind=@tas body=octets]
  ^-  object
  ~|  %stead-git-object
  ?>  ?|(=(kind %blob) =(kind %tree) =(kind %commit))
  ?>  (valid-octets body)
  =/  header=@t  (cat 3 kind (cat 3 ' ' (decimal length.body)))
  =/  raw=octets  (append [(add 1 (met 3 header)) header] body)
  [kind body (sha-1l:sha [length.raw (rev 3 length.raw data.raw)])]
::
++  make-blob
  |=  body=octets
  ^-  object
  (make-object %blob body)
::
++  make-tree
  |=  entries=(list entry)
  ^-  object
  ~|  %stead-git-tree
  =/  pending  entries
  =/  count=@ud  0
  =.  entries
    |-  ^-  (list entry)
    ?~  pending  entries
    ?>  (lth count 32)
    ?>  (valid-name name.i.pending)
    ?>  (lte (met 0 oid.i.pending) 160)
    $(pending t.pending, count +(count))
  =/  ordered=(list entry)
    (sort entries |=([left=entry right=entry] (aor name.left name.right)))
  =/  previous=(unit @t)  ~
  =/  body=octets  [0 0]
  |-  ^-  object
  ?~  ordered  (make-object %tree body)
  ?^  previous
    ?>  !=(u.previous name.i.ordered)
    $(previous ~)
  =/  prefix=@t  (cat 3 '100644 ' name.i.ordered)
  =/  record=octets
    (append [(add 1 (met 3 prefix)) prefix] [20 (rev 3 20 oid.i.ordered)])
  $(ordered t.ordered, previous [~ name.i.ordered], body (append body record))
::
++  make-commit
  |=  [tree=@ux parent=(unit @ux) principal=@t timestamp=@ud document-id=@t revision=@ud]
  ^-  object
  ~|  %stead-git-commit
  ?>  (valid-uuid principal)
  ?>  (valid-uuid document-id)
  ?>  (gth revision 0)
  =/  tree-line=@t  (rap 3 ~['tree ' (oid-text tree) 10])
  =/  parent-line=@t
    ?~  parent  ''
    (rap 3 ~['parent ' (oid-text u.parent) 10])
  =/  identity=@t
    (rap 3 ~['Stead Fixture <' principal '@stead.invalid> ' (decimal timestamp) ' +0000' 10])
  =/  content=@t
    (rap 3 ~[tree-line parent-line 'author ' identity 'committer ' identity 10 'Save ' document-id ' revision ' (decimal revision) 10])
  (make-object %commit [(met 3 content) content])
--

=/  stead-code-git-objects
::  Original pure code-Git byte helpers. No graph validation or acceptance.
::  Reuses the already implemented exact-byte SHA-1 document constructors.
|%
+$  octets  octets:stead-git
+$  object  object:stead-git
::  Compute the canonical OID without changing body bytes or author text.
::  A successful hash is not proof that a tree/commit/tag body is well formed.
++  hash-object
  |=  [kind=@tas body=octets]
  ^-  (unit object)
  ?.  (valid-octets:stead-git body)  ~
  ?.  ?|  =(%blob kind)  =(%tree kind)  =(%commit kind)  =(%tag kind)
      ==
    ~
  ?.  =(%tag kind)  [~ (make-object:stead-git kind body)]
  =/  header=@t  (cat 3 'tag ' (decimal:stead-git length.body))
  =/  raw=octets  (append:stead-git [(add 1 (met 3 header)) header] body)
  [~ kind body (sha-1l:sha [length.raw (rev 3 length.raw data.raw)])]
::  Protocol SHA-1 spelling. Zero is parsed, but remains a create/delete
::  sentinel at the later ref-command layer; it is not an existing object.
++  parse-oid
  |=  text=octets
  ^-  (unit @ux)
  ?.  &(=(40 length.text) (lte (met 3 data.text) 40))  ~
  =/  index=@ud  0
  =/  result=@ux  0x0
  |-  ^-  (unit @ux)
  ?:  =(40 index)  [~ result]
  =/  byte=@ud  (cut 3 [index 1] data.text)
  =/  digit=(unit @ud)
    ?:  &((gte byte 48) (lte byte 57))  [~ (sub byte 48)]
    ?:  &((gte byte 97) (lte byte 102))  [~ (add 10 (sub byte 97))]
    ~
  ?~  digit  ~
  $(index +(index), result (add (mul result 16) u.digit))
::  Full refs/ names only, at most 1,024 bytes. No case folding, Unicode,
::  path or slash normalization. HEAD belongs to a future symbolic-ref layer.
++  valid-ref
  |=  name=octets
  ^-  ?
  ?.  ?&  (gte length.name 6)
          (lte length.name 1.024)
          (lte (met 3 data.name) length.name)
          =('refs/' (cut 3 [0 5] data.name))
      ==
    %.n
  ?:  =(46 (cut 3 [(dec length.name) 1] data.name))  %.n
  =/  index=@ud  0
  =/  start=@ud  0
  =/  previous=@ud  0
  |-  ^-  ?
  ?:  =(index length.name)
    ?.  (gth index start)  %.n
    ?.  (gte (sub index start) 5)  %.y
    !=('.lock' (cut 3 [(sub index 5) 5] data.name))
  =/  byte=@ud  (cut 3 [index 1] data.name)
  ?:  ?|  (lte byte 32)  =(byte 127)  =(byte 126)  =(byte 94)
          =(byte 58)  =(byte 63)  =(byte 42)  =(byte 91)  =(byte 92)
          &(=(byte 46) =(previous 46))
          &(=(byte 123) =(previous 64))
          &(=(index start) =(byte 46))
      ==
    %.n
  ?:  =(47 byte)
    ?.  (gth index start)  %.n
    ?:  &((gte (sub index start) 5) =('.lock' (cut 3 [(sub index 5) 5] data.name)))  %.n
    $(index +(index), start +(index), previous byte)
  $(index +(index), previous byte)
--

=/  stead-code-git-pack
::  Original bounded SHA-1 pack envelope inspection, without decompression.
::  %envelope proves the header/trailer only, never object validity or trust.
|%
+$  octets  [length=@ud data=@]
+$  result
  $%  [%envelope version=@ud declared=@ud entries-length=@ud checksum=@ux]
      [%invalid reason=@tas]
  ==
++  inspect
  |=  pack=octets
  ^-  result
  ?.  ?&  (lte length.pack 8.388.608)
          (lte (met 3 data.pack) length.pack)
      ==
    [%invalid %byte-bound]
  ?:  (lth length.pack 32)  [%invalid %truncated-envelope]
  ?.  =('PACK' (cut 3 [0 4] data.pack))  [%invalid %signature]
  =/  version=@ud  (rev 3 4 (cut 3 [4 4] data.pack))
  ?.  ?|(=(2 version) =(3 version))  [%invalid %version]
  =/  count=@ud  (rev 3 4 (cut 3 [8 4] data.pack))
  ?:  (gth count 4.096)  [%invalid %object-count]
  =/  entries=@ud  (sub length.pack 32)
  ?:  &(=(0 count) !=(0 entries))  [%invalid %empty-pack-payload]
  ?:  &((gth count 0) =(0 entries))  [%invalid %missing-entries]
  =/  hashed-length=@ud  (sub length.pack 20)
  =/  expected=@ux  (rev 3 20 (cut 3 [hashed-length 20] data.pack))
  =/  observed=@ux
    (sha-1l:sha [hashed-length (rev 3 hashed-length (cut 3 [0 hashed-length] data.pack))])
  ?.  =(expected observed)  [%invalid %checksum]
  [%envelope version count entries observed]
--

=/  stead-code-git-emit
::  Original bounded SHA-1 pack writer. Stored DEFLATE only; exact bytes.
::  The caller chooses an authorized graph. Encoding grants no read access.
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

=,  test
=>
::  Literal vectors derive independently from RFC 1950/1951 and SHA-1.
|%
++  object
  |=  [kind=@tas body=octets:stead-code-git-emit]
  ^-  object:stead-code-git-emit
  (need (hash-object:stead-code-git-objects kind body))
++  bytes
  |=  value=@t
  ^-  octets:stead-code-git-emit
  [(met 3 value) value]
++  metadata
  |=  count=@ud
  ^-  (list object:stead-code-git-emit)
  =/  out=(list object:stead-code-git-emit)  ~
  |-  ^-  (list object:stead-code-git-emit)
  ?:  =(0 count)  out
  =/  oid=@ux  (add count 0)
  $(count (dec count), out [[%blob [0 0] oid] out])
++  fixture
  ^-  (list object:stead-code-git-emit)
  =/  blob  (object %blob [3 97])
  =/  tree  (object %tree [0 0])
  =/  commit-text=@t
    (rap 3 ~['tree ' (oid-text:stead-git oid.tree) 10 'author Fixture <fixture@example.invalid> 0 +0000' 10 'committer Fixture <fixture@example.invalid> 0 +0000' 10 10 'Synthetic pack fixture' 10])
  =/  commit  (object %commit (bytes commit-text))
  =/  tag-text=@t
    (rap 3 ~['object ' (oid-text:stead-git oid.commit) 10 'type commit' 10 'tag v1' 10 'tagger Fixture <fixture@example.invalid> 0 +0000' 10 10 'Synthetic annotated tag' 10])
  ~[blob tree commit (object %tag (bytes tag-text))]
::  Optional driver vector: exact emitted pack for independent stock Git.
++  interoperability
  ^-  octets:stead-code-git-emit
  =/  result  (encode:stead-code-git-emit fixture)
  ?>  ?=(%& -.result)
  p.result
++  test-emit-empty-pack
  (expect !>(=([%& 32 0x1ed3.3efd.3c82.5cc7.6aad.10b5.eaa8.d83b.8208.9d02.0000.0000.0200.0000.4b43.4150] (encode:stead-code-git-emit ~))))
++  test-emit-blob-golden
  =/  result  (encode:stead-code-git-emit ~[(object %blob [3 'abc'])])
  (expect !>(=([%& 47 0x53.aa97.6a94.c0cd.ed4d.68c0.7006.1356.07b2.105d.1527.014d.0263.6261.fffc.0003.0101.7833.0100.0000.0200.0000.4b43.4150] result)))
++  test-emit-ordinary-kinds
  =/  value  interoperability
  =/  envelope  (inspect:stead-code-git-pack value)
  ?>  ?=(%envelope -.envelope)
  (expect !>(=(4 declared.envelope)))
++  test-emit-deterministic-order
  =/  first  (encode:stead-code-git-emit fixture)
  =/  second  (encode:stead-code-git-emit fixture)
  =/  reversed  (encode:stead-code-git-emit (flop fixture))
  (expect !>(&(=(first second) !=(first reversed))))
++  test-emit-reject-declared-hash
  (expect !>(=([%| %oid-mismatch] (encode:stead-code-git-emit ~[[%blob [3 'abc'] 0x1]]))))
++  test-emit-reject-wide-oid
  (expect !>(=([%| %oid-bound] (encode:stead-code-git-emit ~[[%blob [0 0] (bex 160)]]))))
++  test-emit-reject-duplicate
  =/  item  (object %blob [0 0])
  (expect !>(=([%| %duplicate-object] (encode:stead-code-git-emit ~[item item]))))
++  test-emit-reject-kind
  (expect !>(=([%| %unsupported-kind] (encode:stead-code-git-emit ~[[%ofs-delta [0 0] 0x1]]))))
++  test-emit-reject-body-width
  (expect !>(=([%| %object-bound] (encode:stead-code-git-emit ~[[%blob [0 1] 0x1]]))))
++  test-emit-reject-body-bound
  (expect !>(=([%| %object-bound] (encode:stead-code-git-emit ~[[%blob [8.388.609 0] 0x1]]))))
++  test-emit-count-at-bound
  (expect !>(=([%& 4.096 49.184] (admit:stead-code-git-emit (metadata 4.096)))))
++  test-emit-count-over-bound
  (expect !>(=([%| %object-count] (admit:stead-code-git-emit (metadata 4.097)))))
++  test-emit-size-at-bound
  (expect !>(=([%& 1 8.388.608] (admit:stead-code-git-emit ~[[%blob [8.387.926 0] 0x1]]))))
++  test-emit-size-over-bound
  (expect !>(=([%| %pack-bound] (admit:stead-code-git-emit ~[[%blob [8.387.927 0] 0x1]]))))
++  test-emit-header-empty-kinds
  =/  valid=?
    ?&  =([%& 1 0x10] (header:stead-code-git-emit %commit 0))
        =([%& 1 0x20] (header:stead-code-git-emit %tree 0))
        =([%& 1 0x30] (header:stead-code-git-emit %blob 0))
        =([%& 1 0x40] (header:stead-code-git-emit %tag 0))
    ==
  (expect !>(valid))
++  test-emit-header-first-boundary
  (expect !>(&(=([%& 1 0x3f] (header:stead-code-git-emit %blob 15)) =([%& 2 0x1b0] (header:stead-code-git-emit %blob 16)))))
++  test-emit-header-next-boundary
  (expect !>(&(=([%& 2 0x7fbf] (header:stead-code-git-emit %blob 2.047)) =([%& 3 0x1.80b0] (header:stead-code-git-emit %blob 2.048)))))
++  test-emit-header-size-bound
  (expect !>(&(=([%& 4 0x2080.80b0] (header:stead-code-git-emit %blob 8.388.608)) =([%| %object-bound] (header:stead-code-git-emit %blob 8.388.609)))))
++  test-emit-adler-empty
  (expect !>(=([%& 1] (adler:stead-code-git-emit [0 0]))))
++  test-emit-adler-known
  (expect !>(=([%& 0x11e6.0398] (adler:stead-code-git-emit [9 'Wikipedia']))))
++  test-emit-adler-width
  (expect !>(=([%| %object-bound] (adler:stead-code-git-emit [0 1]))))
++  test-emit-zlib-empty
  (expect !>(=([%& 11 0x1.0000.00ff.ff00.0001.0178] (stored:stead-code-git-emit [0 0]))))
++  test-emit-zlib-literal
  (expect !>(=([%& 14 0x2701.4d02.6362.61ff.fc00.0301.0178] (stored:stead-code-git-emit [3 'abc']))))
++  test-emit-zlib-trailing-zero
  (expect !>(=([%& 14 0x6200.2601.0000.61ff.fc00.0301.0178] (stored:stead-code-git-emit [3 97]))))
++  test-emit-zlib-all-zero
  (expect !>(=([%& 14 0x100.0300.0000.00ff.fc00.0301.0178] (stored:stead-code-git-emit [3 0]))))
++  test-emit-zlib-last-full-block
  =/  value  (stored:stead-code-git-emit [65.535 0])
  ?>  ?=(%& -.value)
  =/  valid=?
    ?&  =(65.546 length.p.value)
        =(0xff.ff01.0178 (cut 3 [0 7] data.p.value))
        =(0xe.0001 (rev 3 4 (cut 3 [65.542 4] data.p.value)))
    ==
  (expect !>(valid))
++  test-emit-zlib-split-block
  =/  value  (stored:stead-code-git-emit [65.536 0])
  ?>  ?=(%& -.value)
  =/  valid=?
    ?&  =(65.552 length.p.value)
        =(0xff.ff00.0178 (cut 3 [0 7] data.p.value))
        =(0xff.fe00.0101 (cut 3 [65.542 5] data.p.value))
        =(0 (cut 3 [65.547 1] data.p.value))
        =(0xf.0001 (rev 3 4 (cut 3 [65.548 4] data.p.value)))
    ==
  (expect !>(valid))
++  test-emit-zlib-over-bound
  (expect !>(=([%| %zlib-bound] (stored:stead-code-git-emit [8.388.608 0]))))
++  failure-control
  (expect !>(%.n))
--

^-  (list [@ta @ta])
:~  [(scot %tas %test-emit-empty-pack) (scot %ud (lent test-emit-empty-pack))]
    [(scot %tas %test-emit-blob-golden) (scot %ud (lent test-emit-blob-golden))]
    [(scot %tas %test-emit-ordinary-kinds) (scot %ud (lent test-emit-ordinary-kinds))]
    [(scot %tas %test-emit-deterministic-order) (scot %ud (lent test-emit-deterministic-order))]
    [(scot %tas %test-emit-reject-declared-hash) (scot %ud (lent test-emit-reject-declared-hash))]
    [(scot %tas %test-emit-reject-wide-oid) (scot %ud (lent test-emit-reject-wide-oid))]
    [(scot %tas %test-emit-reject-duplicate) (scot %ud (lent test-emit-reject-duplicate))]
    [(scot %tas %test-emit-reject-kind) (scot %ud (lent test-emit-reject-kind))]
    [(scot %tas %test-emit-reject-body-width) (scot %ud (lent test-emit-reject-body-width))]
    [(scot %tas %test-emit-reject-body-bound) (scot %ud (lent test-emit-reject-body-bound))]
    [(scot %tas %test-emit-count-at-bound) (scot %ud (lent test-emit-count-at-bound))]
    [(scot %tas %test-emit-count-over-bound) (scot %ud (lent test-emit-count-over-bound))]
    [(scot %tas %test-emit-size-at-bound) (scot %ud (lent test-emit-size-at-bound))]
    [(scot %tas %test-emit-size-over-bound) (scot %ud (lent test-emit-size-over-bound))]
    [(scot %tas %test-emit-header-empty-kinds) (scot %ud (lent test-emit-header-empty-kinds))]
    [(scot %tas %test-emit-header-first-boundary) (scot %ud (lent test-emit-header-first-boundary))]
    [(scot %tas %test-emit-header-next-boundary) (scot %ud (lent test-emit-header-next-boundary))]
    [(scot %tas %test-emit-header-size-bound) (scot %ud (lent test-emit-header-size-bound))]
    [(scot %tas %test-emit-adler-empty) (scot %ud (lent test-emit-adler-empty))]
    [(scot %tas %test-emit-adler-known) (scot %ud (lent test-emit-adler-known))]
    [(scot %tas %test-emit-adler-width) (scot %ud (lent test-emit-adler-width))]
    [(scot %tas %test-emit-zlib-empty) (scot %ud (lent test-emit-zlib-empty))]
    [(scot %tas %test-emit-zlib-literal) (scot %ud (lent test-emit-zlib-literal))]
    [(scot %tas %test-emit-zlib-trailing-zero) (scot %ud (lent test-emit-zlib-trailing-zero))]
    [(scot %tas %test-emit-zlib-all-zero) (scot %ud (lent test-emit-zlib-all-zero))]
    [(scot %tas %test-emit-zlib-last-full-block) (scot %ud (lent test-emit-zlib-last-full-block))]
    [(scot %tas %test-emit-zlib-split-block) (scot %ud (lent test-emit-zlib-split-block))]
    [(scot %tas %test-emit-zlib-over-bound) (scot %ud (lent test-emit-zlib-over-bound))]
    [(scot %tas %failure-control) (scot %ud (lent failure-control))]
==

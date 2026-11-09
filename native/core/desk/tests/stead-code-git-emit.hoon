/+  *test, stead-git, stead-code-git-objects, stead-code-git-pack, stead-code-git-emit
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

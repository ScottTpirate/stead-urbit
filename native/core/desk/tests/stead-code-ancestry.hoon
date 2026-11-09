/+  *test, stead-code-ancestry, stead-code-git-objects, stead-git
=,  stead-code-ancestry
|%
++  make
  |=  [message=@t parents=(list @ux)]
  ^-  object:stead-git
  =/  newline=@t  `@t`10
  =/  parent-lines  (turn parents |=(parent=@ux (rap 3 ~['parent ' (oid-text:stead-git parent) newline])))
  =/  body=@t
    (rap 3 (weld ~['tree 4b825dc642cb6eb9a060e54bf8d69288fbee4904' newline] (weld parent-lines ~['author Test <test@example.invalid> 1 +0000' newline 'committer Test <test@example.invalid> 1 +0000' newline newline message newline])))
  (need (hash-object:stead-code-git-objects %commit [(met 3 body) body]))
++  first
  (make 'first' ~)
++  other
  (make 'other' ~)
++  child
  (make 'child' ~[oid:first])
++  merge
  (make 'merge' ~[oid:child oid:other])
++  blob
  (need (hash-object:stead-code-git-objects %blob [1 'x']))
++  view
  |=  oid=@ux
  ^-  (unit object:stead-git)
  ?:  =(oid oid:first)  [~ first]
  ?:  =(oid oid:other)  [~ other]
  ?:  =(oid oid:child)  [~ child]
  ?:  =(oid oid:merge)  [~ merge]
  ?:  =(oid oid:blob)  [~ blob]
  ::  Commit ancestry must never load the tree or any unselected object.
  !!
++  corrupt-view
  |=  oid=@ux
  ^-  (unit object:stead-git)
  [~ %commit [1 'x'] oid]
++  wrong-oid-view
  |=  oid=@ux
  ^-  (unit object:stead-git)
  [~ other]
++  missing-view
  |=  oid=@ux
  ^-  (unit object:stead-git)
  ~
++  close
  |=  [base=@ux tip=@ux]
  ^-  search
  =/  work  (begin base tip)
  =/  turn-count=@ud  0
  |-  ^-  search
  ?.  ?=(%walking -.work)  work
  ?:  =(turn-count 10)  [%invalid %fixture-bound]
  $(work (step work view), turn-count +(turn-count))
++  test-ancestry-identity
  (expect !>(=([%ancestor ~] (close oid:first oid:first))))
++  test-ancestry-parent
  (expect !>(=([%ancestor ~] (close oid:first oid:child))))
++  test-ancestry-grandparent
  (expect !>(=([%ancestor ~] (close oid:first oid:merge))))
++  test-ancestry-second-parent
  (expect !>(=([%ancestor ~] (close oid:other oid:merge))))
++  test-ancestry-diverged
  (expect !>(=([%diverged ~] (close oid:other oid:child))))
++  test-ancestry-reversed
  (expect !>(=([%diverged ~] (close oid:child oid:first))))
++  test-ancestry-tree-not-parent
  (expect !>(=([%diverged ~] (close 0x4b82.5dc6.42cb.6eb9.a060.e54b.f8d6.9288.fbee.4904 oid:first))))
++  test-ancestry-invalid-oid
  (expect !>(=([%invalid %object-oid] (begin 0x0 oid:first))))
++  test-ancestry-missing-commit
  (expect !>(=([%invalid %missing-commit] (step (begin oid:first oid:child) missing-view))))
++  test-ancestry-oid-mismatch
  (expect !>(=([%invalid %commit-kind] (step (begin oid:first oid:child) wrong-oid-view))))
++  test-ancestry-rehash
  (expect !>(=([%invalid %object-oid] (step (begin oid:first oid:first) corrupt-view))))
++  test-ancestry-blob-rejected
  (expect !>(=([%invalid %commit-kind] (close oid:blob oid:blob))))
++  test-ancestry-work-bound
  (expect !>(=([%invalid %ancestry-work-bound] (step [%walking oid:first ~[oid:child] ~ 1 0 100] missing-view))))
++  test-ancestry-byte-bound
  (expect !>(=([%invalid %ancestry-byte-bound] (step [%walking oid:first ~[oid:child] ~ 1 1 0] view))))
++  test-ancestry-queue-bound
  =/  todo  [oid:merge (reap 32.767 oid:child)]
  (expect !>(=([%invalid %ancestry-queue-bound] (step [%walking oid:other todo ~ 32.768 10 10.000] view))))
++  test-ancestry-terminal-stable
  (expect !>(=([%ancestor ~] (step [%ancestor ~] missing-view))))
++  failure-control
  (expect !>(%.n))
--

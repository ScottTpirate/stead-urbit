/+  *test, stead-code-receive
|%
++  initial
  ^-  refs:stead-code-receive
  (malt ~[['refs/heads/main' 0x1] ['refs/tags/v1' 0x2]])
++  allowed
  |=  [operation=action:stead-code-receive change=update:stead-code-receive]
  ^-  ?
  &
++  denied
  |=  [operation=action:stead-code-receive change=update:stead-code-receive]
  ^-  ?
  |
++  objects
  |=  oid=@ux
  ^-  (unit @tas)
  ?:  =(0 oid)  ~
  ?:  =(3 oid)  [~ %blob]
  ?:  (lte oid 2)  [~ %commit]
  ~
++  ancestor
  |=  [old=@ux new=@ux]
  ^-  ?
  =([0x1 0x2] [old new])
++  protect
  ^-  (set @t)
  (silt ~['refs/heads/main'])
++  check
  |=  [updates=(list update:stead-code-receive) reason=@tas]
  ^-  tang
  (expect !>(=([%| reason] (decide:stead-code-receive initial 1 1 updates protect allowed objects ancestor))))
++  test-ref-advance
  =/  current  (decide:stead-code-receive initial 1 1 ~[['refs/heads/main' 0x1 0x2]] protect allowed objects ancestor)
  ?>  ?=([%& *] current)
  (expect !>(=([~ 0x2] (~(get by p.current) 'refs/heads/main'))))
++  test-ref-competing-writes
  =/  proposal  ~[['refs/heads/main' 0x1 0x2]]
  =/  first  (decide:stead-code-receive initial 1 1 proposal protect allowed objects ancestor)
  ?>  ?=([%& *] first)
  (expect !>(=([%| %stale-ref] (decide:stead-code-receive p.first 1 1 proposal protect allowed objects ancestor))))
++  test-ref-revoked
  (expect !>(=([%| %denied] (decide:stead-code-receive initial 1 1 ~[['refs/heads/main' 0x1 0x2]] protect denied objects ancestor))))
++  test-ref-epoch
  (expect !>(=([%| %stale-epoch] (decide:stead-code-receive initial 2 1 ~[['refs/heads/main' 0x1 0x2]] protect allowed objects ancestor))))
++  test-ref-protected-delete
  (check ~[['refs/heads/main' 0x1 0x0]] %protected-ref)
++  test-ref-batch-rejects-stale-member
  (check ~[['refs/heads/main' 0x1 0x2] ['refs/heads/temp' 0x1 0x2]] %stale-ref)
++  test-ref-non-fast-forward
  =/  newer=refs:stead-code-receive  (~(put by initial) 'refs/heads/main' 0x2)
  (expect !>(=([%| %non-fast-forward] (decide:stead-code-receive newer 1 1 ~[['refs/heads/main' 0x2 0x1]] protect allowed objects ancestor))))
++  test-ref-namespace
  (check ~[['refs/heads/main/nested' 0x0 0x2]] %ref-conflict)
++  test-ref-duplicate
  (check ~[['refs/heads/new' 0x0 0x1] ['refs/heads/new' 0x0 0x2]] %duplicate-ref)
++  test-ref-bad-name
  (check ~[['refs/heads/../x' 0x0 0x1]] %invalid-ref)
++  test-ref-unsupported
  (check ~[['refs/notes/main' 0x0 0x1]] %unsupported-ref)
++  test-ref-tag-replacement
  (check ~[['refs/tags/v1' 0x2 0x1]] %tag-replacement)
++  test-ref-bad-target
  (check ~[['refs/heads/new' 0x0 0x3]] %wrong-object-kind)
++  test-ref-missing-target
  (check ~[['refs/heads/new' 0x0 0x4]] %missing-object)
++  test-ref-tag-and-branch-create
  =/  updates  ~[['refs/tags/v2' 0x0 0x3] ['refs/heads/new' 0x0 0x1]]
  =/  result  (decide:stead-code-receive initial 1 1 updates protect allowed objects ancestor)
  ?>  ?=([%& *] result)
  (expect !>(=([~ 0x3] (~(get by p.result) 'refs/tags/v2'))))
--

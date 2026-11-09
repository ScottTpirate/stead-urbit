/+  *test, stead-code-git-graph, stead-code-git-objects, stead-git
=,  stead-code-git-graph
|%
++  make
  |=  [kind=@tas content=octets]
  ^-  object
  (need (hash-object:stead-code-git-objects kind content))
++  blob
  (make %blob [4 'data'])
++  tree-row
  |=  [mode=@t name=@t oid=@ux]
  ^-  octets
  =/  prefix=@t  (rap 3 ~[mode ' ' name])
  =/  size=@ud  (add (met 3 prefix) 1)
  [(add size 20) (can 3 ~[[size prefix] [20 (rev 3 20 oid)]])]
++  leaf
  (make %tree (tree-row '100644' 'code.txt' oid:blob))
++  root-tree
  (make %tree (tree-row '40000' 'src' oid:leaf))
++  commit
  =/  data=@t
    (rap 3 ~['tree ' (oid-text:stead-git oid:root-tree) 10 'author A <a@example.invalid> 1700000000 +0000' 10 'committer B <b@example.invalid> 1700000000 +0000' 10 10 'A change' 10])
  (make %commit [(met 3 data) data])
++  tag
  =/  data=@t
    (rap 3 ~['object ' (oid-text:stead-git oid:commit) 10 'type commit' 10 'tag v1' 10 10])
  (make %tag [(met 3 data) data])
++  view
  |=  oid=@ux
  ^-  (unit object)
  ?:  =(oid oid:blob)  [~ blob]
  ?:  =(oid oid:leaf)  [~ leaf]
  ?:  =(oid oid:root-tree)  [~ root-tree]
  ?:  =(oid oid:commit)  [~ commit]
  ?:  =(oid oid:tag)  [~ tag]
  ~
++  close
  |=  roots=(list edge)
  ^-  closure
  =/  work  (start roots)
  =/  count=@ud  0
  |-  ^-  closure
  ?.  ?=(%checking -.work)  work
  ?:  =(count 20)  [%invalid %fixture-bound]
  $(work (walk work view), count +(count))
++  no-view
  |=  oid=@ux
  ^-  (unit object)
  ~
++  corrupt-view
  |=  oid=@ux
  ^-  (unit object)
  ?:  =(oid oid:blob)  [~ %blob [4 'evil'] oid]
  (view oid)
++  queued-work
  |=  count=@ud
  ^-  closure
  =/  pending=(list path-item)
    [[%visit oid:root-tree %tree] (reap (dec count) [%visit oid:blob %blob])]
  [%checking pending ~ ~ count 32.768 67.108.864]
++  test-graph-tree-exact-name
  =/  expected  [%& %tree ~[['code.txt' %file oid:blob %blob]]]
  (expect !>(=(expected (inspect leaf))))
++  test-graph-tree-malformed-name
  =/  invalid  (make %tree (tree-row '100644' '.GiT' oid:blob))
  (expect !>(=([%| %tree-name] (inspect invalid))))
++  test-graph-tree-unsupported-symlink
  =/  invalid  (make %tree (tree-row '120000' 'target' oid:blob))
  (expect !>(=([%| %tree-mode] (inspect invalid))))
++  test-graph-tree-duplicate
  =/  row  (tree-row '100644' 'a' oid:blob)
  =/  invalid  (make %tree (append:stead-git row row))
  (expect !>(=([%| %tree-duplicate] (inspect invalid))))
++  test-graph-tree-order
  =/  first  (tree-row '100644' 'z' oid:blob)
  =/  second  (tree-row '100644' 'a' oid:blob)
  =/  invalid  (make %tree (append:stead-git first second))
  (expect !>(=([%| %tree-order] (inspect invalid))))
++  test-graph-commit-tree
  (expect !>(=([%& %commit [oid:root-tree %tree] ~] (inspect commit))))
++  test-graph-tag-target
  (expect !>(=([%& %tag oid:commit %commit] (inspect tag))))
++  test-graph-closure
  =/  done  (close ~[[oid:tag %tag]])
  (expect !>(&(?=(%verified -.done) =(5 ~(wyt by reachable.done)))))
++  test-graph-closure-missing-object
  (expect !>(=([%invalid %missing-object] (close ~[[0x1 %commit]]))))
++  test-graph-closure-wrong-type
  (expect !>(=([%invalid %edge-kind] (close ~[[oid:blob %tree]]))))
++  test-graph-read-exact-commit
  =/  done  (close ~[[oid:commit %commit]])
  ?>  ?=(%verified -.done)
  (expect !>(=([%& blob] (read-path oid:commit ~['src' 'code.txt'] reachable.done view))))
++  test-graph-read-unreachable-object
  =/  done  (close ~[[oid:commit %commit]])
  ?>  ?=(%verified -.done)
  =/  blocked  (~(del by reachable.done) oid:blob)
  (expect !>(=([%| %unavailable] (read-path oid:commit ~['src' 'code.txt'] blocked view))))
++  test-graph-read-traversal
  (expect !>(=([%| %path-bound] (read-path oid:commit ~['..'] ~ view))))
++  test-graph-empty-closure
  (expect !>(=([%verified ~] (walk (start ~) view))))
++  test-graph-duplicate-roots
  =/  done  (close ~[[oid:tag %tag] [oid:tag %tag]])
  (expect !>(&(?=(%verified -.done) =(5 ~(wyt by reachable.done)))))
++  test-graph-visit-bound
  =/  work  (start ~[[oid:blob %blob]])
  ?>  ?=(%checking -.work)
  (expect !>(=([%invalid %graph-edge-bound] (walk work(visits 0) view))))
++  test-graph-byte-bound
  =/  work  (start ~[[oid:blob %blob]])
  ?>  ?=(%checking -.work)
  (expect !>(=([%invalid %graph-byte-bound] (walk work(bytes 3) view))))
++  test-graph-queue-state
  =/  work  (start ~[[oid:blob %blob]])
  ?>  ?=(%checking -.work)
  (expect !>(=([%invalid %graph-queue-state] (walk work(queued 0) view))))
++  test-graph-queue-bound
  (expect !>(=([%invalid %graph-queue-bound] (walk (queued-work 32.768) view))))
++  test-graph-queue-at-bound
  =/  work  (walk (queued-work 32.767) view)
  ?>  ?=(%checking -.work)
  (expect !>(=(32.768 queued.work)))
++  test-graph-oid-mismatch
  =/  value  blob
  (expect !>(=([%| %object-oid] (inspect value(oid 0x1)))))
++  test-graph-read-unreachable-revision
  =/  done  (close ~[[oid:commit %commit]])
  ?>  ?=(%verified -.done)
  =/  allowed  (~(del by reachable.done) oid:commit)
  (expect !>(=([%| %unavailable] (read-path oid:commit ~['src' 'code.txt'] allowed view))))
++  test-graph-read-unreachable-tree
  =/  done  (close ~[[oid:commit %commit]])
  ?>  ?=(%verified -.done)
  =/  allowed  (~(del by reachable.done) oid:root-tree)
  (expect !>(=([%| %unavailable] (read-path oid:commit ~['src' 'code.txt'] allowed view))))
++  test-graph-read-forbidden-loader
  =/  done  (close ~[[oid:commit %commit]])
  ?>  ?=(%verified -.done)
  (expect !>(=([%| %unavailable] (read-path oid:commit ~['src' 'code.txt'] reachable.done no-view))))
++  test-graph-read-corrupt-loader
  =/  done  (close ~[[oid:commit %commit]])
  ?>  ?=(%verified -.done)
  (expect !>(=([%| %unavailable] (read-path oid:commit ~['src' 'code.txt'] reachable.done corrupt-view))))
++  test-graph-read-directory
  =/  done  (close ~[[oid:commit %commit]])
  ?>  ?=(%verified -.done)
  (expect !>(=([%| %unavailable] (read-path oid:commit ~['src'] reachable.done view))))
++  test-graph-path-depth-bound
  (expect !>(=([%| %path-bound] (read-path oid:commit (reap 33 'src') ~ view))))
++  test-graph-root-bound
  (expect !>(=([%invalid %root-bound] (start (reap 257 [oid:commit %commit])))))
++  test-graph-executable-file
  =/  value  (make %tree (tree-row '100755' 'run' oid:blob))
  (expect !>(=([%& %tree ~[['run' %executable oid:blob %blob]]] (inspect value))))
--

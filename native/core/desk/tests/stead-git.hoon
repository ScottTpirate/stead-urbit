/+  *test, stead-git
::  Original object-format tests; stock Git independently checks exact bytes/OIDs.
|%
++  test-empty-blob
  =/  value  (make-blob:stead-git [0 0])
  (expect !>(=(0xe69d.e29b.b2d1.d643.4b8b.29ae.775a.d8c2.e48c.5391 oid.value)))
++  test-trailing-zero-blob
  =/  value  (make-blob:stead-git [2 97])
  (expect !>(=([%blob [2 97] 0x9080.2fed.c246.2f10.bf21.14d0.86ca.cb9e.3af9.9ffb] value)))
++  test-all-zero-blob
  =/  value  (make-blob:stead-git [2 0])
  (expect !>(=([%blob [2 0] 0x9f3.70e3.8f49.8a46.2e1c.a0fa.a724.559b.6630.c04f] value)))
++  test-blob-width-rejected
  (expect-fail-message 'stead-git-object' |.((make-blob:stead-git [0 1])))
++  test-object-kind-rejected
  (expect-fail-message 'stead-git-object' |.((make-object:stead-git %tag [0 0])))
++  test-empty-tree
  =/  value  (make-tree:stead-git ~)
  (expect !>(=(0x4b82.5dc6.42cb.6eb9.a060.e54b.f8d6.9288.fbee.4904 oid.value)))
++  test-tree-byte-order
  =/  first=entry:stead-git  ['019939ba-4000-7000-8000-000000000002.md' 0x1]
  =/  second=entry:stead-git  ['019939bb-4000-7000-8000-000000000001.md' 0x2]
  (expect !>(=((make-tree:stead-git ~[first second]) (make-tree:stead-git ~[second first]))))
++  test-tree-duplicate-rejected
  =/  item=entry:stead-git  ['019939ba-4000-7000-8000-000000000002.md' 0x1]
  (expect-fail-message 'stead-git-tree' |.((make-tree:stead-git ~[item item])))
++  test-tree-path-rejected
  (expect-fail-message 'stead-git-tree' |.((make-tree:stead-git ~[['../outside.md' 0x1]])))
++  test-tree-uppercase-rejected
  (expect-fail-message 'stead-git-tree' |.((make-tree:stead-git ~[['019939BA-4000-7000-8000-000000000002.md' 0x1]])))
++  test-tree-uuid-version-rejected
  (expect-fail-message 'stead-git-tree' |.((make-tree:stead-git ~[['019939ba-4000-4000-8000-000000000002.md' 0x1]])))
++  test-tree-oid-width-rejected
  (expect-fail-message 'stead-git-tree' |.((make-tree:stead-git ~[['019939ba-4000-7000-8000-000000000002.md' (bex 160)]])))
++  test-tree-at-bound
  =/  value  (make-tree:stead-git (many-entries 32))
  (expect !>(=(2.144 length.body.value)))
++  test-tree-over-bound-rejected
  (expect-fail-message 'stead-git-tree' |.((make-tree:stead-git (many-entries 33))))
++  test-oid-leading-zero-padding
  (expect !>(=('0000000000000000000000000000000000000001' (oid-text:stead-git 0x1))))
++  test-commit-no-parent
  =/  value  (make-commit:stead-git 0x4b82.5dc6.42cb.6eb9.a060.e54b.f8d6.9288.fbee.4904 ~ '019939ba-4000-7000-8000-000000000102' 1.789.171.200 '019939ba-4000-7000-8000-000000000002' 1)
  (expect !>(=(0x7819.726c.df00.caeb.7522.1b52.7f7d.5d18.eefa.5a6d oid.value)))
++  test-commit-invalid-principal-rejected
  (expect-fail-message 'stead-git-commit' |.((make-commit:stead-git 0x1 ~ 'forged' 1 '019939ba-4000-7000-8000-000000000002' 1)))
++  test-commit-zero-revision-rejected
  (expect-fail-message 'stead-git-commit' |.((make-commit:stead-git 0x1 ~ '019939ba-4000-7000-8000-000000000102' 1 '019939ba-4000-7000-8000-000000000002' 0)))
++  test-commit-parent-width-rejected
  (expect-fail-message 'stead-git-oid' |.((make-commit:stead-git 0x1 [~ (bex 160)] '019939ba-4000-7000-8000-000000000102' 1 '019939ba-4000-7000-8000-000000000002' 1)))
++  test-commit-time-overflow-rejected
  (expect-fail-message 'stead-git-number' |.((make-commit:stead-git 0x1 ~ '019939ba-4000-7000-8000-000000000102' 18.446.744.073.709.551.616 '019939ba-4000-7000-8000-000000000002' 1)))
::  Explicitly invoked failing control; excluded from -test discovery.
++  failure-control
  (expect !>(%.n))
++  many-entries
  |=  count=@ud
  ^-  (list entry:stead-git)
  %+  turn  (gulf 1 count)
  |=  number=@ud
  ^-  entry:stead-git
  =/  suffix=@t  (cut 3 [28 12] (oid-text:stead-git `@ux`number))
  [(cat 3 '019939ba-4000-7000-8000-' (cat 3 suffix '.md')) 0x1]
--

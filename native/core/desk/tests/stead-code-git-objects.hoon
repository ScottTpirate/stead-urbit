/+  *test, stead-code-git-objects
|%
++  test-object-empty-blob
  =/  value  (hash-object:stead-code-git-objects %blob [0 0])
  ?>  ?=(^ value)
  (expect !>(=(0xe69d.e29b.b2d1.d643.4b8b.29ae.775a.d8c2.e48c.5391 oid.u.value)))
++  test-object-trailing-zero
  =/  value  (hash-object:stead-code-git-objects %blob [2 97])
  ?>  ?=(^ value)
  (expect !>(=([2 97] body.u.value)))
++  test-object-tag-exact-bytes
  =/  value  (hash-object:stead-code-git-objects %tag [2 97])
  ?>  ?=(^ value)
  (expect !>(=([%tag [2 97]] [kind.u.value body.u.value])))
++  test-object-kind-rejected
  (expect !>(=(~ (hash-object:stead-code-git-objects %invalid [0 0]))))
++  test-object-width-rejected
  (expect !>(=(~ (hash-object:stead-code-git-objects %blob [0 1]))))
++  test-object-bound-rejected
  (expect !>(=(~ (hash-object:stead-code-git-objects %blob [8.388.609 0]))))
++  test-oid-zero
  (expect !>(=([~ 0x0] (parse-oid:stead-code-git-objects [40 '0000000000000000000000000000000000000000']))))
++  test-oid-leading-zero
  (expect !>(=([~ 0x1] (parse-oid:stead-code-git-objects [40 '0000000000000000000000000000000000000001']))))
++  test-oid-full-width
  (expect !>(=([~ (dec (bex 160))] (parse-oid:stead-code-git-objects [40 'ffffffffffffffffffffffffffffffffffffffff']))))
++  test-oid-uppercase-rejected
  (expect !>(=(~ (parse-oid:stead-code-git-objects [40 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF']))))
++  test-oid-short-rejected
  (expect !>(=(~ (parse-oid:stead-code-git-objects [39 '000000000000000000000000000000000000000']))))
++  test-oid-nul-rejected
  (expect !>(=(~ (parse-oid:stead-code-git-objects [40 0]))))
++  test-ref-valid
  (expect !>(=(%.y (valid-ref:stead-code-git-objects [15 'refs/heads/main']))))
++  test-ref-head-rejected
  (expect !>(=(%.n (valid-ref:stead-code-git-objects [4 'HEAD']))))
++  test-ref-leading-dot-rejected
  (expect !>(=(%.n (valid-ref:stead-code-git-objects [17 'refs/heads/.local']))))
++  test-ref-lock-component-rejected
  (expect !>(=(%.n (valid-ref:stead-code-git-objects [17 'refs/a.lock/child']))))
++  test-ref-nul-rejected
  (expect !>(=(%.n (valid-ref:stead-code-git-objects [16 'refs/heads/main']))))
++  test-ref-bound-rejected
  (expect !>(=(%.n (valid-ref:stead-code-git-objects [1.025 'refs/heads/main']))))
--

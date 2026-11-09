/+  *test, stead-code-upload
|%
++  scope
  ^-  scope:stead-code-upload
  [~zod '018f0000-0000-7000-8000-000000000001' '018f0000-0000-7000-8000-000000000001' 1]
++  owner
  ^-  actor:stead-code-upload
  [~bus '018f0000-0000-7000-8000-000000000002' '018f0000-0000-7000-8000-000000000003' 1 & 800.000]
++  test-upload-rebind-exact-job
  =/  first  (stage:stead-code-upload ~ scope owner [4 'PACK'] 1 '018f0000-0000-7000-8000-000000000001')
  ?>  ?=(%& -.first)
  =/  second  (stage:stead-code-upload next.p.first scope owner [4 'PACK'] 2 '018f0000-0000-7000-8000-000000000002')
  (expect !>(=([%& p.first] second)))
++  test-upload-key-binds-trailing-zero-and-epoch
  =/  left  (key:stead-code-upload scope owner [4 'PACK'])
  =/  padded  (key:stead-code-upload scope owner [5 'PACK'])
  =/  prior=scope:stead-code-upload  scope
  =/  moved  (key:stead-code-upload prior(epoch 2) owner [4 'PACK'])
  (expect !>(&(!=(left padded) !=(left moved))))
++  test-upload-key-binds-member-revision
  =/  first  (key:stead-code-upload scope owner [4 'PACK'])
  =/  prior=actor:stead-code-upload  owner
  =/  second  (key:stead-code-upload scope prior(revision 2) [4 'PACK'])
  (expect !>(!=(first second)))
++  test-upload-key-ignores-expiry
  =/  prior=actor:stead-code-upload  owner
  (expect !>(=((key:stead-code-upload scope owner [4 'PACK']) (key:stead-code-upload scope prior(expires 2.000) [4 'PACK']))))
++  test-upload-rejects-oversize-and-inconsistent-width
  =/  large  (stage:stead-code-upload ~ scope owner [65.537 'PACK'] 1 '018f0000-0000-7000-8000-000000000001')
  =/  short  (stage:stead-code-upload ~ scope owner [3 'PACK'] 1 '018f0000-0000-7000-8000-000000000001')
  (expect !>(&(?=([%| %invalid-upload] large) ?=([%| %invalid-upload] short))))
++  test-upload-expired-rows-pruned
  =/  first  (stage:stead-code-upload ~ scope owner [4 'PACK'] 1 '018f0000-0000-7000-8000-000000000001')
  ?>  ?=(%& -.first)
  =/  next  (trim:stead-code-upload next.p.first 300.001)
  (expect !>(=(~ next)))
++  test-upload-saved-key-is-recomputed
  =/  first  (stage:stead-code-upload ~ scope owner [4 'PACK'] 1 '018f0000-0000-7000-8000-000000000001')
  ?>  ?=(%& -.first)
  =/  row  (~(got by next.p.first) key.p.first)
  =/  forged  (~(put by next.p.first) key.p.first row(wire [4 'FORK']))
  (expect !>(&((valid:stead-code-upload next.p.first) !(valid:stead-code-upload forged))))
++  test-upload-one-actor-cannot-fill-home
  =/  first  (stage:stead-code-upload ~ scope owner [4 'PACK'] 1 '018f0000-0000-7000-8000-000000000001')
  ?>  ?=(%& -.first)
  =/  second  (stage:stead-code-upload next.p.first scope owner [4 'FORK'] 2 '018f0000-0000-7000-8000-000000000002')
  ?>  ?=(%& -.second)
  =/  third  (stage:stead-code-upload next.p.second scope owner [4 'STOP'] 3 '018f0000-0000-7000-8000-000000000003')
  (expect !>(?=([%| %upload-capacity] third)))
++  failure-control
  (expect !>(%.n))
--

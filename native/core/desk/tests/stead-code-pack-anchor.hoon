/+  *test, stead-codec, stead-code-pack-anchor, stead-session
=,  stead-code-pack-anchor
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  request=@t  '019939ba-4000-7000-8000-000000000004'
=/  destination=scope  [~zod project project 1]
=/  who=actor:stead-session
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 1 & 2.000.000]
=/  expected=@t  'd0644338c8d3e787eefe9b23c7ee213d2cc8e451ec64b993b184afc1f2a0208a'
=/  pack=manifest
  :*  destination  expected  '726566732f68656164732f31'
      %-  malt
      :-  ['726566732f746167732f76' 'dddddddddddddddddddddddddddddddddddddddd']
      %+  turn  (gulf 1 17)
      |=  number=@ud
      [(bytes-hex:stead-codec (cat 3 'refs/heads/' (decimal:stead-codec number))) 'cccccccccccccccccccccccccccccccccccccccc']
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'  400
      7.000  700.000  'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
  ==
=/  wire=@t
  =/  flat
    %-  object:stead-codec
    :~  ['protocol' 'stead.code-pack-attestation/1']
        ['home' '~zod']
        ['project_id' project]
        ['repository_id' project]
        ['authority_epoch' '1']
        ['snapshot' expected]
        ['head' head.pack]
        ['pack_sha256' pack-sha.pack]
        ['pack_bytes' '400']
        ['object_count' '7000']
        ['object_bytes' '700000']
        ['object_ids_sha256' ids-sha.pack]
    ==
  ?>  ?=([%o *] flat)
  (canonical:stead-codec [%o (~(put by p.flat) 'refs' (object:stead-codec ~(tap by refs.pack)))])
=/  staged  (stage ~ pack ~zod 1)
?>  ?=(%& -.staged)
=/  ready  next.p.staged
|%
++  test-pack-anchor-stock-manifest-digest
  (expect !>(&((valid-manifest pack) =(18 ~(wyt by refs.pack)) =(pack (decode wire)))))
++  test-pack-anchor-stage-owner-and-digest
  (expect !>(&(?=([%| %pack-attestation-invalid] (stage ~ pack ~nec 1)) !(valid-manifest pack(objects 7.001)) !(valid-manifest pack(head '726566732f746167732f31')))))
++  test-pack-anchor-accept-and-retry
  =/  accepted  (accept ready destination who 3 2 expected request |)
  ?>  ?=(%& -.accepted)
  ?>  ?=(%accepted -.row.p.accepted)
  =/  saved=state  (state (cue (jam next.p.accepted)))
  (expect !>(&((valid row.p.accepted) =(next.p.accepted saved) =([%& p.accepted] (accept saved destination who 3 3 expected request |)))))
++  test-pack-anchor-accept-fences
  =/  digest  'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'
  (expect !>(&(?=([%| %denied-or-not-found] (accept ready destination who 2 2 expected request |)) ?=([%| %authority-epoch-conflict] (accept ready destination(epoch 2) who 3 2 expected request |)) ?=([%| %pack-snapshot-conflict] (accept ready destination who 3 2 digest request |)) ?=([%| %inline-repository-exists] (accept ready destination who 3 2 expected request &)) ?=([%| %pack-unavailable] (accept ready destination who 3 900.001 expected request |)))))
++  test-pack-anchor-revoked-retry-and-immutable
  =/  accepted  (accept ready destination who 3 2 expected request |)
  ?>  ?=(%& -.accepted)
  =/  saved  next.p.accepted
  (expect !>(&(?=([%| %denied-or-not-found] (accept saved destination who 0 3 expected request |)) ?=([%| %pack-already-accepted] (accept saved destination who(revision 2) 3 3 expected request |)) ?=([%| %pack-already-accepted] (stage saved pack ~zod 3)))))
--

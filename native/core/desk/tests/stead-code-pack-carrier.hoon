/+  *test, stead-code-pack-carrier, stead-code-pack-control, stead-code-pack-anchor, stead-code-pack-proof, stead-code-credentials, stead-code-pack-ledger, stead-code-receive
=,  stead-code-pack-carrier
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  destination=scope:stead-code-credentials  [~zod project project 1]
=/  current=manifest
  :*  destination  'a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af'
      '726566732f68656164732f6d61696e'  (malt ~[['726566732f68656164732f6d61696e' '07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc']])
      '960476b9a1028ebf443621355100782660490b3da12c3b17979988d17abf5a88'  164  2  189
      '28b0737ef6149aea47c58298976ca9e413a69a2522f900a23618e8e3e382c66e'
  ==
::  Python canonical admissions and worker proofs, produced using pinned Git.
=/  admitted-1=@t
  (cat 3 '{"actor":{"binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"3","identity_ship":"~bus","principal_id":"019939ba-4000-7000-8000-000000000002"},"admitted_at_ms":"1000","attempt":"1","base_snapshot":"a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af","changes":{"00":{"prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f65786163742dff","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc"}},"expires_at_ms":"301000","generation":"0","incarnation":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","protocol":"stead.git-pack-admission/1","request_id":"019939ba-4000-7000-8000-000000000004","scope":{"authority_epoch":"1","home":"~zod","project_id":"019939ba-4000-7000-8000-000000000001","repository_id":"019939ba-4000-7000-8000-000000000001"},"update_count":"1","wire_sha256":"0a795defdcee0d36429e71c162e273934cec59f4eea4302fa098fb528af568eb"}' 10)
=/  proof-1=@t
  (cat 3 '{"actor":{"binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"3","identity_ship":"~bus","principal_id":"019939ba-4000-7000-8000-000000000002"},"admission_sha256":"3bf5be5f85f0cc03132f9da6666e854548d6c3915e9507be23aa4eb36cf73972","admitted_at_ms":"1000","attempt":"1","base_snapshot":"a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af","candidate_snapshot":"4daa4e155c8f9d48ec82f89c1c7827380714cf549afad6804a1f2367f099a12f","expires_at_ms":"301000","generation":"0","head":"726566732f68656164732f6d61696e","incarnation":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","pack":{"object_bytes":"189","object_count":"2","object_ids_sha256":"28b0737ef6149aea47c58298976ca9e413a69a2522f900a23618e8e3e382c66e","pack_bytes":"164","pack_sha256":"960476b9a1028ebf443621355100782660490b3da12c3b17979988d17abf5a88"},"protocol":"stead.git-pack-worker-proof/1","request_id":"019939ba-4000-7000-8000-000000000004","scope":{"authority_epoch":"1","home":"~zod","project_id":"019939ba-4000-7000-8000-000000000001","repository_id":"019939ba-4000-7000-8000-000000000001"},"update_count":"1","updates":{"00":{"kind":"commit","lineage":"none","prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f65786163742dff","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc"}},"wire_sha256":"0a795defdcee0d36429e71c162e273934cec59f4eea4302fa098fb528af568eb"}' 10)
=/  msg-1=input  [%admit '019939ba-4000-7000-8000-000000000004' admitted-1 (hash-wire:stead-code-pack-proof admitted-1) ~]
=/  admitted-2=@t
  (cat 3 '{"actor":{"binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"3","identity_ship":"~bus","principal_id":"019939ba-4000-7000-8000-000000000002"},"admitted_at_ms":"1100","attempt":"2","base_snapshot":"4daa4e155c8f9d48ec82f89c1c7827380714cf549afad6804a1f2367f099a12f","changes":{"00":{"prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f7365636f6e64","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc"}},"expires_at_ms":"301100","generation":"1","incarnation":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","protocol":"stead.git-pack-admission/1","request_id":"019939ba-4000-7000-8000-000000000005","scope":{"authority_epoch":"1","home":"~zod","project_id":"019939ba-4000-7000-8000-000000000001","repository_id":"019939ba-4000-7000-8000-000000000001"},"update_count":"1","wire_sha256":"1bf2f8398b1f3e8d6c18c0a0ff1cdff0f2a4c40cb5f6eea8d5ea584abce99a1e"}' 10)
=/  proof-2=@t
  (cat 3 '{"actor":{"binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"3","identity_ship":"~bus","principal_id":"019939ba-4000-7000-8000-000000000002"},"admission_sha256":"4b032b68788746d080eaff95e4180172f3fbd93273bc6aee354450f7b0f16613","admitted_at_ms":"1100","attempt":"2","base_snapshot":"4daa4e155c8f9d48ec82f89c1c7827380714cf549afad6804a1f2367f099a12f","candidate_snapshot":"2b5fc025fadf2d4ade709ba3f40f06c96bf5bb8bc86b5bdf134f6efc8dca8969","expires_at_ms":"301100","generation":"1","head":"726566732f68656164732f6d61696e","incarnation":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","pack":{"object_bytes":"189","object_count":"2","object_ids_sha256":"28b0737ef6149aea47c58298976ca9e413a69a2522f900a23618e8e3e382c66e","pack_bytes":"164","pack_sha256":"960476b9a1028ebf443621355100782660490b3da12c3b17979988d17abf5a88"},"protocol":"stead.git-pack-worker-proof/1","request_id":"019939ba-4000-7000-8000-000000000005","scope":{"authority_epoch":"1","home":"~zod","project_id":"019939ba-4000-7000-8000-000000000001","repository_id":"019939ba-4000-7000-8000-000000000001"},"update_count":"1","updates":{"00":{"kind":"commit","lineage":"none","prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f7365636f6e64","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc"}},"wire_sha256":"1bf2f8398b1f3e8d6c18c0a0ff1cdff0f2a4c40cb5f6eea8d5ea584abce99a1e"}' 10)
=/  msg-2=input  [%admit '019939ba-4000-7000-8000-000000000005' admitted-2 (hash-wire:stead-code-pack-proof admitted-2) ~]
=/  owner=actor
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 3 & 2.000.000]
=/  seed=anchor  [%accepted [current ~zod 1 900.001] ['019939ba-4000-7000-8000-000000000006' owner 2]]
=/  members=membership:stead-code-credentials
  |=  ship=@p
  ^-  (unit actor)
  ?.  =(ship ship.owner)  ~
  [~ owner]
=/  allow=allowance:stead-code-credentials  |=([actor scope:stead-code-credentials access:stead-code-credentials] &)
=/  issued  (issue:stead-code-credentials *ledger:stead-code-credentials owner destination & 1.900.000 1.000 42 allow)
?>  ?=(%& -.issued)
=/  credential  bearer.p.issued
=/  worker=worker-check:stead-code-pack-control
  |=  [row=admission:stead-code-pack-ledger proof=checked:stead-code-pack-ledger]
  (proof-matches:stead-code-pack-ledger claim.row proof)
=/  gate=context
  :*  destination  1.000  'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
      &  |  |  next.p.issued  members  allow
      |=([action:stead-code-receive update:stead-code-pack-ledger] &)
      ~  worker
  ==
|%
++  first
  ^-  state-ledger
  =/  a  (apply ~ seed gate credential msg-1)
  ?>  ?=([%pending %applied *] a)
  =/  v  (apply [~ next.result.a] seed gate(now 1.001) credential msg-1(step %verify, proof [~ proof-1]))
  ?>  ?=([%pending %applied *] v)
  =/  c  (apply [~ next.result.v] seed gate(now 1.002) credential msg-1(step %commit, proof [~ proof-1]))
  ?>  ?=([%committed %applied *] c)
  next.result.c
++  second
  ^-  state-ledger
  =/  a  (apply [~ first] seed gate(now 1.100) credential msg-2)
  ?>  ?=([%pending %applied *] a)
  =/  v  (apply [~ next.result.a] seed gate(now 1.101) credential msg-2(step %verify, proof [~ proof-2]))
  ?>  ?=([%pending %applied *] v)
  =/  c  (apply [~ next.result.v] seed gate(now 1.102) credential msg-2(step %commit, proof [~ proof-2]))
  ?>  ?=([%committed %applied *] c)
  next.result.c
++  test-pack-carrier-opens-current-anchor-and-applies-verified-proof
  ^-  tang
  =/  saved  first
  ?>  =(generation.saved 1)
  ?>  =(snapshot.current.saved '4daa4e155c8f9d48ec82f89c1c7827380714cf549afad6804a1f2367f099a12f')
  ?>  =(pending.saved ~)
  ?>  (valid:stead-code-pack-ledger saved seed)
  ~
++  test-pack-carrier-receipt-selects-exact-historical-base
  ^-  tang
  =/  saved  second
  ?>  =(generation.saved 2)
  ?>  =(snapshot.current.saved '2b5fc025fadf2d4ade709ba3f40f06c96bf5bb8bc86b5bdf134f6efc8dca8969')
  =/  deny-worker=worker-check:stead-code-pack-control
    |=([admission:stead-code-pack-ledger checked:stead-code-pack-ledger] |)
  =/  restarted
    gate(now 1.103, incarnation '2b5fc025fadf2d4ade709ba3f40f06c96bf5bb8bc86b5bdf134f6efc8dca8969', worker deny-worker)
  ?>  ?=([%committed %replayed *] (apply [~ saved] seed restarted credential msg-1(step %receipt, proof [~ proof-1])))
  ?>  ?=([%committed %replayed *] (apply [~ saved] seed restarted credential msg-2(step %receipt, proof [~ proof-2])))
  ?>  ?=([%refused %invalid-proof] (apply [~ saved] seed restarted credential msg-1(step %receipt, proof [~ proof-2])))
  ?>  ?=([%refused %denied] (apply [~ saved] seed restarted credential msg-1(step %receipt, request request.msg-2, proof [~ proof-1])))
  ?>  ?=([%refused %invalid-admission] (apply [~ saved] seed restarted credential msg-1(step %commit, proof [~ proof-1])))
  ~
++  test-pack-carrier-refuses-missing-credential-inexact-time-and-worker
  ^-  tang
  ?>  ?=([%refused %denied] (apply ~ seed gate '' msg-1))
  ?>  ?=([%refused %invalid-admission] (apply ~ seed gate(now 1.001) credential msg-1))
  ?>  ?=([%refused %invalid-admission] (apply ~ seed gate credential msg-1(proof [~ proof-1])))
  =/  a  (apply ~ seed gate credential msg-1)
  ?>  ?=([%pending %applied *] a)
  =/  deny-worker=worker-check:stead-code-pack-control
    |=([admission:stead-code-pack-ledger checked:stead-code-pack-ledger] |)
  ?>  ?=([%refused %worker-denied] (apply [~ next.result.a] seed gate(worker deny-worker) credential msg-1(step %verify, proof [~ proof-1])))
  ?>  ?=([%refused %invalid-proof] (apply [~ next.result.a] seed gate credential msg-1(step %verify)))
  ~
--

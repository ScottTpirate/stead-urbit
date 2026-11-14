/+  *test, stead-code-pack-admit, stead-code-pack-proof, stead-code-credentials, stead-code-pack-ledger, stead-codec
=,  stead-code-pack-admit
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  destination=scope:stead-code-credentials  [~zod project project 1]
=/  current=manifest
  :*  destination  'a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af'
      '726566732f68656164732f6d61696e'  (malt ~[['726566732f68656164732f6d61696e' '07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc']])
      '960476b9a1028ebf443621355100782660490b3da12c3b17979988d17abf5a88'  164  2  189
      '28b0737ef6149aea47c58298976ca9e413a69a2522f900a23618e8e3e382c66e'
  ==
::  Python canonical admissions and worker proofs, produced using pinned Git.
=/  admitted=@t
  (cat 3 '{"actor":{"binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"3","identity_ship":"~bus","principal_id":"019939ba-4000-7000-8000-000000000002"},"admitted_at_ms":"1000","attempt":"1","base_snapshot":"a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af","changes":{"00":{"prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f65786163742dff","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc"}},"expires_at_ms":"301000","generation":"0","incarnation":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","protocol":"stead.git-pack-admission/1","request_id":"019939ba-4000-7000-8000-000000000004","scope":{"authority_epoch":"1","home":"~zod","project_id":"019939ba-4000-7000-8000-000000000001","repository_id":"019939ba-4000-7000-8000-000000000001"},"update_count":"1","wire_sha256":"0a795defdcee0d36429e71c162e273934cec59f4eea4302fa098fb528af568eb"}' 10)
=/  owner=actor
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 3 & 2.000.000]
=/  pin=@t  (hash-wire:stead-code-pack-proof admitted)
=/  input  (need (decode-admission:stead-code-pack-proof admitted pin current))
=/  claim  claim.input
|%
++  test-pack-admit-exact-python-roundtrip
  ^-  tang
  ?>  =([~ admitted pin] (build destination claim owner 1.000 current))
  =/  short  owner(expires 1.500)
  =/  built  (need (build destination claim short 1.001 current))
  =/  read  (need (decode-admission:stead-code-pack-proof wire.built digest.built current))
  ?>  =(since.read 1.001)
  ?>  =(until.read 1.500)
  ?>  =(claim.read claim)
  ~
++  test-pack-admit-refuses-wrong-scope-and-invalid-actor
  ^-  tang
  ?>  =(~ (build destination(epoch 2) claim owner 1.000 current))
  ?>  =(~ (build destination claim(base pin) owner 1.000 current))
  ?>  =(~ (build destination claim owner(active |) 1.000 current))
  ?>  =(~ (build destination claim owner(ship ~zod) 1.000 current))
  ?>  =(~ (build destination claim owner 2.000.000 current))
  ?>  =(~ (build destination claim(generation 7) owner 1.000 current))
  ~
++  test-pack-admit-refuses-duplicate-or-oversized-changes
  ^-  tang
  =/  listed  changes.claim
  ?>  ?=(^ listed)
  ?>  =(~ (build destination claim(changes [i.listed listed]) owner 1.000 current))
  =/  many=(list update)
    %+  turn  (gulf 10 41)
    |=  number=@ud
    =/  stem  (cat 3 'refs/heads/' (decimal:stead-codec number))
    =/  suffix  (crip (reap 1.010 'a'))
    [(cat 3 stem suffix) 0x0 0x11]
  ?>  =(~ (build destination claim(changes many) owner 1.000 current))
  ~
--

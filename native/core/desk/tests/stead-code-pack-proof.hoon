/+  *test, stead-code-pack-proof, stead-code-pack-anchor, stead-codec, stead-git
=,  stead-code-pack-proof
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  current=manifest
  :*  [~zod project project 1]  'a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af'
      '726566732f68656164732f6d61696e'  (malt ~[['726566732f68656164732f6d61696e' '07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc']])
      '960476b9a1028ebf443621355100782660490b3da12c3b17979988d17abf5a88'  164  2  189
      '28b0737ef6149aea47c58298976ca9e413a69a2522f900a23618e8e3e382c66e'
  ==
::  Canonical input and output from Python git_pack_proof against stock Git.
=/  admitted=@t
  (cat 3 '{"actor":{"binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"3","identity_ship":"~bus","principal_id":"019939ba-4000-7000-8000-000000000002"},"admitted_at_ms":"1000","attempt":"1","base_snapshot":"a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af","changes":{"00":{"prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f65786163742dff","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc"},"01":{"prior":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc","ref":"726566732f68656164732f6d61696e","target":"f9464fd3edb67b36617065ace26442e08019fef9"}},"expires_at_ms":"6000","generation":"0","incarnation":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","protocol":"stead.git-pack-admission/1","request_id":"019939ba-4000-7000-8000-000000000004","scope":{"authority_epoch":"1","home":"~zod","project_id":"019939ba-4000-7000-8000-000000000001","repository_id":"019939ba-4000-7000-8000-000000000001"},"update_count":"2","wire_sha256":"f3d275a0085bb7acf743a930ea4971384d55a20cf0128ec0252977aa16af77c1"}' 10)
=/  proof=@t
  (cat 3 '{"actor":{"binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"3","identity_ship":"~bus","principal_id":"019939ba-4000-7000-8000-000000000002"},"admission_sha256":"e80157e568a80d2e4a1a13340c6bdb4317a9050569e769b01d19f7363a89f14d","admitted_at_ms":"1000","attempt":"1","base_snapshot":"a335cd8a77fa8910c2afd5b1fee7a7674b2f4d722382a04a40fbc6d593d555af","candidate_snapshot":"40f2a68135a3c5fff1bfa6e4b2e8c492eadf35bdf1882737ccf27110019aa333","expires_at_ms":"6000","generation":"0","head":"726566732f68656164732f6d61696e","incarnation":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","pack":{"object_bytes":"429","object_count":"3","object_ids_sha256":"cd9cb8c0a43c31bdd4d183c9b6835e624d424eb54181947977022d31812aa5ff","pack_bytes":"221","pack_sha256":"ad9e24020f945801ebb4b710d5ae7a525ec2c60a35d82eba6aa1e92829116b6a"},"protocol":"stead.git-pack-worker-proof/1","request_id":"019939ba-4000-7000-8000-000000000004","scope":{"authority_epoch":"1","home":"~zod","project_id":"019939ba-4000-7000-8000-000000000001","repository_id":"019939ba-4000-7000-8000-000000000001"},"update_count":"2","updates":{"00":{"kind":"commit","lineage":"none","prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f65786163742dff","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc"},"01":{"kind":"commit","lineage":"fast-forward","prior":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc","ref":"726566732f68656164732f6d61696e","target":"f9464fd3edb67b36617065ace26442e08019fef9"}},"wire_sha256":"f3d275a0085bb7acf743a930ea4971384d55a20cf0128ec0252977aa16af77c1"}' 10)
=/  digest=@t  'e80157e568a80d2e4a1a13340c6bdb4317a9050569e769b01d19f7363a89f14d'
=/  expected=@t  '40f2a68135a3c5fff1bfa6e4b2e8c492eadf35bdf1882737ccf27110019aa333'
|%
++  test-pack-proof-exact-python-canonical-admission-and-proof
  =/  original  (need (decode-admission admitted digest current))
  =/  checked  (need (decode-proof proof admitted digest current))
  =/  changes  changes.checked
  ?>  ?=(^ changes)
  =/  first  i.changes
  =/  ok=?
    ?&  =(snapshot.pack.checked expected)
        =(base.checked snapshot.current)
        =(attempt.claim.original 1)
        =(changes.checked changes.claim.original)
        =(2 (lent changes.checked))
        =(2 ~(wyt by kinds.checked))
        =(1 ~(wyt in lineage.checked))
        =((bytes-hex:stead-codec name.first) '726566732f746167732f65786163742dff')
        =((oid-text:stead-git target.first) '07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc')
    ==
  (expect !>(ok))
++  test-pack-proof-refuses-noncanonical-sha-and-length
  =/  no-lf=@t  (cut 3 [0 (dec (met 3 admitted))] admitted)
  =/  oversized=@t  (cat 3 admitted (lsh [3 65.536] 10))
  =/  ok=?
    ?&  =(~ (decode-admission admitted expected current))
        =(~ (decode-admission no-lf (hash-wire no-lf) current))
        =(~ (decode-admission oversized digest current))
        =(~ (decode-proof (cat 3 proof 10) admitted digest current))
    ==
  (expect !>(ok))
++  test-pack-proof-refuses-substituted-head-scope-or-update-order
  =/  wrong-head=@t
    (rap 3 ~[(cut 3 [0 516] proof) '746167732f65786163742dff' (cut 3 [536 1.056] proof)])
  =/  wrong-scope=@t
    (rap 3 ~[(cut 3 [0 978] proof) '2' (cut 3 [979 613] proof)])
  =/  reversed=@t
    (rap 3 ~[(cut 3 [0 1.166] proof) 'fast-forward","prior":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc","ref":"726566732f68656164732f6d61696e","target":"f9464fd3edb67b36617065ace26442e08019fef9"},"01":{"kind":"commit","lineage":"none","prior":"0000000000000000000000000000000000000000","ref":"726566732f746167732f65786163742dff","target":"07d3e6bee13ee85e00e9c30a24d7e7ab9859ffdc' (cut 3 [1.506 86] proof)])
  =/  ok=?
    ?&  =(~ (decode-proof wrong-head admitted digest current))
        =(~ (decode-proof wrong-scope admitted digest current))
        =(~ (decode-proof reversed admitted digest current))
    ==
  (expect !>(ok))
++  test-pack-proof-refuses-unknown-key-inventory-and-stale-digest
  =/  extra=@t
    (rap 3 ~[(cut 3 [0 1.173] proof) 'new":"unrecognized","' (cut 3 [1.173 419] proof)])
  =/  wrong-pack=@t
    (rap 3 ~[(cut 3 [0 664] proof) '1' (cut 3 [665 927] proof)])
  =/  wrong-ref=@t
    (rap 3 ~[(cut 3 [0 1.251] proof) 'f74686572' (cut 3 [1.264 328] proof)])
  =/  ok=?
    ?&  =(~ (decode-proof extra admitted digest current))
        =(~ (decode-proof wrong-pack admitted digest current))
        =(~ (decode-proof wrong-ref admitted digest current))
    ==
  (expect !>(ok))
--

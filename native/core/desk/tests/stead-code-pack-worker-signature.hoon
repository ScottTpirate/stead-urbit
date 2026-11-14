/+  *test, stead-code-pack-worker-signature
=,  stead-code-pack-worker-signature
=/  public  'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a'
=/  proof  (cat 3 '{"protocol":"stead.git-pack-worker-proof/1","candidate_snapshot":"test"}' 10)
=/  sig
  'c5940957a474e0c05b4074e69ae9123fda7d7217b575cf6c2d55b807492776cd39528f82fc3ce3bbcab3d2c5ea9914b3afea986e558200a52d27cdd9b1e9a40f'
|%
++  test-pack-worker-signature-exact-proof-and-generation
  ^-  tang
  ;:  weld
    (expect-eq !>(%.y) !>((verify [7 public] 7 proof sig)))
    (expect-eq !>(%.n) !>((verify [8 public] 7 proof sig)))
    (expect-eq !>(%.n) !>((verify [8 public] 8 proof sig)))
    (expect-eq !>(%.n) !>((verify [7 public] 7 (cat 3 proof 10) sig)))
  ==
++  test-pack-worker-signature-canonical-key-and-scalar
  ^-  tang
  =/  malformed
    'c5940957a474e0c05b4074e69ae9123fda7d7217b575cf6c2d55b807492776cd262685df16a0f513a150ca68c993f3c7afea986e558200a52d27cdd9b1e9a41f'
  =/  weak-key  '0100000000000000000000000000000000000000000000000000000000000000'
  ;:  weld
    (expect-eq !>(%.n) !>((verify [7 public] 7 proof malformed)))
    (expect-eq !>(%.n) !>((verify [7 public] 7 proof '')))
    (expect-eq !>(%.n) !>((verify [7 weak-key] 7 proof sig)))
    (expect-eq !>(%.n) !>((verify [7 public] 7 '' sig)))
  ==
--

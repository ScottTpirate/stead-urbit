::  Trusted disposable source-capture helper only. Reads actual idle Gall
::  old-state, including its original type. No app mark or mutation route.
/+  stead-codec, stead-team, stead-product-home, stead-code-home, stead-home-handoff, stead-project-retirement, stead-code-pack-anchor, stead-team-owner
:-  %say
|=  [[now=@da eny=@uvJ bec=beak] [[wanted=@tas offset=@ud expected=@t] ~] ~]
:-  %noun
?>  &(=(~zod p.bec) ?=(?(%predecessor %product) wanted))
?>  .^(? %j /(scot %p p.bec)/fake/(scot %da now))
?>  =(%.n .^(? %gu /=stead-home=/$))
=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)
?>  ?=([%20 %live *] egg)
=/  saved=vase  +.old-state.egg
=/  stored
  !<  [%stead-home %10 profile=@t target=target:stead-product-home code=persisted:stead-code-home mode=phase:stead-home-handoff retired=ledger:stead-project-retirement packs=state:stead-code-pack-anchor external=external-writes:stead-team-owner reviews=pack-boards:stead-team-owner]
  saved
?>  &((lte offset 262.144) =(0 (mod offset 16.384)))
?>  &(=(wanted -.target.stored) =('native-human-doc/1' profile.stored))
?>  ?&  =(code.stored *persisted:stead-code-home)
        =(mode.stored [%open 1 ~])
        ?=(~ retired.stored)  ?=(~ packs.stored)
        ?=(~ external.stored)  ?=(~ reviews.stored)
    ==
=/  db  ?:(?=(%predecessor -.target.stored) db.target.stored db.value.target.stored)
=/  config  (need current.registry.db)
?>  &(=(~zod home.config) =('isolated-fake' runtime.config) =('local-disposable' custody.config))
=/  packed  (jam saved)
=/  total  (met 3 packed)
?>  &((gth total 0) (lte total 262.144) (lth offset total))
=/  pin  (hash:stead-codec 'stead.v10-capture/1' (bytes-hex:stead-codec packed))
?>  ?:  =(0 offset)
      =('' expected)
    =(pin expected)
=/  size  (min 16.384 (sub total offset))
=/  chunk  (cut 3 [offset size] packed)
^-  @ux
%-  canonical:stead-codec
%-  object:stead-codec
:~  ['protocol' 'stead.v10-capture/1']
    ['target' (scot %tas wanted)]
    ['offset' (decimal:stead-codec offset)]
    ['length' (decimal:stead-codec size)]
    ['total_bytes' (decimal:stead-codec total)]
    ['capture_pin' pin]
    ['native_vase_fingerprint' (hex:stead-codec 64 (shax packed))]
    ['type_pin' (hash:stead-codec 'stead.v10-type-observation/1' (bytes-hex:stead-codec (jam p.saved)))]
    ['payload_pin' (hash:stead-codec 'stead.v10-payload-observation/1' (bytes-hex:stead-codec (jam q.saved)))]
    ['data_hex' (hex:stead-codec (mul 2 size) (rev 3 size chunk))]
==

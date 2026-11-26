::  Read-only fixed saved8 observer for the disposable asset rehearsal.
::  Installed on %base, never retained in the %release-test Home package.
::  Reads Gall's actual suspended vase. No noun input or mutation route.
/+  stead-codec
:-  %say
|=  [[now=@da eny=@uvJ bec=beak] [[offset=@ud expected=@t] ~] ~]
:-  %noun
?>  =(~zod p.bec)
?>  .^(? %j /(scot %p p.bec)/fake/(scot %da now))
?>  =(%.n .^(? %gu /=stead-home=/$))
?>  =(%release-test .^(desk %gd /=stead-home=/$))
=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)
?>  ?=([%20 %live *] egg)
=/  saved=vase  +.old-state.egg
=/  stored
  !<  [%stead-home %8 team=[db=* projection=*] code=* handoff=* retired=* packs=* external=*]
  saved
::  The fixed producer's populated outer tails must survive every stage.
?>  ?&  ?=(^ code.stored)  ?=(^ -.code.stored)
        =(handoff.stored [%open 2 ~])
        ?=(^ retired.stored)  ?=(^ packs.stored)  ?=(^ external.stored)
    ==
?>  &((lth offset 262.144) =(0 (mod offset 16.384)))
=/  packed  (jam saved)
=/  total  (met 3 packed)
?>  &((gth total 0) (lte total 262.144) (lth offset total))
=/  pin  (hash:stead-codec 'stead.saved8-capture/1' (bytes-hex:stead-codec packed))
?>  ?:  =(0 offset)  =('' expected)
    =(pin expected)
=/  size  (min 16.384 (sub total offset))
=/  chunk  (cut 3 [offset size] packed)
=/  durable  [db.team.stored code.stored handoff.stored retired.stored packs.stored external.stored]
^-  @ux
^-  @
%-  canonical:stead-codec
%-  object:stead-codec
:~  ['protocol' 'stead.saved8-capture/1']
    ['offset' (decimal:stead-codec offset)]
    ['length' (decimal:stead-codec size)]
    ['total_bytes' (decimal:stead-codec total)]
    ['capture_pin' pin]
    ['vase_fingerprint' (hex:stead-codec 64 (shax packed))]
    ['type_pin' (hash:stead-codec 'stead.saved8-type/1' (bytes-hex:stead-codec (jam p.saved)))]
    ['payload_pin' (hash:stead-codec 'stead.saved8-payload/1' (bytes-hex:stead-codec (jam q.saved)))]
    ['durable_pin' (hash:stead-codec 'stead.saved8-durable/1' (bytes-hex:stead-codec (jam durable)))]
    ['db_pin' (hash:stead-codec 'stead.saved8-tail/1' (bytes-hex:stead-codec (jam db.team.stored)))]
    ['code_pin' (hash:stead-codec 'stead.saved8-tail/1' (bytes-hex:stead-codec (jam code.stored)))]
    ['handoff_pin' (hash:stead-codec 'stead.saved8-tail/1' (bytes-hex:stead-codec (jam handoff.stored)))]
    ['retired_pin' (hash:stead-codec 'stead.saved8-tail/1' (bytes-hex:stead-codec (jam retired.stored)))]
    ['packs_pin' (hash:stead-codec 'stead.saved8-tail/1' (bytes-hex:stead-codec (jam packs.stored)))]
    ['external_pin' (hash:stead-codec 'stead.saved8-tail/1' (bytes-hex:stead-codec (jam external.stored)))]
    ['data_hex' (hex:stead-codec (mul 2 size) (rev 3 size chunk))]
==

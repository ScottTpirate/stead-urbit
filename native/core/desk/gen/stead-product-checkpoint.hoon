::  Read the ACTUAL idle saved predecessor. Never infer it from timing/cards.
/+  stead-codec, stead-team, stead-product-home, stead-code-home, stead-home-handoff, stead-project-retirement, stead-code-pack-anchor, stead-team-owner
:-  %say
|=  *
:-  %noun
?>  =(%.n .^(? %gu /=stead-home=/$))
=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)
?>  ?=([%20 %live *] egg)
=/  saved=vase  +.old-state.egg
=/  stored
  !<  [%stead-home %10 profile=@t target=target:stead-product-home code=persisted:stead-code-home mode=phase:stead-home-handoff retired=ledger:stead-project-retirement packs=state:stead-code-pack-anchor external=external-writes:stead-team-owner reviews=pack-boards:stead-team-owner]
  saved
?>  =('native-human-doc/1' profile.stored)
?>  ?=(%predecessor -.target.stored)
?>  ?&  =(code.stored *persisted:stead-code-home)
        =(mode.stored [%open 1 ~])
        ?=(~ retired.stored)  ?=(~ packs.stored)
        ?=(~ external.stored)  ?=(~ reviews.stored)
    ==
=/  config  (need current.registry.db.target.stored)
?>  &(=(~zod home.config) =('isolated-fake' runtime.config) =('local-disposable' custody.config))
^-  @ux
%-  canonical:stead-codec
%-  object:stead-codec
:~  ['protocol' 'stead.product-checkpoint/1']
    ['profile' profile.stored]
    ['target' 'predecessor']
    ['expected_config_revision' (decimal:stead-codec revision.config)]
    ['predecessor_sha256' (hash:stead-codec 'stead.product-predecessor/1' (bytes-hex:stead-codec (jam db.target.stored)))]
==

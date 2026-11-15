::  Owner-Dojo-only rehearsal input. Reads the exact saved predecessor; no write.
::  Activation still independently checks actual Gall owner, Jael fake, runtime,
::  custody, no-Code state, configuration revision and this digest.
/+  stead-codec, stead-team, stead-team-owner
:-  %say
|=  *
:-  %noun
=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)
?>  ?=([%20 %live *] egg)
=/  saved=vase  +.old-state.egg
=/  stored  !<([%stead-home %3 team=saved:stead-team-owner] saved)
=/  config  (need current.registry.db.team.stored)
?>  &(=('isolated-fake' runtime.config) =('local-disposable' custody.config))
^-  @ux
%-  canonical:stead-codec
%-  object:stead-codec
:~  ['protocol' 'stead.product-activate/1']
    ['profile' 'native-human-doc/1']
    ['expected_config_revision' (decimal:stead-codec revision.config)]
    ['predecessor_sha256' (hash:stead-codec 'stead.product-predecessor/1' (bytes-hex:stead-codec (jam db.team.stored)))]
==

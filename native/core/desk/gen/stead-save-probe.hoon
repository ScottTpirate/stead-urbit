::  Actual agent arms and serialized v2 noun; synthetic bowl, no network claim.
/=  home-agent  /app/stead-home
:-  %say
|=  *
:-  %noun
=/  context=bowl:gall  *bowl:gall
=/  initial  ~(. home-agent context(our ~zod, src ~zod, now ~2026.9.25))
=/  saved=vase  on-save:initial
?>  ?=([%stead-home %2 *] q.saved)
=+  [cards after]=(on-load:initial saved)
?>  =(~ cards)
=/  reloaded=vase  on-save:after
?>  =(q.saved q.reloaded)
%stead-save-format2-roundtrip-pass

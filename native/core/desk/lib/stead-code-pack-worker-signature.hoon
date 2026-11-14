::  A worker attests its exact canonical proof. The Home selects the active
::  key generation and public key from its own policy, never from the proof.
/+  stead-codec, stead-code-pack-anchor, stead-code-pack-push
|%
+$  pin  [generation=@ud public=@t]
++  generation-valid
  |=  generation=@ud
  &((gth generation 0) (lte generation 18.446.744.073.709.551.615))
++  signed-message
  |=  [generation=@ud proof=@t]
  ^-  @t
  =/  domain=@t  'stead.git-pack-worker-attestation/1'
  =/  epoch  (decimal:stead-codec generation)
  =/  size  (met 3 proof)
  =/  digest  (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size proof)]))
  %-  can  :-  3
  :~  [(met 3 domain) domain]  [1 0]
      [(met 3 epoch) epoch]    [1 0]
      [64 digest]
  ==
++  wire-atom
  |=  [raw=@t width=@ud]
  ^-  @
  (rev 3 width (raw-ref:stead-code-pack-push raw))
++  verify
  |=  [active=pin claimed=@ud proof=@t signature=@t]
  ^-  ?
  ?.  ?&  (generation-valid generation.active)
          =(generation.active claimed)
          (gth (met 3 proof) 0)  (lte (met 3 proof) 65.536)
          (hex-text:stead-code-pack-anchor public.active 64)
          (hex-text:stead-code-pack-anchor signature 128)
      ==
    |
  =/  public  (wire-atom public.active 32)
  =/  sig  (wire-atom signature 64)
  =/  scalar  `@uxscalar`(cut 3 [32 32] sig)
  =/  prime  (sub (bex 255) 19)
  ?.  ?&  (lth (end 0^255 public) prime)
          (lth (end 0^255 sig) prime)
          =(scalar (recs:ed:crypto scalar))
      ==
    |
  =/  cofactor  (mule |.((scalarmult:ed:crypto 0x8 `@uxpoint`public)))
  ?:  ?=(%| -.cofactor)  |
  ?:  =(1 p.cofactor)  |
  =/  message  (signed-message claimed proof)
  (veri-octs:ed:crypto sig [(met 3 message) message] public)
--

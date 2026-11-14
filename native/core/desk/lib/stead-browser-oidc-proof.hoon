::  Pure proof verification only. The caller owns enrollment, current challenge
::  capacity/revisions, browser confirmation and one-use session transitions.
::  No provider token, caller-supplied key, route or saved state is admitted.
/+  stead-codec, stead-session, stead-code-pack-anchor, stead-code-pack-worker-signature
=,  stead-codec
|%
+$  pin
  $:  home=@p  origin=@t  organization=@t  verifier=@t  revision=@ud
      issuer=@t  public=@t  policy=?
  ==
+$  challenge  [id=@t incarnation=@t until=@ud]
+$  identity  [subject=@t assurance=@tas issued=@ud expires=@ud]
++  tick
  |=  value=@ud
  &((gth value 0) (lte value 18.446.744.073.709.551.615))
++  identifier
  |=  value=@t
  ^-  ?
  ?.  =(36 (met 3 value))  |
  =/  index=@ud  0
  |-
  ?:  =(36 index)  &
  =/  byte  (cut 3 [index 1] value)
  ?:  ?|(=(index 8) =(index 13) =(index 18) =(index 23))
    &(=(byte '-') $(index +(index)))
  ?.  ?|(&((gte byte 48) (lte byte 57)) &((gte byte 97) (lte byte 102)))  |
  ?:  =(index 14)
    &((gte byte '1') (lte byte '8') $(index +(index)))
  ?:  =(index 19)
    &(?|(=(byte '8') =(byte '9') =(byte 'a') =(byte 'b')) $(index +(index)))
  $(index +(index))
++  point-valid
  |=  point=@
  ^-  ?
  ?.  (lth (end 0^255 point) (sub (bex 255) 19))  |
  =/  cofactor  (mule |.((scalarmult:ed:crypto 0x8 `@uxpoint`point)))
  ?:  ?=(%| -.cofactor)  |
  !=(1 p.cofactor)
++  read-wire
  |=  raw=@t
  ^-  object-map
  ?>  &((gth (met 3 raw) 0) (lte (met 3 raw) 2.048))
  =/  value  (need (parse raw))
  ?>  ?=(%o -.value)
  =/  fields  p.value
  ?>  (keys fields ~['protocol' 'home' 'origin' 'organization_id' 'verifier_id' 'verifier_revision' 'issuer_id' 'challenge_id' 'incarnation' 'subject_tag' 'assurance' 'issued_at_ms' 'expires_at_ms' 'signature'])
  ?>  =(raw (canonical value))
  ?>  %+  levy  ~(tap by fields)
      |=  pair=[key=@t value=json]
      ?.  ?=(%s -.value.pair)  |
      (levy (rip 3 p.value.pair) |=(byte=@ &((gte byte 32) (lth byte 127))))
  fields
++  signed-message
  |=  fields=object-map
  ^-  @t
  =/  domain=@t  'stead.oidc-proof/1'
  =/  body  (canonical [%o (~(del by fields) 'signature')])
  (can 3 ~[[(met 3 domain) domain] [1 0] [(met 3 body) body]])
++  check
  |=  [active=pin pending=challenge now=@ud raw=@t]
  ^-  identity
  ::  All cheap wire/scope/time checks precede the two bounded point checks.
  =/  fields  (read-wire raw)
  ?>  ?&  (lte (met 0 home.active) 128)
          (origin-valid:stead-session origin.active)
          (identifier organization.active)  (identifier verifier.active)
          (identifier issuer.active)  (tick revision.active)  (tick now)
          (tick until.pending)
          (hex-text:stead-code-pack-anchor id.pending 64)
          (hex-text:stead-code-pack-anchor incarnation.pending 64)
          (hex-text:stead-code-pack-anchor public.active 64)
          =('stead.oidc-proof/1' (field fields 'protocol'))
          =((scot %p home.active) (field fields 'home'))
          =(origin.active (field fields 'origin'))
          =(organization.active (field fields 'organization_id'))
          =(verifier.active (field fields 'verifier_id'))
          =((decimal revision.active) (field fields 'verifier_revision'))
          =(issuer.active (field fields 'issuer_id'))
          =(id.pending (field fields 'challenge_id'))
          =(incarnation.pending (field fields 'incarnation'))
      ==
  =/  subject  (field fields 'subject_tag')
  =/  assurance  (field fields 'assurance')
  =/  signature  (field fields 'signature')
  =/  issued  (uint (field fields 'issued_at_ms'))
  =/  expires  (uint (field fields 'expires_at_ms'))
  ?>  ?&  (hex-text:stead-code-pack-anchor subject 64)
          (hex-text:stead-code-pack-anchor signature 128)
          |(=('oidc' assurance) &(policy.active =('oidc-policy-verified' assurance)))
          (tick issued)  (tick expires)  (lth now expires)
          (lte expires until.pending)  (lte until.pending (add now 125.000))
          (lte issued (add now 5.000))  (lth issued expires)
          (lte (sub expires issued) 30.000)
      ==
  =/  public  (wire-atom:stead-code-pack-worker-signature public.active 32)
  =/  sig  (wire-atom:stead-code-pack-worker-signature signature 64)
  =/  scalar  `@uxscalar`(cut 3 [32 32] sig)
  ?>  &(=(scalar (recs:ed:crypto scalar)) (point-valid public) (point-valid (cut 3 [0 32] sig)))
  =/  message  (signed-message fields)
  ?>  (veri-octs:ed:crypto sig [(met 3 message) message] public)
  [subject `@tas`assurance issued expires]
++  verify
  |=  [active=pin pending=challenge now=@ud raw=@t]
  ^-  (unit identity)
  ?.  &((gth (met 3 raw) 0) (lte (met 3 raw) 2.048))  ~
  =/  out  (mule |.((check active pending now raw)))
  ?:  ?=(%| -.out)  ~
  [~ p.out]
--

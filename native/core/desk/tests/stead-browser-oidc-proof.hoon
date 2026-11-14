::  Published host vector; no self-signed native success fixture.
/+  *test, stead-browser-oidc-proof, stead-codec
=,  stead-browser-oidc-proof
=/  active=pin
  [~zod 'https://home.example.test' '00000000-0000-4000-8000-000000000001' '00000000-0000-4000-8000-000000000002' 1 '00000000-0000-4000-8000-000000000003' 'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a' |]
=/  pending=challenge
  ['1111111111111111111111111111111111111111111111111111111111111111' '2222222222222222222222222222222222222222222222222222222222222222' 1.070.000]
=/  proof  '{"assurance":"oidc","challenge_id":"1111111111111111111111111111111111111111111111111111111111111111","expires_at_ms":"1030000","home":"~zod","incarnation":"2222222222222222222222222222222222222222222222222222222222222222","issued_at_ms":"1000000","issuer_id":"00000000-0000-4000-8000-000000000003","organization_id":"00000000-0000-4000-8000-000000000001","origin":"https://home.example.test","protocol":"stead.oidc-proof/1","signature":"21baf7a271d9d2c1c163f5ef35413c5c8da94c7b2b7663967d80164c119caef1671dd34df4e439dfd4819f08af10a2aca29032183ba300bf4abcf731d6009e04","subject_tag":"3fd14320b0de7d6bb5f48da4c8d558ab8658c9b24a7d5a41305cdc82b346c4d8","verifier_id":"00000000-0000-4000-8000-000000000002","verifier_revision":"1"}'
=/  expected=identity
  ['3fd14320b0de7d6bb5f48da4c8d558ab8658c9b24a7d5a41305cdc82b346c4d8' %oidc 1.000.000 1.030.000]
|%
++  changed
  |=  [name=@t value=@t]
  (canonical:stead-codec [%o (~(put by (read-wire proof)) name [%s value])])
++  test-oidc-proof-published-vector
  ^-  tang
  =/  message  (signed-message (read-wire proof))
  ;:  weld
    (expect-eq !>([~ expected]) !>((verify active pending 1.000.000 proof)))
    (expect-eq !>(602) !>((met 3 message)))
    (expect-eq !>('5a8117dfc33b6fddfae133ef811116e9fec5d6f517e481440a8d767f7c57a3f9') !>((hex:stead-codec 64 (sha-256l:sha [(met 3 message) (rev 3 (met 3 message) message)]))))
  ==
++  test-oidc-proof-exact-pin-and-challenge
  ^-  tang
  ;:  weld
    (expect-eq !>(*(unit identity)) !>((verify active(home ~bus) pending 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active(origin 'https://other.example.test') pending 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active(revision 2) pending 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active(issuer '00000000-0000-4000-8000-000000000004') pending 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending(id '2222222222222222222222222222222222222222222222222222222222222222') 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending(incarnation '1111111111111111111111111111111111111111111111111111111111111111') 1.000.000 proof)))
  ==
++  test-oidc-proof-time-and-assurance
  ^-  tang
  ;:  weld
    (expect-eq !>([~ expected]) !>((verify active pending 1.029.999 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.030.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending 994.999 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending(until 1.020.000) 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending(until 1.125.001) 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (changed 'assurance' 'oidc-policy-verified'))))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (changed 'issued_at_ms' '0999999'))))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (changed 'expires_at_ms' '1030001'))))
  ==
++  test-oidc-proof-canonical-wire-and-tamper
  ^-  tang
  ;:  weld
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (cat 3 proof 10))))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (cat 3 ' ' proof))))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 '{"protocol":"x","protocol":"x"}')))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (changed 'extra' 'x'))))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (changed 'subject_tag' '2222222222222222222222222222222222222222222222222222222222222222'))))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 '')))
  ==
++  test-oidc-proof-canonical-key-r-and-scalar
  ^-  tang
  ;:  weld
    (expect-eq !>(%.n) !>((point-valid 0)))
    (expect-eq !>(%.n) !>((point-valid 1)))
    (expect-eq !>(*(unit identity)) !>((verify active(public '0100000000000000000000000000000000000000000000000000000000000000') pending 1.000.000 proof)))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (changed 'signature' '21baf7a271d9d2c1c163f5ef35413c5c8da94c7b2b7663967d80164c119caef1edd3f55c1a631258d69cf7a2def9de1400000000000000000000000000000010'))))
    (expect-eq !>(*(unit identity)) !>((verify active pending 1.000.000 (changed 'signature' '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'))))
  ==
--

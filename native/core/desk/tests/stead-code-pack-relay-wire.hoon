/+  *test, stead-code-pack-relay-wire
=,  stead-code-pack-relay-wire
=/  advertise
  '{"protocol":"stead.git-pack-relay/1","request_id":"019939ba-4000-7000-8000-000000000002","step":"advertise"}'
=/  receipt
  '{"admission_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","protocol":"stead.git-pack-relay/1","request_id":"019939ba-4000-7000-8000-000000000002","step":"receipt"}'
|%
++  test-pack-relay-wire-advertise-closed-frame
  ^-  tang
  =/  answer  (need (decode (cat 3 advertise 10)))
  ?>  ?=(%advertise -.task.answer)
  ?>  ?=(~ attestation.answer)
  ?>  ?=(~ (decode advertise))
  ?>  ?=(~ (decode (rap 3 ~[advertise 10 '{}' 10])))
  ?>  ?=(~ (decode (rap 3 ~[' ' advertise 10])))
  ~
++  test-pack-relay-wire-receipt-preserves-cords
  ^-  tang
  =/  raw  (rap 3 ~[receipt 10 '{"a":"first"}' 10 '{"b":"second"}' 10])
  =/  answer  (need (decode raw))
  ?>  ?=(%receipt -.task.answer)
  ?>  &(?=(~ attestation.answer) =(admission.task.answer (cat 3 '{"a":"first"}' 10)))
  ?>  =(proof.task.answer (cat 3 '{"b":"second"}' 10))
  ?>  ?=(~ (decode (cat 3 raw 10)))
  ?>  ?=(~ (decode (rap 3 ~[receipt 10 '{}' 10])))
  ~
--

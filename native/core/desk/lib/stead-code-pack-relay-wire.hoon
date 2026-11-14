::  Fixed private Git relay framing. The caller authenticates the relay,
::  selects the repository and worker pin, and rechecks the member bearer.
/+  stead-codec, stead-code-pack-owner, stead-code-pack-proof, stead-code-pack-anchor, stead-code-pack-worker-signature, stead-session
=,  stead-codec
|%
+$  signed  [generation=@ud signature=@t]
+$  input  [request=@t task=task:stead-code-pack-owner attestation=(unit signed)]
++  first-line
  |=  raw=@t
  ^-  (unit [line=@t remainder=@t])
  =/  size  (min 65.536 (met 3 raw))
  =/  n=@ud  0
  |-
  ?:  =(n size)  ~
  ?:  =(10 (cut 3 [n 1] raw))
    [~ (cut 3 [0 +(n)] raw) (rsh [3 +(n)] raw)]
  $(n +(n))
++  decode
  |=  raw=@t
  ^-  (unit input)
  ?.  (lte (met 3 raw) 196.608)  ~
  =/  result
    %-  mule  |.
    ^-  input
    =/  top  (need (first-line raw))
    =/  header  (read-wire:stead-code-pack-proof line.top)
    ?>  =('stead.git-pack-relay/1' (field header 'protocol'))
    =/  request  (field header 'request_id')
    ?>  (uuid request)
    =/  common  ~['protocol' 'request_id' 'step']
    =/  step  (field header 'step')
    ?:  =('advertise' step)
      ?>  &((keys header common) =('' remainder.top))
      [request [%advertise ~] ~]
    ?:  =('admit' step)
      ?>  &((keys header ['wire_sha256' 'update_count' 'changes' common]) =('' remainder.top))
      =/  digest  (field header 'wire_sha256')
      ?>  (token-valid:stead-session digest)
      =/  changes  (turn (read-rows:stead-code-pack-proof header 'changes' |) |=(row=row:stead-code-pack-proof change.row))
      [request [%admit digest changes] ~]
    ?>  ?|(=('verify' step) =('commit' step) =('receipt' step))
    =/  lookup  =('receipt' step)
    =/  required  ['admission_sha256' common]
    ?>  (keys header ?:(lookup required ['worker_generation' 'worker_signature' required]))
    =/  digest  (field header 'admission_sha256')
    ?>  (token-valid:stead-session digest)
    =/  admitted  (need (first-line remainder.top))
    =/  proof  (need (first-line remainder.admitted))
    ?>  =('' remainder.proof)
    =/  seal=(unit signed)
      ?:  lookup  ~
      =/  epoch  (uint (field header 'worker_generation'))
      =/  signature  (field header 'worker_signature')
      ?>  &((generation-valid:stead-code-pack-worker-signature epoch) (hex-text:stead-code-pack-anchor signature 128))
      [~ epoch signature]
    ?:  lookup  [request [%receipt line.admitted digest line.proof] ~]
    ?:  =('verify' step)  [request [%verify line.admitted digest line.proof] seal]
    [request [%commit line.admitted digest line.proof] seal]
  ?:  ?=(%| -.result)  ~
  [~ p.result]
--

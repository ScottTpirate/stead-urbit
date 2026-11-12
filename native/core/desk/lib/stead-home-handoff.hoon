::  Owner-operated same-ship move. A sealed pier requires the release ticket.
/+  stead-codec, stead-session
|%
+$  phase  $%([%open generation=@ud ~] [%sealed generation=@ud challenge=@t])
+$  command  [operation=?(%seal %activate) generation=@ud proof=@t]
++  decode
  |=  raw=@t
  ^-  command
  ?>  (lte (met 3 raw) 256)
  =/  value  (need (parse-result:stead-codec raw))
  ?>  ?=([%o *] value)
  ?>  (keys:stead-codec p.value ~['operation' 'generation' 'proof'])
  =/  op  (field:stead-codec p.value 'operation')
  ?>  |(=('seal' op) =('activate' op))
  =/  operation  ?:(=('seal' op) %seal %activate)
  [operation (uint:stead-codec (field:stead-codec p.value 'generation')) (field:stead-codec p.value 'proof')]
++  valid
  |=  mode=phase
  ^-  ?
  &((gth generation.mode 0) (lte generation.mode 18.446.744.073.709.551.615) ?:(?=(%sealed -.mode) (token-valid:stead-session challenge.mode) &))
++  challenge-for
  |=  [home=@p generation=@ud ticket=@t]
  ^-  @t
  (hash:stead-codec 'stead.home-handoff/1' (cat 3 (scot %p home) (cat 3 '/' (cat 3 (decimal:stead-codec generation) (cat 3 '/' ticket)))))
++  transition
  |=  [home=@p prior=phase input=command]
  ^-  (unit phase)
  ?.  &((valid prior) (token-valid:stead-session proof.input))  ~
  ?:  ?=(%open -.prior)
    ?.  &(?=(%seal operation.input) =(generation.input generation.prior))  ~
    =/  next=phase  [%sealed +(generation.prior) proof.input]
    ?:  (valid next)  [~ next]
    ~
  ?.  &(?=(%activate operation.input) =(generation.input generation.prior))  ~
  ?.  =(challenge.prior (challenge-for home generation.prior proof.input))  ~
  [~ %open generation.prior ~]
--

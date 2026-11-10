::  Private owner-local Khan certificate setup for native Eyre TLS.
/-  spider
/+  strandio, stead-codec
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ expected=@p key=wain cert=wain]  ;;([~ @p wain wain] q.arg)
?>  &((gth (lent key) 0) (lte (lent key) 64))
?>  &((gth (lent cert) 0) (lte (lent cert) 128))
?>  (levy (weld key cert) |=([line=@t] (lte (met 3 line) 256)))
=/  m  (strand ,vase)
^-  form:m
;<  =bowl:spider  bind:m  get-bowl:strandio
?>  =(expected our.bowl)
;<  ~  bind:m  (send-raw-card:strandio [%pass /stead-pilot-cert %arvo %e %rule %cert `[key cert]])
(pure:m !>([%stead-core-result (bytes-hex:stead-codec '{"requested":"yes"}')]))

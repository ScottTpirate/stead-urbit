::  Disposable owner-local Khan setup, never a public Gall/HTTP mark.
/-  spider
/+  strandio, stead-codec
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ key=wain cert=wain]  ;;([~ wain wain] q.arg)
?>  &((gth (lent key) 0) (lte (lent key) 64))
?>  &((gth (lent cert) 0) (lte (lent cert) 128))
?>  (levy (weld key cert) |=([line=@t] (lte (met 3 line) 256)))
=/  m  (strand ,vase)
^-  form:m
;<  ~  bind:m  (send-raw-card:strandio [%pass /stead-local-cert %arvo %e %rule %cert `[key cert]])
(pure:m !>([%stead-core-result (bytes-hex:stead-codec '{"requested":"yes"}')]))

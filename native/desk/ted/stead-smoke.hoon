::  Fixture thread waits for the destination Gall poke ACK/NACK.
::  A positive result only means this synthetic transition finished.
/-  spider
/+  strandio
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  m  (strand ,vase)
^-  form:m
=/  [~ target=@p command=*]  ;;([~ target=@p command=*] q.arg)
;<  ~  bind:m  (poke:strandio [target %stead-home] %noun !>(command))
(pure:m !>(%stead-smoke-ack))

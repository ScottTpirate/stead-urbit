/+  default-agent
=>
|%
+$  state-1  [%1 count=@ud revision=@ud]
+$  saved  $%([%0 count=@ud] [%1 count=@ud revision=@ud])
--
=|  state=state-1
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def   ~(. (default-agent this %|) bowl)
++  on-init
  `this
++  on-save
  !>(state)
++  on-load
  |=  old=vase
  =/  restored  !<(saved old)
  =/  next=state-1
    ?-  -.restored
      %0  [%1 count.restored 0]
      %1  restored
    ==
  ?>  &((lte count.next 65.535) (lte revision.next 65.535))
  `this(state next)
++  on-poke   on-poke:def
++  on-watch  on-watch:def
++  on-leave  on-leave:def
++  on-peek   on-peek:def
++  on-agent  on-agent:def
++  on-arvo   on-arvo:def
++  on-fail   on-fail:def
--

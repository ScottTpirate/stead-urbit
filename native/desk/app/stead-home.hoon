::  URB-020 synthetic native probe. No Work/Docs, sessions, Git, or live use.
::  One mutation owner; no HTTP routes, subscriptions, or application scries.
/+  default-agent, stead-smoke
=>
|%
+$  state-0  [%0 count=@ud]
+$  command
  $%  [%advance claimed-author=@p expected=@ud]
      [%assert expected=@ud]
  ==
--
=|  state=state-0
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
  =/  restored  !<(state-0 old)
  `this(state restored)
++  on-poke
  |=  [=mark =vase]
  ^-  (quip card:agent:gall _this)
  ?>  =(%noun mark)
  =/  cmd  ;;(command q.vase)
  ?-  -.cmd
    %assert
      ::  Assertion is only a fixture administration operation on this fake home.
      ?.  =(our.bowl src.bowl)
        ~|  %stead-smoke-denied
        !!
      ?.  =(expected.cmd count.state)
        ~|  %stead-smoke-assertion
        !!
      `this
    %advance
      ::  claimed-author is deliberately ignored: the negative corpus spoofs it.
      ?.  =(~bus src.bowl)
        ~|  %stead-smoke-denied
        !!
      =/  next  (advance:stead-smoke src.bowl count.state expected.cmd)
      ?~  next
        ~|  %stead-smoke-stale
        !!
      `this(state [%0 u.next])
  ==
++  on-watch  on-watch:def
++  on-leave  on-leave:def
++  on-peek   on-peek:def
++  on-agent  on-agent:def
++  on-arvo   on-arvo:def
++  on-fail   on-fail:def
--

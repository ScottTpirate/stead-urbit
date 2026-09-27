/+  default-agent
=>
|%
+$  state-0  [%0 value=@ud]
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
  `this(state !<(state-0 old))
++  on-poke
  |=  [=mark =vase]
  ^-  (quip card:agent:gall _this)
  !!
++  on-watch
  |=  =path
  ^-  (quip card:agent:gall _this)
  !!
++  on-leave  on-leave:def
++  on-peek   on-peek:def
++  on-agent  on-agent:def
++  on-arvo   on-arvo:def
++  on-fail   on-fail:def
--

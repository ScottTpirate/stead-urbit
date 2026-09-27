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
  ?.  =(%noun mark)
    ~|  %eval-mark
    !!
  ?.  =(~bus src.bowl)
    ~|  %eval-denied
    !!
  =/  command  !<([%set claimed=@p value=@ud] vase)
  ?.  (lte value.command 255)
    ~|  %eval-limit
    !!
  `this(state [%0 value.command])
++  on-watch
  |=  =path
  ^-  (quip card:agent:gall _this)
  ?.  =(path /value)
    ~|  %eval-path
    !!
  ?.  ?|(=(~bus src.bowl) =(~nec src.bowl))
    ~|  %eval-denied
    !!
  :_  this
  :~  [%give %fact ~ %noun !>(value.state)]
      [%give %kick ~ ~]
  ==
++  on-leave  on-leave:def
++  on-peek   on-peek:def
++  on-agent  on-agent:def
++  on-arvo   on-arvo:def
++  on-fail   on-fail:def
--

::  Fixed disposable fake-only seed. No arbitrary input or live import route.
/+  default-agent, stead-home-ui-seed
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def  ~(. (default-agent this %|) bowl)
++  on-init
  ?>  =(our.bowl ~zod)
  ?>  .^(? %j /(scot %p our.bowl)/fake/(scot %da now.bowl))
  `this
++  on-save
  ?>  =(our.bowl ~zod)
  saved-eight:stead-home-ui-seed
++  on-load
  |=  old=vase
  !!
++  on-poke
  |=  [=mark =vase]
  !!
++  on-watch
  |=  path=path
  !!
++  on-leave  on-leave:def
++  on-peek  on-peek:def
++  on-agent  on-agent:def
++  on-arvo  on-arvo:def
++  on-fail  on-fail:def
--

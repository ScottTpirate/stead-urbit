::  Personal-ship approval owner. Business authority remains at stead-home.
/+  default-agent, stead-identity-owner
=|  owner=state:stead-identity-owner
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def  ~(. (default-agent this %|) bowl)
    helper  ~(. (driver:stead-identity-owner owner) bowl)
++  on-init
  =/  [cards=(list card:agent:gall) next=state:stead-identity-owner]  init:helper
  [cards this(owner next)]
++  on-load
  |=  old=vase
  =/  [cards=(list card:agent:gall) next=state:stead-identity-owner]  (load:helper old)
  [cards this(owner next)]
++  on-poke
  |=  [=mark =vase]
  =/  [cards=(list card:agent:gall) next=state:stead-identity-owner]  (poke:helper mark vase)
  [cards this(owner next)]
++  on-watch
  |=  route=path
  =/  [cards=(list card:agent:gall) next=state:stead-identity-owner]  (watch:helper route)
  [cards this(owner next)]
++  on-agent
  |=  [=wire =sign:agent:gall]
  =/  [cards=(list card:agent:gall) next=state:stead-identity-owner]  (agent:helper wire sign)
  [cards this(owner next)]
++  on-arvo
  |=  [=wire =sign-arvo]
  =/  [cards=(list card:agent:gall) next=state:stead-identity-owner]  (arvo:helper wire sign-arvo)
  [cards this(owner next)]
++  on-save  save:helper
++  on-leave  on-leave:def
++  on-peek  on-peek:def
++  on-fail  on-fail:def
--

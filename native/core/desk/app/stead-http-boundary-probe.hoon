::  Synthetic runtime-boundary probe; contains no business data or credentials.
/+  default-agent, stead-eyre, stead-codec, stead-http, server
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def  ~(. (default-agent this %|) bowl)
++  on-init
  [[%pass /bind %arvo %e %connect [~ /stead-boundary-probe] dap.bowl]~ this]
++  on-save  !>(~)
++  on-load
  |=  old=vase
  ?>  =(~ !<(~ old))
  on-init
++  on-watch
  |=  route=path
  ?:  =(/public-control route)
    :_  this
    :~  [%give %fact ~ [%json !>((object:stead-codec ~[['public_control' 'yes']]))]]
        [%give %kick ~ ~]
    ==
  ?>  ?=([%http-response @ ~] route)
  ?>  (response-source:stead-eyre sup.bowl src.bowl i.t.route)
  `this
++  on-poke
  |=  [=mark =vase]
  ?:  =(%json mark)
    ?>  =((object:stead-codec ~[['public_control' 'yes']]) !<(json vase))
    `this
  ?>  =(%handle-http-request mark)
  =/  [id=@ta request=inbound-request:eyre]  !<([@ta inbound-request:eyre] vase)
  ?>  (response-source:stead-eyre sup.bowl src.bowl id)
  ::  Count only a bounded prefix; do not echo names, values, cookies or body.
  =/  headers  (scag 33 header-list.request.request)
  =/  cookie-count
    (lent (skim headers |=([key=@t value=@t] =('cookie' (lower:stead-http key)))))
  =/  text
    (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.http-boundary-probe/1'] ['src' (scot %p src.bowl)] ['sap' (spat sap.bowl)] ['secure' ?:(secure.request 'yes' 'no')] ['owner_authenticated' ?:(authenticated.request 'yes' 'no')] ['header_count_capped_33' (decimal:stead-codec (lent headers))] ['cookie_header_count_capped_33' (decimal:stead-codec cookie-count)]]))
  ::  Only source/provenance/route/duct are diagnostic; never log the request.
  =/  matched  (skim ~(tap by sup.bowl) |=([key=duct val=[ship=@p route=path]] =(route.val [%http-response id ~])))
  ~&  [%stead-http-boundary src.bowl sap.bowl matched]
  [(give-simple-payload:app:server id [[200 ~[['content-type' 'application/json'] ['cache-control' 'no-store']]] [~ [(met 3 text) text]]]) this]
++  on-leave  on-leave:def
++  on-peek
  |=  route=path
  ^-  (unit (unit cage))
  ?:  =(/x/public-control/json route)
    ``json+!>((object:stead-codec ~[['public_control' 'yes']]))
  (on-peek:def route)
++  on-agent  on-agent:def
++  on-arvo
  |=  [=wire =sign-arvo]
  ?>  &(?=([%eyre %bound *] sign-arvo) accepted.sign-arvo)
  `this
++  on-fail  on-fail:def
--

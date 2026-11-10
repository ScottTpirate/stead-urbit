::  Owner-local Khan adapter for configuration, bootstrap and Home status.
/-  spider
/+  strandio, stead-codec, stead-delivery
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ expected=@p app=@tas mode=@tas route=path raw=@t]
  ;;([~ @p @tas @tas path @t] q.arg)
?>  (lte (met 3 raw) 65.536)
?>  ?|  =(app %stead-home)
        &(=(app %stead-identity) !=(mode %operator-status))
    ==
=/  m  (strand ,vase)
=/  n  (strand ,~)
^-  form:m
%+  (set-timeout:strandio ,vase)  ~s55
;<  =bowl:spider  bind:m  get-bowl:strandio
?>  =(expected our.bowl)
?:  =(%configure mode)
  ?>  ?=(~ route)
  =/  mark  ?:(=(app %stead-home) %stead-team-config-1 %stead-identity-config-1)
  ;<  ~  bind:m  (poke:strandio [our.bowl app] mark !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?>  ?:  =(%operator-status mode)
      &(?=([%operator @ ~] route) =('' raw))
    &(=(%bootstrap mode) ?=([%bootstrap @ ~] route))
;<  ~  bind:m  (watch:strandio /result [our.bowl app] route)
;<  ~  bind:m
  ?:  =(%operator-status mode)  (pure:n ~)
  (send-raw-card:strandio [%pass /command %agent [our.bowl app] %poke %stead-bootstrap-1 !>(raw)])
=/  state=progress:stead-delivery  [=(%operator-status mode) | ~]
|=  tin=strand-input:strand
=*  loop  $
?:  (complete:stead-delivery state)
  =/  text  (need answer.state)
  `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
=/  event=(unit event:stead-delivery)
  ?+  in.tin  ~
    [~ %agent * %poke-ack *]
      ?.  =(/command wire.u.in.tin)  ~
      `[?^(p.sign.u.in.tin %nack %ack) ~]
    [~ %agent * %fact *]
      ?.  =(/watch/result wire.u.in.tin)  ~
      ?.  =(%stead-result-3 p.cage.sign.u.in.tin)  `[%nack ~]
      =/  text  !<(@t q.cage.sign.u.in.tin)
      ?.  (lte (met 3 text) 2.048)  `[%nack ~]
      `[%fact text]
    [~ %agent * %kick *]
      ?.  =(/watch/result wire.u.in.tin)  ~
      `[%kick ~]
  ==
?~  event  ?~(in.tin `[%wait ~] `[%skip ~])
=/  next  (advance:stead-delivery state u.event)
?~  next  `[%fail %stead-owner-exchange ~]
`[%cont ..loop(state u.next)]
